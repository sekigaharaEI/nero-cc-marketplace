#!/bin/bash
# daemon-archon 服务停止脚本

BASE_DIR="$HOME/.claude/daemon-archon"
PID_FILE="$BASE_DIR/archon.pid"

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

echo "停止 Archon 服务 (PID: $PID)..."

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
echo "强制终止进程..."
kill -9 $PID 2>/dev/null
rm -f "$PID_FILE"
echo "Archon 服务已强制停止"
