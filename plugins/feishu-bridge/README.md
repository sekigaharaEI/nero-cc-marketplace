# Feishu Bridge - 飞书消息桥

通过飞书开放平台发送私聊通知消息的 Claude Code 插件。支持文本消息发送、环境变量和配置文件双模式凭证管理。

## 功能特性

- 🚀 **简单易用**: 一行命令发送飞书通知
- 🔐 **灵活配置**: 支持环境变量和配置文件两种方式
- 💬 **私聊通知**: 向个人发送文本消息
- 🔄 **自动调用**: AI 可根据需要自动发送通知
- 🛡️ **安全可靠**: Token 自动缓存和刷新

## 安装

```bash
/plugin install feishu-bridge@nero-cc-marketplace
```

## 快速开始

### 1. 配置飞书应用

首次使用需要配置飞书应用凭证。运行交互式配置向导:

```bash
/feishu-setup
```

配置向导将引导你完成以下步骤:
1. 检查依赖环境
2. 创建飞书企业自建应用
3. 配置应用权限并发布
4. 获取 App ID 和 App Secret
5. 选择配置方式（配置文件/环境变量）
6. 获取接收者 Open ID
7. 测试发送消息
8. 配置完成

**新版特性**: v1.0.1 提供了完全交互式的配置流程，每一步都有明确的网址链接和选项引导。

### 2. 发送测试消息

配置完成后,测试发送消息:

```bash
python3 ~/.claude/plugins/feishu-bridge/scripts/feishu_cli.py send \
  --to ou_xxx \
  --message "测试消息"
```

### 3. AI 自动调用

配置完成后,AI 可以根据需要自动发送飞书通知:

```
用户: "代码审查完成后,通过飞书通知我"
AI: [执行审查...]
    [发送飞书通知: "代码审查已完成"]
```

## Skills

### feishu-send-notification

教 AI 如何发送飞书通知消息。

**使用场景:**
- 任务完成通知
- 状态同步提醒
- 工作流进度更新

**示例:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py send \
  --to ou_xxx \
  --message "部署完成"
```

### feishu-setup

交互式配置向导（仅用户手动调用）。

**调用方式:**
```bash
/feishu-setup
```

**功能:**
- 分步引导完成飞书应用创建和配置
- 提供明确的网址链接和操作指引
- 使用选项式交互，降低配置出错率
- 自动验证配置并发送测试消息

**新版特性 (v1.0.1):**
- 完全重写的交互式配置流程
- 每一步都有明确的飞书开放平台链接
- 使用 AskUserQuestion 工具引导用户选择
- 详细的故障排查指南

## 配置方式

**推荐**: 使用 `/feishu-setup` 交互式配置向导，它会自动引导你选择配置方式。

### 方式 1: 配置文件（推荐）

使用 CLI 工具设置:

```bash
python3 ~/.claude/plugins/feishu-bridge/scripts/feishu_cli.py config set \
  --app-id "cli_xxx" \
  --app-secret "xxx" \
  --domain "feishu"
```

配置保存在 `~/.feishu-bridge/config.json`

### 方式 2: 环境变量

在 `~/.bashrc` 或 `~/.zshrc` 中添加:

```bash
export FEISHU_APP_ID="cli_xxxxxxxxxx"
export FEISHU_APP_SECRET="你的 App Secret"
export FEISHU_DOMAIN="feishu"
```

**注意**: 本插件仅支持飞书中国版，不支持 Lark 国际版。

## CLI 命令

### 发送消息

```bash
python3 feishu_cli.py send --to <open_id> --message "消息内容"
```

### 查看配置

```bash
python3 feishu_cli.py config show
```

### 设置配置

```bash
python3 feishu_cli.py config set \
  --app-id "cli_xxx" \
  --app-secret "xxx" \
  --domain "feishu"
```

## 飞书应用配置

### 必需权限

在飞书开放平台为应用添加以下权限:

- `im:message` - 获取与发送单聊、群组消息
- `im:message:send_as_bot` - 以应用的身份发消息

### 获取用户 Open ID

**方法 1: 通过飞书管理后台（推荐）**

🔗 **飞书管理后台**: https://feishu.cn/admin

1. 登录飞书管理后台
2. 点击左侧菜单 **"通讯录"**
3. 找到目标用户
4. 点击用户名，进入用户详情页
5. 复制用户的 Open ID (格式: `ou_xxxxxxxxxx`)

**方法 2: 通过飞书开放平台**

🔗 **事件订阅**: https://open.feishu.cn/app

1. 配置事件订阅（需要公网可访问的回调地址）
2. 订阅 `im.message.receive_v1` 事件
3. 在飞书客户端中给应用发送消息
4. 在事件订阅日志中查看 `sender.sender_id.open_id`

## 故障排查

### 错误: "未找到配置"

**解决**: 运行 `/feishu-setup` 完成配置

### 错误: "Failed to get token"

**原因**: App ID 或 App Secret 错误

**解决**: 检查环境变量或配置文件中的凭证是否正确

### 错误: "Permission denied"

**原因**: 应用缺少必要权限

**解决**:
1. 在飞书开放平台添加 `im:message` 权限
2. 重新发布应用版本

### 错误: "Invalid receive_id"

**原因**: 接收者 ID 格式错误

**解决**: 确认 Open ID 格式为 `ou_xxx`

## 安全建议

1. ⚠️ **不要提交 App Secret 到代码仓库**
2. 🔒 **使用环境变量存储凭证**
3. 🔄 **定期更新 App Secret**
4. 🛡️ **最小权限原则**: 只添加必要的权限

## 技术架构

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
│     Feishu      │
│ Open Platform   │
│   (中国版)      │
└─────────────────┘
```

## 依赖项

- Python 3.8+
- requests >= 2.28.0

## 限制

- 仅支持文本消息
- 仅支持个人私聊(不支持群组消息)
- 单向发送(不接收消息)

## 相关链接

- [飞书开放平台](https://open.feishu.cn/)
- [发送消息 API 文档](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create)
- [获取 tenant_access_token](https://open.feishu.cn/document/ukTMukTMukTM/ukDNz4SO0MjL5QzM/auth-v3/auth/tenant_access_token_internal)

## 许可证

MIT License

## 作者

Nero
