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

