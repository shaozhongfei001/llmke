"""只读取流探测：POST previewStream / stream，把转换后内容落盘，供后续解析。
零写入业务数据（仅 GET/POST 读取 + 写本角色 evidence 目录）。"""
import sys, json, os
sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
import requests
from r12_client import login

FE = "http://127.0.0.1:18088"
OUT = "/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2/evidence/converted"
os.makedirs(OUT, exist_ok=True)

s, token, b = login()
H = {"Authorization": token, "X-Platform": "rag-qa", "userName": "admin",
     "userId": "1", "Content-Type": "application/json"}

keys = {
    "docx-plain": "r12-rag/kb_9/docx-plain.docx/V0/docx-plain.docx",
    "docx-table": "r12-rag/kb_9/docx-table.docx/V0/docx-table.docx",
    "pptx-V1": "r12-rag/kb_9/R12FIX-product-intro.pptx/V1/R12FIX-product-intro(1).pptx",
    "pptx-V0": "r12-rag/kb_9/R12FIX-product-intro.pptx/V0/R12FIX-product-intro.pptx",
    "loan-V1": "r12-rag/kb_9/R12FIX-product-loan.docx/V1/R12FIX-product-loan(1).docx",
    "loan-V0": "r12-rag/kb_9/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx",
    "pdf-digital": "r12-rag/kb_9/pdf-digital.pdf/V0/pdf-digital.pdf",
    "pdf-scanned": "r12-rag/kb_9/pdf-scanned.pdf/V0/pdf-scanned.pdf",
    "xlsx-md": "r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/parsed/R12FIX-credit-ledger.xlsx.md",
    "xlsx-raw": "r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx",
}
base = FE + "/proxy/index/knowledgeBase/file"
summary = {}
for name, k in keys.items():
    for api in ["previewStream", "stream"]:
        try:
            r = requests.post(f"{base}/{api}", headers=H,
                              json={"convertedFilePath": k}, timeout=300)
        except Exception as e:
            print(f"{name:12s} {api:13s} EXC {e}")
            summary[f"{name}/{api}"] = {"error": str(e)}
            continue
        ct = r.headers.get("Content-Type")
        n = len(r.content)
        info = {"status": r.status_code, "ct": ct, "bytes": n, "magic": r.content[:8].hex()}
        print(f"{name:12s} {api:13s} -> {r.status_code} ct={ct} bytes={n}")
        if r.content[:4] == b"%PDF":
            p = os.path.join(OUT, f"{name}-{api}.pdf")
            open(p, "wb").write(r.content)
            info["saved"] = p
        elif ct and "json" in ct:
            info["body"] = r.text[:400]
            print("      body:", r.text[:300])
        else:
            p = os.path.join(OUT, f"{name}-{api}.bin")
            open(p, "wb").write(r.content)
            info["saved"] = p
            info["head"] = r.content[:200].decode("utf-8", "replace")
            print("      head:", info["head"][:200])
        summary[f"{name}/{api}"] = info
json.dump(summary, open(os.path.join(OUT, "..", "converted-summary.json"), "w"),
          ensure_ascii=False, indent=1)
print("done")
