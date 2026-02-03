# Memory Stalker 初始化向导

检测当前环境并引导用户完成 Memory Stalker 插件的配置。

## 执行步骤

### 1. 检测 Python 环境

运行环境检测脚本：

```bash
python "${CLAUDE_PROJECT_DIR}/plugins/memory-stalker/scripts/check_env.py"
```

### 2. 分析检测结果

根据脚本输出的 JSON 结果，分析以下内容：

- `python_ok`: Python 版本是否满足要求 (>=3.8)
- `anthropic_ok`: anthropic 包是否已安装且版本正确 (>=0.18.0)
- `api_key_ok`: API 密钥是否已配置
- `errors`: 错误信息列表
- `warnings`: 警告信息列表

### 3. 展示检测结果

以清晰的格式展示检测结果：

```
## 环境检测结果

| 检测项 | 状态 | 说明 |
|--------|------|------|
| Python 版本 | ✅/❌ | {python_version} |
| anthropic 包 | ✅/❌ | {anthropic_version 或 未安装} |
| API 密钥 | ✅/❌ | {已配置/未配置} |
```

### 4. 引导安装缺失依赖

如果有检测项未通过，按以下顺序引导用户：

#### 4.1 Python 未安装或版本过低

```
Python 版本不满足要求，需要 Python 3.8 或更高版本。

请访问 https://www.python.org/downloads/ 下载安装 Python 3.8+
```

#### 4.2 anthropic 包未安装

询问用户是否自动安装：

```
anthropic 包未安装，是否现在安装？
```

选项：
- **自动安装 (推荐)**: 执行 `pip install anthropic>=0.18.0`
- **手动安装**: 显示安装命令让用户自行执行
- **跳过**: 稍后手动安装

如果用户选择自动安装，执行：

```bash
pip install anthropic>=0.18.0
```

#### 4.3 API 密钥未配置

```
API 密钥未配置。Memory Stalker 需要 Anthropic API 密钥来生成 AI 摘要。

请设置以下环境变量之一：
- ANTHROPIC_API_KEY: 你的 Anthropic API 密钥
- ANTHROPIC_AUTH_TOKEN: 替代的认证令牌

获取 API 密钥: https://console.anthropic.com/

可选配置：
- ANTHROPIC_BASE_URL: 自定义 API 地址（支持代理服务）
- ANTHROPIC_DEFAULT_SONNET_MODEL: 自定义模型（默认 claude-sonnet-4-20250514）
```

### 5. 所有检测通过后，展示使用指南

```
## 🎉 Memory Stalker 已就绪！

### 自动记忆保存
插件会在上下文压缩时自动保存记忆，无需手动操作。
记忆文件保存在: `{项目}/.claude/memories/`

### 可用命令

| 命令 | 说明 |
|------|------|
| `/resume` | 接续上次对话，显示最近 5 个记忆供选择 |
| `/resume latest` | 直接加载最新的记忆 |
| `/resume 20260129` | 按日期加载记忆 |
| `/memories` | 交互式浏览所有记忆文件 |
| `/edit-memory-prompt` | 编辑记忆摘要提示词 |

### 查看日志

如果遇到问题，可以查看日志文件：
- Windows: `%USERPROFILE%\.claude\logs\memory_stalker.log`
- macOS/Linux: `~/.claude/logs/memory_stalker.log`
```

### 6. 展示当前摘要提示词并询问是否修改

运行提示词路径查找脚本：

```bash
python "${CLAUDE_PROJECT_DIR}/plugins/memory-stalker/scripts/find_prompt_path.py"
```

根据返回结果：

#### 6.1 如果找到提示词文件 (found = true)

读取提示词文件内容（使用 Read 工具读取 `path` 指向的文件），然后展示完整内容：

```
## 当前记忆摘要提示词

**文件位置**: {path}
**来源**: {source === "cache" ? "缓存目录" : "插件安装目录"}

### 提示词内容

{完整的提示词内容}

---
```

#### 6.2 如果未找到提示词文件 (found = false)

```
## 记忆摘要提示词

当前使用内置默认提示词。
```

### 7. 询问后续操作

使用 AskUserQuestion 询问用户：

```
初始化完成！接下来你想做什么？
```

选项：
- **修改摘要提示词**: 执行 `/edit-memory-prompt` 命令
- **查看记忆文件**: 执行 `/memories` 命令
- **接续上次对话**: 执行 `/resume` 命令
- **开始新任务**: 结束初始化向导
