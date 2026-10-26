#!/usr/bin/env python3
"""R13 Office -> PDF 预览转换服务（容器内 LibreOffice，端口 18095）。

对外路径（nginx: location /preview/ -> http://127.0.0.1:18095/，前缀被剥掉）：
  GET  /healthz                                  -> {"ok": true, "filters": [...]}
  GET  /convert?key=<bucket/object>              -> application/pdf
  POST /convert   {"objectKey": "..."} / {"key": "..."} -> application/pdf
  POST /stream    {"convertedFilePath": "...", "pageNo": n, "pageSize": m}
                                                 -> application/pdf
     （兼容 @gientech/modual GientechStreamReader：它把 convertedFilePath 原样 POST 回来，
       读取到的 arraybuffer 由 pdf.js 整体解析，因此每次返回整份 PDF 即可。）

设计约束：
  * 宿主 LibreOffice 缺 writer/impress 过滤器（无 sudo 不能装），故转换必须在容器内做；
  * MinIO 匿名读已撤销，必须 AK/SK 直读（不经过 Java 网关，避免 /stream 只支持 pdf/html/md）；
  * 每请求独立 -env:UserInstallation，避免 LO profile 锁；转换超时 60s 并 kill 进程组；
  * 同对象按 ETag 做进程内 LRU 缓存（reader 会按页反复请求同一文档）。
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import threading
import time
import uuid
from collections import OrderedDict
from typing import Iterable, Optional, Tuple
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Query, Request, Response
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel

# ---------------------------------------------------------------- 配置

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "127.0.0.1:19000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "r12minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "R12minio#2026local")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "r12-rag")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("1", "true", "yes")

CONVERT_TIMEOUT = int(os.getenv("CONVERT_TIMEOUT", "60"))
MAX_OBJECT_BYTES = int(os.getenv("MAX_OBJECT_BYTES", str(300 * 1024 * 1024)))
MAX_CONCURRENT_CONVERSIONS = int(os.getenv("MAX_CONCURRENT_CONVERSIONS", "2"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "900"))
CACHE_MAX = int(os.getenv("CACHE_MAX", "24"))

# 需要 LibreOffice 转换的扩展名 -> 导出过滤器
OFFICE_FILTERS = {
    "doc": "writer_pdf_Export",
    "docx": "writer_pdf_Export",
    "odt": "writer_pdf_Export",
    "rtf": "writer_pdf_Export",
    "ppt": "impress_pdf_Export",
    "pptx": "impress_pdf_Export",
    "odp": "impress_pdf_Export",
    "xls": "calc_pdf_Export",
    "xlsx": "calc_pdf_Export",
    "ods": "calc_pdf_Export",
    "csv": "calc_pdf_Export",
}
PASSTHROUGH_EXT = {"pdf"}

SOFFICE = os.getenv("SOFFICE_BIN", "soffice")
_conversion_slots = threading.BoundedSemaphore(max(1, MAX_CONCURRENT_CONVERSIONS))
_cache_lock = threading.Lock()
_cache: "OrderedDict[str, Tuple[float, bytes]]" = OrderedDict()


def _minio() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


# ---------------------------------------------------------------- key 归一

def _strip_bucket(path: str) -> Iterable[str]:
    """返回可尝试的对象键候选：先原样，再尝试去掉 bucket 前缀。"""
    yield path
    prefix = MINIO_BUCKET + "/"
    if path.startswith(prefix):
        yield path[len(prefix):]


def key_candidates(raw: str) -> list:
    if not raw:
        return []
    k = raw.strip()
    # 允许整条 URL（前端可能把 http://host/bucket/obj 或 /minio/obj 塞进来）
    if k.lower().startswith(("http://", "https://")):
        k = re.sub(r"^[a-zA-Z]+://[^/]+/?", "", k)
    elif k.startswith("/minio/"):
        k = k[len("/minio/"):]
    elif k.startswith("/preview/convert"):
        qs = k.split("?", 1)[1] if "?" in k else ""
        m = re.search(r"(?:^|&)key=([^&]*)", qs)
        k = unquote(m.group(1)) if m else ""
    k = unquote(k.split("?", 1)[0]).lstrip("/")
    if not k:
        return []
    out: list = []
    for c in _strip_bucket(k):
        if c and c not in out:
            out.append(c)
    return out


def ext_of(key: str) -> str:
    name = key.rsplit("/", 1)[-1]
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


# ---------------------------------------------------------------- MinIO 读取

def _fetch(key: str) -> Tuple[bytes, str, str]:
    """按候选键取对象，返回 (bytes, etag, 实际使用的 key)。"""
    client = _minio()
    last_err: Optional[Exception] = None
    for cand in key_candidates(key):
        try:
            st = client.stat_object(MINIO_BUCKET, cand)
        except S3Error as exc:
            last_err = exc
            if exc.code in ("NoSuchKey", "NoSuchBucket", "NoSuchObject"):
                continue
            raise
        if st.size and st.size > MAX_OBJECT_BYTES:
            raise HTTPException(413, f"对象过大：{st.size} bytes > 上限 {MAX_OBJECT_BYTES}")
        resp = client.get_object(MINIO_BUCKET, cand)
        try:
            data = resp.read()
        finally:
            resp.close()
            resp.release_conn()
        return data, (st.etag or "").strip('"'), cand
    raise HTTPException(404, f"MinIO 对象不存在：{MINIO_BUCKET}/{key}（{last_err}）")


# ---------------------------------------------------------------- 缓存

def _cache_get(ck: str) -> Optional[bytes]:
    now = time.time()
    with _cache_lock:
        hit = _cache.get(ck)
        if not hit:
            return None
        ts, data = hit
        if now - ts > CACHE_TTL:
            _cache.pop(ck, None)
            return None
        _cache.move_to_end(ck)
        return data


def _cache_put(ck: str, data: bytes) -> None:
    with _cache_lock:
        _cache[ck] = (time.time(), data)
        _cache.move_to_end(ck)
        while len(_cache) > CACHE_MAX:
            _cache.popitem(last=False)


# ---------------------------------------------------------------- 转换

def pdf_page_count(data: bytes) -> int:
    """优先 pdfinfo（poppler-utils），失败则回退正则计数。"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as fh:
            fh.write(data)
            fh.flush()
            out = subprocess.run(
                ["pdfinfo", fh.name], capture_output=True, timeout=20
            ).stdout.decode("utf-8", "replace")
        m = re.search(r"^Pages:\s+(\d+)", out, re.M)
        if m:
            return int(m.group(1))
    except Exception:  # noqa: BLE001 - 计页失败不应阻断预览
        pass
    return len(re.findall(rb"/Type\s*/Page[^s]", data))


