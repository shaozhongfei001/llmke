#!/usr/bin/env bash
# R14-F06：把 requirements 拉成 wheel 目录，供目标机 `pip install --no-index --find-links` 离线安装。
# 目的：venv 不能原样拷贝到异构机器（https://docs.python.org/3.11/library/venv.html ），
#      必须能从源码 + wheel 复建。
#
# 用法（在仓库根执行）:
#   resolve-python-offline.sh [wheel 目录，默认 ./wheels] [requirements 文件]
# 环境变量:
#   PIP_INDEX_URL  内网 PyPI，例: https://pypi.internal/simple
#   PY_TARGET      目标机 python 版本，默认 3.11
set -uo pipefail
WHEELS="${1:-./wheels}"
REQ="${2:-requirements.txt}"
PY_TARGET="${PY_TARGET:-3.11}"
ok()  { printf '  [ok] %s\n' "$1"; }
die() { printf '  [FAIL] %s\n' "$1"; exit 1; }

[ -f "$REQ" ] || die "找不到 $REQ"
mkdir -p "$WHEELS"
ARGS=(download -r "$REQ" -d "$WHEELS" --only-binary=:all:)
if [ -n "${PIP_INDEX_URL:-}" ]; then ok "使用内网 PyPI $PIP_INDEX_URL"; else ok "使用默认 PyPI（内网请设 PIP_INDEX_URL）"; fi
command -v python3 >/dev/null || die "未安装 python3"

python3 -m pip "${ARGS[@]}" || die "pip download 失败（部分包可能只有源码分发，去掉 --only-binary 再试）"
ok "wheel 就绪: $WHEELS（$(du -sh "$WHEELS" | cut -f1)，$(ls "$WHEELS" | wc -l) 个文件）"
echo "目标机（Python ${PY_TARGET}）复现："
echo "  python${PY_TARGET} -m venv venv"
echo "  venv/bin/pip install --no-index --find-links <该目录> -r $REQ"
