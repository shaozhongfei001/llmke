#!/usr/bin/env bash
# R13 恢复脚本：清理僵死的解析任务，避免"文件永远停在 99"。
# 用法: recover-stuck-tasks.sh [分钟数，默认10]
# 语义（依 file_parse_task.status 实测）：
#   1 = 待处理 / 2 = 失败 / 3 = ? / 4 = 完成 / 5 = 处理中（僵死占用并发槽）
set -uo pipefail
MINS="${1:-10}"
MYSQL=(docker exec r12-mysql mysql -uroot -pR12r00t#2026local -N -e)

echo "== 清理超过 ${MINS} 分钟仍处于处理中(5)的任务 =="
"${MYSQL[@]}" "update gienrag.file_parse_task set status=2 where status=5 and gmt_modified < now() - interval ${MINS} minute" 2>/dev/null
"${MYSQL[@]}" "select status,count(*) from gienrag.file_parse_task group by status" 2>/dev/null | sed 's/^/  task status /'

echo "== 把卡在 99 的文件状态归零（允许重新派发）=="
"${MYSQL[@]}" "update gienrag.knowledge_base_list set status=1 where status=99 and gmt_modified < now() - interval ${MINS} minute" 2>/dev/null
"${MYSQL[@]}" "select status,count(*) from gienrag.knowledge_base_list group by status" 2>/dev/null | sed 's/^/  file status /'

echo "== 触发知识库重解析（kbId 需传入）=="
if [[ -n "${2:-}" ]]; then
  TOKEN=$(cd /home/szf/data/dev/llmke-r12 && python3 -c "
import sys; sys.path.insert(0,'platform/r12/qa')
from r12_client import login
print(login()[1])")
  curl -sS -X POST "http://127.0.0.1:8088/index/knowledgeBase/file/filesAllParse?kbId=$2" \
    -H "Authorization: $TOKEN" -H "X-Platform: rag-qa" -o /dev/null -w "  filesAllParse kbId=$2 -> %{http_code}\n"
fi
