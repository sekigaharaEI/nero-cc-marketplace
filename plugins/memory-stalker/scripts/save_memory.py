#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Memory Stalker - 记忆追猎者
让记忆无所遁形，无论散落在哪里都可以捞出来

PreCompact Hook 主脚本 - 增强版
继承 custom-compact 的基础功能，新增：
- 最后一轮完整交互的保留
- 当前任务列表的提取和保留

Compatible with Python 3.8+
"""

import json
import os
import sys
import io
import logging

# Windows 中文路径支持：强制 stdin 使用 UTF-8 编码
# Claude Code 传入的 JSON 数据是 UTF-8 编码的，但 Windows 默认使用 GBK
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 添加 scripts 目录到 path，以便导入 transcript_parser
sys.path.insert(0, str(Path(__file__).parent))

from transcript_parser import (
    parse_transcript,
    get_last_interaction,
    get_current_todos,
    extract_conversation_text,
    format_todos_markdown,
    format_last_interaction
)

# Setup logging
LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "memory_stalker.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


def get_plugin_root() -> Path:
    """Get the plugin root directory from environment variable."""
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        return Path(plugin_root)
    # Fallback to script directory's parent
    return Path(__file__).parent.parent


def get_api_config() -> dict:
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


def load_prompt_template() -> str:
    """Load the memory prompt template from the plugin's prompts directory."""
    plugin_root = get_plugin_root()
    prompt_file = plugin_root / "prompts" / "memory_prompt.txt"

    if not prompt_file.exists():
        logger.warning("Prompt template not found at %s, using default", prompt_file)
        return get_default_prompt()

    return prompt_file.read_text(encoding="utf-8")


def get_default_prompt() -> str:
    """Return the default prompt template if file is not found."""
    return """你是一个专业的会话记忆提取助手。请分析以下 Claude Code 会话记录，提取关键信息并生成结构化的记忆摘要。

## 输出格式要求

请严格按照以下 Markdown 格式输出（不要包含标题，直接从"任务摘要"开始）：

### 任务摘要
{列出本次会话完成的主要任务，使用列表格式，最多5条}
- 任务1
- 任务2

### 代码变更
{如果有代码变更，使用表格格式；如果没有，写"无"}
| 文件 | 操作 | 说明 |
|------|------|------|

### 关键决策
{记录重要的技术决策及其原因，最多3条}
- **决策**: 描述
  - **原因**: 原因

### 用户偏好
{提取用户表达的偏好、习惯、风格要求等，最多3条}
- 偏好1

### 待办/后续
{列出未完成的任务或后续需要处理的事项}
- [ ] 任务1

## 注意事项
- 只提取有价值的信息，忽略无关的对话
- 保持简洁，每个部分不超过 5 条
- 如果某个部分没有相关内容，写"无"
- 使用中文输出
- 不要重复"最后一轮交互"和"当前任务列表"中已有的内容"""


def generate_ai_summary(conversation_text: str, session_id: str, project_path: str, api_config: dict) -> Optional[str]:
    """Call Anthropic API to generate a memory summary.

    Args:
        conversation_text: 对话文本
        session_id: 会话 ID
        project_path: 项目路径
        api_config: API 配置

    Returns:
        AI 生成的摘要内容，失败返回 None
    """
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed. Run: pip install anthropic")
        return None

    prompt_template = load_prompt_template()

    # Build the user message
    user_message = f"""## 会话信息
- Session ID: {session_id}
- 项目路径: {project_path}

## 会话记录
{conversation_text}

请根据以上会话记录生成结构化的记忆摘要。注意：不要包含标题行，直接从"### 任务摘要"开始输出。"""

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


