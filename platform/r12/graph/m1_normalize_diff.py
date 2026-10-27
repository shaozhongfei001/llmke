#!/usr/bin/env python3
"""M1 归一化前后差异对比（只读：从 Nebula 读现有图，喂给新规则，不写任何库）。

用法：
  PYTHONPATH=<graph svc> platform/r12/venvs/graph/bin/python platform/r12/graph/m1_normalize_diff.py kb_9
"""
import json
import os
import re
import sys

import requests

SVC = "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service"
sys.path.insert(0, SVC)
os.environ.setdefault("PYTHONPATH", SVC)
os.environ.setdefault("NACOS_SERVER_ADDRESS", "127.0.0.1:18848")
os.environ.setdefault("NAMESPACE", "")
os.environ.setdefault("DATA_ID", "index_graph_config_py")
os.environ.setdefault("GROUP", "DEFAULT_GROUP")

import graph_types as gt  # noqa: E402
from graph_fun_tool import user_connect_space  # noqa: E402

kb = sys.argv[1] if len(sys.argv) > 1 else "kb_9"
session = user_connect_space("g_" + kb)

ES_PORT, MV_PORT, MV_DB = 19527, 19526, "graph_base"


def _ver_num(v):
    """'V1' -> 1；空 -> -1。用于"有效版本"判定（同 parent 取最大）。"""
    import re as _re
    m = _re.fullmatch(r"[Vv](\d+)", str(v or "").strip())
    return int(m.group(1)) if m else -1


def _es_ids(index):
    """当前代次 ES 里真实存在的 chunk _id 集合（引用有效性的分母/对照）。

    R14-B（A 提醒）：图抽取读 `[kb, "table_chunks_"+kb]`，所以台账的 pk 落在
    `table_chunks_*` 里；只用 kb 主索引当分母会把"台账命中 table_chunks 的 pk"
    误判成悬空。因此分母取 **kb + table_chunks + table_summary** 三索引之并，
    并输出逐索引明细，便于看出是哪一类在贡献命中。
    （注：`table_summary` 不会进图引用，但纳入全集不影响命中率上限，分档报告里单列。）
    

    同时返回"version 覆盖情况"：只有在**所有块 metadata.version 非空**时，
    "引用全部命中"才算合法判据；代次未统一时命中率没有判别力（C 的提醒）。
    """
    ids, no_ver, per_index = set(), [], {}
    docs = []  # (id, index, parent, version, chunk_index)
    for idx in (index, f"table_chunks_{index}", f"table_summary_{index}"):
        r = requests.post(f"http://127.0.0.1:{ES_PORT}/search_by_custom_param",
                          json={"index_name": [idx], "page_no": 1, "page_size": 2000}, timeout=120)
        rows = ((r.json().get("data") or {}) or {}).get("result_data") or []
        per_index[idx] = 0
        for row in rows:
            _id = str(row.get("_id"))
            ids.add(_id)
            per_index[idx] += 1
            md = (row.get("_source") or {}).get("metadata") or {}
            ver = md.get("version")
            if ver in (None, ""):
                no_ver.append({"id": _id, "file_id": md.get("file_id"),
                               "title": md.get("title"), "index": idx})
            docs.append((_id, idx, md.get("parent_file_name") or md.get("title"),
                         _ver_num(ver), md.get("chunk_index")))
    # R14-B（TL 裁定）：**分母只取"有效版本 chunk 集合"**，且不把 table_summary 的汇总行算进去
    # （chunk_index=-1，图抽取不读 table_summary，算进去会让分母虚高、hit 虚低）。
    eff_by_parent = {}
    for _id, idx, parent, v, _ci in docs:
        if idx.startswith("table_summary_"):
            continue
        if parent:
            eff_by_parent[parent] = max(eff_by_parent.get(parent, -1), v)
    effective = [{"chunk_id": _id, "index": idx, "parent": parent, "version": v}
                 for _id, idx, parent, v, _ci in docs
                 if not idx.startswith("table_summary_") and parent
                 and v == eff_by_parent.get(parent)]
    return ids, no_ver, per_index, effective


def _entity_pks(names):
    """实体名 → 真实 chunk_pk_list（向量实体表 graph_entity_<kb>）。

    R14-B：原脚本把顶点的 `file_id`（文件 id，逗号串）当 chunk pk 用，口径是错的——
    顶点上根本没有 chunk 级引用，chunk_pk_list 存在向量实体表里。
    """
    out = {}
    names = [str(n).replace('"', "") for n in names if n]
    for i in range(0, len(names), 50):
        batch = names[i:i + 50]
        expr = "text in [%s]" % ", ".join('"%s"' % n for n in batch)
        try:
            r = requests.post(f"http://127.0.0.1:{MV_PORT}/get_doc_by_col",
                              json={"collection_name": f"graph_entity_{kb}", "db_name": MV_DB,
                                    "expr": expr}, timeout=120)
            rows = ((r.json().get("data") or {}).get("result_data")) or []
        except Exception as e:
            print("# 读取实体 pk 失败:", e)
            continue
        for row in rows:
            md = row.get("metadata") or {}
            text = row.get("page_content") or md.get("text")
            if text:
                out[str(text)] = [str(p) for p in (md.get("chunk_pk_list") or [])]
    return out

