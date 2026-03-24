#!/bin/bash
# setup_layout.sh - 在当前 tmux session 中创建三分屏布局
#
# 布局示意：
# +---------------------------+------------------+
# |                           |  [右上] Bash执行  |
# |   Claude Code (主窗口)    +------------------+
# |                           |  [右下] Agent活动 |
# +---------------------------+------------------+
#
# 用法：
#   bash setup_layout.sh           # 在当前 tmux window 中添加分屏
#   bash setup_layout.sh --new     # 创建新的 tmux session 并启动 Claude

set -e

CONFIG_FILE="${HOME}/.claude/tmux-pane-router.conf"
mkdir -p "$(dirname "$CONFIG_FILE")"

# ── 检查 tmux 环境 ─────────────────────────────────────────────────────────────
if [ -z "$TMUX" ]; then
    if [ "$1" = "--new" ]; then
        # 在新 session 中启动完整布局
        SESSION="claude-code"
        echo "创建新 tmux session: $SESSION"
        tmux new-session -d -s "$SESSION" -x 220 -y 50
        # 用 tmux 内部执行布局脚本（此时 $TMUX 已设置）
        tmux send-keys -t "$SESSION" "bash '${BASH_SOURCE[0]}' && claude" Enter
        tmux attach-session -t "$SESSION"
        exit 0
    else
        echo "错误：请在 tmux session 内运行此脚本，或使用 --new 参数创建新 session"
        echo "  bash setup_layout.sh --new"
        exit 1
    fi
fi

CURRENT_WINDOW=$(tmux display-message -p '#{window_id}')
CURRENT_PANE=$(tmux display-message -p '#{pane_id}')

echo "当前 window: $CURRENT_WINDOW, 当前 pane: $CURRENT_PANE"

# ── 检查是否已有三格布局 ────────────────────────────────────────────────────────
PANE_COUNT=$(tmux list-panes -F '#{pane_id}' | wc -l)
if [ "$PANE_COUNT" -ge 3 ]; then
    echo "警告：当前 window 已有 $PANE_COUNT 个 pane，是否覆盖配置？(y/N)"
    read -r answer
    if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
        echo "已取消"
        exit 0
    fi
fi

# ── 创建分屏布局 ────────────────────────────────────────────────────────────────
# 第1步：水平分割，创建右侧区域（右侧占 38%）
tmux split-window -h -p 38 -t "$CURRENT_PANE"
RIGHT_TOP_PANE=$(tmux display-message -p '#{pane_id}')

# 第2步：垂直分割右侧，上下各占 50%
tmux split-window -v -p 50 -t "$RIGHT_TOP_PANE"
RIGHT_BOTTOM_PANE=$(tmux display-message -p '#{pane_id}')

# 重新获取主 pane（分割后 ID 不变）
MAIN_PANE="$CURRENT_PANE"
BASH_PANE="$RIGHT_TOP_PANE"
AGENT_PANE="$RIGHT_BOTTOM_PANE"

# ── 设置 pane 标题 ──────────────────────────────────────────────────────────────
tmux select-pane -t "$MAIN_PANE"  -T "Claude Code"
tmux select-pane -t "$BASH_PANE"  -T "Bash 执行"
tmux select-pane -t "$AGENT_PANE" -T "Agent 活动"

# 在右侧 pane 显示欢迎信息
tmux send-keys -t "$BASH_PANE" "echo '── Bash 执行区 ──────────────────────────────'" Enter
tmux send-keys -t "$BASH_PANE" "echo 'Claude Code 的 Bash 命令将在此处执行并显示'" Enter

tmux send-keys -t "$AGENT_PANE" "echo '── Agent 活动区 ─────────────────────────────'" Enter
tmux send-keys -t "$AGENT_PANE" "echo 'Claude Code 的 Agent 调用将在此处显示信息'" Enter

# ── 保存配置 ────────────────────────────────────────────────────────────────────
cat > "$CONFIG_FILE" << EOF
# tmux-pane-router 配置文件
# 自动生成于 $(date)
TMUX_MAIN_PANE=$MAIN_PANE
TMUX_BASH_PANE=$BASH_PANE
TMUX_AGENT_PANE=$AGENT_PANE
TMUX_SESSION=$(tmux display-message -p '#S')
TMUX_WINDOW=$CURRENT_WINDOW
EOF

# ── 返回主 pane ─────────────────────────────────────────────────────────────────
tmux select-pane -t "$MAIN_PANE"

echo ""
echo "✓ tmux 三分屏布局创建成功！"
echo ""
echo "  主窗口 (Claude Code): $MAIN_PANE"
echo "  右上 (Bash 执行):     $BASH_PANE"
echo "  右下 (Agent 活动):    $AGENT_PANE"
echo ""
echo "配置已保存至: $CONFIG_FILE"
echo ""
echo "提示：插件 Hook 将自动将 Bash 命令路由到右上 pane 执行。"
