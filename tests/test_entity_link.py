"""D2 实体链接第一版：规则归并 + 同名异体隔离（确定性、可审计）。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "services" / "rag-alg" / "index_data_service"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_engine_adapter.assertions import Assertion, AssertionStore, SourceRef  # noqa: E402
from graph_engine_adapter import entity_link  # noqa: E402


def _store_with(name_a, name_b, fact_a=None, fact_b=None):
    s = AssertionStore()
    s.register_entity(f"ent:{name_a}", name_a, f"ent:{name_a}")
    s.register_entity(f"ent:{name_b}", name_b, f"ent:{name_b}")
    ref = SourceRef(file_id="f-1", locator="p1", artifact_id="a1")
    if fact_a:
        s.add(Assertion(subject=fact_a[0], predicate=fact_a[1], object_entity=fact_a[2],
                        sources=[ref]))
    if fact_b:
        ref2 = SourceRef(file_id="f-2", locator="p2", artifact_id="a2")
        s.add(Assertion(subject=fact_b[0], predicate=fact_b[1], object_entity=fact_b[2],
                        sources=[ref2]))
    return s


def test_alias_collision_merges_and_sources_union():
    """华东精密 vs 华东精密有限公司（仅法律后缀）→ 同一实体；同谓词事实合账、来源并集。"""
    s = _store_with(
        "华东精密", "华东精密有限公司",
        ("ent:华东精密", "拟申请", "ent:星航贷"),
        ("ent:华东精密有限公司", "拟申请", "ent:星航贷"),
    )
    out, report = entity_link.apply_linking(s)
    assert report["merged_count"] == 1
    assert report["merged_groups"][0]["alias_key"] == "华东精密"
    assert out.resolve("华东精密") == out.resolve("华东精密有限公司")
    # 归并后同一 (subject,predicate,object) 合账为一条，两来源并集
    merged = [a for a in out._assertions.values() if a.predicate == "拟申请"]
    assert len(merged) == 1
    keys = {src.file_id for src in merged[0].sources}
    assert keys == {"f-1", "f-2"}
    assert report["entities_after"] == report["entities_before"] - 1


def test_homonym_list_keeps_separate(tmp_path):
    """同名异体名单：华东精密 vs 华东精密有限公司 永不归并。"""
    hom = tmp_path / "homonyms.json"
    hom.write_text('{"schema":"x","separate":[["华东精密","华东精密有限公司"]]}',
                   encoding="utf-8")
    s = _store_with("华东精密", "华东精密有限公司")
    out, report = entity_link.apply_linking(s, entity_link.load_homonyms(str(hom)))
    assert report["merged_count"] == 0
    assert report["kept_separate"][0]["alias_key"] == "华东精密"
    assert out.resolve("华东精密") != out.resolve("华东精密有限公司")
    assert report["entities_after"] == report["entities_before"]


def test_different_alias_keys_never_merge():
    s = _store_with("智造贷", "星航贷")
    out, report = entity_link.apply_linking(s)
    assert report["merged_count"] == 0
    assert out.resolve("智造贷") != out.resolve("星航贷")


def test_idempotent_and_deterministic():
    s = _store_with(
        "华东精密", "华东精密有限公司",
        ("ent:华东精密", "拟申请", "ent:星航贷"),
    )
    out1, r1 = entity_link.apply_linking(s)
    out2, r2 = entity_link.apply_linking(out1)
    assert r1["merged_count"] == 1
    assert r2["merged_count"] == 0  # 已归并，再跑无变化
    assert sorted(out2._entities) == sorted(out1._entities)
    assert {a.content_key() for a in out2._assertions.values()} == {
        a.content_key() for a in out1._assertions.values()}


def test_orphan_remapped():
    s = AssertionStore()
    s.register_entity("ent:华东精密", "华东精密", "ent:华东精密")
    s.register_entity("ent:华东精密有限公司", "华东精密有限公司",
                      "ent:华东精密有限公司")
    s._orphans.add("ent:华东精密有限公司")
    out, report = entity_link.apply_linking(s)
    kept = out.resolve("华东精密")
    assert kept is not None and kept in out._orphans
    assert report["entities_after"] == 1
