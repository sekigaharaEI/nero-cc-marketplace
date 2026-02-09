#!/usr/bin/env python3
"""
NotebookLM 环境检查脚本
输出 JSON 格式的检查结果，供 Claude 读取后决定下一步操作。

用法:
  python check_env.py

输出示例:
  {
    "notebooklm_found": true,
    "notebooklm_cmd": "notebooklm",
    "playwright_found": true,
    "auth_ok": true,
    "python_found": true,
    "python_version": "3.12.0",
    "platform": "windows"
  }
"""

import json
import platform
import shutil
import subprocess
import sys


def run_cmd(cmd, timeout=10):
    """运行命令，返回 (成功, 输出)"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, shell=isinstance(cmd, str)
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception:
        return False, ""


def find_notebooklm():
    """查找 notebooklm，返回 (found, cmd_path)"""
    if shutil.which("notebooklm"):
        return True, "notebooklm"
    return False, ""


def check_auth(notebooklm_cmd):
    """检查认证状态"""
    cmd = f"{notebooklm_cmd} auth check --json"
    ok, output = run_cmd(cmd)
    if ok and output:
        try:
            data = json.loads(output)
            return data.get("authenticated", False)
        except json.JSONDecodeError:
            pass
    return False


def check_playwright():
    """检查 Playwright chromium 是否已安装"""
    ok, output = run_cmd([sys.executable, "-c",
        "from playwright.sync_api import sync_playwright; "
        "p = sync_playwright().start(); "
        "b = p.chromium.launch(headless=True); "
        "b.close(); p.stop(); "
        "print('ok')"
    ], timeout=30)
    return ok and "ok" in output


def find_python():
    """查找 Python"""
    is_win = platform.system() == "Windows"
    candidates = ["python", "python3"] if is_win else ["python3", "python"]
    for cmd in candidates:
        ok, output = run_cmd([cmd, "--version"] if not is_win else f"{cmd} --version")
        if ok and output:
            version = output.replace("Python ", "").strip()
            return True, version
    return False, ""


def main():
    result = {
        "notebooklm_found": False,
        "notebooklm_cmd": "",
        "playwright_found": False,
        "auth_ok": False,
        "python_found": False,
        "python_version": "",
        "platform": platform.system().lower(),
    }

    # 查找 notebooklm
    found, cmd = find_notebooklm()
    result["notebooklm_found"] = found
    result["notebooklm_cmd"] = cmd

    # 检查认证
    if found:
        result["auth_ok"] = check_auth(cmd)

    # 检查 Playwright（独立于 notebooklm）
    result["playwright_found"] = check_playwright()

    # 检查 Python
    py_found, py_version = find_python()
    result["python_found"] = py_found
    result["python_version"] = py_version

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
