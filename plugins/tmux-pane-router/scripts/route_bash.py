#!/usr/bin/env python3
"""
route_bash.py - Claude Code PreToolUse Hook：将 Bash 工具路由到右上 tmux pane

工作原理：
  1. 拦截 Claude Code 的 Bash 工具调用
  2. 在右上 tmux pane 中执行命令，通过临时文件捕获输出
  3. 将输出打印到 stdout，以 exit code 2 退出
  4. Claude Code 看到 exit 2 后，使用 stdout 作为 Bash 工具的结果，
     不再自行执行该命令

退出码语义（Claude Code PreToolUse Hook）：
  exit 0  → 允许工具正常执行（hook 的 stdout 仅供记录）
  exit 2  → 阻止工具执行，用 hook 的 stdout 作为工具返回结果
  其他非零 → 报错，Claude 看到 stderr 作为错误信息

配置文件：~/.claude/tmux-pane-router.conf
  需要包含：TMUX_BASH_PANE=<pane_id>
"""

import json
import os
import sys
import subprocess
import tempfile
import time


CONFIG_FILE = os.path.expanduser("~/.claude/tmux-pane-router.conf")
# Bash 命令最长等待时间（秒）
TIMEOUT = 120


def load_config() -> dict:
    """读取配置文件，返回 key-value 字典。"""
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
    """检查指定 tmux pane 是否存在。"""
    try:
        result = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", "#{pane_id}"],
            capture_output=True, text=True, timeout=5
        )
        return pane_id in result.stdout.splitlines()
    except Exception:
        return False


def run_in_pane(pane_id: str, command: str) -> tuple[str, int]:
    """
    在指定 tmux pane 中执行命令，等待完成并返回 (output, exit_code)。

    策略：
      - 将命令写入临时脚本文件（避免 shell 转义问题）
      - 在 tmux pane 中执行，stdout/stderr 同时写入临时输出文件（tee）
      - 等待 "完成标记文件" 出现（由脚本末尾的 touch 创建）
      - 读取输出文件并返回
    """
    # 创建临时文件
    script_fd, script_path = tempfile.mkstemp(suffix=".sh", prefix="claude_bash_")
    out_fd, out_path = tempfile.mkstemp(suffix=".out", prefix="claude_bash_")
    exit_path = out_path + ".exit"
    done_path = out_path + ".done"

    os.close(script_fd)
    os.close(out_fd)

    try:
        # 写入命令脚本（完整保留换行、特殊字符）
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n")
            f.write(command + "\n")
            f.write(f'echo $? > "{exit_path}"\n')
            f.write(f'touch "{done_path}"\n')
        os.chmod(script_path, 0o755)

        # 在 tmux pane 中运行（使用 tee 同时显示和捕获）
        # 添加分隔线方便用户辨认
        sep = "─" * 40
        header = f"echo '\\033[90m{sep}\\033[0m'"
        run_cmd = f'{header}; bash "{script_path}" 2>&1 | tee "{out_path}"; {header}'
        subprocess.run(
            ["tmux", "send-keys", "-t", pane_id, run_cmd, "Enter"],
            timeout=5
        )

        # 轮询等待完成标记
        start = time.time()
        while time.time() - start < TIMEOUT:
            if os.path.exists(done_path):
                break
            time.sleep(0.2)
        else:
            # 超时，返回已捕获的部分输出
            output = _read_file(out_path)
            return output + f"\n[tmux-pane-router] 警告：命令执行超时（>{TIMEOUT}s）", 1

        # 读取结果
        output = _read_file(out_path)
        exit_code = _read_exit_code(exit_path)
        return output, exit_code

    finally:
        # 清理临时文件
        for path in [script_path, out_path, exit_path, done_path]:
            try:
                os.unlink(path)
            except OSError:
                pass


def _read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _read_exit_code(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def main():
    # ── 读取 Claude Code 传入的 JSON ──────────────────────────────────────────
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    # ── 读取配置 ───────────────────────────────────────────────────────────────
    config = load_config()
    bash_pane = config.get("TMUX_BASH_PANE", "")
    if not bash_pane:
        # 未配置，让 Claude 正常执行
        sys.exit(0)

    # ── 检查 tmux 环境 ─────────────────────────────────────────────────────────
    if not os.environ.get("TMUX"):
        sys.exit(0)

    if not pane_exists(bash_pane):
        # pane 不存在（可能 session 已关闭），透传给 Claude 正常处理
        sys.exit(0)

    # ── 在右上 pane 执行命令 ────────────────────────────────────────────────────
    output, exit_code = run_in_pane(bash_pane, command)

    # ── 将输出返回给 Claude Code ────────────────────────────────────────────────
    # exit 2：Claude Code 使用我们的 stdout 作为 Bash 工具结果，不再自己执行
    sys.stdout.write(output)
    sys.exit(2)


if __name__ == "__main__":
    main()
