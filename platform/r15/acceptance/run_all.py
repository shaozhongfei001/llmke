#!/usr/bin/env python3
"""R15 / F12 反例法验收断言集：一键跑 A01–A16。

用法：
    cd <repo>
    platform/r15/verify.sh                        # 推荐入口（参数化 + 前置检查）
    python3 platform/r15/acceptance/run_all.py    # 直接跑（用默认/环境变量）
    python3 platform/r15/acceptance/run_all.py A03 A09 A11

退出码：
    0  = 没有 FAIL（允许存在 SKIP，但 SKIP 不等于 PASS）
    1  = 至少一条 FAIL
    2  = 断言集本身执行异常（导入失败/基础设施不可用导致跑不完）

证据落盘（R15 可转让性改造：结论必须带原始产物，否则只是自述）：
    results/last-run.json              最新一次（兼容旧路径）
    results/<run_id>/env.json          本次环境指纹（地址/库/空间/模型/解释器）
    results/<run_id>/report.json       全部断言判定
    results/<run_id>/summary.txt       人读摘要
    results/<run_id>/raw/<Axx>.json    每条断言的完整返回（含每条 check 明细）
    results/<run_id>/baseline-diff.json 与 baseline/expect.json 的差异

基线比对的意义：单次运行只能说"此刻怎样"；有基线才能说"他跑的结果和我的一样/变差了"。
"""
import hashlib
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
BASELINE = os.path.join(os.path.dirname(HERE), "baseline", "expect.json")


def _dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def _sha(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return ""


def baseline_diff(results):
    """与基线比对。分类必须分清，否则"变差"会被"新增断言"掩盖：
      regressed  基线 PASS → 现在 FAIL（最需要关注）
      recovered  基线 FAIL → 现在 PASS
      still_fail 基线 FAIL → 现在 FAIL
      new        基线里没有这条
      missing    基线有、这次没跑
      skipped    这次 SKIP（不算回归，但也不算通过）
    """
    if not os.path.isfile(BASELINE):
        return {"baseline": "<absent>", "note": "尚无基线；本次可作为首份基线"}
    with open(BASELINE, encoding="utf-8") as f:
        base = json.load(f)
    b = {r["id"]: r for r in base.get("results", [])}
    cur = {r["id"]: r for r in results}
    out = {"baseline": BASELINE, "baseline_run_at": base.get("run_at"),
           "baseline_commit": base.get("commit", ""),
           "regressed": [], "recovered": [], "still_fail": [],
           "new": [], "missing": [], "skipped": []}
    for aid, r in cur.items():
        bs = (b.get(aid) or {}).get("status")
        cs = r["status"]
        if bs is None:
            out["new"].append({"id": aid, "now": cs})
        elif cs == "FAIL" and bs == "PASS":
            out["regressed"].append({"id": aid, "reason": r.get("reason", "")[:200]})
        elif cs == "PASS" and bs == "FAIL":
            out["recovered"].append({"id": aid})
        elif cs == "FAIL" and bs == "FAIL":
            out["still_fail"].append({"id": aid})
        elif cs == "SKIP":
            out["skipped"].append({"id": aid, "was": bs})
    for aid in b:
        if aid not in cur:
            out["missing"].append({"id": aid, "was": b[aid].get("status")})
    return out


def main(argv):
    want = [a.lower() for a in argv[1:]] or ORDER
    mods = []
    for name in ORDER:
        if name not in want:
            continue
        mods.append(importlib.import_module(name))

    from common import env_fingerprint  # noqa: E402  (需在 sys.path 设置后导入)

    run_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    run_id = time.strftime("%Y-%m-%dT%H-%M-%S")
    commit = ""
    try:
        import subprocess
        commit = subprocess.run(["git", "-C", HERE, "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        pass

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
                print(f"  - {r['id']} {r['reason']}")
                for c in [c for c in r.get("checks", []) if c["ok"] is False][:3]:
                    print(f"      · {c['check']}: {c['detail'][:200]}")
    if n_skip:
        print("SKIP 明细：")
        for r in results:
            if r["status"] == "SKIP":
                print(f"  - {r['id']} {r['reason'][:150]}")

    # ── 证据落盘
    env = env_fingerprint()
    payload = {"run_id": run_id, "run_at": run_at, "commit": commit,
               "summary": {"total": len(results), "pass": n_pass,
                           "fail": n_fail, "skip": n_skip},
               "results": results}
    diff = baseline_diff(results)

    run_dir = os.path.join(HERE, "results", run_id)
    _dump(os.path.join(run_dir, "env.json"), env)
    _dump(os.path.join(run_dir, "report.json"), payload)
    _dump(os.path.join(run_dir, "baseline-diff.json"), diff)
    for r in results:
        _dump(os.path.join(run_dir, "raw", f"{r['id']}.json"), r)

    lines = [f"R15 验收证据   run_id={run_id}  commit={commit}",
             f"时间 {run_at}",
             f"环境 gateway={env['gateway']} es={env['es']} nebula={env['nebula']} "
             f"kb={env['kb']} space={env['space']} model={env['model_id']}",
             f"合计 {len(results)} 条：PASS {n_pass} / FAIL {n_fail} / SKIP {n_skip}",
             ""]
    for r in results:
        lines.append(f"[{r['status']:4s}] {r['id']}  {r['title']}")
        lines.append(f"        {r['reason']}")
        for c in r.get("checks", []):
            lines.append(f"        {'ok ' if c['ok'] else 'BAD'} {c['check']}: {c['detail'][:400]}")
    if isinstance(diff, dict) and diff.get("regressed"):
        lines.append("")
        lines.append(f"相对基线回归：{[x['id'] for x in diff['regressed']]}")
    with open(os.path.join(run_dir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # 兼容旧路径：last-run.json 始终指向最新一次，并记录证据目录
    payload["evidence_dir"] = os.path.relpath(run_dir, HERE)
    payload["baseline_diff"] = {k: v for k, v in diff.items()
                                if k in ("regressed", "recovered", "still_fail", "new", "missing")}
    _dump(os.path.join(HERE, "results", "last-run.json"), payload)

    print(f"[evidence] {run_dir}/  (env.json / report.json / summary.txt / raw/)")
    if isinstance(diff, dict):
        if diff.get("regressed"):
            print(f"[baseline] 回归 {len(diff['regressed'])} 条：{[x['id'] for x in diff['regressed']]}")
        if diff.get("recovered"):
            print(f"[baseline] 由 FAIL 转 PASS {len(diff['recovered'])} 条：{[x['id'] for x in diff['recovered']]}")
        if diff.get("note"):
            print(f"[baseline] {diff['note']}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:
        traceback.print_exc()
        sys.exit(2)
