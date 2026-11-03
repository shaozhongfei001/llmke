"""中文兼容补丁：上游会把中文清空，这是"图没跑"的根因；补丁行为要能被单独验证。"""

from graph_engine_adapter.hipporag_compat import cjk_text_processing


def test_upstream_behaviour_would_erase_chinese():
    """复现上游规则，证明"空主谓"不是抽取问题而是清洗问题。"""
    import re
    upstream = re.sub("[^A-Za-z0-9 ]", " ", "产品甲 最高额度 8000万元".lower()).strip()
    assert upstream == "8000"          # 中文全没了，只剩数字


def test_patch_keeps_chinese_and_digits():
    out = cjk_text_processing("产品甲 最高额度 8000万元")
    assert "产品甲" in out and "最高额度" in out and "8000" in out
    assert "万元" in out                 # 单位也保留，否则账目对不上


def test_patch_still_normalizes_punctuation_and_case():
    out = cjk_text_processing("Product A：额度（万元）！")
    assert "：" not in out and "（" not in out and "！" not in out
    assert "product a" in out and "额度" in out and "万元" in out


def test_patch_handles_list_and_non_str():
    assert cjk_text_processing(["产品甲", 8000]) == ["产品甲", "8000"]


def test_patch_is_opt_in():
    """默认不能自行安装：不调用 install 时，模块里只有函数，没有副作用。"""
    import importlib
    mod = importlib.import_module("graph_engine_adapter.hipporag_compat")
    assert callable(mod.install_cjk_text_processing)
    # 导入本模块本身不应改变任何 hipporag 行为（hipporag 可能未安装，则跳过）
    assert mod.is_patched() in (None, False)
