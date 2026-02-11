# 企业微信 Webhook 消息桥 - 技术设计

## 概述

`wecom-bridge-webhook` 插件通过企业微信群机器人 Webhook 发送 Markdown 通知消息。相比 feishu-bridge 使用开放平台 API + OAuth 认证，本插件直接使用 Webhook URL，无需 access_token 管理，实现极简。

核心能力：通过 `curl` 调用企业微信群机器人 Webhook，发送 Markdown 格式消息。

## 与 feishu-bridge 的关键差异

| 项目 | feishu-bridge | wecom-bridge-webhook |
|------|--------------|---------------------|
| 认证方式 | OAuth (app_id + app_secret → token) | Webhook URL (key 即凭证) |
| API 复杂度 | 需要获取 token → 发消息两步 | 单次 POST 即可 |
| 消息格式 | text (JSON content 字符串) | markdown (原生支持) |
| 发送目标 | 个人私聊 (open_id) | 群机器人所在群聊 (可 @指定人) |
| 依赖 | requests (Python) | curl (系统自带) |
| Token 管理 | 需要缓存/刷新 | 无需 |

## 系统架构

```
┌─────────────────┐
│  Claude Code    │
│   (AI Agent)    │
└────────┬────────┘
         │
         │ 调用 CLI (Python)
         ▼
┌─────────────────┐
│ wecom_cli.py    │
│  构建消息体      │
│  调用 curl       │
└────────┬────────┘
         │
         │ curl POST (Webhook)
         ▼
┌─────────────────┐
│  企业微信        │
│  群机器人 API    │
└─────────────────┘
```

## 插件目录结构

```
plugins/wecom-bridge-webhook/
├── .claude-plugin/
│   └── plugin.json                    # 插件元数据
├── hooks/
│   ├── hooks.json                     # Hook 定义
│   ├── send_notification.py           # Notification hook
│   └── send_task_report.py            # Stop hook
├── scripts/
│   └── wecom_cli.py                   # CLI 工具 (核心)
├── skills/
│   ├── wecom-send-notification/
│   │   └── SKILL.md                   # 发送通知 skill
│   └── wecom-setup/
│       └── SKILL.md                   # 配置向导 skill
├── README.md
└── requirements.txt                   # 无额外依赖，仅标注 Python 3.8+
```

## 配置设计

### 配置文件

路径：`~/.wecom-bridge-webhook/config.json`，权限 600。

```json
{
  "webhook_key": "6b13a910-c195-4975-b198-73272695f3f1",
  "user_id": "ZhaYunWei",
  "user_name": "查云威",
  "notification_templates": {
    "permission_prompt": "### 🔔 权限确认\n> **<@${user_id}> ${user_name}**，Claude Code 正在等待您的权限确认。\n> 请查看 Claude Code 界面并做出选择。",
    "idle_prompt": "### ⏰ 等待输入\n> **<@${user_id}> ${user_name}**，Claude Code 已空闲超过 60 秒。\n> 请查看是否需要提供输入。",
    "elicitation_dialog": "### ❓ 需要输入\n> **<@${user_id}> ${user_name}**，Claude Code 需要您提供信息。\n> 请查看 Claude Code 界面。",
    "task_complete": "### ✅ 任务完成\n> **<@${user_id}> ${user_name}**，Claude Code 任务已完成，请查看状态。"
  }
}
```

### 配置字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `webhook_key` | string | 是 | 企业微信群机器人 Webhook URL 中的 key 参数 |
| `user_id` | string | 是 | 企业微信 UserId，用于 `<@UserId>` 提及 |
| `user_name` | string | 是 | 显示名称，用于消息中的称呼 |
| `notification_templates` | object | 否 | 自定义消息模板，支持 `${user_id}` 和 `${user_name}` 变量替换。不提供则使用默认模板 |

### 模板变量

模板中支持以下变量，运行时自动替换：

- `${user_id}` → 配置中的 `user_id` 值
- `${user_name}` → 配置中的 `user_name` 值

## CLI 工具设计 (wecom_cli.py)

### 命令

```bash
# 发送自定义 markdown 消息
python3 wecom_cli.py send --message "### 标题\n内容"

# 发送消息并 @指定人
python3 wecom_cli.py send --message "### 标题\n内容" --mention

# 显示当前配置
python3 wecom_cli.py config show

# 设置配置
python3 wecom_cli.py config set \
  --webhook-key "6b13a910-xxxx" \
  --user-id "ZhaYunWei" \
  --user-name "查云威"

# 测试发送
python3 wecom_cli.py test
```

### 核心实现逻辑

```
send 命令流程:
1. 加载 ~/.wecom-bridge-webhook/config.json
2. 构建请求体:
   {
     "msgtype": "markdown",
     "markdown": {
       "content": "<消息内容>"
     }
   }
3. 调用 curl:
   curl -s -X POST \
     "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}" \
     -H "Content-Type: application/json" \
     -d '{请求体}'
4. 解析响应，检查 errcode == 0
5. 输出结果
```

### 为什么用 curl 而不是 requests

