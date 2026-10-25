#!/usr/bin/env python3
"""R13 图谱迁移回滚：按 migrate_normalize.py 产生的审计 JSONL 逆操作恢复。

支持的动作（与审计写入一一对应）：
  delete_vertex        -> 重建顶点与其边
  delete_alias_vertex  -> 重建别名顶点（canonical 关系不自动还原，会打印提示）
  add_edge_for_merge   -> 删除合并时新增的边
  retype               -> 恢复旧类型
用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/rollback_audit.py <audit.jsonl> [--dry-run]
"""
import json
import sys

from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool

AUDIT_DIR = "/home/szf/data/dev/llmke-r12/platform/r12/graph/audit"


def q(s):
    def esc(v):
        return str(v).replace('"', '\\"')

    return esc(s)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("用法: rollback_audit.py <audit.jsonl> [--dry-run]")
        return 2
    dry = "--dry-run" in sys.argv
    recs = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    if not recs:
        print("审计为空")
        return 1
    space = recs[0].get("space")
    print(f"批次 {recs[0].get('batch_id')} / space={space} / 记录 {len(recs)} 条")

    cfg = Config()
    pool = ConnectionPool()
    pool.init([("127.0.0.1", 19669)], cfg)
    s = pool.get_session("root", "nebula")
    print("use:", s.execute(f"USE {space}").is_succeeded())

    ok = fail = 0
    # 逆序执行：先撤类型与合并边，再还原顶点
    for rec in reversed(recs):
        action = rec.get("action")
        try:
            if action == "retype":
                stmt = f'UPDATE VERTEX ON entity "{rec["vid"]}" SET type = "{rec["old"]}"'
            elif action == "add_edge_for_merge":
                p = rec["props"]
                stmt = (f'DELETE EDGE relationship "{rec["src"]}"->"{rec["dst"]}"')
            elif action in ("delete_vertex", "delete_alias_vertex"):
                props = rec.get("props") or {}
                name = q(props.get("name", rec["vid"]))
                title = q(props.get("title", ""))
                fid = q(props.get("file_id", ""))
                typ = q(props.get("type", "其他"))
                stmt = (f'INSERT VERTEX entity(name,title,file_id,type) VALUES '
                        f'"{rec["vid"]}":("{name}","{title}","{fid}","{typ}")')
            elif action == "summary":
                continue
            else:
                continue
            if dry:
                print("  [dry]", stmt[:110])
                ok += 1
                continue
            r = s.execute(stmt)
            if not r.is_succeeded():
                print("  [fail]", stmt[:100], "->", r.error_msg())
                fail += 1
            else:
                ok += 1
            # 顶点还原后补边
            if action in ("delete_vertex", "delete_alias_vertex") and not dry:
                for e in rec.get("edges") or []:
                    p = e.get("props") or {}
                    src, dst = (rec["vid"], e["other"]) if e.get("is_out") else (e["other"], rec["vid"])
                    s.execute(f'INSERT EDGE relationship(name,file_id,show_flag,page_num) VALUES '
                              f'"{src}"->"{dst}":("{q(p.get("name",""))}","{q(p.get("file_id",""))}",'
                              f'"{q(p.get("show_flag","1"))}","{q(p.get("page_num",""))}")')
        except Exception as ex:
            print("  [err]", action, ex)
            fail += 1

    r = s.execute("MATCH (v:entity) RETURN count(v) AS c")
    vc = r.row_values(0)[0].as_int() if r.is_succeeded() and r.row_size() else -1
    r = s.execute("MATCH ()-[e:relationship]->() RETURN count(e) AS c")
    ec = r.row_values(0)[0].as_int() if r.is_succeeded() and r.row_size() else -1
    print(f"回滚完成：ok={ok} fail={fail}；当前 entities={vc} edges={ec}")
    print("注意：canonical 合并后的三元组指向不会自动还原（已在 audit 中记录 canonical 字段，可按需手工处理）")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
