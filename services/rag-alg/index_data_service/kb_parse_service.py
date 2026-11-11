"""上传回调入口（方案 A）：MinIO 原件 → doc2md 四件套 → 18096 消费一次。

为什么单独一个服务
------------------
Java 上传/解析成功后会 POST `remote.v2-ingest.url`，但 18096 的
`IngestRequest` 强制 UPSERT 必带 `doc2md_dir`（解析只发生一次），
而 `file_url` 只是元数据、不得触发第二次解析。所以必须有一个入口
负责**第一次解析**：把平台原件交给 doc2md，产出四件套目录，再交给
18096 做唯一的双路消费（搜索 + 按库图谱）。

本服务不写 ES / Milvus / 图，也不重复消费；`consume=False` 走的是
`scripts/v2_ingest_doc2md.py` 里新增的分支（默认行为不变）。

契约边界：`/kb/ingest` 的 `file_url` 语义不变；本端点接收的
`file_url` 是「待首次解析的原件地址」，两者不是同一个接口。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse

import boto3
import requests
from botocore.config import Config
from fastapi import FastAPI, Response
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SCHEMA = "llmke.kb-parse-and-ingest.v1"
DEFAULT_MINIO_ENDPOINT = os.environ.get("LLMKE_MINIO_ENDPOINT", "http://127.0.0.1:19000")
DEFAULT_INGEST_URL = os.environ.get("LLMKE_INGEST_URL", "http://127.0.0.1:18096/kb/ingest")
DEFAULT_CONFIG = Path(os.environ.get(
    "LLMKE_DOC2MD_CONFIG", "/home/szf/data/dev/doc2md/config/app.yaml"))

app = FastAPI(title="kb parse-and-ingest", version="1.0.0")


class ParseIngestRequest(BaseModel):
    """与 Java `RemoteV2IngestUtils.ingest` 发出的 JSON 对齐，附加可选控制字段。"""

    model_config = {"extra": "forbid"}

    kb: str = Field(min_length=1)
    file_id: Any
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    # 直连实测/无基线的新库可显式关闭图路；产品链默认 True，由 18096 决定 delta/full
    build_graph: bool = True
    timeout: int = 1800


def _minio_client():
    user = os.environ.get("LLMKE_MINIO_USER")
    password = os.environ.get("LLMKE_MINIO_PASSWORD")
    if not (user and password):
        raise RuntimeError("缺少 LLMKE_MINIO_USER / LLMKE_MINIO_PASSWORD，无法读取原件")
    return boto3.client(
        "s3", endpoint_url=DEFAULT_MINIO_ENDPOINT,
        aws_access_key_id=user, aws_secret_access_key=password,
        region_name="us-east-1", config=Config(signature_version="s3v4"),
    )


def _resolve_original(req: ParseIngestRequest, workdir: Path) -> Path:
    """把 Java 给的地址变成本地文件；只下载，不解析。"""
    addr = req.file_url or req.file_path
    if not addr:
        raise RuntimeError("file_url / file_path 均为空，没有原件可解析")

    local = Path(addr)
    if local.is_file():
        return local

    u = urlparse(addr)
    if u.scheme not in ("http", "https"):
        raise RuntimeError(f"原件地址既不是本地文件也不是 http(s)：{addr[:160]}")
    parts = [unquote(x) for x in u.path.strip("/").split("/") if x]
    if len(parts) < 2:
        raise RuntimeError(f"无法从地址解析 bucket/object：{addr[:160]}")
    bucket, key = parts[0], "/".join(parts[1:])

    obj = _minio_client().get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read()
    if not data:
        raise RuntimeError(f"原件为空：{bucket}/{key}")

    name = req.file_name or Path(key).name
    # 扩展名决定 doc2md 走 MarkItDown 还是 MinerU，必须保留
    if not Path(name).suffix:
        name = Path(key).name
    target = workdir / name
    target.write_bytes(data)
    return target


def _produce_doc2md_dir(local: Path, req: ParseIngestRequest) -> str:
    from v2_ingest_doc2md import ingest_file  # noqa: E402

    if not DEFAULT_CONFIG.is_file():
        raise RuntimeError(f"doc2md 配置不存在：{DEFAULT_CONFIG}")
    out = ingest_file(
        local, req.kb, req.file_id,
        config=DEFAULT_CONFIG,
        timeout=req.timeout,
        consume=False,  # 只产出四件套，消费交给 18096 一次
    )
    directory = out.get("doc2md_dir")
    if not directory or not Path(directory).is_dir():
        raise RuntimeError(f"doc2md 未产出可用四件套目录：{out}")
    return str(directory)


def _resp(code: int, msg: str, data=None) -> dict:
    return {"schema": SCHEMA, "code": code, "msg": msg, "data": data}


@app.get("/health")
def health() -> dict:
    return {
        "schema": SCHEMA,
        "status": "ok",
        "minio_endpoint": DEFAULT_MINIO_ENDPOINT,
        "ingest_url": DEFAULT_INGEST_URL,
        "doc2md_config": str(DEFAULT_CONFIG),
        "doc2md_config_exists": DEFAULT_CONFIG.is_file(),
        "credentials_present": bool(os.environ.get("LLMKE_MINIO_USER")
                                    and os.environ.get("LLMKE_MINIO_PASSWORD")),
        "wired": ["POST /kb/parse-and-ingest"],
    }


@app.post("/kb/parse-and-ingest")
def parse_and_ingest(req: ParseIngestRequest, response: Response) -> dict:
    workdir = Path(tempfile.mkdtemp(prefix="kb-parse-"))
    try:
        local = _resolve_original(req, workdir)
        doc2md_dir = _produce_doc2md_dir(local, req)

        payload = {
            "kb": req.kb,
            "file_id": req.file_id,
            "operation": "UPSERT",
            "doc2md_dir": doc2md_dir,
            "build_graph": req.build_graph,
        }
        if req.file_name:
            payload["file_name"] = req.file_name
        if req.file_path:
            payload["file_path"] = req.file_path
        if req.file_size is not None:
            payload["file_size"] = req.file_size

        upstream = requests.post(DEFAULT_INGEST_URL, json=payload, timeout=req.timeout)
        try:
            body = upstream.json()
        except ValueError:
            response.status_code = 502
            return _resp(502, f"18096 返回非 JSON：{upstream.text[:300]}")
        # 原样透传上游 code/msg/data，Java 的 classify(http, code) 依赖它
        response.status_code = upstream.status_code
        if isinstance(body, dict) and "code" in body:
            return body
        return _resp(upstream.status_code, "18096 响应缺 code", body)
    except Exception as exc:  # noqa: BLE001 - 失败必须带原因，不假成功
        response.status_code = 502
        return _resp(502, f"{type(exc).__name__}: {exc}")
    finally:
        # 只删下载用的临时目录；doc2md 四件套在 parsed_root，不能删
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=18097)
