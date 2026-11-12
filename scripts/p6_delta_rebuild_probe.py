#!/usr/bin/env python3
"""P6-L17 隔离副本演练：让 delta **真实执行重建分支**，验证「重建后不削」。

背景
----
STEP2-M 生产窗口的 6 份 POST 都判 `freshness.stale=False` → `SKIPPED_FRESH` 零重建，
所以「delta 重建分支执行后仍不削」尚未验证。本脚本补上这一块，**不碰生产**。

方法（零生产风险）
------------------
- 复制生产 `kb_9/`（current.json + 2 个快照）到隔离副本 root，并把副本指针的
  `dir`/`previous` 改指向副本内快照，确保 `rebuild_delta` 的 `base_dir` 不指向生产。
- 从生产快照派生同源 `live`（46 行 / 11 file_id），**改动其中 1 块文本** →
  `check_freshness` 判 `changed` → `stale=True` → `delta_build` 走 `rebuild_delta`。
- 进程内直接调 `graph_engine_adapter.delta_build.delta_build()`，不启服务、不发 HTTP、
  不写 ES/Milvus、不碰生产 18094 进程。
- 验收：重建后副本 `current.json` 的 `fingerprint.files` 仍为 11 个、`documents=46`、
  新快照含 sources/kb.json/community、旧 file_id 的块仍在 sources.json；
  生产 `current.json` sha256 前后不变。
- **变异复验**：换成 shadow 4 文件 live，同一「11 个全在」判据必须 FAIL。

用法：
    python scripts/p6_delta_rebuild_probe.py            # 真实 apply_fn（调 LLM/embed）
    python scripts/p6_delta_rebuild_probe.py --light    # 轻量 apply_fn（不调 LLM，仍真实走 rebuild_delta/_promote）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/rag-alg/index_data_service"))
sys.path.insert(0, str(ROOT / "scripts"))

PROD_KB = Path("/home/szf/data/dev/llmke-runtime/app/platform/r12/data/graph-root/kb_9")
PROD_CURRENT = PROD_KB / "current.json"
BACKUP = Path("/home/szf/data/dev/coordination/p6-window-20261112")
REPLICA = BACKUP / "replica"
SNAP_MAIN = "snapshot-20261107212905-365431-g0"
SNAP_PREV = "snapshot-20261106214944-511715-g0"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def setup_replica(case: str) -> Path:
    """复制生产 kb_9 到副本，并把指针改到副本内部（关键：不指向生产）。"""
    base = REPLICA / case / "graph-root"
    if base.exists():
        shutil.rmtree(base)
    kbdir = base / "kb_9"
    kbdir.mkdir(parents=True)
    for snap in sorted(PROD_KB.glob("snapshot-*")):
        shutil.copytree(snap, kbdir / snap.name)
    cur = json.loads(PROD_CURRENT.read_text(encoding="utf-8"))
    cur["dir"] = str(kbdir / SNAP_MAIN)
    cur["previous"] = str(kbdir / SNAP_PREV)
    (kbdir / "current.json").write_text(
        json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    (kbdir / ".pointer.lock").touch()
    return base


def build_live(*, mutate: bool, shadow: bool) -> list[dict]:
    from p6_request_graph_root_probe import derive_state, prod_files

    state = derive_state(prod_files(), only_shadow=shadow)
    docs: list[dict] = []
    for fid in sorted(state["chunks"]["kb_9"], key=str):
        for chunk in state["chunks"]["kb_9"][fid]:
            docs.append({
                "file_id": str(fid), "text": chunk["text"],
                "locator": chunk["locator"], "pk": chunk["pk"],
                "title": (state["kb"]["kb_9"][fid] or {}).get("file_name", ""),
            })
    if mutate and docs:
        docs[0]["text"] += " [P6-DELTA-REBUILD-PROBE]"
    return docs


def light_apply(target: str, texts: list[str]) -> dict:
    """不调 LLM 的替身：只让 rebuild_delta 走完 copytree/_promote/收口。

    注意：指纹由 `_promote` 从 live 全量计算，与 apply_fn 无关，故「不削」判据仍有效；
    但图内容未经 LLM 重抽，证据里必须如实标注。
    """
    return {"deleted": 0, "added": 0, "reused": len(texts), "duplicates": 0,
            "remaining": len(texts), "expected": len(texts), "consistent": True,
            "probe": "light-apply (no LLM)"}


def run_case(case: str, *, shadow: bool, light: bool) -> dict:
    from graph_engine_adapter.delta_build import delta_build

    base = setup_replica(case)
    kbdir = base / "kb_9"
    before = json.loads((kbdir / "current.json").read_text(encoding="utf-8"))
    live = build_live(mutate=True, shadow=shadow)
    req = SimpleNamespace(kb="kb_9", docs=live, root=str(base),
                          requested_mode="auto", fallback_reason=None, fencing=None)
    kw = {"apply_fn": light_apply} if light else {}
    started = time.time()
    out = delta_build(req, **kw)
    elapsed = round(time.time() - started, 2)

    after = json.loads((kbdir / "current.json").read_text(encoding="utf-8"))
    new_snap = Path(after["dir"])
    sources = {}
    if (new_snap / "sources.json").is_file():
        sources = json.loads((new_snap / "sources.json").read_text(encoding="utf-8"))
    source_fids = sorted({str(s.get("file_id")) for v in sources.values() for s in v})
    return {
        "case": case,
        "elapsed_s": elapsed,
        "live_rows": len(live),
        "live_file_ids": sorted({d["file_id"] for d in live}),
        "status": out.get("status"),
        "effective_mode": out.get("effective_mode"),
        "freshness": out.get("freshness"),
        "before": {"documents": before["documents"],
                   "files": before["fingerprint"]["files"],
                   "dir": before["dir"]},
        "after": {"documents": after["documents"],
                  "files": after["fingerprint"]["files"],
                  "mode": after.get("mode"), "dir": after["dir"],
                  "generation": after.get("generation"),
                  "fencing": after.get("fencing")},
        "new_snapshot_exists": new_snap.is_dir(),
        "new_snapshot_files": sorted(p.name for p in new_snap.iterdir()) if new_snap.is_dir() else [],
        "sources_file_ids": source_fids,
        "apply_result": out.get("apply_result"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--light", action="store_true")
    args = ap.parse_args()

    prod_before = sha256(PROD_CURRENT)
    if REPLICA.exists():
        shutil.rmtree(REPLICA)
    REPLICA.mkdir(parents=True)

    main_case = run_case("case-main", shadow=False, light=args.light)
    # 主场景验收
    expected = main_case["before"]["files"]
    assert main_case["status"] == "BUILT", main_case
    assert main_case["effective_mode"] == "DELTA", main_case
    assert main_case["freshness"]["stale"] is True, main_case
    assert main_case["after"]["files"] == expected, "重建后 file_id 集合被削/被改"
    assert main_case["after"]["documents"] == 46, main_case
    assert main_case["after"]["dir"] != main_case["before"]["dir"], "指针未推进"
    assert str(REPLICA) in main_case["after"]["dir"], "重建落点不在副本内"
    assert main_case["new_snapshot_exists"], "新快照目录缺失"
    kept = [f for f in expected if f in main_case["sources_file_ids"]]
    assert len(kept) >= 10, f"sources.json 旧块保留不足: {kept}"

    # 变异复验：shadow 4 文件 live，同一「11 个全在」判据必须 FAIL
    mutant = run_case("case-mutant", shadow=True, light=args.light)
    mutant_detected = False
    reason = ""
    lost = sorted(set(expected) - set(mutant["after"]["files"]))
    try:
        # 对变异体执行与主场景**同一个**「11 个全在」判据；它必须 FAIL，
        # 否则说明主场景的断言在任何输入下都成立（空转）。
        assert mutant["after"]["files"] == expected, (
            f"mutant lost prod file_ids: {lost}")
    except AssertionError as exc:
        mutant_detected = True
        reason = str(exc)[:200]
    assert mutant_detected, "变异体未 FAIL → 断言空转，演练无效"
    assert len(lost) >= 7, f"变异体丢失数不足，判据可疑: {lost}"

    prod_after = sha256(PROD_CURRENT)
    assert prod_before == prod_after, "生产 current.json 被改动了！"

    result = {
        "verdict": "PASS",
        "apply_mode": "light (no LLM, 替身已标注)" if args.light else "real (_default_apply, 调 LLM/embed)",
        "prod_current_sha256_before": prod_before,
        "prod_current_sha256_after": prod_after,
        "isolation": "replica root only; no service restart / no HTTP / no ES-Milvus / no prod graph write",
        "main": main_case,
        "mutation": {"detected": mutant_detected, "reason": reason,
                     "mutant_after_files": mutant["after"]["files"]},
    }
    out = BACKUP / "delta-rebuild-probe.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "main"},
                     ensure_ascii=False, indent=2))
    print("main.status=", main_case["status"], "effective_mode=", main_case["effective_mode"],
          "freshness.stale=", main_case["freshness"]["stale"],
          "after.documents=", main_case["after"]["documents"],
          "after.files=", main_case["after"]["files"])
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
