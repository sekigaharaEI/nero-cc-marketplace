# daemon-archon 开发设计文档

> 本文档记录开发过程中的设计决策和技术细节

---

## 一、架构角色定义

本插件涉及三个核心角色：

### 1.1 Claude Code 终端

**定位**：基础执行环境

- 基于 Claude Code 才能加载插件、skills、commands
- 作为智能体完成一系列复杂的原子操作
- 基于提示词实现代码编写、功能调用等任务

### 1.2 Archon（执政官）

**定位**：任务调度器

基于 cron 实现定时任务调度，分为两种工作模式：

#### Probe 模式
- 新建一个 Claude Code CLI（Probe）执行用户特定的长期任务
- Archon 定时基于预设模板，分析 Probe 的执行情况
- 分析维度：产物、日志、对话记录、工具调用等
- 可对 Probe 进行纠偏（注入新提示词接续对话）

#### Cron 模式
- Archon 根据 cron 定时启动一个**临时** Claude Code CLI
- 按照 workflow 中的工作清单逐个调用并汇总监控
- 如有异常则发送系统通知
- 每次执行完毕后临时会话销毁

### 1.3 Probe（探机）

**定位**：执行层角色

- 基于 Claude Code CLI 模式运行
- 负责接受 Archon 的调度
- Archon 可随时停止 Probe 进程
- Archon 可随时输入新提示词进行接续对话（纠偏）

---

## 二、工作目录设计

### 2.1 目录结构（已确定）

**根目录**：`.claude/daemon-archon/`

```
.claude/daemon-archon/
├── setting.json                          # 全局配置（通知方式等）
├── 20260201_143000_probe/                # Probe 任务目录（时间戳+模式后缀）
│   ├── config.json                       # 任务配置
│   ├── status                            # 状态文件（active/stopped/paused）
│   ├── task.lock                         # 任务级锁文件（防止并发）
│   ├── destination.md                    # 任务目标（Archon 验证完成的依据）
│   ├── corrections.md                    # 纠偏历史（Markdown 格式）
│   └── archon.log                        # 工作日志（带时间戳）
│
└── 20260201_150000_cron/                 # Cron 任务目录（时间戳+模式后缀）
    ├── config.json                       # 任务配置
    ├── status                            # 状态文件（active/stopped/paused）
    ├── task.lock                         # 任务级锁文件（防止并发）
    ├── task.md                           # 任务描述/提示词/背景/特别说明
    ├── workflow/                         # Workflow 子文件夹
    │   ├── workflow.md                   # 工作流程定义
    │   └── scripts/                      # 脚本代码（可选）
    │       └── check_xxx.sh
    └── archon.log                        # 工作日志（带时间戳）
```

### 2.2 文件说明

#### 通用文件

| 文件 | 格式 | 说明 |
|------|------|------|
| `setting.json` | JSON | 全局配置：通知方式等 |
| `status` | 纯文本 | 任务状态：`active` / `stopped` / `paused` |
| `task.lock` | 锁文件 | 任务级锁，防止同一任务被并发处理 |
| `archon.log` | 日志 | Archon 行动日志，每条带时间戳 |

#### Probe 模式专属

| 文件 | 格式 | 说明 |
|------|------|------|
| `config.json` | JSON | 任务 ID、Probe 会话 ID、检查间隔等 |
| `destination.md` | Markdown | 任务目标，Archon 用于验证 Probe 是否完成任务 |
| `corrections.md` | Markdown | 纠偏历史：时间、原因、指令、结果、纠偏者（Archon/人） |

#### Cron 模式专属

| 文件 | 格式 | 说明 |
|------|------|------|
| `config.json` | JSON | 任务 ID、执行间隔等 |
| `task.md` | Markdown | 任务描述、提示词、背景、特别说明 |
| `workflow/workflow.md` | Markdown | 工作流程定义 |
| `workflow/scripts/` | 脚本 | 可选的脚本代码 |

### 2.3 日志格式规范

