#!/usr/bin/env python3
"""隔离向量回环校验：投影 chunk → 真实 embedding → **临时集合（克隆生产 schema）** → 自检索 → 删除。

对应 ES 侧 `scripts/v2_es_roundtrip_check.py`，补上 Milvus/embedding 这一半。

为什么克隆 schema 而不是自造
--------------------------
自造 6 个字段的简化集合只能证明"Milvus 能收能查"，证明不了投影载荷**填得进生产表**。
这里用 `--template _kb_9` 的字段定义建临时集合（同类型、同 dim、同 ARRAY element_type），
再把投影块映射到生产字段名（text/vector/file_id/chunk_index/source/chunk_doc_id/document_id…），
没映射的字段按类型给空值。这样"字段不丢、类型不冲突"才是被验证过的事实。

安全边界
--------
- 集合名强制 `v2rt_` 前缀，只删自己建的；不碰 `_kb_9` 等生产集合；
- 不写生产库的记录，也不改任何 schema；
- `--keep` 才保留临时集合（排查用）。

退出码：0 各通道 recall@1 全中；1 有不一致；2 依赖缺失或连不上。
"""

import argparse
import json
import sys
import urllib.request

DEFAULT_TEMPLATE = "_kb_9"


def _embed(url, model, texts, batch=16):
    out = []
    for i in range(0, len(texts), batch):
        req = urllib.request.Request(
            url, data=json.dumps({"model": model, "input": texts[i:i + batch]}).encode(),
            method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read())
        out.extend(item["embedding"] for item in payload["data"])
    if len(out) != len(texts):
        raise RuntimeError(f"embedding 数量不符: {len(out)} != {len(texts)}")
    return out


def _clone_schema(client, template, DataType):
    """按模板集合克隆字段定义（类型/params/element_type/主键），不复制数据。"""
    spec = client.describe_collection(template)
    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    for f in spec["fields"]:
        kwargs = dict(f.get("params") or {})
        if f["type"] == DataType.ARRAY:
            kwargs["element_type"] = f.get("element_type", DataType.VARCHAR)
        schema.add_field(f["name"], f["type"], is_primary=bool(f.get("is_primary")), **kwargs)
    return schema, spec["fields"]


def _coerce(value, ftype, element_type, DataType):
    """按目标字段类型转换；转换不了就抛错 —— 宁可失败也不静默写错类型。"""
    if ftype == DataType.ARRAY:
        items = value if isinstance(value, (list, tuple)) else []
        if element_type == DataType.INT64:
            return [int(x) for x in items]
        if element_type == DataType.FLOAT:
            return [float(x) for x in items]
        return [str(x) for x in items]
    if ftype == DataType.INT64:
        return int(value or 0)
    if ftype == DataType.BOOL:
        return bool(value)
    if ftype == DataType.FLOAT_VECTOR:
        return value
    return str(value if value is not None else "")


def _row(chunk, vector, fields, DataType, pk):
    """投影 metadata 已覆盖生产字段名，这里按 schema 类型落字段。

    只补三项 metadata 里没有的：pk（临时主键）、text（正文）、vector（向量）。
    """
    meta = dict(chunk["metadata"])
    meta["text"] = chunk["page_content"]
    meta["vector"] = vector
    row = {}
    for f in fields:
        name, ftype = f["name"], f["type"]
        if ftype == DataType.FLOAT_VECTOR:
            row[name] = vector
            continue
        value = meta.get(name)
        if f.get("is_primary"):
            row[name] = pk
        elif value is None:
            row[name] = _coerce([], ftype, f.get("element_type"), DataType) if ftype == DataType.ARRAY \
                else _coerce("", ftype, None, DataType)
        else:
            row[name] = _coerce(value, ftype, f.get("element_type"), DataType)
    return row


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", required=True)
    ap.add_argument("--milvus", default="http://127.0.0.1:19630")
    ap.add_argument("--db", default="rag_knowledge_base")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE)
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1/embeddings")
    ap.add_argument("--model", default="bge-m3")
    ap.add_argument("--prefix", default="v2rt")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if not args.prefix.startswith("v2rt"):
        print("refusing: --prefix must start with 'v2rt'", file=sys.stderr)
        return 2
    try:
        from pymilvus import DataType, MilvusClient
    except ImportError:
        print("pymilvus missing; install in a tool venv (not a repo dependency)", file=sys.stderr)
        return 2

    chunks = (json.loads(open(args.payloads, encoding="utf-8").read()).get("chunks") or [])
    if not chunks:
        print("no chunks to index", file=sys.stderr)
        return 2

    vectors = _embed(args.embed, args.model, [c["page_content"] for c in chunks])
    client = MilvusClient(uri=args.milvus, db_name=args.db)

    by_channel = {}
    for chunk, vec in zip(chunks, vectors):
        by_channel.setdefault(chunk["index"], []).append((chunk, vec))

    report = {"milvus": args.milvus, "db": args.db, "template": args.template,
              "model": args.model, "channels": {}, "status": "OK"}
    created, pk = [], 1
    try:
        for src, items in by_channel.items():
            name = f"{args.prefix}_{src}"
            if client.has_collection(name):
                client.drop_collection(name)
            schema, fields = _clone_schema(client, args.template, DataType)
            client.create_collection(name, schema=schema)
            created.append(name)

            index_params = client.prepare_index_params()
            index_params.add_index("vector", index_type="AUTOINDEX", metric_type="IP")
            client.create_index(name, index_params)
            client.load_collection(name)

            rows = []
            for chunk, vec in items:
                rows.append(_row(chunk, vec, fields, DataType, pk))
                pk += 1
            client.insert(name, rows)
            client.flush(name)

            hits, missed = 0, []
            for row, vec in zip(rows, [v for _, v in items]):
                res = client.search(name, data=[vec], anns_field="vector", limit=1,
                                    output_fields=["text", "file_id", "chunk_index"])
                top = (res[0][0] if res and res[0] else None)
                got = top.get("entity", {}).get("text") if top else None
                if got == row["text"] and top.get("entity", {}).get("file_id") == row["file_id"]:
                    hits += 1
                else:
                    missed.append({"pk": row.get("pk"), "score": (round(float(top["distance"]), 4)
                                                                 if top else None)})
            report["channels"][name] = {"source_index": src, "inserted": len(rows),
                                        "recall_at_1": hits, "missed": missed[:3]}
            if hits != len(rows):
                report["status"] = "MISMATCH"
        return 0 if report["status"] == "OK" else 1
    except Exception as exc:  # noqa: BLE001 - 连不上/依赖问题要与"不一致"区分
        report["status"] = "ERROR"
        report["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        return 2
    finally:
        if not args.keep:
            for name in created:
                try:
                    client.drop_collection(name)
                except Exception:  # noqa: BLE001
                    print(f"warn: failed to drop {name}", file=sys.stderr)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
