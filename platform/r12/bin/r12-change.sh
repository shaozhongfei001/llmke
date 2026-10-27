#!/usr/bin/env bash
# R14：服务的"带原因变更"入口（手工操作也必须走它）
#
# 为什么需要（今天两次整栈中断，排查花了 20+ 分钟）：
#   13:22 与 13:39 各有一次业务层全断，日志里只有 `Failed with result 'signal'`，
#   谁也说不清"谁在什么时候停了什么"。最后靠比对另一个项目 dkws-skill 的 unit 记录，
#   才判定是**外部按 unit 列表批量 stop/restart**，不是我们任何人。
#
# 约定：
#   * 手工启停 r12 服务**一律走本脚本**，不要直接 systemctl / r12ctl；
#   * 不传原因时脚本会**拒绝执行**（`--force` 才放行，并记为 "NO-REASON"）——
#     因为无原因的变更正是最难排查的那种；
#   * 每条都写 platform/r12/logs/changes.log：
#     时间 / 用户 / 原因 / 动作 / 目标 / 调用方进程链 / 结果
#
# 用法：
#   r12-change.sh <start|stop|restart|status> <服务|all> <原因...>
#   r12-change.sh restart rag-index-service "加载 C 的 new-index5.jar，F 基线需要"
#   r12-change.sh --tail            # 看最近 20 条变更
#
# 目标只接受**明确的服务名或 all**；禁止用进程名/宽泛串（pkill/killall）。
# 需要清理某端口的残留进程时用配套脚本（同样是"先打印 ps、再杀"）：
#   r12-kill-port.sh <端口> [--yes] [--signal TERM|KILL] [--with-children]
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHANGES="$R12/logs/changes.log"

if [[ "${1:-}" == "--tail" ]]; then
  [[ -f "$CHANGES" ]] || { echo "（暂无变更记录：$CHANGES）"; exit 0; }
  echo "== 最近 20 条变更（时间 | 用户 | 原因 | 动作 | 目标 | 调用链）=="
  tail -20 "$CHANGES" | awk -F'\t' '{printf "  %s | %s | %s | %s %s | %s\n", $1, $2, $3, $4, $5, $6}'
  exit 0
fi

ACTION="${1:-}"; TARGET="${2:-}"; shift 2 2>/dev/null || true
# TL 硬规矩：禁止 pkill/pkill -f 宽泛串/killall；目标必须是**明确的服务名或 all**。
# 不认识的"目标"（例如 `python`、`java`、`rag-*`）一律拒绝——那类宽泛匹配今天已经
# 把另一个项目（dkws-skill）和我们自己的 docparse 在同一秒杀掉两次。
KNOWN_SVC="rag-auth-service rag-index-service rag-qa-service sensitive-words-service rag-gateway rag-graph-service all"
REASON="$*"
FORCE=0
[[ "$REASON" == *"--force"* ]] && { FORCE=1; REASON="${REASON//--force/}"; }

case "$ACTION" in
  start|stop|restart|status) ;;
  *) echo "用法: $0 <start|stop|restart|status> <服务|all> <原因…>   （--tail 查看记录）"; exit 2 ;;
esac
[ -n "$TARGET" ] || { echo "[FAIL] 必须指定目标服务（或 all）"; exit 2; }
if ! echo " $KNOWN_SVC " | grep -q " $TARGET "; then
  echo "[FAIL] 目标 '$TARGET' 不是明确的 r12 服务名。"
  echo "       允许: $KNOWN_SVC"
  echo "       按进程名/宽泛串清理被禁止（pkill/killall 会波及其它项目）。"
  echo "       要清理某个端口的残留进程，用: bin/r12-kill-port.sh <端口> [--yes]（会先打印 ps 再杀）"
  exit 2
fi

if [ -z "${REASON// }" ]; then
  if [ "$FORCE" != "1" ]; then
    echo "[FAIL] 必须给出变更原因（这是 R14 纪律：无原因变更最难排查）"
    echo "       例: $0 $ACTION $TARGET \"加载新 jar，F 基线需要\""
    echo "       确实无法说明时用 --force（会被记为 NO-REASON）"
    exit 2
  fi
  REASON="NO-REASON(--force)"
fi

echo "== r12-change: $ACTION $TARGET =="
printf '  原因: %s\n' "$REASON"

# 交给 r12ctl 执行；原因通过环境变量传入，由其统一写 changes.log（含调用方进程链）
R12_CHANGE_REASON="$REASON" bash "$R12/bin/r12ctl.sh" "$ACTION" "$TARGET"
rc=$?

# 追加一条结果行（r12ctl 只记"即将执行"，这里补 rc，便于事后判断是否真的成功）
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$(date -Is)" "${USER:-$(id -un)}" "$REASON" "${ACTION}(result)" "$TARGET" "-" "rc=$rc" >> "$CHANGES"
printf '  已记录到 %s（rc=%s）\n' "$CHANGES" "$rc"
exit "$rc"
