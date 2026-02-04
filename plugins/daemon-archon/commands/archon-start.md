# /archon-start

启动 Archon 后台服务

## 用法

```
/archon-start [--port=8765] [--host=127.0.0.1]
```

## 参数

- `--port`: 服务端口（默认 8765）
- `--host`: 服务地址（默认 127.0.0.1）

## 说明

启动 Archon 后台服务，该服务负责：
- 定时检查 Probe 任务状态
- 定时执行 Cron 任务
- 提供 HTTP API 接口

服务启动后会在后台运行，PID 保存在 `~/.claude/daemon-archon/archon.pid`。

## 实现

```bash
#!/bin/bash
# 启动 Archon 服务

SCRIPT_DIR="${CLAUDE_PLUGIN_ROOT}/scripts/server"
PID_FILE="$HOME/.claude/daemon-archon/archon.pid"

# 检查是否已运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Archon 服务已在运行 (PID: $PID)"
        exit 0
    fi
fi

# 确保目录存在
mkdir -p "$HOME/.claude/daemon-archon"

# 安装依赖（如果需要）
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "安装依赖..."
    pip3 install -r "$SCRIPT_DIR/requirements.txt"
fi

# 启动服务
export ARCHON_HOST="${1:-127.0.0.1}"
export ARCHON_PORT="${2:-8765}"

nohup python3 "$SCRIPT_DIR/main.py" > "$HOME/.claude/daemon-archon/server.log" 2>&1 &

echo "Archon 服务已启动"
echo "PID: $!"
echo "日志: ~/.claude/daemon-archon/server.log"
echo "API: http://$ARCHON_HOST:$ARCHON_PORT"
```

## 示例

```bash
# 使用默认配置启动
/archon-start

# 指定端口
/archon-start --port=9000

# 查看服务状态
/archon-status
```
