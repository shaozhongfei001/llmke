#!/usr/bin/env bash
# R12 服务启停控制（Java 业务服务）
# 用法：r12ctl.sh {start|stop|restart|status} [服务名|all]
set -uo pipefail

R12_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$R12_ROOT/../.." && pwd)"
JAVA_PARENT="$REPO_ROOT/services/rag-java/rag-parent"
LOGS="$R12_ROOT/logs"
RUN="$R12_ROOT/run"
CONF="$R12_ROOT/conf"
mkdir -p "$LOGS" "$RUN"

# 运行期口令从 platform/r12/.env 注入（该文件不入库），避免把口令写进版本库
R12_ENV_FILE="${R12_ENV_FILE:-$R12_ROOT/.env}"
if [[ -f "$R12_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$R12_ENV_FILE"
  set +a
fi
export R12_MYSQL_PASSWORD="${R12_MYSQL_ROOT_PASSWORD:-}"
export R12_REDIS_PASSWORD="${R12_REDIS_PASSWORD:-}"
export R12_MINIO_SECRET_KEY="${R12_MINIO_SECRET_KEY:-}"

# 端口表：status 要判"pidfile 的 pid 是否就是持端口的 pid"（C 报的第三例：pidfile 指向不监听的孤儿）
declare -A PORTS=(
  [rag-auth-service]=18081
  [rag-index-service]=18082
  [rag-qa-service]=18083
  [rag-gateway]=8088
  [sensitive-words-service]=18085
  [rag-graph-service]=18084
)

declare -A JARS=(
  [rag-auth-service]="rag-auth-service/target/rag-auth-service-0.0.1-SNAPSHOT.jar"
  [rag-index-service]="rag-index-service/target/rag-index-service-0.0.1-SNAPSHOT.jar"
  [rag-qa-service]="rag-qa-service/target/rag-qa-service-0.0.1-SNAPSHOT.jar"
  [rag-gateway]="rag-gateway/target/rag-gateway-0.0.1-SNAPSHOT.jar"
  [sensitive-words-service]="sensitive-words-service/target/sensitive-words-service-0.0.1-SNAPSHOT.jar"
  [rag-graph-service]="rag-graph-service/target/rag-graph-service-0.0.1-SNAPSHOT.jar"
)

# F-qa 报的现场：rag-qa/rag-index 的 jar 在 10:29 被重建，但 JVM 是 10:02 起的，
# 内存里仍是旧 jar，导致 /error 渲染 ClassNotFoundException -> 拒绝态变 500。
# 并发构建是常态，所以必须能在起停/状态里直接看出来，而不是靠人比对 mtime。
listen_pids_of() { ss -ltnpH "sport = :$1" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u | paste -sd, -; }

jar_stale() {  # jar_stale <name> <pid> ：jar 比进程新则返回 0
  local name=$1 pid=$2 jar
  jar="$JAVA_PARENT/${JARS[$name]:-}"
  [[ -f "$jar" ]] || return 1
  local jar_ts proc_ts
  jar_ts="$(stat -c %Y "$jar" 2>/dev/null)" || return 1
  # R14-C 报的真实 bug（假阴性）：原来写 `xargs -r date -d '+%s'`，把输出格式当成了 -d 的入参，
  # date 直接失败 -> proc_ts 为空 -> 永远 return 1 -> [STALE_JAR] 从不告警（这轮三次踩坑全靠人眼比对）。
  # 正确写法：把 lstart 作为 -d 的参数传入，+%s 作为独立格式参数。
  proc_ts="$(ps -o lstart= -p "$pid" 2>/dev/null | xargs -r -I{} date -d '{}' +%s 2>/dev/null)" || return 1
  [[ -z "$jar_ts" || -z "$proc_ts" ]] && return 1
  (( jar_ts > proc_ts ))
}

# 诊断用：打印 jar_ts / proc_ts / 差值，避免"门禁自己坏了却显示绿色"
jar_meta() {  # jar_meta <name> <pid> -> "jar_ts proc_ts delta"
  local name=$1 pid=$2 jar jar_ts proc_ts
  jar="$JAVA_PARENT/${JARS[$name]:-}"
  jar_ts="$(stat -c %Y "$jar" 2>/dev/null || echo -)"
  proc_ts="$(ps -o lstart= -p "$pid" 2>/dev/null | xargs -r -I{} date -d '{}' +%s 2>/dev/null || echo -)"
  if [[ "$jar_ts" =~ ^[0-9]+$ && "$proc_ts" =~ ^[0-9]+$ ]]; then
    echo "$jar_ts $proc_ts $(( jar_ts - proc_ts ))"
  else
    echo "${jar_ts:- -} ${proc_ts:- -} ?"
  fi
}

start_one() {
  local name=$1
  local jar="${JARS[$name]:-}"
  if [[ -z "$jar" ]]; then echo "unknown service: $name"; return 1; fi
  local pidfile="$RUN/$name.pid"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name already running pid=$(cat "$pidfile")"
    if jar_stale "$name" "$(cat "$pidfile")"; then
      read -r _jt _pt _dl <<< "$(jar_meta "$name" "$(cat "$pidfile")")"
      echo "  [!!] $name 的 jar 比进程新 ${_dl}s：当前进程仍加载旧 jar，需 restart 才生效"
      echo "  ⚠ 运行进程可能已进入懒加载损坏态（NoClassDefFoundError / 随机 5xx），请立即重启，勿继续压测"
    fi
    return 0
  fi
  local logconf="-Dlogging.config=$R12_ROOT/log4j2/$name.xml"
  local loghome="-DLOG_HOME=$LOGS/java/$name"
  # R14-F02 暴露面收口：Spring 的 server.address=127.0.0.1 在双栈 JVM 上会绑成
  # [::ffff:127.0.0.1]（ss 里看起来像"对外监听"，实际仍是回环）。加 preferIPv4Stack
  # 让它只绑 127.0.0.1，监听面判定不再有歧义。
  # 网关(rag-gateway)除外：8088 是明确批准对外的入口，不能砍掉 IPv6 客户端。
  local netopt="-Djava.net.preferIPv4Stack=true"
  [[ "$name" == "rag-gateway" ]] && netopt=""
  local jvm="-Xms256m -Xmx1g -XX:+UseG1GC $netopt"
  local addloc=""
  if [[ -d "$CONF/$name" ]]; then addloc="--spring.config.additional-location=file:$CONF/$name/"; fi
  # .out 每次启动前截断，避免"文件里是上一次的崩溃栈"被误读成当前失败（D 已踩过）
  : > "$LOGS/$name.out"
  ( cd "$JAVA_PARENT/$name" && nohup setsid java $jvm $logconf $loghome \
      -jar "$JAVA_PARENT/$jar" --spring.profiles.active=r12 $addloc \
      >> "$LOGS/$name.out" 2>&1 & )
  # R14-C 报的"制造僵尸"机制：start 后只 sleep 3 就按 pgrep 写 pidfile，
  # 若端口被上一实例占着，新 JVM 绑不上也不退出 -> 留下一个"不监听端口"的孤儿，
  # 而 pidfile 恰指向它 -> status 显示 RUNNING、stop 杀掉它却把真实例留下（今天三例）。
  # 修法：等**端口真正绑定**再写 pidfile，且 pidfile 写"持端口的那个 pid"；超时就杀掉自己。
  local port="${PORTS[$name]:-}" wait_s="${R12CTL_WAIT:-180}" i listen
  if [[ -n "$port" ]]; then
    for (( i=0; i<wait_s; i+=2 )); do
      listen="$(listen_pids_of "$port")"
      [[ -n "$listen" ]] && break
      sleep 2
    done
    if [[ -z "$listen" ]]; then
      local cand; cand="$(pgrep -f "$jar" | head -1)"
      [[ -n "$cand" ]] && { echo "  [!!] $name 端口 $port 在 ${wait_s}s 内未绑定，杀掉未就绪进程 pid=$cand（避免留下不监听的孤儿）"; kill -9 "$cand" 2>/dev/null; }
      rm -f "$pidfile"
      echo "$name start FAILED: port $port not bound（见 $LOGS/$name.out）" >&2
      return 1
    fi
    echo "$listen" | cut -d, -f1 > "$pidfile"
    echo "$name started pid=$(cat "$pidfile") port=$port log=$LOGS/$name.out"
    return 0
  fi
  sleep 3
  pgrep -f "$jar" | head -1 > "$pidfile"
  echo "$name started pid=$(cat "$pidfile") log=$LOGS/$name.out"
}

stop_one() {
  local name=$1
  local pidfile="$RUN/$name.pid"
  if [[ -f "$pidfile" ]]; then
    local pid; pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null
      for _ in $(seq 1 30); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
      kill -9 "$pid" 2>/dev/null || true
      echo "$name stopped"
    else
      echo "$name not running"
    fi
    rm -f "$pidfile"
  else
    echo "$name no pidfile"
  fi
}

# 全局：status 发现不一致时以非零退出（F/C 都要求"单实例 + pidfile 一致"才算可复测）
STATUS_BAD=0

status_one() {
  local name=$1 pf pid port listen
  pf="$RUN/$name.pid"; pid="$(cat "$pf" 2>/dev/null || true)"; port="${PORTS[$name]:-}"
  listen="$(listen_pids_of "$port" 2>/dev/null || true)"

  # 无 pidfile / pidfile 进程已死，但端口还在监听 -> pidfile 脱钩（孤儿在跑）
  if [[ -z "$pid" || ! -d "/proc/$pid" ]]; then
    if [[ -n "$listen" ]]; then
      echo "$name [PIDFILE_MISMATCH] pidfile=${pid:-缺失} 但 $port 由 pid=$listen 持有"
      echo "  ⚠ 控制面与实际脱钩：stop 会杀错进程；执行 echo $listen > $pf 后重试"
      STATUS_BAD=1
    else
      echo "$name STOPPED"
    fi
    return
  fi

  # pidfile 进程活着，但没绑定端口 -> 未就绪的孤儿（今天三例的形态）
  if [[ -z "$listen" ]]; then
    echo "$name [NO_LISTEN] pid=$pid 存活但 $port 无监听（未就绪/绑端口失败）"
    echo "  ⚠ 该进程是"起了但没绑上"的孤儿：r12ctl stop $name 后再 start"
    STATUS_BAD=1
    return
  fi

  # pidfile 与持端口 pid 必须一致
  if [[ ",$listen," != *",$pid,"* ]]; then
    echo "$name [PIDFILE_MISMATCH] pidfile=$pid，$port 实际由 pid=$listen 持有"
    echo "  ⚠ 执行 echo $listen > $pf 校正后，再 stop/start 清理多余实例"
    STATUS_BAD=1
    return
  fi

  if jar_stale "$name" "$pid"; then
    read -r _jt _pt _dl <<< "$(jar_meta "$name" "$pid")"
    echo "$name RUNNING pid=$pid [STALE_JAR] jar 比进程新 ${_dl}s（重启才生效）"
    echo "  ⚠ 运行进程可能已进入懒加载损坏态（NoClassDefFoundError / 随机 5xx），请立即重启，勿继续压测"
  else
    echo "$name RUNNING pid=$pid"
  fi
}

# R14：变更留痕（TL 要求）。目的不是防外部，而是**下次服务莫名停了能在 1 分钟内定位**
# —— 今天两次整栈中断排查花了 20+ 分钟，就是因为"谁在什么时候对哪个服务做了什么"没有记录。
# 记录：时间 / 用户 / 调用方进程链 / 动作 / 目标 / 原因（R12_CHANGE_REASON）/ 结果
CHANGES="$R12_ROOT/logs/changes.log"
caller_chain() {  # 从当前进程往上找 4 层，拼成 "cmd<-cmd<-cmd"
  local pid=$$ out="" i=0 cmd
  while [[ -n "$pid" && "$pid" -gt 1 && $i -lt 4 ]]; do
    cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | cut -c1-60)"
    [[ -z "$cmd" ]] && cmd="$(awk '{print $1}' "/proc/$pid/comm" 2>/dev/null)"
    out="${out:+$out<-}${cmd:-?}"
    pid="$(awk '{print $4}' "/proc/$pid/stat" 2>/dev/null)"
    i=$((i+1))
  done
  echo "$out"
}
log_change() {  # log_change <动作> <目标> [补充]
  mkdir -p "$(dirname "$CHANGES")"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(date -Is)" "${USER:-$(id -un)}" "${R12_CHANGE_REASON:--}" "$1" "$2" "$(caller_chain)" "${3:-}" >> "$CHANGES"
}

action=${1:-status}
shift || true
targets=("${@:-all}")
if [[ "${targets[0]}" == "all" ]]; then
  targets=(rag-auth-service rag-index-service rag-qa-service sensitive-words-service rag-gateway rag-graph-service)
fi

if [[ "$action" == "diag" ]]; then
  printf '%-24s %-8s %-12s %-12s %s\n' SERVICE PID JAR_TS PROC_TS DELTA
  for n in "${targets[@]}"; do
    pf="$RUN/$n.pid"
    if [[ -f "$pf" ]] && kill -0 "$(cat "$pf")" 2>/dev/null; then
      read -r jt pt dl <<< "$(jar_meta "$n" "$(cat "$pf")")"
      printf '%-24s %-8s %-12s %-12s %s\n' "$n" "$(cat "$pf")" "$jt" "$pt" "${dl}s"
    else
      printf '%-24s %-8s %-12s %-12s %s\n' "$n" - - - STOPPED
    fi
  done
  echo "  说明：DELTA>0 表示 jar 比进程新（需 restart）；若 JAR_TS/PROC_TS 出现 '-' 说明取时间失败（门禁会假阴性）"
  exit 0
fi

case "$action" in
  start) for n in "${targets[@]}"; do log_change start "$n"; start_one "$n"; done ;;
  stop) for n in "${targets[@]}"; do log_change stop "$n"; stop_one "$n"; done ;;
  restart) for n in "${targets[@]}"; do log_change restart "$n"; stop_one "$n"; start_one "$n"; done ;;
  status)
    for n in "${targets[@]}"; do status_one "$n"; done
    if (( STATUS_BAD )); then
      echo "  [FAIL] 存在 PIDFILE_MISMATCH / NO_LISTEN（单实例或 pidfile 与监听者不一致）" >&2
      exit 3
    fi
    ;;
  *) echo "usage: $0 {start|stop|restart|status} [service|all]"; exit 1 ;;
esac
