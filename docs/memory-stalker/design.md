# Memory-Stalker 插件详细设计文档

> **记忆追猎者：让记忆无所遁形，无论散落在哪里都可以捞出来**

> 版本: 1.0.0
> 作者: Nero
> 创建日期: 2026-01-29

## 1. 概述

Memory-Stalker 是一个 Claude Code 记忆管理插件套件，整合了 custom-compact 的基础功能并大幅增强，提供以下核心功能：

### 核心功能

| 功能模块 | 说明 | 来源 |
|----------|------|------|
| **PreCompact Hook** | 上下文压缩前自动保存记忆 | 继承自 custom-compact |
| **增强压缩** | 保留最后一轮完整交互和当前任务列表 | 新增 |
| **可溯源存储** | 每次压缩生成独立的记忆文件 | 继承自 custom-compact |
| **接续对话** | 基于任意记忆文件恢复上下文 | 新增 |
| **记忆浏览** | 交互式浏览和选择记忆文件 | 新增 |

### 设计理念

- **无所遁形**: 自动捕获压缩前的关键信息，不丢失重要上下文
- **可追溯**: 每次压缩都有迹可循，支持回溯任意历史记忆
- **可接续**: 基于任意记忆文件恢复对话，实现跨会话的连续性

## 2. 项目结构

```
plugins/memory-stalker/
├── .claude-plugin/
│   └── plugin.json                 # 插件元数据
├── hooks/
│   └── hooks.json                  # Hook 配置 (PreCompact)
├── skills/
│   ├── resume.md              # /resume 技能定义
│   └── memories.md            # /memories 技能定义
├── scripts/
│   ├── save_memory.py              # PreCompact Hook 主脚本 (增强版)
│   ├── list_memories.py            # 列出记忆文件
│   └── transcript_parser.py        # transcript.jsonl 解析器
├── prompts/
│   └── memory_prompt.txt           # AI 摘要生成提示词
└── README.md
```

## 3. 技术背景

### 3.1 transcript.jsonl 文件

Claude Code 会话记录存储在 `~/.claude/projects/{project-hash}/{session-id}.jsonl`，格式为 JSONL（每行一个 JSON 对象）。

**文件位置示例：**
```
~/.claude/projects/-data-zyw-nero-cc-marketplace/ff246da3-e969-4e32-aedc-3d096a93020a.jsonl
```

**记录类型：**

| type 字段 | 说明 |
|-----------|------|
| `queue-operation` | 队列操作记录 |
| `file-history-snapshot` | 文件历史快照 |
| `user` | 用户消息 |
| `assistant` | 助手回复（包括工具调用） |

**用户消息示例：**
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [
      {"type": "text", "text": "用户输入的内容"}
    ]
  },
  "uuid": "8e091f32-6597-4bd2-8bc9-481e8f0c2fbb",
  "timestamp": "2026-01-29T08:32:19.408Z"
}
```

**助手回复示例（包含工具调用）：**
```json
{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      {"type": "text", "text": "助手的回复内容"},
      {
        "type": "tool_use",
        "name": "TodoWrite",
        "input": {
          "todos": [
            {"content": "任务1", "status": "completed", "activeForm": "..."},
            {"content": "任务2", "status": "in_progress", "activeForm": "..."}
          ]
        }
      }
    ]
  },
  "uuid": "eae58ac0-5f95-487e-9c69-6d66e4066938",
  "timestamp": "2026-01-29T08:32:27.623Z"
}
```

### 3.2 PreCompact Hook 输入

Hook 通过 stdin 接收 JSON 数据：

```json
{
  "session_id": "ff246da3-e969-4e32-aedc-3d096a93020a",
  "transcript_path": "/root/.claude/projects/-data-zyw-nero-cc-marketplace/ff246da3-e969-4e32-aedc-3d096a93020a.jsonl",
  "cwd": "/data/zyw/nero-cc-marketplace",
  "trigger": "auto",
  "hook_event_name": "PreCompact"
}
```

| 字段 | 说明 |
|------|------|
| `session_id` | 当前会话 ID |
| `transcript_path` | transcript.jsonl 文件的完整路径 |
| `cwd` | 当前工作目录（项目路径） |
| `trigger` | 触发方式：`auto`（自动）或 `manual`（手动 /compact） |

## 4. 核心模块设计

### 4.1 transcript_parser.py - 解析器模块

```python
"""transcript.jsonl 解析器

提供对 Claude Code 会话记录的解析功能，支持提取：
- 完整对话历史
- 最后一轮交互
- 当前任务列表（TodoWrite 状态）
"""

