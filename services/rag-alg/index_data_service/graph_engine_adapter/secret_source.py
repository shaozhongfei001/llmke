"""密钥来源链：环境变量 → 文件 → 显式值，任何路径都不打印明文。

与 `llm_config.py` 的分工（互补，不重复）：
- `llm_config.resolve()` 回答"用哪个 provider/model/base、那把钥匙的环境变量叫什么名字"，
  取值只有 `env.get(key_env)` 一条来源，够用但部署形态一变就不够；
- 本模块回答"这把钥匙从哪儿来、取不取得到、落盘文件权限是不是太松"，
  支持 env/file/显式值三级回退，并给出**可以安全写进日志**的描述。

铁律：**明文只出现在 `get()` / `require()` 的返回值里**。
`describe()`、异常消息、日志一律只有「来源类型 + 键名/路径 + sha256 前 8 位指纹」；
取不到就明确写 `absent`。指纹不是加密，它只用来"两次读到的是不是同一把钥匙"
（例如确认 env 覆盖没生效），不足以反推明文。

不做的事：
- 不改文件权限（`warn_if_world_readable` 只报告，不 chmod——静默改权限会让部署侧
  以为自己的权限设置是对的）；
- 不缓存密钥（env 可以在进程内被改，长驻进程缓存住会把轮换变成"要重启才生效"）；
- 不做 KMS/Vault 对接（本仓离线交付，多一个外部依赖就多一条供应链要审）。
"""

import hashlib
import os
import stat
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCHEMA = "llmke.graph-engine.secret-source.v1"

ENV = "env"
FILE = "file"
VALUE = "value"

# 显式值允许的写法；`inline` 只是别名，语义完全一样。
_VALUE_ALIASES = frozenset({"value", "literal", "explicit", "inline"})

# 规范化后的条目：(kind, label, payload)
# - env  : label = 变量名, payload = None
# - file : label = 路径,   payload = None
# - value: label = "value", payload = 值（唯一持有明文的地方）
_Entry = Tuple[str, str, Optional[str]]


class MissingSecret(RuntimeError):
    """所有来源都没有非空值。

    消息只列"查过哪些 env 变量名 / 哪些文件路径"，**不包含任何值**。
    """


def fingerprint(raw: Optional[str]) -> Optional[str]:
    """明文的 sha256 前 8 位；空值返回 None（不要用空串的哈希冒充"有指纹"）。"""
    if not raw:
        return None
    return hashlib.sha256(str(raw).encode("utf-8")).hexdigest()[:8]


def warn_if_world_readable(path: str) -> bool:
    """文件权限是否过宽：`mode & 0o077 != 0` 即组/其他用户可读（True = 该告警）。

    只报告，不改权限。文件不存在或平台没有 POSIX mode 时返回 False——
    "读不到"不是"权限宽"，不该混成一个信号。
    """
    try:
        mode = os.stat(path).st_mode
    except OSError:
        return False
    return bool(stat.S_IMODE(mode) & 0o077)


class SecretSource:
    """按顺序尝试多个来源，返回第一个非空值。

    典型用法：
        SecretSource([("env", "DSEEK_KEY"), ("file", "/etc/llmke/key")])
        SecretSource.from_env("DSEEK_KEY", "/etc/llmke/key")

    便捷写法：条目可以直接给字符串，等价于按环境变量名解释。
    """

    def __init__(self, sources: Optional[Sequence[Any]] = None, *,
                 environ: Optional[Dict[str, str]] = None):
        self._environ = os.environ if environ is None else environ
        self._entries: List[_Entry] = [self._normalize(item) for item in (sources or ())]

    # ---------- 构造 ----------
    @classmethod
    def from_env(cls, name: str, file_path: Optional[str] = None,
                 **kwargs: Any) -> "SecretSource":
        """环境变量优先、文件兜底；给了 file_path 才加第二级。"""
        entries: List[Any] = [(ENV, name)]
        if file_path:
            entries.append((FILE, file_path))
        return cls(entries, **kwargs)

    @staticmethod
    def _normalize(item: Any) -> _Entry:
        if isinstance(item, str):
            return (ENV, item, None)
        try:
            kind, target = item
        except (TypeError, ValueError):
            raise ValueError(f"密钥来源必须是 (类型, 目标) 二元组，收到 {item!r}") from None
        key = str(kind).strip().lower()
        if key == ENV:
            return (ENV, str(target), None)
        if key == FILE:
            return (FILE, str(target), None)
        if key in _VALUE_ALIASES:
            return (VALUE, VALUE, str(target))
        raise ValueError(f"未知的密钥来源类型：{kind!r}（支持 env / file / value）")

    # ---------- 取值 ----------
    @staticmethod
    def _read_file(path: str) -> Optional[str]:
        """读文件；读不到（不存在/无权限/是目录）当作"该来源没有值"，不抛。"""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read()
        except OSError:
            return None

    def _read_entry(self, kind: str, label: str, payload: Optional[str]) -> Optional[str]:
        raw: Optional[str]
        if kind == ENV:
            raw = self._environ.get(label)
        elif kind == FILE:
            raw = self._read_file(label)
        else:
            raw = payload
        if raw is None:
            return None
        # 首尾空白与换行一律去掉：`echo sk-xxx > key` 会带一个换行，
        # 带着它去拼 Authorization 头，报错信息会指向"鉴权失败"这种完全无关的方向。
        cleaned = str(raw).strip()
        return cleaned or None

    def get(self) -> Optional[str]:
        """返回第一个非空值；全空返回 None。"""
        for kind, label, payload in self._entries:
            value = self._read_entry(kind, label, payload)
            if value:
                return value
        return None

    def require(self) -> str:
        """取不到就抛 `MissingSecret`（消息只含来源标识）。"""
        value = self.get()
        if value:
            return value
        raise MissingSecret(self._missing_message())

    # ---------- 可安全打印的描述 ----------
    def describe(self) -> Dict[str, Any]:
        """来源类型 / 键名 / 是否 present / 指纹。**没有明文**。"""
        rows: List[Dict[str, Any]] = []
        resolved: Optional[Dict[str, Any]] = None
        for kind, label, payload in self._entries:
            value = self._read_entry(kind, label, payload)
            present = bool(value)
            rows.append({"kind": kind, "key": label,
                         "state": "present" if present else "absent",
                         "fingerprint": fingerprint(value)})
            if present and resolved is None:
                resolved = {"kind": kind, "key": label, "fingerprint": fingerprint(value)}
        return {"schema": SCHEMA,
                "present": resolved is not None,
                "resolved": resolved if resolved is not None else {"state": "absent"},
                "sources": rows}

    def _missing_message(self) -> str:
        looked: List[str] = []
        for kind, label, _payload in self._entries:
            if kind == ENV:
                looked.append(f"env {label}")
            elif kind == FILE:
                looked.append(f"file {label}")
            else:
                looked.append("value <inline>")
        if not looked:
            return "缺少密钥：没有配置任何来源（值不入日志）"
        return ("缺少密钥：按顺序查找 "
                + " / ".join(looked)
                + "，均未取到非空值（值不入日志）")
