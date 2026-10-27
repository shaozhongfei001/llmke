#!/usr/bin/env python3
"""R13 图谱存量数据归一迁移：清理噪声实体、合并长短名（canonical 重指向）。

规则与 graph_types.py 完全一致（同一份代码，不是另写一套）：
  - is_valid_entity() 判定为无效的（纯数字/结构词/过短）→ 删除顶点及其边
  - canonical_of() 判定应合并的 → 把边重指向到 canonical，再删除别名顶点
用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/migrate_normalize.py [space] [--dry-run]
"""
import json
import os
import sys
import time
import uuid

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service")

from nebula3.Config import Config  # noqa: E402
from nebula3.gclient.net import ConnectionPool  # noqa: E402

import graph_types as gt  # noqa: E402


AUDIT_DIR = "/home/szf/data/dev/llmke-r12/platform/r12/graph/audit"


# ---- schema 预检：比"写后复查"更早，且对**零行批次**同样有效 --------------------
# A-data 2026-10-27：写后复查在"这次要插的恰好为空"时永远不会触发，
# schema 漂移会潜伏到某天才炸。所以在**写任何数据之前**先读真实 tag/edge 定义做子集断言。

ENTITY_PROPS = ("name", "title", "file_id", "type")
EDGE_PROPS = ("name", "file_id", "show_flag", "page_num")


def _describe(s, kind, name):
    """读 tag/edge 的真实属性名集合。kind: 'TAG' | 'EDGE'。"""
    try:
        r = s.execute(f"DESCRIBE {kind} {name}")
    except Exception as e:
        raise RuntimeError(f"读取 {kind} {name} 定义失败: {str(e)[:80]}")
    props = set()
    for i in range(r.row_size()):
        vals = r.row_values(i)
        p = vals[0].as_string() if vals and vals[0].is_string() else None
        if not p:
            continue
        typ = vals[1].as_string() if len(vals) > 1 and vals[1].is_string() else ""
        if typ in ("string", "int64", "int32", "double", "bool", "timestamp", "date", "datetime", "float"):
            props.add(p)
    return props


def assert_schema(s, tag="entity", edge="relationship"):
    """脚本声明的属性集必须是真实 schema 的子集，否则**启动即失败**（不写任何数据）。

    动机：`INSERT VERTEX entity(...,e_type)` 在属性不存在时**不报错也不写入**，
    实测 count 仍为 0；如果只靠写后复查，遇到"本次待插集合为空"就永远发现不了。
    """
    tp = _describe(s, "TAG", tag)
    ep = _describe(s, "EDGE", edge)
    bad_t = [p for p in ENTITY_PROPS if p not in tp]
    bad_e = [p for p in EDGE_PROPS if p not in ep]
    if bad_t or bad_e:
        raise RuntimeError(
            f"schema 不匹配: TAG {tag} 缺 {bad_t}（实际 {sorted(tp)}）; "
            f"EDGE {edge} 缺 {bad_e}（实际 {sorted(ep)}）")
    print(f"schema 预检通过: TAG {tag}{sorted(tp)} / EDGE {edge}{sorted(ep)}")
    return True


def _props_of(s, vid):
    """按 id 读回顶点属性，用于 round-trip 比对。

    **必须用 `FETCH PROP ON`，不能用 `MATCH ... RETURN v.name`**：
    本环境实测（g_kb_26，真实顶点 `恒星项目` 与新建顶点都一样）
        MATCH (v) WHERE id(v)=="恒星项目" RETURN v.name   -> 返回 NULL（属性明明存在）
        FETCH PROP ON entity "恒星项目" YIELD properties  -> 属性齐全
    这是本环境的第三个"静默为空"：**读法本身会让"属性存在"看起来像"属性丢了"**。
    若用 MATCH 读法做 round-trip，会把"写入成功"全部判成"未落库"（假红）。
    """
    r = s.execute(f'FETCH PROP ON entity "{vid}" YIELD properties(vertex)')
    if not r.row_size():
        return None
    v = r.row_values(0)[0]
    if not v.is_map():
        return None
    out = {k: (x.as_string() if x.is_string() else str(x)) for k, x in v.as_map().items()}
    return out if out else None


