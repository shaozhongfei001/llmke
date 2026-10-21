#!/usr/bin/env bash
# Run after protected checkout and venv activation; signing keys are absent here.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"
python3 -c 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 venv required"'
make framework-verify
# Business jobs invoke the catalog-driven business-verify for their approved profile.
# This framework job deliberately does not claim that OPEN P0 items are closed.
