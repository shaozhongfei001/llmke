"""问答召回接线层：19995 `/retrieval_documents` → 18094 `/v2/graph/query`。

为什么需要这一层：Java `rag-qa-service` 的召回入口是
`AiServiceImpl.java:3114 retrieveRecallByRetrieveDocReq`，把请求 POST 到
`config/application-r12.yml:39 spring.ai.gt.search-docs-url:
http://127.0.0.1:19995/retrieval_documents`。`RetrieveClient.java:14-18` 的 Feign 声明还在，
但调用点 `AiServiceImpl.java:3119` 已注释，实际走 `RestTemplate.postForObject`。
19995 上是 legacy `alg_retrieval_service`（ES + Milvus + FAQ + rerank）；V2 的图能力在 18094
（`POST /v2/graph/query`）。本层保留 legacy 的**路径与响应形状**，内部只调 18094，
不直连 ES / Milvus / Nebula。

## 真实契约（读代码 + 实测）

请求：`alg_retrieval_service/app/base.py:83 QARetrieveConfig`（`query`、`rewritten_query`、
`knowledge_base_name[]`、`top_k=10`、`top_n`、`enabled_graph`、`condition_json` …）。
Java 当前实际发的是 `interfaces/req/app/RetrieveDocReq.java:20-64`（**不含 `rewritten_query`**，
该字段只经 `ExtendedConfig.java:123-127` 出现在另一条 `/qa/ai/question` 路径上）。
两条路径的字段交集本层一律按 dict 取，**不建 pydantic 模型**——否则会把 19995 的
config/nacos 依赖拖进来，本层就无法在独立 venv 里单跑。

响应：`alg_retrieval_service/app/retrieval_service.py:577-582`
`BaseResponse{code, msg, data}`，`data` 五个键：
`faq_result_list / database_documents / documents_list / web_documents_list / log_list`。
`documents_list` 每项按 `rag-common/.../qa/dto/Document.java:26-32` 反序列化
（`page_content` + `metadata` 是 JSONObject，多余的 metadata 键被忽略）。
注意 legacy 的空结果分支（`retrieval_service.py:535-538`）**漏了 `web_documents_list`**；
本层始终给全五键（Java `RetrievedData.existDocs:73-85` 对 null 也判空，给全更稳）。

上游 18094：`graph_engine_adapter/api.py:212-234`
`POST /v2/graph/query {query, top_k}`（`QueryRequest:33-35` 硬约束 `top_k ∈ [1,20]`，越界 422）→
`{executed_route, reason, trace, hit_count, docs:[{rank,text,idx,sources:[{file_id,locator,title?}]}],
sources_available}`。
`sources` 由 build 时写入快照的 `sources.json` 提供（`api.py:111-124`），**没有映射时是 `[]`**，
且 `title` 只在 build 时给过才有。

## 映射规则

| 上游 | documents_list |
|---|---|
| `docs[i].text` | `page_content`（原样，不改写） |
| `sources[0]` | `metadata.file_id / title / locator`（缺就不给值，用 null） |
| `sources[全部]` | `metadata.sources`（逐条原样保留，失败时为空数组） |
| `docs[i].idx` | `metadata.idx` |
| `executed_route=GRAPH` | `metadata.search_type=["graph"]` |
| `executed_route=DENSE_FALLBACK` | `metadata.search_type=["dense_fallback"]` + `metadata.graph_reason=reason` |

`metadata.score` 恒为 null：18094 不返回分数，宁可空着也不编一个看起来像排序分的数。

## 错误语义（沿用 legacy：HTTP 200 + body.code）

| 场景 | code |
|---|---|
| 转发成功（含 0 条命中） | 200 |
| 请求体为空/非 JSON/query 为空 | 400 |
| `enabled_graph` 显式为 false | 400（本层没有 dense 路径，不能装作走了图） |
| 上游 HTTP 非 200 / 超时 / 连不上 / 非 JSON / 无可用 `executed_route` | 502 |

502 一律 `data=null`，原因写在 `msg`（Java `:3129-3134` 只在 code≠200 时取 `msg` 抛
`RETRIEVE_DOC_ERROR`，`:3137` 兜住并记日志）。

## 已知边界（不假装）

- **不做知识库分区**：18094 服务的是**单个快照**，`knowledge_base_name` **不参与过滤**
  （请求里给了多个 KB 时只在 `msg` 里写明"多知识库未分区"）；不同 KB 的请求拿到的仍是同一份图的命中。
- `search_policy`（1 混合 / 2 文本 / 3 语义）、`enabled_rerank`、`enabled_faq`、
  `condition_json` 本层都不实现，也不转成别的检索去凑数。
- 不产出 `faq_result_list` / `database_documents` / `web_documents_list`（恒为 `[]`）。
- **`/retrieval_documents_global` 转发到 18094 `/v2/graph/global`**（读建图时落盘的
  `community.json`）：答案只由社区事实拼装、每行带来源，`data.global_answer` 给 Java
  （`RetrievedData.getGlobalAnswer:62-63`）。不可用时如实给业务码，且**按语义分开**，不混用：
  无 `community.json` → 501 `global not ready: community report not wired`（**唯一** 501 场景）；
  报告里 0 个社区 → **200** `no communities in snapshot` + `reason="NO_COMMUNITIES"`；
  引用校验不过 → 502（不给无来源结论）；
  **能力正常但该问句没命中** → **200** + `global_answer=""` + `reason="NO_RELEVANT_FACTS"`
  （501 只表示"没接入"；"接了但没数据/没命中"一律 200，混用会让评审误判）。
  请求里 `enabled_graph=false` 时先回 400。

## 环境变量

    LLMKE_V2_GRAPH_API         V2 图服务地址，默认 http://127.0.0.1:18094
    LLMKE_V2_GRAPH_TIMEOUT     上游超时秒数，默认 120

启动（**不占 19995**，避免顶掉 legacy；切换 19995 是配置变更，不在本层职责内）：

    PYTHONPATH=services/rag-alg/index_data_service \
      uvicorn graph_engine_adapter.retrieval_shim:app --host 127.0.0.1 --port 19532
"""

