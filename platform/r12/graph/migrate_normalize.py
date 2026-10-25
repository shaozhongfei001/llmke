#!/usr/bin/env python3
"""R13 图谱存量数据归一迁移：清理噪声实体、合并长短名（canonical 重指向）。

规则与 graph_types.py 完全一致（同一份代码，不是另写一套）：
  - is_valid_entity() 判定为无效的（纯数字/结构词/过短）→ 删除顶点及其边
  - canonical_of() 判定应合并的 → 把边重指向到 canonical，再删除别名顶点
用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/migrate_normalize.py [space] [--dry-run]
"""
import os
import sys

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service")

from nebula3.Config import Config  # noqa: E402
from nebula3.gclient.net import ConnectionPool  # noqa: E402

import graph_types as gt  # noqa: E402


def main():
    space = sys.argv[1] if len(sys.argv) > 1 else "g_kb_9"
    dry = "--dry-run" in sys.argv
    cfg = Config()
    pool = ConnectionPool()
    pool.init([("127.0.0.1", 19669)], cfg)
    s = pool.get_session("root", "nebula")
    print(f"use {space}:", s.execute(f"USE {space}").is_succeeded())

    r = s.execute("MATCH (v:entity) RETURN id(v) AS n")
    names = [r.row_values(i)[0].as_string() for i in range(r.row_size())]

    invalid, name_map = [], {}
    for n in names:
        ok, reason = gt.is_valid_entity(n)
        if not ok:
            invalid.append((n, reason))
            continue
        canon = gt.canonical_of(n, names)
        if canon != n:
            name_map[n] = canon

    print(f"总实体 {len(names)}；待删 {len(invalid)}；待合并 {len(name_map)}")
    for n, why in invalid:
        print("  delete", n, why)
    for a, c in name_map.items():
        print("  merge", a, "->", c)
    if dry:
        print("dry-run，不写库")
        return 0

    for n, _why in invalid:
        s.execute(f'DELETE VERTEX "{n}" WITH EDGE')

    # 合并：先把别名顶点的边重指向 canonical，再删别名
    for alias, canon in name_map.items():
        r = s.execute(f'MATCH (v:entity)-[e:relationship]-(v2:entity) WHERE id(v)=="{alias}" '
                      f'RETURN id(v2) AS other, properties(e) AS p, startNode(e)==id(v) AS is_out')
        rows = [(r.row_values(i)[0].as_string(),
                 {k: (v.as_string() if v.is_string() else str(v)) for k, v in r.row_values(i)[1].as_map().items()},
                 r.row_values(i)[2].as_bool())
                for i in range(r.row_size())]
        for other, props, is_out in rows:
            if other == canon:
                continue
            name_v = props.get("name", "")
            fid = props.get("file_id", "")
            flag = props.get("show_flag", "1")
            pn = props.get("page_num", "")
            src, dst = (canon, other) if is_out else (other, canon)
            s.execute(f'INSERT EDGE relationship(name,file_id,show_flag,page_num) VALUES '
                      f'"{src}"->"{dst}":("{name_v}","{fid}","{flag}","{pn}")')
        s.execute(f'DELETE VERTEX "{alias}" WITH EDGE')

    # 存量节点重新推断类型（合并/删除之外的第二种清洗）
    r = s.execute("MATCH (v:entity) RETURN id(v) AS n, v.entity.type AS t")
    retyped = 0
    for i in range(r.row_size()):
        n = r.row_values(i)[0].as_string()
        old_t = r.row_values(i)[1].as_string() if r.row_values(i)[1].is_string() else ""
        new_t, _src = gt.infer_type(n, old_t)
        if new_t != old_t:
            s.execute(f'UPDATE VERTEX ON entity "{n}" SET type = "{new_t}"')
            retyped += 1
    print(f"类型重判：{retyped} 个节点")

    r = s.execute("MATCH (v:entity) RETURN count(v) AS c")
    vc = r.row_values(0)[0].as_int() if r.is_succeeded() and r.row_size() else -1
    r = s.execute("MATCH ()-[e:relationship]->() RETURN count(e) AS c")
    ec = r.row_values(0)[0].as_int() if r.is_succeeded() and r.row_size() else -1
    print(f"迁移后：entities={vc} edges={ec}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
