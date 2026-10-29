#!/usr/bin/env python3
"""R15-W09-BRIDGE：用文档里已有的业务关系，把孤立的文件图连起来。

问题（实测 kb_9）：
  64 个有边实体里只有 1 个跨文件（"日均存款"），全图是 4 个互不相连的碎片：
    file 343（产品规则）· file 329（客户额度表）· file 333/332（指标口径与值）
  用户感知到的"每个文件一个图、没有形成关联知识"就是这个拓扑事实。

为什么清洗解决不了：
  归一与句子过滤只能把图变干净（已做，删掉 29 个句子节点），
  但 343 与 329 **没有共享实体**，清洗不会凭空产生连接。

桥接的依据（来自文档，不是编的）：
  343: 智造贷 -[适用对象]-> 制造业中小微企业
  329: 每个客户都有 -[所属产业链]-> 装备制造 / 汽车零部件 / 电子信息 / ...
  规则 BRIDGE-1：若 产品 P 的适用对象是「制造业中小微企业」，且客户 C 的所属产业链
  属于制造业范畴，则 C 是该产品的适用客户。

诚实边界：
  · 这条边是**推导**，不是抽取。关系名写成 "适用产品(推导)"，与抽取边可区分；
  · 规则命中情况逐条打印，可人工核对；
  · 只处理能明确判定为制造业的产业链，未命中就不连（宁缺勿造）。

用法：
    platform/r12/venvs/graph/bin/python platform/r12/qa/tools/r15_w09_bridge.py --dry-run
    platform/r12/venvs/graph/bin/python platform/r12/qa/tools/r15_w09_bridge.py --apply
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SPACE = os.environ.get("R15_SPACE", "g_kb_9")
OUT = os.path.join(ROOT, "platform/r12/qa/evidence/r15/w09-bridge")

# 明确属于"制造业"的产业链关键词。不在这里的一律不连（宁可少连）。
MFG_KEYS = ("制造", "装备", "汽车", "零部件", "机械", "电子", "材料", "化工", "纺织", "冶金")

from nebula3.Config import Config  # noqa: E402
from nebula3.gclient.net import ConnectionPool  # noqa: E402


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


def _rows(s, ngql):
    r = s.execute(ngql)
    if not r.is_succeeded():
        raise SystemExit(f"查询失败: {r.error_msg()}  [{ngql[:80]}]")
    out = []
    for i in range(r.row_size()):
        out.append([r.row_values(i)[j].as_string() for j in range(r.col_size())])
    return out


def _q(v):
    return '"' + str(v).replace('"', '\\"') + '"'


def components(s):
    """连通分量数（只看有边的实体）。孤岛越多，说明图越碎。"""
    edges = _rows(s, "MATCH (v:entity)-[e:relationship]->(v2:entity) RETURN id(v),id(v2)")
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in edges:
        union(a, b)
    comps = {}
    for x in list(parent):
        comps.setdefault(find(x), set()).add(x)
    return len(comps), sorted((len(v) for v in comps.values()), reverse=True), len(edges)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    pool, s = _sess()
    try:
        n_before, sizes_before, e_before = components(s)
        print(f"桥接前：有边实体连通分量 {n_before} 个（{sizes_before}），边 {e_before}")

        # 1) 产品 -> 适用对象
        obj = _rows(s, "MATCH (v:entity)-[e:relationship]->(v2:entity) "
                       "WHERE properties(e).name CONTAINS \"适用对象\" "
                       "RETURN id(v), id(v2), properties(e).name")
        print("\n产品适用对象事实：")
        products = {}
        for p, o, rel in obj:
            print(f"   {p} -[{rel}]-> {o}")
            if "制造业" in o or "中小微" in o:
                products.setdefault(p, set()).add(o)
        if not products:
            print("  [STOP] 图中没有『适用对象=制造业中小微企业』的事实，无法桥接")
            return 0

        # 2) 客户 -> 所属产业链  与  客户 -> 授信额度（认定"客户"身份）
        chains = _rows(s, "MATCH (v:entity)-[e:relationship]->(v2:entity) "
                          "WHERE properties(e).name CONTAINS \"产业链\" "
                          "RETURN id(v), id(v2), properties(e).file_id")
        clients = {c: (ch, fid) for c, ch, fid in chains}
        print(f"\n候选客户（有『所属产业链』事实）：{len(clients)} 个")
        for c, (ch, fid) in clients.items():
            print(f"   {c:<26} 产业链={ch:<10} 来源file={fid}")

        # 3) 规则 BRIDGE-1
        plan, skipped = [], []
        for c, (ch, fid) in clients.items():
            if not any(k in ch for k in MFG_KEYS):
                skipped.append({"client": c, "chain": ch, "why": "产业链不在制造业关键词内"})
                continue
            for p in products:
                plan.append({"client": c, "product": p, "chain": ch,
                             "file_id": fid, "rule": "BRIDGE-1",
                             "why": f"产品适用对象含制造业中小微企业，客户产业链={ch}"})

        print(f"\nBRIDGE-1 命中 {len(plan)} 条，未命中 {len(skipped)} 条：")
        for x in plan:
            print(f"   + {x['client']} -[适用产品(推导)]-> {x['product']}   ({x['why']})")
        for x in skipped:
            print(f"   - {x['client']} 跳过：{x['why']}（{x['chain']}）")

        if not args.apply:
            print("\n[dry-run] 未改动。加 --apply 执行。")
            json.dump({"before": {"components": n_before, "sizes": sizes_before, "edges": e_before},
                       "plan": plan, "skipped": skipped},
                      open(os.path.join(OUT, "plan.json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            return 0

        # 4) 写边：关系名带"(推导)"前缀，与抽取边可区分；rank 用稳定哈希避免重复
        import hashlib
        written = 0
        for x in plan:
            rank = int(hashlib.sha1(
                f"{x['client']}|适用产品(推导)|{x['product']}".encode()).hexdigest()[:15], 16)
            ngql = ("INSERT EDGE relationship(name,file_id,show_flag,page_num) VALUES "
                    f"{_q(x['client'])}->{_q(x['product'])}@{rank}:"
                    f"({_q('适用产品(推导)')},{_q(x['file_id'])},\"1\",\"0\")")
            r = s.execute(ngql)
            if r.is_succeeded():
                written += 1
            else:
                print(f"   [WARN] 写边失败 {x['client']}->{x['product']}: {r.error_msg()[:80]}")
        print(f"\n已写入推导边 {written}/{len(plan)}")

        n_after, sizes_after, e_after = components(s)
        print(f"桥接后：有边实体连通分量 {n_after} 个（{sizes_after}），边 {e_after}")
        print(f"  分量数 {n_before} -> {n_after}（越少越连通）")

        rep = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "space": SPACE,
               "rule": "BRIDGE-1",
               "before": {"components": n_before, "sizes": sizes_before, "edges": e_before},
               "after": {"components": n_after, "sizes": sizes_after, "edges": e_after},
               "written": written, "plan": plan, "skipped": skipped,
               "note": "推导边关系名为『适用产品(推导)』，非抽取结果；规则依据见 343 的『适用对象』事实"}
        json.dump(rep, open(os.path.join(OUT, "report.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"[evidence] {OUT}")
        return 0
    finally:
        s.release()
        pool.close()


if __name__ == "__main__":
    sys.exit(main())
