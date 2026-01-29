---
name: resume_nero
description: 基于记忆文件接续对话 - Memory Stalker 记忆追猎者
user_invocable: true
---

<resume_nero>

# Resume Nero - 接续对话

根据用户指定的记忆文件恢复上下文，实现跨会话的连续性。

## 使用方式

| 命令 | 说明 |
|------|------|
| `/resume_nero` | 显示最近 5 个记忆文件供选择 |
| `/resume_nero latest` | 加载最新记忆 |
| `/resume_nero 20260129` | 按日期匹配 |
| `/resume_nero ff246da3` | 按 session ID 匹配 |

## 执行指令

当用户调用此 Skill 时，请按以下步骤执行：

### 步骤 1: 获取参数

从用户输入中提取 target 参数（如果有）。参数可能是：
- 空（显示列表供选择）
- `latest`（加载最新）
- 日期（如 `20260129`）
- session ID（如 `ff246da3`）
- 完整文件名

### 步骤 2: 查找记忆文件

使用 Bash 工具运行以下命令查找记忆文件：

如果有 target 参数：
```bash
python ${CLAUDE_PROJECT_DIR}/plugins/memory-stalker/scripts/list_memories.py "${CLAUDE_PROJECT_DIR}" -t "<target>" --json
```

如果没有 target 参数（列出最近 5 个）：
```bash
python ${CLAUDE_PROJECT_DIR}/plugins/memory-stalker/scripts/list_memories.py "${CLAUDE_PROJECT_DIR}" -l 5 --json
```

注意：如果插件是通过 marketplace 安装的，脚本路径可能在 `~/.claude/plugins/memory-stalker/scripts/` 下。

### 步骤 3: 处理结果

**如果找到单个记忆文件：**
1. 使用 Read 工具读取记忆文件内容
2. 向用户展示记忆摘要
3. 使用 AskUserQuestion 询问用户是否继续之前的任务

**如果找到多个记忆文件：**
1. 使用 AskUserQuestion 让用户选择要加载的记忆
2. 读取选中的记忆文件
3. 展示内容并询问是否继续

**如果没有找到记忆文件：**
告知用户没有找到匹配的记忆文件，并建议使用 `/memories_nero` 查看所有可用记忆。

### 步骤 4: 展示记忆内容

加载记忆后，向用户展示以下信息：

```markdown
## 已加载记忆: {文件名}

**日期**: {日期}
**Session ID**: {session_id}
**项目路径**: {项目路径}

### 最后一轮交互摘要
{简要展示最后一轮交互的内容}

### 当前任务列表
{展示任务列表}

### 关键上下文
{展示重要上下文信息}
```

### 步骤 5: 询问后续操作

使用 AskUserQuestion 询问用户：

```
已加载记忆文件，你想要：
1. 继续未完成的任务
2. 查看完整记忆内容
3. 加载其他记忆文件
4. 开始新的任务
```

## 注意事项

- 如果项目目录下没有 `.claude/memories/` 目录，说明还没有保存过记忆
- 记忆文件是 Markdown 格式，可以直接读取和展示
- 优先展示"最后一轮交互"和"当前任务列表"，这是最重要的上下文信息

</resume_nero>
