#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""transcript.jsonl 解析器

提供对 Claude Code 会话记录的解析功能，支持提取：
- 完整对话历史
- 最后一轮交互
- 当前任务列表（TodoWrite 状态）

Memory Stalker - 记忆追猎者
"""

import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_transcript(file_path: str) -> List[dict]:
    """解析 transcript.jsonl 文件，返回所有记录

    Args:
        file_path: transcript.jsonl 文件路径

    Returns:
        List[dict]: 所有记录的列表，按时间顺序排列
    """
    records = []
    transcript_file = Path(file_path)

    if not transcript_file.exists():
        logger.error("Transcript file not found: %s", file_path)
        return records

    try:
        with open(transcript_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    records.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse line %d: %s", line_num, e)
                    continue
    except Exception as e:
        logger.error("Failed to read transcript file: %s", e)

    return records


def _extract_text_from_content(content, include_tool_results: bool = True) -> str:
    """从 message.content 中提取文本内容

    Args:
        content: message.content 字段，可能是字符串或列表
        include_tool_results: 是否包含工具结果，默认 True

    Returns:
        提取的文本内容
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif item.get("type") == "tool_result" and include_tool_results:
                    # 工具结果也包含文本
                    result_content = item.get("content", "")
                    if isinstance(result_content, str):
                        text_parts.append(f"[Tool Result]: {result_content[:500]}...")
            elif isinstance(item, str):
                text_parts.append(item)
        return "\n".join(text_parts)

    return ""


def _is_tool_result_only(content) -> bool:
    """检查 content 是否只包含 tool_result（没有真正的用户文本）

    Args:
        content: message.content 字段

    Returns:
        True 如果只包含 tool_result
    """
    if isinstance(content, str):
        return False

    if isinstance(content, list):
        has_text = False
        has_tool_result = False
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text = item.get("text", "").strip()
                    # 忽略空文本和系统提示
                    if text and not text.startswith("<"):
                        has_text = True
                elif item.get("type") == "tool_result":
                    has_tool_result = True
        return has_tool_result and not has_text

    return False


def _extract_tool_calls_from_content(content) -> List[dict]:
    """从 message.content 中提取工具调用

    Args:
        content: message.content 字段

    Returns:
        工具调用列表
    """
    tool_calls = []

    if not isinstance(content, list):
        return tool_calls

    for item in content:
        if isinstance(item, dict) and item.get("type") == "tool_use":
            tool_calls.append({
                "name": item.get("name", ""),
                "input": item.get("input", {})
            })

    return tool_calls


def get_last_interaction(records: List[dict]) -> Dict[str, str]:
    """提取最后一轮完整交互（用户输入 + 助手回复）

    逻辑:
    1. 从后向前遍历记录
    2. 找到最后一个 type="user" 的记录
    3. 收集该记录之后所有 type="assistant" 的记录
    4. 合并助手的多条回复（流式输出会产生多条记录）

    Args:
        records: 所有记录列表

    Returns:
        {
            "user_message": "用户的完整消息（纯文本）",
            "assistant_message": "助手的完整回复（合并多条）",
            "tool_calls": "工具调用描述",
            "timestamp": "时间戳"
        }
    """
    result = {
        "user_message": "",
        "assistant_message": "",
        "tool_calls": "",
        "timestamp": ""
    }

    # 找到最后一个真正的用户消息（不是纯 tool_result）
    last_user_idx = -1
    for i in range(len(records) - 1, -1, -1):
        if records[i].get("type") == "user":
            content = records[i].get("message", {}).get("content", "")
            # 跳过只包含 tool_result 的记录
            if not _is_tool_result_only(content):
                last_user_idx = i
                break

    if last_user_idx == -1:
        logger.warning("No user message found in transcript")
        return result

    # 提取用户消息（不包含 tool_result）
    user_record = records[last_user_idx]
    user_content = user_record.get("message", {}).get("content", "")
    result["user_message"] = _extract_text_from_content(user_content, include_tool_results=False)
    result["timestamp"] = user_record.get("timestamp", "")

    # 收集该用户消息之后的所有助手回复
    assistant_texts = []
    tool_calls_list = []

    for i in range(last_user_idx + 1, len(records)):
        record = records[i]
        if record.get("type") == "assistant":
            content = record.get("message", {}).get("content", [])
            text = _extract_text_from_content(content)
            if text.strip():
                assistant_texts.append(text)

            # 提取工具调用
            tools = _extract_tool_calls_from_content(content)
            tool_calls_list.extend(tools)

    # 合并助手回复（去重，因为流式输出可能有重复）
    seen_texts = set()
    unique_texts = []
    for text in assistant_texts:
        # 使用前100个字符作为去重key
        key = text[:100]
        if key not in seen_texts:
            seen_texts.add(key)
            unique_texts.append(text)

    result["assistant_message"] = "\n\n".join(unique_texts)

    # 格式化工具调用
    if tool_calls_list:
        tool_descriptions = []
        for tool in tool_calls_list:
            name = tool.get("name", "Unknown")
            # 不展开完整的 input，只显示工具名
            tool_descriptions.append(f"- {name}")
        result["tool_calls"] = "\n".join(tool_descriptions)

    return result


