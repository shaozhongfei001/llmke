#!/usr/bin/env bash
# R14 全栈一键启动/停止/状态/验收（按依赖顺序，幂等）
# 顺序：基础设施(容器) + 就绪等待 -> ES 副本治理 -> 模型 -> 算法 -> 文档解析 -> 图谱 -> 业务 -> Office 预览 -> 前端(生产 nginx)
# 用法: up.sh {up|down|status|verify} [--with-dev-fe]
#   --with-dev-fe  额外起前端 dev server(15174)。**默认不起**：R13 把 npm run dev 当默认，
#                  等于生产入口跑在开发服务器上（F07 明确要求移除）。
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$R12/../.." && pwd)"
if [ -f "$R12/.env" ]; then set -a; . "$R12/.env"; set +a; fi
ACTION="${1:-status}"
WITH_DEV_FE=0
[[ "${2:-}" == "--with-dev-fe" || "${1:-}" == "--with-dev-fe" ]] && WITH_DEV_FE=1
[[ "${1:-}" == "--with-dev-fe" ]] && ACTION="${2:-status}"

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
fail() { printf '  [FAIL] %s\n' "$1"; }

wait_port() {  # wait_port <port> <seconds> <host=127.0.0.1>
  local p=$1 t=${2:-60} h=${3:-127.0.0.1} i=0
  while (( i < t )); do
    (exec 3<>"/dev/tcp/$h/$p") 2>/dev/null && return 0
    sleep 1; ((i++))
  done
  return 1
}

