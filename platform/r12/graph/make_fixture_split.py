#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""方案 C 夹具：把 02 拆成 02a(背景) / 02b(答案事实)，**串行上传 + 每篇确认入库**。

为什么新建库而不是改 kb_22：
  · kb_22 的 01 是"并发建索引 400 -> 文件静默丢失"的现场物证（TL 要求保留）；
  · 拆分后 02 必须消失（否则旧块仍会被词面召回，② 恒红），而删文件要动 Java 侧接口；
  · 因此新建 `graph-increment-split`，kb_22 原样冻结。

前置（方案 C 三条，TL 2026-10-27 裁决）：
  ① 词面：问句关键词不在 02b 中出现；
  ② 向量：关图 top_k=5 时 02b 的 chunk 不在返回里；
  ③ 图  ：装备制造事业部 的 chunk_pk_list 必须包含 02b 的 chunk id。

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/make_fixture_split.py
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_fixture_kb as M  # noqa: E402  复用 login/upload/es_state

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
EVID = os.path.join(HERE, "evidence")
KB_NAME = "graph-increment-split"
DOCS = [
    "R14FIX-graph-01-project.docx",   # 恒星项目 -> 启明计划（保留原链的起点）
    "R14FIX-graph-02a-plan.docx",     # 启明计划背景（不含任何目标实体）
    "R14FIX-graph-02b-dept.docx",     # 答案事实：装备制造事业部承接启明计划
    "R14FIX-graph-03-noise.docx",     # 噪声
]


def create_kb(s, token):
    payload = {"kbName": KB_NAME,
               "kbDes": "图增量夹具-方案C（02 拆段）：验证'仅图可达块'能否被带进上下文",
               "fileType": "naive", "chunkSize": 512, "chunkOverlap": 50,
               "embeddingModelName": "bge-m3", "privateKb": 0, "platform": "rag-qa"}
    return M.api(s, "POST", "/index/knowledgeBase/create", token, json=payload)


def find_kb(s, token):
    code, body = M.api(s, "GET", "/index/knowledgeBase/list?pageNo=1&pageSize=100", token)
    recs = ((body.get("data") or {}).get("records") or []) if isinstance(body, dict) else []
    for r in recs:
        if isinstance(r, dict) and r.get("kbName") == KB_NAME:
            return r
    return None


def main():
    s, token, _ = M.login()
    kb = find_kb(s, token)
    if kb:
        kb_id = kb["id"]
        print(f"[1] 复用已存在的拆分夹具库 kbId={kb_id}（如需重建请先确认，脚本不自动删库）")
    else:
        code, body = create_kb(s, token)
        data = (body.get("data") or {}) if isinstance(body, dict) else {}
        kb_id = data.get("id")
        print(f"[1] 建库 http={code} kbId={kb_id}")
        if not kb_id:
            print("  !! 建库失败:", json.dumps(body, ensure_ascii=False)[:300])
            return 1

    # 串行上传：每篇等它真的进了 ES 再传下一篇（TL 硬要求，且可暴露"并发建索引 400"）
    report = []
    for name in DOCS:
        before = M.es_state(kb_id).get(f"kb_{kb_id}")
        before = before if isinstance(before, int) else 0
        code, body = M.upload(s, token, kb_id, os.path.join(FIXTURES, name))
        ok = code == 200 and isinstance(body, dict) and body.get("success", True)
        print(f"[2] 上传 {name} -> http={code} success={ok}")
        grew = False
        for _ in range(18):
            time.sleep(5)
            now = M.es_state(kb_id).get(f"kb_{kb_id}")
            if isinstance(now, int) and now > before:
                grew = True
                print(f"    入库确认：kb_{kb_id} {before} -> {now}")
                break
        if not grew:
            print(f"    !! {name} 未入库（可能是解析/建索引失败，属 A 的 ensure-then-insert 那条）")
        report.append({"doc": name, "http": code, "success": ok, "indexed": grew,
                       "blocks_before": before})

    state = M.es_state(kb_id)
    print("[3] ES 现状:", json.dumps(state, ensure_ascii=False))
    os.makedirs(EVID, exist_ok=True)
    out = os.path.join(EVID, "R14-B-fixture-split-"
                       f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"kb_name": KB_NAME, "kb_id": kb_id, "space": f"g_kb_{kb_id}",
                   "docs": DOCS, "per_doc": report, "es": state}, f, ensure_ascii=False, indent=1)
    print("[evidence]", out)
    print(f"\n[下一步] 只抽这一个库的图：POST 19529/generate_triple_data "
          f'{{"space_name":"kb_{kb_id}"}}')
    print(f"[然后] platform/r12/venvs/graph/bin/python platform/r12/graph/check_fixture_target_pk.py kb_{kb_id} 装备制造事业部")
    return 0


if __name__ == "__main__":
    sys.exit(main())
