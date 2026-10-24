#!/usr/bin/env bash
# R12：为知识库桶设置"仅对象读"的匿名策略，使前端 /minio 反代可直接打开引用原文。
# 安全边界（必须与交付报告口径一致）：
#   - 仅授予 s3:GetObject，不含 ListBucket / PutObject / DeleteObject；
#   - 仅限隔离/预生产环境；生产应改为后端 viewFile 用 AK/SK 流式转发或预签名 URL。
set -euo pipefail
R12_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$R12_ROOT/venvs/parse/bin/python"
[[ -x "$PY" ]] || PY="python3"
"$PY" - <<'EOF'
import json, os, sys
from minio import Minio

endpoint = os.environ.get("R12_MINIO_ENDPOINT", "127.0.0.1:19000")
ak = os.environ.get("R12_MINIO_ACCESS_KEY", "r12minio")
sk = os.environ.get("R12_MINIO_SECRET_KEY", "")
bucket = os.environ.get("R12_MINIO_BUCKET", "r12-rag")
if not sk:
    sys.exit("R12_MINIO_SECRET_KEY 未设置（从 platform/r12/.env 注入）")

cli = Minio(endpoint, access_key=ak, secret_key=sk, secure=False)
policy = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"AWS": ["*"]},
        "Action": ["s3:GetObject"],
        "Resource": [f"arn:aws:s3:::{bucket}/*"],
    }],
}
cli.set_bucket_policy(bucket, json.dumps(policy))
print(f"bucket {bucket} policy set: s3:GetObject anonymous (read-only)")
EOF
