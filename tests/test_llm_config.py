"""回答段模型配置：键只在环境里，代码与日志里都不出现。"""

import pytest

from graph_engine_adapter.llm_config import describe, make_llm_call, resolve


def test_default_is_deepseek_flash():
    cfg = resolve({})
    assert cfg["provider"] == "deepseek"
    assert cfg["base"] == "https://api.deepseek.com/v1"
    assert cfg["model"] == "deepseek-flash"
    assert cfg["key_env"] == "DSEEK_2026_SZF_KEY"
    assert cfg["key"] is None


def test_local_provider_has_no_key_requirement():
    cfg = resolve({"LLMKE_ANSWER_PROVIDER": "local"})
    assert cfg["provider"] == "local" and cfg["base"].startswith("http://127.0.0.1")
    assert cfg["key"] is None


def test_describe_never_leaks_key_value():
    cfg = resolve({"DSEEK_2026_SZF_KEY": "sk-super-secret-value"})
    d = describe(cfg)
    assert d["key_present"] is True and d["key_len"] == len("sk-super-secret-value")
    assert "sk-super-secret-value" not in str(d)
    assert d["ready"] is True


def test_missing_key_raises_helpful_error_not_401():
    cfg = resolve({"DSEEK_2026_SZF_KEY": ""})
    with pytest.raises(RuntimeError) as exc:
        make_llm_call(cfg)
    assert "DSEEK_2026_SZF_KEY" in str(exc.value)


def test_custom_model_and_key_env_are_honoured():
    cfg = resolve({"LLMKE_ANSWER_MODEL": "deepseek-v4-pro",
                   "LLMKE_ANSWER_KEY_ENV": "MY_KEY", "MY_KEY": "abc"})
    assert cfg["model"] == "deepseek-v4-pro" and cfg["key"] == "abc"
    assert cfg["key_env"] == "MY_KEY"


def test_key_file_fallback_does_not_change_env_priority(tmp_path):
    """密钥来源链：env 优先、文件兜底；文件里的换行必须被去掉。"""
    from graph_engine_adapter.llm_config import resolve

    key_file = tmp_path / "key"
    key_file.write_text("from-file\n", encoding="utf-8")

    # 只有文件：走兜底
    assert resolve({"LLMKE_ANSWER_KEY_FILE": str(key_file)})["key"] == "from-file"
    # 两者都有：env 仍然优先（不能因为加了文件兜底就改了原有优先级）
    both = resolve({"DSEEK_2026_SZF_KEY": "from-env",
                    "LLMKE_ANSWER_KEY_FILE": str(key_file)})
    assert both["key"] == "from-env"
    assert both["key_file"] == str(key_file)


def test_key_file_missing_falls_back_to_none(tmp_path):
    from graph_engine_adapter.llm_config import resolve

    cfg = resolve({"LLMKE_ANSWER_KEY_FILE": str(tmp_path / "nope")})
    assert cfg["key"] is None


def test_budget_is_off_by_default():
    """不配 LLMKE_ANSWER_RATE 时必须完全保持原行为：没有预算对象、不额外计时。"""
    from graph_engine_adapter.llm_config import describe, resolve

    cfg = resolve({"DSEEK_2026_SZF_KEY": "k"})
    assert cfg["budget"] is None
    assert describe(cfg)["budget"] is None


def test_budget_is_built_when_rate_configured():
    from graph_engine_adapter.llm_config import resolve

    cfg = resolve({"DSEEK_2026_SZF_KEY": "k", "LLMKE_ANSWER_RATE": "3/60"})
    assert cfg["budget"] is not None
    assert cfg["budget"].stats()["capacity"] == 3.0


def test_budget_rejects_bad_rate_with_original_value():
    import pytest

    from graph_engine_adapter.llm_config import resolve

    with pytest.raises(ValueError) as excinfo:
        resolve({"DSEEK_2026_SZF_KEY": "k", "LLMKE_ANSWER_RATE": "abc"})
    assert "abc" in str(excinfo.value)
