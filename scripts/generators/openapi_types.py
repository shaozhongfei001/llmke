#!/usr/bin/env python3
"""OpenAPI -> lossless validation bundle and human type index (not a compiled SDK).

Reads an OpenAPI 3.x document (JSON or YAML) and emits
generated/sdk/<contract-id>.types.json containing schema names and field
types. Deterministic output (sorted keys) so hash linkage is stable.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_doc(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ImportError:
        print("ERROR: contract is YAML but PyYAML is not installed", file=sys.stderr)
        sys.exit(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--id", required=True)
    args = ap.parse_args()

    doc = load_doc(args.contract)
    if not isinstance(doc, dict) or "openapi" not in doc:
        print("ERROR: not an OpenAPI 3.x document", file=sys.stderr)
        return 1

    schemas = (doc.get("components") or {}).get("schemas") or {}
    types = {}
    for name in sorted(schemas):
        s = schemas[name] or {}
        props = s.get("properties") or {}
        types[name] = {
            "type": s.get("type", "object"),
            "required": sorted(s.get("required") or []),
            "fields": {
                fname: (fdef or {}).get("type", "any")
                for fname, fdef in sorted(props.items())
            },
        }

    out = args.outdir / "generated" / "sdk" / f"{args.id}.types.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract_id": args.id,
        "openapi": doc.get("openapi"),
        "schema_count": len(types),
        "types": types,
        "schema_document": doc,
        "schema_resources": {json.loads(p.read_text())["$id"]: json.loads(p.read_text()) for p in sorted((args.contract.parent.parent / "schema").glob("*.json"))},
        "artifact_kind": "LOSSLESS_VALIDATION_BUNDLE_NOT_DTO_SDK",
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"generated {out} ({len(types)} types)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
