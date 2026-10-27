#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B 重建期间的只读过程证据（第⑥条：逐 file_id 块数不得减少）。

每 20s 采一次：
  · ES: kb_9 / table_chunks_kb_9 / table_summary_kb_9 的逐 file_id 块数
  · Nebula: g_kb_9 是否存在、顶点数
发现任一 file_id 块数 < 基线 -> 立即打印 ALARM 并退出码 3（不等跑完）。

用法：
  platform/r12/venvs/graph/bin/python monitor_rebuild.py <baseline.json> <out.jsonl> [max_seconds]
"""
import json
import sys
import time
import urllib.request

from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool

ES = "http://127.0.0.1:19200"


def es_counts(idx):
    try:
        body = json.dumps({"size": 500, "_source": ["metadata.file_id"]}).encode()
        req = urllib.request.Request(f"{ES}/{idx}/_search", data=body,
                                     headers={"Content-Type": "application/json"})
        hits = json.load(urllib.request.urlopen(req, timeout=10))["hits"]["hits"]
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)[:80]}
    out = {}
    for h in hits:
        fid = str(((h["_source"].get("metadata") or {}).get("file_id")))
        out[fid] = out.get(fid, 0) + 1
    return out


def nebula_state(pool):
    try:
        s = pool.get_session("root", "nebula")
        r = s.execute("SHOW SPACES")
        spaces = [r.row_values(i)[0].as_string() for i in range(r.row_size())]
        if "g_kb_9" not in spaces:
            return {"space": False, "vertices": None, "edges": None}
        s.execute("USE g_kb_9")
        vc = s.execute("MATCH (v:entity) RETURN count(v) AS c")
        ec = s.execute("MATCH ()-[e:relationship]->() RETURN count(e) AS c")
        v = vc.row_values(0)[0].as_int() if vc.is_succeeded() and vc.row_size() else -1
        e = ec.row_values(0)[0].as_int() if ec.is_succeeded() and ec.row_size() else -1
        return {"space": True, "vertices": v, "edges": e}
    except Exception as ex:  # noqa: BLE001
        return {"space": None, "error": str(ex)[:80]}


def main():
    baseline_path = sys.argv[1]
    out_path = sys.argv[2]
    max_seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    baseline = json.load(open(baseline_path, encoding="utf-8"))

    cfg = Config()
    cfg.max_connection_pool_size = 2
    pool = ConnectionPool()
    pool.init([("127.0.0.1", 19669)], cfg)

    t0 = time.time()
    n = 0
    worst = 0
    with open(out_path, "w", encoding="utf-8") as out:
        while time.time() - t0 < max_seconds:
            n += 1
            ts = time.strftime("%H:%M:%S")
            sample = {"t": ts, "n": n, "nebula": nebula_state(pool)}
            bad = []
            for idx in ("kb_9", "table_chunks_kb_9", "table_summary_kb_9"):
                cur = es_counts(idx)
                sample[idx] = cur
                base = (baseline.get(idx) or {}).get("count_by_file_id") or {}
                if "_error" in cur:
                    continue
                for fid, need in base.items():
                    got = cur.get(fid, 0)
                    if got < need:
                        bad.append(f"{idx}/{fid}: {need}->{got}")
            sample["alarm"] = bad
            out.write(json.dumps(sample, ensure_ascii=False) + "\n")
            out.flush()
            if bad:
                worst = 3
                print(f"ALARM {ts} 块数减少: {bad}")
                break
            print(f"{ts} N{n} nebula={sample['nebula']} kb_9={sum(es_counts('kb_9').values())}", flush=True)
            time.sleep(20)
    pool.close()
    print(f"done samples={n} worst={worst}")
    sys.exit(worst)


if __name__ == "__main__":
    main()
