#!/usr/bin/env python3
"""A2 冒烟：用真实 MinerU（magic-pdf CLI）解析扫描件，断言中文正文被抽出。

为什么用 CLI 而不是直接 import `deepdoc.parser.MinerUParser`：
平台适配器会连带拉 `deepdoc.parser.__init__` 的一串云厂商 SDK（ali/textin/…），
在没有完整 parse venv 的环境里根本 import 不进去。CLI 是上游稳定入口，
能把"权重+配置+模型链路"这条最重的部分验证掉；适配器的接缝另用代码评审+部署清单管。

用法：
  MINERU_TOOLS_CONFIG_JSON=/path/magic-pdf.json \
  /path/mineru-venv/bin/python scripts/v2_mineru_smoke.py --pdf <scan.pdf> --out /tmp/mineru-smoke.json
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--magic-pdf", default=os.path.join(
        os.path.dirname(sys.executable), "magic-pdf"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--expect", nargs="*", default=[],
                    help="必须出现在输出正文里的片段（中文、金额等）")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args(argv)

    if not os.path.isfile(args.magic_pdf):
        print(json.dumps({"status": "NO_MINERU_CLI", "path": args.magic_pdf}, ensure_ascii=False))
        return 2
    if not os.environ.get("MINERU_TOOLS_CONFIG_JSON"):
        print(json.dumps({"status": "NO_CONFIG_ENV",
                          "hint": "设置 MINERU_TOOLS_CONFIG_JSON 指向 magic-pdf.json"}, ensure_ascii=False))
        return 2

    work = tempfile.mkdtemp(prefix="mineru-smoke-")
    try:
        proc = subprocess.run([args.magic_pdf, "-p", args.pdf, "-o", work, "-m", "ocr"],
                              capture_output=True, text=True, timeout=args.timeout)
        if proc.returncode != 0:
            print(json.dumps({"status": "MINERU_FAILED", "code": proc.returncode,
                              "tail": (proc.stderr or proc.stdout).strip().splitlines()[-6:]},
                             ensure_ascii=False))
            return 1

        md_files = []
        for root, _dirs, files in os.walk(work):
            md_files += [os.path.join(root, f) for f in files if f.endswith(".md")]
        if not md_files:
            print(json.dumps({"status": "NO_MARKDOWN", "work": work}, ensure_ascii=False))
            return 1

        text = open(md_files[0], encoding="utf-8").read()
        missing = [e for e in args.expect if e not in text]
        report = {"status": "OK" if not missing else "CONTENT_MISMATCH",
                  "markdown": os.path.basename(md_files[0]),
                  "chars": len(text),
                  "missing": missing,
                  "head": text[:120]}
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
        print(json.dumps(report, ensure_ascii=False))
        return 0 if not missing else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