def assemble_memory_content(
    session_id: str,
    project_path: str,
    trigger: str,
    last_interaction: Dict[str, str],
    todos: List[dict],
    ai_summary: Optional[str]
) -> str:
    """组装完整的记忆文件内容

    Args:
        session_id: 会话 ID
        project_path: 项目路径
        trigger: 触发方式 (auto/manual)
        last_interaction: 最后一轮交互
        todos: 任务列表
        ai_summary: AI 生成的摘要

    Returns:
        完整的 Markdown 格式记忆内容
    """
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    parts = []

    # 标题
    parts.append(f"# 会话记忆 - {timestamp_str}")
    parts.append("")

    # 元数据
    parts.append("## 元数据")
    parts.append(f"- Session ID: {session_id}")
    parts.append(f"- 项目路径: {project_path}")
    parts.append(f"- 生成时间: {timestamp_str}")
    parts.append(f"- 触发方式: {trigger}")
    parts.append("")

    # 最后一轮完整交互
    parts.append("## 最后一轮完整交互")
    parts.append("")
    parts.append(format_last_interaction(last_interaction))
    parts.append("")

    # 当前任务列表
    parts.append("## 当前任务列表")
    parts.append(format_todos_markdown(todos))
    parts.append("")

    # 分隔线
    parts.append("---")
    parts.append("")

    # AI 生成摘要
    parts.append("## AI 生成摘要")
    parts.append("")
    if ai_summary:
        parts.append(ai_summary)
    else:
        parts.append("*AI 摘要生成失败*")

    return "\n".join(parts)


def save_memory(memory_content: str, project_path: str, session_id: str) -> Optional[Path]:
    """Save the memory content to a markdown file.

    Args:
        memory_content: 记忆内容
        project_path: 项目路径
        session_id: 会话 ID

    Returns:
        保存的文件路径，失败返回 None
    """
    memories_dir = Path(project_path) / ".claude" / "memories"
    memories_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Use first 8 chars of session_id for filename
    short_session_id = session_id[:8] if len(session_id) > 8 else session_id
    filename = f"{timestamp}_{short_session_id}.md"

    memory_file = memories_dir / filename

    try:
        memory_file.write_text(memory_content, encoding="utf-8")
        logger.info("Memory saved to: %s", memory_file)
        return memory_file
    except Exception as e:
        logger.error("Failed to save memory file: %s", e)
        return None


def main():
    """Main entry point for the Memory Stalker hook."""
    logger.info("Memory Stalker hook triggered")

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
    trigger = hook_input.get("trigger", "unknown")

    logger.info("Processing session: %s", session_id)
    logger.info("Transcript path: %s", transcript_path)
    logger.info("Project path: %s", project_path)
    logger.info("Trigger: %s", trigger)

    # Parse transcript
    records = parse_transcript(transcript_path)
    if not records:
        logger.warning("No records found in transcript")
        print(json.dumps({"continue": True}))
        return

    logger.info("Parsed %d records from transcript", len(records))

    # 提取关键信息
    last_interaction = get_last_interaction(records)
    todos = get_current_todos(records)
    conversation_text = extract_conversation_text(records, max_chars=50000)

    logger.info("Last interaction user message length: %d", len(last_interaction.get("user_message", "")))
    logger.info("Found %d todos", len(todos))
    logger.info("Conversation text length: %d", len(conversation_text))

    # Get API config and generate AI summary
    ai_summary = None
    try:
        api_config = get_api_config()
        ai_summary = generate_ai_summary(conversation_text, session_id, project_path, api_config)
    except ValueError as e:
        logger.warning("API config error: %s, skipping AI summary", e)
    except Exception as e:
        logger.warning("Failed to generate AI summary: %s", e)

    # 组装记忆内容
    memory_content = assemble_memory_content(
        session_id=session_id,
        project_path=project_path,
        trigger=trigger,
        last_interaction=last_interaction,
        todos=todos,
        ai_summary=ai_summary
    )

    # 保存记忆文件
    saved_path = save_memory(memory_content, project_path, session_id)
    if saved_path:
        logger.info("Memory successfully saved to %s", saved_path)
    else:
        logger.warning("Failed to save memory file")

    # Always output success to not block the compaction
    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
