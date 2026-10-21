"""命令行入口：从 JSON 读入并输出契约化证据。失败退出码 2（fail-closed）。"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

from .assembler import EvidenceError, build_document_evidence, validate_evidence


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="citation-evidence")
    ap.add_argument("--input", type=Path, required=True, help="JSON: {evidence_id, document_text, source}")
    ap.add_argument("--out", type=Path, help="输出文件；缺省打印到 stdout")
    ap.add_argument("--repo-root", type=Path, default=Path("."), help="含 contracts/ 的仓库根")
    ap.add_argument("--no-contract-check", action="store_true", help="只做字段校验，跳过 schema 校验")
    a = ap.parse_args(argv)

    try:
        payload = json.loads(a.input.read_text(encoding="utf-8"))
        ev = build_document_evidence(
            payload["document_text"], payload["source"], payload["evidence_id"])
        if not a.no_contract_check:
            validate_evidence(ev, a.repo_root)
    except EvidenceError as e:
        print(json.dumps({"ok": False, "code": e.code, "detail": e.detail}, ensure_ascii=False))
        return 2
    except (KeyError, json.JSONDecodeError) as e:
        print(json.dumps({"ok": False, "code": "ILLEGAL_INPUT", "detail": str(e)}, ensure_ascii=False))
        return 2

    text = json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)
    if a.out:
        a.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
