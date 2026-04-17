# ZXW 禅道 Bug 修复

`zxw-zentao-bug-fix` 是一个纯 Codex 插件，用于在禅道里查询候选 bug、按 `bug_id` 进入单 bug 修复闭环，并通过 `setup` 初始化当前项目上下文。

## 支持范围

| 平台 | 状态 | 说明 |
| --- | --- | --- |
| Claude Code | 不支持 | 该插件不提供 Claude 兼容层 |
| Codex | 支持 | 复用现成 `zentao-mcp`，并通过 `zentao-setup` 初始化本地配置 |

## 核心能力

- `zentao-bug-list-query`：按条件查询禅道 bug 列表
- `zentao-bug-fix-by-id`：按 `bug_id` 处理单个 bug 并完成修复闭环
- `zentao-setup`：初始化禅道连接、本地项目配置和当前项目身份信息

## 安装

1. 克隆仓库：

```bash
git clone https://github.com/sekigaharaEI/nero-cc-marketplace.git
```

2. 进入仓库目录：

```bash
cd nero-cc-marketplace
```

3. 打开 Codex 并进入插件目录：

```bash
codex
/plugins
```

4. 在插件列表中选择 `zxw-zentao-bug-fix` 并安装。

5. 安装后，先运行 `zentao-setup`，完成当前项目和禅道连接初始化。

## 初始化

`zentao-setup` 会让你填写：

- `human_owner`
- `project_id`
- `ZENTAO_BASE_URL`
- `ZENTAO_ACCOUNT`
- `ZENTAO_PASSWORD`

它会把项目上下文写入当前项目的 `./.codex/zentao-bug-fix.yaml`，并把 `zentao-mcp` 配置合并到本机 Codex 配置中。

如果你想先看占位符模板，可以直接参考：

- `./templates/zentao-mcp.toml.example`
- `./templates/zentao-bug-fix.yaml.example`

## 本地配置示例

仓库只保留占位符示例，不保存真实禅道账号密码。

```toml
[mcp_servers.zentao]
command = "npx"
args = ["-y", "zentao-mcp"]

[mcp_servers.zentao.env]
ZENTAO_BASE_URL = "http://your-zentao-host/zentao/"
ZENTAO_ACCOUNT = "your-account"
ZENTAO_PASSWORD = "your-password"
MCP_ENABLE_WRITE_TOOLS = "true"
```

## 使用顺序

1. 先执行 `zentao-setup`
2. 再使用 `zentao-bug-list-query` 拉取候选 bug
3. 选定 `bug_id` 后使用 `zentao-bug-fix-by-id` 进入修复闭环

## 目录说明

```text
plugins/zxw-zentao-bug-fix/
├── .codex-plugin/plugin.json
├── README.md
├── scripts/setup_zentao.py
└── skills/
    ├── zentao-setup/
    ├── zentao-bug-list-query/
    └── zentao-bug-fix-by-id/
```

## 兼容说明

- 该插件不提供 Claude Code 兼容层。
- 所有 skill 均以 Codex 为目标平台。
- 复用现成 `zentao-mcp`，不新增独立 MCP 服务。
- 项目级上下文只保留 `project_id` 和 `human_owner` 两个最小字段。
