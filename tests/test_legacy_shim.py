"""19529 legacy 兼容层：ES 取正文、计数回填、以及"不许伪成功"。

依赖 fastapi/httpx，在工具 venv 里可能没有，故 importorskip；
真实运行环境是 hipporag venv（见 docs/v2-tasks/ENV.md）。
"""

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from graph_engine_adapter.legacy_shim import SCHEMA, create_app  # noqa: E402

BUILT = {
    "schema": "llmke.graph-api.v1",
    "status": "BUILT",
    "snapshot": "/tmp/snap/snapshot-1",
    "generation": 1,
    "documents": 2,
    "chunks": 2,
    "sources": 2,
    "facts": 7,
    "edges": 2,
}

# 实测 19527 的真实形状：hit 是扁平的 {_index,_id,_score,_source,sort}
ES_HITS = {
    "code": 200,
    "msg": "查询成功",
    "data": {
        "total_count": 2,
        "result_data": [
            {"_index": "kb_9", "_id": "144729756366911329", "_score": 1.0,
             "_source": {"page_content": "单笔授信金额超过五亿元须提交分行审批。",
                         "metadata": {"file_id": 999010, "title": "丙-额度分项.docx",
                                      "page_number": [0, 0, 0, 0]}}},
            {"_index": "table_chunks_kb_9", "_id": "144729756366911330",
             "_source": {"page_content": "贷后检查每季度开展一次。",
                         "metadata": {"title": "丙-额度分项.docx"}}},
        ],
    },
}

ES_EMPTY = {"code": 200, "msg": "查询成功", "data": {"total_count": 0, "result_data": []}}


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else str(body)

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("not json")
        return self._body


class Recorder:
    """按 URL 分流：ES 代理 vs 18094 建图。记录每次调用，可分别注入响应/异常。"""

    def __init__(self, build=None, es=None, build_exc=None, es_exc=None):
        self.calls = []
        self._build = build if build is not None else FakeResponse(200, dict(BUILT))
        self._es = es if es is not None else FakeResponse(200, json.loads(json.dumps(ES_HITS)))
        self._build_exc = build_exc
        self._es_exc = es_exc

    def __call__(self, url, payload, timeout):
        self.calls.append({"url": url, "payload": payload, "timeout": timeout})
        if url.endswith("/search_by_custom_param"):
            if self._es_exc:
                raise self._es_exc
            return self._es
        if self._build_exc:
            raise self._build_exc
        return self._build

    @property
    def build_calls(self):
        return [c for c in self.calls if not c["url"].endswith("/search_by_custom_param")]

    @property
    def es_calls(self):
        return [c for c in self.calls if c["url"].endswith("/search_by_custom_param")]


LEGACY_BODY = {
    "space_name": "kb_9",
    "embedding_model_name": "text-embedding-bge-m3",
    "model_info": {"modelName": "qwen2.5-7b-instruct"},
    "col_name": "title",
    "col_values": ["丙-额度分项.docx"],
    "generation": "V0",
}


def client(**kw):
    return TestClient(create_app(**kw))


# ── 1. 带 docs：直接转发 ──────────────────────────────────────────────


def test_forwards_docs_to_v2_graph_build(monkeypatch):
    monkeypatch.setenv("LLMKE_V2_GRAPH_API", "http://127.0.0.1:18094/")
    monkeypatch.delenv("LLMKE_V2_ROOT", raising=False)
    rec = Recorder()
    body = dict(LEGACY_BODY, docs=[
        {"file_id": "343", "text": "单笔授信超过五亿元须经分行审批", "locator": "p12"},
        {"file_id": "343", "text": "贷后检查每季度一次"},
    ])

    r = client(http_post=rec).post("/generate_triple_data", json=body)
    assert r.status_code == 200
    out = r.json()
    assert out["code"] == 200
    assert out["data"]["chunks"] == 2 and out["data"]["snapshot"] == "/tmp/snap/snapshot-1"

    assert rec.es_calls == []                       # 带 docs 就不查 ES
    assert len(rec.build_calls) == 1
    call = rec.build_calls[0]
    assert call["url"] == "http://127.0.0.1:18094/v2/graph/build"      # 尾斜杠不叠成 //
    assert call["payload"]["docs"] == [
        {"file_id": "343", "text": "单笔授信超过五亿元须经分行审批", "locator": "p12"},
        {"file_id": "343", "text": "贷后检查每季度一次", "locator": None},  # 缺 locator 传 None
    ]
    assert call["payload"]["root"] == ".artifacts/api-root"
    assert call["timeout"] > 0


