#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Stalker 环境检测脚本
检测 Python 版本、依赖包和 API 配置
"""

import sys
import json
import os

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    ok = version.major >= 3 and version.minor >= 8
    return {
        "ok": ok,
        "version": version_str,
        "required": ">=3.8",
        "error": None if ok else f"Python 版本 {version_str} 不满足要求，需要 3.8 或更高版本"
    }

def check_anthropic_package():
    """检查 anthropic 包"""
    try:
        import anthropic
        version = getattr(anthropic, "__version__", "unknown")

        # 检查版本是否 >= 0.18.0
        ok = True
        if version != "unknown":
            try:
                parts = version.split(".")
                major = int(parts[0])
                minor = int(parts[1]) if len(parts) > 1 else 0
                if major == 0 and minor < 18:
                    ok = False
            except (ValueError, IndexError):
                pass  # 无法解析版本，假设 OK

        return {
            "ok": ok,
            "installed": True,
            "version": version,
            "required": ">=0.18.0",
            "error": None if ok else f"anthropic 版本 {version} 过低，需要 0.18.0 或更高版本"
        }
    except ImportError:
        return {
            "ok": False,
            "installed": False,
            "version": None,
            "required": ">=0.18.0",
            "error": "anthropic 包未安装"
        }

def check_api_key():
    """检查 API 密钥配置"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    model = os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL")

    has_key = bool(api_key or auth_token)

    return {
        "ok": has_key,
        "has_api_key": bool(api_key),
        "has_auth_token": bool(auth_token),
        "has_base_url": bool(base_url),
        "base_url": base_url if base_url else None,
        "custom_model": model if model else None,
        "error": None if has_key else "未配置 API 密钥 (ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN)"
    }

def check_memories_dir():
    """检查记忆文件目录"""
    # 从环境变量获取项目路径
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    memories_dir = os.path.join(project_dir, ".claude", "memories")

    exists = os.path.exists(memories_dir)
    memory_count = 0

    if exists:
        try:
            memory_count = len([f for f in os.listdir(memories_dir) if f.endswith(".md")])
        except OSError:
            pass

    return {
        "ok": True,  # 目录不存在不是错误，会自动创建
        "exists": exists,
        "path": memories_dir,
        "memory_count": memory_count
    }

def main():
    """主函数"""
    # Windows 中文支持
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    # 执行所有检查
    python_check = check_python_version()
    anthropic_check = check_anthropic_package()
    api_check = check_api_key()
    memories_check = check_memories_dir()

    # 汇总结果
    all_ok = python_check["ok"] and anthropic_check["ok"] and api_check["ok"]

    errors = []
    warnings = []

    if not python_check["ok"]:
        errors.append(python_check["error"])

    if not anthropic_check["ok"]:
        if anthropic_check["installed"]:
            errors.append(anthropic_check["error"])
        else:
            errors.append(anthropic_check["error"])

    if not api_check["ok"]:
        warnings.append(api_check["error"])  # API 密钥缺失作为警告，因为可能稍后配置

    result = {
        "all_ok": all_ok,
        "python_ok": python_check["ok"],
        "anthropic_ok": anthropic_check["ok"],
        "api_key_ok": api_check["ok"],
        "python": python_check,
        "anthropic": anthropic_check,
        "api_key": api_check,
        "memories": memories_check,
        "errors": errors,
        "warnings": warnings,
        "install_command": "pip install anthropic>=0.18.0"
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 返回状态码
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
