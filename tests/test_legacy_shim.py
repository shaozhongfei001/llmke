"""19529 legacy 兼容层：ES 取块（复用 legacy_es）、计数回填、不伪成功。

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

# legacy_es 认识的形状：`{chunk_id: source}`（legacy graph_fun_tool.py:956 折形）
ES_ROWS = [
    {"chunk-a": {"page_content": "单笔授信金额超过五亿元须提交分行审批。",
                 "metadata": {"file_id": 999010, "page_number": "[0, 0]",
                              "offset": "[[0, 66]]", "chunk_index": "0"}}},
    {"chunk-b": {"page_content": "贷后检查每季度开展一次。",
                 "metadata": {"title": "丙-额度分项.docx"}}},
]
ES_OK = {"code": 200, "msg": "查询成功",
         "data": {"total_count": 2, "result_data": ES_ROWS}}
ES_EMPTY = {"code": 200, "msg": "查询成功", "data": {"total_count": 0, "result_data": []}}

# 19527 的真实返回是扁平 hit（实测 2026-11-02）。legacy_es 目前按折形解析，
# 会拿 `_source` 当 chunk id —— 本层必须把它降级成文件级 locator，不能写进产物。
ES_FLAT = {"code": 200, "msg": "查询成功", "data": {"total_count": 1, "result_data": [
    {"_index": "kb_9", "_id": "144729756366911329", "_score": 1.0,
     "_source": {"page_content": "星航贷单户最高授信额度为8000万元。",
                 "metadata": {"file_id": 999010, "title": "丙-额度分项.docx",
                              "page_number": [0, 0, 0, 0]}}}]}}

LEGACY_BODY = {
    "space_name": "kb_9",
    "embedding_model_name": "text-embedding-bge-m3",
    "model_info": {"modelName": "qwen2.5-7b-instruct"},
    "col_name": "title",
    "col_values": ["丙-额度分项.docx"],
    "generation": "V0",
}


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
    """按 URL 分流：ES 代理 vs 18094 建图；记录调用并可分别注入响应/异常。"""

    def __init__(self, build=None, es=None, build_exc=None, es_exc=None):
        self.calls = []
        self._build = build if build is not None else FakeResponse(200, dict(BUILT))
        self._es = es if es is not None else FakeResponse(200, json.loads(json.dumps(ES_OK)))
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


def client(**kw):
    return TestClient(create_app(**kw))


# ── 1. 无 docs：经 legacy_es 取块再转发 ───────────────────────────────


def test_no_docs_fetches_chunks_from_es_then_forwards(monkeypatch):
    monkeypatch.setenv("LLMKE_V2_ES_PROXY", "http://127.0.0.1:19527/")
    rec = Recorder()
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()

    assert out["code"] == 200, out
    assert len(rec.es_calls) == 1
    es_call = rec.es_calls[0]
    assert es_call["url"] == "http://127.0.0.1:19527/search_by_custom_param"
    assert es_call["payload"] == {                     # legacy graph_fun_tool.py:919-929 同款
        "index_name": ["kb_9", "table_chunks_kb_9"],
        "col_name": "title",
        "col_values": ["丙-额度分项.docx"],
    }

    sent = rec.build_calls[0]["payload"]["docs"]
    assert [d["text"] for d in sent] == ["单笔授信金额超过五亿元须提交分行审批。",
                                        "贷后检查每季度开展一次。"]
    assert sent[0]["file_id"] == "999010"                                  # metadata.file_id
    assert sent[0]["locator"] == "page=-;offset=[[0, 66]];chunk=0"    # 全 0 页码不算页
    assert sent[1]["file_id"] == "丙-额度分项.docx"                          # 缺 file_id 兜底
    assert sent[1]["locator"] == "es:chunk-b"                               # 无元数据 → es:<id>
    assert set(sent[0]) == {"file_id", "text", "locator", "title"}                   # es_id 不进 BuildDoc
    assert out["data"]["es"]["es_docs_used"] == 2


def test_flat_es_hit_keeps_real_id_and_drops_zero_page():
    """真实 19527 是扁平 hit：必须取 row._id / row._source，且全 0 页码不写成第 0 页。"""
    rec = Recorder(es=FakeResponse(200, json.loads(json.dumps(ES_FLAT))))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()

    assert out["code"] == 200, out
    sent = rec.build_calls[0]["payload"]["docs"]
    assert sent[0]["text"] == "星航贷单户最高授信额度为8000万元。"
    assert sent[0]["file_id"] == "999010"
    # 该 fixture 只有全 0 页码、没有 offset/chunk：退回真实 ES id，且不是 "_source"
    assert sent[0]["locator"] == "es:144729756366911329"


def test_es_empty_is_500_and_never_calls_graph_build():
    """原"无 docs → 400"的行为改为：ES 也查不到才 500，且不许打 18094。"""
    rec = Recorder(es=FakeResponse(200, json.loads(json.dumps(ES_EMPTY))))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] == 500
    assert "未查询到" in out["msg"]
    assert rec.build_calls == []


def test_es_failure_is_500_with_reason_and_no_build_call():
    rec = Recorder(es_exc=ConnectionError("connection refused"))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] == 500
    assert "connection refused" in out["msg"]
    assert rec.build_calls == []


def test_es_http_error_is_500():
    rec = Recorder(es=FakeResponse(503, "<html>es down</html>"))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] == 500
    assert "503" in out["msg"]
    assert rec.build_calls == []


def test_missing_space_name_is_500_with_reason_and_no_upstream_call():
    rec = Recorder()
    out = client(http_post=rec).post("/generate_triple_data",
                                     json={"col_name": "title", "col_values": ["x"]}).json()
    assert out["code"] == 500
    assert "space_name" in out["msg"]
    assert rec.calls == []


# ── 2. 计数回填（Java 判定靠它） ──────────────────────────────────────


def test_edge_counts_come_from_upstream_facts_and_edges():
    rec = Recorder(build=FakeResponse(200, dict(BUILT, facts=3, edges=5)))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] == 200
    assert out["data"]["edges_total"] == 3          # facts = 抽取三元组总数
    assert out["data"]["edges_written"] == 5        # edges = 图中真实边数
    assert out["data"]["triples_total"] == 3
    assert "facts" in out["data"]["edges_semantics"]


@pytest.mark.parametrize("upstream", [
    dict(BUILT, facts=0, edges=5),
    dict(BUILT, facts=3, edges=0),
    {k: v for k, v in BUILT.items() if k not in ("facts", "edges")},
    dict(BUILT, facts=None, edges=2),
    dict(BUILT, facts=True, edges=2),               # bool 不算数值
])
def test_zero_or_missing_counts_never_report_success(upstream):
    rec = Recorder(build=FakeResponse(200, upstream))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] != 200
    assert "edges_total" in out["msg"] or "计数" in out["msg"]


# ── 3. 请求自带 docs（V2 形态） ───────────────────────────────────────


def test_request_docs_skip_es_and_forward(monkeypatch):
    monkeypatch.setenv("LLMKE_V2_GRAPH_API", "http://127.0.0.1:18094/")
    rec = Recorder()
    out = client(http_post=rec).post("/generate_triple_data", json=dict(LEGACY_BODY, docs=[
        {"file_id": "343", "text": "单笔授信超过五亿元须经分行审批", "locator": "p12"},
        {"file_id": "343", "text": "贷后检查每季度一次"},
    ])).json()
    assert out["code"] == 200
    assert rec.es_calls == []                                       # 带 docs 就不查 ES
    assert rec.build_calls[0]["url"] == "http://127.0.0.1:18094/v2/graph/build"
    assert rec.build_calls[0]["payload"]["docs"] == [
        {"file_id": "343", "text": "单笔授信超过五亿元须经分行审批", "locator": "p12"},
        {"file_id": "343", "text": "贷后检查每季度一次", "locator": "file:343"},
    ]


def test_doc_without_text_is_rejected():
    rec = Recorder()
    out = client(http_post=rec).post("/generate_triple_data",
                                     json={"space_name": "kb_9",
                                           "docs": [{"file_id": "1", "text": "   "}]}).json()
    assert out["code"] == 400
    assert "text" in out["msg"]
    assert rec.calls == []


def test_root_env_and_request_override(monkeypatch):
    monkeypatch.setenv("LLMKE_V2_ROOT", "/env/root")
    rec = Recorder()
    assert client(http_post=rec).post(
        "/generate_triple_data", json=LEGACY_BODY).json()["code"] == 200
    assert rec.build_calls[-1]["payload"]["root"] == "/env/root"

    assert client(http_post=rec).post(
        "/generate_triple_data", json=dict(LEGACY_BODY, root="/req/root")).json()["code"] == 200
    assert rec.build_calls[-1]["payload"]["root"] == "/req/root"


# ── 4. 上游异常 ──────────────────────────────────────────────────────


def test_upstream_500_becomes_non_200_code_with_reason():
    rec = Recorder(build=FakeResponse(500, {"detail": "build failed: RuntimeError: llm 超时"}))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] != 200
    assert "llm 超时" in out["msg"]
    assert out["data"]["upstream_status"] == 500


def test_upstream_timeout_returns_json_not_html():
    rec = Recorder(build_exc=TimeoutError("read timed out"))
    r = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY)
    assert r.status_code == 200                        # legacy 约定：HTTP 200 + body.code
    assert r.headers["content-type"].startswith("application/json")
    out = r.json()
    assert out["code"] != 200
    assert "TimeoutError" in out["msg"] and "read timed out" in out["msg"]


def test_upstream_200_without_built_snapshot_is_failure():
    rec = Recorder(build=FakeResponse(200, {"schema": "x", "status": "PARTIAL", "snapshot": None}))
    out = client(http_post=rec).post("/generate_triple_data", json=LEGACY_BODY).json()
    assert out["code"] != 200
    assert "BUILT" in out["msg"]


# ── 5. 未接线端点 ────────────────────────────────────────────────────


def test_generate_community_is_501_and_never_calls_upstream():
    rec = Recorder()
    out = client(http_post=rec).post("/generate_community", json={
        "space_name": "kb_9", "max_level": 2, "min_community_size": 3,
        "resolution": 1.0, "with_summary": True,
    }).json()
    assert out["code"] == 501
    assert out["msg"] == "community not wired yet"
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
        assert out["data"]["upstream_called"] is False, path
    assert rec.calls == []


# ── 6. 其他 ──────────────────────────────────────────────────────────


def test_json_string_body_is_accepted():
    rec = Recorder()
    r = client(http_post=rec).post(
        "/generate_triple_data",
        content=json.dumps(dict(LEGACY_BODY, docs=[{"file_id": "1", "text": "文本"}])),
        headers={"content-type": "application/json"})
    assert r.json()["code"] == 200


def test_health_reports_wiring_without_calling_upstream():
    rec = Recorder()
    out = client(http_post=rec).get("/health").json()
    assert out["schema"] == SCHEMA
    assert out["wired"] == ["POST /generate_triple_data"]
    assert out["not_wired"]["/generate_community"] == "community not wired yet"
    assert out["es_proxy"].startswith("http")
    assert rec.calls == []
