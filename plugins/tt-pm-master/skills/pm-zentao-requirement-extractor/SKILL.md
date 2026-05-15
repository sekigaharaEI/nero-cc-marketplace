---
name: pm-zentao-requirement-extractor
description: 从禅道产品浏览地址或产品 ID 中批量提取 story/研发需求，导出为可分析的 Markdown 文件，并保留需求详情、截图链接与关键字段。适用于需要抓取禅道研发需求详情、批量导出某产品下全部需求、保留 `spec` 或源 Bug `steps` 中截图、或将需求落盘到指定目录后继续分析的场景。
---

# pm-zentao-requirement-extractor

> 本 skill 同时适配 **Claude Code** 与 Codex。检测/示例以 Claude Code 为主，Codex 配置作为兼容回退。

## 概述

先（如有 `zentao` MCP）做范围确认、字段抽样和接口验证，再用附带脚本做全量导出。这样既能快速确认数据口径，也能稳定生成适合后续分析的 Markdown 文件。

注意区分两件事：

- 某个配置文件里存在 `zentao` 配置，不等于当前会话已经加载了 `zentao` MCP。
- 当前会话没有加载 `zentao` MCP，不等于附带脚本不能执行。脚本会按优先级依次读取：环境变量 → `~/.claude.json`（含项目级 `projects.<path>.mcpServers.zentao.env`）→ `~/.claude/settings.json` → 当前目录 `.mcp.json` → `~/.codex/config.toml` → `~/.codex/config_api.toml`。

默认输出字段（每条研发需求按下面这种格式输出，**字段名加粗、不带列表前缀**）：

```
## <id>

**研发需求名称**：<title>

**需求描述**：

<spec 正文，保留原文加粗/字号样式，并把 ![](url) 内嵌在原图位置>

**所属模块**：<moduleTitle>

**当前状态**：<status>

**优先级**：<pri>

**计划**：<planTitle>

**创建日期**：<openedDate>
```

重要原则：

1. **不要把截图从需求描述里抽离出来单列**。禅道 `spec` 或源 Bug `steps` 里图片出现在哪一段文字旁，导出 Markdown 里 `![](url)` 就保留在同样位置，按原始图文顺序输出。
2. **如实复现禅道原文的样式**。禅道 `spec` 中可能含 `<strong>` / `<b>` 包裹的加粗文本，或 `<h1>`-`<h6>`、`font-size` 较大的 `<span>` / `<font>` 标题样式；导出时统一用 Markdown `**…**` 复现，让"被作者强调的部分"在 Markdown 里仍然显眼。
3. **字段名加粗、不带 `-` 列表前缀**。`研发需求名称`、`需求描述`、`所属模块`、`当前状态`、`优先级`、`计划`、`创建日期` 七个字段标题在每条研发需求段落里都按 `**字段名**：值` 的形式输出，字段与字段之间用空行分段，不要用无序列表前缀。

## 先检查 zentao MCP（Claude Code 流程）

按以下顺序判断当前会话是否真的加载了 `zentao` MCP，**不要只看配置文件存不存在**：

1. 看当前可调用工具列表里是否有 `mcp__zentao__*` 前缀的工具（例如 `mcp__zentao__getStoryList`、`mcp__zentao__getStoryDetail`、`mcp__zentao__getBugDetail`）。
   - 如果有 → 当前会话 zentao MCP 已生效，可直接用 MCP 抽样。
2. 如果工具列表里没有 `mcp__zentao__*`，再用 `ListMcpResourcesTool` 列资源，或直接 `ReadMcpResourceTool` 读 `zentao://config` 验证。
   - 任一调用成功 → 当前会话 zentao MCP 已生效。
3. 如果 1、2 都失败，再去检查本机配置文件，**判断是否只是会话没加载**：
   - Claude Code 用户优先看：`~/.claude.json`（顶层或 `projects.<path>` 节点下的 `mcpServers.zentao.env`），以及项目根目录 `.mcp.json`、`~/.claude/settings.json`。
   - Codex 兼容路径：`~/.codex/config.toml` 与 `~/.codex/config_api.toml`。
   - 如果上述任一文件已配置 zentao 但当前会话仍调不通，要明确说明：
     - 当前 Claude Code 会话未加载 `zentao` MCP（可能需要重启 Claude Code 或运行 `/mcp` 重连）。
     - 但附带脚本仍可直接读这些文件中的账号继续执行导出。