`archon.log` 每条日志格式：
```
[2026-02-01 14:30:00] [ACTION] 触发定时检查
[2026-02-01 14:30:01] [INPUT] 读取 Probe transcript...
[2026-02-01 14:30:05] [OUTPUT] 分析结果：任务进度 60%，无异常
[2026-02-01 14:30:05] [DECISION] 无需纠偏，继续监控
```

### 2.4 状态文件说明

`status` 文件内容为单行文本：
- `active` - 任务启用中
- `stopped` - 任务已停止
- `paused` - 任务暂停中

---

## 待讨论问题

1. ~~**纠偏历史**是否需要单独文件，还是记录在任务配置中？~~ → 已确定：单独 `corrections.md` 文件
2. ~~**执行日志**的格式和保留策略？~~ → 已确定：`archon.log`，每条带时间戳
3. ~~**全局配置 `setting.json`** 需要包含哪些内容？~~ → 已确定：见决策 #2
4. ~~是否需要 **锁文件** 防止并发执行？~~ → 已确定：任务级锁文件 `task.lock`，见决策 #3
5. ~~**corrections.md** 的具体格式？~~ → 已确定：见决策 #4
6. ~~**config.json** 的具体字段？~~ → 已确定：见决策 #5

**所有设计问题已解决，可进入开发阶段。**

---

## 三、设计决策记录

### 决策 #1：工作目录结构
- **问题**：插件的工作目录和持久化文件如何组织？
- **结论**：
  - 根目录：`.claude/daemon-archon/`
  - 每个任务独立目录，命名格式：`时间戳_模式后缀`（如 `20260201_143000_probe`）
  - 全局配置：`setting.json`
  - 任务状态：`status` 文件（纯文本：active/stopped/paused）
  - 纠偏历史：`corrections.md`（Markdown 格式，方便人读）
  - 工作日志：`archon.log`（每条带时间戳）
  - Cron 模式额外包含 `workflow/` 子文件夹
- **理由**：
  - 每个任务独立目录便于管理和清理
  - 时间戳命名便于排序和识别
  - Markdown 格式的纠偏历史便于人工阅读
  - 状态文件独立便于快速判断任务状态
- **日期**：2026-02-01

### 决策 #2：全局配置 setting.json

- **问题**：全局配置文件需要包含哪些内容？
- **结论**：

```json
{
  "version": "1.0",
  "notification": {
    "enabled": true,
    "method": "system",
    "webhook_url": null,
    "slack_webhook": null
  },
  "defaults": {
    "probe_check_interval_minutes": 5,
    "cron_check_interval_minutes": 60,
    "max_auto_corrections": 3
  },
  "claude_cli": {
    "path": "claude",
    "default_model": null
  },
  "logging": {
    "level": "INFO",
    "max_log_size_mb": 10,
    "max_log_files": 5
  }
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | string | 配置文件版本号 |
| `notification.enabled` | boolean | 是否启用通知 |
| `notification.method` | string | 通知方式：`system` / `slack` / `email` / `webhook` |
| `notification.webhook_url` | string | 自定义 webhook 地址（可选） |
| `notification.slack_webhook` | string | Slack webhook 地址（可选） |
| `defaults.probe_check_interval_minutes` | number | Probe 模式默认检查间隔（分钟） |
| `defaults.cron_check_interval_minutes` | number | Cron 模式默认执行间隔（分钟） |
| `defaults.max_auto_corrections` | number | 最大自动纠偏次数 |
| `claude_cli.path` | string | Claude CLI 可执行文件路径 |
| `claude_cli.default_model` | string | 默认使用的模型（可选） |
| `logging.level` | string | 日志级别：`DEBUG` / `INFO` / `WARN` / `ERROR` |
| `logging.max_log_size_mb` | number | 单个日志文件最大大小（MB） |
| `logging.max_log_files` | number | 保留的日志文件数量 |

- **日期**：2026-02-02

### 决策 #3：任务级锁文件

- **问题**：是否需要锁文件防止并发执行？锁文件应该放在哪里？
- **结论**：
  - **需要锁文件**，采用**任务级锁**而非插件级锁
  - 位置：`任务目录/task.lock`
  - 内容格式：`PID:时间戳`（如 `12345:2026-02-01T14:30:00Z`）
  - 超时机制：锁文件存在超过 30 分钟视为僵尸锁，可以覆盖
- **理由**：
  - 不同任务之间应该可以并行检查，互不阻塞
  - 只需要防止**同一个任务**被并发处理
  - 任务级锁更细粒度，更灵活
  - 场景支持：
    - 用户手动 `/check-task` 与定时器同时触发
    - 定时器触发时上一次检查尚未完成
- **日期**：2026-02-02

### 决策 #4：纠偏历史 corrections.md 格式规范

- **问题**：corrections.md 的具体格式是什么？
- **结论**：采用 Markdown 表格 + 详情块的混合格式

```markdown
# 纠偏历史

