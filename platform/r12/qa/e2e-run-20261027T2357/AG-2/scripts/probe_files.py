import json, sys
sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import login, api
OUT="/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2/evidence"
s, token, _ = login()
q = "/index/knowledgeBase/file/folder/list?fileListType=1&kbId=9&folderId=0&pageNo=1&pageSize=200"
code, j = api(s, "GET", q, token)
print("HTTP", code, "success=", j.get("success"))
d = j.get("data") or {}
recs = d.get("records") or []
print("total", d.get("total"), "records", len(recs))
json.dump(j, open(f"{OUT}/kb9-files-raw.json","w"), ensure_ascii=False, indent=1)
keys = ["id","fileName","fileType","fileSize","status","convertedFilePath","filePath","pdfPage","permission","uploadTime","folderId"]
for r in recs:
    print(" | ".join(str(r.get(k)) for k in keys))
print("\nFIELDS:", sorted(recs[0].keys()) if recs else "none")
