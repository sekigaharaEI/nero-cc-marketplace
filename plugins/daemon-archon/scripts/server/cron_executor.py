"""
daemon-archon Cron 执行器

负责 Cron 模式的任务执行和结果分析
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .types import AnalysisResult
from .state_store import (
    load_task_config, save_task_config, get_task_dir,
    ensure_task_dir, set_task_status, append_log,
    load_workflow, load_task_md, ensure_workflow_dir,
    save_workflow, save_task_md, acquire_task_lock,
    release_task_lock
)
from .analyzer import CronResultAnalyzer
from .notifier import notify_task_error, notify_task_completed
from .stuck_detector import mark_check_start, mark_check_end

logger = logging.getLogger(__name__)


class CronExecutor:
    """Cron 执行器"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.config: Optional[Dict[str, Any]] = None

    def load_config(self) -> bool:
        """加载任务配置"""
        self.config = load_task_config(self.task_id)
        return self.config is not None

    async def create_cron_task(
        self,
        name: str,
        description: str,
        project_path: str,
        task_content: str,
        workflow_content: str,
        cron_expression: Optional[str] = None,
        check_interval_minutes: int = 60,
        timeout_minutes: int = 10
    ) -> Dict[str, Any]:
        """
        创建 Cron 任务

        Args:
            name: 任务名称
            description: 任务描述
            project_path: 项目路径
            task_content: 任务描述内容 (task.md)
            workflow_content: 工作流程内容 (workflow.md)
            cron_expression: Cron 表达式（可选）
            check_interval_minutes: 检查间隔（分钟）
            timeout_minutes: 执行超时时间（分钟）

        Returns:
            任务配置
        """
        task_dir = ensure_task_dir(self.task_id)
        workflow_dir = ensure_workflow_dir(self.task_id)

        # 构造配置
        config = {
            "task_id": self.task_id,
            "mode": "cron",
            "name": name,
            "description": description,
            "project_path": project_path,
            "created_at": datetime.utcnow().isoformat() + "Z",

            "schedule": {
                "cron_expression": cron_expression,
                "check_interval_minutes": check_interval_minutes,
                "next_run": None
            },

            "execution": {
                "timeout_minutes": timeout_minutes,
                "last_run": None,
                "last_result": None,
                "run_count": 0,
                "consecutive_failures": 0,
                "max_consecutive_failures": 3
            },

            "notification": {
                "notify_on_error": True,
                "notify_on_success": False,
                "notify_on_status": ["error"],
                "suspicious_status": ["warning"],
                "enable_claude_analysis": True,
                "quiet_hours": None
            },

            "state": {
                "status": "active",
                "last_check": None
            },

            "cron_state": {
                "next_run_at_ms": None,
                "last_run_at_ms": None,
                "last_run_duration_ms": None,
                "run_count": 0,
                "error_count": 0,
                "last_error": None
            }
        }

        # 保存配置
        save_task_config(self.task_id, config)
        set_task_status(self.task_id, "active")

        # 保存 task.md
        save_task_md(self.task_id, task_content)

        # 保存 workflow.md
        save_workflow(self.task_id, workflow_content)

        append_log(self.task_id, "ACTION", "Cron 任务已创建")

        self.config = config
        return config

    async def execute_cron(self) -> AnalysisResult:
        """
        执行 Cron 任务

        Returns:
            执行结果分析
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
                summary="任务正在被其他进程执行"
            )

        start_time = datetime.now()
        start_ms = int(start_time.timestamp() * 1000)

        try:
            mark_check_start(self.task_id)

            # 更新执行状态
            self.config["execution"]["last_run"] = start_time.isoformat() + "Z"
            self.config["execution"]["last_result"] = None  # 清空，表示正在执行
            self.config["cron_state"]["last_run_at_ms"] = start_ms
            save_task_config(self.task_id, self.config)

            append_log(self.task_id, "ACTION", "开始执行 Cron 任务")

            # 构建提示词
            prompt = self._build_prompt()

            # 执行 Claude CLI
            result = await self._execute_claude_cli(prompt)

            # 计算执行时长
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # 分析结果
            analyzer = CronResultAnalyzer(self.config)
            analysis = analyzer.analyze_output(result.get("output", ""))

            # 更新状态
            self._update_execution_state(analysis, duration_ms)

            append_log(self.task_id, "OUTPUT", f"执行完成: {analysis.status}, {analysis.summary}")

            return analysis

        except subprocess.TimeoutExpired:
            # 超时处理
            return await self._handle_timeout()

        except Exception as e:
            logger.error(f"执行 Cron 任务失败: {e}")
            append_log(self.task_id, "ERROR", f"执行失败: {e}")
            return AnalysisResult(
                status="error",
                summary=str(e),
                issues=[{"type": "execution_error", "message": str(e)}]
            )

        finally:
            mark_check_end(self.task_id)
            release_task_lock(self.task_id)

    def _build_prompt(self) -> str:
        """构建执行提示词"""
        task_md = load_task_md(self.task_id)
        workflow_md = load_workflow(self.task_id)

        prompt = f"""# 任务描述

{task_md}

# 工作流程

