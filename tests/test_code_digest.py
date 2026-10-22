"""W-01 — 业务代码必须被「该绑它的门禁」绑住，且不能连累其他门禁。

背景（实测缺口）：
    modules/citation_evidence/assembler.py 追加一行注释后，整树 snapshot 变了，
    但 control_digest 不变、evidence-check 仍 PASS —— scheme=2 下没有任何门禁证据绑定业务代码。
方案：
    新增 code_digest，只被 CODE_DEPENDENT_GATES 比较；
    不并入 control_digest（否则每次改代码作废全部门禁，重演 P-03 前的返工）。
"""
import fixture_helpers  # noqa: F401  （建立 scripts/ 的导入路径）
from fixture_helpers import make_loop, guard, devpass, load, dump
from baseline_support import (CODE_DEPENDENT_GATES, code_digest, code_files,
                              control_digest, doc_digest, filehash)
from loop_guard import stale_reasons


# ---- code_files 口径 ----
def test_code_files_includes_implementation_only(tmp_path):
    (tmp_path / "modules" / "m").mkdir(parents=True)
    (tmp_path / "modules" / "m" / "impl.py").write_text("x = 1\n")
    (tmp_path / "modules" / "m" / "tests").mkdir(parents=True)
    (tmp_path / "modules" / "m" / "tests" / "test_impl.py").write_text("def test_x(): pass\n")
    (tmp_path / "modules" / "m" / "__pycache__").mkdir(parents=True)
    (tmp_path / "modules" / "m" / "__pycache__" / "impl.cpython-312.pyc").write_text("")
    assert code_files(tmp_path) == ["modules/m/impl.py"]


def test_code_digest_changes_when_implementation_changes(tmp_path):
    (tmp_path / "modules").mkdir()
    f = tmp_path / "modules" / "a.py"
    f.write_text("x = 1\n")
    before = code_digest(tmp_path)
    f.write_text("x = 1\n# comment only\n")     # 语义不变也要变，因为它是「那版代码」的指纹
    assert code_digest(tmp_path) != before


def test_code_digest_ignores_docs_and_tests(tmp_path):
    (tmp_path / "modules").mkdir()
    (tmp_path / "modules" / "a.py").write_text("x = 1\n")
    before = code_digest(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "NOTE.md").write_text("doc\n")
    (tmp_path / "modules" / "tests").mkdir()
    (tmp_path / "modules" / "tests" / "test_a.py").write_text("def test_a(): pass\n")
    assert code_digest(tmp_path) == before


# ---- stale_reasons 的 scheme=3 分支 ----
def _rec(root, scheme):
    """构造一条与当前树完全绑定的记录，再按需改树。"""
    manifest = root / "docs" / "baseline" / "FROZEN-MANIFEST.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('{"baseline_version": "test"}\n', encoding="utf-8")
    return {
        "status": "pass", "digest_scheme": scheme,
        "baseline_sha256": filehash(manifest),
        "control_sha256": control_digest(root),
        "doc_sha256": doc_digest(root),
        "code_sha256": code_digest(root),
    }


def test_scheme3_flags_code_change_for_code_dependent_gate(tmp_path):
    (tmp_path / "modules").mkdir()
    f = tmp_path / "modules" / "a.py"
    f.write_text("x = 1\n")
    gate_id = sorted(CODE_DEPENDENT_GATES)[0]
    rec = _rec(tmp_path, 3)
    assert stale_reasons(tmp_path, rec, {"id": gate_id}) == []

    f.write_text("x = 2\n")
    errs = stale_reasons(tmp_path, rec, {"id": gate_id})
    assert any("implementation code changed" in e for e in errs), errs


def test_scheme3_does_not_bind_code_to_other_gates(tmp_path):
    """窄绑定：非 CODE_DEPENDENT_GATES 的门禁不得因业务代码变动而 STALE。"""
    (tmp_path / "modules").mkdir()
    f = tmp_path / "modules" / "a.py"
    f.write_text("x = 1\n")
    rec = _rec(tmp_path, 3)
    f.write_text("x = 2\n")
    assert stale_reasons(tmp_path, rec, {"id": "contract_check_gate"}) == []


def test_scheme2_record_is_not_retroactively_bound_to_code(tmp_path):
    """兼容：历史 scheme=2 记录不回溯加约束（否则等于改写历史证据）。"""
    (tmp_path / "modules").mkdir()
    f = tmp_path / "modules" / "a.py"
    f.write_text("x = 1\n")
    gate_id = sorted(CODE_DEPENDENT_GATES)[0]
    rec = _rec(tmp_path, 2)
    f.write_text("x = 2\n")
    assert stale_reasons(tmp_path, rec, {"id": gate_id}) == []


# ---- 端到端：真实批次（dev 门禁）不受业务代码影响 ----
def test_dev_gates_in_real_loop_are_not_stale_on_code_change(tmp_path):
    root, d = make_loop(tmp_path)
    devpass(root)
    (root / "modules").mkdir()
    (root / "modules" / "new_slice.py").write_text("y = 1\n")
    p = guard(root, "evidence-check", "--loop", "T1")
    assert p.returncode == 0, p.stdout + p.stderr


# ---- W-01b：QA 候选过期必须在 evidence-check 阶段就可见（不再只靠 accept-qa 拦截） ----
def _qa_candidate(tmp_path):
    """把夹具的 QA 门禁改成真实 id（`independent_qa_gate`），使其真正属于 CODE_DEPENDENT_GATES。

    注意：不能 monkeypatch —— guard() 起的是独立进程，补丁不跨进程生效。
    """
    from freeze_baseline import run as freeze
    root, d = make_loop(tmp_path)
    loop = load(d / "LOOP.yaml")
    for g in loop["gates"]:
        if g.get("type") == "qa_gate":
            g["id"] = "independent_qa_gate"
    dump(d / "LOOP.yaml", loop)
    freeze(root, write=True)          # 门禁定义变了，必须重冻结后再产证据
    devpass(root)
    assert guard(root, "baton-transfer", "--loop", "T1", "--to", "qa-independent",
                 "--executor", "dev-1", "--expected-revision", "2").returncode == 0
    assert guard(root, "qa-run", "--loop", "T1", "--gate", "independent_qa_gate",
                 "--executor", "qa-independent").returncode == 0
    return root, d


def test_qa_candidate_current_passes_evidence_check(tmp_path):
    root, d = _qa_candidate(tmp_path)
    p = guard(root, "evidence-check", "--loop", "T1")
    assert p.returncode == 0, p.stdout + p.stderr


def test_qa_candidate_stale_is_reported(tmp_path):
    """业务代码一变，QA 候选必须当场判 STALE；否则'候选已过期'会被 PASS 掩盖。"""
    root, d = _qa_candidate(tmp_path)
    # 新增一个实现文件同样是"代码变了"：code_digest 覆盖文件集本身，不只是内容
    (root / "modules").mkdir(exist_ok=True)
    (root / "modules" / "impl.py").write_text("x = 2\n")
    p = guard(root, "evidence-check", "--loop", "T1")
    assert p.returncode != 0, p.stdout + p.stderr
    assert "independent_qa_gate" in p.stdout and "implementation code changed" in p.stdout
