"""19529 legacy 图接口 → 18094 V2 图服务的兼容层。

为什么需要这一层：`rag-index-service/application-r12.yml:89-97` 把建图请求固定发到
`127.0.0.1:19529`（`/generate_triple_data`、`/generate_community`、`/del_space`、
`/del_doc_entity`）。19529 上是 legacy `index_graph_service`（Nebula + ES + Milvus）；
V2 图服务在 18094（`POST /v2/graph/build`）。本模块保留 legacy 的**路径与响应形状**，
内部按 legacy 的**同一读法**取正文（复用 `legacy_es.fetch_docs`，本文件不再自己写 ES 查询），
再转发到 18094。

## 真实契约（读代码 + 实测）

legacy 路由：`index_graph_service/graph_api_start.py:97`（del_space）、`:103`
（generate_triple_data）、`:130`（generate_community）。
请求模型：`index_graph_service/base.py:64 QueryDocChunk`（**请求里没有正文**）。
响应模型：`base.py:16 BaseResponse{code:int=200, msg:str, data:Any}`。

Java 发送方：`rag-index-service/.../impl/FileAppServiceImpl.java:634-657` 构造
`{space_name(kb.getPrimitiveName()), embedding_model_name, model_info, col_name:"title",
col_values:[原始文件名], generation, entity_types?}`；删除请求见
`GraphDomainServiceImpl.java:29-70`。

Java 侧判定（`FileAppServiceImpl.java:659-673`，**必须满足**）：`code==200` 且
`data.edges_total>0` 且 `data.edges_written>0`，否则抛 `GRAPH_PARSE_ERROR`。
所以本层回填的计数必须来自上游真实统计，不能填固定值。

## 正文从哪来

`legacy_es.fetch_docs(space_name, col_name, col_values, post=...)` —— 与 legacy
`graph_fun_tool.py:908-957 get_document_chunk` 同一读法（`/search_by_custom_param`，
`index_name=["{space_name}", "table_chunks_{space_name}"]`，用 `col_name`/`col_values`
过滤），返回 `{file_id, text, locator, es_id}` 与可读 error。

本层只做两件事：转成 18094 的 `BuildDoc{file_id,text,locator}`（去掉 `es_id`），
以及 **locator 的降级修正**（见 `_to_build_docs` 注释：`es:_source` 是取不到真实 chunk id
的哨兵值，不能当定位串写进产物）。

## 错误语义

legacy 约定是 **HTTP 200 + body.code 表达成败**（`graph_api_start.py:25 _safe_entry`
把异常折成 `code=500`）。本层沿用：这样 Java `RemoteGraphUtils.doExchange:65-77`
（HTTP≠200 直接抛错、丢掉 body 里的原因）仍能读到 `msg` 并记进日志。

| 场景 | code |
|---|---|
| 转发成功且 facts>0、edges>0 | 200 |
| ES 取不到正文 / ES 不可用 / 缺 space_name | 500（带可读原因，不返回 400） |
| 上游 18094 HTTP 非 200 / 超时 / 未 BUILT / 非 JSON | 502 |
| facts 或 edges 为 0 或缺失 | 500 |
| `/generate_community`、`/del_space`、`/del_doc_entity` | 501 + 原因，不调上游 |
| 请求自带 docs 但结构非法（text 为空等） | 400 |

## 环境变量

    LLMKE_V2_GRAPH_API        V2 图服务地址，默认 http://127.0.0.1:18094
    LLMKE_V2_ES_PROXY         ES 代理地址（由 legacy_es 读取），默认 http://127.0.0.1:19527
    LLMKE_V2_ROOT             build 根目录，默认 .artifacts/api-root（请求里的 root 优先）
    LLMKE_V2_GRAPH_TIMEOUT    上游超时秒数，默认 600（LLM 抽取是慢操作）

启动（不占 19529，避免顶掉 legacy）：

    PYTHONPATH=services/rag-alg/index_data_service \
      uvicorn graph_engine_adapter.legacy_shim:app --host 127.0.0.1 --port 19531

边界：只读 ES（取正文，输入侧）与 18094（图引擎），不直连 Nebula/Milvus，不启停服务。
"""

import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import Body, FastAPI

from .legacy_es import fetch_docs

SCHEMA = "llmke.graph-api.legacy-shim.v1"
DEFAULT_GRAPH_API = "http://127.0.0.1:18094"
DEFAULT_ES_PROXY = "http://127.0.0.1:19527"
DEFAULT_ROOT = ".artifacts/api-root"
DEFAULT_TIMEOUT = 600.0

