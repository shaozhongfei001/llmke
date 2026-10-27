#!/usr/bin/env python3
"""生成图增量夹具的三篇 docx（本地文件，不入库）。

设计稿：docs/r12/r14/B-GRAPH-INCREMENT-FIXTURE.md §7
硬约束：
  · 01 不得出现「装备制造事业部」
  · 02 不得出现「恒星项目」
  · 02 必须含「启明计划归口装备制造事业部管理」——这是唯一答案来源
命名：R14FIX-graph-*（与 R12FIX-* 业务夹具、R14-BASELINE-* F 的验收库区分开）

跑法（parse venv 有 python-docx）：
  platform/r12/venvs/parse/bin/python platform/r12/graph/make_fixture_docs.py
输出：platform/r12/graph/fixtures/
"""
import os

from docx import Document

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

DOCS = {
    "R14FIX-graph-01-project.docx": [
        "恒星项目一期验收纪要",
        "",
        "恒星项目一期于 2026 年 9 月完成验收，验收结论为“通过”。",
        "项目由启明计划统筹推进，参与单位包括装备制造板块的三家配套企业。",
        "本纪要仅记录验收结论与统筹关系，不含人员与外协明细。",
    ],
    "R14FIX-graph-02-dept.docx": [
        "装备制造事业部年度工作要点",
        "",
        "一、归口管理",
        "启明计划归口装备制造事业部管理，年度预算由该事业部统一编报。",
        "",
        "二、重点任务",
        "围绕关键工序能力提升，推进设备更新与工艺优化，按季度考核进度。",
    ],
    "R14FIX-graph-03-noise.docx": [
        "财务口径说明",
        "",
        "本年度报表按季度编制，收入确认以交付验收单为凭据。",
        "成本按项目归集，跨期费用按权责发生制分摊。",
    ],
}

# 约束自检（生成前后都跑）
FORBIDDEN = {
    "R14FIX-graph-01-project.docx": "装备制造事业部",
    "R14FIX-graph-02-dept.docx": "恒星项目",
}
REQUIRED = {
    "R14FIX-graph-02-dept.docx": "启明计划归口装备制造事业部管理",
}


def main():
    os.makedirs(OUT, exist_ok=True)
    ok = True
    for name, lines in DOCS.items():
        text = "\n".join(lines)
        bad = FORBIDDEN.get(name)
        if bad and bad in text:
            print(f"  [FAIL] {name} 含禁用词「{bad}」——夹具会自欺，必须改写")
            ok = False
        need = REQUIRED.get(name)
        if need and need not in text:
            print(f"  [FAIL] {name} 缺少必需事实「{need}」")
            ok = False
        path = os.path.join(OUT, name)
        doc = Document()
        for line in lines:
            doc.add_paragraph(line)
        doc.save(path)
        print(f"  [OK] {path}  ({len(text)} 字)")
    print("\n[结论]", "PASS：三篇夹具已生成且约束自检通过" if ok else "FAIL：约束不自洽，未通过")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
