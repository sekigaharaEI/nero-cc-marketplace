#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""列出和搜索记忆文件

提供记忆文件的列表、搜索、解析功能，供 Skill 调用。

Memory Stalker - 记忆追猎者
"""

import re
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def get_memories_dir(project_path: str) -> Path:
    """获取记忆文件存储目录

    Args:
        project_path: 项目路径

    Returns:
        {project_path}/.claude/memories/
    """
    return Path(project_path) / ".claude" / "memories"


def parse_memory_filename(filename: str) -> Optional[Dict[str, str]]:
    """解析记忆文件名，提取日期和 session ID

    文件名格式: {YYYYMMDD}_{HHMMSS}_{session_id}.md

    Args:
        filename: 文件名

    Returns:
        {"date": "2026-01-29 17:30:00", "session_id": "ff246da3"} 或 None
    """
    # 匹配格式: 20260129_173000_ff246da3.md
    pattern = r"^(\d{8})_(\d{6})_([a-f0-9]+)\.md$"
    match = re.match(pattern, filename)

    if not match:
        return None

    date_str = match.group(1)  # 20260129
    time_str = match.group(2)  # 173000
    session_id = match.group(3)  # ff246da3

    try:
        dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        formatted_date = f"{date_str} {time_str}"

    return {
        "date": formatted_date,
        "session_id": session_id
    }


def parse_memory_file(file_path: str) -> dict:
    """解析记忆文件，提取元数据

    从记忆文件中提取：
    - 日期时间
    - Session ID
    - 任务数量
    - 摘要（第一个任务摘要条目）

    Args:
        file_path: 记忆文件路径

    Returns:
        元数据字典
    """
    path = Path(file_path)
    result = {
        "filename": path.name,
        "path": str(path),
        "date": "",
        "session_id": "",
        "summary": "",
        "task_count": 0,
        "size_bytes": 0
    }

    # 从文件名解析基本信息
    filename_info = parse_memory_filename(path.name)
    if filename_info:
        result["date"] = filename_info["date"]
        result["session_id"] = filename_info["session_id"]

    # 获取文件大小
    try:
        result["size_bytes"] = path.stat().st_size
    except Exception:
        pass

    # 读取文件内容提取更多信息
    try:
        content = path.read_text(encoding="utf-8")

        # 统计任务数量（匹配 - [x] 或 - [ ] 格式）
        task_pattern = r"^- \[[ x]\]"
        tasks = re.findall(task_pattern, content, re.MULTILINE)
        result["task_count"] = len(tasks)

        # 提取摘要（从"### 任务摘要"部分提取第一条）
        summary_match = re.search(r"### 任务摘要\n(.*?)(?=\n###|\n---|\Z)", content, re.DOTALL)
        if summary_match:
            summary_text = summary_match.group(1).strip()
            # 提取第一个列表项
            first_item = re.search(r"^- (.+)$", summary_text, re.MULTILINE)
            if first_item:
                result["summary"] = first_item.group(1)[:100]  # 限制长度

        # 如果没有找到摘要，尝试从标题提取
        if not result["summary"]:
            title_match = re.search(r"^# 会话记忆 - (.+)$", content, re.MULTILINE)
            if title_match:
                result["summary"] = f"会话记忆 - {title_match.group(1)}"

    except Exception as e:
        logger.warning("Failed to parse memory file %s: %s", file_path, e)

    return result


def list_memories(
    project_path: str,
    filter_pattern: str = None,
    limit: int = None
) -> List[dict]:
    """列出记忆文件

    Args:
        project_path: 项目路径
        filter_pattern: 过滤模式（日期、session ID 等）
        limit: 返回数量限制

    Returns:
        按时间倒序排列的记忆文件列表
    """
    memories_dir = get_memories_dir(project_path)

    if not memories_dir.exists():
        logger.info("Memories directory does not exist: %s", memories_dir)
        return []

    # 获取所有 .md 文件
    memory_files = list(memories_dir.glob("*.md"))

    if not memory_files:
        logger.info("No memory files found in %s", memories_dir)
        return []

    # 解析每个文件
    memories = []
    for file_path in memory_files:
        memory_info = parse_memory_file(str(file_path))
        memories.append(memory_info)

    # 按日期倒序排序
    memories.sort(key=lambda x: x.get("date", ""), reverse=True)

    # 应用过滤
    if filter_pattern:
        pattern_lower = filter_pattern.lower()
        memories = [
            m for m in memories
            if pattern_lower in m.get("date", "").lower()
            or pattern_lower in m.get("session_id", "").lower()
            or pattern_lower in m.get("filename", "").lower()
        ]

    # 应用数量限制
    if limit and limit > 0:
        memories = memories[:limit]

    return memories


def find_memory(project_path: str, target: str) -> Optional[dict]:
    """根据目标查找记忆文件

    target 可以是:
    - "latest": 最新的记忆文件
    - "20260129": 日期匹配（模糊匹配）
    - "ff246da3": session ID 匹配（前缀匹配）
    - 完整文件名

    Args:
        project_path: 项目路径
        target: 搜索目标

    Returns:
        匹配的记忆文件信息，未找到返回 None
    """
    if not target:
        return None

    target_lower = target.lower().strip()

    # 特殊处理 "latest"
    if target_lower == "latest":
        memories = list_memories(project_path, limit=1)
        return memories[0] if memories else None

    # 获取所有记忆文件
    memories = list_memories(project_path)

    if not memories:
        return None

    # 精确匹配文件名
    for m in memories:
        if m.get("filename", "").lower() == target_lower:
            return m
        if m.get("filename", "").lower() == f"{target_lower}.md":
            return m

    # 模糊匹配日期或 session ID
    for m in memories:
        # 日期匹配（支持 20260129 或 2026-01-29 格式）
        date_str = m.get("date", "").replace("-", "").replace(":", "").replace(" ", "")
        if target_lower.replace("-", "") in date_str:
            return m

        # Session ID 前缀匹配
        if m.get("session_id", "").lower().startswith(target_lower):
            return m

    return None


def format_memories_table(memories: List[dict]) -> str:
    """将记忆列表格式化为 Markdown 表格

    Args:
        memories: 记忆文件列表

    Returns:
        Markdown 表格字符串
    """
    if not memories:
        return "没有找到记忆文件。"

    lines = []
    lines.append("| # | 日期 | Session | 任务数 | 摘要 |")
    lines.append("|---|------|---------|--------|------|")

    for i, m in enumerate(memories, 1):
        date = m.get("date", "")[:16]  # 只显示到分钟
        session = m.get("session_id", "")[:8]
        task_count = m.get("task_count", 0)
        summary = m.get("summary", "")[:30]
        if len(m.get("summary", "")) > 30:
            summary += "..."

        lines.append(f"| {i} | {date} | {session} | {task_count} | {summary} |")

    return "\n".join(lines)


# 命令行接口
if __name__ == "__main__":
    import sys
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="List and search memory files")
    parser.add_argument("project_path", help="Project path")
    parser.add_argument("-f", "--filter", help="Filter pattern")
    parser.add_argument("-l", "--limit", type=int, help="Limit number of results")
    parser.add_argument("-t", "--target", help="Find specific memory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.target:
        # 查找特定记忆
        result = find_memory(args.project_path, args.target)
        if result:
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"Found: {result['filename']}")
                print(f"Date: {result['date']}")
                print(f"Session: {result['session_id']}")
                print(f"Tasks: {result['task_count']}")
                print(f"Path: {result['path']}")
        else:
            print(f"No memory found for target: {args.target}")
            sys.exit(1)
    else:
        # 列出记忆
        memories = list_memories(args.project_path, args.filter, args.limit)
        if args.json:
            print(json.dumps(memories, ensure_ascii=False, indent=2))
        else:
            print(format_memories_table(memories))
            print(f"\nTotal: {len(memories)} memory file(s)")
