"""召回接线层：19995 `/retrieval_documents` → 18094 `/v2/graph/query` 的形状与语义。

依赖 fastapi/httpx，在工具 venv 里没有时用 importorskip；
真实运行环境是 hipporag venv（见 docs/v2-tasks/ENV.md）。
"""

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from graph_engine_adapter.retrieval_shim import SCHEMA, create_app  # noqa: E402

# 上游 18094 的真实响应（实测 2026-11-02，kb_9 快照）：docs[i].sources 里只有
# file_id + locator，没有 title —— 本层不得据此编 title。
GRAPH_BODY = {
    "schema": "llmke.graph-api.v1",
    "query": "单笔授信超过五亿元由谁审议通过",
    "executed_route": "GRAPH",
    "reason": "GRAPH_CALLED",
    "trace": {"graph_calls": 1, "seed_hits": [], "fact_candidates": 5, "rerank_fallback": True},
    "hit_count": 2,
    "docs": [
        {"rank": 1, "text": "单笔授信金额超过五亿元须提交总行授信审查委员会审议。",
         "idx": "chunk-ca1d8268933dd200d88189cca497d46c",
         "sources": [{"file_id": "999016",
                      "locator": "page=-;offset=[[0, 459]];chunk=0"}]},
        {"rank": 2, "text": "贷后检查每季度开展一次。",
         "idx": "chunk-2b1a",
         "sources": [{"file_id": "999010", "title": "丙-额度分项.docx",
                      "locator": "page=[0, 0];offset=[[0, 66]];chunk=0"}]},
    ],
    "sources_available": True,
}

FALLBACK_BODY = {
    "schema": "llmke.graph-api.v1",
    "query": "单笔授信超过五亿元由谁审议通过",
    "executed_route": "DENSE_FALLBACK",
    "reason": "GRAPH_NOT_CALLED",
    "trace": {"graph_calls": 0, "seed_hits": [], "fact_candidates": None,
              "rerank_fallback": False},
    "hit_count": 1,
    "docs": [{"rank": 1, "text": "向量召回的段落。", "idx": "chunk-9c",
              "sources": [{"file_id": "999016",
                           "locator": "page=-;offset=[[0, 459]];chunk=0"}]}],
    "sources_available": True,
}

QA_REQUEST = {"query": "单笔授信超过五亿元由谁审议通过",
              "knowledge_base_name": ["kb_9"], "top_k": 3}


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else str(body)

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("not json")
        return self._body


class FakePost:
    """记录出站调用；单条结果可重复使用，多条按序消费。"""

    def __init__(self, *results):
        self.results = list(results) or [FakeResponse(200, GRAPH_BODY)]
        self.calls = []

    def __call__(self, url, payload, timeout):
        self.calls.append({"url": url, "payload": payload, "timeout": timeout})
        item = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(item, Exception):
            raise item
        return item


def client(*results):
    fake = FakePost(*results)
    return TestClient(create_app(http_post=fake)), fake


def call(body=QA_REQUEST, *results):
    c, fake = client(*results)
    return c.post("/retrieval_documents", json=body), fake


# ---------- 正常图检索 ----------

def test_graph_route_maps_documents_and_metadata():
    r, fake = call()
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200 and body["msg"] == "查询成功"

    data = body["data"]
    # legacy 五键齐全（retrieval_service.py:577-582）
    assert sorted(data) == sorted(["faq_result_list", "database_documents", "documents_list",
                                  "web_documents_list", "log_list"])
    assert data["faq_result_list"] == [] and data["database_documents"] == []
    assert data["web_documents_list"] == [] and data["log_list"] == []

    docs = data["documents_list"]
    assert len(docs) == 2
    first = docs[0]
    assert first["page_content"] == "单笔授信金额超过五亿元须提交总行授信审查委员会审议。"
    assert first["metadata"]["file_id"] == 999016          # Java Long
    assert first["metadata"]["source"] is None           # 不把 id/文件名塞进路径字段
    assert "offset=[[0, 459]]" in first["metadata"]["position"]["locator"]
    assert first["metadata"]["chunk_index"] == 0
    assert first["metadata"]["locator"] == "page=-;offset=[[0, 459]];chunk=0"
    assert first["metadata"]["search_type"] == ["graph"]
    assert first["metadata"]["idx"] == "chunk-ca1d8268933dd200d88189cca497d46c"
    # 18094 不给分数 → 不编
    assert first["metadata"]["score"] is None
    # 回退原因只在真回退时出现
    assert "graph_reason" not in first["metadata"]
    # 上游没给 title 就是 null，不从正文或 file_id 猜
    assert first["metadata"]["title"] is None
    assert docs[1]["metadata"]["title"] == "丙-额度分项.docx"

    # 出站报文与地址
    assert len(fake.calls) == 1
    assert fake.calls[0]["url"].endswith("/v2/graph/query")
    assert fake.calls[0]["payload"] == {"query": "单笔授信超过五亿元由谁审议通过", "top_k": 3}


