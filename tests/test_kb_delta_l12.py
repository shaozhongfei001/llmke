"""P4-L12 · 库级增量 `KbDeltaService`（B1/B2/B3/B8 + Q1/Q2/Q5/Q7）。

为什么这些断言必须在 **v2 主口径** 下真跑：`kb_delta.py` 是编排层，不该依赖
pydantic/fastapi（那两个只有 hipporag 装了，TL Q5）。请求/响应模型的断言在
`test_kb_ingest_l12.py`，只在 hipporag 跑；本文件在**两个解释器**下都必须绿。

阶段 A（实现前）本文件应全红且落在**断言/行为层**：`kb_delta.py` 骨架只抛
`NotImplementedError`，不产生 collection error。
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
IDX_ROOT = REPO_ROOT / "services/rag-alg/index_data_service"
if str(IDX_ROOT) not in sys.path:
    sys.path.insert(0, str(IDX_ROOT))

from ingest_pipeline import index_writer as IW  # noqa: E402
from ingest_pipeline import kb_pipeline as K  # noqa: E402

KB = "kb_9"
FID = "290"
OTHER = "999"
MANIFEST_SCHEMA = "llmke.doc2md.kb-manifest/1"


# ---------------------------------------------------------------- 工具
def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chunk(pk: int, text: str, seq: int = 0):
    return {"pk": pk, "text": text, "seq": seq, "channel": "text",
            "parse_artifact_id": "a" * 64, "content_uid": "b" * 64,
            "locator": {"kind": "text_span", "source": "parsed_text.md",
                        "start_offset": 0, "end_offset": len(text)}}


def _seed_state(tmp_path, monkeypatch, *, files=None, chunks=None,
                version: int = 3, cursor: str = "cursor-old") -> Path:
    """落一份 v2 状态文件，并把 `LLMKE_KB_STATE` 指过去。"""
    state = {
        "schema": K.KB_STATE_SCHEMA, "version": version, "cursor": cursor,
        "set_digest": "digest-old",
        "kb": {KB: files or {}},
        "chunks": {KB: chunks or {}},
        "graph": {KB: {"snapshot": None, "fencing": 0, "mode": "DELTA"}},
    }
    path = tmp_path / "kb-state" / "kb_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("LLMKE_KB_STATE", str(path))
    return path


def _entry(content_hash: str, *, file_name: str = "a.md", status: str = "ACTIVE", **extra):
    return {"artifact_id": "f" * 64, "snapshot": "/snap", "content_uid": "c" * 64,
            "content_hash": content_hash, "file_name": file_name, "status": status,
            "file_path": "/tmp/a.md", "file_size": 10, "source": "kb_9/a.md", **extra}


class Recorder:
    """记录每一次外部动作，用于断言「零调用」与「调用顺序」。"""

    def __init__(self):
        self.events = []
        self.calls = {"commit_snapshot": 0, "project": 0, "build": 0,
                      "revoke": 0, "delta": 0, "wanted": 0, "txn": 0}
        self.fail_on = None
        self.posts = []

    def _hit(self, name):
        self.calls[name] = self.calls.get(name, 0) + 1
        self.events.append(name)
        if self.fail_on == name:
            raise RuntimeError(f"injected failure at {name}")


@pytest.fixture()
def svc(tmp_path, monkeypatch):
    """带全套替身的服务；返回 (service, recorder, state_path)。"""
    from ingest_pipeline import kb_delta as D

    rec = Recorder()

    def commit_snapshot(doc2md_dir, store_root, *, producer_inputs, artifact_id=None):
        rec._hit("commit_snapshot")
        artifact = {"artifact_id": "a" * 64, "content_uid": "b" * 64,
                    "committed_at": "2026-11-08 00:00:00", "quality": {"state": "OK"}}
        return artifact, Path("/snapshot/" + "a" * 64)

    def project_snapshot(snapshot_dir, *, index_name, file_id, chunk_chars=800):
        rec._hit("project")
        chunks = [_chunk(111, "正文块")]

        class R:
            status = "READY"
            stats = {"chunks_text": 1, "chunks_table": 0}
        R.chunks = chunks
        return R()

    def build(chunks, artifact, *, kb, index_prefix=IW.DEFAULT_INDEX_PREFIX, file_id=None):
        rec._hit("build")
        return IW.build(chunks, {**artifact, "file_id": file_id}, kb=kb,
                        index_prefix=index_prefix, file_id=file_id)

    def revoke(file_ids, kb=""):
        rec._hit("revoke")

    def delta(plan_obj):
        rec._hit("delta")
        return {"status": "BUILT"}

    def state_txn():
        rec._hit("txn")
        return K._kb_state_txn("/store-root")

    service = D.KbDeltaService(
        "/store-root",
        state_txn=state_txn,
        es_base="http://es-stub:19527", milvus_base="http://mv-stub:19526",
        commit_snapshot=commit_snapshot,
        project_snapshot=project_snapshot,
        writer=IW,          # 真 index_writer，但 build 被下面替换
        revoke=revoke,
        delta=delta,
    )
    def apply(plan, *, es_url, milvus_url):
        rec._hit("apply")
        rec.posts.append(es_url)

        class R:
            status = "OK"
            side = None
            error = None
            completed_sides = ["es", "milvus"]
            needs_compensation = False
            calls = []
        return R

    # 只替换 build/bind/apply/delete_scope，语义形状与真 index_writer 一致；
    # `poster` 必须注入 —— 否则默认会真的 POST 到线上 19527（红线）
    w = type("W", (), {"build": staticmethod(build),
                       "bind_chunks": staticmethod(IW.bind_chunks),
                       "delete_scope": staticmethod(IW.delete_scope),
                       "apply": staticmethod(apply),
                       "IndexWriterError": IW.IndexWriterError})()
    service._writer = w
    service._poster = lambda url, body: (rec.events.append("post"), rec.posts.append(url))
    return service, rec


def _req(**kw):
    base = {"kb": KB, "file_id": FID, "operation": "UPSERT",
            "doc2md_dir": "/doc2md-out", "index_name": KB,
            "file_name": "a.md", "file_path": "/tmp/a.md", "file_size": 10,
            "source": "kb_9/a.md", "content_hash": _sha("正文块"),
            "producer_inputs": {"source_revision": "r1"},
            "build_graph": True, "requested_mode": "auto"}
    base.update(kw)
    return base


# ---------------------------------------------------------------- B1 空 diff 短路
def test_b1_empty_diff_short_circuits_every_path(tmp_path, monkeypatch, svc):
    service, rec = svc
    _seed_state(tmp_path, monkeypatch,
                files={FID: _entry(_sha("正文块"))},
                chunks={FID: [{"pk": 111, "text": "正文块", "locator": "chunk=0",
                               "channel": "text", "content_hash": _sha("正文块")}]})

    out = service.run(_req())

    assert out["status"] == "SKIPPED_FRESH"
    assert rec.calls["commit_snapshot"] == 0
    assert rec.calls["project"] == 0
    assert rec.calls["build"] == 0
    assert rec.calls["delta"] == 0, "空 diff 不得触发 18094"
    assert rec.events == []


def test_b1_skipped_does_not_advance_cursor_or_version(tmp_path, monkeypatch, svc):
    service, _rec = svc
    path = _seed_state(tmp_path, monkeypatch, files={FID: _entry(_sha("正文块"))})
    before = json.loads(path.read_text(encoding="utf-8"))

    out = service.run(_req())

    after = json.loads(path.read_text(encoding="utf-8"))
    assert out["cursor"] == before["cursor"]
    assert after["version"] == before["version"]
    assert after["cursor"] == before["cursor"]


# ---------------------------------------------------------------- B2 revoke 先于 delta
def test_b2_revoke_precedes_delta(tmp_path, monkeypatch, svc):
    service, rec = svc
    # 留一个存活文件：删到空库现在按契约 §5 走 ALL_REVOKED（零副作用拒绝），
    # 本用例验的是「非空库删除」时 revoke 早于 delta。
    _seed_state(tmp_path, monkeypatch,
                files={FID: _entry(_sha("正文块")), OTHER: _entry(_sha("旧块"))},
                chunks={FID: [{"pk": 111, "text": "正文块", "locator": "chunk=0",
                               "channel": "text", "content_hash": _sha("正文块")}]})

    out = service.run(_req(operation="DELETE", file_id=OTHER, content_hash=None))

    assert rec.calls["revoke"] == 1
    assert rec.calls["delta"] == 1
    assert rec.events.index("revoke") < rec.events.index("delta"), rec.events
    assert out["diff"]["removed"] == [OTHER]


def test_b2_revoked_file_absent_from_wanted_docs(tmp_path, monkeypatch, svc):
    service, _rec = svc
    _seed_state(tmp_path, monkeypatch,
                files={FID: _entry(_sha("正文块")), OTHER: _entry(_sha("旧块"), file_name="old.md")},
                chunks={FID: [{"pk": 111, "text": "正文块", "locator": "chunk=0",
                               "channel": "text", "content_hash": _sha("正文块")}],
                        OTHER: [{"pk": 222, "text": "旧块", "locator": "chunk=0",
                                 "channel": "text", "content_hash": _sha("旧块")}]})

    out = service.run(_req(operation="DELETE", file_id=OTHER, content_hash=None))

    fids = {d["file_id"] for d in out["wanted_docs"]}
    assert OTHER not in fids, "撤权文件不得出现在 delta 的 wanted docs 里"
    state = json.loads(Path(out["state_path"]).read_text(encoding="utf-8"))
    assert state["kb"][KB][OTHER]["status"] == "REVOKED"
    assert state["kb"][KB][OTHER]["revoked_at"]


# ---------------------------------------------------------------- B3 三路成功才推 cursor
@pytest.mark.parametrize("broken", ["commit_snapshot", "project", "build"])
def test_b3_any_path_failure_does_not_advance_cursor(tmp_path, monkeypatch, svc, broken):
    service, rec = svc
    path = _seed_state(tmp_path, monkeypatch, files={})
    before = json.loads(path.read_text(encoding="utf-8"))
    rec.fail_on = broken

    # 必须命中**注入的**故障：用 Exception 会把 NotImplementedError 也算通过（空转假绿）
    with pytest.raises(RuntimeError, match=f"injected failure at {broken}"):
        service.run(_req())

    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["version"] == before["version"], f"{broken} 失败后 cursor/version 不得推进"
    assert after["cursor"] == before["cursor"]
    assert after["kb"][KB] == {}, "失败不得留下半提交状态"


def test_b3_replay_after_failure_runs_full_plan(tmp_path, monkeypatch, svc):
    service, rec = svc
    _seed_state(tmp_path, monkeypatch, files={})
    rec.fail_on = "project"
    with pytest.raises(RuntimeError, match="injected failure at project"):
        service.run(_req())

    rec.fail_on = None          # 故障恢复后重放同一请求
    out = service.run(_req())
    # A 段（L13-A1）已接线真实写入 → applied=True、可报 OK。
    # L12 当时的 `applied is False / PARTIAL` 是"未接线"的**诚实占位**，已被取代。
    assert out["status"] == "OK"
    assert out["index_write"]["applied"] is True
    assert out["diff"]["added"] == [FID]


# ---------------------------------------------------------------- B8 wanted docs 不重投影
def test_b8_wanted_docs_read_state_without_reprojecting(tmp_path, monkeypatch, svc):
    service, rec = svc
    _seed_state(tmp_path, monkeypatch,
                files={FID: _entry(_sha("正文块"))},
                chunks={FID: [{"pk": 111, "text": "正文块", "locator": "chunk=0",
                               "channel": "text", "content_hash": _sha("正文块"),
                               "parse_artifact_id": "a" * 64}]})

    docs = service.wanted_docs(KB)

    assert rec.calls["project"] == 0, "组装 wanted docs 不得重新投影"
    assert [d["text"] for d in docs] == ["正文块"]
    assert docs[0]["locator"] == "chunk=0"
    assert docs[0]["parse_artifact_id"] == "a" * 64


def test_b8_wanted_docs_skip_non_active_files(tmp_path, monkeypatch, svc):
    service, _rec = svc
    _seed_state(tmp_path, monkeypatch,
                files={FID: _entry(_sha("正文块")),
                       OTHER: _entry(_sha("旧块"), status="REVOKED")},
                chunks={FID: [{"pk": 1, "text": "正文块", "locator": "chunk=0"}],
                        OTHER: [{"pk": 2, "text": "旧块", "locator": "chunk=0"}]})

    docs = service.wanted_docs(KB)
    assert {d["file_id"] for d in docs} == {FID}


# ---------------------------------------------------------------- Q1 diff_source
def test_q1_diff_source_is_request_without_manifest(tmp_path, monkeypatch, svc):
    service, _rec = svc
    _seed_state(tmp_path, monkeypatch, files={})
    diff = service.diff(KB, None, file_id=FID, operation="UPSERT")
    assert diff["diff_source"] == "request"
    assert diff["removed"] == [], "无 manifest 时 removed 恒空（数据来源决定，不是 bug）"
    assert diff["schema"] == "llmke.kb-diff/1"


def test_q1_manifest_path_enables_full_file_set_diff(tmp_path, monkeypatch, svc):
    service, _rec = svc
    _seed_state(tmp_path, monkeypatch, files={FID: _entry(_sha("正文块"))})
    manifest = tmp_path / "kb-manifest.json"
    manifest.write_text(json.dumps({
        "schema": MANIFEST_SCHEMA, "kb": KB, "cursor": "c1", "set_digest": "d1",
        "parser_fingerprint": "fp-1",
        "entries": [{"file_id": "330", "sha256": _sha("新块"), "status": "ACTIVE"}],
    }), encoding="utf-8")

    diff = service.diff(KB, manifest)

    assert diff["diff_source"] == "manifest"
    assert diff["added"] == ["330"]
    assert diff["removed"] == [FID], "manifest 才是 removed 的真实来源"


def test_q1_bad_manifest_schema_is_refused(tmp_path, monkeypatch, svc):
    from ingest_pipeline import kb_delta as D

    service, _rec = svc
    _seed_state(tmp_path, monkeypatch, files={})
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "llmke.doc2md.kb-manifest/999", "entries": []}),
                   encoding="utf-8")
    with pytest.raises(D.KbDeltaRefused) as exc:
        service.diff(KB, bad)
    assert exc.value.code == "DOC2MD_ARTIFACT_INCOMPLETE"


def test_q1_reason_priority_full_rebuild_wins(tmp_path, monkeypatch, svc):
    service, _rec = svc
    _seed_state(tmp_path, monkeypatch, files={FID: _entry(_sha("正文块"))})
    diff = service.diff(KB, None, file_id=FID, operation="UPSERT",
                        full_rebuild=True, content_hash=_sha("正文块"))
    assert diff["reason"] == "FULL_REBUILD_REQUESTED"


def test_q1_reason_no_change_when_identical(tmp_path, monkeypatch, svc):
    service, _rec = svc
    _seed_state(tmp_path, monkeypatch, files={FID: _entry(_sha("正文块"))})
    diff = service.diff(KB, None, file_id=FID, operation="UPSERT",
                        content_hash=_sha("正文块"))
    assert diff["reason"] == "NO_CHANGE"
    assert diff["added"] == diff["changed"] == diff["removed"] == []


# ---------------------------------------------------------------- Q2 IngestPlan 内部
def test_q2_ingest_plan_is_internal_dataclass(tmp_path):
    from ingest_pipeline import kb_delta as D

    assert is_dataclass(D.IngestPlan)
    assert not hasattr(D.IngestPlan, "model_fields"), "IngestPlan 不得是 Pydantic 模型"
    names = {f.name for f in fields(D.IngestPlan)}
    # 这些是编排中间产物，**不得**成为响应字段（见 hipporag 侧的响应模型断言）
    assert {"write_plan", "wanted_docs", "chunks"} <= names


# ---------------------------------------------------------------- Q5 无 pydantic/fastapi
def test_q5_kb_delta_does_not_import_web_frameworks():
    src = (IDX_ROOT / "ingest_pipeline" / "kb_delta.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    banned = {"pydantic", "fastapi", "starlette"}
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [a.name.split(".")[0] for a in node.names if a.name.split(".")[0] in banned]
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in banned:
                found.append(root)
    assert found == [], f"kb_delta.py 不得 import {sorted(banned)}（v2 环境没有它们）: {found}"


# ---------------------------------------------------------------- Q7 additive 字段
def test_q7_reading_state_does_not_bump_version(tmp_path, monkeypatch, svc):
    service, _rec = svc
    path = _seed_state(tmp_path, monkeypatch, files={FID: _entry(_sha("正文块"))}, version=7)
    before = json.loads(path.read_text(encoding="utf-8"))

    service.wanted_docs(KB)          # 纯读
    service.diff(KB, None, file_id=FID)

    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["version"] == before["version"] == 7
    assert after["cursor"] == before["cursor"]


def test_q7_old_state_without_new_fields_still_loads(tmp_path, monkeypatch, svc):
    """旧 state 的 entry 没有 `parser_fingerprint` / `revoked_at` —— 按默认值兼容。"""
    service, _rec = svc
    _seed_state(tmp_path, monkeypatch,
                files={FID: {"content_hash": _sha("正文块"), "status": "ACTIVE"}},
                chunks={FID: [{"pk": 1, "text": "正文块", "locator": "chunk=0"}]})
    diff = service.diff(KB, None, file_id=FID, content_hash=_sha("正文块"))
    assert diff["reason"] == "NO_CHANGE"
    assert service.wanted_docs(KB)[0]["text"] == "正文块"

# ------------------------------------------------ B3 修正 · delta 必须在事务之前
def test_b3_delta_runs_before_state_commit(tmp_path, monkeypatch, svc):
    """顺序：revoke → delta → txn。delta 若在 txn 之后就等于「已提交但图没建」。"""
    service, rec = svc
    _seed_state(tmp_path, monkeypatch,
                files={FID: _entry(_sha("正文块")), OTHER: _entry(_sha("旧块"))},
                chunks={FID: [{"pk": 111, "text": "正文块", "locator": "chunk=0",
                               "channel": "text", "content_hash": _sha("正文块")}]})

    service.run(_req(operation="DELETE", file_id=OTHER, content_hash=None))

    assert "delta" in rec.events and "txn" in rec.events, rec.events
    assert rec.events.index("delta") < rec.events.index("txn"), \
        f"delta 必须在状态事务之前（实际顺序 {rec.events}）"
    assert rec.events.index("revoke") < rec.events.index("delta"), rec.events


def test_b3_delta_failure_does_not_advance_cursor(tmp_path, monkeypatch, svc):
    """delta 失败 → cursor/version 不推进；重放仍能走完整 plan（否则图永远建不起来）。"""
    service, rec = svc
    path = _seed_state(tmp_path, monkeypatch, files={})
    before = json.loads(path.read_text(encoding="utf-8"))

    def boom(_plan):
        rec._hit("delta")
        raise K.PipelineRefused("GRAPH_UNREACHABLE", "18094 不可达")

    service._delta = boom
    out = service.run(_req())

    after = json.loads(path.read_text(encoding="utf-8"))
    assert out["status"] == "PARTIAL"
    assert "GRAPH_UNREACHABLE" in out["graph"]["error"]
    assert out["state_committed"] is False
    assert after["version"] == before["version"], "delta 失败不得推进 cursor"
    assert after["cursor"] == before["cursor"]
    assert after["kb"][KB] == {}, "delta 失败不得留下已提交状态"

    # 重放：diff 仍看到 added（因为状态没落），所以还能再跑一次完整 plan
    service._delta = lambda p: {"status": "BUILT"}
    replay = service.run(_req())
    assert replay["diff"]["added"] == [FID], "状态没落 → 重放不能变成 SKIPPED_FRESH"


def test_no_delta_runner_is_not_ok(tmp_path, monkeypatch, svc):
    """漏配 delta runner 不得静默报 OK（否则「成功但无图」）。"""
    service, _rec = svc
    path = _seed_state(tmp_path, monkeypatch, files={})
    before = json.loads(path.read_text(encoding="utf-8"))
    service._delta = None

    out = service.run(_req())

    assert out["status"] == "PARTIAL", "没有 delta runner 不能算三路成功"
    assert "delta_runner_not_configured" in (out["graph"]["error"] or "")
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["version"] == before["version"]


# ------------------------------------------------ ES/Milvus 未写入必须如实暴露
def test_index_write_reports_applied_after_l13_wiring(tmp_path, monkeypatch, svc):
    """L12 时这里断言 `PLANNED/applied=False`（未接线的诚实占位）；
    L13-A1 接线后改为断言 `APPLIED/applied=True` —— 同一位置、语义随事实更新。"""
    service, _rec = svc
    _seed_state(tmp_path, monkeypatch, files={})

    out = service.run(_req())

    block = out["index_write"]
    assert block["status"] == "APPLIED"
    assert block["applied"] is True
    assert block["required"] is True


def test_status_must_not_be_ok_when_compensation_needed(tmp_path, monkeypatch, svc):
    """A 段改写：`applied=False` ⇒ 不再报 OK 这条规则由 L13-A3 覆盖；
    这里保留同一位置的等价规则 —— **需要补偿时不得报 OK**。"""
    from ingest_pipeline import kb_delta as D

    service, _rec = svc
    plan = D.IngestPlan(kb=KB, diff={"reason": "FILE_SET_CHANGED"}, diff_source="request")
    out = service._result(
        plan, status=None, cursor="c", wanted=[], graph_result={"status": "BUILT"},
        graph_error=None,
        index_write={"status": "APPLIED", "applied": True, "required": True,
                     "compensation": {"needs": True, "completed_sides": ["es"], "calls": []}},
        state_committed=True)
    assert out["status"] != "OK"

# ------------------------------------------------ 缺陷 6：plan 必须携带 fallback_reason
def test_plan_carries_fallback_reason(tmp_path, monkeypatch, svc):
    """`operation=FULL_REBUILD` 时 18094 要求 `requested_mode=full` **必须**带 fallback_reason，
    否则 422 `value_error`（禁止静默走全量）。所以 plan 必须把请求里的值带下去。"""
    service, _rec = svc
    _seed_state(tmp_path, monkeypatch, files={})

    plan = service.plan(_req(operation="FULL_REBUILD", fallback_reason="SHADOW_BOOTSTRAP"))

    assert plan.diff["reason"] == "FULL_REBUILD_REQUESTED"
    assert plan.fallback_reason == "SHADOW_BOOTSTRAP", (
        "plan 丢了 fallback_reason → runner 只能传 None → 18094 必 422")

# ------------------------------------------------ 缺陷 11：删到空库必须零副作用拒绝
def test_delete_last_file_is_all_revoked_with_zero_side_effects(tmp_path, monkeypatch, svc):
    """删掉库里**最后一个文件** → `ALL_REVOKED`，且**零副作用**：

    - 不发撤权（否则 fence.json 已被写）；
    - 不删索引（否则索引与未提交状态不一致 —— 这正是 TL 20:2x 指出的顺序问题）；
    - 状态 version 不变。

    为什么拒而不是「清空图」：契约 §5 用 `ALL_REVOKED` 表达「全撤权需人工介入」，
    且 `rebuild` 两处都明确拒绝生成空快照（`rebuild.py:132-133 / :270-271`）。
    """
    service, rec = svc
    path = _seed_state(tmp_path, monkeypatch, files={FID: _entry(_sha("旧块"))})

    from ingest_pipeline import kb_delta as D

    with pytest.raises(D.KbDeltaRefused) as ei:
        service.run(_req(operation="DELETE"))

    assert ei.value.code == "ALL_REVOKED", ei.value.code
    assert "revoke" not in rec.events, f"撤权不得发出（副作用已发生）：{rec.events}"
    assert "build" not in rec.events, f"索引不得被删/写：{rec.events}"
    assert rec.calls["txn"] == 0, "状态事务不得进入"
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 3, "state version 不得变"


def test_delete_non_last_file_writes_and_reports_index_block(tmp_path, monkeypatch, svc):
    """删「非最后一个」→ 正常建图，并且 `index_write` 块如实说明索引动作（TL 采纳 (c) 的一半）。"""
    service, rec = svc
    _seed_state(tmp_path, monkeypatch,
                files={FID: _entry(_sha("旧块")), OTHER: _entry(_sha("另一块"))},
                chunks={FID: [{"pk": 111, "text": "旧块", "locator": "chunk=0",
                               "channel": "text", "content_hash": _sha("旧块")}]})

    out = service.run(_req(operation="DELETE", file_id=OTHER, content_hash=None))

    assert out["status"] == "OK", out
    block = out["index_write"]
    assert block["applied"] is True
    assert block["mode"] == "DELETE", f"DELETE 要标出模式，实际 {block.get('mode')}"
    assert len(block["deletes"]) == 4, f"4 个 target 都要删：{block['deletes']}"
    assert block.get("inserts") is None, "DELETE 不写新块，inserts 必须是 None（不能报 OK 冒充插入）"
    assert "revoke" in rec.events, "非空库删除应发撤权"
