import json, sys, os
sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import login, api

s, token, body = login()
print("LOGIN ok, user=", (body.get("data") or {}).get("userName"))
print("---- kb list ----")
code, j = api(s, "GET", "/index/knowledgeBase/list?pageNo=1&pageSize=50", token)
print(code)
rows = (j.get("data") or {}).get("rows") or (j.get("data") or {}).get("records") or []
for r in rows:
    print(r.get("knowledgeBaseId") or r.get("id"), "|", r.get("name") or r.get("kbName"), "|", r.get("documentCount"))
print("total=", len(rows))
open("/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2/evidence/kb-list.json","w").write(json.dumps(j, ensure_ascii=False, indent=1))
