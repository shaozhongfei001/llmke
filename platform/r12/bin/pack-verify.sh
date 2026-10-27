#!/usr/bin/env bash
# R14：离线包"是不是新版"的可执行检查（TL 要求，替代人肉核对）
#
# 背景（本轮三个交付阻断，全部是"包与代码不同步"）：
#   F1 包内 SHA256SUMS 过期（payload/db/gienrag.sql 被替换后没重算）→ 客户第 2 步 sha256sum -c 就停
#   F2 包内 INSTALL-OFFLINE.md 仍是 R13 顺序（init-db 写在"起容器"之前）→ 照装第 5 步必失败
#   F3 包内 bin/systemd/.env.template 缺当天全部修复 → 装完没有自愈、没有端点注册
# 这三条只要有一条成立，包就**不能**作为交付候选。本脚本把三条变成断言。
#
# 用法: pack-verify.sh <离线包目录> [--repo <仓库根>]
#   <离线包目录> 形如 platform/r12/dist/offline（内含 payload/、SHA256SUMS、INSTALL-OFFLINE.md）
# 退出: 0 全过；1 有阻断；2 用法/路径错误
#
# 三道断言（缺一不可）：
#   ① sha256sum -c 全通过（禁止 --ignore-missing：缺文件必须失败）
#   ② INSTALL 步骤**顺序断言**（不是文本比对）：起基础设施必须早于 init-db，且包含新增关键步骤
#   ③ 包内 bin/ 与 systemd/ 与 .env.template 与仓库当前**逐字节一致**
set -uo pipefail
PKG="${1:-}"
[[ -n "$PKG" ]] || { echo "用法: $0 <离线包目录> [--repo <仓库根>]"; exit 2; }
shift
REPO=""
while [ $# -gt 0 ]; do case "$1" in
  --repo) REPO="${2:-}"; shift 2 ;;
  *) echo "未知参数: $1"; exit 2 ;;
esac; done
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${REPO:-$(cd "$R12/../.." && pwd)}"

ok()   { printf '  [ok] %s\n' "$1"; }
bad()  { printf '  [FAIL] %s\n' "$1"; FAIL=$((FAIL+1)); }
warn() { printf '  [!!] %s\n' "$1"; }
FAIL=0

[ -d "$PKG" ] || { echo "包目录不存在: $PKG"; exit 2; }
echo "== pack-verify =="
printf '  [..] pkg=%s\n  [..] repo=%s\n' "$PKG" "$REPO"

# ---------------- ① sha256 ----------------
echo "== ① sha256sum -c（禁止 --ignore-missing）=="
if [ ! -f "$PKG/SHA256SUMS" ]; then
  bad "缺 SHA256SUMS"
else
  out="$( cd "$PKG" && sha256sum -c SHA256SUMS 2>&1 )"; rc=$?
  if [ "$rc" -eq 0 ]; then
    ok "全部匹配（$(wc -l < "$PKG/SHA256SUMS") 条）"
  else
    bad "校验失败 —— 包内文件与清单不一致（清单旧或文件被替换）"
    printf '%s\n' "$out" | grep -E '失败|FAILED|不匹配' | head -8 | sed 's/^/      /'
    printf '      处置：重打（offline-kit.sh pack 会自动重算清单）；不要用 --ignore-missing 绕过\n'
  fi
fi

# ---------------- ② INSTALL 顺序断言 ----------------
echo "== ② INSTALL-OFFLINE.md 步骤顺序断言 =="
DOC="$PKG/INSTALL-OFFLINE.md"
if [ ! -f "$DOC" ]; then
  bad "包内缺 INSTALL-OFFLINE.md"
else
  # 取形如 "5) ..." / "7.1) ..." 的步骤行，按出现顺序生成序列
  mapfile -t steps < <(grep -oE '^[0-9]+(\.[0-9]+)?\)[^：]*' "$DOC" | sed 's/)$//' )
  seq_txt="$(printf '%s\n' "${steps[@]}" | tr '\n' '|')"
  printf '     步骤序列：%s\n' "$seq_txt"

  pos_infra=$(printf '%s\n' "${steps[@]}" | grep -n -m1 -E '\) *(起基础设施|起容器)' | cut -d: -f1)
  pos_initdb=$(printf '%s\n' "${steps[@]}" | grep -n -m1 -E '\) *(初始化数据|init-db)' | cut -d: -f1)
  if [ -z "$pos_infra" ] || [ -z "$pos_initdb" ]; then
    bad "文档里找不到「起基础设施」或「初始化数据库」步骤（顺序无法断言）"
  elif [ "$pos_infra" -lt "$pos_initdb" ]; then
    ok "顺序正确：起基础设施(第 $pos_infra 步) 早于 初始化数据库(第 $pos_initdb 步)"
  else
    bad "顺序倒置：初始化数据库(第 $pos_initdb 步) 早于 起基础设施(第 $pos_infra 步) —— 照装必失败（F2）"
  fi

  # 新增关键步骤必须出现（缺一条就说明文档是旧的）
  for kw in '接口注册表' 'ES 单节点' 'verify' '看门狗'; do
    if grep -q "$kw" "$DOC"; then ok "文档包含关键步骤：$kw"
    else bad "文档缺关键步骤：$kw（说明是修复前的旧文档）"; fi
  done
