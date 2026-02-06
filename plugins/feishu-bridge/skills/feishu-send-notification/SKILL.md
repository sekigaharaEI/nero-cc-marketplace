---
name: feishu-send-notification
description: 通过飞书开放平台发送私聊通知消息。向个人(open_id)发送文本消息。当需要发送飞书通知、提醒用户、同步状态时使用。
allowed-tools: Bash(python:*), Bash(python3:*)
---

# 飞书消息通知

向飞书发送私聊通知消息,支持单个机器人应用的个人对话。

## 使用场景

- 任务完成通知
- 个人状态同步
- 个人消息提醒
- 工作流进度更新

## 发送消息命令

### 发送个人消息

向特定用户发送私聊消息(使用用户的 Open ID):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py send \
  --to <open_id> \
  --message "消息内容"
```

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--to` | 用户 Open ID(必需) | `ou_xxx` |
| `--message` | 消息文本 | `"任务已完成"` |

## 错误处理

如果发送失败,检查:
1. 配置是否正确:`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py config show`
2. 网络连接是否正常
3. 接收者 ID 是否正确
4. 应用权限是否配置(需要 `im:message` 权限)

如果提示"未配置",请先运行 `/feishu-setup` 完成配置。

## 示例

**提醒会议时间:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py send --to ou_xxx --message "会议时间改到下午3点"
```
