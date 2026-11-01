"""灰度策略：名单决定这个 KB 走全量还是增量，改文件即生效，配错就必须停下。

这些用例刻意都断"行为"而不是断"实现"：
- 名单内/名单外各走哪条路（`mode_for` 的真值）；
- 改文件后同一个 `kb_id` 的判断确实变了（回退不需要重启的真实依据）；
- 配错时**抛错而不是按默认跑**（静默降级是最坏的一种"绿灯"）。
"""

import json
from dataclasses import FrozenInstanceError

import pytest

from graph_engine_adapter.canary import (MODES, CanaryConfigError, CanaryPolicy,
                                         choose_rebuild, load)

SECRET_WORDS = ("key", "token", "secret", "password")


def write(tmp_path, payload, name="canary.json"):
    """写一份配置：dict 走 JSON 序列化，str 原样落盘（用于造损坏文件）。"""
    path = tmp_path / name
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return path


def policy(scope=(), mode="delta", default="full"):
    return CanaryPolicy(scope=frozenset(scope), mode=mode, default=default)


# ---------- mode_for：名单内/名单外/空名单 ----------

def test_listed_kb_uses_canary_mode():
    p = policy({"kb_1", "kb_2"}, mode="delta")
    assert p.mode_for("kb_1") == "delta"
    assert p.mode_for("kb_2") == "delta"
    assert p.in_canary("kb_1") is True


def test_unlisted_kb_falls_back_to_default():
    p = policy({"kb_1"}, mode="delta", default="full")
    assert p.mode_for("kb_2") == "full"
    assert p.in_canary("kb_2") is False


def test_empty_scope_means_nobody_is_in_canary():
    p = CanaryPolicy(scope=frozenset(), mode="delta", default="full")
    for kb_id in ("kb_1", "kb_2", "", "unknown-kb"):
        assert p.mode_for(kb_id) == "full"
        assert p.in_canary(kb_id) is False


def test_mode_for_is_prefix_free_exact_match():
    """`kb_1` 在灰度里不等于 `kb_10` 在灰度里：灰度名单按 KB 标识精确匹配。"""
    p = policy({"kb_1"}, mode="delta")
    assert p.mode_for("kb_10") == "full"
    assert p.mode_for("kb_") == "full"


# ---------- 构造校验：非法值必须带原值和允许值 ----------

@pytest.mark.parametrize("field", ["mode", "default"])
def test_illegal_mode_names_raise_with_allowed_and_original(field):
    kwargs = {"scope": frozenset({"kb_1"}), "mode": "delta", "default": "full"}
    kwargs[field] = "gap"
    with pytest.raises(ValueError) as exc:
        CanaryPolicy(**kwargs)
    msg = str(exc.value)
    assert "gap" in msg                      # 原值
    assert all(mode in msg for mode in MODES)  # 允许值


@pytest.mark.parametrize("bad", ["", "   ", "\t\n"])
def test_blank_kb_in_scope_raises(bad):
    with pytest.raises(ValueError) as exc:
        policy({bad})
    assert repr(bad) in str(exc.value)


def test_scope_accepts_comma_string_and_normalizes():
    p = CanaryPolicy(scope=" kb_1 , kb_2 ,kb_1", mode="delta")
    assert p.scope == frozenset({"kb_1", "kb_2"})
    assert p.describe()["count"] == 2


# ---------- describe：结构、排序、不含敏感信息 ----------

def test_describe_shape_and_stable_order():
    p = policy({"kb_c", "kb_a", "kb_b"}, mode="delta", default="full")
    d = p.describe()
    assert list(d.keys()) == ["schema", "scope", "count", "mode", "default", "sources"]
    assert d["scope"] == ["kb_a", "kb_b", "kb_c"]       # 排序后输出，不受 set 顺序影响
    assert d["count"] == 3
    assert d["mode"] == "delta" and d["default"] == "full"
    assert d["schema"] == "llmke.graph-engine.canary-policy.v1"


def test_describe_and_repr_contain_no_secret_words():
    p = policy({"kb_1"}, mode="delta")
    text = (json.dumps(p.describe(), ensure_ascii=False) + repr(p)).lower()
    for word in SECRET_WORDS:
        assert word not in text


