"""VL1-01 ParseArtifact 产物仓：正例与反例。

边界：只用仓内合成样例，证明"封装/校验/提交"逻辑成立；
不证明 doc2md 真实解析、模型执行或目标机发布（那些属 VL1-02 及之后）。
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services/rag-alg/index_data_service"))

from contract_runtime import validate_instance  # noqa: E402
from parse_artifact import store as S  # noqa: E402

E = ROOT / "docs/design/unified-documents-v2/examples"
PRODUCER = {"source_revision": "TEST_SYNTHETIC", "runtime_lock_hash": "0" * 64,
            "config_hash": "1" * 64}


def sample(tmp_path, name="artifact"):
    dst = tmp_path / ("src-" + name.replace("/", "-"))
    shutil.copytree(E / name, dst)
    return dst


def edit_json(path, **changes):
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.update(changes)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def assert_contract(artifact):
    validate_instance(ROOT, "schema/llmke-document-pipeline-v2.json",
                      artifact, "/$defs/ParseArtifact")


# ───────────────────────────────────────────────────────────── 正例


def test_commit_plain_artifact_passes_v2_contract(tmp_path):
    artifact, target = S.commit(sample(tmp_path), tmp_path / "store", PRODUCER)
    assert_contract(artifact)
    assert artifact["artifact_id"] == artifact["content_uid"]
    assert artifact["commit_state"] == "COMMITTED"
    assert [p["role"] for p in artifact["parts"]] == [
        "document_ir", "parse_manifest", "parsed_metadata", "parsed_text"]
    assert (target / "artifact.json").is_file()
    assert (target / "parsed_text.md").read_bytes() == (E / "artifact/parsed_text.md").read_bytes()
    # 内容身份来自 doc2md 清单，不是自己编的
    assert artifact["content_uid"] == json.loads(
        (E / "artifact/parse_manifest.json").read_text(encoding="utf-8"))["content_uid"]


def test_commit_multimodal_artifact_reports_figure_capability(tmp_path):
    artifact, _ = S.commit(sample(tmp_path, "multimodal/artifact"), tmp_path / "store", PRODUCER)
    assert_contract(artifact)
    roles = [p["role"] for p in artifact["parts"]]
    assert roles.count("asset") == 1
    assert "figure_assets" in artifact["quality"]["capabilities"]
    assert artifact["quality"]["state"] == "COMPLETE"
    assert S.verify_committed(tmp_path / "store", artifact["artifact_id"]) == artifact


def test_commit_is_idempotent_and_leaves_no_staging(tmp_path):
    src = sample(tmp_path)
    first, target = S.commit(src, tmp_path / "store", PRODUCER)
    second, target2 = S.commit(src, tmp_path / "store", PRODUCER)
    assert target == target2
    assert second["content_uid"] == first["content_uid"]
    assert second["parts"] == first["parts"]
    assert not (tmp_path / "store" / ".staging").exists()


def test_read_set_digest_tracks_bytes(tmp_path):
    src = sample(tmp_path)
    before = S.build_artifact(src, PRODUCER)["read_set_digest"]
    target = src / "parsed_metadata.json"
    target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")
    after = S.build_artifact(src, PRODUCER)["read_set_digest"]
    assert before != after


# ───────────────────────────────────────────────────────────── 反例


def test_missing_singleton_part_refused(tmp_path):
    src = sample(tmp_path)
    (src / "document_ir.json").unlink()
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(src, PRODUCER)
    assert err.value.code == "MISSING_PART"


def test_unknown_top_level_file_refused(tmp_path):
    src = sample(tmp_path)
    (src / "debug.log").write_text("noise", encoding="utf-8")
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(src, PRODUCER)
    assert err.value.code == "UNKNOWN_TOP_LEVEL_FILE"


def test_symlink_part_refused(tmp_path):
    src = sample(tmp_path)
    real = tmp_path / "outside.md"
    shutil.copyfile(src / "parsed_text.md", real)
    (src / "parsed_text.md").unlink()
    (src / "parsed_text.md").symlink_to(real)
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(src, PRODUCER)
    assert err.value.code == "SYMLINK_REFUSED"


def test_bom_text_refused(tmp_path):
    src = sample(tmp_path)
    raw = (src / "parsed_text.md").read_bytes()
    (src / "parsed_text.md").write_bytes(b"\xef\xbb\xbf" + raw)
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(src, PRODUCER)
    assert err.value.code == "BOM_REFUSED"


def test_failed_parse_status_refused(tmp_path):
    src = sample(tmp_path)
    edit_json(src / "parse_manifest.json", status="FAILED")
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(src, PRODUCER)
    assert err.value.code == "FAILED_PARSE_REFUSED"


def test_content_uid_mismatch_refused(tmp_path):
    src = sample(tmp_path)
    edit_json(src / "parsed_metadata.json", content_uid="f" * 64)
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(src, PRODUCER)
    assert err.value.code == "CONTENT_UID_MISMATCH"


def test_text_hash_mismatch_refused(tmp_path):
    src = sample(tmp_path)
    target = src / "parsed_text.md"
    target.write_text(target.read_text(encoding="utf-8") + "追加", encoding="utf-8")
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(src, PRODUCER)
    assert err.value.code == "TEXT_HASH_MISMATCH"


def test_ir_span_mismatch_refused(tmp_path):
    src = sample(tmp_path)
    path = src / "document_ir.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    for block in doc["blocks"]:
        if block.get("content_ref", {}).get("kind") == "text_span":
            block["content_ref"]["text"] = "被篡改的引用"
            break
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(src, PRODUCER)
    assert err.value.code == "IR_SPAN_MISMATCH"


def test_asset_manifest_mismatch_refused(tmp_path):
    src = sample(tmp_path, "multimodal/artifact")
    (src / "assets/images/chart.svg").unlink()
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(src, PRODUCER)
    assert err.value.code == "ASSET_MANIFEST_MISMATCH"


def test_source_changed_during_copy_refused(tmp_path):
    """全部件复制完、提交前源被改写：必须整批放弃，不能留下混合快照。"""
    src = sample(tmp_path)
    total = len(S.collect_parts(src))

    def mutate(index, part):
        if index == total - 1:
            target = src / "parsed_metadata.json"
            target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(S.ArtifactRefused) as err:
        S.commit(src, tmp_path / "store", PRODUCER, after_part_copied=mutate)
    assert err.value.code == "SOURCE_CHANGED"
    assert not (tmp_path / "store" / "artifacts").exists()
    assert not (tmp_path / "store" / ".staging").exists()


def test_copy_mismatch_when_source_changes_before_its_copy(tmp_path):
    """还没复制到的件被改写：复制后逐件复核直接失败（COPY_MISMATCH）。"""
    src = sample(tmp_path)

    def mutate(index, part):
        if index == 0:
            target = src / "parsed_metadata.json"
            target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(S.ArtifactRefused) as err:
        S.commit(src, tmp_path / "store", PRODUCER, after_part_copied=mutate)
    assert err.value.code == "COPY_MISMATCH"
    assert not (tmp_path / "store" / "artifacts").exists()


def test_conflicting_artifact_id_refused(tmp_path):
    S.commit(sample(tmp_path), tmp_path / "store", PRODUCER, artifact_id="pa-fixed")
    other = sample(tmp_path, "multimodal/artifact")
    with pytest.raises(S.ArtifactRefused) as err:
        S.commit(other, tmp_path / "store", PRODUCER, artifact_id="pa-fixed")
    assert err.value.code == "ARTIFACT_CONFLICT"


def test_tampered_committed_snapshot_detected(tmp_path):
    artifact, target = S.commit(sample(tmp_path), tmp_path / "store", PRODUCER)
    victim = target / "parsed_text.md"
    victim.write_bytes(victim.read_bytes() + b"x")
    with pytest.raises(S.ArtifactRefused) as err:
        S.verify_committed(tmp_path / "store", artifact["artifact_id"])
    assert err.value.code == "VERIFY_FAILED"


def test_unsafe_artifact_id_refused(tmp_path):
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(sample(tmp_path), PRODUCER, artifact_id="../escape")
    assert err.value.code == "UNSAFE_ARTIFACT_ID"


def test_incomplete_producer_refused(tmp_path):
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_artifact(sample(tmp_path), {"source_revision": "X"})
    assert err.value.code == "PRODUCER_INCOMPLETE"
