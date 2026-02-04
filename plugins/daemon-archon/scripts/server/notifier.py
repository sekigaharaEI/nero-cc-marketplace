"""
daemon-archon 系统通知模块

支持多种通知方式：系统通知、Slack、Webhook 等
"""

import os
import json
import logging
import subprocess
import platform
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class Notifier:
    """通知器"""

    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        """
        初始化通知器

        Args:
            settings: 通知配置，格式：
                {
                    "enabled": True,
                    "method": "system",  # system / slack / webhook
                    "webhook_url": None,
                    "slack_webhook": None
                }
        """
        self.settings = settings or {}
        self.enabled = self.settings.get("enabled", True)
        self.method = self.settings.get("method", "system")

    def send(self, title: str, message: str, level: str = "info") -> bool:
        """
        发送通知

        Args:
            title: 通知标题
            message: 通知内容
            level: 通知级别 (info / warning / error)

        Returns:
            是否发送成功
        """
        if not self.enabled:
            logger.debug("通知已禁用")
            return True

        try:
            if self.method == "system":
                return self._send_system_notification(title, message, level)
            elif self.method == "slack":
                return self._send_slack_notification(title, message, level)
            elif self.method == "webhook":
                return self._send_webhook_notification(title, message, level)
            else:
                logger.warning(f"未知的通知方式: {self.method}")
                return False
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            return False

    def _send_system_notification(self, title: str, message: str, level: str) -> bool:
        """发送系统通知"""
        system = platform.system()

        try:
            if system == "Darwin":
                # macOS
                return self._send_macos_notification(title, message)
            elif system == "Linux":
                # Linux
                return self._send_linux_notification(title, message, level)
            elif system == "Windows":
                # Windows
                return self._send_windows_notification(title, message)
            else:
                logger.warning(f"不支持的操作系统: {system}")
                return False
        except Exception as e:
            logger.error(f"发送系统通知失败: {e}")
            return False

    def _send_macos_notification(self, title: str, message: str) -> bool:
        """macOS 系统通知"""
        script = f'''
        display notification "{message}" with title "{title}"
        '''
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=10
            )
            return True
        except Exception as e:
            logger.error(f"macOS 通知失败: {e}")
            return False

    def _send_linux_notification(self, title: str, message: str, level: str) -> bool:
        """Linux 系统通知 (使用 notify-send)"""
        # 映射级别到图标
        urgency_map = {
            "info": "low",
            "warning": "normal",
            "error": "critical"
        }
        urgency = urgency_map.get(level, "normal")

        try:
            # 尝试使用 notify-send
            result = subprocess.run(
                [
                    "notify-send",
                    "-u", urgency,
                    "-a", "daemon-archon",
                    title,
                    message
                ],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except FileNotFoundError:
            logger.warning("notify-send 未安装，尝试其他方式")
            # 尝试使用 zenity
            try:
                subprocess.run(
                    [
                        "zenity",
                        "--notification",
                        f"--text={title}: {message}"
                    ],
                    capture_output=True,
                    timeout=10
                )
                return True
            except FileNotFoundError:
                logger.error("无法发送 Linux 通知：notify-send 和 zenity 都未安装")
                return False
        except Exception as e:
            logger.error(f"Linux 通知失败: {e}")
            return False

    def _send_windows_notification(self, title: str, message: str) -> bool:
        """Windows 系统通知"""
        try:
            # 使用 PowerShell 发送 Toast 通知
            script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

            $template = @"
            <toast>
                <visual>
                    <binding template="ToastText02">
                        <text id="1">{title}</text>
                        <text id="2">{message}</text>
                    </binding>
                </visual>
            </toast>
"@

            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("daemon-archon").Show($toast)
            '''

            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Windows 通知失败: {e}")
            # 备选方案：使用 msg 命令
            try:
                subprocess.run(
                    ["msg", "*", f"{title}\n{message}"],
                    capture_output=True,
                    timeout=10
                )
                return True
            except Exception:
                return False

    def _send_slack_notification(self, title: str, message: str, level: str) -> bool:
        """发送 Slack 通知"""
        webhook_url = self.settings.get("slack_webhook")

        if not webhook_url:
            logger.error("Slack webhook URL 未配置")
            return False

        # 映射级别到颜色
        color_map = {
            "info": "#36a64f",
            "warning": "#ff9800",
            "error": "#f44336"
        }
        color = color_map.get(level, "#36a64f")

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "footer": "daemon-archon",
                    "ts": int(__import__("time").time())
                }
            ]
        }

        return self._send_http_post(webhook_url, payload)

    def _send_webhook_notification(self, title: str, message: str, level: str) -> bool:
        """发送 Webhook 通知"""
        webhook_url = self.settings.get("webhook_url")

        if not webhook_url:
            logger.error("Webhook URL 未配置")
            return False

        payload = {
            "title": title,
            "message": message,
            "level": level,
            "source": "daemon-archon",
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }

        return self._send_http_post(webhook_url, payload)

    def _send_http_post(self, url: str, payload: Dict[str, Any]) -> bool:
        """发送 HTTP POST 请求"""
        try:
            import urllib.request
            import urllib.error

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200

        except urllib.error.URLError as e:
            logger.error(f"HTTP 请求失败: {e}")
            return False
        except Exception as e:
            logger.error(f"发送 HTTP POST 失败: {e}")
            return False


# 全局通知器实例
_notifier: Optional[Notifier] = None


def get_notifier() -> Notifier:
    """获取全局通知器实例"""
    global _notifier
    if _notifier is None:
        from .state_store import load_global_settings
        settings = load_global_settings()
        _notifier = Notifier(settings.get("notification", {}))
    return _notifier


def send_notification(title: str, message: str, level: str = "info") -> bool:
    """发送通知的便捷函数"""
    return get_notifier().send(title, message, level)


def notify_task_error(task_id: str, error_message: str) -> bool:
    """通知任务错误"""
    return send_notification(
        title=f"任务错误: {task_id}",
        message=error_message,
        level="error"
    )


def notify_task_stuck(task_id: str, stuck_duration: float) -> bool:
    """通知任务卡住"""
    return send_notification(
        title=f"任务卡住: {task_id}",
        message=f"任务已卡住 {stuck_duration:.1f} 分钟",
        level="warning"
    )


def notify_task_completed(task_id: str, summary: str = "") -> bool:
    """通知任务完成"""
    return send_notification(
        title=f"任务完成: {task_id}",
        message=summary or "任务已成功完成",
        level="info"
    )


def notify_correction_needed(task_id: str, reason: str) -> bool:
    """通知需要人工介入"""
    return send_notification(
        title=f"需要人工介入: {task_id}",
        message=reason,
        level="error"
    )


def notify_service_status(status: str, message: str = "") -> bool:
    """通知服务状态变化"""
    return send_notification(
        title=f"Archon 服务: {status}",
        message=message,
        level="info"
    )
