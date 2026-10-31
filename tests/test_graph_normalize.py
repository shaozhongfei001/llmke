"""归一化：谓词只查显式字典、数值要单位、来源对不上就丢弃并计数。"""

from graph_engine_adapter.assertions import SourceRef
from graph_engine_adapter.normalize import (build_store, entity_id, normalize_predicate,
                                            parse_number)


def ref(fid="333", loc="0-10"):
    return SourceRef(file_id=fid, artifact_id="a" * 64, channel="text", locator=loc)


def test_predicate_map_only_explicit_entries():
    assert normalize_predicate("最高额度为") == "额度"
    assert normalize_predicate("授信额度") == "额度"
    # 字典里没有的谓词保持原样，不做模糊联想
    assert normalize_predicate("与...存在往来") == "与...存在往来"


def test_parse_number_requires_unit():
    assert parse_number("8000万元") == {"value": 8000.0, "unit": "万元"}
    assert parse_number("12 个月") == {"value": 12.0, "unit": "个月"}
    assert parse_number("1亿元") == {"value": 10000.0, "unit": "万元"}
    assert parse_number("8000") is None          # 无单位不入账
    assert parse_number("很多") is None


def test_numeric_fact_becomes_ledger_entry():
    docs = [{"idx": "chunk-a", "extracted_triples": [["产品甲", "最高额度为", "8000万元"]]}]
    out = build_store(docs, lambda idx: [ref()])
    store = out["store"]
    led = store.ledger("ent:产品甲", "额度")
    assert led["total"] == 8000 and led["unit"] == "万元"
    assert out["stats"]["numeric"] == 1


def test_relational_fact_links_entities():
    docs = [{"idx": "chunk-a", "extracted_triples": [["客户A", "申请", "产品甲"]]}]
    out = build_store(docs, lambda idx: [ref()])
    store = out["store"]
    assert store.related("ent:客户a", "申请", "ent:产品甲") is True
    assert store.related("ent:产品甲", "申请", "ent:客户a") is False
    assert out["stats"]["relational"] == 1


def test_fact_without_source_is_dropped_and_counted():
    docs = [{"idx": "chunk-x", "extracted_triples": [["甲", "额度为", "1万元"]]}]
    out = build_store(docs, lambda idx: [])       # 解析不出来源
    assert out["stats"]["facts_out"] == 0
    assert out["stats"]["dropped_no_source"] == 1
    assert out["store"].stats()["assertions"] == 0


def test_empty_triples_are_counted_not_crash():
    docs = [{"idx": "chunk-a", "extracted_triples": [["甲", "", "1万元"], [], None]}]
    out = build_store(docs, lambda idx: [ref()])
    assert out["stats"]["dropped_empty"] == 3
    assert out["stats"]["facts_out"] == 0


def test_no_source_means_no_assertion_even_if_value_is_nice():
    """来源缺失时宁可丢事实：无来源的事实不可引用，进了图就是脏数据。"""
    docs = [{"idx": "chunk-a", "extracted_triples": [["产品甲", "最高额度为", "8000万元"]]}]
    out = build_store(docs, lambda idx: [])
    assert out["store"].facts("ent:产品甲") == []
    assert out["stats"]["dropped_no_source"] == 1
