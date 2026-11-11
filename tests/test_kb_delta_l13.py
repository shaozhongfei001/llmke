"""P4-L13-A · 写入接线（insert + delete）与删除防护（A1~A4、A6）。

为什么 A 段必须把 delete 一起接上：`index_writer.apply` 只发 insert；
19527 的写后剪枝只在 `duplicate_flag=True` 时执行，而 L6 硬约束是 False。
只接 insert ⇒ 文件变小/块减少时旧块留在 ES/Milvus，**检索会命中已删内容**，
且接口一路 200 —— 这是**静默错误**，比 L12 的「恒 207」更严重。

**只在 v2 主口径跑**：`kb_delta.py` 不许 import pydantic/fastapi。
`/v2/fence/revoke` 端点在 `tests/test_fence_revoke_l13.py`（hipporag）。
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
IDX_ROOT = REPO_ROOT / "services/rag-alg/index_data_service"
if str(IDX_ROOT) not in sys.path:
    sys.path.insert(0, str(IDX_ROOT))

from ingest_pipeline import kb_pipeline as K  # noqa: E402

KB = "kb_9"
FID = "290"
OTHER = "999"
FULLTEXT_SRC = (IDX_ROOT / "index_fulltext_service" / "src"
                / "index_fulltext_service_pactera")


# ---------------------------------------------------------------- 19527 实现侧
def _load_init_field_body():
    """从 19527 的源码取 `init_field_body`（**实现侧真值**，不是我们抄一遍）。"""
    pkg = types.ModuleType("controller")
    pkg.__path__ = [str(FULLTEXT_SRC / "controller")]
    qt = types.ModuleType("controller.query_type")
    exec((FULLTEXT_SRC / "controller" / "query_type.py").read_text(encoding="utf-8"),
         qt.__dict__)
    sys.modules["controller"] = pkg
    sys.modules["controller.query_type"] = qt
    spec = importlib.util.spec_from_file_location(
        "es_query_probe_l13", FULLTEXT_SRC / "controller" / "es_query.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.init_field_body, qt.QueryType


def _mapping_block(field: str) -> str:
    """从 mapping 配置源码里取某个字段的定义块（不硬编码假设）。"""
    text = (FULLTEXT_SRC / "es_kb_config.py").read_text(encoding="utf-8")
    idx = text.index(f'"{field}": {{')
    depth = 0
    for pos in range(idx, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[idx:pos + 1]
    raise AssertionError("mapping 块未闭合")


# ---------------------------------------------------------------- 替身
class Rec:
    def __init__(self):
        self.events = []
        self.http = []
        self.fail_url_contains = None
        self.apply_urls = []
        self.calls = {"build": 0, "delete_scope": 0, "apply": 0, "delta": 0,
                      "revoke": 0, "txn": 0, "commit_snapshot": 0, "project": 0}

    def hit(self, name):
        self.calls[name] = self.calls.get(name, 0) + 1
        self.events.append(name)

    def post(self, url, body):
        self.http.append((url, body))
        self.events.append("post:" + url.rsplit("/", 1)[-1])
        if self.fail_url_contains and self.fail_url_contains in url:
            raise RuntimeError(f"injected http failure at {url}")


class FakeWriter:
    """只替身 HTTP 与计划产出，语义按真 index_writer 的形状。"""

    IndexWriterError = Exception

    def __init__(self, rec, chunks):
        self.rec = rec
        self.chunks = chunks

    def build(self, chunks, artifact, *, kb, index_prefix="v2cand_", file_id=None):
        self.rec.hit("build")
        # 计划与同源绑定都走**真实现**（只替身 apply/delete_scope 的网络动作）
        from ingest_pipeline import index_writer as IW
        return IW.build(chunks, {**artifact, "file_id": str(file_id)}, kb=kb,
                        index_prefix=index_prefix, file_id=file_id)

    @staticmethod
    def bind_chunks(chunks, artifact):
        from ingest_pipeline import index_writer as IW
        return IW.bind_chunks(chunks, artifact)

    def delete_scope(self, *, kb, file_id, index_prefix="v2cand_"):
        self.rec.hit("delete_scope")
        names = [f"{index_prefix}{kb}", f"{index_prefix}table_chunks_{kb}"]
        targets = []
        for name in names:
            targets.append({"side": "es", "index_name": name})
            targets.append({"side": "milvus", "collection_name": name})
        return {"kb": kb, "file_id": str(file_id), "col_name": "metadata.file_id",
                "col_values": [str(file_id)], "targets": targets}

    def apply(self, plan, *, es_url, milvus_url):
        self.rec.hit("apply")
        self.rec.apply_urls.append((es_url, milvus_url))
        # 真 apply 是「先 ES 后 Milvus」，空计划不产生请求
        for url, bodies in ((es_url, plan.es_plan), (milvus_url, plan.milvus_plan)):
            for _body in bodies:
                self.rec.post(url, {"stub": True})

        class R:
            status = "OK"
            side = None
            error = None
            completed_sides = ["es", "milvus"]
            needs_compensation = False
            calls = []
        return R()


@pytest.fixture()
def svc(tmp_path, monkeypatch):
    from ingest_pipeline import kb_delta as D

    rec = Rec()
    chunks = [{"pk": 1, "text": "正文块", "seq": 0, "channel": "text",
               "parse_artifact_id": "a" * 64, "content_uid": "b" * 64,
               "locator": {"kind": "text_span", "source": "parsed_text.md",
                           "start_offset": 0, "end_offset": 3}}]

    def commit_snapshot(*a, **kw):
        rec.hit("commit_snapshot")
        return ({"artifact_id": "a" * 64, "content_uid": "b" * 64,
                 "committed_at": "2026-11-08 00:00:00"}, Path("/snap"))

    def project_snapshot(*a, **kw):
        rec.hit("project")

        class R:
            status = "READY"
            stats = {"chunks_text": 1, "chunks_table": 0}
        R.chunks = chunks
        return R()

    def state_txn():
        rec.hit("txn")
        return K._kb_state_txn(str(tmp_path / "kb-state"))

    def delta(_plan):
        rec.hit("delta")
        return {"status": "BUILT"}

    service = D.KbDeltaService(
        str(tmp_path / "kb-state"),
        commit_snapshot=commit_snapshot, project_snapshot=project_snapshot,
        state_txn=state_txn, writer=FakeWriter(rec, chunks),
        revoke=lambda ids, kb="": rec.hit("revoke"),
        delta=delta, poster=rec.post,
        es_base="http://es-shim:19527", milvus_base="http://milvus-shim:19526",
    )
    state = {"schema": K.KB_STATE_SCHEMA, "version": 1, "cursor": "cursor-old",
             "set_digest": "d", "kb": {KB: {}}, "chunks": {KB: {}},
             "graph": {KB: {"snapshot": None, "fencing": 0, "mode": "DELTA"}}}
    path = tmp_path / "kb-state" / "kb_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setenv("LLMKE_KB_STATE", str(path))
    return service, rec, path


def _req(**kw):
    base = {"kb": KB, "file_id": FID, "operation": "UPSERT", "doc2md_dir": "/doc2md-out",
            "index_name": KB, "content_hash": "c" * 64, "producer_inputs": {}}
    base.update(kw)
    return base


# ---------------------------------------------------------------- A1
def test_a1_upsert_writes_and_reports_applied(svc):
    service, rec, path = svc
    out = service.run(_req())

    assert rec.calls["apply"] >= 1
    assert out["index_write"]["applied"] is True
    assert out["index_write"]["status"] == "APPLIED"
    assert out["status"] == "OK", f"写入完整后应能返回 OK，实际 {out['status']}"
    assert out["state_committed"] is True


def test_a1_write_order_is_delete_insert_per_side(svc):
    service, rec, _path = svc
    service.run(_req())

    # 每侧都是「先删后写」：ES 删 → ES 写 → Milvus 删 → Milvus 写
    del_es = [i for i, e in enumerate(rec.events) if e == "post:del_doc_by_col"]
    ins = [i for i, e in enumerate(rec.events) if e == "post:insert_fulltext_documents"]
    ins_mv = [i for i, e in enumerate(rec.events) if e == "post:insert_vector_documents_custom"]
    assert del_es and ins and ins_mv, rec.events
    assert max(del_es[:2]) < min(ins), "ES 必须先删完再写"
    assert max(del_es) > min(ins), "Milvus 的删除必须在 ES 写之后（per-侧先删后写）"


# ---------------------------------------------------------------- A2
def test_a2_all_four_targets_are_deleted(svc):
    service, rec, _path = svc
    service.run(_req())

    deletes = [(u, b) for u, b in rec.http if u.endswith("/del_doc_by_col")]
    assert len(deletes) == 4, deletes
    es = [b for u, b in deletes if u.startswith("http://es-shim")]
    mv = [b for u, b in deletes if u.startswith("http://milvus-shim")]
    assert {b["index_name"] for b in es} == {f"v2cand_{KB}", f"v2cand_table_chunks_{KB}"}
    assert {b["collection_name"] for b in mv} == {f"v2cand_{KB}", f"v2cand_table_chunks_{KB}"}
    for b in es + mv:
        assert b["col_values"] == [FID]


def test_a2_both_sides_use_file_id_for_different_reasons(svc):
    """两侧**都传 `file_id`，但理由不同**（C1 用 describe 核出的服务端真值）。

    - ES(19527)：服务端自己拼 `metadata.{field}.keyword` → 传裸名；
    - Milvus(19526)：原样拼 `expr`，而集合是**平铺字段**、文件 id 就是顶层 `file_id` → 也传裸名。

    **反向断言保留**：若有人「统一」成 `metadata.file_id`，ES 会变双前缀、Milvus 找不到字段。
    测试名曾叫 `..._use_different_col_name`，那是**错的**（值相同），已按事实改名，
    避免后人看名字以为「两侧必须不同」又改回去。
    """
    service, rec, _path = svc
    service.run(_req())

    deletes = [(u, b) for u, b in rec.http if u.endswith("/del_doc_by_col")]
    es_cols = {b["col_name"] for u, b in deletes if u.startswith("http://es-shim")}
    mv_cols = {b["col_name"] for u, b in deletes if u.startswith("http://milvus-shim")}
    assert es_cols == {"file_id"}, es_cols
    assert mv_cols == {"file_id"}, mv_cols

    # 反向：统一传 metadata.file_id 必须是错的（两个理由都成立）
    from ingest_pipeline import kb_delta as D
    with pytest.raises(D.KbDeltaRefused):
        D.build_delete_body(side="es", target=f"v2cand_{KB}", file_id=FID,
                            col_name="metadata.file_id", col_values=[FID])
    with pytest.raises(D.KbDeltaRefused):
        D.build_delete_body(side="milvus", target=f"v2cand_{KB}", file_id=FID,
                            col_name="metadata.file_id", col_values=[FID])


def _milvus_schema_fields(collection: str) -> set:
    """从 **19526 的 schema 源**（`milvus_kb_config.py`）读真实字段名。

    与 ES 侧「从 `init_field_body` 源码取真值」同一标准：比服务端定义，不抄我们自己的常量。
    """
    import ast
    import pathlib as _pl

    src = (IDX_ROOT / "index_vector_service" / "src" / "index_vector_service_pactera"
           / "milvus_kb_config.py")
    tree = ast.parse(src.read_text(encoding="utf-8"))
    target = ("MILVUS_FIELDS_TABLE_CHUNKS" if "table_chunks_" in collection
              else "MILVUS_FIELDS")
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == target for t in node.targets):
            if isinstance(node.value, ast.Dict):
                return {k.value for k in node.value.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    raise AssertionError(f"未找到 {target} 定义")


def test_a2_milvus_field_exists_in_server_schema(svc):
    """Milvus 侧也必须「服务端真值 vs 我们的值」，不是自说自话。

    C1 的教训：A2 当时只给 ES 侧做了端到端断言，Milvus 侧只断言了「我们发了什么」，
    于是 `metadata.file_id` 这个错值一路活到 C1（真实 schema 里根本没有该字段）。
    """
    from ingest_pipeline import kb_delta as D

    for collection, side in ((f"v2cand_{KB}", "milvus"), (f"v2cand_table_chunks_{KB}", "milvus")):
        fields = _milvus_schema_fields(collection)
        assert "file_id" in fields, f"{collection}: schema 里应有顶层 file_id，实际 {sorted(fields)[:8]}…"
        assert "metadata.file_id" not in fields, "Milvus 是平铺字段，不存在 metadata.file_id"

        body = D.build_delete_body(side=side, target=collection, file_id=FID,
                                  col_name=D.MILVUS_DELETE_FIELD, col_values=[FID])
        assert body["col_name"] in fields, \
            f"我们传的 {body['col_name']!r} 必须真实存在于服务端 schema"


def test_a2_es_field_path_matches_server_side_transform(svc):
    """端到端：把我们的 ES `col_name` 喂给 19527 的 `init_field_body`，
    必须正好得到 `metadata.file_id.keyword`（**用实现侧真值比，不自说自话**）。"""
    init_field_body, QueryType = _load_init_field_body()
    service, rec, _path = svc
    service.run(_req())

    (url, body), = [(u, b) for u, b in rec.http if u.endswith("/del_doc_by_col")
                    and u.startswith("http://es-shim")][:1]
    produced = init_field_body(body["col_name"], body["col_values"], QueryType.METADATA)
    assert produced == {"terms": {"metadata.file_id.keyword": [FID]}}, produced

    # 反证：如果按「统一成一个值」传 metadata.file_id，服务端会拼成双前缀 → 0 命中
    wrong = init_field_body("metadata.file_id", [FID], QueryType.METADATA)
    assert list(wrong["terms"]) == ["metadata.metadata.file_id.keyword"]


def test_a2_mapping_declares_file_id_keyword():
    """mapping 里 `file_id` 必须有 `.keyword` 子字段，否则 ES 侧同样是 0 命中。"""
    block = _mapping_block("file_id")
    assert '"keyword"' in block
    assert '"ignore_above"' in block


def test_a2_guard_refuses_metadata_prefixed_col_name_on_es(svc):
    """防「将来有人统一成同一个值」：ES 侧拿到 `metadata.file_id` 必须直接拒绝发送。"""
    from ingest_pipeline import kb_delta as D

    with pytest.raises(D.KbDeltaRefused) as exc:
        D.build_delete_body(side="es", target=f"v2cand_{KB}", file_id=FID,
                            col_name="metadata.file_id", col_values=[FID])
    assert exc.value.code == "DELETE_FIELD_INVALID"


def test_a2_guard_refuses_empty_col_name_before_sending(svc):
    """防删库：`col_name` 为空时 19526 会 `coll.drop()` 整个集合 —— 客户端必须拦住。"""
    from ingest_pipeline import kb_delta as D

    service, rec, path = svc
    before = json.loads(path.read_text(encoding="utf-8"))

    with pytest.raises(D.KbDeltaRefused) as exc:
        D.build_delete_body(side="milvus", target=f"v2cand_{KB}", file_id=FID,
                            col_name="", col_values=[FID])
    assert exc.value.code == "DELETE_FIELD_INVALID"
    assert rec.http == [], "防护失败时不得发出任何请求"
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == before["version"]


# ---------------------------------------------------------------- A3
def test_a3_partial_failure_records_completed_side(svc):
    service, rec, path = svc
    before = json.loads(path.read_text(encoding="utf-8"))
    rec.fail_url_contains = "insert_vector_documents_custom"   # ES 已写、Milvus 失败

    with pytest.raises(Exception) as exc:
        service.run(_req())

    err = exc.value
    assert getattr(err, "code", None) == "INDEX_WRITE_FAILED"
    payload = getattr(err, "payload", None) or {}
    comp = payload.get("index_write", {}).get("compensation", {})
    assert comp.get("needs") is True, "已写的一侧必须显式记录补偿需求"
    assert "es" in comp.get("completed_sides", []), comp
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["version"] == before["version"], "写入失败不得提交状态"
    assert rec.calls["delta"] == 0, "写入失败不得继续建图"


def test_a3_status_not_ok_when_compensation_needed(svc):
    from ingest_pipeline import kb_delta as D

    plan = D.IngestPlan(kb=KB, diff={"reason": "FILE_SET_CHANGED"}, diff_source="request")
    out = service_result = None
    service, _rec, _p = svc
    out = service._result(
        plan, status=None, cursor="c", wanted=[], graph_result={"status": "BUILT"},
        graph_error=None,
        index_write={"status": "APPLIED", "applied": True, "required": True,
                     "compensation": {"needs": True, "completed_sides": ["es"], "calls": []}},
        state_committed=True)
    assert out["status"] != "OK", "需要补偿时不得报 OK（同 L12 的 applied 规则）"


# ---------------------------------------------------------------- A4
def test_a4_delete_with_runner_commits_state(svc):
    service, rec, path = svc
    state = json.loads(path.read_text(encoding="utf-8"))
    state["kb"][KB][OTHER] = {"status": "ACTIVE", "content_hash": "x"}
    # 留一个存活文件：删到空库现在按契约 §5 走 ALL_REVOKED（零副作用拒绝）。
    # 本用例验的是「非空库删除」提交状态。
    state["kb"][KB][FID] = {"status": "ACTIVE", "content_hash": "h" * 64}
    state.setdefault("chunks", {}).setdefault(KB, {})[FID] = [
        {"pk": 1, "text": "存活正文", "locator": "chunk=0", "channel": "text",
         "content_hash": "h" * 64}]
    path.write_text(json.dumps(state), encoding="utf-8")

    out = service.run(_req(operation="DELETE", file_id=OTHER, content_hash=None))

    assert out["state_committed"] is True
    assert out["status"] == "OK"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["kb"][KB][OTHER]["status"] == "REVOKED"


# ---------------------------------------------------------------- A6
def test_a6_delta_still_before_state_txn(svc):
    service, rec, _path = svc
    service.run(_req())
    assert rec.events.index("delta") < rec.events.index("txn"), rec.events


def test_a6_apply_runs_before_delta(svc):
    """搜索路先落，图谱后建：写失败不该已经动过图。"""
    service, rec, _path = svc
    service.run(_req())
    first_insert = rec.events.index("post:insert_fulltext_documents")
    assert first_insert < rec.events.index("delta"), rec.events


# ---------------------------------------------------------------- 加固项（TL 15:1x）
def test_harden_a_write_targets_fail_closed_without_config(svc, monkeypatch):
    """默认目标是**线上** 19527/19526：没配 env 又没显式开关 → 必须拒绝，不得静默回退。"""
    from ingest_pipeline import kb_delta as D

    monkeypatch.delenv(D.ES_BASE_ENV, raising=False)
    monkeypatch.delenv(D.MILVUS_BASE_ENV, raising=False)
    monkeypatch.delenv(D.ALLOW_DEFAULT_WRITE_ENV, raising=False)

    service, rec, _path = svc
    # 模拟「生产漏配 env 且没传参」：其余全用替身，只有写入端点未配置
    service._es_base_given = None
    service._milvus_base_given = None

    # 构造期不炸（否则连 /health 都拿不到，无法诊断），但**首次写入必须拒绝**
    with pytest.raises(D.KbDeltaRefused) as exc:
        service.run(_req())
    assert rec.http == [], "未配置写入端点时不得发出任何请求"
    assert exc.value.code == "INDEX_WRITE_FAILED"
    assert "19527" in str(exc.value.detail) or "未配置" in str(exc.value.detail)
    # 启动自检可读到的状态（B 段用它 fail-fast）
    assert D.write_targets_configured()["configured"] is False


def test_harden_a_default_target_requires_explicit_switch(monkeypatch):
    from ingest_pipeline import kb_delta as D

    monkeypatch.delenv(D.ES_BASE_ENV, raising=False)
    monkeypatch.delenv(D.MILVUS_BASE_ENV, raising=False)
    monkeypatch.setenv(D.ALLOW_DEFAULT_WRITE_ENV, "1")

    service = D.KbDeltaService("/store-root")
    assert service.es_base == D.DEFAULT_ES_BASE
    assert service.milvus_base == D.DEFAULT_MILVUS_BASE


def test_harden_a_env_configured_needs_no_switch(monkeypatch):
    from ingest_pipeline import kb_delta as D

    monkeypatch.setenv(D.ES_BASE_ENV, "http://es-from-env:19527")
    monkeypatch.setenv(D.MILVUS_BASE_ENV, "http://mv-from-env:19526")
    monkeypatch.delenv(D.ALLOW_DEFAULT_WRITE_ENV, raising=False)

    service = D.KbDeltaService("/store-root")
    assert service.es_base == "http://es-from-env:19527"
    assert service.milvus_base == "http://mv-from-env:19526"


def test_harden_b_milvus_insert_carries_no_es_url(svc):
    """`side=milvus` 分支必须显式传 `es_url=None`，不靠「空 plan 不发请求」的隐含行为。"""
    service, rec, _path = svc
    service.run(_req())

    assert rec.apply_urls, "apply 必须被调用"
    for es_url, milvus_url in rec.apply_urls:
        if milvus_url:
            assert es_url is None, f"Milvus 侧不得携带 ES URL：{es_url!r}"
        if es_url:
            assert "insert_fulltext_documents" in es_url

# ------------------------------------------------ C5 追加：索引「先删后写」失败的可见性
def test_c5_es_insert_failure_after_deletes_file_becomes_invisible_then_replay(svc):
    """**比 delta 失败更危险的场景**（TL 21:1x §4）：

    `_apply_writes` 是「先删后写」—— `do_deletes("es")` 成功、`do_insert("es")` 失败时，
    该文件在 ES 里的旧块**已被删掉、新块没写** ⇒ **短暂不可见**。

    要断言三件事：
    1. 失败确实发生在「删已发、写未成」之后（`deletes` 有 2 个 es target，且有真实 delete 请求）；
    2. 异常带出 `INDEX_WRITE_FAILED` + `compensation`（上层能看到已完成/未完成的一侧）；
    3. **重放同一请求能收敛**（state 前进、索引恢复）——这是「可恢复」的证明。
    """
    from ingest_pipeline import kb_delta as D

    service, rec, path = svc
    before = json.loads(path.read_text(encoding="utf-8"))
    rec.fail_url_contains = "insert_fulltext_documents"       # 删成功、插入失败

    with pytest.raises(D.KbDeltaRefused) as ei:
        service.run(_req())

    err = ei.value
    assert err.code == "INDEX_WRITE_FAILED", err.code
    iw = (getattr(err, "payload", None) or {}).get("index_write") or {}
    es_deletes = [d for d in (iw.get("deletes") or []) if d.get("side") == "es"]
    assert len(es_deletes) == 2, f"es 两个 target 都应已删：{iw.get('deletes')}"
    assert any("del_doc_by_col" in url for url, _b in rec.http), \
        "删除必须是真的发出去了（这就是「该文件短暂不可见」的成因）"
    assert any("insert_fulltext_documents" in url for url, _b in rec.http), \
        "插入也尝试过（失败点）"
    assert iw.get("status") == "FAILED" and iw.get("applied") is False
    assert "compensation" in iw, "必须带回补偿信息（契约 §5）"
    assert rec.calls["delta"] == 0, "索引失败不得继续建图（图未动，重放代价最小）"
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == before["version"]

    # 重放：恢复正常写入 → 收敛
    rec.fail_url_contains = None
    out = service.run(_req())
    assert out["status"] == "OK", out.get("status")
    assert out["index_write"]["applied"] is True
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["version"] > before["version"], "重放后状态必须前进"
    assert FID in after["kb"][KB] and after["kb"][KB][FID]["status"] == "ACTIVE"
