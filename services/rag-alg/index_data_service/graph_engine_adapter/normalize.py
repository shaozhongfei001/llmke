"""把引擎抽取结果归一进平台断言层。

分工要说清楚：引擎抽出来的三元组**不是**业务事实，只是候选。这里做三件有边界的事：
1. 谓词归一：只查**显式字典**，查不到就原样保留（不猜、不模糊匹配）；
2. 数值解析：`"8000万元"` → 8000 + 万元；解析不出数值的当实体关系处理；
3. 来源绑定：每条事实必须能对回真实 SourceRef，对不上的**丢弃并计数**，不许挂空来源。

被丢弃的事实和未归一的谓词都要出现在 stats 里——它们是"抽取质量"的真实度量，
藏起来会让后续"图里有答案"的判断失真。
"""

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .assertions import FORWARD, SYMMETRIC, Assertion, AssertionStore, SourceRef

SCHEMA = "llmke.graph-engine.normalize.v1"

# 只归一"同一个意思的几种写法"，不做语义联想。未列出的谓词一律保留原名。
PREDICATE_MAP = {
    "最高额度为": "额度",
    "最高额度": "额度",
    "额度为": "额度",
    "授信额度为": "额度",
    "授信额度": "额度",
    "担保方式为保证": "担保方式",
    "担保方式为": "担保方式",
    "申请": "申请",
    "是": "是",
}

_NUM_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*([万亿千百]?元|个月|年|%|天|倍)?\s*$")
_UNIT_ALIAS = {"亿元": "万元", "千元": "元"}

# 谓词的方向语义必须**显式**，不允许靠猜。
# 只有这里列出的谓词，`甲 -X-> 乙` 与 `乙 -X-> 甲` 才被认定为**同一条事实**（去重键无序）。
# 不在表里的谓词一律按**非对称**处理，两个方向各存一条。
#
# 为什么默认非对称：两类错误的代价不对称。
#   · 误合并（把有向谓词当对称）：`乙 -担保-> 甲` 这条真实事实被整条丢掉，
#     而且丢掉之后从图里看不出来——facts_out 照样计数，只有断言数少一条，
#     下游"图里有答案"的判断会被悄悄带偏；
#   · 多留一条（把对称谓词当有向）：最坏只是同一事实重复一次，可去重、可核对，不会失真。
# 所以查不到就保留两条：宁可重复，也不替抽取结果猜方向。
SYMMETRIC_PREDICATES = {"相似", "关联"}


def predicate_direction(predicate: str) -> str:
    """谓词方向：显式字典命中 → symmetric，其余一律 forward。"""
    return SYMMETRIC if predicate in SYMMETRIC_PREDICATES else FORWARD


def dedup_key(predicate: str, subject_id: str, object_id: str) -> Tuple[str, str, str]:
    """事实去重键 —— **这是唯一决定"两条三元组算不算同一事实"的地方**。

    非对称谓词：(predicate, subject, object)，有序。`甲 -担保-> 乙` 与 `乙 -担保-> 甲`
                键不同，两个方向都保留；
    对称谓词  ：端点先排序再用，即无序键。正反两向键相同，交给 AssertionStore 按内容合并
                （来源会合并到同一条断言上，事实不丢）。

    副作用要说明白：对称谓词的断言以"排序在前的端点"作 subject，所以
    `store.facts(某个端点)` 对对称谓词只命中排序在前的那一侧；方向无关的查询请用
    `store.related()`（它认 direction="symmetric"，两个方向都返回 True）。
    """
    if predicate_direction(predicate) == SYMMETRIC and object_id < subject_id:
        return (predicate, object_id, subject_id)
    return (predicate, subject_id, object_id)


def normalize_predicate(raw: str) -> str:
    key = (raw or "").strip()
    return PREDICATE_MAP.get(key, key)