## 摘要

| # | 时间 | 纠偏者 | 原因 | 结果 |
|---|------|--------|------|------|
| 1 | 2026-02-01 14:30 | Archon | 测试失败 | 成功 |
| 2 | 2026-02-01 15:00 | 用户 | 架构问题 | 成功 |

---

## 详细记录

### #1 - 2026-02-01 14:30:00

**纠偏者**：Archon（自动）

**触发原因**：
- 检测到 3 个单元测试失败
- 错误信息：`TypeError: undefined is not a function`

**分析结论**：
- 问题级别：中等
- 根因：函数参数类型不匹配

**纠偏指令**：
\`\`\`
请检查 src/utils/helper.ts 中的 processData 函数，
第 42 行的参数类型应该是 string[] 而不是 string。
\`\`\`

**执行结果**：成功
**后续状态**：测试全部通过

---
```

**格式要点**：
1. **摘要表格**：快速浏览所有纠偏记录
2. **详细记录**：每次纠偏的完整信息
3. **必填字段**：
   - 纠偏者（Archon/用户）
   - 触发原因
   - 分析结论（问题级别、根因）
   - 纠偏指令
   - 执行结果
   - 后续状态

- **理由**：
  - Markdown 格式便于人工阅读和编辑
  - 摘要表格便于快速定位
  - 详细记录保留完整上下文，便于复盘
- **日期**：2026-02-02

### 决策 #5：config.json 字段定义

- **问题**：Probe 模式和 Cron 模式的 config.json 具体包含哪些字段？
- **结论**：

#### Probe 模式 config.json

```json
{
  "task_id": "20260201_143000_probe",
  "mode": "probe",
  "name": "代码重构任务",
  "description": "重构 src/legacy 目录，迁移到新架构",
  "project_path": "/home/user/project",
  "created_at": "2026-02-01T14:30:00Z",

  "probe": {
    "session_id": "abc123def456",
    "pid": 12345,
    "initial_prompt": "请重构 src/legacy 目录..."
  },

  "schedule": {
    "check_interval_minutes": 5,
    "next_check": "2026-02-01T14:35:00Z"
  },

  "correction": {
    "max_auto_corrections": 3,
    "current_count": 1,
    "escalate_after_failures": 2
  },

  "criteria": {
    "success_indicators": ["测试通过", "无 lint 错误"],
    "failure_indicators": ["build 失败", "严重错误"],
    "completion_keywords": ["任务完成", "重构完成"]
  }
}
```

**重要说明**：
- `probe.session_id` **必须**与启动的 Claude Code CLI 的 session_id 一致
- 后续的 `--resume`、transcript 读取等操作都依赖此 session_id

#### Cron 模式 config.json

```json
{
  "task_id": "20260201_150000_cron",
  "mode": "cron",
  "name": "服务器日志检查",
  "description": "每小时检查服务器日志，发现错误通知",
  "project_path": "/home/user/project",
  "created_at": "2026-02-01T15:00:00Z",

  "schedule": {
    "cron_expression": "0 * * * *",
    "check_interval_minutes": 60,
    "next_run": "2026-02-01T16:00:00Z"
  },

  "execution": {
    "timeout_minutes": 10,
    "last_run": "2026-02-01T15:00:00Z",
    "last_result": "success",
    "run_count": 5,
    "consecutive_failures": 0
  },

  "notification": {
    "notify_on_error": true,
    "notify_on_success": false,
    "quiet_hours": null
  }
}
```

