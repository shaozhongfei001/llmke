"""C1 遗留问题的最小反例：`phrase_weights /= number_of_occurs` 的 0 除。

上游代码（hipporag 2.0.0a4，`HippoRAG.graph_search_with_fact_entities`）：
```
number_of_occurs = np.zeros(len(self.graph.vs['name']))
... 只有出现在 top_k_facts 里的顶点才 += 1 ...
phrase_weights /= number_of_occurs      # 其余顶点 0/0 = NaN
```
这里不改上游，只把这段算术**原样复现**，钉住三条事实：
1. 任何没被 fact 命中的顶点都会得到 NaN —— 不是偶发，是必然；
2. 只要后续只读"出现过"的顶点，NaN 不会进入结果（这解释了为什么实跑没炸）；
3. 一旦按 `phrase_id=None` 去索引，`arr[None]` 返回的是**整个数组**而不是标量，
   这条路径会把 NaN 带出来（下游若直接比较/平均就会污染）。

用 numpy 复现而不是调用引擎方法，是因为后者需要完整 igraph/PPR 状态；
断言的是**算术性质**，不冒充"运行时一定出 NaN"。
"""

import numpy as np
import pytest


def _reproduce(n_vertices, fact_vertex_ids):
    phrase_weights = np.zeros(n_vertices)
    number_of_occurs = np.zeros(n_vertices)
    for vid in fact_vertex_ids:
        phrase_weights[vid] += 1.0
        number_of_occurs[vid] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        phrase_weights = phrase_weights / number_of_occurs
    return phrase_weights


def test_vertices_without_facts_become_nan():
    weights = _reproduce(5, fact_vertex_ids=[0, 2])
    assert np.isnan(weights[1]) and np.isnan(weights[3]) and np.isnan(weights[4])
    assert weights[0] == 1.0 and weights[2] == 1.0
    # 未被命中的顶点数量与 NaN 数量相等 —— 必然发生，不是概率事件
    assert int(np.isnan(weights).sum()) == 3


def test_reading_only_hit_vertices_is_safe():
    weights = _reproduce(5, fact_vertex_ids=[0, 2])
    hit_only = [weights[i] for i in (0, 2)]
    assert all(np.isfinite(v) for v in hit_only)


def test_none_index_returns_whole_array_and_leaks_nan():
    """phrase_id 为 None 时 `weights[None]` 不是标量，而是整个数组（含 NaN）。"""
    weights = _reproduce(5, fact_vertex_ids=[0])
    leaked = weights[None]
    assert isinstance(leaked, np.ndarray)
    # 索引 None 会在最前面加一个轴：形状 (1, n)，不是标量，也不是原形状
    assert leaked.ndim == weights.ndim + 1
    assert np.isnan(leaked).any()


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("hipporag") is None,
    reason="本机没有 hipporag 环境（另见 hipporag 独立 venv）")
def test_upstream_still_has_the_unguarded_division():
    """上游是否已加保护：读源码确认仍是裸除法；若已修，这条会红，提醒我们更新结论。"""
    import inspect

    import hipporag

    src = inspect.getsource(hipporag.HippoRAG.graph_search_with_fact_entities)
    assert "number_of_occurs" in src
    assert "/= number_of_occurs" in src, "上游已改，需重新评估 NaN 结论"