def test_root_env_and_request_override(monkeypatch):
    monkeypatch.setenv("LLMKE_V2_ROOT", "/env/root")
    rec = Recorder()
    ok = client(http_post=rec).post("/generate_triple_data",
                                    json={"space_name": "kb_9", "docs": ["文本"]})
    assert ok.json()["code"] == 200
    assert rec.build_calls[-1]["payload"]["root"] == "/env/root"

    ok = client(http_post=rec).post("/generate_triple_data",
                                    json={"space_name": "kb_9", "docs": ["文本"],
                                          "root": "/req/root"})
    assert ok.json()["code"] == 200
    assert rec.build_calls[-1]["payload"]["root"] == "/req/root"


# ── 2. 无 docs：走 legacy 同款 ES 读法 ───────────────────────────────


def test_no_docs_fetches_chunks_from_es_then_forwards(monkeypatch):
    monkeypatch.setenv("LLMKE_V2_ES_PROXY", "http://127.0.0.1:19527/")
    rec = Recorder()
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()

    assert out["code"] == 200, out
    # ES 请求体与 legacy graph_fun_tool.py:919-929 一致
    assert len(rec.es_calls) == 1
    es_call = rec.es_calls[0]
    assert es_call["url"] == "http://127.0.0.1:19527/search_by_custom_param"
    assert es_call["payload"] == {
        "index_name": ["kb_9", "table_chunks_kb_9"],
        "col_name": "title",
        "col_values": ["丙-额度分项.docx"],
    }

    # 正文/来源/locator 都来自 ES 真实字段
    assert rec.build_calls[0]["payload"]["docs"] == [
        {"file_id": "999010",                                # metadata.file_id
         "text": "单笔授信金额超过五亿元须提交分行审批。",       # _source.page_content
         "locator": "es:144729756366911329"},                # 无 page_num → es:<_id>，不编页码
        {"file_id": "丙-额度分项.docx",                        # 无 file_id → col_values[0]，留痕
         "text": "贷后检查每季度开展一次。",
         "locator": "es:144729756366911330"},
    ]
    assert out["data"]["file_id_fallbacks"] == 1
    assert out["data"]["es"]["es_total_count"] == 2
    assert out["data"]["es"]["es_docs_used"] == 2


def test_es_empty_is_500_and_never_calls_graph_build():
    rec = Recorder(es=FakeResponse(200, json.loads(json.dumps(ES_EMPTY))))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] == 500
    assert "未查询到相关文本" in out["msg"]
    assert rec.build_calls == []                    # 没正文就绝不能调 18094


def test_es_unavailable_is_500_with_reason():
    rec = Recorder(es_exc=ConnectionError("connection refused"))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] == 500
    assert "ES 查询不可用" in out["msg"] and "connection refused" in out["msg"]
    assert rec.build_calls == []


def test_es_http_error_is_500():
    rec = Recorder(es=FakeResponse(503, "<html>es down</html>"))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] == 500
    assert "503" in out["msg"]


def test_missing_space_name_is_500_with_reason():
    rec = Recorder()
    out = client(http_post=rec).post("/generate_triple_data",
                                     json={"col_name": "title", "col_values": ["x"]}).json()
    assert out["code"] == 500
    assert "space_name" in out["msg"]
    assert rec.calls == []


def test_es_legacy_folded_shape_is_accepted():
    """legacy 在 graph_fun_tool.py:956 把 hit 折成 {_id: _source}；这种形态也要认。"""
    folded = {"code": 200, "data": {"total_count": 1, "result_data": [
        {"144729756366911329": {"page_content": "折形正文", "metadata": {"file_id": 7}}}]}}
    rec = Recorder(es=FakeResponse(200, folded))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] == 200
    assert rec.build_calls[0]["payload"]["docs"] == [
        {"file_id": "7", "text": "折形正文", "locator": "es:144729756366911329"}]


# ── 3. 计数回填（Java 判定靠它） ──────────────────────────────────────


def test_edge_counts_come_from_upstream_facts_and_edges():
    upstream = dict(BUILT, facts=3, edges=5)
    rec = Recorder(build=FakeResponse(200, upstream))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] == 200
    assert out["data"]["edges_total"] == 3          # facts = 抽取三元组总数
    assert out["data"]["edges_written"] == 5        # edges = 图中真实边数
    assert out["data"]["triples_total"] == 3
    assert "facts" in out["data"]["edges_semantics"]


