#!/usr/bin/env python
"""doc/docx → PDF 转换能力探测：给出**可归因**的结论，而不是"转换失败"四个字。

背景：MinerU 只吃 PDF/图片，Office 文件必须先转 PDF。之前一直记着"D-01 缺 LibreOffice writer"，
但没验过到底是"没装 LibreOffice"还是"装了但缺 Writer 过滤器"——这两种的修法完全不同。

分类（按可观测证据，不猜）：
- `OK`：真转出一份非空 PDF；
- `NO_SOFFICE`：PATH 里找不到 soffice；
- `NO_WRITER_FILTER`：soffice 在，但转换报 "source file could not be loaded"，
  且运行目录里没有 `libswlo.so`（Writer 模块）——说明只装了 core/calc；
- `CONVERT_FAILED`：soffice 在、Writer 也可能在，但转换仍失败（附 stderr 尾部）。

只做探测，不修环境：装不装 Writer 是部署决策，不是本脚本能悄悄改的。
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DOCX = os.path.join(HERE, "platform/r12/parse/fixtures/generated/cn-docx-direct.docx")


def writer_libs(soffice_path):
    """列出 LibreOffice 程序目录里与 Writer 相关的模块（libswlo.so 是 Writer 本体）。"""
    if not soffice_path:
        return []
    program_dir = os.path.dirname(os.path.realpath(soffice_path))
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(program_dir, "libsw*.so")))


def probe(source=DEFAULT_DOCX, timeout=180):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    result = {"schema": "llmke.convert-probe.v1", "source": source,
              "soffice": soffice, "writer_libs": writer_libs(soffice)}
    if not soffice:
        result.update(status="NO_SOFFICE", detail="PATH 里没有 soffice/libreoffice")
        return result
    if not os.path.isfile(source):
        result.update(status="NO_SOURCE", detail=f"样本不存在: {source}")
        return result

    workdir = tempfile.mkdtemp(prefix="convert-probe-")
    target = os.path.join(workdir, "input.docx")
    shutil.copy(source, target)
    proc = subprocess.run([soffice, "--headless", "--convert-to", "pdf",
                           "--outdir", workdir, target],
                          capture_output=True, text=True, timeout=timeout)
    pdf = os.path.join(workdir, "input.pdf")
    stderr = ((proc.stderr or "") + (proc.stdout or "")).strip()
    if os.path.isfile(pdf) and os.path.getsize(pdf) > 0:
        result.update(status="OK", pdf_bytes=os.path.getsize(pdf),
                      detail=f"转换成功，{os.path.getsize(pdf)} 字节")
        return result

    libs = result["writer_libs"]
    if "libswlo.so" not in libs:
        result.update(status="NO_WRITER_FILTER",
                      detail="soffice 存在但缺 libswlo.so（Writer 模块未安装）",
                      stderr_tail=stderr.splitlines()[-3:],
                      fix="安装 libreoffice-writer（或最小 Writer 过滤器包），无需重装整个套件")
    else:
        result.update(status="CONVERT_FAILED", detail="Writer 模块在，但转换仍失败",
                      stderr_tail=stderr.splitlines()[-3:])
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_DOCX)
    ap.add_argument("--timeout", type=float, default=180)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    result = probe(args.source, args.timeout)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: result[k] for k in ("status", "detail", "writer_libs")},
                     ensure_ascii=False))
    return 0 if result["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