from typing import List, Dict, Optional
import json

def parse_transcript(file_path: str) -> List[dict]:
    """解析 transcript.jsonl 文件，返回所有记录

    Args:
        file_path: transcript.jsonl 文件路径

    Returns:
        List[dict]: 所有记录的列表，按时间顺序排列
    """
    pass

def get_last_interaction(records: List[dict]) -> Dict[str, str]:
    """提取最后一轮完整交互（用户输入 + 助手回复）

    逻辑:
    1. 从后向前遍历记录
    2. 找到最后一个 type="user" 的记录
    3. 收集该记录之后所有 type="assistant" 的记录
    4. 合并助手的多条回复（流式输出会产生多条记录）

    Returns:
        {
            "user_message": "用户的完整消息（纯文本）",
            "assistant_message": "助手的完整回复（合并多条，包含文本和工具调用描述）",
            "timestamp": "2026-01-29T08:32:19.408Z"
        }
    """
    pass

def get_current_todos(records: List[dict]) -> List[dict]:
    """提取最新的任务列表状态

    逻辑:
    1. 从后向前遍历记录
    2. 找到最后一个包含 TodoWrite 工具调用的 assistant 记录
    3. 提取 tool_use.input.todos

    Returns:
        [
            {"content": "任务1", "status": "completed", "activeForm": "..."},
            {"content": "任务2", "status": "in_progress", "activeForm": "..."},
            {"content": "任务3", "status": "pending", "activeForm": "..."}
        ]

    如果没有找到 TodoWrite 调用，返回空列表 []
    """
    pass

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
    pass
```

### 4.2 save_memory.py - 增强版压缩脚本

```python
"""PreCompact Hook 主脚本 - 增强版

继承 custom-compact 的基础功能，新增：
- 最后一轮完整交互的保留
- 当前任务列表的提取和保留
"""

import json
import sys
from typing import List, Dict
from transcript_parser import (
    parse_transcript,
    get_last_interaction,
    get_current_todos,
    extract_conversation_text
)

def main():
    """主流程

    1. 读取 Hook 输入 (stdin)
    2. 解析 transcript.jsonl
    3. 提取关键信息:
       - 最后一轮完整交互 (直接写入，不经过 AI)
       - 当前任务列表 (直接写入，不经过 AI)
       - 对话文本 (用于 AI 生成摘要)
    4. 调用 AI 生成摘要部分
    5. 组装完整记忆内容
    6. 保存到 {project}/.claude/memories/
    7. 输出 {"continue": true} 确保压缩流程继续
    """
    pass

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
    pass

def format_last_interaction(interaction: Dict[str, str]) -> str:
    """将最后一轮交互格式化为 Markdown

    Args:
        interaction: get_last_interaction() 的返回值

    Returns:
        Markdown 格式的交互内容
    """
    pass

def generate_ai_summary(conversation_text: str, api_config: dict) -> str:
    """调用 AI 生成摘要

    Args:
        conversation_text: 对话文本
        api_config: API 配置（key, base_url, model）

    Returns:
        AI 生成的摘要内容（Markdown 格式）
    """
    pass

def assemble_memory_content(
    session_id: str,
    project_path: str,
    trigger: str,
    last_interaction: Dict[str, str],
    todos: List[dict],
    ai_summary: str
) -> str:
    """组装完整的记忆文件内容

    Returns:
        完整的 Markdown 格式记忆内容
    """
    pass