# 读顶点（只读）
r = session.execute('MATCH (v:entity) RETURN id(v) AS n, properties(v) AS p')
entity_source = {}
for i in range(r.row_size()):
    vals = r.row_values(i)
    name = vals[0].as_string()
    props = {}
    try:
        if vals[1].is_map():
            props = {k: (v.as_string() if v.is_string() else str(v)) for k, v in vals[1].as_map().items()}
    except Exception:
        pass
    fid = props.get("file_id", "")
    entity_source[name] = {
        "entity_type": "1",
        "e_type": [props.get("e_type", "") or ""],
        "file_id": fid,
        "title": props.get("title", ""),
        # 真实 chunk pk 在后面一次性从向量实体表补（见 _entity_pks），
        # 不再把顶点上的 file_id（文件 id）冒充成 chunk pk。
        "chunk_pk_list": [],
    }

# 真实 chunk pk（向量实体表）+ 当前代次 ES _id：用于"引用有效性"判据（TL 要求必须与实体名集合差同时输出）
_pks = _entity_pks(list(entity_source.keys()))
for _n, _ps in _pks.items():
    if _n in entity_source:
        entity_source[_n]["chunk_pk_list"] = _ps
ES_IDS, ES_NO_VER, ES_PER_INDEX, ES_EFFECTIVE = _es_ids(kb)
DENOM = {x["chunk_id"] for x in ES_EFFECTIVE}
ALL_PKS = sorted({p for v in entity_source.values() for p in v["chunk_pk_list"]})
HIT = [p for p in ALL_PKS if p in DENOM]
HIT_ANY = [p for p in ALL_PKS if p in ES_IDS]
print(f"# ES 索引分母明细：{ES_PER_INDEX}")
print(f"# ES 代次就绪度：块 {len(ES_IDS)}，其中 version 为空 {len(ES_NO_VER)}"
      + (f"  -> 代次未统一，引用判据降级" if ES_NO_VER else "  -> 代次已统一，判据有效"))
for _x in ES_NO_VER:
    print(f"   -no-version chunk={_x['id']} file_id={_x['file_id']} title={_x['title']}")
print(f"# 分母口径：有效版本 chunk {len(DENOM)} 个（已排除 table_summary 汇总行与旧版本 V0，"
      f"全量 ES _id {len(ES_IDS)} 个）")
print(f"# 参与统计的 chunk id：{sorted(DENOM)}")
print(f"# 引用有效性（合并前）：pk 去重 {len(ALL_PKS)}，命中有效版本 {len(HIT)}，"
      f"命中率 {(len(HIT) / len(ALL_PKS)) if ALL_PKS else 0:.1%}"
      f"（若按全量 ES 口径命中 {len(HIT_ANY)}）")
if ALL_PKS and not HIT:
    print("#   !! 全部悬空：此时\"pk 集合相等\"是假 PASS，M1 只能判\"逻辑等价、引用未验\"")

# 读边（只读）
r2 = session.execute('MATCH (a:entity)-[e:relationship]->(b:entity) RETURN id(a) AS s, id(b) AS d, properties(e) AS p')
triples, triples_source = [], {}
for i in range(r2.row_size()):
    vals = r2.row_values(i)
    src, dst = vals[0].as_string(), vals[1].as_string()
    props = {}
    try:
        if vals[2].is_map():
            props = {k: (v.as_string() if v.is_string() else str(v)) for k, v in vals[2].as_map().items()}
    except Exception:
        pass
    rel = props.get("name", "") or "related"
    triples.append([src, rel, dst])
    triples_source[f"{src},{rel},{dst}"] = props

new_triples, kept, new_src, report = gt.normalize_graph_data(triples, entity_source, triples_source)

WATCH = ["万元", "额度", "已用额度", "授信额度", "AA", "AAA", "人民币5000万元", "5000万元",
         "加30个基点", "30个基点", "信用部分不超过1000万元", "客户信用评级", "日均存款"]

print(f"# kb={kb}")
print(f"# 输入：顶点 {len(entity_source)}，边 {len(triples)}")
print(f"# 输出：保留实体 {report['kept_entities']}，边 {len(new_triples)}，"
      f"过滤 {len(report['filtered'])}，合并 {len(report['merged'])}，丢弃三元组 {report['dropped_triples']}")
print("# 过滤明细：")
for f in report["filtered"]:
    print("   -", f["name"], "->", f["reason"])
print("# 合并映射（前 -> 后）：")
for k, v in report["merged"].items():
    print(f"   - {k} -> {v}")