def parse_number(text: str) -> Optional[Dict[str, Any]]:
    """`"8000万元"` → {'value': 8000.0, 'unit': '万元'}；纯数字无单位返回 None（缺单位不可入账）。"""
    m = _NUM_RE.match(str(text or ""))
    if not m:
        return None
    value, unit = m.group(1), m.group(2)
    if not unit:
        return None
    value_f = float(value)
    unit = _UNIT_ALIAS.get(unit, unit)
    if _UNIT_ALIAS.get(m.group(2)) == "万元" and m.group(2) == "亿元":
        value_f *= 10000.0
    return {"value": value_f, "unit": unit}


def entity_id(name: str) -> str:
    cleaned = re.sub(r"\s+", "", str(name or "")).lower()
    return "ent:" + cleaned if cleaned else ""


@dataclass
class NormalizeStats:
    facts_in: int = 0
    facts_out: int = 0
    dropped_no_source: int = 0
    dropped_empty: int = 0
    numeric: int = 0
    relational: int = 0
    unmapped_predicates: Set[str] = field(default_factory=set)


def build_store(docs: Sequence[Dict[str, Any]],
                source_resolver: Callable[[str], Sequence[SourceRef]],
                store: Optional[AssertionStore] = None,
                *, visibility: Optional[Set[str]] = None) -> Dict[str, Any]:
    """`docs` 形如 hipporag openie 输出：[{idx, passage, extracted_triples, ...}]。"""
    store = store or AssertionStore()
    stats = NormalizeStats()
    vis = visibility or {"public"}

    for doc in docs:
        idx = doc.get("idx") or ""
        refs = list(source_resolver(idx))
        if not refs:
            stats.dropped_no_source += len(doc.get("extracted_triples") or [])
            continue
        for triple in doc.get("extracted_triples") or []:
            stats.facts_in += 1
            if not isinstance(triple, (list, tuple)) or len(triple) != 3:
                stats.dropped_empty += 1
                continue
            subj, pred, obj = (str(x).strip() for x in triple)
            if not subj or not pred or not obj:
                stats.dropped_empty += 1
                continue

            predicate = normalize_predicate(pred)
            if predicate == pred and pred not in PREDICATE_MAP.values():
                stats.unmapped_predicates.add(pred)

            sid = entity_id(subj)
            store.register_entity(sid, subj, entity_id(subj))

            numeric = parse_number(obj)
            if numeric:
                store.add(Assertion(subject=sid, predicate=predicate,
                                    object_value=numeric["value"], unit=numeric["unit"],
                                    key=predicate, sources=refs, visibility=set(vis)))
                stats.numeric += 1
            elif obj.endswith(("万元", "亿元", "元")) and parse_number(obj) is None:
                # 看着是金额但解析不出数值：不当数值断言，也不猜，按关系存并记 unmapped
                store.add(Assertion(subject=sid, predicate=predicate, object_entity=entity_id(obj),
                                    qualifiers={"raw_object": obj}, sources=refs,
                                    visibility=set(vis)))
                stats.relational += 1
            else:
                oid = entity_id(obj)
                store.register_entity(oid, obj, oid)
                # 方向语义与去重键在此决定：对称谓词端点排序后入账（正反两向并一条），
                # 其余保持 甲→乙 的原序（两个方向是两条事实）。
                _, subj_id, obj_id = dedup_key(predicate, sid, oid)
                store.add(Assertion(subject=subj_id, predicate=predicate, object_entity=obj_id,
                                    direction=predicate_direction(predicate),
                                    sources=refs, visibility=set(vis)))
                stats.relational += 1
            stats.facts_out += 1

    return {"schema": SCHEMA, "store": store,
            "stats": {"facts_in": stats.facts_in, "facts_out": stats.facts_out,
                      "dropped_no_source": stats.dropped_no_source,
                      "dropped_empty": stats.dropped_empty,
                      "numeric": stats.numeric, "relational": stats.relational,
                      "unmapped_predicates": sorted(stats.unmapped_predicates),
                      "store": store.stats()}}
