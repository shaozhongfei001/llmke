#!/usr/bin/env bash
# R13 离线安装路径适配器（目标机执行）
#
# 背景：离线包是在构建机（/home/szf/data/dev/llmke-r12）上打包的，
#       systemd/*.service、nacos/configs.json、run/*.env、graph/*.py 里残留构建机绝对路径。
#       直接把包拷到 /opt/r12 后，这些路径全部指向不存在的位置，服务起不来。
#
# 本脚本做四件事（幂等，可重复执行）：
#   1) 文本路径改写：构建机前缀 -> 目标前缀（先长后短，避免前缀互相吞掉）
#   2) 目录补齐：logs/ logs/java/ logs/parse/ run/ graph/audit/
#   3) venv 修复：bin/python* 悬空符号链接改指目标机解释器，pyvenv.cfg 的 home 同步
#   4) 兼容布局：生成 services/rag-java/rag-parent/<svc>/target/<jar> 软链，让 r12ctl.sh 不必改代码
#
# 用法:
#   install-paths.sh [--prefix /opt/r12] [--root /opt/r12/src] [--from <构建机前缀>]
#                    [--python /usr/bin/python3.11] [--dry-run] [--check]
#
#   --prefix  安装前缀，默认取脚本所在 bin/ 的上一级，再退化为 /opt/r12
#   --root    services/、frontend/ 源码落地根，默认 <prefix>/src
#   --from    构建机前缀，默认自动从 systemd/*.service 里探测
#   --python  指定 venv 使用的解释器；缺省按 venv 需要的版本自动找
#   --dry-run 只打印动作，不落盘
#   --check   只检查残留（不改写），有残留则退出码 1
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG="$(cd "$SELF_DIR/.." && pwd)"

PREFIX=""
ROOT=""
FROM=""
PYTHON=""
DRY=0
CHECK=0

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
info() { printf '  [..] %s\n' "$1"; }

usage() { sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --prefix) PREFIX="${2:-}"; shift 2 ;;
    --root)   ROOT="${2:-}"; shift 2 ;;
    --from)   FROM="${2:-}"; shift 2 ;;
    --python) PYTHON="${2:-}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --check)  CHECK=1; shift ;;
    -h|--help) usage ;;
    *) echo "未知参数: $1"; usage ;;
  esac
done

[ -n "$PREFIX" ] || PREFIX="$PKG"
# 构建机前缀探测：systemd 里第一条 /home/ 绝对路径的公共父级
if [ -z "$FROM" ]; then
  FROM="$(grep -rhoE '/(home|Users|opt|data)/[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*/platform/r12' "$PKG/systemd" 2>/dev/null \
          | sed 's#/platform/r12$##' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')"
fi
[ -n "$FROM" ] || FROM="/home/szf/data/dev/llmke-r12"
[ -n "$ROOT" ] || ROOT="$PREFIX/src"

OLD_R12="$FROM/platform/r12"
NEW_R12="$PREFIX"
NEW_ROOT="$ROOT"

# 需要改写的文件集合（只碰离线安装相关文本，不动二进制与模型）
TEXT_GLOBS=(
  "$PKG/systemd/*.service"
  "$PKG/systemd/*.env"
  "$PKG/run/*.env"
  "$PKG/run/*.sh"
  "$PKG/models/*.sh"
  "$PKG/graph/*.py"
  "$PKG/nacos/configs.json"
  "$PKG/preview/*.sh"
  "$PKG/docker/*.yml"
  "$PKG/bin/up.sh"
  "$PKG/bin/r12ctl.sh"
  "$PKG/bin/offline-kit.sh"
)

collect_files() {
  local g f
  {
    for g in "${TEXT_GLOBS[@]}"; do
      for f in $g; do
        [ -f "$f" ] || continue
        printf '%s\n' "$f"
      done
    done
    # 算法服务的 Nacos 本地快照（python-nacos 的 SNAPSHOT_BASE 默认是相对路径
    # nacos-data/snapshot，按服务 CWD 解析，正是这些文件）：配置中心不可达时会被回读，
    # 里面同样带构建机绝对路径与 server.host，必须一并改写，否则会被快照静默抵消。
    if [ -d "$PKG/src" ]; then
      find "$PKG/src" -path '*/nacos-data/snapshot/*' -type f 2>/dev/null
    fi
  } | sort -u
}