4. 如果所有配置文件里都没有 `zentao`，再按"未安装 / 未配置"处理，并引导用户补配置。

### Claude Code 推荐配置（`~/.claude.json` 或项目根 `.mcp.json`）

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

### Codex 兼容配置（`~/.codex/config.toml`）

```toml
[mcp_servers.zentao]
command = "npx"
args = ["-y", "@makun111/zentao-mcp-server"]

[mcp_servers.zentao.env]
ZENTAO_BASE_URL = "http://your-zentao-host/zentao/"
ZENTAO_ACCOUNT = "your-account"
ZENTAO_PASSWORD = "your-password"
```

提醒用户：
- `ZENTAO_BASE_URL` 应指向禅道根路径，通常以 `/zentao/` 结尾。
- `ZENTAO_ACCOUNT` 填禅道登录账号。
- `ZENTAO_PASSWORD` 填禅道登录密码。
- 若希望本会话直接通过 MCP 调用，配置完成后请重启 Claude Code，或在会话里执行 `/mcp` 重连，再用步骤 1～2 验证。

## 用 MCP 做抽样确认（仅在 zentao MCP 真实可用时）

在全量导出前，先验证一页列表和一条详情，确认字段结构无误。

- 列研发需求一页：

```text
GET /stories?product=<product_id>&page=1&limit=20
```

- 单条研发需求详情：

```text
GET /stories/<story_id>
```

- 若 `moduleTitle` 或 `spec` 缺失，且 `fromBug` 存在，则继续查源 Bug：

```text
GET /bugs/<bug_id>
```

如当前会话提供 `mcp__zentao__getBugDetail`，优先用它来获取 Bug 详情与截图链接。

## 全量导出流程

1. 先确定导出范围。
   - 如果用户给的是 `product-browse-131-...` 这类地址，就从 URL 中解析产品 ID。
   - 同时把原始页面地址写入输出文件头部，作为来源说明。
2. 如果用户给的是"目录"而不是完整文件名，优先使用 `--output-dir`，让脚本自动命名文件。
3. 执行附带脚本做全量导出。
   - 先把 `<skill_dir>` 替换成当前 skill 的实际目录。
   - Claude Code 常见路径：`C:\Users\<你的用户名>\.claude\skills\pm-zentao-requirement-extractor`
   - Codex / 本仓库安装路径可能是：`<repo>\plugins\tt-pm-master\skills\pm-zentao-requirement-extractor`

PowerShell 示例（Windows / Claude Code 默认 shell）：

```powershell
python "<skill_dir>\scripts\export_zentao_requirements.py" `
  --browse-url "http://your-zentao-host/zentao/product-browse-131---0-story--134-20-1-0.html" `
  --output-dir "F:\path\to\folder"
```

Bash 示例（macOS / Linux）：

```bash
python "<skill_dir>/scripts/export_zentao_requirements.py" \
  --browse-url "http://your-zentao-host/zentao/product-browse-131---0-story--134-20-1-0.html" \
  --output-dir "/path/to/folder"
```

4. 如果用户只给了产品 ID：

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
   - 命令行显式参数（`--base-url` / `--account` / `--password`）
   - 当前 shell 环境变量（`ZENTAO_BASE_URL` / `ZENTAO_ACCOUNT` / `ZENTAO_PASSWORD`）
   - Claude Code JSON 配置：`$CLAUDE_HOME/.claude.json`、`~/.claude.json`、`~/.claude/settings.json`、`./.mcp.json`
     - 顶层 `mcpServers.zentao.env`
     - 也支持 `~/.claude.json` 中 `projects.<工作区路径>.mcpServers.zentao.env`
   - Codex TOML 兼容：`$CODEX_HOME/config.toml`、`config_api.toml`、`~/.codex/config.toml`、`~/.codex/config_api.toml`
