#!/bin/bash

# 获取当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 设置 PYTHONPATH，确保可以找到当前目录的模块
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# 启动 index_graph_service
# stdbuf+sed -u 保证通过管道时日志行缓冲，避免 docker logs 观察到延迟
exec stdbuf -oL -eL gunicorn -c gunicorn_conf.py \
    "graph_api_start:graph_app" \
    --access-logfile - \
    --capture-output \
    --log-level info 2>&1 | stdbuf -oL -eL sed -u 's/^/[graph]/'

