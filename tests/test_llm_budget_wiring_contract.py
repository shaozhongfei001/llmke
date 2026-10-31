"""接线契约：钉住 `llm_budget` 与回答段配置/调用之间的形状，防止接线方踩空。

已经落地的接线形状（`llm_config.resolve` / `make_llm_call` 侧，本文件只做**只读**断言）：

- 预算**走 cfg**：`resolve()` 产出 `budget` 键（未配置 `LLMKE_ANSWER_RATE` 时为 `None`），
  `make_llm_call` 从 `cfg["budget"]` 取用并在**每次回答入口**调一次 `before_call()`；
- `make_llm_call(cfg, *, retries=2)` 的签名**不变**——既有调用点一行都不用改，
  限流是"给 cfg 加一个键"的附加能力，不是新参数；
- 预算层**不认识**配置层（`llm_budget` 不 import `llm_config`），依赖单向：
  配置层 → 预算层，避免循环 import。

这份测试不重复验限流逻辑（那在 test_llm_budget.py），只固定"接线方可以依赖什么"。
"""

import ast
import inspect
import json
import urllib.request

import pytest

import graph_engine_adapter.llm_budget as budget_mod
from graph_engine_adapter.llm_budget import (
    ENV_VAR,
    SCHEMA,
    CallBudget,
    RateLimitedError,
    from_env,
    guard,
    parse_limit,
)
from graph_engine_adapter.llm_config import describe as describe_cfg
from graph_engine_adapter.llm_config import make_llm_call, resolve


class FakeResponse:
    """最小可用的 urlopen 替身：让接线测试不触网。"""

    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _cfg_without_budget():
    """老代码手工拼的 cfg：没有 budget 键（走 local，免得要 key）。"""
    return {"schema": "llmke.answer-llm.v1", "provider": "local",
            "base": "http://127.0.0.1:18092/v1", "model": "qwen2.5-7b-instruct",
            "key_env": None, "key": None, "timeout": 5, "max_tokens": 16}


def _cfg_with_budget(budget, key="test-key-not-real"):
    cfg = _cfg_without_budget()
    cfg.update({"provider": "deepseek", "base": "http://127.0.0.1:1/v1",
                "model": "deepseek-flash", "key_env": "TEST_KEY", "key": key,
                "budget": budget})
    return cfg


# ------------------------------------------------------------------ 默认关闭


def test_cfg_without_budget_key_is_tolerated():
    """cfg 里没有 budget 键时必须照常工作（默认关闭，向后兼容老 cfg）。"""
    cfg = _cfg_without_budget()
    assert "budget" not in cfg
    llm_call = make_llm_call(cfg)          # 不报错
    assert callable(llm_call)


def test_resolve_defaults_budget_to_none():
    cfg = resolve({})
    assert "budget" in cfg and cfg["budget"] is None
    assert describe_cfg(cfg)["budget"] is None
    # 未配置限流 → from_env 也是 None → guard 无副作用
    assert from_env({}) is None
    with guard(from_env({})):
        pass


def test_resolve_builds_budget_from_rate_env():
    cfg = resolve({ENV_VAR: "2/60"})
    budget = cfg["budget"]
    assert isinstance(budget, CallBudget)
    assert budget.stats()["capacity"] == 2.0
    assert budget.stats()["refill_per_s"] == budget.stats()["capacity"] / 60.0
    # describe(cfg) 只带摘要，不带密钥
    described = describe_cfg(cfg)
    assert described["budget"]["remaining"] == 2.0
    assert "key_present" in described


def test_budget_layer_does_not_know_llm_config():
    """依赖必须单向：llm_budget 不 import llm_config（否则循环 import）。

    用 AST 扫 import 语句而不是搜文本：docstring/注释里提到 `llm_config` 是给人看的
    说明，不构成依赖（第一版写成文本搜，被自己的注释判红过一次）。
    """
    assert not hasattr(budget_mod, "make_llm_call")
    assert not hasattr(budget_mod, "resolve")

    tree = ast.parse(inspect.getsource(budget_mod))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not [name for name in imported if "llm_config" in name]


# ------------------------------------------------------------- 符号与签名契约


def test_rate_limited_error_is_importable_from_llm_budget():
    """接线侧只需 `from graph_engine_adapter.llm_budget import RateLimitedError`。"""
    from graph_engine_adapter.rate_limit import RateLimitedError as Origin

    assert budget_mod.RateLimitedError is Origin
    budget = CallBudget(0.0, 0.0)
    with pytest.raises(RateLimitedError) as exc:
        budget.before_call()
    assert isinstance(exc.value, Origin)
    assert isinstance(exc.value, RuntimeError)
    assert exc.value.retry_after is None


