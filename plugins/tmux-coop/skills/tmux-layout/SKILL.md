---
name: tmux-layout
description: 设置或复用 tmux 三栏工作布局（左侧 Claude 主流程占 60%，右上长程任务，右下 Codex 专用），并将不同类型任务路由到对应 pane。手动触发：用户说 "setup tmux layout"、"初始化 tmux 布局"、"建 tmux 工作区"、"/tmux-layout"。自动触发：当 Claude 需要执行长程命令（构建/测试/服务启动/超过10秒的bash）、写超长文本文件（超过3000字）、启动 subagent、或调用 Codex 时，必须先确保布局存在，再将任务路由到对应 pane。
---

# TMux 三栏协作布局

## 布局结构

```
┌─────────────────────┬──────────────┐
│                     │  右上 Pane B  │
│  左 Claude 主流程    │  长程任务     │
│     (约 60% 宽)     ├──────────────┤
│                     │  右下 Pane C  │
│                     │  Codex 专用  │
└─────────────────────┴──────────────┘
```

## 前置检查

如果当前不在 tmux 中（`$TMUX` 为空），提示用户先进入 tmux session，不自动创建。

```bash
[ -z "$TMUX" ] && echo "请先进入 tmux session，或运行 /tmux-init 完成初始化" && exit 1
```

## 第一步：检查布局是否已存在（优先复用）

```bash
RIGHT_TOP=$(tmux show-environment CLAUDE_PANE_RIGHT_TOP 2>/dev/null | cut -d= -f2)
RIGHT_BOTTOM=$(tmux show-environment CLAUDE_PANE_RIGHT_BOTTOM 2>/dev/null | cut -d= -f2)
PANES_ALIVE=$(tmux list-panes -a -F '#{pane_id}' 2>/dev/null)

if echo "$PANES_ALIVE" | grep -q "^${RIGHT_TOP}$" && \
   echo "$PANES_ALIVE" | grep -q "^${RIGHT_BOTTOM}$"; then
    echo "复用已有布局: RIGHT_TOP=$RIGHT_TOP RIGHT_BOTTOM=$RIGHT_BOTTOM"
else
    echo "建立新布局..."
fi
```

## 第二步：建立布局（仅在不存在时执行）

```bash
MAIN_PANE=$(tmux display-message -p '#{pane_id}')

# 向右分割，右侧占 40%（左侧自然是 60%）
tmux split-window -h -p 40
RIGHT_TOP=$(tmux display-message -p '#{pane_id}')

# 将右侧 pane 上下对半分
tmux split-window -v -p 50
RIGHT_BOTTOM=$(tmux display-message -p '#{pane_id}')

# 持久化三个 pane ID 到 tmux 环境变量，供后续复用
tmux set-environment CLAUDE_PANE_MAIN "$MAIN_PANE"
tmux set-environment CLAUDE_PANE_RIGHT_TOP "$RIGHT_TOP"
tmux set-environment CLAUDE_PANE_RIGHT_BOTTOM "$RIGHT_BOTTOM"

# 焦点回到 Claude 主 pane
tmux select-pane -t "$MAIN_PANE"
```

## 第三步：任务路由规则

建立或复用布局后，按以下规则将任务路由到对应 pane：

| 任务类型 | 路由目标 | 执行方式 |
|---------|---------|---------|
| 普通短命令（预计 < 10s） | 主 pane | 直接用 Bash 工具 |
| 长程命令（构建/测试/服务启动） | 右上 Pane B | `tmux send-keys` |
| 写超长文本文件（> 3000字） | 右上 Pane B | `tmux send-keys` |
| 启动 subagent | 右上 Pane B | `tmux send-keys` |
| 调用 Codex | 右下 Pane C | `tmux send-keys` |

### 发送任务到右上 Pane B（长程任务）

```bash
RIGHT_TOP=$(tmux show-environment CLAUDE_PANE_RIGHT_TOP | cut -d= -f2)
OUTFILE="/tmp/task_$(date +%s).txt"
tmux send-keys -t "$RIGHT_TOP" \
  "cd ${PROJECT_DIR} && <命令> > $OUTFILE 2>&1" Enter
```

执行完毕后，用 Read 工具读取结果：`$OUTFILE`

### 发送 Codex 命令到右下 Pane C

Codex 是异步长程任务，标准路由：右下执行，输出重定向到文件。

```bash
RIGHT_BOTTOM=$(tmux show-environment CLAUDE_PANE_RIGHT_BOTTOM | cut -d= -f2)
OUTFILE="/tmp/codex_$(date +%s).txt"

tmux send-keys -t "$RIGHT_BOTTOM" \
  "cd ${PROJECT_DIR} && \
   timeout <秒数> codex exec --full-auto \
   --sandbox danger-full-access \
   --model gpt-4.1 \"<prompt>\" > $OUTFILE 2>&1 & tail -f $OUTFILE" Enter
```

执行完毕后，用 Read 工具读取完整结果：`$OUTFILE`

## 注意事项

- 主 pane 的 Claude 主流程**只通过 Bash 工具执行命令**，不通过 `send-keys` 操作自身
- 异步任务的输出统一重定向到 `/tmp/` 临时文件，Claude 通过 Read 工具异步读取
- 布局只在当前 tmux window 内操作，不跨 window
- pane ID 通过 tmux 环境变量持久化，session 内有效
- `PROJECT_DIR` 替换为当前项目目录（通常为 `$PWD` 或 `$CLAUDE_PROJECT_DIR`）
