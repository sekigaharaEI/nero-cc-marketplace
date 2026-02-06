# 飞书消息发送 Skill - 技术设计

## 概述

本文档描述 `feishu-bridge` 插件的技术设计方案,该插件为 Claude Code 提供通过飞书开放平台发送消息的能力。

插件包含两个 skills:
1. **feishu-send-notification**: 教模型如何发送飞书通知
2. **feishu-setup**: 引导用户安装和配置(手动调用)

## 系统架构

```
┌─────────────────┐
│  Claude Code    │
│   (AI Agent)    │
└────────┬────────┘
         │
         │ 调用 CLI
         ▼
┌─────────────────┐
│ feishu-bridge   │
│   CLI Tool      │
└────────┬────────┘
         │
         │ HTTP API
         ▼
┌─────────────────┐
│  Feishu/Lark    │
│ Open Platform   │
└─────────────────┘
```

## 插件结构

```
nero-cc-marketplace/
└── plugins/
    └── feishu-bridge/
        ├── skills/
        │   ├── feishu-send-notification/
        │   │   └── SKILL.md           # 发送通知技能
        │   └── feishu-setup/
        │       └── SKILL.md           # 安装引导技能(disable-model-invocation: true)
        ├── scripts/
        │   └── feishu_cli.py          # CLI 工具实现
        ├── README.md                  # 插件说明
        └── requirements.txt           # Python 依赖
```

## Skill 1: feishu-send-notification

### SKILL.md 结构

```yaml
---
name: feishu-send-notification
description: 通过飞书开放平台发送通知消息。支持向个人(open_id)和群组(chat_id)发送文本消息。当需要发送飞书通知、提醒团队、同步状态时使用。
allowed-tools: Bash(python:*), Bash(feishu-bridge:*)
---

# 飞书消息通知

向飞书发送通知消息,支持个人对话和群组对话。

## 使用场景

- 任务完成通知
- 团队状态同步
- 个人消息提醒
- 工作流进度更新

## 发送消息命令

### 发送个人消息

向特定用户发送消息(使用用户的 Open ID):

```bash
python3 /path/to/feishu-bridge/scripts/feishu_cli.py send \
  --to <open_id> \
  --message "消息内容"
```

### 发送群组消息

向飞书群组发送消息(使用群组的 Chat ID):

```bash
python3 /path/to/feishu-bridge/scripts/feishu_cli.py send \
  --chat <chat_id> \
  --message "消息内容"
```

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--to` | 用户 Open ID | `ou_xxx` |
| `--chat` | 群组 Chat ID | `oc_xxx` |
| `--message` | 消息文本 | `"任务已完成"` |

## 错误处理

如果发送失败,检查:
1. 配置是否正确:`python3 feishu_cli.py config show`
2. 网络连接是否正常
3. 接收者 ID 是否正确
4. 应用权限是否配置(需要 `im:message` 权限)

如果提示"未配置",请先运行 `/feishu-setup` 完成配置。

## 示例

**通知团队任务完成:**
```bash
python3 feishu_cli.py send --chat oc_xxx --message "代码审查已完成,可以部署了"
```

**提醒个人会议时间:**
```bash
python3 feishu_cli.py send --to ou_xxx --message "会议时间改到下午3点"
```
```

### 关键设计点

1. **allowed-tools**: 只允许运行 Python 和 feishu-bridge CLI 命令
2. **简洁文档**: 聚焦使用方法,不包含安装步骤
3. **错误引导**: 如果未配置,引导用户运行 `/feishu-setup`

## Skill 2: feishu-setup

### SKILL.md 结构

```yaml
---
name: feishu-setup
description: 飞书消息发送服务的安装和配置引导。包含服务安装、应用创建、权限配置、环境变量设置等完整步骤。
disable-model-invocation: true
---

# 飞书消息发送 - 安装配置指南

本指南帮助你配置飞书消息发送服务,完成后即可使用 `feishu-send-notification` 发送飞书通知。

## 前置要求

- Python 3.8+
- 飞书企业账号(或 Lark 国际版账号)
- 网络连接

## 步骤 1: 创建飞书应用

### 1.1 访问飞书开放平台

- **中国版**: https://open.feishu.cn/
- **国际版(Lark)**: https://open.larksuite.com/

### 1.2 创建企业自建应用

1. 登录飞书开放平台
2. 点击"创建企业自建应用"
3. 填写应用名称和描述
4. 创建成功后,进入应用详情页

