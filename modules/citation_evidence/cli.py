"""命令行入口。

- `assemble`：组装 DocumentEvidence（fail-closed，失败退出码 2）
- `audit`：支持率审计（读契约阈值，未达标退出码 2）

兼容：不写子命令时默认按 `assemble` 处理（历史调用 `--input ...` 仍可用）。
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

from .assembler import (EvidenceError, audit_support, build_document_evidence,
                        validate_evidence)

SUBCOMMANDS = ("assemble", "audit")


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="citation-evidence")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("assemble", help="组装并校验 DocumentEvidence")
    p1.add_argument("--input", type=Path, required=True,
                    help="JSON: {evidence_id, document_text, source}")
    p1.add_argument("--out", type=Path)
    p1.add_argument("--repo-root", type=Path, default=Path("."))
    p1.add_argument("--no-contract-check", action="store_true")

    p2 = sub.add_parser("audit", help="支持率审计（阈值来自契约）")
    p2.add_argument("--claims", type=Path, required=True,
                    help="JSON：claim 数组，或 {\"claims\": [...]}")
    p2.add_argument("--repo-root", type=Path, default=Path("."))
    p2.add_argument("--out", type=Path)
    return ap


def _emit(obj: dict, out: Path | None) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True)
    if out:
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def _cmd_assemble(a) -> int:
    try:
        payload = json.loads(a.input.read_text(encoding="utf-8"))
        ev = build_document_evidence(
            payload["document_text"], payload["source"], payload["evidence_id"])
        if not a.no_contract_check:
            validate_evidence(ev, a.repo_root)
    except EvidenceError as e:
        _emit({"ok": False, "code": e.code, "detail": e.detail}, a.out)
        return 2
    except (KeyError, json.JSONDecodeError) as e:
        _emit({"ok": False, "code": "ILLEGAL_INPUT", "detail": str(e)}, a.out)
        return 2
    _emit(ev, a.out)
    return 0


def _cmd_audit(a) -> int:
    try:
        raw = json.loads(a.claims.read_text(encoding="utf-8"))
        claims = raw["claims"] if isinstance(raw, dict) else raw
        if not isinstance(claims, list):
            raise EvidenceError("ILLEGAL_INPUT", "claims 必须是数组")
        result = audit_support(claims, a.repo_root)
    except EvidenceError as e:
        _emit({"ok": False, "code": e.code, "detail": e.detail}, a.out)
        return 2
    except (json.JSONDecodeError, KeyError) as e:
        _emit({"ok": False, "code": "ILLEGAL_INPUT", "detail": str(e)}, a.out)
        return 2
    _emit({"ok": result["verdict"] == "PASS", **result}, a.out)
    return 0 if result["verdict"] == "PASS" else 2


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # 兼容历史调用：无子命令时默认 assemble
    if argv and argv[0] not in SUBCOMMANDS and argv[0] not in ("-h", "--help"):
        argv = ["assemble", *argv]
    a = _parser().parse_args(argv)
    return _cmd_assemble(a) if a.cmd == "assemble" else _cmd_audit(a)


if __name__ == "__main__":
    sys.exit(main())
