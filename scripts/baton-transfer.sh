#!/usr/bin/env bash
# Atomic baton transfer — thin wrapper over loop_guard.py.
# Usage: bash scripts/baton-transfer.sh <LOOP_ID> --to <HOLDER> [--packet P] [--wave W]
#        [--executor NAME] [--role ROLE]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOOP_ID="${1:?usage: baton-transfer.sh <LOOP_ID> --to <HOLDER> [--packet P] [--wave W]}"
shift

exec python3 "${ROOT}/scripts/loop_guard.py" --root "${ROOT}" \
  baton-transfer --loop "${LOOP_ID}" "$@"
