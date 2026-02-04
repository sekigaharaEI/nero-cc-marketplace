"""
daemon-archon Probe 执行器

负责 Probe 模式的任务启动、监控和纠偏
"""

import os
import re
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from .types import ProbeStatus, AnalysisResult
from .state_store import (
    load_task_config, save_task_config, get_task_dir,
    ensure_task_dir, set_task_status, append_log,
    append_correction, save_destination, acquire_task_lock,
    release_task_lock
)
from .analyzer import TranscriptAnalyzer, read_transcript_incremental, get_transcript_path
from .notifier import notify_task_error, notify_correction_needed, notify_task_completed
from .stuck_detector import mark_check_start, mark_check_end

logger = logging.getLogger(__name__)


class ProbeExecutor:
    """Probe 执行器"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.config: Optional[Dict[str, Any]] = None

    def load_config(self) -> bool:
        """加载任务配置"""
        self.config = load_task_config(self.task_id)
        return self.config is not None

    async def start_probe(
        self,
        initial_prompt: str,
        project_path: str,
        name: str = "",
        description: str = "",
        check_interval_minutes: int = 5,
        max_auto_corrections: int = 3
    ) -> Dict[str, Any]:
        """
        启动 Probe 任务

        Args:
            initial_prompt: 初始提示词
            project_path: 项目路径
            name: 任务名称
            description: 任务描述
            check_interval_minutes: 检查间隔（分钟）
            max_auto_corrections: 最大自动纠偏次数

        Returns:
            任务配置
        """
        task_dir = ensure_task_dir(self.task_id)

        # 启动 Claude Code CLI
        probe_info = await self._start_claude_cli(
            self.task_id,
            initial_prompt,
            project_path
        )

        if not probe_info:
            raise RuntimeError("启动 Probe 失败")

        # 构造配置
        config = {
            "task_id": self.task_id,
            "mode": "probe",
            "name": name or f"Probe 任务 - {self.task_id}",
            "description": description,
            "project_path": project_path,
            "created_at": datetime.utcnow().isoformat() + "Z",

            "probe": {
                "pid": probe_info.get("pid"),
                "session_id": probe_info.get("session_id", self.task_id),
                "log_dir": str(task_dir),
                "initial_prompt": initial_prompt,
                "stdout_log": str(task_dir / "probe_stdout.log"),
                "stderr_log": str(task_dir / "probe_stderr.log"),
                "transcript_path": probe_info.get("transcript_path")
            },

            "schedule": {
                "check_interval_minutes": check_interval_minutes,
                "next_check": None
            },

            "correction": {
                "max_auto_corrections": max_auto_corrections,
                "current_count": 0,
                "escalate_after_failures": 2
            },

            "criteria": {
                "success_indicators": ["任务完成", "测试通过"],
                "failure_indicators": ["错误", "失败", "Error", "Exception"],
                "completion_keywords": ["任务完成", "已完成"]
            },

            "state": {
                "status": "active",
                "last_check": None,
                "last_correction": None,
                "last_transcript_offset": 0
            }
        }

        # 保存配置
        save_task_config(self.task_id, config)
        set_task_status(self.task_id, "active")

        # 创建 destination.md
        destination_content = f"""# 任务目标

## 核心目标
{initial_prompt}

## 验收标准
- [ ] 任务按要求完成
- [ ] 无严重错误

## 完成标志
当 Probe 输出包含以下关键词时认为完成：
{', '.join(config['criteria']['completion_keywords'])}

