#!/usr/bin/env python
"""生成"高相似度"压力语料，用来检验 C3/C4 的结论能不能外推。

为什么需要它：现有 5 块语料每块主题完全不同（授信台账 / 政策 / 担保 / 分类），
块间相似度低到"随便检索都能命中正确那块"——在这种语料上跑出"full 与 delta 检索完全一致"，
**不能**说明真实库里也一致。真实库的特征恰恰是：同一客户在多份台账里出现、
新旧政策条款只差一句话。

所以这里造三组"故意难分"的文档：
- 两份授信台账（列相同、客户重叠、只有额度不同）；
- 新旧两版政策（99% 相同，只差"单笔超五亿须董事会"这一句）；
- 担保方式与五级分类说明（措辞接近）。

不做的事：不追求真实业务正确性，只追求"检索时容易混淆"。
"""

import argparse
import json
import os

CUSTOMERS = [
    ("华东精密制造有限公司", "汽车零部件", "AA", 3000, 1800, "正常", "2027-03-31"),
    ("江南装备科技有限公司", "装备制造", "AAA", 5000, 3200, "正常", "2027-06-30"),
    ("海川电子材料股份有限公司", "电子信息", "A", 1200, 900, "关注", "2026-12-31"),
    ("北方重工配件厂", "汽车零部件", "AA", 2000, 0, "正常", "2027-01-31"),
    ("东海新材料有限公司", "新材料", "BBB", 800, 700, "关注", "2026-09-30"),
    ("西部物流集团有限公司", "物流", "A", 1500, 1100, "正常", "2027-05-31"),
]

POLICY_COMMON = """## 授信管理办法

第一章 总则。本办法适用于集团内全部对公客户授信业务，包括额度核定、发放与贷后管理。

第二章 额度核定。授信额度依据客户信用评级、所属产业链与近三年经营情况综合核定。
信用评级 AA 及以上客户，额度上限为净资产的百分之三十；A 级客户为百分之二十。

第三章 审批权限。单笔授信不超过一亿元的，由分行授信审批部审批；
超过一亿元不超过五亿元的，由总行授信审批部审批。"""

POLICY_REVISION = """

第四章 特别条款（2026 年修订）。单笔授信超过五亿元的，须经董事会审议通过。
本条自 2026 年 7 月 1 日起执行，存量业务在到期重检时适用。"""

GUARANTEE = """## 担保方式说明

保证担保：由第三方企业提供连带责任保证，保证人信用评级不得低于被担保人。
抵押担保：以不动产或生产设备设定抵押，抵押率不超过评估价值的百分之七十。
质押担保：以存单、应收账款或股权质押，质押率不超过评估价值的百分之八十。"""

CLASSIFICATION = """## 五级分类口径

正常：借款人能够履行合同，没有足够理由怀疑本息不能按时足额偿还。
关注：尽管借款人目前有能力偿还本息，但存在一些可能对偿还产生不利影响的因素。
次级：借款人的还款能力出现明显问题，完全依靠其正常经营收入无法足额偿还本息。"""


def ledger_rows(rows):
    head = ("| 客户名称 | 所属产业链 | 信用评级 | 授信额度(万元) | 已用额度(万元) | 五级分类 | 到期日 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n")
    body = "".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} |\n" for r in rows)
    return "## 授信台账\n\n" + head + body


def build_docs():
    """返回 [(file_id, title, [chunk_text, ...])]，顺序稳定便于复现。"""
    docs = [
        ("s-101", "授信台账（一）.xlsx", [ledger_rows(CUSTOMERS[:3]),
                                          "台账说明：额度单位为万元，已用额度含表内贷款与承兑。"])
        ,
        ("s-102", "授信台账（二）.xlsx", [ledger_rows(CUSTOMERS[3:]),
                                          "台账说明：本表为季度末时点数，与月度报表可能存在时间性差异。"]),
        ("s-201", "授信管理办法 v1.docx",
         [POLICY_COMMON, "附则：本办法由总行授信管理部负责解释，自 2025 年 1 月 1 日起施行。"]),
        ("s-202", "授信管理办法 v2.docx",
         [POLICY_COMMON + POLICY_REVISION,
          "附则：本办法由总行授信管理部负责解释，自 2026 年 7 月 1 日起施行，原办法同时废止。"]),
        ("s-301", "担保方式说明.docx", [GUARANTEE]),
        ("s-401", "五级分类口径.docx", [CLASSIFICATION]),
    ]
    return docs


def to_payload(docs, index="kb_9"):
    chunks = []
    for fid, title, texts in docs:
        for i, text in enumerate(texts):
            chunks.append({"index": index, "page_content": text,
                           "metadata": {"file_id": fid, "title": title, "seq": i,
                                        "knowledge_base_name": index},
                           "pk": f"{fid}-{i}"})
    return {"status": "OK", "mode": "projection", "artifact_id": "stress" + "0" * 58,
            "chunks": chunks, "counts": {"chunks": len(chunks)}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/tmp/stress-payloads")
    ap.add_argument("--per-doc", type=int, default=1,
                    help="拆成几个载荷文件（仅用于 --payloads 传多个路径）")
    args = ap.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    payload = to_payload(build_docs())
    chunks = payload["chunks"]
    n = max(1, args.per_doc)
    size = (len(chunks) + n - 1) // n
    paths = []
    for i in range(n):
        part = dict(payload)
        part["chunks"] = chunks[i * size:(i + 1) * size]
        part["counts"] = {"chunks": len(part["chunks"])}
        path = os.path.join(args.out_dir, f"stress-{i + 1}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(part, fh, ensure_ascii=False, indent=1)
        paths.append(path)
    print(json.dumps({"payloads": paths, "chunks": len(chunks),
                      "files": len(build_docs())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
