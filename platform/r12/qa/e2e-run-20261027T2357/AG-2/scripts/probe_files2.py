import json, sys
sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import login, api
s, token, _ = login()
for q in [
 "/index/knowledgeBase/file/folder/list?fileListType=1&kbId=9&pageNo=1&pageSize=200",
 "/index/knowledgeBase/file/folder/list?fileListType=1&kbId=9&folderId=&pageNo=1&pageSize=200",
 "/index/knowledgeBase/file/list?kbId=9&pageNo=1&pageSize=200",
]:
    code, j = api(s, "GET", q, token)
    d = (j.get("data") or {}) if isinstance(j, dict) else {}
    recs = d.get("records") or []
    print(q, "->", code, "total=", d.get("total"), "recs=", len(recs))
    if recs:
        json.dump(j, open("/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2/evidence/kb9-files-raw.json","w"), ensure_ascii=False, indent=1)
        for r in recs:
            print("   ", r.get("id"), "|", r.get("fileName"), "|", r.get("fileType"), "|", r.get("fileSize"), "| st=", r.get("status"), "| page=", r.get("pdfPage"))
            print("      convertedFilePath=", r.get("convertedFilePath"))
            print("      filePath=", r.get("filePath"))
        print("FIELDS:", sorted(recs[0].keys()))
        break
