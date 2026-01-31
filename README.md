# Nero's Claude Code Marketplace

个人的 Claude Code 插件市场，用于存放和分发自己开发的各种 Claude Code 插件。

## 快速开始

### 添加 Marketplace

```bash
/plugin marketplace add sekigaharaEI/nero-cc-marketplace
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
| [custom-compact](./plugins/custom-compact/)   | 1.0.3 | 在上下文压缩前自动保存会话记忆              |
| [memory-stalker](./plugins/memory-stalker/)   | 1.0.3 | 记忆追猎者 - 智能压缩、可溯源存储、接续对话 |
| [tulei-pm-master](./plugins/tulei-pm-master/) | 1.0.1 | 涂磊产品经理大师 - 专业的产品经理工具集     |

## 插件详情

### custom-compact

在 Claude Code 上下文压缩（PreCompact）前，自动将当前会话的关键信息提取并保存为 Markdown 文件。

**功能特性:**

- 自动触发，无需手动操作
- 智能提取任务摘要、代码变更、用户偏好、关键决策
- 结构化 Markdown 输出
- 持久化存储在项目目录

**安装:**

```bash
/plugin install custom-compact@nero-cc-marketplace
pip install anthropic>=0.18.0
export ANTHROPIC_API_KEY="your-api-key"
```

[查看详细文档](./plugins/custom-compact/README.md)

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

**使用:**

```bash
/memories  # 浏览和选择记忆文件
/resume    # 基于记忆文件接续对话
```

[查看详细文档](./plugins/memory-stalker/README.md)

### tulei-pm-master

涂磊产品经理大师 - 专业的产品经理工具集，以涂磊式犀利风格提供产品管理全流程支持。

**功能特性:**

- 📱 竞品分析：根据 APP 截图反向分析产品功能、商业模式及资源投入
- 📋 PRD 撰写：编写高质量的产品需求文档
- 💼 商业模式规划：生成针对总经理汇报的新项目商业模式规划方案
- 🔍 产品评审：模拟产品评审委员会进行深度评审
- 💬 评审意见处理：智能处理和答复评审团队的意见
- 📦 会话存档与恢复：支持工作进度的持久化存储

**安装:**

```bash
/plugin install tulei-pm-master@nero-cc-marketplace
```

**使用:**

```bash
/help                    # 查看所有可用命令
/pm-analyze-competitor   # 竞品分析
/pm-write-prd           # 撰写 PRD
/pm-plan-business-model # 商业模式规划
/pm-review-product      # 产品评审
/pm-response-review     # 评审意见处理
```

[查看详细文档](./plugins/tulei-pm-master/README.md)

## 仓库结构

```
nero-cc-marketplace/
├── .claude-plugin/
│   └── marketplace.json        # Marketplace 清单
├── plugins/
│   ├── custom-compact/         # Custom Compact 插件
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── hooks/
│   │   ├── scripts/
│   │   └── README.md
│   ├── memory-stalker/         # Memory Stalker 插件
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── commands/
│   │   ├── hooks/
│   │   ├── scripts/
│   │   └── README.md
│   └── tulei-pm-master/        # 涂磊产品经理大师插件
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── commands/
│       ├── hooks/
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
