#!/usr/bin/env python3
"""R13 能力矩阵自检（TL 集成用）。

只做"能力是否真实可用"的端到端探针，不替代 acceptance.py（主链）与
security_acceptance.py（对象授权负例）。每个探针都打印可复核的原始证据片段。

用法:
  python3 platform/r12/qa/r13_full_check.py            # 全部
  python3 platform/r12/qa/r13_full_check.py --only FAQ,GLOBAL
"""
import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r12_client import GATEWAY, UA, api, login  # noqa: E402

import requests  # noqa: E402

R12 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVID = os.path.join(R12, "qa", "evidence", "CAPS-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
RESULTS = []

# 默认助手：普通 RAG（config 1）；FAQ 助手 config 9；global 用请求级开关，不依赖 config
CFG_DEFAULT = 1
CFG_FAQ = 9
KB_ID = 9
KB_NAME = "kb_9"


def record(cap, ok, detail, extra=None):
    RESULTS.append({"cap": cap, "ok": bool(ok), "detail": detail})
    print(f"{'PASS' if ok else 'FAIL'} [{cap}] {detail}")
    if extra:
        try:
            os.makedirs(EVID, exist_ok=True)
            with open(os.path.join(EVID, cap.replace("/", "_") + ".json"), "w", encoding="utf-8") as f:
                json.dump(extra, f, ensure_ascii=False, indent=1)
        except Exception:
            pass


def ask(s, content, config_id=CFG_DEFAULT, global_mode=False, timeout=240):
    """发一问，返回 (http, status, answer, reference_list, resultType)。"""
    payload = {"sessionId": f"cap-{int(time.time()*1000)}", "queryId": f"q-{int(time.time()*1000)}",
               "content": content, "type": "text", "sysType": "KNO_INDEX", "configId": config_id}
    if global_mode:
        payload["globalMode"] = True
    r = requests.post(
        GATEWAY + "/qa/ai/question", json=payload,
        headers={"Authorization": s.token, "Accept": "text/event-stream",
                 "Content-Type": "application/json", "User-Agent": UA},
        stream=True, timeout=timeout)
    answer, ref, rt, status = "", [], None, None
    buf = b""
    for line in r.iter_lines():
        if not line:
            continue
        buf += line + b"\n"
    txt = buf.decode("utf-8", "replace")
    for part in txt.split("data:"):
        part = part.strip()
        if not part:
            continue
        try:
            o = json.loads(part)
        except Exception:
            continue
        c = (o.get("reply") or {}).get("content") or ""
        if c:
            answer = c
        if o.get("status") is not None:
            status = o["status"]
        if o.get("resultType") is not None:
            rt = o["resultType"]
        v = o.get("reference")
        if v:
            try:
                d = json.loads(v) if isinstance(v, str) else v
                raw = d.get("documents") if isinstance(d, dict) else d
                lst = json.loads(raw) if isinstance(raw, str) else (raw or [])
                if lst:
                    ref = lst
            except Exception:
                pass
    return r.status_code, status, answer, ref, rt


def cap_normal(s):
    code, status, ans, ref, rt = ask(s, "智造贷最高额度是多少？")
    ok = code == 200 and status == 2 and len(ans) > 10 and bool(ref)
    record("NORMAL", ok, f"http={code} status={status} answer_len={len(ans)} refs={len(ref)} rt={rt}",
           {"answer": ans[-300:], "ref0": ref[0] if ref else None})


def cap_faq(s):
    code, status, ans, ref, rt = ask(s, "客户访前准备是否是文档的主要内容？", config_id=CFG_FAQ)
    ok = code == 200 and status == 2 and rt == 2 and bool(ans)
    record("FAQ", ok, f"http={code} status={status} resultType={rt} answer={ans[:40]!r} refs={len(ref)}",
           {"answer": ans, "ref0": ref[0] if ref else None})


def cap_global(s):
    t0 = time.time()
    code, status, ans, ref, rt = ask(s, "我们这类企业的授信额度与票据贴现是什么关系", global_mode=True)
    cost = time.time() - t0
    srcs = [(x.get("metadata") or {}).get("source", "") for x in (ref or [])]
    ok = code == 200 and status == 2 and len(ans) > 10 and any(srcs)
    record("GLOBAL", ok, f"http={code} status={status} cost={cost:.1f}s refs={len(ref)} "
                         f"ref_src示例={srcs[0][-40:] if srcs else None}",
           {"answer": ans[-400:], "sources": srcs[:5]})


def cap_version(s):
    code, body = api(s, "GET", f"/index/knowledgeBase/file/multiple/version?kbNames={KB_NAME}&pageNo=1&pageSize=10", s.token)
    groups = ((body or {}).get("data") or {}).get("records") if isinstance(body, dict) else None
    ok = code == 200 and isinstance(groups, list)
    detail = f"http={code} groups={len(groups or [])}"
    if groups:
        detail += f" 版本示例={[k.get('version') for k in (groups[0].get('kbFiles') or [])][:4]}"
    record("VERSION", ok, detail, {"groups": (groups or [])[:2]})


def cap_table(s):
    code, status, ans, ref, rt = ask(s, "台账里华东精密制造的授信额度是多少？")
    ok = code == 200 and status == 2 and ("3000" in ans)
    record("TABLE", ok, f"http={code} status={status} 命中3000={'3000' in ans} answer={ans[-60:]!r}",
           {"answer": ans[-300:], "refs": len(ref)})


def cap_graph_local(s):
    """图局部检索：直接打检索服务，避免被 rerank 掩盖。"""
    payload = {"query": "智造贷的授信额度和票据贴现是什么关系", "knowledge_base_name": [KB_NAME],
               "top_k": 10, "enabled_faq": False, "enabled_graph": True, "enabled_rerank": False,
               "model_info": {"model_id": "qwen2.5-7b-instruct",
                              "url": "http://127.0.0.1:18092/v1/chat/completions", "key": "sk-r12-local"}}
    r = requests.post("http://127.0.0.1:19995/retrieval_documents", json=payload, timeout=180)
    data = (r.json() or {}).get("data") or {}
    docs = data.get("documents_list") or []
    graph_docs = [d for d in docs if "graph" in json.dumps((d.get("metadata") or {}), ensure_ascii=False).lower()]
    ok = r.status_code == 200 and len(graph_docs) > 0
    record("GRAPH_LOCAL", ok, f"http={r.status_code} docs={len(docs)} graph_docs={len(graph_docs)}",
           {"graph_docs": graph_docs[:3]})


def cap_internal_guard(s):
    """内部回写入口必须拒绝无令牌调用。"""
    r = requests.post(GATEWAY + "/index/parseTask/callback", json={},
                      headers={"Content-Type": "application/json", "User-Agent": UA}, timeout=20)
    r2 = requests.post(GATEWAY + "/index/knowledgeBase/file/uploadParsedFile?kbId=1&fileId=1&userId=1",
                       headers={"Content-Type": "application/json", "User-Agent": UA}, timeout=20)
    ok = r.status_code in (401, 403) and r2.status_code in (401, 403)
    record("INTERNAL_GUARD", ok, f"callback={r.status_code} uploadParsedFile={r2.status_code}")


CAPS = {
    "NORMAL": cap_normal,
    "FAQ": cap_faq,
    "GLOBAL": cap_global,
    "VERSION": cap_version,
    "TABLE": cap_table,
    "GRAPH_LOCAL": cap_graph_local,
    "INTERNAL_GUARD": cap_internal_guard,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="逗号分隔，如 FAQ,GLOBAL")
    args = ap.parse_args()
    want = [x.strip().upper() for x in args.only.split(",") if x.strip()] or list(CAPS)

    s, token, _ = login()
    s.token = token

    for name in want:
        fn = CAPS.get(name)
        if not fn:
            record(name, False, "未知能力名")
            continue
        try:
            fn(s)
        except Exception as e:
            record(name, False, f"异常: {type(e).__name__}: {e}")
            print(traceback.format_exc(limit=3))

    os.makedirs(EVID, exist_ok=True)
    passed = sum(1 for r in RESULTS if r["ok"])
    with open(os.path.join(EVID, "caps.json"), "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=1)
    with open(os.path.join(EVID, "summary.md"), "w", encoding="utf-8") as f:
        f.write(f"# R13 能力矩阵自检\n\n总计 {passed}/{len(RESULTS)} PASS\n\n| 能力 | 结果 | 详情 |\n|---|---|---|\n")
        for r in RESULTS:
            f.write(f"| {r['cap']} | {'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |\n")
    print(f"\n== {passed}/{len(RESULTS)} PASS == 证据: {EVID}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