# legacy_es 在拿不到真实 chunk id 时用 `_source` 当 id（扁平 ES hit 的键名），
# 产出的 locator 会变成 "es:_source"。这不是定位串，是缺陷的痕迹，见 _to_build_docs。
_FAKE_CHUNK_ID = "_source"

WIRED = ("POST /generate_triple_data",)
NOT_WIRED = {
    "/generate_community": ("community not wired yet",
                            "HippoRAG 侧社区检测/摘要未接入 18094（graph_engine_adapter.community 未暴露 HTTP）"),
    "/del_space": ("delete not wired yet",
                   "legacy 走 Nebula DROP SPACE；V2 图服务无删除端点，快照按代次重建，不能假装删成功"),
    "/del_doc_entity": ("delete not wired yet",
                        "legacy 删的是 Milvus 实体表 graph_entity_<space>；V2 无对应端点"),
}


def _resp(code: int, msg: str, data: Any = None) -> Dict[str, Any]:
    """legacy BaseResponse 形状（base.py:16）。"""
    return {"code": code, "msg": msg, "data": data}


def _graph_api() -> str:
    return os.environ.get("LLMKE_V2_GRAPH_API", DEFAULT_GRAPH_API).rstrip("/")


def _es_proxy() -> str:
    return os.environ.get("LLMKE_V2_ES_PROXY", DEFAULT_ES_PROXY).rstrip("/")


def _timeout() -> float:
    raw = os.environ.get("LLMKE_V2_GRAPH_TIMEOUT")
    try:
        return float(raw) if raw else DEFAULT_TIMEOUT
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def _default_http_post(url: str, payload: Dict[str, Any], timeout: float) -> Any:
    import requests

    return requests.post(url, json=payload, timeout=timeout)


def _parse_body(body: Any) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """把请求体解析成 dict；失败返回 (None, 400 响应)。

    容忍 JSON 字符串：Java 用 `HttpEntity<String>` 发 body（RemoteGraphUtils:68），
    正常是 JSON 文本；被上层多包一层字符串时也不至于 422 无原因。
    """
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except ValueError as exc:
            return None, _resp(400, f"请求体不是合法 JSON: {exc}")
    if body is None:
        return None, _resp(400, "请求体为空")
    if not isinstance(body, dict):
        return None, _resp(400, f"请求体必须是 JSON 对象，收到 {type(body).__name__}")
    return body, None


def _first_col_value(body: Dict[str, Any]) -> Optional[str]:
    values = body.get("col_values")
    if isinstance(values, list) and values:
        return str(values[0])
    return None


