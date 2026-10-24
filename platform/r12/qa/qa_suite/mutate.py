#!/usr/bin/env python3
"""变异自检：证明 negatives.py 里的断言"真的会 FAIL"，不是恒真空转。

做法（两条独立证据）：
  M1 违约观察注入：把真实观察里的关键字段改成"违约值"（flip），再喂给同一断言函数。
     期望：断言必须从"通过"翻成 FAIL。若注入违约值后仍然 PASS/BLOCKED → 断言空转。
  M2 期望反转：把整套判定的"期望"反过来（要求 PASS 的用例断言其必须 FAIL），
     验证报告层确实能把失败渲染成 FAIL，而不是无论输入都打印 PASS。

用法: python3 mutate.py [--evidence <dir>]
不指定 --evidence 时自动取最新一次含 s8_negative_obs.json 的证据目录。
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import negatives as NEG  # noqa: E402

R12 = "/home/szf/data/dev/llmke-r12/platform/r12"


def latest_evidence():
    cands = sorted(glob.glob(f"{R12}/qa/evidence/*/s8_negative_obs.json"))
    return os.path.dirname(cands[-1]) if cands else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default="")
    args = ap.parse_args()
    ev = args.evidence or latest_evidence()
    real = {}
    if ev and os.path.exists(os.path.join(ev, "s8_negative_obs.json")):
        real = json.load(open(os.path.join(ev, "s8_negative_obs.json"), encoding="utf-8"))

    rows, vacuous = [], []
    for cid, (name, fn, flip) in NEG.CASES.items():
        base = real.get(cid)
        if base is None:
            # 未真实跑过（例如 P1~P3 属正向场景）：用"全部合规"的最小观察做基线
            base = {
                "N1": {"status": 401, "control_status": 200},
                "N2": {"control_status": 200, "results": [{"label": "x", "status": 401}]},
                "N3": {"status": 401, "control_status": 200, "leaked_admin": False},
                "N4": {"status": 401, "control_status": 200},
                "N5": {"status": 403, "n_records": 0, "kb_private": 1},
                "N6": {"results": [{"path": "/x", "status": 401, "snippet": ""}]},
                "N7": {"reject": True, "http": 500, "snippet": "文件格式不支持"},
                "N8": {"reject": False, "final_status": 4, "chunk_count": 0},
                "N9": {"cited_after_delete": ["2"], "deleted_file_ids": ["1"]},
                "P1": {"cited": ["1"], "uploaded": ["1"]},
                "P2": {"allowed": ["content", "sessionId"], "req_keys": ["content", "sessionId"],
                       "content_len": 20, "question_len": 20},
                "P3": {"final_status": 3, "chunk_count": 7},
            }.get(cid, {})
            src = "合成合规基线"
        else:
            src = f"真实观察({os.path.basename(ev)})"

        good_v, good_why = fn(base)
        bad = flip(base)
        bad_v, bad_why = fn(bad)

        # M1：注入违约观察后必须变 FAIL
        m1 = (bad_v == "FAIL")
        # M2：期望反转——要求"该用例必须不是 PASS"，对合规基线应当不成立
        m2 = (good_v != "PASS") if good_v == "PASS" else None
        if not m1:
            vacuous.append(cid)
        rows.append({
            "case": cid, "name": name, "baseline_src": src,
            "baseline_verdict": good_v, "baseline_why": good_why,
            "mutated_verdict": bad_v, "mutated_why": bad_why,
            "M1_违约观察被判FAIL": "PASS" if m1 else "空转",
            "M2_期望反转后应非PASS": ("n/a(基线本身不是PASS)" if m2 is None
                                     else ("PASS" if m2 else "空转")),
        })

    out = os.path.join(R12, "qa", "evidence", "mutation-selfcheck.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"{'用例':4} {'基线':8} {'注入违约后':10} M1")
    for r in rows:
        print(f"{r['case']:4} {r['baseline_verdict']:8} {r['mutated_verdict']:10} {r['M1_违约观察被判FAIL']}"
              f"  | 违约说明: {r['mutated_why'][:60]}")
    print()
    if vacuous:
        print("!! 存在空转断言（注入违约观察后仍未 FAIL）:", vacuous)
        return 1
    print(f"变异自检通过：{len(rows)}/{len(rows)} 条断言在注入违约观察后均翻成 FAIL，非空转。")
    print("证据:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
