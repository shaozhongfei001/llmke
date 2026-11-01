"""双写对比工具：块集合是硬判据，事实差异必须逐条列出而不是只报个数。"""

import importlib.util
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "dual_diff", os.path.join(REPO, "scripts", "v2_dual_build_diff.py"))
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def write_snapshot(root, docs):
    root.mkdir(parents=True, exist_ok=True)
    payload = {"docs": [{"idx": f"c{i}", "passage": p, "extracted_entities": [],
                         "extracted_triples": [list(t) for t in triples]}
                        for i, (p, triples) in enumerate(docs)]}
    (root / "openie_results_ner_x.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(root)


def test_identical_snapshots(tmp_path):
    docs = [("块一", [("A", "p", "B")]), ("块二", [("C", "p", "D")])]
    a = write_snapshot(tmp_path / "a", docs)
    b = write_snapshot(tmp_path / "b", docs)
    out = mod.diff(a, b)
    assert out["verdict"] == "IDENTICAL"
    assert out["chunks"]["identical"] is True
    assert out["facts"]["only_a"] == 0 and out["facts"]["only_b"] == 0


def test_missing_chunk_is_attributed(tmp_path):
    a = write_snapshot(tmp_path / "a", [("块一", [("A", "p", "B")]),
                                        ("块二", [("C", "p", "D")])])
    b = write_snapshot(tmp_path / "b", [("块一", [("A", "p", "B")])])
    out = mod.diff(a, b)
    assert out["verdict"] == "DIFFERENT"
    assert out["chunks"]["identical"] is False
    assert out["attribution"].get("MISSING_CHUNK") == 1     # 块二的两条事实？只有 C 一条
    assert out["samples"][0]["reason"] == "MISSING_CHUNK"


def test_extraction_diff_is_listed_not_just_counted(tmp_path):
    a = write_snapshot(tmp_path / "a", [("块一", [("A", "p", "B")])])
    b = write_snapshot(tmp_path / "b", [("块一", [("A", "p", "Z")])])
    out = mod.diff(a, b)
    assert out["chunks"]["identical"] is True
    assert out["facts"]["only_a"] == 1 and out["facts"]["only_b"] == 1
    assert out["attribution"] == {"EXTRACTION_DIFF": 2}
    triples = {tuple(s["triple"]) for s in out["samples"]}
    assert ("A", "p", "B") in triples and ("A", "p", "Z") in triples


def test_cli_fails_on_chunk_mismatch(tmp_path):
    a = write_snapshot(tmp_path / "a", [("块一", [])])
    b = write_snapshot(tmp_path / "b", [("块二", [])])
    out = tmp_path / "r.json"
    assert mod.main(["--a", a, "--b", b, "--out", str(out)]) == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["status"] == "FAIL"
