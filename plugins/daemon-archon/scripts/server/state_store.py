"""
daemon-archon 状态存储模块

负责任务配置的持久化存储和读取
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from .types import (
    TaskConfig, ProbeTaskConfig, CronTaskConfig,
    TaskMode, TaskStatus, GlobalSettings
)

logger = logging.getLogger(__name__)


def get_base_dir() -> Path:
    """获取 daemon-archon 工作目录"""
    return Path.home() / ".claude" / "daemon-archon"


def ensure_base_dir() -> Path:
    """确保工作目录存在"""
    base_dir = get_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_task_dir(task_id: str) -> Path:
    """获取任务目录"""
    return get_base_dir() / task_id


def ensure_task_dir(task_id: str) -> Path:
    """确保任务目录存在"""
    task_dir = get_task_dir(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


# ============ 全局配置 ============

def load_global_settings() -> Dict[str, Any]:
    """加载全局配置"""
    settings_file = get_base_dir() / "setting.json"

    if not settings_file.exists():
        # 返回默认配置
        return {
            "version": "1.0",
            "notification": {
                "enabled": True,
                "method": "system",
                "webhook_url": None,
                "slack_webhook": None
            },
            "defaults": {
                "probe_check_interval_minutes": 5,
                "cron_check_interval_minutes": 60,
                "max_auto_corrections": 3
            },
            "claude_cli": {
                "path": "claude",
                "default_model": None
            },
            "logging": {
                "level": "INFO",
                "max_log_size_mb": 10,
                "max_log_files": 5
            }
        }

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载全局配置失败: {e}")
        return {}


def save_global_settings(settings: Dict[str, Any]) -> bool:
    """保存全局配置"""
    ensure_base_dir()
    settings_file = get_base_dir() / "setting.json"

    try:
        # 原子写入
        temp_file = settings_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        temp_file.rename(settings_file)
        return True
    except Exception as e:
        logger.error(f"保存全局配置失败: {e}")
        return False


# ============ 任务配置 ============

def load_task_config(task_id: str) -> Optional[Dict[str, Any]]:
    """加载任务配置"""
    config_file = get_task_dir(task_id) / "config.json"

    if not config_file.exists():
        return None

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载任务配置失败 [{task_id}]: {e}")
        return None


def save_task_config(task_id: str, config: Dict[str, Any]) -> bool:
    """保存任务配置"""
    task_dir = ensure_task_dir(task_id)
    config_file = task_dir / "config.json"

    try:
        # 原子写入
        temp_file = config_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        temp_file.rename(config_file)
        return True
    except Exception as e:
        logger.error(f"保存任务配置失败 [{task_id}]: {e}")
        return False


def delete_task_config(task_id: str) -> bool:
    """删除任务配置"""
    import shutil
    task_dir = get_task_dir(task_id)

    if not task_dir.exists():
        return True

    try:
        shutil.rmtree(task_dir)
        return True
    except Exception as e:
        logger.error(f"删除任务配置失败 [{task_id}]: {e}")
        return False


# ============ 任务状态 ============

def get_task_status(task_id: str) -> Optional[str]:
    """获取任务状态"""
    status_file = get_task_dir(task_id) / "status"

    if not status_file.exists():
        return None

    try:
        return status_file.read_text().strip()
    except Exception as e:
        logger.error(f"读取任务状态失败 [{task_id}]: {e}")
        return None


def set_task_status(task_id: str, status: str) -> bool:
    """
    设置任务状态

    同时更新 status 文件和 config.json 中的 state.status 字段
    """
    task_dir = ensure_task_dir(task_id)
    status_file = task_dir / "status"

    try:
        # 更新 status 文件
        status_file.write_text(status)

        # 同步更新 config.json
        config = load_task_config(task_id)
        if config:
            config.setdefault("state", {})["status"] = status
            save_task_config(task_id, config)

        return True
    except Exception as e:
        logger.error(f"设置任务状态失败 [{task_id}]: {e}")
        return False


# ============ 任务锁 ============

def acquire_task_lock(task_id: str, timeout_minutes: int = 30) -> bool:
    """
    获取任务锁

    Args:
        task_id: 任务 ID
        timeout_minutes: 锁超时时间（分钟），超过此时间视为僵尸锁

    Returns:
        是否成功获取锁
    """
    task_dir = ensure_task_dir(task_id)
    lock_file = task_dir / "task.lock"

    # 检查是否存在锁
    if lock_file.exists():
        try:
            content = lock_file.read_text().strip()
            pid, timestamp = content.split(':')
            lock_time = datetime.fromisoformat(timestamp)

            # 检查是否超时
            elapsed = (datetime.now() - lock_time).total_seconds() / 60
            if elapsed < timeout_minutes:
                # 锁未超时，检查进程是否存活
                try:
                    os.kill(int(pid), 0)
                    # 进程存活，锁有效
                    return False
                except OSError:
                    # 进程已死，可以覆盖锁
                    pass
        except Exception:
            # 锁文件格式错误，覆盖
            pass

    # 创建锁
    try:
        pid = os.getpid()
        timestamp = datetime.now().isoformat()
        lock_file.write_text(f"{pid}:{timestamp}")
        return True
    except Exception as e:
        logger.error(f"创建任务锁失败 [{task_id}]: {e}")
        return False


def release_task_lock(task_id: str) -> bool:
    """释放任务锁"""
    lock_file = get_task_dir(task_id) / "task.lock"

    if not lock_file.exists():
        return True

    try:
        lock_file.unlink()
        return True
    except Exception as e:
        logger.error(f"释放任务锁失败 [{task_id}]: {e}")
        return False


def is_task_locked(task_id: str) -> bool:
    """检查任务是否被锁定"""
    lock_file = get_task_dir(task_id) / "task.lock"
    return lock_file.exists()


# ============ 任务列表 ============

def list_all_tasks() -> List[Dict[str, Any]]:
    """列出所有任务"""
    base_dir = get_base_dir()

    if not base_dir.exists():
        return []

    tasks = []
    for task_dir in base_dir.iterdir():
        if not task_dir.is_dir():
            continue
        if task_dir.name.startswith('.'):
            continue
        if task_dir.name == "setting.json":
            continue

        config = load_task_config(task_dir.name)
        if config:
            tasks.append(config)

    # 按创建时间排序
    tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return tasks


def list_tasks_by_mode(mode: str) -> List[Dict[str, Any]]:
    """按模式列出任务"""
    all_tasks = list_all_tasks()
    return [t for t in all_tasks if t.get("mode") == mode]


def list_active_tasks() -> List[Dict[str, Any]]:
    """列出所有活跃任务"""
    all_tasks = list_all_tasks()
    return [t for t in all_tasks if t.get("state", {}).get("status") == "active"]


# ============ 日志 ============

def append_log(task_id: str, level: str, message: str) -> bool:
    """追加日志"""
    task_dir = ensure_task_dir(task_id)
    log_file = task_dir / "archon.log"

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level.upper()}] {message}\n"

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_line)
        return True
    except Exception as e:
        logger.error(f"写入日志失败 [{task_id}]: {e}")
        return False


def read_log(task_id: str, lines: int = 100) -> List[str]:
    """读取日志"""
    log_file = get_task_dir(task_id) / "archon.log"

    if not log_file.exists():
        return []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        return all_lines[-lines:]
    except Exception as e:
        logger.error(f"读取日志失败 [{task_id}]: {e}")
        return []


# ============ 纠偏历史 ============

def load_corrections(task_id: str) -> str:
    """加载纠偏历史"""
    corrections_file = get_task_dir(task_id) / "corrections.md"

    if not corrections_file.exists():
        return ""

    try:
        return corrections_file.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"读取纠偏历史失败 [{task_id}]: {e}")
        return ""


def save_corrections(task_id: str, content: str) -> bool:
    """保存纠偏历史"""
    task_dir = ensure_task_dir(task_id)
    corrections_file = task_dir / "corrections.md"

    try:
        corrections_file.write_text(content, encoding='utf-8')
        return True
    except Exception as e:
        logger.error(f"保存纠偏历史失败 [{task_id}]: {e}")
        return False


def append_correction(task_id: str, record: Dict[str, Any]) -> bool:
    """追加纠偏记录"""
    existing = load_corrections(task_id)

    # 如果是空的，创建初始结构
    if not existing:
        existing = """# 纠偏历史