```

### 4.3 list_memories.py - 记忆文件列表

```python
"""列出和搜索记忆文件

提供记忆文件的列表、搜索、解析功能，供 Skill 调用。
"""

from typing import List, Dict, Optional
from pathlib import Path

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
        按时间倒序排列的记忆文件列表:
        [
            {
                "filename": "20260129_173000_ff246da3.md",
                "path": "/data/zyw/project/.claude/memories/20260129_173000_ff246da3.md",
                "date": "2026-01-29 17:30:00",
                "session_id": "ff246da3",
                "summary": "第一行摘要内容...",
                "task_count": 5,
                "size_bytes": 4096
            },
            ...
        ]
    """
    pass

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
    pass

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
    pass

def get_memories_dir(project_path: str) -> Path:
    """获取记忆文件存储目录

    Returns:
        {project_path}/.claude/memories/
    """
    return Path(project_path) / ".claude" / "memories"
```

## 5. Skill 定义

### 5.1 /resume - 接续对话

**文件: skills/resume.md**

```markdown
---
name: resume
description: 基于记忆文件接续对话 - Memory Stalker
arguments:
  - name: target
    description: 文件名、日期、session ID 或 "latest"
    required: false
---

# Resume 技能

根据用户指定的记忆文件恢复上下文，实现跨会话的连续性。

## 使用方式

| 命令 | 说明 |
|------|------|
| `/resume` | 显示最近 5 个记忆文件供选择 |
| `/resume latest` | 加载最新记忆 |
| `/resume 20260129` | 按日期匹配 |
| `/resume ff246da3` | 按 session ID 匹配 |

## 执行逻辑

1. 解析用户输入的 target 参数
2. 调用 list_memories.py 获取匹配的记忆文件
3. 如果有多个匹配，使用 AskUserQuestion 让用户选择
4. 读取选中的记忆文件内容
5. 将内容作为上下文展示给用户
6. 询问用户是否继续之前的任务

## 输出格式

加载记忆后，向用户展示：
- 记忆文件的基本信息（日期、Session ID）
- 最后一轮交互摘要
- 当前任务列表状态
- 询问是否继续未完成的任务
```

### 5.2 /memories - 记忆浏览

**文件: skills/memories.md**

```markdown
---
name: memories
description: 交互式浏览和选择记忆文件 - Memory Stalker
---

# Memories 技能

列出所有可用的记忆文件，让用户选择要加载的记忆。

## 使用方式

| 命令 | 说明 |
|------|------|
| `/memories` | 列出所有记忆文件 |

## 执行逻辑

1. 调用 list_memories.py 获取所有记忆文件
2. 以表格形式显示列表：

| # | 日期 | Session | 任务数 | 摘要 |
|---|------|---------|--------|------|
| 1 | 2026-01-29 17:30 | ff246da3 | 5 | 完成了 XXX... |
| 2 | 2026-01-29 15:00 | abc12345 | 3 | 实现了 YYY... |

3. 使用 AskUserQuestion 让用户选择
4. 加载选中的记忆文件内容
```

## 6. 记忆文件格式

```markdown
# 会话记忆 - 2026-01-29 17:30:00

## 元数据
- Session ID: ff246da3-e969-4e32-aedc-3d096a93020a
- 项目路径: /data/zyw/nero-cc-marketplace
- 生成时间: 2026-01-29 17:30:00
- 触发方式: auto

## 最后一轮完整交互

### 用户输入
```
{用户最后一条消息的原始内容，保持原格式}
```

### 助手回复
```
{助手最后一条回复的原始内容，包括代码块、工具调用结果等}
```

## 当前任务列表
- [x] 已完成任务1
- [x] 已完成任务2
- [ ] **进行中**: 任务3
- [ ] 待办任务4
- [ ] 待办任务5

---

## AI 生成摘要

### 任务摘要
- 完成了 XXX 功能的开发
- 实现了 YYY 模块

### 代码变更
| 文件 | 操作 | 说明 |
|------|------|------|
| src/main.py | 创建 | 主入口文件 |
| src/utils.py | 修改 | 添加辅助函数 |

### 关键决策
- **决策**: 使用 XXX 方案
  - **原因**: 因为 YYY

### 用户偏好
- 偏好使用中文注释
- 喜欢简洁的代码风格

### 待办/后续
- [ ] 完成单元测试
- [ ] 更新文档
```

## 7. Hook 配置

**hooks/hooks.json:**

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": ["auto", "manual"],
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/scripts/save_memory.py",
            "timeout": 120000
          }
        ]
      }
    ]
  }
}
```

**配置说明：**

| 字段 | 值 | 说明 |
|------|-----|------|
| `matcher` | `["auto", "manual"]` | 同时响应自动压缩和手动 /compact |
| `timeout` | `120000` | 超时时间 120 秒（需要调用 AI 生成摘要） |
| `${CLAUDE_PLUGIN_ROOT}` | 自动替换 | Claude Code 自动设置的插件根目录 |

## 8. 插件元数据

**plugin.json:**

```json
{
  "name": "memory-stalker",
  "description": "记忆追猎者 - 让记忆无所遁形，无论散落在哪里都可以捞出来。智能压缩、可溯源存储、接续对话。",
  "version": "1.0.0",
  "author": {
    "name": "Nero"
  },
  "license": "MIT",
  "repository": "https://github.com/sekigaharaEI/nero-cc-marketplace",
  "keywords": [
    "memory",
    "stalker",
    "context",
    "compaction",
    "resume",
    "productivity",
    "automation"
  ]
}
```

## 9. 开发计划

| 阶段 | 任务 | 依赖 | 状态 |
|------|------|------|------|
| **Phase 1** | transcript_parser.py | 无 | 待开发 |
| **Phase 2** | save_memory.py (增强版) | Phase 1 | 待开发 |
| **Phase 3** | list_memories.py | 无 | 待开发 |
| **Phase 4** | /resume Skill | Phase 3 | 待开发 |
| **Phase 5** | /memories Skill | Phase 3, 4 | 待开发 |
| **Phase 6** | 测试和文档 | 全部 | 待开发 |

## 10. 依赖项

**Python 依赖:**
- Python 3.8+
- `anthropic>=0.18.0`

**环境变量:**

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | 是* | - | API 密钥 |
| `ANTHROPIC_AUTH_TOKEN` | 是* | - | 替代 API 密钥（二选一） |
| `ANTHROPIC_BASE_URL` | 否 | - | 自定义 API 地址（支持代理） |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | 否 | `claude-sonnet-4-20250514` | 使用的模型 |

## 11. 与 custom-compact 的关系

Memory-Stalker 是 custom-compact 的**完全升级版**，包含其所有功能并大幅增强：

| 功能 | custom-compact | memory-stalker |
|------|----------------|----------------|
| PreCompact Hook | ✅ | ✅ |
| 基础压缩摘要 | ✅ | ✅ |
| 可溯源存储 | ✅ | ✅ |
| 保留最后一轮交互 | ❌ | ✅ |
| 保留任务列表 | ❌ | ✅ |
| /resume 接续对话 | ❌ | ✅ |
| /memories 记忆浏览 | ❌ | ✅ |

**迁移建议：**
- 保留 custom-compact 作为历史版本和简化版选择
- memory-stalker 作为功能完整的新插件独立发布
- 两者可以共存，但建议只启用其中一个以避免重复保存

## 12. 存储位置

记忆文件存储在项目级别：

```
{project}/.claude/memories/
├── 20260129_173000_ff246da3.md
├── 20260129_150000_abc12345.md
└── ...
```

**文件命名规则：**
```
{YYYYMMDD}_{HHMMSS}_{session_id前8位}.md
```

**优点：**
- 记忆与项目绑定，便于管理
- 支持 Git 版本控制（可选择是否提交）
- 不同项目的记忆相互隔离
