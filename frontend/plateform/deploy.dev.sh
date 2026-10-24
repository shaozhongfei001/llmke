#!/bin/bash

# 变量配置
LOCAL_DIST_DIR="./dist"
LOCAL_RAG_DIR="./rag"
REMOTE_USER="p6012575"
REMOTE_PASS="Gientech123"
REMOTE_HOST="10.15.12.13"
REMOTE_DIR="/mnt/4917bc85-2af2-4737-9557-f2e2b600ba7f/nginx_web_9005/project"
REMOTE_RAG_DIR="$REMOTE_DIR/rag"
REMOTE_TMP_DIR="$REMOTE_DIR/rag_tmp"


# 1. 本地复制（而不是mv）
if [ -d "$LOCAL_DIST_DIR" ]; then
  rm -rf "$LOCAL_RAG_DIR"
  cp -r "$LOCAL_DIST_DIR" "$LOCAL_RAG_DIR"
fi

# 2. 上传到服务器临时目录
sshpass -p "$REMOTE_PASS" scp -r "$LOCAL_RAG_DIR" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_TMP_DIR"

# 3. 远程替换
sshpass -p "$REMOTE_PASS" ssh -tt "$REMOTE_USER@$REMOTE_HOST" << EOF
  rm -rf "$REMOTE_RAG_DIR"
  mv "$REMOTE_TMP_DIR" "$REMOTE_RAG_DIR"
EOF

echo "部署完成！"