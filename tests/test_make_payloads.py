"""验收载荷自举：形状必须与生产投影一致，否则图检查会"用假数据通过"。

这条测试不是"能生成 JSON"，而是钉住三件事：
- 34 个 metadata 字段（生产投影就 34 个，缺字段会让下游按 None 处理）；
- 双通道（正文/表格）都要有，且 table 块在表格通道；
- 确定性：同一 file_id 两次生成内容一致（否则验收不可复现）。
"""

import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "v2_make_payloads.py")


@pytest.fixture(scope="module")
def outdir(tmp_path_factory):
    path = tmp_path_factory.mktemp("payloads")
    subprocess.run([sys.executable, SCRIPT, "--out-dir", str(path)], check=True,
                   capture_output=True, text=True)
    return path


def load(outdir, file_id):
    return json.loads((outdir / f"ingest-{file_id}.json").read_text(encoding="utf-8"))


def test_metadata_has_34_fields(outdir):
    for file_id in ("333", "329"):
        doc = load(outdir, file_id)
        assert len(doc["chunks"][0]["metadata"]) == 34


def test_both_channels_present(outdir):
    for file_id in ("333", "329"):
        doc = load(outdir, file_id)
        # 生产的 metadata.channel 是**索引名**（kb_9 / table_chunks_kb_9），不是 text/table；
        # 块类型另由 metadata.type 表示。这两者混用会让下游按错误的索引名去查。
        channels = {c["metadata"]["channel"] for c in doc["chunks"]}
        assert channels == {"kb_9", "table_chunks_kb_9"}
        table = [c for c in doc["chunks"] if c["metadata"]["type"] == "table"][0]
        assert table["metadata"]["channel"] == "table_chunks_kb_9"


def test_chunk_counts_match_spec(outdir):
    assert len(load(outdir, "333")["chunks"]) == 3
    assert len(load(outdir, "329")["chunks"]) == 2


def test_deterministic(outdir, tmp_path):
    again = tmp_path / "again"
    subprocess.run([sys.executable, SCRIPT, "--out-dir", str(again)], check=True,
                   capture_output=True, text=True)
    for file_id in ("333", "329"):
        a = (outdir / f"ingest-{file_id}.json").read_text(encoding="utf-8")
        b = (again / f"ingest-{file_id}.json").read_text(encoding="utf-8")
        assert a == b, f"{file_id} 两次生成不一致"


def test_idempotent_without_force(outdir):
    proc = subprocess.run([sys.executable, SCRIPT, "--out-dir", str(outdir)],
                          capture_output=True, text=True, check=True)
    payload = json.loads(proc.stdout)
    assert payload["written"] == []
    assert len(payload["skipped"]) == 2
