"""授权上下文（P0-03 参考实现）：校验 + 编译成**检索层的过滤谓词**。

核心不变式：
    进入 LLM 上下文的内容必须**在取数时**就已过滤，而不是取回后再滤。
    因此本模块产出的是 SQL 谓词，调用方必须把它放进 WHERE，而不是 Python 里 `if` 掉。

不做什么：
    - 不校验签名（签名验证属网关/服务间认证，需要真实公钥；这里只校验结构与时效）；
    - 不实现图检索（`retrieval_graph` 无文件范围参数，本模块只提供"是否允许走图"的判定）。
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


class AuthZError(PermissionError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as e:
        raise AuthZError("BAD_TIMESTAMP", str(value)) from e
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def validate_context(ctx: dict, *, now: datetime | None = None) -> dict:
    """结构 + 时效校验。缺字段一律拒绝，**不按空权限继续**（E6）。"""
    if not isinstance(ctx, dict):
        raise AuthZError("CONTEXT_MISSING", "必须提供授权上下文，禁止匿名继续")
    for field in ("request_id", "principal_id", "service", "authz_version", "expires_at"):
        if field not in ctx or ctx[field] in (None, ""):
            raise AuthZError("FIELD_MISSING", field)
    if not isinstance(ctx.get("kb_scope"), (list, tuple)) or not ctx["kb_scope"]:
        raise AuthZError("KB_SCOPE_EMPTY", "kb_scope 必须是非空列表")
    if not isinstance(ctx.get("file_scope"), dict) or not ctx["file_scope"]:
        raise AuthZError("FILE_SCOPE_EMPTY", "file_scope 必须是非空映射")
    if not isinstance(ctx["authz_version"], int) or ctx["authz_version"] < 0:
        raise AuthZError("BAD_VERSION", str(ctx["authz_version"]))
    if _parse_ts(ctx["expires_at"]) <= (now or _now()):
        raise AuthZError("CONTEXT_EXPIRED", str(ctx["expires_at"]))
    for kb, files in ctx["file_scope"].items():
        if not ID_RE.match(kb):
            raise AuthZError("BAD_KB_ID", kb)
        if files == "*":
            continue
        if not isinstance(files, (list, tuple)) or not files:
            raise AuthZError("FILE_SCOPE_EMPTY", f"{kb} 未给出文件范围")
        for f in files:
            if not ID_RE.match(str(f)):
                raise AuthZError("BAD_FILE_ID", str(f))
    return ctx


def files_for(ctx: dict, kb_id: str) -> str | list[str]:
    """返回该 kb 的文件范围；`*` 表示整库授权。未授权该 kb 直接拒绝。"""
    if kb_id not in (ctx.get("kb_scope") or []):
        raise AuthZError("KB_NOT_AUTHORIZED", kb_id)
    files = (ctx.get("file_scope") or {}).get(kb_id)
    if files is None:
        raise AuthZError("KB_SCOPE_MISSING", kb_id)
    return files


def can_use_graph(ctx: dict, kb_id: str) -> bool:
    """图检索无法做文件级隔离，只对整库授权开放（P0-03 §4 的降级策略）。"""
    return files_for(ctx, kb_id) == "*"


def _sql_id(value: str) -> str:
    if not ID_RE.match(value):
        raise AuthZError("BAD_ID", value)     # 防注入：只允许白名单字符
    return f"'{value}'"


def compile_chunk_predicate(ctx: dict, kb_id: str) -> str:
    """编译成 document_chunk 上的 SQL 谓词。

    必须放进 WHERE —— 这样"未授权内容"在数据库层就不会被取出，
    满足"进入 LLM 上下文之前已过滤"的不变式。
    """
    files = files_for(ctx, kb_id)
    base = f"kb_id = {_sql_id(kb_id)}"
    if files == "*":
        return base
    allowed = ",".join(_sql_id(str(f)) for f in files)
    return f"{base} AND file_id IN ({allowed})"


def compile_evidence_predicate(ctx: dict, kb_id: str) -> str:
    """证据表同样按文件范围过滤（证据也会进 Prompt，不能豁免）。"""
    files = files_for(ctx, kb_id)
    base = f"kb_id = {_sql_id(kb_id)}"
    if files == "*":
        return base
    allowed = ",".join(_sql_id(str(f)) for f in files)
    return f"{base} AND file_id IN ({allowed})"