def test_rewritten_query_takes_precedence_and_is_reported():
    body = {"query": "原始问句", "rewritten_query": "改写后的问句",
            "knowledge_base_name": ["kb_9"], "top_k": 3}
    r, fake = call(body)
    assert fake.calls[0]["payload"]["query"] == "改写后的问句"
    assert "rewritten_query" in r.json()["msg"]


def test_top_k_defaults_to_ten_and_is_clamped_to_upstream_range():
    r, fake = call({"query": "问句"})
    assert fake.calls[0]["payload"]["top_k"] == 10

    r, fake = call({"query": "问句", "top_k": 50})
    assert fake.calls[0]["payload"]["top_k"] == 20
    assert "截断" in r.json()["msg"]

    r, fake = call({"query": "问句", "top_k": 0})
    assert fake.calls[0]["payload"]["top_k"] == 1


# ---------- 回退必须自证 ----------

def test_dense_fallback_is_not_reported_as_graph():
    r, fake = call(QA_REQUEST, FakeResponse(200, FALLBACK_BODY))
    docs = r.json()["data"]["documents_list"]
    assert docs[0]["metadata"]["search_type"] == ["dense_fallback"]
    assert docs[0]["metadata"]["graph_reason"] == "GRAPH_NOT_CALLED"
    assert "graph" not in docs[0]["metadata"]["search_type"]


def test_unknown_executed_route_fails_closed():
    bad = dict(GRAPH_BODY, executed_route=None)
    r, _ = call(QA_REQUEST, FakeResponse(200, bad))
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 502 and body["data"] is None
    assert "executed_route" in body["msg"]


# ---------- 来源 ----------

def test_multiple_sources_keep_all_but_first_goes_to_top_level():
    body = {"executed_route": "GRAPH", "reason": "GRAPH_CALLED", "docs": [
        {"rank": 1, "text": "同一段被两个文件引用。", "idx": "chunk-multi", "sources": [
            {"file_id": "999016", "title": "甲.pdf", "locator": "page=1"},
            {"file_id": "999017", "title": "乙.pdf", "locator": "page=2"},
        ]}]}
    r, _ = call(QA_REQUEST, FakeResponse(200, body))
    meta = r.json()["data"]["documents_list"][0]["metadata"]
    assert (meta["file_id"], meta["title"], meta["locator"]) == (999016, "甲.pdf", "page=1")
    assert len(meta["sources"]) == 2
    assert [s["file_id"] for s in meta["sources"]] == ["999016", "999017"]


def test_missing_sources_does_not_fabricate_file_id():
    body = {"executed_route": "GRAPH", "reason": "GRAPH_CALLED", "docs": [
        {"rank": 1, "text": "快照里没有来源映射的段落。", "idx": None, "sources": []}]}
    r, _ = call(QA_REQUEST, FakeResponse(200, body))
    meta = r.json()["data"]["documents_list"][0]["metadata"]
    assert meta["file_id"] is None
    assert meta["title"] is None
    assert meta["locator"] is None
    assert meta["sources"] == []
    assert meta["idx"] is None


def test_hits_without_text_are_dropped_and_counted():
    body = {"executed_route": "GRAPH", "reason": "GRAPH_CALLED", "docs": [
        {"rank": 1, "text": "  ", "idx": "chunk-empty", "sources": []},
        {"rank": 2, "text": "有效正文。", "idx": "chunk-ok", "sources": []}]}
    r, _ = call(QA_REQUEST, FakeResponse(200, body))
    body_json = r.json()
    docs = body_json["data"]["documents_list"]
    assert len(docs) == 1 and docs[0]["page_content"] == "有效正文。"
    assert "丢弃" in body_json["msg"]


