# daemon-archon 守护进程执政官

Claude Code 定时任务调度和智能体监控插件。

## 功能特性

### 两种工作模式

#### Probe 模式（监控智能体）
- 启动并监控一个持续运行的 Claude Code CLI（Probe）
- 定时分析 Probe 的执行状态（transcript、日志、输出）
- 自动纠偏：检测到问题时注入纠偏指令
- 人工介入：严重问题时发送系统通知

**适用场景**：代码重构、长期开发任务、需要 Claude Code 持续执行的任务

#### Cron 模式（定时任务）
- 定时执行临时 Claude Code CLI 任务
- 每次执行都是新的会话，无上下文
- 分析执行结果，按需发送通知

**适用场景**：定时检查、日志分析、状态巡检、周期性任务

### 核心功能

- **FastAPI 服务**：内嵌轻量级 HTTP API 服务
- **APScheduler 调度**：精确的定时任务调度
- **卡住检测**：自动检测并处理长时间未完成的任务
- **系统通知**：支持系统通知、Slack、Webhook 等多种通知方式
- **状态持久化**：JSON 文件存储，服务重启后自动恢复任务

## 安装

```bash
# 从 marketplace 安装
/plugin install daemon-archon@nero-cc-marketplace
```

## 快速开始

### 1. 检查环境

```bash
/archon-init
```

### 2. 启动服务

```bash
/archon-start
```

### 3. 创建任务

```bash
# Probe 模式：启动长期任务
/start-probe 请重构 src/legacy 目录，将旧代码迁移到新架构

# Cron 模式：创建定时任务
/start-cron 每小时检查服务器日志，发现 ERROR 级别错误就通知我
```

### 4. 查看任务

```bash
/list-tasks
```

## 命令列表

### 服务管理

| 命令 | 说明 |
|------|------|
| `/archon-init` | 检查环境并初始化 |
| `/archon-start` | 启动 Archon 后台服务 |
| `/archon-stop` | 停止 Archon 后台服务 |
| `/archon-status` | 查看服务和任务状态 |

### Probe 模式

| 命令 | 说明 |
|------|------|
| `/start-probe <description>` | 启动 Probe 模式任务 |
| `/stop-probe <task_id>` | 停止 Probe 任务 |

### Cron 模式

| 命令 | 说明 |
|------|------|
| `/start-cron <description>` | 创建并启动 Cron 任务 |
| `/stop-cron <task_id>` | 停止 Cron 任务 |

### 通用

| 命令 | 说明 |
|------|------|
| `/list-tasks` | 列出所有任务 |
| `/check-task <task_id>` | 手动检查/执行任务 |
| `/check-stuck` | 检查卡住的任务 |

## 目录结构

```
~/.claude/daemon-archon/
├── setting.json                    # 全局配置
├── archon.pid                      # 服务 PID 文件
├── server.log                      # 服务日志
├── 20260201_143000_probe/          # Probe 任务目录
│   ├── config.json                 # 任务配置
│   ├── status                      # 状态文件
│   ├── task.lock                   # 任务锁
│   ├── destination.md              # 任务目标
│   ├── corrections.md              # 纠偏历史
│   ├── archon.log                  # 监控日志
│   ├── probe_stdout.log            # Probe 标准输出
│   └── probe_stderr.log            # Probe 错误输出
└── 20260201_150000_cron/           # Cron 任务目录
    ├── config.json                 # 任务配置
    ├── status                      # 状态文件
    ├── task.lock                   # 任务锁
    ├── task.md                     # 任务描述
    ├── workflow/
    │   └── workflow.md             # 工作流程
    └── archon.log                  # 执行日志
```

## 配置说明

### 全局配置 (setting.json)

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

## API 接口

服务启动后，可通过 HTTP API 进行操作：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/status` | GET | 获取服务状态 |
| `/tasks` | GET | 列出所有任务 |
| `/tasks/{task_id}` | GET | 获取任务详情 |
| `/probe/create` | POST | 创建 Probe 任务 |
| `/probe/{task_id}/check` | POST | 检查 Probe 状态 |
| `/probe/{task_id}/stop` | POST | 停止 Probe 任务 |
| `/cron/create` | POST | 创建 Cron 任务 |
| `/cron/{task_id}/execute` | POST | 执行 Cron 任务 |
| `/cron/{task_id}/stop` | POST | 停止 Cron 任务 |
| `/stuck` | GET | 检查卡住的任务 |

## 依赖

- Python >= 3.8
- Claude CLI
- fastapi >= 0.100.0
- uvicorn >= 0.23.0
- apscheduler >= 3.10.0
- psutil >= 5.9.0

## 设计参考

本插件的定时任务系统借鉴了 OpenClaw 的优秀设计：
- 精确的定时器管理（基于 setTimeout 的精确调度）
- 完善的任务状态追踪（运行次数、错误统计、执行时长）
- 卡住检测机制（自动检测并处理长时间未完成的任务）
- 灵活的执行模式（主会话 vs 隔离会话）

## 许可证

MIT License
