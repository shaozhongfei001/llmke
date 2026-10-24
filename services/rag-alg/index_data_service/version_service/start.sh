#!/bin/bash

# 获取当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 设置 PYTHONPATH，确保可以找到当前目录的模块
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

exec stdbuf -oL -eL gunicorn "server:app" \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:19525 \
    --workers 1 \
    --access-logfile - \
    --capture-output \
    --log-level info 2>&1 | stdbuf -oL -eL sed -u 's/^/[version]/'