def test_zero_hits_is_200_with_empty_list_and_honest_msg():
    body = {"executed_route": "GRAPH", "reason": "GRAPH_CALLED", "docs": []}
    r, _ = call(QA_REQUEST, FakeResponse(200, body))
    body_json = r.json()
    assert body_json["code"] == 200
    assert body_json["data"]["documents_list"] == []
    assert "未召回" in body_json["msg"]


# ---------- 失败面 ----------

@pytest.mark.parametrize("upstream", [
    FakeResponse(500, {"detail": "engine exploded"}),
    FakeResponse(503, "service unavailable"),
    TimeoutError("read timeout"),
    ConnectionRefusedError("connection refused"),
])
def test_upstream_failure_maps_to_502_with_reason(upstream):
    r, _ = call(QA_REQUEST, upstream)
    assert r.status_code == 200          # legacy 习惯：HTTP 200 + body.code
    body = r.json()
    assert body["code"] == 502
    assert body["data"] is None
    assert body["msg"] and len(body["msg"]) > 10


def test_non_json_upstream_is_502_not_500_html():
    r, _ = call(QA_REQUEST, FakeResponse(200, "<html>bad gateway</html>"))
    body = r.json()
    assert body["code"] == 502 and "JSON" in body["msg"]


@pytest.mark.parametrize("body", [
    {"query": ""},
    {"query": "   "},
    {"rewritten_query": "", "query": ""},
    {},
])
def test_empty_query_is_400_without_calling_upstream(body):
    r, fake = call(body)
    assert r.status_code == 200
    assert r.json()["code"] == 400
    assert fake.calls == []


def test_enabled_graph_false_is_not_served_as_graph():
    r, fake = call(dict(QA_REQUEST, enabled_graph=False))
    assert r.json()["code"] == 400
    assert "dense" in r.json()["msg"]
    assert fake.calls == []


def test_health_self_reports_wiring():
    c, _ = client()
    d = c.get("/health").json()
    assert d["schema"] == SCHEMA
    assert d["upstream_endpoint"] == "/v2/graph/query"
    assert d["graph_api"].endswith("18094")
    assert d["route_passthrough"] == {"GRAPH": "graph", "DENSE_FALLBACK": "dense_fallback"}
    # 未实现的部分必须自己说出来
    assert "knowledge_base_scope" in d["not_implemented"]


# ---------- global（社区摘要）：转发真实报告，不可用时如实报业务码 ----------

GLOBAL_BODY = {
    "schema": "llmke.graph-api.v1",
    "snapshot": "/tmp/snap",
    "query": "单笔授信超过五亿元由谁审议通过",
    "status": "READY",
    "communities": 2,
    "answer": "- 北方重工 额度 8000万元（来源：999010）\n- 星航贷 担保方式 保证（来源：999016）",
    "citations": [{"community": "c-1", "text": "北方重工 额度 8000万元", "sources": ["999010"]},
                  {"community": "c-2", "text": "星航贷 担保方式 保证", "sources": ["999016"]}],
    "sections": [
        {"id": "c-1", "size": 2, "isolated": False,
         "entities": ["ent:北方重工", "ent:额度"],
         "facts": [{"text": "北方重工 额度 8000万元", "sources": ["999010"]}],
         "fact_count": 1, "sources": ["999010"]},
        {"id": "c-2", "size": 2, "isolated": False,
         "entities": ["ent:星航贷", "ent:保证"],
         "facts": [{"text": "星航贷 担保方式 保证", "sources": ["999016"]}],
         "fact_count": 1, "sources": ["999016"]},
    ],
    "citation_check": {"ok": True, "checked": 2, "valid": ["c-1:999010", "c-2:999016"],
                       "invalid": [], "sources_available": True, "reason": None},
    "used_communities": ["c-1", "c-2"],
    "reason": None,
}


def global_call(body=None, *results):
    c, fake = client(*results or (FakeResponse(200, GLOBAL_BODY),))
    payload = dict(QA_REQUEST, query_mode="global", summary_top_k=5)
    payload.update(body or {})
    return c.post("/retrieval_documents_global", json=payload), fake


