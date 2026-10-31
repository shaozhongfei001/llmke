#!/usr/bin/env python3
"""A2 平台适配器探针：直接跑平台自己的 `deepdoc.parser.MinerUParser`。

与 `v2_mineru_smoke.py` 的分工：
- smoke 走上游 `magic-pdf` CLI，只验证"权重+配置+模型链路"；
- 本脚本走**平台适配器**，验证 `ParsedText` 的字段映射（page_content / position / page_number /
  page_size / title）是不是解析后段能直接吃，这是 CLI 验不到的部分。

必须在装了 parse 依赖的环境里跑（见 docs/design/unified-documents-v2/A2-MINERU-INTEGRATION.md），
且需要：
- naocs 配置里有 `mineru` 段（build-in/backend/version/endpoint）；本机用测试 data-id
  `alg_doc_config_py_v2test`，**不动线上 data-id**；
- `MINERU_TOOLS_CONFIG_JSON` 指向本地 magic-pdf.json；
- `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1`（torch ≥2.6 默认 weights_only=True，doclayout_yolo
  的 ckpt 会被拒；这是 env 级开关，不是改上游代码）。
"""

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVICE = REPO / "services/rag-alg/alg_doc_parse_service"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--nacos-data-id", default="alg_doc_config_py_v2test")
    ap.add_argument("--nacos-address", default="http://127.0.0.1:18848")
    ap.add_argument("--nacos-group", default="DEFAULT_GROUP")
    ap.add_argument("--mineru-config", default="/home/szf/data/dev/models/mineru/magic-pdf.json")
    ap.add_argument("--expect", nargs="*", default=[])
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if not Path(args.mineru_config).is_file():
        print(json.dumps({"status": "NO_MINERU_CONFIG", "path": args.mineru_config},
                         ensure_ascii=False))
        return 2

    os.environ.update({
        "NACOS_SERVER_ADDRESS": args.nacos_address,
        "NACOS_NAMESPACE": "",
        "NACOS_DATA_ID": args.nacos_data_id,
        "NACOS_GROUP": args.nacos_group,
        "DATA_ID": args.nacos_data_id,
        "MINERU_TOOLS_CONFIG_JSON": args.mineru_config,
        "HF_HUB_OFFLINE": "1",
        "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD": "1",
    })
    sys.path.insert(0, str(SERVICE))

    import log  # noqa: F401  —— 先加载平台日志配置，否则后续 remove 不生效
    from loguru import logger
    logger.remove()
    logger.add(lambda _m: None)  # 平台的队列 sink 在脚本进程里会 pickle 失败，直接丢弃

    from langchain_core.document_loaders import Blob
    from log import request_id
    request_id.set("v2-adapter-probe")

    from deepdoc.parser.mineru_parser import MinerUParser, magic_pdf  # noqa: F401

    docs = MinerUParser().parse(Blob.from_path(args.pdf))
    rows = []
    for doc in docs:
        meta = getattr(doc, "metadata", None)
        rows.append({
            "chars": len(doc.page_content or ""),
            "type": getattr(meta, "type", None),
            "title": getattr(meta, "title", None),
            "page_number": getattr(meta, "page_number", None),
            "has_position": bool(getattr(meta, "position", None)),
            "page_size": getattr(meta, "page_size", None),
        })
    joined = "\n".join(d.page_content or "" for d in docs)
    missing = [e for e in args.expect if e.replace(" ", "") not in joined.replace("\n", "").replace(" ", "")]
    report = {"status": "OK" if not missing else "CONTENT_MISMATCH",
              "sdk": magic_pdf, "docs": len(docs), "missing": missing, "rows": rows}
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                  encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
