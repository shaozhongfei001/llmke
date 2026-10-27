"""R14-A：kb_9 全量重解析（走 12340 /parse_sync，version 取自 MySQL knowledge_base_list.version）。

背景：Java 的 /index/knowledgeBase/file/filesParse 当前 500（jar 在进程运行期间被覆盖，
NoClassDefFoundError），所以直接调用解析服务；version 值与 Java 侧 `file.setVersion(kbFile.getVersion())`
同源（都读 knowledge_base_list.version），因此 ES 落库结论等价。

只写 kb_9 一个库；逐文件执行并即时校验，任一失败不影响其它文件。

用法：venvs/alg/bin/python reparse_kb9_full.py > reparse_kb9_full.json
"""
import json
import subprocess
import time
import urllib.error
import urllib.request

MYSQL = ["docker", "exec", "r12-mysql", "mysql", "-uroot", "-pR12r00t#2026local", "-N", "-e"]
BASE = "http://127.0.0.1:12340"
ES = "http://127.0.0.1:19200"
KB = "kb_9"
KB_ID = 9
END_POINT = "http://127.0.0.1:19000/"

MODEL = {"model_id": "qwen2.5-7b-instruct", "url": "http://127.0.0.1:18092/v1/chat/completions"}
EMB = {"model_id": "bge-m3", "url": "http://127.0.0.1:18090/v1/embeddings"}
MM = {"model_id": "qwen2.5-vl-3b-instruct", "url": "http://127.0.0.1:18093/v1/chat/completions"}


def sql(q):
    r = subprocess.run(MYSQL + [q], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:200])
    return [line.split("\t") for line in r.stdout.strip().splitlines() if line.strip()]


def files():
    rows = sql("select id, file_name, ifnull(converted_file_path,file_path), ifnull(parent_file_name,''), "
               f"ifnull(version,''), ifnull(file_size,'0') from gienrag.knowledge_base_list "
               f"where kb_id={KB_ID} and status in (0,3,4) and is_enable=1 order by id")
    out = []
    for fid, name, path, parent, ver, size in rows:
        out.append({
            "file_id": int(fid), "file_name": name,
            "file_path": path.replace(END_POINT, "", 1),
            "parent_file_name": parent or None, "version": ver or None,
            "file_size": f"{float(size or 0)/1024/1024:.3f}MB",
        })
    return out


def parse_one(f):
    body = {
        "knowledge_base_name": KB,
        "files": [{k: f[k] for k in ("file_path", "file_id", "file_size")} |
                  {"parent_file_name": f["parent_file_name"], "version": f["version"]}],
        "file_type": "naive", "chunk_size": 512, "chunk_overlap": 100,
        "length_function": "char", "need_chunk": True, "index_name": KB,
        "model_info": MODEL, "embedding_model_info": EMB, "multi_model_info": MM,
    }
    req = urllib.request.Request(BASE + "/parse_sync", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            return {"http": r.status, "secs": round(time.perf_counter() - t0, 1),
                    "body": json.loads(r.read().decode() or "{}")}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "secs": round(time.perf_counter() - t0, 1),
                "body": e.read().decode()[:300]}
    except Exception as e:  # noqa: BLE001
        return {"http": None, "secs": round(time.perf_counter() - t0, 1), "error": str(e)[:200]}


def es_state():
    body = {"size": 500, "_source": ["metadata.file_id", "metadata.version", "metadata.title",
                                     "metadata.chunk_index", "metadata.pk", "metadata.document_id"]}
    req = urllib.request.Request(f"{ES}/{KB}/_search", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    hits = json.load(urllib.request.urlopen(req, timeout=30))["hits"]["hits"]
    rows = []
    for h in hits:
        md = h["_source"].get("metadata") or {}
        rows.append({"id": h["_id"], "file_id": md.get("file_id"), "version": md.get("version"),
                     "title": md.get("title"), "chunk_index": md.get("chunk_index"),
                     "pk": md.get("pk"), "document_id": md.get("document_id")})
    return rows


def main():
    fs = files()
    out = {"kb": KB, "files_total": len(fs), "files": fs, "runs": []}
    print(f"[files] {len(fs)}", flush=True)
    for f in fs:
        r = parse_one(f)
        ok = (r.get("http") == 200 and
              all(x.get("success") for x in ((r.get("body") or {}).get("task_statuses") or [{}])))
        print(f"[parse] fid={f['file_id']} ver={f['version']} http={r.get('http')} ok={ok} "
              f"{r.get('secs')}s {str(r.get('body'))[:120]}", flush=True)
        out["runs"].append({"file_id": f["file_id"], "version": f["version"], "result": r, "ok": ok})
        time.sleep(2)
    rows = es_state()
    out["es_rows"] = rows
    nn = [r for r in rows if r["version"]]
    out["summary"] = {
        "es_total": len(rows),
        "version_nonnull": len(nn),
        "version_ratio": round(len(nn) / len(rows), 4) if rows else 0,
        "by_file": {},
    }
    for r in rows:
        key = str(r["file_id"])
        d = out["summary"]["by_file"].setdefault(key, {"chunks": 0, "versions": set(), "title": r["title"]})
        d["chunks"] += 1
        d["versions"].add(str(r["version"]))
    for d in out["summary"]["by_file"].values():
        d["versions"] = sorted(d["versions"])
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
