# daemon-archon 守护进程执政官 - 设计文档

## 一、核心想法

daemon-archon 是一个 Claude Code 插件，提供两种工作模式：

1. **Probe 模式**：Archon 启动并监控一个 Probe（子 Claude Code），进行长期任务执行和纠偏
2. **Workflow 模式**：定时执行临时任务，分析结果并按需通知用户

**关键角色**：
- **Archon（执政官）**：统领全局，负责监控、调度、纠偏
- **Probe（探机）**：执行具体任务，负责采集信息、构建代码（仅 Probe 模式）

---

## 二、两种工作模式

### 模式 2.1：Probe 模式（监控智能体）

**适用场景**：代码重构、长期开发任务等**需要 Claude Code 持续执行**的任务

**核心流程**：
```
用户 → Archon → 启动 Probe → Probe 执行任务
                    ↓
              定时检测状态
                    ↓
         ┌─────────┴─────────┐
         ↓                   ↓
    状态正常              状态异常
    (继续监控)               ↓
                    ┌───────┴───────┐
                    ↓               ↓
               自动纠偏         通知用户介入
```

**特点**：
- Probe 是一个**持续运行的会话**
- Archon 与 Probe 之间有**双向交互**（纠偏）
- 需要分析 Probe 的 transcript.jsonl 判断状态

### 模式 2.2：Cron 模式（定时任务）

**适用场景**：定时检查、日志分析、状态巡检等**周期性任务**

**核心流程**：
```
用户 → 创建 Cron 任务 → 生成 cron 任务文件
                           ↓
                    系统定时器触发
                           ↓
              启动临时 Claude Code CLI
              执行 workflow 中的任务
                           ↓
                      分析执行结果
                           ↓
                ┌─────────┴─────────┐
                ↓                   ↓
           结果正常              发现问题
           (记录日志)          (通知用户)
```

**特点**：
- 每次执行都是**新的临时会话**，不保留上下文
- 没有"纠偏"概念，只有"执行 + 分析 + 通知"
- 根据用户提示词生成 cron 任务文件

### 两种模式对比

| 维度 | Probe 模式 | Cron 模式 |
|------|-----------|--------------|
| 会话类型 | 持续会话（Probe） | 临时会话（每次新建） |
| 核心动作 | 监控 + 纠偏 | 执行 + 分析 + 通知 |
| 上下文 | Probe 保持上下文 | 无上下文，每次独立 |
| 交互方式 | Archon ↔ Probe 双向 | 单向执行 |
| 适用场景 | 需要 Claude Code 持续执行的长期任务 | 定时巡检/检查 |

---

## 三、架构方案

### 确定方案：FastAPI 内嵌服务

- 插件内嵌轻量级 FastAPI 服务，使用 APScheduler 实现定时调度
- 服务常驻运行，通过 subprocess 调用 Claude CLI 执行任务
- 跨平台支持：Linux (Ubuntu) + Windows + macOS

**理由**：
1. 不依赖系统定时器（cron/systemd/Task Scheduler），代码逻辑统一
2. 跨平台一致，易于调试和测试
3. 插件内嵌，安装部署简单，用户通过命令启停服务
4. 服务通过 subprocess 调用 Claude CLI，权限与系统定时器方案相同

---

## 四、功能点拆解

### Probe 模式功能 (P0)
| ID | 功能 | 描述 |
|----|------|------|
| P1 | 启动 Probe 任务 | 创建 Probe（Claude Code 进程），开始执行长期任务 |
| P2 | 定时监控 | 系统定时器定时唤醒 Archon 检查 Probe 状态 |
| P3 | 状态分析 | 分析 Probe 的 transcript + 文件输出 + AI 智能判断 |
| P4 | 问题评估 | 评估问题严重程度（简单/中等/严重） |
| P5 | 自动纠偏 | 向 Probe 注入纠偏指令（通过 `claude --resume`） |
| P6 | 用户通知 | 严重问题时发送系统通知 |
| P7 | 停止 Probe | 终止 Probe 进程 |

