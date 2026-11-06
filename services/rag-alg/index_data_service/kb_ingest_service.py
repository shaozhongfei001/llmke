"""知识库摄取触发服务：解析完成后，把同一份快照双路消费（搜索 + 图谱）。

为什么单独一个 HTTP 服务
-----------------------
解析（doc2md）与索引/图谱是两个容器，跨容器 import 会把部署绑死。Java 侧解析完成后
只需 POST 一次，本服务负责"封快照 → 投影 → 按库建图"。

调用方（Java rag-index-service 解析成功回调）传：
    {"kb": "kb_9", "file_id": 333, "doc2md_dir": "<doc2md 产物目录>",
     "file_name": "x.docx", "file_path": "...", "file_size": 1234, "source": "..."}

边界（如实写在响应里，不粉饰）
----------------------------
- 不重新解析：doc2md_dir 不是合规四件套就拒绝（`ARTIFACT_*`），不在这里兜底解析；
- 不写 ES/Milvus：第一路只返回"可直接落库的载荷"，落地由索引层负责；
- 图这一路失败不回滚已封好的快照，但响应里 `status=PARTIAL` + `graph.error` 写明原因。

启动：
    PYTHONPATH=services/rag-alg/index_data_service \
      uvicorn kb_ingest_service:app --host 127.0.0.1 --port 18096
"""

import hashlib
import os
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ingest_pipeline import kb_pipeline as K
from parse_artifact.store import ArtifactRefused
from rag_projection.projection import ProjectionRefused

SCHEMA = "llmke.kb-ingest.v1"
DEFAULT_STORE_ROOT = ".artifacts/artifact-store"

# 复用 scripts/ 下的 doc2md 编排（解析 → 四件套 → 双路消费），避免两处各写一遍
_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

DEFAULT_MINIO_ENDPOINT = "http://127.0.0.1:19000"


def _store_root() -> str:
    return os.environ.get("LLMKE_ARTIFACT_STORE") or DEFAULT_STORE_ROOT


def _producer_inputs(doc2md_dir: Path) -> Dict[str, Any]:
    """构造产物指纹输入。

    `runtime_lock_hash` / `config_hash` 取真实文件哈希（不填占位值）：
    没有真实指纹就说明部署基线不明，产物绑定从第一步就不可复核。
    """
    lock = os.environ.get("LLMKE_DOC2MD_LOCK")
    config = os.environ.get("LLMKE_DOC2MD_CONFIG")
    if not (lock and os.path.isfile(lock)):
        raise K.PipelineRefused(
            "PRODUCER_LOCK_MISSING",
            "缺少 LLMKE_DOC2MD_LOCK（doc2md 冻结锁文件路径），无法证明解析基线")
    if not (config and os.path.isfile(config)):
        raise K.PipelineRefused(
            "PRODUCER_CONFIG_MISSING",
            "缺少 LLMKE_DOC2MD_CONFIG（doc2md 配置路径），无法证明解析配置")
    return {
        "source_revision": os.environ.get("LLMKE_DOC2MD_REVISION", "unknown"),
        "parser_profile": os.environ.get("LLMKE_DOC2MD_PROFILE", "default_v1"),
        "runtime_lock_hash": hashlib.sha256(Path(lock).read_bytes()).hexdigest(),
        "config_hash": hashlib.sha256(Path(config).read_bytes()).hexdigest(),
        "model_fingerprints": [],
    }


def _resp(code: int, msg: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"schema": SCHEMA, "code": code, "msg": msg, "data": data}


def _download_minio(file_url: str, dest_dir: Path) -> Path:
    """把平台上文件的 MinIO URL 下载到本地。

    URL 形如 `http://127.0.0.1:19000/<bucket>/<object_key>`（实测自 knowledge_base_list.file_path）。
    MinIO 对匿名 GET 返回 403，必须带凭据；凭据从环境变量取（R12_MINIO_ACCESS_KEY/SECRET）。
    """
    import boto3
    from botocore.client import Config

    parsed = urllib.parse.urlparse(file_url)
    if not parsed.scheme.startswith("http"):
        raise K.PipelineRefused("FILE_URL_INVALID", f"不是 http(s) URL: {file_url}")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise K.PipelineRefused("FILE_URL_INVALID", f"URL 缺少 bucket/object: {file_url}")
    bucket, object_key = parts[0], "/".join(parts[1:])

    access = os.environ.get("R12_MINIO_ACCESS_KEY")
    secret = os.environ.get("R12_MINIO_SECRET_KEY")
    if not (access and secret):
        raise K.PipelineRefused(
            "MINIO_CREDENTIALS_MISSING",
            "缺少 R12_MINIO_ACCESS_KEY / R12_MINIO_SECRET_KEY，无法下载原件")
    endpoint = os.environ.get("LLMKE_MINIO_ENDPOINT", DEFAULT_MINIO_ENDPOINT)

    client = boto3.client(
        "s3", endpoint_url=endpoint,
        aws_access_key_id=access, aws_secret_access_key=secret,
        config=Config(signature_version="s3v4"), region_name="us-east-1")
    name = Path(object_key).name or "download.bin"
    target = dest_dir / name
    try:
        client.download_file(bucket, object_key, str(target))
    except Exception as exc:  # noqa: BLE001 - 下载失败要带原因，不能当成"没文件"
        raise K.PipelineRefused(
            "MINIO_DOWNLOAD_FAILED",
            f"{bucket}/{object_key}: {type(exc).__name__}: {exc}") from exc
    return target


