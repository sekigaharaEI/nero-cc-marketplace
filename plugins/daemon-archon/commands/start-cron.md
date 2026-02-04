# /start-cron

创建并启动 Cron 模式任务

## 用法

```
/start-cron <task_description>
```

## 参数

- `task_description`: 任务描述

## 说明

创建一个 Cron 模式任务。Cron 任务会定时执行，每次执行都是一个新的临时 Claude Code 会话。

**适用场景**：
- 定时检查服务器日志
- 定时执行代码质量检查
- 定时生成报告
- 周期性巡检任务

## 工作流程

1. 根据用户描述生成任务配置
2. 创建 `task.md` 和 `workflow/workflow.md`
3. 注册定时任务到 Archon 调度器
4. 定时触发时，启动临时 Claude Code CLI 执行任务
5. 分析执行结果，按需发送通知

## 任务文件结构

```
~/.claude/daemon-archon/{task_id}/
├── config.json           # 任务配置
├── status                # 状态文件
├── task.md               # 任务描述
├── workflow/
│   └── workflow.md       # 工作流程定义
└── archon.log            # 执行日志
```

## 实现

当用户执行 `/start-cron` 时，Claude Code 应该：

1. 确保 Archon 服务正在运行
2. 根据用户描述生成 `task.md` 和 `workflow.md`
3. 调用 Archon API 创建 Cron 任务

```bash
# 创建 Cron 任务
curl -X POST http://127.0.0.1:8765/cron/create \
    -H "Content-Type: application/json" \
    -d '{
        "name": "任务名称",
        "description": "任务描述",
        "project_path": "<current_project_path>",
        "task_content": "<task.md 内容>",
        "workflow_content": "<workflow.md 内容>",
        "cron_expression": "0 * * * *",
        "check_interval_minutes": 60,
        "timeout_minutes": 10
    }'
```

## 示例

```bash
# 创建日志检查任务
/start-cron 每小时检查服务器日志，发现 ERROR 或 FATAL 级别错误就通知我

# 创建代码质量检查任务
/start-cron 每天早上 9 点运行 lint 检查，报告代码质量问题

# 查看任务状态
/list-tasks
```

## Workflow 格式

生成的 `workflow.md` 应遵循以下格式：

```markdown
# Workflow: {任务名称}

## 元信息
- 版本: 1.0
- 预计耗时: 5 分钟
- 失败策略: stop_on_error

## 执行步骤

### Step 1: {步骤名称}
- 动作: {具体要做什么}
- 成功条件: {什么情况算成功}
- 失败处理: {失败时怎么办}

### Step 2: {步骤名称}
- 动作: {具体要做什么}
- 成功条件: {什么情况算成功}

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

## 相关命令

- `/stop-cron <task_id>` - 停止 Cron 任务
- `/check-task <task_id>` - 手动执行任务
- `/list-tasks` - 列出所有任务
