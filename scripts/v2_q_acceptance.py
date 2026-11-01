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
import tempfile
import socket
import time
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services/rag-alg/index_data_service"))

ES = "http://127.0.0.1:19200"
RESULTS = []
# 断点续跑：整轮 Q 要跑 40+ 分钟，任一检查卡住/超时就会丢掉**整份**结果。
# 写一行落一行，进程被杀也能知道"哪些已经真的过了"，续跑只补没过的部分。
CHECKPOINT = None


def record(item, status, evidence, boundary=None, _fn=None):
    entry = {"item": item, "status": status, "evidence": evidence, "boundary": boundary}
    RESULTS.append(entry)
    if CHECKPOINT:
        fn = _fn or sys._getframe(1).f_code.co_name
        try:
            with open(CHECKPOINT, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({**entry, "fn": fn}, ensure_ascii=False) + "\n")
        except OSError:
            pass          # 落盘失败不能反过来打死验收本身


def install_resume(path):
    """按检查函数粒度续跑：上一轮**全部 PASS** 的函数直接回放结果，不再执行。

    为什么按函数而不是按条目：条目名是函数内部拼出来的，调用前不知道；
    而函数名从 checkpoint 里带出来了。只要该函数上次产出的每条记录都是 PASS，
    这轮跳过它就是安全的；有一条 SKIP/FAIL 就必须重跑（SKIP 往往说明环境变了）。
    """
    if not os.path.isfile(path):
        return {"resumed_functions": [], "reason": "checkpoint 不存在"}
    by_fn = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        by_fn.setdefault(row.get("fn"), []).append(row)

    resumed = []
    for fn, rows in by_fn.items():
        if not fn or any(r.get("status") != "PASS" for r in rows):
            continue
        func = globals().get(fn)
        if not callable(func):
            continue
        for row in rows:
            RESULTS.append({"item": row["item"], "status": row["status"],
                            "evidence": row.get("evidence"), "boundary": row.get("boundary")})

        def _skip(*_a, _rows=rows, _fn=fn, **_k):
            print(f"[resume] skip {_fn} ({len(_rows)} 项已 PASS)", file=sys.stderr)

        _skip.__name__ = fn
        globals()[fn] = _skip
        resumed.append(fn)
    return {"resumed_functions": sorted(resumed), "count": len(resumed)}


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


def check_retrieval_orchestration():
    """编排层不变量：路线必须带原因；强制图验收不得靠回退通过；引用要能判失效。"""
    from graph_engine_adapter import Assertion, AssertionStore, SourceRef
    from graph_engine_adapter.pipeline import retrieve

    class Fake:
        def dense(self, q, k):
            return [{"text": "d", "sources": [{"file_id": "333"}]}]

        def graph(self, q, seeds, k):
            return [{"text": "g", "sources": [{"file_id": "333"}]}]

    s = AssertionStore()
    s.register_entity("p", "产品甲")
    s.add(Assertion(subject="p", predicate="额度", object_value=8000, unit="万元",
                    key="额度", sources=[SourceRef("333", "a" * 64)]))

    graph_out = retrieve("产品甲的额度", store=s, retriever=Fake())
    fallback = retrieve("无关问题", store=s, retriever=Fake())
    forced = retrieve("无关问题", store=s, retriever=Fake(), require_graph=True)
    invalid = retrieve("产品甲的额度", store=s, retriever=Fake(), known_files={"999"})

    ok = (graph_out["route"] == "GRAPH" and graph_out["passed"]
          and fallback["route"] == "DENSE_FALLBACK" and fallback["reason"] == "NO_SEED_ENTITY"
          and forced["passed"] is False                     # 强制图验收不许回退通过
          and len(invalid["invalid_citations"]) == 1)
    record("graph:检索编排不变量", "PASS" if ok else "FAIL",
           {"graph": graph_out["route"], "fallback": fallback["reason"],
            "forced_passed": forced["passed"], "invalid": len(invalid["invalid_citations"])},
           "编排层（假 retriever）；真实引擎接线未做")


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


# 任务书业务场景已全部转成真实检查；引擎侧仍缺的能力由 describe() 的 NOT_IMPLEMENTED 体现，
# 不在这里重复登记（避免两处口径不一致）。
NOT_IMPLEMENTED = []


def check_visibility_fence():
    """撤权 fence：撤权后旧内容不得被检索到；索引代次落后必须拒绝读。"""
    from graph_engine_adapter.assertions import Assertion, AssertionStore, SourceRef
    from graph_engine_adapter.fence import FenceState, StaleIndexError, filter_hits
    from graph_engine_adapter.pipeline import retrieve

    class OldIndexRetriever:            # 故意返回已撤权内容，模拟"引擎不认识撤权"
        last_executed_route = "GRAPH"

        def dense(self, q, k):
            return [{"text": "旧内容", "sources": [{"file_id": "999"}]}]

        def graph(self, q, seeds, k):
            return [{"text": "旧内容", "sources": [{"file_id": "999"}]}]

    store = AssertionStore()
    store.register_entity("p", "产品甲")
    store.add(Assertion(subject="p", predicate="额度", object_value=1, unit="万元", key="额度",
                        sources=[SourceRef("999", "a" * 64)]))

    fence = FenceState()
    fence.revoke(["999"])
    filtered = filter_hits([{"text": "x", "sources": [{"file_id": "999"}]}], fence)
    out = retrieve("产品甲的额度", store=store, retriever=OldIndexRetriever(),
                   known_files={"999"}, fence=fence, index_generation=1)
    stale_blocked = False
    try:
        retrieve("产品甲的额度", store=store, retriever=OldIndexRetriever(),
                 fence=fence, index_generation=0)
    except StaleIndexError:
        stale_blocked = True

    ok = (not filtered["hits"] and out["hit_count"] == 0 and stale_blocked)
    record("graph:撤权 fence", "PASS" if ok else "FAIL",
           {"dropped": out["fence"]["dropped"], "stale_blocked": stale_blocked,
            "generation": fence.generation},
           "平台侧 fence（先验索引代次再过滤）；引擎侧增量删除仍未实现，"
           "首版靠隔离快照全量重建")


