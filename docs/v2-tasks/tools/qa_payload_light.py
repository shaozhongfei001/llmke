#!/usr/bin/env python3
"""A 方案（轻量签署）· 待签 payload 生成器。

用途
----
把「已完成内部收口的 loop」事实清单、证据文件指纹、独立复跑结果打成一个
**未签名** payload，交给持有私钥的独立 QA 主体用既有 `scripts/qa_sign.py` 签名。

设计约束（不得放宽）
--------------------
- 本脚本**不生成密钥、不签名、不写 QA_PASS**；只产出 UNSIGNED payload。
- 私钥必须由 QA 一方在受保护位置生成与保管（`qa_sign.py` 会强制检查私钥在工作区外）。
- `canonical` 口径与 `scripts/contract_runtime.canonical` 一致，保证签名可被
  `qa_verify_light.py` / 既有 `verify_envelope` 复验。
- 本脚本放在 `docs/v2-tasks/tools/`：该目录**不在冻结基线控制面**内
  （`freeze_baseline.controls()` 0 命中），新增不改变 `FROZEN-MANIFEST`。

用法
----
    # 1) 只打事实清单（不跑测试）
    PYTHONPATH=. /home/szf/data/dev/llmke-v2-toolenv/bin/python \
        docs/v2-tasks/tools/qa_payload_light.py \
        --principal-id qa-owner-xxxx --out /tmp/qa-batch.json

    # 2) 事实清单 + 独立复跑（推荐）
    ... qa_payload_light.py --principal-id qa-owner-xxxx \
        --fill-verification --out /tmp/qa-batch.json

    # 3) 签名（在持有私钥的受保护位置跑；私钥不得进工作区）
    PYTHONPATH=. python3 scripts/qa_sign.py \
        --key-file ~/data/qa-keys/llmke-qa.key --key-id qa-ed25519-202611 \
        --payload /tmp/qa-batch.json --out /tmp/qa-envelope.json

    # 4) 验签
    /home/szf/data/dev/llmke-v2-toolenv/bin/python \
        docs/v2-tasks/tools/qa_verify_light.py \
        --trust-root /path/to/trust-root.json --envelope /tmp/qa-envelope.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # /home/szf/data/dev/llmke-v2
TASKS = ROOT / "docs/v2-tasks/TASKS.yaml"
CHECKPOINT = ROOT / "docs/v2-tasks/CHECKPOINT-VL-DOC2MD-INC.md"
SLICE = "VL-DOC2MD-INC"
SCHEMA = "llmke.qa-attestation-light/1"

V2_PY = "/home/szf/data/dev/llmke-v2-toolenv/bin/python"
D2MD = Path("/home/szf/data/dev/doc2md")
D2MD_PY = "/home/szf/data/dev/doc2md-toolenv/bin/python"
IDX = "services/rag-alg/index_data_service"

# 每个 loop 的独立复跑命令（只读、离线、不启停服务、不写线上存储）
RERUN = {
    "P1-L1": {"cwd": str(D2MD), "cmd": [D2MD_PY, "-m", "pytest", "backend/tests/test_kb_diff.py", "-q"],
              "env": {"PYTHONPATH": "backend"}},
    "P1-L2": {"cwd": str(D2MD), "cmd": [D2MD_PY, "-m", "pytest", "backend/tests/test_parse_queue.py", "-q"],
              "env": {"PYTHONPATH": "backend"}},
    "P1-L3": {"cwd": str(D2MD), "cmd": [D2MD_PY, "-m", "pytest", "backend/tests/test_idempotency_key.py", "-q"],
              "env": {"PYTHONPATH": "backend"}},
    "P1-L4": {"cwd": str(D2MD), "cmd": [D2MD_PY, "-m", "pytest", "backend/tests/test_pdf_fourth_artifact.py", "-q"],
              "env": {"PYTHONPATH": "backend"}},
    "P1-L5": {"cwd": str(ROOT), "cmd": [V2_PY, "-m", "pytest",
                                        f"{IDX}/tests/test_table_projection.py",
                                        "tests/test_rag_projection.py", "-q"],
              "env": {"PYTHONPATH": IDX}},
    "P2-L6": {"cwd": str(ROOT), "cmd": [V2_PY, "-m", "pytest",
                                        f"{IDX}/tests/test_index_writer.py",
                                        f"{IDX}/tests/test_table_projection.py",
                                        "tests/test_rag_projection.py", "-q"],
              "env": {"PYTHONPATH": IDX}},
}


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_tasks() -> list[dict]:
    import yaml  # 由 llmke-v2-toolenv 提供
    data = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
    tasks = data.get("tasks", data) if isinstance(data, dict) else data
    return list(tasks or [])


def collect_loops() -> list[dict]:
    """已完成内部收口 = evidence 非空且 blocker 含 WAIT_QA_ATTESTATION。"""
    out = []
    for t in load_tasks():
        tid = str(t.get("id", ""))
        if not tid.startswith("T-D2MD"):
            continue
        ev = str(t.get("evidence") or "").strip()
        blocker = str(t.get("blocker") or "")
        if not ev or "WAIT_QA_ATTESTATION" not in blocker:
            continue
        ev_path = ROOT / ev
        tl_logs = sorted((ROOT / "docs/v2-tasks/evidence").glob(f"{t.get('loop')}-TL-VERIFY-*.log"))
        out.append({
            "loop_id": t.get("loop"),
            "task_id": tid,
            "title": t.get("title"),
            "state": t.get("state"),
            "evidence": ev,
            "evidence_sha256": file_sha(ev_path),
            "evidence_lines": sum(1 for _ in ev_path.open(encoding="utf-8")) if ev_path.is_file() else None,
            "tl_verify": [str(p.relative_to(ROOT)) for p in tl_logs],
            "tl_verify_sha256": {str(p.relative_to(ROOT)): file_sha(p) for p in tl_logs},
        })
    return out


def rerun(loop_id: str) -> dict:
    spec = RERUN.get(loop_id)
    if not spec:
        return {"status": "NOT_CONFIGURED"}
    env = dict(**__import__("os").environ)
    env.update(spec.get("env") or {})
    try:
        p = subprocess.run(spec["cmd"], cwd=spec["cwd"], env=env,
                           capture_output=True, text=True, timeout=900, shell=False)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "cmd": " ".join(spec["cmd"])}
    tail = (p.stdout + p.stderr).strip().splitlines()[-1:] or [""]
    return {
        "status": "PASS" if p.returncode == 0 else "FAIL",
        "exit_code": p.returncode,
        "cmd": " ".join(spec["cmd"]),
        "cwd": spec["cwd"],
        "interpreter": spec["cmd"][0],
        "tail": tail[0][:240],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--principal-id", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fill-verification", action="store_true",
                    help="对每个 loop 独立复跑验收命令并写入 verification.rerun")
    ap.add_argument("--mutation", action="append", default=[],
                    help="抽样变异记录：LOOP::变异说明::实际结果（可重复）")
    ap.add_argument("--only", default="", help="逗号分隔，只纳入指定 loop")
    args = ap.parse_args()

    loops = collect_loops()
    if args.only:
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        loops = [x for x in loops if x["loop_id"] in want]
    if not loops:
        print("FAIL: 没有可纳入的 loop（检查 TASKS.yaml 的 evidence/blocker）", file=sys.stderr)
        return 1

    missing = [x["loop_id"] for x in loops if not x["evidence_sha256"]]
    if missing:
        print(f"FAIL: evidence 缺失 {missing}", file=sys.stderr)
        return 1

    verification = {"rerun": {}, "mutation": []}
    if args.fill_verification:
        for item in loops:
            verification["rerun"][item["loop_id"]] = rerun(item["loop_id"])
    for raw in args.mutation:
        parts = raw.split("::")
        verification["mutation"].append({
            "loop_id": parts[0] if parts else raw,
            "what": parts[1] if len(parts) > 1 else "",
            "actual": parts[2] if len(parts) > 2 else "",
        })

    now = datetime.now(timezone.utc)
    payload = {
        "purpose": "QA_ATTESTATION",
        "schema": SCHEMA,
        "slice": SLICE,
        "principal_id": args.principal_id,
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "fact_source": {
            "checkpoint": str(CHECKPOINT.relative_to(ROOT)),
            "checkpoint_sha256": file_sha(CHECKPOINT),
            "tasks": str(TASKS.relative_to(ROOT)),
            "tasks_sha256": file_sha(TASKS),
        },
        "loops": loops,
        "batch_digest": digest(loops),
        "verification": verification,
        "scope_note": (
            "本 payload 为 A 方案轻量签署：只背书所列 loop 的证据文件指纹、TL 复核记录"
            "与 verification 段中的独立复跑/抽样变异结果；不改变 TASKS.yaml 的 state，"
            "不代表 snapshot 已可切读。"
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical(payload) + b"\n")
    print(f"UNSIGNED_QA_PAYLOAD  loops={len(loops)}  batch_digest={payload['batch_digest'][:16]}…")
    for item in loops:
        v = verification["rerun"].get(item["loop_id"]) if verification["rerun"] else None
        mark = f"  rerun={v['status']}" if v else ""
        print(f"  {item['loop_id']:6s} {item['task_id']}  {item['evidence_sha256'][:12]}…{mark}")
    if verification["rerun"]:
        bad = [k for k, v in verification["rerun"].items() if v.get("status") != "PASS"]
        if bad:
            print(f"WARN: 复跑未全 PASS -> {bad}（签署前请先处理）", file=sys.stderr)
    print(f"payload -> {args.out}")
    print("下一步：在持有私钥的受保护位置用 scripts/qa_sign.py 签名，再用 qa_verify_light.py 验签")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
