"""
daemon-archon 结果分析器

分析 Probe 和 Cron 任务的执行结果
"""

import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

from .types import ProbeStatus, AnalysisResult
from .state_store import load_task_config, load_global_settings

logger = logging.getLogger(__name__)


class TranscriptAnalyzer:
    """Transcript 分析器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化分析器

        Args:
            config: 任务配置
        """
        self.config = config
        self.criteria = config.get("criteria", {})
        self.success_indicators = self.criteria.get("success_indicators", [])
        self.failure_indicators = self.criteria.get("failure_indicators", [])
        self.completion_keywords = self.criteria.get("completion_keywords", [])

    def analyze_messages(self, messages: List[Dict[str, Any]]) -> AnalysisResult:
        """
        分析 transcript 消息

        Args:
            messages: transcript 消息列表

        Returns:
            分析结果
        """
        if not messages:
            return AnalysisResult(
                status="unknown",
                summary="无法获取 Probe 状态",
                issues=[{"type": "no_data", "message": "transcript 为空"}],
                progress=0
            )

        # 获取最后一条消息
        last_message = messages[-1]
        last_activity = last_message.get("timestamp")

        # 计算空闲时间
        idle_minutes = 0
        if last_activity:
            try:
                last_time = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                idle_minutes = (datetime.now(last_time.tzinfo) - last_time).total_seconds() / 60
            except Exception:
                pass

        # 分析消息内容
        issues = []
        findings = []
        status = "running"

        # 检查最近的消息
        for msg in reversed(messages[-10:]):
            role = msg.get("role")
            content = str(msg.get("content", ""))

            # 检查工具调用失败
            if role == "tool_result" and msg.get("is_error"):
                issues.append({
                    "type": "tool_error",
                    "message": content[:200],
                    "timestamp": msg.get("timestamp")
                })

            # 检查失败指标
            for indicator in self.failure_indicators:
                if indicator.lower() in content.lower():
                    issues.append({
                        "type": "failure_indicator",
                        "indicator": indicator,
                        "message": content[:200]
                    })

            # 检查成功指标
            for indicator in self.success_indicators:
                if indicator.lower() in content.lower():
                    findings.append({
                        "type": "success_indicator",
                        "indicator": indicator,
                        "message": content[:100]
                    })

        # 判断状态
        if issues:
            status = "error"
        elif idle_minutes > 60:  # 超过 1 小时无活动
            status = "stuck"
        elif idle_minutes > 15:  # 超过 15 分钟无活动
            status = "idle"
        else:
            status = "running"

        # 检查是否完成
        for msg in reversed(messages[-5:]):
            content = str(msg.get("content", ""))
            for keyword in self.completion_keywords:
                if keyword in content:
                    status = "completed"
                    break

        # 估计进度
        progress = self._estimate_progress(messages, findings)

        return AnalysisResult(
            status=status,
            summary=f"状态: {status}, 最后活动: {idle_minutes:.1f} 分钟前",
            issues=issues,
            findings=findings,
            progress=progress,
            last_activity=last_activity
        )

    def _estimate_progress(
        self,
        messages: List[Dict[str, Any]],
        findings: List[Dict[str, Any]]
    ) -> int:
        """估计任务进度"""
        total_messages = len(messages)
        success_count = len(findings)

        # 基于成功指标的进度
        if success_count >= len(self.success_indicators):
            return 100

        # 基于消息数量的简单估计
        return min(90, int((total_messages / 50) * 100))


class CronResultAnalyzer:
    """Cron 结果分析器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化分析器

        Args:
            config: 任务配置
        """
        self.config = config
        self.notification_rules = config.get("notification", {})

    def analyze_output(self, output: str) -> AnalysisResult:
        """
        分析 Cron 任务输出

        Args:
            output: Claude CLI 输出

        Returns:
            分析结果
        """
        # 尝试解析 JSON 输出
        try:
            result = json.loads(output)
            return self._analyze_json_result(result)
        except json.JSONDecodeError:
            # 非 JSON 输出，进行文本分析
            return self._analyze_text_result(output)

    def _analyze_json_result(self, result: Dict[str, Any]) -> AnalysisResult:
        """分析 JSON 格式的结果"""
        status = result.get("status", "unknown")
        summary = result.get("summary", "")
        findings = result.get("findings", [])
        metrics = result.get("metrics", {})

        # 根据状态判断
        issues = []
        if status == "error":
            issues = [{"type": "status_error", "message": summary}]
        elif status == "warning":
            issues = [{"type": "status_warning", "message": summary}]

        return AnalysisResult(
            status=status,
            summary=summary,
            issues=issues,
            findings=findings,
            metrics=metrics
        )

    def _analyze_text_result(self, output: str) -> AnalysisResult:
        """分析文本格式的结果"""
        output_lower = output.lower()

        # 检查错误关键词
        error_keywords = ["error", "failed", "exception", "fatal", "错误", "失败"]
        warning_keywords = ["warning", "warn", "警告"]

        issues = []
        status = "success"

        for keyword in error_keywords:
            if keyword in output_lower:
                status = "error"
                issues.append({
                    "type": "keyword_error",
                    "keyword": keyword,
                    "message": output[:200]
                })
                break

        if status != "error":
            for keyword in warning_keywords:
                if keyword in output_lower:
                    status = "warning"
                    issues.append({
                        "type": "keyword_warning",
                        "keyword": keyword,
                        "message": output[:200]
                    })
                    break

        return AnalysisResult(
            status=status,
            summary=output[:100] if output else "无输出",
            issues=issues
        )

    def should_notify(self, result: AnalysisResult) -> bool:
        """判断是否需要发送通知"""
        notify_on_status = self.notification_rules.get("notify_on_status", ["error"])
        suspicious_status = self.notification_rules.get("suspicious_status", ["warning"])

        # 确定需要通知的状态
        if result.status in notify_on_status:
            return True

        # 可疑状态需要进一步分析
        if result.status in suspicious_status:
            # 如果启用了 Claude 分析，返回 True 让调用者决定
            if self.notification_rules.get("enable_claude_analysis", True):
                return True

        return False


