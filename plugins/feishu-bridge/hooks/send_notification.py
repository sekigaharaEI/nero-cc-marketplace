#!/usr/bin/env python3
"""
飞书通知钩子脚本
当 Claude Code 发送特定通知时，自动通过飞书发送提醒
"""

import os
import sys
import json
import subprocess
from pathlib import Path


def load_config():
    """加载飞书配置（从配置文件）"""
    config_dir = Path(os.getenv("FEISHU_BRIDGE_HOME", "~/.feishu-bridge")).expanduser()
    config_file = config_dir / "config.json"

    if config_file.exists():
        with open(config_file, encoding='utf-8') as f:
            data = json.load(f)
        data["recipient"] = data.get("recipient_open_id")
        data["source"] = str(config_file)
        return data

    return None


def send_feishu_notification(message: str, recipient: str):
    """发送飞书通知"""
    try:
        # 获取插件根目录
        plugin_root = os.getenv("CLAUDE_PLUGIN_ROOT")
        if not plugin_root:
            print("警告: CLAUDE_PLUGIN_ROOT 未设置，无法发送飞书通知", file=sys.stderr)
            return False

        cli_path = Path(plugin_root) / "scripts" / "feishu_cli.py"

        # 调用 CLI 工具发送消息
        result = subprocess.run(
            ["python3", str(cli_path), "send", "--to", recipient, "--message", message],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return True
        else:
            print(f"飞书通知发送失败: {result.stderr}", file=sys.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("飞书通知发送超时", file=sys.stderr)
        return False
    except Exception as e:
        print(f"飞书通知发送异常: {e}", file=sys.stderr)
        return False


def main():
    try:
        # 从 stdin 读取钩子输入
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"错误: 无效的 JSON 输入: {e}", file=sys.stderr)
        sys.exit(1)

    # 加载配置
    config = load_config()
    if not config:
        # 未配置飞书，静默退出
        sys.exit(0)

    # 检查是否配置了接收者
    recipient = config.get("recipient")
    if not recipient:
        # 未配置接收者，静默退出
        sys.exit(0)

    # 获取通知信息
    notification_type = input_data.get("notification_type", "unknown")
    message_text = input_data.get("message", "")

    # 根据通知类型生成飞书消息
    feishu_messages = {
        "permission_prompt": "🔔 Claude Code 正在等待您的权限确认\n\n请查看 Claude Code 界面并做出选择。",
        "idle_prompt": "⏰ Claude Code 正在等待您的回复\n\n已空闲超过 60 秒，请查看是否需要提供输入。",
        "elicitation_dialog": "❓ Claude Code 需要您的输入\n\n请查看 Claude Code 界面并提供所需信息。"
    }

    feishu_message = feishu_messages.get(
        notification_type,
        f"🔔 Claude Code 通知\n\n{message_text}"
    )

    # 发送飞书通知
    success = send_feishu_notification(feishu_message, recipient)

    # 无论成功与否都退出 0，不阻塞 Claude Code
    sys.exit(0)


if __name__ == "__main__":
    main()
