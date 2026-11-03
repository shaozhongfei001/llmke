"""指标契约断言：把"字符串在不在"升级成"结构对不对、配额自不自洽"。

覆盖的都是线上会真出事、但简单 includes 检查看不出来的情况。
"""

import importlib.util
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "contract", os.path.join(REPO, "scripts", "v2_metrics_contract.py"))
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)

GOOD = """# HELP llmke_graph_scheduler_cycles_total c
# TYPE llmke_graph_scheduler_cycles_total counter
llmke_graph_scheduler_cycles_total 3
# HELP llmke_graph_rebuild_pending p
# TYPE llmke_graph_rebuild_pending gauge
llmke_graph_rebuild_pending 0
# HELP llmke_graph_quota_used u
# TYPE llmke_graph_quota_used gauge
llmke_graph_quota_used{tenant="kb_1"} 2
# HELP llmke_graph_quota_limit l
# TYPE llmke_graph_quota_limit gauge
llmke_graph_quota_limit{tenant="kb_1"} 5
"""


def test_good_text_passes():
    out = contract.validate(GOOD, require_quota=True)
    assert out["ok"] is True and out["problems"] == []
    assert out["quota"]["tenants"] == ["kb_1"]


def test_nan_is_a_violation():
    """nan 会污染 rate()/avg()，但字符串里看它长得像正常样本。"""
    bad = GOOD.replace("llmke_graph_rebuild_pending 0", "llmke_graph_rebuild_pending nan")
    out = contract.validate(bad)
    assert not out["ok"]
    assert any("nan" in p for p in out["problems"])


def test_duplicate_type_is_a_violation():
    bad = GOOD + "# TYPE llmke_graph_rebuild_pending gauge\n"
    out = contract.validate(bad)
    assert any("TYPE 重复" in p for p in out["problems"])


def test_counter_without_total_suffix():
    bad = "# TYPE llmke_graph_bad counter\nllmke_graph_bad 1\n"
    out = contract.validate(bad, required=[])
    assert any("_total" in p for p in out["problems"])


def test_quota_used_without_limit():
    text = GOOD.replace('# HELP llmke_graph_quota_limit l\n'
                         '# TYPE llmke_graph_quota_limit gauge\n'
                         'llmke_graph_quota_limit{tenant="kb_1"} 5\n', "")
    out = contract.validate(text)
    assert any("没有对应 limit" in p for p in out["problems"])


def test_quota_used_exceeds_limit():
    text = GOOD.replace('llmke_graph_quota_used{tenant="kb_1"} 2',
                        'llmke_graph_quota_used{tenant="kb_1"} 9')
    out = contract.validate(text)
    assert any("used(9) > limit(5)" in p for p in out["problems"])


def test_quota_requires_tenant_label():
    text = GOOD.replace('llmke_graph_quota_used{tenant="kb_1"} 2',
                        'llmke_graph_quota_used 2')
    out = contract.validate(text)
    assert any("tenant" in p for p in out["problems"])


def test_require_quota_flag():
    text = GOOD.replace('llmke_graph_quota_used{tenant="kb_1"} 2\n', "") \
               .replace('llmke_graph_quota_limit{tenant="kb_1"} 5\n', "")
    assert contract.validate(text, require_quota=False)["ok"] is True
    assert contract.validate(text, require_quota=True)["ok"] is False


def test_missing_required_series():
    out = contract.validate('# TYPE x gauge\nx 1\n', required=["llmke_graph_rebuild_pending"])
    assert any("缺少必需指标" in p for p in out["problems"])


def test_malformed_line_is_reported():
    out = contract.validate(GOOD + "this is not metrics\n", required=[])
    assert any("格式错误" in p for p in out["problems"])


def test_empty_text_reports_missing():
    out = contract.validate("", required=["llmke_graph_rebuild_pending"])
    assert not out["ok"]
