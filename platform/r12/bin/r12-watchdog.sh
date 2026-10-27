#!/usr/bin/env bash
# R14-F07 服务自愈看门狗（一次巡检；由 r12-watchdog.timer 每 45s 触发）
#
# 背景（R14 真事故）：r12-alg / r12-models 是 Type=oneshot + RemainAfterExit=yes + Restart=no，
# 启动器退出后子进程完全没有守护；Nacos 抖动导致 19995/19996/19526/19527 全灭后，
# unit 仍显示 active (exited)，systemd 不会再拉起，实际死了 7 小时无人发现。
#
# 本脚本做的是"外部可观测性 + 有界自愈"：
#   1) 用真实监听口（+ 模型服务的 HTTP 探针）判定每个服务组是否还活着——不看 unit 状态
#   2) 连续 FAIL_CONFIRM 次（默认 2 次 × 45s = 90s 持续故障）才动手，避免把滚动重启/正常启停当故障
#   3) 修复动作按组最小化：算法组只重启缺失的那一个服务（algctl restart <svc>），不整组重拉
#   4) 冷却 + 指数退避（300s 起，上限 1800s），失败也不会变成重启风暴
#   5) 全过程写 platform/r12/logs/watchdog.log，状态落 platform/r12/run/watchdog/<group>.state
#
# 用法:
#   r12-watchdog.sh              # 单次巡检（timer 调用）
#   r12-watchdog.sh --status     # 只打印各组状态，不动作
#   r12-watchdog.sh --reset      # 清空所有组的失败计数/退避状态
#   r12-watchdog.sh --doctor     # 打印判定表（端口/HTTP/unit 状态）
#
# 环境变量: FAIL_CONFIRM(2) COOLDOWN(300) MAX_BACKOFF(1800)
set -uo pipefail

R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$R12/logs/watchdog.log"
STATE_DIR="$R12/run/watchdog"
LOCK="$R12/run/.watchdog.lock.d"
MAINT="$R12/run/.maintenance"
ALGCTL="$R12/run/algctl.sh"
R12CTL="$R12/bin/r12ctl.sh"

FAIL_CONFIRM="${FAIL_CONFIRM:-3}"
# 冷却/退避基数。R14 事故（11:00–11:16）教训：整层挂掉时，单个服务上一轮的退避
# 会把整层恢复拖到 600s 之后（实测 [java-*] 连续 4 轮"冷却中，剩余 130s/85s/40s"）。
COOLDOWN="${COOLDOWN:-300}"
MAX_BACKOFF="${MAX_BACKOFF:-900}"
# 启动宽限期：命中则本轮不判死（Java 冷启动实测 60–120s，模型 20s，index 最高 ~120s）
STARTUP_GRACE="${STARTUP_GRACE:-180}"
# 整层故障旁路的"最小动作间隔"（仍不允许对同一服务 30s 内连续重启）
BYPASS_MIN_INTERVAL="${BYPASS_MIN_INTERVAL:-120}"
# 同时不健康的组数达到该阈值即视为"整层故障"，跳过冷却立刻修（每轮仍只尝试一次）
TIER_BYPASS="${TIER_BYPASS:-3}"
STUCK_SECS="${STUCK_SECS:-150}"   # 单元在启停过渡态滞留超过该秒数（且端口已失）即判卡死强杀

mkdir -p "$STATE_DIR" "$(dirname "$LOG")"

log()  { local l; l="[$(date -Is)] $*"; printf '%s\n' "$l" >> "$LOG"; printf '%s\n' "$l"; }
info() { local l; l="[$(date -Is)] $*"; printf '%s\n' "$l" >> "$LOG"; printf '%s\n' "$l"; }

