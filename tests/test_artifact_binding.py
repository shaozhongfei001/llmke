"""doc2md 产物绑定（D1）的反证：合法产物能绑，被改/缺定位/缺身份的一律拒绝。

为什么要独立重算期望值：如果测试里的期望哈希来自被测模块自己的常量/工具函数，
那么"聚合口径被改坏"这类缺陷会连同期望值一起漂移，测试永远绿（假绿）。
所以下面 `expected_content_hash()` 里的 schema 标记与序列化参数是**手写常量**，
模块改了聚合口径它就会失败。
"""

import hashlib
import json

import pytest

from graph_engine_adapter.artifact_binding import (
    ArtifactBindingError, assert_same_artifact, bind_artifact)

ARTIFACT = "a" * 64


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def expected_content_hash(pairs):
    """按 D1 口径独立重算：有序的 [(locator_key, text)] → 聚合哈希。

    spec 字符串是手写的，不从模块 import：口径一改就必须在这里显式同步。
    """
    manifest = [{"locator": locator, "text_sha256": text_hash(text)} for locator, text in pairs]
    payload = {"schema": "llmke.artifact-binding.chunks/1", "chunks": manifest}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


PARA = "产品甲的单笔最高额度为8000万元，期限不超过三年。"
CELL = "产品乙 | 利率 | 4.35%"


def sample_artifact():
    return {
        "artifact_id": ARTIFACT,
        "document_id": "DOC-001",
        "chunks": [
            {"text": PARA, "locator": "p1", "file_id": "F-001"},
            {"text": CELL, "locator": "table:r2", "file_id": "F-001"},
        ],
    }


# ---------------------------------------------------------------- 1. 合法 2 块
def test_bind_two_chunks_keeps_order_and_hash():
    out = bind_artifact(sample_artifact())

    assert out["artifact_id"] == ARTIFACT
    assert out["document_id"] == "DOC-001"
    assert [d["locator"] for d in out["docs"]] == ["p1", "table:r2"]     # 顺序与输入一致
    assert [d["text"] for d in out["docs"]] == [PARA, CELL]             # 正文逐字未改
    assert all(d["artifact_id"] == ARTIFACT for d in out["docs"])       # 每块都带产物身份
    assert all(d["file_id"] == "F-001" for d in out["docs"])
    assert out["content_hash"] == expected_content_hash([("p1", PARA), ("table:r2", CELL)])


def test_file_id_falls_back_to_document_id():
    art = sample_artifact()
    for chunk in art["chunks"]:
        chunk.pop("file_id")
    out = bind_artifact(art)
    assert [d["file_id"] for d in out["docs"]] == ["DOC-001", "DOC-001"]


def test_chunk_declared_hash_matching_is_accepted():
    art = sample_artifact()
    art["chunks"][0]["text_sha256"] = text_hash(PARA)
    out = bind_artifact(art)
    assert out["docs"][0]["text"] == PARA


# ------------------------------------------------------- 2. artifact_id 非 64 hex
@pytest.mark.parametrize("bad_id", [
    "",                              # 空
    "a" * 63, "a" * 65,              # 长度不对
    "A" * 64,                        # 大写：下游哈希拼接要求小写定长
    "g" * 64,                        # 非十六进制字符
    "art-0001",                      # 人类可读 id
    None, 12345,                     # 类型不对
])
def test_bad_artifact_id_rejected(bad_id):
    art = sample_artifact()
    art["artifact_id"] = bad_id
    with pytest.raises(ArtifactBindingError):
        bind_artifact(art)


# ------------------------------------------------------------ 3. chunk 缺 locator
@pytest.mark.parametrize("bad_locator", [None, "", "   ", {}, {"kind": "made_up"}, 17])
def test_missing_locator_rejected(bad_locator):
    art = sample_artifact()
    if bad_locator is None:
        art["chunks"][1].pop("locator")
    else:
        art["chunks"][1]["locator"] = bad_locator
    with pytest.raises(ArtifactBindingError) as exc:
        bind_artifact(art)
    assert "locator" in str(exc.value)


