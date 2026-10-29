#!/usr/bin/env python3
"""A02 多关系与方向（任务书 §5.2 A02）。

判据：同端点两谓词都保留、自然方向正确、遍历辅助边不进入社区事实。
反例：
  N1 同一谓词在两个方向各存一条且都可见（伪反向事实）
  N2 事实查询没有按 show_flag='1' 过滤（历史伪反向边会被当独立事实喂给下游）
  N3 事实查询遍历了 `*`（把 relationship_similar 相似边当业务事实）
"""
import re

import common as C

ID = "A02"
TITLE = "多关系与方向：同端点多谓词都保留、无双向伪反向、辅助边不计业务事实"
WRITES = False


def _exec_body():
    """取 execute_query 的真实 NGQL 函数体（生产事实查询的唯一入口）。"""
    src = C.read_src("services/rag-alg/index_data_service/index_graph_service/graph_fun_tool.py")
    m = re.search(r"def execute_query\(.*?\n(?=def )", src, re.S)
    return m.group(0) if m else ""


def run():
    checks = []
    es = C.edges()
    vis = [e for e in es if e["sf"] == "1"]
    hidden = [e for e in es if e["sf"] != "1"]

    pair_pred = {}
    for e in vis:
        pair_pred.setdefault((e["s"], e["o"]), set()).add(e["p"])
    multi = {k: v for k, v in pair_pred.items() if len(v) >= 2}
    checks.append(C.chk("P1 同端点存在 ≥2 个谓词（多关系都保留）", bool(multi),
                        f"可见边 {len(vis)} 条，多谓词端点对 {len(multi)} 组，"
                        f"示例={list(multi.items())[:2]}"))

    seen = {(e["s"], e["p"], e["o"]) for e in vis}
    rev = [(s, p, o) for (s, p, o) in seen
           if (o, p, s) in seen and (s, p, o) < (o, p, s)]
    checks.append(C.chk("N1 反例：无同谓词双向伪反向事实", not rev,
                        f"双向可见谓词对 {len(rev)} 组：{rev[:3]}"))

    body = _exec_body()
    checks.append(C.chk("N2 反例：事实查询按 show_flag='1' 过滤", "show_flag" in body,
                        f"execute_query 体长度={len(body)}；隐藏边(show_flag=0)={len(hidden)} 条"))
    checks.append(C.chk("N3 反例：事实查询只走 relationship，不遍历 * / 相似边",
                        "e:relationship" in body and "relationship_similar" not in body,
                        f"用 relationship 限定={'e:relationship' in body}；"
                        f"函数体提到 relationship_similar={'relationship_similar' in body}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES)
