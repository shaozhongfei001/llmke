#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb_9 图**全量重建**：del_space -> 建 schema -> 全量重抽 -> 重建社区 -> 五条判据。

为什么需要这个驱动（而不是直接跑 rebuild_kb9_effective.py）：
  那个脚本的 `del_space` 传的是 **"kb_9"**，而真实 space 是 **"g_kb_9"**；
  `del_space` 内部是 `DROP SPACE IF EXISTS {name}`，名字不存在 **也返回 200「删除成功」**。
  实测证明：传不带前缀的名字 -> 空间仍在、零删除；传 `g_kb_9` -> 空间真的消失。
  于是"重建"退化成"追加"：87 -> 91，55 个旧代顶点、76/126 条旧代边全部留存，
  R1/R2/R4 的归一化一个字都没落库（16 个探针词全为 1）。

本脚本的三条护栏（TL 2026-10-27 定为项目模板）：
  ① 默认 dry-run，必须显式 --yes 才动；
  ② 开工前查进程：检测到 acceptance.py / 基线在跑 -> 拒绝执行（退出码 2）；
  ③ 打印"将要影响的对象与数量"（顶点/边/待抽块数），数字对不上就停。

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/rebuild_kb9_full.py            # 只出计划
  platform/r12/venvs/graph/bin/python platform/r12/graph/rebuild_kb9_full.py --yes      # 执行
