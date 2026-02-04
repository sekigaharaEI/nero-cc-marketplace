"""
daemon-archon 卡住检测器

借鉴 OpenClaw 的卡住检测机制，自动检测并处理长时间未完成的任务
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from .types import StuckInfo, TaskMode
from .state_store import (
    get_base_dir, load_task_config, save_task_config,
    get_task_status, set_task_status, append_log
)
from .notifier import notify_task_stuck

logger = logging.getLogger(__name__)

# 卡住阈值配置（分钟）
STUCK_THRESHOLDS = {
    "probe_no_output": 60,      # Probe 1小时无输出
    "archon_check_timeout": 5,  # Archon 检查超过5分钟
    "cron_execution": 30,       # Cron 任务默认30分钟
}


class StuckDetector:
    """卡住检测器"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or get_base_dir()

    def scan_all_tasks(self) -> List[StuckInfo]:
        """
        扫描所有任务，检测卡住状态

        Returns:
            卡住任务列表
        """
        stuck_tasks = []

        if not self.base_dir.exists():
            return stuck_tasks

        for task_dir in self.base_dir.iterdir():
            if not task_dir.is_dir():
                continue
            if task_dir.name.startswith('.'):
                continue

            task_id = task_dir.name
            task_mode = self._get_task_mode(task_id)

            if task_mode == "unknown":
                continue

            # 检测是否卡住
            stuck_info = self._detect_stuck(task_id, task_dir, task_mode)
            if stuck_info:
                stuck_tasks.append(stuck_info)

        return stuck_tasks

    def _get_task_mode(self, task_id: str) -> str:
        """从任务ID推断任务模式"""
        if task_id.endswith("_probe"):
            return "probe"
        elif task_id.endswith("_cron"):
            return "cron"

        # 尝试从配置文件读取
        config = load_task_config(task_id)
        if config:
            return config.get("mode", "unknown")

        return "unknown"

    def _detect_stuck(
        self,
        task_id: str,
        task_dir: Path,
        mode: str
    ) -> Optional[StuckInfo]:
        """
        检测单个任务是否卡住

        检测逻辑：
        1. Probe 模式：检查 transcript 文件最后修改时间
        2. Cron 模式：检查上次执行是否超时
        3. 检查状态文件（archon 正在检查中）
        """
        # 检查任务状态
        status = get_task_status(task_id)
        if status != "active":
            return None

        # 检查是否在 Archon 检查中
        check_start_file = task_dir / ".check_start"
        if check_start_file.exists():
            try:
                start_time = float(check_start_file.read_text().strip())
                elapsed = (datetime.now() - datetime.fromtimestamp(start_time)).total_seconds() / 60

                if elapsed > STUCK_THRESHOLDS["archon_check_timeout"]:
                    return StuckInfo(
                        task_id=task_id,
                        task_mode=TaskMode(mode),
                        stuck_type="archon_check_timeout",
                        stuck_duration_minutes=round(elapsed, 1),
                        details=f"Archon 检查已进行 {elapsed:.1f} 分钟，超过阈值 {STUCK_THRESHOLDS['archon_check_timeout']} 分钟"
                    )
            except Exception as e:
                logger.warning(f"读取检查开始时间失败: {e}")

        # Probe 模式：检查 transcript 输出
        if mode == "probe":
            return self._detect_probe_stuck(task_id, task_dir)

        # Cron 模式：检查执行超时
        if mode == "cron":
            return self._detect_cron_stuck(task_id, task_dir)

        return None

    def _detect_probe_stuck(
        self,
        task_id: str,
        task_dir: Path
    ) -> Optional[StuckInfo]:
        """检测 Probe 是否卡住"""
        config = load_task_config(task_id)
        if not config:
            return None

        # 获取 transcript 路径
        transcript_path = config.get("probe", {}).get("transcript_path")

        if not transcript_path:
            # 尝试从 session_id 推断
            session_id = config.get("probe", {}).get("session_id")
            if session_id:
                # 常见的 transcript 路径模式
                possible_paths = [
                    Path.home() / ".claude" / "sessions" / session_id / "transcript.jsonl",
                    Path.home() / ".claude" / "projects" / "*" / f"{session_id}.jsonl"
                ]
                for pattern in possible_paths:
                    if pattern.exists():
                        transcript_path = str(pattern)
                        break

        if not transcript_path or not Path(transcript_path).exists():
            return None

        # 检查文件最后修改时间
        try:
            mtime = datetime.fromtimestamp(Path(transcript_path).stat().st_mtime)
            elapsed = (datetime.now() - mtime).total_seconds() / 60

            if elapsed > STUCK_THRESHOLDS["probe_no_output"]:
                # 检查进程是否存活
                pid = config.get("probe", {}).get("pid")
                is_alive = self._is_process_alive(pid) if pid else False

                return StuckInfo(
                    task_id=task_id,
                    task_mode=TaskMode.PROBE,
                    stuck_type="probe_no_output",
                    stuck_duration_minutes=round(elapsed, 1),
                    details=f"Probe 进程 {'存活' if is_alive else '已退出'}，但已 {elapsed:.1f} 分钟无输出"
                )
        except Exception as e:
            logger.warning(f"检查 transcript 修改时间失败: {e}")

        return None

    def _detect_cron_stuck(
        self,
        task_id: str,
        task_dir: Path
    ) -> Optional[StuckInfo]:
        """检测 Cron 任务是否卡住"""
        config = load_task_config(task_id)
        if not config:
            return None

        execution = config.get("execution", {})
        last_run = execution.get("last_run")
        last_result = execution.get("last_result")
        timeout = config.get("execution", {}).get("timeout_minutes", STUCK_THRESHOLDS["cron_execution"])

        # 检查是否正在执行中（有 last_run 但没有 last_result）
        if last_run and not last_result:
            try:
                start_time = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                elapsed = (datetime.now(start_time.tzinfo) - start_time).total_seconds() / 60

                if elapsed > timeout:
                    return StuckInfo(
                        task_id=task_id,
                        task_mode=TaskMode.CRON,
                        stuck_type="cron_execution_timeout",
                        stuck_duration_minutes=round(elapsed, 1),
                        details=f"Cron 任务执行已进行 {elapsed:.1f} 分钟，超过配置的超时时间 {timeout} 分钟"
                    )
            except Exception as e:
                logger.warning(f"解析执行时间失败: {e}")

        return None

    def _is_process_alive(self, pid: int) -> bool:
        """检查进程是否存活"""
        try:
            import psutil
            process = psutil.Process(pid)
            return process.is_running()
        except ImportError:
            # psutil 未安装，使用 os.kill
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
        except Exception:
            return False


