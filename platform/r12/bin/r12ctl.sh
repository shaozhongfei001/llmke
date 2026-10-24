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

declare -A JARS=(
  [rag-auth-service]="rag-auth-service/target/rag-auth-service-0.0.1-SNAPSHOT.jar"
  [rag-index-service]="rag-index-service/target/rag-index-service-0.0.1-SNAPSHOT.jar"
  [rag-qa-service]="rag-qa-service/target/rag-qa-service-0.0.1-SNAPSHOT.jar"
  [rag-gateway]="rag-gateway/target/rag-gateway-0.0.1-SNAPSHOT.jar"
  [sensitive-words-service]="sensitive-words-service/target/sensitive-words-service-0.0.1-SNAPSHOT.jar"
  [rag-graph-service]="rag-graph-service/target/rag-graph-service-0.0.1-SNAPSHOT.jar"
)

start_one() {
  local name=$1
  local jar="${JARS[$name]:-}"
  if [[ -z "$jar" ]]; then echo "unknown service: $name"; return 1; fi
  local pidfile="$RUN/$name.pid"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name already running pid=$(cat "$pidfile")"; return 0
  fi
  local logconf="-Dlogging.config=$R12_ROOT/log4j2/$name.xml"
  local loghome="-DLOG_HOME=$LOGS/java/$name"
  local jvm="-Xms256m -Xmx1g -XX:+UseG1GC"
  local addloc=""
  if [[ -d "$CONF/$name" ]]; then addloc="--spring.config.additional-location=file:$CONF/$name/"; fi
  ( cd "$JAVA_PARENT/$name" && nohup setsid java $jvm $logconf $loghome \
      -jar "$JAVA_PARENT/$jar" --spring.profiles.active=r12 $addloc \
      > "$LOGS/$name.out" 2>&1 & )
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

status_one() {
  local name=$1
  local pidfile="$RUN/$name.pid"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name RUNNING pid=$(cat "$pidfile")"
  else
    echo "$name STOPPED"
  fi
}

action=${1:-status}
shift || true
targets=("${@:-all}")
if [[ "${targets[0]}" == "all" ]]; then
  targets=(rag-auth-service rag-index-service rag-qa-service sensitive-words-service rag-gateway rag-graph-service)
fi

case "$action" in
  start) for n in "${targets[@]}"; do start_one "$n"; done ;;
  stop) for n in "${targets[@]}"; do stop_one "$n"; done ;;
  restart) for n in "${targets[@]}"; do stop_one "$n"; start_one "$n"; done ;;
  status) for n in "${targets[@]}"; do status_one "$n"; done ;;
  *) echo "usage: $0 {start|stop|restart|status} [service|all]"; exit 1 ;;
esac