- 零依赖：不需要 `pip install` 任何包
- 系统自带：Linux/macOS/WSL 均预装 curl
- 与用户提供的命令一致，降低调试成本
- Webhook 场景足够简单，不需要 session/cookie/token 管理

### 错误处理

| 场景 | 处理 |
|------|------|
| 配置文件不存在 | 提示运行 `/wecom-setup` |
| webhook_key 为空 | 报错退出 |
| curl 执行失败 | 输出 stderr，退出码 1 |
| API 返回 errcode != 0 | 输出错误信息（如 key 无效、频率限制等） |
| 网络超时 | curl 设置 10s 超时 |

## Hooks 设计

### hooks.json

```json
{
  "description": "企业微信 Webhook 消息桥钩子 - 在关键事件时发送企业微信通知",
  "hooks": {
    "Notification": [
      {
        "matcher": "permission_prompt|idle_prompt|elicitation_dialog",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/send_notification.py",
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/send_task_report.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### Hook 脚本逻辑

与 feishu-bridge 保持一致的模式：

1. 从 stdin 读取 JSON 输入
2. 加载 `~/.wecom-bridge-webhook/config.json`
3. 未配置则静默退出 (exit 0)
4. 根据 notification_type 选择对应模板
5. 替换模板变量 (`${user_id}`, `${user_name}`)
6. 调用 `wecom_cli.py send` 发送
7. 始终 exit 0（不阻塞 Claude Code）

## Skills 设计

### Skill 1: wecom-send-notification

```yaml
---
name: wecom-send-notification
description: 通过企业微信群机器人 Webhook 发送 Markdown 通知消息。当需要发送企业微信通知、提醒用户、同步状态时使用。
allowed-tools: Bash(python:*), Bash(python3:*), Bash(curl:*)
---
```

内容：教模型如何调用 `wecom_cli.py send` 发送消息，包含参数说明和示例。

### Skill 2: wecom-setup

```yaml
---
name: wecom-setup
description: 企业微信 Webhook 消息桥的安装和配置引导。
disable-model-invocation: true
---
```

交互式配置向导，引导用户：

1. 在企业微信群中添加群机器人，获取 Webhook URL
2. 从 URL 中提取 key
3. 确认 UserId 和显示名称
4. 保存配置到 `~/.wecom-bridge-webhook/config.json`
5. 发送测试消息验证

## plugin.json

```json
{
  "name": "wecom-bridge-webhook",
  "description": "企业微信 Webhook 消息桥 - 通过群机器人 Webhook 发送 Markdown 通知消息。支持 @指定人、自定义消息模板。",
  "version": "1.0.0",
  "author": {
    "name": "Nero"
  },
  "license": "MIT",
  "repository": "https://github.com/sekigaharaEI/nero-cc-marketplace",
  "keywords": [
    "wecom",
    "wechat-work",
    "webhook",
    "notification",
    "messaging",
    "automation"
  ]
}
```

## Marketplace 注册

在 `.claude-plugin/marketplace.json` 的 `plugins` 数组中添加：

```json
{
  "name": "wecom-bridge-webhook",
  "source": "./plugins/wecom-bridge-webhook",
  "description": "企业微信 Webhook 消息桥 - 通过群机器人 Webhook 发送 Markdown 通知",
  "version": "1.0.0",
  "tags": ["wecom", "webhook", "notification", "messaging"]
}
```

## 企业微信 Webhook API 参考

### 接口地址

```
POST https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}
```

### Markdown 消息请求体

```json
{
  "msgtype": "markdown",
  "markdown": {
    "content": "### 标题\n> 引用内容\n**加粗** 普通文本\n<@UserId> 提及某人"
  }
}
```

### 成功响应

```json
{
  "errcode": 0,
  "errmsg": "ok"
}
```

### Markdown 语法支持范围

企业微信 Webhook Markdown 支持有限子集：
- 标题：`#`、`##`、`###`
- 加粗：`**text**`
- 链接：`[text](url)`
- 引用：`> text`
- 字体颜色：`<font color="info">绿色</font>`、`<font color="warning">橙色</font>`、`<font color="comment">灰色</font>`
- @人：`<@UserId>`

**不支持**：图片、表格、代码块、有序/无序列表。

### 频率限制

- 每个机器人每分钟最多发送 20 条消息

## 开发顺序

1. **plugin.json** — 元数据
2. **wecom_cli.py** — CLI 核心（config set/show + send + test）
3. **hooks.json + hook 脚本** — Notification 和 Stop hook
4. **skills/** — wecom-send-notification + wecom-setup
5. **README.md** — 插件文档
6. **注册 marketplace + 更新根 README**

## 待确认事项

在开始编码前，需要你确认：

1. ~~企业微信 API 文档~~ — 已明确使用 Webhook，无需额外 API 文档
2. **消息模板**：上面设计的默认模板（permission_prompt / idle_prompt / elicitation_dialog / task_complete）是否满足需求？需要调整措辞吗？
3. **是否需要支持 text 类型消息**：当前设计只支持 markdown，是否需要同时支持纯文本？
4. **配置文件路径**：`~/.wecom-bridge-webhook/config.json` 是否合适？
