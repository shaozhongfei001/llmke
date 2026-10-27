#!/usr/bin/env bash
# R14-F06：在"可联网或内网 npm 镜像可达"的机器上把 node_modules 拉成离线缓存，
# 目标机用 `npm ci --offline --cache <缓存目录>` 复现（不拷 node_modules）。
#
# 用法（在 frontend/plateform 目录下执行）:
#   resolve-npm-offline.sh [缓存目录，默认 ./npm-cache]
# 环境变量:
#   NPM_REGISTRY  内网 registry，例: https://nexus.internal/repository/npm-group/
set -uo pipefail
CACHE="${1:-./npm-cache}"
ok()  { printf '  [ok] %s\n' "$1"; }
die() { printf '  [FAIL] %s\n' "$1"; exit 1; }

[ -f package.json ] || die "请在 frontend/plateform 目录下执行"
[ -f package-lock.json ] || die "缺 package-lock.json（lock 是精确清单，不能用 package.json 代替）"
command -v npm >/dev/null || die "未安装 npm"

mkdir -p "$CACHE"
if [ -n "${NPM_REGISTRY:-}" ]; then
  ok "使用内网 registry $NPM_REGISTRY"
  npm ci --cache "$CACHE" --registry "$NPM_REGISTRY" || die "npm ci 失败"
else
  ok "使用默认 registry（内网请设 NPM_REGISTRY）"
  npm ci --cache "$CACHE" || die "npm ci 失败"
fi

# 只保留缓存本体，node_modules 不回传给目标机（体积）
ok "npm 离线缓存就绪: $CACHE（$(du -sh "$CACHE" | cut -f1)）"
echo "目标机复现："
echo "  npm ci --offline --cache <该缓存目录>   # 严格按 package-lock.json"
echo "  npm run build"
