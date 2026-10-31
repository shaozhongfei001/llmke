"""`/metrics` 端点的鉴权闸门：把"这次抓取该不该放行"收敛成一个纯判定函数。

为什么需要它：metrics.py 把重建循环的内部状态渲染成 Prometheus 文本，其中
`lease_fencing` / `rebuild_consecutive_failures` / `rebuild_retry_in_seconds`
是运维内部信息，不是公开信息。fencing 尤其敏感——知道当前 fencing 值的调用方
可以据此冒充主实例去动租约。所以这个端点在暴露到非 loopback 之前必须先过一道闸门。

四条刻意的取舍：

1. **返回 `(bool, 稳定原因码)`，原因码不拼接自由文本**。原因码要进日志聚合、要被
   测试用 `==` 断言、要能按码画告警曲线；一旦往码里塞 "token mismatch, expected
   len=32 got 12" 这类文字，码就不再是码，聚合立刻变成高基数垃圾。可读说明走
   `last_detail` / `stats()["last_detail"]` 这个旁路，不进码。
2. **令牌比较先 sha256 再 `hmac.compare_digest`**。`compare_digest` 对**长度不等**
   的入参会直接返回 False，这本身就是一条时序侧信道（"错长度"比"错内容"快得多，
   攻击者可先探长度）——所以两边都过一遍摘要压成等长 32 字节再比。见过"先用 ==
   比长度、再用 compare_digest 比内容"的写法，那等于把侧信道原样保留。
3. **loopback 默认免令牌**。抓取端通常就在同一台机器上（node_exporter / 排障时
   手敲 curl），要求本机也带令牌会诱使运维把它写进 shell history 或 curl 脚本。
   代价是：同一主机上任何进程都能读到指标。这条取舍用 `allow_loopback=False`
   显式收回，且该开关是构造参数（部署时定），不是每次请求的可选行为。
4. **判不了就拒（fail-closed）**。`headers` 不是键值容器、`client_ip` 不是非空
   字符串、内部任何一步抛异常——一律 `(False, "DENY_INTERNAL")`。宁可监控断掉
   并被人发现，也不要"因为参数不对所以放行"。这也是 `require_configured` 的
   动机：生产环境没配令牌本身就是事故，不该静默变成"公开端点"。

不做的事：不做限流/防重放（无共享计数器，本地限流挡不住真攻击，假装有更危险）、
不解析 `X-Forwarded-For`（信任链一旦猜错就等于让任何人自报 IP）、不做令牌轮换
（多令牌需要版本/生效时间语义，当前部署侧没这个需求）、不实现 TLS（网关层的事）。

`stats()` 里**不含任何令牌材料**（连掩码形式都不放），掩码只供调用方显式记日志用。
"""

import hashlib
import ipaddress
import threading
import time
from hmac import compare_digest
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

# ---------------------------------------------------------------- 原因码
# 全部大写 ASCII、无空格无标点：可以直接当日志字段、指标 label、断言字面量。
OK_TOKEN = "OK_TOKEN"
OK_LOOPBACK = "OK_LOOPBACK"
OK_NO_AUTH_CONFIGURED = "OK_NO_AUTH_CONFIGURED"
DENY_BAD_TOKEN = "DENY_BAD_TOKEN"
DENY_MISSING_TOKEN = "DENY_MISSING_TOKEN"
DENY_IP = "DENY_IP"
DENY_INTERNAL = "DENY_INTERNAL"

REASON_CODES: Tuple[str, ...] = (
    OK_TOKEN,
    OK_LOOPBACK,
    OK_NO_AUTH_CONFIGURED,
    DENY_BAD_TOKEN,
    DENY_MISSING_TOKEN,
    DENY_IP,
    DENY_INTERNAL,
)

#: 放行类原因码。调用方不该自己维护这份清单（漏一个就是一处静默拒绝）。
ALLOW_REASONS = frozenset({OK_TOKEN, OK_LOOPBACK, OK_NO_AUTH_CONFIGURED})

_EXPLAIN: Dict[str, str] = {
    OK_TOKEN: "token matched",
    OK_LOOPBACK: "loopback client admitted without token",
    OK_NO_AUTH_CONFIGURED: "no token configured; endpoint is open",
    DENY_BAD_TOKEN: "token mismatch",
    DENY_MISSING_TOKEN: "no usable token in request",
    DENY_IP: "client ip not allowlisted",
    DENY_INTERNAL: "guard could not evaluate the request",
}

_MASK_KEEP_PREFIX = 3
_MASK_KEEP_SUFFIX = 2


