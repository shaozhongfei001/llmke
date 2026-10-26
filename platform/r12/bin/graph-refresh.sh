#!/usr/bin/env bash
# R13 图谱刷新：文档变更后重算三元组与社区摘要（GraphRAG 一致性）
#
# 为什么需要它：
#   社区摘要里记录的是"当时的 file_id"。文档重新上传会产生新 file_id，
#   旧 id 失效 -> global 引用能显示"社区摘要"，但点不开原文（source 为空）。
#   因此文档增删改后必须刷新图谱，保证 引用->原文 仍然可打开。
#
# 用法: graph-refresh.sh <kbId> [primitiveName]
#   例: graph-refresh.sh 9 kb_9
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KB_ID="${1:?用法: graph-refresh.sh <kbId> [primitiveName]}"
KB_NAME="${2:-kb_$KB_ID}"
GATEWAY="${GATEWAY:-http://127.0.0.1:8088}"
GRAPH="${GRAPH:-http://127.0.0.1:19529}"
LLM_URL="${LLM_URL:-http://127.0.0.1:18092/v1/chat/completions}"
LLM_KEY="${LLM_KEY:-sk-r12-local}"

ok()   { printf '  [ok] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1"; exit 1; }

# 1) 取该知识库下已解析完成的文件 id（直连 MySQL，避免依赖登录）
IDS=$(docker exec r12-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD:-R12r00t#2026local}" -N -e \
  "select group_concat(id order by id) from gienrag.knowledge_base_list where kb_id=${KB_ID} and status=3" 2>/dev/null | tr -d '\r')
[ -n "${IDS:-}" ] && [ "$IDS" != "NULL" ] || die "kb ${KB_ID} 下没有已解析文件"
ok "待刷新文件: $IDS"

# 2) 重新抽三元组（走 Java 的图解析入口，复用其任务与鉴权）
TOKEN=$(python3 - "$GATEWAY" <<'PY'
import json, sys, urllib.request
base = sys.argv[1]
# 用 simpleLogin 拿 admin token；密码走与测试脚本一致的 AES 零填充
sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import login
print(login()[1])
PY
) || die "登录失败，无法触发图解析"
[ -n "${TOKEN:-}" ] || die "空 token"

curl -sS -X POST "$GATEWAY/index/knowledgeBase/file/graphParse" \
  -H "Authorization: $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"knowledge_base_id\":${KB_ID},\"file_ids\":[\"$(echo "$IDS" | tr ',' '","')\"]}" \
  --max-time 120 | head -c 200; echo
ok "已提交图解析（异步，等待 60-180s）"

sleep 90

# 3) 重建社区摘要（先清旧摘要，避免新旧混杂）
curl -sS -X DELETE "http://127.0.0.1:19200/community_summary_${KB_NAME}" -m 20 >/dev/null 2>&1
R=$(curl -sS -X POST "$GRAPH/generate_community" -H 'Content-Type: application/json' \
  -d "{\"space_name\":\"${KB_NAME}\",\"max_level\":2,\"min_community_size\":3,\"resolution\":1.0,\"with_summary\":true,\"model_info\":{\"model_id\":\"qwen2.5-7b-instruct\",\"url\":\"${LLM_URL}\",\"key\":\"${LLM_KEY}\"}}" \
  --max-time 900)
echo "  $R" | head -c 300; echo
echo "$R" | grep -q '"code":200' && ok "社区摘要已重建" || die "社区重建失败"