fi

# ---------------- ③ 安装材料与仓库逐字节一致 ----------------
echo "== ③ 包内 bin/ systemd/ .env.template 与仓库当前逐字节一致 =="
REQUIRED_BIN="up.sh r12ctl.sh r12-change.sh init-db.sh init-nacos.sh init-endpoints.sh install-paths.sh
check-bind.sh check-exposure.sh check-units.sh gates-selftest.sh boot-timing.sh es-single-node.sh
r12-watchdog.sh r12-wait-ready.sh recover-stuck-tasks.sh pack-verify.sh offline-kit.sh"
if [ ! -d "$PKG/payload/bin" ]; then bad "缺 payload/bin/"; else
  miss=""
  for f in $REQUIRED_BIN; do [ -f "$PKG/payload/bin/$f" ] || miss="$miss $f"; done
  [ -z "$miss" ] && ok "必备脚本齐备（$(echo $REQUIRED_BIN | wc -w) 个）" \
    || bad "包内缺必备脚本:$miss（装完会缺能力，如没有端点注册/自愈/门禁）"

  # 交付脚本必须与仓库逐字节一致
  diffn=0
  for f in $REQUIRED_BIN; do
    [ -f "$PKG/payload/bin/$f" ] || continue
    if ! cmp -s "$REPO/platform/r12/bin/$f" "$PKG/payload/bin/$f"; then
      diffn=$((diffn+1)); printf '      内容不同: bin/%s\n' "$f"
    fi
  done
  [ "$diffn" -eq 0 ] && ok "必备脚本与仓库逐字节一致" || bad "有 $diffn 个必备脚本与仓库不一致（F3：包内是旧脚本）"
fi
REQUIRED_UNITS="r12-alg.service r12-models.service r12-docparse.service r12-graphsvc.service r12-java@.service r12-watchdog.service r12-watchdog.timer"
if [ ! -d "$PKG/payload/systemd" ]; then bad "缺 payload/systemd/"; else
  miss=""
  for f in $REQUIRED_UNITS; do [ -f "$PKG/payload/systemd/$f" ] || miss="$miss $f"; done
  [ -z "$miss" ] && ok "unit 齐备（含 watchdog service+timer）" || bad "包内缺 unit:$miss（装完没有自愈/看门狗）"
  diffn=0
  for f in $REQUIRED_UNITS; do
    [ -f "$PKG/payload/systemd/$f" ] || continue
    cmp -s "$REPO/platform/r12/systemd/$f" "$PKG/payload/systemd/$f" || { diffn=$((diffn+1)); printf '      内容不同: systemd/%s\n' "$f"; }
  done
  [ "$diffn" -eq 0 ] && ok "unit 与仓库逐字节一致" || bad "有 $diffn 个 unit 与仓库不一致（KillMode/StopSec/依赖闸门修复没进包）"
fi
tpl_repo="$REPO/platform/r12/offline/templates/env.template"
tpl_pkg="$PKG/payload/.env.template"
if [ ! -f "$tpl_pkg" ]; then bad "缺 payload/.env.template"; else
  if cmp -s "$tpl_repo" "$tpl_pkg"; then ok ".env.template 与仓库一致"
  else
    bad ".env.template 与仓库不一致（缺 R12_MYSQL_PASSWORD 会让 5 个 Java 服务启动即失败）"
    diff -u "$tpl_repo" "$tpl_pkg" | head -12 | sed 's/^/      /'
  fi
fi

echo
if [ "$FAIL" -gt 0 ]; then
  echo "  [FAIL] 该包**不能作为交付候选**：$FAIL 项阻断（详见上）"
  exit 1
fi
echo "  [ok] 包与代码同步、清单有效、文档顺序正确 —— 可以作为候选包"
