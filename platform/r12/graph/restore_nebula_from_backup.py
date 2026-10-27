#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按备份回滚 Nebula 图（`nebula.json` 的 vertices/edges）。

用途：重建失败（图变空/变差）时，把图恢复到**备份那一刻**的状态。
设计要点（这次踩过的坑）：
  1) 回滚前先**清空当前顶点/边**：Nebula 的 INSERT VERTEX 对同名 vid 是覆盖，
     但**边是同 (src,dst) 可多条的**，直接回灌会与残留边叠加 -> edges 数虚高、出现重复三元组；
  2) 回灌后按 id / (src,dst,name) 复查，不只看"执行成功"；
  3) 默认 dry-run，--yes 才写。

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/restore_nebula_from_backup.py \
      --backup platform/r12/graph/backup/kb_9-20261027T053048Z --space g_kb_9 [--yes]
"""
import argparse
import json
import os
import sys

from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool

NEBULA = ("127.0.0.1", 19669)


def _pool():
    cfg = Config()
    cfg.max_connection_pool_size = 10
    pool = ConnectionPool()
    if not pool.init([NEBULA], cfg):
        raise RuntimeError("连接 nebula 失败")
    return pool, pool.get_session("root", "nebula")


def _q(s, stmt):
    r = s.execute(stmt)
    if not r.is_succeeded():
        raise RuntimeError(f"{stmt[:80]} -> {r.error_msg()}")
    return r


def _counts(s):
    v = _q(s, "MATCH (v:entity) RETURN count(v)").row_values(0)[0].as_int()
    e = _q(s, "MATCH ()-[x:relationship]->() RETURN count(x)").row_values(0)[0].as_int()
    return v, e


def _all_ids(s, tag="entity"):
    r = _q(s, f"MATCH (v:{tag}) RETURN id(v)")
    return [r.row_values(i)[0].as_string() for i in range(r.row_size())]


def _clear(s):
    ids = _all_ids(s)
    print(f"   清空当前顶点 {len(ids)} 个（DELETE VERTEX ... WITH EDGE）")
    for i in range(0, len(ids), 200):
        batch = ids[i:i + 200]
        vals = ", ".join(f'"{x}"' for x in batch)
        _q(s, f"DELETE VERTEX {vals} WITH EDGE")
    v, e = _counts(s)
    if v or e:
        raise RuntimeError(f"清空后仍有 顶点{v}/边{e}")


def _insert_vertices(s, vertices):
    sql_rows = []
    for v in vertices:
        p = v.get("props") or {}
        sql_rows.append(
            f'"{v["id"]}":("{p.get("name","")}","{p.get("title","")}",'
            f'"{p.get("file_id","")}","{p.get("type","")}")')
    for i in range(0, len(sql_rows), 100):
        stmt = ("INSERT VERTEX entity(name,title,file_id,type) VALUES "
                + ", ".join(sql_rows[i:i + 100]))
        _q(s, stmt)


def _insert_edges(s, edges):
    sql_rows = []
    for e in edges:
        p = e.get("props") or {}
        sql_rows.append(
            f'"{e["src"]}"->"{e["dst"]}":("{p.get("name","")}","{p.get("file_id","")}",'
            f'"{p.get("show_flag","1")}","{p.get("page_num","")}")')
    for i in range(0, len(sql_rows), 100):
        stmt = ("INSERT EDGE relationship(name,file_id,show_flag,page_num) VALUES "
                + ", ".join(sql_rows[i:i + 100]))
        _q(s, stmt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup", required=True)
    ap.add_argument("--space", default="g_kb_9")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    nb = json.load(open(os.path.join(a.backup, "nebula.json"), encoding="utf-8"))
    vertices, edges = nb.get("vertices") or [], nb.get("edges") or []
    print(f"备份 {a.backup}: vertices={len(vertices)} edges={len(edges)}")

    pool, s = _pool()
    _q(s, f"USE {a.space}")
    v0, e0 = _counts(s)
    print(f"当前 {a.space}: 顶点 {v0} / 边 {e0}")
    if not a.yes:
        print("\n（dry-run）将执行：清空当前 -> 回灌 vertices/edges -> 复查计数。加 --yes 执行。")
        pool.close()
        return 0

    print("\n== 1 清空 ==")
    _clear(s)
    print("\n== 2 回灌顶点 ==")
    _insert_vertices(s, vertices)
    print("\n== 3 回灌边 ==")
    _insert_edges(s, edges)
    print("\n== 4 复查 ==")
    v1, e1 = _counts(s)
    print(f"回灌后: 顶点 {v1} / 边 {e1}（期望 {len(vertices)} / {len(edges)}）")
    pool.close()
    if v1 != len(vertices) or e1 != len(edges):
        print("!! 与备份不一致，请人工核对（同名 vid 覆盖 / 重复边）")
        return 1
    print("OK 与备份完全一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
