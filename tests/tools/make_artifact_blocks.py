# 源自 P4-L13-C 演练工具，md5 0e0a8b31f3ff7edd73e83c17765f439c（原始 /tmp 版本逐位一致）。
# 用途：造一组合法 doc2md 产物（并按仓库自己的 build_artifact 校验），C5/P6 演练使用。
"""通用产物生成器：按给定的段落列表造一组合法 doc2md 产物（并用仓库自己的 build_artifact 校验）。

用法： python make_artifact_blocks.py <输出目录> <源标识> <段落1> [段落2 ...]
"""
import hashlib
import json
import pathlib
import shutil
import sys

SRC = pathlib.Path("/home/szf/data/dev/llmke-v2/docs/design/unified-documents-v2/examples/artifact")

out = pathlib.Path(sys.argv[1])
tag = sys.argv[2]
paras = sys.argv[3:]

sys.path.insert(0, "/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service")

if out.exists():
    shutil.rmtree(out)
shutil.copytree(SRC, out)

text = "\n".join(paras)
text_bytes = (text + "\n").encode("utf-8")
out_hash = hashlib.sha256(text_bytes).hexdigest()
src_uid = hashlib.sha256(f"file-{tag}-source".encode()).hexdigest()

(out / "parsed_text.md").write_bytes(text_bytes)

meta = json.loads((out / "parsed_metadata.json").read_text(encoding="utf-8"))
meta.update({"content_uid": src_uid, "sha256": src_uid,
             "source_vault_path": f"raw_vault/by_hash/{src_uid[:2]}/{src_uid[2:4]}/{src_uid}/original.bin"})
(out / "parsed_metadata.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

man = json.loads((out / "parse_manifest.json").read_text(encoding="utf-8"))
man.update({"content_uid": src_uid, "sha256": src_uid,
            "output_hash": out_hash, "output_size_bytes": len(text_bytes)})
(out / "parse_manifest.json").write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")

blocks, cursor = [], 0
for i, p in enumerate(paras, start=1):
    blocks.append({"bbox": None, "block_id": f"b{i:04d}",
                   "content_ref": {"end_offset": cursor + len(p), "kind": "text_span",
                                   "source": "parsed_text.md", "start_offset": cursor, "text": p},
                   "confidence": None, "page_no": None, "reading_order": i - 1,
                   "type": "paragraph"})
    cursor += len(p) + 1

ir = json.loads((out / "document_ir.json").read_text(encoding="utf-8"))
ir.update({"content_uid": src_uid, "document_uid": f"doc_{src_uid[:16]}_017_mvp_v1",
           "blocks": blocks,
           # 顶层 reading_order 是 block_id 数组（store._check_ir 的规则）
           "reading_order": [b["block_id"] for b in blocks]})
(out / "document_ir.json").write_text(json.dumps(ir, ensure_ascii=False), encoding="utf-8")

from parse_artifact import store as S  # noqa: E402

art = S.build_artifact(str(out), {"source_revision": "r1", "parser_fingerprint": "example",
                                  "config_hash": "c" * 64, "runtime_lock_hash": "d" * 64},
                       artifact_id="8" * 64, committed_at="2026-11-08 18:40:00")
print(f"{out}: 校验通过，段落 {len(paras)} 块，content_uid={art['content_uid'][:16]}")
