#!/usr/bin/env bash
# R13 全栈一键启动/停止/状态（按依赖顺序，幂等）
# 顺序：基础设施(容器) -> 模型 -> 算法(向量/全文/检索/LLM) -> 文档解析 -> 图谱服务 -> 业务服务 -> Office 预览 -> 前端
# 用法: up.sh {up|down|status|verify}
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$R12/../.." && pwd)"
ok() { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }

wait_port() {  # wait_port <port> <seconds>
  local p=$1 t=${2:-60} i=0
  while (( i < t )); do
    ss -lnt 2>/dev/null | grep -q ":$p " && return 0
    sleep 1; ((i++))
  done
  return 1
}

have_port() { ss -lnt 2>/dev/null | grep -q ":$1 "; }

case "${1:-status}" in
up)
  echo "== 1. 基础设施（容器，命名卷保留数据；含 Nebula 3.8）=="
  ( cd "$R12/docker" && docker compose -f docker-compose.infra.yml --env-file "$R12/.env" up -d >/dev/null 2>&1 )
  for p in 13306 16379 19000 19200 19630 18848 19669; do
    wait_port "$p" 120 && ok "port $p" || warn "port $p 未就绪"
  done

  echo "== 2. 模型服务（18090 embedding / 18091 rerank / 18092 llm / 18093 vlm）=="
  bash "$R12/models/start-all.sh" up 2>&1 | tail -3

  echo "== 3. 算法服务（19526 向量 / 19527 全文 / 19529 图 / 19995 检索 / 19996 LLM）=="
  bash "$R12/run/algctl.sh" start all 2>&1 | sed 's/^/  /'

  echo "== 4. 文档解析（12340）=="
  if have_port 12340; then
    ok "doc-parse 已在运行"
  else
    ( set -a; . "$R12/run/doc-parse.env"; set +a
      cd "$REPO/services/rag-alg/alg_doc_parse_service" && \
      nohup setsid "$R12/venvs/parse/bin/python" -u alg_doc_parse_service_start.py \
        > "$R12/logs/doc-parse.log" 2>&1 & )
    wait_port 12340 90 && ok "doc-parse started" || warn "doc-parse 未就绪"
  fi

  echo "== 5. 图谱服务（18084，依赖 Nebula 19669）=="
  "$R12/bin/r12ctl.sh" start rag-graph-service 2>&1 | sed 's/^/  /'

  echo "== 6. 业务服务（auth/index/qa/sensitive/gateway）=="
  "$R12/bin/r12ctl.sh" start rag-auth-service rag-index-service rag-qa-service sensitive-words-service rag-gateway 2>&1 | sed 's/^/  /'

  echo "== 7. Office 预览（容器 r12-preview，18095）=="
  if docker ps --format '{{.Names}}' | grep -q '^r12-preview$'; then
    ok "r12-preview 已在运行"
  elif docker ps -a --format '{{.Names}}' | grep -q '^r12-preview$'; then
    docker start r12-preview >/dev/null 2>&1 && wait_port 18095 60 && ok "r12-preview started" || warn "r12-preview 启动失败"
  else
    warn "镜像/容器不存在，执行: $R12/preview/run.sh up"
  fi

  echo "== 8. 前端 =="
  if ! curl -sS -o /dev/null -m 3 http://127.0.0.1:18088/ 2>/dev/null; then
    if docker ps -a --format '{{.Names}}' | grep -q '^r12-fe$'; then
      docker start r12-fe >/dev/null 2>&1 || docker restart r12-fe >/dev/null 2>&1
      sleep 5; docker exec r12-fe nginx -s reload >/dev/null 2>&1
      ok "r12-fe restarted"
    else warn "前端容器 r12-fe 不存在，见 frontend/plateform/nginx/r12-18088.conf"; fi
  else ok "18088 已在服务"; fi
  if ! curl -sS -o /dev/null -m 3 http://127.0.0.1:15174/ 2>/dev/null; then
    ( cd "$REPO/frontend/plateform" && nohup setsid npm run dev > "$R12/logs/fe-dev.log" 2>&1 & ) && sleep 12 && ok "dev 15174 启动"
  else ok "15174 已在服务"; fi
  ;;
down)
  "$R12/bin/r12ctl.sh" stop 2>&1 | sed 's/^/  /'
  bash "$R12/run/algctl.sh" stop all 2>&1 | sed 's/^/  /'
  bash "$R12/models/start-all.sh" down 2>&1 | tail -2
  pkill -f alg_doc_parse_service_start.py 2>/dev/null
  docker stop r12-preview >/dev/null 2>&1 && ok "r12-preview stopped"
  echo "  其余容器保留（数据卷不清空）；如需停容器: docker compose -f $R12/docker/docker-compose.infra.yml stop"
  ;;
status)
  echo "== 业务服务 =="; "$R12/bin/r12ctl.sh" status | sed 's/ pid=.*//'
  echo "== 端口探针 =="
  for x in "8088 网关" "18084 图谱" "18088 前端nginx" "15174 前端dev" "18095 Office预览" \
           "12340 解析" "19527 全文" "19526 向量" "19529 图索引" "19995 检索" "19996 LLM" \
           "18090 embedding" "18091 rerank" "18092 llm" "18093 vlm" \
           "19200 es" "19630 milvus" "19669 nebula-graphd" "18848 nacos"; do
    set -- $x
    if have_port "$1"; then ok "$1 $2"; else warn "$1 $2"; fi
  done
  ;;
verify)
  for u in "http://127.0.0.1:18088/" "http://127.0.0.1:15174/" "http://127.0.0.1:8088/auth/user/kaptcha" \
           "http://127.0.0.1:18095/healthz" "http://127.0.0.1:19200/_cluster/health"; do
    printf '  %s -> ' "$u"; curl -sS -o /dev/null -m 5 -w '%{http_code}\n' "$u" || echo "conn-fail"
  done
  printf '  %s -> ' "minio anonymous GET (expect 403)"
  curl -sS -o /dev/null -m 5 -w '%{http_code}\n' \
    "http://127.0.0.1:19000/r12-rag/kb_9/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx" || echo "conn-fail"
  "$R12/bin/r12ctl.sh" status | sed 's/ pid=.*//'
  ;;
*) echo "用法: $0 {up|down|status|verify}"; exit 2;;
esac
