#!/usr/bin/env python3
"""A 方案（轻量签署）· 独立验签器。

用途
----
对独立 QA 主体用 `scripts/qa_sign.py` 产出的 Ed25519 信封做四类校验：
1) 信任根：`environment=PROTECTED_RUNNER`、`key_id` 存在且 enabled、`roles` 含 `qa-owner`；
2) 主体：`payload.principal_id` 与信任根一致，且**不在实现方列表**内；
3) 密码学校验：`openssl pkeyutl -verify -pubin -rawin`；
4) 事实绑定：逐个 loop 的 evidence / TL 复核文件**当前** sha256 与 payload 记录一致，
   `batch_digest` 可由 `loops` 复算得出（签完被改即失败）。

只做验证，**不写 QA_PASS、不改 TASKS.yaml**。验签通过后由 TL 手动记录签署结果。

用法
----
    /home/szf/data/dev/llmke-v2-toolenv/bin/python \
        docs/v2-tasks/tools/qa_verify_light.py \
        --trust-root /etc/llmke/trust-root.json \
        --envelope /tmp/qa-envelope.json \
        --implementation-principals python-engineer,integration-agent,legacy-owner,tech-lead

    # 只看密码学与信任根，不比对证据文件：
    ... --no-evidence-check
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = "llmke.qa-attestation-light/1"
PURPOSE = "QA_ATTESTATION"


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class VerifyError(RuntimeError):
    pass


def verify_signature(public_pem: str, payload_bytes: bytes, signature: bytes) -> None:
    with tempfile.TemporaryDirectory(prefix="llmke-verify-") as d:
        d = Path(d)
        (d / "public.pem").write_text(public_pem, encoding="utf-8")
        (d / "payload").write_bytes(payload_bytes)
        (d / "sig").write_bytes(signature)
        proc = subprocess.run(
            ["openssl", "pkeyutl", "-verify", "-pubin",
             "-inkey", str(d / "public.pem"), "-rawin",
             "-in", str(d / "payload"), "-sigfile", str(d / "sig")],
            capture_output=True, text=True, timeout=20)
    if proc.returncode != 0:
        raise VerifyError(f"Ed25519 签名校验失败：{(proc.stdout + proc.stderr).strip()[:200]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trust-root", type=Path, required=True)
    ap.add_argument("--envelope", type=Path, required=True)
    ap.add_argument("--implementation-principals",
                    default="python-engineer,integration-agent,legacy-owner,tech-lead",
                    help="实现方 principal 列表（逗号分隔），QA principal 不得出现在其中")
    ap.add_argument("--no-evidence-check", action="store_true")
    args = ap.parse_args()

    problems: list[str] = []
    try:
        trust = json.loads(args.trust_root.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: 信任根不可读：{exc}", file=sys.stderr)
        return 1
    if trust.get("environment") != "PROTECTED_RUNNER":
        problems.append(f"environment={trust.get('environment')!r}，要求 PROTECTED_RUNNER")
    tr = args.trust_root.resolve()
    if tr.is_relative_to(ROOT.resolve()):
        problems.append("信任根位于实现工作区内（必须放工作区外）")

    try:
        envelope = json.loads(args.envelope.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: 信封不可读：{exc}", file=sys.stderr)
        return 1

    key_id = envelope.get("key_id")
    payload = envelope.get("payload") or {}
    sig_b64 = envelope.get("signature")
    principal = (trust.get("principals") or {}).get(key_id) or {}

    if not principal:
        problems.append(f"信任根无 key_id={key_id!r}")
    elif not principal.get("enabled"):
        problems.append(f"key_id={key_id!r} 未 enabled")
    elif "qa-owner" not in (principal.get("roles") or []):
        problems.append(f"key_id={key_id!r} 缺 qa-owner 角色")

    if payload.get("purpose") != PURPOSE:
        problems.append(f"purpose={payload.get('purpose')!r}，要求 {PURPOSE}")
    if payload.get("schema") != SCHEMA:
        problems.append(f"schema={payload.get('schema')!r}，要求 {SCHEMA}")

    principal_id = payload.get("principal_id")
    if principal and principal_id != principal.get("principal_id"):
        problems.append(f"payload.principal_id={principal_id!r} 与信任根 {principal.get('principal_id')!r} 不一致")
    impl = {x.strip() for x in args.implementation_principals.split(",") if x.strip()}
    if principal_id in impl:
        problems.append(f"principal_id={principal_id!r} 属实现方，不构成独立 QA")

    now = datetime.now(timezone.utc)
    try:
        issued = datetime.fromisoformat(str(payload["issued_at"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(payload["expires_at"]).replace("Z", "+00:00"))
        if expires <= now:
            problems.append(f"载荷已过期（expires_at={payload['expires_at']}）")
        if expires - issued > timedelta(days=7):
            problems.append("有效期超过 7 天")
        if issued - now > timedelta(minutes=5):
            problems.append("issued_at 在未来")
    except Exception:  # noqa: BLE001
        problems.append("issued_at / expires_at 格式非法")

    loops = payload.get("loops") or []
    if not loops:
        problems.append("loops 为空")
    if payload.get("batch_digest") != sha256_bytes(canonical(loops)):
        problems.append("batch_digest 与 loops 复算不一致（载荷被改过）")

    if not args.no_evidence_check:
        for item in loops:
            ev = item.get("evidence")
            recorded = item.get("evidence_sha256")
            if not ev:
                problems.append(f"{item.get('loop_id')}: 缺 evidence 路径")
                continue
            actual = file_sha(ROOT / ev)
            if actual is None:
                problems.append(f"{item.get('loop_id')}: evidence 文件不存在 {ev}")
            elif actual != recorded:
                problems.append(f"{item.get('loop_id')}: evidence 已被改动（{ev}）")
            for rel, want in (item.get("tl_verify_sha256") or {}).items():
                got = file_sha(ROOT / rel)
                if got != want:
                    problems.append(f"{item.get('loop_id')}: TL 复核记录已被改动（{rel}）")

    if principal.get("public_key_pem") and sig_b64:
        try:
            verify_signature(principal["public_key_pem"],
                             canonical(payload), base64.b64decode(sig_b64, validate=True))
        except Exception as exc:  # noqa: BLE001
            problems.append(str(exc))
    else:
        problems.append("缺 public_key_pem 或 signature，无法做密码学校验")

    if problems:
        print("FAIL: QA 轻量签署未通过，问题如下：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    rerun = (payload.get("verification") or {}).get("rerun") or {}
    print("QA_LIGHT_ATTESTATION_VERIFIED")
    print(f"  principal_id = {principal_id}")
    print(f"  key_id       = {key_id}")
    print(f"  batch_digest = {payload.get('batch_digest')}")
    print(f"  loops        = {len(loops)}")
    for item in loops:
        v = rerun.get(item.get("loop_id")) or {}
        print(f"    {item.get('loop_id'):6s} {item.get('task_id')}  "
              f"evidence={str(item.get('evidence_sha256'))[:12]}…  "
              f"rerun={v.get('status', 'NOT_RUN')}")
    muts = (payload.get("verification") or {}).get("mutation") or []
    print(f"  mutation_samples = {len(muts)}")
    print("  提示：验签通过≠已写 QA_PASS；由 TL 记录签署结果并更新 TASKS.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
