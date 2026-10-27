#!/usr/bin/env bash
# R14：systemd 单元静态检查（交付前必跑）
#
# 存在理由（真实事故）：R14 我把 r12-java@.service 从 Type=forking 改成 oneshot 时，
# 只加了 `RemainAfterExit=yes`，没删掉下面原有的 `RemainAfterExit=no` —— systemd 取**后一条**，
# 于是 oneshot 退出即 deactivate → 触发 ExecStop → `r12ctl stop` 把 JVM 杀掉，
# 造成业务层 16 分钟全断。"文件里改对了、生效的是后一条"这类问题必须静态查出来。
#
# 检查四类：
#   1) 同一 [Section] 内重复指令（后一条静默覆盖前一条）
#   2) repo 模板与已安装副本不一致（改了模板忘了装 / 装了旧副本）
#   3) 已安装且已加载的单元：`systemctl show` 的生效值 vs 文件声明值
#   4) 关键约束：Type=forking 必须配 PIDFile；oneshot 服务若声明 ExecStop 必须 RemainAfterExit=yes
#
# 用法: check-units.sh [--repo-only]
#   退出码 0 = 通过；1 = 有问题；2 = 用法错误
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INST="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
REPO_ONLY=0
[[ "${1:-}" == "--repo-only" ]] && REPO_ONLY=1

bad=0
ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; bad=$((bad+1)); }
die()  { printf '  [FAIL] %s\n' "$1"; bad=$((bad+1)); }

echo "== 1. 重复指令（同 Section 内）=="
# 关注这些会被"后一条覆盖前一条"的指令；重复即视为缺陷
for f in "$R12"/systemd/*.service "$R12"/systemd/*.timer; do
  [ -f "$f" ] || continue
  dup="$(awk '
    /^[[:space:]]*\[/ { sec=$0; next }
    /^[[:space:]]*#/ || /^[[:space:]]*$/ { next }
    {
      line=$0; sub(/^[[:space:]]+/,"",line)
      key=line; sub(/=.*/,"",key)
      # 只查"单值"指令：这些被重复定义时后者静默覆盖前者。
      # ExecStartPre/ExecStartPost/Environment/EnvironmentFile/WantedBy 允许多条，不能算重复。
      split("Type RemainAfterExit Restart RestartSec KillMode TimeoutStartSec TimeoutStopSec PIDFile User WorkingDirectory NotifyAccess StandardOutput StandardError", W, " ")
      want=0; for(i in W) if (W[i]==key) want=1
      if (want) { k=sec "|" key; if (k in seen) printf "%s (line %d)\n", key, NR; else seen[k]=NR }
    }' "$f")"
  if [ -n "$dup" ]; then
    while IFS= read -r d; do [ -n "$d" ] && warn "$(basename "$f") 重复指令: $d"; done <<< "$dup"
  fi
done
[ "$bad" -eq 0 ] && ok "无重复指令"

echo "== 2. 关键约束 =="
for f in "$R12"/systemd/*.service; do
  [ -f "$f" ] || continue
  t="$(grep -m1 '^Type=' "$f" | cut -d= -f2)"
  pidf="$(grep -m1 '^PIDFile=' "$f" | cut -d= -f2)"
  rae="$(grep -m1 '^RemainAfterExit=' "$f" | cut -d= -f2)"
  hasstop=0; grep -q '^ExecStop=' "$f" && hasstop=1
  b="$(basename "$f")"
  if [ "$t" = "forking" ] && [ -z "$pidf" ]; then warn "$b: Type=forking 但没有 PIDFile"; fi
  if [ "$t" = "oneshot" ] && [ "$hasstop" = "1" ] && [ "$rae" != "yes" ]; then
    warn "$b: Type=oneshot + ExecStop 但 RemainAfterExit≠yes（退出即 deactivate → 会执行 ExecStop 杀掉服务）"
  fi
done
[ "$bad" -eq 0 ] && ok "关键约束满足"

echo "== 3. repo 模板 vs 已安装副本 =="
if [ "$REPO_ONLY" = "0" ]; then
  for f in "$R12"/systemd/*.service "$R12"/systemd/*.timer; do
    [ -f "$f" ] || continue
    b="$(basename "$f")"
    if [ ! -f "$INST/$b" ]; then warn "$b 未安装到 $INST（目标机/本机会缺自愈与闸门）"; continue; fi
    if ! diff -q "$f" "$INST/$b" >/dev/null 2>&1; then
      warn "$b 与已安装副本不一致（改模板没装？装了旧副本？）"; diff -u "$f" "$INST/$b" | sed -n '1,12p' | sed 's/^/      /'
    fi
  done
  [ "$bad" -eq 0 ] && ok "已安装副本与模板一致"

  echo "== 4. 生效值 vs 文件声明值 =="
  for f in "$R12"/systemd/*.service; do
    [ -f "$f" ] || continue
    b="$(basename "$f")"
    [[ "$b" == *"@"* ]] && continue    # 模板单元不直接 show，交由实例
    command -v systemctl >/dev/null 2>&1 || continue
    state="$(systemctl --user show -p LoadState --value "$b" 2>/dev/null)"
    [ "$state" = "loaded" ] || continue
    want_t="$(grep -m1 '^Type=' "$f" | cut -d= -f2)"
    got_t="$(systemctl --user show -p Type --value "$b" 2>/dev/null)"
    want_r="$(grep -m1 '^RemainAfterExit=' "$f" | cut -d= -f2)"
    got_r="$(systemctl --user show -p RemainAfterExit --value "$b" 2>/dev/null)"
    [ -n "$want_t" ] && [ "$want_t" != "$got_t" ] && warn "$b Type: 文件=$want_t 生效=$got_t"
    [ -n "$want_r" ] && [ "${want_r/yes/true}" != "$got_r" ] && [ "${want_r/true/true}" != "$got_r" ] \
      && warn "$b RemainAfterExit: 文件=$want_r 生效=$got_r"
  done
  [ "$bad" -eq 0 ] && ok "生效值与文件一致"
else
  ok "--repo-only：跳过安装副本与生效值检查"
fi

echo
if [ "$bad" -gt 0 ]; then echo "  [FAIL] 单元检查发现 $bad 项问题"; exit 1; fi
echo "  [ok] systemd 单元检查通过"
