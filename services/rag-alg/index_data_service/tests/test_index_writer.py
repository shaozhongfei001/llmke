"""P2-L6 · T-D2MD-06 反例与断言（P2-L6-PLAN.md §二，TL 03:47 派工）。

F1 按 channel 分两份计划且字段形状符合契约 / F2 duplicate_flag=False 硬约束 /
F3 三路 content_hash 同源（B-1）/ F4 delete_scope 按 file_id+pk 精确删除 /
F5 apply 失败带 side 不静默降级；R-1~R-7 对应反例。

**离线**：只产写入计划 + monkeypatch mock 端点；不写线上 ES(19527)/Milvus(19526)/
DB/18094、不启停服务、不切 INGEST_PROJECTION_MODE、默认 v2cand_ 前缀不碰线上索引名。
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/rag-alg/index_data_service"))

from graph_engine_adapter.artifact_binding import (  # noqa: E402
    ArtifactBindingError,
    assert_same_artifact,
)
from ingest_pipeline import index_writer as IW  # noqa: E402
from ingest_pipeline import kb_pipeline as K  # noqa: E402
from rag_projection import projection as P  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "p2_l6"
ART_ID = "c" * 64
UID = "d" * 64
ES_KEYS = {"index_name", "document_list", "type", "duplicate_flag"}
MV_KEYS = {"collection_name", "model_name", "document_list",
           "consistency_level", "duplicate_flag"}


def _chunks() -> list:
    """text + table 混合 chunks（P.project 的产物形状）。"""
    return [
        {"seq": 0, "channel": "text", "pk": 111, "text": "说明如下。",
         "locator": {"kind": "text_span", "source": "parsed_text.md",
                     "start_offset": 0, "end_offset": 5},
         "parse_artifact_id": ART_ID, "content_uid": UID},
        {"seq": 1, "channel": "table", "pk": 222,
         "text": "指标 | 值\n日均存款 | 100",
         "locator": {"kind": "table_ref", "table_id": "t001",
                     "block_id": "b0002"},
         "parse_artifact_id": ART_ID, "content_uid": UID,
         "rows": 2, "cols": 2},
    ]


def _artifact() -> dict:
    """store.commit() 快照 artifact 形状（file_id 由调用点注入，见判断标注）。"""
    return {"schema_version": "llmke-parse-artifact/2.0",
            "artifact_id": ART_ID, "content_uid": UID, "file_id": "333",
            "committed_at": "2026-11-08 00:00:00"}


class _Resp:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"status":"OK"}'


# --------------------------------------------------------------------------- F1 / R-1
def test_f1_two_channel_plans_and_contract_shapes() -> None:
    plan = IW.build(_chunks(), _artifact(), kb="kb_9")
    assert plan.index_prefix == "v2cand_"
    assert plan.es_plan and plan.milvus_plan  # 阶段 A：空计划 → FAIL
    es_by_index = {b["index_name"]: b for b in plan.es_plan}
    mv_by_coll = {b["collection_name"]: b for b in plan.milvus_plan}
    assert set(es_by_index) == {"v2cand_kb_9", "v2cand_table_chunks_kb_9"}
    assert set(mv_by_coll) == {"v2cand_kb_9", "v2cand_table_chunks_kb_9"}
    assert all(n.startswith("v2cand_") for n in es_by_index)  # 不碰线上索引名
    for body in plan.es_plan:
        assert set(body) == ES_KEYS
        assert body["type"] == "" and body["duplicate_flag"] is False
        assert body["document_list"]
    for body in plan.milvus_plan:
        assert set(body) == MV_KEYS
        assert body["model_name"] == "bge-m3"
        assert body["consistency_level"] == "Bounded"
        assert body["duplicate_flag"] is False
        # 原断言是 `body["db_name"] == "kb_9"` —— 它把 bug 写成了期望值：
        # `kb` 与 Milvus database 是两个维度，真实环境 19526 回
        # `database not found[database=kb_9]`（P4-L13C-C3a-R2 证据）。
        # 19526 侧统一兜底 `db_name = db_name or server_config["milvus_database"]`
        # （milvus_kb_service.py:262/:304/:364），`del_doc_by_col` 同样不传。
        assert "db_name" not in body, "不要把 kb 当 Milvus database 发下去"
        assert body["document_list"]
    # document_list 每项 = {page_content, metadata}，顶层 pk/_fill 已剥掉
    for body in plan.es_plan + plan.milvus_plan:
        for doc in body["document_list"]:
            assert set(doc) == {"page_content", "metadata"}
            assert isinstance(doc["page_content"], str)
            meta = doc["metadata"]
            assert isinstance(meta, dict)
            # metadata 由 enrich.build_payload 生成（含生产集合字段）
            assert "chunk_doc_id" in meta and "parse_artifact_id" in meta
            assert meta["content_uid"] == UID
            assert meta["file_id"] == "333"
            # P2-L8：读侧真实依赖的 4 个键必须齐全（TL 12:1x 裁定 Q5）
            assert "source" in meta and "parsed_text_ref" in meta
            assert meta["parsed_text_ref"] in ("parsed_text.md", "table")


def test_r1_table_must_be_in_table_chunks_plan() -> None:
    """R-1：缺 table channel 或 table 未进 table_chunks 计划 → F1 FAIL。"""
    plan = IW.build(_chunks(), _artifact(), kb="kb_9")
    table_es = [b for b in plan.es_plan
                if b["index_name"] == "v2cand_table_chunks_kb_9"]
    assert table_es and table_es[0]["document_list"]
    table_mv = [b for b in plan.milvus_plan
                if b["collection_name"] == "v2cand_table_chunks_kb_9"]
    assert table_mv and table_mv[0]["document_list"]


# --------------------------------------------------------------------------- F2 / R-2
def test_f2_duplicate_flag_false_hard_constraint() -> None:
    plan = IW.build(_chunks(), _artifact(), kb="kb_9")
    assert plan.es_plan and plan.milvus_plan
    for body in plan.es_plan + plan.milvus_plan:
        assert "duplicate_flag" in body
        assert body["duplicate_flag"] is False  # R-2：置 True 即 FAIL


# --------------------------------------------------------------------------- F3 / R-6
def test_f3_content_hash_same_source_and_recomputable() -> None:
    plan = IW.build(_chunks(), _artifact(), kb="kb_9")
    graph_binding = IW.bind_chunks(_chunks(), _artifact())  # graph docs 侧同源绑定
    assert_same_artifact(plan.binding, graph_binding)  # 不抛错 = 一致
    assert plan.content_hash == graph_binding["content_hash"]
    assert plan.content_hash == plan.binding["content_hash"]
    assert plan.artifact_id == ART_ID and plan.content_uid == UID
    # 三路（ES 计划 / Milvus 计划 / graph docs）的元数据三元组一致
    assert plan.es_plan and plan.milvus_plan
    for body in plan.es_plan + plan.milvus_plan:
        for doc in body["document_list"]:
            meta = doc["metadata"]
            assert meta["artifact_id"] == ART_ID
            assert meta["content_uid"] == UID
            assert meta["content_hash"] == plan.content_hash
    assert graph_binding["artifact_id"] == ART_ID


def test_r6_content_hash_divergence_is_detected() -> None:
    """R-6：三路 content_hash 不一致必须被 assert_same_artifact 拒绝。"""
    good = IW.bind_chunks(_chunks(), _artifact())
    altered = _chunks()
    altered[0]["text"] = "被改写的正文。"
    diverged = IW.bind_chunks(altered, _artifact())
    assert good["content_hash"] != diverged["content_hash"]
    with pytest.raises(ArtifactBindingError):
        assert_same_artifact(good, diverged)


# --------------------------------------------------------------------------- F4 / R-3
def _apply_delete_scope(scope: dict) -> list:
    """模拟把 delete_scope 计划应用到既有文档（离线，纯过滤）。"""
    data = json.loads((FIXTURES / "existing_docs.json").read_text(encoding="utf-8"))
    docs = data["docs"]
    selected = [d for d in docs
                if d["metadata"].get(scope["col_name"].split(".")[-1]) in scope["col_values"]]
    return selected, docs


def test_f4_delete_scope_precise_by_file_id_and_pk() -> None:
    scope = IW.delete_scope(kb="kb_9", file_id="A", index_prefix="v2cand_")
    assert scope["scope"] == "file_id+pk"
    assert scope["duplicate_flag"] is False  # 禁止按 source 全量替换
    assert scope["col_name"] == "metadata.file_id"
    assert scope["col_values"] == ["A"]
    assert scope["pk_field"] == "metadata.pk"
    assert scope["forbidden_scope"] == "source"
    selected, all_docs = _apply_delete_scope(scope)
    assert [d["metadata"]["pk"] for d in selected] == [101, 102]
    assert all(d["metadata"]["file_id"] == "A" for d in selected)
    assert any(d["metadata"]["file_id"] == "B" and d not in selected
               for d in all_docs)  # B 必须保留


def test_r3_same_source_b_file_not_deleted() -> None:
    """R-3：同 source 下 B 文件被误删 → F4 FAIL。"""
    scope = IW.delete_scope(kb="kb_9", file_id="A")
    data = json.loads((FIXTURES / "existing_docs.json").read_text(encoding="utf-8"))
    assert data["source"] == "SHARED"
    selected, _ = _apply_delete_scope(scope)
    b_docs = [d for d in data["docs"] if d["metadata"]["file_id"] == "B"]
    assert b_docs and all(d not in selected for d in b_docs)
    assert scope["scope"] != "source"


# --------------------------------------------------------------------------- F5 / R-4 / R-5
def test_f5_apply_es_failure_has_side(monkeypatch) -> None:
    """R-4：ES 侧 mock 失败 → side='es' 且非成功。"""
    plan = IW.build(_chunks(), _artifact(), kb="kb_9")
    calls = []

    def fake(url, *args, **kwargs):
        calls.append(str(getattr(url, "full_url", url)))
        if "mock-es" in str(getattr(url, "full_url", url)):
            raise RuntimeError("es endpoint down")
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    result = IW.apply(plan, es_url="http://mock-es/insert_fulltext_documents",
                      milvus_url="http://mock-mv/insert_vector_documents_custom")
    assert result.status != "OK"
    assert result.side == "es"
    assert result.error and "es endpoint down" in result.error
    assert result.completed_sides == []
    assert not any("mock-mv" in c for c in calls)  # ES 失败后不得继续写 Milvus


def test_r5_milvus_failure_has_side_and_compensation(monkeypatch) -> None:
    """R-5：Milvus 侧 mock 失败 → side='milvus'、先 ES 后 Milvus、需补偿。"""
    plan = IW.build(_chunks(), _artifact(), kb="kb_9")
    calls = []

    def fake(url, *args, **kwargs):
        calls.append(str(getattr(url, "full_url", url)))
        if "mock-mv" in str(getattr(url, "full_url", url)):
            raise RuntimeError("milvus endpoint down")
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    result = IW.apply(plan, es_url="http://mock-es/insert_fulltext_documents",
                      milvus_url="http://mock-mv/insert_vector_documents_custom")
    assert result.status != "OK"
    assert result.side == "milvus"
    assert result.error and "milvus endpoint down" in result.error
    assert result.completed_sides == ["es"]  # 先 ES 后 Milvus
    assert result.needs_compensation is True  # ES 已写，供调用方登记补偿
    es_calls = [i for i, c in enumerate(calls) if "mock-es" in c]
    mv_calls = [i for i, c in enumerate(calls) if "mock-mv" in c]
    assert es_calls and mv_calls and max(es_calls) < min(mv_calls)


def test_f5_apply_success_path_is_ordered(monkeypatch) -> None:
    plan = IW.build(_chunks(), _artifact(), kb="kb_9")
    calls = []

    def fake(url, *args, **kwargs):
        calls.append(str(getattr(url, "full_url", url)))
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    result = IW.apply(plan, es_url="http://mock-es/insert_fulltext_documents",
                      milvus_url="http://mock-mv/insert_vector_documents_custom")
    assert result.status == "OK"
    assert result.side is None and result.error is None
    assert result.completed_sides == ["es", "milvus"]
    assert result.needs_compensation is False
    assert calls and all("mock-es" in c or "mock-mv" in c for c in calls)


# --------------------------------------------------------------------------- R-7
def test_r7_regression_sentinels() -> None:
    """R-7：L5 既有 13+7 条在验收命令中另跑；此处检查上游模块未被破坏。"""
    assert callable(P.project) and callable(K.build_index_payloads)
    assert callable(IW.build) and callable(IW.delete_scope) and callable(IW.apply)
    # 禁改区延续
    assert P._table_pk("kb_9", "333", 0) == 885155839145947657
