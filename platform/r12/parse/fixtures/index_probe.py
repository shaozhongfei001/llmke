#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
B 项（/parse 带索引）验证探针。

口径来源：TL 2026-10-25 裁定
- 走代理：ES 由 index_fulltext_service(19527) 收，Milvus 由 index_vector_service(19526) 收；
- 模板：es-insert=`http://{ip}:{port}/insert_fulltext_documents`、milvus-insert=`http://{ip}:{port}/insert_vector_documents_custom`；
- 端口取值走 alg-ops 统一发布的 `index_data_config_py`（es_server.port=19527 / milvus_server.port=19526 / milvus_database=rag_knowledge_base）。

用法（venv=parse）：
    python index_probe.py --file cn-digital.pdf --index r12_it_parse_001
随后用 --verify-only 复核 ES / Milvus 计数：
    python index_probe.py --index r12_it_parse_001 --verify-only
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("R12_PARSE_BASE", "http://127.0.0.1:12340")
BUCKET = os.environ.get("R12_BUCKET", "r12-rag")
ES = os.environ.get("R12_ES", "http://127.0.0.1:19200")


def call_parse_sync(key: str, index_name: str, timeout=1800):
    body = {
        "knowledge_base_name": "r12-index-probe",
        # 不传 knowledge_base_id：避免触发 save_to_minio（需要 java-gateway）
        "files": [{"file_path": f"{BUCKET}/fixtures/{key}", "file_id": 9001, "file_size": "1"}],
        "file_type": "naive", "chunk_size": 512, "chunk_overlap": 100,
        "length_function": "char", "need_chunk": True, "index_name": index_name,
        "model_info": {"model_id": os.environ.get("LLM_MODEL", "qwen2.5-7b-instruct"),
                       "url": os.environ.get("LLM_URL", "http://127.0.0.1:18092/v1/chat/completions")},
        "embedding_model_info": {"model_id": os.environ.get("EMB_MODEL", "bge-m3"),
                                 "url": os.environ.get("EMB_URL", "http://127.0.0.1:18090/v1/embeddings")},
        "multi_model_info": {"model_id": os.environ.get("MM_MODEL", "qwen2.5-vl-3b-instruct"),
                             "url": os.environ.get("MM_URL", "http://127.0.0.1:18093/v1/chat/completions")},
    }
    req = urllib.request.Request(BASE.rstrip("/") + "/parse_sync",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), time.perf_counter() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), time.perf_counter() - t0


def es_count(index_name: str):
    for name in (index_name, "table_summary_" + index_name, "table_chunks_" + index_name):
        try:
            with urllib.request.urlopen(f"{ES}/{name}/_count", timeout=10) as r:
                print(f"  ES[{name}] count = {json.load(r).get('count')}")
        except Exception as exc:
            print(f"  ES[{name}] 查询失败：{exc}")


def milvus_count(db: str, collections):
    """用 alg-ops 的 venv（只读）查 Milvus 行数；失败不影响主流程。"""
    py = "/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python"
    if not os.path.exists(py):
        print("  Milvus 校验跳过：找不到 venvs/alg 解释器")
        return
    code = (
        "from pymilvus import MilvusClient\n"
        f"c = MilvusClient(uri='http://127.0.0.1:19630', db_name='{db}')\n"
        f"for n in {collections!r}:\n"
        "    try:\n"
        "        c.load_collection(n)\n"
        "        print(f'  Milvus[{n}] rows =', c.query(n, filter='', output_fields=['count(*)']))\n"
        "    except Exception as e:\n"
        "        print(f'  Milvus[{n}] 查询失败：{e}')\n"
    )
    print(subprocess.run([py, "-c", code], capture_output=True, text=True, timeout=120).stdout.rstrip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="cn-digital.pdf")
    ap.add_argument("--index", required=True)
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()

    if not args.verify_only:
        http, raw, dt = call_parse_sync(args.file, args.index)
        print(f"[parse_sync] {args.file} index={args.index} http={http} {dt:.2f}s")
        print("resp:", raw[:600])
        open(f"/tmp/index-probe-{args.index}.json", "w").write(raw)

    print("[verify] ES（本体 19200 只读计数）")
    es_count(args.index)
    print("[verify] Milvus（只读，db=rag_knowledge_base）")
    milvus_count("rag_knowledge_base", [args.index])


if __name__ == "__main__":
    sys.exit(main())
