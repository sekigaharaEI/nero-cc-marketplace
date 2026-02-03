# daemon-archon 定时任务系统增强设计

> 借鉴 OpenClaw Cron 系统的优秀设计，优化 daemon-archon 的定时任务和监控机制

---

## 一、设计背景

OpenClaw 的 Cron 系统具有以下优秀设计：
- **精确的定时器管理**：基于 setTimeout 的精确调度，避免误差累积
- **完善的任务状态追踪**：运行次数、错误统计、执行时长等
- **卡住检测机制**：自动检测并处理长时间未完成的任务
- **灵活的执行模式**：主会话 vs 隔离会话

本设计将这些优秀实践适配到 daemon-archon 系统中。

---

## 二、核心增强设计

### 2.1 卡住检测机制 (Stuck Detection)

#### 2.1.1 问题定义

**卡住场景**：
1. **Probe 卡住**：Probe 进程存活但长时间无输出（如陷入循环、死锁）
2. **Archon 检查卡住**：Archon 检查任务时自身卡住（如 AI 分析超时）
3. **Cron 任务卡住**：Cron 模式的临时会话执行超时

#### 2.1.2 检测标准

| 任务类型 | 卡住标准 | 检测方式 |
|---------|---------|---------|
| Probe | 1小时无 transcript 更新 | 对比 `transcript.jsonl` 修改时间 |
| Archon 检查 | 检查超过 5 分钟未完成 | 记录检查开始时间，超时报警 |
| Cron 任务 | 执行超过配置的超时时间 | 配置 `timeout_minutes` |

#### 2.1.3 实现设计

**新增文件**：`task_stuck_detector.py`