def read_transcript_incremental(
    transcript_path: str,
    last_offset: int = 0
) -> Dict[str, Any]:
    """
    增量读取 transcript 文件

    Args:
        transcript_path: transcript 文件路径
        last_offset: 上次读取的文件偏移量（字节）

    Returns:
        {
            "messages": [新消息列表],
            "new_offset": 新的文件偏移量,
            "file_size": 当前文件大小
        }
    """
    path = Path(transcript_path)

    if not path.exists():
        return {
            "messages": [],
            "new_offset": 0,
            "file_size": 0
        }

    try:
        file_size = path.stat().st_size

        # 如果文件没有增长，返回空
        if file_size <= last_offset:
            return {
                "messages": [],
                "new_offset": last_offset,
                "file_size": file_size
            }

        # 读取新增内容
        messages = []
        with open(path, 'r', encoding='utf-8') as f:
            f.seek(last_offset)

            for line in f:
                line = line.strip()
                if line:
                    try:
                        message = json.loads(line)
                        messages.append(message)
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析消息失败: {e}")

            new_offset = f.tell()

        return {
            "messages": messages,
            "new_offset": new_offset,
            "file_size": file_size
        }

    except Exception as e:
        logger.error(f"读取 transcript 失败: {e}")
        return {
            "messages": [],
            "new_offset": last_offset,
            "file_size": 0
        }


def get_transcript_path(session_id: str) -> Optional[str]:
    """
    获取指定 session 的 transcript 文件路径

    Args:
        session_id: 会话 ID

    Returns:
        transcript 文件的完整路径，如果未找到返回 None
    """
    try:
        result = subprocess.run(
            ["claude", "--list-sessions", "--format=json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            logger.error(f"列出会话失败: {result.stderr}")
            return None

        sessions = json.loads(result.stdout)

        for session in sessions:
            if session.get("session_id") == session_id:
                return session.get("transcript_path")

        logger.warning(f"未找到 session_id={session_id} 的会话")
        return None

    except subprocess.TimeoutExpired:
        logger.error("列出会话超时")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"解析会话列表失败: {e}")
        return None
    except Exception as e:
        logger.error(f"获取 transcript 路径失败: {e}")
        return None


def analyze_probe_status(task_id: str) -> AnalysisResult:
    """
    分析 Probe 任务状态

    Args:
        task_id: 任务 ID

    Returns:
        分析结果
    """
    config = load_task_config(task_id)
    if not config:
        return AnalysisResult(
            status="error",
            summary="任务配置不存在",
            issues=[{"type": "config_error", "message": f"任务 {task_id} 配置不存在"}]
        )

    # 获取 transcript 路径
    session_id = config.get("probe", {}).get("session_id")
    transcript_path = config.get("probe", {}).get("transcript_path")

    if not transcript_path and session_id:
        transcript_path = get_transcript_path(session_id)

    if not transcript_path:
        return AnalysisResult(
            status="unknown",
            summary="无法获取 transcript 路径",
            issues=[{"type": "transcript_error", "message": "无法定位 transcript 文件"}]
        )

    # 读取 transcript
    last_offset = config.get("state", {}).get("last_transcript_offset", 0)
    transcript_data = read_transcript_incremental(transcript_path, last_offset)

    # 分析消息
    analyzer = TranscriptAnalyzer(config)
    return analyzer.analyze_messages(transcript_data["messages"])


def analyze_cron_result(task_id: str, output: str) -> AnalysisResult:
    """
    分析 Cron 任务结果

    Args:
        task_id: 任务 ID
        output: Claude CLI 输出

    Returns:
        分析结果
    """
    config = load_task_config(task_id)
    if not config:
        return AnalysisResult(
            status="error",
            summary="任务配置不存在",
            issues=[{"type": "config_error", "message": f"任务 {task_id} 配置不存在"}]
        )

    analyzer = CronResultAnalyzer(config)
    return analyzer.analyze_output(output)