# ---------------------------------------------------------------------------
# 服务组定义
#   id | 端口(csv) | unit | heal 模式 | heal 目标 | HTTP 探针(可选, csv)
#   heal 模式: unit-restart=systemctl --user restart <unit>
#              alg-granular=按缺失端口对应的算法服务逐个 algctl restart
#              r12ctl      =裸进程（无 unit），用 r12ctl start <svc>
# ---------------------------------------------------------------------------
TARGETS=(
  "alg|19526,19527,19995,19996|r12-alg|alg-granular||"
  "models|18090,18091,18092,18093|r12-models|unit-restart||http://127.0.0.1:18090/healthz,http://127.0.0.1:18091/healthz,http://127.0.0.1:18092/health,http://127.0.0.1:18093/health"
  "docparse|12340|r12-docparse|unit-restart||"
  "graphsvc|19529|r12-graphsvc|unit-restart||"
  "java-auth|18081|r12-java@rag-auth-service.service|unit-restart||"
  "java-index|18082|r12-java@rag-index-service.service|unit-restart|||/index/knowledgeBase/list;200"
  "java-qa|18083|r12-java@rag-qa-service.service|unit-restart|||/qa/ai/question;499"
  "java-sensitive|18085|r12-java@sensitive-words-service.service|unit-restart||"
  "gateway|8088|r12-java@rag-gateway.service|unit-restart|||/auth/user/kaptcha;200"
  "java-graph|18084|-|r12ctl|rag-graph-service|"
)

# 算法组：端口 -> algctl 服务名
alg_svc_of_port() {
  case "$1" in
    19526) echo index_vector_service ;;
    19527) echo index_fulltext_service ;;
    19995) echo alg_retrieval_service ;;
    19996) echo alg_llm_inference_service ;;
    *) echo "" ;;
  esac
}

# 端口是否 LISTEN（只认 TCP LISTEN，且精确匹配端口，避免 1952 命中 19526）
port_listen() {
  ss -lntH 2>/dev/null | awk -v want=":$1" '{a=$4} a ~ want"$" {found=1} END{exit(found?0:1)}'
}

port_reachable() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

# 监听口存在但监听进程被挂起(T)/僵尸(Z) 时，TCP 仍会 accept（内核 backlog），
# 只测端口连通会把"进程假死"判成健康。这里直接看 /proc/<pid>/stat 的 state 字段。
port_listener_alive() {
  local port="$1" pids pid st
  pids="$(ss -ltnpH "sport = :$port" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u)"
  [[ -z "$pids" ]] && return 1
  for pid in $pids; do
    st="$(awk '{print $3}' "/proc/$pid/stat" 2>/dev/null)"
    case "$st" in
      T|t|Z|X) return 1 ;;   # 停止/跟踪停止/僵尸/已死
    esac
  done
  return 0
}

# 返回该组"不健康"的端口清单（空=健康）
unhealthy_ports() {
  local ports="$1" http="$2" probe="${3:-}" p out=()
  local IFS=','
  for p in $ports; do
    if ! port_listen "$p" || ! port_reachable "$p" || ! port_listener_alive "$p"; then out+=("$p"); fi
  done
  unset IFS
  # HTTP 探针：端口通但服务卡死（accept 后不回包）也要判不健康
  if [[ -n "$http" ]]; then
    local IFS=','
    for u in $http; do
      curl -fsS -m 5 -o /dev/null "$u" 2>/dev/null || out+=("http:${u##*:}" )
    done
    unset IFS
  fi
  # 业务端点探针（第7列）：路径;最大允许状态码。>=500 或连不上 = 不健康
  if [[ -n "${probe:-}" ]]; then
    local path="${probe%;*}" maxc="${probe#*;}" code
    code="$(curl -sS -o /dev/null -m 6 -w '%{http_code}' "http://127.0.0.1:${ports%%,*}$path" 2>/dev/null || echo 000)"
    if [[ "$code" == "000" ]] || (( code > maxc )); then out+=("http:${ports%%,*}$path=$code"); fi
  fi
  printf '%s\n' "${out[@]:-}" | sed '/^$/d' | paste -sd, -
}

port_pids() { ss -ltnpH "sport = :$1" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u | paste -sd, -; }

