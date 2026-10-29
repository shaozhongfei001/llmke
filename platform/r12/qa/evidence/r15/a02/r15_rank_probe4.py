"""R15 A02 组件级反例 v4：每个阶段用新 session，等 schema 真正传播。"""
import time
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config

SPACE = f"r15_rank_t{int(time.time()) % 100000}"
cfg = Config()
cfg.max_connection_pool_size = 4
pool = ConnectionPool()
assert pool.init([("127.0.0.1", 19669)], cfg)


def run(stmts, use_space=None):
    """在一个全新 session 里执行一组语句并释放，避免 session 缓存旧 schema。"""
    s = pool.get_session("root", "nebula")
    try:
        if use_space:
            s.execute(f"USE {use_space}")
        out = []
        for q in stmts:
            r = s.execute(q)
            out.append((r.is_succeeded(), "" if r.is_succeeded() else r.error_msg()))
        return out
    finally:
        s.release()


print("space:", run([f"CREATE SPACE {SPACE} (vid_type=FIXED_STRING(64))"])[0])
time.sleep(22)
print("schema:", run([
    "CREATE TAG IF NOT EXISTS entity(name string)",
    "CREATE EDGE IF NOT EXISTS relationship(name string, show_flag string)",
], SPACE))
time.sleep(22)   # 等 schema 同步到 storaged

print("seed:", run(['INSERT VERTEX entity(name) VALUES "A1":("A1"),"B1":("B1"),"A2":("A2"),"B2":("B2")'], SPACE))

print("old:", run([
    'INSERT EDGE relationship(name,show_flag) VALUES "A1"->"B1":("客户","1")',
    'INSERT EDGE relationship(name,show_flag) VALUES "A1"->"B1":("担保方","1")',
], SPACE))
print("new:", run([
    'INSERT EDGE relationship(name,show_flag) VALUES "A2"->"B2"@1111:("客户","1")',
    'INSERT EDGE relationship(name,show_flag) VALUES "A2"->"B2"@2222:("担保方","1")',
], SPACE))

s = pool.get_session("root", "nebula")
s.execute(f"USE {SPACE}")


def names(src, dst):
    r = s.execute(
        f'MATCH (v:entity)-[e:relationship]->(v2:entity) '
        f'WHERE id(v)=="{src}" AND id(v2)=="{dst}" RETURN properties(e).name'
    )
    if not r.is_succeeded():
        return None, r.error_msg()
    return [r.row_values(i)[0].as_string() for i in range(r.row_size())], ""


old, e1 = names("A1", "B1")
new, e2 = names("A2", "B2")
print(f"\n旧行为(无rank) A1->B1 : {len(old) if old is not None else e1} 条 {old}")
print(f"新行为(有rank) A2->B2 : {len(new) if new is not None else e2} 条 {new}")
print("判定:", "PASS" if old and len(old) == 1 and new and len(new) == 2 else "CHECK")

s.execute(f"DROP SPACE {SPACE}")
s.release()
pool.close()
