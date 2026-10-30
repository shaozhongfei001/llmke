"""命令行：从已提交快照产出投影报告，可选与线上 ES 的 chunk 数做只读对照。

用法（仓库根）：
  PYTHONPATH=services/rag-alg/index_data_service python -m rag_projection \
      --artifact-dir /tmp/pa-ir3/artifacts/<uid> --index kb_9 --file-id 333 \
      --mode shadow --es http://127.0.0.1:19200 --out /tmp/proj-333.json

只读：不写 ES/Milvus/MySQL；`--es` 只发 `_count` 查询。
"""

import argparse
import json
import urllib.request

from .projection import ProjectionPolicy, ProjectionRefused, project


def es_chunk_count(base, index, file_id):
    """只读统计：线上该文件的 chunk 数。file_id 可能是字符串也可能是数字，两种都试。"""
    url = f"{base.rstrip('/')}/{index}/_count"
    total = 0
    errors = []
    for value in (str(file_id), int(file_id) if str(file_id).isdigit() else None):
        if value is None:
            continue
        body = json.dumps({"query": {"term": {"metadata.file_id": value}}}).encode()
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                total = max(total, int(json.loads(resp.read())["count"]))
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc)[:120])
    return total, errors


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rag_projection")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--index", required=True, help="线上索引名（如 kb_9）")
    parser.add_argument("--file-id", required=True)
    parser.add_argument("--mode", default=None, choices=["legacy", "snapshot", "shadow"])
    parser.add_argument("--chunk-chars", type=int, default=800)
    parser.add_argument("--overlap-chars", type=int, default=0)
    parser.add_argument("--es", default=None, help="给出则做只读 chunk 数对照")
    parser.add_argument("--es-index", action="append", default=None,
                        help="参与对照的索引（可重复）。默认只比主索引；xlsx/pdf 的表格块在 table_chunks_* 里")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    policy = ProjectionPolicy(index_name=args.index, file_id=args.file_id,
                              chunk_chars=args.chunk_chars,
                              overlap_chars=args.overlap_chars)
    try:
        result = project(args.artifact_dir, policy, mode=args.mode)
    except ProjectionRefused as exc:
        print(json.dumps({"status": "REFUSED", "code": exc.code, "detail": exc.detail},
                         ensure_ascii=False))
        return 2

    report = result.to_dict()
    if args.es and result.chunks:
        indexes = args.es_index or [args.index]
        per_index, errors = {}, []
        for index in indexes:
            count, errs = es_chunk_count(args.es, index, args.file_id)
            per_index[index] = count
            errors.extend(errs)
        total = sum(per_index.values())
        report["es_compare"] = {"file_id": args.file_id, "per_index": per_index,
                                "es_chunks": total, "snapshot_chunks": len(result.chunks),
                                "diff": len(result.chunks) - total, "errors": errors}
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    summary = {k: v for k, v in report.items() if k != "chunks"}
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if result.status in {"READY", "SHADOW", "EMPTY", "NOT_APPLICABLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
