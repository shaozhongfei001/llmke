#!/usr/bin/env python
"""渲染并校验 systemd 单元：把 @REPO@ / @PYTHON@ 替换成真实路径，再交给 systemd-analyze 验。

为什么要有"渲染"这一步：单元文件里写死某台机器的绝对路径，换机器就废；
模板 + 渲染能在不改单元内容的前提下适配部署路径，同时让 CI 能验证"渲染出来的东西合法"。

`--verify` 调 `systemd-analyze verify`：它会检查语法、未知指令、可执行文件是否存在。
注意它对本机的可执行文件路径敏感（渲染时必须给真实存在的 python），否则会报
"Executable ... not found"——这类告警要当失败看，不能当噪声。
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "deploy" / "systemd"


def render(template_path, repo, python):
    text = Path(template_path).read_text(encoding="utf-8")
    return text.replace("@REPO@", str(repo)).replace("@PYTHON@", str(python))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "build" / "systemd"))
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for template in sorted(TEMPLATES.glob("*.service")):
        text = render(template, args.repo, args.python)
        target = out_dir / template.name
        target.write_text(text, encoding="utf-8")
        results.append({"unit": template.name, "path": str(target),
                        "placeholders_left": "@REPO@" in text or "@PYTHON@" in text})

    report = {"schema": "llmke.systemd-render.v1", "out": str(out_dir),
              "python": args.python, "units": results, "verify": None}
    ok = not any(r["placeholders_left"] for r in results)

    if args.verify:
        if not shutil.which("systemd-analyze"):
            report["verify"] = {"status": "SKIP", "why": "systemd-analyze 不可用"}
        else:
            proc = subprocess.run(
                ["systemd-analyze", "verify", *[r["path"] for r in results]],
                capture_output=True, text=True)
            output = ((proc.stdout or "") + (proc.stderr or "")).strip()
            # systemd-analyze 会把**整机所有 unit** 都扫一遍（本机就有 netplan/spark 的既有噪声），
            # 所以只认与本单元相关的行；对"可执行文件不存在"它只警告不返回非零，必须自己看输出。
            names = [Path(r["path"]).name for r in results]
            suspicious = [line for line in output.splitlines()
                          if any(name in line for name in names)
                          and ("not found" in line or "Unknown" in line or "Failed" in line)]
            report["verify"] = {"status": "PASS" if proc.returncode == 0 and not suspicious
                                else "FAIL",
                                "rc": proc.returncode,
                                "suspicious": suspicious[:5],
                                "output": output[-800:]}
            ok = ok and report["verify"]["status"] == "PASS"

    report["status"] = "PASS" if ok else "FAIL"
    print(json.dumps({"status": report["status"],
                      "units": [r["unit"] for r in results],
                      "verify": (report["verify"] or {}).get("status")},
                     ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
