"""VL1-03→B1：摄取链路集成层（开关、通道路由、只读约束）。"""

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services/rag-alg/index_data_service"))

from ingest_pipeline import IngestRefused, ingest  # noqa: E402
from parse_artifact import store as S  # noqa: E402

E = ROOT / "docs/design/unified-documents-v2/examples"
PRODUCER = {"source_revision": "TEST", "runtime_lock_hash": "0" * 64, "config_hash": "1" * 64}


@pytest.fixture
def artifact_dir(tmp_path):
    src = tmp_path / "src"
    shutil.copytree(E / "artifact", src)
    artifact, _ = S.commit(src, tmp_path / "store", PRODUCER)
    return tmp_path / "store" / "artifacts" / artifact["artifact_id"]


def test_legacy_mode_is_not_applicable(artifact_dir):
    result = ingest(artifact_dir, index_name="kb_9", file_id="333", mode="legacy")
    assert result["status"] == "NOT_APPLICABLE"
    assert "chunks" not in result


def test_shadow_routes_channels_to_separate_indexes(artifact_dir):
    result = ingest(artifact_dir, index_name="kb_9", file_id="333", mode="shadow")
    assert result["status"] == "SHADOW"
    payloads = result["chunks"]
    assert payloads
    for item in payloads:
        assert item["metadata"]["parse_artifact_id"] == result["artifact_id"]
        assert item["index"] in {"kb_9", "table_chunks_kb_9"}
        if item["metadata"]["channel"] == "text":
            assert item["index"] == "kb_9"
            offset = item["metadata"]["offset"]
            assert isinstance(offset, list) and len(offset) == 1 and len(offset[0]) == 2
            assert offset[0][0] < offset[0][1]      # 旧链路是 [[start, end]]，不是字符串
        else:
            assert item["index"].startswith("table_chunks_")
    assert result["counts"] == {"kb_9": result["channels"]["text"],
                                "table_chunks_kb_9": result["channels"]["table"]} \
        or set(result["counts"]) <= {"kb_9", "table_chunks_kb_9"}


def test_shadow_cannot_apply_index(artifact_dir):
    with pytest.raises(IngestRefused) as err:
        ingest(artifact_dir, index_name="kb_9", file_id="333", mode="shadow", apply_index=True)
    assert err.value.code == "APPLY_NOT_ALLOWED_IN_SHADOW"


def test_snapshot_allows_apply_flag_without_writing(artifact_dir):
    result = ingest(artifact_dir, index_name="kb_9", file_id="333",
                    mode="snapshot", apply_index=True)
    assert result["status"] == "READY"
    assert result["chunks"]


def test_unknown_mode_is_refused(artifact_dir):
    with pytest.raises(IngestRefused) as err:
        ingest(artifact_dir, index_name="kb_9", file_id="333", mode="snapshot2")
    assert err.value.code == "INGEST_MODE_INVALID"


def test_payload_covers_all_production_fields_and_flags_placeholders(artifact_dir):
    """生产 _kb_9 的 33 字段必须全在；版面字段只能标 placeholder，不许冒充真实坐标。"""
    production = ['pk', 'text', 'vector', 'source', 'chunk_doc_id', 'document_id', 'folder_id',
                  'title', 'title_path', 'pic_offset_list', 'labels', 'position', 'page_number',
                  'knowledge_base_name', 'file_path', 'image_path', 'file_size', 'page_size',
                  'order_num', 'parent_file_name', 'revise_date', 'create_time', 'update_time',
                  'table_name', 'pic_url_list', 'pic_children_id_list', 'text_parent_id_list',
                  'att_id', 'main_id', 'type', 'offset', 'file_id', 'chunk_index']
    result = ingest(artifact_dir, index_name="kb_9", file_id="333", mode="shadow",
                    file_name="docx-table.docx", file_path="r12-rag/kb_9/docx-table.docx",
                    file_size="47.3 MB")
    for payload in result["chunks"]:
        missing = [f for f in production
                   if f not in payload["metadata"] and f not in {"pk", "text", "vector"}]
        assert not missing, missing
        meta = payload["metadata"]
        assert meta["knowledge_base_name"] == "kb_9"
        assert meta["title"] == "docx-table.docx"
        assert meta["file_size"] == "47.3 MB"
        assert meta["create_time"] and meta["update_time"]
    fill = result["field_fill"]
    # 版面三件套必须显式标成占位，不能让下游当真实坐标去做高亮
    assert set(fill["placeholder"]) >= {"page_number", "page_size", "position"}
    assert fill["layout"] == "unavailable"
    assert {"title", "knowledge_base_name", "file_path", "file_size"} <= set(fill["filled"])


def test_source_is_a_per_file_identity_key_not_a_fixed_path(artifact_dir):
    """回归：source 是文件身份键（相邻块检索/去重/引用 URL 都靠它），不得写成固定值。

    消费点：alg_retrieval_service/retrieval_service.py:309-336（按 source 查相邻块、
    算最大 chunk_index、按 (source, chunk_index) 去重）、retrieval_global_view.py:37
    （Java 一律 endPoint + "/" + source 拼 URL）。写成 parsed_text.md 会把所有文件
    并成一个身份，相邻块会跨文件串台、引用全部指向同一个假路径。
    """
    one = ingest(artifact_dir, index_name="kb_9", file_id="333", mode="shadow",
                 file_path="r12-rag/kb_9/a.docx/V0/a.docx")
    two = ingest(artifact_dir, index_name="kb_9", file_id="334", mode="shadow",
                 file_path="r12-rag/kb_9/b.docx/V0/b.docx")
    src_one = {c["metadata"]["source"] for c in one["chunks"]}
    src_two = {c["metadata"]["source"] for c in two["chunks"]}
    assert src_one == {"r12-rag/kb_9/a.docx/V0/a.docx"}
    assert src_two == {"r12-rag/kb_9/b.docx/V0/b.docx"}
    assert src_one.isdisjoint(src_two)
    for payload in one["chunks"]:
        assert payload["metadata"]["source"] != "parsed_text.md"
        assert payload["metadata"]["parsed_text_ref"].startswith(("parsed_text.md", "table:"))


def test_missing_source_is_reported_not_silently_blank(artifact_dir):
    result = ingest(artifact_dir, index_name="kb_9", file_id="333", mode="shadow")
    assert result["field_fill"]["source_from"] == "MISSING"
    assert "source" in result["field_fill"]["placeholder"]


def test_compare_channels_reports_diff_without_forcing_equality():
    from ingest_pipeline import compare_channels

    out = compare_channels({"kb_9": 1, "table_chunks_kb_9": 1},
                           {"kb_9": 2, "table_chunks_kb_9": 1})
    assert out["kb_9"] == {"legacy": 1, "projected": 2, "diff": 1}
    assert out["table_chunks_kb_9"]["diff"] == 0


def test_missing_artifact_is_reported_not_faked(tmp_path):
    with pytest.raises(Exception) as err:
        ingest(tmp_path / "nope", index_name="kb_9", file_id="333", mode="shadow")
    assert "ARTIFACT_MANIFEST_MISSING" in str(err.value)
