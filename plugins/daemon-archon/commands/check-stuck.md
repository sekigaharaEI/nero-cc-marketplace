# /check-stuck

检查卡住的任务

## 用法

```
/check-stuck
```

## 说明

检查所有任务是否有卡住的情况，包括：
- **Probe 无输出**：Probe 进程存活但长时间无 transcript 更新
- **Archon 检查超时**：Archon 检查任务时自身卡住
- **Cron 执行超时**：Cron 任务执行超过配置的超时时间

## 输出示例

```
卡住任务检测
============

检测到 2 个卡住的任务:

任务 ID: 20260201_143000_probe
  模式: probe
  卡住类型: probe_no_output
  卡住时长: 65.3 分钟
  详情: Probe 进程存活，但已 65.3 分钟无输出

任务 ID: 20260201_150000_cron
  模式: cron
  卡住类型: cron_execution_timeout
  卡住时长: 35.2 分钟
  详情: Cron 任务执行已进行 35.2 分钟，超过配置的超时时间 30 分钟

建议操作
--------
1. 检查 Probe 进程是否正常: ps -p <pid>
2. 查看任务日志: tail -f ~/.claude/daemon-archon/<task_id>/archon.log
3. 如需停止任务: /stop-probe <task_id> 或 /stop-cron <task_id>
```

## 实现

```bash
# 检查卡住的任务
curl -s "http://127.0.0.1:8765/stuck" | python3 -c "
import sys, json

data = json.load(sys.stdin)
stuck_tasks = data.get('stuck_tasks', [])

print('卡住任务检测')
print('============')
print()

if not stuck_tasks:
    print('✓ 没有发现卡住的任务')
else:
    print(f'检测到 {len(stuck_tasks)} 个卡住的任务:')
    print()

    for task in stuck_tasks:
        print(f\"任务 ID: {task['task_id']}\")
        print(f\"  模式: {task['task_mode']}\")
        print(f\"  卡住类型: {task['stuck_type']}\")
        print(f\"  卡住时长: {task['stuck_duration_minutes']} 分钟\")
        print(f\"  详情: {task['details']}\")
        print()

    print('建议操作')
    print('--------')
    print('1. 检查进程是否正常: ps -p <pid>')
    print('2. 查看任务日志: tail -f ~/.claude/daemon-archon/<task_id>/archon.log')
    print('3. 如需停止任务: /stop-probe <task_id> 或 /stop-cron <task_id>')
"
```

## 卡住阈值

| 卡住类型 | 默认阈值 | 说明 |
|---------|---------|------|
| probe_no_output | 60 分钟 | Probe 无 transcript 更新 |
| archon_check_timeout | 5 分钟 | Archon 检查超时 |
| cron_execution | 30 分钟 | Cron 任务执行超时（可配置） |

## 示例

```bash
# 检查卡住的任务
/check-stuck

# 如果发现卡住的 Probe，可以停止它
/stop-probe 20260201_143000_probe

# 或者查看日志了解情况
tail -f ~/.claude/daemon-archon/20260201_143000_probe/archon.log
```

## 相关命令

- `/list-tasks` - 列出所有任务
- `/check-task <task_id>` - 检查特定任务
- `/archon-status` - 查看服务状态
