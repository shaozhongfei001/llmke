#!/usr/bin/env bash
# REPRODUCIBLE：独立重跑本证据，原始输出落 raw/
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../../../.." && pwd)"
PY="${R15_VENV_PY:-$ROOT/platform/r12/venvs/graph/bin/python}"
mkdir -p "$HERE/raw"
OUT="$HERE/raw/$(date +%Y-%m-%dT%H-%M-%S).log"
[ -x "$PY" ] || { echo "[FAIL] 缺 python: $PY" >&2; exit 2; }
"$PY" "$HERE/r15_f10_probe2.py" 2>&1 | tee "$OUT"
rc=${PIPESTATUS[0]}
echo "[raw] $OUT"
echo "[NOTE] 本脚本不自我判定 PASS/FAIL；判定看 raw 输出与 RESULT.md 的预期对照"
exit $rc
