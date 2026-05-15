# ZenTao 环境与 MCP 排查

仅在脚本缺凭据、用户要求配置/排查 ZenTao，或需要判断当前会话是否真的加载 `zentao` MCP 时读取本文件。正常导出任务不要加载本文件。

## 判断当前会话是否真的加载 MCP

不要只看配置文件存不存在。按以下顺序判断：

1. 看当前可调用工具列表里是否有 `mcp__zentao__*` 前缀工具，例如 `mcp__zentao__getStoryList`、`mcp__zentao__getStoryDetail`、`mcp__zentao__getBugDetail`。
   - 有这些工具，说明当前会话 zentao MCP 已生效，可直接做 MCP 抽样。
2. 如果工具列表里没有 `mcp__zentao__*`，再用资源工具列资源，或直接读 `zentao://config` 验证。
   - 任一调用成功，说明当前会话 zentao MCP 已生效。
3. 如果 1、2 都失败，再检查本机配置文件，判断是否只是会话未加载。
   - Claude Code 用户优先看：`~/.claude.json`（顶层或 `projects.<path>.mcpServers.zentao.env`）、项目根目录 `.mcp.json`、`~/.claude/settings.json`。
   - Codex 兼容路径：`~/.codex/config.toml`、`~/.codex/config_api.toml`。
   - 如果配置存在但当前会话调不通，要明确说明：当前会话未加载 `zentao` MCP，可能需要重启 Claude Code 或运行 `/mcp` 重连；但附带脚本仍可直接读取配置中的账号继续导出。
4. 如果所有配置文件里都没有 `zentao`，再按未安装或未配置处理。

## 脚本凭据读取顺序

附带脚本按以下优先级读取凭据：

1. 命令行显式参数：`--base-url` / `--account` / `--password`
2. 当前 shell 环境变量：`ZENTAO_BASE_URL` / `ZENTAO_ACCOUNT` / `ZENTAO_PASSWORD`
3. Claude Code JSON 配置：
   - `$CLAUDE_HOME/.claude.json`
   - `~/.claude.json`
   - `~/.claude/settings.json`
   - `./.mcp.json`
   - 支持顶层 `mcpServers.zentao.env`
   - 支持 `~/.claude.json` 中 `projects.<工作区路径>.mcpServers.zentao.env`
4. Codex TOML 配置：
   - `$CODEX_HOME/config.toml`
   - `$CODEX_HOME/config_api.toml`
   - `~/.codex/config.toml`
   - `~/.codex/config_api.toml`

脚本只依赖账号信息，不依赖当前会话是否已加载 `zentao` MCP。脚本会向 stderr 打印实际使用的配置来源，例如 `Using ZenTao credentials from <path>`。

## Claude Code 配置示例

`~/.claude.json` 或项目根 `.mcp.json`：

```json
{
  "mcpServers": {
    "zentao": {
      "command": "npx",
      "args": ["-y", "@makun111/zentao-mcp-server"],
      "env": {
        "ZENTAO_BASE_URL": "http://your-zentao-host/zentao/",
        "ZENTAO_ACCOUNT": "your-account",
        "ZENTAO_PASSWORD": "your-password"
      }
    }
  }
}
```

## Codex 配置示例

`~/.codex/config.toml`：

```toml
[mcp_servers.zentao]
command = "npx"
args = ["-y", "@makun111/zentao-mcp-server"]

[mcp_servers.zentao.env]
ZENTAO_BASE_URL = "http://your-zentao-host/zentao/"
ZENTAO_ACCOUNT = "your-account"
ZENTAO_PASSWORD = "your-password"
```

## 配置提醒

- `ZENTAO_BASE_URL` 应指向禅道根路径，通常以 `/zentao/` 结尾。
- `ZENTAO_ACCOUNT` 填禅道登录账号。
- `ZENTAO_PASSWORD` 填禅道登录密码。
- 若用户希望本会话直接通过 MCP 调用，配置完成后提示重启 Claude Code，或在会话里执行 `/mcp` 重连，再重新验证当前会话是否真的加载 MCP。
