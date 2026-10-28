#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-3 API 层探针：S6 检索 + S7 问答(local) 的接口事实采集。

只读：只提问 / 只检索，不建库、不删档、不改配置。
所有判定基于可复核锚点（http、status、pk、ES _id 交集、presign 字节数）。
输出：<AG-3>/evidence/api/*.json  +  stdout 摘要
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests

QA = "/home/szf/data/dev/llmke-r12/platform/r12/qa"
sys.path.insert(0, QA)
from r12_client import GATEWAY, UA, api, login  # noqa: E402

RUN = "/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357"
EVID = os.path.join(RUN, "AG-3", "evidence", "api")
os.makedirs(EVID, exist_ok=True)

RETR = "http://127.0.0.1:19995/retrieval_documents"
ES = "http://127.0.0.1:19200"
KB_NAME = "kb_9"
CFG_DEFAULT = 1
IDX_MAIN = "kb_9"
IDX_TBL_CHUNK = "table_chunks_kb_9"
IDX_TBL_SUM = "table_summary_kb_9"
ALL_IDX = (IDX_MAIN, IDX_TBL_CHUNK, IDX_TBL_SUM)
MODEL_INFO = {"model_id": "qwen2.5-7b-instruct",
              "url": "http://127.0.0.1:18092/v1/chat/completions",
              "key": "sk-r12-local"}

TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = {}


def dump(name, obj):
    p = os.path.join(EVID, f"{name}-{TS}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return p


# ---------------- 问答 ----------------

def ask(s, token, content, session_id=None, query_id=None, global_mode=False, timeout=300):
    """SSE 问答。返回 dict(http, status, answer, refs, events)。"""
    t0 = time.time()
    payload = {"sessionId": session_id or f"ag3-{int(time.time()*1000)}",
               "queryId": query_id or f"ag3q-{int(time.time()*1000)}",
               "content": content, "type": "text", "sysType": "KNO_INDEX",
               "configId": CFG_DEFAULT}
    if global_mode:
        payload["globalMode"] = True
    r = requests.post(GATEWAY + "/qa/ai/question", json=payload,
                      headers={"Authorization": token, "Accept": "text/event-stream",
                               "Content-Type": "application/json", "User-Agent": UA},
                      stream=True, timeout=timeout)
    raw = b""
    for line in r.iter_lines():
        if line:
            raw += line + b"\n"
    txt = raw.decode("utf-8", "replace")
    answer, refs, status, events = "", [], None, []
    for part in txt.split("data:"):
        part = part.strip()
        if not part:
            continue
        try:
            o = json.loads(part)
        except Exception:
            continue
        events.append(o)
        c = (o.get("reply") or {}).get("content") or ""
        if c:
            answer = c
        if o.get("status") is not None:
            status = o["status"]
        v = o.get("reference")
        if v:
            try:
                d = json.loads(v) if isinstance(v, str) else v
                rw = d.get("documents") if isinstance(d, dict) else d
                lst = json.loads(rw) if isinstance(rw, str) else (rw or [])
                if lst:
                    refs = lst
            except Exception:
                pass
    return {"http": r.status_code, "status": status, "answer": answer,
            "refs": refs, "events": events, "elapsed": round(time.time() - t0, 2),
            "session_id": payload["sessionId"], "query_id": payload["queryId"],
            "content": content}


# ---------------- 引用可回指三段（§1.5）----------------

VER_RE = re.compile(r"/V(\d+)/")


def es_all_sources():
    """三索引（主 + table_chunks + table_summary）全量 source -> 版本，用于判"有效版本"。

    修正记录：第一版只读主索引，导致台账类 source（只在 table_* 里）取不到有效版本，
    被自己的判据误判为 version_ok=False（假红）。§1.6 要求跨索引。
    """
    out = {}
    for idx in ALL_IDX:
        r = requests.post(f"{ES}/{idx}/_search",
                          json={"query": {"match_all": {}}, "size": 2000,
                                "_source": ["metadata.source", "metadata.version"]}, timeout=60)
        for h in (r.json().get("hits") or {}).get("hits") or []:
            m = (h.get("_source") or {}).get("metadata") or {}
            src = m.get("source")
            if src:
                out[src] = m.get("version")
    return out


def effective_version(src, srcmap):
    """按 /Vn/ 之前前缀归一（陷阱 §5.1：不能按 title 比）。"""
    base = src.split("/V", 1)[0]
    best = -1
    for other, ver in srcmap.items():
        if other.split("/V", 1)[0] != base:
            continue
        mv = re.fullmatch(r"[Vv](\d+)", str(ver or ""))
        if mv:
            best = max(best, int(mv.group(1)))
    return best


def presign(s, token, key):
    last = None
    for base in (GATEWAY, "http://127.0.0.1:18082"):
        for p in ("/index/knowledgeBase/file/presign", "/knowledgeBase/file/presign"):
            try:
                r = s.get(f"{base}{p}", params={"key": key},
                          headers={"Authorization": token, "User-Agent": UA}, timeout=30)
                last = {"url": base + p, "http": r.status_code, "body": (r.text or "")[:200]}
                if r.status_code == 200:
                    try:
                        body = r.json()
                    except Exception:
                        body = {"raw": r.text[:300]}
                    return True, body, last
            except Exception as e:
                last = {"url": base + p, "http": "EXC", "err": str(e)[:120]}
    return False, {}, last


def url_from(body):
    for k in ("data", "url", "presignedUrl", "presigned_url"):
        v = body.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
        if isinstance(v, dict):
            for kk in ("url", "presignedUrl"):
                if isinstance(v.get(kk), str) and v[kk].startswith("http"):
                    return v[kk]
    return None


def es_count_source(src):
    total, hits = 0, []
    for idx in ALL_IDX:
        try:
            r = requests.get(f"{ES}/{idx}/_count",
                             json={"query": {"term": {"metadata.source.keyword": src}}}, timeout=30)
            n = int(((r.json() or {}).get("count")) or 0)
            if n > 0:
                total += n
                hits.append(idx)
        except Exception:
            return -1, []
    return total, hits


def es_ids(pks):
    got = set()
    if not pks:
        return got
    body = {"size": len(pks) + 5, "_source": False,
            "query": {"ids": {"values": [str(p) for p in pks]}}}
    for idx in ALL_IDX:
        try:
            r = requests.post(f"{ES}/{idx}/_search", json=body, timeout=30)
            for h in ((r.json().get("hits") or {}).get("hits") or []):
                got.add(str(h.get("_id")))
        except Exception:
            pass
    return got


def citation_check(s, token, refs, srcmap, label):
    """§1.5 三段全绿：形态 / presign 取回 / 版本==有效版本。"""
    out = []
    for i, d in enumerate(refs):
        md = d.get("metadata") or {}
        src = str(md.get("source") or "")
        rec = {"i": i, "source": src, "pk": doc_pk(d),
               "file_id": md.get("file_id"), "score": md.get("score"),
               "search_type": md.get("search_type")}
        # ① 形态
        rec["form_ok"] = bool(re.match(r"^r12-rag/kb_\d+/.+", src)) \
            and "http" not in src and src.count("//") == 0
        # ③ 版本（先算，不需要网络）
        m = VER_RE.search(src)
        if m:
            ref_v = int(m.group(1))
            eff = effective_version(src, srcmap)
            rec.update({"ref_version": f"V{ref_v}", "effective_version": f"V{eff}" if eff >= 0 else None,
                        "version_ok": bool(eff >= 0 and ref_v >= eff)})
        else:
            rec.update({"ref_version": None, "effective_version": None, "version_ok": False})
        # ② 传输
        if rec["form_ok"]:
            okp, pbody, trace = presign(s, token, src)
            rec["presign_ok"] = okp
            rec["presign_trace"] = trace
            url = url_from(pbody) if okp else None
            rec["has_url"] = bool(url)
            if url:
                try:
                    g = requests.get(url, timeout=60)
                    rec["get_status"] = g.status_code
                    rec["bytes"] = len(g.content)
                except Exception as e:
                    rec["get_status"] = "EXC"
                    rec["get_err"] = str(e)[:120]
        # 存储事实：source 是否在 ES（跨索引）
        n, hit = es_count_source(src)
        rec["es_source_count"] = n
        rec["es_hit_indexes"] = hit
        rec["all_green"] = bool(rec.get("form_ok") and rec.get("presign_ok")
                                and rec.get("get_status") == 200 and rec.get("version_ok")
                                and n > 0)
        out.append(rec)
    return out


# ---------------- 检索 ----------------

def retrieve(query, policy=1, top_k=10, graph=False, rerank=False, faq=False):
    payload = {"query": query, "knowledge_base_name": [KB_NAME], "top_k": top_k,
               "enabled_faq": faq, "enabled_graph": graph, "enabled_rerank": rerank,
               "search_policy": policy, "model_info": MODEL_INFO}
    t0 = time.time()
    r = requests.post(RETR, json=payload, timeout=180)
    dt = round(time.time() - t0, 2)
    try:
        body = r.json()
    except Exception:
        body = {}
    docs = ((body.get("data") or {}).get("documents_list") or []) if isinstance(body, dict) else []
    return {"http": r.status_code, "code": body.get("code") if isinstance(body, dict) else None,
            "msg": body.get("msg") if isinstance(body, dict) else str(body)[:200],
            "docs": docs, "elapsed": dt, "payload": {k: v for k, v in payload.items()
                                                     if k != "model_info"}}


def doc_pk(d):
    """块主键。实测：`pk` 在 **doc 顶层**，`chunk_pk` 在 metadata 里（metadata.pk 不存在）。
    第一版取 metadata.pk → 全 None，导致 pk 存在性断言恒 0/0（空转），已修正。"""
    if d.get("pk") not in (None, ""):
        return str(d.get("pk"))
    md = d.get("metadata") or {}
    for k in ("chunk_pk", "pk", "id"):
        if md.get(k) not in (None, ""):
            return str(md.get(k))
    return None


def summarize_docs(docs, n=10):
    out = []
    for d in docs[:n]:
        md = d.get("metadata") or {}
        st = md.get("search_type")
        out.append({"pk": doc_pk(d), "score": md.get("score"), "search_type": st,
                    "source": str(md.get("source") or "")[-60:],
                    "version": md.get("version"),
                    "len": len(d.get("page_content") or ""),
                    "head": (d.get("page_content") or "")[:60].replace("\n", " ")})
    return out


def main():
    s, token, _ = login()
    s.token = token
    srcmap = es_all_sources()
    print(f"[env] 主索引 source 数={len(srcmap)}")
    OUT["env"] = {"main_sources": len(srcmap),
                  "ts": TS,
                  "pids_baseline": "8088=1403651 18082=2139785 18083=1647331 "
                                   "19527=1823402 19529=1461792 19995=1481869"}

    # ===== S6 检索 =====
    Q = "智造贷最高授信额度是多少"
    s6 = {}
    for name, pol in (("hybrid", 1), ("es_text", 2), ("milvus_vector", 3)):
        r = retrieve(Q, policy=pol, top_k=10)
        r["summary"] = summarize_docs(r["docs"])
        s6[name] = r
        print(f"[S6-{name}] http={r['http']} code={r['code']} docs={len(r['docs'])} "
              f"elapsed={r['elapsed']}s st={[x['search_type'] for x in r['summary'][:3]]}")
    # 一致性：同 query 同模式连跑两次
    a = retrieve(Q, policy=1, top_k=10)
    b = retrieve(Q, policy=1, top_k=10)
    ka = [doc_pk(d) for d in a["docs"]]
    kb = [doc_pk(d) for d in b["docs"]]
    s6["consistency"] = {"run1_pks": ka, "run2_pks": kb,
                         "run1_n": len(ka), "run2_n": len(kb),
                         "same_order": ka == kb,
                         "set_equal": set(ka) == set(kb),
                         "overlap": len(set(ka) & set(kb))}
    print(f"[S6-consistency] run1={len(ka)} run2={len(kb)} same_order={ka == kb} "
          f"set_equal={set(ka) == set(kb)} overlap={len(set(ka) & set(kb))}")

    # 无结果 query（rerank 关 / 开 两态，因为 enabled_rerank=False 会走 no_rerank_score 跳过阈值）
    NQ = "zzzqqq 量子纠缠超导材料的临界温度是多少 zzzqqq"
    nr = retrieve(NQ, policy=1, top_k=10, rerank=False)
    nr2 = retrieve(NQ, policy=1, top_k=10, rerank=True)
    s6["no_result"] = {
        "query": NQ,
        "rerank_off": {"http": nr["http"], "code": nr["code"], "msg": nr["msg"],
                       "docs": len(nr["docs"]), "summary": summarize_docs(nr["docs"], 5)},
        "rerank_on": {"http": nr2["http"], "code": nr2["code"], "msg": nr2["msg"],
                      "docs": len(nr2["docs"]), "summary": summarize_docs(nr2["docs"], 5),
                      "elapsed": nr2["elapsed"]},
    }
    print(f"[S6-noresult] rerank_off: http={nr['http']} docs={len(nr['docs'])} | "
          f"rerank_on: http={nr2['http']} docs={len(nr2['docs'])} msg={nr2['msg'][:60]!r}")

    # 表格类（跨索引）
    TQ = "华东精密制造的授信额度是多少"
    tr = retrieve(TQ, policy=1, top_k=10)
    tsum = summarize_docs(tr["docs"], 20)
    tbl = [x for x in tsum
           if "credit-ledger" in (x["source"] or "") or "table" in str(x["search_type"] or "")]
    s6["table_cross_index"] = {"query": TQ, "http": tr["http"], "docs": len(tr["docs"]),
                               "summary": tsum,
                               "table_hits": tbl}
    print(f"[S6-table] http={tr['http']} docs={len(tr['docs'])} 表格命中={len(tbl)}")

    # pk 存在性（全索引，doc 顶层 pk）
    allpks = [doc_pk(d) for d in tr["docs"] if doc_pk(d)]
    got = es_ids(allpks)
    hit = [p for p in allpks if p in got]
    s6["pk_existence"] = {"pks": allpks, "found_in_es": sorted(got),
                          "missing": [p for p in allpks if p not in got],
                          "rate": f"{len(hit)}/{len(allpks)}",
                          "verify_method": "POST 19200/{kb_9,table_chunks_kb_9,table_summary_kb_9}/_search "
                                           "query.ids.values=[pk]；命中集合交 pk"}
    print(f"[S6-pk] {len(hit)}/{len(allpks)} 存在 缺失={[p for p in allpks if p not in got][:3]}")
    OUT["S6"] = s6
    dump("S6-retrieval", s6)

    # ===== S7 问答 local =====
    s7 = {}
    q1 = "智造贷最高授信额度是多少？"
    r1 = ask(s, token, q1)
    c1 = citation_check(s, token, r1["refs"], srcmap, "q1")
    s7["q1"] = {k: v for k, v in r1.items() if k != "events"}
    s7["q1"]["events_n"] = len(r1["events"])
    s7["q1"]["citation"] = c1
    print(f"[S7-q1] http={r1['http']} status={r1['status']} answer_len={len(r1['answer'])} "
          f"refs={len(r1['refs'])} elapsed={r1['elapsed']}s")
    print(f"    answer={r1['answer'][:160]!r}")
    for c in c1:
        print(f"    ref{c['i']}: form={c['form_ok']} presign={c.get('presign_ok')} "
              f"get={c.get('get_status')} bytes={c.get('bytes')} ver={c.get('ref_version')}"
              f"/{c.get('effective_version')} vok={c.get('version_ok')} "
              f"es={c.get('es_source_count')} all={c['all_green']}")

    # 语义改写两次
    q2a = "请问智造贷这款产品能给到的最高贷款额度是多少"
    q2b = "智造贷最多可以批多少授信"
    r2a = ask(s, token, q2a)
    r2b = ask(s, token, q2b)
    s7["rephrase"] = {
        "A": {"query": q2a, "answer": r2a["answer"], "refs": len(r2a["refs"]),
              "status": r2a["status"], "http": r2a["http"],
              "citations": citation_check(s, token, r2a["refs"], srcmap, "q2a")},
        "B": {"query": q2b, "answer": r2b["answer"], "refs": len(r2b["refs"]),
              "status": r2b["status"], "http": r2b["http"],
              "citations": citation_check(s, token, r2b["refs"], srcmap, "q2b")}}
    print(f"[S7-rephraseA] refs={len(r2a['refs'])} answer={r2a['answer'][:100]!r}")
    print(f"[S7-rephraseB] refs={len(r2b['refs'])} answer={r2b['answer'][:100]!r}")

    # 多轮追问：同一 sessionId
    sid = f"ag3-multi-{int(time.time()*1000)}"
    t1 = ask(s, token, "智造贷是什么产品？", session_id=sid,
             query_id=f"ag3m1-{int(time.time()*1000)}")
    time.sleep(0.5)
    t2 = ask(s, token, "它的最高授信额度是多少？", session_id=sid,
             query_id=f"ag3m2-{int(time.time()*1000)}")
    s7["multiturn"] = {"session_id": sid,
                       "turn1": {"q": t1["content"], "answer": t1["answer"],
                                 "refs": len(t1["refs"]), "status": t1["status"]},
                       "turn2": {"q": t2["content"], "answer": t2["answer"],
                                 "refs": len(t2["refs"]), "status": t2["status"],
                                 "refs_detail": summarize_docs(t2["refs"], 5)}}
    print(f"[S7-multi] turn1 refs={len(t1['refs'])} turn2 refs={len(t2['refs'])}")
    print(f"    turn2 answer={t2['answer'][:160]!r}")

    # 连跑 3 次（同一题）
    runs = []
    for i in range(3):
        rr = ask(s, token, q1)
        pk_list = [doc_pk(d) for d in rr["refs"]]
        runs.append({"i": i, "http": rr["http"], "status": rr["status"],
                     "answer_len": len(rr["answer"]), "answer": rr["answer"],
                     "refs": len(rr["refs"]), "ref_pks": pk_list,
                     "elapsed": rr["elapsed"]})
        print(f"[S7-run{i+1}] status={rr['status']} refs={len(rr['refs'])} "
              f"len={len(rr['answer'])} {rr['elapsed']}s")
    s7["repeat3"] = runs
    OUT["S7"] = s7
    dump("S7-chat", s7)
    print(f"\n[evidence] {EVID}")


if __name__ == "__main__":
    main()