echo "== install-paths =="
info "前缀      : $PREFIX"
info "源码根    : $ROOT"
info "构建机前缀: $FROM"
[ "$DRY" = 1 ] && info "模式      : dry-run（不落盘）"
[ "$CHECK" = 1 ] && info "模式      : check（只检查不改写）"

# ---------- 1) 文本路径改写 ----------
echo "== 1. 文本路径改写（先 platform/r12，后仓库根）=="
changed=0
residual=0
while IFS= read -r f; do
  hits=$(grep -cF -e "$OLD_R12" -e "$FROM" "$f" 2>/dev/null || true)
  [ "${hits:-0}" = "0" ] && continue
  if [ "$CHECK" = 1 ]; then
    warn "残留 $hits 处: ${f#$PKG/}"
    residual=$((residual+1)); continue
  fi
  if [ "$DRY" = 1 ]; then
    info "将改写 $hits 处: ${f#$PKG/}"
    changed=$((changed+1)); continue
  fi
  # 用 + 作 sed 分隔符：路径里含 /，不能用 /
  sed -i -e "s+$OLD_R12+$NEW_R12+g" -e "s+$FROM+$NEW_ROOT+g" "$f"
  changed=$((changed+1))
done < <(collect_files)
[ "$changed" -gt 0 ] && ok "已改写 $changed 个文件" || ok "无需改写（已是目标前缀）"
[ "$residual" -gt 0 ] && warn "存在残留的文件 $residual 个（用不带 --check 再跑一次）"

# ---------- 2) 目录补齐 ----------
echo "== 2. 运行目录 =="
for d in logs logs/java logs/parse run graph/audit; do
  if [ -d "$PREFIX/$d" ]; then ok "$d 已存在"
  elif [ "$DRY" = 1 ]; then info "将创建 $d"
  elif mkdir -p "$PREFIX/$d" 2>/dev/null; then ok "$d 已创建"
  else warn "$d 创建失败（检查 $PREFIX 写权限）"; fi
done

# ---------- 3) venv 修复 ----------
echo "== 3. Python venv 可重定位 =="
find_python_for() {  # $1 = 需要的 3.X
  local want="$1" c
  [ -n "$PYTHON" ] && { echo "$PYTHON"; return 0; }
  for c in "/usr/bin/python$want" "/usr/local/bin/python$want" "$(command -v "python$want" 2>/dev/null)"; do
    [ -n "$c" ] && [ -x "$c" ] && { echo "$c"; return 0; }
  done
  return 1
}
for v in "$PREFIX"/venvs/*; do
  [ -d "$v" ] || continue
  name="$(basename "$v")"
  if [ ! -e "$v/bin/python" ] && [ ! -L "$v/bin/python" ]; then warn "venv $name 无 bin/python"; continue; fi
  cfg="$v/pyvenv.cfg"
  # uv 生成的 pyvenv.cfg 用 version_info，官方 venv 用 version，两种都认
  want="$( [ -f "$cfg" ] && sed -n -e 's/^version *= *\(3\.[0-9]*\).*/\1/p' -e 's/^version_info *= *\(3\.[0-9]*\).*/\1/p' "$cfg" | head -1 )"
  [ -n "${want:-}" ] || want="3.11"
  # 先判可用性（与是否 dry-run 无关）：可用就不动它
  if "$v/bin/python" -V >/dev/null 2>&1; then ok "venv $name 可用（$("$v/bin/python" -V 2>&1)）"; continue; fi
  interp="$(find_python_for "$want")" || { warn "venv $name 需要 python$want，目标机未找到；请安装后再跑一次本脚本"; continue; }
  if [ "$DRY" = 1 ]; then info "venv $name 解释器不可用，将指向 $interp 并改 pyvenv.cfg home"; continue; fi
  # 原有 pythonX.Y 链接可能是构建机的悬空绝对路径，逐个重指
  for p in "$v"/bin/python3.*; do [ -e "$p" ] || [ -L "$p" ] && ln -sfn "$interp" "$p" 2>/dev/null; done
  ln -sfn "$interp" "$v/bin/python" 2>/dev/null
  ln -sfn "$interp" "$v/bin/python3" 2>/dev/null
  if [ -f "$cfg" ]; then
    sed -i -e "s+^home *=.*+home = $(dirname "$interp")+" -e "s+^version *=.*+version = $("$interp" -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])')+" "$cfg"
  fi
  if "$v/bin/python" -V >/dev/null 2>&1; then ok "venv $name 已指向 $interp"
  else warn "venv $name 仍不可用（site-packages ABI 可能不匹配 python$want）"; fi
