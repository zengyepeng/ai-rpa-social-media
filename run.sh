#!/usr/bin/env bash
# 启动AI Agent服务 + 调度器
# 用法: bash run.sh [start|stop|restart|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
AGENT_PORT=${AGENT_PORT:-8888}
SCHEDULER_POLL=${SCHEDULER_POLL:-30}

PID_FILE="$SERVER_DIR/.server.pid"
LOG_DIR="$SERVER_DIR/logs"

mkdir -p "$LOG_DIR"

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "服务已在运行 (PID $(cat "$PID_FILE"))"
        return
    fi

    echo "启动 AI Agent 服务..."
    echo "端口: $AGENT_PORT"
    echo "日志: $LOG_DIR/"

    # 启动 agent_server.py
    cd "$SERVER_DIR"
    nohup python3 agent/agent_server.py \
        >> "$LOG_DIR/agent.log" 2>&1 &
    AGENT_PID=$!
    echo $AGENT_PID > "$PID_FILE"
    echo "Agent 服务已启动 (PID $AGENT_PID)"

    # 等一秒确保起来
    sleep 1

    # 初始化数据库
    python3 -c "import sys; sys.path.insert(0,'$SERVER_DIR'); from db.database import init_db; init_db()" \
        >> "$LOG_DIR/db.log" 2>&1
    echo "数据库初始化完成"

    echo ""
    echo "API 端点:"
    echo "  POST /agent/generate   生成内容"
    echo "  POST /agent/reply      生成回复"
    echo "  POST /agent/analyze    数据分析"
    echo "  GET  /agent/ping       健康检查"
    echo ""
    echo "调度器: 先跑 scheduler.py 单独启动"
    echo "  python3 scheduler/scheduler.py"
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        kill "$PID" 2>/dev/null || true
        rm -f "$PID_FILE"
        echo "服务已停止"
    else
        echo "服务未运行"
    fi
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        PID=$(cat "$PID_FILE")
        echo "✅ Agent 服务运行中 (PID $PID)"
        curl -s http://127.0.0.1:$AGENT_PORT/agent/ping 2>/dev/null || echo "⚠️  健康检查未响应"
    else
        echo "❌ Agent 服务未运行"
    fi
}

case "${1:-start}" in
    start) start ;;
    stop) stop ;;
    restart) stop; sleep 1; start ;;
    status) status ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