print("# 关注实体的最终状态：")
for w in WATCH:
    merged_to = report["merged"].get(w)
    if w in kept:
        status = "KEPT"
    elif merged_to:
        status = "MERGED-> " + merged_to
    elif any(f["name"] == w for f in report["filtered"]):
        status = "FILTERED"
    else:
        status = "GONE"
    b = kept.get(w) or {}
    rule = b.get("norm_rule", "")
    print(f"   {w:24s} {status:28s} rule={rule!r} norm_from={b.get('norm_from','')!r} "
          f"mentions={[m['text'] for m in (b.get('mentions') or [])]}")

print("# 授信额度 是否仍有边：", "YES" if any(t[0] == "授信额度" or t[2] == "授信额度" for t in new_triples) else "NO")
print("# 评级词是否可达：", {w: (w in kept) for w in ("AA", "AAA", "A")})

# ---- A-data 三条建议：类型集合差 / chunk_pk_list 长度变化 / 引用是否被合并吸收 ----
print("# (实体, 类型) 集合差：")
# 实体名字集合差（注意：e_type 前后语义不同——前是 Nebula 属性、后是推断类型，不能直接按 (名,类型) 比）
before_names = set(entity_source.keys())
after_names = set(kept.keys())
lost = sorted(before_names - after_names)
print(f"   实体名集合：前 {len(before_names)} / 后 {len(after_names)} / 消失 {len(lost)}")
for x in lost:
    print("   -lost", x)
import collections as _c
print("   类型分布(后)：", dict(_c.Counter((v.get("e_type") or [""])[0] for v in kept.values()).most_common()))

print("# chunk_pk_list 长度变化（合并后 vs 该 canonical 下各原实体的并集）：")
# 从 report.merged 反推 raw -> canon（name_map 是 normalize 内部变量，这里重建）
merged = report["merged"]
raw_by_canon = {}
for raw in entity_source.keys():
    canon = merged.get(gt.clean_name(raw), gt.clean_name(raw))
    raw_by_canon.setdefault(canon, []).append(raw)
shrunk, grown = [], []
for canon, raws in raw_by_canon.items():
    if canon not in kept:
        continue
    after_n = len(set(kept[canon].get("chunk_pk_list") or []))
    before_union = set()
    for raw in raws:
        before_union |= set(entity_source[raw].get("chunk_pk_list") or [])
    if after_n < len(before_union):
        shrunk.append((canon, len(before_union), after_n))
    elif len(raws) > 1:
        grown.append((canon, len(before_union), after_n))
print(f"   合并后 pk 变少的实体：{len(shrunk)}")
for x in shrunk[:10]:
    print("   -shrunk", x)
print(f"   多写法合并的实体（引用应被并集吸收）：{len(grown)}")
for x in grown[:10]:
    print("   -merged", x)

# ---- 合并后的引用有效性（M1b 的前置指标；重抽取后才有判别力）----
kept_pks = sorted({p for v in kept.values() for p in (v.get("chunk_pk_list") or [])})
kept_hit = [p for p in kept_pks if p in DENOM]
print(f"# 引用有效性（合并后）：pk 去重 {len(kept_pks)}，命中 {len(kept_hit)}，"
      f"命中率 {(len(kept_hit) / len(kept_pks)) if kept_pks else 0:.1%}")
ref_validity = {
    "es_ids": len(ES_IDS),
    "before": {"pks": len(ALL_PKS), "hit": len(HIT),
               "rate": (len(HIT) / len(ALL_PKS)) if ALL_PKS else 0.0},
    "after": {"pks": len(kept_pks), "hit": len(kept_hit),
              "rate": (len(kept_hit) / len(kept_pks)) if kept_pks else 0.0},
    # 判定口径：命中率为 0 时，pk 集合相等无判别力，只能记"逻辑等价、引用未验"
    # C 建议：不只给计数，给**可直接执行的补齐清单**（A 按 file_id 逐条确认是否补跑）
    "es_version_coverage": {"chunks": len(ES_IDS), "per_index": ES_PER_INDEX,
                            "denominator": sorted(DENOM), "denominator_size": len(DENOM),
                            "missing_version": len(ES_NO_VER),
                            "ready": not ES_NO_VER,
                            "missing": [{"chunk_id": x["id"], "file_id": x["file_id"],
                                         "title": x["title"]} for x in ES_NO_VER]},
    "verdict": ("引用未验（代次未统一）" if ES_NO_VER else
                ("引用未验（全部悬空）" if ALL_PKS and not HIT else "可判")),
}

out = {"kept": sorted(kept.keys()), "report": report,
       "triples": new_triples, "ref_validity": ref_validity}
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence",
                 f"M1-diff-{kb}.json")
os.makedirs(os.path.dirname(p), exist_ok=True)
with open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("# 证据：", p)
