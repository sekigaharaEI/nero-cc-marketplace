"""
daemon-archon 类型定义

定义所有核心数据结构和类型
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class TaskMode(str, Enum):
    """任务模式"""
    PROBE = "probe"
    CRON = "cron"


class TaskStatus(str, Enum):
    """任务状态"""
    ACTIVE = "active"
    STOPPED = "stopped"
    PAUSED = "paused"


class ProbeStatus(str, Enum):
    """Probe 执行状态"""
    RUNNING = "running"
    IDLE = "idle"
    STUCK = "stuck"
    ERROR = "error"
    COMPLETED = "completed"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class CronScheduleKind(str, Enum):
    """Cron 调度类型"""
    AT = "at"           # 一次性任务
    EVERY = "every"     # 周期性任务
    CRON = "cron"       # Cron 表达式


@dataclass
class CronSchedule:
    """Cron 调度配置"""
    kind: CronScheduleKind
    # at 模式: 执行时间戳 (毫秒)
    at_ms: Optional[int] = None
    # every 模式: 间隔时间 (毫秒)
    every_ms: Optional[int] = None
    # every 模式: 锚点时间 (毫秒)
    anchor_ms: Optional[int] = None
    # cron 模式: cron 表达式
    expr: Optional[str] = None
    # cron 模式: 时区
    tz: Optional[str] = None


@dataclass
class ProbeConfig:
    """Probe 配置"""
    session_id: str
    pid: Optional[int] = None
    initial_prompt: str = ""
    log_dir: Optional[str] = None
    stdout_log: Optional[str] = None
    stderr_log: Optional[str] = None
    transcript_path: Optional[str] = None


@dataclass
class ScheduleConfig:
    """调度配置"""
    check_interval_minutes: int = 5
    next_check: Optional[str] = None
    cron_expression: Optional[str] = None
    next_run: Optional[str] = None


@dataclass
class CorrectionConfig:
    """纠偏配置"""
    max_auto_corrections: int = 3
    current_count: int = 0
    escalate_after_failures: int = 2


@dataclass
class CriteriaConfig:
    """判断标准配置"""
    success_indicators: List[str] = field(default_factory=lambda: ["任务完成", "测试通过"])
    failure_indicators: List[str] = field(default_factory=lambda: ["错误", "失败", "Error"])
    completion_keywords: List[str] = field(default_factory=lambda: ["任务完成"])


@dataclass
class ExecutionConfig:
    """执行配置 (Cron 模式)"""
    timeout_minutes: int = 10
    last_run: Optional[str] = None
    last_result: Optional[str] = None
    run_count: int = 0
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3


@dataclass
class NotificationRules:
    """通知规则"""
    notify_on_error: bool = True
    notify_on_success: bool = False
    notify_on_status: List[str] = field(default_factory=lambda: ["error"])
    suspicious_status: List[str] = field(default_factory=lambda: ["warning"])
    metric_thresholds: Dict[str, Dict[str, int]] = field(default_factory=dict)
    enable_claude_analysis: bool = True
    quiet_hours: Optional[str] = None


@dataclass
class TaskState:
    """任务状态"""
    status: TaskStatus = TaskStatus.ACTIVE
    last_check: Optional[str] = None
    last_correction: Optional[str] = None


@dataclass
class CronJobState:
    """Cron 任务运行时状态 (借鉴 OpenClaw)"""
    next_run_at_ms: Optional[int] = None
    last_run_at_ms: Optional[int] = None
    last_run_duration_ms: Optional[int] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class TaskConfig:
    """任务配置基类"""
    task_id: str
    mode: TaskMode
    name: str
    description: str = ""
    project_path: str = ""
    created_at: str = ""

    # 调度配置
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)

    # 状态
    state: TaskState = field(default_factory=TaskState)

    # 通知规则
    notification: NotificationRules = field(default_factory=NotificationRules)


@dataclass
class ProbeTaskConfig(TaskConfig):
    """Probe 模式任务配置"""
    probe: ProbeConfig = field(default_factory=lambda: ProbeConfig(session_id=""))
    correction: CorrectionConfig = field(default_factory=CorrectionConfig)
    criteria: CriteriaConfig = field(default_factory=CriteriaConfig)


@dataclass
class CronTaskConfig(TaskConfig):
    """Cron 模式任务配置"""
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    cron_state: CronJobState = field(default_factory=CronJobState)
    workflow_path: Optional[str] = None
    task_md_path: Optional[str] = None


@dataclass
class StuckInfo:
    """卡住信息"""
    task_id: str
    task_mode: TaskMode
    stuck_type: str
    stuck_duration_minutes: float
    details: str


@dataclass
class AnalysisResult:
    """分析结果"""
    status: str
    summary: str
    issues: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    progress: int = 0
    last_activity: Optional[str] = None


@dataclass
class CorrectionRecord:
    """纠偏记录"""
    index: int
    timestamp: str
    corrector: str  # "Archon" 或 "用户"
    reason: str
    analysis: str
    instruction: str
    result: str  # "成功" 或 "失败"
    follow_up_status: str


# 全局配置
@dataclass
class GlobalSettings:
    """全局配置"""
    version: str = "1.0"

    @dataclass
    class NotificationSettings:
        enabled: bool = True
        method: str = "system"  # system / slack / email / webhook
        webhook_url: Optional[str] = None
        slack_webhook: Optional[str] = None

    @dataclass
    class DefaultSettings:
        probe_check_interval_minutes: int = 5
        cron_check_interval_minutes: int = 60
        max_auto_corrections: int = 3

    @dataclass
    class ClaudeCliSettings:
        path: str = "claude"
        default_model: Optional[str] = None

    @dataclass
    class LoggingSettings:
        level: str = "INFO"
        max_log_size_mb: int = 10
        max_log_files: int = 5

    notification: NotificationSettings = field(default_factory=NotificationSettings)
    defaults: DefaultSettings = field(default_factory=DefaultSettings)
    claude_cli: ClaudeCliSettings = field(default_factory=ClaudeCliSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
