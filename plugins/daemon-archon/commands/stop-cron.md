# /stop-cron

停止 Cron 任务

## 用法

```
/stop-cron <task_id>
```

## 参数

- `task_id`: 任务 ID

## 说明

停止指定的 Cron 任务。这会：
1. 从调度器移除定时任务
2. 更新任务状态为 `stopped`

**注意**：任务配置和日志会保留，可以通过 `/list-tasks` 查看历史任务。

## 实现

```bash
# 停止 Cron 任务
curl -X POST "http://127.0.0.1:8765/cron/${TASK_ID}/stop"
```

## 示例

```bash
# 列出任务，获取任务 ID
/list-tasks

# 停止指定任务
/stop-cron 20260201_150000_cron

# 确认任务已停止
/list-tasks
```

## 相关命令

- `/start-cron` - 创建 Cron 任务
- `/check-task <task_id>` - 手动执行任务
- `/list-tasks` - 列出所有任务
