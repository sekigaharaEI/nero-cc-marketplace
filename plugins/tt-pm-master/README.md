# Teacher Tui产品经理大师

`tt-pm-master` 是一个面向产品经理工作的基础双栈插件，核心工作流已同时兼容 Claude Code 和 Codex，个别平台相关技能会单独标注。

## 支持范围

| 平台 | 状态 | 说明 |
| --- | --- | --- |
| Claude Code | 支持 | 保留现有 slash commands、技能和帮助入口 |
| Codex | 支持（核心 skills） | 复用同一套 `skills/` 作为插件主体，通过 `.codex-plugin/plugin.json` 暴露给 Codex；`tt-nanoBanana` 仍为 Claude-only |

## 核心能力

- 竞品分析
- APP 分析
- 商业模式规划
- PRD 撰写
- 产品评审
- 评审意见处理
- 会话存档与恢复
- NotebookLM 集成
- 文档转幻灯片
- 禅道研发需求提取

## 安装

### Claude Code

```bash
/plugin install tt-pm-master@nero-cc-marketplace
```

### Codex

将本仓库作为 Codex 可识别的插件市场后，Codex 会通过 `.agents/plugins/marketplace.json` 发现 `tt-pm-master`。修改 marketplace 或插件内容后，记得重启 Codex 让变更生效。

## 目录说明

```text
plugins/tt-pm-master/
├── .claude-plugin/plugin.json   # Claude Code 清单
├── .codex-plugin/plugin.json    # Codex 清单
├── commands/                   # Claude 侧帮助入口
├── skills/                     # 双栈共享的工作流主体
├── README.md                   # 本说明
└── ...
```

## 兼容说明

- 当前插件的主体能力复用同一套 `skills/`，不拆分核心逻辑。
- `commands/help.md` 仍然保留为 Claude 侧入口。
- `tt-nanoBanana` 仍然依赖 `~/.claude/...` 路径，当前保留为 Claude-only。
- 其余技能以共享工作流为主，后续如果出现平台差异，会在这里单独标注。

## 版本

- 当前版本：`1.0.5`
- 作者：`Teacher Tui`
