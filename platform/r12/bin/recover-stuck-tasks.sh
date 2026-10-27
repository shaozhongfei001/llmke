#!/usr/bin/env bash
# R14：解析任务僵尸清理（幂等，可被看门狗每 5 分钟调用）
#
# ┌──────────────────────────────────────────────────────────────────────────┐
# │ file_parse_task.status 真实枚举（**与旧版脚本注释相反，是本轮事故根因**）      │
# │   -1 删除   1 待处理   2 处理中   3 重试中   4 成功   5 失败                │
# │                                                                          │
# │ 旧版脚本写的是：  1 待处理 / 2 失败 / 3 ? / 4 完成 / 5 处理中               │
# │ 并执行 `update ... set status=2 where status=5` —— 把**失败(5)** 改成        │
# │ **处理中(2)**：既不会被重试、又永久占着并发槽，等于"制造僵尸"。               │
# │ 依据：`ParseTaskStatusEnums.java` + TL 核实。                              │
# └──────────────────────────────────────────────────────────────────────────┘
#
# 语义（本版）：
#   2 处理中 + 超时   -> 1 待处理（重新排队）+ error_msg 写明"recover 判为僵尸"
#   3 重试中 + 超时   -> 5 失败    + error_msg
#   5 失败            -> **不改状态**（只统计；失败的语义就是失败）
#   knowledge_base_list.status=99（孤儿文件，队列已释放但文件仍挂解析中）
#                     -> 4 解析失败，避免用户界面上"永远在解析"
#   任何情况下**都不写 status=2**（那是"正在被执行"，脚本无法真正让它被执行）
#
# 用法：
#   recover-stuck-tasks.sh                # 默认：处理中/重试中 超时 10 分钟即清理
#   recover-stuck-tasks.sh --mins 30      # 自定义超时
#   recover-stuck-tasks.sh --dry-run      # 只报告不修改（评审/排障用）
#   recover-stuck-tasks.sh --check        # 只判是否有僵尸：有则 exit 1（看门狗/门禁用）
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MINS=10; DRY=0; CHECK=0
while [ $# -gt 0 ]; do case "$1" in
  --mins) MINS="${2:-10}"; shift 2 ;;
  --dry-run) DRY=1; shift ;;
  --check) CHECK=1; shift ;;
  -*) echo "未知参数: $1"; exit 2 ;;
  *) MINS="$1"; shift ;;
esac; done

CT="${R12_MYSQL_CONTAINER:-r12-mysql}"
DB="${R12_MYSQL_DB:-gienrag}"
ROOT_PW="${R12_MYSQL_ROOT_PASSWORD:-${MYSQL_ROOT_PASSWORD:-}}"
if [ -z "$ROOT_PW" ] && [ -f "$R12/.env" ]; then
  ROOT_PW="$(sed -n 's/^R12_MYSQL_ROOT_PASSWORD=//p' "$R12/.env" | head -1)"
fi
[ -n "$ROOT_PW" ] || { echo "[FAIL] 缺少 R12_MYSQL_ROOT_PASSWORD（见 $R12/.env）" >&2; exit 1; }

# 口令走 MYSQL_PWD：避免 `-pXXX` 出现在 ps 里（旧脚本用 -p 明文，同机可见）
q() { docker exec -e MYSQL_PWD="$ROOT_PW" "$CT" mysql -uroot -N -B --default-character-set=utf8mb4 "$DB" -e "$1" 2>&1; }

echo "== recover-stuck-tasks（db=$DB 超时=${MINS}min dry_run=$DRY check=$CHECK）=="

# 先回显"库里实际有哪些 status 值"（TL 要求）：
# 今天三个人先后读错这套枚举（旧脚本注释写 2=失败/5=处理中，真实是 2=处理中/5=失败），
# 所以脚本每次运行都先把真实值摊在屏幕上，任何人一眼能看出"我理解的枚举和库里的对不上"。
echo "  库里 file_parse_task.status 实际分布："
q "select status,count(*) from file_parse_task group by status order by status;" | sed 's/^/    /'
echo "  枚举对照：-1删除 1待处理 2处理中 3重试中 4成功 5失败（本脚本永不写 2）"

zombie_processing=$(q "select count(*) from file_parse_task where status=2 and coalesce(start_time, gmt_modified, gmt_create) < now() - interval ${MINS} minute;")
zombie_retrying=$(q "select count(*) from file_parse_task where status=3 and coalesce(start_time, gmt_modified, gmt_create) < now() - interval ${MINS} minute;")
orphan_files=$(q "select count(*) from knowledge_base_list where status=99 and coalesce(gmt_modified, gmt_create) < now() - interval ${MINS} minute;")
for v in "$zombie_processing" "$zombie_retrying" "$orphan_files"; do
  [[ "$v" =~ ^[0-9]+$ ]] || { echo "[FAIL] SQL 执行失败: $v" >&2; exit 1; }
done
printf '  处理中超时=%s  重试中超时=%s  文件挂99=%s\n' "$zombie_processing" "$zombie_retrying" "$orphan_files"

total=$(( zombie_processing + zombie_retrying + orphan_files ))
if [ "$CHECK" = "1" ]; then
  if [ "$total" -gt 0 ]; then echo "  [FAIL] 存在 $total 个僵尸/孤儿（--check）"; exit 1; fi
  echo "  [ok] 无僵尸"; exit 0
fi

if [ "$DRY" = "1" ]; then
  echo "  [..] dry-run：将执行 3 条 update（不写库）"
  q "select id,kb_id,file_id,status,start_time,left(coalesce(error_msg,''),40) from file_parse_task where status in (2,3) and coalesce(start_time, gmt_modified, gmt_create) < now() - interval ${MINS} minute limit 10;"
  exit 0
fi

ts="$(date '+%Y-%m-%d %H:%M:%S')"
# ① 处理中超时 -> 待处理（重新排队）
n1=$(q "update file_parse_task set status=1,
          error_msg=concat(coalesce(nullif(error_msg,''),''),' | recover: 处理中超时(>${MINS}min)判为僵尸，于 ${ts} 重置为待处理'),
          gmt_modified=now()
        where status=2 and coalesce(start_time, gmt_modified, gmt_create) < now() - interval ${MINS} minute;
        select row_count();" | tail -1)
# ② 重试中超时 -> 失败
n2=$(q "update file_parse_task set status=5,
          error_msg=concat(coalesce(nullif(error_msg,''),''),' | recover: 重试中超时(>${MINS}min)判为失败，于 ${ts}'),
          gmt_modified=now()
        where status=3 and coalesce(start_time, gmt_modified, gmt_create) < now() - interval ${MINS} minute;
        select row_count();" | tail -1)
# ③ 文件挂 99 -> 4 解析失败（队列释放 ≠ 文件状态释放）
n3=$(q "update knowledge_base_list set status=4, gmt_modified=now()
        where status=99 and coalesce(gmt_modified, gmt_create) < now() - interval ${MINS} minute;
        select row_count();" | tail -1)

printf '  已处理：处理中->待处理 %s 条；重试中->失败 %s 条；文件99->4 %s 条\n' "${n1:-0}" "${n2:-0}" "${n3:-0}"
echo "  任务状态分布："; q "select status,count(*) from file_parse_task group by status order by status;" | sed 's/^/    task /'
echo "  文件状态分布："; q "select status,count(*) from knowledge_base_list group by status order by status;" | sed 's/^/    file /'
echo "  [ok] 完成（从不写 status=2）"
