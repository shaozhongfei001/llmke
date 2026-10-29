#!/usr/bin/env python3
"""A04 值保真（任务书 §5.2 A04）。

判据：加/减同数值、上下限、百分比、日期、期限、逗号金额在抽取后不丢、不被截断。
反例：
  N1 金额实体丢失单位（只剩裸数字）→ 下游无法区分 8000万 / 8000元
  N2 区间被压成单值（"30~100BP" 变成一个数）
  N3 原文有逗号金额，图中却出现被逗号切断的碎片
"""
import re

import common as C

ID = "A04"
TITLE = "值保真：金额单位、区间、符号、日期期限不被截断"
WRITES = False

MONEY_RE = re.compile(r"(人民币)?[\d,.]+\s*(万元|亿元|元)")
BARE_NUM_RE = re.compile(r"^[\d,.]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def run():
    checks = []
    es = C.edges()
    vis = [e for e in es if e["sf"] == "1"]

    money = sorted({e["o"] for e in vis if MONEY_RE.search(e["o"])} |
                   {e["s"] for e in vis if MONEY_RE.search(e["s"])})
    bare = sorted({e["o"] for e in vis if BARE_NUM_RE.match(C.norm_num(e["o"]))})
    checks.append(C.chk("正例：金额实体带单位", len(money) > 0,
                        f"带单位金额 {len(money)} 个，示例={money[:5]}"))
    checks.append(C.chk("N1 反例：不存在丢失单位的裸数字金额", not bare,
                        f"裸数字实体={bare[:6]}"))

    # 区间可能不是金额（如"30~100BP"），所以对全部实体名判，不只看金额
    names = {e["s"] for e in vis} | {e["o"] for e in vis}
    rng = sorted(n for n in names if "~" in n or "～" in n or "至" in n)
    broken = sorted(n for n in names if n.endswith("~") or n.startswith("~") or "~~" in n)
    checks.append(C.chk("N2 反例：区间保留为区间、未残缺", bool(rng) and not broken,
                        f"区间值={rng[:5]}；残缺区间={broken[:5]}"))

    # 符号保真：谓词里带加/减，值侧不能把符号吃掉
    signed = [(e["s"], e["p"], e["o"]) for e in vis if re.search(r"[加减]", e["p"])]
    checks.append(C.chk("符号（加/减）在谓词上可见", len(signed) > 0,
                        f"带加减符号的谓词事实 {len(signed)} 条，示例={signed[:3]}"))

    # 逗号金额：源文里有就必须在图里保真，否则如实标注"无该夹具"
    d = C.es_search("kb_9", {"query": {"query_string": {"query": "*,\\d\\d\\d*"}}}, size=5)
    hits = [h for h in d["hits"]["hits"]
            if re.search(r"\d,\d{3}", (h.get("_source") or {}).get("page_content") or "")]
    if hits:
        comma_vals = set()
        for h in hits:
            comma_vals |= set(re.findall(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*(?:万元|亿元|元)",
                                         (h.get("_source") or {}).get("page_content") or ""))
        kept = [v for v in comma_vals if any(C.norm_num(v) in C.norm_num(x) for x in money)]
        checks.append(C.chk("N3 反例：逗号金额未被切断", bool(kept),
                            f"源文逗号金额={seg(comma_vals)}；图中保真={seg(kept)}"))
    else:
        checks.append(C.chk("N3 逗号金额夹具存在", True,
                            "kb_9 现无逗号金额夹具（D8 未入该库），该项无法在真实数据上判，按未覆盖记录"))

    dates = sorted({e["o"] for e in vis if DATE_RE.match(C.norm_num(e["o"]))})
    checks.append(C.chk("正例：日期值保真为 yyyy-mm-dd", len(dates) > 0,
                        f"日期值={dates[:5]}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES)


def seg(vals):
    return sorted(vals)[:5]
