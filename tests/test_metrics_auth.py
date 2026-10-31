"""`MetricGuard` 的准入判定。

这些用例的共同立场：**只断言"没抛异常"等于没测**。鉴权模块最常见的假绿是
"配了错令牌也返回 False，所以看起来正常"——所以要钉住的是**具体原因码**：
错令牌必须是 `DENY_BAD_TOKEN` 而不是 `DENY_MISSING_TOKEN`/`DENY_IP`，
否则日志里"令牌错"会被记成"没带令牌"，排障方向直接跑偏。

另外两条刻意写进断言的语义：
- 白名单命中后**必须继续**走令牌校验（用"IP 对 + 令牌错 → DENY_BAD_TOKEN"证明
  IP 那关是真的放过去了，而不是 IP 对就整体放行）；
- 判定真的由 `compare_digest` 驱动（用 spy 强制它返回 False，正确令牌也必须被拒）。
"""

import threading

import pytest

from graph_engine_adapter import metrics_auth
from graph_engine_adapter.metrics_auth import (
    ALLOW_REASONS,
    DENY_BAD_TOKEN,
    DENY_INTERNAL,
    DENY_IP,
    DENY_MISSING_TOKEN,
    OK_LOOPBACK,
    OK_NO_AUTH_CONFIGURED,
    OK_TOKEN,
    REASON_CODES,
    MetricGuard,
    mask,
)

TOKEN = "s3cr3t-token-value"
OUTSIDER = "198.51.100.9"


def auth(value):
    return {"Authorization": value}


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


# ---------------------------------------------------------------- 原因码契约
def test_reason_codes_are_stable_and_allow_set_is_consistent():
    assert REASON_CODES == (OK_TOKEN, OK_LOOPBACK, OK_NO_AUTH_CONFIGURED,
                            DENY_BAD_TOKEN, DENY_MISSING_TOKEN, DENY_IP, DENY_INTERNAL)
    assert ALLOW_REASONS == frozenset({OK_TOKEN, OK_LOOPBACK, OK_NO_AUTH_CONFIGURED})
    # 放行集合必须恰好是 OK_ 前缀那三个，否则调用方按前缀判断会判断错
    assert {code for code in REASON_CODES if code.startswith("OK_")} == set(ALLOW_REASONS)


def test_every_allow_reason_matches_its_verdict():
    cases = [
        (MetricGuard(), {}, OUTSIDER, OK_NO_AUTH_CONFIGURED),
        (MetricGuard(token=TOKEN), auth(TOKEN), OUTSIDER, OK_TOKEN),
        (MetricGuard(token=TOKEN, allow_ips=["203.0.113.1"]), {}, "127.0.0.1", OK_LOOPBACK),
    ]
    for guard, headers, ip, expected in cases:
        allowed, reason = guard(headers, ip)
        assert (allowed, reason) == (True, expected)
        assert reason in ALLOW_REASONS


# ---------------------------------------------------------------- 未配置
def test_no_token_configured_is_open():
    guard = MetricGuard()
    assert guard({}, OUTSIDER) == (True, OK_NO_AUTH_CONFIGURED)
    assert guard(auth("whatever"), OUTSIDER) == (True, OK_NO_AUTH_CONFIGURED)
    assert guard.stats()["OK_NO_AUTH_CONFIGURED"] == 2


def test_empty_token_is_treated_as_not_configured():
    # 环境变量漏配 vs 配成空串在部署侧不可区分，不能让两者走出不同鉴权行为
    guard = MetricGuard(token="")
    assert guard({}, OUTSIDER) == (True, OK_NO_AUTH_CONFIGURED)
    assert MetricGuard(token="   ").token == "   "   # 空白串是"真令牌"，只是极不可能对上


def test_require_configured_refuses_instead_of_going_open():
    guard = MetricGuard(require_configured=True)
    allowed, reason = guard(auth(TOKEN), OUTSIDER)
    assert (allowed, reason) == (False, DENY_MISSING_TOKEN)
    detail = guard.last_detail
    assert "required by policy" in detail and "none configured" in detail
    assert guard.stats()["denied"] == 1 and guard.stats()["allowed"] == 0


