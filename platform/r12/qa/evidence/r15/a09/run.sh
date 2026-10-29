#!/usr/bin/env bash
# ASSERTION：用统一断言入口复跑本结论
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../../../.." && pwd)"
mkdir -p "$HERE/raw"
"$ROOT/platform/r15/verify.sh" --only A09 2>&1 | tee "$HERE/raw/$(date +%Y-%m-%dT%H-%M-%S).log"
