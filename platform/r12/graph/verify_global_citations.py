#!/usr/bin/env python3
"""逐条校验 global 结论能否"回指到能支撑该数值的社区"。

为什么需要（C15 验收口径，C 提的）：
  只断言"答案里出现了 [L0-xxxx]" 只证明带了个标记，没证明该社区能支撑这个数值。
  实测反例：旧版 answer 写"北方重工…0 基点 [L0-60d6fa91]"，而该社区只有评级、没有 0；
  更隐蔽的是"江南…30 个基点 [L0-3af0d4bc]"，30 根本不在 3af0d4bc 里（凭空），
  因为模型靠先验答对了，标记却指错了地方。

判据（每个数值一条）：
  1) 正文含 `N<单位>` 且在答案里标了 [L0-xxx]；
  2) 该社区**在 Nebula 的事实**（community_triples）里存在同一 `N<单位>`；
  3) 若 (2) 不成立，检查该数值是否出现在**别的社区**——是则判 MIS_CITED（引错社区），
     否则判 NO_SUPPORT（无依据）。
注意"支撑事实"取自图里实时读到的三元组，不是社区摘要正文：
  摘要正文可能被重写成短摘要（kb_9 在 11:06 就被重写过一次），拿正文当依据会误判 FAIL。

用法：
  NACOS_SERVER_ADDRESS=127.0.0.1:18848 DATA_ID=index_graph_config_py GROUP=DEFAULT_GROUP \
  platform/r12/venvs/graph/bin/python platform/r12/graph/verify_global_citations.py "问题"
"""
import json
import os
import re
import sys

import requests

SVC = "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service"
sys.path.insert(0, SVC)
os.environ.setdefault("PYTHONPATH", SVC)
os.environ.setdefault("NACOS_SERVER_ADDRESS", "127.0.0.1:18848")
os.environ.setdefault("DATA_ID", "index_graph_config_py")
os.environ.setdefault("GROUP", "DEFAULT_GROUP")

import graph_summary as gs  # noqa: E402

GRAPH = "http://127.0.0.1:19529"
NUM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(个基点|万元|个工作日|年|%)")
CID_RE = re.compile(r"\[(L\d-[0-9a-fA-F]+)\]")


def _ask(query, kb, top_k=7):
    body = {"space_name": kb, "query": query, "mode": "global", "top_k": top_k,
            "model_info": {"model_id": "qwen2.5-7b-instruct",
                           "url": "http://127.0.0.1:18092/v1/chat/completions",
                           "key": "sk-r12-local"}}
    r = requests.post(f"{GRAPH}/query_community", json=body, timeout=300)
    return r.json()


def _community_facts(kb):
    """cid → 该社区在图里的事实行（Nebula 实时，不读摘要正文）。"""
    out = {}
    for s in gs._load_summaries(kb, with_triples=True):
        cid = s.get("community_id")
        out[cid] = [f"{a} -{r}-> {b}" for a, r, b in (s.get("triples") or [])]
    return out


def main():
    query = sys.argv[1]
    kb = sys.argv[2] if len(sys.argv) > 2 else "kb_9"
    resp = _ask(query, kb)
    data = resp.get("data") or {}
    answer = data.get("answer") or ""
    facts = _community_facts(kb)

    print(f"[query] {query}")
    print(f"[answer]\n{answer}\n")
    print("[逐条校验]")
    verdicts = []
    for line in [x.strip() for x in answer.split("\n") if x.strip()]:
        nums = NUM_RE.findall(line)
        cids = CID_RE.findall(line)
        if not nums:
            continue
        if not cids:
            verdicts.append({"line": line[:70], "status": "NO_CITATION"})
            continue
        for num, unit in nums:
            token = f"{num}{unit}"
            proven = [c for c in cids if any(token in f for f in facts.get(c, []))]
            elsewhere = [c for c, fs in facts.items() if any(token in f for f in fs)]
            if proven:
                # 引用命中了支撑社区。若同时还有**别的社区**也含同一数值（如"加点"在规则社区、
                # 台账社区也有同数字），单列 PASS_MULTI，避免把"多社区共同支撑"错算成引用不唯一。
                st = "PASS_MULTI" if len(elsewhere) > 1 else "PASS"
                proven = proven
            else:
                st = "MIS_CITED" if elsewhere else "NO_SUPPORT"
                proven = elsewhere
            verdicts.append({"entity_line": line[:60], "number": token,
                             "cited": cids, "supporting": proven, "status": st})
            print(f"  {st:10s} {token:10s} cited={cids} supporting={proven or '-'}")

    ok = [v for v in verdicts if v["status"] in ("PASS", "PASS_MULTI")]
    multi = [v for v in verdicts if v["status"] == "PASS_MULTI"]
    mis = [v for v in verdicts if v["status"] == "MIS_CITED"]
    nos = [v for v in verdicts if v["status"] == "NO_SUPPORT"]
    # PASS_MULTI 也属正确（多社区共同支撑）；只有 MIS_CITED / NO_SUPPORT / NO_CITATION 才算错
    bad = [v for v in verdicts if v["status"] in ("MIS_CITED", "NO_SUPPORT", "NO_CITATION")]
    total = len(verdicts) or 1
    # R14-B（C 提议）：拆成两个独立指标，不合成一个 "是否 PASS"。
    #   数值可支撑率 = (PASS + MIS_CITED) / 总数  —— 数值在图里确实存在（哪怕引错社区）
    #   引用正确率   = PASS / 总数                —— 数值存在且引到了支撑它的那个社区
    # 两者的差 = MIS_CITED 的占比，正好对应"生成没问题、引用错位"这一类。
    print(f"\n[summary] 数值结论 {len(verdicts)} 条：PASS {len(ok) - len(multi)}，"
          f"PASS_MULTI {len(multi)}，MIS_CITED {len(mis)}，NO_SUPPORT {len(nos)}，非 PASS {len(bad)}")
    print(f"[metric] 数值可支撑率 {(len(ok) + len(mis)) / total:.0%}  "
          f"引用正确率 {len(ok) / total:.0%}  "
          f"（差额即引用错位 {len(mis) / total:.0%}）")
    if bad:
        print("[非 PASS 明细]")
        for v in bad:
            print("  ", json.dumps(v, ensure_ascii=False)[:200])
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence",
                       "R14-B-cite-verify-%s.json" % re.sub(r"\W+", "", str(int(__import__("time").time()))))
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"query": query, "kb": kb, "answer": answer, "verdicts": verdicts,
                   "summary": {"total": len(verdicts), "pass": len(ok),
                               "mis_cited": len(mis), "no_support": len(nos), "fail": len(bad),
                               "value_supported_rate": (len(ok) + len(mis)) / total,
                               "citation_correct_rate": len(ok) / total}},
                  f, ensure_ascii=False, indent=1)
    print("[evidence]", out)


if __name__ == "__main__":
    main()