def test_require_configured_does_not_block_a_configured_guard():
    guard = MetricGuard(token=TOKEN, require_configured=True)
    assert guard(auth(TOKEN), OUTSIDER) == (True, OK_TOKEN)
    assert guard(auth("nope"), OUTSIDER) == (False, DENY_BAD_TOKEN)


# ---------------------------------------------------------------- 令牌判定
def test_correct_bearer_token_is_admitted():
    guard = MetricGuard(token=TOKEN)
    assert guard(auth(f"Bearer {TOKEN}"), OUTSIDER) == (True, OK_TOKEN)
    assert guard.last_detail == "token matched"


def test_bare_token_without_scheme_is_admitted():
    guard = MetricGuard(token=TOKEN)
    assert guard(auth(TOKEN), OUTSIDER) == (True, OK_TOKEN)


def test_wrong_token_is_denied_as_bad_token():
    guard = MetricGuard(token=TOKEN)
    assert guard(auth("Bearer nope"), OUTSIDER) == (False, DENY_BAD_TOKEN)
    assert guard.last_detail == "token mismatch"


def test_token_prefix_is_not_enough():
    # 常见错误实现用 startswith/`in` 比较，那会让前缀令牌直接通过
    guard = MetricGuard(token=TOKEN)
    assert guard(auth(f"Bearer {TOKEN[:6]}"), OUTSIDER) == (False, DENY_BAD_TOKEN)


def test_missing_header_and_blank_header_are_missing_token():
    guard = MetricGuard(token=TOKEN)
    assert guard({}, OUTSIDER) == (False, DENY_MISSING_TOKEN)
    assert guard(auth(""), OUTSIDER) == (False, DENY_MISSING_TOKEN)
    assert guard(auth("   "), OUTSIDER) == (False, DENY_MISSING_TOKEN)
    # "Bearer" 后面没有凭证：属于缺令牌，不是错令牌
    assert guard(auth("Bearer"), OUTSIDER) == (False, DENY_MISSING_TOKEN)
    assert guard(auth("Bearer   "), OUTSIDER) == (False, DENY_MISSING_TOKEN)


def test_scheme_matching_is_case_insensitive():
    guard = MetricGuard(token=TOKEN)
    for value in (f"bearer {TOKEN}", f"BEARER {TOKEN}", f"BeArEr {TOKEN}"):
        assert guard(auth(value), OUTSIDER) == (True, OK_TOKEN)


def test_other_scheme_is_treated_as_bare_token_and_rejected():
    # 文档化行为：不支持 Basic/Digest，整个字符串当裸令牌，因此必然对不上
    guard = MetricGuard(token=TOKEN)
    assert guard(auth(f"Basic {TOKEN}"), OUTSIDER) == (False, DENY_BAD_TOKEN)


def test_header_key_case_insensitive():
    guard = MetricGuard(token=TOKEN)
    assert guard({"authorization": f"Bearer {TOKEN}"}, OUTSIDER) == (True, OK_TOKEN)
    assert guard({"AUTHORIZATION": f"Bearer {TOKEN}"}, OUTSIDER) == (True, OK_TOKEN)


def test_custom_header_name_and_empty_scheme():
    guard = MetricGuard(token=TOKEN, header_name="X-Metrics-Token", scheme="")
    assert guard({"x-metrics-token": TOKEN}, OUTSIDER) == (True, OK_TOKEN)
    # 换了头名就不该再认 Authorization（否则等于留了个隐式后门）
    assert guard(auth(TOKEN), OUTSIDER) == (False, DENY_MISSING_TOKEN)


# ---------------------------------------------------------------- 时序侧信道
def test_compare_digest_receives_equal_length_digests(monkeypatch):
    seen = []
    real = metrics_auth.compare_digest

    def spy(a, b):
        seen.append((a, b))
        return real(a, b)

    monkeypatch.setattr(metrics_auth, "compare_digest", spy)
    guard = MetricGuard(token=TOKEN)

    assert guard(auth("x"), OUTSIDER) == (False, DENY_BAD_TOKEN)
    assert guard(auth(TOKEN * 7), OUTSIDER) == (False, DENY_BAD_TOKEN)   # 长度差异也不早退

    assert len(seen) == 2
    for a, b in seen:
        assert isinstance(a, bytes) and isinstance(b, bytes)
        assert len(a) == len(b) == 32      # sha256 定长，长度信息不会泄露给 compare_digest
    assert seen[0][0] != seen[1][0]