### Cron 模式功能 (P0)
| ID | 功能 | 描述 |
|----|------|------|
| W1 | 创建 Cron 任务 | 根据用户提示词生成 cron 任务文件 |
| W2 | 定时执行 | 系统定时器触发，启动临时 Claude Code 执行 cron 任务 |
| W3 | 结果分析 | 分析执行结果，判断是否有问题 |
| W4 | 用户通知 | 发现问题时发送系统通知 |
| W5 | 停止 Cron 任务 | 停止定时任务 |

### 通用功能 (P1)
| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| C1 | 任务列表 | 查看所有任务（两种模式）及状态 | P1 |
| C2 | 手动检查 | 用户主动触发状态检查 | P1 |
| C3 | 配置定时器 | 自动安装系统定时器 | P1 |
| C4 | 查看日志 | 查看监控和执行历史 | P2 |

---

## 五、命令体系

```
# 服务管理
/archon-start                      # 启动 Archon 后台服务
/archon-stop                       # 停止 Archon 后台服务
/archon-status                     # 查看服务和任务状态

# Probe 模式
/start-probe <task_description>    # 启动 Probe 模式任务
/stop-probe <task_id>              # 停止 Probe 任务

# Cron 模式
/start-cron <task_description>     # 创建并启动 Cron 模式任务
/stop-cron <task_id>               # 停止 Cron 定时任务

# 通用
/list-tasks                        # 列出所有任务（两种模式）
/check-task <task_id>              # 手动检查任务状态
```

---

## 六、系统设计

### 6.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                              │
│  /archon-start  /archon-stop  /start-probe  /start-cron    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    daemon-archon 插件                        │
├─────────────────────────────────────────────────────────────┤
│  Commands (用户命令)          │  Skills (AI 技能)            │
│  ├── archon-start.md         │  ├── probe-monitor/SKILL.md │
│  ├── archon-stop.md          │  └── cron-exec/SKILL.md     │
│  ├── archon-status.md        │                              │
│  ├── start-probe.md          │                              │
│  ├── start-cron.md           │                              │
│  └── list-tasks.md           │                              │
├─────────────────────────────────────────────────────────────┤
│                   Scripts/Server (核心服务)                  │
│  └── server/                                                │
│      ├── main.py             # FastAPI 入口                 │
│      ├── scheduler.py        # APScheduler 定时调度         │
│      ├── probe_executor.py   # Probe 模式执行               │
│      ├── cron_executor.py    # Cron 模式执行                │
│      ├── analyzer.py         # 结果分析                     │
│      ├── notifier.py         # 系统通知                     │
│      └── state_store.py      # 状态持久化                   │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  FastAPI 服务    │  │   状态存储       │  │  Claude Code    │
│  (APScheduler)  │  │ ~/.claude/      │  │  (Probe/临时)   │
│  localhost:port │  │ daemon-archon/  │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 6.2 Probe 模式流程

```
1. 用户启动 Archon 服务（如未启动）
   /archon-start
         │
         ▼
2. 用户启动 Probe 任务
   /start-probe "重构 src/legacy 目录"
         │
         ▼
3. 创建 Probe 进程
   claude -p "重构任务..." --session-id xxx
         │
         ▼
4. 保存任务配置
   ~/.claude/daemon-archon/probes/probe-001.json
         │
         ▼
5. APScheduler 定时触发检查
   scheduler.py → probe_executor.py
         │
         ▼
6. Archon 分析 Probe 状态
   ├── 读取 Probe 的 transcript.jsonl
   ├── 检查输出文件
   └── AI 智能分析
         │
         ▼
7. 问题评估
   ├── 简单/中等 → 自动纠偏
   └── 严重 → 通知用户
         │
         ▼
8. 执行纠偏（如需要）
   claude --resume xxx -p "纠偏指令..."
```

### 6.3 Cron 模式流程

