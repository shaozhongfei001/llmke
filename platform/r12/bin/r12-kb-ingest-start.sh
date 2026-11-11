#!/usr/bin/env bash
# 幂等启动 18096 知识库摄取服务（P4-L13-B）。
#
# 为什么单独一个脚本：18096 是裸进程（无 systemd unit 之外的自愈路径），
# 且它**依赖面比 18094 大得多**——doc2md 配置、artifact store、kb_state、
# MySQL、18094、以及「写 ES/Milvus 的端点是否配置」。任何一项缺失时，
# 进程能起来但**每条摄取都会失败**，这比起不来更糟（看起来 healthy）。
#
# 所以本脚本 = **启动自检（fail-fast）+ 幂等启动 + 存活探针**：
#   1) 自检不过 → 直接 exit 1，不拉起进程（宁可不起，也不带病起）；
#   2) 已监听且 /openapi.json 200 → 跳过（幂等）；
#   3) 端口在但无响应 → 清理残留后重启（uvicorn 主进程死后残留子进程仍占 LISTEN）。
#
# 用法：
#   r12-kb-ingest-start.sh          # 自检 + 幂等启动
#   r12-kb-ingest-start.sh --check  # 只跑自检（不做任何启停）；0=可启动，非0=不可
#
# 注意：`/health` 的 `status=degraded` **不**代表进程挂了（liveness 恒 200），
# readiness 看的是本脚本的自检退出码 —— 不要把 degraded 当"进程死"去反复重启。
set -uo pipefail

R12_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V2_SVC_DIR="/home/szf/data/dev/llmke/services/rag-alg/index_data_service"
PY="/home/szf/data/dev/hipporag-toolenv/bin/python"      # 需 fastapi + pydantic
PORT="18096"
NAME="kb-ingest"
LOGDIR="$R12_ROOT/logs"
RUNDIR="$R12_ROOT/run"
GRAPH_API_DEFAULT="http://127.0.0.1:18094"

mkdir -p "$LOGDIR" "$RUNDIR"

fail_n=0
check() {  # check <描述> <命令...>
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  [ok]   $desc"
  else
    echo "  [FAIL] $desc" >&2
    fail_n=$((fail_n + 1))
  fi
}

# --check 是只读的，不能为了"验证可写"就建目录；但新部署时目录本来就不存在。
# 判据：存在则测自身可写；不存在则测**最近的已存在祖先**可写（即"能建出来"）。
writable_or_creatable() {
  local path="$1"
  while [[ -n "$path" && "$path" != "/" ]]; do
    if [[ -e "$path" ]]; then
      [[ -w "$path" ]] && return 0 || return 1
    fi
    path="$(dirname "$path")"
  done
  return 1
}

port_listen() {
  ss -lntH 2>/dev/null | awk -v want=":$1" '{a=$4} a ~ want"$" {f=1} END{exit(f?0:1)}'
}

