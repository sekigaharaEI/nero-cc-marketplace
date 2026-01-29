#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Memory Saver - Claude Code Plugin
Automatically saves session memories before context compaction.

This script is triggered by the PreCompact hook and:
1. Reads the hook input from stdin (JSON with session_id, transcript_path, cwd)
2. Parses the transcript.jsonl to extract conversation content
3. Calls Anthropic API to generate a structured memory summary
4. Saves the memory to {project}/.claude/memories/{timestamp}_{session_id}.md

Compatible with Python 3.6+
"""

import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "save_memory.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


def get_plugin_root():
    """Get the plugin root directory from environment variable."""
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        return Path(plugin_root)
    # Fallback to script directory's parent
    return Path(__file__).parent.parent


def get_api_config():
    """Get Anthropic API configuration from environment variables."""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN environment variable is required")

    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    model = os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-20250514")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model
    }


def load_prompt_template():
    """Load the memory prompt template from the plugin's scripts directory."""
    plugin_root = get_plugin_root()
    prompt_file = plugin_root / "scripts" / "memory_prompt.txt"

    if not prompt_file.exists():
        logger.warning("Prompt template not found at %s, using default", prompt_file)
        return get_default_prompt()

    return prompt_file.read_text(encoding="utf-8")


def get_default_prompt():
    """Return the default prompt template if file is not found."""
    return """你是一个专业的会话记忆提取助手。请分析以下 Claude Code 会话记录，提取关键信息并生成结构化的记忆摘要。

## 输出格式要求

请严格按照以下 Markdown 格式输出：

# 会话记忆 - {当前日期时间}

## 会话信息
- Session ID: {从输入获取}
- 项目路径: {从输入获取}

## 任务摘要
{列出本次会话完成的主要任务，使用列表格式}

## 代码变更
{如果有代码变更，使用表格格式}
| 文件 | 操作 | 说明 |
|------|------|------|

## 用户偏好
{提取用户表达的偏好、习惯、风格要求等}

## 关键决策
{记录重要的技术决策及其原因}

## 待办/后续
{列出未完成的任务或后续需要处理的事项}
- [ ] 任务1
- [ ] 任务2

## 注意事项
- 只提取有价值的信息，忽略无关的对话
- 保持简洁，每个部分不超过 5 条
- 如果某个部分没有相关内容，可以写"无"
- 使用中文输出"""


def parse_transcript(transcript_path):
    """Parse the transcript.jsonl file and extract conversation messages."""
    messages = []
    transcript_file = Path(transcript_path)

    if not transcript_file.exists():
        logger.error("Transcript file not found: %s", transcript_path)
        return messages

    try:
        with open(transcript_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    messages.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse transcript line: %s", e)
                    continue
    except Exception as e:
        logger.error("Failed to read transcript file: %s", e)

    return messages


def extract_conversation_text(messages):
    """Extract readable conversation text from transcript messages."""
    conversation_parts = []

    for msg in messages:
        msg_type = msg.get("type", "")

        if msg_type == "user":
            content = msg.get("message", {}).get("content", "")
            if isinstance(content, str):
                conversation_parts.append("User: " + content)
            elif isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                if text_parts:
                    conversation_parts.append("User: " + " ".join(text_parts))

        elif msg_type == "assistant":
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                if text_parts:
                    conversation_parts.append("Assistant: " + " ".join(text_parts))
            elif isinstance(content, str):
                conversation_parts.append("Assistant: " + content)

    return "\n\n".join(conversation_parts)


def generate_memory_summary(conversation_text, session_id, project_path, api_config):
    """Call Anthropic API to generate a memory summary."""
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed. Run: pip install anthropic")
        return None

    prompt_template = load_prompt_template()

    # Build the user message
    user_message = """## 会话信息
- Session ID: {session_id}
- 项目路径: {project_path}

## 会话记录
{conversation_text}

请根据以上会话记录生成结构化的记忆摘要。""".format(
        session_id=session_id,
        project_path=project_path,
        conversation_text=conversation_text
    )

    try:
        client_kwargs = {"api_key": api_config["api_key"]}
        if api_config.get("base_url"):
            client_kwargs["base_url"] = api_config["base_url"]

        client = anthropic.Anthropic(**client_kwargs)

        response = client.messages.create(
            model=api_config["model"],
            max_tokens=4096,
            system=prompt_template,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        if response.content and len(response.content) > 0:
            return response.content[0].text

        logger.error("Empty response from API")
        return None

    except Exception as e:
        logger.error("API call failed: %s", e)
        return None


def save_memory(memory_content, project_path, session_id):
    """Save the memory content to a markdown file."""
    memories_dir = Path(project_path) / ".claude" / "memories"
    memories_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Use first 8 chars of session_id for filename
    short_session_id = session_id[:8] if len(session_id) > 8 else session_id
    filename = "{timestamp}_{session_id}.md".format(timestamp=timestamp, session_id=short_session_id)

    memory_file = memories_dir / filename

    try:
        memory_file.write_text(memory_content, encoding="utf-8")
        logger.info("Memory saved to: %s", memory_file)
        return memory_file
    except Exception as e:
        logger.error("Failed to save memory file: %s", e)
        return None


def main():
    """Main entry point for the memory saver hook."""
    logger.info("Memory Saver hook triggered")

    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse hook input: %s", e)
        # Output success to not block the compaction
        print(json.dumps({"continue": True}))
        return

    session_id = hook_input.get("session_id", "unknown")
    transcript_path = hook_input.get("transcript_path", "")
    project_path = hook_input.get("cwd", os.getcwd())

    logger.info("Processing session: %s", session_id)
    logger.info("Transcript path: %s", transcript_path)
    logger.info("Project path: %s", project_path)

    # Parse transcript
    messages = parse_transcript(transcript_path)
    if not messages:
        logger.warning("No messages found in transcript")
        print(json.dumps({"continue": True}))
        return

    # Extract conversation text
    conversation_text = extract_conversation_text(messages)
    if not conversation_text.strip():
        logger.warning("No conversation text extracted")
        print(json.dumps({"continue": True}))
        return

    # Limit conversation text to avoid token limits
    max_chars = 50000
    if len(conversation_text) > max_chars:
        logger.info("Truncating conversation text from %d to %d chars", len(conversation_text), max_chars)
        conversation_text = conversation_text[:max_chars] + "\n\n[... 对话内容已截断 ...]"

    # Get API config
    try:
        api_config = get_api_config()
    except ValueError as e:
        logger.error(str(e))
        print(json.dumps({"continue": True}))
        return

    # Generate memory summary
    memory_content = generate_memory_summary(
        conversation_text,
        session_id,
        project_path,
        api_config
    )

    if memory_content:
        saved_path = save_memory(memory_content, project_path, session_id)
        if saved_path:
            logger.info("Memory successfully saved to %s", saved_path)
    else:
        logger.warning("Failed to generate memory summary")

    # Always output success to not block the compaction
    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