```
1. 用户启动 Archon 服务（如未启动）
   /archon-start
         │
         ▼
2. 用户创建 Cron 任务
   /start-cron "每小时检查服务器日志，发现错误就通知我"
         │
         ▼
3. 生成 cron 任务文件
   ~/.claude/daemon-archon/crons/cron-001/
   (包含：config.json, task.md, workflow/workflow.md)
         │
         ▼
4. APScheduler 定时触发执行
   scheduler.py → cron_executor.py
         │
         ▼
5. 启动临时 Claude Code CLI
   claude -p "$(构建的提示词)" --output-format json
         │
         ▼
6. 执行 workflow 中的任务
   (检查日志、分析状态等)
         │
         ▼
7. 分析执行结果
   ├── 规则初筛
   └── 可疑情况 → Claude 二次分析
         │
         ▼
8. 结果处理
   ├── 正常 → 记录日志
   └── 发现问题 → 发送系统通知
```

### 6.4 数据模型

**Probe 任务配置 (probe-xxx.json)**：
```json
{
  "task_id": "probe-001",
  "mode": "probe",
  "name": "代码重构任务",
  "description": "重构 src/legacy 目录",
  "project_path": "/home/user/project",
  "initial_prompt": "请重构...",
  "created_at": "2026-02-01T10:00:00Z",
  "config": {
    "check_interval_minutes": 5,
    "max_auto_corrections": 3,
    "success_criteria": ["测试通过", "无 lint 错误"]
  },
  "state": {
    "status": "running",
    "probe_session_id": "abc123",
    "probe_transcript_path": "~/.claude/projects/.../abc123.jsonl",
    "corrections_count": 1,
    "last_check": "2026-02-01T10:30:00Z"
  }
}
```

**Cron 任务配置 (cron-xxx.json)**：
```json
{
  "task_id": "cron-001",
  "mode": "cron",
  "name": "服务器日志检查",
  "description": "每小时检查服务器日志",
  "created_at": "2026-02-01T10:00:00Z",
  "config": {
    "check_interval_minutes": 60,
    "cron_file": "~/.claude/daemon-archon/crons/cron-001.md",
    "notify_on_error": true
  },
  "state": {
    "status": "active",
    "last_run": "2026-02-01T11:00:00Z",
    "last_result": "success",
    "run_count": 5
  }
}
```

**Cron 任务文件 (cron-xxx.md)**：
```markdown
# 服务器日志检查任务

## 任务描述
检查服务器日志，发现错误就通知用户

## 检查步骤
1. 读取 /var/log/app.log 最近 1 小时的日志
2. 搜索 ERROR、FATAL、Exception 等关键词
3. 统计错误数量和类型

## 通知条件
- 发现任何 FATAL 级别错误
- ERROR 数量超过 10 条
- 出现新的异常类型

## 输出格式
如果发现问题，输出：
- 问题摘要
- 错误详情
- 建议处理方式
```

### 6.5 纠偏策略（Probe 模式）

**核心原则**：Archon 先自己评估问题严重程度和影响

| 问题级别 | 判断标准 | 处理方式 |
|---------|---------|---------|
| **简单问题** | 语法错误、小 bug、格式问题 | 自动纠偏（注入指令） |
| **中等问题** | 逻辑错误、测试失败、依赖问题 | 自动纠偏（注入指令） |
| **严重问题** | 涉及核心设计、架构改动、可能造成严重后果 | 通知用户介入 |

- 自动纠偏次数：**可配置**（默认 3 次，超过后升级给用户）

---

## 七、实现计划

### Phase 1: 基础框架
1. 创建插件目录结构
2. 编写 plugin.json
3. 实现 state_store.py（状态持久化）
4. 实现 notifier.py（系统通知）

### Phase 2: FastAPI 服务
5. 实现 main.py（FastAPI 入口）
6. 实现 scheduler.py（APScheduler 调度）
7. 编写 archon-start.md / archon-stop.md / archon-status.md

### Phase 3: Probe 模式
8. 实现 probe_executor.py
9. 实现 transcript 分析逻辑
10. 实现纠偏引擎
11. 编写 start-probe.md / stop-probe.md

### Phase 4: Cron 模式
12. 实现 cron_executor.py
13. 实现 analyzer.py（结果分析）
14. 编写 start-cron.md / stop-cron.md

### Phase 5: 通用功能
15. 编写 list-tasks.md
16. 编写 check-task.md（手动检查）
17. 完善日志和错误处理