# ---------------------------------------------------------------- 小工具
def mask(token: Any) -> str:
    """日志用掩码：露出前 3 位和后 2 位，中间按长度打码。

    长度不足以"露两头还不泄露"时（<= 5 位）**整体打码**。否则 5 位令牌会被
    "前3+后2"完整还原，一个名叫掩码的函数反而成了泄露源。

    保留长度信息（按原长打码）是刻意的：排障时"令牌是不是被 shell 截断了"
    靠长度一眼能看出来，而长度本身不构成可用信息。
    """
    if token is None:
        return "***"
    text = token if isinstance(token, str) else str(token)
    if not text:
        return "***"
    if len(text) <= _MASK_KEEP_PREFIX + _MASK_KEEP_SUFFIX:
        return "*" * len(text)
    return text[:_MASK_KEEP_PREFIX] + "*" * (len(text) - _MASK_KEEP_PREFIX - _MASK_KEEP_SUFFIX) \
        + text[-_MASK_KEEP_SUFFIX:]


def _digest(text: str) -> bytes:
    """压成定长摘要：`compare_digest` 因此永远拿到等长入参。"""
    return hashlib.sha256(text.encode("utf-8")).digest()


def _canonical_ip(raw: str) -> str:
    """归一化 IP 字面量；解析不了就原样返回（交给字面比较去判定）。

    两个真实坑都会在这里被抹平：
    - `::1` 与 `0:0:0:0:0:0:0:1` 是同一个地址，字面比较会判成两个；
    - `::ffff:127.0.0.1`（IPv4-mapped）的 `is_loopback` 是 **False**，
      不做映射还原就会把一个本机请求判成外部请求。
    """
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):      # 容忍 [::1] 这种带括号写法
        text = text[1:-1].strip()
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return text
    mapped = getattr(addr, "ipv4_mapped", None)          # 仅 IPv6Address 有这个属性
    if mapped is not None:
        addr = mapped
    return addr.compressed


def _is_loopback(ip: str) -> bool:
    """判断归一化后的 IP 是否本机。解析失败的字符串只按两个常见字面量认。"""
    try:
        return ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return ip in ("127.0.0.1", "::1")