http_alive() {
  [[ "$(curl -s -m 6 -o /dev/null -w '%{http_code}' \
        "http://127.0.0.1:$1/openapi.json" 2>/dev/null)" == "200" ]]
}

# --------------------------------------------------------------------------- 自检
self_check() {  # $1=create_dirs(0/1)：--check 模式**不得**产生任何文件系统副作用
  local create="${1:-1}"
  echo "== [1/6] 代码与解释器"
  check "V2 源码目录存在（kb_ingest_service.py）" test -f "$V2_SVC_DIR/kb_ingest_service.py"
  check "解释器可执行（需 fastapi+pydantic）" test -x "$PY"
  check "解释器可 import fastapi" "$PY" -c "import fastapi, pydantic"

  echo "== [2/6] doc2md 产物基线（解析只能发生一次，缺指纹就无法复核）"
  check "LLMKE_DOC2MD_CONFIG 已设置且可读" test -r "${LLMKE_DOC2MD_CONFIG:-/nonexistent}"
  check "LLMKE_DOC2MD_LOCK 已设置且可读" test -r "${LLMKE_DOC2MD_LOCK:-/nonexistent}"

  echo "== [3/6] artifact store / kb_state 落点（契约 §4.2：绝对路径，禁相对与 /tmp）"
  local store="${LLMKE_ARTIFACT_STORE:-$R12_ROOT/data/artifact-store}"
  case "$store" in
    /*) : ;;
    *)  echo "  [FAIL] LLMKE_ARTIFACT_STORE 必须是绝对路径：$store" >&2
        fail_n=$((fail_n + 1)) ;;
  esac
  if [[ "$create" == "1" ]]; then mkdir -p "$store" 2>/dev/null || true; fi
  check "artifact store 可写（或可创建）：$store" writable_or_creatable "$store"

  local state="${LLMKE_KB_STATE:-$R12_ROOT/data/kb-state/kb_state.json}"
  case "$state" in
    /*) : ;;
    *)  echo "  [FAIL] LLMKE_KB_STATE 必须是绝对路径：$state" >&2
        fail_n=$((fail_n + 1)) ;;
  esac
  case "$state" in
    /tmp/*) echo "  [FAIL] LLMKE_KB_STATE 禁止放 /tmp（曾因 /tmp 被清导致按空库重建）：$state" >&2
            fail_n=$((fail_n + 1)) ;;
  esac
  if [[ "$create" == "1" ]]; then mkdir -p "$(dirname "$state")" 2>/dev/null || true; fi
  check "kb_state 目录可写（或可创建）：$(dirname "$state")" \
        writable_or_creatable "$(dirname "$state")"

  echo "== [4/6] 依赖服务可达"
  check "MySQL 13306 可连" bash -c '(exec 3<>/dev/tcp/127.0.0.1/13306) 2>/dev/null'
  check "18094 /openapi.json = 200" http_alive 18094
  check "19527 全文写服务在线" bash -c '(exec 3<>/dev/tcp/127.0.0.1/19527) 2>/dev/null'
  check "19526 向量写服务在线" bash -c '(exec 3<>/dev/tcp/127.0.0.1/19526) 2>/dev/null'

  echo "== [5/6] 写入端点已配置（惰性 fail-closed 的可观测信号）"
  # kb_delta.write_targets_configured() 纯读 env、不连网；未配置时进程能起但**每次写入必拒**，
  # 所以这里必须 fail-fast，不能让它带病上线。
  if PYTHONPATH="$V2_SVC_DIR" "$PY" - <<'PYCODE'
import json
from ingest_pipeline.kb_delta import write_targets_configured
info = write_targets_configured()
print("  write_targets:", json.dumps(info, ensure_ascii=False))
raise SystemExit(0 if info.get("configured") else 1)
PYCODE
  then
    echo "  [ok]   写入端点已配置（或显式允许默认目标）"
  else
    echo "  [FAIL] 写入端点未配置：设 LLMKE_ES_BASE_URL / LLMKE_MILVUS_BASE_URL，" >&2
    echo "         或显式接受线上默认目标 LLMKE_ALLOW_DEFAULT_WRITE_TARGET=1" >&2
    fail_n=$((fail_n + 1))
  fi

  echo "== [6/6] 端口未被他人占用（或已被本服务占用）"
  if port_listen "$PORT" && ! http_alive "$PORT"; then
    echo "  [warn] $PORT 已监听但 /openapi.json 无响应 —— 启动时会先清理残留" >&2
  else
    echo "  [ok]   $PORT 可用"
  fi

  if (( fail_n > 0 )); then
    echo "" >&2
    echo "自检未通过（$fail_n 项失败）：**不启动** $NAME($PORT)。" >&2
    echo "宁可不起，也不带病起 —— 进程起来但每条摄取都失败比起不来更糟。" >&2
    return 1
  fi
  echo "自检全部通过。"
  return 0
}

# --------------------------------------------------------------------------- 启动
start_one() {
  if port_listen "$PORT" && http_alive "$PORT"; then
    echo "$NAME($PORT) 已运行且可响应，跳过"
    return 0
  fi
  if port_listen "$PORT"; then
    echo "$NAME($PORT) 端口在但无响应，清理残留进程后重启" >&2
    for p in $(ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do
      kill -9 "$p" 2>/dev/null || true
    done
    sleep 2
  fi
  echo "启动 $NAME($PORT) ..."
  (
    cd "$V2_SVC_DIR" || exit 1
    PYTHONPATH=. setsid nohup "$PY" -m uvicorn kb_ingest_service:app \
      --host 127.0.0.1 --port "$PORT" \
      >> "$LOGDIR/$NAME.log" 2>&1 < /dev/null &
    echo $! > "$RUNDIR/$NAME.pid"
  )
  local i
  for i in $(seq 1 30); do
    sleep 1
    if port_listen "$PORT" && http_alive "$PORT"; then
      echo "$NAME($PORT) 已监听且可响应 ✅（日志 $LOGDIR/$NAME.log）"
      return 0
    fi
  done
  echo "$NAME($PORT) 启动失败 ❌（日志 $LOGDIR/$NAME.log）" >&2
  return 1
}

MODE="${1:-start}"
case "$MODE" in
  --check)
    self_check 0      # 只读：不建目录、不写任何文件
    exit $?
    ;;
  start|"")
    self_check 1 || exit 1
    start_one
    ;;
  *)
    echo "用法: $0 [--check]" >&2
    exit 2
    ;;
esac