- **日期**：2026-02-02

### 决策 #6：任务目标 destination.md（Probe 模式专属）

- **问题**：Archon 如何判断 Probe 是否真正完成了任务？
- **结论**：
  - 新增 `destination.md` 文件，仅 Probe 模式使用
  - 内容为任务目标的提示词，Archon 用于验证任务完成情况
  - 位置：`任务目录/destination.md`

**文件格式**：

```markdown
# 任务目标

## 核心目标
[描述任务的核心目标，Archon 将以此为依据判断任务是否完成]

## 验收标准
- [ ] 标准 1：xxx
- [ ] 标准 2：xxx
- [ ] 标准 3：xxx

## 完成标志
[描述什么情况下可以认为任务已完成]

## 特别说明
[任何需要 Archon 注意的特殊情况]
```

- **理由**：
  - 明确的任务目标便于 Archon 进行验证
  - 验收标准可量化，减少主观判断
  - 与 config.json 中的 `criteria` 配合使用
- **日期**：2026-02-02

### 决策 #7：Cron 模式执行流程

- **问题**：Cron 模式的任务执行流程如何设计？
- **结论**：

#### 执行流程

```
定时器触发
    │
    ▼
cron_executor.py
    │
    ├─→ 1. 检查 task.lock（防并发）
    │
    ├─→ 2. 读取 task.md + workflow/workflow.md
    │
    ├─→ 3. 构建提示词
    │
    ├─→ 4. 启动临时 Claude Code CLI（-p 单次执行）
    │      claude -p "{prompt}" --output-format json
    │
    ├─→ 5. 等待执行完成（带超时）
    │
    ├─→ 6. 解析执行结果
    │
    ├─→ 7. 调用 result_analyzer.py 分析结果
    │
    └─→ 8. 根据分析结果决定是否通知
```

#### CLI 调用方式

采用 `-p` 单次执行模式：
- 简单、无状态、执行完即退出
- 无需管理 session
- 如需多轮对话场景，应使用 Probe 模式

- **理由**：
  - Cron 模式定位是定时执行简单任务，单次执行足够
  - 保持简单，降低复杂度
  - 与 Probe 模式形成明确分工
- **日期**：2026-02-03

### 决策 #8：Workflow 格式规范

- **问题**：workflow/workflow.md 的具体格式是什么？条件逻辑如何处理？
- **结论**：

#### 文件格式

```markdown
# Workflow: {任务名称}

## 元信息
- 版本: 1.0
- 预计耗时: 5 分钟
- 失败策略: stop_on_error | continue_on_error

## 执行步骤

### Step 1: {步骤名称}
- 动作: {具体要做什么}
- 成功条件: {什么情况算成功}
- 失败处理: {失败时怎么办}

### Step 2: {步骤名称}
- 动作: {具体要做什么}
- 成功条件: {什么情况算成功}
- 关注指标:
  - {指标} > {阈值} → {级别}

## 结果汇总要求

请按以下格式输出结果：

\`\`\`json
{
  "status": "success | warning | error",
  "summary": "一句话总结",
  "findings": [
    {"level": "info|warning|error", "message": "具体发现"}
  ],
  "metrics": {
    "key": value
  }
}
\`\`\`
```

#### 条件逻辑处理

采用**自然语言描述**，交给 Claude 判断：
- 不设计复杂的 DSL 语法
- 在步骤描述中用自然语言说明条件
- Claude 根据上下文自行理解和执行

**示例**：
```markdown
### Step 3: 决定是否深度扫描
- 动作: 如果 Step 2 发现的错误数量超过 10 个，执行深度日志分析；否则跳过此步骤
```

- **理由**：
  - Markdown 格式人类可读，非技术人员也能理解
  - 自然语言描述条件逻辑，避免设计复杂 DSL
  - 结构化 JSON 输出便于程序解析
  - 充分利用 Claude 的理解能力
- **日期**：2026-02-03

### 决策 #9：Cron 结果分析机制

