#!/usr/bin/env bash
# R14：启动/停机计时（冷启动证据采集）
#
# 用途：**干净安装时**证明"从零能起 5 个 Java 服务 + 算法/模型"，并给出每个服务
#       "启动耗时 + 首次业务探针就绪时间"；同时测"停机成本"（发布窗口必须按这个算）。
#
# 为什么需要它（R14 真实教训）：
#   1) B 之前按"Started 到端口可用"算出 6–8s，漏掉了 `Stopping` 到 `Stopped` 的 30s
#      ——实际每次 restart 不可用约 35s，是"发布期间随机 5xx"的来源之一。
#   2) 只有把"启动耗时/停机耗时/首探针就绪"写成可复算的数字，才能给客户侧运维定发布窗口。
#
# 用法：
#   boot-timing.sh                    # 只对**未运行**的服务计时（幂等，不打断在跑的服务）
#   boot-timing.sh --restart [svc…]   # 对指定服务 stop→start 全量计时（会中断，需窗口与通知）
#   boot-timing.sh --stop-only [svc…] # 只测停机耗时（发布窗口估算用）
#
# 输出：表格 + TSV（platform/r12/logs/boot-timing-<ts>.tsv）
# 判定：端口可连 + 业务探针（每个服务各自的判据）双条件才算"就绪"
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
R12CTL="$R12/bin/r12ctl.sh"
TS="$(date +%Y%m%dT%H%M%SZ)"
OUT="$R12/logs/boot-timing-$TS.tsv"
MODE=start; [[ "${1:-}" == "--restart" ]] && { MODE=restart; shift; }
[[ "${1:-}" == "--stop-only" ]] && { MODE=stop; shift; }

ALL=(rag-auth-service rag-index-service rag-qa-service sensitive-words-service rag-gateway rag-graph-service)
TARGETS=("${@:-}"); [[ -z "${TARGETS[0]:-}" ]] && TARGETS=("${ALL[@]}")

port_of() { case "$1" in
  rag-auth-service) echo 18081;; rag-index-service) echo 18082;; rag-qa-service) echo 18083;;
  sensitive-words-service) echo 18085;; rag-gateway) echo 8088;; rag-graph-service) echo 18084;; esac; }

# 业务探针：返回 HTTP 码；<500 视为"服务能应答"（401/403/404 都算活着，5xx/超时不算）
probe_of() {
  local svc="$1" p code
  p="$(port_of "$svc")"
  case "$svc" in
    rag-index-service) code="$(curl -sS -o /dev/null -m 5 -w '%{http_code}' "http://127.0.0.1:$p/index/knowledgeBase/list" 2>/dev/null)" ;;
    rag-qa-service)    code="$(curl -sS -o /dev/null -m 5 -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{}' "http://127.0.0.1:$p/qa/ai/question" 2>/dev/null)" ;;
    rag-gateway)       code="$(curl -sS -o /dev/null -m 5 -w '%{http_code}' "http://127.0.0.1:$p/auth/user/kaptcha" 2>/dev/null)" ;;
    rag-graph-service) code="$(curl -sS -o /dev/null -m 5 -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{}' "http://127.0.0.1:$p/query_graph_data" 2>/dev/null)" ;;
    *)                 code="$(curl -sS -o /dev/null -m 5 -w '%{http_code}' "http://127.0.0.1:$p/" 2>/dev/null)" ;;
  esac
  echo "${code:-000}"
}

listening() { ss -lntH "sport = :$1" 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1\$"; }
now_ms() { date +%s%3N; }

printf 'service\tmode\tstart\tready\tduration_ms\tprobe_code\tpid\tjar_mtime\n' > "$OUT"
printf '%-24s %-9s %-12s %-12s %-10s %-6s %s\n' SERVICE MODE START READY DURATION PROBE PID

fails=0; measured=0
for svc in "${TARGETS[@]}"; do
  p="$(port_of "$svc")"
  running=0; listening "$p" && running=1

  if [[ "$MODE" == "start" && "$running" == "1" ]]; then
    printf '%-24s %-9s %-12s %-12s %-10s %-6s %s\n' "$svc" skip "-" "-" "-" "-" "已在运行（默认模式不打断；需冷启动请用 --restart 或在干净机上跑）"
    continue
  fi

  stop_ms=0
  if [[ "$MODE" != "start" ]]; then
    t0=$(now_ms)
    bash "$R12CTL" stop "$svc" >/dev/null 2>&1
    for _ in $(seq 1 240); do listening "$p" || break; sleep 0.5; done
    stop_ms=$(( $(now_ms) - t0 ))
  fi

  if [[ "$MODE" == "stop" ]]; then
    measured=$((measured+1))
    printf '%-24s %-9s %-12s %-12s %-10s %-6s %s\n' "$svc" stop "$(date -d @$(( $(date +%s) - stop_ms/1000 )) +%H:%M:%S)" "$(date +%H:%M:%S)" "${stop_ms}ms(stop)" - -
    printf '%s\tstop\t-\t%s\t%s\t-\t-\t-\n' "$svc" "$(date +%H:%M:%S)" "$stop_ms" >> "$OUT"
    continue
  fi

  t0=$(now_ms); st="$(date +%H:%M:%S)"
  bash "$R12CTL" start "$svc" >/dev/null 2>&1
  code=000
  for _ in $(seq 1 360); do          # 最多 180s（index 冷启动实测可达 120s）
    if listening "$p"; then
      code="$(probe_of "$svc")"
      [[ "$code" != "000" ]] && (( code < 500 )) && break
    fi
    sleep 0.5
  done
  dur=$(( $(now_ms) - t0 ))
  pid="$(cat "$R12/run/$svc.pid" 2>/dev/null || echo -)"
  jar="$(stat -c %y "$R12/../../services/rag-java/rag-parent/$svc/target/$svc-0.0.1-SNAPSHOT.jar" 2>/dev/null | cut -c1-19 || echo -)"
  measured=$((measured+1))
  if [[ "$code" == "000" ]] || (( code >= 500 )); then fails=$((fails+1)); fi
  printf '%-24s %-9s %-12s %-12s %-10s %-6s %s\n' "$svc" "${MODE}$([[ $stop_ms -gt 0 ]] && echo "+stop")" "$st" "$(date +%H:%M:%S)" "${dur}ms" "$code" "$pid"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$svc" "$MODE" "$st" "$(date +%H:%M:%S)" "$dur" "$code" "$pid" "$jar" >> "$OUT"
done

echo
echo "  TSV: $OUT"
if [[ "$measured" -eq 0 ]]; then
  echo "  [!!] 本次未测量任何服务（默认模式只对"未运行"的服务计时）"
  echo "       干净安装/冷启动请用: boot-timing.sh --restart <服务…>；停机成本: boot-timing.sh --stop-only <服务…>"
  exit 0
fi
[[ "$fails" -gt 0 ]] && { echo "  [FAIL] $fails/$measured 个服务在 180s 内未达到"端口+业务探针"就绪"; exit 1; }
echo "  [ok] 已测量 $measured 个服务，全部就绪（判据：端口可连 + 业务探针 <500）"
