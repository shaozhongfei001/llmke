"""VL1-03 第一步：快照 → 召回单元（RAG 投影）。只读、确定性、可对照。"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services/rag-alg/index_data_service"))

from parse_artifact import store as S  # noqa: E402
from rag_projection import projection as P  # noqa: E402

E = ROOT / "docs/design/unified-documents-v2/examples"
PRODUCER = {"source_revision": "TEST", "runtime_lock_hash": "0" * 64, "config_hash": "1" * 64}


def snapshot(tmp_path, name="artifact", mode="v2"):
    src = tmp_path / ("src-" + name.replace("/", "-"))
    shutil.copytree(E / name, src)
    if mode == "text_only":
        (src / "document_ir.json").unlink()
    store_root = tmp_path / "store"
    artifact, _ = S.commit(src, store_root, PRODUCER, mode=mode)
    return artifact, store_root / "artifacts" / artifact["artifact_id"]


def policy(**kw):
    base = {"index_name": "kb_9", "file_id": "333", "chunk_chars": 60, "overlap_chars": 0}
    base.update(kw)
    return P.ProjectionPolicy(**base)


def test_mode_default_is_legacy_and_unknown_is_refused():
    assert P.mode_from_env({}) == "legacy"
    assert P.mode_from_env({P.MODE_ENV: "shadow"}) == "shadow"
    with pytest.raises(P.ProjectionRefused) as err:
        P.mode_from_env({P.MODE_ENV: "snapshot2"})
    assert err.value.code == "PROJECTION_MODE_INVALID"


def test_legacy_mode_does_not_silently_consume_snapshot(tmp_path):
    _artifact, target = snapshot(tmp_path)
    result = P.project(target, policy(), mode="legacy")
    assert result.status == "NOT_APPLICABLE"
    assert result.chunks == []


def test_snapshot_projection_is_slice_exact_and_covered(tmp_path):
    artifact, target = snapshot(tmp_path)
    result = P.project(target, policy(), mode="snapshot")
    text = (target / "parsed_text.md").read_text(encoding="utf-8")
    assert result.status == "READY"
    assert result.chunks
    covered = set()
    for chunk in result.chunks:
        loc = chunk["locator"]
        assert chunk["text"] == text[loc["start_offset"]:loc["end_offset"]]
        assert chunk["parse_artifact_id"] == artifact["artifact_id"]
        assert chunk["content_uid"] == artifact["content_uid"]
        covered.update(range(loc["start_offset"], loc["end_offset"]))
    missing = [i for i, ch in enumerate(text) if i not in covered and not ch.isspace()]
    assert missing == [], f"未覆盖的非空白字符: {missing[:5]}"


def test_projection_is_deterministic(tmp_path):
    _artifact, target = snapshot(tmp_path)
    first = P.project(target, policy(), mode="snapshot")
    second = P.project(target, policy(), mode="snapshot")
    assert [c["pk"] for c in first.chunks] == [c["pk"] for c in second.chunks]
    assert first.stats["policy_digest"] == second.stats["policy_digest"]


def test_pk_matches_platform_seed_rule(tmp_path):
    _artifact, target = snapshot(tmp_path)
    result = P.project(target, policy(), mode="snapshot")
    chunk = result.chunks[0]
    seed = "|".join(["chunk", "kb_9", "333", "0",
                     hashlib.sha1(chunk["text"].encode("utf-8")).hexdigest()])
    expected = int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:15], 16)
    assert chunk["pk"] == expected


def test_small_chunks_still_cover_everything(tmp_path):
    _artifact, target = snapshot(tmp_path)
    result = P.project(target, policy(chunk_chars=20), mode="snapshot")
    text = (target / "parsed_text.md").read_text(encoding="utf-8")
    assert len(result.chunks) >= 2
    assert all(c["text"].strip() for c in result.chunks)
    assert max(c["locator"]["end_offset"] for c in result.chunks) == len(text)


def test_coverage_gap_is_refused():
    text = "abcdef"
    with pytest.raises(P.ProjectionRefused) as err:
        P._check_coverage(text, [(0, 3)])
    assert err.value.code == "PROJECTION_COVERAGE_LOST"


def test_tampered_snapshot_text_is_refused(tmp_path):
    _artifact, target = snapshot(tmp_path)
    victim = target / "parsed_text.md"
    victim.write_text(victim.read_text(encoding="utf-8") + "x", encoding="utf-8")
    with pytest.raises(P.ProjectionRefused) as err:
        P.project(target, policy(), mode="snapshot")
    assert err.value.code == "ARTIFACT_TEXT_HASH_MISMATCH"


def test_ir_uid_mismatch_is_refused(tmp_path):
    _artifact, target = snapshot(tmp_path)
    ir_path = target / "document_ir.json"
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    ir["content_uid"] = "f" * 64
    ir_path.write_text(json.dumps(ir), encoding="utf-8")
    with pytest.raises(P.ProjectionRefused) as err:
        P.project(target, policy(), mode="snapshot")
    assert err.value.code == "ARTIFACT_IR_UID_MISMATCH"


def test_text_only_snapshot_projects_without_ir(tmp_path):
    artifact, target = snapshot(tmp_path, mode="text_only")
    assert not (target / "document_ir.json").exists()
    result = P.project(target, policy(), mode="shadow")
    assert result.status == "SHADOW"
    assert result.stats["ir_present"] is False
    assert result.stats["artifact_quality"] == "PARTIAL"
    assert all(c["parse_artifact_id"] == artifact["artifact_id"] for c in result.chunks)


def test_empty_text_yields_empty_status(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    (root / "parsed_text.md").write_text("", encoding="utf-8")
    digest = hashlib.sha256(b"").hexdigest()
    (root / "artifact.json").write_text(json.dumps({
        "artifact_id": "pa-empty", "content_uid": digest, "schema_version": "llmke-parse-artifact/2.0",
        "parts": [{"role": "parsed_text", "relative_path": "parsed_text.md",
                   "sha256": digest, "size_bytes": 0}],
        "quality": {"state": "EMPTY", "capabilities": ["text"], "warnings": ["空"]},
    }), encoding="utf-8")
    result = P.project(root, policy(), mode="snapshot")
    assert result.status == "EMPTY"
    assert result.chunks == []
