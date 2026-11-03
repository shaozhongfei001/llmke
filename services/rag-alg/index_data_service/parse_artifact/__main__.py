"""命令行入口：提交一份 doc2md 产物为 ParseArtifact 快照，并按 V2 合同校验。

用法（在仓库根执行）：
  PYTHONPATH=services/rag-alg/index_data_service python -m parse_artifact \
      --source docs/design/unified-documents-v2/examples/artifact \
      --store /tmp/pa-store \
      --source-revision EXAMPLE_SYNTHETIC \
      --runtime-lock-hash <64hex> --config-hash <64hex> --validate

`--validate` 会用 contracts/schema/llmke-document-pipeline-v2.json 的 ParseArtifact 定义复核，
避免"自测自过"。
"""

import argparse
import json
import sys
from pathlib import Path

from .store import ArtifactRefused, commit, verify_committed

REPO_ROOT = Path(__file__).resolve().parents[4]


def main(argv=None):
    parser = argparse.ArgumentParser(prog="parse_artifact")
    parser.add_argument("--source", required=True, help="doc2md 产物目录（四件套 + assets）")
    parser.add_argument("--store", required=True, help="产物仓根目录")
    parser.add_argument("--artifact-id", default=None)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--runtime-lock-hash", required=True)
    parser.add_argument("--config-hash", required=True)
    parser.add_argument("--model-fingerprint", action="append", default=[])
    parser.add_argument("--parser-profile", default=None,
                        help="平台侧解析档位（doc2md metadata 不含该键时必须显式给）")
    parser.add_argument("--mode", choices=["v2", "text_only"], default="v2",
                        help="v2=ParseArtifact（需 document_ir）；text_only=LegacyTextArtifact（CR BL-2.0.0-02）")
    parser.add_argument("--validate", action="store_true", help="用 V2 合同复核产物形状")
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    args = parser.parse_args(argv)

    producer = {
        "source_revision": args.source_revision,
        "runtime_lock_hash": args.runtime_lock_hash,
        "config_hash": args.config_hash,
        "model_fingerprints": args.model_fingerprint,
    }
    if args.parser_profile:
        producer["parser_profile"] = args.parser_profile
    try:
        artifact, target = commit(args.source, args.store, producer,
                                  artifact_id=args.artifact_id, mode=args.mode)
        verify_committed(args.store, artifact["artifact_id"])
        result = {"status": "COMMITTED", "schema_version": artifact["schema_version"],
                  "artifact_id": artifact["artifact_id"],
                  "content_uid": artifact["content_uid"], "parts": len(artifact["parts"]),
                  "quality": artifact["quality"], "target": str(target)}
        if args.validate:
            sys.path.insert(0, str(Path(args.project_root) / "scripts"))
            from contract_runtime import validate_instance
            definition = "/$defs/ParseArtifact" if args.mode == "v2" else "/$defs/LegacyTextArtifact"
            validate_instance(args.project_root, "schema/llmke-document-pipeline-v2.json",
                              artifact, definition)
            result["contract"] = "PASS"
    except ArtifactRefused as exc:
        print(json.dumps({"status": "REFUSED", "code": exc.code, "detail": exc.detail},
                         ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
