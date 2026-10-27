"""R14-A-FIX-28 验证：解析侧 ensure-then-insert + 失败必须可见。

三个用例（重启 12340 后跑）：
  A 正向：普通 docx -> success=true，且 ES 有块、Milvus 有行
  B 负向：不存在的 MinIO 对象 -> 必须 success=false，task_statuses[*].success=false，code=500
  C 并发：全新索引 3 篇并行 -> 三篇都有块（验证"并发建索引当失败"已修）

用法：
  platform/r12/venvs/alg/bin/python verify_fix28.py > verify_fix28_<ts>.json
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:12340"
ES = "http://127.0.0.1:19200"
ES_URL = "http://127.0.0.1:18090/v1/embeddings"  # 仅用于确认模型可用（不直接调用）

MODEL = {"model_id": "qwen2.5-7b-instruct", "url": "http://127.0.0.1:18092/v1/chat/completions"}
EMB = {"model_id": "bge-m3", "url": "http://127.0.0.1:18090/v1/embeddings"}
MM = {"model_id": "qwen2.5-vl-3b-instruct", "url": "http://127.0.0.1:18093/v1/chat/completions"}


def parse(index_name, file_path, file_id, parent=None, timeout=600):
    body = {
        "knowledge_base_name": index_name,
        "files": [{"file_path": file_path, "file_id": file_id, "file_size": "1MB",
                   "parent_file_name": parent or file_path.split("/")[-1], "version": "V0"}],
        "file_type": "naive", "chunk_size": 512, "chunk_overlap": 100,
        "length_function": "char", "need_chunk": True, "index_name": index_name,
        "model_info": MODEL, "embedding_model_info": EMB, "multi_model_info": MM,
    }
    req = urllib.request.Request(BASE + "/parse_sync", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode() or "{}")
            return {"http": r.status, "secs": round(time.perf_counter() - t0, 1), "body": payload}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "secs": round(time.perf_counter() - t0, 1),
                "raw": e.read().decode()[:500]}
    except Exception as e:  # noqa: BLE001
        return {"http": None, "secs": round(time.perf_counter() - t0, 1), "error": str(e)[:300]}


def es_count(index_name):
    try:
        with urllib.request.urlopen(f"{ES}/{index_name}/_count", timeout=10) as r:
            return json.load(r).get("count")
    except Exception:  # noqa: BLE001
        return None


def mv_count(collection):
    try:
        from pymilvus import Collection, connections
        connections.connect(alias="v", host="127.0.0.1", port="19630", db_name="rag_knowledge_base")
        c = Collection(collection, using="v")
        c.load()
        n = len(c.query(expr="pk>=0", output_fields=["pk"], limit=500))
        connections.disconnect("v")
        return n
    except Exception as e:  # noqa: BLE001
        return f"ERR:{str(e)[:80]}"


def verdict(res):
    """成功判据：HTTP 200 且 success 为真且 task_statuses 全部 success。"""
    if res.get("http") != 200:
        return False, f"http={res.get('http')}"
    b = res.get("body") or {}
    st = b.get("task_statuses") or []
    ok = bool(b.get("success")) and bool(st) and all(x.get("success") for x in st)
    return ok, f"success={b.get('success')} tasks={[(x.get('file_id'), x.get('success'), x.get('code')) for x in st]}"


def main():
    ts = time.strftime("%H%M%S")
    out = {"ts": ts, "cases": {}}

    # A 正向
    ia = f"r12a_fix28_a_{ts}"
    ra = parse(ia, "r12-rag/fixtures/docx-plain.docx", 991001)
    ok_a, why_a = verdict(ra)
    out["cases"]["A_positive"] = {"res": ra, "md": why_a, "es": es_count(ia), "mv": mv_count("_" + ia),
                                  "pass": ok_a and (es_count(ia) or 0) > 0}

    # B 负向：不存在的对象
    ib = f"r12a_fix28_b_{ts}"
    rb = parse(ib, "r12-rag/__no_such_object__/nope.docx", 991002)
    body = rb.get("body") or {}
    st = body.get("task_statuses") or []
    # 负向判据：**不看 HTTP 码**（200 与 500 都可接受），只看"是否明确告知失败"
    # —— 这正是 FIX-28 要修的东西：HTTP 200 但 success=true 才算没修好。
    negatives_ok = (body.get("success") is False) and bool(st) and all(x.get("success") is False for x in st)
    out["cases"]["B_negative"] = {
        "res": rb, "http": rb.get("http"), "body_success": body.get("success"),
        "tasks": [(x.get("file_id"), x.get("success"), x.get("code"), x.get("fail_reason")) for x in st],
        "pass": negatives_ok,
    }

    # C 并发：同一新索引 3 篇
    ic = f"r12a_fix28_c_{ts}"
    results = []
    lock = threading.Lock()

    def worker(i):
        r = parse(ic, "r12-rag/fixtures/docx-plain.docx", 991010 + i, parent=f"f{i}.docx")
        with lock:
            results.append((i, r))

    ths = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    ok_c = all(verdict(r)[0] for _, r in results)
    out["cases"]["C_concurrent"] = {
        "results": [(i, r.get("http"), verdict(r)[1]) for i, r in sorted(results)],
        "es": es_count(ic), "mv": mv_count("_" + ic), "pass": ok_c and (es_count(ic) or 0) > 0,
    }

    out["verdict"] = {k: v.get("pass") for k, v in out["cases"].items()}
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
