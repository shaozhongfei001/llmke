#!/usr/bin/env bash
# R13 Office 预览服务（18095）构建/启停/探活
# 用法: run.sh {build|up|down|restart|logs|status|smoke}
set -uo pipefail
PV="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R12="$(cd "$PV/../.." && pwd)"
IMAGE="${PREVIEW_IMAGE:-r12/preview-office:r13}"
CONTAINER=r12-preview
PORT="${PREVIEW_PORT:-18095}"
ENVF="$R12/.env"

load_env() {
  if [ -f "$ENVF" ]; then
    set -a; . "$ENVF"; set +a
  fi
}

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }

do_build() {
  echo "== docker build $IMAGE =="
  docker build -t "$IMAGE" "$PV" || return 1
  ok "built $IMAGE"
}

do_up() {
  load_env
  docker rm -f "$CONTAINER" >/dev/null 2>&1
  docker run -d --name "$CONTAINER" \
    --network host \
    -e PREVIEW_HOST="${PREVIEW_HOST:-127.0.0.1}" \
    --restart unless-stopped \
    -e MINIO_ENDPOINT="${PREVIEW_MINIO_ENDPOINT:-127.0.0.1:19000}" \
    -e MINIO_ACCESS_KEY="${R12_MINIO_ACCESS_KEY:-r12minio}" \
    -e MINIO_SECRET_KEY="${R12_MINIO_SECRET_KEY:-R12minio#2026local}" \
    -e MINIO_BUCKET="${PREVIEW_MINIO_BUCKET:-r12-rag}" \
    -e MINIO_SECURE=false \
    -e CONVERT_TIMEOUT=60 \
    -e MAX_CONCURRENT_CONVERSIONS=2 \
    -e PORT="$PORT" \
    -v "$R12/logs/preview:/logs" \
    "$IMAGE" >/dev/null || return 1

  for i in $(seq 1 40); do
    if curl -fsS -m 3 "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
      ok "$CONTAINER up on $PORT"
      curl -sS -m 5 "http://127.0.0.1:$PORT/healthz"; echo
      return 0
    fi
    sleep 1
  done
  warn "$CONTAINER 未在 40s 内就绪"
  docker logs --tail 40 "$CONTAINER"
  return 1
}

case "${1:-status}" in
  build)   do_build ;;
  up)      do_up ;;
  down)    docker rm -f "$CONTAINER" >/dev/null 2>&1 && ok "removed $CONTAINER" ;;
  restart) docker restart "$CONTAINER" >/dev/null 2>&1 && ok "restarted" || do_up ;;
  logs)    docker logs --tail "${2:-80}" "$CONTAINER" ;;
  status)
    docker ps -a --filter "name=^${CONTAINER}$" --format '  {{.Names}}\t{{.Status}}\t{{.Image}}'
    printf '  healthz: '; curl -sS -m 5 "http://127.0.0.1:$PORT/healthz" || echo 'down'; echo
    ;;
  smoke)   python3 "$PV/smoke_matrix.py" ;;
  *) echo "用法: $0 {build|up|down|restart|logs|status|smoke}"; exit 2 ;;
esac