## 摘要

| # | 时间 | 纠偏者 | 原因 | 结果 |
|---|------|--------|------|------|

---

## 详细记录

"""

    # 解析现有记录数量
    import re
    matches = re.findall(r'\| (\d+) \|', existing)
    index = max([int(m) for m in matches], default=0) + 1

    # 添加摘要行
    timestamp = record.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M"))
    corrector = record.get("corrector", "Archon")
    reason = record.get("reason", "")[:20]
    result = record.get("result", "")

    summary_line = f"| {index} | {timestamp} | {corrector} | {reason} | {result} |\n"

    # 在摘要表格末尾添加
    parts = existing.split("---\n\n## 详细记录")
    if len(parts) == 2:
        # 在表格末尾添加新行
        table_end = parts[0].rstrip()
        parts[0] = table_end + "\n" + summary_line + "\n"
        existing = parts[0] + "---\n\n## 详细记录" + parts[1]

    # 添加详细记录
    detail = f"""
### #{index} - {timestamp}

**纠偏者**：{corrector}

**触发原因**：
{record.get('reason', '')}

**分析结论**：
{record.get('analysis', '')}

**纠偏指令**：
```
{record.get('instruction', '')}
```

**执行结果**：{result}
**后续状态**：{record.get('follow_up_status', '')}

