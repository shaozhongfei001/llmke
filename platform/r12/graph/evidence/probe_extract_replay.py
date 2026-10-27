#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""离线复放：图抽取"抽不到评级加点映射"的对照实验（只读，不碰服务、不写库）。

背景
----
R14 图侧重建后 G1（AAA/AA/A -> 30/60/100 个基点）断裂。曾提出三种解释并被逐一检验：
  1) max_tokens / count<2 截断      -> 用 2048 与 8192 对照，输出一致（证伪）
  2) is_continue `== "Y"` 判等      -> 1 token 时恰好返回 'Y'（无换行），线上未触发
  3) entity_types 与业务实体不匹配  -> 单次实验"看似"成立，但**重复实验显示单次结果随机**
本脚本的作用就是让下一个人能自己复现第 3 条到底站不站得住。

关键结论（2026-10-27 实测）
--------------------------
同一块、同 prompt、同实体类型表，连跑 5 次：3 次抽出全部 30/60/100 个基点、2 次一个都不出。
temperature=0 也不稳定 => 调用方不能拿"单次没抽到"当能力上限，必须看命中率。

用法
----
    platform/r12/venvs/graph/bin/python probe_extract_replay.py \
        --doc-id 139363536840301567 --reps 3 --out replay.json

输出
----
每个组合（segment × entity_types）的逐次结果 + 命中率汇总，字段见 --out 的 json。
"""
import argparse
import json
import sys
import urllib.request

REPO = "/home/szf/data/dev/llmke-r12"
sys.path.insert(0, f"{REPO}/services/rag-alg/index_data_service/index_graph_service")

from prompts.entity_extraction import system_prompt, user_prompt  # noqa: E402

ES = "http://127.0.0.1:19200"
LLM = "http://127.0.0.1:18092/v1/chat/completions"
MODEL = "qwen2.5-7b-instruct"

# base.py:69 的默认值（线上未传 entity_types 时吃的就是这 8 类）
DEFAULT_TYPES = ["人", "机构", "位置", "时间", "角色", "疾病", "药品", "项目"]
# graph_types.py 的 v1 业务类型（归一化阶段赋的类型，不是抽取时用的）
BIZ_TYPES = ["机构", "评级", "金额", "指标", "期限", "产品", "条款", "编号"]

EK = '("entity"::'
RK = '("relationship"::'
BP_KEYS = ("30个基点", "60个基点", "100个基点")

# 一句补充要求即可把"长块 + 默认类型"从 1/3 拉到 3/3（实测，seed=42）
NUDGE = ("\n\n补充要求：文中若有“评级/档次 → 具体取值”这类对照（例如 AAA级加30个基点），"
         "必须逐项抽成实体与关系，不得省略或概括。")


def es_doc(doc_id):
    with urllib.request.urlopen(f"{ES}/kb_9/_doc/{doc_id}") as r:
        return json.load(r)["_source"]


def chat(messages, temperature=0.01, max_tokens=2048, seed=None):
    payload = {"model": MODEL, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    if seed is not None:
        payload["seed"] = seed
    body = json.dumps(payload).encode()
    req = urllib.request.Request(LLM, data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    c = d["choices"][0]
    return c["message"]["content"], c.get("finish_reason"), (d.get("usage") or {})


def one_run(passage, types, temperature=0.01, max_tokens=2048, seed=None, nudge=""):
    user = user_prompt.format(passage=passage, entity_types=",".join(types)) + nudge
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": user}]
    out, finish, usage = chat(messages, temperature=temperature,
                              max_tokens=max_tokens, seed=seed)
    return {
        "prompt_chars": len(system_prompt) + len(user),
        "out_chars": len(out),
        "entities": out.count(EK),
        "relationships": out.count(RK),
        "has_AAA": "AAA" in out,
        "basis_points": [k for k in BP_KEYS if k in out],
        "finish_reason": finish,
        "completion_tokens": (usage or {}).get("completion_tokens"),
        "raw_head": out[:200],
    }


def summarize(runs):
    n = len(runs)
    return {
        "reps": n,
        "hit_AAA": sum(1 for r in runs if r["has_AAA"]),
        "hit_any_basis_point": sum(1 for r in runs if r["basis_points"]),
        "hit_all_three": sum(1 for r in runs if len(r["basis_points"]) == 3),
        "entities_avg": round(sum(r["entities"] for r in runs) / n, 2),
        "finish_reasons": sorted({str(r["finish_reason"]) for r in runs}),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-id", default="139363536840301567")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.01)
    ap.add_argument("--seed", type=int, default=42,
                    help="固定采样；修复前后对照必须用同一 seed，否则是跨口径比较")
    ap.add_argument("--nudge", action="store_true",
                    help="在 user prompt 末尾追加『分级/分档对照逐项抽取』一句")
    ap.add_argument("--out", default="replay.json")
    a = ap.parse_args()

    chunk = es_doc(a.doc_id)["page_content"]
    md = (es_doc(a.doc_id).get("metadata") or {})
    # 459 字块按分节切；评级加点表是行内文字（该块没有 table_pos，无法按表格坐标切）
    seg_a = chunk[304:350]            # 仅评级表句
    seg_b = chunk[:150] + seg_a       # 前文 150 字 + 评级表句
    cells = [
        ("A_only_rating_sentence|default_types", seg_a, DEFAULT_TYPES),
        ("B_prefix150+rating|default_types", seg_b, DEFAULT_TYPES),
        ("C_full_chunk|default_types", chunk, DEFAULT_TYPES),
        ("A_only_rating_sentence|biz_types", seg_a, BIZ_TYPES),
        ("C_full_chunk|biz_types", chunk, BIZ_TYPES),
    ]

    result = {"doc_id": a.doc_id, "file_id": md.get("file_id"), "chunk_chars": len(chunk),
              "temperature": a.temperature, "seed": a.seed, "nudge": bool(a.nudge),
              "reps": a.reps, "cells": []}
    for name, passage, types in cells:
        runs = [one_run(passage, types, temperature=a.temperature, seed=a.seed,
                        nudge=NUDGE if a.nudge else "") for _ in range(a.reps)]
        cell = {"cell": name, "passage_chars": len(passage), "entity_types": types,
                "summary": summarize(runs), "runs": runs}
        result["cells"].append(cell)
        s = cell["summary"]
        print(f"{name:42s} passage={len(passage):4d} "
              f"AAA {s['hit_AAA']}/{s['reps']}  基点 {s['hit_any_basis_point']}/{s['reps']}  "
              f"全三条 {s['hit_all_three']}/{s['reps']}  ent均值={s['entities_avg']}")

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"written -> {a.out}")


if __name__ == "__main__":
    main()
