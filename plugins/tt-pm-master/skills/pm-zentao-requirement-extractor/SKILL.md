---
name: pm-zentao-requirement-extractor
description: 从禅道产品浏览地址或产品 ID 中批量提取 story/研发需求，导出为可分析的 Markdown 文件，并保留需求详情、截图链接与关键字段。适用于需要抓取禅道研发需求详情、批量导出某产品下全部需求、保留 `spec` 或源 Bug `steps` 中截图、或将需求落盘到指定目录后继续分析的场景。
---

# pm-zentao-requirement-extractor

## 概述

先用 `zentao` MCP 做范围确认、字段抽样和接口验证，再用附带脚本做全量导出。这样既能快速确认数据口径，也能稳定生成适合后续分析的 Markdown 文件。

注意区分两件事：

- 某个配置文件里存在 `zentao` 配置，不等于当前会话已经加载了 `zentao` MCP。
- 当前会话没有加载 `zentao` MCP，不等于附带脚本不能执行。脚本仍可直接读取 `config.toml` 或 `config_api.toml` 里的账号信息发起导出。

默认输出字段：

- `研发需求名称`
- `需求描述`
- `需求描述截图`
- `所属模块`
- `当前状态`
- `创建日期`

## 先检查 zentao MCP

1. 先检查“当前会话里”是否真的加载了 `zentao` MCP。
   - 优先列当前会话的 MCP 资源，或直接尝试读取 `zentao://config`。
   - 只有当前会话能列出 `zentao` 资源，或能成功读取 `zentao://config`，才算 `zentao` MCP 当前可用。
2. 如果当前会话里没有 `zentao` 资源，不要直接下结论说“没配置”。继续检查本机配置文件。
   - 先看 `~/.codex/config.toml`。
   - 再看 `~/.codex/config_api.toml`。
   - 如果 `zentao` 只出现在 `config_api.toml` 而当前会话没有加载对应资源，要明确说明：
     - 当前会话未加载 `zentao` MCP。
     - 但附带脚本仍可直接读取 `config_api.toml` 中的账号继续执行。
3. 如果两个配置文件都没有 `zentao`，再按“未安装 / 未配置”处理，并引导用户补配置。
   - 配置示例如下：

```toml
[mcp_servers.zentao]
command = "npx"
args = ["-y", "@makun111/zentao-mcp-server"]

[mcp_servers.zentao.env]
ZENTAO_BASE_URL = "http://your-zentao-host/zentao/"
ZENTAO_ACCOUNT = "your-account"
ZENTAO_PASSWORD = "your-password"
```

4. 明确提醒用户把占位值替换成真实值。
   - `ZENTAO_BASE_URL` 应指向禅道根路径，通常以 `/zentao/` 结尾。
   - `ZENTAO_ACCOUNT` 填禅道登录账号。
   - `ZENTAO_PASSWORD` 填禅道登录密码。
5. 如果用户希望后续会话直接使用 `zentao` MCP，而不是只靠脚本导出，优先把 `zentao` 同步补到当前实际生效的配置文件中。
   - 若当前会话启动时实际读取的是 `config.toml`，就不要只改 `config_api.toml`。
   - 配置完成后，提醒用户重启 Codex 或重新加载 MCP，再次检查 `zentao://config`。

## 用 MCP 做抽样确认

在全量导出前，先用 MCP 验证一页列表和一条详情，确认字段结构无误。

- 查询某产品的一页研发需求：

```text
GET /stories?product=<product_id>&page=1&limit=20
```

- 查询单条研发需求详情：

```text
GET /stories/<story_id>
```

- 如果 `moduleTitle` 或 `spec` 缺失，且 `fromBug` 存在，则继续查源 Bug：

```text
GET /bugs/<bug_id>
```

如果当前环境提供 `mcp__zentao__getBugDetail`，优先使用它来获取 Bug 详情与截图链接。

## 全量导出流程

1. 先确定导出范围。
   - 如果用户给的是 `product-browse-131-...` 这类地址，就从 URL 中解析产品 ID。
   - 同时把原始页面地址写入输出文件头部，作为来源说明。
