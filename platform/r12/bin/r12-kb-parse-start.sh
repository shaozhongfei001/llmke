#!/usr/bin/env bash
# 幂等启动 18097「上传回调入口」（方案 A：MinIO 原件 → doc2md 四件套 → 18096 消费）。
#
# 为什么需要自检：这个服务同时依赖 MinIO 凭据、doc2md 配置、18096 可达。
# 任何一项缺失时进程能起来但每条上传都会失败，比"起不来"更糟。
# 因此先 fail-fast 自检，再幂等启动，最后用 /health 确认。
#
# 用法：
#   r12-kb-parse-start.sh            # 自检 + 幂等启动
#   r12-kb-parse-start.sh --check    # 只自检，不启停
set -uo pipefail

R12_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V2_SVC_DIR="/home/szf/data/dev/llmke/services/rag-alg/index_data_service"
PY="/home/szf/data/dev/hipporag-toolenv/bin/python"   # 需 fastapi + boto3 + requests
PORT="18097"
LOG="$R12_ROOT/logs/kb-parse-service.log"
DOC2MD_CONFIG="${LLMKE_DOC2MD_CONFIG:-/home/szf/data/dev/doc2md/config/app.yaml}"
INGEST_URL="${LLMKE_INGEST_URL:-http://127.0.0.1:18096/kb/ingest}"

mkdir -p "$(dirname "$LOG")"
fail_n=0
check() {
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "  [ok]   $desc"; else echo "  [FAIL] $desc" >&2; fail_n=$((fail_n + 1)); fi
}

echo "[check] 18097 依赖自检"
check "服务模块存在" test -f "$V2_SVC_DIR/kb_parse_service.py"
check "解释器可 import fastapi/boto3/requests" "$PY" -c "import fastapi,boto3,requests"
check "doc2md 配置存在" test -f "$DOC2MD_CONFIG"
check "18096 摄取服务健康" curl -s --max-time 5 http://127.0.0.1:18096/health
check "18094 图服务健康" curl -s --max-time 5 http://127.0.0.1:18094/health

# 凭据只从运行中的 r12-minio 容器取，不写进仓库、不回显
if docker ps --format '{{.Names}}' | grep -qx r12-minio; then
  eval "$(docker inspect r12-minio --format '{{json .Config.Env}}' | "$PY" -c "
import sys, json, shlex
d = dict(x.split('=', 1) for x in json.load(sys.stdin) if '=' in x)
print('export LLMKE_MINIO_USER=' + shlex.quote(d.get('MINIO_ROOT_USER', '')))
print('export LLMKE_MINIO_PASSWORD=' + shlex.quote(d.get('MINIO_ROOT_PASSWORD', '')))
")"
  check "MinIO 凭据可取" test -n "${LLMKE_MINIO_USER:-}${LLMKE_MINIO_PASSWORD:-}"
else
  echo "  [FAIL] r12-minio 未运行" >&2
  fail_n=$((fail_n + 1))
fi

if [ "$fail_n" -gt 0 ]; then
  echo "[check] 自检失败 $fail_n 项，拒绝带病启动" >&2
  exit 1
fi
echo "[check] 自检通过"
if [ "${1:-}" = "--check" ]; then exit 0; fi

if curl -s --max-time 5 "http://127.0.0.1:$PORT/health" | grep -q '"status":"ok"'; then
  echo "[start] 18097 已健康，跳过（幂等）"
  exit 0
fi

export PYTHONPATH="$V2_SVC_DIR"
export LLMKE_DOC2MD_CONFIG="$DOC2MD_CONFIG"
export LLMKE_INGEST_URL="$INGEST_URL"
(
  cd "$V2_SVC_DIR" || exit 1
  nohup "$PY" -m uvicorn kb_parse_service:app --host 127.0.0.1 --port "$PORT" \
    >> "$LOG" 2>&1 < /dev/null &
)
for _ in $(seq 1 20); do
  if curl -s --max-time 3 "http://127.0.0.1:$PORT/health" | grep -q '"status":"ok"'; then
    echo "[start] 18097 已就绪：$INGEST_URL"
    exit 0
  fi
  sleep 1
done
echo "[start] 18097 启动后 /health 未就绪，见 $LOG" >&2
exit 1