def test_public_signatures_match_contract():
    """参数名即契约：接线方按名传参，改名就是破坏性变更。"""
    assert list(inspect.signature(parse_limit).parameters) == ["text"]

    init_params = inspect.signature(CallBudget.__init__).parameters
    assert list(init_params) == ["self", "capacity", "refill_per_s", "clock", "sleep"]
    assert init_params["clock"].default is None
    assert init_params["sleep"].default is None

    before = inspect.signature(CallBudget.before_call).parameters
    assert list(before) == ["self", "n"]
    assert before["n"].default == 1

    assert list(inspect.signature(CallBudget.stats).parameters) == ["self"]
    assert list(inspect.signature(CallBudget.describe).parameters) == ["self"]

    env_params = inspect.signature(from_env).parameters
    assert list(env_params) == ["env"]
    assert env_params["env"].default is None

    assert list(inspect.signature(guard).parameters) == ["budget", "n"]


def test_stats_key_set_is_the_consumed_contract():
    """metrics/健康检查消费的键集合固定；多一个少一个都算破坏契约。"""
    stats = CallBudget(6.0, 0.1).stats()
    assert set(stats) == {"schema", "capacity", "refill_per_s", "allowed", "denied",
                          "tokens", "exhausted"}
    assert stats["schema"] == SCHEMA


def test_budget_travels_through_cfg_not_call_signature():
    """预算经 cfg 传递，`make_llm_call` 签名保持 `(cfg, *, retries)` 不变。

    这是**已落地的接线形状**，不是"待接线"标记：加参数会动到 `answer.assemble`
    等既有调用点的契约，所以预算只能作为 cfg 的一个键存在。
    """
    params = inspect.signature(make_llm_call).parameters
    assert set(params) == {"cfg", "retries"}
    assert params["retries"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["retries"].default == 2
    assert "budget" not in params
    # 预算的入口在 cfg 上
    assert "budget" in resolve({}).keys()


# --------------------------------------------------------------- 接线后行为


def test_wired_call_consults_budget_before_touching_network(monkeypatch):
    """冻结预算下，调用在**触网之前**就被拒，且异常类型是 RateLimitedError。"""
    calls = []

    def _forbidden(*args, **kwargs):
        calls.append(args)
        raise AssertionError("预算不足时不应发起网络请求")

    monkeypatch.setattr(urllib.request, "urlopen", _forbidden)

    cfg = _cfg_with_budget(CallBudget(0.0, 0.0))
    llm_call = make_llm_call(cfg)
    with pytest.raises(RateLimitedError) as exc:
        llm_call(messages=[{"role": "user", "content": "hi"}])

    assert calls == []
    assert exc.value.retry_after is None
    assert cfg["budget"].stats()["denied"] == 1


def test_wired_call_spends_exactly_one_token_per_answer(monkeypatch):
    """一次回答扣一个令牌；被截断后的**重试不额外扣**（重试属于同一次回答）。"""

    def _fake_urlopen(req, timeout=None):
        return FakeResponse({"choices": [{"message": {"content": "ok"},
                                         "finish_reason": "stop"}]})

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    budget = CallBudget(2.0, 0.0)
    cfg = _cfg_with_budget(budget)
    llm_call = make_llm_call(cfg)

    assert llm_call(messages=[{"role": "user", "content": "hi"}]) == "ok"
    stats = budget.stats()
    assert stats["allowed"] == 1
    assert stats["tokens"] == 1.0
    assert stats["exhausted"] is False

    # 第二次回答：扣到 0，此后拒绝
    assert llm_call(messages=[{"role": "user", "content": "hi"}]) == "ok"
    assert budget.stats()["tokens"] == 0.0
    with pytest.raises(RateLimitedError):
        llm_call(messages=[{"role": "user", "content": "hi"}])
    assert budget.stats()["allowed"] == 2
    assert budget.stats()["denied"] == 1


def test_truncation_retry_does_not_spend_extra_budget(monkeypatch):
    """finish_reason=length 触发加倍预算重试，但不应额外消耗限流额度。"""
    responses = [{"choices": [{"message": {"content": ""}, "finish_reason": "length"}]},
                 {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}]
    seen = []

    def _fake_urlopen(req, timeout=None):
        seen.append(1)
        return FakeResponse(responses[min(len(seen) - 1, len(responses) - 1)])

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    budget = CallBudget(5.0, 0.0)
    llm_call = make_llm_call(_cfg_with_budget(budget))
    assert llm_call(messages=[{"role": "user", "content": "hi"}], max_tokens=8) == "ok"

    assert len(seen) == 2                     # 确实重试了一次
    assert budget.stats()["allowed"] == 1     # 但只扣一次额度
    assert budget.stats()["tokens"] == 4.0
