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
│   ├── corrections.md                    # 纠偏历史（Markdown 格式）
│   └── archon.log                        # 工作日志（带时间戳）
│
└── 20260201_150000_cron/                 # Cron 任务目录（时间戳+模式后缀）
    ├── config.json                       # 任务配置
    ├── status                            # 状态文件（active/stopped/paused）
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
| `archon.log` | 日志 | Archon 行动日志，每条带时间戳 |

#### Probe 模式专属

| 文件 | 格式 | 说明 |
|------|------|------|
| `config.json` | JSON | 任务 ID、Probe 会话 ID、检查间隔等 |
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
3. **全局配置 `setting.json`** 需要包含哪些内容？（通知方式、默认间隔...）
4. 是否需要 **锁文件** 防止并发执行？
5. **corrections.md** 的具体格式？
6. **config.json** 的具体字段？

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

