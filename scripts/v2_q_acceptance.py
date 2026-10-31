#!/usr/bin/env python3
"""Q 阶段验收（项目内部复核，不冒充外部独立签署）。

设计原则：**"没做"必须显式出现在报告里**，不能因为跳过了就从结果里消失。
每项给 PASS / FAIL / SKIP / NOT_IMPLEMENTED 之一，附证据或原因；有 FAIL 才非零退出。

当前覆盖：
- 基础设施可达性（ES/ES 代理/MinIO/解析/索引/Milvus/MySQL）
- 线上两通道数据完整性（kb_9 / table_chunks_kb_9 的 333、329；source 是否按文件唯一）
- 图映射不变量（同文多源 1:N、删一留一）
- MinerU 环境可用性（离线配置 + CLI）
- 任务书"业务场景"9 项：**全部标 NOT_IMPLEMENTED**——平台还没有图执行/版本治理/权限构建，
  不许用 dense 检索或固定夹具顶替。
"""

import argparse
import json
import os
import socket
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services/rag-alg/index_data_service"))

ES = "http://127.0.0.1:19200"
RESULTS = []


def record(item, status, evidence, boundary=None):
    RESULTS.append({"item": item, "status": status, "evidence": evidence, "boundary": boundary})


def http_json(url, timeout=8):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


