#!/usr/bin/env python3
"""A11 原文证据（任务书 §5.2 A11）。

判据：每个关键结论有真实支持；派生内容不伪装原文 offset；同名新文档不替代旧证据。

引用链路的真实语义（读代码确认，不是猜）：
  - 答案里的 [retrive-tag id="X"] 的 X 对应引用列表里的 `order_num`（AiServiceImpl.filterDocuments
    用 orderNum 比对），**不是** ES 文档 id；所以"可回查"要分两段查：
    ① 标签能对上引用列表；② 引用里的 chunk_pk 能在 ES 回查到真实 chunk 正文。
反例：
  N1 答案里的引用标签在引用列表里找不到（前端点了跳不到）
  N2 引用带 chunk_pk 但 ES 查不到（原文不可回查）
  N3 引用的版本不是该 parent 的生效版本（V0 冒充现行）
  N4 答案数值不在被引用原文里（数值凭空/引错块）
  N5 出现 L0-/L1- 社区 id 但在 community_summary 里查不到
"""
import re

import common as C

ID = "A11"
TITLE = "原文证据：引用标签对得上、chunk 可回查、版本现行、数值在原文里"
WRITES = False

Q = "智造贷最高额度是多少？"
AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(万元|亿元)")


def run():
    checks = []
    a = C.ask(Q)
    ans = a["answer"]
    refs = a["refs"]
    tag_ids = C.RETRIEVE_ID_RE.findall(ans)
    comm_ids = C.L_CITE_RE.findall(ans)

    checks.append(C.chk("P1 答案带引用（标签或社区 id）", bool(tag_ids or comm_ids),
                        f"retrive-tag={tag_ids[:3]}；社区 id={comm_ids[:3]}"))

    order = {str(r.get("order_num")) for r in refs}
    miss = [i for i in tag_ids if i not in order]
    checks.append(C.chk("N1 反例：引用标签都能对上引用列表 order_num", not miss,
                        f"标签 {tag_ids}；引用列表 order_num={sorted(order)}；对不上的={miss}"))

    pks = []
    for r in refs:
        md = r.get("metadata") or {}
        if md.get("chunk_pk") is not None:
            pks.append(str(md.get("chunk_pk")))
    found, bodies = [], []
    for pk in pks:
        doc = C.es_get(C.KB, pk) or C.es_get(f"table_chunks_{C.KB}", pk)
        if doc:
            found.append(pk)
            bodies.append(((doc.get("_source") or {}).get("page_content") or ""))
    checks.append(C.chk("N2 反例：引用 chunk_pk 都能在 ES 回查到原文",
                        bool(pks) and len(found) == len(pks),
                        f"引用 chunk_pk={pks}；查到={found}"))

    # N3：引用版本必须是该 parent 的生效版本
    eff = {}
    d = C.es_search(C.KB, {"query": {"match_all": {}}}, size=1000)
    for h in d["hits"]["hits"]:
        md = (h.get("_source") or {}).get("metadata") or {}
        key = md.get("parent_file_name") or md.get("title")
        m = re.fullmatch(r"[Vv](\d+)", str(md.get("version") or ""))
        if key:
            eff[key] = max(eff.get(key, -1), int(m.group(1)) if m else -1)
    stale = {}
    for r in refs:
        md = r.get("metadata") or {}
        key = md.get("parent_file_name") or md.get("title")
        m = re.fullmatch(r"[Vv](\d+)", str(md.get("version") or ""))
        n = int(m.group(1)) if m else -1
        if key in eff and n < eff[key]:
            stale[key] = {"ref": md.get("version"), "effective": f"V{eff[key]}"}
    checks.append(C.chk("N3 反例：引用不指向被取代的旧版本", not stale,
                        f"旧版本引用={stale}；引用条数={len(refs)}"))

    # N4：答案中的金额必须能在被引用原文里找到
    corpus = "\n".join(bodies)
    amounts = {f"{n}{u}" for n, u in AMOUNT_RE.findall(ans)}
    unsupported = sorted(x for x in amounts if C.norm_num(x) not in C.norm_num(corpus))
    checks.append(C.chk("N4 反例：答案金额均出现在被引用原文中", not unsupported,
                        f"答案金额={sorted(amounts)}；原文缺={unsupported}；"
                        f"原文样例={corpus[:120]!r}"))

    # N5：社区 id 必须能回查
    known = {str((c["meta"] or {}).get("community_id")) for c in C.communities()}
    unknown = [i for i in comm_ids if i not in known]
    checks.append(C.chk("N5 反例：社区引用 id 都能在 community_summary 查到", not unknown,
                        f"答案社区 id={comm_ids}；查不到={unknown}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES)