- **问题**：Cron 模式执行后，如何判断"发现问题"？何时触发通知？
- **结论**：

#### 混合分析方案

采用**规则初筛 + Claude 二次分析**的混合方案：

```
Claude CLI 输出
    │
    ▼
result_analyzer.py
    │
    ├─→ 1. 解析 JSON 输出
    │      - 提取 status 字段
    │      - 提取 findings 列表
    │      - 提取 metrics 数据
    │
    ├─→ 2. 规则初筛
    │      - status == "error" → 确定需要通知
    │      - status == "success" 且无异常指标 → 确定不需要通知
    │      - status == "warning" 或指标接近阈值 → 可疑，需二次分析
    │
    ├─→ 3. 可疑情况交给 Claude 二次分析
    │      - 构建分析提示词，包含原始输出和上下文
    │      - Claude 判断是否真的需要通知
    │      - 返回分析结论
    │
    └─→ 4. 生成最终结论并记录
```

#### 通知规则配置

在 `config.json` 中定义：

```json
{
  "notification_rules": {
    "notify_on_status": ["error"],
    "suspicious_status": ["warning"],
    "metric_thresholds": {
      "error_count": { "warn": 10, "error": 50 },
      "disk_usage_percent": { "warn": 80, "error": 95 }
    },
    "enable_claude_analysis": true
  }
}
```

#### 分析结果分类

| 初筛结果 | 处理方式 |
|----------|----------|
| 确定异常 | 直接通知 |
| 确定正常 | 不通知，仅记录日志 |
| 可疑情况 | 交给 Claude 二次分析后决定 |

- **理由**：
  - 规则初筛快速、低成本，处理明确情况
  - Claude 二次分析处理边界情况，减少漏报/误报
  - 可配置是否启用 Claude 分析，平衡成本和智能
- **日期**：2026-02-03

### 决策 #10：架构变更 - FastAPI 事件循环

- **问题**：定时调度采用系统 cron 还是代码实现？
- **结论**：

#### 变更原因

不依赖系统 crontab/Task Scheduler，改用 FastAPI + APScheduler 代码实现定时调度。

#### 架构方案：插件内嵌 FastAPI 服务

```
daemon-archon/（插件目录）
├── commands/
│   ├── archon-start.md      # 启动服务
│   ├── archon-stop.md       # 停止服务
│   ├── archon-status.md     # 查看状态
│   ├── archon-create.md     # 创建任务
│   └── archon-list.md       # 列出任务
│
├── hooks/                   # 可选
│
├── scripts/
│   └── server/              # FastAPI 服务代码
│       ├── main.py          # FastAPI 入口
│       ├── scheduler.py     # APScheduler 调度
│       ├── executor.py      # 任务执行（subprocess 调用 claude）
│       ├── analyzer.py      # 结果分析
│       └── requirements.txt
│
├── settings.json
└── README.md
```

#### 执行流程

```
用户执行 /archon-start
    │
    ▼
Claude Code 启动 scripts/server/main.py
    │
    ▼
FastAPI 服务运行（用户权限）
    │
    ├─→ APScheduler 定时触发
    │
    └─→ subprocess.run(['claude', '-p', prompt])
            │
            └─→ Claude CLI 以用户权限执行（完整权限）
```

#### 权限分析

服务通过 subprocess 调用 Claude CLI，权限链完整：
- 服务以用户权限运行
- Claude CLI 拥有完整权限（读写文件、执行命令）
- 与系统 cron 方案权限相同，不会受限

- **理由**：
  - 跨平台一致，不依赖系统定时器
  - 代码实现，易于调试和测试
  - 插件内嵌，安装部署简单
  - 服务不会特别复杂，内嵌合适
- **日期**：2026-02-03

### 决策 #11：任务持久化方案

- **问题**：APScheduler 是否需要 SQLite 持久化？
- **结论**：

#### 采用文件持久化

不使用 SQLite，任务配置存储在 JSON 文件中：
- 每个任务一个目录，包含 `config.json`
- 服务启动时扫描 `~/.claude/daemon-archon/` 恢复所有 `active` 任务
- APScheduler 使用内存 JobStore

