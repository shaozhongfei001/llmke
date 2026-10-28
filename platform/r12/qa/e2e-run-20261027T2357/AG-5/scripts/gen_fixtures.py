#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成负例夹具（只写 AG-5/evidence/fixtures/，不动仓库 fixtures）：
  encrypted.pdf        真加密 PDF（user password=123456，无密码打不开）
  bad-renamed.pdf      纯文本改后缀 .pdf
  bad-renamed.docx     随机字节改后缀 .docx
  truncated.docx       合法 docx 截断 60%
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import EVID, FIXTURES, dump, sha256

OUT = os.path.join(EVID, "fixtures")
os.makedirs(OUT, exist_ok=True)
res = {}

# 1) 加密 PDF
try:
    from pypdf import PdfReader, PdfWriter
    src = PdfReader(FIXTURES["pdf_digital"])
    w = PdfWriter()
    for p in src.pages:
        w.add_page(p)
    # 兼容 pypdf 新旧签名（旧版无 algorithm 关键字）
    try:
        w.encrypt(user_password="123456", owner_password="owner-123456", algorithm="RC4-128")
        enc_desc = "user_pw=123456 / RC4-128"
    except TypeError:
        w.encrypt("123456", "owner-123456")
        enc_desc = "user_pw=123456 / pypdf default"
    p = os.path.join(OUT, "encrypted.pdf")
    with open(p, "wb") as f:
        w.write(f)
    # 自证：无密码「取页面」必须失败（仅构造 PdfReader 不会抛，必须访问 pages）
    rd = PdfReader(p)
    try:
        len(rd.pages)
        need_pw = "no-error(异常：未真正加密)"
    except Exception as e:
        need_pw = f"{type(e).__name__}: {str(e)[:80]}"
    # 自证：带密码可取
    rd2 = PdfReader(p)
    rd2.decrypt("123456")
    paged_with_pw = len(rd2.pages)
    res["encrypted.pdf"] = {"path": p, "bytes": os.path.getsize(p), "sha256": sha256(p),
                            "encrypted_by": enc_desc, "read_without_pw": need_pw, "pages_with_pw": paged_with_pw, "is_encrypted": rd.is_encrypted}
except Exception as e:
    res["encrypted.pdf"] = {"error": f"{type(e).__name__}: {e}"}

# 2) 改后缀假 PDF（文本）
p = os.path.join(OUT, "bad-renamed.pdf")
with open(p, "w", encoding="utf-8") as f:
    f.write("这不是 PDF。这是一段纯文本，用于验证改后缀的伪造文件必须失败且可见。\n" * 20)
res["bad-renamed.pdf"] = {"path": p, "bytes": os.path.getsize(p), "sha256": sha256(p),
                          "note": "纯文本改后缀"}

# 3) 改后缀假 DOCX（随机字节）
p = os.path.join(OUT, "bad-renamed.docx")
with open(p, "wb") as f:
    f.write(bytes(range(256)) * 40)
res["bad-renamed.docx"] = {"path": p, "bytes": os.path.getsize(p), "sha256": sha256(p),
                           "note": "随机字节改后缀，非 zip 容器"}

# 4) 截断 docx
src = FIXTURES["docx_plain"]
raw = open(src, "rb").read()
p = os.path.join(OUT, "truncated.docx")
with open(p, "wb") as f:
    f.write(raw[: int(len(raw) * 0.6)])
res["truncated.docx"] = {"path": p, "bytes": os.path.getsize(p), "sha256": sha256(p),
                         "note": f"合法 docx 截断 60%（原 {len(raw)}B）"}

dump("fixtures.json", res, sub="S3")
print(os.path.join(EVID, "S3", "fixtures.json"))
