# Nero's Claude Code Marketplace

个人 Claude Code 插件市场，用于存放和分发自己开发的各种 Claude Code 插件。

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

| 插件名称 | 版本 | 描述 |
|---------|------|------|
| [custom-compact](./plugins/custom-compact/) | 1.0.0 | 在上下文压缩前自动保存会话记忆 |

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

## 仓库结构

```
nero-cc-marketplace/
├── .claude-plugin/
│   └── marketplace.json        # Marketplace 清单
├── plugins/
│   └── custom-compact/         # Custom Compact 插件
│       ├── .claude-plugin/
│       │   └── plugin.json     # 插件清单
│       ├── hooks/
│       │   └── hooks.json      # Hook 配置
│       ├── scripts/
│       │   ├── save_memory.py  # 主脚本
│       │   └── memory_prompt.txt
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