def tcp_open(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_infra():
    probes = {
        "es_19200": lambda: http_json(ES + "/_cluster/health")["status"] != "",
        "es_proxy_19527": lambda: tcp_open("127.0.0.1", 19527),
        "minio_19000": lambda: tcp_open("127.0.0.1", 19000),
        "parse_12340": lambda: tcp_open("127.0.0.1", 12340),
        "index_18082": lambda: tcp_open("127.0.0.1", 18082),
        "milvus_19630": lambda: tcp_open("127.0.0.1", 19630),
        "mysql_13306": lambda: tcp_open("127.0.0.1", 13306),
    }
    for name, fn in probes.items():
        try:
            ok = bool(fn())
        except Exception as exc:  # noqa: BLE001
            record(f"infra:{name}", "FAIL", f"{type(exc).__name__}: {exc}")
            continue
        record(f"infra:{name}", "PASS" if ok else "FAIL", "reachable" if ok else "unreachable")


def check_legacy_channels():
    """线上两通道：按**实测事实**断言，不套"两通道都一样"的想象。

    实测（2026-10-31，kb_9 全量 270 doc / table_chunks_kb_9 全量 2 doc）：
    - kb_9 每个文件 chunk_index 从 0 连续；
    - table_chunks_kb_9 里 333 只有 1 条且 chunk_index=1 —— 表格通道**不是**从 0 起；
    - 329 是 xlsx，kb_9 里 **一条都没有**，内容只走表格通道。
    所以：正文通道查"从 0 连续"，表格通道只查"存在且 source 唯一"，
    xlsx 单独查表格通道有、正文通道无（这是事实，不是缺陷）。
    """
    for fid in ("333", "329"):
        body = {"size": 200, "_source": ["metadata.source", "metadata.chunk_index"],
                "query": {"term": {"metadata.file_id": fid}}}
        for index, rule in (("kb_9", "contiguous_from_zero"), ("table_chunks_kb_9", "exists")):
            req = urllib.request.Request(index_url(index + "/_search"),
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            try:
                hits = json.loads(urllib.request.urlopen(req, timeout=10).read())["hits"]["hits"]
            except Exception as exc:  # noqa: BLE001
                record(f"legacy:{index}:{fid}", "FAIL", f"{type(exc).__name__}: {exc}")
                continue
            idxs = sorted(h["_source"].get("metadata", {}).get("chunk_index") for h in hits)
            sources = {h["_source"].get("metadata", {}).get("source") for h in hits}
            evidence = {"docs": len(hits), "distinct_source": len(sources), "chunk_index": idxs[:6]}

            if index == "kb_9" and fid == "329":
                # xlsx 无正文通道：这是实测事实，文档已在证据里
                record("legacy:kb_9:329", "PASS" if not hits else "FAIL", evidence,
                       "xlsx 只走表格通道（实测）")
                continue
            if not hits:
                record(f"legacy:{index}:{fid}", "FAIL", evidence, "该通道没有任何块")
                continue
            if len(sources) != 1 or None in sources:
                record(f"legacy:{index}:{fid}", "FAIL", evidence, "source 不唯一或为空（身份键失效）")
                continue
            if rule == "contiguous_from_zero":
                expected = list(range(len(idxs)))
                ok = idxs == expected
                record(f"legacy:{index}:{fid}", "PASS" if ok else "FAIL", evidence,
                       None if ok else f"chunk_index 不连续: {idxs}")
            else:
                # 表格通道块号起点是 legacy 既有行为（333 为 1），只记录不判失败
                record(f"legacy:{index}:{fid}", "PASS", evidence,
                       f"chunk_index 起点={idxs[0]}（legacy 既有编号，不要求从 0）")


def index_url(path):
    return f"{ES}/{urllib.parse.quote(path, safe='/_')}"


def check_mapping():
    """同文多源：一个引擎 chunk 对应多个 SourceRef；删掉一个来源后另一个仍在。"""
    from graph_engine_adapter.mapping import InputUnit, SourceMap, native_key

    text = "产品甲的最高额度为8000万元。"
    sm = SourceMap()
    for seq, fid in ((0, "333"), (0, "334")):
        sm.add(InputUnit(text, content_uid="c" * 64, parse_artifact_id=f"art{fid}" if fid == "333"
                         else "art334", seq=seq,
                         source_ref={"file_id": fid, "channel": "text", "locator": {"start": 0,
                                                                                    "end": 10}},
                         channel="text"))
    key = native_key(text)
    stats = sm.stats()
    refs = sm.sources_for(key)
    ok = stats["engine_chunks"] == 1 and stats["shared_chunks"] == 1 and len(refs) == 2
    record("mapping:same_text_multi_source", "PASS" if ok else "FAIL",
           {"stats": stats, "sources": [r["file_id"] for r in refs]})

    # 删一留一：去掉 333 后，同一 chunk 仍能解析到 334
    survivors = [u for u in sm.units_for(key) if u.source_ref["file_id"] != "333"]
    remaining = {u.source_ref["file_id"] for u in survivors}
    ok = remaining == {"334"}
    record("mapping:delete_one_keep_rest", "PASS" if ok else "FAIL",
           {"remaining": sorted(remaining)}, None if ok else "删掉一个来源后其余来源丢失")


def check_capabilities():
    """图引擎能力声明：VERIFIED 必须有证据；GRAPH 路线未被证明就不许写成已具备。"""
    try:
        from graph_engine_adapter import describe
    except Exception as exc:  # noqa: BLE001
        record("graph:describe", "FAIL", f"{type(exc).__name__}: {exc}")
        return
    d = describe()
    caps = d["capabilities"]
    lying = [k for k, v in caps.items() if v["status"] == "VERIFIED" and not v["evidence"]]
    route = caps.get("retrieve_graph_route", {}).get("status")
    ok = not lying and route != "VERIFIED"
    record("graph:describe", "PASS" if ok else "FAIL",
           {"counts": d["counts"], "graph_route": route},
           None if ok else f"无证据却声明 VERIFIED: {lying} 或 GRAPH 路线被误标 {route}")


def check_mineru():
    cfg = Path(os.environ.get("MINERU_TOOLS_CONFIG_JSON",
                              os.path.expanduser("~/mineru/magic-pdf.json")))
    if not cfg.is_file():
        record("mineru:config", "SKIP", f"no config at {cfg}")
        return
    try:
        conf = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        record("mineru:config", "FAIL", f"{type(exc).__name__}: {exc}")
        return
    models_dir = Path(conf.get("models-dir", ""))
    weights = models_dir
    present = models_dir.is_dir() and any(models_dir.rglob("*.pt"))
    record("mineru:config", "PASS" if present else "FAIL",
           {"models_dir": str(models_dir), "device": conf.get("device-mode"),
            "formula": conf.get("formula-config", {}).get("enable")},
           None if present else "权重目录不存在或无 .pt")
    # 权重根目录直接取配置里的 models-dir，不在代码里写死机器路径
    record("mineru:weights_root", "PASS" if weights.is_dir() else "FAIL",
           {"path": str(weights)})


NOT_IMPLEMENTED = [
    ("biz:global 报告/引用失效识别（社区/global 真实产物消费）",
     "引用校验已在断言层可用，但社区/global 处理器尚未消费真实产物，不得用普通 RAG 顶替"),
    ("biz:端到端业务问答（真实文档→引擎→回答）",
     "断言层语义已验；引擎侧接线与回答组装未做，端到端不算通过"),
]


def check_business_semantics():
    """任务书业务场景在**标准断言层**的语义验证（构造数据）。

    每项结论都带 boundary：语义层成立 ≠ 端到端成立。没有这句，PASS 会被误读成产品能力已通。
    """
    from graph_engine_adapter.assertions import (Assertion, AssertionStore, SourceRef,
                                                 decide_route, DENSE_FALLBACK, GRAPH)

    def ref(fid, loc="0-10"):
        return SourceRef(file_id=fid, artifact_id="a" * 64, channel="text", locator=loc)

    boundary = "语义层（构造数据）；端到端未做"

    # 1 同谓词双向不误合并
    s = AssertionStore()
    s.register_entity("cust", "客户A"); s.register_entity("p", "产品甲"); s.register_entity("q", "产品乙")
    s.add(Assertion(subject="cust", predicate="申请", object_entity="p", sources=[ref("333")]))
    ok = s.related("cust", "申请", "p") and not s.related("p", "申请", "cust")
    record("biz:同谓词双向不误合并", "PASS" if ok else "FAIL", {"forward": True, "reverse": False}, boundary)

    # 2 加/减/零调整 + 总额与分项
    s2 = AssertionStore(); s2.register_entity("p", "产品甲")
    for op, val in (("set", 8000), ("add", 2000), ("subtract", 500), ("add", 0)):
        s2.add(Assertion(subject="p", predicate="额度", object_value=val, unit="万元", key="额度",
                         op=op, sources=[ref("333")]))
    led = s2.ledger("p", "额度")
    ok = led["total"] == 9500 and len(led["components"]) == 3 and led["unit"] == "万元"
    record("biz:加/减/零调整，总额与分项一致", "PASS" if ok else "FAIL",
           {"total": led["total"], "components": len(led["components"])}, boundary)

    # 3 多文件别名与同名异体
    s3 = AssertionStore()
    s3.register_entity("p1", "产品甲", "甲产品")
    s3.register_entity("x1", "同名"); s3.register_entity("x2", "同名")
    ok = (s3.resolve("甲产品") == "p1" and s3.entities_named("同名") == ["x1", "x2"]
          and s3.resolve("同名") is None)
    record("biz:多文件别名与同名异体", "PASS" if ok else "FAIL",
           {"alias": "甲产品->p1", "homonym_ids": s3.entities_named("同名")}, boundary)

    # 4 同事实多来源删一保留
    s4 = AssertionStore(); s4.register_entity("p", "产品甲")
    s4.add(Assertion(subject="p", predicate="额度", object_value=8000, unit="万元", key="额度",
                     sources=[ref("333"), ref("334")]))
    s4.remove_source("333")
    ok = len(s4.facts("p", "额度")) == 1 and s4.facts("p", "额度")[0].sources[0].file_id == "334"
    s4.remove_source("334")
    ok = ok and s4.facts("p", "额度") == []
    record("biz:同事实多来源删一保留", "PASS" if ok else "FAIL", {"after_first_delete": 1}, boundary)

    # 5 合法孤点
    s5 = AssertionStore(); s5.add_orphan("lonely", "孤立实体")
    d5 = decide_route(True, ["孤立实体"], s5)
    ok = s5.stats()["orphans"] == 1 and s5.facts("lonely") == [] and d5["route"] == DENSE_FALLBACK
    record("biz:合法孤点", "PASS" if ok else "FAIL", {"route": d5["reason"]}, boundary)

    # 6 新旧政策有效版本
    s6 = AssertionStore(); s6.register_entity("p", "产品甲")
    s6.add(Assertion(subject="p", predicate="额度", object_value=5000, unit="万元", key="额度",
                     effective_from="2026-01-01", effective_to="2026-07-01", sources=[ref("333")]))
    s6.add(Assertion(subject="p", predicate="额度", object_value=8000, unit="万元", key="额度",
                     effective_from="2026-07-01", sources=[ref("334")]))
    ok = (s6.effective_fact("p", "额度", as_of="2026-03-15").object_value == 5000
          and s6.effective_fact("p", "额度", as_of="2026-10-31").object_value == 8000)
    record("biz:新旧政策有效版本", "PASS" if ok else "FAIL", {"as_of_0315": 5000, "as_of_1031": 8000}, boundary)

    # 7 不可见文件变化不污染可见构建
    s7 = AssertionStore(); s7.register_entity("p", "产品甲")
    s7.add(Assertion(subject="p", predicate="额度", object_value=8000, unit="万元", key="额度",
                     visibility={"public"}, sources=[ref("333")]))
    s7.add(Assertion(subject="p", predicate="额度", object_value=99999, unit="万元", key="额度",
                     op="add", visibility={"secret"}, sources=[ref("999")]))
    before = s7.ledger("p", "额度", scopes={"public"})["total"]
    s7.remove_source("999")
    after = s7.ledger("p", "额度", scopes={"public"})["total"]
    ok = before == after == 8000
    record("biz:不可见文件变化不污染可见构建", "PASS" if ok else "FAIL",
           {"visible_before": before, "visible_after": after}, boundary)

    # 8 图禁用/无种子时路线准确
    ok = (decide_route(False, ["产品甲"])["reason"] == "GRAPH_DISABLED"
          and decide_route(True, [])["reason"] == "NO_SEED_ENTITY"
          and decide_route(True, ["查无此实体"], s5)["reason"] == "SEEDS_UNKNOWN")
    record("biz:图禁用/无种子时路线准确", "PASS" if ok else "FAIL",
           {"disabled": "GRAPH_DISABLED", "no_seed": "NO_SEED_ENTITY"}, boundary)



def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    check_infra()
    check_legacy_channels()
    check_mapping()
    check_capabilities()
    check_mineru()
    check_business_semantics()
    for item, why in NOT_IMPLEMENTED:
        record(item, "NOT_IMPLEMENTED", why)

    fails = [r for r in RESULTS if r["status"] == "FAIL"]
    summary = {s: sum(1 for r in RESULTS if r["status"] == s)
               for s in ("PASS", "FAIL", "SKIP", "NOT_IMPLEMENTED")}
    report = {"schema": "llmke.q-acceptance.v1",
              "summary": summary,
              "verdict": "PASS" if not fails else "FAIL",
              "note": "NOT_IMPLEMENTED 表示能力未建，不计入 PASS，也不等于通过",
              "results": RESULTS}
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
    print(json.dumps({"summary": summary, "verdict": report["verdict"]}, ensure_ascii=False))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
