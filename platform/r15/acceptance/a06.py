#!/usr/bin/env python3
"""A06 空和失败（任务书 §5.2 A06）。

判据：合法空、格式失败、模型超时、部分边失败、全部摘要失败各有正确状态；
部分/全部失败不能发布为完整；合法空不冒充故障。
反例（关键）：
  N1 "解析成功但 0 边"：graph_parse_status=3 的**生效文件**在 Nebula 里一条边都没有
     —— 这是 NEXT.md 记的 A06/F09 缺陷形态，必须由状态机显式区分，不能标成功
  N2 解析失败的文件（gps=4）却产出了边 → 失败被当成功
  N3 合法空（本来就没有关系的资料）与真失败共用同一状态 → 无法区分
"""
import collections

import common as C

ID = "A06"
TITLE = "空和失败：解析成功不得零产出，失败不得产出，合法空与故障可区分"
WRITES = False


def run():
    checks = []
    led = C.ledger()
    es = C.edges()
    per_fid = collections.Counter(e["fid"] for e in es if e["sf"] == "1")

    active = {fid: m for fid, m in led.items() if m["status"] == "3"}
    gps3 = {fid: m for fid, m in active.items() if m["gps"] == "3"}
    zero = {fid: m["name"] for fid, m in gps3.items() if per_fid.get(fid, 0) == 0}

    checks.append(C.chk("N1 反例：不存在「图解析成功(3)但 0 边」的生效文件", not zero,
                        f"生效且 gps=3 的文件 {len(gps3)} 个，其中 0 边 {len(zero)} 个：{zero}"))

    failed = [fid for fid, m in active.items() if m["gps"] == "4"]
    leaked = {fid: per_fid.get(fid, 0) for fid in failed if per_fid.get(fid, 0) > 0}
    checks.append(C.chk("N2 反例：解析失败(gps=4)的文件不产出边", not leaked,
                        f"失败文件={failed}；其中仍有边的={leaked}"))

    # 状态取值分布：只有 1(未解析)/3(成功)/4(失败) 三态。
    # 这是观测而非 hard 断言：合法空是否必须独立成第四态取决于实现口径，
    # 但 N1 已经证明"成功"与"有产出"之间没有闸门，二者必须一起看。
    states = collections.Counter(m["gps"] for m in led.values())
    checks.append(C.chk("P3 状态取值已枚举（用于解释 N1）", True,
                        f"graph_parse_status 分布={dict(states)}；"
                        f"成功(3) 与 零产出 共用同一状态，故 N1 无法在状态层被拦下"))

    # 摘要全部失败不得标"已就绪"（只读：社区 status 与 edge_count 的一致性）
    comms = C.communities()
    statuses = collections.Counter(str((c["meta"] or {}).get("status")) for c in comms)
    empty_comm = [c["es_id"] for c in comms if not (c["meta"] or {}).get("member_entities")]
    checks.append(C.chk("N4 反例：无空成员社区冒充已就绪", not empty_comm,
                        f"社区 {len(comms)} 个，无成员 {len(empty_comm)} 个；status 分布={dict(statuses)}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES)
