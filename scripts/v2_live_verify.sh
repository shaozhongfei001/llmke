#!/bin/bash
# 待服务恢复的真机验证清单（T-A5/T-A6/D0/D6/D9 批跑；每条打 PASS/FAIL，全部只读查询）
set -u
G=http://127.0.0.1:18094
S=http://127.0.0.1:19532
Q="智造贷的单户最高授信额度是多少"
pass=0; fail=0
ck(){ if [ "$1" = "0" ]; then echo "[PASS] $2"; pass=$((pass+1)); else echo "[FAIL] $2"; fail=$((fail+1)); fi }

echo "== D6 A组（引擎直连，seeds）=="
curl -s -X POST $G/v2/graph/query -H 'Content-Type: application/json' \
  -d "{\"query\":\"$Q\",\"top_k\":3,\"seeds\":[\"ent:智造贷\"],\"enable_graph\":true}" > /tmp/lv-a.json
python3 -c "
import json;d=json.load(open('/tmp/lv-a.json'))
ok = d.get('executed_route')=='GRAPH' and d.get('trace',{}).get('graph_calls',0)>0 \
     and d.get('trace',{}).get('rerank_fallback') is False and d.get('trace',{}).get('facts_after_rerank',0)>0 \
     and '智造贷' in (d.get('trace',{}).get('seed_hits') or [])
print('A:', d.get('executed_route'), d.get('reason'), json.dumps(d.get('trace'),ensure_ascii=False)[:160]); exit(0 if ok else 1)"
ck $? "D6-A GRAPH+seed_hits+无兜底"

echo "== D6 B组（禁用图对照）=="
curl -s -X POST $G/v2/graph/query -H 'Content-Type: application/json' \
  -d "{\"query\":\"$Q\",\"top_k\":3,\"seeds\":[\"ent:智造贷\"],\"enable_graph\":false}" > /tmp/lv-b.json
python3 -c "
import json;d=json.load(open('/tmp/lv-b.json'))
ok = d.get('executed_route')=='DENSE_FALLBACK' and d.get('reason')=='GRAPH_DISABLED' \
     and d.get('trace',{}).get('graph_calls',0)==0
print('B:', d.get('executed_route'), d.get('reason')); exit(0 if ok else 1)"
ck $? "D6-B DENSE_FALLBACK+GRAPH_DISABLED"

echo "== D0 视图端点 =="
curl -s $G/v2/graph/view > /tmp/lv-view.json
python3 -c "
import json;d=json.load(open('/tmp/lv-view.json'))
ok = d.get('status')=='ok' and isinstance(d.get('nodes'),list) and isinstance(d.get('edges'),list)
print('view:', d.get('status'), 'nodes=', d.get('node_count'), 'edges=', d.get('edge_count')); exit(0 if ok else 1)"
ck $? "D0 /v2/graph/view 数据源"

echo "== D9 中文补丁 health =="
curl -s $G/health > /tmp/lv-h.json
python3 -c "
import json;d=json.load(open('/tmp/lv-h.json'))
ok = (d.get('cjk_compat') or {}).get('installed') is True
print('health.cjk_compat:', d.get('cjk_compat')); exit(0 if ok else 1)"
ck $? "D9 health.cjk_compat.installed=true"

echo "== shim 分层（global 未命中=200+reason，不 501）=="
curl -s -X POST $S/retrieval_documents_global -H 'Content-Type: application/json' \
  -d '{"query":"一个不存在的问句xyz","query_mode":"global","summary_top_k":5}' > /tmp/lv-g.json
python3 -c "
import json;d=json.load(open('/tmp/lv-g.json'))
code=d.get('code'); reason=(d.get('data') or {}).get('reason')
ok = code==200 and reason in ('NO_RELEVANT_FACTS','NO_COMMUNITIES')
print('global:', code, reason); exit(0 if ok else 1)"
ck $? "shim global 未命中 200+reason"

echo "== 汇总 =="; echo "PASS=$pass FAIL=$fail"
[ "$fail" = "0" ] || exit 1