2. 如果用户给的是“目录”而不是完整文件名，优先使用 `--output-dir`，让脚本自动命名文件。
3. 执行附带脚本做全量导出。
   - 先把 `<skill_dir>` 替换成当前 skill 的实际目录，例如：
     - `F:\Document\Project\ai-config\.codex\skills\tt-pm-master\pm-zentao-requirement-extractor`
     - `C:\Users\Administrator\.codex\skills\tt-pm-master\pm-zentao-requirement-extractor`

```powershell
python "<skill_dir>\scripts\export_zentao_requirements.py" `
  --browse-url "http://your-zentao-host/zentao/product-browse-131---0-story--134-20-1-0.html" `
  --output-dir "F:\path\to\folder"
```

4. 如果用户只给了产品 ID，则执行：

```powershell
python "<skill_dir>\scripts\export_zentao_requirements.py" `
  --product-id 131 `
  --output "F:\path\to\禅道_研发需求_字段提取.md"
```

5. 如果只是想先看样本，使用 `--max-items`：

```powershell
python "<skill_dir>\scripts\export_zentao_requirements.py" `
  --product-id 131 `
  --max-items 3 `
  --output "F:\path\to\sample.md"
```

## 脚本行为

附带脚本会按以下顺序工作：

1. 按优先级读取凭据：
   - 命令行显式参数
   - 当前 shell 环境变量
   - `~/.codex/config.toml`
   - `~/.codex/config_api.toml`
2. 脚本只依赖账号信息，不依赖当前会话是否已加载 `zentao` MCP。
   - 即使当前会话列不出 `zentao` 资源，只要脚本能从环境变量或配置文件中读到账号，也可以继续导出。
3. 脚本会打印它实际使用的是哪个配置来源，避免把“配置存在”和“当前会话 MCP 可用”混为一谈。
4. 通过 `POST /api.php/v1/tokens` 获取 token。
5. 通过 `GET /api.php/v1/stories?product=<id>&page=<n>&limit=<m>` 分页获取研发需求列表。
6. 对每条研发需求继续请求 `GET /api.php/v1/stories/<id>` 获取详情。
7. 如果研发需求本身缺少 `moduleTitle` 或 `spec`，且存在 `fromBug`，则请求 `GET /api.php/v1/bugs/<id>` 作为兜底。
8. 清理禅道默认占位文本，如 `[步骤]`、`[结果]`、`[期望]`。
9. 保留 `spec` 或 Bug `steps` 中的截图地址，并按 Markdown 图片格式写入结果文件。
10. 输出为适合后续分析的 Markdown 文件。

## 本轮测试收敛规则

- skill 正文使用中文，但 skill 名称固定为英文 `pm-zentao-requirement-extractor`。
- 不要仅因 `config_api.toml` 中存在 `zentao` 配置，就说“当前会话已具备 zentao MCP”。
- 遇到 `config.toml` 与 `config_api.toml` 配置不一致时，要明确区分：
  - 哪个文件里有账号。
  - 当前会话是否真的加载了 `zentao` MCP。
  - 当前任务是走 MCP 还是直接走脚本。
- 如果用户只给落盘目录，不给完整文件名，优先让脚本自动命名，不要求用户先手工补文件名。

## 字段提取规则

- `所属模块` 优先取研发需求详情中的 `moduleTitle`。
- 如果研发需求详情没有 `moduleTitle`，则回退到源 Bug 的 `moduleTitle`。
- `需求描述` 优先取研发需求详情中的 `spec`。
- 如果研发需求详情的 `spec` 无有效内容，则回退到源 Bug 的 `steps`。
- 如果正文没有文字但有截图，则写 `需求正文主要通过截图说明。`
- 如果既没有正文文字也没有截图，则写 `无文本描述，需结合禅道原单或附件进一步确认。`
- 状态值尽量映射成中文，如 `active -> 激活`；如果没有映射，就保留原值。

## 分析时的处理原则

如果用户要的不是“列表”，而是“分析”，不要直接对禅道页面做口头分析。先导出为本地 Markdown 文件，再基于导出文件做模块归类、状态统计、时间分布或详细需求分析。这样数据口径稳定，后续也便于复用。 
