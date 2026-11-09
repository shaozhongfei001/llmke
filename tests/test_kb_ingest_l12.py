"""P4-L12 · `IngestRequest` / 响应模型 / 错误码表（B4/B5/B6/B7 + Q4/Q9 + 两个 207）。

**只在 hipporag 环境跑**：`IngestRequest` 是 Pydantic 模型，而 `llmke-v2-toolenv`
既无 pydantic 也无 fastapi（R-0 D-5 实测）。v2 侧的 skip 单列、**不计入通过数**。
编排逻辑（B1/B2/B3/B8）在 `test_kb_delta_l12.py`，两边都必须绿。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="llmke-v2-toolenv 无 fastapi/pydantic（R-0 D-5）")
pytest.importorskip("pydantic", reason="同上")

from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

import kb_ingest_service as S  # noqa: E402
from ingest_pipeline import kb_pipeline as K  # noqa: E402

SERVICE_PY = Path(S.__file__).resolve()


# ---------------------------------------------------------------- 替身
class FakeService:
    """替身：记录收到的请求，并可注入异常。"""

    def __init__(self, exc=None, data=None):
        self.exc = exc
        self.seen = []
        self.data = data or {"status": "OK", "kb": "kb_9", "cursor": "cursor-new",
                             "diff": {"added": ["290"], "changed": [], "removed": [],
                                      "unchanged": [], "set_digest": "d", "reason": "FILE_SET_CHANGED",
                                      "diff_source": "request"},
                             "projection": {"status": "READY", "chunks": 1}, "graph": {}}

    def run(self, req):
        self.seen.append(req)
        if self.exc:
            raise self.exc
        return self.data


def _client(service) -> TestClient:
    return TestClient(S.create_app(service=service))


def _body(**kw):
    base = {"kb": "kb_9", "file_id": 290, "operation": "UPSERT",
            "doc2md_dir": "/doc2md-out", "file_name": "a.md"}
    base.update(kw)
    return base


# ---------------------------------------------------------------- B5 强校验
def test_b5_missing_required_field_is_422():
    client = _client(FakeService())
    resp = client.post("/kb/ingest", json={"file_id": 290, "operation": "UPSERT"})
    assert resp.status_code == 422, resp.text


def test_b5_request_model_is_pydantic_not_bare_dict():
    req = S.IngestRequest(**{**_body(), "source": "kb_9/a.md"})
    assert hasattr(S.IngestRequest, "model_fields"), "必须是 Pydantic 模型，不是裸 dict"
    assert req.source == "kb_9/a.md"
    assert {"kb", "file_id", "operation", "doc2md_dir", "source"} <= set(S.IngestRequest.model_fields)


def test_b5_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        S.IngestRequest(**{**_body(), "totally_unknown": 1})


def test_b5_operation_enum_rejects_unknown_value():
    with pytest.raises(ValidationError):
        S.IngestRequest(**{**_body(), "operation": "MERGE"})


def test_b5_full_rebuild_requires_fallback_reason():
    with pytest.raises(ValidationError):
        S.IngestRequest(**{**_body(), "operation": "FULL_REBUILD"})


def test_b5_source_is_passed_through_to_service():
    svc = FakeService()
    client = _client(svc)
    resp = client.post("/kb/ingest", json=_body(source="kb_9/a.md", include_payloads=True))
    assert resp.status_code == 200, resp.text
    assert svc.seen[0]["source"] == "kb_9/a.md", "source 必须真传到执行层"


# ---------------------------------------------------------------- B6 同入口同模型
def test_b6_full_and_incremental_share_one_entry_and_one_model():
    inc, full = FakeService(), FakeService()
    body_inc = _body(operation="UPSERT")
    body_full = _body(operation="FULL_REBUILD", fallback_reason="MANUAL")

    r1 = _client(inc).post("/kb/ingest", json=body_inc)
    r2 = _client(full).post("/kb/ingest", json=body_full)

    assert r1.status_code == r2.status_code == 200
    assert set(json_keys(r1)) == set(json_keys(r2)), "全量与增量响应字段集必须相同"
    assert set(S.IngestResult.model_fields) == {"schema", "code", "msg", "data"}


def json_keys(resp):
    return resp.json().keys()


def test_b6_response_is_pydantic_model():
    assert hasattr(S.IngestResult, "model_fields")
    assert S.IngestResult.model_fields["schema"].default == "llmke.kb-ingest.result/1"


# ---------------------------------------------------------------- Q2 IngestPlan 不进响应
def test_q2_ingest_plan_is_not_a_response_field():
    from ingest_pipeline.kb_delta import IngestPlan

    plan_names = set(getattr(IngestPlan, "__dataclass_fields__", {}))
    assert plan_names, "IngestPlan 应是 dataclass"
    assert plan_names & set(S.IngestResult.model_fields) == set(), \
        f"IngestPlan 的字段不得出现在响应模型里：{plan_names & set(S.IngestResult.model_fields)}"
    data_ann = str(S.IngestResult.model_fields["data"].annotation)
    assert "IngestPlan" not in data_ann


# ---------------------------------------------------------------- B7 删掉自动重解析
def test_b7_no_auto_reparse_path_left():
    src = SERVICE_PY.read_text(encoding="utf-8")
    for banned in ("ingest_file", "_download_minio", "v2_ingest_doc2md", "boto3"):
        assert banned not in src, f"file_url 自动重解析残留：{banned}"


def test_b7_file_url_does_not_trigger_reparse():
    svc = FakeService()
    client = _client(svc)
    resp = client.post("/kb/ingest", json=_body(file_url="http://127.0.0.1:19000/b/o.xlsx"))
    assert resp.status_code == 200, resp.text
    assert svc.seen, "file_url 只是元数据，不得短路到重解析"


# ---------------------------------------------------------------- Q4 错误码表
CONTRACT_CODES = {
    "DOC2MD_ARTIFACT_INCOMPLETE": 400, "SOURCE_DIVERGED": 409, "KB_STATE_CORRUPT": 500,
    "CURSOR_CONFLICT": 409, "NO_BASELINE_SNAPSHOT": 422, "ALL_REVOKED": 422,
    "STALE_FENCING": 409, "DELTA_INCONSISTENT": 500, "COMMUNITY_INVALID": 207,
    "GRAPH_UNREACHABLE": 502, "INDEX_WRITE_FAILED": 502,
}
WHITELIST_CODES = {
    "PROJECTION_NOT_APPLICABLE": 422, "DOCS_EMPTY": 422, "KB_REQUIRED": 422,
    "GRAPH_API_UNREACHABLE": 502, "GRAPH_BUILD_NOT_BUILT": 502,
    "POLICY_INVALID": 500, "PROJECTION_COVERAGE_LOST": 500,
    "PROJECTION_EMPTY_CHUNK": 500, "PROJECTION_MODE_INVALID": 500,
}


@pytest.mark.parametrize("code,http", sorted(CONTRACT_CODES.items()))
def test_q4_contract_code_maps_to_contract_http(code, http):
    assert S.http_status_for(K.PipelineRefused(code)) == http


@pytest.mark.parametrize("code,http", sorted(WHITELIST_CODES.items()))
def test_q4_whitelist_code_maps_as_ruled(code, http):
    assert S.http_status_for(K.PipelineRefused(code)) == http


def test_q4_table_has_no_extra_contract_codes_missing():
    missing = set(CONTRACT_CODES) - set(S.ERROR_HTTP)
    assert missing == set(), f"契约 §5 漏登：{missing}"


def test_q4_graph_build_http_prefix_is_dynamic():
    assert S.http_status_for(K.PipelineRefused("GRAPH_BUILD_HTTP_500")) == 502


def test_q8_projection_refused_is_mapped_per_code_not_blanket():
    from rag_projection.projection import ProjectionRefused

    # 产物侧 8 条 → 400
    assert S.http_status_for(ProjectionRefused("ARTIFACT_TEXT_HASH_MISMATCH")) == 400
    assert S.http_status_for(ProjectionRefused("ARTIFACT_PART_MISSING")) == 400
    # 服务端配置/算法 → 500（现状一律 400，是本次修的 bug）
    assert S.http_status_for(ProjectionRefused("PROJECTION_COVERAGE_LOST")) == 500
    assert S.http_status_for(ProjectionRefused("PROJECTION_EMPTY_CHUNK")) == 500
    assert S.http_status_for(ProjectionRefused("PROJECTION_MODE_INVALID")) == 500
    assert S.http_status_for(ProjectionRefused("POLICY_INVALID")) == 500


def test_q8_artifact_refused_is_400_as_a_family():
    from parse_artifact.store import ArtifactRefused

    for code in ("MISSING_PART", "TEXT_HASH_MISMATCH", "CONTENT_UID_MISMATCH"):
        assert S.http_status_for(ArtifactRefused(code)) == 400


def test_policy_invalid_must_not_be_400():
    from rag_projection.projection import ProjectionRefused

    assert S.http_status_for(ProjectionRefused("POLICY_INVALID")) != 400


# ---------------------------------------------------------------- Q9 兜底
def test_q9_unknown_code_is_500_and_logged(caplog):
    with caplog.at_level("ERROR"):
        http = S.http_status_for(K.PipelineRefused("SOMETHING_NEW"), kb="kb_9",
                                 artifact_id="a" * 64)
    assert http == 500
    assert "SOMETHING_NEW" in caplog.text, "表外 code 必须把原文写进日志"


def test_q9_none_code_is_500(caplog):
    with caplog.at_level("ERROR"):
        exc = K.PipelineRefused(None, "no code")
        assert S.http_status_for(exc, kb="kb_9") == 500
    assert "None" in caplog.text or "no code" in caplog.text


# ---------------------------------------------------------------- B4 409 走表
def test_b4_source_diverged_maps_to_409():
    assert S.http_status_for(K.SourceDiverged("hash mismatch")) == 409


def test_b4_source_diverged_endpoint_returns_409():
    svc = FakeService(exc=K.SourceDiverged("载荷与图谱 docs 不同源"))
    resp = _client(svc).post("/kb/ingest", json=_body())
    assert resp.status_code == 409, resp.text
    assert "SOURCE_DIVERGED" in resp.json()["msg"]


# ---------------------------------------------------------------- 两个 207 不能混
def test_two_207s_are_distinct():
    partial = FakeService(data={"status": "PARTIAL", "kb": "kb_9", "cursor": "c",
                                "diff": {}, "projection": {"status": "READY"}, "graph": {}})
    r1 = _client(partial).post("/kb/ingest", json=_body())

    community = FakeService(exc=K.PipelineRefused("COMMUNITY_INVALID", "引用校验不通过"))
    r2 = _client(community).post("/kb/ingest", json=_body())

    assert r1.status_code == 207 and r2.status_code == 207
    assert r1.json()["msg"] != r2.json()["msg"], "成功路 PARTIAL 与异常路 COMMUNITY_INVALID 语义不同"
    assert "COMMUNITY_INVALID" in r2.json()["msg"]


# ---------------------------------------------------------------- 契约形状
def test_response_declares_contract_schema():
    svc = FakeService()
    resp = _client(svc).post("/kb/ingest", json=_body())
    assert resp.json()["schema"] == "llmke.kb-ingest.result/1"
    assert resp.json()["code"] == 200


def test_skipped_fresh_is_200_not_207():
    skipped = FakeService(data={"status": "SKIPPED_FRESH", "kb": "kb_9", "cursor": "c",
                                "diff": {"reason": "NO_CHANGE", "diff_source": "request"},
                                "projection": {}, "graph": {}})
    resp = _client(skipped).post("/kb/ingest", json=_body())
    assert resp.status_code == 200, "契约 §1.2：SKIPPED_FRESH 是 200，不是 207"

# ------------------------------------------------ 缺陷 6：runner 必须转发 fallback_reason
def test_delta_runner_forwards_fallback_reason(monkeypatch):
    """18094 的 `DeltaRequest` 校验：`requested_mode=full` 且无 `fallback_reason` → 422。

    `_delta_runner` 原来恒传 `fallback_reason=None`，即使调用方给了值 —— 等于
    「18096 收下了 fallback_reason，却没往下传」，full rebuild 必然 422。
    """
    import types

    seen = {}

    def fake_post(kb, wanted, **kw):
        seen.update({"kb": kb, "wanted": list(wanted), **kw})
        return {"status": "BUILT"}

    monkeypatch.setattr(S.graph_client, "post_graph_delta", fake_post)

    plan = types.SimpleNamespace(
        kb="kb_9", wanted_docs=[{"file_id": "290", "text": "正文"}], removed=[],
        diff={"reason": "FULL_REBUILD_REQUESTED", "set_digest": "d"},
        fallback_reason="SHADOW_BOOTSTRAP")

    S._delta_runner("http://127.0.0.1:18094", "/shadow/graph-root")(plan)

    assert seen["requested_mode"] == "full"
    assert seen["fallback_reason"] == "SHADOW_BOOTSTRAP", (
        f"runner 没把 fallback_reason 传下去（实际 {seen.get('fallback_reason')!r}）→ 18094 会 422")
    assert seen["root"] == "/shadow/graph-root"

# ------------------------------------------------ 缺陷 11：ALL_REVOKED → 422
def test_all_revoked_maps_to_422():
    """删到空库由 `ALL_REVOKED` 表达（契约 §5，调用方动作=人工介入）。"""
    assert S.ERROR_HTTP["ALL_REVOKED"] == 422

# ------------------------------------------------ C5 追加：索引失败在 HTTP 层的如实暴露
def test_index_write_failure_is_502_with_payload_and_no_state_committed():
    """`INDEX_WRITE_FAILED` 走异常路径：502 + `data.index_write`（含 compensation），

    并且 **`data` 里不得出现 `state_committed`** —— 异常路径根本没有「提交/未提交」这个结论，
    若出现 `false` 会让人误读成「本次尝试过提交且失败」，掩盖「压根没进事务」。
    """
    exc = K.PipelineRefused("INDEX_WRITE_FAILED", "es: insert failed")
    exc.payload = {"index_write": {
        "status": "FAILED", "applied": False, "required": True, "side": "es",
        "error": "insert: RuntimeError: injected",
        "deletes": [{"side": "es", "target": "v2cand_kb_9", "col_name": "file_id",
                     "col_values": ["290"]}],
        "compensation": {"needs": False, "completed_sides": [], "calls": []},
    }}
    client = _client(FakeService(exc=exc))

    resp = client.post("/kb/ingest", json=_body())

    assert resp.status_code == 502, resp.text
    body = resp.json()
    assert body["code"] == 502
    data = body.get("data") or {}
    assert data["index_write"]["status"] == "FAILED"
    assert "compensation" in data["index_write"]
    assert "state_committed" not in data, (
        f"异常路径不得伪造 state_committed（实际 data keys={sorted(data)}）")
