#!/usr/bin/env bash
# R14-F07：单节点 ES 副本治理（幂等）
#
# 问题：r12 的 ES 是单 data node（docker-compose.infra.yml 只跑一个 es），但索引默认
# number_of_replicas=1，副本永远无法分配 -> 27 个 unassigned replica -> 集群长期 yellow。
# 这不是数据故障，也不该靠"忽略 yellow"来糊过去：单节点上副本没有任何 HA 价值。
#
# 处置（两条一起做，才既修现状又防新增）：
#   1) 既有索引：PUT _all/_settings -> number_of_replicas=0
#   2) 新建索引：composable index template（覆盖 r12 的业务索引前缀）默认 0 副本
#      - priority=201：避开与本镜像自带的 .monitoring-* / .fleet-* 模板（priority 200）同优先级冲突
#      - 不用前导通配（*-chunks-* 之类）：ES 会对前导 * 做保守重叠判断，导致模板注册被拒
#   3) 断言：/_cluster/health 必须 green 且 unassigned_shards=0，否则非零退出（不静默）
#
# 用法: es-single-node.sh [es_url]   （默认 http://127.0.0.1:19200）
set -uo pipefail
ES="${1:-http://127.0.0.1:19200}"
ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1"; exit 1; }

curl -fsS -m 5 "$ES/_cluster/health" >/dev/null 2>&1 || die "ES 不可达: $ES"

before="$(curl -fsS -m 5 "$ES/_cluster/health?filter_path=status,unassigned_shards" 2>/dev/null)"
printf '  [..] 处置前: %s\n' "$before"

curl -fsS -m 10 -XPUT "$ES/_all/_settings?expand_wildcards=open" \
  -H 'Content-Type: application/json' \
  -d '{"index":{"number_of_replicas":0}}' >/dev/null \
  && ok "既有索引 number_of_replicas=0" || warn "既有索引副本调整失败（可能无索引）"

curl -fsS -m 10 -XPUT "$ES/_index_template/r12-single-node-default" \
  -H 'Content-Type: application/json' -d '{
  "index_patterns": ["kb_*","table_chunks_*","table_summary_*","faq_*","community_summary_*","r12_*"],
  "priority": 201,
  "template": {"settings": {"index": {"number_of_replicas": 0}}},
  "_meta": {"why": "单节点 ES，副本无法分配->集群常黄；单节点副本无 HA 价值，新索引默认 0 副本"}
}' >/dev/null && ok "模板 r12-single-node-default 已注册（新索引默认 0 副本）" || warn "模板注册失败"

# 等分配收敛再断言
for _ in $(seq 1 20); do
  st="$(curl -fsS -m 5 "$ES/_cluster/health?filter_path=status,unassigned_shards" 2>/dev/null)"
  echo "$st" | grep -q '"status":"green"' && break
  sleep 2
done
st="$(curl -fsS -m 5 "$ES/_cluster/health?filter_path=status,unassigned_shards")"
printf '  [..] 处置后: %s\n' "$st"
echo "$st" | grep -q '"status":"green"' || die "集群仍非 green（见上）"
ok "ES 单节点副本治理完成：green / unassigned_shards=0"
