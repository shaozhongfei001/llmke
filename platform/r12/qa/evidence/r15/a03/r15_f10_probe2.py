"""R15 A03 组件级反例 v2：适用产品 + 加/减符号（COMPONENT）。

预期（先固定，再看结果）：
  客户甲 AAA 适用产品A          -> 1 条：+30（来自产品A）      ；产品B 规则 skip
  客户丙 AAA 适用产品B          -> 1 条：-30（减项符号保留）
  客户乙 AAA 无适用产品事实      -> 0 条（规则分属两个产品 → 歧义 → 不推导）
"""
import sys

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service")
from graph_summary import _join_grade_rules  # noqa: E402

c = {"community_id": "L0-c1", "level": 0}
facts = [
    "客户甲 -信用评级-> AAA",
    "客户甲 -适用产品-> 产品A",
    "客户丙 -信用评级-> AAA",
    "客户丙 -适用产品-> 产品B",
    "客户乙 -信用评级-> AAA",
    "产品A-AAA加点 -AAA级加点幅度-> 30个基点",
    "产品B-AAA减点 -AAA级减点幅度-> 30个基点",
]

derived, audit = _join_grade_rules([(c, facts)])
print("推导结果:")
for f, cid in derived:
    print("   ", f, cid)

by_ent = {}
for f, _ in derived:
    by_ent.setdefault(f.split(" ")[0], []).append(f)

print("\n逐主体:")
print("  客户甲:", by_ent.get("客户甲", []), "期望 1 条 +30")
print("  客户丙:", by_ent.get("客户丙", []), "期望 1 条 -30")
print("  客户乙:", by_ent.get("客户乙", []), "期望 0 条（歧义不推导）")

skip_reasons = sorted({a["reason"] for a in audit if a["decision"] == "skip"})
print("\nskip 原因:", skip_reasons)

ok = (
    len(by_ent.get("客户甲", [])) == 1
    and "30个基点" in by_ent["客户甲"][0]
    and len(by_ent.get("客户丙", [])) == 1
    and "-30个基点" in by_ent["客户丙"][0]
    and len(by_ent.get("客户乙", [])) == 0
)
print("\n判定:", "PASS" if ok else "FAIL")
