#!/usr/bin/env python3
"""A09 代次和版本（任务书 §5.2 A09）。

判据：一请求固定同代；默认现行、显式历史正确；没有新旧图/报告/引用混合。
反例：
  N1 图上仍挂着失效/被取代文件（status!=3）的边 → 旧代事实与新代并存
  N2 同一 (主体, 谓词=最高额度) 同时存在 8000万 与 1000万（新旧值/总额-分项并存）
  N3 边缺少 generation 属性（历史边未回填）→ 无法按代次过滤
  N4 查询/统计侧没有 generation 过滤 → 代次维度只在写入侧存在
"""
import collections
import re

import common as C

ID = "A09"
TITLE = "代次和版本：无旧代混存、边带代次、查询按代次过滤"
WRITES = False


def run():
    checks = []
    es = C.edges()
    vis = [e for e in es if e["sf"] == "1"]
    active = C.active_fids()

    stale = collections.Counter(e["fid"] for e in vis if e["fid"] not in active)
    checks.append(C.chk("N1 反例：可见边全部来自生效文件(status=3)", not stale,
                        f"来自失效文件的可见边={dict(stale)}（生效文件集合大小={len(active)}）"))

    top = [(e["s"], e["o"]) for e in vis if e["p"] == "最高额度"]
    zzd = [o for s, o in top if s == "智造贷"]
    vals = sorted({C.norm_num(v) for v in zzd})
    checks.append(C.chk("N2 反例：同一主体同一谓词不出现两个互斥额度", len(vals) <= 1,
                        f"(主体=智造贷, 谓词=最高额度) 取值={vals}；原始事实={top}"))

    both = any(C.has_amount(v, "5000万") for v in zzd) and any(C.has_amount(v, "8000万") for v in zzd)
    checks.append(C.chk("N2b 反例：5000万与8000万不同时作为最高额度", not both,
                        f"最高额度取值={vals}"))

    nog = [e for e in vis if not (e["gen"] or "").strip()]
    checks.append(C.chk("N3 反例：无缺代次的边", not nog,
                        f"缺 generation 的可见边={len(nog)}；代次分布="
                        f"{dict(collections.Counter(e['gen'] for e in vis))}"))

    svc = C.read_src("services/rag-alg/index_data_service/index_graph_service/graph_service.py")
    sum_src = C.read_src("services/rag-alg/index_data_service/index_graph_service/graph_summary.py")
    q_filter = len(re.findall(r"generation", svc))
    s_filter = len(re.findall(r"generation", sum_src))
    checks.append(C.chk("N4 反例：查询/社区侧按 generation 过滤", q_filter > 0 and s_filter > 0,
                        f"graph_service.py generation 出现 {q_filter} 次；"
                        f"graph_summary.py 出现 {s_filter} 次（0 = 只在写入侧有代次）"))

    return C.verdict(ID, TITLE, checks, writes=WRITES)
