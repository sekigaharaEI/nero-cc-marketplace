# Nero's Claude Code Marketplace

个人的 Claude Code 插件市场，用于存放和分发自己开发的各种 Claude Code 插件。

## 快速开始

### 添加 Marketplace

```bash
/plugin marketplace add sekigaharaEI/nero-cc-marketplace
```

### 添加 Marketplace（jty内网）

```bash
# 需要开通jty git账号

/plugin marketplace add http://username:password@192.168.4.93/zyw23973/jtyjy-cc-marketplace.git
```

### 查看可用插件

```bash
/plugin list --marketplace nero-cc-marketplace
```

### 安装插件

```bash
/plugin install {plugin-name}@nero-cc-marketplace
```

## 可用插件

| 插件名称                                   | 版本  | 描述                                        |
| ------------------------------------------ | ----- | ------------------------------------------- |
| [memory-stalker](./plugins/memory-stalker/)   | 1.0.6 | 记忆追猎者 - 智能压缩、可溯源存储、接续对话 |
| [tt-pm-master](./plugins/tt-pm-master/) | 1.0.2 | Teacher Tui产品经理大师 - 专业的产品经理工具集     |
| [feishu-bridge](./plugins/feishu-bridge/) | 1.0.3 | 飞书消息桥 - 通过飞书开放平台发送私聊通知消息 |
| [tmux-pane-router](./plugins/tmux-pane-router/) | 1.0.0 | Tmux三分屏路由器 - Bash命令路由到右上pane，Agent活动展示在右下pane |

## 插件详情

### memory-stalker

记忆追猎者 - 让记忆无所遁形。智能压缩会话记忆，支持可溯源存储和接续对话。

**功能特性:**

- 🎯 智能记忆压缩与存储
- 📂 交互式记忆文件浏览与选择
- 🔄 基于记忆文件接续对话
- 📝 结构化 Markdown 输出

**安装:**

```bash
/plugin install memory-stalker@nero-cc-marketplace
```

**命令:**

| 命令 | 说明 |
|------|------|
| `/init` | 初始化向导，检测环境并完成配置 |
| `/memories` | 列出所有记忆文件，交互式浏览和选择 |
| `/resume [参数]` | 基于记忆文件接续对话，支持 `latest`、日期、session ID |
| `/edit-memory-prompt` | 编辑 AI 摘要提示词，自定义摘要格式 |
| `/commit` | 提交命令 |

**钩子:**

| 钩子 | 说明 |
|------|------|
| PreCompact Hook | 上下文压缩前自动保存记忆，手动执行 `/compact` 或自动 compact 时触发 |

[查看详细文档](./plugins/memory-stalker/README.md)

### tt-pm-master

Teacher Tui产品经理大师 - 专业的产品经理工具集，以Teacher Tui式犀利风格提供产品管理全流程支持。

**功能特性:**

- 📱 竞品分析：根据 APP 截图反向分析产品功能、商业模式及资源投入
- 📋 PRD 撰写：编写高质量的产品需求文档
- 💼 商业模式规划：生成针对总经理汇报的新项目商业模式规划方案
- 🔍 产品评审：模拟产品评审委员会进行深度评审
- 💬 评审意见处理：智能处理和答复评审团队的意见
- 📦 会话存档与恢复：支持工作进度的持久化存储
- 🎙️ NotebookLM 集成：完整的 Google NotebookLM API 支持，生成播客、视频、幻灯片等
- 📊 文档转幻灯片：将本地文档自动上传到 NotebookLM 并生成幻灯片 PDF
- 📝 长文本分块写入：支持超长文本的分块写入，避免 token 限制

**安装:**

```bash
/plugin install tt-pm-master@nero-cc-marketplace
```

**使用:**

```bash
/help                    # 查看所有可用命令
/pm-analyze-competitor   # 竞品分析
/pm-write-prd           # 撰写 PRD
/pm-plan-business-model # 商业模式规划
/pm-review-product      # 产品评审
/pm-response-review     # 评审意见处理
/notebooklm             # NotebookLM 自动化
/doc-to-slides          # 文档转幻灯片
```