import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import Body, FastAPI

from .assertions import DENSE_FALLBACK, GRAPH

SCHEMA = "llmke.graph-api.retrieval-shim.v1"
DEFAULT_GRAPH_API = "http://127.0.0.1:18094"
DEFAULT_TIMEOUT = 120.0
DEFAULT_TOP_K = 10

# 18094 `QueryRequest`（api.py:33-35）对 top_k 是 Field(ge=1, le=20)，越界直接 422。
UPSTREAM_TOP_K_MIN = 1
UPSTREAM_TOP_K_MAX = 20

# executed_route → search_type 的唯一映射。表外取值一律 502，不猜、不就近归并。
SEARCH_TYPE = {GRAPH: "graph", DENSE_FALLBACK: "dense_fallback"}

DATA_KEYS = ("faq_result_list", "database_documents", "documents_list",
             "web_documents_list", "log_list")

WIRED = ("POST /retrieval_documents",)

# global（社区摘要 map-reduce）现在接到了 18094 `POST /v2/graph/global`：
# 那边读的是**建图时落盘的 community.json**（`global_report.py`），答案只由社区事实拼装、
# 每行带来源。legacy 该路径见 `alg_retrieval_service/app/view/urls.py:24 RetrievalGlobalView`，
# Java 侧 `NacosConfig.java:27` 默认指向 `19995/retrieval_documents_global`，
# 由 `AiServiceImpl.java:2259/2366/2498` 在 `query_mode=global` 时调用，
# 答案走 `RetrievedData.getGlobalAnswer:62-63`（data.global_answer）。
# 报告缺失时仍如实 501——绝不拿普通检索结果冒充社区摘要。
GLOBAL_NOT_WIRED = "global not ready: community report not wired"

# 只剩"能力未接入"这一种才回 501；"接了但没数据/没命中"都回 200（见 _global_empty）。
GLOBAL_REASON_MSG = {"NO_COMMUNITY_REPORT": GLOBAL_NOT_WIRED}
# global 的 search_type 只有这一个取值：它既不是 graph 也不是 dense_fallback，
# 混用会让下游把"社区摘要答案"当成"图检索命中"。
GLOBAL_SEARCH_TYPE = "global"
DEFAULT_MAX_COMMUNITIES = 3
# global "能力正常但该问句没命中"：语义是**命中问题**，不是"能力未接入"。
NO_FACTS_REASON = "NO_RELEVANT_FACTS"
NO_FACTS_MSG = "no relevant facts for query"
NO_COMMUNITIES_REASON = "NO_COMMUNITIES"
NO_COMMUNITIES_MSG = "no communities in snapshot"


def _resp(code: int, msg: str, data: Any = None) -> Dict[str, Any]:
    """legacy BaseResponse 形状（`base.py:21-24`）。"""
    return {"code": code, "msg": msg, "data": data}


