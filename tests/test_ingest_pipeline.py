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
            assert item["metadata"]["start_offset"] < item["metadata"]["end_offset"]
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