def _locator_of(item: Dict[str, Any], fallback_file_id: Optional[str]) -> Optional[str]:
    for key in ("locator", "page_num"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    if fallback_file_id not in (None, ""):
        return f"file:{fallback_file_id}"
    return None


def _coerce_request_docs(body: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int, Optional[Dict[str, Any]]]:
    """请求自带 docs 时归一成 BuildDoc；缺 docs 返回空列表交给 ES 路径。"""
    raw = body.get("docs")
    if raw in (None, []):
        return [], 0, None
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return [], 0, _resp(400, f"docs 必须是数组，收到 {type(raw).__name__}")

    first_value = _first_col_value(body)
    docs: List[Dict[str, Any]] = []
    fallbacks = 0
    for i, item in enumerate(raw):
        if isinstance(item, str):
            item = {"text": item}
        if not isinstance(item, dict):
            return [], 0, _resp(400, f"docs[{i}] 必须是对象或字符串，收到 {type(item).__name__}")
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            return [], 0, _resp(400, f"docs[{i}].text 缺失或为空")
        file_id = item.get("file_id") or item.get("fileId")
        if file_id in (None, ""):
            file_id = first_value or body.get("space_name")
            fallbacks += 1
        if file_id in (None, ""):
            return [], 0, _resp(
                400, f"docs[{i}].file_id 缺失，且 legacy 字段 col_values/space_name 都没有可用值")
        docs.append({"file_id": str(file_id), "text": text,
                     "locator": _locator_of(item, str(file_id))})
    return docs, fallbacks, None


def _to_build_docs(es_docs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """`legacy_es.fetch_docs` 的产出 → 18094 BuildDoc{file_id,text,locator}。

    唯一一处改写：locator 若退化成 `es:_source`（或只差这个 id 的空定位），说明上游
    ES 返回的是扁平 hit 而 legacy_es 按 `{id: source}` 折形解析，拿不到真实 chunk id。
    这种串写进快照的 sources.json 会让检索引用指向不存在的块，所以降级为
    `file:<file_id>`（文件级可回溯），并计数 `locator_degraded`。其余 locator 原样透传
    （含 `page=[0, 0, 0, 0];offset=…;chunk=…` —— page 是 ES 元数据里的真实值，本层不改写）。
    """
    docs: List[Dict[str, Any]] = []
    degraded = 0
    for item in es_docs or []:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        file_id = item.get("file_id")
        file_id = "" if file_id in (None, "") else str(file_id)
        locator = item.get("locator")
        es_id = str(item.get("es_id") or "")
        if locator in (None, "") or locator == f"es:{_FAKE_CHUNK_ID}" or es_id == _FAKE_CHUNK_ID:
            degraded += 1
            locator = f"file:{file_id}" if file_id else None
        else:
            locator = str(locator)
        docs.append({"file_id": file_id, "text": text, "locator": locator})
    return docs, {"locator_degraded": degraded}


def _read_response(result: Any) -> Tuple[Optional[int], Any]:
    """把 http_post 返回值读成 (status, body)。dict 视为已解析的 200 响应。"""
    if isinstance(result, dict):
        return 200, result
    status = getattr(result, "status_code", None)
    try:
        body = result.json()
    except Exception:  # noqa: BLE001 - 上游可能回 HTML/空体
        body = {"msg": str(getattr(result, "text", ""))[:300]}
    return status, body


def _reason_of(body: Any) -> str:
    if isinstance(body, dict):
        return str(body.get("detail") or body.get("msg") or "")[:300]
    return str(body)[:300]


def _count(value: Any) -> Optional[float]:
    """只接受真正的数值；bool 不算（True 是 int 子类，会把"没给"当 1）。"""
    if isinstance(value, bool):
        return None
    return value if isinstance(value, (int, float)) else None


def create_app(http_post: Optional[Callable[[str, Dict[str, Any], float], Any]] = None) -> FastAPI:
    """http_post(url, payload, timeout) → 带 status_code/.json() 的响应（或已解析 dict）。

    `legacy_es.fetch_docs` 的 post 是两参 `(url, payload)`，这里适配成同一个注入口，
    便于测试用一个假客户端覆盖"ES + 建图"两条出站链路。
    """
    post = http_post or _default_http_post
    app = FastAPI(title="LLMKE V2 Legacy Graph Shim", version=SCHEMA)

    def _es_post(url: str, payload: Dict[str, Any]) -> Any:
        return post(url, payload, _timeout())

    @app.get("/health")
    def health() -> Dict[str, Any]:
        # 只是自述接线状态，不访问上游：上游挂掉时它仍要能回答"谁没接"。
        return {
            "schema": SCHEMA,
            "graph_api": _graph_api(),
            "es_proxy": _es_proxy(),
            "root": os.environ.get("LLMKE_V2_ROOT", DEFAULT_ROOT),
            "wired": list(WIRED),
            "not_wired": {path: reason for path, (reason, _) in NOT_WIRED.items()},
        }

    @app.post("/generate_triple_data")
    def generate_triple_data(body: Any = Body(default=None)) -> Dict[str, Any]:
        req, bad = _parse_body(body)
        if bad:
            return bad

        docs, fallbacks, bad = _coerce_request_docs(req)
        if bad:
            return bad

        es_meta: Optional[Dict[str, Any]] = None
        if not docs:
            # legacy 请求里没有正文 → 按 legacy 读法从 ES 取（输入侧，不是图引擎）。
            space_name = req.get("space_name")
            try:
                es_docs, err = fetch_docs(space_name, req.get("col_name"),
                                          req.get("col_values"), post=_es_post)
            except Exception as exc:  # noqa: BLE001 - 适配模块本不抛，兜住也不能 500 HTML
                return _resp(500, f"ES 取块异常 {type(exc).__name__}: {str(exc)[:180]}",
                             data={"es_proxy": _es_proxy(), "space_name": space_name})
            if err:
                return _resp(500, err, data={
                    "es_proxy": _es_proxy(),
                    "es_query": {"space_name": space_name, "col_name": req.get("col_name"),
                                 "col_values": req.get("col_values")},
                })
            docs, degraded = _to_build_docs(es_docs)
            fallbacks = None
            es_meta = {
                "es_proxy": _es_proxy(),
                "es_query": {"space_name": space_name, "col_name": req.get("col_name"),
                             "col_values": req.get("col_values")},
                "es_docs_used": len(docs),
                "locator_degraded": degraded.get("locator_degraded", 0),
            }
            if not docs:
                return _resp(500, f"ES 返回 {len(es_docs or [])} 条但没有可用正文（page_content 为空）",
                             data=es_meta)

        root = req.get("root") or os.environ.get("LLMKE_V2_ROOT") or DEFAULT_ROOT
        url = _graph_api() + "/v2/graph/build"
        payload: Dict[str, Any] = {"docs": docs}
        if root:
            payload["root"] = str(root)

        try:
            result = post(url, payload, _timeout())
        except Exception as exc:  # noqa: BLE001 - 超时/连接失败都要带原因回调用方
            return _resp(
                502, f"上游图服务不可达 {type(exc).__name__}: {str(exc)[:180]}",
                data={"graph_api": url, "forwarded_docs": len(docs), "es": es_meta})

        status, upstream = _read_response(result)
        if status != 200:
            return _resp(
                502, f"上游图服务返回 HTTP {status}: {_reason_of(upstream) or '无响应体'}",
                data={"graph_api": url, "upstream_status": status, "upstream": upstream,
                      "forwarded_docs": len(docs), "es": es_meta})
        if not isinstance(upstream, dict):
            return _resp(502, f"上游图服务响应不是 JSON 对象: {type(upstream).__name__}",
                         data={"graph_api": url, "es": es_meta})
        if upstream.get("status") != "BUILT" or not upstream.get("snapshot"):
            # fail-closed：没有 BUILT/快照就等于没建成，不能回 code=200。
            return _resp(
                502,
                f"上游图服务未返回 BUILT 快照（status={upstream.get('status')!r}, "
                f"snapshot={upstream.get('snapshot')!r}）",
                data={"graph_api": url, "upstream": upstream, "forwarded_docs": len(docs),
                      "es": es_meta})

        # 真实计数：Java FileAppServiceImpl.java:661-673 要求 edges_total>0 且 edges_written>0。
        # edges_total 语义 = 抽取出的三元组总数（上游 facts）；
        # edges_written 语义 = 真正进图的边数（上游 edges）。零产出必须判失败。
        facts = _count(upstream.get("facts"))
        edges = _count(upstream.get("edges"))
        if facts is None or edges is None or facts <= 0 or edges <= 0:
            return _resp(
                500,
                f"上游建图未返回有效计数 facts={upstream.get('facts')!r} "
                f"edges={upstream.get('edges')!r}：Java 侧 edges_total/edges_written 必须均 >0，"
                f"零产出不得记成功",
                data={"graph_api": url, "forwarded_docs": len(docs), "triples_total": facts,
                      "edges_total": facts, "edges_written": edges,
                      "upstream": upstream, "es": es_meta})

        return _resp(
            200,
            f"V2 建图完成 docs={len(docs)} chunks={upstream.get('chunks')} "
            f"facts={int(facts)} edges={int(edges)}",
            data={
                "docs": len(docs),
                "documents": upstream.get("documents"),
                "chunks": upstream.get("chunks"),
                "sources": upstream.get("sources"),
                "snapshot": upstream.get("snapshot"),
                "generation": upstream.get("generation"),
                # legacy 字段：Java 只读 edges_total / edges_written，其余保持 legacy 键名。
                "triples_total": int(facts),
                "edges_total": int(facts),
                "edges_written": int(edges),
                "edges_failed": None,
                "edges_semantics": "edges_total=上游 facts(抽取三元组总数)；"
                                   "edges_written=上游 edges(图中真实边数)",
                # V2 build 是 all-or-nothing（失败抛错→HTTP 500→本层 502），
                # 成功路径不存在"部分失败"清单，故这两个 legacy 字段确为 []。
                "error_edge_data_list": [],
                "error_tag_data_list": [],
                "file_id_fallbacks": fallbacks,
                "legacy_fields_seen": sorted(k for k in req if k not in ("docs", "root")),
                "es": es_meta,          # 走 ES 时给出真实取块情况；带 docs 时为 null
                "graph_api": url,
                "upstream_schema": upstream.get("schema"),
                "upstream": upstream,
            },
        )

    def _not_wired(path: str):
        reason, why = NOT_WIRED[path]

        def handler(body: Any = Body(default=None)) -> Dict[str, Any]:
            return _resp(
                501, reason,
                data={"endpoint": path, "wired": False, "why": why, "upstream_called": False})

        handler.__name__ = f"not_wired_{path.strip('/')}"
        return handler

    for path in ("/generate_community", "/del_space", "/del_doc_entity"):
        app.post(path)(_not_wired(path))

    return app


app = create_app()