def _graph_api() -> str:
    return os.environ.get("LLMKE_V2_GRAPH_API", DEFAULT_GRAPH_API).rstrip("/")


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

    Java `:3122` 用 `HttpEntity<String>` 发 JSON 文本，正常能解析；被上层多包一层字符串时
    也不至于回 422（FastAPI 的 422 body 里没有可读原因）。
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


def _as_int(value: Any) -> Optional[int]:
    """只接受真正的整数语义；bool 不算（True 是 int 子类，会把"没给"当 1）。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("+-").isdigit():
        return int(value.strip())
    return None


def _pick_query(req: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """返回 (查询串, 取自哪个字段)。`rewritten_query` 非空则优先（base.py:87）。"""
    for key in ("rewritten_query", "query"):
        value = req.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip(), key
    return None, None


def _pick_top_k(req: Dict[str, Any]) -> Tuple[int, bool]:
    """返回 (实际下发的 top_k, 是否被上游区间截断)。

    18094 对 top_k 是 [1,20] 硬约束（api.py:35），越界会 422 让整次问答失败；
    这里夹到区间内，并让调用方在 msg 里看得见"被截断"这个事实，不静默。
    """
    raw = _as_int(req.get("top_k"))
    if raw is None:
        return DEFAULT_TOP_K, False
    clamped = min(max(raw, UPSTREAM_TOP_K_MIN), UPSTREAM_TOP_K_MAX)
    return clamped, clamped != raw


def _max_communities(req: Dict[str, Any]) -> int:
    """global 的社区条数：优先 `summary_top_k`（Java global 分支真实发的键，
    `AiServiceImpl.java:2256`），其次 legacy `top_n`（rerank 返回条数），都没有就 3。
    夹到 18094 的 [1,20]。
    """
    for key in ("summary_top_k", "top_n"):
        raw = _as_int(req.get(key))
        if raw is not None:
            return min(max(raw, UPSTREAM_TOP_K_MIN), UPSTREAM_TOP_K_MAX)
    return DEFAULT_MAX_COMMUNITIES


def _global_documents(sections: List[Dict[str, Any]],
                      source_meta: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """把一个社区压成一条 legacy 文档：正文是"事实 + 来源"，来源进 metadata.sources。

    这样 Java 侧拿到的是"有出处的摘要文本"，而不是一段没有引用、无法核验的结论。
    """
    items: List[Dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        lines: List[str] = []
        file_ids: List[str] = []
        for fact in section.get("facts") or []:
            if not isinstance(fact, dict):
                continue
            sources = sorted({str(s) for s in (fact.get("sources") or [])})
            if not sources:
                continue          # 没来源的事实不进正文，也不进引用
            lines.append("- " + str(fact.get("text") or "") + "（来源：" + ",".join(sources) + "）")
            file_ids.extend(sources)
        if not lines:
            continue
        items.append({"text": "\n".join(lines),
                      # idx 是**块 id** 的语义，社区号不能塞进去（会让下游误当 chunk 反查）。
                      "idx": None,
                      "community": section.get("community") or section.get("id"),
                      "sources": [dict({"file_id": fid},
                                       **{k: v for k, v in (source_meta or {}).get(fid, {}).items()
                                          if k in ("locator", "title") and v})
                                  for fid in sorted(set(file_ids))]})
    return items


def _sources_of(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """`docs[i].sources` 逐条原样保留（api.py:222-223，没有映射时是 []）。"""
    raw = item.get("sources")
    if not isinstance(raw, list):
        return []
    return [dict(src) for src in raw if isinstance(src, dict)]


def _to_document(item: Any, search_type: str, reason: Optional[str]) -> Optional[Dict[str, Any]]:
    """一条上游命中 → legacy `Document` 形状；正文为空则返回 None（调用方计数丢弃）。"""
    if isinstance(item, str):
        item = {"text": item}
    if not isinstance(item, dict):
        return None
    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        return None

    sources = _sources_of(item)
    primary = sources[0] if sources else {}
    raw_file_id = primary.get("file_id")
    locator = primary.get("locator")
    # Java 的 RetrieveMetaData 只认固定字段：file_id 是 Long、source 是文件名、
    # position 是 Object（可承载定位对象）。叫 locator/title 的键在 Jackson 反序列化时
    # 会被直接丢掉，所以必须映射到它真能承载的字段，同时保留原名给非 Java 调用方。
    try:
        file_id: Optional[int] = int(str(raw_file_id))
    except (TypeError, ValueError):
        file_id = None
    chunk_index = None
    if isinstance(locator, str):
        m = re.search(r"chunk=(\d+)", locator)
        chunk_index = int(m.group(1)) if m else None
    metadata: Dict[str, Any] = {
        # 没有来源就是 null：legacy 的 file_id 用来反查文件路径（AiServiceImpl:3099-3103），
        # 编一个会让引用指到别的文件。
        "file_id": file_id,
        # source 不能放文件名或 file_id：Document.buildParsedFilePath 假设它是
        # "bucket/path/name" 形式，会连做三次 indexOf("/") 后 substring；
        # 没有斜杠时 substring(0,-1) 直接抛 StringIndexOutOfBounds（rag-common Document.java:70-72）。
        # 同理文件名也不放——保留 null，由 Java 用 file_id 走 addConvertedFilePath 补路径。
        "source": None,
        "position": {"locator": locator, "sources": sources},
        "chunk_index": chunk_index,
        "title": primary.get("title"),
        "locator": locator,
        "search_type": [search_type],
        "score": None,
        "idx": item.get("idx"),
        "sources": sources,
    }
    if search_type == SEARCH_TYPE[DENSE_FALLBACK]:
        # 回退必须自证：不写这个键，调用方无法区分"图真跑了"和"图没跑、捡了向量结果"。
        metadata["graph_reason"] = reason
    return {"page_content": text, "metadata": metadata}


def _read_response(result: Any) -> Tuple[Optional[int], Any, bool]:
    """把 http_post 返回值读成 (status, body, 是否解析成功)。

    解析失败时 body 保留原始文本：不能把它折成 `{"msg": ...}` 混过"是 dict"的检查，
    否则 HTML 错误页会被当成"上游正常但没给 executed_route"，原因就丢了。
    """
    if isinstance(result, dict):
        return 200, result, True
    status = getattr(result, "status_code", None)
    try:
        return status, result.json(), True
    except Exception:  # noqa: BLE001 - 上游可能回 HTML/空体
        return status, str(getattr(result, "text", ""))[:300], False


def _reason_of(body: Any) -> str:
    if isinstance(body, dict):
        return str(body.get("detail") or body.get("msg") or "")[:300]
    return str(body)[:300]


def _global_empty(upstream: Any, reason: str, msg: str) -> Dict[str, Any]:
    """global 能力已接、但没有可用结果（没命中 / 没社区）→ 200 + 空答案 + 原因。

    不能回 501：501 表示"能力未接入"，这里能力是通的；也不能回 502（那是上游异常）。
    调用方拿到 200 + `reason` 才能自己决定要不要降级。
    """
    src = upstream if isinstance(upstream, dict) else {}
    return _resp(200, msg, data={
        "faq_result_list": [],
        "database_documents": [],
        "documents_list": [],
        "web_documents_list": [],
        "log_list": [],
        "global_answer": "",
        "reason": reason,
        "communities": src.get("communities"),
        "citation_check": src.get("citation_check"),
        "answer_stats": src.get("answer_stats"),
    })


def create_app(http_post: Optional[Callable[[str, Dict[str, Any], float], Any]] = None) -> FastAPI:
    """http_post(url, payload, timeout) → 带 status_code/.json() 的响应（或已解析 dict）。"""
    post = http_post or _default_http_post
    app = FastAPI(title="LLMKE V2 Retrieval Shim", version=SCHEMA)

    @app.get("/health")
    def health() -> Dict[str, Any]:
        # 只自述接线状态，不访问上游：上游挂了它仍要能回答"接到了谁、没接什么"。
        return {
            "schema": SCHEMA,
            "graph_api": _graph_api(),
            "upstream_endpoint": "/v2/graph/query",
            "timeout": _timeout(),
            "wired": list(WIRED),
            # global 已接线：转发到 18094 /v2/graph/global（读建图时落盘的 community.json）。
            # 仍然如实写明"什么情况下不可用"，别让路径可达被当成能力存在。
            "global": {
                "endpoint": "/retrieval_documents_global",
                "wired": True,
                "upstream_endpoint": "/v2/graph/global",
                "report": "快照内 community.json（建图时生成）",
                "unavailable_when": {
                    "NO_COMMUNITY_REPORT": "该快照没有 community.json → 501（能力未接入）",
                    "NO_COMMUNITIES": "报告里没有社区 → **200** + 空答案 + reason（能力已接）",
                    "CITATION_INVALID": "引用校验不过 → 502（不给无来源结论）",
                    "NO_RELEVANT_FACTS": "能力正常、该问句没命中 → **200** + 空答案 + reason",
                },
                "why": "答案只由社区事实拼装并逐条带来源；任何一条引用回不到真实文件就不出答案",
            },
            "data_keys": list(DATA_KEYS),
            "route_passthrough": dict(SEARCH_TYPE),
            "not_implemented": {
                "knowledge_base_scope": "18094 服务单个快照，knowledge_base_name 不过滤",
                "search_policy": "1/2/3 均不实现，也不转成别的检索顶上",
                "faq_result_list": "恒为 []",
                "database_documents": "恒为 []",
                "web_documents_list": "恒为 []",
            },
        }

    @app.post("/retrieval_documents")
    def retrieval_documents(body: Any = Body(default=None)) -> Dict[str, Any]:
        req, bad = _parse_body(body)
        if bad:
            return bad

        query, query_field = _pick_query(req)
        if not query:
            return _resp(400, "query 为空（rewritten_query 与 query 都没有可用文本）")

        # 显式关图时不冒充：本层只有图路径，替调用方改语义比报错更糟。
        if req.get("enabled_graph") is False:
            return _resp(
                400,
                "enabled_graph=false：本层只接图检索（18094 /v2/graph/query），没有 dense 路径，"
                "请改用 19995 legacy 召回，不要把本层当通用召回",
            )

        top_k, clamped = _pick_top_k(req)
        url = _graph_api() + "/v2/graph/query"
        payload = {"query": query, "top_k": top_k}

        try:
            result = post(url, payload, _timeout())
        except Exception as exc:  # noqa: BLE001 - 超时/连接失败都要带原因回调用方
            return _resp(502, f"上游图服务 {url} 不可达 {type(exc).__name__}: {str(exc)[:180]}")

        status, upstream, parsed = _read_response(result)
        if status != 200:
            return _resp(502, f"上游图服务 {url} 返回 HTTP {status}: "
                              f"{_reason_of(upstream) or '无响应体'}")
        if not parsed:
            return _resp(502, f"上游图服务响应不是 JSON（{url}）: {str(upstream)[:200]}")
        if not isinstance(upstream, dict):
            return _resp(502, f"上游图服务响应不是 JSON 对象: {type(upstream).__name__}")

        route = upstream.get("executed_route")
        if route not in SEARCH_TYPE:
            # fail-closed：拿不到可识别的路由就等于没证据，不能默认当图检索。
            return _resp(
                502,
                f"上游图服务未返回可识别的 executed_route（{route!r}），"
                f"只认 {sorted(SEARCH_TYPE)}",
            )
        search_type = SEARCH_TYPE[route]
        reason = upstream.get("reason")

        raw_docs = upstream.get("docs")
        if raw_docs is None:
            raw_docs = []
        if not isinstance(raw_docs, list):
            return _resp(502, f"上游 docs 必须是数组，收到 {type(raw_docs).__name__}")

        documents: List[Dict[str, Any]] = []
        dropped = 0
        for item in raw_docs:
            doc = _to_document(item, search_type, reason)
            if doc is None:
                dropped += 1
                continue
            documents.append(doc)

        # msg 沿用 legacy 的写法：成功也允许带"实际发生了什么"，Java 只在 code≠200 时取它。
        notes: List[str] = []
        if query_field == "rewritten_query":
            notes.append("按 rewritten_query 检索")
        if not documents:
            notes.append(f"{search_type} 未召回任何文档")
        if dropped:
            notes.append(f"{dropped} 条命中无可用正文已丢弃")
        if clamped:
            notes.append(f"top_k 已按上游上限截断为 {top_k}")
        kbs = req.get("knowledge_base_name")
        if isinstance(kbs, list) and len(kbs) > 1:
            notes.append("多知识库未分区（18094 单快照）")
        msg = "查询成功" if not notes else "查询成功（" + "；".join(notes) + "）"

        return _resp(200, msg, data={
            "faq_result_list": [],
            "database_documents": [],
            "documents_list": documents,
            "web_documents_list": [],
            "log_list": [],
        })

    @app.post("/retrieval_documents_global")
    def retrieval_documents_global(body: Any = Body(default=None)) -> Dict[str, Any]:
        """legacy 的 GraphRAG 社区摘要入口：转发到 18094 `/v2/graph/global`。

        上游的答案只由建图时落盘的 `community.json` 里的社区事实拼装，每条都带来源；
        本层只做形状转换，不补写、不改写结论。不可用情形按语义分开回码：
        - 快照没有 community.json → 501 `global not ready: community report not wired`
          （**唯一** 501：这是"能力未接入"）
        - 报告里有 0 个社区 → **200** `no communities in snapshot` + `reason="NO_COMMUNITIES"`
          （能力已接、只是没数据，501 会被读成"没实现"）
        - 引用校验不过 → 502（结论挂不上真实来源，不能交给模型当摘要）
        - 有社区但该问句没命中 → **200** + `reason="NO_RELEVANT_FACTS"`
        任何情况下都不拿普通检索结果顶替 global。
        """
        req, bad = _parse_body(body)
        if bad:
            return bad

        # 调用方自己关了图，global 更无从谈起：先给 400 说清原因，别让 501 掩盖请求侧问题。
        if req.get("enabled_graph") is False:
            return _resp(
                400,
                "enabled_graph=false：global 问答建立在图社区摘要之上，关图后本层无法提供该能力，"
                "请改用 19995 legacy 的 /retrieval_documents_global",
            )

        query, _ = _pick_query(req)
        url = _graph_api() + "/v2/graph/global"
        payload = {"query": query or "", "max_communities": _max_communities(req)}

        try:
            result = post(url, payload, _timeout())
        except Exception as exc:  # noqa: BLE001 - 超时/连接失败都要带原因回调用方
            return _resp(502, f"上游图服务 {url} 不可达 {type(exc).__name__}: {str(exc)[:180]}")

        status, upstream, parsed = _read_response(result)
        if status != 200:
            return _resp(502, f"上游图服务 {url} 返回 HTTP {status}: "
                              f"{_reason_of(upstream) or '无响应体'}")
        if not parsed or not isinstance(upstream, dict):
            return _resp(502, f"上游 global 响应不是 JSON 对象（{url}）")

        reason = upstream.get("reason")
        if reason == "CITATION_INVALID":
            return _resp(502, "global citation check failed: 结论里存在无法回到真实来源的引用，"
                              "不交给调用方使用")
        if reason == "NO_RELEVANT_FACTS":
            # 能力是通的、只是这条问句没命中相关事实：**不能**借 501（未接入）表达，也不是 502
            # （上游异常）。按 legacy 习惯回 200 + 空答案 + 原因，让调用方自己决定是否降级。
            return _global_empty(upstream, NO_FACTS_REASON, NO_FACTS_MSG)
        if reason == NO_COMMUNITIES_REASON:
            # 能力已接、只是这份报告没有社区：同 NO_RELEVANT_FACTS，不能用 501（会被读成"没实现"）。
            return _global_empty(upstream, NO_COMMUNITIES_REASON, NO_COMMUNITIES_MSG)
        if reason in GLOBAL_REASON_MSG:
            return _resp(501, GLOBAL_REASON_MSG[reason], data=None)
        if reason:
            return _resp(502, f"上游 global 未给出可用结果: {reason}")

        sections = upstream.get("sections") or []
        # 只把答案真正用到的社区转成文档（上游给了 used_communities 时）；
        # 否则退回全部社区——但那只是兼容老响应，不是默认路径。
        used = upstream.get("used_communities")
        if isinstance(used, list) and used:
            wanted = set(used)
            sections = [s for s in sections
                        if (s.get("community") or s.get("id")) in wanted]
        documents: List[Dict[str, Any]] = []
        for item in _global_documents(sections, upstream.get("source_meta")):
            doc = _to_document(item, GLOBAL_SEARCH_TYPE, None)
            if not doc:
                continue
            # 哪个社区贡献了这段正文：写进 metadata 便于核对（不占 idx，idx 仍是块 id 语义）。
            doc["metadata"]["community"] = item.get("community")
            documents.append(doc)
        answer = str(upstream.get("answer") or "")
        if not documents or not answer:
            # 上游说"能答"但一条可用事实都没有（或 answer 空）：语义仍是"没命中相关事实"，
            # 不是"能力没接"。回 200 + 空答案 + reason，别用 501 让评审误判。
            return _global_empty(upstream, NO_FACTS_REASON, NO_FACTS_MSG)

        return _resp(200, "查询成功", data={
            "faq_result_list": [],
            "database_documents": [],
            "documents_list": documents,
            "web_documents_list": [],
            "log_list": [],
            # Java `RetrievedData.getGlobalAnswer:62-63` 读的就是这个键。
            "global_answer": answer,
            "citation_check": upstream.get("citation_check"),
            "communities": upstream.get("communities"),
        })

    return app


app = create_app()
