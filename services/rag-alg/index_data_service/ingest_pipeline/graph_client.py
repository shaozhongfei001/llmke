"""18094 HTTP 客户端：`/v2/graph/delta` 与 `/v2/fence/revoke`。

为什么单独一个文件（TL 15:0x Q6 裁定）
------------------------------------
`post_graph_build()` 在 `kb_pipeline.py`（L7/L8 已验收），本段不动它；
新客户端放这里，避免为了加两个函数去改已收口文件。

约定
----
- 不 import pydantic / fastapi（与 `kb_delta.py` 同一条约束，v2 环境要能跑）；
- 失败一律抛 `kb_pipeline.PipelineRefused`，**code 已在错误码表里**：
  `GRAPH_API_UNREACHABLE`(502) / `GRAPH_BUILD_HTTP_<status>`(502 前缀) / `GRAPH_BUILD_NOT_BUILT`(502)；
- 不做重试：重试由调用方（Java `RETRY` 回写）驱动，避免双层重试放大故障。
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable, List, Optional

from . import kb_pipeline as K

GRAPH_API_ENV = "LLMKE_V2_GRAPH_API"
SCHEMA_DELTA = "llmke.graph-api.delta/1"
DELTA_PATH = "/v2/graph/delta"
FENCE_REVOKE_PATH = "/v2/fence/revoke"


def graph_api_base(base: Optional[str] = None) -> str:
    return (base or os.environ.get(GRAPH_API_ENV) or K.GRAPH_API_DEFAULT).rstrip("/")


def _post(base: str, path: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    url = base + path
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        # 服务端**拒绝**（4xx/5xx）与「连不上」是两件事：把响应体带出来，否则
        # 调用方只能看到 `HTTP Error 422` 而看不到 `detail`（P4-L13-C 实测：
        # 一次 422 的 detail 里写着「requested_mode=full 必须带 fallback_reason」，
        # 被这里吞掉后多花了两轮才定位）。
        try:
            detail = exc.read().decode("utf-8", "replace")[:400]
        except Exception:  # noqa: BLE001
            detail = ""
        raise K.PipelineRefused(f"GRAPH_BUILD_HTTP_{exc.code}",
                                f"{url}: HTTP {exc.code}: {detail}") from exc
    except Exception as exc:  # noqa: BLE001 - 连不上要带原因，不吞
        raise K.PipelineRefused("GRAPH_API_UNREACHABLE",
                                f"{url}: {type(exc).__name__}: {exc}") from exc
    try:
        return json.loads(raw.decode("utf-8") or "{}")
    except ValueError as exc:
        raise K.PipelineRefused("GRAPH_BUILD_NOT_BUILT",
                                f"{url}: 响应不是 JSON: {raw[:200]!r}") from exc


def wanted_to_delta_docs(wanted: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 `kb_state` 的 wanted docs 归并成契约 §2.1 的 `docs`。

    - **按 `text` 去重**：引擎按文本哈希做 chunk id，同文异源会合并成一块，
      所以用 `file_ids` 数组承载 1:N（`02-CONTRACTS` §2.1）；
    - `content_hash` 用 `sha256(text)`，与 `kb_pipeline._chunk_state_records` 同一口径
      （不另造算法，否则同源校验两侧对不上）。
    """
    by_text: Dict[str, Dict[str, Any]] = {}
    for doc in wanted or []:
        text = str(doc.get("text") or "")
        entry = by_text.get(text)
        if entry is None:
            entry = {
                "file_ids": [],
                "text": text,
                "locator": doc.get("locator") or "",
                "pk": doc.get("pk"),
                "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
            if doc.get("title"):
                entry["title"] = str(doc["title"])
            if doc.get("parse_artifact_id"):
                entry["parse_artifact_id"] = str(doc["parse_artifact_id"])
            by_text[text] = entry
        fid = str(doc.get("file_id"))
        if fid not in entry["file_ids"]:
            entry["file_ids"].append(fid)
    return list(by_text.values())


def post_graph_delta(kb: str, wanted: List[Dict[str, Any]], *, removed: Iterable[Any] = (),
                     set_digest: Optional[str] = None, requested_mode: str = "auto",
                     fallback_reason: Optional[str] = None, root: Optional[str] = None,
                     graph_api: Optional[str] = None,
                     timeout: float = 1800) -> Dict[str, Any]:
    """调 18094 `POST /v2/graph/delta`（契约 §2.1）。"""
    if not kb:
        raise K.PipelineRefused("KB_REQUIRED", "建图必须指定知识库标识")
    docs = wanted_to_delta_docs(wanted)
    revoked = [str(f) for f in (removed or [])]
    if not docs and not revoked:
        # 空 docs 且无撤权：服务端会 400；这里提前如实拒绝，不伪装成功
        raise K.PipelineRefused("DOCS_EMPTY", "没有可建图的块，也无撤权，跳过建图")
    payload: Dict[str, Any] = {
        "schema": SCHEMA_DELTA, "kb": kb, "docs": docs,
        "requested_mode": requested_mode, "fallback_reason": fallback_reason,
        "set_digest": set_digest, "revoked_file_ids": revoked,
    }
    if root:
        payload["root"] = root
    body = _post(graph_api_base(graph_api), DELTA_PATH, payload, timeout)
    status = str(body.get("status") or "")
    if status not in ("BUILT", "SKIPPED_FRESH"):
        raise K.PipelineRefused("GRAPH_BUILD_NOT_BUILT",
                                json.dumps(body, ensure_ascii=False)[:300])
    return body


def post_fence_revoke(kb: str, file_ids: Iterable[Any], *, root: Optional[str] = None,
                      reason: str = "REVOKED",
                      graph_api: Optional[str] = None,
                      timeout: float = 60) -> Dict[str, Any]:
    """调 18094 `POST /v2/fence/revoke`（契约 §3）。

    18096 与 18094 是**两个进程**，18096 拿不到对方的 `FenceState` 内存态，
    所以撤权只能走这个端点（18094 内 `revoke` + `fence.save`）。
    """
    ids = [str(f) for f in (file_ids or []) if str(f).strip()]
    if not ids:
        raise K.PipelineRefused("KB_REQUIRED", "撤权必须指定 file_ids")
    # fail-closed：撤权必须带 root。不带就会落到 18094 进程 env 的图根
    # （= 生产），P4-L13-C 事故正是这样写进了生产 fence.json。
    if not (root or "").strip():
        raise K.PipelineRefused(
            "GRAPH_ROOT_MISSING",
            "撤权必须显式指定 root（禁止默认落到 18094 的 env root）")
    payload = {"kb": kb or "", "file_ids": ids, "reason": reason, "root": str(root)}
    body = _post(graph_api_base(graph_api), FENCE_REVOKE_PATH, payload, timeout)
    revoked = {str(x) for x in (body.get("revoked") or [])}
    missing = [fid for fid in ids if fid not in revoked]
    if missing:
        # 服务端说成功但没记上：不能当成功（否则"撤权了"是假的）
        raise K.PipelineRefused("GRAPH_BUILD_NOT_BUILT",
                                f"撤权未生效：missing={missing} body={body}")
    return body