def _insert_vertex_verified(s, vid, props, expect="create"):
    """插顶点 + **区分"真新增"与"静默覆盖"** + 属性 round-trip。

    Nebula 的 INSERT VERTEX 对已存在 vid 是**覆盖语义**（不报错、直接改属性），
    所以 `after==1` 完全无法区分：
        before==0 -> after==1  真新增
        before==1 -> after==1  静默覆盖（R1/R2 "只增不减"的场景下这就是丢数据）

    expect:
      create —— 要求 before==0，否则 raise（本该新增，实际被覆盖）；
      upsert —— 允许覆盖，但把旧属性读出来，写后在异常里附 old -> new，事后可还原。
    """
    old = _props_of(s, vid)
    before = 1 if old is not None else 0
    if expect == "create" and before:
        raise RuntimeError(f'INSERT VERTEX 期望新增但目标已存在: vid={vid!r} old={old}')
    s.execute(
        'INSERT VERTEX entity(name,title,file_id,type) VALUES '
        f'"{vid}":("{props.get("name","")}","{props.get("title","")}",'
        f'"{props.get("file_id","")}","{props.get("type","1")}")')
    new = _props_of(s, vid)
    if new is None:
        raise RuntimeError(f'INSERT VERTEX 未生效: vid={vid!r} 写后按 id 查不到（属性名与 schema 不符？）')
    for k in ("name", "title", "file_id", "type"):
        want = str(props.get(k, "")) if k != "type" else str(props.get(k, "1"))
        if str(new.get(k)) != want:
            raise RuntimeError(
                f'INSERT VERTEX 属性未落库: vid={vid!r} field={k} want={want!r} got={new.get(k)!r} '
                f'(before={before}, old={old})')
    if expect == "upsert" and before:
        print(f"  ~ upsert 覆盖: {vid!r} old={old} -> new={new}")
    return True


def _count_edge(s, src, dst, name=None):
    """src->dst 之间的 relationship 边数（按 id，不按名字）。

    **边的属性读法与顶点相反，不要"统一风格"**（A-data 2026-10-27 实测）：
        边  : e.name  -> 有值；properties(e) -> 有值；e.relationship.name -> NULL（坏的）
        顶点: v.name  -> NULL；v.entity.name -> 有值；FETCH PROP ON entity -> 有值
    所以本函数用 `e.name`，而 `_props_of` 用 FETCH PROP；两边写法不同是**故意的**。
    """
    q = f'MATCH (a)-[e:relationship]->(b) WHERE id(a)=="{src}" AND id(b)=="{dst}"'
    if name is not None:
        q += f' AND e.name=="{name}"'
    r = s.execute(q + " RETURN count(e)")
    return r.row_values(0)[0].as_int() if r.row_size() else 0


def _insert_edge_verified(s, src, dst, props):
    """插边 + **写后按 (src,dst,name) 复查**。

    nGQL 的 INSERT 在属性名与 schema 不符时**不报错也不写入**（实测：
    `INSERT VERTEX entity(...,e_type)` -> count 仍为 0）。边同理，一旦 tag/edge schema
    演进，就会出现"脚本跑完、审计日志齐、图里什么都没有"——比删除未生效更隐蔽，
    因为它影响的是"该出现的数据"而不是"该消失的数据"。
    """
    name = props.get("name", "")
    before = _count_edge(s, src, dst, name)
    s.execute(
        'INSERT EDGE relationship(name,file_id,show_flag,page_num) VALUES '
        f'"{src}"->"{dst}":("{props.get("name","")}","{props.get("file_id","")}",'
        f'"{props.get("show_flag","1")}","{props.get("page_num","")}")')
    after = _count_edge(s, src, dst, name)
    if after <= before:
        raise RuntimeError(
            f'INSERT EDGE 未生效: {src!r}->{dst!r} name={name!r} before={before} after={after}'
            '（nGQL 未报错但按 (src,dst,name) 复查没有新增；多半是属性名与 schema 不符）')
    return True


def _count_vertex(s, vid):
    """顶点存在性计数（0/1）。用于"删了没"的**前后对照**，不依赖 nGQL 的返回值。"""
    try:
        r = s.execute(f'MATCH (v) WHERE id(v)=="{vid}" RETURN count(v)')
        return r.row_values(0)[0].as_int() if r.row_size() else 0
    except Exception as e:
        print(f"  !! 顶点计数失败 {vid}: {str(e)[:60]}")
        return -1


def _delete_vertex_verified(s, vid, why="", expect="required", name=None):
    """删顶点 + **验证真的删掉了**（A-data 2026-10-27 三条细化后定稿）。

    nGQL 的 `DELETE VERTEX` 在目标不存在时**也返回成功**（与 ES 的
    delete_by_query deleted=0 同一族：静默成功、不报错）。

    `expect`：
      required —— 该 id 来自上游对图上顶点的**实际扫描结果**，不存在即上游算错，必须 raise；
      optional —— 语义是"如果存在就删"（如清理旧别名），不存在属正常，log + skip。
    区分二者是为了**不让护栏自己变成噪声**：一律 raise 会在正常空集场景误炸，
    最后大家把护栏注释掉，等于没有。

    复查按 **id** 而不是按名字：合并场景里 `人民币5000万元` 与 `5000万元` 只差前缀，
    按名字复查会把"还有同名顶点"误判成"没删掉"（或反之）。
    """
    before = _count_vertex(s, vid)
    if before < 0:
        return False
    if before == 0:
        if expect == "required":
            raise RuntimeError(
                f'DELETE VERTEX 目标不存在: vid={vid!r} name={name!r} why={why} '
                f'expect=required（该 id 来自图上扫描结果，缺失说明上游合并/过滤输入已不对）')
        print(f"  .. 顶点不存在（预期可缺），跳过: vid={vid!r} name={name!r} why={why}")
        return False
    s.execute(f'DELETE VERTEX "{vid}" WITH EDGE')
    after = _count_vertex(s, vid)
    if after != 0:
        raise RuntimeError(
            f'DELETE VERTEX 未生效: vid={vid!r} name={name!r} why={why} '
            f'before={before} after={after}（nGQL 未报错但按 id 复查仍在）')
    return True