def test_describe_does_not_echo_config_path(tmp_path):
    """路径可能带运维账号名，describe 会上报/打日志，不该带出去。"""
    path = write(tmp_path, {"scope": ["kb_1"], "mode": "delta"}, name="ops-account-canary.json")
    text = json.dumps(load(path, env={}).describe(), ensure_ascii=False)
    assert "ops-account-canary.json" not in text


def test_describe_reports_provenance(tmp_path):
    path = write(tmp_path, {"mode": "delta"})
    p = load(path, env={"LLMKE_CANARY_SCOPE": "kb_1"})
    assert p.describe()["sources"] == {"scope": "env", "mode": "file", "default": "default"}


# ---------- 不可变性 ----------

def test_policy_is_frozen():
    p = policy({"kb_1"})
    with pytest.raises(FrozenInstanceError):
        p.scope = frozenset({"kb_9"})
    with pytest.raises(AttributeError):
        p.scope.add("kb_9")          # frozenset 没有 add，改不进去
    assert p.in_canary("kb_9") is False


def test_describe_returns_a_copy_not_internal_state():
    p = policy({"kb_1"})
    d = p.describe()
    d["scope"].append("kb_9")
    assert "kb_9" not in p.scope
    assert p.describe()["scope"] == ["kb_1"]


# ---------- load 优先级：文件 > 环境 > 默认 ----------

def test_file_overrides_env(tmp_path):
    path = write(tmp_path, {"scope": ["kb_1"], "mode": "delta", "default": "full"})
    p = load(path, env={"LLMKE_CANARY_SCOPE": "kb_9", "LLMKE_CANARY_MODE": "full",
                        "LLMKE_CANARY_DEFAULT": "delta"})
    assert p.mode_for("kb_1") == "delta"
    assert p.mode_for("kb_9") == "full"       # 文件里没有 kb_9
    assert p.mode_for("kb_9") != "delta"      # 环境里的 default=delta 被文件覆盖
    assert p.describe()["sources"] == {"scope": "file", "mode": "file", "default": "file"}


def test_missing_file_falls_back_to_env(tmp_path):
    p = load(tmp_path / "nope.json",
             env={"LLMKE_CANARY_SCOPE": "kb_1, kb_2", "LLMKE_CANARY_MODE": "delta"})
    assert p.describe()["scope"] == ["kb_1", "kb_2"]      # 去空白
    assert p.mode_for("kb_1") == "delta"
    assert p.mode_for("kb_3") == "full"
    assert p.describe()["sources"] == {"scope": "env", "mode": "env", "default": "default"}


def test_nothing_configured_is_safe_default():
    p = load(None, env={})
    assert p.scope == frozenset()
    assert p.mode == "full" and p.default == "full"
    assert p.mode_for("kb_1") == "full"
    assert p.in_canary("kb_1") is False
    assert p.describe()["sources"] == {"scope": "default", "mode": "default",
                                      "default": "default"}


def test_blank_env_values_are_treated_as_unset():
    """部署模板里留空值是常态：空值表达"没配"，不该直接炸启动。"""
    p = load(None, env={"LLMKE_CANARY_SCOPE": "   ", "LLMKE_CANARY_MODE": ""})
    assert p.scope == frozenset() and p.mode == "full"


def test_file_overrides_only_the_fields_it_contains(tmp_path):
    path = write(tmp_path, {"mode": "delta"})
    p = load(path, env={"LLMKE_CANARY_SCOPE": "kb_1", "LLMKE_CANARY_DEFAULT": "full"})
    assert p.mode == "delta"
    assert p.scope == frozenset({"kb_1"})
    assert p.describe()["sources"] == {"scope": "env", "mode": "file", "default": "env"}


def test_mode_falls_back_to_configured_default(tmp_path):
    """mode 没配时要取这份策略的 default，而不是写死的 full。"""
    path = write(tmp_path, {"scope": ["kb_1"], "default": "delta"})
    p = load(path, env={})
    assert p.mode == "delta"
    assert p.mode_for("kb_1") == "delta"      # 名单内
    assert p.mode_for("kb_9") == "delta"      # 名单外也用 delta（default 就是 delta）


