#!/usr/bin/env python3
"""R13 图谱空间初始化：建 space + tag/edge + 索引，并验证可写入读回。

Schema 依据（源码，不是文档推测）：
  services/rag-alg/index_data_service/index_graph_service/graph_service.py
    - create_space     : CREATE SPACE ... vid_type=FIXED_STRING(500)
    - create_attribute : TAG entity(name,title,file_id,type)
                         EDGE relationship(name,file_id,show_flag,page_num)
                         EDGE relationship_similar(name,show_flag)
                         每个 string 属性建 (200) 前缀索引
  Java 侧：GraphFieldEnums.GRAPH_SPACENAME_PREFIX = "g_"，所有 /graph/** 端点会给 spaceName 加前缀，
  因此同时建 g_rag_graph 供 Java 端点读回验证。

用法：platform/r12/venvs/graph/bin/python platform/r12/graph/init_space.py
"""
import sys
import time

from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool

HOST, PORT = "127.0.0.1", 19669
SPACES = ["rag_graph", "g_rag_graph"]

TAGS = {
    "entity": "name string, title string, file_id string, type string",
}
EDGES = {
    "relationship": "name string, file_id string, show_flag string, page_num string",
    "relationship_similar": "name string, show_flag string",
}


def run(sess, stmt, quiet=False):
    r = sess.execute(stmt)
    if not r.is_succeeded():
        if not quiet:
            print(f"  [!] {stmt[:70]} -> {r.error_msg()}")
        return False, r.error_msg()
    return True, r


def main():
    cfg = Config()
    cfg.max_connection_pool_size = 10
    pool = ConnectionPool()
    if not pool.init([(HOST, PORT)], cfg):
        print(f"connect {HOST}:{PORT} failed")
        return 1
    sess = pool.get_session("root", "nebula")

    for sp in SPACES:
        ok, _ = run(sess, f"CREATE SPACE IF NOT EXISTS {sp} "
                          f"(partition_num=10, replica_factor=1, vid_type=FIXED_STRING(500))", quiet=True)
        print(f"space {sp}: {'created' if ok else 'exists'}")

    # space 生效需要心跳，硬等一轮
    time.sleep(12)

    for sp in SPACES:
        ok, err = run(sess, f"USE {sp}")
        print(f"use {sp}: {ok} {err if not ok else ''}")
        if not ok:
            continue
        for tag, props in TAGS.items():
            run(sess, f"CREATE TAG IF NOT EXISTS {tag}({props})")
            for p in [x.split()[0] for x in props.split(",")]:
                run(sess, f"CREATE TAG INDEX IF NOT EXISTS {tag}_{p}_index ON {tag}({p}(200))")
        for edge, props in EDGES.items():
            run(sess, f"CREATE EDGE IF NOT EXISTS {edge}({props})")
            for p in [x.split()[0] for x in props.split(",")]:
                run(sess, f"CREATE EDGE INDEX IF NOT EXISTS {edge}_{p}_index ON {edge}({p}(200))")
        # 索引 rebuild
        for tag, props in TAGS.items():
            for p in [x.split()[0] for x in props.split(",")]:
                run(sess, f"REBUILD TAG INDEX {tag}_{p}_index")
        for edge, props in EDGES.items():
            for p in [x.split()[0] for x in props.split(",")]:
                run(sess, f"REBUILD EDGE INDEX {edge}_{p}_index")

    # 验证：写一条真实数据再读回（数据来自真实解析样本 cn-digital.pdf / file_id=3000 的口径，
    # 这里只验证引擎可写可读，不代表业务抽取结果）
    ok, err = run(sess, "USE g_rag_graph")
    run(sess, 'INSERT VERTEX entity(name,title,file_id,type) VALUES '
              '"R13_SCHEMA_PROBE":("R13_SCHEMA_PROBE","schema-probe","0","probe")')
    ok, r = run(sess, 'MATCH (v:entity) WHERE id(v)=="R13_SCHEMA_PROBE" RETURN id(v) AS vid, v.entity.type AS t')
    if ok and r.row_size() > 0:
        print("write/read probe: OK ->", r.row_values(0))
    else:
        print("write/read probe: FAILED ->", err if not ok else "no row")
    run(sess, 'DELETE VERTEX "R13_SCHEMA_PROBE" WITH EDGE')

    for sp in SPACES:
        run(sess, f"USE {sp}")
        ok, r = run(sess, "SHOW TAGS")
        tags = [r.row_values(i)[0].as_string() for i in range(r.row_size())] if ok else []
        ok2, r2 = run(sess, "SHOW EDGES")
        edges = [r2.row_values(i)[0].as_string() for i in range(r2.row_size())] if ok2 else []
        print(f"{sp}: tags={tags} edges={edges}")
    sess.release()
    pool.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