#### 服务启动恢复逻辑

```python
async def startup_event():
    """服务启动时恢复所有活跃任务"""
    scheduler = ArchonScheduler()

    # 扫描所有任务目录
    for task_dir in scan_task_directories():
        config = load_config(task_dir)

        if config["state"]["status"] == "active":
            scheduler.add_task(
                task_id=config["task_id"],
                interval_minutes=config["schedule"]["check_interval_minutes"],
                mode=config["mode"]
            )

    scheduler.start()
```

- **理由**：
  - 简单、易调试、用户可直接查看/编辑配置文件
  - 对于任务量不大的场景，文件持久化足够
  - 避免引入 SQLite 增加复杂度
- **日期**：2026-02-03

### 决策 #12：环境检查命令

- **问题**：如何帮助用户检查环境是否满足要求？
- **结论**：

#### 新增 /archon-init 命令

检查环境并输出对照表：

```
检查项                          状态   详情
------------------------------------------------------------
Claude CLI                     ✓     claude 2.1.0
Python 版本                    ✓     Python 3.10
Python 包: fastapi             ✓     已安装
Python 包: uvicorn             ✓     已安装
Python 包: apscheduler         ✓     已安装
Python 包: anthropic           ✗     未安装
工作目录权限                    ✓     /home/user/.claude/daemon-archon
```

#### 检查项

1. Claude CLI 是否安装及版本
2. Python 版本（>= 3.8）
3. 必要的 Python 包（fastapi、uvicorn、apscheduler、anthropic）
4. 工作目录权限（~/.claude/daemon-archon）

#### 修复建议

对于未通过的检查项，输出具体的安装/修复指令。

- **理由**：
  - 降低用户使用门槛，快速发现环境问题
  - 提供明确的修复指导
  - 避免服务启动后才发现环境问题
- **日期**：2026-02-03

### 决策 #13：执行超时机制

- **问题**：Probe 和 Cron 模式是否需要超时机制？
- **结论**：

#### Probe 模式：不设置超时

- Probe 任务可能执行很久（如代码重构）
- 由 Archon 定时监测状态，无需超时终止
- 用户可手动停止：`/stop-probe <task_id>`

#### Cron 模式：10 分钟超时

```python
def execute_cron(task_id: str):
    """执行 Cron 任务"""
    config = load_config(task_id)
    timeout_seconds = config["execution"].get("timeout_minutes", 10) * 60

    try:
        result = subprocess.run(
            ['claude', '-p', prompt, '--output-format', 'json'],
            cwd=config["project_path"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )
        return analyze_result(result.stdout)

    except subprocess.TimeoutExpired:
        handle_timeout(task_id, config)
```

#### 超时处理策略

```python
def handle_timeout(task_id: str, config: dict):
    """处理超时"""
    # 1. 记录日志
    log_timeout(task_id)

    # 2. 更新配置
    config["execution"]["last_result"] = "timeout"
    config["execution"]["consecutive_failures"] += 1
    save_config(task_id, config)

    # 3. 检查连续失败次数
    max_failures = config["execution"].get("max_consecutive_failures", 3)

    if config["execution"]["consecutive_failures"] >= max_failures:
        # 达到阈值，暂停任务
        config["state"]["status"] = "paused"
        save_config(task_id, config)
        scheduler.remove_task(task_id)

        # 发送通知
        notifier.send(
            title="任务超时暂停",
            message=f"任务 {task_id} 连续超时 {max_failures} 次，已自动暂停"
        )
    else:
        # 未达到阈值，仅通知
        notifier.send(
            title="任务执行超时",
            message=f"任务 {task_id} 执行超时"
        )
```

#### 配置参数

```json
{
  "execution": {
    "timeout_minutes": 10,
    "max_consecutive_failures": 3
  }
}
```

- **理由**：
  - Probe 模式任务可能很长，不应超时终止
  - Cron 模式定位是快速巡检，10 分钟超时合理
  - 连续失败自动暂停，避免持续消耗资源
- **日期**：2026-02-03

