# /archon-status

查看 Archon 服务和任务状态

## 用法

```
/archon-status
```

## 说明

显示 Archon 服务的运行状态，包括：
- 服务是否运行
- 任务总数和活跃任务数
- 调度器中的任务列表

## 输出示例

```
Archon 服务状态
================

服务状态: 运行中
PID: 12345
API 地址: http://127.0.0.1:8765

任务统计
--------
总任务数: 5
活跃任务: 3
  - Probe 任务: 1
  - Cron 任务: 2

调度任务
--------
| 任务 ID                    | 类型  | 下次执行时间          |
|---------------------------|-------|---------------------|
| probe_20260201_143000     | probe | 2026-02-01 14:35:00 |
| cron_20260201_150000      | cron  | 2026-02-01 16:00:00 |
| cron_20260201_160000      | cron  | 2026-02-01 17:00:00 |
```

## 实现

```bash
#!/bin/bash
# 查看 Archon 服务状态

PID_FILE="$HOME/.claude/daemon-archon/archon.pid"
API_URL="http://127.0.0.1:8765"

echo "Archon 服务状态"
echo "================"
echo ""

# 检查服务是否运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "服务状态: 运行中"
        echo "PID: $PID"
        echo "API 地址: $API_URL"
        echo ""

        # 获取详细状态
        if command -v curl &> /dev/null; then
            STATUS=$(curl -s "$API_URL/status" 2>/dev/null)
            if [ $? -eq 0 ]; then
                echo "任务统计"
                echo "--------"
                echo "$STATUS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"总任务数: {data.get('tasks_count', 0)}\")
print(f\"活跃任务: {data.get('active_tasks_count', 0)}\")
print()
print('调度任务')
print('--------')
for job in data.get('scheduler_jobs', []):
    print(f\"- {job.get('job_id')}: 下次执行 {job.get('next_run_time', 'N/A')}\")
"
            fi
        fi
    else
        echo "服务状态: 未运行（PID 文件已过期）"
    fi
else
    echo "服务状态: 未运行"
fi
```

## 示例

```bash
# 查看状态
/archon-status

# 如果服务未运行，启动它
/archon-start
```
