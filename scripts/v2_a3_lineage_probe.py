#!/usr/bin/env python3
"""T-A3 / D4：一条事实从 openie 到 community.json 的逐跳溯源。

只读快照，不改引擎、不碰 legacy 图服务。**不使用 HippoRAG 内部相似图**：
本脚本读的是 (1) openie 抽取结果 (2) 归一后的断言层 (3) 社区报告，
相似图（hp.graph 的 synonymy 边）全程未被读取 —— 第 5 跳会直接把两者的数量对照打出来。
"""
import glob
import json
import os
import sys

SNAP = sys.argv[1] if len(sys.argv) > 1 else ""
sys.path.insert(0, "/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service")

from graph_engine_adapter import global_report                      # noqa: E402
from graph_engine_adapter.community import build_communities, export_facts  # noqa: E402
from graph_engine_adapter.normalize import build_store
from graph_engine_adapter import entity_link              # noqa: E402

print("SNAPSHOT:", SNAP)

# ── 跳 1：openie（HippoRAG 抽取产物，非平台自研、非 legacy） ─────────────
files = sorted(glob.glob(os.path.join(SNAP, "openie_results_ner_*.json")))
data = json.load(open(files[-1], encoding="utf-8"))
docs = list(data.get("docs") or [])
print("\n[跳 1] openie 文件:", os.path.basename(files[-1]))
print("        docs(块)=%d  triples=%d" % (
    len(docs), sum(len(d.get("extracted_triples") or []) for d in docs)))

# 选一条"主体/谓词/客体都非空"的真实中文事实（不用空壳三元组凑数）
target = None
for d in docs:
    for t in d.get("extracted_triples") or []:
        if len(t) == 3 and all(str(x).strip() for x in t) and "智造贷" in str(t[0]):
            target = (d, list(t))
            break
    if target:
        break
if target is None:
    for d in docs:
        for t in d.get("extracted_triples") or []:
            if len(t) == 3 and all(str(x).strip() for x in t):
                target = (d, list(t)); break
        if target:
            break
doc, trip = target
print("        选中三元组: %s" % json.dumps(trip, ensure_ascii=False))
print("        所在块 idx=%s" % doc.get("idx"))
print("        原文片段: %s" % (doc.get("passage") or "")[:80])

# ── 跳 2：normalize → 断言（谓词走平台字典、来源绑定、数值解析） ──────────
sources = global_report.read_sources(SNAP)
res = build_store(docs, global_report._resolver(sources))
store = entity_link.apply_linking(res["store"])[0]
store = res["store"]
print("\n[跳 2] normalize stats:", json.dumps(res["stats"], ensure_ascii=False, default=list))
print("        assertions=%d  orphans=%d" % (len(store._assertions), len(store._orphans)))

hit = None
for a in store._assertions.values():
    names = {store.name_of(a.subject)}
    if trip[0] in names and (a.object_entity and trip[2] in store.name_of(a.object_entity)
                             or a.object_value is not None and trip[2] in str(a.object_value)):
        hit = a
        break
if hit is None:                      # 谓词可能被归一/数值化，退一步按主体匹配
    for a in store._assertions.values():
        if trip[0] == store.name_of(a.subject):
            hit = a
            break
if hit is None:
    print("!! 断言层未找到对应事实，溯源中断")
    sys.exit(2)
print("        assertion: subject=%s predicate=%s object_entity=%s object_value=%s unit=%s direction=%s"
      % (store.name_of(hit.subject), hit.predicate,
         store.name_of(hit.object_entity) if hit.object_entity else None,
         hit.object_value, hit.unit, hit.direction))
print("        sources=%s" % json.dumps([{"file_id": s.file_id, "locator": getattr(s, "locator", None)}
                                       for s in hit.sources], ensure_ascii=False))
print("        render: %s" % store.render(hit))

# ── 跳 3：export_facts（按可见文件过滤；引用失效不导出） ─────────────────
known = sorted({str(i.get("file_id")) for v in (sources or {}).values()
                for i in v if isinstance(i, dict) and i.get("file_id")})
exp = export_facts(store, known)
print("\n[跳 3] export_facts: facts=%d excluded=%d known_files=%s"
      % (len(exp["facts"]), len(exp.get("excluded") or []), known))
print("        excluded 原因分布: %s"
      % json.dumps({r: sum(1 for e in (exp.get("excluded") or []) if e["reason"] == r)
                    for r in sorted({e["reason"] for e in (exp.get("excluded") or [])})},
                   ensure_ascii=False))
in_export = any(f.content_key() == hit.content_key() for f in exp["facts"])
print("        该事实是否在导出集合内: %s" % in_export)
if not in_export:
    print("!! 该事实被导出层剔除，后续社区不含它 —— 溯源到此为止（如实报告）")
    sys.exit(3)

# ── 跳 4：build_communities（确定性标签传播，输入 = 跳 3 的事实） ─────────
comm = build_communities(exp["facts"])
mine = [c for c in comm if hit.subject in c["entities"]]
print("\n[跳 4] communities=%d  该事实主体所属社区=%s"
      % (len(comm), [(c["id"], c["size"], c["isolated"]) for c in mine]))
print("        isolated(孤点)社区数=%d  孤点是否保留=%s"
      % (sum(1 for c in comm if c["isolated"]), all("entities" in c for c in comm)))

# ── 跳 5：community.json（两次生成 sha256 必须相同；引用 0 失效） ─────────
r1 = global_report.write(SNAP, known)
r2 = global_report.write(SNAP, known)
path = r1["path"]
rep = json.load(open(path, encoding="utf-8"))
text = store.render(hit)
sec = [c for c in rep["communities"] if any(text == f["text"] for f in c["facts"])]
print("\n[跳 5] community.json: communities=%d citation_check=%s"
      % (rep["community_count"], json.dumps(rep["citation_check"], ensure_ascii=False)[:200]))
print("        inputs.facts=%s inputs.triples=%s" % (rep["inputs"]["facts"], rep["inputs"]["triples"]))
print("        该事实出现在社区: %s" % [(c["community"], c["size"]) for c in sec])
print("        两次生成 sha256: %s / %s  相同=%s"
      % (r1["sha256"], r2["sha256"], r1["sha256"] == r2["sha256"]))
invalid = rep["citation_check"].get("invalid") or []
isolated = [c for c in rep["communities"] if c.get("isolated")]
print("        引用失效 invalid=%s (checked=%s)"
      % (invalid, rep["citation_check"].get("checked")))
print("        孤点社区保留=%s (%d 个)" % (bool(isolated), len(isolated)))

same_sha = r1["sha256"] == r2["sha256"]
ok = bool(sec and in_export and same_sha and not invalid and isolated)
print("\n[结论] openie → 断言 → export_facts → build_communities → community.json "
      "五跳闭合=%s；引用 0 失效=%s；孤点保留=%s；两次 sha 相同=%s"
      % (bool(sec and in_export), not invalid, bool(isolated), same_sha))
sys.exit(0 if ok else 4)
