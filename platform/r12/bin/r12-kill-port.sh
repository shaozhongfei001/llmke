#!/usr/bin/env bash
# R14：**唯一的"按端口清理进程"入口**（禁止 pkill / killall / pkill -f 宽泛串）
#
# 为什么要出这个脚本（今天最贵的一课）：
#   13:23:22  r12-docparse.service: Failed with result 'signal'
#   13:23:22  dkws-skill.service:    Failed with result 'signal'    <- 另一个项目
#   13:39:43 / 13:41:50 又各有一次同样"同一秒两个不相关项目被杀"
#   两个不相关项目的服务在同一秒被信号杀死 => 不是定向 restart，是**宽泛匹配的 kill**
#   （`pkill -f python` / `pkill java` / `killall` 这类）。
#
# 全队硬规矩（TL 已下发）：
#   禁止：pkill -f python / pkill java / pkill -f <宽泛串> / killall
#   只允许三种：
#     ① 按本项目 unit：systemctl --user stop r12-java@rag-index-service
#     ② 按 pidfile 的明确 pid：kill -TERM $(cat platform/r12/run/xxx.pid)
#     ③ 按端口定位 pid：ss -ltnp | grep :18082 取 pid 后再杀      <- 本脚本
#   任何"清理残留"的动作，**先 ps -o pid,cmd 列出要杀的 pid，贴出来，再杀**。
#
# 本脚本强制做到"先显示、后执行"：
#   1) 用 ss 按端口取**监听者** pid（不猜、不按名字匹配）
#   2) 打印这些 pid 的 ps -o pid,ppid,etime,cmd，以及它们的**子进程**
#   3) 默认 dry-run；必须显式 --yes 才真杀
#   4) 只杀该端口的监听者与其子进程，绝不按进程名扩散
#   5) 全过程写 logs/changes.log
#
# 用法：
#   r12-kill-port.sh 18082                       # 只显示"要杀谁"（dry-run，默认）
#   r12-kill-port.sh 18082 --yes                 # 真杀（默认 SIGTERM，10s 后仍活才 SIGKILL）
#   r12-kill-port.sh 18082 --yes --signal KILL   # 直接 SIGKILL（仅用于 TERM 无效时）
#   r12-kill-port.sh 18082 --with-children --yes # 连同子进程一起（多 worker 服务）
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHANGES="$R12/logs/changes.log"

PORT="${1:-}"; shift 2>/dev/null || true
[[ "$PORT" =~ ^[0-9]+$ ]] || { echo "用法: $0 <端口> [--yes] [--signal TERM|KILL] [--with-children]"; exit 2; }
YES=0; SIG=TERM; WITH_CHILD=0
while [ $# -gt 0 ]; do case "$1" in
  --yes) YES=1; shift ;;
  --signal) SIG="${2:-TERM}"; shift 2 ;;
  --with-children) WITH_CHILD=1; shift ;;
  *) echo "未知参数: $1"; exit 2 ;;
esac; done
case "$SIG" in TERM|KILL|INT|QUIT) ;; *) echo "[FAIL] 不支持的信号: $SIG（只允许 TERM/KILL/INT/QUIT）"; exit 2 ;; esac

log_change() {
  mkdir -p "$(dirname "$CHANGES")"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -Is)" "${USER:-$(id -un)}" \
    "${R12_CHANGE_REASON:---kill-port :$PORT}" "$1" "port:$PORT" "r12-kill-port.sh" "${2:-}" >> "$CHANGES"
}

# ① 只按端口取监听者，不做任何名字匹配
mapfile -t PIDS < <(ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u)
if [ "${#PIDS[@]}" -eq 0 ]; then
  echo "[ok] 端口 $PORT 当前无监听者，无需处理"; exit 0
fi

echo "== r12-kill-port :$PORT（信号 $SIG${YES:+}）=="
echo "-- 监听者（来自 ss -ltnp，非名字匹配）--"
ps -o pid,ppid,user,etime,cmd -p "$(IFS=,; echo "${PIDS[*]}")" 2>/dev/null | sed 's/^/   /'

# ② 子进程：多 worker 服务（docparse/graphsvc）只杀父进程会留 worker
KIDS=()
if [ "$WITH_CHILD" = "1" ]; then
  for p in "${PIDS[@]}"; do
    mapfile -t k < <(pgrep -P "$p" 2>/dev/null)
    KIDS+=("${k[@]}")
  done
  if [ "${#KIDS[@]}" -gt 0 ]; then
    echo "-- 子进程（--with-children）--"
    ps -o pid,ppid,user,etime,cmd -p "$(IFS=,; echo "${KIDS[*]}")" 2>/dev/null | sed 's/^/   /'
  fi
fi

echo "-- 将发送 SIG$SIG 给: ${PIDS[*]}${KIDS[*]:+ 以及子进程 ${KIDS[*]}} --"
if [ "$YES" != "1" ]; then
  echo "  [dry-run] 未执行。确认上面这些 pid 确实是你要清理的，再加 --yes"
  echo "            （不要改用 pkill/killall —— 那会把别的项目一起杀掉，今天已发生两次）"
  exit 0
fi

log_change "kill-port($SIG)" "targets=${PIDS[*]}${KIDS[*]:+ kids=${KIDS[*]}}"
for p in "${PIDS[@]}"; do kill -"$SIG" "$p" 2>/dev/null; done
for p in "${KIDS[@]:-}"; do [ -n "$p" ] && kill -"$SIG" "$p" 2>/dev/null; done

if [ "$SIG" = "TERM" ]; then
  for _ in $(seq 1 10); do
    [ -z "$(ss -ltnpH "sport = :$PORT" 2>/dev/null)" ] && break
    sleep 1
  done
  left="$(ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u | paste -sd, -)"
  if [ -n "$left" ]; then
    echo "  [..] SIGTERM 10s 内未释放端口，升级 SIGKILL: $left"
    for p in ${left//,/ }; do kill -9 "$p" 2>/dev/null; done
    log_change "kill-port(KILL)" "targets=$left reason=TERM超时"
    sleep 2
  fi
fi

left="$(ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u | paste -sd, -)"
if [ -z "$left" ]; then echo "  [ok] 端口 $PORT 已释放"; else echo "  [FAIL] 端口 $PORT 仍被 $left 持有"; exit 1; fi
