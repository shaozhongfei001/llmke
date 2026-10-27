#!/usr/bin/env bash
# R14 退出检查（轻量）：只读证据与台账，输出 CONTINUE / RUNNING_JOB / COMPLETE / WAITING_EXTERNAL
# 用法：r14-exit-check.sh [--verbose]
# 说明：这不是产品验收平台，只做"能否宣布完成"的门禁。完成判定必须依赖真实证据目录。
set -uo pipefail
R12="$(cd "$(dirname "$0")/.." && pwd)"
EVID="$R12/qa/evidence"
VERBOSE="${1:-}"

fail=0
say() { [ "$VERBOSE" = "--verbose" ] && echo "  $*"; return 0; }

latest_dir() { ls -1dt "$EVID"/$1* 2>/dev/null | head -1; }

# 1) 四套验收：取各自最新证据，要求全部 PASS 且无 FAIL
check_suite() {
  local label="$1" pattern="$2" dir summary pass failn
  dir="$(latest_dir "$pattern")"
  if [ -z "$dir" ]; then
    echo "[missing] $label 无证据目录"; fail=$((fail+1)); return
  fi
  summary="$dir/summary.md"
  [ -f "$summary" ] || summary=$(ls "$dir"/*.md 2>/dev/null | head -1)
  pass=$(grep -c '^| .*PASS' "$summary" 2>/dev/null | head -1); pass=${pass:-0}
  failn=$(grep -c '^| .*FAIL' "$summary" 2>/dev/null | head -1); failn=${failn:-0}
  say "$label: dir=$(basename "$dir") pass=$pass fail=$failn"
  if [ "$failn" -gt 0 ] || [ "$pass" -eq 0 ]; then
    echo "[FAIL] $label: $(basename "$dir") pass=$pass fail=$failn"; fail=$((fail+1))
  fi
}
check_suite "主链" ""
check_suite "安全" "SEC-"
check_suite "撤权" "REVOKE-"
check_suite "能力矩阵" "CAPS-"

# 2) 能力矩阵里是否还有 ❌（必选未实现）
MATRIX="$R12/../../docs/r12/r14/CAPABILITY-MATRIX.md"
if [ -f "$MATRIX" ]; then
  gaps=$(grep -c '| ❌' "$MATRIX" 2>/dev/null | head -1); gaps=${gaps:-0}
  say "能力矩阵 ❌ 项=$gaps"
  [ "$gaps" -gt 0 ] && { echo "[OPEN] 能力矩阵仍有 $gaps 个 ❌"; fail=$((fail+1)); }
else
  echo "[missing] 能力矩阵不存在"; fail=$((fail+1))
fi

# 3) 监听面门（若脚本可用）
if [ -x "$R12/bin/check-bind.sh" ]; then
  if bash "$R12/bin/check-bind.sh" --expect-loopback >/dev/null 2>&1; then
    say "监听面门: PASS"
  else
    echo "[OPEN] 监听面门未通过（含基础设施面时以 R14 新版为准）"; fail=$((fail+1))
  fi
fi

# 4) 决策
if [ "$fail" -eq 0 ]; then
  echo "DECISION=COMPLETE"
else
  echo "DECISION=CONTINUE ($fail 项未满足)"
fi
exit $([ "$fail" -eq 0 ] && echo 0 || echo 3)