[查看详细文档](./plugins/tt-pm-master/README.md)

### feishu-bridge

飞书消息桥 - 通过飞书开放平台发送私聊通知消息。支持 AI 自动调用和手动配置。

**功能特性:**

- 🚀 简单易用：一行命令发送飞书通知
- 🔐 灵活配置：支持环境变量和配置文件两种方式
- 💬 私聊通知：向个人发送文本消息
- 🔄 自动调用：AI 可根据需要自动发送通知
- 🛡️ 安全可靠：Token 自动缓存和刷新

**安装:**

```bash
/plugin install feishu-bridge@nero-cc-marketplace
```

**快速开始:**

1. 运行配置向导：`/feishu-setup`
2. 按照指引创建飞书应用并配置凭证
3. AI 即可自动发送飞书通知

**Skills:**

| Skill | 说明 |
|------|------|
| `feishu-send-notification` | 教 AI 如何发送飞书通知消息 |
| `feishu-setup` | 安装和配置引导(仅用户手动调用) |

[查看详细文档](./plugins/feishu-bridge/README.md)

### tmux-pane-router

Tmux三分屏路由器 - 在 tmux 中创建三格布局，利用 PreToolUse Hook 将 Bash 命令路由到右上 pane 实际执行，将 Agent 启动信息展示到右下 pane。

**功能特性:**

- 🖥️ 一键创建三分屏布局（左主窗口 + 右上Bash + 右下Agent）
- ⚡ Bash 命令在右上 pane 真实执行，输出自动回传给 Claude
- 🤖 Agent 启动时右下 pane 实时显示任务摘要和类型
- 🔧 配置持久化，重连后只需重新运行 `/tmux-setup`

**安装:**

```bash
/plugin install tmux-pane-router@nero-cc-marketplace
```

**命令:**

| 命令 | 说明 |
|------|------|
| `/tmux-setup` | 在当前 tmux window 创建三分屏，保存 pane 配置 |
| `/tmux-status` | 查看 pane 配置状态，确认各 pane 是否存活 |

**快速开始:**

```bash
# 方式一：在现有 tmux 中
claude  # 启动 Claude Code
/tmux-setup  # 在 Claude 内运行

# 方式二：从普通终端一键启动
bash ~/.claude/plugins/tmux-pane-router/scripts/setup_layout.sh --new
```

[查看详细文档](./plugins/tmux-pane-router/README.md)

## 仓库结构

```
nero-cc-marketplace/
├── .claude-plugin/
│   └── marketplace.json        # Marketplace 清单
├── plugins/
│   ├── memory-stalker/         # Memory Stalker 插件
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── commands/
│   │   ├── hooks/
│   │   ├── scripts/
│   │   └── README.md
│   └── tt-pm-master/           # Teacher Tui产品经理大师插件
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── commands/
│       ├── skills/
│       └── README.md
└── README.md                   # 本文件
```

## 开发新插件

### 插件目录结构

```
plugins/{plugin-name}/
├── .claude-plugin/
│   └── plugin.json             # 必需：插件清单
├── hooks/
│   └── hooks.json              # 可选：Hook 配置
├── scripts/                    # 可选：脚本文件
├── skills/                     # 可选：Skill 定义
└── README.md                   # 推荐：插件文档
```

### 注册新插件

在 `.claude-plugin/marketplace.json` 的 `plugins` 数组中添加新插件：

```json
{
  "name": "new-plugin",
  "path": "plugins/new-plugin",
  "description": "插件描述",
  "version": "1.0.0",
  "tags": ["tag1", "tag2"]
}
```

## 贡献

欢迎提交 Issue 和 Pull Request。

## 许可证

MIT License

## 相关链接

- [Claude Code 官方文档](https://docs.anthropic.com/claude-code)
- [Claude Code 官方插件仓库](https://github.com/anthropics/claude-plugins-official)