unit_state() { systemctl --user show -p ActiveState --value "$1" 2>/dev/null; }

ts_of() { date -d "$1" +%s 2>/dev/null; }   # 把 systemd 的时间字符串转 epoch

# 该组的"最近启动时刻"：unit 的 Active/Inactive 进入时刻、pidfile mtime、上次自愈动作，取最大
group_start_epoch() {  # $1=unit $2=mode $3=target $4=last_heal
  local unit="$1" mode="$2" target="$3" last_heal="$4" t best=0 x
  if [[ "$unit" != "-" ]] && command -v systemctl >/dev/null 2>&1; then
    for p in ActiveEnterTimestamp InactiveEnterTimestamp; do
      x="$(ts_of "$(systemctl --user show -p "$p" --value "$unit" 2>/dev/null)")"
      [[ -n "$x" ]] && (( x > best )) && best=$x
    done
  fi
  if [[ "$mode" == "r12ctl" && -f "$R12/run/${target}.pid" ]]; then
    x="$(stat -c %Y "$R12/run/${target}.pid" 2>/dev/null)"; [[ -n "$x" ]] && (( x > best )) && best=$x
  fi
  [[ "${last_heal:-0}" -gt "$best" ]] && best="$last_heal"
  echo "$best"
}
unit_enabled() { systemctl --user is-enabled "$1" >/dev/null 2>&1; }

# 是否"期望它活着"：unit 已 enable（开机自管）或当前非 inactive（有人手工拉起）
desired_up() {
  local unit="$1"
  [[ "$unit" == "-" ]] && return 0            # 裸进程组：只要没有显式停过就归我们管
  unit_enabled "$unit" && return 0
  [[ "$(unit_state "$unit")" != "inactive" ]] && return 0
  return 1
}

state_file() { echo "$STATE_DIR/$1.state"; }
state_get() { local f; f="$(state_file "$1")"; [[ -f "$f" ]] && sed -n "${2}p" "$f" || true; }

state_read() {  # -> "fails first_fail last_heal level stuck_since"
  local f; f="$(state_file "$1")"
  if [[ -f "$f" ]]; then cat "$f"; else echo "0 0 0 0 0"; fi
}
state_write() { printf '%s\n' "$2" > "$(state_file "$1")"; }
state_clear() { rm -f "$(state_file "$1")"; }

cooldown_left() {  # $1=last_heal $2=level -> 剩余冷却秒
  local last_heal="$1" level="$2" now; now="$(date +%s)"
  local cd="$COOLDOWN"
  local i; for ((i=0; i<level; i++)); do cd=$(( cd * 2 )); [[ $cd -ge $MAX_BACKOFF ]] && { cd=$MAX_BACKOFF; break; }; done
  local elapsed=$(( now - last_heal ))
  local left=$(( cd - elapsed ))
  (( left < 0 )) && left=0
  echo "$left"
}

