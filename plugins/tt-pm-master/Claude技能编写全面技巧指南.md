# Claude 技能编写全面技巧指南

## 1. 引言：Claude 技能开发概述与价值主张

### 1.1 Claude 技能的定义与核心优势

Claude Skills 是 Anthropic 公司推出的革命性 AI 能力扩展机制，作为一种标准化的程序性知识封装格式，为 AI Agent 提供 "操作手册" 或 "SOP（标准作业程序）"，教导智能体如何正确使用工具[(124)](https://c.m.163.com/news/a/KJKDJHFK0538QQXU.html)。简单来说，Skill 是包含指令、脚本和资源的文件夹，供 LLM 可以动态加载，底层采用的是渐进式披露机制，也就是仅在需要的时候加载技能的详细指令，能有效节省宝贵的上下文窗口[(125)](http://m.toutiao.com/group/7595157641827975715/?upstream_biz=doubao)。

从技术架构角度看，Skill 本质上是一个文件系统中的资源包，以标准化的文件夹形式存在，其核心组件包括：



* SKILL.md（必需）：包含 YAML frontmatter 元数据和 Markdown 格式的指令内容

* scripts/（可选）：可执行代码（Python、Bash 等）

* references/（可选）：文档资料

* assets/（可选）：模板、字体、图标等输出资源

这种设计带来了三大核心优势。首先是模块化特性，每个 Skill 做一件事，独立封装，便于复用和维护[(127)](https://juejin.cn/post/7597125475601268763)。其次是自动加载机制，Claude 根据任务描述自动判断需要哪个 Skill，实现智能化的能力调用[(127)](https://juejin.cn/post/7597125475601268763)。最重要的是渐进式披露架构，通过三层加载机制避免一次性加载所有内容：第一层元数据常驻内存（约 100 tokens），第二层指令正文在触发时加载（通常 < 5k tokens），第三层资源按需加载（几乎无限），这种设计实现了 Token 效率与功能深度的完美平衡。

### 1.2 适用人群与学习目标

本指南面向所有 Claude 技能开发者，无论您是个人开发者还是企业团队成员，都能从中获得实用的技巧和最佳实践。对于新手开发者，本指南将帮助您快速入门，掌握基础技能编写方法；对于有经验的开发者，本指南提供了进阶技巧和优化策略，助您提升技能开发效率和质量。

学习本指南后，您将能够：



* 理解 Claude Skills 的核心概念和技术架构

* 掌握不同类型技能（工具调用、知识库问答、流程自动化等）的编写方法

* 针对不同应用场景和行业需求设计相应的技能

* 根据自身经验水平选择合适的开发策略和工具

* 实现企业级技能开发的标准化和规模化

### 1.3 技能开发的技术架构与设计哲学

Claude Skills 的技术实现架构精巧而务实，其设计哲学强调结构化、可治理和确定性。技能被明确分为四种类型：流程型（多步骤工作流）、任务型（单一具体任务）、规范型（格式与标准）以及能力型（基础能力扩展）。这种分类体系为不同应用场景提供了清晰的设计指引。

在架构层面，"文件即 API" 是 Agent Skills 架构的核心理念之一，它通过标准化的文件格式和目录结构，将技能封装为自包含的、可移植的能力单元[(137)](https://jishuzhan.net/article/2018131434805444610)。该文件采用统一的结构：YAML frontmatter 定义技能的元数据和配置，Markdown 内容提供具体的指令和指南。Agent Skills 的生态系统采用了层次化的目录组织结构，这种设计使得技能可以在不同范围和粒度上进行管理和共享[(137)](https://jishuzhan.net/article/2018131434805444610)。

渐进式披露机制是 Skill 架构的技术突破，通过三层加载架构成功打破了上下文窗口的物理限制，实现了知识的高效挂载。这种设计不仅重塑了人机协作的边界，更为企业级 AI 应用的规模化部署提供了标准化的基础设施。

## 2. 基础技能编写核心技巧

### 2.1 技能定义与配置规范

技能定义是整个开发流程的基础，正确的定义规范直接影响技能的可发现性和调用准确性。根据 Anthropic 官方文档，技能定义必须遵循严格的规范要求。

**YAML frontmatter 规范**

YAML frontmatter 是技能定义的核心，它告诉 Claude 何时以及如何加载技能。最小必需格式如下：



```
\---

name: your-skill-name

description: What it does. Use when user asks to \[specific phrases].

\---
```

其中，`name`字段必须使用 kebab-case 格式（小写字母加连字符），不能包含空格或大写字母，长度不超过 64 个字符，且应与文件夹名称保持一致。`description`字段是技能发现的关键，必须同时包含两部分内容：技能的功能描述和使用时机（触发条件），长度不超过 1024 个字符，不能包含 XML 标签（<或>），应该包含用户可能使用的具体任务描述。

**描述字段的最佳实践**

根据 Anthropic 的工程博客，描述字段的设计遵循 "这元数据... 提供了足够的信息让 Claude 知道何时使用每个技能，而无需将所有内容加载到上下文中" 的原则，这是渐进式披露的第一层。

优秀的描述应采用 "功能 + 使用时机 + 关键能力" 的结构，例如：



```
description: Analyzes Figma design files and generates developer handoff documentation. Use when user uploads .fig files, asks for "design specs", "component documentation", or "design-to-code handoff".
```

反面案例包括描述过于模糊（如 "Helps with projects"）、缺少触发条件（如 "Creates sophisticated multi-page documentation systems"）或过于技术化（如 "Implements the Project entity model with hierarchical relationships"）。

**完整技能结构示例**

一个标准的技能目录结构如下：



```
your-skill-name/

├── SKILL.md # 必需 - 主技能文件

├── scripts/ # 可选 - 可执行代码

│   ├── process\_data.py # 示例

│   └── validate.sh # 示例

├── references/ # 可选 - 文档资料

│   ├── api-guide.md # 示例

│   └── examples/ # 示例

└── assets/ # 可选 - 模板等

&#x20;   └── report-template.md # 示例
```

### 2.2 提示词工程与指令设计

提示词工程是决定技能质量的关键因素，现代 LLM 对清晰指令反应极佳，不要假设模型能 "猜中" 你的想法 —— 直接说出你想要什么[(14)](https://blog.csdn.net/weixin_43954818/article/details/155225739)。

**指令设计的核心原则**

优秀的指令设计应遵循以下原则[(40)](https://github.com/ThamJiaHe/claude-prompt-engineering-guide)：



* 清晰直接（Be Explicit and Clear）：用命令式动词开头，如 "写、分析、生成、创建"，指明任务目标，不绕弯，不客套

* 提供上下文与动机：不仅告诉模型 "要做什么"，还要告诉它 "为什么这样做"

* 使用示例（Use examples）：展示而非仅仅讲述，通过具体案例传达期望输出

* 鼓励推理（Encourage reasoning）：思维链提示能显著提升质量

* 定义输出格式：明确指定结构和风格要求

* 利用并行工具：同时执行多个操作以提高效率

**Anthropic 官方 10 组件框架**

Anthropic 推荐的专业提示词结构包含 10 个组件：



1. 任务上下文（WHO 和 WHAT）：定义 Claude 的角色

2. 语气上下文（HOW）：沟通风格

3. 背景数据：相关上下文和文档

4. 详细任务描述：明确的要求和规则

5. 示例：1-3 个期望输出的例子

6. 对话历史：相关的先前上下文

7. 即时任务描述：当前需要的具体交付物

8. 逐步思考：鼓励深思熟虑的推理

9. 输出格式：明确定义结构

10. 预填充响应：开始 Claude 的响应以引导风格

**结构化指令设计**

在技能的 Markdown 内容中，推荐采用以下结构：



```
\# Your Skill Name

\## Instructions

\### Step 1: \[First Major Step]

Clear explanation of what happens.

Example:

\`\`\`bash

python scripts/fetch\_data.py --project-id PROJECT\_ID

Expected output: \[describe what success looks like]
```

## Examples

Example 1: \[common scenario]

User says: "Set up a new marketing campaign"

Actions:



1. Fetch existing campaigns via MCP

2. Create new campaign with provided parameters

   Result: Campaign created with confirmation link



```
指令设计的最佳实践包括：

\- 具体且可操作：使用"Run \`python scripts/validate.py --input {filename}\` to check data format"而非模糊的"Validate the data before proceeding"

\- 包含错误处理：在指令中预见并处理常见错误情况

\- 清晰引用资源：使用"Before writing queries, consult \`references/api-patterns.md\` for rate limiting guidance"等明确指引

\- 利用渐进式披露：保持SKILL.md专注于核心指令，将详细文档移至references/并链接引用

\### 2.3 上下文管理与渐进式披露

上下文管理是Claude Skills的核心技术创新，通过渐进式披露机制实现了在有限上下文窗口内的无限能力扩展。

\*\*三层渐进式披露架构\*\*

技能采用精密的三层加载架构：

\| 层级 | 加载时机 | Token成本 | 内容类型 | 典型内容 |

\|------|----------|-----------|----------|----------|

\| 第1级：元数据 | 启动时常驻 | 约100 tokens | YAML frontmatter | name与description字段 |

\| 第2级：指令正文 | 技能被触发时 | 通常<5k tokens | SKILL.md主体 | 流程与指引 |

\| 第3级+：资源 | 按需加载 | 几乎无限 | 脚本、文档等 | 通过bash执行或读取的文件 |

这种架构的优势在于按需读取：只加载当前任务需要的文件，其余资源不会占用上下文；脚本执行高效：脚本代码本身不进入上下文，只有输出结果消耗token；资源容量充足：可以打包完整API文档、数据集或示例，而无需担心上下文限制。

\*\*上下文管理最佳实践\*\*

根据实践经验，上下文管理应遵循以下原则：

\- 保持技能文件精简：将详细文档移至references/目录

\- 按需加载策略：只有在指令明确引用时才加载相关资源

\- 避免重复加载：利用上下文的持续性，避免重复发送相同信息

\- 优化加载顺序：重要信息优先加载，次要信息延后加载

\### 2.4 错误处理与异常捕获机制

完善的错误处理是技能可靠性的保障，Anthropic Cookbook采用了业界领先的三层防御架构，确保AI工具在各种极端情况下都能优雅降级而非崩溃\<reference type="end" id=27>。

\*\*错误处理的核心原则\*\*

错误处理应遵循以下核心原则\<reference type="end" id=27>：

1\. 具体异常优先于通用异常：总是优先捕获具体异常（如FileNotFoundError）而非通用异常（如Exception）

2\. 提供建设性错误消息：错误消息应包含问题描述、可能原因和解决方案

3\. 实施防御性编程：预见可能的错误并提前处理

4\. 完善日志记录：良好的日志记录是诊断问题的关键

5\. 优雅降级策略：在无法完成任务时提供部分结果或替代方案

\*\*错误处理最佳实践\*\*

在技能开发中，错误处理应包含以下要素\<reference type="end" id=28>：

\- 优雅处理：提供有意义的错误消息和恢复选项

\- 适当记录：捕获调试上下文而不暴露敏感数据

\- 全面测试：在测试套件中包含错误场景

\- 持续监控：跟踪错误率和模式

\- 清晰文档：维护错误处理文档

\*\*具体错误处理模式\*\*

以下是一个完整的错误处理示例：
```

Execute build: !`bash ${CLAUDE_PLUGIN_ROOT}/scripts/``build.sh`` 2>&1 || echo "BUILD_FAILED"`

If build succeeded:

Report success and output location

If build failed:

Analyze error output

Suggest likely causes

Provide troubleshooting steps



```
最佳实践包括：

\- 早期验证：在命令开始时进行输入验证

\- 有用的错误消息：错误消息应帮助用户理解和解决问题

\- 建议纠正措施：不仅指出问题，还要提供解决方案

\- 优雅处理边界情况：预见并妥善处理各种边缘情况

\### 2.5 性能优化基础方法

性能优化是技能开发中的重要考量，涉及响应速度、资源消耗和用户体验等多个方面。

\*\*Token优化策略\*\*

根据实践数据，通过合理的技能设计可以实现显著的成本节约：

\- Haiku模型：约\$0.25/百万token

\- Sonnet模型：约\$3/百万token &#x20;

\- Opus模型：约\$15/百万token

通过渐进式披露机制，Token消耗可降低80%以上，长期使用成本大幅下降\<reference type="end" id=161>。对于频繁使用的场景，这意味着成本降低40-60%\<reference type="end" id=162>。

\*\*模型选择与参数调优\*\*

性能优化的关键策略包括\<reference type="end" id=156>：

\- 模型选择：根据任务复杂度选择合适的模型，Haiku适合简单任务，Sonnet平衡性能与成本，Opus用于复杂分析

\- Prompt缓存：使用平台级缓存（如Amazon Bedrock）可减少延迟50-75%，成本降低75%

\- 批量处理：批量处理可节省50%成本

\- Effort参数：Claude Opus 4.5引入的effort参数可实现精准成本管理

\*\*具体优化技巧\*\*

以下是一些实用的性能优化技巧：

1\. 预热机制：在处理复杂任务前先进行简单调用以激活模型

2\. 缓存策略：对频繁使用的计算结果进行缓存

3\. 并行处理：利用Claude的并行工具调用能力

4\. 流式输出：对于长输出采用流式处理，提高响应速度

5\. 资源复用：共享可重用的函数和模块

\### 2.6 测试与调试技巧

测试是确保技能质量的关键环节，技能可以在不同严格程度上进行测试，具体取决于需求：

\*\*测试层次与方法\*\*

测试方法包括三个层次：

1\. 手动测试（Claude.ai）：直接运行查询并观察行为，迭代快速，无需设置

2\. 脚本测试（Claude Code）：自动化测试用例，可重复验证变更

3\. 程序化测试（技能API）：构建评估套件，系统地针对定义的测试集运行

\*\*推荐测试方法\*\*

基于早期经验，有效的技能测试通常涵盖三个方面：

\- 执行问题：不一致的结果、API调用失败、需要用户纠正

\- 解决方案：改进指令、添加错误处理

\*\*迭代测试策略\*\*

最有效的技能创建者会在单个具有挑战性的任务上迭代，直到Claude成功，然后将成功方法提取到技能中。这种方法利用了Claude的上下文学习能力，比广泛测试提供更快的反馈信号。一旦有了工作基础，就扩展到多个测试用例以获得覆盖范围。

\*\*具体测试实践\*\*

测试实践应包含以下要素：

\- 最小测试集：2个示例（正常路径+边缘情况）

\- 推荐测试集：5个示例（正常路径+2个边缘情况+错误场景+复杂情况）

\- 每个示例必须包含：具体输入（真实数据，非占位符）、完整期望输出（实际内容）、理由（为什么这个示例重要）

\## 3. 不同技能类型的专门开发技巧

\### 3.1 工具调用技能：API集成与MCP整合

工具调用技能是Claude最强大的功能之一，通过Model Context Protocol (MCP)，你可以让Claude直接访问任何外部工具、数据库、API，使Claude从代码生成器转变为真正的工作流集成枢纽\<reference type="end" id=39>。

\*\*MCP集成架构与配置\*\*

MCP集成的核心是将外部服务能力暴露为Claude Code中的工具。插件可以通过两种方式捆绑MCP服务器：

1\. 专用.mcp.json（推荐）：在插件根目录创建.mcp.json

&#x20;  \`\`\`json

&#x20;  {

&#x20;    "database-tools": {

&#x20;      "command": "\${CLAUDE\_PLUGIN\_ROOT}/servers/db-server",

&#x20;      "args": \["--config", "\${CLAUDE\_PLUGIN\_ROOT}/config.json"],

&#x20;      "env": {

&#x20;        "DB\_URL": "\${DB\_URL}"

&#x20;      }

&#x20;    }

&#x20;  }
```



1. 内联在 plugin.json 中：在 plugin.json 添加 mcpServers 字段



```
{

&#x20; "name": "my-plugin",

&#x20; "version": "1.0.0",

&#x20; "mcpServers": {

&#x20;   "plugin-api": {

&#x20;     "command": "\${CLAUDE\_PLUGIN\_ROOT}/servers/api-server",

&#x20;     "args": \["--port", "8080"]

&#x20;   }

&#x20; }

}
```

**MCP 服务器类型与使用场景**

MCP 支持四种服务器类型：



| 类型    | 传输方式      | 最佳用途        | 认证方式  | 典型配置               |
| ----- | --------- | ----------- | ----- | ------------------ |
| stdio | 进程        | 本地工具、自定义服务器 | 环境变量  | 本地数据库连接            |
| SSE   | HTTP      | 托管服务、云 API  | OAuth | Asana、GitHub 等官方服务 |
| HTTP  | REST      | API 后端、令牌认证 | 令牌    | 自定义 API            |
| ws    | WebSocket | 实时、流式       | 令牌    | 实时数据同步             |

**工具命名规范与安全实践**

MCP 工具命名遵循严格规范，格式为：`mcp__plugin_<plugin-name>_<server-name>__<tool-name>`。例如，插件名为 asana，服务器名为 asana，工具名为 create\_task，则完整名称为`mcp__plugin_asana_asana__asana_create_task`。

安全最佳实践包括：



* 使用 HTTPS/WSS：始终使用安全连接

* 令牌管理：使用环境变量存储令牌，不要硬编码

* 权限范围：只预授权必要的 MCP 工具，避免使用通配符

* 错误处理：提供回退行为，通知用户连接问题

**工具调用模式与集成策略**

工具调用可采用三种集成模式：



1. 简单工具包装器：命令使用 MCP 工具并与用户交互



```
\# Command: create-item.md

\---

allowed-tools: \["mcp\_\_plugin\_name\_server\_\_create\_item"]

\---

Steps:

1\. Gather item details from user

2\. Use mcp\_\_plugin\_name\_server\_\_create\_item

3\. Confirm creation
```



1. 自主智能体：智能体自主使用 MCP 工具



```
\# Agent: data-analyzer.md

Analysis Process:

1\. Query data via mcp\_\_plugin\_db\_server\_\_query

2\. Process and analyze results

3\. Generate insights report
```



1. 多服务器插件：集成多个 MCP 服务器



```
{

&#x20; "github": {

&#x20;   "type": "sse",

&#x20;   "url": "https://mcp.github.com/sse"

&#x20; },

&#x20; "jira": {

&#x20;   "type": "sse",

&#x20;   "url": "https://mcp.jira.com/sse"

&#x20; }

}
```

### 3.2 知识库问答技能：RAG 架构与语义理解

知识库问答技能是企业级应用中的核心能力，在构建基于 Claude3 的智能问答系统过程中，知识库的质量直接决定了系统的响应准确性、信息覆盖广度以及语义理解深度[(54)](https://blog.csdn.net/weixin_30356433/article/details/152112523)。

**RAG 架构设计与实现**

检索增强生成（RAG）架构是提升问答准确性的关键技术。在本指南中，我们将演示如何使用 Claude 文档作为知识库构建和优化 RAG 系统，包括使用内存向量数据库和 Voyage AI 的嵌入来设置基本的 RAG 系统[(56)](https://github.com/anthropics/claude-cookbooks/blob/main/capabilities/retrieval_augmented_generation/guide.ipynb)。

RAG 架构的核心组件包括：



* 知识源：企业内部文档、产品手册、常见问题等

* 文档预处理：文本清洗、分段、格式标准化

* 嵌入生成：将文本转换为向量表示

* 向量存储：高效的向量检索数据库

* 查询处理：用户问题的语义理解和向量转换

* 结果检索：基于相似度的相关文档检索

* 答案生成：结合检索结果生成最终答案

**知识库构建最佳实践**

构建企业级知识问答系统的第一步是建立全面、权威且持续更新的知识来源体系。在知识库预处理阶段，应集成正则匹配 + 预训练 NER 模型（如 SpaCy、BERT-based NER）对文本中的个人身份信息（PII）进行自动识别与脱敏[(54)](https://blog.csdn.net/weixin_30356433/article/details/152112523)。

知识库构建的关键步骤：



1. 知识收集：整合企业内外部知识源

2. 知识清洗：去除噪声、重复和无关信息

3. 知识结构化：将非结构化文本转换为结构化格式

4. 知识验证：确保信息的准确性和时效性

5. 知识更新：建立定期更新机制

**语义理解与答案生成技巧**

语义理解是问答系统的核心，通过设计高质量提问模板，引导模型生成符合预期的回答。RAG 架构结合检索与生成的混合架构，提升回答准确性[(59)](https://blog.51cto.com/universsky/14028306)。

在实际应用中，可以这样设计：



```
你是XX企业的智能客服，必须基于提供的知识库内容回答问题。

1\. 优先使用知识库中的具体条款（引用章节编号）

2\. 如果知识库没有直接答案，基于相关内容进行推理

3\. 无法回答时，应明确告知用户
```

**性能优化与扩展策略**

为了优化技能性能，应遵循以下策略[(91)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en)：



1. 优化 skill.md 大小：将详细文档移至 references/，链接引用而非内联，保持 skill.md 在 5000 字以下

2. 减少启用的技能：评估是否同时启用了超过 20-50 个技能，建议选择性启用

### 3.3 流程自动化技能：状态管理与任务调度

流程自动化技能通过智能编排实现任务委派，是一个基于钩子的框架，强制将任务委派给专业智能体，通过智能编排实现结构化工作流和专家级任务处理[(66)](https://github.com/barkain/claude-code-workflow-orchestration)。

**状态管理架构设计**

流程自动化的核心是状态管理，采用 JSON 优先的状态管理：任务状态完全存储在.task/impl-\*.json 文件中作为单一事实来源，实现无状态漂移的程序化编排[(68)](https://www.npmjs.com/package/claude-code-workflow)。

状态管理的关键特性包括：



* 自动会话保存：在会话结束时保存状态，备份完整对话记录，永不丢失上下文

* 文件变更跟踪：监控重要文件编辑，记录 decisions.md、README、代码变更，创建审计轨迹

* 智能阻塞检测：检测 "can't"、"blocked by"、"waiting for" 等阻塞状态，跟踪活跃阻塞并在下一会话中显示[(69)](https://github.com/Toowiredd/claude-skills-automation)

**任务调度与工作流设计**

任务调度采用基于规则的触发系统，通过 skill-rules.json 的智能触发系统，结合 UserPromptSubmit 钩子实现：技能定义（每个技能的触发条件和行为）、优先级设置（控制技能激活的紧急程度）、block 模式（使用前必须激活的护栏功能）[(72)](https://blog.csdn.net/gitblog_00046/article/details/139055225)。

典型的工作流设计包括：



1. 触发定义：明确什么情况下启动流程

2. 步骤分解：将复杂任务分解为多个子步骤

3. 条件判断：根据不同情况执行不同路径

4. 状态保存：在关键节点保存进度

5. 错误处理：定义错误时的回滚或重试机制

**自动化执行模式**

自动化执行可采用多种模式，其中一种创新方式是通过脚本自动保存任务状态，实现断点恢复。另一种是基于容器的持续运行模式，为了让智能体可以自主持续运行，可构建一个简单的框架，在独立的 Docker 容器里跑一个 while true 循环，核心逻辑是：在一个无限循环里调用 Claude，跳过权限确认让它可以自主执行任何操作，任务指令从 AGENT\_PROMPT 文件读取，每次运行的日志都记录下来[(148)](https://www.iesdouyin.com/share/video/7604517615100251428/?region=\&mid=7604517571848719131\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&share_sign=geUUpBcsqz_8ky7QAWtnICWo3JkcL2Ugz_SdBsktDzg-\&share_version=280700\&ts=1770630087\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)。

### 3.4 文档创建技能：模板设计与格式控制

文档创建技能是 Claude Skills 体系中的重要组成部分，属于第一类：文档与资产创建，用于创建一致、高质量的输出，包括文档、演示文稿、应用、设计、代码等[(91)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en)。

**内置文档技能功能**

Anthropic 提供了四个强大的内置文档技能[(79)](https://github.com/anthropics/claude-cookbooks/blob/main/skills/README.md)：



* PDF (pdf)：创建带文本、表格和图像的格式化 PDF 文档

* Word (docx)：生成具有丰富格式和结构的 Word 文档

* PowerPoint (pptx)：专业的 PowerPoint 生成，包括正确的幻灯片布局和格式、演讲者备注、品牌一致的样式

* Excel (xlsx)：创建表格、分析数据、生成带图表的报告

这些技能的工作流程可分为 5 个步骤，全程自动化无需手动干预：指令加载（加载 Skill 的完整指令层，明确执行流程与边界）、资源调用（按需加载脚本、参考文档等资源，执行自动化操作）[(160)](https://blog.csdn.net/m0_55049655/article/details/156996073)。

**自定义文档技能开发**

创建自定义文档技能时，应遵循标准的技能结构[(79)](https://github.com/anthropics/claude-cookbooks/blob/main/skills/README.md)：



```
my\_skill/

├── SKILL.md # 必需：Claude的指令

├── scripts/ # 可选：可执行代码

├── references/ # 可选：参考文档

└── assets/ # 可选：模板、样式等
```

**模板设计最佳实践**

模板设计应考虑以下要素：



1. 样式一致性：定义统一的字体、颜色、布局标准

2. 内容结构：设计清晰的章节和段落层次

3. 数据绑定：创建可动态填充的内容区域

4. 条件渲染：根据不同情况显示不同内容

5. 输出格式：支持多种输出格式（PDF、Word、PPT 等）

### 3.5 数据分析技能：处理、可视化与洞察生成

数据分析技能是 Claude 在企业应用中的重要能力，通过 Memory 功能可以实现高效的数据处理流程：清洗→验证→分析→可视化，使用的工具包括 Python/Pandas/Tableau 等。

**数据处理技能设计**

数据处理技能应采用模块化设计，例如数据处理相关的技能可以有：data-query（查询）、data-clean（清洗）、data-visualize（可视化），每个技能独立维护，按需组合，大大降低了管理成本[(84)](https://blog.csdn.net/abc50319/article/details/157275060)。

典型的数据处理流程：



1. 数据获取：从各种数据源读取数据

2. 数据清洗：处理缺失值、异常值、格式转换

3. 数据验证：检查数据完整性和一致性

4. 数据分析：统计分析、机器学习建模

5. 结果可视化：生成图表和报告

**可视化技能开发**

Claude 可以直接在聊天中创建可视化，支持的图表类型包括柱状图、折线图、散点图、饼图和热图。为了获得准确结果，需要明确说明需求[(87)](https://blog.coupler.io/how-to-use-claude-ai-for-data-analytics/)。

可视化设计原则[(85)](https://www.iesdouyin.com/share/note/7532430265635261746/?region=\&mid=7430689043853477951\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&schema_type=37\&share_sign=vrJnsy3xaA81jyjoAwGWXupFqdfoPeursBCwxdyNd7U-\&share_version=280700\&ts=1770630032\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)：



* 简洁性：去除视觉杂乱，突出关键信息

* 清晰性：确保数据表达明确无误

* 一致性：在整个可视化中保持一致的设计元素

* 可访问性：考虑色盲友好和对比度等因素

* 突出洞察：强调数据中最重要的发现

* 上下文提供：解释数据的背景和意义

**交互式仪表板开发**

通过 Artifacts 功能，可以创建交互式仪表板。Artifacts 是 Claude 创建的 "独立内容"—— 可以是交互式网页、代码工具、数据可视化图表，甚至是小游戏。开发时需要明确说明交互：别只说 "做个图表"，说清楚 "点击可以筛选数据" 等交互功能[(88)](https://juejin.cn/post/7579451710303109146)。

### 3.6 对话流程设计：多轮交互与意图识别

对话流程设计是技能开发中的关键环节，需要处理多轮交互、用户意图识别和上下文维护等复杂问题。

**多轮对话管理策略**

现代大语言模型的成熟使得系统不再局限于简单的关键词匹配或固定流程应答，而是具备了理解复杂语义、维持多轮对话、识别用户情绪并生成个性化回复的能力[(89)](https://blog.csdn.net/weixin_42452483/article/details/152085407)。

多轮对话的关键要素：



1. 对话状态跟踪：记录当前对话的进度和上下文

2. 意图识别：理解用户的真实需求

3. 对话策略：根据用户意图选择合适的回应策略

4. 上下文维护：保持对话的连贯性

5. 结束判断：确定何时结束对话或进入下一轮

**意图识别与分类**

意图识别需要建立清晰的触发规则，例如在客户服务场景中：



* 永远不要承诺不在公开路线图上的功能

* 如果客户看起来沮丧，使用同理心语气，在提供解决方案前先承认他们的感受[(92)](https://www.eesel.ai/blog/claude-code-prompt-engineering)

避免使用负面语言：避免使用 "我不能" 或 "那不是我的工作" 等词汇，始终专注于解决方案。保持冷静和专业，即使客户心烦或粗鲁[(94)](https://chatway.app/blog/customer-service-training-tips-best-practices)。

**对话流程优化技巧**

对话流程优化应遵循以下原则：



1. 清晰的流程引导：让用户清楚知道当前步骤和下一步

2. 智能的上下文理解：利用历史对话信息

3. 灵活的交互方式：支持多种输入方式（文本、语音、按钮等）

4. 及时的反馈机制：对用户输入做出及时响应

5. 优雅的错误处理：处理用户输入错误时保持友好

## 4. 行业适配与场景化开发技巧

### 4.1 通用应用场景：客服、教育、创作等

不同应用场景对技能设计有不同的要求，需要根据具体需求进行定制化开发。

**客户服务场景**

在客户服务领域，Claude Skills 可以帮助提供一致、高质量的客户服务，减少工作量[(90)](https://lasserouhiainen.com/claude-skills-guide/)。典型的客户服务技能设计应包含：



1. 标准化回复模板：针对常见问题提供标准回复

2. 智能转接机制：识别无法处理的问题并转人工

3. 情绪识别与响应：根据用户情绪调整回复策略

4. 知识库集成：快速检索相关信息

5. 工单管理：创建和跟踪服务请求

客户服务技能的最佳实践包括：



* 始终使用积极语言，避免负面表达

* 保持专业和耐心，即使面对情绪激动的客户

* 提供清晰的解决方案，避免模糊回答

* 及时记录对话内容，便于后续跟进

**教育场景**

在教育领域，MagicSchool 等平台展示了 Claude 在教育中的强大应用。该平台的写作反馈工具体现了负责任的 AI 辅助学习：教师可以为每个作业定制评估标准，学生上传草稿后收到符合教师期望的即时、建设性反馈。"学生在提交前有低风险的机会改进他们的文章，教师得到更高质量的文章进行评分"，学生还可以与 AI 就反馈进行互动，加深理解[(93)](https://www.anthropic.com/customers/magicschool)。

教育场景的技能设计要点：



1. 个性化学习路径：根据学生水平提供定制化内容

2. 实时反馈机制：对学生回答提供即时反馈

3. 知识图谱构建：建立知识点之间的关联

4. 评估体系设计：设计科学的评估标准和方法

5. 数据驱动分析：分析学生学习行为和效果

**内容创作场景**

内容创作场景需要技能具备创意生成和风格控制能力：



1. 创意激发：提供创作思路和灵感

2. 风格模仿：学习特定作者或品牌的写作风格

3. 结构设计：帮助组织内容结构

4. 质量检查：语法、逻辑、可读性检查

5. 多语言支持：支持多种语言的内容创作

### 4.2 垂直行业适配：金融、医疗、法律等

垂直行业对技能开发有特殊的合规和专业要求，需要深入理解行业特性。

**金融行业应用**

金融行业对 AI 应用有严格的合规要求，同时也有巨大的应用需求。在金融、法律等专业领域，Claude Opus 4.6 的表现尤为亮眼，在 GDPval-AA 基准测试中，其比行业下一最佳模型高出 144 个 Elo 分，比 Opus 4.5 高出 190 个 Elo 分，意味着在约 70% 的金融、法律相关知识工作任务中，其表现优于同类模型[(96)](http://m.toutiao.com/group/7603911855332934159/?upstream_biz=doubao)。

金融领域的典型应用包括：



1. 风险管理：分析市场数据，识别潜在风险模式

2. 合规审查：自动检查合同文件是否符合监管要求

3. 投资分析：分析投资机会，提供决策支持

4. 财务报表分析：自动分析财务报表，识别异常

5. 交易监控：实时监控交易行为，识别异常交易

在金融领域，Claude Skill 可整合客户交易数据、风险模型和监管规则，生成个性化投资建议并自动完成合规性检查[(97)](https://blog.csdn.net/universsky2015/article/details/153741298)。

**医疗行业应用**

医疗行业对 AI 应用的合规要求最为严格，Anthropic 推出了专门的 Claude for Healthcare 产品。这不是一个实验室产品，而是一套完整的 HIPAA 合规医疗 AI 工具包，面向医疗机构、保险公司和个人用户全面开放。对于医院、诊所、保险公司，Claude 提供 HIPAA 合规的工具，可以加速三大场景：护理协调和患者消息分类，所有连接器都符合 HIPAA 要求。

医疗场景的技能设计要点：



1. HIPAA 合规性：确保所有数据处理符合 HIPAA 要求

2. 医学术语理解：准确理解和使用医学专业术语

3. 患者隐私保护：严格保护患者隐私信息

4. 临床决策支持：提供基于证据的医疗建议

5. 药物相互作用分析：分析药物之间的相互作用

在具体应用中，Claude 可以处理预先授权：聊天机器人可以 "从 CMS 或定制政策中提取覆盖要求，以符合 HIPAA 的方式对照患者记录检查临床标准，然后提出决定并附带支持材料供付款人审查"[(102)](https://www.beckershospitalreview.com/healthcare-information-technology/ai/anthropic-rolls-out-claude-for-healthcare/)。

**法律行业应用**

法律行业是 AI 应用的重要领域，具有巨大的效率提升空间。法律插件的核心功能包括：审核合同、排查风险条款。在所有插件中，法律插件是引发股市暴跌的导火索，现在这个插件能自动扫描合同，告诉你哪里有坑，哪里不符合规定。虽然它还不能完全替代大律师的判断，但它能把初级律师几天的工作量压缩到几秒钟[(99)](https://www.iesdouyin.com/share/note/7604198644098534706/?region=\&mid=6869039835424753672\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&schema_type=37\&share_sign=G9I0cIdhWkOWuTAJ16oCTu9sfIFOz0H5gygJLedSK2k-\&share_version=280700\&ts=1770630038\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)。

法律场景的典型应用：



1. 合同审查：自动审查合同条款，识别风险点

2. 法律研究：检索相关法律条文和判例

3. 案例分析：分析类似案例，提供参考

4. 合规检查：检查业务行为是否符合法律要求

5. 法律文书生成：自动生成各类法律文书

在实际应用中，可以加载 "合同分析技能"，自动对比中美合同条款差异，生成结构化差异报告并标记法律风险点。在法律场景中，可以检索《民法典》条款和过往判例，回答 "连带责任担保期限如何认定" 等问题，并引用具体条文[(97)](https://blog.csdn.net/universsky2015/article/details/153741298)。

### 4.3 行业合规与数据安全标准

不同行业有不同的合规要求，技能开发必须考虑这些要求以确保应用的合法性和安全性。

**医疗行业合规标准**

在医疗领域，最重要的是 HIPAA 合规性。Anthropic 已将 Claude for Healthcare 定位为通过 AWS Bedrock、Google Cloud 和 Microsoft Azure 在商业伙伴协议（BAA）下运行，满足 HIPAA 安全规则对受保护健康信息的标准[(103)](https://www.paubox.com/blog/anthropic-brings-claude-ai-to-healthcare-with-hipaa-tools)。

HIPAA 合规的关键要求：



1. 数据加密：传输和存储过程中的数据加密

2. 访问控制：严格的身份验证和访问控制

3. 审计日志：完整的操作审计记录

4. 数据最小化：只收集必要的健康信息

5. 隐私保护：保护患者隐私，防止信息泄露

企业客户可以使用签署 BAA 的 Claude API，当在符合 HIPAA 的云环境中正确配置时，Claude 可以满足 HIPAA 要求的管理、物理和技术保障措施[(106)](https://www.hipaavault.com/resources/hipaa-compliant-hosting-insights/hipaa-compliant-ai-chatbot/)。

**金融行业合规标准**

金融行业面临多重合规要求，包括：



1. SOX（萨班斯 - 奥克斯利法案）：财务报告合规

2. GDPR（通用数据保护条例）：数据保护

3. PCI-DSS（支付卡行业数据安全标准）：支付安全

4. 行业特定法规：如 SEC、CFPB 等监管要求

在实际应用中，可以使用 CLAUDE MD Compliance 工具同时检查所有标准（HIPAA、SOX、GDPR、PCI-DSS），创建审计轨迹，并行验证所有控制措施，收集所有合规工件[(107)](https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-Compliance/de9922b5355c2c23e82387c587ecec5fade9a645)。

**通用安全标准**

无论哪个行业，都应遵循以下安全标准[(114)](https://github.com/alirezarezvani/claude-code-skill-factory/blob/dev/SECURITY.md)：



* 传输加密（TLS 1.2+）

* 审计日志（所有 PHI/PII 访问）

* 访问控制（基于角色）

* 数据最小化

* 保留策略

* 删除权

* 临床安全

### 4.4 场景化技能设计策略

场景化设计需要深入理解用户在特定场景下的需求和行为模式，设计出真正实用的技能。

**场景分析与需求识别**

场景化设计的第一步是进行深入的场景分析：



1. 角色分析：明确使用技能的用户角色（如医生、律师、教师等）

2. 任务分析：识别该角色在特定场景下的核心任务

3. 痛点识别：找出用户在完成任务时遇到的主要困难

4. 需求定义：将用户需求转化为具体的功能要求

5. 约束条件：考虑行业规范、时间限制、资源限制等

**场景化技能设计要素**

针对不同场景，技能设计应包含以下要素：



1. **用户角色适配**：

* 明确的角色定义和权限控制

* 符合角色认知的交互方式

* 专业术语的正确使用

1. **场景上下文理解**：

* 场景相关的知识库集成

* 场景特定的规则和流程

* 实时环境信息的获取和处理

1. **交互流程优化**：

* 符合场景习惯的操作流程

* 减少不必要的交互步骤

* 智能的默认值和推荐选项

1. **输出格式定制**：

* 符合行业标准的输出格式

* 场景特定的数据展示方式

* 可定制的报告模板

1. **错误处理策略**：

* 场景特定的错误类型识别

* 符合行业规范的错误处理流程

* 友好的错误提示和解决方案

## 5. 分层级技能开发策略（新手到专家）

### 5.1 新手入门级：基础概念与简单技能实现

对于新手开发者，建议从最简单和最常用的功能开始逐步掌握 Claude Code 功能，学习遵循三个关键原则：依赖性（先学习基础概念）、复杂性（先易后难）、使用频率（先学最常用功能）。

**新手学习路径**

推荐的学习路径按顺序包括：



1. 斜杠命令（Slash Commands）⭐️ **从这里开始**

2. 内存（Memory）基础必备

3. 技能（Skills）自动调用能力

4. 子智能体（Subagents）任务委派

5. MCP 外部集成

6. 钩子（Hooks）事件自动化

7. 插件（Plugins）打包解决方案

8. 检查点（Checkpoints）安全实验

9. 高级功能（Advanced Features）高级用户工具

10. CLI 参考命令掌握

**第一个技能开发实践**

以下是新手入门的具体练习步骤[(115)](https://github.com/luongnv89/claude-howto/blob/main/LEARNING-ROADMAP.md)：

**练习 1：安装第一个斜杠命令**



```
mkdir -p .claude/commands

cp 01-slash-commands/optimize.md .claude/commands/
```

**练习 2：创建项目内存**



```
cp 02-memory/project-CLAUDE.md ./CLAUDE.md
```

安装完成后，导航到项目根目录并启动 Claude Code：



```
cd your-project-directory

claude code
```

当 Claude Code 启动时，它会立即扫描存储库并建立对代码库的初步理解[(121)](https://www.datacamp.com/tutorial/claude-code-2-1-guide)。

**简单技能开发示例**

创建一个简单的代码审查技能：



1. 创建技能目录



```
mkdir my-code-review-skill

cd my-code-review-skill
```



1. 创建 SKILL.md 文件



```
\---

name: code-review

description: Reviews code for best practices, potential bugs, and maintainability. Use when reviewing pull requests, checking code quality, analyzing diffs, or when user mentions "review", "pr", "code quality", or "best practices".

\---

\# Code Review Skill

\## Instructions

\### Step 1: Code Analysis

Review the provided code for:

\- Code quality and style

\- Potential bugs or issues

\- Test coverage

\- Documentation needs

\### Step 2: Security Review

Check for security vulnerabilities including:

\- SQL injection

\- XSS attacks

\- Authentication issues

\### Step 3: Best Practices

Verify adherence to best practices:

\- Proper error handling

\- Efficient algorithms

\- Clean code structure
```



1. 安装技能



```
\# 对于Claude Code

cp -r my-code-review-skill \~/.claude/skills/

\# 对于Claude.ai

zip -r my-code-review-skill.zip my-code-review-skill

\# 在Settings > Features中上传
```

### 5.2 进阶提升级：性能优化与复杂逻辑实现

进阶开发者需要掌握更高级的技能开发技术，包括性能优化、复杂逻辑实现和团队协作等。

**性能优化策略**

进阶开发者应掌握以下性能优化技术：



1. **Token 优化技巧**

* 使用平台级缓存（如 Amazon Bedrock），自动存储重复前缀，可减少延迟 50-75%，缓存命中时成本降低 75%[(129)](https://claude3.pro/performance-tuning-claude-best-practices/)

* 优化提示词结构，减少不必要的描述

* 使用批量处理，一次处理多个任务

1. **模型选择与参数调优**

* 根据任务复杂度选择合适的模型（Haiku、Sonnet、Opus）

* 使用 effort 参数进行精准成本控制

* 针对特定任务优化模型参数

1. **代码优化技术**

* 技能重构：将抽象的子智能体指令替换为直接调用高效脚本[(132)](https://egghead.io/lessons/optimizing-claude-skills-from-subagents-to-scripts~af2o7)

* 缓存频繁使用的计算结果

* 使用更高效的算法和数据结构

**复杂逻辑实现**

进阶技能通常需要处理复杂的业务逻辑，包括：



1. **状态机设计**

* 定义清晰的状态转换规则

* 实现状态持久化和恢复

* 处理并发和竞态条件

1. **智能决策系统**

* 基于规则的决策引擎

* 机器学习模型集成

* 模糊逻辑和概率推理

1. **异步处理**

* 长时间任务的异步执行

* 进度跟踪和状态报告

* 超时处理和重试机制

**团队协作优化**

进阶开发者还应掌握团队协作技巧：



* 使用清晰、描述性的键名

* 删除过时信息

* 分享有用的模式

* 保持知识的事实性

* 不将个人偏好存储为团队模式

* 不提交敏感信息

* 未经讨论不进行破坏性更改

* 不使用内存进行任务管理（使用适当的工具）[(143)](https://github.com/robwhite4/claude-memory/wiki/Team-Collaboration)

### 5.3 专家优化级：架构设计与规模化部署

专家级开发者需要掌握技能架构设计、规模化部署和高级优化技术。

**技能架构设计**

专家级开发者应深入理解 Skill 架构的核心理念。"文件即 API" 是 Agent Skills 架构的核心理念之一，它通过标准化的文件格式和目录结构，将技能封装为自包含的、可移植的能力单元。该文件采用统一的结构：YAML frontmatter 定义技能的元数据和配置，Markdown 内容提供具体的指令和指南[(137)](https://jishuzhan.net/article/2018131434805444610)。

架构设计的关键要素：



1. 模块化设计：每个 Skill 做一件事，独立封装

2. 层次化结构：技能之间的依赖关系管理

3. 标准化接口：统一的输入输出格式

4. 可扩展性：支持功能的灵活扩展

5. 可维护性：清晰的代码结构和文档

**规模化部署策略**

规模化部署需要考虑以下因素：



1. **版本管理**

* 使用 Git 标签进行版本管理[(141)](https://github.com/travisvn/awesome-claude-skills/blob/main/README.md)

* 建立版本发布流程

* 管理不同环境的版本

1. **部署架构**

* 分布式部署架构

* 负载均衡和高可用性

* 监控和告警系统

1. **性能监控**

* Token 使用量监控

* 响应时间监控

* 错误率监控

* 资源使用情况监控

**高级优化技术**

专家级优化包括：



1. **成本优化**

* 模型选择优化：根据实践数据，通过合理的技能设计可以实现显著的成本节约，从月费$200降到$20，效率反而提升 3 倍

* 批量处理：批量处理可节省 50% 成本[(156)](https://www.anthropic.com/claude/sonnet?_bhlid=7909c707d9be89bb3ab3d44dc3d53729461014fb)

* 缓存策略：使用 Prompt 缓存可节省高达 90% 成本[(156)](https://www.anthropic.com/claude/sonnet?_bhlid=7909c707d9be89bb3ab3d44dc3d53729461014fb)

1. **架构优化**

* 微服务架构：将复杂技能拆分为多个微服务

* 事件驱动架构：基于事件的异步处理

* 流式处理：处理大规模数据流

1. **智能化优化**

* 自适应学习：根据使用模式自动优化

* 智能路由：根据任务类型选择最优处理路径

* 预测性分析：预测用户需求并提前准备

### 5.4 学习路径规划与实践建议

合理的学习路径规划对于技能提升至关重要，需要根据个人情况制定适合的学习计划。

**分阶段学习计划**

根据学习复杂度和时间安排，建议采用以下分阶段学习计划：

**第一阶段：基础掌握（1-2 周）**



* 学习斜杠命令和内存功能

* 掌握基本的技能创建方法

* 完成简单的技能开发练习

* 目标：能够独立开发简单的实用技能

**第二阶段：进阶应用（3-4 周）**



* 学习技能和钩子功能

* 掌握 MCP 集成和子智能体

* 开发复杂的工作流技能

* 目标：能够开发中等复杂度的专业技能

**第三阶段：高级实践（5 周 +）**



* 学习插件和检查点功能

* 掌握高级功能和 CLI 工具

* 进行性能优化和架构设计

* 目标：能够进行企业级技能开发

**实践建议与项目推荐**

以下是一些实践项目建议：



1. **基础项目**

* 代码格式化技能

* 文件转换工具（如 Markdown 转 PDF）

* 简单的数据处理脚本

1. **进阶项目**

* 完整的 API 客户端

* 知识库问答系统

* 自动化测试框架

1. **高级项目**

* 企业级工作流引擎

* 行业特定的智能助手

* 分布式技能协作平台

**学习资源推荐**

持续学习是提升技能的关键，建议关注以下资源：



1. 官方文档：Anthropic 的官方文档和博客

2. 开源社区：GitHub 上的 Claude 技能项目

3. 技术论坛：Claude 开发者社区和 Stack Overflow

4. 实践项目：从简单到复杂逐步挑战

5. 同行交流：加入 Claude 开发者社群

## 6. 企业级技能开发最佳实践

### 6.1 版本管理与发布流程

企业级技能开发需要建立完善的版本管理和发布流程，确保技能的可追溯性和稳定性。

**版本控制策略**

企业级版本控制应遵循以下最佳实践[(141)](https://github.com/travisvn/awesome-claude-skills/blob/main/README.md)：



* 保持描述简洁：front matter 描述用于技能发现

* 使用清晰、可操作的指令：编写指令就像给人类协作者的说明

* 包含示例：在 skill.md 中展示具体示例

* 对技能进行版本控制：使用 Git 标签进行版本管理

版本管理的具体实施：



1. 建立分支策略：使用功能分支工作流

2. 规范命名：修复分支命名为 fix / 问题描述

3. 定期同步：定期 rebase 主分支保持同步

4. 提交规范：编写描述性的 PR 说明，保持提交原子性（一个逻辑变更）

5. 禁止操作：不直接推送 main 分支（受保护），不直接推送 dev 分支（使用 PR），不提交机密或凭证，不混合多个无关变更[(140)](https://github.com/alirezarezvani/claude-skills/blob/main/documentation/WORKFLOW.md)

**发布流程设计**

企业级发布流程应包含以下环节：



1. **开发阶段**

* 功能开发和单元测试

* 代码审查和规范检查

* 集成测试和兼容性测试

1. **测试阶段**

* 功能测试：验证所有功能正常工作

* 性能测试：确保满足性能要求

* 安全测试：检查安全漏洞

* 合规测试：确保符合行业标准

1. **发布阶段**

* 版本标记和记录

* 变更日志生成

* 部署包构建

* 环境部署和验证

1. **监控阶段**

* 运行状态监控

* 性能指标跟踪

* 用户反馈收集

* 问题及时修复

### 6.2 团队协作与权限管理

企业级开发需要强大的团队协作和权限管理功能，确保多人协作的高效性和安全性。

**协作工具与流程**

企业级团队协作应采用以下工具和流程：



1. **Git 协作流程**

* 使用功能分支模型

* 建立代码审查机制

* 实施持续集成 / 持续部署（CI/CD）

1. **项目管理工具**

* 使用 Jira 或 Trello 进行任务跟踪

* 建立清晰的需求管理流程

* 定期进行项目进度评估

1. **知识共享平台**

* 建立内部技能库

* 分享最佳实践和经验教训

* 维护技能文档和使用指南

**权限管理架构**

企业版提供了强大的权限管理功能[(142)](https://www.anthropic.com/news/claude-for-enterprise)：



1. **SSO 集成**

* 支持 SAML 2.0 和 OIDC 标准

* 实现单点登录和集中认证

* 支持域捕获功能

1. **基于角色的访问控制（RBAC）**

* 定义不同角色和权限

* 细粒度的权限控制

* 支持权限继承和组合

1. **工作区管理**

* 支持多工作区隔离

* 工作区级别权限控制

* 工作区数据独立存储

1. **审计与合规**

* 完整的操作审计日志

* 支持合规性报告生成

* 满足行业监管要求

**具体协作实践**

在实际协作中，应遵循以下原则[(143)](https://github.com/robwhite4/claude-memory/wiki/Team-Collaboration)：



* 使用清晰、描述性的键名

* 删除过时信息

* 分享有用的模式

* 保持知识的事实性

* 不将个人偏好存储为团队模式

* 不提交敏感信息

* 未经讨论不进行破坏性更改

* 不使用内存进行任务管理（使用适当的工具）

### 6.3 质量控制与测试体系

建立完善的质量控制体系是确保技能质量和可靠性的关键。

**质量控制流程**

企业级质量控制应建立多层次的测试体系：



1. **单元测试**

* 为每个技能编写单元测试

* 测试基本功能和边界条件

* 确保代码质量和规范性

1. **集成测试**

* 测试技能间的协作

* 验证数据传递和流程正确性

* 检查系统集成的完整性

1. **功能测试**

* 测试完整的业务流程

* 验证用户故事和需求满足情况

* 确保功能符合设计预期

1. **性能测试**

* 测试响应时间和吞吐量

* 验证系统在高负载下的稳定性

* 进行容量规划和性能优化

**自动化测试框架**

建立自动化测试框架可以大大提高测试效率：



1. **测试用例管理**

* 使用标准化的测试用例模板

* 建立测试用例库

* 实施测试用例版本控制

1. **持续集成**

* 配置 CI/CD 流水线

* 自动触发测试流程

* 实时反馈测试结果

1. **测试报告**

* 生成详细的测试报告

* 统计测试覆盖率

* 分析测试结果趋势

**质量标准与规范**

制定明确的质量标准和规范：



1. **代码规范**

* 统一的代码风格和命名规范

* 严格的代码审查标准

* 规范的注释和文档要求

1. **功能规范**

* 清晰的功能定义和边界

* 统一的输入输出格式

* 标准的错误处理流程

1. **性能标准**

* 响应时间要求

* 资源使用限制

* 可扩展性指标

### 6.4 安全合规与审计要求

企业级应用必须满足严格的安全合规要求，建立完善的安全体系。

**安全架构设计**

企业版提供了全面的安全功能：



1. **数据安全**

* 传输加密（TLS 1.2+）

* 存储加密

* 数据访问控制

* 数据最小化原则

1. **身份安全**

* 多因素认证

* 会话管理和超时

* 密码策略和复杂度要求

1. **审计与监控**

* 操作日志记录

* 异常行为检测

* 安全事件响应机制

**合规性管理**

不同行业有不同的合规要求，需要建立相应的合规管理体系：



1. **行业合规**

* 医疗行业：HIPAA 合规

* 金融行业：SOX、GDPR、PCI-DSS 等合规

* 政府机构：特定的安全标准和规范

1. **合规工具**

* 使用 CLAUDE MD Compliance 同时检查所有标准（HIPAA、SOX、GDPR、PCI-DSS）[(107)](https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-Compliance/de9922b5355c2c23e82387c587ecec5fade9a645)

* 建立合规性检查清单

* 定期进行合规性审计

1. **安全最佳实践**

* 最小权限原则：只授予必要的权限

* 定期审查和轮换 token

* 使用 TLS/SSL 加密

* 启用审计日志[(39)](https://blog.csdn.net/weixin_52694742/article/details/157192821)

**技能安全审查**

对技能进行安全审查是企业级应用的必要环节[(113)](https://blog.csdn.net/JuMengXiaoKeTang/article/details/155643914)：



* 最好只使用可信来源的 Skill

* 对自定义 Skill 建立审批 / 审查流程

* 限制 / 禁止从 Skill 中进行网络下载 / 外部调用

* 保持日志与监控

* 对脚本资源做安全审计与签名

特别是对于自定义 Skill，必须建立严格的审查 / 审批 / 权限管理流程，防止恶意代码、外部 payload、数据泄露、供应链攻击等风险[(113)](https://blog.csdn.net/JuMengXiaoKeTang/article/details/155643914)。

### 6.5 成本优化与资源管理

企业级应用需要严格的成本控制和资源管理，确保投资回报率。

**成本优化策略**

企业级成本优化应从多个维度进行：



1. **模型选择优化**

* 根据任务类型选择合适的模型：Haiku（低成本）、Sonnet（平衡）、Opus（高性能）

* 使用 effort 参数进行精准成本控制

* 优化提示词减少 token 消耗

1. **批量处理优化**

* 批量处理可节省 50% 成本[(156)](https://www.anthropic.com/claude/sonnet?_bhlid=7909c707d9be89bb3ab3d44dc3d53729461014fb)

* 实现批量任务的自动分组和处理

* 优化批处理的大小和频率

1. **缓存策略**

* 使用平台级缓存（如 Amazon Bedrock）可减少延迟 50-75%，成本降低 75%[(129)](https://claude3.pro/performance-tuning-claude-best-practices/)

* 实现应用级缓存，减少重复计算

* 优化缓存策略，提高缓存命中率

1. **渐进式披露优化**

* 通过渐进式披露减少 Token 消耗 80% 以上[(161)](http://m.toutiao.com/group/7594756846331396608/?upstream_biz=doubao)

* 合理设计技能结构，按需加载内容

* 优化资源加载顺序，优先加载关键内容

**资源管理体系**

建立完善的资源管理体系：



1. **资源监控**

* 监控 token 使用量和成本

* 跟踪计算资源使用情况

* 分析资源使用趋势

1. **配额管理**

* 为不同用户或团队设置资源配额

* 实施优先级管理

* 建立资源申请和审批流程

1. **成本分析**

* 建立成本核算模型

* 分析不同项目的成本构成

* 制定成本优化方案

**实际成本优化案例**

根据实践经验，通过合理的优化策略可以实现显著的成本节约。一个实际案例显示，通过优化模型选择和使用策略，月费从$200降到$20，效率反而提升了 3 倍。

具体优化措施包括：



* 优先使用 Haiku 模型处理简单任务（成本约 \$0.25 / 百万 token）

* 使用 Sonnet 模型处理标准任务（成本约 \$3 / 百万 token）

* 仅在必要时使用 Opus 模型（成本约 \$15 / 百万 token）

* 实施批量处理和缓存策略

### 6.6 规模化部署与监控策略

企业级应用需要支持大规模部署和实时监控，确保系统的稳定性和可靠性。

**规模化部署架构**

企业级部署需要考虑以下架构设计：



1. **分布式架构**

* 使用微服务架构实现分布式部署

* 建立负载均衡机制

* 实现服务发现和注册

1. **多环境管理**

* 开发环境：用于技能开发和测试

* 测试环境：用于集成测试和性能测试

* 生产环境：正式对外提供服务

* 建立环境间的部署流程

1. **容器化部署**

* 使用 Docker 进行容器化封装

* 使用 Kubernetes 进行容器编排

* 实现弹性伸缩和自动部署

**监控与告警体系**

建立完善的监控和告警体系：



1. **监控指标**

* 系统性能指标（CPU、内存、磁盘、网络）

* 应用性能指标（响应时间、吞吐量、错误率）

* 业务指标（处理量、成功率、用户活跃度）

* 成本指标（token 消耗、费用统计）

1. **告警策略**

* 设置合理的告警阈值

* 支持多种告警方式（邮件、短信、即时通讯）

* 建立告警分级和处理流程

1. **日志管理**

* 统一的日志格式和标准

* 日志收集和分析平台

* 日志存储和备份策略

**性能优化与扩展**

规模化部署需要考虑性能扩展：



1. **水平扩展**

* 通过增加服务器数量提高处理能力

* 实现无状态服务的负载均衡

* 支持自动扩缩容

1. **垂直扩展**

* 升级硬件配置提高单机性能

* 优化软件架构提高处理效率

* 使用更高效的算法和数据结构

1. **智能优化**

* 基于机器学习的性能预测

* 智能的资源调度和分配

* 自适应的负载均衡策略

通过以上企业级最佳实践的实施，可以确保 Claude 技能在企业环境中的稳定、安全、高效运行，为企业带来真正的价值和竞争优势。

## 7. 总结与展望

### 7.1 核心技巧回顾与要点总结

经过全面深入的研究，我们已经系统地梳理了 Claude 技能编写的各类技巧和最佳实践。这些技巧涵盖了从基础概念到高级应用，从个人开发到企业级部署的各个层面。

**基础技能编写核心要点**

基础技能编写的成功关键在于严格遵循规范和最佳实践。YAML frontmatter 的正确定义是技能可发现性的基础，其中 name 字段必须使用 kebab-case 格式，description 字段必须同时包含功能描述和触发条件。渐进式披露架构通过三层加载机制实现了 Token 效率与功能深度的完美平衡，第一层元数据常驻内存（约 100 tokens），第二层指令正文在触发时加载（通常 < 5k tokens），第三层资源按需加载（几乎无限）。

提示词工程遵循清晰直接、提供上下文、使用示例、鼓励推理、定义输出格式、利用并行工具等核心原则[(40)](https://github.com/ThamJiaHe/claude-prompt-engineering-guide)。错误处理采用三层防御架构，确保优雅降级而非崩溃，遵循具体异常优先、建设性消息、防御性编程、完善日志、优雅降级等原则[(27)](https://blog.csdn.net/gitblog_00757/article/details/151090171)。

**不同技能类型的专门技巧**

工具调用技能通过 MCP 协议实现与外部系统的集成，支持 stdio、SSE、HTTP、WebSocket 四种服务器类型，每种都有其特定的应用场景和配置方法。知识库问答技能采用 RAG 架构，通过检索增强生成提升回答准确性，关键在于知识库质量和语义理解能力的提升[(56)](https://github.com/anthropics/claude-cookbooks/blob/main/capabilities/retrieval_augmented_generation/guide.ipynb)。

流程自动化技能通过状态管理和任务调度实现复杂工作流的自动化，采用 JSON 优先的状态管理确保无状态漂移[(68)](https://www.npmjs.com/package/claude-code-workflow)。文档创建技能利用内置的 PDF、Word、PowerPoint、Excel 技能或自定义模板实现高质量文档的自动生成[(79)](https://github.com/anthropics/claude-cookbooks/blob/main/skills/README.md)。数据分析技能通过模块化设计实现数据查询、清洗、可视化的一体化处理[(84)](https://blog.csdn.net/abc50319/article/details/157275060)。

**行业适配与场景化设计**

不同行业对技能开发有不同的要求和挑战。金融行业需要严格的合规性和安全性，Claude Opus 4.6 在金融、法律相关任务中表现突出，比行业最佳模型高出 144 个 Elo 分[(96)](http://m.toutiao.com/group/7603911855332934159/?upstream_biz=doubao)。医疗行业必须满足 HIPAA 合规要求，Anthropic 提供了完整的 HIPAA 合规医疗 AI 工具包。法律行业的合同审查技能可以将初级律师几天的工作量压缩到几秒钟[(99)](https://www.iesdouyin.com/share/note/7604198644098534706/?region=\&mid=6869039835424753672\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&schema_type=37\&share_sign=G9I0cIdhWkOWuTAJ16oCTu9sfIFOz0H5gygJLedSK2k-\&share_version=280700\&ts=1770630038\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)。

场景化设计需要深入理解用户角色、任务需求、交互习惯等因素，设计出真正符合用户期望的技能。无论是客户服务、教育培训还是内容创作，都需要根据具体场景进行定制化开发。

**分层级开发策略**

新手入门应从斜杠命令和内存功能开始，遵循依赖性、复杂性、使用频率三个原则逐步学习。进阶开发者需要掌握性能优化、复杂逻辑实现和团队协作技巧，特别是 Token 优化、模型选择和代码重构等技术。专家级开发者则需要关注架构设计、规模化部署和智能化优化，通过微服务架构、事件驱动、流式处理等技术实现企业级应用。

**企业级最佳实践**

企业级技能开发需要建立完善的版本管理、团队协作、质量控制、安全合规、成本优化和监控体系。版本管理使用 Git 标签进行版本控制，遵循功能分支模型和代码审查机制[(141)](https://github.com/travisvn/awesome-claude-skills/blob/main/README.md)。团队协作通过 SSO 集成和基于角色的访问控制实现高效安全的多人协作。质量控制建立多层次的测试体系，包括单元测试、集成测试、功能测试和性能测试。

安全合规需要满足不同行业的特定要求，通过传输加密、访问控制、审计日志等措施确保数据安全[(114)](https://github.com/alirezarezvani/claude-code-skill-factory/blob/dev/SECURITY.md)。成本优化通过模型选择、批量处理、缓存策略等技术实现，实践证明可将成本降低 90% 以上同时提升效率 3 倍。规模化部署采用分布式架构和容器化技术，建立完善的监控和告警体系。

### 7.2 未来发展趋势与技术展望

随着 AI 技术的快速发展和应用场景的不断扩展，Claude 技能开发也将迎来新的机遇和挑战。

**技术发展趋势**



1. **模型能力持续提升**

* Claude 模型的推理能力和理解能力不断增强

* 多模态能力的融合，支持文本、图像、音频等多种输入

* 更强的上下文理解和长期记忆能力

1. **技能生态日益丰富**

* 官方技能库的持续扩展和优化

* 第三方技能市场的形成和发展

* 行业特定技能的标准化和规范化

1. **开发工具不断完善**

* 更智能的技能创建辅助工具

* 可视化的技能设计和调试界面

* 自动化的代码生成和优化工具

1. **集成能力全面增强**

* 与更多外部系统的深度集成

* 标准化的 API 接口和协议

* 跨平台的技能移植和共享

**应用场景拓展**



1. **垂直行业深度应用**

* 制造业的智能生产和质量控制

* 零售业的智能营销和客户服务

* 教育行业的个性化学习和评估

* 娱乐行业的内容创作和推荐

1. **新兴应用领域**

* 元宇宙和虚拟现实的智能交互

* 自动驾驶的决策支持系统

* 物联网的智能数据分析和控制

* 区块链的智能合约审计和执行

1. **人机协作新模式**

* 更加自然和直观的交互方式

* 个性化的智能助手和工作伙伴

* 跨语言和跨文化的协作支持

* 情感理解和同理心交互

**发展建议与行动计划**

基于当前技术发展趋势和市场需求，我们提出以下发展建议：



1. **持续学习和技能提升**

* 紧跟 AI 技术发展步伐，学习最新的模型能力和应用技巧

* 深入研究特定行业的业务知识和规范要求

* 提升跨领域的综合能力和创新思维

1. **注重实践和经验积累**

* 通过实际项目锻炼技能开发能力

* 建立个人的技能库和最佳实践

* 积极参与开源社区和技术交流

1. **关注生态建设和合作**

* 参与官方和第三方技能生态建设

* 与其他开发者建立合作关系

* 共同推动行业标准和规范的制定

1. **重视安全和伦理考量**

* 在技术创新的同时关注安全风险

* 遵循 AI 伦理原则和行业规范

* 确保技术应用的社会价值和责任

### 7.3 行动指南与实践建议

为了帮助读者更好地应用本指南中的技巧，我们提供以下具体的行动指南和实践建议。

**立即行动清单**



1. **基础技能掌握（1-2 天）**

* 下载并安装 Claude Code

* 学习创建第一个斜杠命令

* 掌握基本的技能目录结构

* 完成至少一个简单技能的开发

1. **进阶技能开发（1-2 周）**

* 深入学习技能和钩子功能

* 尝试 MCP 集成和外部工具调用

* 开发一个完整的工作流技能

* 进行性能优化和错误处理

1. **专业技能应用（1 个月）**

* 选择一个专业领域深入研究

* 开发行业特定的专业技能

* 进行实际应用测试和迭代优化

* 建立个人的技能作品集

1. **企业级实践（3 个月 +）**

* 学习团队协作和版本管理

* 掌握安全合规和成本优化技术

* 进行规模化部署和监控实践

* 形成完整的企业级解决方案

**技能开发检查清单**

在开发每个技能时，建议使用以下检查清单：

**设计阶段**

明确技能的核心功能和应用场景

定义清晰的触发条件和使用规则

设计合理的输入输出格式

规划必要的外部集成和工具调用

考虑安全和权限控制要求

**开发阶段**

遵循技能目录结构和命名规范

正确编写 YAML frontmatter

设计清晰的指令流程和步骤

实现完善的错误处理机制

编写充分的测试用例

**测试阶段**

进行功能测试，验证核心功能

进行边界测试，检查异常情况

进行性能测试，确保响应速度

进行安全测试，检查漏洞风险

收集用户反馈，进行迭代优化

**发布阶段**

编写详细的使用文档

建立版本控制和变更记录

配置必要的监控和告警

制定更新和维护计划

建立用户支持和反馈机制

**长期发展建议**



1. **建立学习机制**

* 定期学习官方文档和技术更新

* 关注行业动态和最佳实践

* 参加技术会议和培训课程

* 与其他开发者保持交流

1. **实践项目选择**

* 从简单项目开始，逐步增加复杂度

* 选择有实际价值的应用场景

* 注重项目的可扩展性和复用性

* 建立项目案例库和经验总结

1. **团队协作建议**

* 建立清晰的分工和协作流程

* 实施代码审查和质量控制

* 建立知识共享和传承机制

* 培养团队的创新和学习氛围

1. **职业发展规划**

* 明确个人的技术发展方向

* 建立长期的学习和成长计划

* 积累项目经验和技术成果

* 寻求合适的职业发展机会

通过系统学习和持续实践，相信每一位开发者都能掌握 Claude 技能开发的核心技巧，在 AI 时代创造更大的价值。无论是个人开发者追求技术突破，还是企业团队寻求数字化转型，Claude 技能都将成为您不可或缺的强大工具。让我们共同期待 AI 技术带来的美好未来，在这个充满机遇的时代中不断创新和成长。

**参考资料&#x20;**

\[1] The Complete Guide to Building Skills for Claude(pdf)[ https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en)

\[2] Claude Skills: Creation, Integration, and Best Practices[ https://github.com/enuno/claude-command-and-control/blob/main/docs/best-practices/08-Claude-Skills-Guide.md](https://github.com/enuno/claude-command-and-control/blob/main/docs/best-practices/08-Claude-Skills-Guide.md)

\[3] mellanon /2025-12-17-Claude Code Skills Structure and Usage Guide.md[ https://gist.github.com/mellanon/50816550ecb5f3b239aa77eef7b8ed8d](https://gist.github.com/mellanon/50816550ecb5f3b239aa77eef7b8ed8d)

\[4] Claude Skills: Build repeatable workflows in Claude[ https://zapier.com/blog/claude-skills/](https://zapier.com/blog/claude-skills/)

\[5] claude\_skills/plugins/plugin-creator/skills/claude-skills-overview-2026/SKILL.md at main · Jamie-BitFlight/claude\_skills · GitHub[ https://github.com/Jamie-BitFlight/claude\_skills/blob/main/plugins/plugin-creator/skills/claude-skills-overview-2026/SKILL.md](https://github.com/Jamie-BitFlight/claude_skills/blob/main/plugins/plugin-creator/skills/claude-skills-overview-2026/SKILL.md)

\[6] 🎯 Claude Prompt Engineering Guide[ https://github.com/ThamJiaHe/claude-prompt-engineering-guide](https://github.com/ThamJiaHe/claude-prompt-engineering-guide)

\[7] Awesome Claude Code Skills for Coding & Development[ https://apidog.com/blog/coding-and-development-claude-skills/](https://apidog.com/blog/coding-and-development-claude-skills/)

\[8] Claude 开发者平台 - Claude API Docs[ https://docs.anthropic.com/zh-CN/release-notes/api](https://docs.anthropic.com/zh-CN/release-notes/api)

\[9] 2026 最新 Claude Skills 开发指南:原理、入门及实战案例-CSDN博客[ https://blog.csdn.net/qq\_25893567/article/details/157325390](https://blog.csdn.net/qq_25893567/article/details/157325390)

\[10] Claude官方Skills开箱即用：多场景自动化实战教程[ https://www.iesdouyin.com/share/video/7598737426839784723/?region=\&mid=7598737657404984110\&u\_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with\_sec\_did=1\&video\_share\_track\_ver=\&titleType=title\&share\_sign=FanqxqCcBMkhlEtg8BBYp3kssxIJzNT2AL1r8CZ6GkY-\&share\_version=280700\&ts=1770629942\&from\_aid=1128\&from\_ssr=1\&share\_track\_info=%7B%22link\_description\_type%22%3A%22%22%7D](https://www.iesdouyin.com/share/video/7598737426839784723/?region=\&mid=7598737657404984110\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&share_sign=FanqxqCcBMkhlEtg8BBYp3kssxIJzNT2AL1r8CZ6GkY-\&share_version=280700\&ts=1770629942\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)

\[11] 概览 | Agent Skills 学习及案例[ https://www.claudeskills.org/zh/docs/agent-skills/overview](https://www.claudeskills.org/zh/docs/agent-skills/overview)

\[12] 2026年还在复制粘贴?Anthropic官方:给Claude装个脑子吧\_AI那些事儿[ http://m.toutiao.com/group/7604700839210435124/?upstream\_biz=doubao](http://m.toutiao.com/group/7604700839210435124/?upstream_biz=doubao)

\[13] LLMs之Claude:Claude Skills的简介(并对比Projects/MCP/Custom Instructions)、安装和使用方法、案例应用之详细攻略-CSDN博客[ https://yunyaniu.blog.csdn.net/article/details/153884153](https://yunyaniu.blog.csdn.net/article/details/153884153)

\[14] 让 AI 一次就懂你:Claude 提示工程实战手册\_claude 最佳实践-CSDN博客[ https://blog.csdn.net/weixin\_43954818/article/details/155225739](https://blog.csdn.net/weixin_43954818/article/details/155225739)

\[15] 🎯 Claude Prompt Engineering Guide[ https://github.com/ThamJiaHe/claude-prompt-engineering-guide](https://github.com/ThamJiaHe/claude-prompt-engineering-guide)

\[16] docs: Comprehensive January 2026 update (v2.0.0) #1[ https://github.com/ThamJiaHe/claude-prompt-engineering-guide/pull/1/files](https://github.com/ThamJiaHe/claude-prompt-engineering-guide/pull/1/files)

\[17] How to Write a Good Prompt for Claude: 10 Golden Rules[ https://www.aifire.co/p/how-to-write-a-good-prompt-for-claude-10-golden-rules](https://www.aifire.co/p/how-to-write-a-good-prompt-for-claude-10-golden-rules)

\[18] Claude prompting guide[ https://gist.github.com/pashov/dc6d555a18161ff82860191efa6bb9ab](https://gist.github.com/pashov/dc6d555a18161ff82860191efa6bb9ab)

\[19] claude\_guide/02\_prompt/2.7\_optimization.md at main · yeasy/claude\_guide · GitHub[ https://github.com/yeasy/claude\_guide/blob/main/02\_prompt/2.7\_optimization.md](https://github.com/yeasy/claude_guide/blob/main/02_prompt/2.7_optimization.md)

\[20] Migration Guide: November 2025 → January 2026[ https://github.com/ThamJiaHe/claude-prompt-engineering-guide/blob/main/MIGRATION-NOV2025-JAN2026.md](https://github.com/ThamJiaHe/claude-prompt-engineering-guide/blob/main/MIGRATION-NOV2025-JAN2026.md)

\[21] 长文本提示词技巧 - Claude Docs[ https://docs.anthropic.com/zh-TW/docs/build-with-claude/prompt-engineering/long-context-tips](https://docs.anthropic.com/zh-TW/docs/build-with-claude/prompt-engineering/long-context-tips)

\[22] Claude Code最强Prompt指南:10 步提示词公式让 Claude 输出提升 300%\_老猿视角[ http://m.toutiao.com/group/7601551095302849065/?upstream\_biz=doubao](http://m.toutiao.com/group/7601551095302849065/?upstream_biz=doubao)

\[23] Anthropic CPO 揭秘 7 个 大 语言 模型 提示 词 的 新 玩法 # AI # 大 语言 模型 # 提示 词 # 技巧 # Anthropic[ https://www.iesdouyin.com/share/video/7517227751128976649/?region=\&mid=7517227715423079187\&u\_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with\_sec\_did=1\&video\_share\_track\_ver=\&titleType=title\&share\_sign=Hl6F1WcfSaOxzlP91iqKSyi8bJTfmWCkeEVCMOV\_psg-\&share\_version=280700\&ts=1770629960\&from\_aid=1128\&from\_ssr=1\&share\_track\_info=%7B%22link\_description\_type%22%3A%22%22%7D](https://www.iesdouyin.com/share/video/7517227751128976649/?region=\&mid=7517227715423079187\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&share_sign=Hl6F1WcfSaOxzlP91iqKSyi8bJTfmWCkeEVCMOV_psg-\&share_version=280700\&ts=1770629960\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)

\[24] 别再“邪修”Prompt了!向Claude团队学习如何构建提示词\_trac 提示词 生成-CSDN博客[ https://blog.csdn.net/2301\_81888214/article/details/156071506](https://blog.csdn.net/2301_81888214/article/details/156071506)

\[25] 超棒Claude官方提示词:Anthropic发布Claude 4.x提示工程最佳实践\_不秃头程序员[ http://m.toutiao.com/group/7592455571553878569/?upstream\_biz=doubao](http://m.toutiao.com/group/7592455571553878569/?upstream_biz=doubao)

\[26] claude-plugins-official/plugins/plugin-dev/skills/command-development/SKILL.md at main · anthropics/claude-plugins-official · GitHub[ https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/command-development/SKILL.md](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/command-development/SKILL.md)

\[27] 告别崩溃:Anthropic Cookbook异常处理全攻略-CSDN博客[ https://blog.csdn.net/gitblog\_00757/article/details/151090171](https://blog.csdn.net/gitblog_00757/article/details/151090171)

\[28] Error Handling Tutorial[ https://github.com/athola/claude-night-market/blob/master/book/src/tutorials/error-handling-tutorial.md](https://github.com/athola/claude-night-market/blob/master/book/src/tutorials/error-handling-tutorial.md)

\[29] Claude Skills Best Practices[ https://github.com/featbit/featbit-skills/blob/main/.claude/skills/claude-skills-best-practices/SKILL.md](https://github.com/featbit/featbit-skills/blob/main/.claude/skills/claude-skills-best-practices/SKILL.md)

\[30] Claude Agent SDK Rust - Best Practices[ https://github.com/louloulin/claude-agent-sdk/blob/main/docs/guides/best-practices.md](https://github.com/louloulin/claude-agent-sdk/blob/main/docs/guides/best-practices.md)

\[31] Claude Skills: Creation, Integration, and Best Practices[ https://github.com/enuno/claude-command-and-control/blob/main/docs/best-practices/08-Claude-Skills-Guide.md](https://github.com/enuno/claude-command-and-control/blob/main/docs/best-practices/08-Claude-Skills-Guide.md)

\[32] How Claude Handles Ambiguous Prompts[ https://claude3.pro/how-claude-handles-ambiguous-prompts/](https://claude3.pro/how-claude-handles-ambiguous-prompts/)

\[33] ClaudeCode真经第六章:问题排查与故障处理\_api error: 500 no available claude accounts suppor-CSDN博客[ https://blog.csdn.net/east196/article/details/152558674](https://blog.csdn.net/east196/article/details/152558674)

\[34] Claude 升级 “ 思考 ” 工具 ， AI 也 能 三思而后行 # 人工 智能 # AI # Claude # 显卡 # GPU # Deep Seek[ https://www.iesdouyin.com/share/video/7485941474744356134/?region=\&mid=7485942031131495177\&u\_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with\_sec\_did=1\&video\_share\_track\_ver=\&titleType=title\&share\_sign=ZSBW\_uc7flSUoqrh5lHRwpsV89aluPDfRoxBR5As\_wE-\&share\_version=280700\&ts=1770629973\&from\_aid=1128\&from\_ssr=1\&share\_track\_info=%7B%22link\_description\_type%22%3A%22%22%7D](https://www.iesdouyin.com/share/video/7485941474744356134/?region=\&mid=7485942031131495177\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&share_sign=ZSBW_uc7flSUoqrh5lHRwpsV89aluPDfRoxBR5As_wE-\&share_version=280700\&ts=1770629973\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)

\[35] Claude Code实战8: 高效排错修复问题实战手记\_{"tscode":"tsmqam5rc8"}-CSDN博客[ https://blog.csdn.net/GODYAD/article/details/157143460](https://blog.csdn.net/GODYAD/article/details/157143460)

\[36] claude3如何提升准确\_claude3准确度提升技巧与反馈循环机制-人工智能-PHP中文网[ https://m.php.cn/faq/1762957.html](https://m.php.cn/faq/1762957.html)

\[37] 扩展思考技巧 - Claude Docs[ https://docs.anthropic.com/zh-CN/docs/build-with-claude/prompt-engineering/extended-thinking-tips](https://docs.anthropic.com/zh-CN/docs/build-with-claude/prompt-engineering/extended-thinking-tips)

\[38] MCP Integration for Claude Code Plugins[ https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/mcp-integration/SKILL.md](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/mcp-integration/SKILL.md)

\[39] MCP(Model Context Protocol):连接Claude到任何工具-CSDN博客[ https://blog.csdn.net/weixin\_52694742/article/details/157192821](https://blog.csdn.net/weixin_52694742/article/details/157192821)

\[40] 🎯 Claude Prompt Engineering Guide[ https://github.com/ThamJiaHe/claude-prompt-engineering-guide](https://github.com/ThamJiaHe/claude-prompt-engineering-guide)

\[41] claude-code-plugins-plus-skills/tutorials/plugins/04-mcp-server-plugins.ipynb at main · jeremylongshore/claude-code-plugins-plus-skills · GitHub[ https://github.com/jeremylongshore/claude-code-plugins-plus-skills/blob/main/tutorials/plugins/04-mcp-server-plugins.ipynb](https://github.com/jeremylongshore/claude-code-plugins-plus-skills/blob/main/tutorials/plugins/04-mcp-server-plugins.ipynb)

\[42] MCP Tools Integration[ https://docs.vectorize.io/build-deploy/agents/mcp/mcp-tools/](https://docs.vectorize.io/build-deploy/agents/mcp/mcp-tools/)

\[43] Building Claude-Ready Entra ID-Protected MCP Servers with Azure API Management[ https://devblogs.microsoft.com/blog/claude-ready-secure-mcp-apim](https://devblogs.microsoft.com/blog/claude-ready-secure-mcp-apim)

\[44] Enhance Claude’s Skills with MCP for Improved Workflows[ https://www.gend.co/blog/claude-mcp-skills-enterprise-workflows](https://www.gend.co/blog/claude-mcp-skills-enterprise-workflows)

\[45] 如何实现工具使用 - Claude API Docs[ https://docs.anthropic.com/zh-CN/docs/agents-and-tools/tool-use/implement-tool-use](https://docs.anthropic.com/zh-CN/docs/agents-and-tools/tool-use/implement-tool-use)

\[46] Introducing advanced tool use on the Claude Developer Platform \ Anthropic[ https://www.anthropic.com/engineering/advanced-tool-use?ref=approachwithalacrity.com](https://www.anthropic.com/engineering/advanced-tool-use?ref=approachwithalacrity.com)

\[47] 如何使用claude code实现function call\_claudecode tool call-CSDN博客[ https://leijmdas.blog.csdn.net/article/details/152309208](https://leijmdas.blog.csdn.net/article/details/152309208)

\[48] Claude Code 国内 直连 的 方式 ， 更 推荐 新手 使用 # cursor # claude code # ai 编程 # claude[ https://www.iesdouyin.com/share/video/7584677069901008134/?region=\&mid=7584677118735387434\&u\_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with\_sec\_did=1\&video\_share\_track\_ver=\&titleType=title\&share\_sign=Og2c8nx\_77nBaGvFyxkQ7CEwNbFGEL2Uh0q88xw9iSE-\&share\_version=280700\&ts=1770629990\&from\_aid=1128\&from\_ssr=1\&share\_track\_info=%7B%22link\_description\_type%22%3A%22%22%7D](https://www.iesdouyin.com/share/video/7584677069901008134/?region=\&mid=7584677118735387434\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&share_sign=Og2c8nx_77nBaGvFyxkQ7CEwNbFGEL2Uh0q88xw9iSE-\&share_version=280700\&ts=1770629990\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)

\[49] Tool use完全手册:Claude工具调用工作流实现详解-CSDN博客[ https://blog.csdn.net/gitblog\_00554/article/details/154551980](https://blog.csdn.net/gitblog_00554/article/details/154551980)

\[50] Claude API完全指南:从入门到实战Claude API完全指南:从入门到实战(Python/JS代码详解) 本 - 掘金[ https://juejin.cn/post/7560838912362889256](https://juejin.cn/post/7560838912362889256)

\[51] 🚀 MCP基础完全上手指南:让Claude像开挂一样调用外部工具如果能让Claude直接读取你的GitHub仓库、操作 - 掘金[ https://juejin.cn/post/7572147440314613823](https://juejin.cn/post/7572147440314613823)

\[52] The Complete Guide to Building Skills for Claude[ https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en)

\[53] Build with Claude: Practical Guidance & Best Practices[ https://www.gend.co/blog/build-with-claude-practical-guidance-best-practices](https://www.gend.co/blog/build-with-claude-practical-guidance-best-practices)

\[54] Claude3知识问答百科系统快速信息检索实战部署-CSDN博客[ https://blog.csdn.net/weixin\_30356433/article/details/152112523](https://blog.csdn.net/weixin_30356433/article/details/152112523)

\[55] Claude Skills Best Practices[ https://github.com/featbit/featbit-skills/blob/main/.claude/skills/claude-skills-best-practices/SKILL.md](https://github.com/featbit/featbit-skills/blob/main/.claude/skills/claude-skills-best-practices/SKILL.md)

\[56] claude-cookbooks/capabilities/retrieval\_augmented\_generation/guide.ipynb at main · anthropics/claude-cookbooks · GitHub[ https://github.com/anthropics/claude-cookbooks/blob/main/capabilities/retrieval\_augmented\_generation/guide.ipynb](https://github.com/anthropics/claude-cookbooks/blob/main/capabilities/retrieval_augmented_generation/guide.ipynb)

\[57] Skill Creator[ https://github.com/x-cmd/skill/blob/main/data/anthropics/skill-creator/SKILL.md](https://github.com/x-cmd/skill/blob/main/data/anthropics/skill-creator/SKILL.md)

\[58] Claude AI SKILLS.md Best Practices Guide (2025)[ https://github.com/zebbern/SecOps-CLI-Guides/blob/main/claude\_skills\_guidelines.md](https://github.com/zebbern/SecOps-CLI-Guides/blob/main/claude_skills_guidelines.md)

\[59] Claude 在企业知识管理中的应用:构建智能问答系统的 5 步方案\_禅与计算机程序设计艺术的技术博客\_51CTO博客[ https://blog.51cto.com/universsky/14028306](https://blog.51cto.com/universsky/14028306)

\[60] 深度解析 Claude:如何打造高阶 Skill 以及它与 Tool 的本质区别\_skill工具-CSDN博客[ https://blog.csdn.net/weixin\_66005172/article/details/155633854](https://blog.csdn.net/weixin_66005172/article/details/155633854)

\[61] 三步设计AI技能：黄金法则与高效教学策略解析[ https://www.iesdouyin.com/share/video/7565702361784519971/?region=\&mid=7565702303785831187\&u\_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with\_sec\_did=1\&video\_share\_track\_ver=\&titleType=title\&share\_sign=kso.c1Roqp6W93otr2E66xK2m48oRleIaDsqsqtVtq0-\&share\_version=280700\&ts=1770630004\&from\_aid=1128\&from\_ssr=1\&share\_track\_info=%7B%22link\_description\_type%22%3A%22%22%7D](https://www.iesdouyin.com/share/video/7565702361784519971/?region=\&mid=7565702303785831187\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&share_sign=kso.c1Roqp6W93otr2E66xK2m48oRleIaDsqsqtVtq0-\&share_version=280700\&ts=1770630004\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)

\[62] Claude Skills 深度解析:从 skill-creator 看技能创建最佳实践[ https://skills.deeptoai.com/zh/docs/development/skill-creator-deep-dive](https://skills.deeptoai.com/zh/docs/development/skill-creator-deep-dive)

\[63] AI那些趣事系列117:从入门到实战:Claude Skills 彻底指南 —— 让 AI 像专业助手一样精准干活-CSDN博客[ https://blog.csdn.net/abc50319/article/details/157275060](https://blog.csdn.net/abc50319/article/details/157275060)

\[64] Autonomous Orchestrator Template[ https://github.com/catlog22/Claude-Code-Workflow/blob/main/.claude/skills/skill-generator/templates/autonomous-orchestrator.md](https://github.com/catlog22/Claude-Code-Workflow/blob/main/.claude/skills/skill-generator/templates/autonomous-orchestrator.md)

\[65] Workflow Guide[ https://github.com/travisjneuman/.claude/blob/master/docs/WORKFLOW-GUIDE.md](https://github.com/travisjneuman/.claude/blob/master/docs/WORKFLOW-GUIDE.md)

\[66] Claude Code Workflow Orchestration System[ https://github.com/barkain/claude-code-workflow-orchestration](https://github.com/barkain/claude-code-workflow-orchestration)

\[67] Claude-Code-Workflow/.claude/skills/skill-generator/phases/03-phase-generation.md at main · catlog22/Claude-Code-Workflow · GitHub[ https://github.com/catlog22/Claude-Code-Workflow/blob/main/.claude/skills/skill-generator/phases/03-phase-generation.md](https://github.com/catlog22/Claude-Code-Workflow/blob/main/.claude/skills/skill-generator/phases/03-phase-generation.md)

\[68] claude-code-workflow[ https://www.npmjs.com/package/claude-code-workflow](https://www.npmjs.com/package/claude-code-workflow)

\[69] Claude Skills Automation[ https://github.com/Toowiredd/claude-skills-automation](https://github.com/Toowiredd/claude-skills-automation)

\[70] GitHub - MacroMan5/claude-code-workflow-plugins: Claude Code Plugins is an open-source add-on suite that turns Claude Code into a programmable workspace. It gives you composable workflows, automatic project memory, skill packs, lifecycle hooks, sub-agents, and typed commands—all wired with minimal config.[ https://github.com/MacroMan5/claude-code-workflow-plugins](https://github.com/MacroMan5/claude-code-workflow-plugins)

\[71] Vibe Coding - Claude Code 深度实践\_vibecoding、claude code-CSDN博客[ https://blog.csdn.net/yangshangwei/article/details/154573160](https://blog.csdn.net/yangshangwei/article/details/154573160)

\[72] Claude Code技能自动触发终极指南:精准配置与高效管理-CSDN博客[ https://blog.csdn.net/gitblog\_00046/article/details/139055225](https://blog.csdn.net/gitblog_00046/article/details/139055225)

\[73] Claude Skills Automation[ https://github.com/Toowiredd/claude-skills-automation/](https://github.com/Toowiredd/claude-skills-automation/)

\[74] Claude Skills\_claude skills部署-CSDN博客[ https://blog.csdn.net/m0\_55049655/article/details/156996073](https://blog.csdn.net/m0_55049655/article/details/156996073)

\[75] 2026开年教程!Claude Code七大组件，老金一篇讲明明白白!90%的人只会用1个!上周有个读者私信我: "老金 - 掘金[ https://juejin.cn/post/7589958976226672650](https://juejin.cn/post/7589958976226672650)

\[76] The Complete Guide to Building Skills for Claude[ https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en)

\[77] 2026 最新 Claude Skills 开发指南:原理、入门及实战案例-CSDN博客[ https://blog.csdn.net/qq\_25893567/article/details/157325390](https://blog.csdn.net/qq_25893567/article/details/157325390)

\[78] Claude Skills: Transform Claude from a General-Purpose AI into a Specialized Expert[ https://collabnix.com/claude-skills-transform-claude-from-a-general-purpose-ai-into-a-specialized-expert/](https://collabnix.com/claude-skills-transform-claude-from-a-general-purpose-ai-into-a-specialized-expert/)

\[79] Claude Skills Cookbook 🚀[ https://github.com/anthropics/claude-cookbooks/blob/main/skills/README.md](https://github.com/anthropics/claude-cookbooks/blob/main/skills/README.md)

\[80] Claude Skills Best Practices[ https://github.com/featbit/featbit-skills/blob/main/.claude/skills/claude-skills-best-practices/SKILL.md](https://github.com/featbit/featbit-skills/blob/main/.claude/skills/claude-skills-best-practices/SKILL.md)

\[81] Claude AI SKILLS.md Best Practices Guide (2025)[ https://github.com/zebbern/SecOps-CLI-Guides/blob/main/claude\_skills\_guidelines.md](https://github.com/zebbern/SecOps-CLI-Guides/blob/main/claude_skills_guidelines.md)

\[82] Claude Skills 始め方完全ガイド｜5分で動作確認・業務効率80%向上を実現[ https://blog.scuti.jp/claude-skills-getting-started-guide-5min-quick-start/](https://blog.scuti.jp/claude-skills-getting-started-guide-5min-quick-start/)

\[83] 告别繁琐OCR!Claude 3视觉工具让图表分析效率提升10倍-CSDN博客[ https://blog.csdn.net/gitblog\_00567/article/details/151074696](https://blog.csdn.net/gitblog_00567/article/details/151074696)

\[84] AI那些趣事系列117:从入门到实战:Claude Skills 彻底指南 —— 让 AI 像专业助手一样精准干活-CSDN博客[ https://blog.csdn.net/abc50319/article/details/157275060](https://blog.csdn.net/abc50319/article/details/157275060)

\[85] AI数据可视化工具与最佳实践指南[ https://www.iesdouyin.com/share/note/7532430265635261746/?region=\&mid=7430689043853477951\&u\_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with\_sec\_did=1\&video\_share\_track\_ver=\&titleType=title\&schema\_type=37\&share\_sign=vrJnsy3xaA81jyjoAwGWXupFqdfoPeursBCwxdyNd7U-\&share\_version=280700\&ts=1770630032\&from\_aid=1128\&from\_ssr=1\&share\_track\_info=%7B%22link\_description\_type%22%3A%22%22%7D](https://www.iesdouyin.com/share/note/7532430265635261746/?region=\&mid=7430689043853477951\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&schema_type=37\&share_sign=vrJnsy3xaA81jyjoAwGWXupFqdfoPeursBCwxdyNd7U-\&share_version=280700\&ts=1770630032\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)

\[86] How to Use Claude for Data Analysis: Complete Overview[ https://www.datastudios.org/post/how-to-use-claude-for-data-analysis-complete-overview](https://www.datastudios.org/post/how-to-use-claude-for-data-analysis-complete-overview)

\[87] How to Use Claude.ai for Data Analytics[ https://blog.coupler.io/how-to-use-claude-ai-for-data-analytics/](https://blog.coupler.io/how-to-use-claude-ai-for-data-analytics/)

\[88] Claude用不好浪费钱?10个高级技巧让效率翻3倍深度讲解Claude的Artifacts、Projects、Exte - 掘金[ https://juejin.cn/post/7579451710303109146](https://juejin.cn/post/7579451710303109146)

\[89] Claude智能客服自动化解决方案-CSDN博客[ https://blog.csdn.net/weixin\_42452483/article/details/152085407](https://blog.csdn.net/weixin_42452483/article/details/152085407)

\[90] How to use Claude Skills[ https://lasserouhiainen.com/claude-skills-guide/](https://lasserouhiainen.com/claude-skills-guide/)

\[91] The Complete Guide to Building Skills for Claude[ https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en)

\[92] What Claude Code prompt engineering can teach us about smarter AI support[ https://www.eesel.ai/blog/claude-code-prompt-engineering](https://www.eesel.ai/blog/claude-code-prompt-engineering)

\[93] Customer story | MagicSchool | Claude[ https://www.anthropic.com/customers/magicschool](https://www.anthropic.com/customers/magicschool)

\[94] Customer Service Training: Tips & Best Practices[ https://chatway.app/blog/customer-service-training-tips-best-practices](https://chatway.app/blog/customer-service-training-tips-best-practices)

\[95] Publishing Your Skill[ https://github.com/nbashaw/claude-cs/blob/main/PUBLISHING.md](https://github.com/nbashaw/claude-cs/blob/main/PUBLISHING.md)

\[96] 旗舰迭代|Claude Opus 4.6 重磅登场，重新定义前沿AI能力边界\_AI高效研究所[ http://m.toutiao.com/group/7603911855332934159/?upstream\_biz=doubao](http://m.toutiao.com/group/7603911855332934159/?upstream_biz=doubao)

\[97] Claude skill 原理与应用-CSDN博客[ https://blog.csdn.net/universsky2015/article/details/153741298](https://blog.csdn.net/universsky2015/article/details/153741298)

\[98] Claude在AI人工智能领域的行业应用实践-CSDN博客[ https://blog.csdn.net/weixin\_51960949/article/details/149257546](https://blog.csdn.net/weixin_51960949/article/details/149257546)

\[99] Claude 血洗 全球 软件 业 。 为什么 AI 能 让 卖 软件 的 公司 股价 大跌 ？ Claude Co work 到底 怎么 帮 你 干活 ？ 那 11 个 插件 都是 做 什么 的 ？ 以及 为什么 Anthropic 的 CEO 认为 未来 5 年内 一半 的 初级 白领 工作 可能 会 消失 # ai # claude # 美股 # 股市[ https://www.iesdouyin.com/share/note/7604198644098534706/?region=\&mid=6869039835424753672\&u\_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with\_sec\_did=1\&video\_share\_track\_ver=\&titleType=title\&schema\_type=37\&share\_sign=G9I0cIdhWkOWuTAJ16oCTu9sfIFOz0H5gygJLedSK2k-\&share\_version=280700\&ts=1770630038\&from\_aid=1128\&from\_ssr=1\&share\_track\_info=%7B%22link\_description\_type%22%3A%22%22%7D](https://www.iesdouyin.com/share/note/7604198644098534706/?region=\&mid=6869039835424753672\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&schema_type=37\&share_sign=G9I0cIdhWkOWuTAJ16oCTu9sfIFOz0H5gygJLedSK2k-\&share_version=280700\&ts=1770630038\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)

\[100] Anthropic为Claude模型赋能:集成网络搜索 | zh-CN | allm.link|AI|引文|迭代|法律|数据\_新浪新闻[ https://k.sina.com.cn/article\_7857201856\_1d45362c00190268va.html](https://k.sina.com.cn/article_7857201856_1d45362c00190268va.html)

\[101] Claude Opus 4.6:让AI成为职场全能助手的新突破\_飞翔的SA[ http://m.toutiao.com/group/7603703749340578339/?upstream\_biz=doubao](http://m.toutiao.com/group/7603703749340578339/?upstream_biz=doubao)

\[102] Anthropic rolls out Claude for Healthcare: 7 notes[ https://www.beckershospitalreview.com/healthcare-information-technology/ai/anthropic-rolls-out-claude-for-healthcare/](https://www.beckershospitalreview.com/healthcare-information-technology/ai/anthropic-rolls-out-claude-for-healthcare/)

\[103] Anthropic brings Claude AI to healthcare with HIPAA tools[ https://www.paubox.com/blog/anthropic-brings-claude-ai-to-healthcare-with-hipaa-tools](https://www.paubox.com/blog/anthropic-brings-claude-ai-to-healthcare-with-hipaa-tools)

\[104] Anthropic Launches Claude for Healthcare With HIPAA-Ready AI Tools[ https://blockchain.news/news/anthropic-claude-healthcare-hipaa-ready-launch](https://blockchain.news/news/anthropic-claude-healthcare-hipaa-ready-launch)

\[105] Following in the Footsteps of OpenAI: Anthropic Announces the Launch of Claude AI Healthcare Compliance Service[ https://www.aibase.com/news/24512](https://www.aibase.com/news/24512)

\[106] Can AI Chatbots Be HIPAA-Compliant?[ https://www.hipaavault.com/resources/hipaa-compliant-hosting-insights/hipaa-compliant-ai-chatbot/](https://www.hipaavault.com/resources/hipaa-compliant-hosting-insights/hipaa-compliant-ai-chatbot/)

\[107] CLAUDE MD Compliance[ https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-Compliance/de9922b5355c2c23e82387c587ecec5fade9a645](https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-Compliance/de9922b5355c2c23e82387c587ecec5fade9a645)

\[108] Claude 3.7 Sonnet System Card(pdf)[ https://assets.anthropic.com/m/785e231869ea8b3b/original/claude-3-7-sonnet-system-card.pdf?spm=a2c6h.13046898.publish-article.29.2dbf6ffay8jNp8](https://assets.anthropic.com/m/785e231869ea8b3b/original/claude-3-7-sonnet-system-card.pdf?spm=a2c6h.13046898.publish-article.29.2dbf6ffay8jNp8)

\[109] Claude--AI领域的安全优等生\_\_财经头条\_\_新浪财经[ https://cj.sina.com.cn/articles/view/7879848900/1d5acf3c401902na0q?finpagefr=ttzz\&froms=ttmp](https://cj.sina.com.cn/articles/view/7879848900/1d5acf3c401902na0q?finpagefr=ttzz\&froms=ttmp)

\[110] claude-prompt-engineering-guide/skills/examples/security-compliance.md at dbc3a1306b7f1ec347028417fbb10f21d5d96514 · ThamJiaHe/claude-prompt-engineering-guide · GitHub[ https://github.com/ThamJiaHe/claude-prompt-engineering-guide/blob/dbc3a1306b7f1ec347028417fbb10f21d5d96514/skills/examples/security-compliance.md](https://github.com/ThamJiaHe/claude-prompt-engineering-guide/blob/dbc3a1306b7f1ec347028417fbb10f21d5d96514/skills/examples/security-compliance.md)

\[111] 此次 漏洞 直接 击穿 了 Anthropic 标榜 的 最高 安全 等级 ASL - 3 防护 。&#x20;&#x20;\# 信息 安全 # 等 保 测评 # 等 保证书 # 服务器 # 三级 等 保[ https://www.iesdouyin.com/share/video/7515242763068247322/?region=\&mid=7515242651566885666\&u\_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with\_sec\_did=1\&video\_share\_track\_ver=\&titleType=title\&share\_sign=mlo1avSTDFE.WqqgUbnt4FzHOBYBT7WK59zcrURKGPw-\&share\_version=280700\&ts=1770630046\&from\_aid=1128\&from\_ssr=1\&share\_track\_info=%7B%22link\_description\_type%22%3A%22%22%7D](https://www.iesdouyin.com/share/video/7515242763068247322/?region=\&mid=7515242651566885666\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&share_sign=mlo1avSTDFE.WqqgUbnt4FzHOBYBT7WK59zcrURKGPw-\&share_version=280700\&ts=1770630046\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)

\[112] Claude: enterprise security configurations and deployment controls explained[ https://www.datastudios.org/post/claude-enterprise-security-configurations-and-deployment-controls-explained](https://www.datastudios.org/post/claude-enterprise-security-configurations-and-deployment-controls-explained)

\[113] 深入解读 Claude Skills(Anthropic)——原理、实践、风险-CSDN博客[ https://blog.csdn.net/JuMengXiaoKeTang/article/details/155643914](https://blog.csdn.net/JuMengXiaoKeTang/article/details/155643914)

\[114] Security Policy[ https://github.com/alirezarezvani/claude-code-skill-factory/blob/dev/SECURITY.md](https://github.com/alirezarezvani/claude-code-skill-factory/blob/dev/SECURITY.md)

\[115] claude-howto/LEARNING-ROADMAP.md at main · luongnv89/claude-howto · GitHub[ https://github.com/luongnv89/claude-howto/blob/main/LEARNING-ROADMAP.md](https://github.com/luongnv89/claude-howto/blob/main/LEARNING-ROADMAP.md)

\[116] Complete Guide[ https://github.com/prapanch/template-repo-claude-code/blob/main/docs/COMPLETE\_GUIDE.md](https://github.com/prapanch/template-repo-claude-code/blob/main/docs/COMPLETE_GUIDE.md)

\[117] Claude Code for Beginners - The AI Coding Assistant That Actually Understands Your Codebase[ https://codewithmukesh.com/blog/claude-code-for-beginners/](https://codewithmukesh.com/blog/claude-code-for-beginners/)

\[118] Claude Code Skills 实用使用手册 - 技术栈[ https://jishuzhan.net/article/2002905078227861506](https://jishuzhan.net/article/2002905078227861506)

\[119] Inside Claude Skills: Custom Modules That Extend Claude[ https://www.datacamp.com/tutorial/claude-skills](https://www.datacamp.com/tutorial/claude-skills)

\[120] Awesome Claude Code Skills for Coding & Development[ https://apidog.com/blog/coding-and-development-claude-skills/](https://apidog.com/blog/coding-and-development-claude-skills/)

\[121] Claude Code 2.1: A Guide With Practical Examples[ https://www.datacamp.com/tutorial/claude-code-2-1-guide](https://www.datacamp.com/tutorial/claude-code-2-1-guide)

\[122] Claude Skills 完全指南:从入门到精通Claude Skills 是一种可复用的 AI 能力单元，通过结构化 - 掘金[ https://aicoding.juejin.cn/post/7601929765533859891](https://aicoding.juejin.cn/post/7601929765533859891)

\[123] Claude Code Skills:从入门到精通本文是 Anthropic Claude Code Skills 的完 - 掘金[ https://juejin.cn/post/7589838742552805395](https://juejin.cn/post/7589838742552805395)

\[124] 10篇精选文章全面解读Claude Skills:从入门到精通[ https://c.m.163.com/news/a/KJKDJHFK0538QQXU.html](https://c.m.163.com/news/a/KJKDJHFK0538QQXU.html)

\[125] 2026 最新 Claude Skills 保姆级教程及实践!\_人人都是产品经理[ http://m.toutiao.com/group/7595157641827975715/?upstream\_biz=doubao](http://m.toutiao.com/group/7595157641827975715/?upstream_biz=doubao)

\[126] 一文读懂 Skills|从概念到实操的完整指南\_字节跳动技术团队[ http://m.toutiao.com/group/7598240996102586930/?upstream\_biz=doubao](http://m.toutiao.com/group/7598240996102586930/?upstream_biz=doubao)

\[127] Claude Skills 完全指南Claude Skills 完全指南 1. 什么是 Claude Skills Cl - 掘金[ https://juejin.cn/post/7597125475601268763](https://juejin.cn/post/7597125475601268763)

\[128] claudeskills[ https://juejin.cn/post/7598057199963062323](https://juejin.cn/post/7598057199963062323)

\[129] Performance Tuning for Claude: Best Practices[ https://claude3.pro/performance-tuning-claude-best-practices/](https://claude3.pro/performance-tuning-claude-best-practices/)

\[130] mellanon /2025-12-17-Claude Code Skills Structure and Usage Guide.md[ https://gist.github.com/mellanon/50816550ecb5f3b239aa77eef7b8ed8d](https://gist.github.com/mellanon/50816550ecb5f3b239aa77eef7b8ed8d)

\[131] claude-prompt-engineering-guide/skills/examples/performance-optimization-skill.md at dbc3a1306b7f1ec347028417fbb10f21d5d96514 · ThamJiaHe/claude-prompt-engineering-guide · GitHub[ https://github.com/ThamJiaHe/claude-prompt-engineering-guide/blob/dbc3a1306b7f1ec347028417fbb10f21d5d96514/skills/examples/performance-optimization-skill.md](https://github.com/ThamJiaHe/claude-prompt-engineering-guide/blob/dbc3a1306b7f1ec347028417fbb10f21d5d96514/skills/examples/performance-optimization-skill.md)

\[132] Optimizing Claude Skills from Subagents to Scripts[ https://egghead.io/lessons/optimizing-claude-skills-from-subagents-to-scripts\~af2o7](https://egghead.io/lessons/optimizing-claude-skills-from-subagents-to-scripts~af2o7)

\[133] Claude Best Practices: Essential Tips for Optimal Performance | Graph AI[ https://www.graphapp.ai/blog/claude-best-practices-essential-tips-for-optimal-performance](https://www.graphapp.ai/blog/claude-best-practices-essential-tips-for-optimal-performance)

\[134] Claude Skills\_claude skills部署-CSDN博客[ https://blog.csdn.net/m0\_55049655/article/details/156996073](https://blog.csdn.net/m0_55049655/article/details/156996073)

\[135] 【技术收藏】Claude Skills深度解析:停止构建Agent，打造可复用技能架构，让AI变身专业专家!\_claude skills架构-CSDN博客[ https://blog.csdn.net/csdn\_224022/article/details/155987623](https://blog.csdn.net/csdn_224022/article/details/155987623)

\[136] Claude Skills 架构解析:从提示工程到上下文工程\_人工智能\_俞凡\_InfoQ写作社区[ https://xie.infoq.cn/article/58047c3189114e74bec3d0556](https://xie.infoq.cn/article/58047c3189114e74bec3d0556)

\[137] 从 “渐进式披露” 到 “能力即文件”:Claude Agent Skills 的技术本质、架构变革与生态影响 - 技术栈[ https://jishuzhan.net/article/2018131434805444610](https://jishuzhan.net/article/2018131434805444610)

\[138] 产品团队即代码:用 Claude Skill 重构组织能力系统\_人人都是产品经理[ http://m.toutiao.com/group/7578702313578988070/?upstream\_biz=doubao](http://m.toutiao.com/group/7578702313578988070/?upstream_biz=doubao)

\[139] 来自 Claude Code 创始团队的 CC 最佳实践技巧-CSDN博客[ https://blog.csdn.net/LXZZKJ/article/details/157687171](https://blog.csdn.net/LXZZKJ/article/details/157687171)

\[140] claude-skills/documentation/WORKFLOW.md at main · alirezarezvani/claude-skills · GitHub[ https://github.com/alirezarezvani/claude-skills/blob/main/documentation/WORKFLOW.md](https://github.com/alirezarezvani/claude-skills/blob/main/documentation/WORKFLOW.md)

\[141] Awesome Claude Skills[ https://github.com/travisvn/awesome-claude-skills/blob/main/README.md](https://github.com/travisvn/awesome-claude-skills/blob/main/README.md)

\[142] Claude for Enterprise | Claude[ https://www.anthropic.com/news/claude-for-enterprise](https://www.anthropic.com/news/claude-for-enterprise)

\[143] Team Collaboration[ https://github.com/robwhite4/claude-memory/wiki/Team-Collaboration](https://github.com/robwhite4/claude-memory/wiki/Team-Collaboration)

\[144] Claude Code Configuration Guide[ https://github.com/carlrannaberg/claudekit/blob/main/docs/internals/claude-code-config.md](https://github.com/carlrannaberg/claudekit/blob/main/docs/internals/claude-code-config.md)

\[145] Claude Code Best Practices: Advanced Command Line AI Development in 2025[ https://collabnix.com/claude-code-best-practices-advanced-command-line-ai-development-in-2025/](https://collabnix.com/claude-code-best-practices-advanced-command-line-ai-development-in-2025/)

\[146] Enterprise plan | Claude[ https://www.anthropic.com/enterprise?s=03](https://www.anthropic.com/enterprise?s=03)

\[147] 10个关键技巧:掌握Claude-Flow企业级AI开发规范与团队协作标准-CSDN博客[ https://blog.csdn.net/gitblog\_00976/article/details/153906746](https://blog.csdn.net/gitblog_00976/article/details/153906746)

\[148] 从 原型 实验 出发 ， 拆解 Claude Agent Teams 从 原型 实验 出发 ， 拆解 Claude Agent Teams 的 基础 架构 ： 《 Building a C compiler with a team of parallel Claude s 》 ①[ https://www.iesdouyin.com/share/video/7604517615100251428/?region=\&mid=7604517571848719131\&u\_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with\_sec\_did=1\&video\_share\_track\_ver=\&titleType=title\&share\_sign=geUUpBcsqz\_8ky7QAWtnICWo3JkcL2Ugz\_SdBsktDzg-\&share\_version=280700\&ts=1770630087\&from\_aid=1128\&from\_ssr=1\&share\_track\_info=%7B%22link\_description\_type%22%3A%22%22%7D](https://www.iesdouyin.com/share/video/7604517615100251428/?region=\&mid=7604517571848719131\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&share_sign=geUUpBcsqz_8ky7QAWtnICWo3JkcL2Ugz_SdBsktDzg-\&share_version=280700\&ts=1770630087\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)

\[149] Claude Code and new admin controls for business plans \ Anthropic[ https://www.anthropic.com/news/claude-code-on-team-and-enterprise?e45d281a\_page=2\&ref=moonflame.top](https://www.anthropic.com/news/claude-code-on-team-and-enterprise?e45d281a_page=2\&ref=moonflame.top)

\[150] Anthropic 132名工程师Claude使用实录人机协作如何重构研发生产力\_合信通[ http://m.toutiao.com/group/7587419081196814902/?upstream\_biz=doubao](http://m.toutiao.com/group/7587419081196814902/?upstream_biz=doubao)

\[151] claude\_guide/09\_practical/9.4\_qa\_test.md at main · yeasy/claude\_guide · GitHub[ https://github.com/yeasy/claude\_guide/blob/main/09\_practical/9.4\_qa\_test.md](https://github.com/yeasy/claude_guide/blob/main/09_practical/9.4_qa_test.md)

\[152] Qodo helps developers ship quality code faster with Claude \ Anthropic[ https://www.anthropic.com/customers/qodo?e45d281a\_page=2\&ref=bahew.com](https://www.anthropic.com/customers/qodo?e45d281a_page=2\&ref=bahew.com)

\[153] Optimize QE Skills for Claude 4.5 Best Practices #102[ https://github.com/proffesor-for-testing/agentic-qe/issues/102](https://github.com/proffesor-for-testing/agentic-qe/issues/102)

\[154] Customer story | micro1 | Claude[ https://www.anthropic.com/customers/micro1](https://www.anthropic.com/customers/micro1)

\[155] Claude in the enterprise: case studies of AI deployments and real-world results[ https://www.datastudios.org/post/claude-in-the-enterprise-case-studies-of-ai-deployments-and-real-world-results](https://www.datastudios.org/post/claude-in-the-enterprise-case-studies-of-ai-deployments-and-real-world-results)

\[156] Claude Sonnet 4.5 \ Anthropic[ https://www.anthropic.com/claude/sonnet?\_bhlid=7909c707d9be89bb3ab3d44dc3d53729461014fb](https://www.anthropic.com/claude/sonnet?_bhlid=7909c707d9be89bb3ab3d44dc3d53729461014fb)

\[157] 胜算秘籍—Claude 八大神级技巧:从代码助手到 AI 项目经理\_claude init-CSDN博客[ https://blog.csdn.net/weixin\_49470217/article/details/149811307](https://blog.csdn.net/weixin_49470217/article/details/149811307)

\[158] Claude Opus 4.5深度评测:如何以1/3成本实现旗舰级AI性能-腾讯云开发者社区-腾讯云[ https://cloud.tencent.com.cn/developer/article/2596147](https://cloud.tencent.com.cn/developer/article/2596147)

\[159] Anthropic 发布 claude 4 . 5 # claude # ai # ai 编程 # 人工 智能 # 大模型[ https://www.iesdouyin.com/share/video/7579258716694169846/?region=\&mid=7579258709373618971\&u\_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with\_sec\_did=1\&video\_share\_track\_ver=\&titleType=title\&share\_sign=Szx4x.7Dj5NjveHDFXBl4DbH80M09dE57izwmN.D.Rc-\&share\_version=280700\&ts=1770630095\&from\_aid=1128\&from\_ssr=1\&share\_track\_info=%7B%22link\_description\_type%22%3A%22%22%7D](https://www.iesdouyin.com/share/video/7579258716694169846/?region=\&mid=7579258709373618971\&u_code=0\&did=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&iid=MS4wLjABAAAANwkJuWIRFOzg5uCpDRpMj4OX-QryoDgn-yYlXQnRwQQ\&with_sec_did=1\&video_share_track_ver=\&titleType=title\&share_sign=Szx4x.7Dj5NjveHDFXBl4DbH80M09dE57izwmN.D.Rc-\&share_version=280700\&ts=1770630095\&from_aid=1128\&from_ssr=1\&share_track_info=%7B%22link_description_type%22%3A%22%22%7D)

\[160] Claude Skills\_claude skills部署-CSDN博客[ https://blog.csdn.net/m0\_55049655/article/details/156996073](https://blog.csdn.net/m0_55049655/article/details/156996073)

\[161] Claude Skills 实战技巧:让你的 AI 效率提升 50%\_南哥聊技术[ http://m.toutiao.com/group/7594756846331396608/?upstream\_biz=doubao](http://m.toutiao.com/group/7594756846331396608/?upstream_biz=doubao)

\[162] Claude Skills 深度解析:AI工作流的革命性升级最近 Anthropic 推出的 Claude Skills - 掘金[ https://juejin.cn/post/7563193517947191338](https://juejin.cn/post/7563193517947191338)

> （注：文档部分内容可能由 AI 生成）