# Custom Compact

在 Claude Code 上下文压缩（PreCompact）前，自动将当前会话的关键信息提取并保存为 Markdown 文件。

## 功能特性

- **自动触发**: 在上下文压缩前自动执行，无需手动操作
- **智能提取**: 使用 Claude API 智能分析对话，提取关键信息
- **结构化输出**: 生成格式统一的 Markdown 记忆文件
- **持久化存储**: 记忆文件保存在项目的 `.claude/memories/` 目录

## 记忆文件内容

每个记忆文件包含以下结构化信息：

- **会话信息**: Session ID、项目路径、生成时间
- **任务摘要**: 本次会话完成的主要任务
- **代码变更**: 文件创建、修改、删除记录
- **用户偏好**: 用户的习惯、风格要求
- **关键决策**: 重要的技术决策及其原因
- **待办/后续**: 未完成的任务和后续事项

## 安装

### 前置要求

- Python 3.8+
- Claude Code CLI
- Anthropic API Key

### 安装步骤

1. 添加 Marketplace（如果尚未添加）:

```bash
/plugin marketplace add sekigaharaEI/nero-cc-marketplace
```

2. 安装插件:

```bash
/plugin install custom-compact@nero-cc-marketplace
```

3. 安装 Python 依赖:

```bash
pip install anthropic>=0.18.0
```

4. 配置 API Key（选择以下任一方式）:

**方式一**: 设置环境变量
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

**方式二**: 添加到 shell 配置文件（~/.bashrc 或 ~/.zshrc）
```bash
echo 'export ANTHROPIC_API_KEY="your-api-key"' >> ~/.bashrc
source ~/.bashrc
```

## 配置选项

通过环境变量配置插件行为：

| 环境变量 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `ANTHROPIC_API_KEY` | 是* | - | Anthropic API 密钥 |
| `ANTHROPIC_AUTH_TOKEN` | 是* | - | 替代 API 密钥（二选一） |
| `ANTHROPIC_BASE_URL` | 否 | - | 自定义 API 地址（支持代理） |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | 否 | `claude-sonnet-4-20250514` | 使用的模型 |

*`ANTHROPIC_API_KEY` 和 `ANTHROPIC_AUTH_TOKEN` 二选一即可

## 使用方式

插件安装后会自动工作，无需手动操作。当 Claude Code 触发上下文压缩时：

1. 插件自动读取当前会话的对话记录
2. 调用 Claude API 生成结构化摘要
3. 将记忆文件保存到 `{项目}/.claude/memories/` 目录

### 记忆文件命名

```
{YYYYMMDD}_{HHMMSS}_{session_id前8位}.md
```

例如: `20250129_143052_a1b2c3d4.md`

### 查看记忆文件

```bash
# 列出所有记忆文件
ls .claude/memories/

# 查看最新的记忆文件
cat .claude/memories/$(ls -t .claude/memories/ | head -1)
```

## 日志

插件运行日志保存在 `~/.claude/logs/save_memory.log`，可用于调试：

```bash
tail -f ~/.claude/logs/save_memory.log
```

## 文件结构

```
custom-compact/
├── .claude-plugin/
│   └── plugin.json          # 插件清单
├── hooks/
│   └── hooks.json           # Hook 配置
├── scripts/
│   ├── save_memory.py       # 主脚本
│   └── memory_prompt.txt    # 提示词模板
└── README.md                # 本文件
```

## 自定义提示词

如需自定义记忆提取的提示词，可以编辑 `scripts/memory_prompt.txt` 文件。

## 故障排除

### 记忆文件未生成

1. 检查 API Key 是否正确配置
2. 查看日志文件 `~/.claude/logs/save_memory.log`
3. 确认 Python 依赖已安装

### API 调用失败

1. 检查网络连接
2. 如使用代理，确认 `ANTHROPIC_BASE_URL` 配置正确
3. 确认 API Key 有效且有足够配额

## 许可证

MIT License
