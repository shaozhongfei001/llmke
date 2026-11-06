#!/usr/bin/env bash
# 幂等启动 V2 图栈：18094 HippoRAG API + 19531 建图 shim。
#
# 为什么需要：阶段 4 下线 V1（19529/Nebula）后，图能力全部收敛到这两个进程，
# 但 r12-watchdog.sh 原本只守护 19529；18094/19531 挂掉后无人自愈（2026-11-06
# 实测：/tmp 被清 + 进程退出，global 全断、local 只剩 es 路）。
#
# 图根持久化：platform/r12/data/graph-root，绝不再放 /tmp（/tmp 曾被清空，
# 导致 kb_9/kb_1004 的图快照与重建数据源一起丢失）。
#
# 用法：r12-graph-v2-start.sh        # 已监听则跳过，否则拉起
set -uo pipefail

R12_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# graph_engine_adapter 只在 V2 源码仓维护（r12 运行仓无该包）
V2_SVC_DIR="/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service"
PY="/home/szf/data/dev/hipporag-toolenv/bin/python"
GRAPH_ROOT="$R12_ROOT/data/graph-root"
LOGDIR="$R12_ROOT/logs"

mkdir -p "$GRAPH_ROOT" "$LOGDIR"

if [[ ! -d "$V2_SVC_DIR/graph_engine_adapter" || ! -x "$PY" ]]; then
  echo "V2 图服务依赖缺失: $V2_SVC_DIR 或 $PY" >&2
  exit 1
fi

port_listen() {
  ss -lntH 2>/dev/null | awk -v want=":$1" '{a=$4} a ~ want"$" {f=1} END{exit(f?0:1)}'
}

start_one() {
  local port="$1" module="$2" name="$3"
  if port_listen "$port"; then
    echo "$name($port) 已运行，跳过"
    return 0
  fi
  echo "启动 $name($port) ..."
  ( cd "$V2_SVC_DIR" && LLMKE_V2_ROOT="$GRAPH_ROOT" PYTHONPATH=. \
    setsid nohup "$PY" -m uvicorn "$module" \
      --host 127.0.0.1 --port "$port" \
      > "$LOGDIR/$name.log" 2>&1 < /dev/null & )
  sleep 5
  if port_listen "$port"; then
    echo "$name($port) 已监听 ✅"
  else
    echo "$name($port) 启动失败 ❌（日志 $LOGDIR/$name.log）" >&2
    return 1
  fi
}

rc=0
start_one 18094 graph_engine_adapter.api:app hipporag-18094 || rc=1
start_one 19531 graph_engine_adapter.legacy_shim:app legacy-shim-19531 || rc=1
exit "$rc"
