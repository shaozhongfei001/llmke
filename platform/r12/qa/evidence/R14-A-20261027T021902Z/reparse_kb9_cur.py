"""R14-A-FIX-18 收尾：只重解析 kb_9 的**当前代次**文件，并校验 table 索引归一。

与上一版（reparse_kb9_full.py，误把 273 行历史记录全跑）的区别：
  - 文件清单显式给死（当前代次 8 个文件 / 9 行），不再按 kb_id 全表扫；
  - 台账 fid=329 的 converted_file_path 是 `.md`，解析服务不支持 → 改用原始 xlsx 路径，
    以便 table_chunks/table_summary 的 file_id 归一到 329（当前是旧行 314）；
  - 通过判定只看 task_statuses（HTTP 200 + success=false 算失败）。

用法：venvs/alg/bin/python reparse_kb9_cur.py <tag>
输出：reparse_kb9_cur_<tag>.json
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

TAG = sys.argv[1] if len(sys.argv) > 1 else "seed18"
MYSQL = ["docker", "exec", "r12-mysql", "mysql", "-uroot", "-pR12r00t#2026local", "-N", "-e"]
BASE = "http://127.0.0.1:12340"
ES = "http://127.0.0.1:19200"
KB = "kb_9"
END_POINT = "http://127.0.0.1:19000/"

# 当前代次（V0/V1 并存的两组都保留在索引里；图侧只抽有效版本，见 A-IDENTITY.md）
CURRENT = [290, 328, 329, 330, 331, 332, 333, 334, 343]
# 这些行 converted 是 .md，必须退回原始文件路径
RAW_PATH_FALLBACK = {329}

MODEL = {"model_id": "qwen2.5-7b-instruct", "url": "http://127.0.0.1:18092/v1/chat/completions"}
EMB = {"model_id": "bge-m3", "url": "http://127.0.0.1:18090/v1/embeddings"}
MM = {"model_id": "qwen2.5-vl-3b-instruct", "url": "http://127.0.0.1:18093/v1/chat/completions"}


def sql(q):
    r = subprocess.run(MYSQL + [q], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:200])
    return [line.split("\t") for line in r.stdout.strip().splitlines() if line.strip()]


def build_files():
    ids = ",".join(str(i) for i in CURRENT)
    rows = sql(f"select id, file_name, ifnull(converted_file_path,''), ifnull(file_path,''), "
               f"ifnull(parent_file_name,''), ifnull(version,''), ifnull(file_size,'0') "
               f"from gienrag.knowledge_base_list where id in ({ids})")
    out = []
    for fid, name, conv, raw, parent, ver, size in rows:
        fid_i = int(fid)
        path = conv or raw
        if fid_i in RAW_PATH_FALLBACK or not path:
            path = raw
        out.append({
            "file_id": fid_i, "file_name": name,
            "file_path": path.replace(END_POINT, "", 1),
            "parent_file_name": parent or None, "version": ver or None,
            "file_size": f"{float(size or 0)/1024/1024:.3f}MB",
            "path_kind": "raw" if path == raw else "converted",
        })
    return out


def parse_one(f):
    body = {
        "knowledge_base_name": KB,
        "files": [{"file_path": f["file_path"], "file_id": f["file_id"], "file_size": f["file_size"],
                   "parent_file_name": f["parent_file_name"], "version": f["version"]}],
        "file_type": "naive", "chunk_size": 512, "chunk_overlap": 100,
        "length_function": "char", "need_chunk": True, "index_name": KB,
        "model_info": MODEL, "embedding_model_info": EMB, "multi_model_info": MM,
    }
    req = urllib.request.Request(BASE + "/parse_sync", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            payload = json.loads(r.read().decode() or "{}")
            st = payload.get("task_statuses") or []
            ok = bool(st) and all(x.get("success") for x in st)
            return {"http": r.status, "secs": round(time.perf_counter() - t0, 1),
                    "ok": ok, "task_statuses": st, "msg": payload.get("msg")}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "secs": round(time.perf_counter() - t0, 1), "ok": False,
                "error": e.read().decode()[:300]}
    except Exception as e:  # noqa: BLE001
        return {"http": None, "secs": round(time.perf_counter() - t0, 1), "ok": False, "error": str(e)[:200]}


def es_rows():
    rows = []
    for idx in (KB, "table_chunks_kb_9", "table_summary_kb_9"):
        body = {"size": 200, "_source": ["metadata.file_id", "metadata.version", "metadata.title",
                                         "metadata.chunk_index", "metadata.pk"]}
        req = urllib.request.Request(f"{ES}/{idx}/_search", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        for h in json.load(urllib.request.urlopen(req))["hits"]["hits"]:
            md = h["_source"].get("metadata") or {}
            rows.append({"index": idx, "id": h["_id"], "file_id": md.get("file_id"),
                         "version": md.get("version"), "title": md.get("title"),
                         "chunk_index": md.get("chunk_index")})
    return rows


def main():
    fs = build_files()
    if "--dry-run" in sys.argv:
        # R14-A 规则（TL 13:1x 定）：任何批量写操作先 dry-run 报"将影响 N 行"
        print(f"[dry-run] 将影响 {len(fs)} 行（kb_9 当前代次），逐行如下：")
        for f in fs:
            print(f'  fid={f["file_id"]:>4} ver={f["version"]} path={f["path_kind"]:<9} '
                  f'{f["file_path"]}')
        print(f"[dry-run] 目标索引: kb_9 / table_chunks_kb_9 / table_summary_kb_9")
        return
    out = {"tag": TAG, "files": fs, "runs": []}
    print(f"[plan] {len(fs)} files: " + ", ".join(f'{f["file_id"]}({f["path_kind"]})' for f in fs), flush=True)
    for f in fs:
        r = parse_one(f)
        print(f'[parse] fid={f["file_id"]} ver={f["version"]} path={f["path_kind"]} http={r.get("http")} '
              f'ok={r.get("ok")} {r.get("secs")}s', flush=True)
        out["runs"].append({"file_id": f["file_id"], "result": r})
        time.sleep(2)
    rows = es_rows()
    out["es_rows"] = rows
    out["summary"] = {
        "total": len(rows),
        "by_index": {i: sum(1 for r in rows if r["index"] == i)
                     for i in ("kb_9", "table_chunks_kb_9", "table_summary_kb_9")},
        "version_nonnull": sum(1 for r in rows if r["version"]),
        "table_file_ids": sorted({str(r["file_id"]) for r in rows if r["index"].startswith("table_")}),
        "parse_failed": [r["file_id"] for r in out["runs"] if not r["result"].get("ok")],
    }
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
