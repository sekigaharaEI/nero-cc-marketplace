# tmux-pane-router

**Tmux三分屏路由器** - 将 Claude Code 的 Bash 命令路由到右上 pane 执行，将 Agent 活动展示到右下 pane，让终端操作一目了然。

## 布局示意

```
+---------------------------+------------------+
|                           |  [右上] Bash执行  |
|   Claude Code (主窗口)    |                  |
|                           +------------------+
|                           |  [右下] Agent活动 |
+---------------------------+------------------+
```

## 工作原理

本插件利用 Claude Code 的 **PreToolUse Hook** 机制：

| 工具  | Hook 行为 | 退出码 |
|-------|-----------|--------|
| `Bash` | 在右上 pane 中执行命令，捕获输出返回给 Claude | `exit 2`（替代 Claude 自行执行） |
| `Agent` | 在右下 pane 显示 Agent 任务摘要 | `exit 0`（Agent 正常启动） |

### Bash 路由详细流程

```
Claude 决定执行 Bash 命令
        ↓
PreToolUse Hook (route_bash.py) 触发
        ↓
将命令写入临时脚本 → send-keys 发送到右上 pane
        ↓
轮询等待执行完成（最长 120s）
        ↓
读取捕获的输出 → 打印到 stdout → exit 2
        ↓
Claude 收到输出，视为 Bash 工具结果（不再自行执行）
```

## 安装

```bash
/plugin install tmux-pane-router@nero-cc-marketplace
```

## 快速开始

### 方式一：在已有 tmux session 中使用

```bash
# 1. 在 tmux 中启动 Claude Code
tmux new-session
claude

# 2. 在 Claude Code 中运行布局命令
/tmux-setup
```

### 方式二：一键启动（从普通终端）

```bash
# 自动创建 tmux session，分屏，并启动 Claude Code
bash ~/.claude/plugins/tmux-pane-router/scripts/setup_layout.sh --new
```

## 命令

| 命令 | 说明 |
|------|------|
| `/tmux-setup` | 在当前 tmux window 中创建三分屏布局，保存 pane 配置 |
| `/tmux-status` | 查看当前 pane 配置状态，检查各 pane 是否存活 |

## Hooks

| Hook | 触发时机 | 说明 |
|------|----------|------|
| `PreToolUse:Bash` | Claude 执行任何 Bash 命令前 | 路由到右上 pane 执行 |
| `PreToolUse:Agent` | Claude 启动任何 Agent 前 | 在右下 pane 显示任务摘要 |

## 配置文件

布局信息保存在 `~/.claude/tmux-pane-router.conf`：

```ini
# tmux-pane-router 配置文件
TMUX_MAIN_PANE=%0
TMUX_BASH_PANE=%1
TMUX_AGENT_PANE=%2
TMUX_SESSION=claude-code
TMUX_WINDOW=@0
```

如需手动绑定到已有 pane，直接编辑此文件即可。

## 故障排除

**Q：Bash 命令没有出现在右上 pane**

1. 确认在 tmux session 中运行：`echo $TMUX`（有输出即为 tmux 内）
2. 检查配置是否存在：`cat ~/.claude/tmux-pane-router.conf`
3. 检查 pane 是否存活：`tmux list-panes -a`
4. 重新运行 `/tmux-setup`

**Q：重启终端后路由失效**

tmux session 关闭后 pane ID 失效，重新开启 tmux 后运行 `/tmux-setup` 更新配置即可。

**Q：某些命令（如 `vim`、`less`）在右上 pane 中显示异常**

交互式命令不适合通过 tmux send-keys 的捕获方式运行。这类命令会在右上 pane 显示，但交互操作需要切换到该 pane 进行。

## 版本历史

- **v1.0.0** - 初始版本，支持 Bash 路由执行和 Agent 活动展示
