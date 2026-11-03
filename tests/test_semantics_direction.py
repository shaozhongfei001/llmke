"""语义方向：有向谓词的双向事实不得被合并，对称谓词的双向事实必须合并。

外部评审 B01 的问题形态是"关系去重用无序键 → `甲 -担保-> 乙` 与 `乙 -担保-> 甲` 落成同一条，
只留先到者"。这里的断言直接盯住 normalize.build_store 归一后的结果：

1. 非对称谓词（担保/控制/任职/未知）：两个方向是两条事实，都必须留下；
2. 对称谓词（相似/关联）：两个方向是同一条事实，合并成一条，来源合并；
3. 未知谓词默认非对称（宁可重复，也不猜方向）；
4. 去重键不依赖输入顺序，同一方向重复只留一条且来源合并；
5. 三角关系（甲→乙、乙→丙、甲→丙）是三条不同事实，不能被误合成一条。
"""

from graph_engine_adapter.assertions import FORWARD, SYMMETRIC, SourceRef
from graph_engine_adapter.normalize import (SYMMETRIC_PREDICATES, build_store, dedup_key,
                                            entity_id, predicate_direction)

ENTITIES = ("甲", "乙", "丙")


def ref(file_id="f1", locator="0-10"):
    return SourceRef(file_id=file_id, artifact_id="a" * 64, channel="text", locator=locator)


def make_store(docs_triples):
    """每个 doc 一个独立来源，便于检查"来源合并"而不只是"条数对"。"""
    docs = [{"idx": f"chunk-{i}", "extracted_triples": list(triples)}
            for i, triples in enumerate(docs_triples)]
    return build_store(docs, lambda idx: [ref(idx)])


def facts_of(store, names=ENTITIES):
    """按内容键去重地取出涉及这些端点的断言（对称谓词的 subject 可能是任一端点）。"""
    found = {}
    for name in names:
        for assertion in store.facts(entity_id(name)):
            found[assertion.content_key()] = assertion
    return list(found.values())


def triples(store, names=ENTITIES):
    return {(a.predicate, store.name_of(a.subject), store.name_of(a.object_entity))
            for a in facts_of(store, names)}


# ---------- 1. 非对称谓词：两个方向都保留 ----------

def test_directed_predicate_keeps_both_directions():
    out = make_store([[["甲", "担保", "乙"], ["乙", "担保", "甲"]]])
    store = out["store"]

    rows = facts_of(store)
    assert len(rows) == 2, rows
    assert store.stats()["assertions"] == 2
    assert triples(store) == {("担保", "甲", "乙"), ("担保", "乙", "甲")}
    # 两个方向各自可查：谁担保谁没有被丢掉
    assert store.related(entity_id("甲"), "担保", entity_id("乙")) is True
    assert store.related(entity_id("乙"), "担保", entity_id("甲")) is True
    # 丢了哪条都能看出来：facts_out 与断言数一致
    assert out["stats"]["facts_out"] == 2


def test_directed_predicates_control_and_employment_both_kept():
    out = make_store([[["甲", "控制", "乙"], ["乙", "控制", "甲"],
                       ["甲", "任职", "乙"], ["乙", "任职", "甲"]]])
    store = out["store"]

    assert len(facts_of(store)) == 4
    assert triples(store) == {
        ("控制", "甲", "乙"), ("控制", "乙", "甲"),
        ("任职", "甲", "乙"), ("任职", "乙", "甲"),
    }
    # 方向没有被抹平：控制关系两边都在，且都是 forward
    assert {a.direction for a in facts_of(store)} == {FORWARD}


# ---------- 2. 输入顺序不得影响结果 ----------

def test_result_does_not_depend_on_input_order():
    forward = [["甲", "担保", "乙"], ["乙", "担保", "甲"],
               ["甲", "相似", "乙"], ["乙", "相似", "甲"]]
    a = make_store([forward])
    b = make_store([list(reversed(forward))])

    assert triples(a["store"]) == triples(b["store"])
    assert a["store"].stats()["assertions"] == b["store"].stats()["assertions"] == 3
    assert {a2.direction for a2 in facts_of(a["store"])} == {FORWARD, SYMMETRIC}


# ---------- 3. 同方向重复：留一条，来源合并 ----------

def test_same_direction_duplicate_merges_sources():
    out = make_store([[["甲", "担保", "乙"]], [["甲", "担保", "乙"]]])
    store = out["store"]

    rows = facts_of(store)
    assert len(rows) == 1, rows
    assert store.stats()["assertions"] == 1
    assert {s.file_id for s in rows[0].sources} == {"chunk-0", "chunk-1"}
    # 输入两条、输出一条，但这不是丢事实：来源都在同一条断言上
    assert out["stats"]["facts_out"] == 2


# ---------- 4. 对称谓词：双向合并成一条 ----------

def test_symmetric_predicate_merges_both_directions():
    out = make_store([[["甲", "相似", "乙"]], [["乙", "相似", "甲"]]])
    store = out["store"]

    rows = facts_of(store)
    assert len(rows) == 1, rows
    assert rows[0].direction == SYMMETRIC
    assert store.related(entity_id("甲"), "相似", entity_id("乙")) is True
    assert store.related(entity_id("乙"), "相似", entity_id("甲")) is True
    # 合并而不是丢弃：两个方向的来源都要在同一条上
    assert {s.file_id for s in rows[0].sources} == {"chunk-0", "chunk-1"}


def test_symmetric_predicate_guanlian_merged_too():
    out = make_store([[["甲", "关联", "乙"], ["乙", "关联", "甲"]]])
    store = out["store"]

    assert len(facts_of(store)) == 1
    assert store.stats()["assertions"] == 1


# ---------- 5. 未知谓词默认非对称 ----------

def test_unknown_predicate_defaults_to_forward_and_keeps_two():
    out = make_store([[["甲", "随手写的", "乙"], ["乙", "随手写的", "甲"]]])
    store = out["store"]

    assert len(facts_of(store)) == 2
    assert triples(store) == {("随手写的", "甲", "乙"), ("随手写的", "乙", "甲")}
    assert {a.direction for a in facts_of(store)} == {FORWARD}
    # 未知谓词不会被登记成对称，也不在显式对称表里
    assert predicate_direction("随手写的") == FORWARD
    assert "随手写的" not in SYMMETRIC_PREDICATES


def test_dedup_key_is_ordered_for_asymmetric_and_unordered_for_symmetric():
    a, b = entity_id("甲"), entity_id("乙")

    # 非对称：正反两向键不同（有向事实不会被合并）
    assert dedup_key("担保", a, b) != dedup_key("担保", b, a)
    assert dedup_key("担保", a, b) == ("担保", a, b)
    # 对称：正反两向键相同（无序键）
    assert dedup_key("相似", a, b) == dedup_key("相似", b, a)
    # 显式表就是唯一判据
    assert predicate_direction("相似") == SYMMETRIC
    assert predicate_direction("关联") == SYMMETRIC
    assert predicate_direction("担保") == FORWARD


# ---------- 6. 三角关系不能被误合 ----------

def test_triangle_triples_are_not_merged():
    out = make_store([[["甲", "担保", "乙"], ["乙", "担保", "丙"], ["甲", "担保", "丙"]]])
    store = out["store"]

    assert len(facts_of(store)) == 3
    assert store.stats()["assertions"] == 3
    assert triples(store) == {("担保", "甲", "乙"), ("担保", "乙", "丙"), ("担保", "甲", "丙")}
