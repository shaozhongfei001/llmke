#!/usr/bin/env python3
"""A01 类型与归一（任务书 §5.2 A01）。

判据：M1 一致（6 大类 27 码）、合法评级保留、真实别名合并、不同主体不混、审计与回滚成立。
反例（必须成立，否则判 FAIL）：
  N1 图里出现白名单外的实体类型（= 规则/LLM 产出的类型没被受控）
  N2 合法评级被当成停用词过滤掉（F07 的典型形态）
  N3 类型体系硬编码在源码里，没有受控配置可追溯 / 可回滚
"""
import glob
import os
import re

import common as C

ID = "A01"
TITLE = "类型/归一：运行时类型一致 M1、合法评级保留、不同类型不混"
WRITES = False

LEGAL_RATINGS = {"AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C",
                 "正常", "关注", "次级", "可疑", "损失"}


def _block(src, name):
    m = re.search(name + r"\s*=\s*[\[\{](.*?)[\]\}]", src, re.S)
    return m.group(1) if m else ""


def run():
    checks = []
    src = C.read_src("services/rag-alg/index_data_service/index_graph_service/graph_types.py")
    # R15/A01 判据修正：a01 原来用**源码文本**解析 ALLOWED_TYPES，实现改为从契约加载后
    # `ALLOWED_TYPES, _TYPES_SOURCE, _TYPES_REASON = _load_contract_types()`，
    # 文本解析拿不到真实结果（会得到空列表/误判）。改为**运行时 import** 取真实值，
    # 这才是"服务实际用哪套类型表"的判据。
    allowed, types_source, types_reason = [], "", "import_failed"
    try:
        import sys
        import os as _os
        sys.path.insert(0, _os.path.join(C.ROOT, "services/rag-alg/index_data_service/index_graph_service"))
        import graph_types as G  # noqa: E402
        allowed = list(getattr(G, "ALLOWED_TYPES", []) or [])
        types_source = getattr(G, "_TYPES_SOURCE", "") or ""
        types_reason = getattr(G, "_TYPES_REASON", "") or ""
    except Exception as e:  # noqa: BLE001
        types_reason = f"import_failed:{e}"
    checks.append(C.chk("运行时类型白名单可读取", len(allowed) > 0,
                        f"来源={types_reason} 共{len(allowed)}项: {allowed}"))

    # N1：白名单外类型（unclassified 是显式兜底类型，不算越界）
    rows = C.nebula("MATCH (v:entity) RETURN v.entity.type, count(v)")[0]
    dist = {r[0]: int(r[1]) for r in rows}
    outside = sorted(t for t in dist if t not in allowed and t != "unclassified")
    checks.append(C.chk("N1 反例：无白名单外实体类型", not outside,
                        f"越界类型={outside}；实际分布={dist}"))

    # N2：合法评级不得被停用词过滤（正常/关注/次级… 是合法业务值）
    # R15/A01 判据修正：原来从**源码文本**解析 STOPWORDS，注释里出现同样字面量
    # （例如说明"原先把『正常』当停用词"）会被正则当成真值，产生假阴/假阳。
    # 改为运行时读 graph_types.STOPWORDS；同时只在"原文里确实出现过该评级"时
    # 才要求它进图（语料没写"正常"，图中没有它不算缺陷）。
    stop = set(getattr(G, "STOPWORDS", set()) or set())
    dropped = sorted(LEGAL_RATINGS & stop)
    rating_ents = C.nebula("MATCH (v:entity) WHERE v.entity.type=='评级' "
                           "RETURN v.entity.name")[0]
    checks.append(C.chk("N2 反例：合法评级未被当停用词丢弃", not dropped,
                        f"被过滤的合法评级={dropped}；图中评级实体={[r[0] for r in rating_ents]}"))

    # N3：M1 受控配置存在且被生产代码读取（不是源码里写死一张 16 类表）
    onto = [p for p in glob.glob(os.path.join(C.ROOT, "contracts/ontology/**/*"), recursive=True)
            if os.path.isfile(p) and not p.endswith(".md")]
    # 同上：用运行时来源判定，而不是正则匹配源码写法
    loads_cfg = (types_reason == "contract")
    checks.append(C.chk("N3 反例：类型体系来自受控配置而非硬编码",
                        bool(onto) and loads_cfg,
                        f"contracts/ontology 受控文件={len(onto)}；运行时从配置加载={loads_cfg}"
                        f"（当前 ALLOWED_TYPES 为源码字面量，M1 6大类27码未落受控配置）"))

    # 归一质量观测（不判 hard，仅留证）：unclassified 占比
    total = sum(dist.values()) or 1
    unc = dist.get("unclassified", 0)
    checks.append(C.chk("归一覆盖率可计算", True,
                        f"实体 {total} 个，unclassified {unc} 个（{unc / total:.0%}）"))

    return C.verdict(ID, TITLE, checks,
                     writes=WRITES)