# ---------- 文件 scope 两种写法等价 ----------

def test_file_scope_accepts_string_and_list_forms(tmp_path):
    as_list = load(write(tmp_path, {"scope": ["kb_1", "kb_2"], "mode": "delta"},
                         name="a.json"), env={})
    as_str = load(write(tmp_path, {"scope": " kb_1 , kb_2 , kb_1 ", "mode": "delta"},
                        name="b.json"), env={})
    assert as_list.describe()["scope"] == ["kb_1", "kb_2"]
    assert as_str.describe()["scope"] == ["kb_1", "kb_2"]   # 去空白 + 去重 + 排序
    assert as_list == as_str


# ---------- 配错必须停：CanaryConfigError 且带路径 ----------

def test_broken_json_raises_config_error_with_path(tmp_path):
    path = write(tmp_path, '{"scope": ["kb_1"],}')
    with pytest.raises(CanaryConfigError) as exc:
        load(path, env={})
    assert isinstance(exc.value, ValueError)     # 兼容捕获 ValueError 的既有调用方
    assert str(path) in str(exc.value)


def test_non_object_json_raises_config_error_with_path(tmp_path):
    path = write(tmp_path, '["kb_1"]')
    with pytest.raises(CanaryConfigError) as exc:
        load(path, env={})
    assert str(path) in str(exc.value)


def test_unknown_mode_in_file_raises_config_error_with_path(tmp_path):
    path = write(tmp_path, {"scope": ["kb_1"], "mode": "gap"})
    with pytest.raises(CanaryConfigError) as exc:
        load(path, env={})
    msg = str(exc.value)
    assert str(path) in msg and "gap" in msg


def test_unknown_field_in_file_is_not_silently_ignored(tmp_path):
    """把 "scope" 拼成 "scop" 时最危险：名单为空、程序照跑，行为等于灰度没生效。"""
    path = write(tmp_path, {"scop": ["kb_1"], "mode": "delta"})
    with pytest.raises(CanaryConfigError) as exc:
        load(path, env={})
    msg = str(exc.value)
    assert "未知字段" in msg and str(path) in msg


def test_blank_scope_entry_in_file_raises_config_error(tmp_path):
    path = write(tmp_path, {"scope": ["kb_1", "  "], "mode": "delta"})
    with pytest.raises(CanaryConfigError) as exc:
        load(path, env={})
    assert str(path) in str(exc.value)


def test_illegal_env_mode_raises_config_error_naming_variable():
    with pytest.raises(CanaryConfigError) as exc:
        load(None, env={"LLMKE_CANARY_MODE": "gap"})
    msg = str(exc.value)
    assert "LLMKE_CANARY_MODE" in msg and "gap" in msg


# ---------- 热改：同一路径两次 load，结果不同 ----------

def test_hot_file_change_takes_effect_without_restart(tmp_path):
    path = write(tmp_path, {"scope": ["kb_1"], "mode": "delta"})
    first = load(path, env={})
    assert first.mode_for("kb_1") == "delta"

    path.write_text(json.dumps({"scope": ["kb_1"], "mode": "full"}), encoding="utf-8")
    second = load(path, env={})
    assert second.mode_for("kb_1") == "full"

    # 旧对象保持原值（值对象语义：回退是造新对象，不是就地改，避免并发读到中间态）
    assert first.mode_for("kb_1") == "delta"
    assert first is not second

    # 出事时把文件删掉：回落环境变量，同样不用重启
    path.unlink()
    third = load(path, env={"LLMKE_CANARY_SCOPE": "kb_1", "LLMKE_CANARY_MODE": "delta"})
    assert third.mode_for("kb_1") == "delta"


def test_reload_is_idempotent_for_same_content(tmp_path):
    path = write(tmp_path, {"scope": ["kb_2", "kb_1"], "mode": "delta"})
    assert load(path, env={}) == load(path, env={})


# ---------- choose_rebuild：接线点 ----------

def test_choose_rebuild_wraps_mode_for():
    p = policy({"kb_1"}, mode="delta", default="full")
    assert choose_rebuild(p, "kb_1") == "delta"
    assert choose_rebuild(p, "kb_2") == "full"
    assert choose_rebuild(p, "kb_2") in MODES
