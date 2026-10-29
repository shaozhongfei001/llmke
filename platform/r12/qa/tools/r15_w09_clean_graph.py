#!/usr/bin/env python3
"""R15-W09：对既有图做一次"清洗 + 归一"，用于验证两条新规则的收益。

背景（实测 kb_9）：
  · 64 个实体里 17 个是整句（"放款是智造贷办理流程的一部分"），占 27%；
  · 5 个金额是带前缀的变体（"人民币1000万元"），本应早已归一；
  · 64 个实体里只有 1 个跨文件（"日均存款"），图成了 4 个孤岛。

本脚本做两件事，且**先备份再改**：
  ① 删除 sentence_entity 类型的顶点（WITH EDGE，连带其边）
  ② 把 numeric_canon 能归一的金额变体合并到规范名（复制边 → 删旧点）

用法：
    platform/r12/venvs/graph/bin/python platform/r12/qa/tools/r15_w09_clean_graph.py --dry-run
    platform/r12/venvs/graph/bin/python platform/r12/qa/tools/r15_w09_clean_graph.py --apply

--dry-run 只统计与导出快照，不改动；--apply 才真正执行。
快照与统计落在 platform/r12/qa/evidence/r15/w09-clean/。
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service/index_graph_service"))

import graph_types as G  # noqa: E402

from nebula3.Config import Config  # noqa: E402
from nebula3.gclient.net import ConnectionPool  # noqa: E402

SPACE = os.environ.get("R15_SPACE", "g_kb_9")
OUT = os.path.join(ROOT, "platform/r12/qa/evidence/r15/w09-clean")


def _sess():
    cfg = Config()
    cfg.max_connection_pool_size = 2
    pool = ConnectionPool()
    pool.init([(os.environ.get("R15_NEBULA_HOST", "127.0.0.1"),
                int(os.environ.get("R15_NEBULA_PORT", "19669")))], cfg)
    s = pool.get_session(os.environ.get("R15_NEBULA_USER", "root"),
                         os.environ.get("R15_NEBULA_PASS", "nebula"))
    r = s.execute("USE " + SPACE)
    if not r.is_succeeded():
        raise SystemExit(f"USE {SPACE} 失败: {r.error_msg()}")
    return pool, s


def snapshot(s):
    """全量导出顶点与边：任何破坏性操作之前必须先能回滚。"""
    ents = []
    # properties(v) 返回 map，不能 as_string()；只取需要的标量属性
    r = s.execute("MATCH (v:entity) RETURN id(v),properties(v).type,properties(v).file_id")
    for i in range(r.row_size()):
        row = r.row_values(i)
        ents.append({"name": row[0].as_string(),
                     "type": row[1].as_string() if row[1].is_string() else "",
                     "file_id": row[2].as_string() if row[2].is_string() else ""})
    edges = []
    r = s.execute("MATCH (v:entity)-[e:relationship]->(v2:entity) "
                  "RETURN id(v),id(v2),rank(e),properties(e).file_id,properties(e).name,"
                  "properties(e).show_flag,properties(e).page_num")
    for i in range(r.row_size()):
        v = [r.row_values(i)[j] for j in range(7)]
        edges.append({"src": v[0].as_string(), "dst": v[1].as_string(),
                      "rank": v[2].as_int(), "file_id": v[3].as_string(),
                      "rel": v[4].as_string(), "show": v[5].as_string(),
                      "page": v[6].as_string()})
    return {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "space": SPACE,
            "entities": ents, "edges": edges}


def stats(snap):
    files = {}
    for e in snap["edges"]:
        files.setdefault(e["file_id"], 0)
        files[e["file_id"]] += 1
    ent_files = {}
    for e in snap["edges"]:
        ent_files.setdefault(e["src"], set()).add(e["file_id"])
        ent_files.setdefault(e["dst"], set()).add(e["file_id"])
    cross = sorted([k for k, v in ent_files.items() if len(v) >= 2])
    return {"entities": len(snap["entities"]), "edges": len(snap["edges"]),
            "edges_by_file": dict(sorted(files.items(), key=lambda x: -x[1])),
            "cross_file_entities": cross, "cross_file_count": len(cross)}


def classify(snap):
    sent, amount, keep = [], [], []
    for e in snap["entities"]:
        n = e["name"]
        ok, reason = G.is_valid_entity(n)
        if not ok and reason == "sentence_entity":
            sent.append(n)
            continue
        c, changed = G.numeric_canon(n)
        if changed and c != n and c in {x["name"] for x in snap["entities"]} | {c}:
            amount.append((n, c))
        else:
            keep.append(n)
    return sent, amount, keep


def _q(v):
    return '"' + str(v).replace('"', '\\"') + '"'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正执行（默认 dry-run）")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    pool, s = _sess()
    try:
        before = snapshot(s)
        with open(os.path.join(OUT, "snapshot-before.json"), "w", encoding="utf-8") as f:
            json.dump(before, f, ensure_ascii=False, indent=1)

        st_before = stats(before)
        sent, amount, keep = classify(before)

        print(f"空间 {SPACE}")
        print(f"清洗前：实体 {st_before['entities']}  边 {st_before['edges']}  "
              f"跨文件实体 {st_before['cross_file_count']} {st_before['cross_file_entities']}")
        print(f"  句子型实体 {len(sent)} 个（将删除）")
        for x in sent:
            print(f"    - {x}")
        print(f"  可归一金额 {len(amount)} 个（将合并）")
        for a, b in amount:
            print(f"    {a} -> {b}")

        if not args.apply:
            print("\n[dry-run] 未改动。加 --apply 执行。")
            return 0

        # ① 删除句子型顶点（连带边）
        ok = 0
        for n in sent:
            r = s.execute(f"DELETE VERTEX {_q(n)} WITH EDGE")
            ok += 1 if r.is_succeeded() else 0
            if not r.is_succeeded():
                print(f"  [WARN] 删除失败 {n}: {r.error_msg()[:80]}")
        print(f"\n① 已删除句子型顶点 {ok}/{len(sent)}")

        # ② 金额变体合并：复制边到规范名，再删旧点
        ent_set = {e["name"] for e in before["entities"]}
        merged_edges = 0
        for old, new in amount:
            outs = [e for e in before["edges"] if e["src"] == old]
            ins = [e for e in before["edges"] if e["dst"] == old]
            if new not in ent_set:
                files = sorted({e["file_id"] for e in outs + ins})
                fids = ",".join(files) or "0"
                s.execute(f"INSERT VERTEX entity(name,type,file_id,show_flag) "
                          f"VALUES {_q(new)}:({_q(new)},\"金额\",{_q(fids)},\"1\")")
                ent_set.add(new)
            for e in outs:
                s.execute("INSERT EDGE relationship(name,file_id,show_flag,page_num) VALUES "
                          f"{_q(new)}->{_q(e['dst'])}@{e['rank']}:"
                          f"({_q(e['rel'])},{_q(e['file_id'])},{_q(e['show'])},{_q(e['page'])})")
                merged_edges += 1
            for e in ins:
                s.execute("INSERT EDGE relationship(name,file_id,show_flag,page_num) VALUES "
                          f"{_q(e['src'])}->{_q(new)}@{e['rank']}:"
                          f"({_q(e['rel'])},{_q(e['file_id'])},{_q(e['show'])},{_q(e['page'])})")
                merged_edges += 1
            r = s.execute(f"DELETE VERTEX {_q(old)} WITH EDGE")
            print(f"  合并 {old} -> {new}  复制边 {len(outs)+len(ins)}  "
                  f"删除{'成功' if r.is_succeeded() else '失败'}")
        print(f"② 合并金额变体 {len(amount)} 个，复制边 {merged_edges} 条")

        after = snapshot(s)
        with open(os.path.join(OUT, "snapshot-after.json"), "w", encoding="utf-8") as f:
            json.dump(after, f, ensure_ascii=False, indent=1)
        st_after = stats(after)

        print("\n清洗后：实体 %d  边 %d  跨文件实体 %d %s"
              % (st_after["entities"], st_after["edges"],
                 st_after["cross_file_count"], st_after["cross_file_entities"]))
        print("  边按文件：" + ", ".join(f"{k}={v}" for k, v in st_after["edges_by_file"].items()))

        rep = {"before": st_before, "after": st_after,
               "sentence_removed": sent, "amount_merged": amount}
        with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        print(f"\n[evidence] {OUT}")
        return 0
    finally:
        s.release()
        pool.close()


if __name__ == "__main__":
    sys.exit(main())
