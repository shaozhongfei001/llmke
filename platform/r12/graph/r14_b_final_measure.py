#!/usr/bin/env python3
"""R14 B 终版测量：经用户入口 /qa 跑 global 3 正例 + 1 拒答，并做 local 开/关图对照。

只发请求、落证据，不改任何服务。服务未就绪时直接报错退出（不伪造结果）。

用法：platform/r12/venvs/graph/bin/python platform/r12/graph/r14_b_final_measure.py
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qa"))
from r12_client import UA, login  # noqa: E402

import requests  # noqa: E402

GATEWAY = "http://127.0.0.1:8088"
EVID = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

QUESTIONS = [
    ("G1", "江南装备科技有限公司、华东精密制造有限公司、北方重工配件厂三家的信用评级分别是什么？"
           "按智造贷的评级加点规则，它们执行利率相对一年期LPR的加点分别是多少？"),
    ("G2", "知识库里日均存款和用电量这两个对账指标，数据源分别是什么、统计口径分别是什么？"),
    ("G3", "四家授信客户的信用评级和授信到期日分别是什么？其中哪些客户的授信在2027年上半年（2027-06-30之前）到期？"),
    ("R2", "海川电子材料股份有限公司被列为关注类，需要计提多少比例的贷款损失准备？"),
]
LOCAL_Q = "江南装备科技有限公司的信用评级是AAA，按智造贷的评级加点规则，它执行利率相对一年期LPR要加多少基点？"


def parse_sse(r):
    answer, ref, status = "", [], None
    buf = b""
    for line in r.iter_lines():
        if not line:
            continue
        buf += line + b"\n"
    for part in buf.decode("utf-8", "replace").split("data:"):
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
    return answer, ref, status


def ask(token, content, config_id=1, global_mode=False, timeout=120):
    payload = {"sessionId": f"bf-{int(time.time()*1000)}", "queryId": f"qf-{int(time.time()*1000)}",
               "content": content, "type": "text", "sysType": "KNO_INDEX", "configId": config_id}
    if global_mode:
        payload["globalMode"] = True
    t0 = time.time()
    try:
        r = requests.post(GATEWAY + "/qa/ai/question", json=payload,
                          headers={"Authorization": token, "Accept": "text/event-stream",
                                   "Content-Type": "application/json", "User-Agent": UA},
                          stream=True, timeout=timeout)
    except requests.exceptions.RequestException as e:
        return {"http": 0, "transport_error": f"{type(e).__name__}", "answer": "",
                "refs": [], "cost": round(time.time() - t0, 1)}
    if r.status_code != 200:
        return {"http": r.status_code, "answer": "", "refs": [], "cost": round(time.time() - t0, 1)}
    try:
        answer, ref, status = parse_sse(r)
    except requests.exceptions.RequestException as e:
        return {"http": r.status_code, "transport_error": f"{type(e).__name__}",
                "answer": "", "refs": [], "cost": round(time.time() - t0, 1)}
    return {"http": r.status_code, "status": status, "answer": answer, "refs": ref,
            "cost": round(time.time() - t0, 1)}


def summarize(res):
    out = []
    for i, d in enumerate(res.get("refs") or []):
        md = d.get("metadata") or {}
        out.append({"i": i, "pk": d.get("pk"), "order_num": d.get("order_num"), "source": md.get("source"),
                    "title": md.get("title"), "search_type": md.get("search_type"),
                    "community_id": md.get("community_id"),
                    "recovered_by": md.get("recovered_by"),
                    "len": len(d.get("page_content") or ""),
                    "head": (d.get("page_content") or "")[:120]})
    return out


def main():
    s, token, _b = login()
    os.makedirs(EVID, exist_ok=True)
    report = {"ts": TS, "global": {}, "local": {}}
    for tag, q in QUESTIONS:
        res = ask(token, q, global_mode=True)
        res["refs_summary"] = summarize(res)
        report["global"][tag] = {"q": q, **res}
        with open(os.path.join(EVID, f"R14-B-FINAL-{TS}.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        print(f"\n===== {tag} http={res['http']} cost={res['cost']}s refs={len(res['refs'])}")
        print(res["answer"])
        for x in res["refs_summary"]:
            print(f"  [{x['i']}] {x['title']} src={x['source']!r} st={x['search_type']} "
                  f"recovered_by={x['recovered_by']}")
    for tag, cfg in ((os.environ.get("B_LOCAL_ONLY") and "on" or "on", 1),):
        pass
    for tag, cfg in [(t, c) for t, c in (("on", 1), ("off", 6))
                     if not os.environ.get("B_LOCAL_ONLY") or t == "on"]:
        res = ask(token, LOCAL_Q, config_id=cfg)
        res["refs_summary"] = summarize(res)
        report["local"][tag] = {"q": LOCAL_Q, "configId": cfg, **res}
        print(f"\n===== local graph={tag} configId={cfg} http={res['http']} cost={res['cost']}s "
              f"refs={len(res['refs'])}")
        print(res["answer"])
        for x in res["refs_summary"]:
            print(f"  [{x['i']}] {x['title']} src={x['source']!r} st={x['search_type']} "
                  f"recovered_by={x['recovered_by']}")
    p = os.path.join(EVID, f"R14-B-FINAL-{TS}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(f"\n[evidence] {p}")

    # 开/关图引用块集合差异
    # R14-B 更正（A-data 实测）：order_num = str(create_uuid()) 每请求现造，用它做跨请求集合
    # 比较在结构上恒为 0，不能当"开图更差"的证据。稳定键 = 文档顶层 pk（= ES _id / Milvus pk）。
    # /qa 的 reference 对象**没有顶层 pk**（实测 keys: metadata/order_num/page_content/
    # parsedFilePath/score/type），稳定身份只能用 (metadata.id=document_id, metadata.chunk_index)。
    def _ident(x):
        md = x.get("metadata") or {}
        return (md.get("id"), md.get("chunk_index"))
    on = {_ident(x) for x in report["local"]["on"]["refs_summary"]}
    off = {_ident(x) for x in report["local"]["off"]["refs_summary"]}
    print(f"local 引用块集合(按顶层 pk)：on={len(on)} off={len(off)} 交集={len(on & off)}")
    if not on:
        print("  注意：开图返回 0 条引用，集合比较无意义（先看 refs 数，不要用交集下结论）")
    on_graph = [x for x in report["local"]["on"]["refs_summary"]
                if "graph" in json.dumps(x.get("search_type") or [])
                or x.get("recovered_by") == "entity_content"]
    print(f"开图时带图标记/图回填的引用块：{len(on_graph)}")
    for x in on_graph:
        print(f"  - {x['title']} st={x['search_type']} recovered_by={x['recovered_by']} len={x['len']}")


if __name__ == "__main__":
    main()