def _run_soffice(workdir: str, src: str, export_filter: str) -> Tuple[bool, str]:
    profile = f"-env:UserInstallation=file://{workdir}/lo-profile-{uuid.uuid4().hex}"
    cmd = [
        SOFFICE,
        "--headless",
        "--norestore",
        "--invisible",
        "--nologo",
        "--nolockcheck",
        "--nodefault",
        "--nofirststartwizard",
        profile,
        "--convert-to",
        f"pdf:{export_filter}",
        "--outdir",
        workdir,
        src,
    ]
    env = dict(os.environ)
    env["HOME"] = workdir
    env["TMPDIR"] = workdir
    env["SAL_DISABLE_OPENCL"] = "1"
    env["SAL_USE_VCLPLUGIN"] = "svp"
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    try:
        out, _ = proc.communicate(timeout=CONVERT_TIMEOUT)
        return proc.returncode == 0, out.decode("utf-8", "replace")[-1500:]
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except Exception:  # noqa: BLE001
            proc.kill()
        proc.communicate()
        raise HTTPException(504, f"转换超时（>{CONVERT_TIMEOUT}s）")


def convert_to_pdf(key: str, data: bytes) -> Tuple[bytes, int, str]:
    """返回 (pdf bytes, 耗时 ms, 来源 cache|pass|lo)。"""
    ext = ext_of(key)
    etag_key = f"{MINIO_BUCKET}/{key}"

    if ext in PASSTHROUGH_EXT:
        if data[:1024].lower().find(b"%pdf-") < 0:
            raise HTTPException(415, "声明为 pdf 但内容不是合法 PDF")
        return data, 0, "pass"
    if ext not in OFFICE_FILTERS:
        raise HTTPException(
            415,
            f"不支持的格式 .{ext or '(无扩展名)'}；仅支持 "
            + ",".join(sorted(set(OFFICE_FILTERS) | PASSTHROUGH_EXT)),
        )

    workdir = tempfile.mkdtemp(prefix="r12pv-")
    acquired = False
    try:
        _conversion_slots.acquire()
        acquired = True
        started = time.time()
        src = os.path.join(workdir, f"input-{uuid.uuid4().hex}.{ext}")
        with open(src, "wb") as fh:
            fh.write(data)
        ok, log = _run_soffice(workdir, src, OFFICE_FILTERS[ext])
        pdfs = [f for f in os.listdir(workdir) if f.lower().endswith(".pdf")]
        if not ok or not pdfs:
            raise HTTPException(500, f"LibreOffice 转换失败（.{ext}）：{log.strip() or '无输出'}")
        out_path = os.path.join(workdir, pdfs[0])
        with open(out_path, "rb") as fh:
            pdf = fh.read()
        if not pdf[:1024].lower().startswith(b"%pdf") and b"%pdf-" not in pdf[:1024].lower():
            raise HTTPException(500, "转换产物不是合法 PDF（缺 %PDF 头）")
        return pdf, int((time.time() - started) * 1000), "lo"
    finally:
        if acquired:
            _conversion_slots.release()
        subprocess.run(["rm", "-rf", workdir], check=False)


