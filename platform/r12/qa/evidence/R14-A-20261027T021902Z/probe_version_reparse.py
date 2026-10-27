"""R14-A / C12 步1：走真实 Java 重解析链路，验证 metadata.version 是否落进 ES chunk。

流程：
  1. 记录目标文件在 ES kb_9 的现状（_id / metadata.version / chunk 数）
  2. POST /index/knowledgeBase/file/filesParse（网关鉴权，和产品一致）
  3. 轮询 ES 直到该文件 chunks 数量稳定且出现非空 version（或超时）
  4. 输出前后对比 JSON

用法：
  platform/r12/venvs/alg/bin/python probe_version_reparse.py 328 kb_9 > version_reparse_328.json
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import api, login  # noqa: E402

FILE_ID = sys.argv[1] if len(sys.argv) > 1 else "328"
KB = sys.argv[2] if len(sys.argv) > 2 else "kb_9"
ES = "http://127.0.0.1:19200"


def es_file_state(fid):
    body = {"size": 200, "query": {"term": {"metadata.file_id": int(fid)}},
            "_source": ["metadata.file_id", "metadata.version", "metadata.chunk_index", "metadata.title"]}
    req = urllib.request.Request(f"{ES}/{KB}/_search", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    hits = json.load(urllib.request.urlopen(req, timeout=30))["hits"]["hits"]
    return {
        "count": len(hits),
        "versions": sorted({str((h["_source"].get("metadata") or {}).get("version")) for h in hits}),
        "ids": sorted(h["_id"] for h in hits),
        "chunk_index": sorted((h["_source"].get("metadata") or {}).get("chunk_index") for h in hits),
        "nonnull_version": sum(1 for h in hits if (h["_source"].get("metadata") or {}).get("version")),
    }


def main():
    out = {"file_id": FILE_ID, "kb": KB}
    out["before"] = es_file_state(FILE_ID)
    print(f"[before] {out['before']}", file=sys.stderr)

    s, token, _ = login()
    code, body = api(s, "POST", "/index/knowledgeBase/file/filesParse", token,
                     json={"file_ids": [FILE_ID], "knowledge_base_name": KB})
    out["trigger"] = {"http": code, "body": body}
    print(f"[trigger] http={code} body={str(body)[:200]}", file=sys.stderr)

    deadline = time.time() + 900
    last = None
    while time.time() < deadline:
        time.sleep(10)
        st = es_file_state(FILE_ID)
        if st != last:
            print(f"[poll] {st}", file=sys.stderr)
            last = st
        # 结束条件：出现非空 version（说明透传生效）或 chunk 数变化后稳定
        if st["nonnull_version"] > 0:
            break
    out["after"] = es_file_state(FILE_ID)
    out["verdict"] = {
        "version_landed": out["after"]["nonnull_version"] > 0,
        "versions": out["after"]["versions"],
        "ids_stable": out["before"]["ids"] == out["after"]["ids"],
        "count_stable": out["before"]["count"] == out["after"]["count"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
