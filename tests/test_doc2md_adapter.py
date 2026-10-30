"""VL1-02 doc2md 适配器：命令契约、能力探测与"不降级"约束。

用 stub 上游（真实文件 + 真实子进程），不依赖 doc2md 安装；
真实 doc2md 的能力缺口见 adapter.py 顶部说明与 upstash 报告 U-08。
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services/rag-alg/index_data_service"))
sys.path.insert(0, str(ROOT / "services/rag-alg/alg_doc_parse_service"))

from adapter_doc2md import adapter as A  # noqa: E402
from contract_runtime import validate_instance  # noqa: E402
from parse_artifact import store as S  # noqa: E402

E = ROOT / "docs/design/unified-documents-v2/examples"
UID = json.loads((E / "artifact/parse_manifest.json").read_text(encoding="utf-8"))["content_uid"]

STUB = r'''
import argparse, pathlib, shutil, sys
p = argparse.ArgumentParser()
p.add_argument("--content-uid", required=True)
p.add_argument("--src", required=True)
p.add_argument("--out", required=True)
p.add_argument("--no-ir", action="store_true")
p.add_argument("--fail", action="store_true")
a = p.parse_args()
if a.fail:
    print("upstream exploded", file=sys.stderr)
    raise SystemExit(3)
uid = a.content_uid
dst = pathlib.Path(a.out) / "by_hash" / uid[:2] / uid[2:4] / uid
shutil.copytree(a.src, dst)
if a.no_ir:
    (dst / "document_ir.json").unlink()
print("ok")
'''


def make_stub(tmp_path):
    path = tmp_path / "stub_doc2md.py"
    path.write_text(STUB, encoding="utf-8")
    return path


def make_adapter(tmp_path, *extra):
    stub = make_stub(tmp_path)
    parsed = tmp_path / "parsed"
    command = [sys.executable, str(stub), "--content-uid", "{content_uid}",
               "--src", str(E / "artifact"), "--out", str(parsed), *extra]
    return A.Doc2mdAdapter(parsed, command), parsed


def test_adapter_runs_upstream_then_commits(tmp_path):
    adapter, parsed = make_adapter(tmp_path)
    lock = tmp_path / "requirements.lock"
    lock.write_text("jsonschema==4.23.0\n", encoding="utf-8")
    config = tmp_path / "app.yaml"
    config.write_text("app:\n  name: stub\n", encoding="utf-8")

    artifact, target = adapter.parse_to_artifact(
        UID, tmp_path / "store", source_revision="stub-doc2md@1",
        config=config, runtime_lock=lock)

    assert artifact["content_uid"] == UID
    assert artifact["producer"]["source_revision"] == "stub-doc2md@1"
    # parser_name/profile/adapter_version 取自上游 metadata，不由适配器编造
    upstream_meta = json.loads((E / "artifact/parsed_metadata.json").read_text(encoding="utf-8"))
    assert artifact["producer"]["parser_name"] == upstream_meta["parser_name"]
    assert artifact["producer"]["parser_profile"] == upstream_meta["parser_profile"]
    assert artifact["producer"]["runtime_lock_hash"] == A._sha256_file(lock)
    assert artifact["producer"]["config_hash"] == A._sha256_file(config)
    assert (target / "artifact.json").is_file()
    assert A.capability_report(A.locate_artifact(parsed, UID))["v2_artifact_ready"] is True


def test_missing_ir_reported_and_not_committed(tmp_path):
    adapter, _ = make_adapter(tmp_path, "--no-ir")
    store_root = tmp_path / "store"
    with pytest.raises(A.UpstreamContractGap) as err:
        adapter.parse_to_artifact(UID, store_root, source_revision="stub-doc2md@1")
    assert err.value.code == "UPSTREAM_IR_MISSING"
    assert err.value.evidence["document_ir"] is False
    assert not (store_root / "artifacts").exists()


def test_upstream_nonzero_exit_is_loud(tmp_path):
    adapter, _ = make_adapter(tmp_path, "--fail")
    with pytest.raises(A.AdapterFailed) as err:
        adapter.parse_to_artifact(UID, tmp_path / "store", source_revision="stub@1")
    assert err.value.code == "DOC2MD_EXIT_NONZERO"
    assert "upstream exploded" in err.value.detail


def test_missing_entry_is_loud(tmp_path):
    adapter = A.Doc2mdAdapter(tmp_path / "parsed", ["/nonexistent/doc2md-binary"])
    with pytest.raises(A.AdapterFailed) as err:
        adapter.parse_to_artifact(UID, tmp_path / "store", source_revision="stub@1")
    assert err.value.code == "DOC2MD_ENTRY_MISSING"


def test_locate_artifact_rejects_bad_uid(tmp_path):
    with pytest.raises(A.AdapterFailed) as err:
        A.locate_artifact(tmp_path, "abc")
    assert err.value.code == "BAD_CONTENT_UID"


def test_capability_report_does_not_infer_from_display_file(tmp_path):
    directory = tmp_path / "artifact"
    directory.mkdir()
    (directory / "rendered.md").write_text("# view only\n", encoding="utf-8")
    report = A.capability_report(directory)
    assert report["rendered_md"] is True
    assert report["parsed_text"] is False
    assert report["document_ir"] is False
    assert report["v2_artifact_ready"] is False


def test_text_only_upstream_registers_legacy_artifact(tmp_path):
    """CR BL-2.0.0-02：没有 IR 时只能登记 text-only，且能力被契约限死。"""
    adapter, _ = make_adapter(tmp_path, "--no-ir")
    lock = tmp_path / "requirements.lock"
    lock.write_text("markitdown>=0.1.0\n", encoding="utf-8")
    config = tmp_path / "app.yaml"
    config.write_text("app:\n  name: stub\n", encoding="utf-8")
    artifact, target = adapter.parse_to_legacy_artifact(
        UID, tmp_path / "store", source_revision="stub-doc2md@1",
        config=config, runtime_lock=lock)
    validate_instance(ROOT, "schema/llmke-document-pipeline-v2.json",
                      artifact, "/$defs/LegacyTextArtifact")
    assert artifact["schema_version"] == "llmke-legacy-text-artifact/1.0"
    assert artifact["quality"]["state"] == "PARTIAL"
    assert set(artifact["quality"]["capabilities"]) == {"text", "source_alignment"}
    assert "document_ir" not in [p["role"] for p in artifact["parts"]]
    assert artifact["quality"]["warnings"]
    assert (target / "artifact.json").is_file()


def test_legacy_text_cannot_claim_structure(tmp_path):
    src = tmp_path / "text-only"
    shutil.copytree(E / "artifact", src)
    (src / "document_ir.json").unlink()
    artifact = S.build_text_only_artifact(
        src, {"source_revision": "x", "runtime_lock_hash": "0" * 64, "config_hash": "1" * 64})
    artifact["quality"]["capabilities"] = ["text", "document_ir"]
    with pytest.raises(Exception):
        validate_instance(ROOT, "schema/llmke-document-pipeline-v2.json",
                          artifact, "/$defs/LegacyTextArtifact")


def test_text_only_refused_when_ir_present(tmp_path):
    src = sample = tmp_path / "with-ir"
    shutil.copytree(E / "artifact", sample)
    with pytest.raises(S.ArtifactRefused) as err:
        S.build_text_only_artifact(
            src, {"source_revision": "x", "runtime_lock_hash": "0" * 64, "config_hash": "1" * 64})
    assert err.value.code == "IR_PRESENT_USE_V2_PATH"


def test_store_accepts_doc2md_layout_and_drops_display_track(tmp_path):
    """doc2md 目录比四件套多：rendered.md 排除，ir_source/** 记为 ir_source 角色。"""
    src = tmp_path / "doc2md-out"
    shutil.copytree(E / "artifact", src)
    (src / "rendered.md").write_text("# derived view\n", encoding="utf-8")
    (src / "ir_source").mkdir()
    (src / "ir_source/pages.json").write_text('{"pages": []}\n', encoding="utf-8")

    artifact, _ = S.commit(src, tmp_path / "store",
                           {"source_revision": "doc2md@d9e4f98",
                            "runtime_lock_hash": "0" * 64, "config_hash": "1" * 64})
    roles = {p["role"] for p in artifact["parts"]}
    assert "ir_source" in roles
    assert not any(p["relative_path"] == "rendered.md" for p in artifact["parts"])
    assert len(artifact["parts"]) == 5
