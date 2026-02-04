#!/bin/bash
# daemon-archon 服务启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
BASE_DIR="$HOME/.claude/daemon-archon"
PID_FILE="$BASE_DIR/archon.pid"
LOG_FILE="$BASE_DIR/server.log"
ENV_CONF="$BASE_DIR/env.conf"

# 国内镜像源
PYPI_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple"

# 默认配置
HOST="${ARCHON_HOST:-127.0.0.1}"
PORT="${ARCHON_PORT:-8765}"
PYTHON_CMD="python3"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --host=*)
            HOST="${1#*=}"
            shift
            ;;
        --port=*)
            PORT="${1#*=}"
            shift
            ;;
        --help)
            echo "用法: $0 [--host=HOST] [--port=PORT]"
            echo ""
            echo "选项:"
            echo "  --host=HOST  服务地址 (默认: 127.0.0.1)"
            echo "  --port=PORT  服务端口 (默认: 8765)"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 确保目录存在
mkdir -p "$BASE_DIR"

# 读取环境配置
if [ -f "$ENV_CONF" ]; then
    echo "读取环境配置..."
    source "$ENV_CONF"
    if [ -n "$PYTHON_PATH" ] && [ -x "$PYTHON_PATH" ]; then
        PYTHON_CMD="$PYTHON_PATH"
        echo "使用 Python: $PYTHON_CMD"
        if [ -n "$ENV_NAME" ]; then
            echo "环境: $ENV_NAME"
        fi
    fi
fi

# 检查是否已运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Archon 服务已在运行 (PID: $PID)"
        echo "API 地址: http://$HOST:$PORT"
        exit 0
    else
        echo "清理过期的 PID 文件..."
        rm -f "$PID_FILE"
    fi
fi

# 检查 Python
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "错误: 未找到 $PYTHON_CMD"
    echo "请先运行 /archon-init 初始化环境"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
MISSING_DEPS=""
for pkg in fastapi uvicorn apscheduler psutil; do
    if ! $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
        MISSING_DEPS="$MISSING_DEPS $pkg"
    fi
done

if [ -n "$MISSING_DEPS" ]; then
    echo "安装缺失的依赖:$MISSING_DEPS (使用清华源)"
    $PYTHON_CMD -m pip install -i "$PYPI_MIRROR" -r "$SERVER_DIR/requirements.txt"
fi

# 启动服务
echo "启动 Archon 服务..."
export ARCHON_HOST="$HOST"
export ARCHON_PORT="$PORT"

# 使用模块方式运行，解决相对导入问题
cd "$SCRIPT_DIR" && nohup $PYTHON_CMD -m server.main > "$LOG_FILE" 2>&1 &
PID=$!

# 等待服务启动
sleep 2

# 检查是否启动成功
if ps -p $PID > /dev/null 2>&1; then
    echo "$PID" > "$PID_FILE"
    echo ""
    echo "Archon 服务已启动"
    echo "  PID: $PID"
    echo "  API: http://$HOST:$PORT"
    echo "  日志: $LOG_FILE"
else
    echo "错误: 服务启动失败"
    echo "查看日志: cat $LOG_FILE"
    exit 1
fi
