#!/usr/bin/env python3
"""
飞书消息发送 CLI 工具
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path


class FeishuClient:
    """飞书 API 客户端"""

    def __init__(self, app_id: str, app_secret: str, domain: str = "feishu"):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = f"https://open.{domain}.cn"
        self._token = None
        self._token_expire_at = None

    def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        # 检查缓存
        if self._token and self._token_expire_at:
            if datetime.now() < self._token_expire_at - timedelta(minutes=5):
                return self._token

        # 请求新 token
        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal/"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Failed to get token: {data.get('msg')}")

        self._token = data["tenant_access_token"]
        self._token_expire_at = datetime.now() + timedelta(seconds=data.get("expire", 7200))

        return self._token

    def send_text_message(self, receive_id_type: str, receive_id: str, content: str) -> dict:
        """发送文本消息"""
        token = self.get_tenant_access_token()

        url = f"{self.base_url}/open-apis/im/v1/messages"
        params = {"receive_id_type": receive_id_type}
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": content})
        }

        response = requests.post(url, params=params, headers=headers, json=payload, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Failed to send message: {data.get('msg')}")

        return {
            "message_id": data["data"]["message_id"],
            "create_time": data["data"]["create_time"]
        }


def load_config():
    """加载配置（从配置文件）"""
    config_dir = Path(os.getenv("FEISHU_BRIDGE_HOME", "~/.feishu-bridge")).expanduser()
    config_file = config_dir / "config.json"

    if config_file.exists():
        with open(config_file, encoding='utf-8') as f:
            data = json.load(f)
        data["source"] = str(config_file)
        return data

    return None


def cmd_send(args):
    """发送消息命令"""

    # 加载配置
    config = load_config()
    if not config:
        print("错误: 未找到配置", file=sys.stderr)
        print("请先运行 '/feishu-setup' 完成配置", file=sys.stderr)
        sys.exit(1)

    # 创建客户端并发送
    client = FeishuClient(
        app_id=config["app_id"],
        app_secret=config["app_secret"],
        domain=config["domain"]
    )

    try:
        result = client.send_text_message("open_id", args.to, args.message)

        print(f"✅ 消息发送成功")
        print(f"   Message ID: {result['message_id']}")
    except Exception as e:
        print(f"❌ 发送失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_config_show(args):
    """显示配置"""
    config = load_config()
    if not config:
        print("未找到配置")
        print("请运行 '/feishu-setup' 完成配置")
        return

    print(f"App ID: {config['app_id']}")
    print(f"Domain: {config['domain']}")
    print(f"Config loaded from: {config['source']}")


def cmd_config_set(args):
    """设置配置"""
    config_dir = Path(os.getenv("FEISHU_BRIDGE_HOME", "~/.feishu-bridge")).expanduser()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"

    config = {
        "app_id": args.app_id,
        "app_secret": args.app_secret,
        "domain": args.domain
    }

    # 添加可选字段
    if hasattr(args, 'recipient_open_id') and args.recipient_open_id:
        config["recipient_open_id"] = args.recipient_open_id

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # 设置文件权限为 600
    config_file.chmod(0o600)

    print(f"✅ 配置已保存到 {config_file}")


def main():
    parser = argparse.ArgumentParser(description="飞书消息发送工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # send 命令
    send_parser = subparsers.add_parser("send", help="发送消息")
    send_parser.add_argument("--to", required=True, help="用户 Open ID")
    send_parser.add_argument("--message", "-m", required=True, help="消息内容")

    # config 命令
    config_parser = subparsers.add_parser("config", help="配置管理")
    config_subparsers = config_parser.add_subparsers(dest="config_command")

    # config show
    config_subparsers.add_parser("show", help="显示配置")

    # config set
    set_parser = config_subparsers.add_parser("set", help="设置配置")
    set_parser.add_argument("--app-id", required=True, help="App ID")
    set_parser.add_argument("--app-secret", required=True, help="App Secret")
    set_parser.add_argument("--domain", default="feishu", help="域名(feishu/lark)")
    set_parser.add_argument("--recipient-open-id", help="接收者 Open ID（可选，用于钩子）")

    args = parser.parse_args()

    if args.command == "send":
        cmd_send(args)
    elif args.command == "config":
        if args.config_command == "show":
            cmd_config_show(args)
        elif args.config_command == "set":
            cmd_config_set(args)
        else:
            config_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