def test_structured_locator_from_contract_is_accepted():
    """合同里 locator 是对象（TextLocator/CellLocator/FigureLocator），不能只认字符串。"""
    art = sample_artifact()
    art["chunks"][1]["locator"] = {"kind": "table_cell", "table_id": "T1",
                                   "row": 2, "col": 1, "cell_text_hash": text_hash(CELL)}
    out = bind_artifact(art)
    assert out["docs"][1]["locator"]["table_id"] == "T1"


def test_locator_key_order_does_not_change_content_hash():
    """同一份产物的 locator 对象换个键序，content_hash 必须不变（否则误报产物被改）。"""
    loc = {"kind": "table_cell", "table_id": "T1", "row": 2, "col": 1}
    art_a = sample_artifact()
    art_a["chunks"][1]["locator"] = dict(loc)
    art_b = sample_artifact()
    art_b["chunks"][1]["locator"] = {k: loc[k] for k in reversed(list(loc))}
    assert bind_artifact(art_a)["content_hash"] == bind_artifact(art_b)["content_hash"]


# --------------------------------------------------------- 4. 自带 hash 不匹配
def test_declared_hash_mismatch_rejected():
    art = sample_artifact()
    art["chunks"][0]["text_sha256"] = text_hash("产品甲的单笔最高额度为9000万元。")
    with pytest.raises(ArtifactBindingError) as exc:
        bind_artifact(art)
    assert "text_sha256" in str(exc.value)


def test_declared_hash_not_hex_rejected():
    """带了个不是哈希的值同样拒绝：无法校验的"校验字段"等于没有校验。"""
    art = sample_artifact()
    art["chunks"][0]["content_hash"] = "not-a-hash"
    with pytest.raises(ArtifactBindingError):
        bind_artifact(art)


# ----------------------------------------------------------------- 5. 空 chunks
@pytest.mark.parametrize("bad_chunks", [[], None, "p1"])
def test_empty_chunks_rejected(bad_chunks):
    art = sample_artifact()
    if bad_chunks is None:
        art.pop("chunks")
    else:
        art["chunks"] = bad_chunks
    with pytest.raises(ArtifactBindingError):
        bind_artifact(art)


def test_empty_text_rejected():
    art = sample_artifact()
    art["chunks"][0]["text"] = "  "
    with pytest.raises(ArtifactBindingError):
        bind_artifact(art)


# --------------------------------------------------- 6. assert_same_artifact
def test_assert_same_artifact_passes_for_same_product():
    a = bind_artifact(sample_artifact())
    b = bind_artifact(sample_artifact())
    assert_same_artifact(a, b)          # 不抛错即通过（返回 None）


def test_assert_same_artifact_rejects_different_artifact_id():
    a = bind_artifact(sample_artifact())
    art = sample_artifact()
    art["artifact_id"] = "b" * 64
    b = bind_artifact(art)
    with pytest.raises(ArtifactBindingError) as exc:
        assert_same_artifact(a, b)
    assert "artifact_id" in str(exc.value)


def test_assert_same_artifact_rejects_same_id_different_content():
    """同编号不同内容 = 产物被原地改写，必须拦住。"""
    a = bind_artifact(sample_artifact())
    art = sample_artifact()
    art["chunks"][0]["text"] = PARA.replace("8000", "9000")
    b = bind_artifact(art)
    assert b["artifact_id"] == a["artifact_id"]
    with pytest.raises(ArtifactBindingError) as exc:
        assert_same_artifact(a, b)
    assert "content_hash" in str(exc.value)


def test_assert_same_artifact_rejects_reordered_chunks():
    """块序变了就是另一个产物：引用会指向不同位置。"""
    a = bind_artifact(sample_artifact())
    art = sample_artifact()
    art["chunks"] = list(reversed(art["chunks"]))
    b = bind_artifact(art)
    assert b["content_hash"] != a["content_hash"]
    with pytest.raises(ArtifactBindingError):
        assert_same_artifact(a, b)


def test_assert_same_artifact_rejects_unbound_input():
    with pytest.raises(ArtifactBindingError):
        assert_same_artifact({"artifact_id": ARTIFACT}, bind_artifact(sample_artifact()))
