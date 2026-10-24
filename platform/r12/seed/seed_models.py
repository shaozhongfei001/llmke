#!/usr/bin/env python3
"""R12 模型注册种子：通过产品自身接口登记 LLM / Embedding / Rerank。

模型全部指向本机真实服务（A-06 独立服务化）：
  LLM        http://127.0.0.1:18092/v1/chat/completions   (qwen2.5-7b-instruct)
  Embedding  http://127.0.0.1:18090/v1/embeddings         (bge-m3, dim=1024)
  Rerank     http://127.0.0.1:18091/v1/rerank             (bge-reranker-v2-m3)
modelProtocol=4 表示 openAI 协议（源码 Schema 注释：1-Baichuan、2-Qwen、3-GLM、4-openAI）。
"""
import sys

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import api, login  # noqa: E402

MODELS = [
    {"modelName": "qwen2.5-7b-instruct", "type": 1, "modelProtocol": 4,
     "modelIde": "qwen2.5-7b-instruct", "apiKey": "sk-r12-local",
     "url": "http://127.0.0.1:18092/v1/chat/completions",
     "dec": "R12 本地 Qwen2.5-7B-Instruct (llama.cpp)", "thinking": False},
    {"modelName": "bge-m3", "type": 2, "modelProtocol": 4,
     "modelIde": "bge-m3", "apiKey": "sk-r12-local",
     "url": "http://127.0.0.1:18090/v1/embeddings",
     "dec": "R12 本地 BGE-M3 embedding (dim=1024)", "thinking": False},
    {"modelName": "bge-reranker-v2-m3", "type": 3, "modelProtocol": 4,
     "modelIde": "bge-reranker-v2-m3", "apiKey": "sk-r12-local",
     "url": "http://127.0.0.1:18091/v1/rerank",
     "dec": "R12 本地 BGE-Reranker-v2-M3", "thinking": False},
    {"modelName": "qwen2.5-vl-3b-instruct", "type": 4, "modelProtocol": 4,
     "modelIde": "qwen2.5-vl-3b-instruct", "apiKey": "sk-r12-local",
     "url": "http://127.0.0.1:18093/v1/chat/completions",
     "dec": "R12 本地 Qwen2.5-VL-3B (图片描述，可选增强)", "thinking": False},
]


def main():
    s, token, _ = login()
    code, body = api(s, "GET", "/index/modelInfo/list?pageNo=1&pageSize=50", token)
    print("list:", code)
    existing = set()
    if isinstance(body, dict):
        for row in (body.get("data") or {}).get("records", []) or []:
            existing.add(row.get("modelName"))
    for m in MODELS:
        if m["modelName"] in existing:
            print("skip existing:", m["modelName"])
            continue
        code, body = api(s, "POST", "/index/modelInfo/create", token, json=m)
        print("create", m["modelName"], "->", code, body if code != 200 else (body.get("data") or {}).get("id"))
    code, body = api(s, "GET", "/index/modelInfo/list?pageNo=1&pageSize=50", token)
    rows = (body.get("data") or {}).get("records", []) if isinstance(body, dict) else []
    for r in rows:
        print("  model:", r.get("id"), r.get("modelName"), "type=", r.get("type"),
              "protocol=", r.get("modelProtocol"), "status=", r.get("status"), r.get("url"))


if __name__ == "__main__":
    sys.exit(main())
