"""只读探测 presign 的失败语义（不写任何数据）。"""
import sys, json
sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
import requests, urllib.parse
from r12_client import login

FE = "http://127.0.0.1:18088"
s, token, _ = login()
H = {"Authorization": token, "X-Platform": "rag-qa", "userName": "admin", "userId": "1"}

cases = {
    "A_存在(kb_9 pdf)": "r12-rag/kb_9/pdf-digital.pdf/V0/pdf-digital.pdf",
    "B_不存在文件(kb_9)": "r12-rag/kb_9/not-exist-file.pdf/V0/not-exist-file.pdf",
    "C_不存在版本": "r12-rag/kb_9/pdf-digital.pdf/V9/pdf-digital.pdf",
    "D_他人夹具kb_22": "r12-rag/kb_22/R12FIX-loan.docx/V0/R12FIX-loan.docx",
    "E_越权kb_999": "r12-rag/kb_999/x.pdf/V0/x.pdf",
    "F_minio前缀": "minio/r12-rag/kb_9/pdf-digital.pdf/V0/pdf-digital.pdf",
    "G_空key": "",
    "H_路径穿越": "r12-rag/kb_9/../../../etc/passwd",
    "I_非r12前缀": "other-bucket/kb_9/pdf-digital.pdf/V0/pdf-digital.pdf",
}
out = {}
for name, key in cases.items():
    url = f"{FE}/proxy/index/knowledgeBase/file/presign?key={urllib.parse.quote(key, safe='')}"
    try:
        r = requests.get(url, headers=H, timeout=60)
        try:
            b = r.json()
        except Exception:
            b = {"raw": r.text[:200]}
        rec = {"key": key, "http": r.status_code,
               "success": b.get("success"), "errorCode": b.get("errorCode"),
               "errorMsg": b.get("errorMsg"),
               "has_url": bool(b.get("url") or (b.get("data") or {}).get("url")),
               "data_type": type(b.get("data")).__name__ if "data" in b else None}
    except Exception as e:
        rec = {"key": key, "exc": str(e)}
    out[name] = rec
    print(json.dumps({name: rec}, ensure_ascii=False))

json.dump(out, open("/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2/evidence/presign-failcases.json", "w"),
          ensure_ascii=False, indent=1)
