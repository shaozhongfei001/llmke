"""从 legacy ES 取块：兼容层的输入适配，不碰图引擎。

为什么需要：legacy `/generate_triple_data` 的请求**不带正文**，只给
`space_name + col_name + col_values`，由 Python 侧去 ES 捞 chunk
（`index_graph_service/graph_fun_tool.py:908`）。V2 建图要求自带 docs，
所以兼容层必须补这一跳，否则产品链路根本进不来。

只读 ES 代理（默认 127.0.0.1:19527 的 `/search_by_custom_param`），不写任何东西。
"""

import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

DEFAULT_ES_PROXY = "http://127.0.0.1:19527"


def _proxy() -> str:
    return os.environ.get("LLMKE_V2_ES_PROXY", DEFAULT_ES_PROXY).rstrip("/")


def _default_post(url: str, payload: Dict[str, Any]) -> Any:
    import requests

    return requests.post(url, json=payload, timeout=60)


def _field(meta: Dict[str, Any], *names: str) -> Optional[str]:
    for name in names:
        value = meta.get(name)
        if value not in (None, "", "None", "null"):
            return str(value)
    return None


def _locator(meta: Dict[str, Any], chunk_id: str) -> str:
    """定位串：优先页码 + offset + chunk 序号；都没有才退回 ES 文档 id。

    不编页码：缺页码时写 `es:<id>`，调用方一眼能看出"这条只能回指到块级"。
    """
    page = _field(meta, "page_number", "page_num", "page")
    offset = _field(meta, "offset")
    index = _field(meta, "chunk_index")
    if page or offset or index:
        return f"page={page or '-'};offset={offset or '-'};chunk={index or '-'}"
    return f"es:{chunk_id}"


def fetch_docs(space_name: str, col_name: Optional[str] = None,
               col_values: Optional[List[str]] = None,
               post: Optional[Callable[[str, Dict[str, Any]], Any]] = None
               ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """返回 (docs, error)。error 是给调用方直接回给 Java 的原因，不抛异常。"""
    if not space_name:
        return [], "space_name 为空，无法定位 ES 索引"
    payload: Dict[str, Any] = {
        "index_name": [space_name, "table_chunks_" + space_name],
    }
    if col_name:
        payload["col_name"] = col_name
        payload["col_values"] = list(col_values or [])

    fn = post or _default_post
    try:
        response = fn(_proxy() + "/search_by_custom_param", payload)
    except Exception as exc:  # noqa: BLE001 - 连接失败要变成可读原因
        return [], f"ES 代理不可达 {type(exc).__name__}: {str(exc)[:160]}"

    status = getattr(response, "status_code", 200)
    try:
        body = response.json()
    except Exception:  # noqa: BLE001
        body = None
    if status != 200 or not isinstance(body, dict):
        return [], f"ES 代理返回 HTTP {status} 或非 JSON 响应"
    if body.get("code") != 200:
        return [], f"ES 查询失败 code={body.get('code')} msg={body.get('msg')}"

    rows = ((body.get("data") or {}).get("result_data") or [])
    docs: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for chunk_id, source in row.items():
            if not isinstance(source, dict):
                continue
            text = source.get("page_content")
            if not isinstance(text, str) or not text.strip():
                continue
            meta = source.get("metadata") or {}
            file_id = _field(meta, "file_id", "fileId", "document_id") or (
                col_values[0] if col_values else space_name)
            docs.append({"file_id": str(file_id), "text": text,
                         "locator": _locator(meta, str(chunk_id)),
                         "es_id": str(chunk_id)})
    if not docs:
        return [], f"知识库 {space_name} 未查询到可建图文本（ES total={((body.get('data') or {}).get('total_count'))}）"
    return docs, None
