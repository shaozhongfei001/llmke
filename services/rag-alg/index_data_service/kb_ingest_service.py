"""知识库摄取触发服务：解析完成后，把同一份快照双路消费（搜索 + 图谱）。

为什么单独一个 HTTP 服务
-----------------------
解析（doc2md）与索引/图谱是两个容器，跨容器 import 会把部署绑死。Java 侧解析完成后
只需 POST 一次，本服务负责"封快照 → 投影 → 按库增量"。

调用方（Java rag-index-service 解析成功回调）传 `02-CONTRACTS` §1.1 的 `IngestRequest`：
    {"kb": "kb_9", "file_id": 290, "operation": "UPSERT",
     "doc2md_dir": "<doc2md 产物目录>", "file_name": "x.docx", ...}

边界（如实写在响应里，不粉饰）
----------------------------
- **不重新解析**：解析只发生在 doc2md 一次。P4-L12 起 `file_url` 仅作元数据保留，
  **不得触发第二次解析**（原 `:158-185` 的「下载原件 → 重跑 doc2md」分支已删除）；
- 不写 ES/Milvus：写入计划由 `index_writer.build` 产出，落地由索引层负责；
- 图这一路失败不回滚已封好的快照，但响应里 `status=PARTIAL` + `graph.error` 写明原因。

错误码 → HTTP
-------------
唯一一张表 `ERROR_HTTP`（契约 §5 + 表外白名单），**不许第二套**。
`ProjectionRefused` **不得整体映射**：它的 12 个 code 跨三类语义
（`ARTIFACT_*` 是调用方产物问题 400；`POLICY_INVALID`/`PROJECTION_MODE_INVALID` 是服务端配置 500；
`PROJECTION_COVERAGE_LOST`/`PROJECTION_EMPTY_CHUNK` 是算法问题 500），
一律 400 会让调用方拿着同一份产物反复重试（P4-L12 修掉的真实缺陷）。

启动：
    PYTHONPATH=services/rag-alg/index_data_service \
      uvicorn kb_ingest_service:app --host 127.0.0.1 --port 18096
"""

import hashlib
import logging
import os
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ingest_pipeline import graph_client
from ingest_pipeline import kb_pipeline as K
from ingest_pipeline.kb_delta import KbDeltaRefused, KbDeltaService
from parse_artifact.store import ArtifactRefused
from rag_projection.projection import ProjectionRefused

logger = logging.getLogger(__name__)

# 契约 §1.2 的响应顶层键字面就叫 `schema`；Pydantic 会警告「与 BaseModel.schema 同名」。
# 键名不能改（对 Java 是契约），故只精确屏蔽这一条告警，其余告警照常可见。
warnings.filterwarnings("ignore", message='Field name "schema"', category=UserWarning)

SCHEMA = "llmke.kb-ingest.v1"                     # 健康检查沿用（不对外承诺）
SCHEMA_REQUEST = "llmke.kb-ingest.request/1"      # 契约 §1.1
SCHEMA_RESULT = "llmke.kb-ingest.result/1"        # 契约 §1.2
DEFAULT_STORE_ROOT = ".artifacts/artifact-store"

KB_PATTERN = r"^[a-zA-Z0-9_]+$"