{workflow_md}

# 输出要求

请按照工作流程执行任务，并按以下 JSON 格式输出结果：

```json
{{
  "status": "success | warning | error",
  "summary": "一句话总结",
  "findings": [
    {{"level": "info|warning|error", "message": "具体发现"}}
  ],
  "metrics": {{
    "key": value
  }}
}}
```
"""
        return prompt

    async def _execute_claude_cli(self, prompt: str) -> Dict[str, Any]:
        """
        执行 Claude CLI

        Args:
            prompt: 提示词

        Returns:
            执行结果 {output, returncode}
        """
        timeout_seconds = self.config.get("execution", {}).get("timeout_minutes", 10) * 60
        project_path = self.config.get("project_path", ".")

        try:
            # 移除 --output-format json，获取原始文本输出
            result = subprocess.run(
                [
                    "claude",
                    "-p", prompt
                ],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            # 记录原始输出用于调试
            logger.debug(f"Claude CLI 原始输出: {result.stdout[:500]}")

            return {
                "output": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

        except subprocess.TimeoutExpired:
            raise

    def _update_execution_state(
        self,
        analysis: AnalysisResult,
        duration_ms: int
    ) -> None:
        """更新执行状态"""
        if not self.config:
            return

        # 更新执行统计
        self.config["execution"]["last_result"] = analysis.status
        self.config["execution"]["run_count"] = \
            self.config.get("execution", {}).get("run_count", 0) + 1

        # 更新 cron_state
        self.config["cron_state"]["last_run_duration_ms"] = duration_ms
        self.config["cron_state"]["run_count"] = \
            self.config.get("cron_state", {}).get("run_count", 0) + 1

        # 处理失败计数
        if analysis.status == "error":
            self.config["execution"]["consecutive_failures"] = \
                self.config.get("execution", {}).get("consecutive_failures", 0) + 1
            self.config["cron_state"]["error_count"] = \
                self.config.get("cron_state", {}).get("error_count", 0) + 1
            self.config["cron_state"]["last_error"] = analysis.summary
        else:
            self.config["execution"]["consecutive_failures"] = 0
            self.config["cron_state"]["last_error"] = None

        save_task_config(self.task_id, self.config)

    async def _handle_timeout(self) -> AnalysisResult:
        """处理超时"""
        if not self.config:
            return AnalysisResult(status="timeout", summary="任务超时")

        append_log(self.task_id, "WARNING", "任务执行超时")

        # 更新状态
        self.config["execution"]["last_result"] = "timeout"
        self.config["execution"]["consecutive_failures"] = \
            self.config.get("execution", {}).get("consecutive_failures", 0) + 1

        # 检查连续失败次数
        max_failures = self.config.get("execution", {}).get("max_consecutive_failures", 3)
        consecutive_failures = self.config["execution"]["consecutive_failures"]

        if consecutive_failures >= max_failures:
            # 达到阈值，暂停任务
            self.config["state"]["status"] = "paused"
            set_task_status(self.task_id, "paused")
            append_log(self.task_id, "ACTION", f"连续超时 {consecutive_failures} 次，任务已暂停")

            notify_task_error(
                self.task_id,
                f"任务连续超时 {consecutive_failures} 次，已自动暂停"
            )

        save_task_config(self.task_id, self.config)

        return AnalysisResult(
            status="timeout",
            summary=f"任务执行超时 (连续失败 {consecutive_failures} 次)",
            issues=[{"type": "timeout", "message": "执行超时"}]
        )

    async def handle_execution_result(self, result: AnalysisResult) -> None:
        """
        处理执行结果

        Args:
            result: 分析结果
        """
        if not self.config:
            return

        analyzer = CronResultAnalyzer(self.config)

        if analyzer.should_notify(result):
            if result.status == "error":
                notify_task_error(self.task_id, result.summary)
            elif result.status == "warning":
                # 可疑情况，可以选择是否通知
                if self.config.get("notification", {}).get("enable_claude_analysis", True):
                    # 可以在这里添加 Claude 二次分析
                    notify_task_error(self.task_id, f"警告: {result.summary}")

        # 成功时是否通知
        if result.status == "success":
            if self.config.get("notification", {}).get("notify_on_success", False):
                notify_task_completed(self.task_id, result.summary)

    async def stop_cron(self) -> bool:
        """停止 Cron 任务"""
        set_task_status(self.task_id, "stopped")
        append_log(self.task_id, "ACTION", "Cron 任务已停止")
        return True

    async def pause_cron(self) -> bool:
        """暂停 Cron 任务"""
        set_task_status(self.task_id, "paused")
        append_log(self.task_id, "ACTION", "Cron 任务已暂停")
        return True

    async def resume_cron(self) -> bool:
        """恢复 Cron 任务"""
        set_task_status(self.task_id, "active")
        append_log(self.task_id, "ACTION", "Cron 任务已恢复")
        return True


async def cron_execute_callback(task_id: str) -> None:
    """
    Cron 执行回调函数

    由调度器调用
    """
    executor = CronExecutor(task_id)
    result = await executor.execute_cron()
    await executor.handle_execution_result(result)
