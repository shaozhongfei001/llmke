#!/usr/bin/env python3
"""创建图增量夹具知识库并入库三篇夹具（显示名固定，id 运行时取）。

规则（TL 13:1x 裁定）：
  · **不硬编码 id**：kb_21 已被 F 的验收库占用且每轮删建重建；
    这里用显示名 `graph-increment-fixture`，实际 id 从建库响应里取，并写进证据。
  · 只写自己的 Nebula space `g_kb_<id>`，绝不碰 `g_kb_9`。
  · 建前建后各跑一次 kb_9 指纹，证明未触碰（fixture_check 的第 ⑤ 条）。

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/make_fixture_kb.py [--recreate]
  不给 --recreate 时：若同名库已存在则直接复用并把 id 记进证据。
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import GATEWAY, UA, api, login  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
EVID = os.path.join(HERE, "evidence")
KB_NAME = "graph-increment-fixture"
DOCS = ["R14FIX-graph-01-project.docx",
        "R14FIX-graph-02-dept.docx",
        "R14FIX-graph-03-noise.docx"]


def find_kb(s, token):
    code, body = api(s, "GET", "/index/knowledgeBase/list?pageNo=1&pageSize=100", token)
    recs = ((body.get("data") or {}).get("records") or []) if isinstance(body, dict) else []
    for r in recs:
        if isinstance(r, dict) and r.get("kbName") == KB_NAME:
            return r
    return None


def create_kb(s, token):
    payload = {"kbName": KB_NAME,
               "kbDes": "图增量夹具（验收用，非业务数据）：验证'仅图可达块'能否被带进上下文",
               "fileType": "naive", "chunkSize": 512, "chunkOverlap": 50,
               "embeddingModelName": "bge-m3", "privateKb": 0, "platform": "rag-qa"}
    return api(s, "POST", "/index/knowledgeBase/create", token, json=payload)


def delete_kb(s, token, kb_id):
    return api(s, "DELETE", f"/index/knowledgeBase/delete?id={kb_id}", token)


def upload(s, token, kb_id, path):
    fname = os.path.basename(path)
    param = {"kbId": int(kb_id),
             "fileList": [{"fileName": fname, "type": "OVERWRITE",
                           "uid": f"r14fix-{int(time.time() * 1000)}"}],
             "fileListType": 1, "isParse": True, "isExtract": False, "isGraphParse": False,
             "chunking": True, "needChunk": True, "saveTxt": True, "platform": "rag-qa"}
    with open(path, "rb") as f:
        files = [("files", (fname, f, "application/octet-stream"))]
        r = requests.post(f"{GATEWAY}/index/knowledgeBase/file/uploadFileList",
                          data={"uploadFileParam": json.dumps(param, ensure_ascii=False)},
                          files=files,
                          headers={"Authorization": token, "X-Platform": "rag-qa", "User-Agent": UA},
                          timeout=300)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text[:300]


def es_state(kb_id):
    """夹具库的 ES 现状：索引与条数（用于确认入库真的成功）。"""
    out = {}
    for idx in (f"kb_{kb_id}", f"table_chunks_kb_{kb_id}", f"table_summary_kb_{kb_id}"):
        try:
            r = requests.post(f"http://127.0.0.1:19200/{idx}/_search",
                              json={"query": {"match_all": {}}, "size": 2000}, timeout=60)
            j = r.json()
            out[idx] = j.get("hits", {}).get("total", {}).get("value")
        except Exception as e:
            out[idx] = f"ERR {str(e)[:60]}"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recreate", action="store_true")
    a = ap.parse_args()

    s, token, _ = login()
    kb = find_kb(s, token)
    if kb and a.recreate:
        print(f"[0] 删除同名旧库 kbId={kb['id']}")
        delete_kb(s, token, kb["id"])
        kb = None
    if kb:
        kb_id = kb["id"]
        print(f"[1] 复用已存在的夹具库 kbId={kb_id}")
    else:
        code, body = create_kb(s, token)
        data = (body.get("data") or {}) if isinstance(body, dict) else {}
        kb_id = data.get("id")
        print(f"[1] 建库 http={code} kbId={kb_id} primitive={data.get('primitiveName')}")
        if not kb_id:
            print("  !! 建库失败:", json.dumps(body, ensure_ascii=False)[:300])
            return 1

    for name in DOCS:
        path = os.path.join(FIXTURES, name)
        code, body = upload(s, token, kb_id, path)
        ok = code == 200 and isinstance(body, dict) and body.get("success", True)
        print(f"[2] 上传 {name} -> http={code} ok={ok} {str(body)[:140]}")

    print("[3] 等待解析/索引…")
    state = {}
    for _ in range(12):
        time.sleep(5)
        state = es_state(kb_id)
        if isinstance(state.get(f"kb_{kb_id}"), int) and state[f"kb_{kb_id}"] > 0:
            break
    print("[4] ES 现状:", json.dumps(state, ensure_ascii=False))

    os.makedirs(EVID, exist_ok=True)
    out = os.path.join(EVID, "R14-B-fixture-kb-"
                       f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"kb_name": KB_NAME, "kb_id": kb_id, "space": f"g_kb_{kb_id}",
                   "es": state, "docs": DOCS}, f, ensure_ascii=False, indent=1)
    print("[evidence]", out)
    print(f"\n[下一步] 图抽取：POST 19529/generate_triple_data "
          f'{{"space_name":"kb_{kb_id}","model_info":...}}')
    print(f"[然后] platform/r12/graph/fixture_check.py --kb kb_{kb_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
