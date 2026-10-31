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
