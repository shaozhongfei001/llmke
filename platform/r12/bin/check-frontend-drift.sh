#!/usr/bin/env bash
# R14 前端漂移检查：证明"线上跑的产物"与"仓库源码"没有脱节。
#
# 为什么需要它：R14 出现过两次同类事故——
#   ① 容器 bind mount 钉在旧 inode 上，curl 返回 200 但内容是 SPA fallback；
#   ② 源码改了但没重建（dist 13:22 < src 13:34），线上跑的是旧逻辑，而所有断言都基于"新逻辑应该怎样"。
# 这两件事的共同点是：**过程信号正常，产物却不是你以为的那一个**。
#
# 判据（按强度排序）：
#   1) 宿主 dist 的入口 chunk md5 == 线上取回的 md5      → 排除容器钉旧 inode
#   2) 源码最新 mtime <= dist 产物最新 mtime            → 排除"改了没重建"
#   3) 报告 HEAD 短号，供人工确认"这个产物是不是这个提交构建的"
# 注意 3) 不是自动可判的（dist 不记录构建来源），所以本脚本只做 1)/2)，3) 仅打印。
#
# 用法：check-frontend-drift.sh [--prefix <r12根>] [--url <前端地址>]
set -uo pipefail

R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"         # platform/r12
ROOT="$(cd "$R12/../.." && pwd)"                                # 仓库根
URL="http://127.0.0.1:18088"
while [ $# -gt 0 ]; do
  case "$1" in
    --prefix) ROOT="$2"; shift 2 ;;
    --url)    URL="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

DIST="$ROOT/frontend/plateform/dist"
SRC="$ROOT/frontend/plateform/src"
[ -f "$DIST/index.html" ] || { echo "[FAIL] 找不到 $DIST/index.html"; exit 1; }

rc=0
entry=$(grep -oE 'assets/index-[A-Za-z0-9_-]+\.js' "$DIST/index.html" | head -1)
[ -n "$entry" ] || { echo "[FAIL] index.html 里没有入口 chunk"; exit 1; }

disk_md5=$(md5sum "$DIST/$entry" 2>/dev/null | awk '{print $1}')
served_file=$(mktemp)
code=$(curl -sS -o "$served_file" -w '%{http_code}' "$URL/$entry" 2>/dev/null || echo 000)
served_md5=$(md5sum "$served_file" 2>/dev/null | awk '{print $1}')
served_size=$(stat -c%s "$served_file" 2>/dev/null || echo 0)
rm -f "$served_file"

echo "== 1. 产物一致性（宿主 vs 线上）=="
echo "   entry      : $entry"
echo "   disk md5   : $disk_md5"
echo "   served md5 : $served_md5   (http=$code, ${served_size}B)"
if [ "$disk_md5" != "$served_md5" ]; then
  echo "   [FAIL] 宿主与线上不一致 —— 容器可能钉在旧 inode，用 docker restart 而不是 nginx -s reload"
  rc=1
else
  echo "   [ok] 一致"
fi

echo "== 2. 源码 vs 产物（是否改了没重建）=="
newest_src=$(find "$SRC" -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' -o -name '*.scss' -o -name '*.css' \) -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)
newest_dist=$(find "$DIST/assets" -name '*.js' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)
s_ts=${newest_src%% *}; s_f=${newest_src#* }
d_ts=${newest_dist%% *}; d_f=${newest_dist#* }
echo "   最新源码   : $(date -d "@${s_ts%.*}" '+%m-%d %H:%M:%S' 2>/dev/null)  ${s_f#$ROOT/}"
echo "   最新产物   : $(date -d "@${d_ts%.*}" '+%m-%d %H:%M:%S' 2>/dev/null)  ${d_f#$ROOT/}"
if [ "${s_ts%.*}" -gt "${d_ts%.*}" ]; then
  echo "   [FAIL] 源码比产物新 —— 改了没重建，线上跑的是旧逻辑"
  rc=1
else
  echo "   [ok] 产物不早于源码"
fi

echo "== 3. 仓库提交（人工确认用，无法自动判定）=="
if git -C "$ROOT" rev-parse --short HEAD >/dev/null 2>&1; then
  echo "   HEAD : $(git -C "$ROOT" rev-parse --short HEAD)  $(git -C "$ROOT" log -1 --format='%s' | cut -c1-46)"
  if [ -n "$(git -C "$ROOT" status --porcelain -- frontend/plateform/src 2>/dev/null)" ]; then
    echo "   [WARN] 前端源码有未提交改动 —— 线上产物不可能对应任何提交"
  fi
else
  echo "   [..] 非 git 仓库，跳过"
fi

echo
if [ $rc -eq 0 ]; then echo "[PASS] 前端产物与来源一致"; else echo "[FAIL] 前端存在漂移，见上"; fi
exit $rc