def test_verdict_actually_depends_on_compare_digest(monkeypatch):
    # 反向证明：把比较结果强制成 False，正确令牌也必须被拒。
    # 如果实现里偷偷走了 `==` 快捷路径，这条会 FAIL。
    monkeypatch.setattr(metrics_auth, "compare_digest", lambda a, b: False)
    guard = MetricGuard(token=TOKEN)
    assert guard(auth(TOKEN), OUTSIDER) == (False, DENY_BAD_TOKEN)
    assert guard.stats()["OK_TOKEN"] == 0


# ---------------------------------------------------------------- IP 白名单
def test_allowlisted_ip_passes_ip_gate_then_faces_token_gate():
    guard = MetricGuard(token=TOKEN, allow_ips=["203.0.113.7"])
    assert guard(auth(TOKEN), "203.0.113.7") == (True, OK_TOKEN)
    # 关键：IP 命中但令牌错 → 拒绝原因是令牌，说明 IP 关确实放行了而不是整体放行
    assert guard(auth("wrong"), "203.0.113.7") == (False, DENY_BAD_TOKEN)
    assert guard({}, "203.0.113.7") == (False, DENY_MISSING_TOKEN)


def test_non_allowlisted_ip_is_denied_before_token_check():
    guard = MetricGuard(token=TOKEN, allow_ips=["203.0.113.7"])
    # 即使令牌正确也必须拒：否则白名单只是装饰
    assert guard(auth(TOKEN), "203.0.113.8") == (False, DENY_IP)
    assert guard.stats()["DENY_IP"] == 1
    assert guard.stats()["OK_TOKEN"] == 0


def test_allowlist_does_not_apply_when_empty():
    guard = MetricGuard(token=TOKEN)
    assert guard(auth(TOKEN), OUTSIDER) == (True, OK_TOKEN)


def test_loopback_is_admitted_without_token_by_default():
    guard = MetricGuard(token=TOKEN, allow_ips=["203.0.113.7"])
    for ip in ("127.0.0.1", "::1", "0:0:0:0:0:0:0:1", "::ffff:127.0.0.1"):
        assert guard({}, ip) == (True, OK_LOOPBACK), ip
    assert guard.stats()["OK_LOOPBACK"] == 4


def test_loopback_can_be_forced_to_authenticate():
    guard = MetricGuard(token=TOKEN, allow_ips=["127.0.0.1"], allow_loopback=False)
    # 白名单里显式列了 127.0.0.1：IP 关放行，改为要求令牌
    assert guard({}, "127.0.0.1") == (False, DENY_MISSING_TOKEN)
    assert guard(auth(TOKEN), "127.0.0.1") == (True, OK_TOKEN)
    # 未列入白名单的 loopback 直接被 IP 关拒掉
    assert guard({}, "127.0.0.2") == (False, DENY_IP)


def test_ipv4_mapped_ipv6_is_not_mistaken_for_external():
    # ipaddress.IPv6Address('::ffff:127.0.0.1').is_loopback 是 False，不还原映射就是漏洞
    guard = MetricGuard(token=TOKEN, allow_ips=["127.0.0.1"], allow_loopback=False)
    assert guard(auth(TOKEN), "::ffff:127.0.0.1") == (True, OK_TOKEN)


# ---------------------------------------------------------------- 绝不抛
def test_invalid_inputs_deny_internal_instead_of_raising():
    guard = MetricGuard(token=TOKEN)
    assert guard(None, OUTSIDER) == (False, DENY_INTERNAL)
    assert guard(auth(TOKEN), None) == (False, DENY_INTERNAL)
    assert guard(auth(TOKEN), 42) == (False, DENY_INTERNAL)
    assert guard(auth(TOKEN), "   ") == (False, DENY_INTERNAL)
    # list 不是键值容器：不接受，但不抛
    assert guard([("Authorization", TOKEN)], OUTSIDER) == (False, DENY_INTERNAL)
    assert guard.stats()["DENY_INTERNAL"] == 5


