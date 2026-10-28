#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-6 环境代次复核（开工 / 收工各一次）：六端口 pid + 启动时刻 + 前端包 md5（served vs dist）。"""
import json
import os
import re
import subprocess

import ag6_lib as L

DIST = "/home/szf/data/dev/llmke-r12/frontend/plateform/dist"


def main():
    tag = L.ts()
    with open(os.path.join(DIST, "index.html"), encoding="utf-8") as f:
        html = f.read()
    entry = re.search(r'assets/index-[A-Za-z0-9_-]+\.js', html).group(0)
    tmp = f"/tmp/served-AG-6-{tag}.js"
    r = subprocess.run(["curl", "-sS", "-o", tmp, "-w", "%{http_code} %{size_download}",
                        f"{L.FE}/{entry}"], capture_output=True, text=True)
    p = L.pids()
    ev = {"time": L.now(), "tag": tag,
          "pids": p, "lstart": {k: L.pid_start(v) for k, v in p.items()},
          "frontend": {"entry": entry, "curl": r.stdout,
                       "md5_served": L.md5(tmp),
                       "md5_dist": L.md5(os.path.join(DIST, entry)),
                       "dist_mtime": subprocess.run(
                           ["bash", "-lc", f"stat -c '%y' {DIST}/{entry}"],
                           capture_output=True, text=True).stdout.strip()}}
    ev["frontend"]["match"] = ev["frontend"]["md5_served"] == ev["frontend"]["md5_dist"]
    st = L.load_state()
    ev["compare_open"] = {"pids_open": st.get("pids_open"), "pids_now": p,
                          "same": st.get("pids_open") == p}
    path = L.dump(f"env-{tag}.json", ev, "S0")
    print(json.dumps({"evidence": path, "pids": p, "lstart": ev["lstart"],
                      "same_as_open": ev["compare_open"]["same"],
                      "frontend": ev["frontend"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
