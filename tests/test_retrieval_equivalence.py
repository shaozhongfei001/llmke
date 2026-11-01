"""检索等价性比较器：只测 compare() 的判据，不加载引擎。

真跑（加载两份快照 + 调模型）在 Q 与证据里，单测这里只钉住"怎么算一致"——
尤其要防"两边都空 → 完全一致"这种假绿。
"""

import importlib.util
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "ret_equiv", os.path.join(REPO, "scripts", "v2_retrieval_equivalence.py"))
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def rows(*hits, route="GRAPH"):
    return [{"query": f"q{i}", "route": route, "hits": list(h), "seconds": 0.1}
            for i, h in enumerate(hits)]


def test_identical_hits_are_full_score():
    out = mod.compare(rows(["a", "b", "c"]), rows(["a", "b", "c"]), 3)
    assert out["top1_rate"] == 1.0
    assert out["ordered_rate"] == 1.0
    assert out["avg_jaccard"] == 1.0


def test_same_set_different_order_is_not_ordered_match():
    out = mod.compare(rows(["a", "b"]), rows(["b", "a"]), 2)
    assert out["avg_jaccard"] == 1.0          # 集合相同
    assert out["ordered_rate"] == 0.0        # 顺序不同
    assert out["top1_rate"] == 0.0           # 首条不同
    assert out["details"][0]["only_a"] == []


def test_disjoint_hits_have_zero_jaccard():
    out = mod.compare(rows(["a", "b"]), rows(["c", "d"]), 2)
    assert out["avg_jaccard"] == 0.0
    assert out["details"][0]["only_a"] == ["a", "b"]
    assert out["details"][0]["only_b"] == ["c", "d"]


def test_empty_hits_do_not_count_as_top1_match():
    """两边都空不能算"首条一致"——这是最容易被忽略的假绿。"""
    out = mod.compare(rows([]), rows([]), 3)
    assert out["top1_rate"] == 0.0
    assert out["ordered_rate"] == 1.0        # 都是空列表，确实"顺序一致"，但不代表检索成功


def test_route_mismatch_is_reported():
    out = mod.compare(rows(["a"], route="GRAPH"), rows(["a"], route="DENSE_FALLBACK"), 3)
    assert out["problems"] and "路线不同" in out["problems"][0]
