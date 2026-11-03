"""社区与 global 报告：只吃**经校验的标准事实导出**，不直接读引擎内部结构。

设计依据（§6.4）：社区/global 由独立处理器消费经原文和本体校验的标准事实导出；
若导出不足以支持，状态应为 BLOCKED/NOT_READY，**不得用普通 RAG 顶替**。

所以这里的输入是 `AssertionStore`（平台断言层），不是 HippoRAG 的图对象。
三件事分得很开：
1. `export_facts`：只放行"来源存在且在可见集合内"的事实，其余计入 excluded 并写明原因；
2. `build_communities`：在**实体-实体**关系上做标签传播（确定性顺序，可复现），
   孤点单独成社区并在报告里标 `isolated`；
3. `build_report`：每个社区给出成员、代表事实、来源；再逐条校验引用能否回到真实来源。

不产出"看起来很权威"的自然语言结论：叙述是可选步骤，且必须带可核验引用。
"""

import json
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set

from .assertions import Assertion, AssertionStore

SCHEMA = "llmke.graph-engine.community.v1"


def export_facts(store: AssertionStore, known_files: Iterable[str]) -> Dict[str, Any]:
    """标准事实导出：只保留来源可解析的事实，排除项逐条给原因。"""
    known = set(known_files)
    exported, excluded = [], []
    for assertion in store._assertions.values():
        files = {s.file_id for s in assertion.sources}
        if not files:
            excluded.append({"reason": "NO_SOURCE", "fact": store.render(assertion)})
            continue
        missing = sorted(files - known)
        if missing:
            # 引用失效：宁可导出时剔除，也不让报告引用一个看不见的文件
            excluded.append({"reason": "SOURCE_NOT_VISIBLE", "fact": store.render(assertion),
                             "files": missing})
            continue
        if assertion.object_entity is None and assertion.object_value is None:
            excluded.append({"reason": "EMPTY_OBJECT", "fact": store.render(assertion)})
            continue
        exported.append(assertion)

    return {"facts": exported,
            "stats": {"total": len(store._assertions), "exported": len(exported),
                      "excluded": len(excluded)},
            "excluded": excluded[:20]}


def _edges(facts: Sequence[Assertion]) -> Dict[str, Set[str]]:
    adj: Dict[str, Set[str]] = defaultdict(set)
    for fact in facts:
        if fact.object_entity is None:
            continue
        adj[fact.subject].add(fact.object_entity)
        adj[fact.object_entity].add(fact.subject)   # 社区用无向连通性，方向语义在断言里保留
    return adj


def build_communities(facts: Sequence[Assertion], *, min_size: int = 2,
                      max_rounds: int = 20) -> List[Dict[str, Any]]:
    """标签传播（确定性）。

    为什么要确定性：社区编号会进报告与后续引用，随机结果无法复现、无法对比。
    遍历顺序按实体 id 排序，平票取字典序最小标签。
    """
    adj = _edges(facts)
    nodes = sorted(set(adj) | {f.subject for f in facts})
    labels = {n: n for n in nodes}

    for _ in range(max_rounds):
        changed = False
        for node in nodes:
            neighbours = adj.get(node) or set()
            if not neighbours:
                continue
            counts: Dict[str, int] = defaultdict(int)
            for nb in sorted(neighbours):
                counts[labels[nb]] += 1
            best = max(sorted(counts), key=lambda lab: counts[lab])
            if best != labels[node]:
                labels[node] = best
                changed = True
        if not changed:
            break

    groups: Dict[str, List[str]] = defaultdict(list)
    for node in nodes:
        groups[labels[node]].append(node)

    communities = []
    for index, (cid, members) in enumerate(
            sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])), start=1):
        # 编号用序号而不是实体 id：报告要给人看，且保持确定性（排序已稳定）
        communities.append({"id": f"c-{index}", "anchor": cid, "entities": sorted(members),
                            "size": len(members), "isolated": len(members) == 1})
    # min_size 只影响"是否突出展示"，不丢成员
    for c in communities:
        c["flagged_small"] = c["size"] < min_size
    return communities


def build_report(store: AssertionStore, known_files: Iterable[str], *,
                 max_facts_per_community: int = 5) -> Dict[str, Any]:
    """生成结构化 global 报告（不含自然语言结论），并逐条校验引用。"""
    known = set(known_files)
    export = export_facts(store, known)
    facts = export["facts"]
    communities = build_communities(facts)

    by_entity: Dict[str, List[Assertion]] = defaultdict(list)
    for fact in facts:
        by_entity[fact.subject].append(fact)

    sections = []
    for community in communities:
        picked: List[Assertion] = []
        for entity in community["entities"]:
            picked.extend(by_entity.get(entity, []))
        seen, uniq = set(), []
        for fact in picked:
            key = fact.content_key()
            if key in seen:
                continue
            seen.add(key)
            uniq.append(fact)
        sections.append({
            "community": community["id"], "size": community["size"],
            "isolated": community["isolated"], "entities": community["entities"],
            "facts": [{"text": store.render(f), "sources": sorted({s.file_id for s in f.sources})}
                      for f in uniq[:max_facts_per_community]],
            "fact_count": len(uniq),
            "sources": sorted({s.file_id for f in uniq for s in f.sources}),
        })

    citations = validate_report_citations(sections, known)
    status = "READY" if facts and not citations["invalid"] else (
        "BLOCKED" if not facts else "PARTIAL")
    return {"schema": SCHEMA, "status": status,
            "export": export["stats"], "excluded": export["excluded"],
            "communities": sections,
            "citations": citations,
            "policy": "global 报告只消费经原文与可见性校验的标准事实；不可用普通 RAG 顶替"}


def validate_report_citations(sections: Sequence[Dict[str, Any]],
                              known_files: Iterable[str]) -> Dict[str, List[str]]:
    known = set(known_files)
    valid, invalid = [], []
    for section in sections:
        for fact in section["facts"]:
            for fid in fact["sources"]:
                label = f"{section['community']}:{fid}:{fact['text'][:20]}"
                (valid if fid in known else invalid).append(label)
    return {"valid": sorted(set(valid)), "invalid": sorted(set(invalid))}


def narrate(report: Dict[str, Any], llm_call: Callable[..., Any],
            *, max_communities: int = 3) -> Dict[str, Any]:
    """可选：让模型给社区写一段说明。每个社区单独一次调用，引用由平台回填。"""
    notes = []
    for section in report["communities"][:max_communities]:
        materials = "\n".join(f"- {f['text']}（file_id={','.join(f['sources'])}）"
                              for f in section["facts"])
        prompt = ("下面的材料是同一组实体的事实。请用一句中文概括，"
                  "不要引入材料外信息，不要编造数字。\n" + materials)
        try:
            text = llm_call(messages=[{"role": "user", "content": prompt}])
        except Exception as exc:  # noqa: BLE001
            notes.append({"community": section["community"], "error": f"{type(exc).__name__}: {exc}"})
            continue
        notes.append({"community": section["community"], "text": str(text)[:300],
                      "sources": section["sources"]})
    return {"schema": "llmke.graph-engine.community.narrative.v1",
            "notes": notes,
            "note": "叙述是可选产物，事实与引用以 build_report 的结构化结果为准"}
