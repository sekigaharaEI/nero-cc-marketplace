# daemon-archon 使用说明（开发版）

## 本地安装

```bash
/plugin install /data/zyw/nero-cc-marketplace/plugins/daemon-archon
```

## 快速启动

```bash
# 1. 初始化（交互式向导）
/archon-init
# - 检测 conda 环境
# - 选择：使用当前环境 / 新建 daemon-archon 环境 / 系统 Python
# - 选择：自动安装（清华源）/ 手动安装

# 2. 启动服务
/archon-start

# 3. 查看状态
/archon-status
```

## 环境配置

初始化后会保存配置到 `~/.claude/daemon-archon/env.conf`：
```
PYTHON_PATH=/path/to/python
ENV_NAME=daemon-archon
```

启动脚本会自动读取此配置。

## Probe 模式

长期任务监控，适合代码重构、持续开发等场景。

```bash
# 启动
/start-probe 请重构 src/legacy 目录

# 停止
/stop-probe <task_id>
```

## Cron 模式

定时任务，每次执行都是新会话。

```bash
# 启动（自然语言描述时间）
/start-cron 每小时检查服务器日志

# 停止
/stop-cron <task_id>
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `/list-tasks` | 列出所有任务 |
| `/check-task <id>` | 手动检查任务 |
| `/check-stuck` | 检查卡住的任务 |
| `/archon-stop` | 停止服务 |

## 目录结构

```
~/.claude/daemon-archon/
├── setting.json          # 全局配置
├── archon.pid            # PID 文件
├── server.log            # 服务日志
└── <task_id>/            # 任务目录
    ├── config.json       # 任务配置
    ├── status            # 状态文件
    └── archon.log        # 任务日志
```

## API 端点

服务默认运行在 `http://127.0.0.1:8765`

```bash
# 状态
curl http://127.0.0.1:8765/status

# 任务列表
curl http://127.0.0.1:8765/tasks

# 卡住检测
curl http://127.0.0.1:8765/stuck
```

## 调试

```bash
# 查看服务日志
tail -f ~/.claude/daemon-archon/server.log

# 查看任务日志
tail -f ~/.claude/daemon-archon/<task_id>/archon.log
```
