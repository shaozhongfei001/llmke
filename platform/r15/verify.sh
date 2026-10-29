#!/usr/bin/env bash
# R15 验收统一入口（R15 可转让性改造 第 2 步）
#
# 目标：任何人拿到仓库 + 一套装好的环境，用同一条命令跑出可比的结论，
#       而不是读一份别人手写的"结论是 PASS"。
#
# 用法：
#   platform/r15/verify.sh                                  # 跑全部 A01–A16
#   platform/r15/verify.sh --only A01,A03,A09               # 只跑指定项
#   platform/r15/verify.sh --gw http://h:8088 --es http://h:19200 \
#                          --nebula-host h --nebula-port 9669 \
#                          --kb kb_9 --space g_kb_9          # 指向另一套环境
#   platform/r15/verify.sh --freeze-baseline                  # 把本次结果冻结为基线
#
# 退出码（与 run_all.py 一致，且基础设施不可用单列）：
#   0  没有 FAIL（SKIP 不算通过）
#   1  至少一条 FAIL
#   2  断言集自身无法执行：环境不通 / 缺依赖 / 缺口令
#
# 环境变量（命令行参数优先）：
#   R15_GW R15_ES R15_GRAPH R15_NEBULA_HOST R15_NEBULA_PORT R15_NEBULA_USER
#   R15_KB R15_SPACE R15_CONFIG_ID R15_MYSQL_CONTAINER R15_MYSQL_PWD
#   R15_MODEL_URL R15_MODEL_ID R15_VENV_PY R15_ENV_FILE
#
# 口令：只从环境变量或 platform/r12/.env 读，本脚本不内置任何默认口令。
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
ACC="$HERE/acceptance"

GW="${R15_GW:-http://127.0.0.1:8088}"
ES="${R15_ES:-http://127.0.0.1:19200}"
GRAPH="${R15_GRAPH:-http://127.0.0.1:19529}"
NEB_HOST="${R15_NEBULA_HOST:-127.0.0.1}"
NEB_PORT="${R15_NEBULA_PORT:-19669}"
KB="${R15_KB:-kb_9}"
SPACE="${R15_SPACE:-g_kb_9}"
ONLY=""
FREEZE=0
SKIP_PRECHECK=0

while [ $# -gt 0 ]; do
  case "$1" in
    --gw) GW="$2"; shift 2 ;;
    --es) ES="$2"; shift 2 ;;
    --graph) GRAPH="$2"; shift 2 ;;
    --nebula-host) NEB_HOST="$2"; shift 2 ;;
    --nebula-port) NEB_PORT="$2"; shift 2 ;;
    --kb) KB="$2"; shift 2 ;;
    --space) SPACE="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --freeze-baseline) FREEZE=1; shift ;;
    --skip-precheck) SKIP_PRECHECK=1; shift ;;
    -h|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf '[FAIL] 未知参数 %s（--help 看用法）\n' "$1" >&2; exit 2 ;;
  esac
done

export R15_GW="$GW" R15_ES="$ES" R15_GRAPH="$GRAPH"
export R15_NEBULA_HOST="$NEB_HOST" R15_NEBULA_PORT="$NEB_PORT"
export R15_KB="$KB" R15_SPACE="$SPACE"

# 口令：环境变量 → 包内 .env。取不到就在前置检查里明确失败。
ENV_FILE="${R15_ENV_FILE:-$ROOT/platform/r12/.env}"
if [ -z "${R15_MYSQL_PWD:-}" ] && [ -f "$ENV_FILE" ]; then
  _v=$(grep -hE '^(R12_MYSQL_ROOT_PASSWORD|MYSQL_ROOT_PASSWORD)=' "$ENV_FILE" 2>/dev/null | head -1 | sed 's/^[^=]*=//' | tr -d '"\r')
  [ -n "$_v" ] && export R15_MYSQL_PWD="$_v"
  unset _v
fi

say() { printf '%s\n' "$*"; }
die() { printf '[ABORT] %s\n' "$*" >&2; exit 2; }

say "R15 验收  gateway=$GW  es=$ES  graph=$GRAPH  nebula=$NEB_HOST:$NEB_PORT  kb=$KB  space=$SPACE"

# ── 前置检查：环境不通时，断言跑出来的 FAIL 是假象，必须单列成"无法执行"
if [ "$SKIP_PRECHECK" = "0" ]; then
  probe() {  # probe <名字> <url>
    code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 8 "$2" 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
      say "  [DOWN] $1  $2  (curl rc=$rc)"
      return 1
    fi
    say "  [ UP ] $1  $2  -> $code"
    return 0
  }
  bad=0
  probe "网关"   "$GW/"            || bad=1
  probe "ES"     "$ES/"            || bad=1
  probe "图服务" "$GRAPH/health"   || bad=1
  probe "模型"   "${R15_MODEL_URL:-http://127.0.0.1:18092/v1/models}" || bad=1
  if timeout 6 bash -c "cat < /dev/null > /dev/tcp/$NEB_HOST/$NEB_PORT" 2>/dev/null; then
    say "  [ UP ] Nebula $NEB_HOST:$NEB_PORT"
  else
    say "  [DOWN] Nebula $NEB_HOST:$NEB_PORT"; bad=1
  fi
  [ -n "${R15_MYSQL_PWD:-}" ] && say "  [ UP ] MySQL 口令已就绪（长度 ${#R15_MYSQL_PWD}，不回显）" \
                               || { say "  [DOWN] MySQL 口令缺失（$ENV_FILE）"; bad=1; }
  [ "$bad" = "0" ] || die "环境不完整，断言结果无意义。修好上述项或加 --skip-precheck 强行跑（结果不可用于举证）"
fi

PY="${R15_VENV_PY:-$ROOT/platform/r12/venvs/graph/bin/python}"
# run_all 只需要标准库 + requests；优先用系统 python3（避免 venv 差异）
RUNPY="python3"
command -v "$RUNPY" >/dev/null 2>&1 || die "找不到 python3"
"$RUNPY" -c "import requests" 2>/dev/null || die "python3 缺 requests：pip install requests"

say ""
if [ -n "$ONLY" ]; then
  args=$(printf '%s' "$ONLY" | tr ',' ' ')
else
  args=""
fi

# shellcheck disable=SC2086
"$RUNPY" "$ACC/run_all.py" $args
rc=$?

if [ "$FREEZE" = "1" ] && [ -f "$ACC/results/last-run.json" ]; then
  mkdir -p "$HERE/baseline"
  "$RUNPY" - "$ACC/results/last-run.json" "$HERE/baseline/expect.json" <<'PY'
import json, sys, time
src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8"))
d["frozen_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
d["frozen_note"] = "基线 = 某次评审确认的状态；之后的运行与它比对，用于发现回归"
json.dump(d, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"[baseline] 已冻结 {dst}（{d['summary']}）")
PY
fi

say ""
case $rc in
  0) say "[结论] 无 FAIL（SKIP 项不等于通过，见证据目录里的 SKIP 明细）" ;;
  1) say "[结论] 存在 FAIL，不可声明通过" ;;
  *) say "[结论] 断言集无法执行（环境/依赖问题），结果不可用于举证" ;;
esac
say "[证据] $ACC/results/$(ls -t "$ACC/results" 2>/dev/null | grep -v last-run | head -1)"
exit $rc
