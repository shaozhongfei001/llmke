#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R12 Nacos 配置发布器（alg-ops 维护，任务书 §2 / 决议 A-03）

用法：
    python3 platform/r12/nacos/publish.py            # 发布本目录下 4 个 alg 配置并回读校验
    python3 platform/r12/nacos/publish.py --verify   # 只回读校验

行为：
  - 只处理 DATA_IDS 白名单，避免误覆盖他人 data_id（parse-ops 的 alg_doc_* 不在名单内）。
  - 发布后立刻 GET 回读并逐字节比对（内容不一致即失败退出），避免"以为发了其实没生效"。
  - 打印每个 data_id 的 md5（对回读内容计算），供证据留档。
"""
import hashlib
import sys
import time
import urllib.parse
import urllib.request

NACOS = "http://127.0.0.1:18848/nacos"
GROUP = "DEFAULT_GROUP"
TENANT = ""  # public 命名空间
BASE_DIR = "/home/szf/data/dev/llmke-r12/platform/r12/nacos"
DATA_IDS = [
    "alg_common_py",
    "index_data_config_py",
    "alg_retrieval_config_py",
    "alg_llm_config_py",
]


def _request(path, params=None, data=None, method="GET"):
    url = NACOS + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def publish(data_id, content):
    return _request(
        "/v1/cs/configs",
        data={"dataId": data_id, "group": GROUP, "tenant": TENANT, "content": content, "type": "yaml"},
        method="POST",
    )


def fetch(data_id):
    # Nacos 2.3.2 在 POST 之后立刻 GET 有概率返回 404（本地 dump 未刷新），重试若干次
    last = None
    for _ in range(6):
        try:
            return _request("/v1/cs/configs", {"dataId": data_id, "group": GROUP, "tenant": TENANT})
        except Exception as e:  # noqa: BLE001 - 404 视为未就绪
            last = e
            time.sleep(0.5)
    print(f"[WARN] {data_id} 回读连续失败: {last}")
    return None


def main():
    verify_only = "--verify" in sys.argv
    ok = True
    for data_id in DATA_IDS:
        path = f"{BASE_DIR}/{data_id}.yaml"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if not verify_only:
            resp = publish(data_id, content)
            if resp.strip().lower() != "true":
                print(f"[FAIL] {data_id} 发布返回 {resp!r}")
                ok = False
                continue
            time.sleep(0.4)  # 等 Nacos 本地 dump 落盘，避免紧随的 GET 404
        back = fetch(data_id)
        if back is None or back == "":
            print(f"[FAIL] {data_id} 回读为空（未发布成功）")
            ok = False
            continue
        # 注意：Nacos 可能把 content 原样存储；比对时容忍行尾差异
        same = back.strip() == content.strip()
        md5 = hashlib.md5(back.encode("utf-8")).hexdigest()
        print(f"[{'OK' if same else 'DIFF'}] {data_id} bytes={len(back)} md5={md5} match={same}")
        if not same:
            ok = False
    print("RESULT:", "ALL_OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