# ---------------------------------------------------------------- 错误码 → HTTP
# A · 契约 §5 的 11 条（逐条对齐，不得漏）
ERROR_HTTP: Dict[str, int] = {
    "DOC2MD_ARTIFACT_INCOMPLETE": 400,
    "SOURCE_DIVERGED": 409,
    "KB_STATE_CORRUPT": 500,
    "CURSOR_CONFLICT": 409,
    "NO_BASELINE_SNAPSHOT": 422,
    "ALL_REVOKED": 422,
    "STALE_FENCING": 409,
    "DELTA_INCONSISTENT": 500,
    "COMMUNITY_INVALID": 207,
    "GRAPH_UNREACHABLE": 502,
    "INDEX_WRITE_FAILED": 502,
    # `ProjectionRefused` 的 8 条 `ARTIFACT_*`：语义是「调用方产物不合法」→ 400，
    # 与 `DOC2MD_ARTIFACT_INCOMPLETE` 同族。**逐条列出**而不是按前缀/类型整体映射，
    # 因为 `ProjectionRefused` 跨三类语义（另 4 条是服务端问题，见下面白名单）。
    "ARTIFACT_ID_MISSING": 400,
    "ARTIFACT_MANIFEST_MISSING": 400,
    "ARTIFACT_PART_MISSING": 400,
    "ARTIFACT_IR_UID_MISMATCH": 400,
    "ARTIFACT_SPAN_MISMATCH": 400,
    "ARTIFACT_SPAN_OUT_OF_RANGE": 400,
    "ARTIFACT_SPAN_OVERLAP": 400,
    "ARTIFACT_TEXT_HASH_MISMATCH": 400,
    # B · 表外白名单（TL 14:1x 裁定，每行都带理由）
    "PROJECTION_NOT_APPLICABLE": 422,   # 该文件无可投影内容，前提不满足（同 ALL_REVOKED 族）
    "DOCS_EMPTY": 422,                  # 无可建图块，前提不满足
    "KB_REQUIRED": 422,                 # 请求缺 kb，调用方漏传
    "GRAPH_API_UNREACHABLE": 502,       # 契约 GRAPH_UNREACHABLE 的别名（L7 既有命名，未改名）
    "GRAPH_BUILD_NOT_BUILT": 502,       # 18094 返回非成功体
    # 以下 4 条属服务端问题：现状被一律映射成 400，是 P4-L12 修掉的真实缺陷。
    # 注意：若将来 chunk_chars/overlap 等 policy 参数进请求体，POLICY_INVALID 须改回 400。
    "POLICY_INVALID": 500,              # 服务端计划参数非法（chunk_chars/overlap）
    "PROJECTION_COVERAGE_LOST": 500,    # 投影漏字，算法问题，数据不完整
    "PROJECTION_EMPTY_CHUNK": 500,      # 切出空块，算法问题
    "PROJECTION_MODE_INVALID": 500,     # INGEST_PROJECTION_MODE 配置错误，服务端问题
}

# 动态 code：`GRAPH_BUILD_HTTP_<status>` 这类带后缀的按前缀匹配
ERROR_HTTP_PREFIXES: Dict[str, int] = {
    "GRAPH_BUILD_HTTP_": 502,
}


def http_status_for(exc: BaseException, *, kb: Optional[str] = None,
                    artifact_id: Optional[str] = None) -> int:
    """**唯一**的错误 → HTTP 出口。查表，绝不按异常类型「猜」。

    - `ArtifactRefused` 一族整体 400（40+ code 同属「产物不合法」，逐条抄必然过期）；
    - `ProjectionRefused` **必须按 code 查表**（跨三类语义，整体映射就是把 bug 换个位置）；
    - 表外 / code 为 None → 500，并把 **code 原文 + kb + artifact_id** 写进日志。
    """
    if isinstance(exc, ArtifactRefused):
        return ERROR_HTTP["DOC2MD_ARTIFACT_INCOMPLETE"]

    code = getattr(exc, "code", None)
    if isinstance(code, str):
        if code in ERROR_HTTP:
            return ERROR_HTTP[code]
        for prefix, http in ERROR_HTTP_PREFIXES.items():
            if code.startswith(prefix):
                return http
    logger.error(
        "未登记的错误码按 500 处理：code=%r type=%s kb=%r artifact_id=%r detail=%r",
        code, type(exc).__name__, kb, artifact_id, getattr(exc, "detail", None))
    return 500


# ---------------------------------------------------------------- 请求 / 响应模型
class Operation(str, Enum):
    UPSERT = "UPSERT"
    DELETE = "DELETE"
    FULL_REBUILD = "FULL_REBUILD"


class RequestedMode(str, Enum):
    AUTO = "auto"
    DELTA = "delta"
    FULL = "full"
    SKIP_IF_FRESH = "skip_if_fresh"


class IngestRequest(BaseModel):
    """`02-CONTRACTS` §1.1。`extra="forbid"`：未知字段**拒绝**而不是悄悄忽略。"""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    kb: str = Field(pattern=KB_PATTERN)
    file_id: Any
    operation: Operation = Operation.UPSERT
    doc2md_dir: Optional[str] = None
    # 保留兼容：仅元数据展示，**不得触发第二次解析**（契约 §1.1）
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    source: Optional[str] = None
    index_name: Optional[str] = None
    build_graph: bool = True
    graph_root: Optional[str] = None
    graph_api: Optional[str] = None
    requested_mode: RequestedMode = RequestedMode.AUTO
    expected_cursor: Optional[str] = None
    include_payloads: bool = False
    timeout: int = 1800
    fallback_reason: Optional[str] = None
    # additive：内容指纹（用于 diff 判 changed）；缺省时按「可能已变」处理，宁可重摄取
    content_hash: Optional[str] = None
    manifest_path: Optional[str] = None
    parser_fingerprint: Optional[str] = None

    @model_validator(mode="after")
    def _check_operation(self):
        if self.operation in (Operation.UPSERT.value, Operation.UPSERT) and not self.doc2md_dir:
            raise ValueError("UPSERT 必须带 doc2md_dir（解析只发生在 doc2md 一次）")
        if self.operation in (Operation.FULL_REBUILD.value, Operation.FULL_REBUILD) \
                and not (self.fallback_reason or "").strip():
            raise ValueError("FULL_REBUILD 必须带 fallback_reason（禁止静默降级）")
        if self.operation in (Operation.UPSERT.value, Operation.UPSERT) \
                and self.doc2md_dir and not Path(self.doc2md_dir).is_dir():
            # 目录不存在属调用方前提不满足；这里只校验形状，存在性在 plan 里由 store 判
            return self
        return self

    def to_service_request(self) -> Dict[str, Any]:
        data = self.model_dump()
        data["operation"] = str(getattr(self.operation, "value", self.operation))
        return data