# ---------------------------------------------------------------- 主体
class MetricGuard:
    """抓取指标前的准入判定。可调用对象，便于直接当 WSGI/handler 前置钩子用。

    `__call__(headers, client_ip) -> (allowed, reason)`，`reason` 恒为 `REASON_CODES`
    里的某个常量；判定过程的自然语言说明放在 `last_detail`（不进返回值）。

    `clock` 可注入：只用于 `stats()` 里的 `last_ok_at` / `last_deny_at`，测试不必真等。
    """

    def __init__(self, token: Optional[str] = None,
                 allow_ips: Optional[Iterable[str]] = None,
                 header_name: str = "Authorization",
                 scheme: str = "Bearer",
                 clock: Optional[Any] = None,
                 require_configured: bool = False,
                 allow_loopback: bool = True):
        if token is not None and not isinstance(token, str):
            raise ValueError("token 必须是 str 或 None")
        if not isinstance(header_name, str) or not header_name.strip():
            raise ValueError("header_name 不能为空")
        if scheme is not None and not isinstance(scheme, str):
            raise ValueError("scheme 必须是 str 或 None")

        # 空串等同未配置：部署侧用环境变量取值时，未设置与设为空是不可区分的，
        # 任由这两种情况走出不同的鉴权行为，等于让"少配一个字符"变成安全事件。
        self.token: Optional[str] = token or None
        self.allow_ips = frozenset(
            _canonical_ip(item) for item in (allow_ips or ()) if isinstance(item, str) and item.strip()
        )
        self.header_name = header_name.strip()
        self.scheme = (scheme or "").strip()
        self.require_configured = bool(require_configured)
        self.allow_loopback = bool(allow_loopback)
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            **{code: 0 for code in REASON_CODES},
            "calls": 0,
            "allowed": 0,
            "denied": 0,
            "last_reason": None,
            "last_detail": None,
            "last_ok_at": None,
            "last_deny_at": None,
        }

    # ------------------------------------------------------------ 公开面
    def __call__(self, headers: Any, client_ip: Any) -> Tuple[bool, str]:
        """永不抛异常：任何意外都折成 `(False, "DENY_INTERNAL")`。

        这条不是洁癖——它是 `/metrics` 的抓取路径，抛出去会把"鉴权判断出错"升级成
        "抓取端 500"，面板上表现为"指标全没了"，根因反而被藏起来。
        """
        try:
            allowed, reason, detail = self._decide(headers, client_ip)
        except Exception as exc:                          # noqa: BLE001
            allowed, reason = False, DENY_INTERNAL
            detail = f"{type(exc).__name__}: {exc}"
        self._record(allowed, reason, detail)
        return allowed, reason

    def stats(self) -> Dict[str, Any]:
        """各原因码计数 + 汇总。快照式返回，调用方改返回值不影响内部状态。"""
        with self._lock:
            return dict(self._state)

    @property
    def last_detail(self) -> Optional[str]:
        with self._lock:
            return self._state["last_detail"]

    @staticmethod
    def explain(reason: str) -> str:
        return _EXPLAIN.get(reason, "unknown reason")

    @staticmethod
    def mask(token: Any) -> str:
        return mask(token)

    # ------------------------------------------------------------ 判定
    def _decide(self, headers: Any, client_ip: Any) -> Tuple[bool, str, str]:
        # 入参自检放在最前：判不了请求是谁发的，就不该替它做"放行"的决定。
        if not callable(getattr(headers, "items", None)):
            return (False, DENY_INTERNAL,
                    f"headers must be a mapping, got {type(headers).__name__}")
        if not isinstance(client_ip, str) or not client_ip.strip():
            return (False, DENY_INTERNAL,
                    f"client_ip must be a non-empty str, got {type(client_ip).__name__}")

        if self.require_configured and not self.token:
            return (False, DENY_MISSING_TOKEN,
                    "token required by policy but none configured; refusing instead of "
                    "treating the endpoint as open")

        if self.allow_ips:
            verdict = self._ip_verdict(client_ip)
            if verdict is not None:
                return verdict

        if not self.token:
            return True, OK_NO_AUTH_CONFIGURED, _EXPLAIN[OK_NO_AUTH_CONFIGURED]

        provided = self._extract(headers)
        if provided is None:
            return (False, DENY_MISSING_TOKEN,
                    f"no usable value in header {self.header_name!r}")
        if not self._token_matches(provided):
            return False, DENY_BAD_TOKEN, _EXPLAIN[DENY_BAD_TOKEN]
        return True, OK_TOKEN, _EXPLAIN[OK_TOKEN]

    def _ip_verdict(self, client_ip: str) -> Optional[Tuple[bool, str, str]]:
        """IP 层判定：返回 None 表示"IP 这关过了，继续走令牌校验"。

        loopback 优先于白名单：本机抓取不该因为白名单里没写 `127.0.0.1` 而被拒
        ——那是最常见的一次配错。`allow_loopback=False` 时本机也要令牌，但若它
        确实在白名单里，就该继续走令牌校验，而不是直接判 DENY_IP。
        """
        ip = _canonical_ip(client_ip)
        listed = ip in self.allow_ips
        if _is_loopback(ip):
            if self.allow_loopback:
                return True, OK_LOOPBACK, _EXPLAIN[OK_LOOPBACK]
            if listed:
                return None                     # 不允许免令牌，但 IP 本身是被许可的
            return False, DENY_IP, f"loopback client {ip} rejected (allow_loopback=False)"
        if listed:
            return None
        return False, DENY_IP, f"client ip {ip} not in allowlist"

    def _extract(self, headers: Mapping[str, Any]) -> Optional[str]:
        """从头部取出待比较的令牌；取不到返回 None。

        键名大小写不敏感（HTTP 头部本来就不区分大小写，但 dict 区分，且反代/测试桩
        经常给出小写）。值是 `Bearer xxx` 还是裸 `xxx` 都接受：裸令牌是给内网
        curl 和 Prometheus `authorization` 配置里那些不写 scheme 的场景留的口子。
        """
        target = self.header_name.lower()
        raw: Any = None
        for key, value in headers.items():
            if isinstance(key, str) and key.strip().lower() == target:
                raw = value
                break
        if raw is None:
            return None
        text = raw if isinstance(raw, str) else str(raw)
        text = text.strip()
        if not text:
            return None

        if self.scheme:
            parts = text.split(None, 1)
            if parts[0].lower() == self.scheme.lower():
                # "Bearer" 后面什么都没有 = 有 scheme 无凭证，属于"缺令牌"而非"错令牌"。
                if len(parts) == 1:
                    return None
                return parts[1].strip() or None
        return text

    def _token_matches(self, provided: str) -> bool:
        # 两边都过 sha256：既保证入参等长（见模块 docstring 取舍 2），也避免把
        # 明文令牌留在比较函数的调用栈/局部变量里更长时间。
        return compare_digest(_digest(provided), _digest(self.token or ""))

    # ------------------------------------------------------------ 记账
    def _record(self, allowed: bool, reason: str, detail: str) -> None:
        now = self._clock()
        with self._lock:
            self._state["calls"] += 1
            self._state[reason] = self._state.get(reason, 0) + 1
            if allowed:
                self._state["allowed"] += 1
                self._state["last_ok_at"] = now
            else:
                self._state["denied"] += 1
                self._state["last_deny_at"] = now
            self._state["last_reason"] = reason
            self._state["last_detail"] = detail