## 特别说明
无
"""
        save_destination(self.task_id, destination_content)

        append_log(self.task_id, "ACTION", f"Probe 任务已启动, PID: {probe_info.get('pid')}")

        self.config = config
        return config

    async def _start_claude_cli(
        self,
        task_id: str,
        initial_prompt: str,
        project_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        启动 Claude Code CLI

        Args:
            task_id: 任务 ID（同时作为 session_id）
            initial_prompt: 初始提示词
            project_path: 项目路径

        Returns:
            Probe 信息 {pid, session_id, log_dir}
        """
        task_dir = ensure_task_dir(task_id)
        stdout_log = task_dir / "probe_stdout.log"
        stderr_log = task_dir / "probe_stderr.log"

        try:
            # 使用 nohup 后台启动
            with open(stdout_log, 'w') as stdout_f, open(stderr_log, 'w') as stderr_f:
                process = subprocess.Popen(
                    [
                        "claude",
                        "-p", initial_prompt,
                        "--session-id", task_id
                    ],
                    cwd=project_path,
                    stdout=stdout_f,
                    stderr=stderr_f,
                    start_new_session=True  # 创建新会话，防止终端关闭时被杀死
                )

            # 等待一小段时间确保进程启动
            import asyncio
            await asyncio.sleep(2)

            # 检查进程是否存活
            if process.poll() is None:
                logger.info(f"Probe 启动成功, PID: {process.pid}")
                return {
                    "pid": process.pid,
                    "session_id": task_id,
                    "log_dir": str(task_dir)
                }
            else:
                logger.error(f"Probe 启动失败，进程已退出")
                return None

        except Exception as e:
            logger.error(f"启动 Claude CLI 失败: {e}")
            return None

    async def check_probe(self) -> AnalysisResult:
        """
        检查 Probe 状态

        Returns:
            分析结果
        """
        if not self.config:
            if not self.load_config():
                return AnalysisResult(
                    status="error",
                    summary="任务配置不存在"
                )

        # 获取锁
        if not acquire_task_lock(self.task_id):
            return AnalysisResult(
                status="locked",
                summary="任务正在被其他进程检查"
            )

        try:
            mark_check_start(self.task_id)

            # 检查进程状态
            pid = self.config.get("probe", {}).get("pid")
            process_alive = self._check_process_alive(pid)

            if not process_alive:
                append_log(self.task_id, "WARNING", f"Probe 进程 {pid} 已退出")
                set_task_status(self.task_id, "stopped")
                return AnalysisResult(
                    status="stopped",
                    summary=f"Probe 进程 {pid} 已退出"
                )

            # 读取 transcript
            session_id = self.config.get("probe", {}).get("session_id")
            transcript_path = self.config.get("probe", {}).get("transcript_path")

            if not transcript_path and session_id:
                transcript_path = get_transcript_path(session_id)
                if transcript_path:
                    # 更新配置
                    self.config["probe"]["transcript_path"] = transcript_path
                    save_task_config(self.task_id, self.config)

            if not transcript_path:
                return AnalysisResult(
                    status="unknown",
                    summary="无法获取 transcript 路径"
                )

            # 增量读取 transcript
            last_offset = self.config.get("state", {}).get("last_transcript_offset", 0)
            transcript_data = read_transcript_incremental(transcript_path, last_offset)

            # 更新偏移量
            self.config.setdefault("state", {})["last_transcript_offset"] = transcript_data["new_offset"]
            self.config["state"]["last_check"] = datetime.utcnow().isoformat() + "Z"
            save_task_config(self.task_id, self.config)

            # 分析消息
            analyzer = TranscriptAnalyzer(self.config)
            result = analyzer.analyze_messages(transcript_data["messages"])

            append_log(self.task_id, "OUTPUT", f"分析结果: {result.status}, {result.summary}")

            return result

        finally:
            mark_check_end(self.task_id)
            release_task_lock(self.task_id)

    async def handle_check_result(self, result: AnalysisResult) -> None:
        """
        处理检查结果

        Args:
            result: 分析结果
        """
        if result.status == "error" and result.issues:
            await self._handle_error(result)
        elif result.status == "stuck":
            await self._handle_stuck(result)
        elif result.status == "completed":
            await self._handle_completed(result)
        else:
            append_log(self.task_id, "DECISION", "Probe 运行正常，无需干预")

    async def _handle_error(self, result: AnalysisResult) -> None:
        """处理错误状态"""
        if not self.config:
            return

        correction_count = self.config.get("correction", {}).get("current_count", 0)
        max_corrections = self.config.get("correction", {}).get("max_auto_corrections", 3)

        if correction_count >= max_corrections:
            append_log(self.task_id, "DECISION", f"纠偏次数已达上限 ({correction_count}/{max_corrections})")
            notify_correction_needed(
                self.task_id,
                f"任务自动纠偏 {correction_count} 次失败，请手动处理"
            )
            return

        # 执行纠偏
        append_log(self.task_id, "ACTION", f"开始执行纠偏 ({correction_count + 1}/{max_corrections})")
        await self._execute_correction(result)

    async def _handle_stuck(self, result: AnalysisResult) -> None:
        """处理卡住状态"""
        append_log(self.task_id, "WARNING", f"Probe 卡住: {result.summary}")
        notify_task_error(self.task_id, f"Probe 任务卡住: {result.summary}")

    async def _handle_completed(self, result: AnalysisResult) -> None:
        """处理完成状态"""
        append_log(self.task_id, "ACTION", "任务已完成")
        set_task_status(self.task_id, "stopped")
        notify_task_completed(self.task_id, result.summary)

    async def _execute_correction(self, result: AnalysisResult) -> None:
        """
        执行纠偏

        使用 claude --resume 向 Probe 注入纠偏指令
        """
        if not self.config:
            return

        session_id = self.config.get("probe", {}).get("session_id")
        if not session_id:
            logger.error("无法获取 session_id，无法执行纠偏")
            return

        # 构造纠偏指令
        issues_text = "\n".join([
            f"- {issue.get('type')}: {issue.get('message', '')[:100]}"
            for issue in result.issues
        ])

        correction_prompt = f"""检测到以下问题，请修复：

{issues_text}

请分析问题原因并修复，修复后继续执行原任务。
"""

        try:
            # 使用 claude --resume 注入纠偏指令
            process = subprocess.Popen(
                [
                    "claude",
                    "--resume", session_id,
                    "-p", correction_prompt
                ],
                cwd=self.config.get("project_path"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )

            # 更新纠偏计数
            self.config["correction"]["current_count"] = \
                self.config.get("correction", {}).get("current_count", 0) + 1
            self.config["state"]["last_correction"] = datetime.utcnow().isoformat() + "Z"
            save_task_config(self.task_id, self.config)

            # 记录纠偏历史
            append_correction(self.task_id, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "corrector": "Archon",
                "reason": issues_text,
                "analysis": f"问题级别: 中等\n问题数量: {len(result.issues)}",
                "instruction": correction_prompt,
                "result": "执行中",
                "follow_up_status": "待观察"
            })

            append_log(self.task_id, "ACTION", f"纠偏指令已注入, 新 PID: {process.pid}")

        except Exception as e:
            logger.error(f"执行纠偏失败: {e}")
            append_log(self.task_id, "ERROR", f"纠偏失败: {e}")

    def _check_process_alive(self, pid: Optional[int]) -> bool:
        """检查进程是否存活"""
        if not pid:
            return False

        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    async def stop_probe(self, graceful: bool = True, timeout: int = 30) -> bool:
        """
        停止 Probe

        Args:
            graceful: 是否优雅终止
            timeout: 超时时间（秒）

        Returns:
            是否成功停止
        """
        if not self.config:
            if not self.load_config():
                return False

        pid = self.config.get("probe", {}).get("pid")
        if not pid:
            return True

        try:
            import signal

            if graceful:
                os.kill(pid, signal.SIGTERM)
                # 等待进程退出
                import asyncio
                for _ in range(timeout):
                    if not self._check_process_alive(pid):
                        break
                    await asyncio.sleep(1)

                # 如果还没退出，强制杀死
                if self._check_process_alive(pid):
                    os.kill(pid, signal.SIGKILL)
            else:
                os.kill(pid, signal.SIGKILL)

            set_task_status(self.task_id, "stopped")
            append_log(self.task_id, "ACTION", f"Probe 已停止, PID: {pid}")
            return True

        except OSError as e:
            if e.errno == 3:  # No such process
                set_task_status(self.task_id, "stopped")
                return True
            logger.error(f"停止 Probe 失败: {e}")
            return False


async def probe_check_callback(task_id: str) -> None:
    """
    Probe 检查回调函数

    由调度器调用
    """
    executor = ProbeExecutor(task_id)
    result = await executor.check_probe()
    await executor.handle_check_result(result)
