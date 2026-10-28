#!/usr/bin/env python3
"""AG-4 第二轮只读探针：global 稳定性/版本污染、回链三段、数值可支撑率、多版本问答、图开关对照。"""
import json
import os
import re
import sys
import time

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import GATEWAY, UA, login  # noqa: E402

import requests  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EVID = os.path.join(HERE, "evidence")
KB = "kb_9"
REFUSE_KEYS = ("未提及", "无法", "不足以回答", "未生成推测性答案", "没有相关", "未找到", "无法获取", "无法直接")


def dump(name, obj):
    with open(os.path.join(EVID, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print("  ->", name)


def ask(token, content, global_mode=False, config_id=1, timeout=300):
    body = {"sessionId": f"ag4b-{int(time.time()*1000)}", "queryId": f"q-{int(time.time()*1000)}",
            "content": content, "type": "text", "sysType": "KNO_INDEX", "configId": config_id}
    if global_mode:
        body["globalMode"] = True
    t0 = time.time()
    try:
        r = requests.post(GATEWAY + "/qa/ai/question", json=body,
                          headers={"Authorization": token, "Accept": "text/event-stream",
                                   "Content-Type": "application/json", "User-Agent": UA},
                          stream=True, timeout=timeout)
    except Exception as e:
        return {"transport_error": f"{type(e).__name__}: {e}"}
    raw = b""
    for line in r.iter_lines():
        if line:
            raw += line + b"\n"
    txt = raw.decode("utf-8", "replace")
    answer, refs, status, rtype = "", [], None, None
    for part in txt.split("data:"):
        part = part.strip()
        if not part or part == "[DONE]":
            continue
        try:
            o = json.loads(part)
        except Exception:
            continue
        c = ((o.get("reply") or {}) if isinstance(o.get("reply"), dict) else {}).get("content") or ""
        if len(c) > len(answer):
            answer = c
        if o.get("status") is not None:
            status = o["status"]
        if o.get("resultType") is not None:
            rtype = o["resultType"]
        v = o.get("reference")
        if v:
            try:
                d = json.loads(v) if isinstance(v, str) else v
                rawl = d.get("documents") if isinstance(d, dict) else d
                lst = json.loads(rawl) if isinstance(rawl, str) else (rawl or [])
                if lst:
                    refs = lst
            except Exception:
                pass
    return {"http": r.status_code, "status": status, "resultType": rtype, "answer": answer,
            "refs": refs, "refs_n": len(refs), "cost": round(time.time() - t0, 1),
            "globalMode_sent": global_mode,
            "is_refusal": any(k in answer for k in REFUSE_KEYS),
            "community_ids": re.findall(r"\[L0-[0-9a-f]+\]", answer)}


def src(x):
    return str(((x.get("metadata") or {}).get("source")) or "")


def presign(token, source):
    key = source.lstrip("/")
    if key.startswith("minio/"):
        key = key[len("minio/"):]
    r = requests.get(GATEWAY + "/index/knowledgeBase/file/presign",
                     params={"key": key},
                     headers={"Authorization": token, "X-Platform": "rag-qa", "User-Agent": UA},
                     timeout=60)
    url = None
    try:
        b = r.json()
        url = b.get("url") or (b.get("data") or {}).get("url")
    except Exception:
        pass
    out = {"source": source, "key": key, "presign_http": r.status_code, "presign_url_ok": bool(url)}
    if url:
        try:
            g = requests.get(url, timeout=60)
            out["fetch_http"] = g.status_code
            out["bytes"] = len(g.content)
            out["head"] = g.content[:6].decode("latin-1")
        except Exception as e:
            out["fetch_error"] = f"{type(e).__name__}: {e}"
    return out


def numbers_in(text):
    """抽取答案中的数值型结论（保留单位，便于核对原文）"""
    return re.findall(r"(\d+(?:\.\d+)?)\s*(万元|亿元|元|个基点|基点|%|％|天|个月|年|个工作日)?", text or "")


def main():
    s, token, _ = login()
    print("login ok")

    G1 = ("江南装备科技有限公司、华东精密制造有限公司、北方重工配件厂三家的信用评级分别是什么？"
          "按智造贷的评级加点规则，它们执行利率相对一年期LPR的加点分别是多少？")
    Q_AMT = "智造贷最高额度是多少？"
    Q_V0 = "R12FIX-product-loan.docx 的 V0 版本里，智造贷的单户最高授信额度是多少？"
    Q_V1 = "R12FIX-product-loan.docx 的 V1 版本里，智造贷的单户最高授信额度是多少？"
    Q_REF = "海川电子材料股份有限公司被列为关注类，需要计提多少比例的贷款损失准备？"

    # ---- B1 G1 连跑 3 次（global 开）----
    g1_runs = [ask(token, G1, global_mode=True) for _ in range(3)]
    dump("B1-global-G1-3runs.json", {
        "question": G1,
        "runs": [{"i": i + 1, "http": r.get("http"), "status": r.get("status"),
                  "is_refusal": r.get("is_refusal"), "cost": r.get("cost"),
                  "refs_n": r.get("refs_n"), "sources": [src(x) for x in r.get("refs") or []],
                  "community_ids": r.get("community_ids"),
                  "answer": r.get("answer")} for i, r in enumerate(g1_runs)]})

    # ---- B2 额度题：global 开/关 各 3 次（版本污染与假拒答）----
    amt = {}
    for mode, tag in ((True, "on"), (False, "off")):
        rows = []
        for i in range(3):
            r = ask(token, Q_AMT, global_mode=mode)
            rows.append({"i": i + 1, "http": r.get("http"), "status": r.get("status"),
                         "is_refusal": r.get("is_refusal"), "refs_n": r.get("refs_n"),
                         "sources": [src(x) for x in r.get("refs") or []],
                         "has_5000": "5000" in (r.get("answer") or ""),
                         "has_8000": "8000" in (r.get("answer") or ""),
                         "answer": r.get("answer")})
        amt[tag] = rows
    dump("B2-amount-onoff-3x.json", {"question": Q_AMT, **amt})

    # ---- B3 显式问 V0 / V1 ----
    v0 = ask(token, Q_V0, global_mode=False)
    v1 = ask(token, Q_V1, global_mode=False)
    dump("B3-ask-version-explicit.json", {
        "v0": {"question": Q_V0, "http": v0.get("http"), "status": v0.get("status"),
               "answer": v0.get("answer"), "sources": [src(x) for x in v0.get("refs") or []],
               "has_5000": "5000" in (v0.get("answer") or ""), "has_8000": "8000" in (v0.get("answer") or "")},
        "v1": {"question": Q_V1, "http": v1.get("http"), "status": v1.get("status"),
               "answer": v1.get("answer"), "sources": [src(x) for x in v1.get("refs") or []],
               "has_5000": "5000" in (v1.get("answer") or ""), "has_8000": "8000" in (v1.get("answer") or "")}})

    # ---- B4 拒答题（global 开/关）----
    rr_on = ask(token, Q_REF, global_mode=True)
    rr_off = ask(token, Q_REF, global_mode=False)
    dump("B4-refusal.json", {
        "on": {"answer": rr_on.get("answer"), "is_refusal": rr_on.get("is_refusal"),
               "refs_n": rr_on.get("refs_n"), "sources": [src(x) for x in rr_on.get("refs") or []],
               "nums": numbers_in(rr_on.get("answer"))},
        "off": {"answer": rr_off.get("answer"), "is_refusal": rr_off.get("is_refusal"),
                "refs_n": rr_off.get("refs_n"), "sources": [src(x) for x in rr_off.get("refs") or []],
                "nums": numbers_in(rr_off.get("answer"))}})

    # ---- B5 回链三段全绿（对 global G1 与默认额度答案的每条引用）----
    chain = {"G1_on": [], "amount_off": []}
    for tag, res in (("G1_on", g1_runs[0]), ("amount_off", None)):
        if res is None:
            res = ask(token, Q_AMT, global_mode=False)
        for x in (res.get("refs") or []):
            srcv = src(x)
            row = {"source": srcv, "version_in_source": (re.search(r"/V(\d+)/", srcv).group(1) if re.search(r"/V(\d+)/", srcv) else None),
                   "shape_ok": bool(srcv) and srcv.startswith("r12-rag/") and "://" not in srcv}
            if srcv:
                row.update(presign(token, srcv))
            chain[tag].append(row)
    dump("B5-citation-chain.json", chain)

    # ---- B6 数值可支撑率：答案里的数值是否都能在引用原文里找到 ----
    # 原文取自 ES 的 page_content（存储事实），按引用 source 精确匹配
    ES = "http://127.0.0.1:19200"
    IDX = (KB, "table_chunks_" + KB, "table_summary_" + KB)

    def source_text(srcv):
        out = []
        for idx in IDX:
            r = requests.post(f"{ES}/{idx}/_search", json={
                "size": 5, "_source": ["page_content"],
                "query": {"term": {"metadata.source.keyword": srcv}}}, timeout=30)
            for h in (((r.json() or {}).get("hits") or {}).get("hits") or []):
                out.append(((h.get("_source") or {}).get("page_content") or ""))
        return "\n".join(out)

    support = {}
    for tag, res in (("G1_on", g1_runs[0]), ("amount_off", ask(token, Q_AMT, global_mode=False))):
        ctx = "\n".join(source_text(src(x)) for x in (res.get("refs") or []))
        nums = [n for n, u in numbers_in(res.get("answer") or "")]
        # 去掉明显的序数/年份噪声，只留 >=2 位数值
        nums = [n for n in nums if len(n.replace(".", "")) >= 2]
        sup = [n for n in nums if n in ctx]
        support[tag] = {"answer": res.get("answer"), "numbers": nums,
                        "supported": sup, "unsupported": [n for n in nums if n not in sup],
                        "source_chars": len(ctx)}
    dump("B6-number-support.json", support)

    # ---- B7 图开/关对照（检索服务 19995），跨两跳题 ----
    def retrieve(q, enabled_graph):
        payload = {"query": q, "knowledge_base_name": [KB], "top_k": 10,
                   "enabled_faq": False, "enabled_graph": enabled_graph, "enabled_rerank": False,
                   "model_info": {"model_id": "qwen2.5-7b-instruct",
                                  "url": "http://127.0.0.1:18092/v1/chat/completions",
                                  "key": "sk-r12-local"}}
        r = requests.post("http://127.0.0.1:19995/retrieval_documents", json=payload, timeout=180)
        try:
            b = r.json()
        except Exception:
            b = {}
        docs = ((b.get("data") or {}).get("documents_list") or [])
        return {"http": r.status_code, "code": b.get("code"), "msg": str(b.get("msg"))[:120],
                "n": len(docs),
                "docs": [{"pk": (d.get("metadata") or {}).get("pk"),
                          "source": (d.get("metadata") or {}).get("source"),
                          "version": (d.get("metadata") or {}).get("version"),
                          "search_type": (d.get("metadata") or {}).get("search_type"),
                          "score": d.get("score"),
                          "len": len(d.get("page_content") or "")} for d in docs]}

    MH = "江南装备科技有限公司的信用评级是什么，按这个评级它适用的加点是多少，对应产品的最高授信额度又是多少？"
    g_on = retrieve(MH, True)
    g_off = retrieve(MH, False)
    pk_on = {d["pk"] for d in g_on["docs"] if d.get("pk")}
    pk_off = {d["pk"] for d in g_off["docs"] if d.get("pk")}
    dump("B7-graph-onoff-retrieval.json", {
        "question": MH, "graph_on": g_on, "graph_off": g_off,
        "pk_on_n": len(pk_on), "pk_off_n": len(pk_off),
        "only_on": sorted(pk_on - pk_off), "only_off": sorted(pk_off - pk_on),
        "identical": pk_on == pk_off})

    print("done")


if __name__ == "__main__":
    main()
