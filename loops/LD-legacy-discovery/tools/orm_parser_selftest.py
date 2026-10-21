#!/usr/bin/env python3
"""B4：ORM 解析器的可核对样例集（含负例与已知盲区）。

目的：让「覆盖率 38%」这个数字**可被人工复核**——每个样例都写明：
它代表哪种写法、期望解析出什么、当前解析器实际解析出什么、盲区在哪。

不是扩展解析器，而是先量出边界。
"""
from __future__ import annotations
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from db_mapper_columns import columns_from_mapper  # noqa: E402

FIXTURES = {
    "F1_id_and_result": {
        "xml": """<mapper namespace="x"><resultMap id="Base" type="A">
  <id column="id" property="id"/>
  <result column="create_by" property="createBy"/>
</resultMap></mapper>""",
        "expect_columns": {"id", "create_by"},
        "note": "基线写法：column 在前",
    },
    "F2_property_first": {
        "xml": """<mapper namespace="x"><resultMap id="Base" type="A">
  <result property="kbId" column="kb_id"/>
  <id property="id" column="id"/>
</resultMap></mapper>""",
        "expect_columns": {"id", "kb_id"},
        "note": "属性顺序反转（真实代码里存在）",
    },
    "F3_association": {
        "xml": """<mapper namespace="x"><resultMap id="Base" type="A">
  <id column="id" property="id"/>
  <association property="kb" javaType="K">
    <result column="kb_name" property="name"/>
  </association>
</resultMap></mapper>""",
        "expect_columns": {"id", "kb_name"},
        "note": "**RISK**：association 内嵌列被计入**父表**（kb_name 会被误判为父表列）",
    },
    "F4_collection": {
        "xml": """<mapper namespace="x"><resultMap id="Base" type="A">
  <id column="id" property="id"/>
  <collection property="files" ofType="F">
    <result column="file_id" property="id"/>
  </collection>
</resultMap></mapper>""",
        "expect_columns": {"file_id"},
        "note": "**RISK**：collection 内层 property=`id` 覆盖外层 `<id property=\"id\">`，外层主键列丢失（实测）",
    },
    "F5_alias_in_sql": {
        "xml": """<mapper namespace="x">
  <select id="q" resultType="map">SELECT a.create_by AS creator FROM t a</select>
</mapper>""",
        "expect_columns": set(),
        "note": "**盲区**：SQL 别名与 SELECT 列表不在 resultMap，解析不到（但会进 B1 的 SQL 引用索引）",
    },
    "F6_duplicate_property": {
        "xml": """<mapper namespace="x"><resultMap id="Base" type="A">
  <result column="create_by" property="createBy"/>
  <result column="creator" property="createBy"/>
</resultMap></mapper>""",
        "expect_columns": {"creator"},
        "note": "**RISK**：同名 property 后者覆盖前者，先出现的列丢失（真实代码里 create_by 常被这样覆盖）",
    },
}


def main() -> int:
    import tempfile
    ok = 0
    print(f"fixtures={len(FIXTURES)}")
    with tempfile.TemporaryDirectory() as td:
        for name, f in FIXTURES.items():
            p = Path(td) / f"{name}.xml"
            p.write_text(f["xml"], encoding="utf-8")
            # 注意：result_map 是 {property: column}，判定覆盖率要用 column（值），不是 key
            got_columns = set(columns_from_mapper(p)["result_map"].values())
            passed = got_columns == f["expect_columns"]
            ok += passed
            print(f"  {'PASS' if passed else 'FAIL'} {name}: "
                  f"expect_cols={sorted(f['expect_columns'])} got={sorted(got_columns)} | {f['note']}")
    print(f"passed={ok}/{len(FIXTURES)}")
    return 0 if ok == len(FIXTURES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