---
"""
    existing += detail

    return save_corrections(task_id, existing)


# ============ Destination (Probe 模式) ============

def load_destination(task_id: str) -> str:
    """加载任务目标"""
    destination_file = get_task_dir(task_id) / "destination.md"

    if not destination_file.exists():
        return ""

    try:
        return destination_file.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"读取任务目标失败 [{task_id}]: {e}")
        return ""


def save_destination(task_id: str, content: str) -> bool:
    """保存任务目标"""
    task_dir = ensure_task_dir(task_id)
    destination_file = task_dir / "destination.md"

    try:
        destination_file.write_text(content, encoding='utf-8')
        return True
    except Exception as e:
        logger.error(f"保存任务目标失败 [{task_id}]: {e}")
        return False


# ============ Workflow (Cron 模式) ============

def ensure_workflow_dir(task_id: str) -> Path:
    """确保 workflow 目录存在"""
    workflow_dir = get_task_dir(task_id) / "workflow"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    return workflow_dir


def load_workflow(task_id: str) -> str:
    """加载 workflow"""
    workflow_file = get_task_dir(task_id) / "workflow" / "workflow.md"

    if not workflow_file.exists():
        return ""

    try:
        return workflow_file.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"读取 workflow 失败 [{task_id}]: {e}")
        return ""


def save_workflow(task_id: str, content: str) -> bool:
    """保存 workflow"""
    workflow_dir = ensure_workflow_dir(task_id)
    workflow_file = workflow_dir / "workflow.md"

    try:
        workflow_file.write_text(content, encoding='utf-8')
        return True
    except Exception as e:
        logger.error(f"保存 workflow 失败 [{task_id}]: {e}")
        return False


def load_task_md(task_id: str) -> str:
    """加载任务描述"""
    task_md_file = get_task_dir(task_id) / "task.md"

    if not task_md_file.exists():
        return ""

    try:
        return task_md_file.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"读取任务描述失败 [{task_id}]: {e}")
        return ""


def save_task_md(task_id: str, content: str) -> bool:
    """保存任务描述"""
    task_dir = ensure_task_dir(task_id)
    task_md_file = task_dir / "task.md"

    try:
        task_md_file.write_text(content, encoding='utf-8')
        return True
    except Exception as e:
        logger.error(f"保存任务描述失败 [{task_id}]: {e}")
        return False
