#!/usr/bin/env python3
"""隔离索引回环校验：把投影载荷写进**临时索引**、查回来、再删掉。

用途
----
证明"快照投影产出的 chunk 能被 ES 接受并可检索回"，且**不碰**线上 `kb_9` /
`table_chunks_kb_9`。索引名强制带前缀（默认 `v2rt_`），脚本只删除自己创建的索引。

不做
----
- 不写 Milvus、不调 embedding（那属于向量通道，另有校验）；
- 不读 MySQL，也不需要 llmke 的 Java 服务在跑。

退出码：0 全部通道回读一致；1 有通道不一致；2 无法连接 ES 或参数错误。
"""

import argparse
import json
import sys
import urllib.error
import urllib.request


def _req(method, url, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        return resp.status, (json.loads(raw) if raw else {})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", required=True, help="ingest_pipeline --out 产出的 JSON")
    ap.add_argument("--es", default="http://127.0.0.1:19200")
    ap.add_argument("--prefix", default="v2rt")
    ap.add_argument("--keep", action="store_true", help="保留临时索引（排查用）")
    args = ap.parse_args(argv)

    if not args.prefix.startswith("v2rt"):
        print("refusing: --prefix must start with 'v2rt' (only temporary indexes)", file=sys.stderr)
        return 2

    payload = json.loads(open(args.payloads, encoding="utf-8").read())
    chunks = payload.get("chunks") or []
    if not chunks:
        print("no chunks to index", file=sys.stderr)
        return 2

    # 源索引名 → 临时索引名（保持通道分离：正文 / 表格）
    mapping = {}
    for chunk in chunks:
        src = chunk["index"]
        mapping.setdefault(src, f"{args.prefix}_{src}")

    base = args.es.rstrip("/")
    created, report = [], {"es": base, "channels": {}, "status": "OK"}
    try:
        for src, temp in mapping.items():
            try:
                _req("DELETE", f"{base}/{temp}")
            except urllib.error.HTTPError:
                pass
            _req("PUT", f"{base}/{temp}", {"mappings": {"properties": {
                "page_content": {"type": "text"},
                "metadata": {"type": "object", "enabled": True},
            }}})
            created.append(temp)

        lines = []
        for chunk in chunks:
            temp = mapping[chunk["index"]]
            doc = {"page_content": chunk["page_content"], "metadata": chunk["metadata"]}
            lines.append(json.dumps({"index": {"_index": temp, "_id": str(chunk["pk"])}}))
            lines.append(json.dumps(doc, ensure_ascii=False))
        body = ("\n".join(lines) + "\n").encode()
        req = urllib.request.Request(f"{base}/_bulk", data=body, method="POST",
                                     headers={"Content-Type": "application/x-ndjson"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            bulk = json.loads(resp.read())
        if bulk.get("errors"):
            report["status"] = "BULK_ERRORS"
            report["bulk"] = [i for i in bulk["items"] if i["index"].get("error")][:3]
            return 1

        for src, temp in mapping.items():
            _req("POST", f"{base}/{temp}/_refresh")
            expected = sum(1 for c in chunks if c["index"] == src)
            _, got = _req("POST", f"{base}/{temp}/_count")
            artifact_ids = {c["metadata"]["parse_artifact_id"] for c in chunks if c["index"] == src}
            _, query = _req("POST", f"{base}/{temp}/_search", {
                "size": 0, "query": {"term": {"metadata.parse_artifact_id":
                                              next(iter(artifact_ids))}}})
            hit = (query.get("hits") or {}).get("total", {}).get("value", 0)
            report["channels"][temp] = {"source_index": src, "expected": expected,
                                        "count": got.get("count"), "by_artifact": hit}
            if got.get("count") != expected or hit != expected:
                report["status"] = "MISMATCH"
        return 0 if report["status"] == "OK" else 1
    except urllib.error.URLError as exc:
        report["status"] = "ES_UNAVAILABLE"
        report["error"] = str(exc)[:200]
        return 2
    finally:
        if not args.keep:
            for temp in created:
                try:
                    _req("DELETE", f"{base}/{temp}")
                except Exception:  # noqa: BLE001 - 清理失败不影响结论，但会打印
                    print(f"warn: failed to delete {temp}", file=sys.stderr)
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