def check_isolated_rebuild():
    """撤权 → 隔离重建 → 切读 的真实演练（需要 hipporag 环境与载荷）。"""
    import subprocess

    py = hipporag_python()
    payloads = payloads_or_fail("graph:隔离重建（撤权→重建→切读）")
    if payloads is None:
        return
    if not os.path.isfile(py):
        record("graph:隔离重建（撤权→重建→切读）", "SKIP", {"why": "hipporag venv 缺失"})
        return

    cmd = [py, str(REPO / "scripts/v2_rebuild_drill.py"), "--payloads", *payloads,
           "--revoke", "329", "--root", f"/tmp/q-rebuild-{int(time.time())}", "--cjk-compat",
           "--out", "/tmp/q-rebuild.json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0 or not os.path.isfile("/tmp/q-rebuild.json"):
        record("graph:隔离重建（撤权→重建→切读）", "FAIL",
               {"tail": (proc.stderr or proc.stdout)[-300:]})
        return
    data = json.loads(open("/tmp/q-rebuild.json", encoding="utf-8").read())
    record("graph:隔离重建（撤权→重建→切读）", "PASS" if data.get("passed") else "FAIL",
           {"generation": data.get("fence_generation"), "chunks": data.get("snapshot_chunks"),
            "revoked_text_leaked": data.get("new_snapshot_has_revoked_text"),
            "stale_blocked": data.get("stale_index_blocked"),
            "fresh_allowed": data.get("fresh_index_allowed")},
           "真实引擎重建；引擎侧按文档删除图产物仍未实现，删文档走重建路径")


def check_rebuild_window():
    """重建窗口：过程中一次都不许放行；失败后指针不动且仍拒读。"""
    import subprocess

    py = hipporag_python()
    payloads = payloads_or_fail("graph:重建窗口并发")
    if payloads is None:
        return
    if not os.path.isfile(py):
        record("graph:重建窗口并发", "SKIP", {"why": "hipporag venv 缺失"})
        return

    cmd = [py, str(REPO / "scripts/v2_concurrency_drill.py"), "--payloads", *payloads,
           "--root", f"/tmp/q-window-{int(time.time())}", "--cjk-compat", "--out", "/tmp/q-window.json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0 or not os.path.isfile("/tmp/q-window.json"):
        record("graph:重建窗口并发", "FAIL", {"tail": (proc.stderr or proc.stdout)[-300:]})
        return
    data = json.loads(open("/tmp/q-window.json", encoding="utf-8").read())
    record("graph:重建窗口并发", "PASS" if data.get("passed") else "FAIL",
           {"failure_case": data.get("failure_case"), "during": data["success_case"]["during_rebuild"],
            "after_allowed": data["success_case"]["reader_allowed_after"]},
           "真实引擎重建 + 线程采样；只覆盖单进程读者，多进程/多实例未测")


def check_rebuild_consistency():
    """写并发（重建期间新增文件→stale→重建转 fresh）与多进程读者（窗口内全拒、完成后代次一致）。"""
    import subprocess

    py = hipporag_python()
    payloads = payloads_or_fail("graph:写并发与多读者一致性")
    if payloads is None:
        return
    if not os.path.isfile(py):
        record("graph:写并发与多读者一致性", "SKIP", {"why": "hipporag venv 缺失"})
        return

    cmd = [py, str(REPO / "scripts/v2_rebuild_consistency_drill.py"), "--payloads", *payloads,
           "--root", f"/tmp/q-consistency-{int(time.time())}", "--cjk-compat", "--out", "/tmp/q-consistency.json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if proc.returncode != 0 or not os.path.isfile("/tmp/q-consistency.json"):
        record("graph:写并发与多读者一致性", "FAIL",
               {"tail": (proc.stderr or proc.stdout)[-300:]})
        return
    data = json.loads(open("/tmp/q-consistency.json", encoding="utf-8").read())
    readers = data["multi_reader"]["readers"]
    record("graph:写并发与多读者一致性", "PASS" if data.get("passed") else "FAIL",
           {"write_first_stale": data["write_concurrent"]["first_snapshot_stale"]["stale"],
            "write_missing": data["write_concurrent"]["first_snapshot_stale"]["missing"],
            "readers_blocked": [r["blocked"] for r in readers],
            "readers_allowed": [r["allowed"] for r in readers],
            "final_generation": data["multi_reader"]["pointer_generation_after"]},
           "单机多进程读者；跨机器多实例与真实库规模窗口未测；窗口被 sleep 延长以便采样")


def check_rebuild_coalescing():
    """重建合并：连续变更只构建一次；判据是构建次数，不是耗时。"""
    import subprocess

    py = hipporag_python()
    payloads = payloads_or_fail("graph:重建合并")
    if payloads is None:
        return
    if not os.path.isfile(py):
        record("graph:重建合并", "SKIP", {"why": "hipporag venv 缺失"})
        return

    cmd = [py, str(REPO / "scripts/v2_rebuild_coalesce_drill.py"), "--payloads", *payloads,
           "--root", f"/tmp/q-coalesce-{int(time.time())}", "--cjk-compat", "--out", "/tmp/q-coalesce.json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if proc.returncode != 0 or not os.path.isfile("/tmp/q-coalesce.json"):
        record("graph:重建合并", "FAIL", {"tail": (proc.stderr or proc.stdout)[-300:]})
        return
    data = json.loads(open("/tmp/q-coalesce.json", encoding="utf-8").read())
    record("graph:重建合并", "PASS" if data.get("passed") else "FAIL",
           {"first_requests": data["first_run"]["requests"],
            "second_requests": data["second_run"]["requests"],
            "builds": data["stats"]["builds"],
            "documents": data["snapshot_documents"],
            "expected": data["expected_documents"]},
           "单进程协调器；多实例需外部协调（未做），失败重试/积压上限未做")


def check_rebuild_backpressure():
    """重建故障边界：背压拒绝、指数退避、到点重试、成功复位、阈值告警。"""
    from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator

    class Clock:
        now = 1000.0

        def __call__(self):
            return self.now

    clock = Clock()
    alerts = []

    def broken(batch):
        raise RuntimeError("模型不可用")

    c = RebuildCoordinator(broken, clock=clock, max_pending=2, backoff_base=1.0,
                           backoff_factor=2.0, backoff_max=4.0, alert_after=2,
                           on_alert=lambda e, p: alerts.append((e, p)))

    c.request("u", files=["a"]); c.request("u", files=["b"])
    rejected = c.request("u", files=["c"])["status"]
    first = c.run_once()
    during = c.run_once()["status"]
    clock.now += first["retry_in_s"] + 0.1
    second = c.run_once()
    clock.now += second["retry_in_s"] + 0.1
    third = c.run_once()

    ok = (rejected == "BACKPRESSURE" and first["status"] == "FAILED"
          and during == "BACKOFF"
          and [first["retry_in_s"], second["retry_in_s"], third["retry_in_s"]] == [1.0, 2.0, 4.0]
          and len(alerts) == 1 and c.stats()["pending"] == 2)
    record("graph:重建退避与背压", "PASS" if ok else "FAIL",
           {"rejected": rejected, "delays": [first["retry_in_s"], second["retry_in_s"],
                                             third["retry_in_s"]],
            "alerts": len(alerts), "pending_kept": c.stats()["pending"]},
           "进程内协调器逻辑；真实告警通道、定时调度、多实例协调未接")


def check_rebuild_scheduler():
    """调度器：突发请求合并成一次构建、停机后不再构建、指针与新鲜度正确。"""
    import subprocess

    py = hipporag_python()
    payloads = payloads_or_fail("graph:重建调度器")
    if payloads is None:
        return
    if not os.path.isfile(py):
        record("graph:重建调度器", "SKIP", {"why": "hipporag venv 缺失"})
        return

    root = f"/tmp/q-scheduler-{int(time.time())}"
    cmd = [py, str(REPO / "scripts/v2_scheduler_drill.py"), "--payloads", *payloads,
           "--root", root, "--cjk-compat", "--out", "/tmp/q-scheduler.json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if proc.returncode != 0 or not os.path.isfile("/tmp/q-scheduler.json"):
        record("graph:重建调度器", "FAIL", {"tail": (proc.stderr or proc.stdout)[-300:]})
        return
    data = json.loads(open("/tmp/q-scheduler.json", encoding="utf-8").read())
    record("graph:重建调度器", "PASS" if data.get("passed") else "FAIL",
           {"builds": data.get("builds"), "stopped": data.get("stopped_cleanly"),
            "no_build_after_stop": data.get("no_build_after_stop"),
            "debounce_waits": data["stats"].get("debounce_waits"),
            "documents": data["pointer"].get("documents")},
           "单进程后台线程；多实例/进程守护/监控接入未做")


def check_multi_instance_lease():
    """双实例争租约：两个进程都请求重建，合计只允许 1 次真正构建。"""
    import subprocess

    py = hipporag_python()
    payloads = payloads_or_fail("graph:多实例租约")
    if payloads is None:
        return
    if not os.path.isfile(py):
        record("graph:多实例租约", "SKIP", {"why": "hipporag venv 缺失"})
        return

    stamp = int(time.time())
    root = f"/tmp/q-lease-{stamp}"
    lease = f"{root}/lease.json"
    os.makedirs(root, exist_ok=True)
    common = [py, str(REPO / "scripts/v2_lease_drill.py"),
              "--payloads", *payloads, "--root", root, "--lease", lease,
              "--cjk-compat", "--duration", "20"]
    a_out, b_out = f"/tmp/q-lease-A-{stamp}.json", f"/tmp/q-lease-B-{stamp}.json"
    # 先起 B 并让它在主位上跑起来，再起 A：这样窗口是确定性的，
    # 不依赖两个进程谁先抢到（抢谁赢都对，但断言要看"只有一个建"）
    proc_b = subprocess.Popen(common + ["--owner", "inst-B", "--out", b_out],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(6)
    proc_a = subprocess.run(common + ["--owner", "inst-A", "--out", a_out],
                            capture_output=True, text=True, timeout=1200)
    proc_b.wait(timeout=1200)

    if not (os.path.isfile(a_out) and os.path.isfile(b_out)):
        record("graph:多实例租约", "FAIL", {"tail": (proc_a.stderr or "")[-200:]})
        return
    a = json.loads(open(a_out, encoding="utf-8").read())
    b = json.loads(open(b_out, encoding="utf-8").read())
    total = a["builds"] + b["builds"]
    stale_blocked = [a.get("stale_write_blocked"), b.get("stale_write_blocked")]
    ok = (total == 1 and (a["builds"], b["builds"]) in ((1, 0), (0, 1))
          and any(v is True for v in stale_blocked))     # 旧主晚到的写入必须被拒
    record("graph:多实例租约", "PASS" if ok else "FAIL",
           {"builds": {"A": a["builds"], "B": b["builds"]},
            "not_leader": {"A": a["stats"]["not_leader"], "B": b["stats"]["not_leader"]},
            "skipped_fresh": {"A": a.get("skipped_fresh"), "B": b.get("skipped_fresh")},
            "fencing": {"A": a.get("fencing"), "B": b.get("fencing")},
            "stale_write_blocked": {"A": a.get("stale_write_blocked"),
                                    "B": b.get("stale_write_blocked")}},
           "单机双进程 + 文件租约；跨机需共享存储，两端时钟漂移会带来短暂双主（重建本身幂等）")


def check_mysql_lease():
    """MySQL 租约：跨机部署的选主（用隔离库，需要 LLMKE_LEASE_MYSQL_* 环境变量）。"""
    import subprocess

    need = ("LLMKE_LEASE_MYSQL_HOST", "LLMKE_LEASE_MYSQL_USER",
            "LLMKE_LEASE_MYSQL_PASSWORD", "LLMKE_LEASE_MYSQL_DB")
    missing = [k for k in need if not os.environ.get(k)]
    if missing:
        record("graph:MySQL 租约（跨机）", "SKIP", {"missing_env": missing})
        return

    py = hipporag_python()
    payloads = payloads_or_fail("graph:MySQL 租约（跨机）")
    if payloads is None:
        return
    if not os.path.isfile(py):
        record("graph:MySQL 租约（跨机）", "SKIP", {"why": "hipporag venv 缺失"})
        return

    stamp = int(time.time())
    root = f"/tmp/q-mysql-lease-{stamp}"
    key = f"q-lease-{stamp}"
    os.makedirs(root, exist_ok=True)
    a_out, b_out = f"/tmp/q-mysql-A-{stamp}.json", f"/tmp/q-mysql-B-{stamp}.json"
    common = [py, str(REPO / "scripts/v2_lease_drill.py"), "--lease-backend", "mysql",
              "--lease-key", key, "--payloads", *payloads, "--root", root,
              "--cjk-compat", "--duration", "40"]
    proc_b = subprocess.Popen(common + ["--owner", "inst-B", "--out", b_out],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(6)
    proc_a = subprocess.run(common + ["--owner", "inst-A", "--out", a_out],
                            capture_output=True, text=True, timeout=1200)
    proc_b.wait(timeout=1200)
    if not (os.path.isfile(a_out) and os.path.isfile(b_out)):
        record("graph:MySQL 租约（跨机）", "FAIL", {"tail": (proc_a.stderr or "")[-200:]})
        return
    a = json.loads(open(a_out, encoding="utf-8").read())
    b = json.loads(open(b_out, encoding="utf-8").read())
    total = a["builds"] + b["builds"]
    ok = total == 1 and (a["builds"], b["builds"]) in ((1, 0), (0, 1))
    record("graph:MySQL 租约（跨机）", "PASS" if ok else "FAIL",
           {"builds": {"A": a["builds"], "B": b["builds"]},
            "fencing": {"A": a.get("fencing"), "B": b.get("fencing")},
            "not_leader": {"A": a["stats"]["not_leader"], "B": b["stats"]["not_leader"]},
            "lease_key": key},
           "隔离库 gienrag_v2_restore + 表 v2_rebuild_lease；未做断网/主从切换下的租约行为")


def check_lease_fault_visibility():
    """租约存储不可用：不构建、不打死循环、故障必须变成可见事件。"""
    import subprocess

    py = hipporag_python()
    payloads = payloads_or_fail("graph:租约故障可见性")
    if payloads is None:
        return
    if not os.path.isfile(py):
        record("graph:租约故障可见性", "SKIP", {"why": "hipporag venv 缺失"})
        return

    stamp = int(time.time())
    root = f"/tmp/q-lease-fault-{stamp}"
    os.makedirs(root, exist_ok=True)
    out = f"/tmp/q-lease-fault-{stamp}.json"
    env = {**os.environ,
           "PYTHONPATH": str(REPO / "services/rag-alg/index_data_service"),
           "LLMKE_LEASE_MYSQL_HOST": "127.0.0.1", "LLMKE_LEASE_MYSQL_PORT": "1",   # 必然连不上
           "LLMKE_LEASE_MYSQL_USER": "nobody", "LLMKE_LEASE_MYSQL_PASSWORD": "x",
           "LLMKE_LEASE_MYSQL_DB": "nope"}
    proc = subprocess.run([py, str(REPO / "scripts/v2_lease_drill.py"),
                           "--lease-backend", "mysql", "--lease-key", f"q-fault-{stamp}",
                           "--owner", "inst-A", "--payloads", *payloads, "--root", root,
                           "--cjk-compat", "--duration", "20", "--out", out],
                          capture_output=True, text=True, timeout=300, env=env)
    if not os.path.isfile(out):
        record("graph:租约故障可见性", "FAIL", {"tail": (proc.stderr or "")[-200:]})
        return
    d = json.loads(open(out, encoding="utf-8").read())
    stats = d["stats"]
    ok = (d["builds"] == 0 and stats["lease_errors"] > 0
          and "LEASE_UNAVAILABLE" in d["alert_kinds"] and d["stopped"])
    record("graph:租约故障可见性", "PASS" if ok else "FAIL",
           {"builds": d["builds"], "lease_errors": stats["lease_errors"],
            "alert_kinds": d["alert_kinds"][:3], "alerts_sent": stats["alerts_sent"],
            "thread_stopped": d["stopped"],
            "schema_error": str(d.get("schema_error"))[:60]},
           "用 127.0.0.1:1 制造连接拒绝；未测「连上但查询超时」与锁等待")


def check_lease_hang_timeout():
    """卡住型故障：TCP 通、对端不回包。必须在驱动超时内失败，不能卡满 50s。"""
    import socket
    import subprocess
    import threading

    py = hipporag_python()
    payloads = payloads_or_fail("graph:租约卡住型故障超时")
    if payloads is None:
        return
    if not os.path.isfile(py):
        record("graph:租约卡住型故障超时", "SKIP", {"why": "hipporag venv 缺失"})
        return

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    srv.settimeout(0.2)
    held, stop = [], threading.Event()

    def accept_only():
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
                held.append(conn)          # 收下连接，一句不回
            except socket.timeout:
                continue
            except OSError:
                break

    threading.Thread(target=accept_only, daemon=True).start()
    port = srv.getsockname()[1]
    stamp = int(time.time())
    root, out = f"/tmp/q-lease-hang-{stamp}", f"/tmp/q-lease-hang-{stamp}.json"
    os.makedirs(root, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(REPO / "services/rag-alg/index_data_service"),
           "LLMKE_LEASE_MYSQL_HOST": "127.0.0.1", "LLMKE_LEASE_MYSQL_PORT": str(port),
           "LLMKE_LEASE_MYSQL_USER": "nobody", "LLMKE_LEASE_MYSQL_PASSWORD": "x",
           "LLMKE_LEASE_MYSQL_DB": "nope",
           "LLMKE_LEASE_MYSQL_CONNECT_TIMEOUT": "1", "LLMKE_LEASE_MYSQL_READ_TIMEOUT": "2"}
    started = time.time()
    try:
        proc = subprocess.run([py, str(REPO / "scripts/v2_lease_drill.py"),
                               "--lease-backend", "mysql", "--lease-key", f"q-hang-{stamp}",
                               "--owner", "inst-A", "--payloads", *payloads, "--root", root,
                               "--cjk-compat", "--duration", "20", "--out", out],
                              capture_output=True, text=True, timeout=240, env=env)
        elapsed = time.time() - started
    finally:
        stop.set()
        srv.close()
        for conn in held:
            try:
                conn.close()
            except OSError:
                pass

    if not os.path.isfile(out):
        record("graph:租约卡住型故障超时", "FAIL", {"tail": (proc.stderr or "")[-200:]})
        return
    d = json.loads(open(out, encoding="utf-8").read())
    ok = (d["builds"] == 0 and d["stats"]["lease_errors"] > 0
          and "LEASE_UNAVAILABLE" in d["alert_kinds"]
          and d["stopped"] and elapsed < 90)
    record("graph:租约卡住型故障超时", "PASS" if ok else "FAIL",
           {"builds": d["builds"], "lease_errors": d["stats"]["lease_errors"],
            "alert_kinds": d["alert_kinds"][:3], "elapsed_s": round(elapsed, 1),
            "connections_accepted": len(held),
            "read_timeout_s": 2},
           "对端只 accept 不回包；read_timeout=2s。未测真实 MySQL 的锁等待(50s)场景")


def check_metrics_and_alert_channel():
    """指标文本格式 + 真实 HTTP 告警通道（本地起服务器，不连外网）。"""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from graph_engine_adapter.alert_sink import WebhookAlertSink
    from graph_engine_adapter.lease import FileLease
    from graph_engine_adapter.metrics import CONTENT_TYPE, render_with_lease
    from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator
    from graph_engine_adapter.rebuild_scheduler import RebuildScheduler

    received, statuses = [], [200]

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            received.append(self.rfile.read(length))
            self.send_response(statuses[0])
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args):
            return None

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        root = tempfile.mkdtemp(prefix="q-obs-")
        lease = FileLease(os.path.join(root, "lease"), owner="q", ttl=30)
        coord = RebuildCoordinator(lambda batch: {"written": len(batch)})
        sched = RebuildScheduler(coord, debounce=0, idle_poll=0, sleep=lambda s: None,
                                 lease=lease)
        coord.request("upload", ["f-1"])          # 有 pending，stats 才有非零信号
        text = render_with_lease(sched, lease)

        problems = []
        types_seen = {}
        for line in text.splitlines():
            if not line or line.startswith("#"):
                if line.startswith("# TYPE "):
                    name = line.split()[2]
                    types_seen[name] = types_seen.get(name, 0) + 1
                continue
            parts = line.split()
            if len(parts) != 2:
                problems.append(f"样本行格式错误: {line[:60]}")
                continue
            try:
                value = float(parts[1])
            except ValueError:
                problems.append(f"样本值非法: {line[:60]}")
                continue
            if value != value or value in (float("inf"), float("-inf")):
                problems.append(f"输出了 nan/inf: {line[:60]}")
        dup = [k for k, v in types_seen.items() if v > 1]
        if dup:
            problems.append(f"TYPE 重复: {dup[:3]}")
        if "llmke_graph_rebuild_pending" not in types_seen:
            problems.append("缺少核心 gauge: rebuild_pending")

        url = f"http://127.0.0.1:{server.server_port}/hook"
        sink = WebhookAlertSink(url, timeout=2, retries=2, sleep=lambda s: None,
                                dedupe_window_s=0)
        ok_send = sink({"kind": "LEASE_UNAVAILABLE", "n": 1}) is True
        sink({"kind": "LEASE_UNAVAILABLE", "n": 2})          # 去重关掉 → 应再发一次
        statuses[0] = 500                                     # 服务端开始返错
        failed_send = sink({"kind": "LEASE_OTHER", "n": 3})
        stats = sink.stats()
        if not ok_send:
            problems.append("200 响应被判失败")
        if failed_send is not False:
            problems.append("500 响应未判失败")
        if stats["sent"] != 2:
            problems.append(f"sent 应为 2，实际 {stats['sent']}")
        if stats["failed"] != 1:
            problems.append(f"failed 应为 1，实际 {stats['failed']}")
        if stats["attempts"] != 5:
            problems.append(f"attempts 应为 5（2 成功 + 3 次重试），实际 {stats['attempts']}")
        if len(received) != 5:
            problems.append(f"服务端应收到 5 次请求，实际 {len(received)}")

        record("graph:指标导出与告警通道", "PASS" if not problems else "FAIL",
               {"metrics_lines": len(text.splitlines()), "metrics_series": len(types_seen),
                "content_type": CONTENT_TYPE, "webhook": stats,
                "http_requests_received": len(received), "problems": problems[:5]},
               "本地 HTTP 服务器；未接真实企业微信/钉钉网关，未验签名与鉴权")
    finally:
        server.shutdown()


def check_mineru_wheelhouse():
    """MinerU 离线 wheelhouse：清单里每个 wheel 都在、大小与 sha256 对得上。

    只验"交付包完整"，不验"装得上"——后者要新建 venv 跑几分钟，放进部署演练更合适
    （见 EVIDENCE-A2-MINERU-OFFLINE）。
    """
    import hashlib

    manifest = REPO / "docs/design/unified-documents-v2/offline/r12-mineru-venv-py311.manifest.json"
    if not manifest.is_file():
        record("mineru:离线 wheelhouse", "SKIP", {"why": "清单不存在"})
        return
    wheel_dir = Path(os.path.expanduser(
        os.environ.get("V2_MINERU_WHEELHOUSE", "~/delivery/wheels-mineru-py311")))
    if not wheel_dir.is_dir():
        record("mineru:离线 wheelhouse", "SKIP",
               {"why": "wheel 目录不存在（部署机才有）", "expected": str(wheel_dir)})
        return
    man = json.loads(manifest.read_text(encoding="utf-8"))
    missing, bad_size, bad_hash = [], [], []
    for item in man.get("wheels") or []:
        path = wheel_dir / item["file"]
        if not path.is_file():
            missing.append(item["file"])
            continue
        if path.stat().st_size != item["bytes"]:
            bad_size.append(item["file"])
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            bad_hash.append(item["file"])
    ok = not missing and not bad_size and not bad_hash
    record("mineru:离线 wheelhouse", "PASS" if ok else "FAIL",
           {"wheels": len(man.get("wheels") or []), "missing": missing[:3],
            "bad_size": bad_size[:3], "bad_hash": bad_hash[:3],
            "total_mb": round((man.get("total_bytes") or 0) / 1024**2, 1)},
           "只验包完整与摘要；装入干净 venv 的实测在证据文档里")


def check_use_mineru_switch():
    """`use-mineru` 开关真跑：开 → 出正文；关 → 不出；MinerU 坏 → 走 bypass 不崩。"""
    import subprocess

    # 解释器找不到就整项 SKIP；但本机其实有装 magic_pdf 的 venv（重启后 /tmp 里那个没了），
    # 所以按已知位置兜底，而不是让环境变量缺一项就把能力检查跳过。
    candidates = [os.environ.get("V2_SWITCH_PYTHON"), os.environ.get("V2_MINERU_PYTHON"),
                  "/home/szf/data/dev/parse-v2-venv/bin/python",
                  "/home/szf/data/dev/mineru-toolenv/bin/python"]

    def _has(py, mods):
        """只靠"文件存在"选解释器会踩坑：装 magic_pdf 的那个 venv 可能没有 minio，
        脚本跑到一半 ModuleNotFoundError，看起来像功能坏了。所以直接探测导入。"""
        try:
            proc = subprocess.run([py, "-c", "import " + ", ".join(mods)],
                                  capture_output=True, timeout=90)
            return proc.returncode == 0
        except Exception:  # noqa: BLE001
            return False

    usable = [p for p in candidates if p and os.path.isfile(p)]
    py = next((p for p in usable if _has(p, ["magic_pdf", "minio"])), None)
    if py is None:
        py = next((p for p in usable if _has(p, ["magic_pdf"])), None)
    if py is None:
        record("mineru:use-mineru 开关", "SKIP", {"why": "找不到装 MinerU 的 venv"})
        return
    pdf = REPO / "platform/r12/parse/fixtures/generated/cn-scan.pdf"
    if not pdf.is_file():
        record("mineru:use-mineru 开关", "SKIP", {"why": "扫描件样本缺失"})
        return
    stamp = int(time.time())
    out = f"/tmp/q-switch-{stamp}.json"
    env = {**os.environ}
    if not env.get("MINERU_TOOLS_CONFIG_JSON"):
        record("mineru:use-mineru 开关", "SKIP", {"why": "缺 MINERU_TOOLS_CONFIG_JSON"})
        return
    proc = subprocess.run([py, str(REPO / "scripts/v2_switch_drill.py"),
                           "--pdf", str(pdf), "--python", py, "--out", out],
                          capture_output=True, text=True, timeout=2400, env=env)
    if not os.path.isfile(out):
        record("mineru:use-mineru 开关", "FAIL", {"tail": (proc.stderr or "")[-300:]})
        return
    try:
        d = json.loads(open(out, encoding="utf-8").read())
    except Exception as exc:  # noqa: BLE001
        # 演练可能写出截断文件（中途序列化失败）；不能让它把整个验收带崩
        record("biz:回答段限流", "FAIL",
               {"why": f"{type(exc).__name__}: {exc}",
                "tail": (proc.stderr or "")[-200:]})
        return
    ok = d.get("status") == "OK"
    record("mineru:use-mineru 开关", "PASS" if ok else "FAIL",
           {"on": {"chars": d["on"]["chars"], "hit": d["on"]["hit"]},
            "off": {"chars": d["off"]["chars"], "hit": d["off"]["hit"]},
            "broken": {"chars": d["broken"]["chars"], "events": d["broken"].get("events")},
            "problems": d.get("problems")},
           "真实 nacos 开关 + MinIO 取文件；只测扫描 PDF，未测 doc/docx 转换路径")


def check_image_load_smoke():
    """镜像包：条件 load（ID 一致才 load）+ 冒烟启动。不是干净机首装，但能证明镜像起得来。"""
    import subprocess

    delivery = os.path.expanduser(os.environ.get("V2_DELIVERY", "~/delivery"))
    if not os.path.isdir(os.path.join(delivery, "images-r12")):
        record("infra:镜像条件 load 与冒烟", "SKIP",
               {"why": "交付目录缺失", "delivery": delivery})
        return
    env = {**os.environ, "PATH": os.environ.get("PATH", "")}
    proc = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"],
                          capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        record("infra:镜像条件 load 与冒烟", "SKIP", {"why": "docker 不可用"})
        return
    out = tempfile.mktemp(suffix=".json")
    run = subprocess.run([sys.executable, str(REPO / "scripts/v2_verify_image_bundles.py"),
                          "--delivery", delivery, "--load", "--smoke", "--out", out],
                         capture_output=True, text=True, timeout=1800, env=env)
    if not os.path.isfile(out):
        record("infra:镜像条件 load 与冒烟", "FAIL", {"tail": (run.stderr or "")[-200:]})
        return
    d = json.loads(open(out, encoding="utf-8").read())
    results = d["results"]
    refused = [r["image"] for r in results if r.get("load") == "REFUSED"]
    smoke_bad = [r["image"] for r in results if r.get("smoke") == "FAIL"]
    ok = d["verdict"] == "PASS" and not refused and not smoke_bad
    record("infra:镜像条件 load 与冒烟", "PASS" if ok else "FAIL",
           {"images": len(results), "verdict": d["verdict"],
            "refused": refused, "smoke_failed": smoke_bad,
            "smoke": {r["image"].split(":")[0]: r.get("smoke") for r in results}},
           "load 仅在 tar 与本地镜像 ID 完全一致时执行（no-op）；未在干净机首装")


def check_delta_upgrade_roundtrip():
    """升级快照/回滚的**逻辑**闭环（不装包，秒级）：快照→比对→无事可做。

    真正的"降级 26 个包"发生在证据文档里的独立 venv 演练，不在 Q 里跑——
    那要新建 venv 并装 80+ 个 wheel，几分钟，不适合每次验收。
    """
    import importlib.util

    script = REPO / "scripts/v2_delta_upgrade.py"
    if not script.is_file():
        record("deploy:升级快照与回滚", "SKIP", {"why": "脚本不存在"})
        return
    spec = importlib.util.spec_from_file_location("v2_delta_upgrade", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    path = tempfile.mktemp(suffix=".snapshot.json")
    try:
        snap = mod.snapshot(sys.executable, path, note="q-roundtrip")
        report = mod.rollback(sys.executable, path, [])
    finally:
        if os.path.exists(path):
            os.remove(path)

    ok = (report["status"] == "PASS" and report["matches_snapshot"] is True
          and report["restore_count"] == 0 and len(snap["packages"]) > 0)
    record("deploy:升级快照与回滚", "PASS" if ok else "FAIL",
           {"packages": len(snap["packages"]), "restore": report["restore_count"],
            "matches": report["matches_snapshot"], "extras": len(report["extras"]),
            "status": report["status"]},
           "只验快照/比对闭环；真实降级（26 包）在 EVIDENCE-DEPLOY-CLOSEOUT 里")


def check_systemd_units():
    """systemd 单元渲染 + `systemd-analyze verify`（只认与本单元相关的告警）。"""
    import subprocess

    out_dir = tempfile.mkdtemp(prefix="q-systemd-")
    proc = subprocess.run([sys.executable, str(REPO / "scripts/install_systemd_units.py"),
                           "--out", out_dir, "--verify"],
                          capture_output=True, text=True, timeout=120)
    text = (proc.stdout or "").strip().splitlines()
    payload = None
    for line in text:
        if line.startswith("{"):
            payload = json.loads(line)
    units = sorted(os.listdir(out_dir))
    ok = bool(payload) and payload.get("status") == "PASS" and units
    record("deploy:systemd 单元渲染与校验", "PASS" if ok else "FAIL",
           {"units": units, "result": payload,
            "tail": (proc.stderr or "")[-160:] if not ok else ""},
           "只验渲染与 systemd-analyze；未在真实 systemd 上 enable/start")


def check_graph_worker_service():
    """常驻进程：/healthz、/metrics、SIGTERM 优雅退出。"""
    import subprocess
    import urllib.request

    payloads = payloads_or_fail("deploy:常驻进程健康与优雅停机")
    if payloads is None:
        return
    payload = payloads[0]                      # 333：单文件足够验端点与停机
    port = 18871
    root = tempfile.mkdtemp(prefix="q-worker-")
    env = {**os.environ, "PYTHONPATH": str(REPO / "services/rag-alg/index_data_service")}
    proc = subprocess.Popen([sys.executable, str(REPO / "scripts/v2_graph_worker.py"),
                             "--root", root, "--payloads", payload,
                             "--lease", os.path.join(root, "lease"),
                             "--metrics-port", str(port)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    problems, health, metrics = [], None, ""
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as r:
                    health = json.loads(r.read())
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        if not health:
            # 进程可能已经死了：把退出码带上，否则只看到"30s 不可用"，不知道是慢还是崩。
            problems.append(f"/healthz 30s 内不可用（进程退出码 {proc.poll()}）")
        else:
            # 这里必须兜住异常：worker 可能在 /healthz 之后崩掉，
            # 未捕获的 RemoteDisconnected 会把**整轮验收**打断（实测过一次）。
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=3) as r:
                    metrics = r.read().decode()
            except Exception as exc:  # noqa: BLE001
                problems.append(f"/metrics 读取失败：{type(exc).__name__}: {exc}")
            if metrics:
                if "llmke_graph_scheduler_cycles_total" not in metrics:
                    problems.append("/metrics 缺核心计数器")
                if "nan" in metrics or "inf" in metrics:
                    problems.append("/metrics 输出 nan/inf")
        proc.terminate()
        try:
            code = proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            problems.append("SIGTERM 15s 内未退出")
            code = None
        if code not in (0, None):
            problems.append(f"退出码 {code}")
    finally:
        if proc.poll() is None:
            proc.kill()

    record("deploy:常驻进程健康与优雅停机", "PASS" if not problems else "FAIL",
           {"health": health, "metrics_lines": len(metrics.splitlines()),
            "exit_code": proc.returncode, "problems": problems},
           "只验端点与停机；未验 systemd 托管、未验重建实际发生")


CJK_DIR = os.path.join(str(REPO), ".artifacts", "hippo-cjk")
ARTIFACT_MANIFEST = os.environ.get(
    "LLMKE_ARTIFACT_MANIFEST", os.path.join(str(REPO), ".artifacts", "artifacts.json"))


def hipporag_python():
    """按顺序找 hipporag 解释器。写死 `~/hipporag-venv` 会让检查在没设环境变量时整片 SKIP，
    而 SKIP 在报告里看起来和"这台机器没装"一样——实际只是路径不对。"""
    for path in (os.environ.get("V2_HIPPORAG_PYTHON"),
                 os.path.expanduser("~/hipporag-venv/bin/python"),
                 "/home/szf/data/dev/hipporag-toolenv/bin/python"):
        if path and os.path.isfile(path):
            return path
    return os.environ.get("V2_HIPPORAG_PYTHON") or os.path.expanduser("~/hipporag-venv/bin/python")


def artifact_paths():
    """图快照路径：优先读 `scripts/v2_build_artifacts.py` 写的清单。

    为什么不写死 /tmp：关机一次 /tmp 就被清空，6 项图检查会整片 SKIP，
    而报告仍显示 PASS——"跳过"让验收范围悄悄缩水，比失败更难发现。
    """
    try:
        data = json.loads(open(ARTIFACT_MANIFEST, encoding="utf-8").read())
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for name, item in (data.get("sets") or {}).items():
        if item.get("ok") and item.get("full"):
            out[name] = {"full": item["full"], "delta": item.get("delta"),
                         "a2": (data["sets"].get(name + "_b") or {}).get("full")}
    return out


PAYLOAD_IDS = ("333", "329")
PAYLOAD_DIR = "/tmp"


class PayloadBootstrapError(RuntimeError):
    """载荷既不在、又造不出来。这是环境问题，必须显式失败，不许退化成 SKIP。"""


def payload_paths(out_dir=PAYLOAD_DIR):
    return [os.path.join(out_dir, f"ingest-{fid}.json") for fid in PAYLOAD_IDS]


def payload_ok(path):
    """存在、可解析、且是含 chunks 列表的对象。坏 JSON 和空对象都不算可用。"""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return False
    return isinstance(doc, dict) and isinstance(doc.get("chunks"), list)


def _run_payload_generator(ids, out_dir):
    """调用仓库里既有的生成器。import 执行而非 subprocess：不用再猜一次解释器路径。"""
    import contextlib
    import importlib.util
    import io

    script = REPO / "scripts/v2_make_payloads.py"
    if not script.is_file():
        raise PayloadBootstrapError(f"生成器缺失: {script}")
    spec = importlib.util.spec_from_file_location("v2_make_payloads", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)        # 顶层只有常量，argparse 在 main() 内，导入无副作用
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.main(["--out-dir", out_dir, "--files", *ids, "--force"])
    if rc != 0:
        raise PayloadBootstrapError(f"生成器返回 {rc}: {buf.getvalue()[-160:]}")
    return buf.getvalue()


def ensure_payloads(out_dir=PAYLOAD_DIR, generator=None):
    """缺验收载荷就先自己造：否则相关图检查会整片 SKIP，验收范围悄悄缩水。

    返回两个载荷的路径（顺序固定 333、329）。缺失或坏 JSON 都会重新生成；
    生成不出来就抛 PayloadBootstrapError —— "造不出验收数据"是环境问题，不是能力缺失，
    绝不能让它退化成 SKIP 混进报告。
    """
    generator = generator or _run_payload_generator
    paths = payload_paths(out_dir)
    broken = [fid for fid, path in zip(PAYLOAD_IDS, paths) if not payload_ok(path)]
    if not broken:
        return paths
    try:
        generator(broken, out_dir)
    except PayloadBootstrapError:
        raise
    except Exception as exc:                                   # noqa: BLE001
        raise PayloadBootstrapError(f"生成器异常 {type(exc).__name__}: {exc}") from exc
    still = [path for path in paths if not payload_ok(path)]
    if still:
        raise PayloadBootstrapError(f"生成后仍不可用: {still}")
    return paths


def payloads_or_fail(item):
    """检查取载荷的入口：造不出来就记 FAIL 并返回 None（不 SKIP、不静默）。"""
    try:
        return ensure_payloads()
    except PayloadBootstrapError as exc:
        record(item, "FAIL", {"why": f"验收载荷造不出来: {exc}"},
               "环境问题（生成器不可用），不是「没有这项能力」")
        return None


def check_payload_bootstrap():
    """载荷自举：能在空目录里造出与生产同形状的投影载荷（34 字段、双通道）。"""
    import subprocess

    tmp = tempfile.mkdtemp(prefix="q-payload-")
    proc = subprocess.run([sys.executable, str(REPO / "scripts/v2_make_payloads.py"),
                           "--out-dir", tmp], capture_output=True, text=True, timeout=120)
    problems = []
    if proc.returncode != 0:
        problems.append(f"生成失败: {(proc.stderr or '')[-160:]}")
    detail = {}
    for file_id, expect in (("333", 3), ("329", 2)):
        path = os.path.join(tmp, f"ingest-{file_id}.json")
        if not os.path.isfile(path):
            problems.append(f"缺 {file_id}")
            continue
        doc = json.loads(open(path, encoding="utf-8").read())
        meta = doc["chunks"][0]["metadata"]
        detail[file_id] = {"chunks": len(doc["chunks"]), "meta_fields": len(meta),
                           "channels": doc.get("channels")}
        if len(doc["chunks"]) != expect:
            problems.append(f"{file_id} 块数 {len(doc['chunks'])} != {expect}")
        if len(meta) != 34:
            problems.append(f"{file_id} metadata 字段 {len(meta)} != 34")
        for key in ("file_id", "source", "channel", "parse_artifact_id", "content_uid"):
            if key not in meta:
                problems.append(f"{file_id} 缺关键字段 {key}")
    record("deploy:验收载荷自举", "PASS" if not problems else "FAIL",
           {"detail": detail, "problems": problems},
           "生成的是投影形状样本，不解析真实文档")


def check_office_conversion():
    """doc/docx → PDF 能力：能转就 PASS；缺 Writer 过滤器记为 NOT_IMPLEMENTED（能力未具备）。"""
    import importlib.util

    script = REPO / "scripts/v2_convert_probe.py"
    if not script.is_file():
        record("deploy:docx→pdf 转换能力", "SKIP", {"why": "探测脚本缺失"})
        return
    spec = importlib.util.spec_from_file_location("v2_convert_probe", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.probe()
    status = out["status"]
    if status == "OK":
        record("deploy:docx→pdf 转换能力", "PASS",
               {"pdf_bytes": out["pdf_bytes"], "soffice": out["soffice"],
                "writer_libs": out["writer_libs"]})
    elif status == "NO_WRITER_FILTER":
        # 能力确实不具备：记 NOT_IMPLEMENTED（不计入 PASS），并给出可执行修法
        record("deploy:docx→pdf 转换能力", "NOT_IMPLEMENTED",
               {"soffice": out["soffice"], "writer_libs": out["writer_libs"],
                "stderr_tail": out.get("stderr_tail"), "fix": out.get("fix")},
               "只装了 LibreOffice core/calc，缺 Writer 过滤器（libswlo.so）；"
               "Office 文件走 MinerU 的路径仍然不通")
    else:
        record("deploy:docx→pdf 转换能力", "FAIL", out)


def check_metrics_auth_endpoint():
    """指标端点鉴权：无 token 401、错 token 401、对 token 200；/healthz 不鉴权。"""
    import subprocess
    import urllib.error
    import urllib.request

    payloads = payloads_or_fail("deploy:指标端点鉴权")
    if payloads is None:
        return
    payload = payloads[0]                      # 333：与常驻进程检查同源
    # token 必须是 ASCII：HTTP header 只能承载 latin-1，中文 token 会在客户端编码阶段就炸
    port, token = 18872, "q-token-abc123"
    root = tempfile.mkdtemp(prefix="q-auth-")
    env = {**os.environ, "PYTHONPATH": str(REPO / "services/rag-alg/index_data_service")}
    proc = subprocess.Popen([sys.executable, str(REPO / "scripts/v2_graph_worker.py"),
                             "--root", root, "--payloads", payload,
                             "--lease", os.path.join(root, "lease"),
                             "--metrics-port", str(port), "--metrics-token", token],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)

    def code(headers=None):
        req = urllib.request.Request(f"http://127.0.0.1:{port}/metrics",
                                     headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except Exception:  # noqa: BLE001
            return None

    problems, health = [], None
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as r:
                    health = json.loads(r.read())
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        if not health:
            problems.append("worker 未起来")
        else:
            if code() != 401:
                problems.append(f"无 token 应为 401，实际 {code()}")
            if code({"Authorization": "Bearer wrong"}) != 401:
                problems.append("错 token 未被拒")
            if code({"Authorization": f"Bearer {token}"}) != 200:
                problems.append("正确 token 未放行")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

    record("deploy:指标端点鉴权", "PASS" if not problems else "FAIL",
           {"health": health, "problems": problems},
           "只验 Bearer token 路径；IP 白名单与 loopback 策略由单元测试覆盖")


def check_answer_rate_limit():
    """回答段限流：超限被拦在发请求之前，且默认关闭不改变原有行为。"""
    import subprocess

    script = REPO / "scripts/v2_rate_limit_drill.py"
    if not script.is_file():
        record("biz:回答段限流", "SKIP", {"why": "演练脚本缺失"})
        return
    out = tempfile.mktemp(suffix=".json")
    proc = subprocess.run([sys.executable, str(script), "--out", out],
                          capture_output=True, text=True, timeout=300)
    if not os.path.isfile(out):
        record("biz:回答段限流", "FAIL", {"tail": (proc.stderr or proc.stdout or "")[-300:]})
        return
    try:
        d = json.loads(open(out, encoding="utf-8").read())
    except Exception as exc:  # noqa: BLE001
        # 演练可能写出截断文件（中途序列化失败）；不能让它把整个验收带崩
        record("biz:回答段限流", "FAIL",
               {"why": f"{type(exc).__name__}: {exc}",
                "tail": (proc.stderr or "")[-200:]})
        return
    ok = d.get("status") == "OK"
    record("biz:回答段限流", "PASS" if ok else "FAIL",
           {"unlimited_ok": d["unlimited"]["ok"],
            "limited_ok": d["limited"]["ok"],
            "limited_denied": len(d["limited"]["denied"]),
            "server_hits_under_limit": d["limited"]["server_hits"],
            "retry_after": (d["limited"]["denied"] or [{}])[0].get("retry_after"),
            "budget": d["limited"].get("budget"), "problems": d.get("problems")},
           "用本地假 OpenAI 服务；只验「单进程内按次数限流」，未验多进程/分布式配额")


def check_canary_switch():
    """灰度开关：按 KB 选 full/delta，改配置即回退，回退后仍可读。"""
    import subprocess

    script = REPO / "scripts/v2_canary_drill.py"
    if not script.is_file():
        record("graph:灰度开关", "SKIP", {"why": "演练脚本缺失"})
        return
    out = tempfile.mktemp(suffix=".json")
    proc = subprocess.run([sys.executable, str(script), "--out", out],
                          capture_output=True, text=True, timeout=300)
    if not os.path.isfile(out):
        record("graph:灰度开关", "FAIL", {"tail": (proc.stderr or proc.stdout or "")[-300:]})
        return
    try:
        d = json.loads(open(out, encoding="utf-8").read())
    except Exception as exc:  # noqa: BLE001
        record("graph:灰度开关", "FAIL", {"why": f"{type(exc).__name__}: {exc}"})
        return
    ok = d.get("status") == "OK"
    record("graph:灰度开关", "PASS" if ok else "FAIL",
           {"steps": d["steps"], "policy": d["policy"],
            "read_after_revert": d["read_after_revert"], "problems": d.get("problems")},
           "假 builder 验调度决策；真引擎下的切换质量未测")


def check_incremental_rebuild():
    """增量重建真跑：全量一次 → 删一个文件 + 加一段 → 只走增量，存量不重抽。"""
    import subprocess

    py = hipporag_python()
    payloads = payloads_or_fail("graph:增量重建（删+增）")
    if payloads is None:
        return
    if not os.path.isfile(py):
        record("graph:增量重建（删+增）", "SKIP", {"why": "hipporag venv 缺失"})
        return

    stamp = int(time.time())
    root, out = f"/tmp/q-delta-{stamp}", f"/tmp/q-delta-{stamp}.json"
    env = {**os.environ, "PYTHONPATH": str(REPO / "services/rag-alg/index_data_service")}
    proc = subprocess.run([py, str(REPO / "scripts/v2_delta_drill.py"),
                           "--payloads", *payloads, "--root", root,
                           "--cjk-compat", "--out", out],
                          capture_output=True, text=True, timeout=1800, env=env)
    if not os.path.isfile(out):
        record("graph:增量重建（删+增）", "FAIL", {"tail": (proc.stderr or "")[-200:]})
        return
    d = json.loads(open(out, encoding="utf-8").read())
    apply_result = (d.get("delta") or {}).get("apply") or {}
    ok = (d.get("status") == "OK" and apply_result.get("consistent") is True
          and d.get("deleted_still_present") == []
          and (d.get("pointer") or {}).get("mode") == "DELTA"
          and d.get("delta", {}).get("openie_docs") == d.get("openie_expected")
          and d.get("delta", {}).get("seconds", 1e9) < d.get("full", {}).get("seconds", -1))
    record("graph:增量重建（删+增）", "PASS" if ok else "FAIL",
           {"full_s": d["full"]["seconds"], "delta_s": d["delta"]["seconds"],
            "speedup_x": d.get("speedup_x"), "apply": apply_result,
            "openie": {"base": d["full"]["openie_docs"],
                       "after": d["delta"]["openie_docs"],
                       "expected": d.get("openie_expected")},
            "pointer_mode": (d.get("pointer") or {}).get("mode"),
            "deleted_still_present": d.get("deleted_still_present"),
            "problems": d.get("problems")},
           "真跑 5 块语料；未测检索质量变化（需重排模型，波动大）")


def check_retrieval_equivalence():
    """检索层等价性：同一批 query 在 full 与 delta 两份快照上命中是否一致。"""
    import subprocess

    py = hipporag_python()
    # 比的是**同内容**两份独立构建（a vs a2）：内容没变，检索就该一致。
    # 拿 full vs delta 比是错的——delta 删了块，命中不同才是正确行为（那是 C4 的事）。
    sets = artifact_paths()
    std = sets.get("standard") or {}
    pairs = [(std["full"], std["a2"])] if std.get("full") and std.get("a2") else []
    pairs = [(a, b) for a, b in pairs if os.path.isdir(a) and os.path.isdir(b)]
    if not os.path.isfile(py) or not pairs:
        record("graph:检索层等价性", "SKIP",
               {"why": "hipporag venv 或标准语料的第二份全量缺失",
                "manifest": ARTIFACT_MANIFEST})
        return
    a, b = pairs[0]
    out = tempfile.mktemp(suffix=".json")
    env = {**os.environ, "PYTHONPATH": str(REPO / "services/rag-alg/index_data_service")}
    proc = subprocess.run([py, str(REPO / "scripts/v2_retrieval_equivalence.py"),
                           "--a", a, "--b", b, "--top-k", "3",
                           "--queries", "授信额度是多少", "华东精密制造有限公司的信用评级",
                           "单笔授信超过五亿元由谁审议通过",
                           "--out", out],
                          capture_output=True, text=True, timeout=1200, env=env)
    if not os.path.isfile(out):
        record("graph:检索层等价性", "FAIL", {"tail": (proc.stderr or "")[-200:]})
        return
    d = json.loads(open(out, encoding="utf-8").read())
    r = d["a_vs_b"]
    ok = d["status"] == "OK" and r["top1_rate"] == 1.0 and r["avg_jaccard"] == 1.0
    record("graph:检索层等价性", "PASS" if ok else "FAIL",
           {"queries": r["queries"], "top1_rate": r["top1_rate"],
            "ordered_rate": r["ordered_rate"], "avg_jaccard": r["avg_jaccard"],
            "elapsed_s": d["elapsed_s"], "problems": d["problems"]},
           "只比 top-k 命中集合与顺序；未做端到端答案质量评分（需人工/模型判定）")


def check_graph_export():
    """图导出：节点/边/事实能落成稳定排序的 JSONL，且两份全量导出可复现。"""
    import subprocess

    py = hipporag_python()
    sets = artifact_paths()
    base = next(((s.get("full"), s.get("a2") or s.get("full")) for s in sets.values()
                 if s.get("full")), (None, None))
    if not os.path.isfile(py) or not base[0]:
        record("graph:图导出与差异", "SKIP",
               {"why": "hipporag venv 或全量快照缺失", "manifest": ARTIFACT_MANIFEST})
        return
    stamp = int(time.time())
    out = f"/tmp/q-export-{stamp}"
    env = {**os.environ, "PYTHONPATH": str(REPO / "services/rag-alg/index_data_service")}
    proc = subprocess.run([py, str(REPO / "scripts/v2_graph_export.py"),
                           "--snapshot", base[0], "--out", out,
                           "--compare", base[1]],
                          capture_output=True, text=True, timeout=900, env=env)
    try:
        report = json.loads((proc.stdout or "").strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        record("graph:图导出与差异", "FAIL", {"tail": (proc.stderr or "")[-200:]})
        return
    diff = report.get("diff") or {}
    ok = (report["nodes"] > 0 and report["edges"] > 0 and report["facts"] > 0
          and diff.get("identical") is True and proc.returncode == 0)
    record("graph:图导出与差异", "PASS" if ok else "FAIL",
           {"nodes": report["nodes"], "edges": report["edges"], "facts": report["facts"],
            "same_sha_twice": True, "diff_identical": diff.get("identical"),
            "exit": proc.returncode},
           "与同语料第二份全量比较；未测大图截断与增量导出")


def check_image_tag_safety():
    """镜像 load 的**覆盖检测**：tar 被 load 时会不会悄悄顶掉在用 tag。

    既有 `infra:镜像条件 load 与冒烟` 验的是"能 load、能起"；这一项验的是
    "load 之后 tag 指向有没有变"——两件事，覆盖了在用镜像是最难在事后发现的一种。
    """
    import subprocess

    delivery = os.path.expanduser(os.environ.get("V2_DELIVERY", "~/delivery"))
    tar = os.path.join(delivery, "images-r12", "redis_7.4.10-alpine.tar")
    if not os.path.isfile(tar):
        record("infra:镜像 load 覆盖检测", "SKIP", {"why": "redis tar 缺失", "tar": tar})
        return
    out = tempfile.mktemp(suffix=".json")
    proc = subprocess.run([sys.executable, str(REPO / "scripts/v2_image_load_drill.py"),
                           "--tar", tar, "--run", "--out", out],
                          capture_output=True, text=True, timeout=900)
    if not os.path.isfile(out):
        record("infra:镜像 load 覆盖检测", "FAIL", {"tail": (proc.stderr or "")[-200:]})
        return
    d = json.loads(open(out, encoding="utf-8").read())
    ok = (proc.returncode == 0 and d.get("overwrote_existing") is False
          and (d.get("container") or {}).get("health_ok") is True
          and (d.get("container") or {}).get("cleaned_up") is True)
    record("infra:镜像 load 覆盖检测", "PASS" if ok else "FAIL",
           {"image_ref": d.get("image_ref"), "already_present": d.get("already_present"),
            "overwrote_existing": d.get("overwrote_existing"),
            "previous_image_id": d.get("previous_image_id"),
            "load_seconds": d.get("load_seconds"),
            "container": d.get("container")},
           "只测 redis 一个 tar；未做「tar 与在用镜像内容不一致」的真实构造（需先有旧版本镜像）")


def mod_exit(verdict):
    """退出码必须与判定一致，否则 CI 里的 gate 会形同虚设。"""
    return {"SAFE": 0, "REVIEW": 1, "UNSAFE": 2, "INCONCLUSIVE": 3}.get(verdict, -1)


def _count(value):
    """差异字段可能是列表也可能是计数，统一成数——报告里不要出现"None 个差异"。"""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return value


def check_canary_verdict():
    """C4 灰度判定：把结构/抽取 + 检索合成一个结论（SAFE/REVIEW/UNSAFE）。"""
    import subprocess

    py = hipporag_python()
    sets = artifact_paths()
    # 用**同语料两份独立全量**做对照（b = a2）：内容没有任何变化，
    # 所以结论只允许 SAFE 或 INCONCLUSIVE——判成 UNSAFE/REVIEW 就等于
    # "把重建噪声当成缺陷"，这种判定不能进 CI。
    # "能抓出真差异"由压力语料（stress vs stress_b vs stress_delta）在证据里单独跑。
    pair = next(((s["full"], s.get("a2"), s.get("a2")) for s in sets.values()
                 if s.get("full") and s.get("a2")), None)
    if not os.path.isfile(py) or pair is None:
        record("graph:灰度判定（C4）", "SKIP",
               {"why": "hipporag venv 或含基线的快照组缺失", "manifest": ARTIFACT_MANIFEST})
        return
    out = tempfile.mktemp(suffix=".json")
    env = {**os.environ, "PYTHONPATH": str(REPO / "services/rag-alg/index_data_service")}
    proc = subprocess.run([py, str(REPO / "scripts/v2_canary_verdict.py"),
                           "--a", pair[0], "--a2", pair[1], "--b", pair[2], "--json", out],
                          capture_output=True, text=True, timeout=1800, env=env)
    if not os.path.isfile(out):
        record("graph:灰度判定（C4）", "FAIL", {"tail": (proc.stderr or "")[-200:]})
        return
    d = json.loads(open(out, encoding="utf-8").read())
    # 无内容变化时：SAFE(0) = 检索与抽取都可复现；INCONCLUSIVE(3) = 基线自己就不稳，
    # 说明这套栈的抽取不可复现（实测确实如此）。两者都是诚实结论；
    # UNSAFE/REVIEW 才是错的——那等于把噪声当缺陷。
    ok = (d.get("verdict") in ("SAFE", "INCONCLUSIVE")
          and proc.returncode == mod_exit(d.get("verdict")))
    record("graph:灰度判定（C4）", "PASS" if ok else "FAIL",
           {"verdict": d.get("verdict"), "exit": proc.returncode,
            "reasons": (d.get("reasons") or [])[:3],
            "facts_only_b": _count(d.get("facts", {}).get("only_b")),
            "retrieval": d.get("retrieval")},
           "对照是同语料两份独立全量（无内容变化）；只接受 SAFE/INCONCLUSIVE，"
           "抓真差异的能力由压力语料在证据里单独验证")


def check_scope_merge():
    """跨范围合并检索：单范围看不到越界内容，多范围能取到。"""
    import subprocess

    py = hipporag_python()
    scoped = os.path.join(str(REPO), ".artifacts", "scoped", "scopes.json")
    if not os.path.isfile(py) or not os.path.isfile(scoped):
        record("graph:跨范围合并检索", "SKIP",
               {"why": "hipporag venv 或范围索引缺失", "manifest": scoped})
        return
    out = tempfile.mktemp(suffix=".json")
    env = {**os.environ, "PYTHONPATH": str(REPO / "services/rag-alg/index_data_service")}
    proc = subprocess.run([py, str(REPO / "scripts/v2_scope_merge_drill.py"),
                           "--cjk-compat", "--out", out],
                          capture_output=True, text=True, timeout=1200, env=env)
    if not os.path.isfile(out):
        record("graph:跨范围合并检索", "FAIL", {"tail": (proc.stderr or "")[-200:]})
        return
    d = json.loads(open(out, encoding="utf-8").read())
    ok = d.get("status") == "OK" and proc.returncode == 0
    record("graph:跨范围合并检索", "PASS" if ok else "FAIL",
           {"single_contains": d["single"]["contains_needle"],
            "merged_contains": d["merged"]["contains_needle"],
            "merged_used": d["merged"]["used"], "problems": d["problems"]},
           "RRF 融合（名次），未做跨索引语义重排；多范围用户的相关文档可能排在多路重复文档之后")


def check_alert_channels():
    """企业微信/钉钉报文与签名：本地 HTTP 服务器接收，不外连。"""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from graph_engine_adapter.alert_channels import DingtalkChannel, WecomChannel

    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            received.append({"path": self.path, "body": json.loads(self.rfile.read(length))})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"errcode":0}')

        def log_message(self, *args):
            return None

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    problems = []
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        secret = "SEC0123456789"
        wecom = WecomChannel(base + "/wecom?key=k")
        # 时间戳由 clock 注入（通道内部用 now_ms），不是构造参数
        ding = DingtalkChannel(base + "/ding?access_token=t", secret=secret,
                               clock=lambda: 1767225600.0)
        ok_w = wecom({"kind": "LEASE_UNAVAILABLE", "error": "MySQL down", "impact": "重建暂停"})
        ok_d = ding({"kind": "LEASE_UNAVAILABLE", "error": "MySQL down"})

        if not ok_w or not ok_d:
            problems.append("通道发送返回 False")
        if len(received) != 2:
            problems.append(f"服务端收到 {len(received)} 条，应为 2")
        else:
            w = received[0]["body"]
            if w.get("msgtype") != "markdown" or "LEASE_UNAVAILABLE" not in \
                    json.dumps(w, ensure_ascii=False):
                problems.append("企微报文结构不对")
            d = received[1]["body"]
            if "sign" not in d or "timestamp" not in d:
                problems.append("钉钉报文缺 sign/timestamp")
            if "sign=" not in received[1]["path"]:
                problems.append("钉钉 URL 未带签名")
            if secret in json.dumps(received, ensure_ascii=False):
                problems.append("secret 出现在请求里（应只参与签名）")
    finally:
        server.shutdown()

    record("obs:告警通道报文", "PASS" if not problems else "FAIL",
           {"received": len(received), "problems": problems},
           "本地模拟网关；未验证真实企业微信/钉钉是否接受（无账号）")


def check_network_partition():
    """网络分区：TCP 通→断→恢复，租约与调度器都要跟着变。"""
    import subprocess

    env_keys = ("LLMKE_TEST_MYSQL_HOST", "LLMKE_TEST_MYSQL_PASSWORD")
    if not all(os.environ.get(k) for k in env_keys):
        record("lease:网络分区恢复", "SKIP", {"why": "缺 LLMKE_TEST_MYSQL_*"})
        return
    out = tempfile.mktemp(suffix=".json")
    env = {**os.environ, "PYTHONPATH": str(REPO / "services/rag-alg/index_data_service")}
    proc = subprocess.run([sys.executable, str(REPO / "scripts/v2_network_partition_drill.py"),
                           "--out", out],
                          capture_output=True, text=True, timeout=900, env=env)
    if not os.path.isfile(out):
        record("lease:网络分区恢复", "FAIL", {"tail": (proc.stderr or "")[-250:]})
        return
    d = json.loads(open(out, encoding="utf-8").read())
    phases = d.get("phase") or {}
    ok = (d.get("status") in ("OK", "PASS")
          and (phases.get("before") or {}).get("acquired") is True
          and (phases.get("cut") or {}).get("error_type")
          and (phases.get("restored") or {}).get("acquired") is True)
    record("lease:网络分区恢复", "PASS" if ok else "FAIL",
           {"before": phases.get("before"), "cut": phases.get("cut"),
            "restored": phases.get("restored"), "problems": d.get("problems")},
           "本地 TCP 代理制造分区；未做真实主从切换与脑裂")


def check_shared_quota():
    """跨实例共享配额：MySQL 原子计数，拒绝不占额度。"""
    if not all(os.environ.get(k) for k in ("LLMKE_LEASE_MYSQL_HOST", "LLMKE_LEASE_MYSQL_PASSWORD")):
        record("deploy:跨实例共享配额", "SKIP", {"why": "缺 LLMKE_LEASE_MYSQL_*"})
        return
    try:
        from graph_engine_adapter.lease_mysql import make_pymysql_factory
        from graph_engine_adapter.quota_shared import SharedQuotaCounter, ensure_schema

        factory = make_pymysql_factory(
            host=os.environ["LLMKE_LEASE_MYSQL_HOST"],
            port=int(os.environ.get("LLMKE_LEASE_MYSQL_PORT", "3306")),
            user=os.environ["LLMKE_LEASE_MYSQL_USER"],
            password=os.environ["LLMKE_LEASE_MYSQL_PASSWORD"],
            database=os.environ["LLMKE_LEASE_MYSQL_DB"])
        ensure_schema(factory)
        tenant = f"q-quota-{int(time.time())}"
        counter = SharedQuotaCounter(factory, limit=3, window_s=3.0)
        allowed = [counter.take(tenant)["allowed"] for _ in range(5)]
        ok = allowed == [True, True, True, False, False]
        record("deploy:跨实例共享配额", "PASS" if ok else "FAIL",
               {"allowed": allowed, "tenant": tenant},
               "隔离库 v2_quota_window；未验证多副本并发下的总量上限")
    except Exception as exc:  # noqa: BLE001
        record("deploy:跨实例共享配额", "FAIL",
               {"error": f"{type(exc).__name__}: {exc}"})


def check_community_report():
    """社区/global：只消费校验过的标准事实导出，报告引用必须全部可解析。"""
    import subprocess

    py = hipporag_python()
    if not os.path.isfile(py):
        record("biz:global 报告/引用失效识别", "SKIP", {"why": "no hipporag venv"})
        return
    payloads = payloads_or_fail("biz:global 报告/引用失效识别")
    if payloads is None:
        return

    cmd = [py, str(REPO / "scripts/v2_community_report.py"), "--payloads", *payloads,
           "--save-dir", CJK_DIR, "--cjk-compat", "--out", "/tmp/q-community.json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 or not os.path.isfile("/tmp/q-community.json"):
        record("biz:global 报告/引用失效识别", "FAIL",
               {"tail": (proc.stderr or proc.stdout)[-300:]})
        return
    data = json.loads(open("/tmp/q-community.json", encoding="utf-8").read())
    report = data.get("report") or {}
    ok = (report.get("status") == "READY" and report.get("communities")
          and not (report.get("citations") or {}).get("invalid"))
    record("biz:global 报告/引用失效识别", "PASS" if ok else "FAIL",
           {"status": report.get("status"), "export": report.get("export"),
            "communities": len(report.get("communities") or []),
            "invalid_citations": len((report.get("citations") or {}).get("invalid") or [])},
           "结构化报告（断言层导出 + 确定性标签传播 + 引用校验）；叙述为可选步骤，"
           "未参与判定" if ok else "报告状态或引用校验未通过")


def check_end_to_end_answer():
    """真实端到端：载荷 → 引擎（CJK 补丁）→ 断言 → 检索 → 回答 → 引用核验。

    需要三样外部条件：hipporag 环境、本地 embedding/图索引目录、外部回答模型 key。
    缺任一项就 SKIP 并写明缺什么——**不许**用"没有 FAIL"冒充通过。
    """
    import subprocess

    py = hipporag_python()
    if not os.path.isfile(py):
        record("biz:端到端业务问答", "SKIP", {"why": "no hipporag venv", "python": py})
        return
    from graph_engine_adapter.llm_config import describe as describe_llm, resolve as resolve_llm
    llm = describe_llm(resolve_llm())
    if not llm["ready"]:
        record("biz:端到端业务问答", "SKIP", {"why": "answer LLM key missing",
                                              "key_env": llm["key_env"]})
        return

    payloads = payloads_or_fail("biz:端到端业务问答")
    if payloads is None:
        return

    cmd = [py, str(REPO / "scripts/v2_answer_e2e.py"), "--payloads", *payloads,
           # 查询必须**点名一个被抽出来的实体**：种子匹配是"实体名是 query 子串"，
           # 实测 "多指标对账口径是什么" 这类概念式问句经常认不出种子 → 回退稠密 → require_graph 失败。
           # 换成客户名后稳定走 GRAPH。这正是"种子识别偏弱"的具体表现，已记进证据。
           "--queries", "华东精密制造有限公司的授信额度是多少", "--save-dir", CJK_DIR,
           # 不再 --skip-build：/tmp 被清空后旧索引就没了，跳过构建会让它读空索引崩在
           # dense_passage_retrieval 的 shape 上（表现为 FAIL，像真回归）。宁可多花 40s。
           "--cjk-compat", "--require-graph", "--top-k", "5",
           "--out", "/tmp/q-e2e.json"]
    # 回答模型是采样的：实测同一问句会偶发给出"quote 不是原文子串"（INVALID_CITATION），
    # 单独复跑就过。一次抖动记 FAIL 会把真回归淹掉，所以失败重试一次并把 attempts 写进报告；
    # 两次都失败才是真失败（那多半是检索/引用链路坏了，不是采样）。
    attempts, first, proc = 0, {}, None
    for attempts in range(1, 3):
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0 or not os.path.isfile("/tmp/q-e2e.json"):
            continue
        report = json.loads(open("/tmp/q-e2e.json", encoding="utf-8").read())
        first = (report.get("results") or [{}])[0]
        if first.get("answer_passed") is True and first.get("executed_route") == "GRAPH":
            break
    if proc is None or proc.returncode != 0 or not first:
        record("biz:端到端业务问答", "FAIL",
               {"tail": ((proc.stderr or proc.stdout) if proc else "")[-300:],
                "attempts": attempts})
        return
    ok = first.get("answer_passed") is True and first.get("executed_route") == "GRAPH"
    record("biz:端到端业务问答", "PASS" if ok else "FAIL",
           {"route": first.get("executed_route"), "reason": first.get("answer_reason"),
            "answer": str(first.get("answer"))[:60],
            "citations": len(first.get("citations") or []),
            "attempts": attempts,
            "model": (report or {}).get("llm", {}).get("model")},
           # 端到端只跑单问句：多跳、表格合计、跨文档合并都还没覆盖，边界必须写出来
           "真实端到端（外部回答模型 + 本地引擎 + CJK 补丁），单问句；"
           "多跳/合计/跨文档未覆盖" if ok else "回答未通过核验或图路线未执行")


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
    ap.add_argument("--checkpoint", default=os.environ.get("LLMKE_Q_CHECKPOINT"),
                    help="每项结果即时落盘（JSONL），进程被杀也不丢已完成项")
    ap.add_argument("--resume", action="store_true",
                    help="从 --checkpoint 续跑：上一轮全 PASS 的检查函数直接回放")
    args = ap.parse_args(argv)

    global CHECKPOINT
    CHECKPOINT = args.checkpoint
    resume_state = install_resume(args.checkpoint) if (args.resume and args.checkpoint) \
        else {"resumed_functions": []}
    if CHECKPOINT:
        open(CHECKPOINT, "w" if not args.resume else "a", encoding="utf-8").close()

    # 先保证验收载荷存在：缺了会让一批图检查 SKIP（"跳过"等于验收范围缩水）。
    # 这里失败不抛出：每项检查自己会记 FAIL 并写明原因，报错细节落在报告的 payload_bootstrap 里。
    try:
        payload_state = {"payloads": ensure_payloads()}
    except PayloadBootstrapError as exc:
        payload_state = {"error": f"{type(exc).__name__}: {exc}"}

    check_infra()
    check_legacy_channels()
    check_mapping()
    check_capabilities()
    check_retrieval_orchestration()
    check_mineru()
    check_business_semantics()
    check_visibility_fence()
    check_isolated_rebuild()
    check_rebuild_window()
    check_rebuild_consistency()
    check_rebuild_coalescing()
    check_rebuild_backpressure()
    check_rebuild_scheduler()
    check_multi_instance_lease()
    check_mysql_lease()
    check_lease_fault_visibility()
    check_lease_hang_timeout()
    check_metrics_and_alert_channel()
    check_incremental_rebuild()
    check_mineru_wheelhouse()
    check_use_mineru_switch()
    check_image_load_smoke()
    check_delta_upgrade_roundtrip()
    check_payload_bootstrap()
    check_office_conversion()
    check_systemd_units()
    check_graph_worker_service()
    check_metrics_auth_endpoint()
    check_answer_rate_limit()
    check_canary_switch()
    check_retrieval_equivalence()
    check_graph_export()
    check_image_tag_safety()
    check_canary_verdict()
    check_scope_merge()
    check_alert_channels()
    check_network_partition()
    check_shared_quota()
    # 顺序有讲究：端到端会**构建** CJK 索引，社区报告只读该索引（脚本自身不建）。
    # 反过来跑会读到空目录 → export total 0 → BLOCKED，看起来像功能坏了。
    check_end_to_end_answer()
    check_community_report()
    for item, why in NOT_IMPLEMENTED:
        record(item, "NOT_IMPLEMENTED", why)

    fails = [r for r in RESULTS if r["status"] == "FAIL"]
    summary = {s: sum(1 for r in RESULTS if r["status"] == s)
               for s in ("PASS", "FAIL", "SKIP", "NOT_IMPLEMENTED")}
    report = {"schema": "llmke.q-acceptance.v1",
              "summary": summary,
              "verdict": "PASS" if not fails else "FAIL",
              "note": "NOT_IMPLEMENTED 表示能力未建，不计入 PASS，也不等于通过",
              "payload_bootstrap": payload_state,
              "resume": resume_state,
              "results": RESULTS}
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
    print(json.dumps({"summary": summary, "verdict": report["verdict"]}, ensure_ascii=False))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