done

# ---------- 4) Java jar 兼容布局 ----------
echo "== 4. Java jar 兼容布局（r12ctl.sh 期望 services/rag-java/rag-parent/<svc>/target/）=="
SVCS=(rag-auth-service rag-index-service rag-qa-service rag-gateway sensitive-words-service rag-graph-service)
need_layout=0
for s in "${SVCS[@]}"; do
  [ -f "$NEW_ROOT/services/rag-java/rag-parent/$s/target/$s-0.0.1-SNAPSHOT.jar" ] || need_layout=1
done
if [ "$need_layout" = 0 ]; then ok "布局已就绪"
elif [ "$DRY" = 1 ]; then info "将生成 $NEW_ROOT/services/rag-java/rag-parent/<svc>/target/*.jar 软链 -> $PREFIX/jars/"
else
  made=0
  for s in "${SVCS[@]}"; do
    d="$NEW_ROOT/services/rag-java/rag-parent/$s/target"
    mkdir -p "$d" 2>/dev/null || { warn "无法创建 $d（检查写权限）"; break; }
    if [ -f "$PREFIX/jars/$s-0.0.1-SNAPSHOT.jar" ]; then
      ln -sfn "$PREFIX/jars/$s-0.0.1-SNAPSHOT.jar" "$d/$s-0.0.1-SNAPSHOT.jar" && made=$((made+1))
    else warn "jar 缺失: $PREFIX/jars/$s-0.0.1-SNAPSHOT.jar"; fi
  done
  [ "$made" -gt 0 ] && ok "已生成 $made 个 jar 软链"
fi

# log4j2：r12ctl.sh 用 -Dlogging.config=$PREFIX/log4j2/<svc>.xml，缺失会导致 java 启动即失败
echo "== 5. log4j2 配置 =="
miss=0
for s in "${SVCS[@]}"; do [ -f "$PREFIX/log4j2/$s.xml" ] || miss=$((miss+1)); done
if [ "$miss" = 0 ]; then ok "log4j2 配置齐备（${#SVCS[@]} 个）"
else warn "缺少 $miss 个 log4j2/<svc>.xml —— 当前包未收录该目录，需重新 pack（见 offline/INSTALL-FINDINGS.md F-05）"; fi

# .env 存在性（compose --env-file 缺失会直接失败）
echo "== 6. .env =="
if [ -f "$PREFIX/.env" ]; then
  if grep -q 'CHANGE_ME' "$PREFIX/.env" 2>/dev/null; then warn "$PREFIX/.env 仍含 CHANGE_ME 占位符，需人工填写"
  else ok "$PREFIX/.env 已就绪（口令类内容不在本脚本处理范围）"; fi
elif [ -f "$PREFIX/.env.template" ]; then
  warn "缺少 $PREFIX/.env；请执行: cp $PREFIX/.env.template $PREFIX/.env 并填写口令"
else
  warn "缺少 .env 与 .env.template（compose --env-file 会直接失败）"
fi

# ---------- 7) 结果 ----------
echo
if [ "$CHECK" = 1 ]; then
  rest=$(collect_files | xargs -r grep -lF "$FROM" 2>/dev/null | wc -l)
  if [ "$rest" -eq 0 ]; then ok "无构建机路径残留"; exit 0; else warn "仍有 $rest 个文件残留构建机路径"; exit 1; fi
fi

if [ "$DRY" = 0 ]; then
  rest=$(collect_files | xargs -r grep -lF "$FROM" 2>/dev/null | wc -l)
  if [ "$rest" -eq 0 ]; then ok "路径适配完成，无残留"; else warn "仍有 $rest 个文件残留（见上）"; fi
fi
