#!/usr/bin/env python3
"""引用"可回指"的第一段断言：source 形态 + presign 200 + 用签名 URL 取回 200。

第二段（依据正确）由 verify_global_citations.py 负责：数值 → 社区 id → Nebula 三元组。
两段都过才算"引用可回指"；只做本脚本会掩盖"引对了文件、引错了块"。

判据（C 提供）：
  · source 匹配 ^r12-rag/…            —— FIX-19 已加载后的规范形态
  · presign(key=source) == 200        —— 服务端有存在性校验，200 等价于"对象真实存在 + 有读权限"；
                                         不存在时返回 404 {"errorCode":"10002"}
  · 用返回的签名 URL GET == 200      —— 真正能取到字节

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/verify_source_presign.py "问题" [--mode global|local]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import GATEWAY, UA, api, login  # noqa: E402

EVID = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
KEY_RE = re.compile(r"^r12-rag/kb_[^/]+/.+")
PRESIGN_PATHS = ["/index/knowledgeBase/file/presign",
                 "/knowledgeBase/file/presign"]


def _ask(s, token, query, mode):
    """/qa 要完整 payload（sessionId/queryId/type/sysType）且是 SSE 流；
    直接复用探针的 ask()，避免自己拼错参数（我已踩过一次 400）。
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from r14_b_probe import ask as probe_ask  # noqa: E402
    s.token = token
    res = probe_ask(s, query, config_id=1, global_mode=(mode == "global"))
    return res.get("http"), {"documents_list": res.get("refs") or [],
                             "answer": res.get("answer") or ""}


VER_RE = re.compile(r"/V(\d+)/")


def _effective_version_ok(src):
    """第三维：**版本正确性**。source 指向的 /Vn/ 是否就是当前有效版本。

    关键：不能按 title 查！同文件不同版本 title 不同
    （V0 = R12FIX-product-loan.docx，V1 = R12FIX-product-loan(1).docx），
    按 title 查只会找到自己那一代，永远判 PASS。用**对象键去掉版本段**归一后比对。
    """
    m = VER_RE.search(src or "")
    if not m:
        return None, None, False
    ref_ver = int(m.group(1))
    # 归一到"版本目录"这一层：V0/V1 的文件名可能不同
    # （R12FIX-product-loan.docx vs R12FIX-product-loan(1).docx），
    # 所以只能用 `/V<n>/` **之前**的路径前缀当同一文件标识。
    base = src.split("/V", 1)[0]
    best = -1
    try:
        r = requests.post("http://127.0.0.1:19200/kb_9/_search",
                          json={"query": {"match_all": {}}, "size": 2000}, timeout=60)
        for h in r.json().get("hits", {}).get("hits", []):
            md = (h.get("_source") or {}).get("metadata") or {}
            other = md.get("source")
            if not other or other.split("/V", 1)[0] != base:
                continue
            mv = re.fullmatch(r"[Vv](\d+)", str(md.get("version") or ""))
            if mv:
                best = max(best, int(mv.group(1)))
    except Exception:
        return ref_ver, None, False
    return ref_ver, best, (best >= 0 and ref_ver >= best)


def _presign(s, token, key):
    last = None
    for p in PRESIGN_PATHS:
        for base in (GATEWAY, "http://127.0.0.1:18082"):
            try:
                r = s.get(f"{base}{p}", params={"key": key},
                          headers={"Authorization": token, "User-Agent": UA}, timeout=30)
                last = (base + p, r.status_code, (r.text or "")[:200])
                if r.status_code == 200:
                    try:
                        return True, r.json(), last
                    except Exception:
                        return True, {"raw": r.text[:300]}, last
            except Exception as e:
                last = (base + p, "EXC", str(e)[:120])
    return False, {}, last


def _url_from(body):
    for k in ("data", "url", "presignedUrl", "presigned_url"):
        v = body.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
        if isinstance(v, dict):
            for kk in ("url", "presignedUrl"):
                if isinstance(v.get(kk), str) and v[kk].startswith("http"):
                    return v[kk]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--mode", default="global", choices=["global", "local"])
    a = ap.parse_args()

    s, token, _ = login()
    code, body = _ask(s, token, a.query, a.mode)
    # _ask 返回的是 {"documents_list": [...], "answer": ...}，不要再往 data 里找一层
    refs = (body.get("documents_list") or (body.get("data") or {}).get("documents_list") or [])
    print(f"[qa] http={code} refs={len(refs)}")

    results = []
    for i, d in enumerate(refs):
        md = d.get("metadata") or {}
        src = md.get("source")
        rec = {"i": i, "source": src, "community_id": md.get("community_id")}
        rec["form_ok"] = bool(src and KEY_RE.match(str(src)))
        if rec["form_ok"]:
            ref_ver, eff_ver, v_ok = _effective_version_ok(str(src))
            rec["ref_version"], rec["effective_version"], rec["version_ok"] = ref_ver, eff_ver, v_ok
        if rec["form_ok"]:
            ok, pbody, last = _presign(s, token, src)
            rec["presign_ok"] = ok
            rec["presign_trace"] = last
            url = _url_from(pbody) if ok else None
            rec["presigned_url"] = bool(url)
            if url:
                try:
                    g = requests.get(url, timeout=30)
                    rec["get_status"] = g.status_code
                    rec["bytes"] = len(g.content)
                except Exception as e:
                    rec["get_status"] = "EXC"
                    rec["get_err"] = str(e)[:120]
        results.append(rec)
        print("  ", json.dumps({k: rec.get(k) for k in
                                ("i", "form_ok", "presign_ok", "presigned_url", "get_status", "bytes")},
                               ensure_ascii=False), "|", (src or "")[-50:])

    ok_transport = all(r.get("form_ok") and r.get("presign_ok") and r.get("get_status") == 200
                       for r in results) and bool(results)
    ok_version = bool(results) and all(r.get("version_ok") for r in results)
    ok_all = ok_transport and ok_version
    print(f"\n[结论] {'PASS' if ok_all else 'FAIL'}")
    print(f"  ① 传输正确（形态+presign+取回）：{'PASS' if ok_transport else 'FAIL'}"
          f"  {sum(1 for r in results if r.get('get_status') == 200)}/{len(results)}")
    print(f"  ② 版本正确（source 的 /Vn/ == 当前有效版本）：{'PASS' if ok_version else 'FAIL'}")
    for r in results:
        if not r.get("version_ok"):
            print(f"     - 引用落在 V{r.get('ref_version')}，有效版本 V{r.get('effective_version')}"
                  f"  {str(r.get('source'))[-40:]}")
    if not ok_all:
        print("[提示] 第二段（数值→社区→三元组回指）请看 verify_global_citations.py，两者都过才算可回指")

    os.makedirs(EVID, exist_ok=True)
    out = os.path.join(EVID, "R14-B-source-presign-"
                       f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"query": a.query, "mode": a.mode, "http": code,
                   "refs": results, "ok": ok_all}, f, ensure_ascii=False, indent=1)
    print("[evidence]", out)


if __name__ == "__main__":
    main()