@pytest.mark.parametrize("upstream", [
    dict(BUILT, facts=0, edges=5),
    dict(BUILT, facts=3, edges=0),
    {k: v for k, v in BUILT.items() if k not in ("facts", "edges")},   # 上游没给计数
    dict(BUILT, facts=None, edges=2),
])
def test_zero_or_missing_counts_never_report_success(upstream):
    rec = Recorder(build=FakeResponse(200, upstream))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] != 200
    assert "edges_total" in out["msg"] or "计数" in out["msg"]


# ── 4. 上游异常 ──────────────────────────────────────────────────────


def test_upstream_500_becomes_non_200_code_with_reason():
    rec = Recorder(build=FakeResponse(500, {"detail": "build failed: RuntimeError: llm 超时"}))
    out = client(http_post=rec).post("/generate_triple_data",
                                    json={"docs": [{"file_id": "1", "text": "x"}]}).json()
    assert out["code"] != 200
    assert "llm 超时" in out["msg"]
    assert out["data"]["upstream_status"] == 500


def test_upstream_timeout_returns_json_not_html():
    rec = Recorder(build_exc=TimeoutError("read timed out"))
    r = client(http_post=rec).post("/generate_triple_data",
                                   json={"docs": [{"file_id": "1", "text": "x"}]})
    assert r.status_code == 200                        # legacy 约定：HTTP 200 + body.code
    assert r.headers["content-type"].startswith("application/json")
    out = r.json()
    assert out["code"] != 200
    assert "TimeoutError" in out["msg"] and "read timed out" in out["msg"]


def test_upstream_200_without_built_snapshot_is_failure():
    rec = Recorder(build=FakeResponse(200, {"schema": "x", "status": "PARTIAL", "snapshot": None}))
    out = client(http_post=rec).post("/generate_triple_data",
                                     json={"docs": [{"file_id": "1", "text": "x"}]}).json()
    assert out["code"] != 200
    assert "BUILT" in out["msg"]


def test_upstream_non_json_body_is_failure():
    rec = Recorder(build=FakeResponse(502, "<html>bad gateway</html>"))
    out = client(http_post=rec).post("/generate_triple_data",
                                     json={"docs": [{"file_id": "1", "text": "x"}]}).json()
    assert out["code"] != 200
    assert out["data"]["upstream_status"] == 502


# ── 5. 未接线端点 ────────────────────────────────────────────────────


def test_generate_community_is_501_and_never_calls_upstream():
    rec = Recorder()
    out = client(http_post=rec).post("/generate_community", json={
        "space_name": "kb_9", "max_level": 2, "min_community_size": 3,
        "resolution": 1.0, "with_summary": True,
    }).json()
    assert out["code"] == 501
    assert out["msg"] == "community not wired yet"
    assert out["data"]["wired"] is False
    assert rec.calls == []


def test_delete_endpoints_are_501_and_never_call_upstream():
    rec = Recorder()
    c = client(http_post=rec)
    for path, payload in (
        ("/del_space", {"space_name": "kb_9", "condition_json": {"file_id": 343}}),
        ("/del_space", {"space_name": "kb_9"}),
        ("/del_doc_entity", {"db_name": "rag_knowledge_base",
                             "index_name": "graph_entity_kb_9",
                             "update_condition_json": {"file_id": [343]}}),
    ):
        out = c.post(path, json=payload).json()
        assert out["code"] == 501, path
        assert "not wired yet" in out["msg"], path
        assert out["data"]["upstream_called"] is False, path
    assert rec.calls == []


# ── 6. 输入校验与其他 ────────────────────────────────────────────────


def test_doc_without_text_is_rejected():
    rec = Recorder()
    out = client(http_post=rec).post("/generate_triple_data",
                                     json={"docs": [{"file_id": "1", "text": "   "}]}).json()
    assert out["code"] == 400
    assert "text" in out["msg"]
    assert rec.calls == []


def test_json_string_body_is_accepted():
    """Java 侧 HttpEntity<String> 发 body，必要时可能是 JSON 字符串。"""
    rec = Recorder()
    r = client(http_post=rec).post(
        "/generate_triple_data",
        content=json.dumps({"space_name": "kb_9", "docs": [{"file_id": "1", "text": "文本"}]}),
        headers={"content-type": "application/json"})
    assert r.json()["code"] == 200


def test_health_reports_wiring_without_calling_upstream():
    rec = Recorder()
    out = client(http_post=rec).get("/health").json()
    assert out["schema"] == SCHEMA
    assert out["wired"] == ["POST /generate_triple_data"]
    assert set(out["not_wired"]) == {"/generate_community", "/del_space", "/del_doc_entity"}
    assert out["not_wired"]["/generate_community"] == "community not wired yet"
    assert out["es_proxy"].startswith("http")
    assert rec.calls == []