def test_global_forwards_report_and_returns_legacy_shape():
    r, fake = global_call()
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    # Java `RetrievedData.getGlobalAnswer` 读的就是 global_answer
    assert data["global_answer"] == GLOBAL_BODY["answer"]
    # 正文是"事实 + 来源"，不是没有出处的结论
    doc = data["documents_list"][0]
    assert "（来源：999010）" in doc["page_content"]
    assert doc["metadata"]["search_type"] == ["global"]      # 不混成 graph/dense_fallback
    assert doc["metadata"]["source"] is None
    assert doc["metadata"]["file_id"] == 999010
    assert doc["metadata"]["sources"] == [{"file_id": "999010"}]
    # 社区号进 metadata.community，不占 idx（idx 是块 id 语义）
    assert doc["metadata"]["community"] == "c-1"
    assert doc["metadata"]["idx"] is None
    # 五键仍然齐全（legacy 形状）
    for key in ("faq_result_list", "database_documents", "web_documents_list", "log_list"):
        assert data[key] == []

    # 出站：打到 global 端点，社区条数取 Java global 分支真实发的 summary_top_k=5
    assert len(fake.calls) == 1
    assert fake.calls[0]["url"].endswith("/v2/graph/global")
    assert fake.calls[0]["payload"] == {"query": QA_REQUEST["query"], "max_communities": 5}


def test_global_only_ships_communities_used_in_answer():
    """上游给了 used_communities 时，只把这些社区转成文档，别把全部社区整包下发。"""
    body = dict(GLOBAL_BODY)
    body["sections"] = GLOBAL_BODY["sections"] + [
        {"id": "c-3", "size": 3, "isolated": True, "entities": ["ent:无关"],
         "facts": [{"text": "无关事实", "sources": ["999099"]}], "fact_count": 1,
         "sources": ["999099"]}]
    body["used_communities"] = ["c-1"]

    r, _ = global_call(None, FakeResponse(200, body))
    data = r.json()["data"]
    assert len(data["documents_list"]) == 1
    assert "（来源：999010）" in data["documents_list"][0]["page_content"]
    assert all("999099" not in doc["page_content"] for doc in data["documents_list"])


def test_global_without_report_is_501():
    upstream = dict(GLOBAL_BODY, reason="NO_COMMUNITY_REPORT", communities=0,
                    answer="", citations=[], sections=[],
                    citation_check={"ok": False, "checked": 0, "valid": [], "invalid": [],
                                    "sources_available": False,
                                    "reason": "NO_COMMUNITY_REPORT"})
    r, _ = global_call(None, FakeResponse(200, upstream))
    body = r.json()
    assert body["code"] == 501
    assert body["msg"] == "global not ready: community report not wired"
    assert body["data"] is None


def test_global_without_communities_is_501():
    upstream = dict(GLOBAL_BODY, reason="NO_COMMUNITIES", communities=0, answer="",
                    citations=[], sections=[])
    r, _ = global_call(None, FakeResponse(200, upstream))
    body = r.json()
    assert body["code"] == 501
    assert body["msg"] == "global not ready: no communities in snapshot"
    assert body["data"] is None


def test_global_with_invalid_citations_is_502_not_success():
    upstream = dict(GLOBAL_BODY, reason="CITATION_INVALID")
    r, _ = global_call(None, FakeResponse(200, upstream))
    body = r.json()
    assert body["code"] == 502
    assert "citation" in body["msg"].lower()
    assert body["data"] is None


def test_global_upstream_down_is_502():
    r, _ = global_call(None, ConnectionRefusedError("refused"))
    assert r.json()["code"] == 502


def test_global_with_graph_disabled_is_400_and_never_forwards():
    r, fake = global_call({"enabled_graph": False})
    body = r.json()
    assert body["code"] == 400
    assert "enabled_graph" in body["msg"]
    assert body["data"] is None
    assert fake.calls == []


def test_health_reports_global_wired_with_upstream_endpoint():
    c, _ = client()
    g = c.get("/health").json()["global"]
    assert g["endpoint"] == "/retrieval_documents_global"
    assert g["wired"] is True
    assert g["upstream_endpoint"] == "/v2/graph/global"
    # 不可用条件仍要写清楚，别让 wired=true 被读成"永远有答案"
    assert set(g["unavailable_when"]) == {"NO_COMMUNITY_REPORT", "NO_COMMUNITIES",
                                          "CITATION_INVALID"}
