#!/usr/bin/env bash
# setup_tmux.sh - 安装 tmux-coop 配置到用户 ~/.tmux.conf
# 用法: bash setup_tmux.sh [--plugin-root <path>]

set -euo pipefail

# 解析参数
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin-root) PLUGIN_ROOT="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

CONF_SRC="$PLUGIN_ROOT/configs/tmux.conf"
CONF_DST="$HOME/.tmux.conf"

# 1. 检测 tmux 是否安装
if ! command -v tmux &>/dev/null; then
  echo '{"ok": false, "error": "tmux not installed", "hint": "apt install tmux / brew install tmux"}'
  exit 1
fi

TMUX_VERSION=$(tmux -V | grep -oP '[\d.]+')
echo "tmux $TMUX_VERSION detected"

# 2. 备份已有配置
if [[ -f "$CONF_DST" ]]; then
  BACKUP="${CONF_DST}.bak.$(date +%Y%m%d%H%M%S)"
  cp "$CONF_DST" "$BACKUP"
  echo "Backed up existing config to $BACKUP"
fi

# 3. 复制插件配置
cp "$CONF_SRC" "$CONF_DST"
echo "Installed $CONF_SRC -> $CONF_DST"

# 4. 如果当前在 tmux 中，热加载配置
if [[ -n "${TMUX:-}" ]]; then
  tmux source-file "$CONF_DST"
  echo "Config reloaded (tmux source-file)"
fi

echo '{"ok": true}'
