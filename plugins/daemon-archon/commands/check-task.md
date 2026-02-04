# /check-task

手动检查或执行任务

## 用法

```
/check-task <task_id>
```

## 参数

- `task_id`: 任务 ID

## 说明

手动触发任务检查或执行：
- **Probe 任务**：检查 Probe 状态，分析 transcript，判断是否需要纠偏
- **Cron 任务**：立即执行一次 Cron 任务

## 输出示例

### Probe 任务

```
任务检查结果: 20260201_143000_probe
===================================

任务类型: probe
任务名称: 代码重构任务
任务状态: active

Probe 状态分析
--------------
状态: running
进度: 60%
最后活动: 5 分钟前

问题列表
--------
无

结论: Probe 运行正常，无需干预
```

### Cron 任务

```
任务执行结果: 20260201_150000_cron
===================================

任务类型: cron
任务名称: 日志检查
执行状态: success

执行结果
--------
{
  "status": "success",
  "summary": "未发现异常",
  "findings": [],
  "metrics": {
    "error_count": 0,
    "warning_count": 3
  }
}
```

## 实现

```bash
# 获取任务信息
TASK_INFO=$(curl -s "http://127.0.0.1:8765/tasks/${TASK_ID}")
MODE=$(echo "$TASK_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('mode',''))")

if [ "$MODE" = "probe" ]; then
    # 检查 Probe 状态
    curl -X POST "http://127.0.0.1:8765/probe/${TASK_ID}/check"
elif [ "$MODE" = "cron" ]; then
    # 执行 Cron 任务
    curl -X POST "http://127.0.0.1:8765/cron/${TASK_ID}/execute"
fi
```

## 示例

```bash
# 检查 Probe 任务状态
/check-task 20260201_143000_probe

# 手动执行 Cron 任务
/check-task 20260201_150000_cron

# 查看任务日志
tail -f ~/.claude/daemon-archon/20260201_143000_probe/archon.log
```

## 相关命令

- `/list-tasks` - 列出所有任务
- `/stop-probe <task_id>` - 停止 Probe 任务
- `/stop-cron <task_id>` - 停止 Cron 任务
