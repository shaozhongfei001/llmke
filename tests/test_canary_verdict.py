"""灰度判定器：只测 judge() 的判据，不加载引擎。

最容易被写错的一格是第 3 项：**事实有差异但检索一致 → REVIEW，不是 SAFE**。
如果把它写成 SAFE，"抽取差了一条、用户暂时没看见"就被记成"切换无风险"，
而这正是 C2 实测到的真实情形（delta 多 1 条 openie 事实）。
"""

import copy
import importlib.util
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "canary_verdict", os.path.join(REPO, "scripts", "v2_canary_verdict.py"))
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

BASELINE_OK = {"chunks_identical": True, "only_a": 0, "only_b": 0,
               "facts_only_a": 0, "facts_only_b": 0,
               "retrieval": {"top1_rate": 1.0, "ordered_rate": 1.0, "avg_jaccard": 1.0}}
CHUNKS_OK = {"identical": True, "only_a": 0, "only_b": 0}
FACTS_OK = {"only_a": 0, "only_b": 0}
RETRIEVAL_OK = {"top1_rate": 1.0, "ordered_rate": 1.0, "avg_jaccard": 1.0,
                "route_changed": []}


def run(chunks=None, facts=None, retrieval=None, baseline=None):
    """用默认"全一致"打底，只覆盖关心的那一格，避免测试互相污染。"""
    return mod.judge(
        chunks=copy.deepcopy(CHUNKS_OK if chunks is None else chunks),
        facts=copy.deepcopy(FACTS_OK if facts is None else facts),
        retrieval=copy.deepcopy(RETRIEVAL_OK if retrieval is None else retrieval),
        baseline=copy.deepcopy(BASELINE_OK if baseline is None else baseline),
    )


def test_all_identical_is_safe():
    out = run()
    assert out["verdict"] == "SAFE"
    assert out["exit_code"] == 0
    assert out["hard"] == [] and out["soft"] == []


def test_chunk_set_diff_is_unsafe():
    out = run(chunks={"identical": False, "only_a": 1, "only_b": 0})
    assert out["verdict"] == "UNSAFE"
    assert out["exit_code"] == 2
    assert any("块集合不一致" in r for r in out["reasons"])


def test_extraction_diff_with_identical_retrieval_is_review():
    """delta 多 1 条事实、检索全一致 —— 必须 REVIEW，绝不能是 SAFE。"""
    out = run(facts={"only_a": 0, "only_b": 1})
    assert out["verdict"] == "REVIEW"
    assert out["exit_code"] == 1
    assert out["hard"] == []
    assert any("抽取事实存在差异" in r for r in out["reasons"])
    assert "only_b=1" in " ".join(out["reasons"])


def test_baseline_instability_is_unsafe_and_says_baseline():
    baseline = copy.deepcopy(BASELINE_OK)
    baseline["facts_only_b"] = 1          # 同一语料两份全量自己就不一致
    out = run(baseline=baseline)
    assert out["verdict"] == "UNSAFE"
    assert out["exit_code"] == 2
    assert any("基线" in r for r in out["reasons"])


def test_baseline_chunk_mismatch_is_unsafe():
    baseline = copy.deepcopy(BASELINE_OK)
    baseline["chunks_identical"] = False
    out = run(baseline=baseline)
    assert out["verdict"] == "UNSAFE"
    assert any("基线" in r for r in out["reasons"])


def test_baseline_retrieval_noise_is_unsafe():
    """检索基线自己都不稳时，a vs b 的检索差异同样归因不了。"""
    baseline = copy.deepcopy(BASELINE_OK)
    baseline["retrieval"] = {"top1_rate": 0.83, "ordered_rate": 0.83, "avg_jaccard": 0.94}
    out = run(baseline=baseline)
    assert out["verdict"] == "UNSAFE"
    assert any("基线" in r for r in out["reasons"])


def test_top1_mismatch_is_unsafe():
    out = run(retrieval={"top1_rate": 0.833, "ordered_rate": 0.833, "avg_jaccard": 0.95})
    assert out["verdict"] == "UNSAFE"
    assert any("top1" in r for r in out["reasons"])


def test_route_change_is_unsafe_even_if_hits_match():
    out = run(retrieval={"top1_rate": 1.0, "ordered_rate": 1.0, "avg_jaccard": 1.0,
                         "route_changed": ["授信额度是多少"]})
    assert out["verdict"] == "UNSAFE"
    assert any("路线变化" in r for r in out["reasons"])


def test_ordered_only_mismatch_is_not_safe():
    """集合与首条都一致、只有名次不同：信息相同但排序变了，至少 REVIEW。"""
    out = run(retrieval={"top1_rate": 1.0, "ordered_rate": 0.5, "avg_jaccard": 1.0})
    assert out["verdict"] == "REVIEW"
    assert out["exit_code"] == 1
    assert any("排序" in r for r in out["reasons"])


def test_missing_retrieval_is_never_safe():
    """检索证据缺失 → fail-closed，不得因为"结构和事实都一致"就放行。"""
    out = mod.judge(chunks=copy.deepcopy(CHUNKS_OK), facts=copy.deepcopy(FACTS_OK),
                    retrieval=None, baseline=copy.deepcopy(BASELINE_OK))
    assert out["verdict"] != "SAFE"
    assert out["exit_code"] != 0
    assert any("检索层证据缺失" in r for r in out["reasons"])


def test_partial_retrieval_fields_are_not_safe():
    """检索字段半残（只有 top1）也不能算一致，否则残缺数据会变成假绿。"""
    out = run(retrieval={"top1_rate": 1.0})
    assert out["verdict"] != "SAFE"
    assert out["exit_code"] != 0


def test_missing_facts_evidence_is_not_safe():
    out = mod.judge(chunks=copy.deepcopy(CHUNKS_OK), facts=None,
                    retrieval=copy.deepcopy(RETRIEVAL_OK),
                    baseline=copy.deepcopy(BASELINE_OK))
    assert out["verdict"] != "SAFE"
    assert any("事实层" in r for r in out["reasons"])


def test_missing_baseline_is_unsafe():
    out = mod.judge(chunks=copy.deepcopy(CHUNKS_OK), facts=copy.deepcopy(FACTS_OK),
                    retrieval=copy.deepcopy(RETRIEVAL_OK), baseline=None)
    assert out["verdict"] == "UNSAFE"
    assert any("基线" in r for r in out["reasons"])


def test_exit_codes_are_ci_friendly():
    assert mod.EXIT_CODES == {"SAFE": 0, "REVIEW": 1, "UNSAFE": 2}
    assert run()["exit_code"] == 0
    assert run(facts={"only_a": 1, "only_b": 0})["exit_code"] == 1
    assert run(chunks={"identical": False})["exit_code"] == 2
