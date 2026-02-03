#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找 Memory Stalker 提示词文件路径
优先级：缓存目录 > 插件安装目录
"""

import sys
import os
import json
from pathlib import Path


def get_home_dir() -> Path:
    """获取用户主目录，兼容 Windows 和 Linux"""
    return Path.home()


def find_prompt_file() -> dict:
    """
    查找提示词文件路径

    优先级：
    1. 缓存目录（如果存在且有 memory_prompt.txt）
    2. 插件安装目录 ~/.claude/plugins/marketplaces/nero-cc-marketplace/plugins/memory-stalker/prompts/

    Returns:
        dict: {
            "found": bool,
            "path": str,
            "source": str,  # "cache" | "installed" | "not_found"
            "all_paths": list  # 所有检查过的路径
        }
    """
    home = get_home_dir()
    claude_dir = home / ".claude"

    # 要检查的路径列表（按优先级排序）
    paths_to_check = []

    # 1. 缓存目录 - Claude Code 插件缓存位置
    # 需要检查带版本号和不带版本号的路径
    cache_base = claude_dir / "plugins" / "cache" / "nero-cc-marketplace" / "memory-stalker"

    # 先检查带版本号的目录（查找最新版本）
    versioned_cache = cache_base
    if cache_base.exists():
        # 查找版本号目录（如 1.0.5）
        version_dirs = [d for d in cache_base.iterdir() if d.is_dir() and d.name[0].isdigit()]
        if version_dirs:
            # 按版本号排序，取最新的
            version_dirs.sort(key=lambda x: [int(p) if p.isdigit() else 0 for p in x.name.split('.')], reverse=True)
            versioned_cache = version_dirs[0]

    cache_patterns = [
        # 带版本号的缓存目录（优先）
        versioned_cache / "prompts" / "memory_prompt.txt",
        # 不带版本号的缓存目录
        cache_base / "prompts" / "memory_prompt.txt",
    ]

    for cache_path in cache_patterns:
        paths_to_check.append(("cache", cache_path))

    # 2. 插件安装目录
    installed_path = claude_dir / "plugins" / "marketplaces" / "nero-cc-marketplace" / "plugins" / "memory-stalker" / "prompts" / "memory_prompt.txt"
    paths_to_check.append(("installed", installed_path))

    # 3. 备用：直接在 marketplaces 下
    alt_installed_path = claude_dir / "marketplaces" / "nero-cc-marketplace" / "plugins" / "memory-stalker" / "prompts" / "memory_prompt.txt"
    paths_to_check.append(("installed", alt_installed_path))

    # 检查每个路径
    all_paths = []
    for source, path in paths_to_check:
        all_paths.append(str(path))
        if path.exists():
            return {
                "found": True,
                "path": str(path),
                "source": source,
                "all_paths": all_paths
            }

    # 如果都不存在，返回安装目录路径（让用户可以创建）
    return {
        "found": False,
        "path": str(installed_path),
        "source": "not_found",
        "all_paths": all_paths,
        "suggested_path": str(installed_path)
    }


def main():
    """主函数"""
    # Windows 中文支持
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    result = find_prompt_file()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if result["found"] else 1


if __name__ == "__main__":
    sys.exit(main())
