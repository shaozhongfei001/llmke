"""D3 稳定性门禁纯函数测试。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "services" / "rag-alg" / "index_data_service"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_engine_adapter import stability  # noqa: E402


def test_identical_results_are_stable():
    r = stability.evaluate([(["a", "b", "c"], ["a", "b", "c"]),
                            (["x"], ["x"])])
    assert r["verdict"] == "STABLE"
    assert r["top1_ratio"] == 1.0 and r["ordered_mean"] == 1.0


def test_top1_drift_flips_verdict():
    r = stability.evaluate([(["a", "b"], ["z", "a"])])
    assert r["top1_ratio"] == 0.0
    assert r["verdict"] == "REVIEW"


def test_threshold_boundary():
    # 1/2 = 0.5 < 0.8 → REVIEW；调低阈值到 0.5 → STABLE
    pairs = [(["a"], ["a"]), (["b"], ["c"])]
    assert stability.evaluate(pairs).get("verdict") == "REVIEW"
    assert stability.evaluate(pairs, top1_min=0.5).get("verdict") == "STABLE"


def test_empty_results_handled_fail_closed():
    # 空对空无法证明稳定：verdict fail-closed 判 REVIEW（不能拿"没数据"当"没漂移"）
    r = stability.evaluate([([], [])])
    assert r["verdict"] == "REVIEW"
    assert r["per_query"][0]["ordered"] == 1.0


def test_dict_hits_keyed_by_idx():
    r = stability.evaluate([([{"idx": "c1", "text": "t"}], [{"idx": "c1", "text": "t2"}])])
    assert r["top1_ratio"] == 1.0
