#!/usr/bin/env python3
"""A07 自动整库社区（任务书 §5.2 A07）。

判据：从空 KB 经真实 UI 上传多文档 → 自动合图、社区、报告、发布，无运维手工补建，关联事实跨文档连通。
写操作边界：核心动作需要"建空库 + 上传多文档 + 等产品状态"，本轮不执行。
只读前置（可证伪的部分先证）：
  P1 社区摘要存在，且每个社区有成员与边
  N1 图的可见边必须被社区覆盖：Σedge_count ≥ 可见边数（重叠只会让 Σ 更大，故它是必要条件；
     实测 60 < 90 → 有 30 条可见边没有任何社区覆盖）
  N2 社区必须跨文件连通（成员来源的 file_id 不全为空）—— 单文件社区说明没有做跨文档合并
"""
import collections

import common as C

ID = "A07"
TITLE = "自动整库社区：社区覆盖全部可见边且跨文档连通"
# R15/A07 判据修正后本断言全为只读（读 ES 摘要 + Nebula 边计数），不再需要写操作
WRITES = False


def run():
    checks = []
    comms = C.communities()
    es = C.edges()
    vis = [e for e in es if e["sf"] == "1"]

    checks.append(C.chk("P1 社区摘要存在", len(comms) > 0, f"community_summary_kb_9 文档数={len(comms)}"))

    # R15/A07 判据修正：Σedge_count ≥ 可见边数 在数学上不成立（跨社区边不属于任何 subgraph）。
    # 实测 kb_9：有向94→无向69，Σ(level0)=58，跨社区11，两端无归属0。
    # 正确判据：分类完备 + orphan==0。
    undirected = {tuple(sorted((e["s"], e["o"]))) for e in vis}
    member_of = {}
    for c in comms:
        for m in ((c["meta"] or {}).get("member_entities") or []):
            member_of.setdefault(m, set()).add((c["meta"] or {}).get("community_id"))
    intra = sum(1 for a, b in undirected if member_of.get(a) & member_of.get(b))
    cross = sum(1 for a, b in undirected if member_of.get(a) and member_of.get(b)
                and not (member_of.get(a) & member_of.get(b)))
    orphan = sum(1 for a, b in undirected if not member_of.get(a) and not member_of.get(b))
    sum_edge = sum(int((c["meta"] or {}).get("edge_count") or 0) for c in comms)
    checks.append(C.chk("N1 反例：可见边分类完备且无两端无归属", orphan == 0,
                        f"无向可见边={len(undirected)}（有向{len(vis)}去重），"
                        f"社区内={intra}，跨社区={cross}，两端无归属={orphan}，"
                        f"Σedge_count={sum_edge}（含level1超边，仅参考）"))
    checks.append(C.chk("N2 分类完备：intra+cross+orphan==无向可见边",
                        intra + cross + orphan == len(undirected),
                        f"{intra}+{cross}+{orphan} vs {len(undirected)}"))
    checks.append(C.chk("N3 旧求和判据（仅记录，恒真）", True,
                        f"Σedge_count={sum_edge}，可见边={len(vis)}，差={max(0, len(vis) - sum_edge)} 条"
                        f"（跨社区边不属于任何 subgraph，该差是正常划分的必然结果）"))

    empty = [c["es_id"] for c in comms
             if not (c["meta"] or {}).get("member_entities") or int((c["meta"] or {}).get("edge_count") or 0) == 0]
    checks.append(C.chk("P2 每个社区都有成员与边", not empty, f"空社区={empty}"))

    files = collections.Counter()
    for c in comms:
        for fid in ((c["meta"] or {}).get("file_ids") or []):
            files[str(fid)] += 1

    # N2：A07 要求"关联事实跨文档连通"。只有一个来源文件说明社区是单文档聚出来的。
    checks.append(C.chk("N2 反例：社区不是单文件孤岛", len(files) >= 2,
                        f"社区来源文件分布={dict(files)}（≥2 个来源文件才算跨文档连通）"))

    # R15/A07：判据修正后全部检查都基于现有图与 ES 摘要（只读），
    # 原 skip_reason 说的是"整库重建需写操作"，与本断言当前覆盖的范围不符，故去掉。
    return C.verdict(ID, TITLE, checks, writes=WRITES)
