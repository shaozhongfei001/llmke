#!/usr/bin/env python3
"""JSON Schema -> canonical snapshot generator.

为什么需要它：schema 合同的价值在于「被实现引用」，而不是「躺在仓库里」。
本生成器把 schema 规范化后产出快照（属性路径、必需性、枚举闭集、$ref 计数），
实现侧据此生成校验代码；`make check` 再通过哈希联动确保快照未被手改。

输出：generated/schema/<contract-id>.snapshot.json
确定性：键排序、无时间戳、无绝对路径，保证同输入同哈希。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MAX_DEPTH = 12


def canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def walk(node, path="$", depth=0, out=None):
    """Collect property paths, required flags and enum closures."""
    if out is None:
        out = {"properties": {}, "enums": {}, "refs": []}
    if depth > MAX_DEPTH or not isinstance(node, (dict, list)):
        return out

    if isinstance(node, list):
        for i, item in enumerate(node):
            walk(item, f"{path}[{i}]", depth + 1, out)
        return out

    ref = node.get("$ref")
    if isinstance(ref, str):
        out["refs"].append(ref)

    props = node.get("properties")
    if isinstance(props, dict):
        required = node.get("required") or []
        for name in sorted(props):
            child = props[name]
            child_path = f"{path}.{name}"
            if isinstance(child, dict):
                out["properties"][child_path] = {
                    "type": child.get("type"),
                    "required": name in required,
                }
                if isinstance(child.get("enum"), list):
                    out["enums"][child_path] = sorted(str(v) for v in child["enum"])
                walk(child, child_path, depth + 1, out)
            else:
                out["properties"][child_path] = {"type": None, "required": name in required}

    for key in ("allOf", "anyOf", "oneOf", "items", "then", "if"):
        if key in node:
            walk(node[key], f"{path}.{key}", depth + 1, out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--id", required=True)
    args = ap.parse_args()

    try:
        doc = json.loads(args.contract.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: contract is not JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(doc, dict):
        print("ERROR: schema root must be an object", file=sys.stderr)
        return 1

    collected = walk(doc)
    digest = hashlib.sha256(canonical(doc).encode("utf-8")).hexdigest()
    payload = {
        "contract_id": args.id,
        "schema_document": doc,
        "artifact_kind": "LOSSLESS_SCHEMA_SNAPSHOT",
        "schema_id": doc.get("$id") or doc.get("$schema"),
        "title": doc.get("title"),
        "content_sha256": digest,
        "property_count": len(collected["properties"]),
        "properties": collected["properties"],
        "enums": collected["enums"],
        "refs": sorted(set(collected["refs"])),
    }
    out = args.outdir / "generated" / "schema" / f"{args.id}.snapshot.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"generated {out} ({payload['property_count']} properties)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