def _serve(raw_key: str) -> Response:
    if not raw_key or not raw_key.strip():
        raise HTTPException(400, "缺少对象键：请提供 key/objectKey/convertedFilePath")
    data, etag, used_key = _fetch(raw_key)
    ck = f"{MINIO_BUCKET}/{used_key}@{etag}"
    cached = _cache_get(ck)
    if cached is not None:
        pdf, ms, src, pages = cached, 0, "hit", pdf_page_count(cached)
    else:
        pdf, ms, src = convert_to_pdf(used_key, data)
        _cache_put(ck, pdf)
        pages = pdf_page_count(pdf)
    if pages <= 0:
        raise HTTPException(500, "转换产物页数 <= 0")
    name = used_key.rsplit("/", 1)[-1].rsplit(".", 1)[0] + ".pdf"
    ascii_name = re.sub(r"[^A-Za-z0-9._-]", "_", name) or "preview.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{ascii_name}"; '
                f"filename*=UTF-8''{_rfc5987(name)}"
            ),
            "Content-Length": str(len(pdf)),
            "Cache-Control": "private, max-age=300",
            "X-Pdf-Pages": str(pages),
            "X-Convert-Ms": str(ms),
            "X-Convert-Source": src,
            "X-Source-Object": _header_safe(f"{MINIO_BUCKET}/{used_key}"),
        },
    )


def _rfc5987(name: str) -> str:
    from urllib.parse import quote

    return quote(name, safe="")


def _header_safe(value: str) -> str:
    """HTTP 头只能放 latin-1：中文对象名走百分号编码。"""
    try:
        value.encode("latin-1")
        return value
    except UnicodeEncodeError:
        return _rfc5987(value)


# ---------------------------------------------------------------- FastAPI

app = FastAPI(title="R13 office preview converter", version="1.0.0")


class ConvertBody(BaseModel):
    objectKey: Optional[str] = None
    key: Optional[str] = None
    convertedFilePath: Optional[str] = None
    bucket: Optional[str] = None
    pageNo: Optional[int] = None
    pageSize: Optional[int] = None


@app.get("/healthz")
def healthz() -> dict:
    filters = []
    for lib, name in (
        ("libswlo.so", "writer_pdf_Export"),
        ("libsclo.so", "calc_pdf_Export"),
        ("libsdlo.so", "impress_pdf_Export"),
    ):
        if os.path.exists(f"/usr/lib/libreoffice/program/{lib}"):
            filters.append(name)
    try:
        ver = subprocess.run(
            [SOFFICE, "--version"], capture_output=True, timeout=20
        ).stdout.decode("utf-8", "replace").strip()
    except Exception as exc:  # noqa: BLE001
        ver = f"unavailable: {exc}"
    return {
        "ok": bool(filters),
        "filters": filters,
        "soffice": ver,
        "bucket": MINIO_BUCKET,
        "minio": MINIO_ENDPOINT,
        "timeoutSeconds": CONVERT_TIMEOUT,
        "cache": {"entries": len(_cache), "ttl": CACHE_TTL, "max": CACHE_MAX},
    }


@app.get("/convert")
def convert_get(key: Optional[str] = Query(None, description="bucket/object 或 object")) -> Response:
    # 缺参不用 FastAPI 默认的 422，统一按契约返回 400
    return _serve(key or "")


@app.post("/convert")
def convert_post(body: ConvertBody) -> Response:
    raw = body.objectKey or body.key or body.convertedFilePath
    if not raw:
        raise HTTPException(400, "请求体需含 objectKey 或 key")
    return _serve(raw)


@app.post("/stream")
def stream_post(body: ConvertBody, request: Request) -> Response:
    """兼容 GientechStreamReader 的 stream 契约（只读 convertedFilePath，忽略分页）。"""
    raw = body.convertedFilePath or body.objectKey or body.key
    if not raw:
        raise HTTPException(400, "请求体需含 convertedFilePath")
    return _serve(raw)


@app.get("/")
def root() -> dict:
    return {
        "service": "r13-office-preview",
        "endpoints": ["/healthz", "/convert?key=", "POST /convert", "POST /stream"],
    }


if __name__ == "__main__":
    import uvicorn

    # R13-SEC-NET-01：默认只绑回环。预览服务不做鉴权（收口在 Java /previewStream），
    # 原来写死 0.0.0.0 等于同网段任意主机可直连取原文。
    uvicorn.run(app, host=os.getenv("PREVIEW_HOST", "127.0.0.1"),
                port=int(os.getenv("PORT", "18095")), log_level="info")