async def handle_stuck_tasks(stuck_tasks: List[StuckInfo]) -> None:
    """
    处理卡住的任务

    Args:
        stuck_tasks: 卡住任务列表
    """
    for stuck in stuck_tasks:
        logger.warning(f"检测到卡住任务: {stuck.task_id} ({stuck.stuck_type})")
        append_log(stuck.task_id, "WARNING", f"任务卡住: {stuck.details}")

        # 发送通知
        notify_task_stuck(stuck.task_id, stuck.stuck_duration_minutes)

        # 根据卡住类型处理
        if stuck.stuck_type == "archon_check_timeout":
            # 清理检查状态文件
            check_file = get_base_dir() / stuck.task_id / ".check_start"
            if check_file.exists():
                check_file.unlink()

        elif stuck.stuck_type == "probe_no_output":
            # 更新任务状态
            config = load_task_config(stuck.task_id)
            if config:
                config.setdefault("state", {})["status"] = "stuck"
                save_task_config(stuck.task_id, config)

        elif stuck.stuck_type == "cron_execution_timeout":
            # 更新执行状态
            config = load_task_config(stuck.task_id)
            if config:
                config.setdefault("execution", {})["last_result"] = "timeout"
                config["execution"]["consecutive_failures"] = \
                    config.get("execution", {}).get("consecutive_failures", 0) + 1
                save_task_config(stuck.task_id, config)


def run_stuck_detection(base_dir: Optional[Path] = None) -> List[StuckInfo]:
    """
    运行卡住检测的入口函数

    建议调用方式：
    1. Archon 正常检查时调用（作为前置检查）
    2. 独立的定时任务调用（更频繁地检测）
    3. 用户手动触发 `/check-stuck` 命令

    Returns:
        卡住任务列表（空列表表示没有卡住的任务）
    """
    detector = StuckDetector(base_dir)
    stuck_tasks = detector.scan_all_tasks()

    # 记录检测结果到日志
    if stuck_tasks:
        log_file = (base_dir or get_base_dir()) / "stuck_detection.log"
        timestamp = datetime.now().isoformat()

        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[{timestamp}] 检测到 {len(stuck_tasks)} 个卡住任务:\n")
                for task in stuck_tasks:
                    f.write(f"  - {task.task_id} ({task.task_mode}): {task.stuck_type}\n")
        except Exception as e:
            logger.error(f"写入卡住检测日志失败: {e}")

    return stuck_tasks


def mark_check_start(task_id: str) -> None:
    """标记检查开始"""
    check_file = get_base_dir() / task_id / ".check_start"
    try:
        check_file.write_text(str(datetime.now().timestamp()))
    except Exception as e:
        logger.warning(f"标记检查开始失败: {e}")


def mark_check_end(task_id: str) -> None:
    """标记检查结束"""
    check_file = get_base_dir() / task_id / ".check_start"
    try:
        if check_file.exists():
            check_file.unlink()
    except Exception as e:
        logger.warning(f"标记检查结束失败: {e}")
