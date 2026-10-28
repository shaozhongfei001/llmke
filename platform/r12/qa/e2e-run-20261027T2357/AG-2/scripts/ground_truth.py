import json, sys, os, hashlib, urllib.parse
sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
import requests
from r12_client import login

BASE = "/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2"
OUT = BASE + "/evidence/ground-truth"
os.makedirs(OUT, exist_ok=True)
FE = "http://127.0.0.1:18088"
GW = "http://127.0.0.1:8088"

s, token, _ = login()
files = json.load(open(BASE + "/evidence/kb9-files-raw.json"))["data"]["records"]
keys = {}
for r in files:
    for f in ("convertedFilePath", "filePath"):
        v = r.get(f)
        if not v: continue
        k = v.split("://", 1)[-1]
        k = k.split("/", 1)[1] if "/" in k else k
        keys.setdefault(r["id"], {})[f] = k

report = {}
for fid, ks in keys.items():
    fname = next(r["fileName"] for r in files if r["id"] == fid)
    for field, key in ks.items():
        # presign 走前端 nginx proxy（与浏览器同路径）
        url = f"{FE}/proxy/index/knowledgeBase/file/presign?key={urllib.parse.quote(key, safe='')}"
        rr = requests.get(url, headers={"Authorization": token}, timeout=60)
        entry = {"file": fname, "field": field, "key": key, "presign_status": rr.status_code}
        try:
            b = rr.json(); entry["presign_body"] = {k: b.get(k) for k in ("success","errorCode","errorMsg")}
            purl = (b.get("url") or (b.get("data") or {}).get("url"))
        except Exception:
            purl = None; entry["presign_body"] = rr.text[:200]
        if purl:
            g = requests.get(purl, timeout=120)
            entry["get_status"] = g.status_code
            entry["bytes"] = len(g.content)
            ext = os.path.splitext(key)[1] or ".bin"
            safe = f"{fid}-{field}{ext}"
            open(os.path.join(OUT, safe), "wb").write(g.content)
            entry["saved"] = safe
            entry["sha256"] = hashlib.sha256(g.content).hexdigest()[:16]
            entry["magic"] = g.content[:8].hex()
        report[f"{fid}/{field}"] = entry
        print(json.dumps(entry, ensure_ascii=False))

json.dump(report, open(BASE + "/evidence/presign-report.json", "w"), ensure_ascii=False, indent=1)