### 1.3 获取凭证

在应用详情页的"凭证与基础信息"中,复制:
- **App ID**: `cli_xxxxxxxxxx`
- **App Secret**: 点击"查看"按钮获取

### 1.4 配置权限

在"权限管理"中,添加以下权限:
- `im:message` - 获取与发送单聊、群组消息
- `im:message:send_as_bot` - 以应用的身份发消息

**重要**: 添加权限后,需要在应用版本管理中创建版本并发布到企业。

### 1.5 发布应用

1. 进入"版本管理与发布"
2. 创建新版本
3. 提交审核(企业自建应用通常自动通过)
4. 发布到企业

## 步骤 2: 安装 CLI 工具

### 2.1 安装 Python 依赖

```bash
cd /path/to/nero-cc-marketplace/plugins/feishu-bridge
pip install -r requirements.txt
```

### 2.2 配置环境变量

创建或编辑 `~/.bashrc` 或 `~/.zshrc`,添加:

```bash
# 飞书应用凭证
export FEISHU_APP_ID="cli_xxxxxxxxxx"
export FEISHU_APP_SECRET="你的 App Secret"
export FEISHU_DOMAIN="feishu"  # 或 "lark" (国际版)

# (可选) 配置目录
export FEISHU_BRIDGE_HOME="$HOME/.feishu-bridge"
```

重新加载配置:
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

### 2.3 验证配置

测试配置是否生效:

```bash
python3 /path/to/feishu-bridge/scripts/feishu_cli.py config show
```

预期输出:
```
App ID: cli_xxxxxxxxxx
Domain: feishu
Config loaded from: environment variables
```

## 步骤 3: 获取接收者 ID

### 3.1 获取用户 Open ID

方法 1: 通过飞书管理后台
1. 进入飞书管理后台
2. 找到用户信息
3. 复制 Open ID

方法 2: 接收一条测试消息后在飞书开放平台查看

### 3.2 获取群组 Chat ID

方法 1: 通过群组信息
1. 在飞书中打开群组
2. 点击群名称 → 更多 → 群组信息
3. 如果应用已加入群组,可以看到 Chat ID

方法 2: 使用飞书 API 列出群组

## 步骤 4: 测试发送

### 4.1 发送测试消息

向自己发送测试消息:

```bash
python3 feishu_cli.py send --to <你的 open_id> --message "测试消息"
```

### 4.2 发送到群组

确保应用已加入群组,然后:

```bash
python3 feishu_cli.py send --chat <群组 chat_id> --message "测试消息"
```

## 步骤 5: 使用 feishu-send-notification

配置完成后,你可以在 Claude Code 中使用飞书通知功能:

```
用户: "代码审查完成后,在飞书群里通知团队"
Claude: [审查完成] 发送通知到群组...
```

或者直接调用发送通知的功能。

## 故障排查

### 错误: "Failed to get token"

**原因**: App ID 或 App Secret 错误

**解决**:
1. 检查环境变量是否正确设置
2. 重新从飞书开放平台复制凭证
3. 确保没有多余的空格或引号

### 错误: "Permission denied"

**原因**: 应用缺少必要权限

**解决**:
1. 检查权限管理中是否添加了 `im:message` 权限
2. 确保应用已发布到企业
3. 重新发布应用版本

### 错误: "Invalid receive_id"

**原因**: 接收者 ID 格式错误或不存在

**解决**:
1. 确认 Open ID 格式为 `ou_xxx`
2. 确认 Chat ID 格式为 `oc_xxx`
3. 确保应用已加入目标群组(群组消息)

### 错误: "Network timeout"

**原因**: 网络连接问题或域名配置错误

**解决**:
1. 检查网络连接
2. 确认 FEISHU_DOMAIN 设置正确(中国版用 `feishu`,国际版用 `lark`)
3. 尝试访问 https://open.feishu.cn 确认可达

## 配置文件方式(可选)

如果不想使用环境变量,也可以使用配置文件:

```bash
python3 feishu_cli.py config set \
  --app-id "cli_xxx" \
  --app-secret "xxx" \
  --domain "feishu"
```

配置将保存到 `~/.feishu-bridge/config.json`

## 安全建议

1. **不要提交 App Secret 到代码仓库**
2. **使用环境变量或配置文件存储凭证**
3. **定期更新 App Secret**
4. **最小权限原则**: 只添加必要的权限

## 下一步

配置完成后,模型可以自动使用 `feishu-send-notification` 发送飞书通知了。