```python
"""
卡住检测器 - 独立运行，不依赖正常的 Archon 检查周期
"""
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

# 卡住阈值配置（分钟）
STUCK_THRESHOLDS = {
    "probe_no_output": 60,      # Probe 1小时无输出
    "archon_check_timeout": 5,  # Archon 检查超过5分钟
    "cron_execution": 30,       # Cron 任务默认30分钟
}

class StuckDetector:
    """卡住检测器"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.detected_stuck: List[dict] = []

    def scan_all_tasks(self) -> List[dict]:
        """
        扫描所有任务，检测卡住状态

        Returns:
            卡住任务列表，每项包含：
            - task_id: 任务ID
            - task_mode: 任务模式 (probe/cron)
            - stuck_type: 卡住类型
            - stuck_duration_minutes: 卡住时长
            - details: 详细信息
        """
        stuck_tasks = []

        # 遍历所有任务目录
        for task_dir in self.base_dir.iterdir():
            if not task_dir.is_dir():
                continue
            if task_dir.name.startswith('.'):
                continue

            task_id = task_dir.name
            task_mode = self._get_task_mode(task_id)

            # 检测是否卡住
            stuck_info = self._detect_stuck(task_id, task_dir, task_mode)
            if stuck_info:
                stuck_tasks.append(stuck_info)

        return stuck_tasks

    def _detect_stuck(self, task_id: str, task_dir: Path, mode: str) -> Optional[dict]:
        """
        检测单个任务是否卡住

        检测逻辑：
        1. Probe 模式：检查 transcript 文件最后修改时间
        2. Cron 模式：检查上次执行是否超时
        3. 检查状态文件（archon 正在检查中）
        """
        # 检查是否在 Archon 检查中（检查开始时间 > 5分钟）
        check_start_file = task_dir / ".check_start"
        if check_start_file.exists():
            start_time = float(check_start_file.read_text().strip())
            elapsed = (datetime.now() - datetime.fromtimestamp(start_time)).total_seconds() / 60
            if elapsed > STUCK_THRESHOLDS["archon_check_timeout"]:
                return {
                    "task_id": task_id,
                    "task_mode": mode,
                    "stuck_type": "archon_check_timeout",
                    "stuck_duration_minutes": round(elapsed, 1),
                    "details": f"Archon 检查已进行 {elapsed:.1f} 分钟，超过阈值 {STUCK_THRESHOLDS['archon_check_timeout']} 分钟"
                }

        # Probe 模式：检查 transcript 输出
        if mode == "probe":
            transcript_file = self._get_transcript_path(task_id)
            if transcript_file and transcript_file.exists():
                mtime = datetime.fromtimestamp(transcript_file.stat().st_mtime)
                elapsed = (datetime.now() - mtime).total_seconds() / 60

                if elapsed > STUCK_THRESHOLDS["probe_no_output"]:
                    # 同时检查进程是否存活
                    pid = self._get_probe_pid(task_id)
                    is_alive = self._is_process_alive(pid) if pid else False

                    return {
                        "task_id": task_id,
                        "task_mode": mode,
                        "stuck_type": "probe_no_output",
                        "stuck_duration_minutes": round(elapsed, 1),
                        "details": f"Probe 进程 {'存活' if is_alive else '已退出'}，但已 {elapsed:.1f} 分钟无输出，超过阈值 {STUCK_THRESHOLDS['probe_no_output']} 分钟"
                    }

        # Cron 模式：检查执行超时（基于 config.json 中的记录）
        if mode == "cron":
            config_file = task_dir / "config.json"
            if config_file.exists():
                import json
                config = json.loads(config_file.read_text())
                execution = config.get("execution", {})

                last_run = execution.get("last_run")
                timeout = config.get("timeout_minutes", STUCK_THRESHOLDS["cron_execution"])

                # 检查是否正在执行中（有 last_run 但没有 last_result）
                if last_run and not execution.get("last_result"):
                    start_time = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                    elapsed = (datetime.now() - start_time).total_seconds() / 60

                    if elapsed > timeout:
                        return {
                            "task_id": task_id,
                            "task_mode": mode,
                            "stuck_type": "cron_execution_timeout",
                            "stuck_duration_minutes": round(elapsed, 1),
                            "details": f"Cron 任务执行已进行 {elapsed:.1f} 分钟，超过配置的超时时间 {timeout} 分钟"
                        }

        return None

    def _get_task_mode(self, task_id: str) -> str:
        """从任务ID推断任务模式"""
        if task_id.endswith("_probe"):
            return "probe"
        elif task_id.endswith("_cron"):
            return "cron"
        return "unknown"

    def _get_transcript_path(self, task_id: str) -> Optional[Path]:
        """获取任务的 transcript 文件路径"""
        # 从 config.json 中读取 session_id
        config_file = self.base_dir / task_id / "config.json"
        if config_file.exists():
            import json
            config = json.loads(config_file.read_text())
            session_id = config.get("probe", {}).get("session_id")
            if session_id:
                # transcript 路径: ~/.claude/sessions/{session_id}/transcript.jsonl
                return Path.home() / ".claude" / "sessions" / session_id / "transcript.jsonl"
        return None

    def _get_probe_pid(self, task_id: str) -> Optional[int]:
        """从 config.json 获取 Probe PID"""
        config_file = self.base_dir / task_id / "config.json"
        if config_file.exists():
            import json
            config = json.loads(config_file.read_text())
            return config.get("probe", {}).get("pid")
        return None

    def _is_process_alive(self, pid: int) -> bool:
        """检查进程是否存活"""
        import psutil
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except psutil.NoSuchProcess:
            return False


def run_stuck_detection(base_dir: Optional[Path] = None) -> List[dict]:
    """
    运行卡住检测的入口函数

    建议调用方式：
    1. Archon 正常检查时调用（作为前置检查）
    2. 独立的定时任务调用（更频繁地检测）
    3. 用户手动触发 `/check-stuck` 命令

    Returns:
        卡住任务列表（空列表表示没有卡住的任务）
    """
    if base_dir is None:
        base_dir = Path.home() / ".claude" / "daemon-archon"

    detector = StuckDetector(base_dir)
    stuck_tasks = detector.scan_all_tasks()

    # 记录检测结果到日志
    if stuck_tasks:
        log_file = base_dir / "stuck_detection.log"
        timestamp = datetime.now().isoformat()
        with open(log_file, 'a') as f:
            f.write(f"\n[{timestamp}] 检测到 {len(stuck_tasks)} 个卡住任务:\n")
            for task in stuck_tasks:
                f.write(f"  - {task['task_id']} ({task['task_mode']}): {task['stuck_type']}\n")

    return stuck_tasks


if __name__ == "__main__":
    # 测试代码
    stuck = run_stuck_detection()
    if stuck:
        print(f"发现 {len(stuck)} 个卡住的任务:")
        for task in stuck:
            print(f"\n  任务ID: {task['task_id']}")
            print(f"  模式: {task['task_mode']}")
            print(f"  卡住类型: {task['stuck_type']}")
            print(f"  卡住时长: {task['stuck_duration_minutes']} 分钟")
            print(f"  详情: {task['details']}")
    else:
        print("没有发现卡住的任务")
