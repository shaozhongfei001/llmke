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


def check_mineru():
    cfg = Path(os.environ.get("MINERU_TOOLS_CONFIG_JSON",
                              "/home/szf/data/dev/models/mineru/magic-pdf.json"))
    weights = Path("/home/szf/data/dev/models/mineru/models")
    if not cfg.is_file():
        record("mineru:config", "SKIP", f"no config at {cfg}")
        return
    try:
        conf = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        record("mineru:config", "FAIL", f"{type(exc).__name__}: {exc}")
        return
    models_dir = Path(conf.get("models-dir", ""))
    present = models_dir.is_dir() and any(models_dir.rglob("*.pt"))
    record("mineru:config", "PASS" if present else "FAIL",
           {"models_dir": str(models_dir), "device": conf.get("device-mode"),
            "formula": conf.get("formula-config", {}).get("enable")},
           None if present else "权重目录不存在或无 .pt")
    record("mineru:weights_root", "PASS" if weights.is_dir() else "FAIL",
           {"path": str(weights)})


NOT_IMPLEMENTED = [
    ("biz:同谓词双向不误合并", "平台尚无图执行与谓词归一化，只有映射层"),
    ("biz:加/减/零调整，总额与分项一致", "无数值一致性校验器，也无图查询结果"),
    ("biz:多文件别名与同名异体", "别名归一未实现（映射层只保证同文多源不丢来源）"),
    ("biz:新旧政策有效版本", "无时间/版本过滤执行路径"),
    ("biz:合法孤点", "无图遍历，孤点语义未定义"),
    ("biz:不可见文件变化不污染可见构建", "无权限/可见性构建，无法构造该场景"),
    ("biz:图禁用/无种子时路线准确", "图未接入运行时，无法降级验证"),
    ("biz:global 报告/引用失效识别", "未消费真实社区/global 产物"),
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    check_infra()
    check_legacy_channels()
    check_mapping()
    check_mineru()
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
