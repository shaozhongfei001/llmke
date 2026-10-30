"""命令行：对一份已提交快照跑摄取链路，打印各索引通道将要写入的 chunk 数。

用法（仓库根）：
  PYTHONPATH=services/rag-alg/index_data_service python -m ingest_pipeline \
      --artifact-dir /tmp/pa-native/333/artifacts/<uid> --index kb_9 --file-id 333 \
      --mode shadow --out /tmp/ingest-333.json

只读：不连 ES/Milvus/MySQL；`--apply` 仅在 snapshot 模式下被接受（本命令仍不写库）。
"""

import argparse
import json

from .pipeline import MODES, IngestRefused, ingest


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ingest_pipeline")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--file-id", required=True)
    parser.add_argument("--mode", default=None, choices=list(MODES))
    parser.add_argument("--apply", action="store_true", help="仅 snapshot 模式允许")
    parser.add_argument("--chunk-chars", type=int, default=800)
    parser.add_argument("--file-name", default=None, help="原始文件名（title / parent_file_name）")
    parser.add_argument("--file-path", default=None, help="原对象键（file_path）")
    parser.add_argument("--file-size", default=None, help="展示用大小，如 47.3 MB")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    try:
        result = ingest(args.artifact_dir, index_name=args.index, file_id=args.file_id,
                        mode=args.mode, apply_index=args.apply,
                        chunk_chars=args.chunk_chars, file_name=args.file_name,
                        file_path=args.file_path, file_size=args.file_size)
    except IngestRefused as exc:
        print(json.dumps({"status": "REFUSED", "code": exc.code, "detail": exc.detail},
                         ensure_ascii=False))
        return 2
    except Exception as exc:  # noqa: BLE001 - 投影层的拒绝要如实透出
        print(json.dumps({"status": "REFUSED", "code": type(exc).__name__,
                          "detail": str(exc)[:300]}, ensure_ascii=False))
        return 2

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    summary = {k: v for k, v in result.items() if k != "chunks"}
    summary["chunk_payloads"] = len(result.get("chunks") or [])
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
