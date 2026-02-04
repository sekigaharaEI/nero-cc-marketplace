# /list-tasks

列出所有任务

## 用法

```
/list-tasks [--mode=probe|cron] [--status=active|stopped|paused]
```

## 参数

- `--mode`: 按模式筛选（可选）
- `--status`: 按状态筛选（可选）

## 说明

列出所有 daemon-archon 管理的任务，包括 Probe 和 Cron 模式的任务。

## 输出示例

```
daemon-archon 任务列表
======================

| 任务 ID                    | 模式  | 名称           | 状态   | 创建时间            |
|---------------------------|-------|----------------|--------|---------------------|
| 20260201_143000_probe     | probe | 代码重构任务    | active | 2026-02-01 14:30:00 |
| 20260201_150000_cron      | cron  | 日志检查       | active | 2026-02-01 15:00:00 |
| 20260131_100000_probe     | probe | 测试修复       | stopped| 2026-01-31 10:00:00 |

总计: 3 个任务 (2 个活跃)
```

## 实现

```bash
# 获取任务列表
curl -s "http://127.0.0.1:8765/tasks" | python3 -c "
import sys, json
from datetime import datetime

data = json.load(sys.stdin)
tasks = data.get('tasks', [])

print('daemon-archon 任务列表')
print('======================')
print()
print(f\"{'任务 ID':<28} {'模式':<6} {'名称':<15} {'状态':<8} {'创建时间'}\")
print('-' * 80)

active_count = 0
for task in tasks:
    task_id = task.get('task_id', '')
    mode = task.get('mode', '')
    name = task.get('name', '')[:15]
    status = task.get('state', {}).get('status', '')
    created = task.get('created_at', '')[:19].replace('T', ' ')

    print(f'{task_id:<28} {mode:<6} {name:<15} {status:<8} {created}')

    if status == 'active':
        active_count += 1

print()
print(f'总计: {len(tasks)} 个任务 ({active_count} 个活跃)')
"
```

## 示例

```bash
# 列出所有任务
/list-tasks

# 只列出 Probe 任务
/list-tasks --mode=probe

# 只列出活跃任务
/list-tasks --status=active

# 查看特定任务详情
/check-task 20260201_143000_probe
```

## 相关命令

- `/check-task <task_id>` - 查看任务详情
- `/start-probe` - 启动 Probe 任务
- `/start-cron` - 启动 Cron 任务
