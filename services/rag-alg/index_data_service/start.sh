#!/bin/bash

# 启动 index_fulltext_service
bash index_fulltext_service/src/index_fulltext_service_pactera/start.sh &
p1=$!

# 启动 index_graph_service
bash index_graph_service/start.sh &
p2=$!

# 启动 index_vector_service
bash index_vector_service/src/index_vector_service_pactera/start.sh &
p3=$!

# 启动 version_service
bash version_service/start.sh &
p4=$!

cleanup() {
    echo "关闭剩余进程..."
    kill -TERM $p1 $p2 $p3 $p4 2>/dev/null
    wait $p1 $p2 $p3 $p4 2>/dev/null
    exit 1
}

# 捕获信号，保证退出时清理
trap cleanup INT TERM

# 等待任意一个服务退出
while true; do
    for pid in $p1 $p2 $p3 $p4; do
        if ! kill -0 "$pid" 2>/dev/null; then
            wait "$pid"
            echo "有服务进程失败（PID=$pid），重启容器..."
            cleanup
        fi
    done
    sleep 2
done