def _props(session, vid):
    r = session.execute(f'MATCH (v:entity) WHERE id(v)=="{vid}" RETURN properties(v) AS p')
    if r.is_succeeded() and r.row_size():
        m = r.row_values(0)[0]
        if m.is_map():
            return {k: (v.as_string() if v.is_string() else str(v)) for k, v in m.as_map().items()}
    return {}


def _edges(session, vid):
    r = session.execute(f'MATCH (v:entity)-[e:relationship]-(v2:entity) WHERE id(v)=="{vid}" '
                        f'RETURN id(v2) AS other, properties(e) AS p, startNode(e)==id(v) AS is_out')
    out = []
    for i in range(r.row_size()):
        vals = r.row_values(i)
        props = {}
        try:
            if vals[1].is_map():
                props = {k: (v.as_string() if v.is_string() else str(v)) for k, v in vals[1].as_map().items()}
        except Exception:
            pass
        out.append({"other": vals[0].as_string(), "props": props, "is_out": vals[2].as_bool()})
    return out


class Audit:
    """R13 合并/删除审计：每批一个 JSONL，记录可逆的原始状态，供 rollback_audit.py 回滚。"""

    def __init__(self, space):
        os.makedirs(AUDIT_DIR, exist_ok=True)
        self.batch_id = f"{space}-{time.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
        self.path = os.path.join(AUDIT_DIR, f"{self.batch_id}.jsonl")
        self.fp = open(self.path, "a", encoding="utf-8")

    def log(self, action, **kw):
        rec = {"batch_id": self.batch_id, "space": kw.pop("space", None), "action": action, "ts": int(time.time())}
        rec.update(kw)
        self.fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.fp.flush()

    def close(self):
        self.fp.close()


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

    # 写任何数据之前先做 schema 预检（零行批次也能发现漂移）
    assert_schema(s)

    audit = Audit(space)
    print(f"审计批次：{audit.batch_id} -> {audit.path}")

    for n, _why in invalid:
        audit.log("delete_vertex", space=space, vid=n, props=_props(s, n), edges=_edges(s, n))
        _delete_vertex_verified(s, n, "invalid", expect="required", name=n)

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
            _insert_edge_verified(s, src, dst, {"name": name_v, "file_id": fid,
                                                "show_flag": flag, "page_num": pn})
            audit.log("add_edge_for_merge", space=space, src=src, dst=dst,
                      props={"name": name_v, "file_id": fid, "show_flag": flag, "page_num": pn})
        audit.log("delete_alias_vertex", space=space, vid=alias, canonical=canon,
                  props=_props(s, alias))
        _delete_vertex_verified(s, alias, f"merge->{canon}", expect="required", name=alias)

    # 存量节点重新推断类型（合并/删除之外的第二种清洗）
    r = s.execute("MATCH (v:entity) RETURN id(v) AS n, v.entity.type AS t")
    retyped = 0
    for i in range(r.row_size()):
        n = r.row_values(i)[0].as_string()
        old_t = r.row_values(i)[1].as_string() if r.row_values(i)[1].is_string() else ""
        new_t, _src = gt.infer_type(n, old_t)
        if new_t != old_t:
            audit.log("retype", space=space, vid=n, old=old_t, new=new_t)
            s.execute(f'UPDATE VERTEX ON entity "{n}" SET type = "{new_t}"')
            # 必须带 tag 前缀：`v.type` 在本环境恒返回 NULL（不带 tag 的属性访问不可靠），
            # 会导致"UPDATE 明明成功却判成未生效"，且归因会一路跑偏到写入侧。
            r2 = s.execute(f'MATCH (v:entity) WHERE id(v)=="{n}" RETURN v.entity.type')
            got = r2.row_values(0)[0].as_string() if r2.row_size() else ""
            if got != new_t:
                raise RuntimeError(f'UPDATE VERTEX 未生效: {n!r} 期望 type={new_t!r} 实际 {got!r}')
            retyped += 1
    print(f"类型重判：{retyped} 个节点")

    r = s.execute("MATCH (v:entity) RETURN count(v) AS c")
    vc = r.row_values(0)[0].as_int() if r.is_succeeded() and r.row_size() else -1
    r = s.execute("MATCH ()-[e:relationship]->() RETURN count(e) AS c")
    ec = r.row_values(0)[0].as_int() if r.is_succeeded() and r.row_size() else -1
    print(f"迁移后：entities={vc} edges={ec}")
    audit.log("summary", space=space, entities=vc, edges=ec)
    audit.close()
    print(f"审计已落盘：{audit.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
