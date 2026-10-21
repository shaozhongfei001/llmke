#!/usr/bin/env python3
"""回放对比：臂 A（原始字节 + server 假桩） vs 臂 B（server→_shims 改写 + 惰性注册表）。

判定：两个臂对同一批样本产出的 ParsedText 序列是否逐字段一致（page_content / type / position /
page_number / page_size / offset / title_path / chunk_index / need_filtered / 表格与图片名）。

用法：
  python3 parity_check.py --src <alg_doc_parse_service> --samples <dir> --work /tmp/llmke-spike \
      --report <输出 md> --json <输出 json>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUFFIXES = {".txt", ".html", ".htm", ".md", ".docx", ".csv"}


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--samples", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--json", type=Path, required=True)
    a = ap.parse_args()

    shimmed = a.work / "shimmed"
    arm_a_tree = a.work / "armA"
    outdir = a.work / "out"
    outdir.mkdir(parents=True, exist_ok=True)

    # 臂 A：原始字节 + 只替换惰性 __init__（不改 server.* 导入）
    build_a = run([sys.executable, str(HERE / "build_shimmed.py"),
                   "--src", str(a.src), "--out", str(arm_a_tree), "--no-rewrite"])
    # 臂 B：原始字节 + 惰性 __init__ + server.* → _shims
    build = run([sys.executable, str(HERE / "build_shimmed.py"),
                 "--src", str(a.src), "--out", str(shimmed)])
    if build.returncode != 0 or build_a.returncode != 0:
        print(build.stdout, build.stderr, build_a.stdout, build_a.stderr)
        return 2
    rewritten = [ln.strip() for ln in build.stdout.splitlines() if ln.startswith("   deepdoc")]
    shims = build.stdout.strip().splitlines()[-1]

    samples = sorted(p for p in a.samples.iterdir() if p.suffix.lower() in SUFFIXES)
    rows = []
    for s in samples:
        rec = {"sample": s.name, "bytes": s.stat().st_size}
        for arm in ("A", "B"):
            out = outdir / f"{arm}-{s.name}.json"
            root = arm_a_tree if arm == "A" else shimmed
            r = run([sys.executable, str(HERE / "run_arm.py"), "--arm", arm,
                     "--src-root", str(root), "--shimmed", str(shimmed),
                     "--sample", str(s), "--out", str(out)])
            if r.returncode != 0:
                rec[f"{arm}_runner_error"] = (r.stdout + r.stderr)[-500:]
                continue
            rec[arm] = json.loads(out.read_text(encoding="utf-8"))
        if "A" in rec and "B" in rec:
            A, B = rec["A"], rec["B"]
            rec["count_a"], rec["count_b"] = A.get("count"), B.get("count")
            # 只有两臂都成功，才谈得上「一致」；任一侧失败一律判 FAILED，不冒充一致
            if not (A.get("ok") and B.get("ok")):
                rec["verdict"] = "FAILED"
            elif A.get("blocks") == B.get("blocks"):
                rec["verdict"] = "IDENTICAL"
            else:
                rec["verdict"] = "DIFF"
                diff_at = next((i for i, (x, y) in enumerate(zip(A["blocks"], B["blocks"])) if x != y), None)
                rec["first_diff_index"] = diff_at
        else:
            rec["verdict"] = "INCOMPLETE"
        rows.append(rec)

    # 仓库内不留个人绝对路径：只保留模块名，完整路径由运行参数提供
    src_label = "…/" + a.src.name
    for r in rows:
        for arm in ("A", "B"):
            if isinstance(r.get(arm), dict) and r[arm].get("deepdoc_file"):
                r[arm]["deepdoc_file"] = "…/" + "/".join(
                    Path(r[arm]["deepdoc_file"]).parts[-3:])
    summary = {
        "src": src_label,
        "rewritten_files": len(rewritten),
        "rewritten_list": rewritten,
        "shims": shims,
        "samples": len(rows),
        "identical": sum(1 for r in rows if r.get("verdict") == "IDENTICAL"),
        "diff": sum(1 for r in rows if r.get("verdict") == "DIFF"),
        "incomplete": sum(1 for r in rows if r.get("verdict") == "INCOMPLETE"),
        "rows": rows,
    }
    a.json.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    lines = ["# 回放对比：切断服务层耦合前 vs 后", "",
             f"- 原始模块：`{src_label}`（完整路径由运行参数给出，不入库）",
             f"- 改写文件数：**{len(rewritten)}**（`server.*` → `_shims.*`）",
             f"- 生成桩：{shims}",
             f"- 样本数：{len(rows)}；**逐字段一致：{summary['identical']}**；"
             f"不一致：{summary['diff']}；不完整：{summary['incomplete']}", "",
             "| 样本 | 大小 | 臂A 块数 | 臂B 块数 | 结论 | 备注 |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        note = ""
        if r.get("verdict") == "DIFF":
            note = f"首个差异块 #{r.get('first_diff_index')}"
        for arm in ("A", "B"):
            if r.get(arm) and not r[arm].get("ok"):
                note += f" {arm}:{r[arm].get('error')}"
        lines.append(f"| `{r['sample']}` | {r['bytes']} | {r.get('count_a', '-')} | "
                     f"{r.get('count_b', '-')} | **{r['verdict']}** | {note} |")
    lines += ["", "## 两臂实际解析到的源码路径（防止臂 A 被臂 B 顶替）", "",
              "| 样本 | 臂A 解析器文件 | 臂B 解析器文件 |", "|---|---|---|"]
    for r in rows:
        fa = r.get("A", {}).get("deepdoc_file", "-") if r.get("A") else "-"
        fb = r.get("B", {}).get("deepdoc_file", "-") if r.get("B") else "-"
        lines.append(f"| `{r['sample']}` | `{fa}` | `{fb}` |")

    lines += ["", "## 运行期桩统计（量化导入期耦合）", "",
              "| 样本 | 臂A 需要桩的模块数 | 臂B 需要桩的模块数 |", "|---|---|---|"]
    for r in rows:
        ca = len(r.get("A", {}).get("stubbed_modules", [])) if r.get("A") else "-"
        cb = len(r.get("B", {}).get("stubbed_modules", [])) if r.get("B") else "-"
        lines.append(f"| `{r['sample']}` | {ca} | {cb} |")
    a.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("samples", "identical", "diff", "incomplete",
                                              "rewritten_files")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