have_port() { ss -lntH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1\$"; }

conf_placeholders() { grep -rho '\${R12_[A-Z_]*}' "$R12/conf" 2>/dev/null | sed 's/[${}]//g' | sort -u; }
env_has_key() { grep -qE "^$1=" "$R12/.env" 2>/dev/null; }
fe_chunk_of_file() { grep -oE 'index-[A-Za-z0-9_-]+\.js' "$1" 2>/dev/null | head -1; }
fe_chunk_of_http() { curl -sS -m 5 "$1" 2>/dev/null | grep -oE 'index-[A-Za-z0-9_-]+\.js' | head -1; }

http_code() { local c; c="$(curl -sS -o /dev/null -m "${2:-5}" -w '%{http_code}' "$1" 2>/dev/null)" || true; echo "${c:-000}"; }

case "$ACTION" in
up)
  echo "== 1. 基础设施（容器，命名卷保留数据；含 Nebula 3.8）=="
  ( cd "$R12/docker" && docker compose -f docker-compose.infra.yml --env-file "$R12/.env" up -d >/dev/null 2>&1 )
  infra_rc=0
  for p in 13306 16379 19000 19200 19630 18848 19669; do
    wait_port "$p" 120 && ok "port $p" || { fail "port $p 未就绪"; infra_rc=1; }
  done
  echo "== 1.1 就绪判据（不是「起完就算」）=="
  bash "$R12/bin/r12-wait-ready.sh" nacos 300 && ok "nacos readiness" || { fail "nacos readiness"; infra_rc=1; }
  docker exec r12-mysql mysqladmin ping -uroot -p"${R12_MYSQL_ROOT_PASSWORD:-}" 2>/dev/null | grep -q alive \
    && ok "mysql ping" || { fail "mysql ping"; infra_rc=1; }
  es_st="$(curl -sS -m 5 "http://127.0.0.1:19200/_cluster/health?filter_path=status" 2>/dev/null)"
  [[ -n "$es_st" ]] && ok "ES 可应答（$es_st）" || { fail "ES 不可应答"; infra_rc=1; }

  echo "== 1.2 ES 单节点副本治理（单节点副本无法分配 -> 常黄）=="
  bash "$R12/bin/es-single-node.sh" 2>&1 | sed 's/^/  /' || warn "ES 副本治理未通过（不阻断启动，但 verify 会判失败）"

  echo "== 2. 模型服务（18090 embedding / 18091 rerank / 18092 llm / 18093 vlm）=="
  bash "$R12/models/start-all.sh" up 2>&1 | tail -3 || { fail "模型服务启动失败"; infra_rc=1; }

  echo "== 3. 算法服务（19526 向量 / 19527 全文 / 19995 检索 / 19996 LLM）=="
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

  echo "== 8. 前端（生产：nginx 容器监听 18088）=="
  if [ "$(http_code http://127.0.0.1:18088/)" = "200" ]; then
    ok "18088 已在服务"
  elif docker ps -a --format '{{.Names}}' | grep -q '^r12-fe$'; then
    docker start r12-fe >/dev/null 2>&1 || docker restart r12-fe >/dev/null 2>&1
    sleep 5; docker exec r12-fe nginx -s reload >/dev/null 2>&1
    ok "r12-fe restarted"
  else
    warn "前端容器 r12-fe 不存在（见 frontend/plateform/nginx/r12-18088.conf；安装文档第 10 步）"
  fi
  # D 报的 bind mount inode 陷阱：宿主机替换 dist 目录后，容器仍钉在旧 inode 上，
  # 出现"构建了但页面没变"。这里比对入口 chunk 名，不一致就 restart（3s）。
  hc="$(fe_chunk_of_file "$REPO/frontend/plateform/dist/index.html")"
  sc="$(fe_chunk_of_http http://127.0.0.1:18088/index.html)"
  if [ -n "$hc" ] && [ "$hc" != "$sc" ]; then
    warn "前端入口 chunk 不一致（宿主=$hc 服务=$sc）→ bind mount 旧 inode，执行 docker restart r12-fe"
    docker restart r12-fe >/dev/null 2>&1 && sleep 3
    sc="$(fe_chunk_of_http http://127.0.0.1:18088/index.html)"
    [ "$hc" = "$sc" ] && ok "重启后一致：$sc" || warn "重启后仍不一致（宿主=$hc 服务=$sc）"
  else
    ok "前端入口 chunk 一致（${hc:-未取到}）"
  fi

  if [ "$WITH_DEV_FE" = "1" ]; then
    warn "起前端 dev server 15174（仅开发用，不是生产入口）"
    ( cd "$REPO/frontend/plateform" && nohup setsid npm run dev > "$R12/logs/fe-dev.log" 2>&1 & ) && sleep 12 && ok "dev 15174 启动"
  else
    ok "未启动 npm dev（生产默认走 18088 nginx；需要时加 --with-dev-fe）"
  fi
  [ "$infra_rc" -eq 0 ] || { echo; fail "基础设施/模型存在失败项，见上"; exit 1; }
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
  # R14-F07：分为 must / warn 两级，**must 任一项失败即退出非零**。
  # R13 的 verify 只打印状态、永远退出 0，安装流程无法据此中断（F07 原文）。
  must_fail=0; warn_n=0
  check_must() {  # check_must <名称> <期望> <实际>
    local n="$1" exp="$2" got="$3"
    if [ "$got" = "$exp" ]; then ok "$n = $got"; else fail "$n = ${got:-无响应}（期望 $exp）"; must_fail=$((must_fail+1)); fi
  }
  check_warn() {
    local n="$1" exp="$2" got="$3"
    if [ "$got" = "$exp" ]; then ok "$n = $got"; else warn "$n = ${got:-无响应}（期望 $exp，不阻断）"; warn_n=$((warn_n+1)); fi
  }

  echo "== [must] 用户入口 =="
  check_must "前端 18088 /" 200 "$(http_code http://127.0.0.1:18088/)"
  check_must "网关 8088 /auth/user/kaptcha" 200 "$(http_code http://127.0.0.1:8088/auth/user/kaptcha)"
  check_must "Office 预览 18095 /healthz" 200 "$(http_code http://127.0.0.1:18095/healthz)"

  echo "== [must] 配置占位符可解析（R14 事故：缺 .env 键导致 5 个 Java 服务启动即失败）=="
  miss_ph=""
  for v in $(conf_placeholders); do env_has_key "$v" || miss_ph="$miss_ph $v"; done
  if [ -n "$miss_ph" ]; then
    fail "conf 引用的占位符在 .env 里不存在:$miss_ph（Java 会报 Could not resolve placeholder）"
    must_fail=$((must_fail+1))
  else
    ok "conf 占位符全部能在 .env 找到（$(conf_placeholders | wc -l) 个）"
  fi
  if [ -f "$R12/.env" ]; then ok ".env 存在"; else fail ".env 缺失（compose 与 unit 都依赖它）"; must_fail=$((must_fail+1)); fi

  echo "== [must] 前端产物与容器一致（bind mount 旧 inode 陷阱）=="
  hc="$(fe_chunk_of_file "$REPO/frontend/plateform/dist/index.html")"
  sc="$(fe_chunk_of_http http://127.0.0.1:18088/index.html)"
  if [ -n "$hc" ] && [ "$hc" = "$sc" ]; then
    ok "入口 chunk 一致：$hc"
  else
    fail "入口 chunk 不一致（宿主=${hc:-?} 服务=${sc:-?}）→ 容器仍服务旧 inode，执行 docker restart r12-fe"
    must_fail=$((must_fail+1))
  fi

  echo "== [must] 数据面真实可读写（不是只看端口）=="
  es_code="$(http_code 'http://127.0.0.1:19200/kb_9/_count' 8)"
  check_must "ES kb_9/_count 可达" 200 "$es_code"
  es_health="$(curl -sS -m 5 'http://127.0.0.1:19200/_cluster/health?filter_path=status' 2>/dev/null | tr -d '{}"' )"
  if echo "$es_health" | grep -q 'green'; then
    ok "ES 集群 green"
  else
    fail "ES 集群非 green（$es_health）"; must_fail=$((must_fail+1))
    # 诊断：单节点上"索引副本数>0"必然产生 unassigned -> yellow。点名到索引，别只报 yellow。
    rep_bad="$(curl -sS -m 5 'http://127.0.0.1:19200/_cat/indices?h=index,rep' 2>/dev/null | awk '$2+0>0{printf "%s(rep=%s) ", $1, $2}')"
    if [ -n "$rep_bad" ]; then
      echo "       诊断：以下索引 number_of_replicas>0，单节点无法分配副本：$rep_bad"
      echo "       处置：bash $R12/bin/es-single-node.sh（既有索引置 0 + 模板默认 0）；若是新前缀，把 pattern 加进该脚本"
    else
      echo "       诊断：无副本数>0 的索引，yellow 可能来自其它原因（见 _cluster/allocation/explain）"
    fi
  fi
  check_must "MinIO 匿名 GET（期望 403）" 403 \
    "$(http_code 'http://127.0.0.1:19000/r12-rag/kb_9/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx' 8)"

  echo "== [must] 依赖层连通（不借业务端点当健康检查）=="
  if docker exec r12-mysql mysqladmin ping -uroot -p"${R12_MYSQL_ROOT_PASSWORD:-}" 2>/dev/null | grep -q alive; then
    ok "MySQL(13306) ping alive"
  else fail "MySQL(13306) ping 失败"; must_fail=$((must_fail+1)); fi
  redis_pong="$(docker exec r12-redis redis-cli -a "${R12_REDIS_PASSWORD:-}" --no-auth-warning PING 2>/dev/null | tr -d '\r')"
  if [ "$redis_pong" = "PONG" ]; then ok "Redis(16379) PING=PONG"; else fail "Redis PING=${redis_pong:-无响应}"; must_fail=$((must_fail+1)); fi
  if [ "$(http_code http://127.0.0.1:18848/nacos/v1/console/health/readiness)" = "200" ]; then
    ok "Nacos readiness=200"
  else fail "Nacos readiness 非 200"; must_fail=$((must_fail+1)); fi
  nb="$(docker inspect -f '{{.State.Health.Status}}' r12-nebula-graphd 2>/dev/null)"
  if [ "$nb" = "healthy" ]; then ok "Nebula graphd healthy"; else fail "Nebula graphd=${nb:-未知}"; must_fail=$((must_fail+1)); fi

  echo "== [must] 内部服务在监听（回环）=="
  for p in 12340 18081 18082 18083 18084 18085 19526 19527 19529 19995 19996; do
    if have_port "$p"; then ok "port $p"; else fail "port $p 无监听"; must_fail=$((must_fail+1)); fi
  done
  echo "== [must] 模型真实可用 =="
  check_must "embedding 18090 /healthz" 200 "$(http_code http://127.0.0.1:18090/healthz 8)"
  check_must "rerank 18091 /healthz" 200 "$(http_code http://127.0.0.1:18091/healthz 8)"
  check_must "llm 18092 /health" 200 "$(http_code http://127.0.0.1:18092/health 8)"
  check_warn "vlm 18093 /health" 200 "$(http_code http://127.0.0.1:18093/health 8)"

  echo "== [warn] 运行代码是否与构建一致（[STALE_JAR]）=="
  stale="$(bash "$R12/bin/r12ctl.sh" status 2>/dev/null | grep -c 'STALE_JAR')"
  if [ "$stale" -eq 0 ]; then
    ok "无 STALE_JAR（运行中的 jar 不旧于进程启动）"
  else
    warn "$stale 个服务的 jar 比进程新（运行的是旧字节码，需 restart 才生效）。"
    warn "  口径：无人在改构建产物时 STALE 应为 0；出现即表示「有人 stage 了新 jar 但还没重启」，不是误报。"
    bash "$R12/bin/r12ctl.sh" status 2>/dev/null | grep 'STALE_JAR' | sed 's/^/      /'
    warn_n=$((warn_n+1))
  fi

  echo "== [warn] 开发入口 =="
  check_warn "前端 dev 15174" 200 "$(http_code http://127.0.0.1:15174/ 3)"

  echo
  if [ "$must_fail" -gt 0 ]; then
    fail "验收失败：must 项 $must_fail 个未通过（warn $warn_n 个）"
    exit 1
  fi
  ok "验收通过：must 全部通过（warn $warn_n 个）"
  ;;
*) echo "用法: $0 {up|down|status|verify} [--with-dev-fe]"; exit 2;;
esac
