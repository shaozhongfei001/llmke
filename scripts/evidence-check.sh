#!/usr/bin/env bash
# Loop evidence / state machine integrity check (fail-closed) — delegates to loop_guard.py.
# Usage: bash scripts/evidence-check.sh [LOOP_ID]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOOP_ID="${1:-}"

if [[ -z "${LOOP_ID}" ]]; then
  mapfile -t candidates < <(find "${ROOT}/loops" -mindepth 1 -maxdepth 1 -type d \
    ! -name '_template' ! -name 'LH-DRYRUN*' -printf '%f\n' 2>/dev/null)
  if [[ "${#candidates[@]}" -eq 1 ]]; then
    LOOP_ID="${candidates[0]}"
  else
    echo "FAIL: pass LOOP_ID explicitly (found: ${candidates[*]:-none})"
    exit 1
  fi
fi

exec python3 "${ROOT}/scripts/loop_guard.py" --root "${ROOT}" evidence-check --loop "${LOOP_ID}"