如需帮助,请参考:
- [飞书开放平台文档](https://open.feishu.cn/document/)
- [发送消息 API](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create)
```

### 关键设计点

1. **disable-model-invocation: true**: 只能用户手动调用 `/feishu-setup`
2. **完整引导**: 包含从创建应用到测试发送的完整步骤
3. **故障排查**: 提供常见错误的解决方案
4. **安全提醒**: 强调凭证安全

## CLI 工具实现

### feishu_cli.py 核心功能

```python
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
    """加载配置(优先环境变量,其次配置文件)"""
    # 优先从环境变量读取
    if os.getenv("FEISHU_APP_ID"):
        return {
            "app_id": os.getenv("FEISHU_APP_ID"),
            "app_secret": os.getenv("FEISHU_APP_SECRET"),
            "domain": os.getenv("FEISHU_DOMAIN", "feishu"),
            "source": "environment variables"
        }
    
    # 从配置文件读取
    config_dir = Path(os.getenv("FEISHU_BRIDGE_HOME", "~/.feishu-bridge")).expanduser()
    config_file = config_dir / "config.json"
    
    if config_file.exists():
        with open(config_file) as f:
            data = json.load(f)
        data["source"] = str(config_file)
        return data
    
    return None


def cmd_send(args):
    """发送消息命令"""
    # 验证参数
    if not args.to and not args.chat:
        print("错误: 必须指定 --to 或 --chat", file=sys.stderr)
        sys.exit(1)
    
    if args.to and args.chat:
        print("错误: --to 和 --chat 不能同时使用", file=sys.stderr)
        sys.exit(1)
    
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
        if args.to:
            result = client.send_text_message("open_id", args.to, args.message)
        else:
            result = client.send_text_message("chat_id", args.chat, args.message)
        
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
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    # 设置文件权限为 600
    config_file.chmod(0o600)
    
    print(f"✅ 配置已保存到 {config_file}")


def main():
    parser = argparse.ArgumentParser(description="飞书消息发送工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # send 命令
    send_parser = subparsers.add_parser("send", help="发送消息")
    send_parser.add_argument("--to", help="用户 Open ID")
    send_parser.add_argument("--chat", help="群组 Chat ID")
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
```

## 依赖项

### requirements.txt

```
requests>=2.28.0
```

## 安装和使用流程

### 用户首次使用

1. **手动调用安装引导**: `/feishu-setup`
2. **按照指南配置**: 创建应用、配置环境变量、测试发送
3. **模型自动使用**: 配置完成后,模型可以根据需要自动调用 `feishu-send-notification`

### 模型自动调用流程

```
用户: "部署完成后通知飞书群组"
  ↓
模型识别意图 → 激活 feishu-send-notification skill
  ↓
模型执行: python3 feishu_cli.py send --chat oc_xxx --message "部署完成"
  ↓
发送成功 → 向用户报告结果
```

## 错误处理

### CLI 工具错误码

| 退出码 | 含义 | 处理方式 |
|-------|------|---------|
| 0 | 成功 | 继续 |
| 1 | 配置错误/发送失败 | 检查配置和参数 |

### 常见错误处理

1. **未配置**: 引导用户运行 `/feishu-setup`
2. **权限不足**: 提示检查应用权限配置
3. **网络错误**: 自动重试(最多 3 次)
4. **Token 失效**: 自动刷新

## 安全性设计

1. **凭证存储**: 配置文件权限设置为 600
2. **环境变量优先**: 支持从环境变量读取,避免文件存储
3. **日志安全**: 不在日志中记录 App Secret
4. **最小权限**: 只申请必要的飞书权限

## 总结

这个设计通过两个 skills 实现清晰的职责分离:

- **feishu-send-notification**: 模型使用的工具,简洁明了
- **feishu-setup**: 用户配置的指南,详细完整

两者配合,既保证了模型能够自动发送通知,又确保用户能够轻松完成配置。


## 核心组件

### 1. CLI 工具 (feishu-bridge CLI)

#### 主要命令

```bash
# 配置管理
feishu-bridge config set --app-id <id> --app-secret <secret> [--domain feishu|lark]
feishu-bridge config show
feishu-bridge config test

# 消息发送
feishu-bridge send --to <open_id> --message <text> [--account default]
feishu-bridge send --chat <chat_id> --message <text> [--account default]

# 工具管理
feishu-bridge skill install  # 安装到 Claude Code
feishu-bridge skill update   # 更新 skill 文档
feishu-bridge --version
feishu-bridge --help
```

#### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--to` | 用户 Open ID | `ou_xxx` |
| `--chat` | 群聊 Chat ID | `oc_xxx` |
| `--message` | 消息文本内容 | `"任务已完成"` |
| `--account` | 账号名称(多账号) | `default` |
| `--domain` | 飞书域名 | `feishu` 或 `lark` |
| `--json` | JSON 格式输出 | - |

### 2. 配置管理 (Config Manager)

#### 配置文件位置
```
~/.feishu-bridge/
├── config.json          # 主配置文件
└── credentials/         # 凭证存储(可选)
    └── default.json
```

#### 配置文件格式 (config.json)

```json
{
  "accounts": {
    "default": {
      "app_id": "cli_xxx",
      "app_secret": "xxx",
      "domain": "feishu",
      "enabled": true
    },
    "lark_account": {
      "app_id": "cli_yyy",
      "app_secret": "yyy",
      "domain": "lark",
      "enabled": true
    }
  },
  "default_account": "default"
}
```

#### 环境变量支持

```bash
# 配置目录
export FEISHU_BRIDGE_HOME=/custom/path

# 直接配置凭证(优先级最高)
export FEISHU_APP_ID=cli_xxx
export FEISHU_APP_SECRET=xxx
export FEISHU_DOMAIN=feishu
```

### 3. 飞书 API 客户端 (Feishu Client)

#### 核心功能模块

```python
class FeishuClient:
    """飞书 API 客户端"""
    
    def __init__(self, app_id: str, app_secret: str, domain: str = "feishu"):
        """初始化客户端"""
        
    def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        
    def send_text_message(
        self,
        receive_id_type: str,  # "open_id" | "chat_id"
        receive_id: str,
        content: str
    ) -> dict:
        """发送文本消息"""
        
    def send_message(
        self,
        receive_id_type: str,
        receive_id: str,
        msg_type: str,
        content: dict
    ) -> dict:
        """通用消息发送接口"""
```

#### API 调用流程

```
1. 获取 tenant_access_token
   POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/
   Body: {
     "app_id": "cli_xxx",
     "app_secret": "xxx"
   }
   
2. 发送消息
   POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id
   Headers: {
     "Authorization": "Bearer <tenant_access_token>"
   }
   Body: {
     "receive_id": "ou_xxx",
     "msg_type": "text",
     "content": "{\"text\": \"消息内容\"}"
   }
```

#### Token 管理策略

- **缓存**: Token 有效期 2 小时,缓存到内存避免频繁请求
- **自动刷新**: Token 过期前 5 分钟自动刷新
- **错误重试**: Token 失效自动重新获取

### 4. SKILL.md 文档

参考 `notebooklm` skill 的格式,包含以下部分:

#### YAML Frontmatter

```yaml
---
name: feishu-bridge
description: 通过飞书开放平台发送消息。支持向个人和群组发送文本消息,用于工作流通知、状态同步等场景。
---
```

#### 文档结构

1. **简介** - Skill 功能概述
2. **安装** - 安装和配置步骤
3. **前置条件** - 飞书应用创建和权限配置
4. **激活条件** - 何时自动激活此 skill
5. **自主运行规则** - 哪些命令自动运行,哪些需要确认
6. **快速参考** - 常用命令表格
7. **命令详解** - 每个命令的详细说明
8. **常见工作流** - 使用场景示例
9. **错误处理** - 故障排查指南
10. **已知限制** - 功能限制说明

## 技术选型

### 编程语言
- **Python 3.8+**
  - 与 Claude Code 环境兼容
  - 丰富的 HTTP 客户端库
  - 易于打包和分发

### 核心依赖

```python
# requirements.txt
requests>=2.28.0        # HTTP 客户端
click>=8.0.0           # CLI 框架
pydantic>=2.0.0        # 配置验证
python-dotenv>=1.0.0   # 环境变量支持
```

### 项目结构

```
feishu-bridge/
├── feishu_bridge/
│   ├── __init__.py
│   ├── __main__.py          # CLI 入口
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── config.py        # config 命令
│   │   ├── send.py          # send 命令
│   │   └── skill.py         # skill 管理命令
│   ├── client/
│   │   ├── __init__.py
│   │   ├── feishu.py        # 飞书 API 客户端
│   │   └── auth.py          # Token 管理
│   ├── config/
│   │   ├── __init__.py
│   │   ├── manager.py       # 配置管理
│   │   └── schema.py        # 配置模型
│   └── utils/
│       ├── __init__.py
│       ├── logger.py        # 日志工具
│       └── errors.py        # 异常定义
├── scripts/
│   └── install_skill.py     # Skill 安装脚本
├── SKILL.md                 # Skill 文档
├── README.md
├── pyproject.toml
└── requirements.txt
```

## 详细设计

### 1. CLI 命令实现

#### send 命令实现

```python
import click
from feishu_bridge.client import FeishuClient
from feishu_bridge.config import ConfigManager

@click.command()
@click.option('--to', 'user_id', help='User Open ID')
@click.option('--chat', 'chat_id', help='Chat ID')
@click.option('--message', '-m', required=True, help='Message text')
@click.option('--account', default='default', help='Account name')
@click.option('--json', 'json_output', is_flag=True, help='JSON output')
def send(user_id, chat_id, message, account, json_output):
    """发送飞书消息"""
    
    # 验证参数
    if not user_id and not chat_id:
        raise click.UsageError("Must specify either --to or --chat")
    if user_id and chat_id:
        raise click.UsageError("Cannot specify both --to and --chat")
    
    # 加载配置
    config = ConfigManager().get_account(account)
    
    # 创建客户端
    client = FeishuClient(
        app_id=config.app_id,
        app_secret=config.app_secret,
        domain=config.domain
    )
    
    # 发送消息
    if user_id:
        result = client.send_text_message("open_id", user_id, message)
    else:
        result = client.send_text_message("chat_id", chat_id, message)
    
    # 输出结果
    if json_output:
        click.echo(json.dumps(result))
    else:
        click.echo(f"✅ Message sent successfully (message_id: {result['message_id']})")
```

### 2. 配置管理实现

#### ConfigManager 类

```python
from pathlib import Path
from pydantic import BaseModel
import json
import os

class AccountConfig(BaseModel):
    app_id: str
    app_secret: str
    domain: str = "feishu"
    enabled: bool = True

class Config(BaseModel):
    accounts: dict[str, AccountConfig]
    default_account: str = "default"

class ConfigManager:
    def __init__(self):
        self.config_dir = Path(os.getenv("FEISHU_BRIDGE_HOME", "~/.feishu-bridge")).expanduser()
        self.config_file = self.config_dir / "config.json"
        
    def load(self) -> Config:
        """加载配置"""
        if not self.config_file.exists():
            return Config(accounts={})
        
        with open(self.config_file) as f:
            data = json.load(f)
        return Config(**data)
    
    def save(self, config: Config):
        """保存配置"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config.dict(), f, indent=2)
    
    def get_account(self, name: str) -> AccountConfig:
        """获取账号配置"""
        # 优先从环境变量读取
        if name == "default" and os.getenv("FEISHU_APP_ID"):
            return AccountConfig(
                app_id=os.getenv("FEISHU_APP_ID"),
                app_secret=os.getenv("FEISHU_APP_SECRET"),
                domain=os.getenv("FEISHU_DOMAIN", "feishu")
            )
        
        config = self.load()
        if name not in config.accounts:
            raise ValueError(f"Account {name} not found")
        return config.accounts[name]
```

### 3. 飞书客户端实现

#### FeishuClient 类

```python
import requests
from datetime import datetime, timedelta
from typing import Optional

class FeishuClient:
    def __init__(self, app_id: str, app_secret: str, domain: str = "feishu"):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = f"https://open.{domain}.cn"
        
        self._token: Optional[str] = None
        self._token_expire_at: Optional[datetime] = None
    
    def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token (带缓存)"""
        
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
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Failed to get token: {data.get('msg')}")
        
        self._token = data["tenant_access_token"]
        # Token 有效期 2 小时
        self._token_expire_at = datetime.now() + timedelta(seconds=data.get("expire", 7200))
        
        return self._token
    
    def send_text_message(
        self,
        receive_id_type: str,
        receive_id: str,
        content: str
    ) -> dict:
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
        
        response = requests.post(url, params=params, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Failed to send message: {data.get('msg')}")
        
        return {
            "message_id": data["data"]["message_id"],
            "create_time": data["data"]["create_time"]
        }
```

## 错误处理设计

### 错误类型定义

```python
class FeishuBridgeError(Exception):
    """基础异常"""
    pass

class ConfigError(FeishuBridgeError):
    """配置错误"""
    pass

class AuthError(FeishuBridgeError):
    """认证错误"""
    pass

class APIError(FeishuBridgeError):
    """API 调用错误"""
    pass
```

### 错误处理策略

| 错误类型 | 处理方式 | 用户提示 |
|---------|---------|---------|
| 配置缺失 | 引导配置 | `未找到配置,请运行: feishu-bridge config set --app-id <id> --app-secret <secret>` |
| Token 获取失败 | 检查凭证 | `认证失败,请检查 App ID 和 App Secret 是否正确` |
| 消息发送失败 | 显示详细错误 | `发送失败: {错误原因}, 请检查接收者 ID 是否正确` |
| 网络超时 | 自动重试 3 次 | `网络超时,已重试 {n} 次` |
| 权限不足 | 引导配置权限 | `权限不足,请在飞书开放平台为应用添加"发送消息"权限` |

## Skill 自动激活设计

### 激活触发器

#### 显式触发
- 用户说 `/feishu`
- 用户说 "use feishu-bridge"
- 用户提到 "feishu-bridge"

#### 意图识别
识别以下模式的请求:
- "发送飞书消息给..."
- "通知飞书群组..."
- "在飞书里告诉某某..."
- "Send feishu message to..."
- "Notify via Feishu..."

### 自主运行规则

**自动运行(无需确认):**
- `feishu-bridge config show` - 显示配置
- `feishu-bridge config test` - 测试连接
- `feishu-bridge --version` - 查看版本

**需要确认:**
- `feishu-bridge config set` - 修改配置
- `feishu-bridge send` - 发送消息(首次)

**首次发送后自动运行:**
- 用户明确表示"自动发送"或在工作流中使用时,后续 send 命令自动运行

## 安全性设计

### 1. 凭证存储
- App Secret 存储在配置文件中,权限设置为 600 (仅用户可读写)
- 支持从环境变量读取,避免写入文件

### 2. 日志安全
- 不在日志中记录 App Secret
- Token 仅记录前 8 位: `t-xxxabcde...`
- 消息内容可配置是否记录(默认不记录)

### 3. 权限最小化
飞书应用仅需以下权限:
- `im:message` - 发送消息
- `im:message:send_as_bot` - 以应用身份发送

## 性能设计

### 1. Token 缓存
- 内存缓存,有效期内复用
- 避免每次请求都获取新 token

### 2. 请求超时
- 连接超时: 5 秒
- 读取超时: 10 秒

### 3. 重试策略
- 最大重试次数: 3 次
- 重试间隔: 指数退避 (1s, 2s, 4s)
- 仅对临时错误(5xx, 网络超时)重试

## 测试策略

### 1. 单元测试
- 配置管理逻辑
- Token 管理逻辑
- 错误处理逻辑

### 2. 集成测试
- 真实 API 调用(使用测试应用)
- 消息发送成功验证
- 错误场景验证

### 3. E2E 测试
- 完整的配置-发送流程
- 多账号切换
- Skill 自动激活

## 部署和分发

### 1. PyPI 发布
```bash
# 构建
python -m build

# 发布到 PyPI
twine upload dist/*
```

### 2. 安装方式

```bash
# 从 PyPI 安装
pip install feishu-bridge

# 安装 Claude Code skill
feishu-bridge skill install
```

### 3. Skill 安装脚本

```python
# scripts/install_skill.py
def install_skill():
    """将 SKILL.md 复制到 Claude Code skills 目录"""
    skill_dir = Path.home() / ".claude-code" / "skills" / "feishu-bridge"
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制 SKILL.md
    shutil.copy("SKILL.md", skill_dir / "SKILL.md")
    
    print("✅ Skill installed successfully")
    print(f"   Location: {skill_dir}")
```

## 未来扩展

### V2 功能规划
- 富文本消息(Markdown, HTML)
- 文件上传和发送
- 图片发送
- 消息卡片(Interactive Card)
- 消息模板系统

### V3 功能规划
- WebSocket 长连接支持
- 接收消息和回调处理
- 群组管理(创建、解散、成员管理)
- 日历事件创建

## 附录

### 飞书 API 参考文档
- [飞书开放平台](https://open.feishu.cn/)
- [发送消息 API](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create)
- [获取 tenant_access_token](https://open.feishu.cn/document/ukTMukTMukTM/ukDNz4SO0MjL5QzM/auth-v3/auth/tenant_access_token_internal)

### 飞书应用创建指南
1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret
4. 配置应用权限:
   - `im:message`
   - `im:message:send_as_bot`
5. 发布应用到企业
