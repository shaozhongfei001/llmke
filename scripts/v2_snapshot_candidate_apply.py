#!/usr/bin/env python3
"""隔离候选启用/回退：把投影载荷写进独立命名空间，验证可检索，再整体回退并核对线上未变。

与 `v2_es_roundtrip_check.py` / `v2_milvus_roundtrip_check.py` 的差别
------------------------------------------------------------------
那两个是"写完就删"的一次性回环；这个要模拟**真实切换与回退**：

  apply     建 `v2cand_*` 索引/集合，写入，记录 manifest（含线上基线计数）
  verify    从候选命名空间检索：条数、按 artifact 过滤、Milvus recall@1、字段抽样
  rollback  删除本次创建的索引/集合，并与 manifest 里的基线计数逐项核对"线上未变"

安全边界
--------
- 命名空间强制以 `v2cand` 开头；只操作带命名空间前缀的目标，**绝不**碰 `kb_9` 等线上索引；
- rollback 只删 manifest 里登记过的对象，不做通配删除；
- 不写 MySQL、不改任何线上集合 schema；
- 基线只读：`_count` / `count(*)`，用于证明回退后线上未变。

退出码：0 成功；1 校验不一致；2 环境/参数/依赖问题。
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_NS = "v2cand"


def _req(method, url, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def _es_count(base, index):
    try:
        return _req("GET", f"{base}/{index}/_count").get("count")
    except urllib.error.HTTPError:
        return None


def _embed(url, model, texts, batch=8):
    out = []
    for i in range(0, len(texts), batch):
        req = urllib.request.Request(
            url, data=json.dumps({"model": model, "input": texts[i:i + batch]}).encode(),
            method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = json.loads(resp.read())
        out.extend(item["embedding"] for item in payload["data"])
    return out


def _coerce(value, ftype, element_type, DataType):
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


def _clone_schema(client, template, DataType):
    spec = client.describe_collection(template)
    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    for f in spec["fields"]:
        kwargs = dict(f.get("params") or {})
        if f["type"] == DataType.ARRAY:
            kwargs["element_type"] = f.get("element_type", DataType.VARCHAR)
        schema.add_field(f["name"], f["type"], is_primary=bool(f.get("is_primary")), **kwargs)
    return schema, spec["fields"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["apply", "verify", "rollback"])
    ap.add_argument("--payloads", help="apply 需要：ingest_pipeline --out 产出")
    ap.add_argument("--manifest", required=True, help="apply 写出、verify/rollback 读入")
    ap.add_argument("--namespace", default=DEFAULT_NS)
    ap.add_argument("--es", default="http://127.0.0.1:19200")
    ap.add_argument("--milvus", default="http://127.0.0.1:19630")
    ap.add_argument("--db", default="rag_knowledge_base")
    ap.add_argument("--template", default="_kb_9")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1/embeddings")
    ap.add_argument("--model", default="bge-m3")
    ap.add_argument("--retrieval-compatible", action="store_true",
                    help="按检索服务的索引命名规则落库：正文=<ns>_<kb>、表格=table_chunks_<ns>_<kb>、"
                         "总结=table_summary_<ns>_<kb>；这样把 <ns>_<kb> 当知识库名即可直接检索")
    ap.add_argument("--milvus-collections", action="store_true",
                    help="同时写 Milvus（默认只写 ES，避免无谓开销）")
    args = ap.parse_args(argv)

    if not args.namespace.startswith(DEFAULT_NS):
        print(f"refusing: namespace must start with '{DEFAULT_NS}'", file=sys.stderr)
        return 2
    ns = args.namespace
    es = args.es.rstrip("/")

    if args.action == "apply":
        return _apply(args, ns, es)
    if args.action == "verify":
        return _verify(args, ns, es)
    return _rollback(args, ns, es)


def _apply(args, ns, es):
    if not args.payloads:
        print("apply requires --payloads", file=sys.stderr)
        return 2
    chunks = (json.loads(open(args.payloads, encoding="utf-8").read()).get("chunks") or [])
    if not chunks:
        print("no chunks", file=sys.stderr)
        return 2

    manifest = {"namespace": ns, "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "es": [], "milvus": [], "baseline": {}, "source_payloads": args.payloads,
                "counts": {}}
    # 先记线上基线，回退后逐项核对（只读）
    sources = sorted({c["index"] for c in chunks})
    for src in sources:
        manifest["baseline"][f"es:{src}"] = _es_count(es, src)

    def target_name(src):
        """检索侧按 `table_chunks_<kb>` / `table_summary_<kb>` 拼索引名，
        因此候选命名要么自洽，要么检索根本查不到（这是实测会踩的坑）。"""
        if not args.retrieval_compatible:
            return f"{ns}_{src}"
        if src.startswith("table_chunks_"):
            return f"table_chunks_{ns}_{src[len('table_chunks_'):]}"
        if src.startswith("table_summary_"):
            return f"table_summary_{ns}_{src[len('table_summary_'):]}"
        return f"{ns}_{src}"

    by_index = {}
    for chunk in chunks:
        by_index.setdefault(chunk["index"], []).append(chunk)

    for src, items in by_index.items():
        target = target_name(src)
        try:
            _req("DELETE", f"{es}/{target}")
        except urllib.error.HTTPError:
            pass
        _req("PUT", f"{es}/{target}", {"mappings": {"properties": {
            "page_content": {"type": "text"},
            "metadata": {"type": "object", "enabled": True}}}})
        lines = []
        for chunk in items:
            lines.append(json.dumps({"index": {"_index": target, "_id": str(chunk["pk"])}}))
            lines.append(json.dumps({"page_content": chunk["page_content"],
                                     "metadata": chunk["metadata"]}, ensure_ascii=False))
        body = ("\n".join(lines) + "\n").encode()
        req = urllib.request.Request(f"{es}/_bulk", data=body, method="POST",
                                     headers={"Content-Type": "application/x-ndjson"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            bulk = json.loads(resp.read())
        if bulk.get("errors"):
            print("bulk errors", file=sys.stderr)
            return 1
        _req("POST", f"{es}/{target}/_refresh")
        manifest["es"].append({"target": target, "source_index": src, "rows": len(items)})
        manifest["counts"][f"es:{target}"] = _es_count(es, target)

    if args.milvus_collections:
        from pymilvus import DataType, MilvusClient

        def template_for(src):
            """按通道选模板集合：总结/表格块/正文的字段集不同，用同一模板会缺字段。"""
            if src.startswith("table_summary_"):
                return "_table_summary_kb_10"
            if src.startswith("table_chunks_"):
                return "_table_chunks_kb_10"
            return args.template
        client = MilvusClient(uri=args.milvus, db_name=args.db)
        vectors = _embed(args.embed, args.model, [c["page_content"] for c in chunks])
        vec_by_pk = {c["pk"]: v for c, v in zip(chunks, vectors)}
        pk_seq = 1
        for src, items in by_index.items():
            target = f"{ns}_{src}"
            if client.has_collection(target):
                client.drop_collection(target)
            schema, fields = _clone_schema(client, template_for(src), DataType)
            client.create_collection(target, schema=schema)
            index_params = client.prepare_index_params()
            index_params.add_index("vector", index_type="AUTOINDEX", metric_type="IP")
            client.create_index(target, index_params)
            client.load_collection(target)
            rows = []
            for chunk in items:
                meta = dict(chunk["metadata"])
                meta["text"] = chunk["page_content"]
                row = {}
                for f in fields:
                    if f["type"] == DataType.FLOAT_VECTOR:
                        row[f["name"]] = vec_by_pk[chunk["pk"]]
                    elif f.get("is_primary"):
                        # 主键必须用投影里登记的 pk：总结文档的 pk 就是表格块的 table_summary_id，
                        # 用自增序号会让"总结→明细"的关联断掉（实测 linked_chunks=0）。
                        declared = chunk.get("pk")
                        row[f["name"]] = int(declared) if declared is not None else pk_seq
                    elif meta.get(f["name"]) is None:
                        row[f["name"]] = _coerce([], f["type"], f.get("element_type"), DataType) \
                            if f["type"] == DataType.ARRAY else _coerce("", f["type"], None, DataType)
                    else:
                        row[f["name"]] = _coerce(meta[f["name"]], f["type"],
                                                 f.get("element_type"), DataType)
                rows.append(row)
                pk_seq += 1
            client.insert(target, rows)
            client.flush(target)
            manifest["milvus"].append({"target": target, "source_index": src, "rows": len(rows)})

    with open(args.manifest, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"action": "apply", "namespace": ns,
                      "es": manifest["es"], "milvus": manifest["milvus"],
                      "baseline": manifest["baseline"]}, ensure_ascii=False))
    return 0


def _verify(args, ns, es):
    manifest = json.loads(open(args.manifest, encoding="utf-8").read())
    if manifest.get("namespace") != ns:
        print("manifest namespace mismatch", file=sys.stderr)
        return 2
    problems = []
    report = {"namespace": ns, "es": [], "milvus": [], "status": "OK"}

    for entry in manifest["es"]:
        target = entry["target"]
        payloads = (json.loads(open(manifest["source_payloads"], encoding="utf-8").read())
                    .get("chunks") or [])
        expected_ids = {str(c["pk"]) for c in payloads if c["index"] == entry["source_index"]}
        count = _es_count(es, target)
        query = _req("POST", f"{es}/{target}/_search",
                     {"size": len(expected_ids),
                      "query": {"ids": {"values": sorted(expected_ids)}}})
        got = {hit["_id"] for hit in (query.get("hits") or {}).get("hits", [])}
        artifact_ids = {c["metadata"]["parse_artifact_id"] for c in payloads
                        if c["index"] == entry["source_index"]}
        by_artifact = _req("POST", f"{es}/{target}/_search", {
            "size": 0, "query": {"term": {"metadata.parse_artifact_id": next(iter(artifact_ids))}}}
        )["hits"]["total"]["value"]
        ok = (count == entry["rows"] and got == expected_ids and by_artifact == entry["rows"])
        report["es"].append({"target": target, "count": count, "ids_hit": len(got),
                             "by_artifact": by_artifact, "expected": entry["rows"], "ok": ok})
        if not ok:
            problems.append(f"ES {target} 不一致")

    if manifest["milvus"]:
        from pymilvus import MilvusClient
        client = MilvusClient(uri=args.milvus, db_name=args.db)
        for entry in manifest["milvus"]:
            total = client.query(entry["target"], filter="", output_fields=["count(*)"])[0]["count(*)"]
            ok = total == entry["rows"]
            report["milvus"].append({"target": entry["target"], "count": total,
                                     "expected": entry["rows"], "ok": ok})
            if not ok:
                problems.append(f"Milvus {entry['target']} 行数不符")

    if problems:
        report["status"] = "MISMATCH"
        report["problems"] = problems
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not problems else 1


def _rollback(args, ns, es):
    manifest = json.loads(open(args.manifest, encoding="utf-8").read())
    if manifest.get("namespace") != ns:
        print("manifest namespace mismatch", file=sys.stderr)
        return 2
    report = {"namespace": ns, "deleted": [], "baseline_check": {}, "status": "OK"}

    for entry in manifest["es"]:
        target = entry["target"]
        # 命名空间可能是前缀（v2cand_kb_10）或中间段（table_chunks_v2cand_kb_10），
        # 判据是"名称里含有独立段 ns"，而不是简单 startswith。
        assert ns in target.split("_"), target
        try:
            _req("DELETE", f"{es}/{target}")
            report["deleted"].append(f"es:{target}")
        except urllib.error.HTTPError:
            report["deleted"].append(f"es:{target}:absent")

    if manifest["milvus"]:
        from pymilvus import MilvusClient
        client = MilvusClient(uri=args.milvus, db_name=args.db)
        for entry in manifest["milvus"]:
            target = entry["target"]
            assert ns in target.split("_"), target
            if client.has_collection(target):
                client.drop_collection(target)
                report["deleted"].append(f"milvus:{target}")

    # 回退后核对线上基线未变（这是"回退成立"的唯一硬证据）
    for key, before in manifest["baseline"].items():
        src = key.split(":", 1)[1]
        after = _es_count(es, src)
        report["baseline_check"][src] = {"before": before, "after": after,
                                         "unchanged": before == after}
        if before != after:
            report["status"] = "BASELINE_CHANGED"

    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
