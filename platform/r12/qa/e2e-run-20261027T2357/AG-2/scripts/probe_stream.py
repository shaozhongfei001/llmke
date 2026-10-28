import sys, json, urllib.parse, os
sys.path.insert(0,"/home/szf/data/dev/llmke-r12/platform/r12/qa")
import requests
from r12_client import login
FE="http://127.0.0.1:18088"; GW="http://127.0.0.1:8088"
s, token, _ = login()
H={"Authorization": token, "X-Platform": "rag-qa", "userName": "admin", "userId": "1", "appKey": "rag-qa"}
keys = {
 "docx-plain":"r12-rag/kb_9/docx-plain.docx/V0/docx-plain.docx",
 "docx-table":"r12-rag/kb_9/docx-table.docx/V0/docx-table.docx",
 "pptx-V1":"r12-rag/kb_9/R12FIX-product-intro.pptx/V1/R12FIX-product-intro(1).pptx",
 "pptx-V0":"r12-rag/kb_9/R12FIX-product-intro.pptx/V0/R12FIX-product-intro.pptx",
 "loan-V1":"r12-rag/kb_9/R12FIX-product-loan.docx/V1/R12FIX-product-loan(1).docx",
 "pdf-digital":"r12-rag/kb_9/pdf-digital.pdf/V0/pdf-digital.pdf",
 "xlsx-md":"r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/parsed/R12FIX-credit-ledger.xlsx.md",
}
base=FE+"/proxy/index/knowledgeBase/file"
os.makedirs("AG-2/evidence/converted", exist_ok=True)
for name,k in keys.items():
    for pname in ["convertedFilePath"]:
        u=f"{base}/previewStream?{pname}={urllib.parse.quote(k, safe='')}"
        try:
            r=requests.get(u, headers=H, timeout=180)
        except Exception as e:
            print(name,"previewStream EXC",e); continue
        print(f"{name:12s} previewStream -> {r.status_code} ct={r.headers.get('Content-Type')} bytes={len(r.content)} magic={r.content[:8].hex()}")
        if r.content[:4]==b"%PDF":
            p=f"AG-2/evidence/converted/{name}.pdf"; open(p,"wb").write(r.content)
            import fitz; d=fitz.open(p); print("      pages=",d.page_count, "textlen=",[len(pg.get_text().strip()) for pg in d])
            txt=" ".join(pg.get_text() for pg in d)
            print("      text[:200]=",repr(txt[:200]))
        elif r.status_code!=200:
            print("      body:", r.text[:200])
    # stream 端点（xlsx md 走这个）
    u=f"{base}/stream?convertedFilePath={urllib.parse.quote(k, safe='')}"
    r=requests.get(u, headers=H, timeout=120)
    print(f"{name:12s} stream         -> {r.status_code} bytes={len(r.content)} magic={r.content[:8].hex()} body[:80]={r.content[:80]!r}")