def create_app(consume=None) -> FastAPI:
    # 用 consume_for_kb：本次文件并入该库清单后，用**该库全部文件**重建图谱，
    # 否则传第二个文件会把第一个文件的图谱覆盖掉（实测缺陷）。
    runner = consume or K.consume_for_kb
    app = FastAPI(title="LLMKE KB Ingest", version=SCHEMA)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "schema": SCHEMA,
            "status": "ok",
            "store_root": _store_root(),
            "graph_api": os.environ.get("LLMKE_V2_GRAPH_API", K.GRAPH_API_DEFAULT),
            "doc2md_lock": os.environ.get("LLMKE_DOC2MD_LOCK"),
            "doc2md_config": os.environ.get("LLMKE_DOC2MD_CONFIG"),
            "wired": ["POST /kb/ingest"],
        }

    @app.post("/kb/ingest")
    def ingest(body: Any = Body(default=None)) -> Dict[str, Any]:
        if not isinstance(body, dict):
            return _resp(400, "请求体必须是 JSON 对象")
        kb = str(body.get("kb") or "").strip()
        if not kb:
            return _resp(400, "缺少 kb（知识库标识）")
        raw_file_id = body.get("file_id")
        if raw_file_id in (None, ""):
            return _resp(400, "缺少 file_id（平台文件 id）")
        doc2md_dir = str(body.get("doc2md_dir") or "").strip()
        file_url = str(body.get("file_url") or "").strip()
        if not doc2md_dir and not file_url:
            return _resp(400, "需要 file_url（平台文件地址）或 doc2md_dir（已就绪的产物目录）")

        try:
            if file_url and not doc2md_dir:
                # 全自动模式：下载原件 → doc2md 解析（它自己产四件套）→ 双路消费
                from v2_ingest_doc2md import ingest_file

                config = os.environ.get("LLMKE_DOC2MD_CONFIG")
                if not (config and Path(config).is_file()):
                    return _resp(412, "缺少 LLMKE_DOC2MD_CONFIG（doc2md 配置路径）")
                tmp_root = Path(tempfile.mkdtemp(prefix="kb-ingest-"))
                try:
                    local_file = _download_minio(file_url, tmp_root)
                    result = ingest_file(
                        local_file, kb, raw_file_id,
                        config=Path(config),
                        store_root=_store_root(),
                        graph_api=body.get("graph_api")
                        or os.environ.get("LLMKE_V2_GRAPH_API", K.GRAPH_API_DEFAULT),
                        graph_root=body.get("graph_root"),
                        build_graph=bool(body.get("build_graph", True)),
                        revision=os.environ.get("LLMKE_DOC2MD_REVISION", "unknown"),
                        profile=os.environ.get("LLMKE_DOC2MD_PROFILE", "default_v1"),
                        # 解析预算（秒）：大文件（如 48MB 书籍）需显式放大，默认按
                        # ingest_file 的 1800 兜底；PDF 分支会把它再传给 magic-pdf。
                        timeout=int(body.get("timeout") or 1800),
                    )
                finally:
                    import shutil

                    shutil.rmtree(tmp_root, ignore_errors=True)
            else:
                # 产物目录模式：解析链路已经产出 doc2md 四件套，只做双路消费
                if not Path(doc2md_dir).is_dir():
                    return _resp(400, f"doc2md_dir 不存在：{doc2md_dir}")
                producer = _producer_inputs(Path(doc2md_dir))
                result = runner(
                    doc2md_dir,
                    _store_root(),
                    kb=kb,
                    file_id=raw_file_id,
                    index_name=body.get("index_name") or kb,
                    producer_inputs=producer,
                    file_name=body.get("file_name"),
                    file_path=body.get("file_path"),
                    file_size=body.get("file_size"),
                    source=body.get("source"),
                    build_graph=bool(body.get("build_graph", True)),
                    graph_root=body.get("graph_root"),
                    graph_api=body.get("graph_api"),
                )
        except ArtifactRefused as exc:
            # 产物不合规（缺件/哈希不符/解析失败）：400，调用方不应重试同一份产物
            return _resp(400, f"{exc.code}: {exc.detail}")
        except ProjectionRefused as exc:
            return _resp(400, f"{exc.code}: {exc.detail}")
        except K.PipelineRefused as exc:
            return _resp(502, f"{exc.code}: {exc.detail}")
        except Exception as exc:  # noqa: BLE001 - 失败要带原因，不伪装成功
            return _resp(500, f"{type(exc).__name__}: {exc}")

        # payloads 可能很大（整篇文档的块），默认不回传；需要时显式要
        if not body.get("include_payloads"):
            result["projection"].pop("payloads", None)

        code = 200 if result.get("status") == "OK" else 207
        return _resp(code, "摄取完成" if code == 200 else "搜索路完成、图谱路失败", result)

    return app


app = create_app()
