#!/usr/bin/env bash
# R14-F07 启动依赖就绪闸门（systemd ExecStartPre 用）
#
# 存在理由：R14 事故——Nacos 抖动时算法服务在冷启动阶段直接起不来，
# 而 unit 是 Type=oneshot + Restart=no，失败后没有任何重试，整单元 failed 无人拉起。
# 这里把"依赖先就绪再拉服务"变成启动前的显式、可观测、可失败的步骤。
#
# 用法:
#   r12-wait-ready.sh nacos  [timeout=300]        等 Nacos /nacos/v1/console/health/readiness 返回 200
#   r12-wait-ready.sh tcp  <port> [port...] --  [timeout=120]
#                                                 等一个或多个 TCP 端口可连
#   r12-wait-ready.sh docker [timeout=120]        等 docker daemon 可用
#
# 退出码：0=就绪；1=超时（调用方应视为启动失败，由 unit 的 Restart/看门狗处理）
set -uo pipefail

NACOS_URL="${NACOS_READY_URL:-http://127.0.0.1:18848/nacos/v1/console/health/readiness}"

log() { printf '[%s] [wait-ready] %s\n' "$(date -Is)" "$*" >&2; }

wait_nacos() {
  local timeout="${1:-300}" i=0 code
  while (( i < timeout )); do
    code="$(curl -sS -o /dev/null -m 3 -w '%{http_code}' "$NACOS_URL" 2>/dev/null || echo 000)"
    if [[ "$code" == "200" ]]; then
      log "nacos readiness=200（用时 ${i}s）"
      return 0
    fi
    (( i % 10 == 0 )) && log "nacos 未就绪 (http=$code)，已等 ${i}s/${timeout}s"
    sleep 1; ((i++))
  done
  log "FAIL nacos ${timeout}s 内未就绪（最后 http=$code）url=$NACOS_URL"
  return 1
}

wait_docker() {
  local timeout="${1:-120}" i=0
  while (( i < timeout )); do
    if docker info >/dev/null 2>&1; then log "docker daemon 就绪（用时 ${i}s）"; return 0; fi
    sleep 1; ((i++))
  done
  log "FAIL docker daemon ${timeout}s 内不可用"
  return 1
}

port_open() {
  # 用 /dev/tcp 判可连（比 grep ss 更接近真实调用方视角）
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

wait_tcp() {
  local timeout="$1"; shift
  local ports=("$@") i=0 missing
  while (( i < timeout )); do
    missing=()
    for p in "${ports[@]}"; do port_open "$p" || missing+=("$p"); done
    if (( ${#missing[@]} == 0 )); then log "tcp ${ports[*]} 全部可连（用时 ${i}s）"; return 0; fi
    sleep 1; ((i++))
  done
  log "FAIL tcp ${missing[*]} ${timeout}s 内未就绪"
  return 1
}

kind="${1:-}"; shift || true
case "$kind" in
  nacos)  wait_nacos "${1:-300}" ;;
  docker) wait_docker "${1:-120}" ;;
  tcp)
    timeout=""
    ports=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --) shift; timeout="${1:-120}"; shift || true ;;
        *)  ports+=("$1"); shift ;;
      esac
    done
    [[ -n "$timeout" ]] || timeout=120
    (( ${#ports[@]} > 0 )) || { log "tcp 需要至少一个端口"; exit 2; }
    wait_tcp "$timeout" "${ports[@]}" ;;
  *) echo "用法: $0 {nacos|docker|tcp <port...> -- [timeout]} [timeout]"; exit 2 ;;
esac