class IngestResult(BaseModel):
    """`02-CONTRACTS` §1.2。全量/增量**同一模型**，字段集不随 operation 变化（B6）。

    刻意只放 4 个顶层键：`IngestPlan` 是编排中间产物，**不得**出现在这里（TL Q2）。
    """

    model_config = ConfigDict(extra="forbid")

    schema: str = SCHEMA_RESULT
    code: int
    msg: str
    data: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------- 现有助手
def _write_targets() -> Dict[str, Any]:
    """写入端点是否已配置（纯读 env，不连网、不实例化服务）。"""
    from ingest_pipeline.kb_delta import write_targets_configured

    return write_targets_configured()


def _store_root() -> str:
    return os.environ.get("LLMKE_ARTIFACT_STORE") or DEFAULT_STORE_ROOT


def _delta_runner(graph_api, graph_root):
    """delta runner：18096 → 18094 `POST /v2/graph/delta`（L12 的 `self._delta` 注入点）。

    L12 未配 runner 时 DELETE 会停在 `PARTIAL / state_committed=false`（撤权已发、状态未落）；
    A 段必须配，否则 A4 不成立。失败抛 `PipelineRefused`，由错误码表统一映射。
    """
    def runner(plan):
        return graph_client.post_graph_delta(
            plan.kb, plan.wanted_docs, removed=plan.removed,
            set_digest=(plan.diff or {}).get("set_digest"),
            requested_mode=("full" if (plan.diff or {}).get("reason") == "FULL_REBUILD_REQUESTED"
                            else "auto"),
            # 必须转发调用方给的值：18094 对 `requested_mode=full` 缺它就 422
            # （`DeltaRequest._check_full_reason`，禁止静默走全量）。
            fallback_reason=plan.fallback_reason, root=graph_root, graph_api=graph_api)
    return runner


def _fence_revoke(graph_api, graph_root=None):
    """撤权：18096 → 18094 `POST /v2/fence/revoke`（契约 §3 端点，A 段补齐）。

    注意：撤权只在 18094 侧生效并落盘；18096 不持有 `FenceState`。

    **必须带 root**：不带就落到 18094 进程 env 的图根（生产）。
    P4-L13-C 事故：影子 DELETE 的撤权写进了生产 `fence.json`。
    """
    def revoke(file_ids, kb=""):
        return graph_client.post_fence_revoke(
            kb, file_ids, root=graph_root, graph_api=graph_api)
    return revoke


def _build_service(graph_api=None, graph_root=None) -> KbDeltaService:
    graph_api = graph_api or os.environ.get("LLMKE_V2_GRAPH_API", K.GRAPH_API_DEFAULT)
    graph_root = graph_root or os.environ.get("LLMKE_V2_GRAPH_ROOT")
    return KbDeltaService(
        _store_root(),
        producer_inputs_provider=_producer_inputs,
        es_base=os.environ.get("LLMKE_ES_BASE_URL"),
        milvus_base=os.environ.get("LLMKE_MILVUS_BASE_URL"),
        delta=_delta_runner(graph_api, graph_root),
        revoke=_fence_revoke(graph_api, graph_root),
    )


def _producer_inputs() -> Dict[str, Any]:
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
    return {"schema": SCHEMA_RESULT, "code": code, "msg": msg, "data": data}