2. 脚本只依赖账号信息，不依赖当前会话是否已加载 `zentao` MCP。即使 Claude Code 会话调不到 `mcp__zentao__*`，只要脚本能从环境变量或上述文件读到账号，就能继续导出。
3. 脚本会向 stderr 打印它实际使用的是哪个配置来源（形如 `Using ZenTao credentials from <path>`），避免把"配置存在"和"当前会话 MCP 可用"混为一谈。
4. 通过 `POST /api.php/v1/tokens` 获取 token。
5. 通过 `GET /api.php/v1/stories?product=<id>&page=<n>&limit=<m>` 分页获取研发需求列表。
6. 对每条研发需求继续请求 `GET /api.php/v1/stories/<id>` 获取详情。
7. 如果研发需求本身缺少 `moduleTitle` 或 `spec`，且存在 `fromBug`，则请求 `GET /api.php/v1/bugs/<id>` 作为兜底。
8. 清理禅道默认占位文本，如 `[步骤]`、`[结果]`、`[期望]`。
9. 保留 `spec` 或 Bug `steps` 中的截图地址，并按 Markdown 图片格式写入结果文件。
10. 输出为适合后续分析的 Markdown 文件。

## 本轮测试收敛规则

- skill 正文使用中文，但 skill 名称固定为英文 `pm-zentao-requirement-extractor`。
- 不要仅因 `~/.claude.json` 或 `~/.codex/config*.toml` 中存在 `zentao` 配置，就说"当前会话已具备 zentao MCP"。判定依据是：当前会话能否调用 `mcp__zentao__*` 工具，或能否通过 `ListMcpResourcesTool` / `ReadMcpResourceTool` 访问 `zentao://config`。
- 当多个配置文件并存且不一致时，要明确区分：
  - 哪个文件里有账号；
  - 当前 Claude Code 会话是否真的加载了 `zentao` MCP；
  - 当前任务是走 MCP 还是直接走脚本。
- 如果用户希望本会话立刻通过 MCP 调用，优先把 zentao 同步补到 Claude Code 实际生效的配置（`~/.claude.json` 或项目 `.mcp.json`），然后提示重启 Claude Code 或运行 `/mcp` 重连。
- 如果用户只给落盘目录、不给完整文件名，优先让脚本自动命名（`--output-dir`），不要求用户先手工补文件名。

## 字段提取规则

- `所属模块` 优先取研发需求详情中的 `moduleTitle`。
- 如果研发需求详情没有 `moduleTitle`，则回退到源 Bug 的 `moduleTitle`。
- `需求描述` 优先取研发需求详情中的 `spec`。
- 如果研发需求详情的 `spec` 无有效内容，则回退到源 Bug 的 `steps`。
- 截图按禅道原 HTML 中的位置以 `![](url)` 内嵌在描述正文里，**不要单列"需求描述截图"字段**。
- 如实复现禅道原文样式：`<strong>` / `<b>` 包裹的文本，以及 `<h1>`-`<h6>`、`font-size` 较大的 `<span>` / `<font>` 标题样式，统一用 Markdown `**…**` 复现。
- 如果既没有正文文字也没有截图，则写 `无文本描述，需结合禅道原单或附件进一步确认。`
- 状态值尽量映射成中文，如 `active -> 激活`；如果没有映射，就保留原值。
- `优先级` 取禅道详情中的 `pri` 数字，按 `1 最高 / 2 高 / 3 中 / 4 低` 映射并保留原数字（如 `3（中）`）；为空或 0 写为 `未指定`；映射不到的值原样保留。
- `计划` 优先取 `planTitle`：是数组时把所有非空标题用 `、` 拼接；只有 `plan`（计划 ID）时写 `未命名计划（#<id>）`；都没有时写 `未关联计划`。

## 按功能分组重排（可选后处理）

适用场景：用户拿到字段提取 Markdown 后，希望需求**按"功能"语义聚合**而不是按 ID 倒序，方便逐个功能讨论、评审或排期。

职责切分（重要）：

- **AI 负责语义判断**：读完源文件里所有研发需求的标题与需求描述，识别每条属于哪个"功能"，输出分组方案。
- **脚本只做机械拼接**：附带的 `scripts/reorder_by_function.py` 按 AI 给出的分组 JSON 把条目重新组织、降级标题、校验完整性、落新文件；脚本本身**不做任何语义判断**，也**不许把分组规则写死**。