heal() {  # $1=group $2=unit $3=mode $4=target $5=missing(csv)
  local group="$1" unit="$2" mode="$3" target="$4" missing="$5" rc=0
  case "$mode" in
    alg-granular)
      local p svc
      local IFS=','
      for p in $missing; do
        [[ "$p" == http:* ]] && continue
        svc="$(alg_svc_of_port "$p")"
        [[ -z "$svc" ]] && { log "[$group] 未知算法端口 $p，跳过"; continue; }
        log "[$group] 修复动作: $ALGCTL restart $svc（端口 $p 不在监听）"
        # 用独立 scope 执行，避免拉起的长驻进程落进看门狗自己的 cgroup（否则 stop 时会连带被杀）
        if command -v systemd-run >/dev/null 2>&1; then
          systemd-run --user --scope --collect --quiet bash "$ALGCTL" restart "$svc" >>"$LOG" 2>&1 || rc=1
        else
          bash "$ALGCTL" restart "$svc" >>"$LOG" 2>&1 || rc=1
        fi
      done
      unset IFS
      # 单个服务粒度修复失败 -> 退回整单元重启（仍在 systemd 管控内）
      if [[ $rc -ne 0 ]]; then
        log "[$group] 单服务修复失败，退回: systemctl --user restart $unit"
        systemctl --user restart "$unit" >>"$LOG" 2>&1 || rc=1
      fi
      ;;
    unit-restart)
      # --no-block：只排队重启任务，立即返回。否则 index 这类冷启动 120s 的服务会让
      # 一拍巡检阻塞 3 分钟，巡检节拍被打乱（11:13 就是这样把 timer 拖停的）。
      log "[$group] 修复动作: systemctl --user restart --no-block $unit"
      systemctl --user restart --no-block "$unit" >>"$LOG" 2>&1 || rc=1
      ;;
    r12ctl)
      log "[$group] 修复动作: $R12CTL start $target"
      if command -v systemd-run >/dev/null 2>&1; then
        systemd-run --user --scope --collect --quiet bash "$R12CTL" start "$target" >>"$LOG" 2>&1 || rc=1
      else
        bash "$R12CTL" start "$target" >>"$LOG" 2>&1 || rc=1
      fi
      ;;
    *) log "[$group] 未知 heal 模式 $mode"; rc=1 ;;
  esac
  return $rc
}

