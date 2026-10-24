COMMAND="python -u alg_doc_parse_service_start.py"

# 检查是否启动
pid=$(pgrep -f "$COMMAND")

# 如果找到运行中的进程，杀掉它
if [ -n "$pid" ]; then
    echo "Killing process with PID: $pid"
    kill -9 $pid
fi

$COMMAND > alg_doc_parse_service.log 2>&1 &