def test_exception_inside_headers_is_contained():
    class Exploding(dict):
        def items(self):
            raise RuntimeError("boom")

    guard = MetricGuard(token=TOKEN)
    assert guard(Exploding(), OUTSIDER) == (False, DENY_INTERNAL)
    assert "RuntimeError: boom" in guard.last_detail


def test_non_str_header_value_is_coerced_not_raising():
    guard = MetricGuard(token=TOKEN)
    assert guard({"Authorization": 12345}, OUTSIDER) == (False, DENY_BAD_TOKEN)


def test_constructor_rejects_nonsense_config():
    with pytest.raises(ValueError):
        MetricGuard(token=123)
    with pytest.raises(ValueError):
        MetricGuard(token=TOKEN, header_name="")
    with pytest.raises(ValueError):
        MetricGuard(token=TOKEN, scheme=7)


# ---------------------------------------------------------------- 记账
def test_stats_counts_each_reason():
    clock = Clock()
    guard = MetricGuard(token=TOKEN, clock=clock)
    guard(auth(TOKEN), OUTSIDER)
    guard(auth(TOKEN), OUTSIDER)
    guard(auth("bad"), OUTSIDER)
    guard({}, OUTSIDER)
    guard(auth(TOKEN), None)

    stats = guard.stats()
    assert stats["OK_TOKEN"] == 2
    assert stats["DENY_BAD_TOKEN"] == 1
    assert stats["DENY_MISSING_TOKEN"] == 1
    assert stats["DENY_INTERNAL"] == 1
    assert stats["calls"] == 5
    assert stats["allowed"] == 2 and stats["denied"] == 3
    assert stats["last_reason"] == DENY_INTERNAL
    assert stats["last_ok_at"] == 1000.0 and stats["last_deny_at"] == 1000.0
    assert set(REASON_CODES) <= set(stats)


def test_stats_snapshot_is_detached():
    guard = MetricGuard(token=TOKEN)
    guard(auth(TOKEN), OUTSIDER)
    snapshot = guard.stats()
    snapshot["OK_TOKEN"] = 999
    assert guard.stats()["OK_TOKEN"] == 1


def test_stats_never_leaks_token_material():
    guard = MetricGuard(token=TOKEN)
    guard(auth(TOKEN), OUTSIDER)
    guard(auth(TOKEN), OUTSIDER)
    dumped = repr(guard.stats()) + repr(guard.last_detail)
    assert TOKEN not in dumped
    assert mask(TOKEN) not in dumped


def test_stats_are_thread_safe():
    guard = MetricGuard(token=TOKEN)
    per_thread, threads_n = 50, 8

    def worker():
        for _ in range(per_thread):
            guard(auth(TOKEN), OUTSIDER)
            guard(auth("bad"), OUTSIDER)

    threads = [threading.Thread(target=worker) for _ in range(threads_n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    stats = guard.stats()
    assert stats["OK_TOKEN"] == per_thread * threads_n
    assert stats["DENY_BAD_TOKEN"] == per_thread * threads_n
    assert stats["calls"] == 2 * per_thread * threads_n


# ---------------------------------------------------------------- 掩码
def test_mask_shows_edges_and_hides_the_middle():
    assert mask(TOKEN) == "s3c" + "*" * (len(TOKEN) - 5) + "ue"
    assert mask("abcdefg") == "abc**fg"        # 前 3 位 + 2 位掩码 + 后 2 位，长度不变


def test_mask_fully_hides_short_values():
    assert mask(None) == "***"
    assert mask("") == "***"
    # <=5 位时"前3后2"会把令牌完整还原，所以整体打码
    assert mask("abcd") == "****"
    assert mask("abcde") == "*****"


def test_mask_accepts_non_str_and_is_exposed_on_guard():
    assert mask(12345) == "*****"
    assert MetricGuard.mask(TOKEN) == mask(TOKEN)
    assert MetricGuard.mask(None) == "***"