排序规则（AI 生成分组时遵守）：

- **组内**：按优先级 `1(最高) → 2(高) → 3(中) → 4(低)` 排序；同优先级保持原 ID 倒序（新需求在前）。
- **组之间**：先按"组内最高优先级"降序；同档时按"组规模"降序；再同则按"组内最大 ID"降序。
- **分组粒度（防太粗 + 防太细，按顺序应用）**：
  1. **不要复用禅道"所属模块"做分组** —— 模块太粗。例如"订单处理-前端过滤"和"订单处理-发货状态字段"是两个不同功能，不能因为同属"销售管理"模块就归到一起。
  2. **聚合优先：先按"单据/界面"分一版，再扫一遍** —— 同一业务领域（如"统计报表"、"退货管理"、"发货管理"）下若有 ≥2 条来自不同单据/界面但属同一领域，**合并到"领域"组**，不要每个单据自成一组。
  3. **每个单条独立组都要先自问一句**："它和现有任何一个组有没有公共的业务领域？" 有 → 合并过去；没有 → 独立成组也合理（如"查询条件自定义"是跨模块通用功能、与任何业务领域都不重叠，独立成组就是对的）。**不要为了凑独立组而硬找名字。**
  4. **命名层次对齐** —— 聚合组用领域名（"统计报表"、"退货管理"），单功能簇用功能名（"订单处理 — 前端过滤"）。**组名不要直接复用某条 story 的标题**（标题级粒度往往等于"为这一条专门起个名"，违反规则 3 的精神）。

流程（5 步）：

1. 用 `Read` 读完整个字段提取 Markdown，理解每条需求要解决的问题。
2. 把分组草案展示给用户（功能名 + 该组下的 `id(优先级)` 列表 + 排序逻辑），让用户先看是否要并/拆。也可以直接执行，让用户基于产出反馈。
3. 把分组写到临时 JSON 文件（系统临时目录即可），格式：
   ```json
   [
     {"name": "订单处理 — 前端过滤（有库存 / 配套有库存）", "ids": [1092, 1094, 1120]},
     {"name": "智能下印 — 印量表", "ids": [982, 980]}
   ]
   ```
4. 调用脚本：
   ```powershell
   python "$env:USERPROFILE\.claude\skills\pm-zentao-requirement-extractor\scripts\reorder_by_function.py" `
     --src "<原字段提取.md 完整路径>" `
     --groups "<临时 groups.json 完整路径>"
   ```
   默认输出到源文件同目录，文件名为 `<src-stem>_按功能分组_<YYYY-MM-DD>.md`，**不修改源文件**。也可用 `--output` / `--output-dir` 指定其他位置。
5. 跑完确认结果后删除临时 `groups.json`。

脚本的安全保证：

- 校验"groups 中的所有 ids ⇄ 源文件中的所有 ids"必须**完全相同**（无重复、无遗漏、无多余）。任何一项不满足就 `SystemExit` 并打印诊断信息，**不会**写出新文件。
- 条目从 `## <id>` 降级为 `### <id>`，组使用 `## <功能名>` 作为二级标题。原标题层级保留，文件结构清晰。
- 条目正文（含截图 `![](url)`、原 SQL、原文加粗 `**…**`、字段值）**全部按字节复制**，不做任何加工。

不要做的事：

- 不要让脚本去做语义分组（脚本不会，也不该会）。
- 不要把分组结果硬编码到脚本里 —— 每次运行的需求集合不同，分组都要 AI 重新判断。
- 不要覆盖源文件 —— 默认文件名带 `_按功能分组_<日期>` 后缀，避免冲突。
- 不要在 `groups.json` 里省略任何一条源文件中的需求；脚本会因为"extra ids in source"拒绝。

## 分析时的处理原则

如果用户要的不是"列表"，而是"分析"，不要直接对禅道页面做口头分析。先导出为本地 Markdown 文件，再基于导出文件做模块归类、状态统计、时间分布或详细需求分析。这样数据口径稳定，后续也便于复用。
