#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-6 第 0 步：前端版本自证（QA-SPEC §1.4）+ 服务代次 + kb 基线 + 写锁。

不做任何写操作（除写锁文件）。证据：AG-6/evidence/S0/preflight-*.json
"""
import json
import os
import subprocess

import ag6_lib as L

DIST = "/home/szf/data/dev/llmke-r12/frontend/plateform/dist"
INDEX_HTML = os.path.join(DIST, "index.html")


def served_entry():
    with open(INDEX_HTML, encoding="utf-8") as f:
        html = f.read()
    import re
    m = re.search(r'assets/index-[A-Za-z0-9_-]+\.js', html)
    entry = m.group(0) if m else None
    return entry, len(html)


def main():
    os.makedirs(os.path.join(L.EVID, "S0"), exist_ok=True)
    entry, html_len = served_entry()
    dist_path = os.path.join(DIST, entry)
    tmp = "/tmp/served-AG-6.js"
    curl = subprocess.run(["curl", "-sS", "-o", tmp, "-w", "%{http_code} %{size_download}",
                           f"{L.FE}/{entry}"], capture_output=True, text=True)
    http, got = (curl.stdout.split() + ["", ""])[:2]
    served_md5 = L.md5(tmp)
    dist_md5 = L.md5(dist_path)

    st = L.load_state()
    s, token = L.login()
    code_list, kbs, _ = L.kb_list(s, token)
    recs = (kbs.get("data") or {}).get("records") if isinstance(kbs, dict) else None
    names = [r.get("kbName") for r in (recs or [])]

    # 只读核查：FAQ 直答依赖的助手配置口径（哪条配置 enabled_faq=1、绑哪个库）
    cfg = L.mysql_rows("select id,name,enabled_faq,status,ifnull(depend_on_kb,'') "
                       "from search_config order by id")
    faq_tbl = L.mysql_rows("select count(*) from faq_info" if False else
                           "select table_name from information_schema.tables "
                           "where table_schema='gienrag' and table_name like '%faq%'")

    out = {
        "time": L.now(),
        "frontend": {
            "entry": entry,
            "dist_index_html_bytes": html_len,
            "curl": f"http={http} bytes={got}",
            "md5_served": served_md5,
            "md5_dist": dist_md5,
            "match": served_md5 == dist_md5,
            "dist_mtime": subprocess.run(
                ["bash", "-lc", f"stat -c '%y %s' {dist_path}"],
                capture_output=True, text=True).stdout.strip(),
            "backup_md5_old_pkg": "de2424501bd29e358043049876db2a75",
        },
        "pids_open": L.pids(),
        "pids_open_lstart": {k: L.pid_start(v) for k, v in L.pids().items()},
        "kb_list": {"http": code_list, "count": len(names), "names": names},
        "search_config_rows": cfg,
        "faq_tables": faq_tbl,
    }
    p = L.dump(f"preflight-{L.ts()}.json", out, "S0")
    print(json.dumps({"evidence": p, "frontend_match": out["frontend"]["match"],
                      "entry": entry, "md5": served_md5,
                      "kb_count": len(names), "kb_names": names}, ensure_ascii=False, indent=1))
    print("cfg:", json.dumps(cfg, ensure_ascii=False))
    print("faq_tables:", json.dumps(faq_tbl, ensure_ascii=False))
    st["frontend"] = out["frontend"]
    st["pids_open"] = out["pids_open"]
    st["kb_baseline"] = names
    L.save_state(st)


if __name__ == "__main__":
    main()
