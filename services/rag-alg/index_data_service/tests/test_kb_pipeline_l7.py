"""P2-L7 · T-D2MD-07 反例与断言（`P2-L7-PLAN.md` §三，TL 12:0x 裁定）。

G1 `consume_for_kb` 接 `index_writer.build` 且 `file_id` 必须真实（禁回落 `kb`）
G2 `assert_same_artifact` 成生产闸门，不一致时三路 0 写入
G3 `kb_state.json` v2 持久化（绝对路径 / flock / 原子替换 / 损坏抛错 / 并发不丢写）
G4 `consume_for_kb` 不再遍历全库重建图谱（改返回 wanted docs 引用）
G5 不写线上 / 行为等价性

R-1~R-6 为对应反例。**离线**：monkeypatch 掉 `commit_snapshot` / `project_snapshot` /
`post_graph_build` / `index_writer.apply`，不读写线上 ES(19527) / Milvus(19526) / DB /
18094、不启停服务、不切 `INGEST_PROJECTION_MODE`。

刻意约定
--------
本文件在阶段 A（实现前）必须 **全部 FAIL 于断言/执行层**，而不是 collection 层：
新符号（`KB_STATE_SCHEMA` / `SourceDiverged` / `build_wanted_docs` / `_kb_state_txn` /
`build(..., file_id=)`）一律在用例体内用 `getattr` 取，避免「导入即报错」掩盖判别力。
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/rag-alg/index_data_service"))

from graph_engine_adapter.artifact_binding import (  # noqa: E402
    ArtifactBindingError,
    assert_same_artifact,
)
from ingest_pipeline import index_writer as IW  # noqa: E402
from ingest_pipeline import kb_pipeline as K  # noqa: E402
from rag_projection import projection as P  # noqa: E402

ART_ID = "c" * 64
UID = "d" * 64
KB = "kb_9"
REPO_ROOT = ROOT
_STORE_ROOT = "/store-root"  # 由 _wire 改写到 tmp_path，避免测试在根目录落盘


# --------------------------------------------------------------------------- helpers
def _chunks(tag: str = "") -> list:
    """P.project 的产物形状（text + table 各一条）。"""
    return [
        {"seq": 0, "channel": "text", "pk": 111, "text": f"说明如下。{tag}",
         "locator": {"kind": "text_span", "source": "parsed_text.md",
                     "start_offset": 0, "end_offset": 5},
         "parse_artifact_id": ART_ID, "content_uid": UID},
        {"seq": 1, "channel": "table", "pk": 222,
         "text": f"指标 | 值\n日均存款 | 100{tag}",
         "locator": {"kind": "table_ref", "table_id": "t001", "block_id": "b0002"},
         "parse_artifact_id": ART_ID, "content_uid": UID, "rows": 2, "cols": 2},
    ]


def _artifact(*, with_file_id: bool = False) -> dict:
    """`store.commit()` 的 artifact 形状：**真实产物不含 file_id**（L6 判断①）。"""
    art = {"schema_version": "llmke-parse-artifact/2.0",
           "artifact_id": ART_ID, "content_uid": UID,
           "committed_at": "2026-11-08 00:00:00"}
    if with_file_id:
        art["file_id"] = "333"
    return art


def _wire(monkeypatch, tmp_path, *, chunks: list | None = None, calls: dict | None = None):
    """把 `consume_for_kb` 的外部依赖全部替换为可观测替身（不触盘、不联网）。"""
    calls = calls if calls is not None else {}
    calls.setdefault("project", 0)
    calls.setdefault("graph", [])
    calls.setdefault("apply", [])
    data = chunks if chunks is not None else _chunks()
    snapshot = tmp_path / "snap"
    snapshot.mkdir(exist_ok=True)

    def fake_commit(doc2md_dir, store_root, *, producer_inputs, artifact_id=None):
        return _artifact(), snapshot

    def fake_project(snapshot_dir, *, index_name, file_id, chunk_chars=800):
        calls["project"] += 1
        return SimpleNamespace(status="APPLICABLE", mode="snapshot", chunks=list(data),
                               stats={"chunks_text": 1, "chunks_table": 1}, refusals=[])

    def fake_graph(kb, docs, **kwargs):
        calls["graph"].append({"kb": kb, "docs": len(docs)})
        return {"status": "BUILT"}

    def fake_apply(plan, **kwargs):
        calls["apply"].append(plan)
        return SimpleNamespace(status="OK")

    monkeypatch.setattr(K, "commit_snapshot", fake_commit)
    monkeypatch.setattr(K, "project_snapshot", fake_project)
    monkeypatch.setattr(K, "post_graph_build", fake_graph)
    monkeypatch.setattr(IW, "apply", fake_apply)
    state_path = tmp_path / "kb-state" / "kb_state.json"
    monkeypatch.setenv("LLMKE_KB_STATE", str(state_path))
    global _STORE_ROOT
    _STORE_ROOT = str(tmp_path / "store")
    return calls, state_path


def _consume(**kwargs):
    params = dict(kb=KB, file_id="333", producer_inputs={"source_revision": "r1"},
                  index_name=KB, file_name="a.md", file_path="/tmp/a.md",
                  file_size=10, source="kb_9/a.md", build_graph=True)
    params.update(kwargs)
    return K.consume_for_kb("/doc2md-out", _STORE_ROOT, **params)


# --------------------------------------------------------------------------- G1 / R-1
def test_g1_build_requires_real_file_id_no_kb_fallback() -> None:
    """R-1：artifact 无 file_id 且未传参 → FILE_ID_MISSING，**不得回落 `kb`**。"""
    with pytest.raises(IW.IndexWriterError) as exc:
        IW.build(_chunks(), _artifact(), kb=KB)
    assert exc.value.code == "FILE_ID_MISSING"


def test_g1_build_accepts_injected_file_id() -> None:
    plan = IW.build(_chunks(), _artifact(), kb=KB, file_id="333")
    metas = [d["metadata"] for b in plan.es_plan + plan.milvus_plan
             for d in b["document_list"]]
    assert metas and all(m["file_id"] == "333" for m in metas)
    # 注入值与 kb 不同，防止「回落 kb」伪装通过
    assert all(m["file_id"] != KB for m in metas)


def test_g1_build_prefers_explicit_over_artifact() -> None:
    """:param file_id 优先于 artifact['file_id']。"""
    plan = IW.build(_chunks(), _artifact(with_file_id=True), kb=KB, file_id="999")
    metas = [d["metadata"] for b in plan.es_plan for d in b["document_list"]]
    assert metas and all(m["file_id"] == "999" for m in metas)


def test_g1_consume_rejects_missing_file_id(monkeypatch, tmp_path) -> None:
    """R-1：`consume_for_kb` 缺真实 file_id → fail-closed，不得静默用 kb。"""
    calls, state_path = _wire(monkeypatch, tmp_path)
    with pytest.raises(K.PipelineRefused) as exc:
        _consume(file_id=None)
    assert exc.value.code == "FILE_ID_MISSING"
    assert not state_path.is_file()  # 拒绝即止，不留半成品状态


# --------------------------------------------------------------------------- G2 / R-2
def test_g2_source_diverged_blocks_all_writes(monkeypatch, tmp_path) -> None:
    """R-2：ES 侧 `content_hash` 改一位 → SOURCE_DIVERGED 且四路 0 写入。"""
    calls, state_path = _wire(monkeypatch, tmp_path)
    real_build = IW.build

    def diverged_build(chunks, artifact, **kwargs):
        import dataclasses

        plan = real_build(chunks, artifact, **kwargs)
        tampered = dict(plan.binding)
        tampered["content_hash"] = ("0" if plan.content_hash[0] != "0" else "1") \
            + plan.content_hash[1:]
        return dataclasses.replace(plan, binding=tampered,
                                   content_hash=tampered["content_hash"])

    monkeypatch.setattr(K.index_writer, "build", diverged_build)

    with pytest.raises(Exception) as exc:
        _consume()
    assert getattr(exc.value, "code", None) == "SOURCE_DIVERGED"
    # 「不一致时三路都不写」——ES/Milvus 计划未落地、图未建、状态未落盘
    assert calls["graph"] == []
    assert calls["apply"] == []
    assert not state_path.is_file()


def test_g2_gate_is_wired_not_noop(monkeypatch, tmp_path) -> None:
    """闸门必须真的被调用（变异：删掉调用点应让本断言 FAIL）。"""
    calls, _ = _wire(monkeypatch, tmp_path)
    seen = []
    real_assert = assert_same_artifact

    def spy(a, b):
        seen.append((a.get("content_hash"), b.get("content_hash")))
        return real_assert(a, b)

    monkeypatch.setattr(K, "assert_same_artifact", spy)
    _consume()
    assert len(seen) == 1 and seen[0][0] == seen[0][1]


def test_g2_divergence_is_artifact_binding_error_too() -> None:
    """`SourceDiverged` 同时是 `PipelineRefused` 与 `ArtifactBindingError`。"""
    cls = getattr(K, "SourceDiverged")
    assert issubclass(cls, K.PipelineRefused)
    assert issubclass(cls, ArtifactBindingError)


# --------------------------------------------------------------------------- G3 / R-3
def test_g3_state_has_v2_schema_and_fields(monkeypatch, tmp_path) -> None:
    _, state_path = _wire(monkeypatch, tmp_path)
    _consume()
    doc = json.loads(state_path.read_text(encoding="utf-8"))
    assert doc["schema"] == getattr(K, "KB_STATE_SCHEMA") == "llmke.kb-state/2"
    for key in ("version", "cursor", "set_digest", "kb", "chunks", "graph"):
        assert key in doc, f"契约 §4.2 要求的 {key} 缺失"
    entry = doc["kb"][KB]["333"]
    for key in ("artifact_id", "snapshot", "content_uid", "content_hash",
                "file_name", "status"):
        assert key in entry, f"kb 条目缺 {key}"
    assert entry["status"] == "ACTIVE"
    assert entry["content_uid"] == UID
    chunk = doc["chunks"][KB]["333"][0]
    for key in ("pk", "text", "locator", "channel", "content_hash"):
        assert key in chunk, f"chunks 条目缺 {key}"
    assert isinstance(chunk["locator"], str) and chunk["locator"].startswith("chunk=")


def test_g3_default_path_is_absolute_under_repo_root(monkeypatch) -> None:
    """TL 裁定 2：基准用 `parents[4]`；并锚定「该目录下 platform/ 与 docs/v2-tasks/ 都在」。"""
    monkeypatch.delenv("LLMKE_KB_STATE", raising=False)
    path = K._kb_state_path()
    assert path.is_absolute()
    assert path == REPO_ROOT / "platform/r12/data/kb-state/kb_state.json"
    # parents: 0=kb-state 1=data 2=r12 3=platform 4=仓根
    repo = path.parents[4]
    assert repo == REPO_ROOT
    assert (repo / "platform").is_dir()
    assert (repo / "docs/v2-tasks").is_dir()


def test_g3_env_path_wins_and_must_be_absolute(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLMKE_KB_STATE", str(tmp_path / "s.json"))
    assert K._kb_state_path() == tmp_path / "s.json"
    monkeypatch.setenv("LLMKE_KB_STATE", "relative/s.json")
    with pytest.raises(K.PipelineRefused) as exc:
        K._kb_state_path()
    assert exc.value.code == "KB_STATE_PATH_NOT_ABSOLUTE"


def test_g3_corrupt_state_raises_instead_of_empty(monkeypatch, tmp_path) -> None:
    """R-3：损坏 → `KB_STATE_CORRUPT`，**禁止静默返回 `{}`**（否则按空库重建）。"""
    state_path = tmp_path / "kb_state.json"
    state_path.write_text("{ this is not json", encoding="utf-8")
    monkeypatch.setenv("LLMKE_KB_STATE", str(state_path))
    with pytest.raises(K.PipelineRefused) as exc:
        K._load_kb_state()
    assert exc.value.code == "KB_STATE_CORRUPT"


def test_g3_wrong_schema_raises(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "kb_state.json"
    state_path.write_text(json.dumps({"schema": "llmke.kb-state/1", "kb": {}}),
                          encoding="utf-8")
    monkeypatch.setenv("LLMKE_KB_STATE", str(state_path))
    with pytest.raises(K.PipelineRefused) as exc:
        K._load_kb_state()
    assert exc.value.code == "KB_STATE_CORRUPT"


def test_g3_save_is_atomic_without_fixed_tmp_residue(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "kb_state.json"
    monkeypatch.setenv("LLMKE_KB_STATE", str(state_path))
    K._save_kb_state(K._empty_kb_state())
    files = sorted(p.name for p in tmp_path.iterdir())
    assert files == ["kb_state.json"]  # 固定 `.json.tmp` 残留即 FAIL
    assert json.loads(state_path.read_text(encoding="utf-8"))["schema"] == \
        getattr(K, "KB_STATE_SCHEMA")


def test_g3_concurrent_writers_do_not_lose_updates(monkeypatch, tmp_path) -> None:
    """R-4：两个写者并发 → 串行化、无丢更新。"""
    state_path = tmp_path / "kb_state.json"
    monkeypatch.setenv("LLMKE_KB_STATE", str(state_path))
    errors: list = []

    def writer(name: str) -> None:
        try:
            with K._kb_state_txn() as state:
                time.sleep(0.15)  # 放大竞态窗口：无锁时后写者必丢前者
                state["kb"].setdefault(KB, {})[name] = {"status": "ACTIVE"}
        except Exception as exc:  # noqa: BLE001 - 失败要看见
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(n,)) for n in ("A", "B")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    doc = json.loads(state_path.read_text(encoding="utf-8"))
    assert set(doc["kb"][KB]) == {"A", "B"}  # 丢任一 → FAIL
    assert doc["version"] >= 2


def test_g3_round_trip_verification_rejects_incomplete(monkeypatch, tmp_path) -> None:
    """裁定 3：迁移/写入后 round-trip 校验；缺 `set_digest` 必须 `KB_STATE_CORRUPT`。"""
    state_path = tmp_path / "kb_state.json"
    monkeypatch.setenv("LLMKE_KB_STATE", str(state_path))

    def bad_save(state, *args, **kwargs):
        broken = dict(state)
        broken.pop("set_digest", None)
        state_path.write_text(json.dumps(broken), encoding="utf-8")

    monkeypatch.setattr(K, "_save_kb_state", bad_save)
    with pytest.raises(K.PipelineRefused) as exc:
        with K._kb_state_txn() as state:
            state["kb"].setdefault(KB, {})["A"] = {"status": "ACTIVE"}
    assert exc.value.code == "KB_STATE_CORRUPT"


# --------------------------------------------------------------------------- G3 · v1 迁移
def test_g3_v1_migration_keeps_backup(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "kb_state.json"
    v1 = {KB: {"290": {"artifact_id": ART_ID, "snapshot": "/abs/snap", "file_name": "a.md"}}}
    state_path.write_text(json.dumps(v1), encoding="utf-8")
    monkeypatch.setenv("LLMKE_KB_STATE", str(state_path))

    state = K._load_kb_state()
    assert state["schema"] == getattr(K, "KB_STATE_SCHEMA")
    assert state["kb"][KB]["290"]["artifact_id"] == ART_ID  # v1 内容不丢
    bak = state_path.with_suffix(".json.v1.bak")
    assert bak.is_file() and json.loads(bak.read_text(encoding="utf-8")) == v1


def test_g3_v1_backup_never_overwrites_existing(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "kb_state.json"
    v1 = {KB: {"290": {"artifact_id": ART_ID}}}
    state_path.write_text(json.dumps(v1), encoding="utf-8")
    old = state_path.with_suffix(".json.v1.bak")
    old.write_text('{"historical": true}', encoding="utf-8")
    monkeypatch.setenv("LLMKE_KB_STATE", str(state_path))

    K._load_kb_state()
    assert json.loads(old.read_text(encoding="utf-8")) == {"historical": True}  # 不覆盖
    backups = [p.name for p in tmp_path.iterdir() if ".v1.bak." in p.name]
    assert len(backups) == 1 and backups[0].startswith("kb_state.json.v1.bak.")


# --------------------------------------------------------------------------- G4 / R-5
def test_g4_no_full_library_graph_rebuild(monkeypatch, tmp_path) -> None:
    """R-5：第二次摄取不得重投影历史文件、不得全库建图。"""
    calls, _ = _wire(monkeypatch, tmp_path)
    _consume(file_id="A")
    _consume(file_id="B")
    assert calls["project"] == 2      # 每次只投影本次文件（历史文件不重投影）
    assert calls["graph"] == []       # 绝不调用 post_graph_build（全库重建）
    assert calls["apply"] == []       # 不写线上 ES / Milvus


def test_g4_returns_wanted_docs_references(monkeypatch, tmp_path) -> None:
    _, _ = _wire(monkeypatch, tmp_path)
    _consume(file_id="A")
    result = _consume(file_id="B")
    graph = result["graph"]
    assert graph["requested"] is True
    assert graph["deferred"] is True
    assert graph["result"] is None
    assert graph["error"] and graph["error"].startswith("GRAPH_REBUILD_DEFERRED")
    # 每次都只有 2 个块：A + B = 4（引用，不重建）
    assert graph["docs"] == 4
    assert {f["file_id"] for f in graph["files"]} == {"A", "B"}
    assert result["status"] == "PARTIAL"  # 不谎报图谱已建好


def test_g4_wanted_docs_helper_shape(monkeypatch, tmp_path) -> None:
    _, _ = _wire(monkeypatch, tmp_path)
    _consume(file_id="A")
    state = K._load_kb_state()
    docs = K.build_wanted_docs(state, KB)
    assert len(docs) == 2
    assert {d["file_id"] for d in docs} == {"A"}
    for doc in docs:
        assert set(doc) >= {"file_id", "text", "locator", "pk"}
        assert isinstance(doc["locator"], str)


# --------------------------------------------------------------------------- G5 · 行为等价
def test_g5_return_shape_unchanged_and_build_graph_false(monkeypatch, tmp_path) -> None:
    calls, _ = _wire(monkeypatch, tmp_path)
    result = _consume(build_graph=False)
    # 与 L7 之前的返回键集合**逐字相同**（含 doc2md_dir）
    assert set(result) == {"status", "kb", "artifact_id", "content_uid",
                           "artifact_quality", "snapshot", "projection", "graph",
                           "doc2md_dir"}
    assert set(result["projection"]) == {"status", "chunks", "channels", "counts",
                                         "payloads"}
    assert set(result["graph"]) == {"requested", "docs", "files", "result", "error",
                                    "deferred"}
    assert result["status"] == "OK"       # 未请求建图 → 不该是 PARTIAL
    assert result["graph"]["deferred"] is False
    assert calls["graph"] == []


def test_g5_partial_payloads_and_counts(monkeypatch, tmp_path) -> None:
    _, _ = _wire(monkeypatch, tmp_path)
    result = _consume()
    proj = result["projection"]
    assert proj["chunks"] == 2 and proj["payloads"]
    assert proj["counts"].get("kb_9") == 1
    assert proj["counts"].get("table_chunks_kb_9") == 1


def test_g5_reingest_same_content_does_not_bump_version(monkeypatch, tmp_path) -> None:
    _, state_path = _wire(monkeypatch, tmp_path)
    _consume()
    first = json.loads(state_path.read_text(encoding="utf-8"))["version"]
    _consume()
    second = json.loads(state_path.read_text(encoding="utf-8"))["version"]
    assert first == second  # 同内容重摄取 = 幂等，不推进 version/cursor


def test_r6_protected_regions_untouched() -> None:
    """R-6 哨兵：禁改区（L5 `_table_pk` / `table_summary_id`）语义不变。"""
    assert P._table_pk("kb_9", "333", 0) == 885155839145947657
    assert callable(K.build_index_payloads) and callable(K.consume)
    assert os.path.basename(str(Path(K.__file__))) == "kb_pipeline.py"
