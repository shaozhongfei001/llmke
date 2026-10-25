#!/usr/bin/env python3
"""R13 预览转换实测矩阵（可重复执行，产物与文本进 evidence 目录）。

用法:
  python3 platform/r12/preview/smoke_matrix.py            # 直连 18095
  PREVIEW_BASE=http://127.0.0.1:18088/preview python3 ...  # 走 nginx
判定: HTTP 200 + 响应体含 %PDF + X-Pdf-Pages>0 + pdftotext 能抽出文本。
无样本的格式（.doc/.ppt/.ods）明确标注"无样本未实测"，不计入通过数。
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.getenv("PREVIEW_BASE", "http://127.0.0.1:18095").rstrip("/")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.getenv("PREVIEW_EVIDENCE_DIR", os.path.join(HERE, "..", "logs", "preview", "matrix"))
os.makedirs(OUT, exist_ok=True)

CASES = [
    ("docx", "fixtures/cn-docx-direct.docx"),
    ("pptx", "fixtures/image-slide.pptx"),
    ("xlsx", "fixtures/big-table.xlsx"),
    ("pdf", "fixtures/cn-digital.pdf"),
]
NEGATIVE = [
    ("404-对象不存在", "fixtures/__not_exists__.docx", 404),
    ("415-不支持的格式", "fixtures/chart.png", 415),
    ("400-缺 key", None, 400),
]
NO_SAMPLE = ["doc", "ppt", "ods"]


def http(url, method="GET", body=None, timeout=120):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def pdftotext_first(path, chars=60):
    try:
        out = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", "-l", "1", path, "-"],
            capture_output=True,
            timeout=30,
        )
        text = out.stdout.decode("utf-8", "replace")
        flat = re.sub(r"\s+", " ", text).strip()
        return flat[:chars]
    except Exception as exc:  # noqa: BLE001
        return f"pdftotext 失败: {exc}"


def has_cjk(text):
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def main():
    rows = []
    print(f"# base = {BASE}")
    st, _, raw = http(f"{BASE}/healthz", timeout=30)
    health = {}
    try:
        health = json.loads(raw.decode())
    except Exception:  # noqa: BLE001
        pass
    print(f"# healthz {st} {json.dumps(health, ensure_ascii=False)}")
    if st != 200 or not health.get("ok"):
        print("FATAL: healthz 不健康")
        return 2

    passed = failed = 0
    for name, key in CASES:
        url = f"{BASE}/convert?key={urllib.parse.quote(key, safe='')}"
        t0 = time.time()
        st, hdr, body = http(url)
        cost = int((time.time() - t0) * 1000)
        pages = hdr.get("X-Pdf-Pages") or hdr.get("x-pdf-pages") or "0"
        is_pdf = body[:5] == b"%PDF-"
        local = os.path.join(OUT, f"{name}__{key.rsplit('/', 1)[-1]}.pdf")
        text = ""
        if st == 200 and is_pdf:
            with open(local, "wb") as fh:
                fh.write(body)
            text = pdftotext_first(local)
        ok = st == 200 and is_pdf and int(pages or 0) > 0 and bool(text)
        passed += 1 if ok else 0
        failed += 0 if ok else 1
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name:5s} key={key} http={st} pdf={is_pdf} "
            f"pages={pages} bytes={len(body)} convertMs={hdr.get('X-Convert-Ms', hdr.get('x-convert-ms'))} "
            f"src={hdr.get('X-Convert-Source', hdr.get('x-convert-source'))} wall={cost}ms cjk={has_cjk(text)}"
        )
        print(f"       text[0:60] = {text}")
        rows.append(
            {
                "format": name,
                "key": key,
                "http": st,
                "isPdf": is_pdf,
                "pages": int(pages or 0),
                "bytes": len(body),
                "convertMs": hdr.get("X-Convert-Ms"),
                "source": hdr.get("X-Convert-Source"),
                "cjk": has_cjk(text),
                "text60": text,
                "pass": ok,
            }
        )

    for label, key, expect in NEGATIVE:
        if key is None:
            st, _, body = http(f"{BASE}/convert")
        else:
            st, _, body = http(f"{BASE}/convert?key={urllib.parse.quote(key, safe='')}")
        ok = st == expect
        passed += 1 if ok else 0
        failed += 0 if ok else 1
        detail = body[:160].decode("utf-8", "replace")
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: http={st} expect={expect} body={detail}")
        rows.append({"format": label, "http": st, "expect": expect, "pass": ok})

    # POST /convert 与 /stream（GientechStreamReader 契约）各一次
    for path, payload in (
        ("/convert", {"objectKey": CASES[0][1]}),
        ("/stream", {"convertedFilePath": "/preview/convert?key=" + CASES[1][1], "pageNo": 1, "pageSize": 5}),
    ):
        st, hdr, body = http(f"{BASE}{path}", method="POST", body=payload)
        ok = st == 200 and body[:5] == b"%PDF-"
        passed += 1 if ok else 0
        failed += 0 if ok else 1
        print(f"[{'PASS' if ok else 'FAIL'}] POST {path}: http={st} pdf={body[:5] == b'%PDF-'} pages={hdr.get('X-Pdf-Pages')}")
        rows.append({"format": f"POST {path}", "http": st, "pass": ok})

    print(f"\n# 无样本未实测: {', '.join('.' + e for e in NO_SAMPLE)}（不勾选）")
    print(f"# RESULT passed={passed} failed={failed}")
    with open(os.path.join(OUT, "matrix.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {"base": BASE, "healthz": health, "rows": rows, "passed": passed, "failed": failed},
            fh,
            ensure_ascii=False,
            indent=2,
        )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
