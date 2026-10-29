#!/usr/bin/env python3
"""R15 / F12 反例法验收断言集：一键跑 A01–A16。

用法：
    cd /home/szf/data/dev/llmke-r12
    python3 platform/r15/acceptance/run_all.py                # 跑全部
    python3 platform/r15/acceptance/run_all.py A03 A09 A11    # 只跑指定项

退出码：
    0  = 没有 FAIL（允许存在 SKIP，但 SKIP 不等于 PASS）
    1  = 至少一条 FAIL
    2  = 断言集本身执行异常（导入失败/基础设施不可用导致跑不完）

结果落盘：platform/r15/acceptance/results/last-run.json
"""
import importlib
import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ORDER = [f"a{i:02d}" for i in range(1, 17)]
MARK = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}


def main(argv):
    want = [a.lower() for a in argv[1:]] or ORDER
    mods = []
    for name in ORDER:
        if name not in want:
            continue
        mods.append(importlib.import_module(name))

    results = []
    t_all = time.time()
    for m in mods:
        t0 = time.time()
        try:
            r = m.run()
            r["elapsed"] = round(time.time() - t0, 1)
        except Exception as e:  # 断言集自身异常：不能当通过，也不能静默跳过
            r = {"id": getattr(m, "ID", m.__name__),
                 "title": getattr(m, "TITLE", ""),
                 "status": "FAIL",
                 "reason": f"断言执行异常 {type(e).__name__}: {str(e)[:200]}",
                 "checks": [], "writes_required": getattr(m, "WRITES", False),
                 "elapsed": round(time.time() - t0, 1)}
            r["traceback"] = traceback.format_exc()[-800:]
        results.append(r)
        print(f"[{MARK.get(r['status'], r['status']):4s}] {r['id']}  {r['title']}")
        print(f"       └─ {r['reason']}  ({r['elapsed']}s)")
        for c in r.get("checks", []):
            flag = "ok " if c["ok"] else "BAD"
            print(f"          {flag} {c['check']}: {c['detail'][:220]}")
        print()

    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_fail = sum(1 for r in results if r["status"] == "FAIL")
    n_skip = sum(1 for r in results if r["status"] == "SKIP")
    print("=" * 78)
    print(f"合计 {len(results)} 条：PASS {n_pass} / FAIL {n_fail} / SKIP {n_skip}"
          f"  总耗时 {round(time.time() - t_all, 1)}s")
    if n_fail:
        print("FAIL 明细：")
        for r in results:
            if r["status"] == "FAIL":
                bad = [c for c in r.get("checks", []) if c["ok"] is False]
                print(f"  - {r['id']} {r['reason']}")
                for c in bad[:3]:
                    print(f"      · {c['check']}: {c['detail'][:200]}")
    if n_skip:
        print("SKIP 明细：")
        for r in results:
            if r["status"] == "SKIP":
                print(f"  - {r['id']} {r['reason'][:150]}")

    out_dir = os.path.join(HERE, "results")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "last-run.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"run_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   "summary": {"total": len(results), "pass": n_pass,
                               "fail": n_fail, "skip": n_skip},
                   "results": results}, f, ensure_ascii=False, indent=1)
    print(f"[evidence] {out}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:
        traceback.print_exc()
        sys.exit(2)
