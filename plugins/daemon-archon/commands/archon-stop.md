# /archon-stop

停止 Archon 后台服务

## 用法

```
/archon-stop
```

## 说明

停止正在运行的 Archon 后台服务。

**注意**：停止服务后，所有定时任务将暂停执行，但任务配置会保留。重新启动服务后，活跃任务会自动恢复。

## 实现

```bash
#!/bin/bash
# 停止 Archon 服务

PID_FILE="$HOME/.claude/daemon-archon/archon.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Archon 服务未运行"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p $PID > /dev/null 2>&1; then
    echo "Archon 服务未运行（PID 文件已过期）"
    rm -f "$PID_FILE"
    exit 0
fi

# 发送 SIGTERM 信号
kill $PID

# 等待进程退出
for i in {1..10}; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "Archon 服务已停止"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# 强制终止
kill -9 $PID 2>/dev/null
rm -f "$PID_FILE"
echo "Archon 服务已强制停止"
```

## 示例

```bash
# 停止服务
/archon-stop

# 确认服务已停止
/archon-status
```
