"""P2-L8 · T-D2MD-08 影子命名空间反例与断言（`P2-L8-PLAN.md` §三 + TL 12:1x 裁定）。

I1 前缀对齐且默认不碰线上 · I2 读模式开关行为 · I3 旧命名空间零影响
I4 回滚可逆 · I5 回归；R-1~R-6 为对应反例。

**模式 A**：全程离线/mock，不创建任何索引/collection、不启停服务、不写线上。

TL 12:1x 追加的三条裁定断言
--------------------------
1. 读侧通道名与写侧 `index_writer._target_name` **逐字对拍**（I1-c）；
2. snapshot 下图召回请求的 `kb` 必须是原库名（`kb_9`，不是 `v2cand_kb_9`）；
3. 影子 metadata = 生产载荷键集 **+** `artifact_id` / `content_hash`，且读侧依赖的
   `source` / `parsed_text_ref` / `n_rows` / `n_cols` 四个键齐全。

阶段 A（实现前）必须 FAIL 于断言/行为层，故新符号一律在用例体内取，避免 collection 层假 FAIL。
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "services/rag-alg/alg_retrieval_service/app"
IDX = ROOT / "services/rag-alg/index_data_service"
for path in (str(APP), str(IDX)):
    if path not in sys.path:
        sys.path.insert(0, path)

import projection_read as R  # noqa: E402
from ingest_pipeline import index_writer as IW  # noqa: E402
from ingest_pipeline import kb_pipeline as K  # noqa: E402

ART = "c" * 64
UID = "d" * 64
KB = "kb_9"
PREFIX_WRITE = "v2cand_"      # index_writer 的写侧约定（带尾下划线）
PREFIX_READ = "v2cand"        # projection_read 的读侧约定（不带，历史上靠拼接）
CHANNELS = ("text", "table_chunks", "table_summary", "faq")


# --------------------------------------------------------------------------- helpers
def _chunks() -> list:
    return [
        {"seq": 0, "channel": "text", "pk": 111, "text": "说明如下。",
         "locator": {"kind": "text_span", "source": "parsed_text.md",
                     "start_offset": 0, "end_offset": 5},
         "parse_artifact_id": ART, "content_uid": UID},
        {"seq": 1, "channel": "table", "pk": 222,
         "text": "指标 | 值\n日均存款 | 100",
         "locator": {"kind": "table_ref", "table_id": "t001", "block_id": "b0002"},
         "parse_artifact_id": ART, "content_uid": UID, "rows": 2, "cols": 2},
    ]


def _artifact() -> dict:
    return {"artifact_id": ART, "content_uid": UID,
            "committed_at": "2026-11-08 00:00:00"}


def _production_payloads() -> list:
    """生产链路（L5）载荷：线上 38 键的权威来源（离线）。"""
    return K.build_index_payloads(
        _chunks(), index_name=KB, file_id="333", file_name="a.md",
        file_path="/tmp/a.md", file_size=10, source="kb_9/a.md",
        now="2026-11-08 00:00:00")


def _shadow_plan():
    return IW.build(_chunks(), _artifact(), kb=KB, file_id="333",
                    file_path="/tmp/a.md")


# --------------------------------------------------------------------------- I1 / R-1
def test_i1a_write_default_prefix_is_v2cand() -> None:
    assert IW.DEFAULT_INDEX_PREFIX == PREFIX_WRITE
    plan = _shadow_plan()
    assert plan.index_prefix == PREFIX_WRITE
    names = {b["index_name"] for b in plan.es_plan}
    assert names == {"v2cand_kb_9", "v2cand_table_chunks_kb_9"}
    # 旧命名空间绝不出现在写入计划里（I3）
    assert not any(n in (KB, f"table_chunks_{KB}", f"table_summary_{KB}") for n in names)


def test_i1b_prefix_empty_or_kb_is_refused() -> None:
    """R-1：`index_prefix` 为空 / 等于 kb → 必须拒绝（防误写线上）。"""
    with pytest.raises(IW.IndexWriterError) as exc:
        IW.build(_chunks(), _artifact(), kb=KB, file_id="333", index_prefix="")
    assert exc.value.code == "INDEX_PREFIX_EMPTY"
    for bad in (KB, f"{KB}_", "v2cand"):
        with pytest.raises(IW.IndexWriterError) as exc2:
            IW.build(_chunks(), _artifact(), kb=KB, file_id="333", index_prefix=bad)
        assert exc2.value.code == "INDEX_PREFIX_INVALID"


def test_i1c_read_and_write_channel_names_match_verbatim(monkeypatch) -> None:
    """**本 loop 核心**：读侧通道名必须与写侧 `_target_name` 逐字相等。

    阶段 A 必 FAIL：读侧当前给 `table_chunks_v2cand_kb_9`，写侧产 `v2cand_table_chunks_kb_9`。
    """
    names, info = R.resolve([KB], mode="snapshot")
    channel_names = info["channel_names"]
    plan = _shadow_plan()
    write_names = {b["index_name"] for b in plan.es_plan}
    assert channel_names["text"] == [IW._target_name("text", kb=KB, index_prefix=PREFIX_WRITE)]
    assert channel_names["table_chunks"] == [
        IW._target_name("table", kb=KB, index_prefix=PREFIX_WRITE)]
    # 读侧产出的「会真正去查」的通道名，必须全在写侧可能产出的名字集合内
    read_names = {n for ch in ("text", "table_chunks") for n in channel_names[ch]}
    assert read_names == write_names
    # 反向：不允许出现 table_chunks_v2cand_kb_9 这类「拼接出来的错名」
    assert "table_chunks_v2cand_kb_9" not in read_names


def test_i1c_bad_name_is_explicitly_forbidden(monkeypatch) -> None:
    """把「错名」写进断言，确保它不会再被当成契约（旧测试固化过它）。"""
    _names, info = R.resolve([KB], mode="snapshot")
    all_names = {n for ch in CHANNELS for n in info["channel_names"][ch]}
    assert "table_chunks_v2cand_kb_9" not in all_names
    assert "table_summary_v2cand_kb_9" not in all_names


# --------------------------------------------------------------------------- I2 / R-2
def test_i2a_modes_are_exactly_three() -> None:
    assert tuple(R.MODES) == ("legacy", "shadow", "snapshot")
    assert R.DEFAULT_MODE == "legacy"


def test_i2b_unknown_mode_refused(monkeypatch) -> None:
    """R-2：`INGEST_READ_MODE=bogus` → 拒绝，**不静默默认**。"""
    monkeypatch.setenv("INGEST_READ_MODE", "bogus")
    with pytest.raises(ValueError):
        R.resolve([KB])


def test_i2c_legacy_is_identity() -> None:
    names, info = R.resolve([KB], mode="legacy")
    assert names == [KB]
    assert info["mode"] == "legacy" and info["switched"] == []
    assert info["channel_names"]["text"] == [KB]
    assert info["channel_names"]["table_chunks"] == [f"table_chunks_{KB}"]


def test_i2d_shadow_does_not_change_results_only_reports(monkeypatch) -> None:
    """shadow 降级语义（TL 裁定 Q4）：**返回名与 legacy 完全相同**，只多报 `shadow_names`。"""
    legacy_names, legacy_info = R.resolve([KB], mode="legacy")
    shadow_names, shadow_info = R.resolve([KB], mode="shadow")
    assert shadow_names == legacy_names  # 不改返回结果
    assert shadow_info["channel_names"] == legacy_info["channel_names"]
    assert shadow_info["shadow_names"]["text"] == ["v2cand_kb_9"]
    assert shadow_info["shadow_names"]["table_chunks"] == ["v2cand_table_chunks_kb_9"]
    assert shadow_info["mode"] == "shadow"


def test_i2e_snapshot_switches_all_channels(monkeypatch) -> None:
    names, info = R.resolve([KB], mode="snapshot")
    cn = info["channel_names"]
    assert names == ["v2cand_kb_9"]
    assert cn["text"] == ["v2cand_kb_9"]
    assert cn["table_chunks"] == ["v2cand_table_chunks_kb_9"]
    assert cn["table_summary"] == ["v2cand_table_summary_kb_9"]
    assert cn["faq"] == ["v2cand_faq_kb_9"]


def test_i2f_per_kb_scope_keeps_others_legacy(monkeypatch) -> None:
    names, info = R.resolve([KB, "kb_10"], mode="snapshot", only=["kb_10"])
    assert names == [KB, "v2cand_kb_10"]
    assert info["kept_legacy"] == [KB]
    # 未切换的库，通道名必须还是旧名（不能半切）
    assert info["channel_names"]["text"] == [KB, "v2cand_kb_10"]
    assert info["channel_names"]["table_chunks"] == [
        f"table_chunks_{KB}", "v2cand_table_chunks_kb_10"]


def test_i2g_missing_channels_declared(monkeypatch) -> None:
    """Q3：写侧不产 table_summary 影子 → 必须显式声明，不得静默。"""
    _n, info = R.resolve([KB], mode="snapshot")
    assert info["missing_channels"] == ["table_summary"]
    _n2, legacy_info = R.resolve([KB], mode="legacy")
    assert legacy_info["missing_channels"] == []


# --------------------------------------------------------------------------- graph kb
def test_graph_kb_mapping_under_snapshot(monkeypatch) -> None:
    """裁定断言 ②：snapshot 下图召回必须用原库名 `kb_9`。"""
    _n, info = R.resolve([KB], mode="snapshot")
    assert info["graph_kb"] == {"v2cand_kb_9": KB}
    assert R.original_kb("v2cand_kb_9") == KB
    assert R.original_kb(KB) == KB  # legacy 下原样返回


def test_channel_name_helper_used_by_secondary_call_sites(monkeypatch) -> None:
    """第 4 处拼装点（`retrieval_table_chunks`）走同一映射，不另写一套。"""
    monkeypatch.setenv("INGEST_READ_MODE", "snapshot")
    assert R.channel_name("table_chunks", KB) == "v2cand_table_chunks_kb_9"
    monkeypatch.setenv("INGEST_READ_MODE", "legacy")
    assert R.channel_name("table_chunks", KB) == f"table_chunks_{KB}"


# --------------------------------------------------------------------------- metadata 键
def test_shadow_metadata_equals_production_plus_two_trace_keys(monkeypatch) -> None:
    """裁定断言 ③：影子 = 生产键集 + `artifact_id` / `content_hash`（不得更少）。"""
    prod = {p["index"]: p["metadata"] for p in _production_payloads()}
    plan = _shadow_plan()
    shadow = {b["index_name"]: b["document_list"] for b in plan.es_plan}

    for channel, prod_index, shadow_index in (
            ("text", KB, "v2cand_kb_9"),
            ("table", f"table_chunks_{KB}", "v2cand_table_chunks_kb_9")):
        prod_keys = set(prod[prod_index])
        shadow_keys = set(shadow[shadow_index][0]["metadata"])
        assert shadow_keys - prod_keys == {"artifact_id", "content_hash"}, channel
        assert prod_keys - shadow_keys == set(), f"{channel} 缺键：{sorted(prod_keys - shadow_keys)}"


def test_shadow_metadata_has_read_side_dependency_keys(monkeypatch) -> None:
    """TL 裁定 Q5：4 个读侧依赖键必须齐全，且值不得编造。"""
    plan = _shadow_plan()
    docs = {b["index_name"]: b["document_list"] for b in plan.es_plan}
    text_meta = docs["v2cand_kb_9"][0]["metadata"]
    table_meta = docs["v2cand_table_chunks_kb_9"][0]["metadata"]

    # 无显式 source 时按 file_path 去 URL 前缀派生（不写死路径，见 _resolve_source）
    assert text_meta["source"] == urlparse("/tmp/a.md").path.lstrip("/")
    assert text_meta["parsed_text_ref"] == "parsed_text.md"
    assert table_meta["parsed_text_ref"] == "table"
    # 表格维度取 IR 真值（fixture 里 rows=2 / cols=2）
    assert table_meta["n_rows"] == 2 and table_meta["n_cols"] == 2
    # 正文块不带表格维度（与生产载荷一致：production text 通道没有这两个键）
    assert "n_rows" not in text_meta and "n_cols" not in text_meta


# --------------------------------------------------------------------------- source 语义
def test_source_explicit_wins() -> None:
    """优先级 1：调用点显式 `source` 直接采用（与 build_index_payloads 同口径）。"""
    plan = IW.build(_chunks(), _artifact(), kb=KB, file_id="333",
                    file_path="http://host:19000/x/y.txt/V0/y.txt", source="kb_9/y.txt")
    meta = [b for b in plan.es_plan if b["index_name"] == "v2cand_kb_9"][0]["document_list"][0]
    assert meta["metadata"]["source"] == "kb_9/y.txt"


def test_source_matches_online_shape_after_url_strip() -> None:
    """优先级 2：`urlparse(file_path).path.lstrip("/")` 必须与线上 source 同形态。

    线上样本：`source` 是 MinIO 对象键（无 scheme/host），`file_path` 是完整 URL。
    这里**不写死路径**，用 `urlparse` 派生后逐字比对，并断言结果里不含 scheme/host。
    """
    file_path = ("http://127.0.0.1:19000/r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/"
                 "R12FIX-credit-ledger.xlsx")
    expected = urlparse(file_path).path.lstrip("/")
    plan = IW.build(_chunks(), _artifact(), kb=KB, file_id="333", file_path=file_path)
    for body in plan.es_plan:
        meta = body["document_list"][0]["metadata"]
        assert meta["source"] == expected
        assert not meta["source"].startswith("http")
        assert "://" not in meta["source"]
        assert urlparse(meta["source"]).scheme == ""


def test_source_priority_2_falls_back_to_empty() -> None:
    """优先级 3：既无 source 也无 file_path → 空串（不得回落成库名/文件名）。"""
    plan = IW.build(_chunks(), _artifact(), kb=KB, file_id="333")
    meta = [b for b in plan.es_plan if b["index_name"] == "v2cand_kb_9"][0]["document_list"][0]
    assert meta["metadata"]["source"] == ""


def test_shadow_metadata_n_rows_missing_is_none_not_fabricated() -> None:
    """IR 缺表格维度 → `None`，不得编造 0/1。"""
    chunks = [c for c in _chunks() if c["channel"] == "text"]
    chunks.append({"seq": 1, "channel": "table", "pk": 222, "text": "指标",
                   "locator": {"kind": "table_ref", "table_id": "t9"},
                   "parse_artifact_id": ART, "content_uid": UID})
    plan = IW.build(chunks, _artifact(), kb=KB, file_id="333", file_path="/tmp/a.md")
    meta = [b for b in plan.es_plan
            if b["index_name"] == "v2cand_table_chunks_kb_9"][0]["document_list"][0]["metadata"]
    assert meta["n_rows"] is None and meta["n_cols"] is None


# --------------------------------------------------------------------------- I3 / R-4
def test_i3a_mode_a_writes_nothing(monkeypatch) -> None:
    """R-4：模式 A 全程不发写入请求；`apply` 未被调用即证明。"""
    calls = []

    def boom(*args, **kwargs):
        calls.append(args)
        raise AssertionError("模式 A 不得发写入请求")

    monkeypatch.setattr(IW, "_post_json", boom)
    plan = _shadow_plan()                       # 只产计划
    assert plan.es_plan and plan.milvus_plan
    assert calls == []


def test_i3b_legacy_names_never_produced_by_writer(monkeypatch) -> None:
    plan = _shadow_plan()
    for body in plan.es_plan:
        assert body["index_name"].startswith(PREFIX_WRITE)
    for body in plan.milvus_plan:
        assert body["collection_name"].startswith(PREFIX_WRITE)
        # Milvus 服务端统一加 `_` 前缀，这里不得自己加（R-0 §3）
        assert not body["collection_name"].startswith("_")


# --------------------------------------------------------------------------- I4 / R-5
def test_i4a_rollback_to_legacy_is_bitwise_identity(monkeypatch) -> None:
    """R-5：回滚 `INGEST_READ_MODE=legacy` 后行为与改动前一致。"""
    monkeypatch.setenv("INGEST_READ_MODE", "legacy")
    monkeypatch.setenv("INGEST_READ_PREFIX", PREFIX_READ)
    names, info = R.resolve([KB], mode=None)
    assert names == [KB]
    assert info["switched"] == []
    assert info["channel_names"] == {
        "text": [KB], "table_chunks": [f"table_chunks_{KB}"],
        "table_summary": [f"table_summary_{KB}"], "faq": [f"faq_{KB}"]}
    assert info["graph_kb"] == {KB: KB}


# --------------------------------------------------------------------------- 接线静态守卫
def _source(rel):
    return (APP / rel).read_text(encoding="utf-8")


def test_retrieval_service_wiring_uses_channel_names() -> None:
    """`retrieval_service` 两个拼装点都必须走映射（该模块依赖 langchain，无法 import 验证）。"""
    src = _source("retrieval_service.py")
    assert '_channel("table_chunks")' in src
    assert '_channel("table_summary")' in src
    assert '_channel("faq")' in src
    assert '_channel_name("table_chunks", kn)' in src
    # 旧的裸拼接不得再出现在代码行里（注释允许）
    for line in src.splitlines():
        code = line.split("#", 1)[0]
        assert '"table_chunks_" + kn' not in code
        assert '"table_summary_" + kn' not in code
        assert '"faq_" + kn' not in code


def test_multiple_retrieval_graph_uses_original_kb() -> None:
    src = _source("multiple_retrieval.py")
    assert '"kb": _original_kb(k_name)' in src
    assert '"kb": k_name,' not in src


def test_residual_concatenation_sites_are_documented() -> None:
    """已知未收口的拼装点（新增一处就 FAIL，防将来又有人自己拼一套影子名）。

    当前只剩 `retrieval_service_cec.py` 的 `table_summary_`：该通道本 loop **没有影子**，
    已被 Q3 的 `missing_channels` 与 `T-D2MD-17` 硬前置覆盖，故按 TL 裁定不动。
    `multiple_retrieval.py` 的两处（图召回 kb、多版本 table 索引）已在 L8 收口。
    """
    residuals = set()
    for path in APP.glob("*.py"):
        if path.name == "projection_read.py":   # 唯一允许拼名字的地方
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            code = line.split("#", 1)[0]
            if ('"table_chunks_" +' in code or '"table_summary_" +' in code
                    or '"faq_" +' in code):
                residuals.add(path.name)
    assert residuals == {"retrieval_service_cec.py"}


def test_multi_version_table_index_uses_channel_mapping() -> None:
    """多版本路径的 table 索引名也走映射，不再裸拼（TL 12:2x 授权收口）。"""
    src = _source("multiple_retrieval.py")
    assert '_channel_name(\n' in src or '_channel_name("table_chunks"' in src
    assert '"table_chunks_" + es_knowledge_base_name' not in src


# --------------------------------------------------------------------------- I5 / R-6
def test_i5_regression_sentinels() -> None:
    """R-6：禁改区与关键入口仍在。"""
    from rag_projection import projection as P

    assert P._table_pk("kb_9", "333", 0) == 885155839145947657
    assert callable(IW.build) and callable(IW.delete_scope) and callable(IW.apply)
    assert callable(K.build_index_payloads) and callable(K.consume_for_kb)
    assert callable(R.resolve)