def get_current_todos(records: List[dict]) -> List[dict]:
    """提取最新的任务列表状态

    逻辑:
    1. 从后向前遍历记录
    2. 找到最后一个包含 TodoWrite 工具调用的 assistant 记录
    3. 提取 tool_use.input.todos

    Args:
        records: 所有记录列表

    Returns:
        [
            {"content": "任务1", "status": "completed", "activeForm": "..."},
            {"content": "任务2", "status": "in_progress", "activeForm": "..."},
            {"content": "任务3", "status": "pending", "activeForm": "..."}
        ]

        如果没有找到 TodoWrite 调用，返回空列表 []
    """
    for i in range(len(records) - 1, -1, -1):
        record = records[i]
        if record.get("type") != "assistant":
            continue

        content = record.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue

        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                if item.get("name") == "TodoWrite":
                    todos = item.get("input", {}).get("todos", [])
                    if todos:
                        logger.info("Found TodoWrite with %d todos", len(todos))
                        return todos

    logger.info("No TodoWrite found in transcript")
    return []


def extract_conversation_text(records: List[dict], max_chars: int = 50000) -> str:
    """提取对话文本（用于 AI 摘要生成）

    格式:
    User: 用户消息1

    Assistant: 助手回复1

    User: 用户消息2

    Assistant: 助手回复2
    ...

    Args:
        records: 所有记录
        max_chars: 最大字符数限制，超出则截断早期内容

    Returns:
        格式化的对话文本
    """
    conversation_parts = []

    for record in records:
        record_type = record.get("type", "")

        if record_type == "user":
            content = record.get("message", {}).get("content", "")
            text = _extract_text_from_content(content)
            if text.strip():
                conversation_parts.append(f"User: {text}")

        elif record_type == "assistant":
            content = record.get("message", {}).get("content", [])
            text = _extract_text_from_content(content)
            if text.strip():
                conversation_parts.append(f"Assistant: {text}")

    full_text = "\n\n".join(conversation_parts)

    # 如果超出限制，截断早期内容
    if len(full_text) > max_chars:
        logger.info("Truncating conversation from %d to %d chars", len(full_text), max_chars)
        # 保留后面的内容（更近期的对话）
        full_text = "... [早期对话已截断] ...\n\n" + full_text[-max_chars:]

    return full_text


def format_todos_markdown(todos: List[dict]) -> str:
    """将任务列表格式化为 Markdown

    格式:
    - [x] 已完成任务 (status=completed)
    - [ ] **进行中**: 任务名 (status=in_progress)
    - [ ] 待办任务 (status=pending)

    Args:
        todos: TodoWrite 的 todos 列表

    Returns:
        Markdown 格式的任务列表字符串
    """
    if not todos:
        return "无任务列表"

    lines = []
    for todo in todos:
        content = todo.get("content", "未知任务")
        status = todo.get("status", "pending")

        if status == "completed":
            lines.append(f"- [x] {content}")
        elif status == "in_progress":
            lines.append(f"- [ ] **进行中**: {content}")
        else:  # pending
            lines.append(f"- [ ] {content}")

    return "\n".join(lines)


def format_last_interaction(interaction: Dict[str, str]) -> str:
    """将最后一轮交互格式化为 Markdown

    Args:
        interaction: get_last_interaction() 的返回值

    Returns:
        Markdown 格式的交互内容
    """
    parts = []

    user_msg = interaction.get("user_message", "").strip()
    assistant_msg = interaction.get("assistant_message", "").strip()
    tool_calls = interaction.get("tool_calls", "").strip()

    parts.append("### 用户输入")
    if user_msg:
        # 使用代码块包裹，保持原格式
        parts.append("```")
        parts.append(user_msg)
        parts.append("```")
    else:
        parts.append("无")

    parts.append("")
    parts.append("### 助手回复")
    if assistant_msg:
        # 限制长度，避免过长
        if len(assistant_msg) > 5000:
            assistant_msg = assistant_msg[:5000] + "\n\n... [回复已截断] ..."
        parts.append("```")
        parts.append(assistant_msg)
        parts.append("```")
    else:
        parts.append("无")

    if tool_calls:
        parts.append("")
        parts.append("### 工具调用")
        parts.append(tool_calls)

    return "\n".join(parts)


# 测试代码
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python transcript_parser.py <transcript_path>")
        sys.exit(1)

    transcript_path = sys.argv[1]
    print(f"Parsing: {transcript_path}")

    records = parse_transcript(transcript_path)
    print(f"Total records: {len(records)}")

    print("\n--- Last Interaction ---")
    last = get_last_interaction(records)
    print(format_last_interaction(last))

    print("\n--- Current Todos ---")
    todos = get_current_todos(records)
    print(format_todos_markdown(todos))

    print("\n--- Conversation Text (first 1000 chars) ---")
    conv = extract_conversation_text(records, max_chars=1000)
    print(conv)
