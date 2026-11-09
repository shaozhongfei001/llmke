"""P3-L9 · T-D2MD-09 `delta_build` 编排断言（`P3-L9-PLAN.md` §三 + TL 13:1x 裁定）。

J2 freshness 短路零引擎调用 · J3 DELTA 后四文件由本次输入重算 · J4 无自动降级
J5 `_binding_input` 残留收口 · **J8 无 canary 配置时 `auto` 必须走 delta**
R-1~R-6 对应反例。

**离线**：不启停 18094、不起监听端口、不写线上存储；引擎用替身（`openie_docs()` 假数据），
不 import fastapi/pydantic（`llmke-v2-toolenv` 两者都没有，见 evidence D-3）。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
IDX = ROOT / "services/rag-alg/index_data_service"
if str(IDX) not in sys.path:
    sys.path.insert(0, str(IDX))

from graph_engine_adapter import canary, delta_build as D, rebuild as R  # noqa: E402
from ingest_pipeline import index_writer as IW  # noqa: E402

KB = "kb_9"


# --------------------------------------------------------------------------- 替身
class FakeEngine:
    """只实现 `delta_build` 需要的 `openie_docs()`。"""

    def __init__(self, mapping):
        self._mapping = mapping          # text -> idx

    def openie_docs(self):
        return [{"passage": t, "idx": i} for t, i in self._mapping.items()]


def _docs(*specs):
    """specs: (file_id, text) 或 (file_id, text, pk)。"""
    out = []
    for spec in specs:
        fid, text = spec[0], spec[1]
        pk = spec[2] if len(spec) > 2 else None
        # 契约 §2.1：请求侧用 `file_ids` 数组（单文件时为单元素数组）
        out.append(SimpleNamespace(file_ids=[fid], text=text, locator=f"chunk=0;f={fid}",
                                   title=f"{fid}.md", pk=pk,
                                   parse_artifact_id="c" * 64))
    return out


def _req(docs, *, kb=KB, mode="auto", reason=None, root=None, fencing=None):
    return SimpleNamespace(kb=kb, docs=docs, requested_mode=mode, fallback_reason=reason,
                           root=root, fencing=fencing)


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def _sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _base_snapshot(tmp_path: Path, *, files, fence=None, kb_marker=None) -> tuple:
    """造一个"基准快照"：`root/current.json` + 快照目录（含 copytree 会带走的四文件）。

    刻意让四文件内容都是**旧值**（sentinel），这样 DELTA 后若没重算，J3 必失败。
    """
    root = tmp_path / "api-root" / KB
    base = root / "snapshot-20260101000000-000000-g0"
    base.mkdir(parents=True)
    _write_json(base / "sources.json", {"idx-old": [{"file_id": "DELETED-FILE"}]})
    (base / "community.json").write_text('{"sentinel": "base-community"}', encoding="utf-8")
    # 基准 fence 用 indent=2 写；fence.save 是 compact+sort_keys，重写后 sha 必变，
    # 从而能证明"这个文件确实被本次流程重写过"，而不是 copytree 留下的原件。
    (base / "fence.json").write_text(json.dumps(fence or {"generation": 0, "revoked": {}},
                                                indent=2), encoding="utf-8")
    if kb_marker is not None:
        _write_json(base / "kb.json", kb_marker)
    live = [{"file_id": f, "text": t} for f, t in files]
    _write_json(root / "current.json", {"dir": str(base),
                                        "fingerprint": R.docs_fingerprint(live),
                                        "fencing": 1, "generation": 0})
    return root, base


def _run(tmp_path, req, *, apply_calls=None, full_calls=None, mapping=None, policy=None):
    """跑一次 delta_build，注入 apply/full 替身并记录调用次数。"""
    apply_calls = apply_calls if apply_calls is not None else []
    full_calls = full_calls if full_calls is not None else []

    def apply_fn(target, texts):
        apply_calls.append({"target": target, "texts": list(texts)})
        return {"applied": len(texts)}

    def full_builder(items, target):
        full_calls.append({"target": target, "items": len(items)})
        return {"built": len(items)}

    engine_map = mapping if mapping is not None else {d.text: f"idx-{i}"
                                                      for i, d in enumerate(req.docs)}
    out = D.delta_build(req, apply_fn=apply_fn, full_builder=full_builder,
                        engine_factory=lambda target: FakeEngine(engine_map),
                        policy=policy)
    return out, apply_calls, full_calls


# --------------------------------------------------------------------------- J2
def test_j2_not_stale_auto_skips_with_zero_engine_calls(tmp_path, monkeypatch) -> None:
    """R-2 前身：快照已新鲜 → SKIPPED_FRESH，apply/full 计数都为 0。"""
    monkeypatch.delenv("LLMKE_CANARY_SCOPE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_MODE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_DEFAULT", raising=False)
    docs = _docs(("A", "甲"), ("B", "乙"))
    root, _base = _base_snapshot(tmp_path, files=[("A", "甲"), ("B", "乙")])
    req = _req(docs, root=str(root.parent))
    out, apply_calls, full_calls = _run(tmp_path, req)
    assert out["status"] == D.STATUS_SKIPPED_FRESH
    assert out["freshness"]["stale"] is False
    assert apply_calls == [] and full_calls == []


def test_j2_skip_if_fresh_same_as_auto_when_fresh(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("LLMKE_CANARY_SCOPE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_MODE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_DEFAULT", raising=False)
    docs = _docs(("A", "甲"))
    root, _ = _base_snapshot(tmp_path, files=[("A", "甲")])
    out, apply_calls, full_calls = _run(tmp_path, _req(docs, mode="skip_if_fresh",
                                                      root=str(root.parent)))
    assert out["status"] == D.STATUS_SKIPPED_FRESH
    assert apply_calls == [] and full_calls == []


# --------------------------------------------------------------------------- J8（最关键的 D-11）
def test_j8_auto_without_canary_config_must_go_delta(tmp_path, monkeypatch) -> None:
    """**D-11 核心**：canary 的 `DEFAULT_MODE="full"` 是 dataclass 默认值，不是运维意图。

    无任何 canary 配置时 `auto` 必须走 DELTA：`full_build` 计数 0，
    且响应写明 `canary_source="default->delta"`。否则 L7 刚停掉的全库重建会被悄悄恢复。
    """
    monkeypatch.delenv("LLMKE_CANARY_SCOPE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_MODE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_DEFAULT", raising=False)
    # canary 默认确实是 full —— 把这条事实也钉住，避免有人改默认值后本断言悄悄失效
    assert canary.load(None).mode_for(KB) == "full"

    docs = _docs(("A", "甲"), ("B", "乙"))
    root, base = _base_snapshot(tmp_path, files=[("OLD", "旧")])   # 指纹不符 → stale
    out, apply_calls, full_calls = _run(tmp_path, _req(docs, root=str(root.parent)))
    assert out["status"] == D.STATUS_BUILT
    assert out["effective_mode"] == "DELTA"
    assert out["canary_source"] == "default->delta"
    assert full_calls == []          # ← 全量重建一次都没跑
    assert len(apply_calls) == 1


def test_j8_explicit_canary_full_allows_full_build(tmp_path, monkeypatch) -> None:
    """运维**显式**配 full 时才允许全量。"""
    monkeypatch.setenv("LLMKE_CANARY_SCOPE", KB)
    monkeypatch.setenv("LLMKE_CANARY_MODE", "full")
    docs = _docs(("A", "甲"))
    root, _ = _base_snapshot(tmp_path, files=[("OLD", "旧")])
    out, apply_calls, full_calls = _run(tmp_path, _req(docs, root=str(root.parent)))
    assert out["effective_mode"] == "FULL"
    assert out["canary_source"] == "canary:full"
    assert len(full_calls) == 1 and apply_calls == []


# --------------------------------------------------------------------------- J4 / R-1 / R-2
def test_j4a_no_baseline_rejected_not_fallback(tmp_path, monkeypatch) -> None:
    """R-2：无基准快照 → REJECTED，**不自动走 FULL**（D-9：判空前置，不靠异常字符串）。"""
    monkeypatch.delenv("LLMKE_CANARY_SCOPE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_MODE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_DEFAULT", raising=False)
    docs = _docs(("A", "甲"))
    root = tmp_path / "api-root" / KB            # 目录都没有 → 无指针
    out, apply_calls, full_calls = _run(tmp_path, _req(docs, root=str(root.parent)))
    assert out["status"] == D.STATUS_REJECTED
    assert out["reason"] == "NO_BASELINE_SNAPSHOT"
    assert apply_calls == [] and full_calls == []


def test_j4b_full_without_reason_rejected(tmp_path) -> None:
    """R-1：`full` 缺 `fallback_reason` → 拒绝（HTTP 层另有 422）。"""
    docs = _docs(("A", "甲"))
    root, _ = _base_snapshot(tmp_path, files=[("A", "甲")])
    out, apply_calls, full_calls = _run(tmp_path, _req(docs, mode="full", root=str(root.parent)))
    assert out["status"] == D.STATUS_REJECTED
    assert out["reason"] == "FULL_REQUIRES_FALLBACK_REASON"
    assert full_calls == []


def test_j4c_delta_failure_does_not_fallback_to_full(tmp_path, monkeypatch) -> None:
    """R-2 变体：delta 失败 → FAILED 带原因，**不**改走 full。"""
    monkeypatch.delenv("LLMKE_CANARY_SCOPE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_MODE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_DEFAULT", raising=False)
    docs = _docs(("A", "甲"))
    root, _ = _base_snapshot(tmp_path, files=[("OLD", "旧")])
    full_calls = []

    def boom(target, texts):
        raise RuntimeError("engine exploded")

    out = D.delta_build(_req(docs, root=str(root.parent)), apply_fn=boom,
                        full_builder=lambda items, t: full_calls.append(1),
                        engine_factory=lambda t: FakeEngine({}),
                        policy=canary.load(None))
    assert out["status"] == D.STATUS_FAILED
    assert "engine exploded" in out["reason"]
    assert full_calls == []


# --------------------------------------------------------------------------- J3 / R-3 / R-4 / R-5
def test_j3_four_files_rewritten_from_current_input(tmp_path, monkeypatch) -> None:
    """R-3/R-4/R-5：copytree 带进来的四份旧文件必须被本次输入重算覆盖。"""
    monkeypatch.delenv("LLMKE_CANARY_SCOPE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_MODE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_DEFAULT", raising=False)
    docs = _docs(("A", "甲"), ("B", "乙"))
    root, base = _base_snapshot(tmp_path, files=[("OLD", "旧")], kb_marker={"kb_id": "OTHER"})
    base_sha = {n: _sha(base / n) for n in D.FINAL_FILES}

    out, apply_calls, _full = _run(tmp_path, _req(docs, root=str(root.parent)))
    assert out["status"] == D.STATUS_BUILT
    target = Path(out["snapshot"])
    assert target != base

    # ① sources.json：旧 sentinel / 已删文件都不得留下，且由 live 重算
    sources = json.loads((target / "sources.json").read_text(encoding="utf-8"))
    assert "idx-old" not in sources
    assert "DELETED-FILE" not in json.dumps(sources, ensure_ascii=False)
    assert {ref["file_id"] for refs in sources.values() for ref in refs} == {"A", "B"}
    assert _sha(target / "sources.json") != base_sha["sources.json"]

    # ② community.json：不再是基准 sentinel
    community_text = (target / "community.json").read_text(encoding="utf-8")
    assert "base-community" not in community_text
    assert _sha(target / "community.json") != base_sha["community.json"]

    # ③ kb.json：归属标记被重写成本库
    assert json.loads((target / "kb.json").read_text(encoding="utf-8")) == {"kb_id": KB}
    assert _sha(target / "kb.json") != base_sha["kb.json"]

    # ④ fence.json：L9 不推进 generation，内容语义不变，但**文件确实被重写过**
    fence_doc = json.loads((target / "fence.json").read_text(encoding="utf-8"))
    assert fence_doc == {"generation": 0, "revoked": {}}
    assert _sha(target / "fence.json") != base_sha["fence.json"]   # 基准是 indent=2，我们 compact

    # 响应里回报的 sha 就是落盘值（供 P4 对账）
    assert out["file_shas"]["sources.json"] == _sha(target / "sources.json")


def test_j3_community_receives_live_file_ids(tmp_path, monkeypatch) -> None:
    """community 由**本次 live** 重算：`global_report.write` 收到的 file_ids 就是 live 集合。"""
    monkeypatch.delenv("LLMKE_CANARY_SCOPE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_MODE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_DEFAULT", raising=False)
    docs = _docs(("A", "甲"), ("B", "乙"))
    root, _ = _base_snapshot(tmp_path, files=[("OLD", "旧")])
    seen = []
    real_write = D.global_report.write

    def spy(snapshot, file_ids):
        seen.append({"snapshot": snapshot, "file_ids": list(file_ids)})
        return real_write(snapshot, file_ids)

    monkeypatch.setattr(D.global_report, "write", spy)
    out, _a, _f = _run(tmp_path, _req(docs, root=str(root.parent)))
    assert out["status"] == D.STATUS_BUILT
    assert seen and seen[0]["file_ids"] == ["A", "B"]
    assert seen[0]["snapshot"] == out["snapshot"]


def test_r5_revoked_file_never_reaches_sources(tmp_path, monkeypatch) -> None:
    """R-5：已撤权文件不得出现在 sources.json（fence 从基准快照恢复）。"""
    monkeypatch.delenv("LLMKE_CANARY_SCOPE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_MODE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_DEFAULT", raising=False)
    fence = {"generation": 1, "revoked": {"B": {"reason": "REVOKED", "generation": 1}}}
    docs = _docs(("A", "甲"), ("B", "乙"))
    root, _ = _base_snapshot(tmp_path, files=[("OLD", "旧")], fence=fence)
    out, apply_calls, _f = _run(tmp_path, _req(docs, root=str(root.parent)))
    assert out["status"] == D.STATUS_BUILT
    sources = json.loads((Path(out["snapshot"]) / "sources.json").read_text(encoding="utf-8"))
    fids = {ref["file_id"] for refs in sources.values() for ref in refs}
    assert fids == {"A"}                      # B 已撤权 → 不进 sources
    assert "B" not in json.dumps(sources, ensure_ascii=False).replace("DELETED", "")
    # apply 只拿到存活文本
    assert apply_calls[0]["texts"] == ["甲"]
    assert out["dropped_revoked"] == ["B"]


# --------------------------------------------------------------------------- J5 / R-6
def test_j5_binding_input_no_longer_falls_back_to_kb() -> None:
    """R-6：`_binding_input` 不再回落 `"kb"`，缺 file_id 直接 fail-closed。"""
    chunks = [{"seq": 0, "channel": "text", "pk": 1, "text": "甲",
               "locator": {"kind": "text_span", "source": "parsed_text.md",
                           "start_offset": 0, "end_offset": 1},
               "parse_artifact_id": "c" * 64, "content_uid": "d" * 64}]
    artifact = {"artifact_id": "c" * 64, "content_uid": "d" * 64}
    with pytest.raises(IW.IndexWriterError) as exc:
        IW.bind_chunks(chunks, artifact)
    assert exc.value.code == "FILE_ID_MISSING"
    # 注入了 file_id 就正常（L6/L7 走的路径）
    binding = IW.bind_chunks(chunks, {**artifact, "file_id": "333"})
    assert binding["artifact_id"] == "c" * 64
    assert binding["docs"][0]["file_id"] == "333"


def test_j5_l6_l7_assertions_not_regressed() -> None:
    """J5 回归哨兵：`build` 仍能用注入的 file_id 正常出计划。"""
    chunks = [{"seq": 0, "channel": "text", "pk": 1, "text": "甲",
               "locator": {"kind": "text_span", "source": "parsed_text.md",
                           "start_offset": 0, "end_offset": 1},
               "parse_artifact_id": "c" * 64, "content_uid": "d" * 64}]
    plan = IW.build(chunks, {"artifact_id": "c" * 64, "content_uid": "d" * 64},
                    kb=KB, file_id="333")
    assert plan.es_plan[0]["index_name"] == "v2cand_kb_9"


# --------------------------------------------------------------------------- D-1 等价性
def test_d1_write_sources_byte_identical_to_default_build(tmp_path, monkeypatch) -> None:
    """TL D-1 附加要求：抽出来的 `_write_sources` 与 `_default_build` 内联写法**逐字节相同**。

    否则就是两份实现慢慢漂移，比不抽更糟。这里用假引擎跑**真实** `_default_build`，
    再与 `_write_sources` 的输出做字节对拍。

    注意：`_default_build` 在 `api.py` 里，而 v2 env 无 fastapi → 本用例在 v2 下跳过、
    只在 hipporag 下真跑（与 J1 同一限制，evidence 已注明）。
    """
    pytest.importorskip("fastapi", reason="llmke-v2-toolenv 无 fastapi（既有环境限制）")
    from graph_engine_adapter import api as A
    from graph_engine_adapter import engine_hipporag as EH

    mapping = {"甲": "idx-A", "乙": "idx-B"}

    class FakeEngineClass:
        def __init__(self, *args, **kwargs):
            pass

        def build(self, texts):
            return {"chunks": len(texts)}

        def openie_docs(self):
            return [{"passage": t, "idx": i} for t, i in mapping.items()]

    monkeypatch.setattr(EH, "HippoRAGEngine", FakeEngineClass)
    monkeypatch.setattr(A, "_ensure_cjk_compat", lambda: {"installed": False})

    docs = [SimpleNamespace(file_ids=["A"], text="甲", locator="chunk=0;f=A", title="A.md",
                            pk=11, parse_artifact_id="c" * 64),
            SimpleNamespace(file_ids=["B"], text="乙", locator="chunk=0;f=B", title=None,
                            pk=None, parse_artifact_id=None)]
    built = A._default_build(docs, str(tmp_path / "root-default"))
    default_sources = Path(built["snapshot"]) / "sources.json"

    mine = tmp_path / "mine"
    mine.mkdir()
    D._write_sources(str(mine), D._as_live(docs), FakeEngineClass())

    assert default_sources.is_file() and (mine / "sources.json").is_file()
    assert default_sources.read_bytes() == (mine / "sources.json").read_bytes()


def test_d1_helpers_exist_and_are_private() -> None:
    """D-1：四个 helper 抽到 `delta_build.py`（不能放 api.py，见 D-3 的 import 约束）。"""
    for name in ("_kb_root", "_load_fence", "_write_sources", "_write_kb_json"):
        assert callable(getattr(D, name)), name
    assert D._kb_root("kb_9", "/tmp/x") == "/tmp/x/kb_9"
    assert D._kb_root("", "/tmp/x") == "/tmp/x"


def test_r6_protected_regions_untouched() -> None:
    """R-6：禁改区（`_table_pk`）与关键入口仍在；`delta_build` 无 web 依赖。

    用 AST 查真实 import 节点，而不是 grep 源码文本 —— 否则 docstring 里提到
    「不 import fastapi」这句解释性文字会把守卫误判成违规。
    """
    import ast

    from rag_projection import projection as P

    assert P._table_pk("kb_9", "333", 0) == 885155839145947657
    tree = ast.parse(Path(D.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
            assert not node.level or True        # 相对导入不受限
    assert imported & {"fastapi", "pydantic", "starlette"} == set(), imported

# ------------------------------------------------ 缺陷 9：契约 §2.2 的 apply_result
def test_built_response_carries_apply_result(tmp_path, monkeypatch) -> None:
    """契约 §2.2 要求响应带 `apply_result{deleted,added,reused,duplicates,remaining,expected,consistent}`，
    且 §2.3 不变式 #2 依赖 `apply_result.consistent`。

    实现里**早就有**这些数据（`engine.apply_delta` 返回、`rebuild.py:294` 放进
    `out["apply_result"]`），只是 `delta_build` 拼响应时漏了 —— 本用例锁住「必须透传」。
    """
    monkeypatch.delenv("LLMKE_CANARY_SCOPE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_MODE", raising=False)
    monkeypatch.delenv("LLMKE_CANARY_DEFAULT", raising=False)
    docs = _docs(("A", "甲"), ("B", "乙"))
    root, _base = _base_snapshot(tmp_path, files=[("A", "甲")])

    out, apply_calls, _full = _run(tmp_path, _req(docs, root=str(root.parent)))

    assert out["status"] == D.STATUS_BUILT, out
    assert apply_calls, "delta 分支必须调用 apply_fn"
    assert "apply_result" in out, "契约 §2.2 的 apply_result 不得缺失"
    # 透传 `apply_fn` 的返回值（本替身返回 {"applied": N}），证明「不新造统计」
    assert out["apply_result"] == {"applied": 2}, out["apply_result"]
