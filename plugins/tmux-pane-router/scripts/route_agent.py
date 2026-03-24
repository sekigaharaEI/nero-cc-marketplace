#!/usr/bin/env python3
"""
route_agent.py - Claude Code PreToolUse Hook：将 Agent 活动展示到右下 tmux pane

工作原理：
  1. 拦截 Claude Code 的 Agent 工具调用（spawn subagent）
  2. 在右下 tmux pane 中显示 Agent 的任务描述和关键信息
  3. 以 exit 0 退出，让 Claude Code 继续正常执行 Agent

退出码语义：
  exit 0  → 允许 Agent 正常启动（只做展示，不干预执行）

配置文件：~/.claude/tmux-pane-router.conf
  需要包含：TMUX_AGENT_PANE=<pane_id>
"""

import json
import os
import sys
import subprocess
import textwrap
from datetime import datetime


CONFIG_FILE = os.path.expanduser("~/.claude/tmux-pane-router.conf")
# Agent 描述最多展示的字符数
PROMPT_PREVIEW_LEN = 300


def load_config() -> dict:
    config = {}
    if not os.path.exists(CONFIG_FILE):
        return config
    with open(CONFIG_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                config[key.strip()] = val.strip()
    return config


def pane_exists(pane_id: str) -> bool:
    try:
        result = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", "#{pane_id}"],
            capture_output=True, text=True, timeout=5
        )
        return pane_id in result.stdout.splitlines()
    except Exception:
        return False


def send_to_pane(pane_id: str, text: str):
    """向 tmux pane 发送一行文本（echo 输出）。"""
    # 转义单引号
    safe = text.replace("'", "'\\''")
    subprocess.run(
        ["tmux", "send-keys", "-t", pane_id, f"echo '{safe}'", "Enter"],
        timeout=5
    )


def display_agent_info(pane_id: str, tool_input: dict):
    """在 Agent 活动 pane 中展示本次 Agent 调用的摘要。"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    sep = "─" * 44

    # 提取关键字段
    description = tool_input.get("description", "")
    prompt = tool_input.get("prompt", "")
    subagent_type = tool_input.get("subagent_type", "general-purpose")

    # 构造预览文本
    preview = description or prompt
    if len(preview) > PROMPT_PREVIEW_LEN:
        preview = preview[:PROMPT_PREVIEW_LEN] + "…"
    # 截断为单行（避免 send-keys 换行问题）
    preview_line = " ".join(preview.splitlines())[:200]

    lines = [
        f"\\033[90m{sep}\\033[0m",
        f"\\033[1;36m[{timestamp}] Agent 启动\\033[0m",
        f"  类型: {subagent_type}",
    ]
    if description:
        lines.append(f"  描述: {description[:120]}")
    if preview_line:
        lines.append(f"  任务: {preview_line}")
    lines.append(f"\\033[90m{sep}\\033[0m")

    for line in lines:
        # 使用 echo -e 支持 ANSI 颜色代码
        safe = line.replace("'", "'\\''")
        try:
            subprocess.run(
                ["tmux", "send-keys", "-t", pane_id, f"echo -e '{safe}'", "Enter"],
                timeout=5
            )
        except Exception:
            pass


def main():
    # ── 读取 Claude Code 传入的 JSON ──────────────────────────────────────────
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})

    # ── 读取配置 ───────────────────────────────────────────────────────────────
    config = load_config()
    agent_pane = config.get("TMUX_AGENT_PANE", "")
    if not agent_pane:
        sys.exit(0)

    # ── 检查 tmux 环境 ─────────────────────────────────────────────────────────
    if not os.environ.get("TMUX"):
        sys.exit(0)

    if not pane_exists(agent_pane):
        sys.exit(0)

    # ── 在右下 pane 展示 Agent 信息 ────────────────────────────────────────────
    try:
        display_agent_info(agent_pane, tool_input)
    except Exception:
        pass  # 展示失败不影响 Agent 执行

    # exit 0：让 Claude Code 正常执行 Agent
    sys.exit(0)


if __name__ == "__main__":
    main()
