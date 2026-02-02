# Memory Stalker - 记忆追猎者

> 让记忆无所遁形，无论散落在哪里都可以捞出来

Memory Stalker 是一个 Claude Code 记忆管理插件套件，提供智能压缩、可溯源存储和接续对话功能。

## 功能特性

| 功能 | 说明 |
|------|------|
| **PreCompact Hook** | 上下文压缩前自动保存记忆 |
| **增强压缩** | 保留最后一轮完整交互和当前任务列表 |
| **可溯源存储** | 每次压缩生成独立的记忆文件 |
| **接续对话** | 基于任意记忆文件恢复上下文 |
| **记忆浏览** | 交互式浏览和选择记忆文件 |

## 安装

### 通过 Marketplace 安装

```bash
# 1. 添加 Marketplace
/plugin marketplace add sekigaharaEI/nero-cc-marketplace

# 2. 安装插件
/plugin install memory-stalker@nero-cc-marketplace
```

### 手动安装

```bash
# 克隆仓库
git clone https://github.com/sekigaharaEI/nero-cc-marketplace.git

# 复制插件到 Claude Code 插件目录
cp -r nero-cc-marketplace/plugins/memory-stalker ~/.claude/plugins/
```

## 依赖

- Python 3.8+
- `anthropic>=0.18.0`

```bash
pip install anthropic>=0.18.0
```

## 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | 是* | - | API 密钥 |
| `ANTHROPIC_AUTH_TOKEN` | 是* | - | 替代 API 密钥（二选一） |
| `ANTHROPIC_BASE_URL` | 否 | - | 自定义 API 地址（支持代理） |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | 否 | `claude-sonnet-4-20250514` | 使用的模型 |

## 使用方法

### 自动保存记忆

插件会在以下情况自动保存记忆：
- 上下文自动压缩时
- 手动执行 `/compact` 命令时

记忆文件保存在: `{项目}/.claude/memories/`

### 接续对话

```bash
# 显示最近的记忆文件供选择
/resume

# 加载最新的记忆
/resume latest

# 按日期加载
/resume 20260129

# 按 session ID 加载
/resume ff246da3
```

### 浏览记忆

```bash
# 列出所有记忆文件
/memories
```

## 记忆文件格式

```markdown
# 会话记忆 - 2026-01-29 17:30:00

## 元数据
- Session ID: ff246da3-e969-4e32-aedc-3d096a93020a
- 项目路径: /path/to/project
- 生成时间: 2026-01-29 17:30:00
- 触发方式: auto

## 最后一轮完整交互

### 用户输入
{用户最后一条消息}

### 助手回复
{助手最后一条回复}

## 当前任务列表
- [x] 已完成任务
- [ ] **进行中**: 当前任务
- [ ] 待办任务

---

## AI 生成摘要

### 任务摘要
- 完成了 XXX

### 代码变更
| 文件 | 操作 | 说明 |
|------|------|------|

### 关键决策
- **决策**: XXX
  - **原因**: YYY

### 用户偏好
- 偏好1

### 待办/后续
- [ ] 后续任务
```

## 与 custom-compact 的关系

Memory Stalker 是 custom-compact 的完全升级版，包含其所有功能并大幅增强：

| 功能 | custom-compact | memory-stalker |
|------|----------------|----------------|
| PreCompact Hook | ✅ | ✅ |
| 基础压缩摘要 | ✅ | ✅ |
| 可溯源存储 | ✅ | ✅ |
| 保留最后一轮交互 | ❌ | ✅ |
| 保留任务列表 | ❌ | ✅ |
| /resume 接续对话 | ❌ | ✅ |
| /memories 记忆浏览 | ❌ | ✅ |

建议只启用其中一个插件，避免重复保存记忆。

## 文件结构

```
plugins/memory-stalker/
├── .claude-plugin/
│   └── plugin.json           # 插件元数据
├── hooks/
│   └── hooks.json            # PreCompact Hook 配置
├── skills/
│   ├── resume.md        # /resume 技能
│   └── memories.md      # /memories 技能
├── scripts/
│   ├── save_memory.py        # 记忆保存脚本
│   ├── list_memories.py      # 记忆列表脚本
│   └── transcript_parser.py  # transcript 解析器
├── prompts/
│   └── memory_prompt.txt     # AI 摘要提示词
└── README.md
```

## 日志

日志文件位置: `~/.claude/logs/memory_stalker.log`

```bash
# 查看日志
tail -f ~/.claude/logs/memory_stalker.log
```

## License

MIT