def _notify_callback(result: Dict[str, Any]) -> None:
    """回调 Java `/index/parseTask/callback`（带 `X-Internal-Token`）。

    **本 loop 只留调用点，不实现回写**（`T-D2MD-13`）：Java 侧的 `TaskReq` 与
    token 校验（`AuthFilter` fail-closed）已就绪，但 18096 尚未启用，
    现在发请求只会制造"看似回调成功"的假象。
    """
    logger.info("callback 预留调用点：T-D2MD-13 实现回写，本次不发送（status=%s）",
                result.get("status"))


def create_app(consume=None, service=None) -> FastAPI:
    """建 FastAPI 应用。

    `consume` / `service` 都是注入缝：`service` 优先（P4-L12 起的编排入口），
    `consume` 保留给旧调用方/测试（等价于 `service.run` 的简化替身）。
    """
    if service is None:
        service = _build_service()
        service_is_default = True
    else:
        service_is_default = False
    runner = consume
    app = FastAPI(title="LLMKE KB Ingest", version=SCHEMA)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])

    @app.get("/health")
    def health() -> Dict[str, Any]:
        """liveness + readiness 分开（TL 15:2x 要求）。

        - **HTTP 恒 200**：这是 liveness。`degraded` 只写在 body 里——
          若这里返 503，`r12-watchdog.sh` / 启动探针会把它当「进程挂了」反复重启，
          形成「服务其实正常但被 watchdog 杀掉」的死循环。
        - **readiness 由 body 的 `status` + `write_targets.configured` 表达**；
          启动自检脚本据此 `exit 1`，不放量。
        - 惰性 fail-closed（写入端点未配置时首次写入即拒）必须有这个信号，
          否则就退化成「静默带病运行」。
        """
        targets = _write_targets()
        ready = bool(targets.get("configured"))
        return {
            "schema": SCHEMA,
            "status": "ok" if ready else "degraded",
            "write_targets": targets,
            "store_root": _store_root(),
            "graph_api": os.environ.get("LLMKE_V2_GRAPH_API", K.GRAPH_API_DEFAULT),
            "doc2md_lock": os.environ.get("LLMKE_DOC2MD_LOCK"),
            "doc2md_config": os.environ.get("LLMKE_DOC2MD_CONFIG"),
            "wired": ["POST /kb/ingest"],
        }

    @app.post("/kb/ingest", response_model=IngestResult)
    def ingest(req: IngestRequest, response: Response) -> Dict[str, Any]:
        kb = req.kb
        artifact_id = None
        try:
            payload = req.to_service_request()
            if runner is not None:
                # 兼容缝：旧的单函数 runner（生产默认走 service）
                result = runner(req.doc2md_dir, _store_root(),
                                **{k: v for k, v in payload.items()
                                   if k in ("kb", "file_id", "index_name", "file_name",
                                            "file_path", "file_size", "source", "build_graph",
                                            "graph_root", "graph_api")},
                                producer_inputs=_producer_inputs())
            else:
                # 契约 §1.1 已有 graph_root / graph_api；service 路径原先只在启动时把
                # env 绑进 _delta_runner 闭包，请求里给的值被静默忽略。与旧 runner 缝对齐：
                # 请求给了就按请求绑定，没给仍回退 env；注入 service 的调用方不受影响。
                active_service = service
                if service_is_default and (req.graph_root or req.graph_api):
                    active_service = _build_service(
                        graph_api=req.graph_api, graph_root=req.graph_root)
                result = active_service.run(payload)
                artifact = (result or {}).get("artifact") or {}
                artifact_id = artifact.get("artifact_id")
        except Exception as exc:  # noqa: BLE001 - 失败要带原因，不伪装成功
            http = http_status_for(exc, kb=kb, artifact_id=artifact_id)
            code = getattr(exc, "code", None) or type(exc).__name__
            detail = getattr(exc, "detail", "") or str(exc)
            message = f"{code}: {detail}" if detail else str(code)
            response.status_code = http      # 返回 dict 只会有 200，必须显式设码
            # 失败也必须把「已写的一侧」带出去（契约 §5 要求显式记录补偿，不得只 log）
            payload = getattr(exc, "payload", None)
            return _resp(http, message, payload if isinstance(payload, dict) else None)

        status = (result or {}).get("status")
        # 契约 §1.2：SKIPPED_FRESH 是 200（不是 207）；只有 PARTIAL 才是 207
        code = 200 if status in ("OK", "SKIPPED_FRESH") else 207
        if code == 200:
            msg = "摄取完成" if status == "OK" else "内容未变化，跳过（SKIPPED_FRESH）"
        else:
            msg = "搜索路完成、图谱路失败（PARTIAL）"
        _notify_callback(result or {})
        response.status_code = code
        return _resp(code, msg, result)

    return app


app = create_app()