MODE="${1:-run}"
case "$MODE" in
  --reset)
    rm -f "$STATE_DIR"/*.state 2>/dev/null
    echo "已清空 watchdog 状态: $STATE_DIR"
    exit 0 ;;
esac

# 单实例互斥。
# 注意（R14 实测踩坑）：不能用 `exec 9>lock; flock -n 9`——自愈动作会 `nohup setsid python`
# 拉起服务进程，子进程继承 fd 9，锁就永远不会释放，之后每轮巡检都被自己"上一轮仍在进行"挡掉
# （实测 10:29:44 起连续 4 轮空转，已停止的 docparse 没能被拉起）。
# 改为原子 mkdir + pid 存活/超时判定，不向子进程传递任何 fd。
acquire_lock() {
  if mkdir "$LOCK" 2>/dev/null; then echo "$$" > "$LOCK/pid"; return 0; fi
  local pid; pid="$(cat "$LOCK/pid" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then return 1; fi
  # 持有者已死或 pid 文件缺失 -> 抢锁（40s 内不抢，可能正在写 pid 文件）
  if [[ -n "$(find "$LOCK" -maxdepth 0 -mmin +1 2>/dev/null)" ]]; then
    rm -rf "$LOCK" 2>/dev/null
    mkdir "$LOCK" 2>/dev/null && { echo "$$" > "$LOCK/pid"; return 0; }
  fi
  return 1
}
release_lock() { rm -rf "$LOCK" 2>/dev/null; }
trap 'release_lock' EXIT

if ! acquire_lock; then
  info "上一轮巡检仍在进行（holder pid=$(cat "$LOCK/pid" 2>/dev/null)），跳过本轮"
  exit 0
fi

if [[ "$MODE" == "--status" || "$MODE" == "--doctor" ]]; then
  printf '%-16s %-34s %-10s %-10s %-12s %s\n' GROUP PORTS UNIT UNIT_STATE FAILS LAST_HEAL
fi

changed=0; unhealthy=0
now="$(date +%s)"

for row in "${TARGETS[@]}"; do
  IFS='|' read -r group ports unit mode target http probe <<< "$row"
  IFS=$' \t' read -r fails first_fail last_heal level stuck_since <<< "$(state_read "$group")"
  fails="${fails:-0}"; first_fail="${first_fail:-0}"; last_heal="${last_heal:-0}"
  level="${level:-0}"; stuck_since="${stuck_since:-0}"

  if ! desired_up "$unit"; then
    info "[$group] skip：unit=$unit 未启用且未运行，视为人为停机"
    continue
  fi

  ustate="$([[ "$unit" == "-" ]] && echo naked || unit_state "$unit")"

  missing="$(unhealthy_ports "$ports" "$http" "$probe")"

  if [[ "$MODE" == "--status" || "$MODE" == "--doctor" ]]; then
    printf '%-16s %-34s %-10s %-10s %-12s %s\n' "$group" "$ports" "$unit" "$ustate" "$fails" "$([[ "$last_heal" == "0" ]] && echo - || date -d "@$last_heal" +%H:%M:%S)"
  fi

  if [[ -z "$missing" ]]; then
    if [[ "$fails" != "0" || "$stuck_since" != "0" ]]; then
      info "[$group] 恢复健康（此前连续失败 $fails 次，stuck_since=$stuck_since）"
      state_clear "$group"
    fi
    continue
  fi

  (( unhealthy++ ))

  # 启动宽限期：刚启动/刚被自愈的服务一律先不判死（TL 硬约束 ①）
  gstart="$(group_start_epoch "$unit" "$mode" "$target" "$last_heal")"
  gage=$(( now - ${gstart:-0} )); (( gage < 0 )) && gage=0   # systemd 时间戳可能略超前，别打出"启动于 -2s 前"
  if [[ "${gstart:-0}" -gt 0 ]] && (( gage < STARTUP_GRACE )); then
    info "[$group] 启动宽限期内（启动于 ${gage}s 前，宽限 ${STARTUP_GRACE}s，缺 $missing），本轮不判死"
    continue
  fi

  # 单元处于启停过渡态：默认不介入（避免和滚动重启抢跑），但要防"卡死"。
  # R14 实测：uvicorn 派生 worker 不响应 SIGTERM，unit 会长期停在 deactivating(final-sigterm)，
  # 此时端口已经不监听＝服务实际不可用，没有任何东西会来拉起它。所以超过 STUCK_SECS 就强制处理。
  case "$ustate" in
    activating|deactivating|reloading|refreshing)
      if [[ "$stuck_since" == "0" ]]; then
        state_write "$group" "$fails $first_fail $last_heal $level $now"
        info "[$group] unit 进入过渡态 $ustate（缺 $missing），开始计时"
        continue
      fi
      stuck_for=$(( now - stuck_since ))
      if (( stuck_for < STUCK_SECS )); then
        info "[$group] skip：unit 卡在 $ustate 已 ${stuck_for}s（阈值 ${STUCK_SECS}s），缺 $missing"
        continue
      fi
      if [[ "$MODE" == "--doctor" ]]; then
        log "[$group] --doctor：unit 卡在 $ustate ${stuck_for}s，本应 KillMode 强杀后重启"
        continue
      fi
      log "[$group] unit 卡在 $ustate 已 ${stuck_for}s（端口已失），强制 systemctl --user kill -s KILL 后 restart"
      systemctl --user kill -s KILL "$unit" >>"$LOG" 2>&1
      sleep 2
      systemctl --user restart "$unit" >>"$LOG" 2>&1
      changed=$(( changed + 1 ))
      state_write "$group" "0 0 $now $level 0"
      continue ;;
  esac
  # 状态正常：清掉过渡态计时
  [[ "$stuck_since" != "0" ]] && stuck_since=0
  if [[ -f "$MAINT" ]]; then
    info "[$group] skip：存在维护锁 $MAINT（缺 $missing）"
    continue
  fi

  # 计数封顶在 FAIL_CONFIRM：超过分母的 FAIL(3/2) 会让人误以为状态机坏了（C 已报）
  (( fails < FAIL_CONFIRM )) && fails=$(( fails + 1 ))
  [[ "$first_fail" == "0" ]] && first_fail="$now"
  state_write "$group" "$fails $first_fail $last_heal $level $stuck_since"
  info "[$group] FAIL($fails/$FAIL_CONFIRM) 缺失=$missing ustate=$ustate listener_pids=[${before_pids:-无}]"

  if (( fails < FAIL_CONFIRM )); then
    continue    # 防抖：首次发现只记账，下一轮仍坏才动手
  fi

  left=0
  (( level > 0 )) && left="$(cooldown_left "$last_heal" "$level")"
  if (( left > 0 )) && (( unhealthy >= TIER_BYPASS )); then
    if [[ "${last_heal:-0}" -gt 0 ]] && (( now - last_heal < BYPASS_MIN_INTERVAL )); then
      info "[$group] 整层故障但距上次动作 $(( now - last_heal ))s < ${BYPASS_MIN_INTERVAL}s，仍等待"
    else
      info "[$group] 整层故障（不健康组=$unhealthy ≥ $TIER_BYPASS），跳过冷却直接修复"
      left=0
    fi
  fi
  if (( left > 0 )); then
    info "[$group] 冷却中，剩余 ${left}s 不重复修复（退避级别 $level）"
    continue
  fi

  if [[ "$MODE" == "--doctor" ]]; then
    log "[$group] --doctor：本应执行 heal（$mode），但只诊断不改动"
    continue
  fi

  before_pids=""
  for p0 in $(printf '%s' "$missing" | tr ',' ' '); do
    [[ "$p0" == http:* ]] && continue
    before_pids="$before_pids $p0:$(port_pids "$p0")"
  done
  log "[$group] 触发自愈：缺失=$missing 已持续 $(( now - first_fail ))s unit=$unit 动作=$mode 修复前 listener_pids=[${before_pids# }]"
  if heal "$group" "$unit" "$mode" "$target" "$missing"; then
    sleep 4
    still="$(unhealthy_ports "$ports" "$http" "$probe")"
    if [[ -z "$still" ]]; then
      after_pids=""
      for p1 in $(printf '%s' "$ports" | tr ',' ' '); do
        after_pids="$after_pids $p1:$(port_pids "$p1")"
      done
      log "[$group] 自愈成功 用时=$(( $(date +%s) - now ))s 修复后 listener_pids=[${after_pids# }]（复位失败计数/冷却/退避）"
      # 注意：必须完全复位。R14 实测：若成功时保留 last_heal，紧随其后的"新故障"会被
      # COOLDOWN 挡 300s，等同让服务白死 5 分钟（10:34:21 成功 -> 10:34:29 新故障被冷却挡住）。
      state_write "$group" "0 0 0 0 0"
      changed=$(( changed + 1 ))
    else
      if [[ "$mode" == "unit-restart" ]]; then
        log "[$group] 已排队重启（--no-block），端口尚未就绪，下一轮确认"
        state_write "$group" "0 $first_fail $now $level 0"
      else
        level=$(( level + 1 )); [[ $level -gt 4 ]] && level=4
        log "[$group] 自愈后仍不健康（缺失=$still），退避级别升到 $level"
        state_write "$group" "0 $first_fail $level 0" 2>/dev/null || state_write "$group" "0 $first_fail $now $level 0"
      fi
    fi
  else
    level=$(( level + 1 )); [[ $level -gt 4 ]] && level=4
    log "[$group] 自愈命令返回非零，退避级别升到 $level"
    state_write "$group" "0 $first_fail $now $level 0"
  fi
done

if [[ "$MODE" == "--status" || "$MODE" == "--doctor" ]]; then
  echo; echo "不健康组数=$unhealthy"; exit 0
fi

# ---- 容器级守护（r12-* 统一 restart=unless-stopped；被显式 stop 的从容器侧看不出，这里兜住）----
CONTAINERS=(r12-mysql r12-redis r12-es r12-minio r12-milvus r12-nacos r12-rocketmq-namesrv
            r12-rocketmq-broker r12-nebula-metad r12-nebula-storaged r12-nebula-graphd
            r12-etcd r12-preview r12-fe)
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  c_bad=0; c_heal=0
  IFS=$' \t\n' read -r c_fails c_first c_last c_level _c_stuck <<< "$(state_read containers)"
  c_missing=(); c_detail=""
  for c in "${CONTAINERS[@]}"; do
    st="$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null)"
    [[ -z "$st" ]] && continue                 # 容器不存在（未安装/已删）不强行创建
    [[ "$st" == "running" ]] || { c_missing+=("$c"); c_detail="$c_detail $c($st)"; }
  done
  if (( ${#c_missing[@]} > 0 )); then
    c_bad=1
    info "[containers] 未运行:$c_detail"
    if [[ "$MODE" != "--doctor" ]] && [[ ! -f "$MAINT" ]]; then
      c_left=0; (( c_level > 0 )) && c_left="$(cooldown_left "$c_last" "$c_level")"
      if (( c_left > 0 )); then info "[containers] 冷却中，剩余 ${c_left}s"
      else
        for cname in "${c_missing[@]}"; do
          log "[containers] 拉起容器 $cname，动作: docker start $cname"
          docker start "$cname" >/dev/null 2>&1 && c_heal=$((c_heal+1)) || log "[containers] docker start $cname 失败"
        done
        sleep 3
        still=""
        for cname in "${c_missing[@]}"; do [[ "$(docker inspect -f '{{.State.Status}}' "$cname" 2>/dev/null)" == "running" ]] || still="$still $cname"; done
        if [[ -z "$still" ]]; then log "[containers] 容器已全部拉起"; state_write containers "0 0 0 0 0"
        else c_level=$((c_level+1)); (( c_level > 4 )) && c_level=4
             log "[containers] 仍有容器未起:$still 退避级别升到 $c_level"
             state_write containers "0 $now $now $c_level 0"; fi
      fi
    fi
  else
    [[ "${c_fails:-0}" != "0" || "${c_level:-0}" != "0" ]] && state_clear containers
  fi
  changed=$(( changed + c_heal )); unhealthy=$(( unhealthy + c_bad ))
else
  info "[containers] docker 不可用，跳过容器守护"
fi

# ---- 解析任务僵尸兜底（TL：recoverStaleTasksOnStartup 只在重启时跑一次，需定期兜底）----
# 每 5 分钟一次；单独 state 文件记 last_run，不算"不健康组"，失败只告警不阻塞。
STALE_TASK_SECS="${STALE_TASK_SECS:-300}"
if [[ "$MODE" != "--doctor" && ! -f "$MAINT" && -x "$R12/bin/recover-stuck-tasks.sh" ]]; then
  IFS=$' \t\n' read -r _tf _tff t_last _tl _ts <<< "$(state_read tasks)"
  if (( now - ${t_last:-0} >= STALE_TASK_SECS )); then
    if out="$(bash "$R12/bin/recover-stuck-tasks.sh" --mins 10 2>&1)"; then
      info "[tasks] 僵尸兜底：$(printf '%s' "$out" | grep -E '已处理' | head -1)"
    else
      log "[tasks] recover-stuck-tasks 失败：$(printf '%s' "$out" | tail -2 | tr '\n' ' ')"
    fi
    state_write tasks "0 0 $now 0 0"
  fi
fi

info "巡检结束：不健康组=$unhealthy 本轮自愈=$changed"
# 重要（R14 实测教训）：**不要**用非零退出码表示"发现问题"。
# 本单元由 timer 驱动，oneshot 退出非零 -> unit failed，连续几次后 systemd 会停掉
# OnUnitActiveSec 的 timer，看门狗彻底停摆（10:44:34 真实发生过，停了 11 分钟没人发现）。
# 问题通过 watchdog.log 的 ALERT 行 + run/watchdog-status.txt 暴露，退出码恒 0。
printf 'time=%s unhealthy=%s healed=%s\n' "$(date -Is)" "$unhealthy" "$changed" > "$R12/run/watchdog-status.txt"
(( unhealthy > 0 )) && log "ALERT 仍有 $unhealthy 个服务组不健康（详见上文明细），看门狗将继续巡检"
exit 0