"""
import argparse
import json
import os
import subprocess
import sys
import time

import requests
from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from init_space import TAGS, EDGES  # noqa: E402  schema 定义与 init_space 同源
from rebuild_kb9_effective import _scan, MODEL_INFO  # noqa: E402  有效版本 file_id 计算同源

NEBULA = ("127.0.0.1", 19669)
GRAPH = "http://127.0.0.1:19529"
SNAPSHOT = os.path.abspath(os.path.join(
    HERE, "..", "qa", "evidence", "R14-A-20261027T021902Z", "snapshot_graph_vertices.py"))
EVID = os.path.join(HERE, "evidence")
BLOCKING = ("acceptance.py",)
PROBES = ["加30个基点", "加60个基点", "加100个基点", "30个基点", "60个基点", "100个基点",
          "人民币5000万元", "5000万元", "人民币1000万元", "1000万元",
          "八千万元", "8000万元", "额度", "万元", "已用额度", "授信额度"]


# ---------------------------------------------------------------- 基础设施
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
        raise RuntimeError(f"{stmt[:70]} -> {r.error_msg()}")
    return r


def _spaces(s):
    r = _q(s, "SHOW SPACES")
    return [r.row_values(i)[0].as_string() for i in range(r.row_size())]


def _counts(s, space):
    _q(s, f"USE {space}")
    v = _q(s, "MATCH (v:entity) RETURN count(v)").row_values(0)[0].as_int()
    e = _q(s, "MATCH ()-[x:relationship]->() RETURN count(x)").row_values(0)[0].as_int()
    return v, e


def _blocking_procs():
    try:
        out = subprocess.run(["ps", "-eo", "pid,etime,cmd"], capture_output=True,
                             text=True, timeout=10).stdout
    except Exception:
        return []
    return [ln.strip() for ln in out.splitlines()[1:]
            if any(p in ln for p in BLOCKING) and "grep" not in ln]


def _snapshot(space, out_path):
    py = sys.executable
    print(f"   $ {py} {SNAPSHOT} {space} {out_path}")
    r = subprocess.run([py, SNAPSHOT, space, out_path], capture_output=True, text=True)
    tail = (r.stdout or "").strip().splitlines()
    for ln in tail[-6:]:
        print("    ", ln)
    if r.returncode != 0:
        raise RuntimeError(f"快照失败 rc={r.returncode}: {(r.stderr or '')[:200]}")
    with open(out_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- schema
def _create_schema(s, space, wait=12):
    _q(s, f"CREATE SPACE IF NOT EXISTS {space} "
          f"(partition_num=10, replica_factor=1, vid_type=FIXED_STRING(500))")
    print(f"   .. 等待 space 生效 {wait}s")
    time.sleep(wait)
    _q(s, f"USE {space}")
    for tag, props in TAGS.items():
        _q(s, f"CREATE TAG IF NOT EXISTS {tag}({props})")
        for p in [x.split()[0] for x in props.split(",")]:
            _q(s, f"CREATE TAG INDEX IF NOT EXISTS {tag}_{p}_index ON {tag}({p}(200))")
    for edge, props in EDGES.items():
        _q(s, f"CREATE EDGE IF NOT EXISTS {edge}({props})")
        for p in [x.split()[0] for x in props.split(",")]:
            _q(s, f"CREATE EDGE INDEX IF NOT EXISTS {edge}_{p}_index ON {edge}({p}(200))")
    # 索引创建是**异步**的：立刻 REBUILD 会报 "Index ... not found"。
    # 这不是致命错误（数据写入不依赖索引，只是后续按属性过滤会变慢），
    # 所以这里等待 + 失败只警告，不中断重建——否则会在"建 schema"这一步白白停掉。
    time.sleep(10)
    for kind, items in (("TAG", TAGS), ("EDGE", EDGES)):
        for name, props in items.items():
            for p in [x.split()[0] for x in props.split(",")]:
                idx = f"{name}_{p}_index"
                r = s.execute(f"REBUILD {kind} INDEX {idx}")
                if not r.is_succeeded():
                    print(f"   .. 警告：REBUILD {kind} INDEX {idx} 失败（索引可能尚未就绪，不阻断）: {r.error_msg()[:60]}")
    time.sleep(3)


# ---------------------------------------------------------------- 判据
def _judge(snap, expect_vertices=79):
    gen = snap.get("generation") or {}
    eg = snap.get("edge_generation") or {}
    probes = snap.get("probe") or {}
    total = snap.get("vertices")
    unc = snap.get("unclassified")
    rows = []
    rows.append(("① 顶点数", total, f"== {expect_vertices}（M1a 预期）",
                 total == expect_vertices))
    rows.append(("② vertex old_only", gen.get("old_only"), "== 0", gen.get("old_only") == 0))
    pz = {k: probes.get(k) for k in PROBES}
    rows.append(("③ 探针 16 项", sum(1 for v in pz.values() if v), "全为 0",
                 all((pz.get(k) or 0) == 0 for k in PROBES)))
    rows.append(("④ unclassified", unc, "<= 34/91 (37.4%)",
                 isinstance(unc, (int, float)) and unc <= 34 / 91 * (total or 91)))
    rows.append(("⑤ edge old_only", eg.get("old_only"), "== 0", eg.get("old_only") == 0))
    print("\n== 判据 ==")
    ok = True
    for name, val, rule, passed in rows:
        print(f"   {'PASS' if passed else 'FAIL'}  {name}: {val}   ({rule})")
        ok = ok and passed
    print(f"   [dup_triples] {snap.get('dup_triples')}  （只记录，不作硬阈值）")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="真正执行（会 DROP SPACE g_kb_9）")
    ap.add_argument("--space", default="g_kb_9")
    ap.add_argument("--kb", default="kb_9")
    ap.add_argument("--skip-snapshot", action="store_true")
    ap.add_argument("--expect-vertices", type=int, default=79)
    ap.add_argument("--force", action="store_true",
                    help="紧急恢复：即使检测到验收进程也继续（仅用于把空图恢复回来，须在群里声明）")
    ap.add_argument("--resume", action="store_true",
                    help="space 已被 DROP 并重建、数据为空时，跳过 DROP 直接补 schema + 重抽")
    a = ap.parse_args()

    print("== 1 环境前置检查 ==")
    blocked = _blocking_procs()
    if blocked:
        print("!! 检测到验收/基线进程正在运行：")
        for b in blocked:
            print("   ", b)
        if a.yes and a.force:
            print("   ！--force：图中断恢复模式，强行继续（验收需在恢复后重跑）")
        elif a.yes:
            print("   拒绝执行（--yes 已给）：图断言会成片假红且归因不到任何人。")
            print("   若图当前为空、先恢复数据，用 --force 并在群里声明。")
            return 2
        print("   （当前是 dry-run，只读，继续打印计划；真实执行会被拒绝）")
    else:
        print("   OK 无验收进程在跑")
    if not os.path.exists(SNAPSHOT):
        print(f"!! 缺快照脚本 {SNAPSHOT}，无法做重建前后对照")
        return 2
    print(f"   OK 快照脚本存在")

    pool, s = _pool()
    spaces = _spaces(s)
    if a.space not in spaces:
        print(f"!! {a.space} 不在 SHOW SPACES 里：{sorted(spaces)}")
        return 2
    v, e = _counts(s, a.space)
    print(f"   当前 {a.space}: 顶点 {v} / 边 {e}")

    docs, eff, eff_fids, dropped = _scan(a.kb)
    print("\n== 2 计划（dry-run 也打印，数字对不上就停）==")
    print(f"   DROP SPACE {a.space}                 -> 预计删除 {v} 顶点 / {e} 边")
    print(f"   重建 schema                          -> TAG {list(TAGS)} / EDGE {list(EDGES)}")
    print(f"   重抽 col_values(file_id)={eff_fids}  -> 预计 {len(eff)} 块")
    print(f"   重建社区                             -> 现有摘要 7 条，file_ids 刷新为新代")
    print(f"   （被排除的 V0/汇总块：{[d['id'] for d in dropped]}）")

    if not a.yes:
        print("\n（未加 --yes，只打印计划，未做任何写入）")
        pool.close()
        return 0

    os.makedirs(EVID, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    pre_path = os.path.join(EVID, f"R14-B-rebuild-pre-{ts}.json")
    post_path = os.path.join(EVID, f"R14-B-rebuild-post-{ts}.json")

    print("\n== 3 pre 快照 ==")
    if a.resume or a.skip_snapshot:
        print("   （resume / skip：沿用上一次 pre 快照 %s）" % pre_path)
        pre = {}
    else:
        pre = _snapshot(a.space, pre_path)
    if pre and pre.get("vertices") != v:
        print(f"!! pre 快照顶点数 {pre.get('vertices')} 与实时计 {v} 不一致，停止")
        pool.close()
        return 2

    if a.resume:
        print("\n== 4 [resume] 跳过 DROP（space 已重建、数据为空）==")
        cur_v, cur_e = _counts(s, a.space)
        if cur_v or cur_e:
            print(f"!! resume 但空间非空（顶点 {cur_v} / 边 {cur_e}），拒绝继续")
            pool.close()
            return 2
    else:
        print("\n== 4 DROP SPACE（带完整名）+ 复查真的消失 ==")
        print(f"   备份参考：platform/r12/graph/backup/kb_9-*")
        _q(s, f"DROP SPACE {a.space}")
        time.sleep(5)
        if a.space in _spaces(s):
            print("!! DROP 后 space 仍存在 -> 停止（这正是上次 87->91 的失败模式）")
            pool.close()
            return 2
        print(f"   OK {a.space} 已消失")

    print("\n== 5 建 schema ==")
    _create_schema(s, a.space)
    print("   OK tags/edges/索引已建")

    print("\n== 6 全量重抽（只写 g_kb_9）==")
    # col_values 必须是**字符串**：传 int 会被 FastAPI 422 拒绝（实测）
    payload = {"space_name": a.kb, "col_name": "file_id",
               "col_values": [str(f) for f in eff_fids], "model_info": MODEL_INFO}
    t0 = time.time()
    r = requests.post(f"{GRAPH}/generate_triple_data", json=payload, timeout=3600)
    print(f"   http={r.status_code} 用时 {time.time()-t0:.0f}s")
    print(f"   {r.text[:300]}")
    if r.status_code != 200:
        pool.close()
        return 2

    print("\n== 7 重建社区 ==")
    t0 = time.time()
    r = requests.post(f"{GRAPH}/generate_community",
                      json={"space_name": a.kb, "model_info": MODEL_INFO, "with_summary": True},
                      timeout=3600)
    print(f"   http={r.status_code} 用时 {time.time()-t0:.0f}s")
    print(f"   {r.text[:300]}")

    print("\n== 8 post 快照 + 判据 ==")
    v2, e2 = _counts(s, a.space)
    print(f"   重建后 {a.space}: 顶点 {v2} / 边 {e2}（重建前 {v}/{e}）")
    post = _snapshot(a.space, post_path)
    ok = _judge(post, a.expect_vertices)
    pool.close()

    print(f"\n[evidence] pre={pre_path}\n           post={post_path}")
    print(f"[verdict] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
