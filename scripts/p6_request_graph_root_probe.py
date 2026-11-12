#!/usr/bin/env python3
"""P6-L17 隔离演练：请求级 graph_root + 同源 kb_state，验证「不削」。

零生产风险边界（务必如实读）
----------------------------
- 不启动/停止/重启任何服务，不发外部 HTTP，不写生产图根，不写 ES/Milvus。
- **真实**跑的部分：18096 `IngestRequest` → `KbDeltaService.plan()` →
  `commit_snapshot` / `project_snapshot` / `index_writer.build` / 同源闸门 /
  `commit()` → 状态事务；`wanted_docs` 由同源 kb_state 全量装配（B-1 的风险点）。
  请求经 FastAPI `TestClient` 走真实 `create_app()` 路由，携带 `graph_root`。
- **替身**的部分：`_apply_writes`（不写索引）、delta runner（不调 18094 真实建图，
  只记录 root 与 wanted_docs）。因此本演练**不声称**「图已重建」或「查询可读」，
  只证明以下三条可证伪判据：
    ① `graph_root` 由请求驱动，不是启动期 env 死值；
    ② 同源 state 下逐文件 UPSERT，wanted_docs 始终包含生产 11 个 file_id（不削）；
    ③ 生产 root 的 `current.json` 前后逐字节不变。
- 变异复验：换成 shadow-like state（290/291/292/293）跑同一判据，必须 FAIL。

用法：
    PYTHONPATH=scripts:services/rag-alg/index_data_service \
      <hipporag-toolenv>/bin/python scripts/p6_request_graph_root_probe.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COORD = ROOT.parent / "coordination"
PROD_ROOT = Path("/home/szf/data/dev/llmke-runtime/app/platform/r12/data/graph-root")
PROD_KB = PROD_ROOT / "kb_9"
PROD_SNAP = PROD_KB / "snapshot-20261107212905-365431-g0"
PARSED = Path("/home/szf/data/dev/doc2md/parsed/by_hash")

SHAS = [
    "aa8f26b94de1302f7a776a772e2af465d4b5f6a9241389051728b8d1ce4f9cb2",
    "50f2740f82444c677b23d5bfde02d1edbbedf3ec09da9185a3153432ae0dc62f",
    "efd100b7227067c990d7bfd04f8d2a04ddded47a068af580ed1a4a59d446eceb",
    "f4982001defc71791fa7b5af39db08cb953df151d458da2799aca4abb824b3fc",
    "a846ab142d8d24afe3f552f95888c4b261dd7c8908921a16a2932c4a7838fa1d",
    "53d265c710bc41f1a352030993ede86763cc14eed7df4069e96c4c7ae7e02231",
]

WORK = COORD / ".p6-replica-probe"
REPLICA_ROOT = WORK / "graph-root"
STORE_ROOT = WORK / "artifact-store"
STATE_PATH = WORK / "kb-state" / "kb_state.json"
ENV_FIXED_ROOT = "/env/FIXED-STARTUP-ROOT"   # 故意与请求值不同，用于证伪
ENV_ROOT = str(REPLICA_ROOT)                 # 请求级 graph_root


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prod_files() -> list[str]:
    cur = json.loads((PROD_KB / "current.json").read_text(encoding="utf-8"))
    return [str(x) for x in cur["fingerprint"]["files"]]


def derive_state(files: list[str], only_shadow: bool = False) -> dict:
    """从生产快照派生 kb_state（46 行 / 11 file_id）。

    这是**从快照派生的重建 state**，不是原始解析产物：sources.json 给
    idx→file_id/locator，openie 结果给 idx→passage。如实标注，不冒充原件。
    """
    sources = json.loads((PROD_SNAP / "sources.json").read_text(encoding="utf-8"))
    openie = json.loads(
        (PROD_SNAP / "openie_results_ner_qwen2.5-7b-instruct.json").read_text(
            encoding="utf-8"))
    passage = {d["idx"]: d.get("passage", "") for d in openie["docs"]}

    keep = {"290", "291", "292", "293"} if only_shadow else set(files)
    chunks: dict[str, list] = defaultdict(list)
    kb: dict[str, dict] = {}
    for idx, srcs in sources.items():
        text = passage.get(idx, "")
        for s in srcs:
            fid = str(s["file_id"])
            if only_shadow and fid not in keep:
                # 变异体：把生产 11 份压成 shadow 4 份，文本仍取自生产快照
                fid = "290" if fid in files else fid
                if fid not in keep:
                    continue
            elif fid not in keep:
                continue
            chunks[fid].append({
                "text": text,
                "locator": s.get("locator", ""),
                "pk": int(hashlib.sha256(f"{fid}:{idx}".encode()).hexdigest()[:15], 16),
                "seq": len(chunks[fid]),
                "channel": "text",
                "content_hash": hashlib.sha256(text.encode()).hexdigest(),
                "parse_artifact_id": "derived-from-prod-snapshot",
            })
            kb[fid] = {"status": "ACTIVE", "file_name": s.get("title", "")}
    if only_shadow:
        for fid in ("291", "292", "293"):
            kb.setdefault(fid, {"status": "ACTIVE", "file_name": "shadow-c5"})
            chunks.setdefault(fid, [{"text": f"shadow fixture {fid}",
                                     "locator": "chunk=0;offset=0-18", "pk": 1,
                                     "seq": 0, "channel": "text",
                                     "content_hash": hashlib.sha256(
                                         f"shadow fixture {fid}".encode()).hexdigest(),
                                     "parse_artifact_id": "derived-shadow"}])
    # v2 形状（kb_pipeline.KB_STATE_SCHEMA）；缺 schema 会被当 v1 迁移而拒绝。
    # cursor / set_digest / version 由 _kb_state_txn 在真实提交时推进。
    return {"schema": "llmke.kb-state/2", "version": 1,
            "cursor": None, "set_digest": None,
            "chunks": {"kb_9": dict(chunks)}, "kb": {"kb_9": kb}, "graph": {}}


def setup(state: dict, prod_current_sha: str) -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    (REPLICA_ROOT / "kb_9").mkdir(parents=True)
    STORE_ROOT.mkdir(parents=True)
    STATE_PATH.parent.mkdir(parents=True)
    shutil.copyfile(PROD_KB / "current.json", REPLICA_ROOT / "kb_9" / "current.json")
    assert sha256(REPLICA_ROOT / "kb_9" / "current.json") == prod_current_sha
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    for key, val in {
        "LLMKE_V2_GRAPH_ROOT": ENV_FIXED_ROOT,
        "LLMKE_ARTIFACT_STORE": str(STORE_ROOT),
        "LLMKE_KB_STATE": str(STATE_PATH),
        "LLMKE_DOC2MD_LOCK": str(COORD / "doc2md.lock"),
        "LLMKE_DOC2MD_CONFIG": "/home/szf/data/dev/doc2md/config/app.yaml",
        "LLMKE_ES_BASE_URL": "http://127.0.0.1:1",
        "LLMKE_MILVUS_BASE_URL": "http://127.0.0.1:1",
        "LLMKE_V2_GRAPH_API": "http://127.0.0.1:18094",
    }.items():
        os.environ[key] = val


def run_scenario(n_posts: int, first_file_id: int) -> dict:
    sys.path.insert(0, str(ROOT / "services/rag-alg/index_data_service"))
    import kb_ingest_service as S
    from fastapi.testclient import TestClient
    from ingest_pipeline.kb_delta import KbDeltaService

    binds: list[dict] = []
    deltas: list[dict] = []

    def record(plan, root):
        deltas.append({
            "root": root,
            "n_docs": len(plan.wanted_docs),
            "file_ids": sorted({str(d["file_id"]) for d in plan.wanted_docs}),
            "removed": list(plan.removed),
        })
        return {"status": "BUILT"}

    def factory(graph_api=None, graph_root=None):
        binds.append({"graph_api": graph_api, "graph_root": graph_root})
        return KbDeltaService(
            str(STORE_ROOT),
            delta=lambda plan, _r=graph_root: record(plan, _r),
            revoke=None,
            producer_inputs_provider=S._producer_inputs,
            es_base="http://127.0.0.1:1",
            milvus_base="http://127.0.0.1:1",
        )

    # 不写 ES/Milvus：只替换这一处，plan/commit/wanted_docs 全为真实实现
    KbDeltaService._apply_writes = lambda self, plan: {
        "status": "NOT_APPLICABLE", "applied": False, "required": False,
        "reason": "isolated probe: no external index writes"}
    S._build_service = factory
    client = TestClient(S.create_app())

    statuses = []
    for i in range(n_posts):
        h = SHAS[i % len(SHAS)]
        doc2md_dir = PARSED / h[:2] / h[2:4] / h
        body = {"kb": "kb_9", "file_id": first_file_id + i,
                "operation": "UPSERT", "doc2md_dir": str(doc2md_dir),
                "file_name": f"p6-probe-{i}.bin", "graph_root": ENV_ROOT}
        r = client.post("/kb/ingest", json=body)
        body = r.json()
        statuses.append({"http": r.status_code,
                         "status": (body.get("data") or {}).get("status"),
                         "msg": body.get("msg")})

    # 重复同一请求 → 应 SKIPPED_FRESH（零 delta 调用）。
    # 幂等键口径：请求 content_hash 必须等于 state 落盘的 content_hash
    # （kb_delta.diff:364-369），故从真实落盘 state 取值，不自己编。
    state_now = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    prior = ((state_now.get("kb") or {}).get("kb_9") or {}).get(
        str(first_file_id)) or {}
    h = SHAS[0]
    repeat_body = {"kb": "kb_9", "file_id": first_file_id,
                   "operation": "UPSERT",
                   "doc2md_dir": str(PARSED / h[:2] / h[2:4] / h),
                   "file_name": "p6-probe-0.bin",
                   "content_hash": prior.get("content_hash"),
                   "graph_root": ENV_ROOT}
    before = len(deltas)
    r = client.post("/kb/ingest", json=repeat_body)
    repeat = {"http": r.status_code,
              "status": (r.json().get("data") or {}).get("status"),
              "delta_calls": len(deltas) - before,
              "prior_content_hash": prior.get("content_hash")}
    return {"binds": binds, "deltas": deltas, "statuses": statuses,
            "repeat": repeat}


def assert_scenario(out: dict, prod_files_expected: list[str]) -> dict:
    binds, deltas = out["binds"], out["deltas"]
    # ① 请求驱动：每次按请求重建的绑定值必须等于请求 root，且不等于 env 死值
    req_binds = [b for b in binds if b["graph_root"] == ENV_ROOT]
    assert len(req_binds) == len(out["statuses"]) + 1, binds
    assert all(d["root"] == ENV_ROOT for d in deltas), deltas
    assert all(b["graph_root"] != ENV_FIXED_ROOT for b in req_binds)
    # ② 不削：每次 wanted_docs 都包含生产 11 个 file_id，且 removed 恒空
    for d in deltas:
        missing = sorted(set(prod_files_expected) - set(d["file_ids"]))
        assert not missing, f"wanted_docs 缺生产 file_id: {missing}"
        assert d["removed"] == [], d
    counts = [d["n_docs"] for d in deltas]
    assert counts == sorted(counts), counts     # 单调不减
    assert all(s["http"] == 200 and s["status"] == "OK" for s in out["statuses"]), out["statuses"]
    # ③ 重复短路
    assert out["repeat"]["status"] == "SKIPPED_FRESH" and out["repeat"]["delta_calls"] == 0, out["repeat"]
    return {"posts": len(out["statuses"]), "delta_calls": len(deltas),
            "n_docs_first": counts[0], "n_docs_last": counts[-1],
            "prod_file_ids_kept": len(prod_files_expected),
            "request_roots": len(req_binds),
            "removed_total": sum(len(d["removed"]) for d in deltas),
            "repeat": out["repeat"]}


def main() -> int:
    prod_before = sha256(PROD_KB / "current.json")
    files = prod_files()
    assert len(files) == 11, files

    state = derive_state(files)
    derived_rows = sum(len(v) for v in state["chunks"]["kb_9"].values())
    derived_files = sorted(state["kb"]["kb_9"])
    # 同源硬校验：派生 state 的行数/文件集必须与生产 current.json 指纹一致
    assert derived_rows == 46 and derived_files == sorted(files), (
        f"派生 state 与生产指纹不符: rows={derived_rows} files={derived_files}")
    setup(state, prod_before)
    good = assert_scenario(run_scenario(6, 990201), files)

    # 变异复验：换成 shadow-like state，同一「不削」判据必须 FAIL
    setup(derive_state(files, only_shadow=True), prod_before)
    mutant = run_scenario(1, 990301)
    mutant_failed = False
    try:
        assert_scenario(mutant, files)
    except AssertionError as exc:
        mutant_failed = True
        mutant_reason = str(exc)[:160]
    assert mutant_failed, "变异体未 FAIL → 断言空转，演练无效"

    prod_after = sha256(PROD_KB / "current.json")
    assert prod_before == prod_after, "生产 current.json 被改动了！"

    print(json.dumps({
        "verdict": "PASS",
        "prod_current_sha256_before": prod_before,
        "prod_current_sha256_after": prod_after,
        "prod_file_ids": files,
        "derived_state": {"rows": derived_rows, "file_ids": derived_files,
                          "source": "prod snapshot sources.json + openie passages"},
        "env_fixed_root": ENV_FIXED_ROOT,
        "request_graph_root": ENV_ROOT,
        "isolation": "no service restart / no external HTTP / no ES-Milvus / no prod root write",
        "substitutes": ["_apply_writes", "delta runner (no real 18094 graph rebuild)"],
        "main": good,
        "mutation": {"detected": mutant_failed, "reason": mutant_reason,
                     "mutant_file_ids": mutant["deltas"][0]["file_ids"] if mutant["deltas"] else []},
    }, ensure_ascii=False, indent=2))
    shutil.rmtree(WORK, ignore_errors=True)
    print(f"[cleanup] removed {WORK}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
