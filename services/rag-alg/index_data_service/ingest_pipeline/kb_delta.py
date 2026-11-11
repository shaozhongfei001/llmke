"""P4-L12 · 库级增量：`diff → plan → commit`（18096 侧编排）。

设计边界（TL 14:1x 裁定）
------------------------
- `diff()` 的输入是 **doc2md 侧写的 `kb-manifest.json`**（`llmke.doc2md.kb-manifest/1`）。
  平台仓此前**没有任何** `kb-manifest` 读取代码（R-0 实测 0 命中），也不该跨仓 import
  `doc2md/backend/app/services/kb_diff.py` —— 那会把两个独立部署绑死
  （`kb_ingest_service.py:5-7` 自述的边界）。所以这里只**读文件、按 §4.3 判定优先级比对**。
- 没有 manifest 时**退化**为「单文件 vs `kb_state`」：此时 `removed` 只能来自显式
  `operation=DELETE`，**恒空不是 bug 而是数据来源决定**。响应必须带
  `diff_source: "manifest" | "request"` 如实暴露（TL Q1），不得让调用方以为做了全库 diff。
- 本模块**不 import pydantic / fastapi**（TL Q5，有 AST 静态断言）：18096 的两个解释器里
  只有 hipporag 装了 fastapi，编排逻辑必须能在 v2 主口径下真跑。
- 不引入第二套写入者：写入计划只由 `index_writer.build()` 产生，本模块不拼任何 ES/Milvus 请求体。
- `fence.revoke` 只有**调用点**：契约 §3 的 `POST /v2/fence/revoke` 端点**尚不存在**
  （`api.py` 只有 `GET /v2/fence`），且 18096 与 18094 是两个进程、拿不到对方内存态。
  → 本 loop 只保证「removed 非空时 revoke 先于 delta」的**调用序**，不代表线上已支持撤权。

顺序（不可调换）
----------------
```text
diff → (skip? 直接返回，三路零调用) → 封快照 → 投影 → index_writer.build
     → assert_same_artifact 闸门 → revoke? → wanted(内存预算) → delta → 状态事务(ACTIVE/REVOKED + cursor)
```
**快照+投影+写入计划**在事务前完成；**图（delta）也在事务前**，失败即不提交状态
（否则 cursor 已推进 → 重放变 SKIPPED_FRESH → 图永远建不起来）；
**ES/Milvus 只产计划、不写入**（L12 红线），响应里用 `index_write.applied=false` 如实标注。
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from graph_engine_adapter.artifact_binding import (
    ArtifactBindingError,
    assert_same_artifact,
)

from . import index_writer
from . import kb_pipeline as K

logger = logging.getLogger(__name__)

SCHEMA_KB_MANIFEST = "llmke.doc2md.kb-manifest/1"
SCHEMA_DIFF = "llmke.kb-diff/1"
SCHEMA_KB_STATE = K.KB_STATE_SCHEMA

STATUS_ACTIVE = "ACTIVE"
STATUS_REVOKED = "REVOKED"

DIFF_SOURCE_MANIFEST = "manifest"
DIFF_SOURCE_REQUEST = "request"

REASON_FULL_REBUILD = "FULL_REBUILD_REQUESTED"
REASON_FILE_SET_CHANGED = "FILE_SET_CHANGED"
REASON_CONTENT_CHANGED = "CONTENT_CHANGED"
REASON_PARSER_FP_CHANGED = "PARSER_FINGERPRINT_CHANGED"
REASON_NO_CHANGE = "NO_CHANGE"

# ---- 写入端点（A 段新增）：一个 base 同时支持 insert 与 delete 两个路径 ----
ES_BASE_ENV = "LLMKE_ES_BASE_URL"
MILVUS_BASE_ENV = "LLMKE_MILVUS_BASE_URL"
DEFAULT_ES_BASE = "http://127.0.0.1:19527"       # index_fulltext_service（**线上**）
DEFAULT_MILVUS_BASE = "http://127.0.0.1:19526"   # index_vector_service（**线上**）
# fail-closed（TL 15:1x 加固）：默认目标就是**真实线上索引服务**，
# 静默回退等于「env 漏配也照写线上」。必须显式开这个开关才允许回退默认值；
# 否则写入端点未配置时直接拒绝（错误码走 INDEX_WRITE_FAILED，502）。
ALLOW_DEFAULT_WRITE_ENV = "LLMKE_ALLOW_DEFAULT_WRITE_TARGET"
ES_INSERT_PATH = "/insert_fulltext_documents"
ES_DELETE_PATH = "/del_doc_by_col"
MILVUS_INSERT_PATH = "/insert_vector_documents_custom"
MILVUS_DELETE_PATH = "/del_doc_by_col"
# 两侧**都传 `file_id`，但理由不同**（C1 阶段用 `describe` 核出的服务端真值）：
# - 19527 会自己拼 `metadata.{field}.keyword` → 传裸名 `file_id`，落成 `metadata.file_id.keyword`；
# - 19526 原样拼 `expr=f'{col_name} in {values}'`，而 Milvus 集合是**平铺字段**
#   （`enable_dynamic_field=False`），文件 id 就是顶层 `file_id` → 也必须传 `file_id`。
#
# **不要因为「两侧值相同」就合并成一个常量后的语义**：绝不能传 `metadata.file_id`
# （ES 会拼成 `metadata.metadata.file_id.keyword` → 0 命中；Milvus 无该字段 → 删不到）。
# 原以为 Milvus 要带前缀，是按「ES 自动加前缀 ⇒ Milvus 显式加」推错了方向；
# 单测当时只断言「我们自己发出的值」，抓不到这类错 —— 只有真实 schema 能抓。
ES_DELETE_FIELD = "file_id"
MILVUS_DELETE_FIELD = "file_id"

PLAN_STATUS_READY = "READY"
PLAN_STATUS_SKIPPED = "SKIPPED_FRESH"

OPERATIONS = ("UPSERT", "DELETE", "FULL_REBUILD")


class KbDeltaRefused(K.PipelineRefused):
    """库级增量的拒绝：复用编排错误族，`code` 走 `kb_ingest_service.ERROR_HTTP` 查表。"""


@dataclass
class IngestPlan:
    """一次摄取的执行计划（**内部结构**，不得出现在响应模型字段里 —— TL Q2）。

    刻意用 dataclass 而不是 Pydantic：它是编排中间产物，不是对外契约；
    对外只有 `02-CONTRACTS` §1.2 的 7 个块。
    """

    kb: str
    status: str = PLAN_STATUS_READY
    diff: Dict[str, Any] = field(default_factory=dict)
    diff_source: str = DIFF_SOURCE_REQUEST
    cursor_before: Optional[str] = None
    snapshot: Optional[str] = None
    artifact: Optional[Dict[str, Any]] = None
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    write_plan: Any = None
    wanted_docs: List[Dict[str, Any]] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    projection_status: Optional[str] = None
    file_id: Any = None
    index_name: Optional[str] = None
    operation: str = "UPSERT"
    parser_fingerprint: Optional[str] = None
    binding: Optional[Dict[str, Any]] = None
    # 18094 的 `DeltaRequest` 校验：`requested_mode=full` 必须带 fallback_reason，
    # 否则 422（禁止静默走全量）。请求里给了就必须带到 runner，不能在中途丢。
    fallback_reason: Optional[str] = None

    @property
    def skipped(self) -> bool:
        return self.status == PLAN_STATUS_SKIPPED

    @property
    def has_write(self) -> bool:
        return self.write_plan is not None


def build_delete_body(*, side: str, target: str, file_id: Any,
                      col_name: str, col_values: List[str]) -> Dict[str, Any]:
    """构造并**校验**删除请求体（客户端侧拦截，不依赖服务端兜底）。

    为什么必须在客户端拦（R-0 实测两处服务端行为）：

    1. **删库高危**：19526 的 `del_doc_by_col` 在 `col_name` 为空但
       `collection_name` 非空时会 `coll.drop()` —— **整个集合消失**。一个字段拼错就够。
    2. **静默不删**：19527 的 `init_field_body` 会自己拼 `metadata.{field}.keyword`，
       若把 `metadata.file_id` 传给 ES，实际字段变成 `metadata.metadata.file_id.keyword`
       → 0 命中、接口仍返回 200、什么都没删。

    两侧期望的 `col_name` **相反**（ES 要裸名、Milvus 要带前缀），所以这里按 side 校验，
    不允许「统一成一个值」。
    """
    expected = ES_DELETE_FIELD if side == "es" else MILVUS_DELETE_FIELD
    if side not in ("es", "milvus"):
        raise _delete_refused(f"未知 side：{side!r}")
    if not str(target or "").strip():
        raise _delete_refused(f"{side}: 目标名为空，拒绝发送（防误删整库）")
    if not str(col_name or "").strip():
        # 19526 在 col_name 为空时会 drop 整个 collection
        raise _delete_refused(f"{side}: col_name 为空，拒绝发送（19526 会 drop 整个集合）")
    if col_name != expected:
        raise _delete_refused(
            f"{side}: col_name 必须是 {expected!r}，实际 {col_name!r}"
            + ("（19527 会自己拼 metadata.<field>.keyword，传前缀会变成双前缀 → 静默不删）"
               if side == "es" else "（19526 原样拼 expr，而 Milvus 集合是平铺字段，"
                                    "文件 id 是顶层 file_id；传 metadata.file_id 会找不到字段）"))
    values = list(col_values or [])
    if not values:
        raise _delete_refused(f"{side}: col_values 为空，拒绝发送")
    for value in values:
        if value is None or not str(value).strip() or not isinstance(value, (str, int)):
            raise _delete_refused(f"{side}: col_values 含非法值 {value!r}")
    values = [str(v).strip() for v in values]
    if str(file_id).strip() not in values:
        raise _delete_refused(f"{side}: col_values 必须只针对目标 file_id={file_id!r}")
    key = "index_name" if side == "es" else "collection_name"
    return {key: str(target).strip(), "col_name": expected, "col_values": values}


def _allow_default_write() -> bool:
    return str(os.environ.get(ALLOW_DEFAULT_WRITE_ENV) or "").strip().lower() in (
        "1", "true", "yes", "on")


def _resolve_write_base(side: str, given: Optional[str], default: str) -> str:
    """写入端点 base：显式值 > env > **仅当显式开关打开时**用默认值。

    默认值是**线上** 19527/19526。不设开关就回退默认 = 「env 漏配也照写线上」，
    而且测试只要忘了注入替身就会真的打到线上 —— 那是纪律不是防护，故 fail-closed。
    """
    if given and str(given).strip():
        return str(given).strip().rstrip("/")
    if _allow_default_write():
        logger.warning("写入端点 %s 未配置，按 %s=1 回退默认目标 %s（线上）",
                       side, ALLOW_DEFAULT_WRITE_ENV, default)
        return default
    raise KbDeltaRefused(
        "INDEX_WRITE_FAILED",
        f"{side} 写入端点未配置：需显式传入或设 "
        f"{ES_BASE_ENV if side == 'es' else MILVUS_BASE_ENV}；"
        f"默认目标 {default} 是线上服务，逐需 {ALLOW_DEFAULT_WRITE_ENV}=1 才允许回退")


def write_targets_configured() -> Dict[str, Any]:
    """给启动自检用：写入端点是否已配置（不实例化服务、不连网）。"""
    return {
        "es": bool(os.environ.get(ES_BASE_ENV)),
        "milvus": bool(os.environ.get(MILVUS_BASE_ENV)),
        "allow_default": _allow_default_write(),
        "configured": bool(os.environ.get(ES_BASE_ENV) and os.environ.get(MILVUS_BASE_ENV))
                      or _allow_default_write(),
        "env": [ES_BASE_ENV, MILVUS_BASE_ENV, ALLOW_DEFAULT_WRITE_ENV],
        "defaults": {"es": DEFAULT_ES_BASE, "milvus": DEFAULT_MILVUS_BASE},
    }


def _delete_refused(detail: str) -> "KbDeltaRefused":
    """删除参数不合法：刻意用**未登记**的 code → 走错误码表兜底（500 + 日志含原文）。

    这是本侧的编程错误（不是调用方的请求问题），不该伪装成 4xx 让调用方重试。
    """
    return KbDeltaRefused("DELETE_FIELD_INVALID", detail)


class _SidePlan:
    """把一份 `IndexWritePlan` 过滤成只含某一侧，供 `index_writer.apply` 分两次调用。

    只为满足「per-侧先删后写」的顺序，**不复制 apply 的实现**（写入者仍然只有一个）。
    """

    def __init__(self, plan: Any, side: str):
        self._plan = plan
        self._side = side

    @property
    def es_plan(self):
        return getattr(self._plan, "es_plan", []) if self._side == "es" else []

    @property
    def milvus_plan(self):
        return getattr(self._plan, "milvus_plan", []) if self._side == "milvus" else []

    def __getattr__(self, item: Any) -> Any:
        return getattr(self._plan, item)


def _canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class KbDeltaService:
    """库级增量服务：`diff` 算差异、`plan` 产计划、`commit` 落状态。

    所有外部动作（封快照 / 投影 / 写计划 / 撤权 / delta）都通过**注入**获得，
    默认接 `kb_pipeline` 的真实实现；测试注入替身即可断言「零调用」「调用序」。
    """

    def __init__(self, store_root, *, state_loader=None, state_txn=None,
                 commit_snapshot=None, project_snapshot=None,
                 build_wanted_docs=None, writer=None, revoke=None,
                 delta=None, producer_inputs_provider=None,
                 es_base=None, milvus_base=None, poster=None,
                 chunk_chars: int = K.DEFAULT_CHUNK_CHARS):
        self.store_root = store_root
        self._load_state = state_loader or (lambda: K._load_kb_state(store_root))
        self._state_txn = state_txn or (lambda: K._kb_state_txn(store_root))
        self._commit_snapshot = commit_snapshot or K.commit_snapshot
        self._project_snapshot = project_snapshot or K.project_snapshot
        self._build_wanted_docs = build_wanted_docs or K.build_wanted_docs
        self._writer = writer or index_writer
        self._revoke = revoke
        self._delta = delta
        # A 段：写入端点。base + 固定路径，insert 与 delete 共用同一个 base。
        # **fail-closed**：不静默回退默认（默认是线上 19527/19526）。
        # 构造期**不**解析（否则 import 就炸，连 /health 都拿不到，无法诊断）；
        # 真正使用（第一次写入）时才解析 → 未配置即 INDEX_WRITE_FAILED，绝不回退默认。
        # 启动期 fail-fast 由 B 段的启动自检 + `/health` 的 write_targets 承担。
        self._es_base_given = es_base
        self._milvus_base_given = milvus_base
        self._poster = poster or index_writer._post_json
        # 只在**真的要封快照**时才取（缺少 lock/config 属部署缺陷，不该拦住 DELETE/SKIP）
        self._producer_inputs = producer_inputs_provider
        self.chunk_chars = chunk_chars

    # ------------------------------------------------------------------ diff
    @property
    def es_base(self) -> str:
        """写入端点（ES）：显式参数 > env > **仅开关打开时**默认；未配置即拒绝。"""
        return _resolve_write_base("es", self._es_base_given or os.environ.get(ES_BASE_ENV),
                                   DEFAULT_ES_BASE)

    @property
    def milvus_base(self) -> str:
        return _resolve_write_base("milvus",
                                   self._milvus_base_given or os.environ.get(MILVUS_BASE_ENV),
                                   DEFAULT_MILVUS_BASE)


    def diff(self, kb: str, manifest_path: Optional[Path] = None, *,
             file_id: Any = None, content_hash: Optional[str] = None,
             operation: str = "UPSERT", full_rebuild: bool = False,
             parser_fingerprint: Optional[str] = None) -> Dict[str, Any]:
        """按 `02-CONTRACTS` §4.3 产 `DiffResult`（附加 `schema` / `diff_source`）。

        判定优先级（照契约，**不改顺序**）：
        `FULL_REBUILD_REQUESTED` > removed > added/changed > parser_fingerprint > `NO_CHANGE`。
        """
        if not kb:
            raise KbDeltaRefused("KB_REQUIRED", "diff 必须指定知识库")

        state = self._load_state()
        files = (state.get("kb") or {}).get(kb) or {}
        active = {str(fid): (entry or {}) for fid, entry in files.items()
                  if (entry or {}).get("status", STATUS_ACTIVE) == STATUS_ACTIVE}

        added: List[str] = []
        changed: List[str] = []
        removed: List[str] = []
        unchanged: List[str] = []
        prev_fingerprint: Optional[str] = None
        source = DIFF_SOURCE_REQUEST
        resulting: Dict[str, Dict[str, Any]] = dict(active)

        if manifest_path is not None:
            doc = self._read_manifest(manifest_path)
            prev_fingerprint = doc.get("parser_fingerprint")
            source = DIFF_SOURCE_MANIFEST
            incoming = {str(e.get("file_id")): e for e in doc.get("entries") or []
                        if str(e.get("status") or STATUS_ACTIVE) == STATUS_ACTIVE}
            added = sorted(set(incoming) - set(active))
            removed = sorted(set(active) - set(incoming))
            for fid in sorted(set(incoming) & set(active)):
                want = str(incoming[fid].get("sha256") or "")
                have = str(active[fid].get("content_hash") or "")
                if want and have and want != have:
                    changed.append(fid)
                else:
                    unchanged.append(fid)
            resulting = {fid: {"content_hash": str(e.get("sha256") or "")}
                         for fid, e in incoming.items()}
        else:
            fid = None if file_id in (None, "") else str(file_id).strip()
            if operation == "DELETE":
                if fid is None:
                    raise KbDeltaRefused("KB_REQUIRED", "DELETE 必须带 file_id")
                if fid in active:
                    removed = [fid]
                    resulting.pop(fid, None)
            else:
                if fid is None:
                    raise KbDeltaRefused("KB_REQUIRED", "UPSERT 必须带 file_id")
                if fid not in active:
                    added = [fid]
                else:
                    want = str(content_hash or "")
                    have = str(active[fid].get("content_hash") or "")
                    if not want or not have or want != have:
                        changed = [fid]
                    else:
                        unchanged = [fid]
                resulting[fid] = {"content_hash": str(
                    content_hash or (active.get(fid) or {}).get("content_hash") or "")}

        reason = self._reason(full_rebuild=bool(full_rebuild), added=added,
                              changed=changed, removed=removed,
                              parser_fingerprint=parser_fingerprint,
                              prev_fingerprint=prev_fingerprint)
        triples = sorted([kb, fid, str((entry or {}).get("content_hash") or "")]
                         for fid, entry in resulting.items())
        set_digest = _canonical_sha256(triples)
        cursor = "cursor-" + _canonical_sha256(
            {"kb": kb, "set_digest": set_digest, "reason": reason})

        return {
            "schema": SCHEMA_DIFF,
            "kb": kb,
            "added": added,
            "changed": changed,
            "removed": removed,
            "unchanged": unchanged,
            "cursor": cursor,
            "set_digest": set_digest,
            "reason": reason,
            # additive：数据来源如实暴露（TL Q1）。没有 manifest 时 removed 恒空，
            # 是「看不到全库文件集」而不是「没有文件被删」。
            "diff_source": source,
        }

    @staticmethod
    def _reason(*, full_rebuild: bool, added: List[str], changed: List[str],
                removed: List[str], parser_fingerprint: Optional[str],
                prev_fingerprint: Optional[str]) -> str:
        if full_rebuild:
            return REASON_FULL_REBUILD
        if removed or added:
            return REASON_FILE_SET_CHANGED
        if changed:
            return REASON_CONTENT_CHANGED
        if parser_fingerprint and prev_fingerprint and parser_fingerprint != prev_fingerprint:
            return REASON_PARSER_FP_CHANGED
        return REASON_NO_CHANGE

    @staticmethod
    def _read_manifest(manifest_path) -> Dict[str, Any]:
        path = Path(manifest_path)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise KbDeltaRefused("DOC2MD_ARTIFACT_INCOMPLETE",
                                 f"kb-manifest 不存在：{path}") from exc
        except (OSError, ValueError) as exc:
            raise KbDeltaRefused("DOC2MD_ARTIFACT_INCOMPLETE",
                                 f"kb-manifest 不可读：{path}: {exc}") from exc
        if not isinstance(doc, dict):
            raise KbDeltaRefused("DOC2MD_ARTIFACT_INCOMPLETE", f"{path}: 顶层必须是对象")
        if doc.get("schema") != SCHEMA_KB_MANIFEST:
            raise KbDeltaRefused(
                "DOC2MD_ARTIFACT_INCOMPLETE",
                f"{path}: schema={doc.get('schema')!r} 期望 {SCHEMA_KB_MANIFEST!r}")
        return doc

    # ------------------------------------------------------------ wanted docs
    def wanted_docs(self, kb: str) -> List[Dict[str, Any]]:
        """全库 wanted docs：**只读 `kb_state.chunks`**，不重新投影（B8）。

        `build_wanted_docs` 本身就是 §4.2 的唯一装配实现（L7 交付），这里只做转发 ——
        绝不为了「顺手补全」而调用 `project_snapshot`（那会让 `seq` 重排、pk 漂移）。
        """
        return self._build_wanted_docs(self._load_state(), kb)

    # ------------------------------------------------------------------ plan
    def plan(self, req: Dict[str, Any]) -> IngestPlan:
        """产执行计划：空 diff → `SKIPPED_FRESH` 且三路零调用（B1）。

        `req` 是 `IngestRequest.model_dump()` 的普通 dict（本函数不依赖 pydantic）。
        """
        kb = str(req.get("kb") or "").strip()
        if not kb:
            raise KbDeltaRefused("KB_REQUIRED", "摄取必须指定知识库")
        operation = str(req.get("operation") or "UPSERT").upper()
        if operation not in OPERATIONS:
            raise KbDeltaRefused("KB_REQUIRED", f"未知 operation：{operation!r}")
        file_id = req.get("file_id")
        index_name = req.get("index_name") or kb

        state = self._load_state()
        diff = self.diff(kb, req.get("manifest_path"), file_id=file_id,
                         content_hash=req.get("content_hash"), operation=operation,
                         full_rebuild=operation == "FULL_REBUILD",
                         parser_fingerprint=req.get("parser_fingerprint"))
        plan = IngestPlan(kb=kb, diff=diff, diff_source=diff["diff_source"],
                          cursor_before=state.get("cursor"),
                          removed=list(diff["removed"]), file_id=file_id,
                          index_name=index_name, operation=operation,
                          parser_fingerprint=req.get("parser_fingerprint"),
                          fallback_reason=req.get("fallback_reason"))

        if diff["reason"] == REASON_NO_CHANGE and operation != "FULL_REBUILD":
            plan.status = PLAN_STATUS_SKIPPED
            return plan

        if operation == "DELETE":
            # 删除不封快照、不投影、不产写入计划：只撤权 + 状态标 REVOKED。
            return plan

        doc2md_dir = req.get("doc2md_dir")
        if not doc2md_dir:
            raise KbDeltaRefused("DOC2MD_ARTIFACT_INCOMPLETE", "UPSERT 必须带 doc2md_dir")

        producer_inputs = req.get("producer_inputs")
        if producer_inputs is None and self._producer_inputs is not None:
            producer_inputs = self._producer_inputs()
        artifact, snapshot = self._commit_snapshot(
            doc2md_dir, self.store_root,
            producer_inputs=producer_inputs or {},
            artifact_id=req.get("artifact_id"))

        current = self._project_snapshot(snapshot, index_name=index_name,
                                        file_id=file_id, chunk_chars=self.chunk_chars)
        if getattr(current, "status", None) == "NOT_APPLICABLE":
            raise KbDeltaRefused(
                "PROJECTION_NOT_APPLICABLE",
                str((getattr(current, "stats", None) or {}).get("reason") or ""))
        chunks = list(getattr(current, "chunks", []) or [])

        binding_artifact = {**artifact, "file_id": str(file_id)}
        try:
            write_plan = self._writer.build(chunks, binding_artifact, kb=index_name,
                                            file_id=file_id)
        except index_writer.IndexWriterError as exc:
            raise KbDeltaRefused(exc.code, exc.detail) from exc

        # G2：同源闸门放在 build 与 apply 之间 —— 不一致时零写入（不重排写入顺序）
        binding = self._writer.bind_chunks(chunks, binding_artifact)
        try:
            assert_same_artifact(write_plan.binding, binding)
        except ArtifactBindingError as exc:
            raise K.SourceDiverged(str(exc)) from exc

        plan.artifact = artifact
        plan.snapshot = str(snapshot)
        plan.chunks = chunks
        plan.write_plan = write_plan
        plan.projection_status = getattr(current, "status", None)
        plan.binding = binding
        return plan

    # ---------------------------------------------------------------- commit
    def commit(self, plan: IngestPlan) -> Dict[str, Any]:
        """落状态：revoke → wanted（内存预算）→ **delta** → 状态事务。

        顺序为什么是「delta 在事务之前」（TL 14:2x 必改一）
        ---------------------------------------------------
        反例推演：若先提交状态再调 delta，delta 失败时 cursor 已推进 →
        Java 按 207 回写 RETRY → 重放时 diff 看到 `NO_CHANGE` → `SKIPPED_FRESH` →
        **图永远建不起来，而且每次重放都"成功"返回**（与 L9 的「指针悬空」同类：
        报成功但目标状态没达成）。所以：**delta 成功才提交状态，失败 cursor 不动。**

        `wanted_docs` 需要"应用后的状态"，但那时还不能写盘 →
        在 `copy.deepcopy(state)` 的 **prospective** 上应用一次（纯内存），
        拿它算 docs；delta 成功后再进 txn 真正应用。
        """
        if plan.skipped:
            return {
                "status": "SKIPPED_FRESH", "kb": plan.kb, "cursor": plan.cursor_before,
                "diff": plan.diff, "diff_source": plan.diff_source,
                "wanted_docs": [], "removed": [], "state_committed": False,
                "index_write": {"status": "NOT_APPLICABLE", "applied": False,
                                "required": False, "reason": "空 diff：未写任何索引"},
                "graph": {"result": None, "error": None},
                "state_path": str(self._kb_state_path()),
            }

        # 0) 内存预算：不写盘、无副作用，只为算 wanted docs。
        #    **必须在 revoke / 索引写入之前**：删到空库要「零副作用」拒绝
        #    （TL 20:2x 裁定 (b)：检测点前移到所有副作用之前）。
        prospective = copy.deepcopy(self._load_state())
        self._apply_plan(prospective, plan)
        wanted = self._build_wanted_docs(prospective, plan.kb)
        plan.wanted_docs = wanted

        # 删到空库：拒绝，且**一个副作用都不许发生**。
        # 为什么不在这一层「清空图」：契约 §5 用 ALL_REVOKED 表达「全撤权需人工介入」，
        # 且 rebuild 两处都拒绝生成空快照（rebuild.py:132-133 / :270-271）。
        # 之前 revoke 在 wanted 之前，导致「撤权已发、索引已删、状态未提交」的中间态。
        if not wanted:
            raise KbDeltaRefused(
                "ALL_REVOKED",
                "删到空库需人工介入（契约 §5 ALL_REVOKED）；本次零副作用："
                "未撤权、未改索引、状态未动")

        # B2：撤权必须早于 delta —— 先让可见性失效，再让图谱按新集合收敛。
        if plan.removed and self._revoke is not None:
            self._revoke(list(plan.removed), plan.kb)

        # 2) 搜索路真实写入：每侧「先删后写」（见 _apply_writes）
        index_write = self._apply_writes(plan)

        # 3) 图在状态事务**之前**（失败即不提交，见 docstring 反例推演）
        graph_result = None
        graph_error = None
        if self._delta is None:
            graph_error = ("delta_runner_not_configured: 未注入 delta runner，"
                           "图未建；不得报 OK")
        else:
            try:
                graph_result = self._delta(plan)
            except K.PipelineRefused as exc:
                graph_error = f"{exc.code}: {exc.detail}"
            except Exception as exc:  # noqa: BLE001 - 失败必须带原因返回
                graph_error = f"{type(exc).__name__}: {exc}"

        if graph_error is not None:
            # 状态完全不落盘 → cursor/version 不动 → 重放仍能看到同样的 diff
            return self._result(plan, status="PARTIAL", cursor=plan.cursor_before,
                                wanted=wanted, graph_result=graph_result,
                                graph_error=graph_error, index_write=index_write,
                                state_committed=False)

        # 3) 三路 + 图全部成功，才落状态并推进 cursor
        with self._state_txn() as state:
            self._apply_plan(state, plan)
            touched = state
        return self._result(plan, status=None, cursor=touched.get("cursor"),
                            wanted=wanted, graph_result=graph_result,
                            graph_error=None, index_write=index_write,
                            state_committed=True)

    # ---------------------------------------------------------------- 内部
    def _apply_writes(self, plan: IngestPlan) -> Dict[str, Any]:
        """真实写 ES/Milvus：每侧 **先删后写**，4 个 target 全删。

        顺序（TL 15:0x 裁定）::

            delete ES(2) → insert ES → delete Milvus(2) → insert Milvus

        - per-侧先删后写：避免「旧块与新块共存」被检索命中，也避免
          「ES 已删、Milvus 未删」的跨侧窗口被观察者看到；
        - **4 个 target 全删**：`{prefix}{kb}` 与 `{prefix}table_chunks_{kb}`，
          各 es/milvus —— 只删主集合会留下 `table_chunks_*` 残留
          （线上实测 `table_chunks_kb_9=2` 真实存在）；
        - 插入仍只走 `index_writer.apply`（**不引入第二套写入者**）：把它拆成
          「只 ES」「只 Milvus」两次调用，才能与 per-侧删除交错。
        """
        scope = self._writer.delete_scope(kb=plan.index_name or plan.kb,
                                          file_id=plan.file_id)
        targets = list(scope.get("targets") or [])
        fid = str(plan.file_id)
        completed: List[str] = []
        calls: List[Dict[str, Any]] = []
        deletes: List[Dict[str, Any]] = []

        def do_deletes(side: str) -> None:
            field = ES_DELETE_FIELD if side == "es" else MILVUS_DELETE_FIELD
            base = self.es_base if side == "es" else self.milvus_base
            path = ES_DELETE_PATH if side == "es" else MILVUS_DELETE_PATH
            for target in [t for t in targets if t.get("side") == side]:
                name = target.get("index_name") if side == "es" else target.get("collection_name")
                body = build_delete_body(side=side, target=name, file_id=fid,
                                         col_name=field, col_values=[fid])
                url = base + path
                try:
                    self._poster(url, body)
                except Exception as exc:  # noqa: BLE001 - 失败必须带原因
                    raise self._write_failed(side, f"delete {name}: {type(exc).__name__}: {exc}",
                                             completed, calls, deletes) from exc
                calls.append({"side": side, "op": "delete", "url": url, "target": name})
                deletes.append({"side": side, "target": name, "col_name": field,
                                "col_values": [fid]})

        def do_insert(side: str) -> Dict[str, Any]:
            # 显式 None：不依赖「空 plan 不会发请求」这个隐含行为
            url_es = (self.es_base + ES_INSERT_PATH) if side == "es" else None
            url_mv = (self.milvus_base + MILVUS_INSERT_PATH) if side == "milvus" else None
            side_plan = _SidePlan(plan.write_plan, side)
            try:
                result = self._writer.apply(side_plan, es_url=url_es, milvus_url=url_mv)
            except Exception as exc:  # noqa: BLE001 - 真 apply 内部已兜，这里再兜一层
                raise self._write_failed(
                    side, f"insert: {type(exc).__name__}: {exc}",
                    completed, calls, deletes) from exc
            status = getattr(result, "status", "OK")
            if status != "OK":
                raise self._write_failed(
                    side, f"insert {getattr(result, 'error', '')}",
                    completed, calls, deletes, result=result)
            completed.append(side)
            calls.extend(getattr(result, "calls", []) or [])
            return {"status": "OK", "side": side}

        do_deletes("es")
        insert_es = do_insert("es")
        do_deletes("milvus")
        insert_mv = do_insert("milvus")

        is_delete = plan.write_plan is None
        return {
            "status": "APPLIED", "applied": True, "required": True,
            # DELETE 只有删除、没有新块：inserts 必须是 None，
            # 否则上层会把「空插入返回 OK」读成「写了新块」（TL 20:2x 采纳 (c) 的一半）。
            "mode": "DELETE" if is_delete else "UPSERT",
            "deletes": deletes,
            "inserts": None if is_delete else {"es": insert_es, "milvus": insert_mv},
            "compensation": {"needs": False, "completed_sides": completed, "calls": calls},
            "es_base": self.es_base, "milvus_base": self.milvus_base,
        }

    def _write_failed(self, side: str, error: str, completed: List[str],
                      calls: List[Dict[str, Any]], deletes: List[Dict[str, Any]],
                      *, result: Any = None) -> "KbDeltaRefused":
        """写入失败：把「已写的一侧」显式带出去（契约 §5 `INDEX_WRITE_FAILED` 要求）。

        不只 log —— 异常对象带 `payload`，服务层会把它放进响应 `data`。
        """
        index_write = {
            "status": "FAILED", "applied": False, "required": True,
            "side": side, "error": error,
            "deletes": deletes,
            "compensation": {"needs": bool(completed),
                             "completed_sides": list(completed),
                             "calls": calls},
        }
        if result is not None:
            index_write["result"] = getattr(result, "to_dict", lambda: {})()
        logger.error("索引写入失败（已写的一侧=%s）：side=%s kb=%s file_id=%s error=%s",
                     completed, side, "--", "--", error)
        exc = KbDeltaRefused("INDEX_WRITE_FAILED", f"{side}: {error}")
        exc.payload = {"index_write": index_write}
        return exc

    def _apply_plan(self, state: Dict[str, Any], plan: IngestPlan) -> None:
        """把计划应用到一份 state（可写盘，也可只是纯内存 prospective）。"""
        bucket = state.setdefault("kb", {}).setdefault(plan.kb, {})
        chunks_bucket = state.setdefault("chunks", {}).setdefault(plan.kb, {})
        if plan.artifact is not None:
            fid = str(plan.file_id)
            bucket[fid] = {
                "artifact_id": plan.artifact.get("artifact_id"),
                "snapshot": plan.snapshot,
                "content_uid": plan.artifact.get("content_uid"),
                "content_hash": getattr(plan.write_plan, "content_hash", None),
                "file_name": (plan.diff.get("file_name") if isinstance(plan.diff, dict) else None),
                "status": STATUS_ACTIVE,
                # additive（TL Q7）：解析基线随文件落盘，便于判「换解析器」；
                # 旧 state 没有该字段时读侧按 None 处理，不触发 version 推进。
                "parser_fingerprint": plan.parser_fingerprint,
            }
            chunks_bucket[fid] = K._chunk_state_records(plan.chunks)
        for fid in plan.removed:
            entry = bucket.get(str(fid))
            if entry is None:
                continue
            entry["status"] = STATUS_REVOKED
            entry["revoked_at"] = _now_iso()
            entry.setdefault("revoke_reason", "SOURCE_REMOVED")
        graph_slot = state.setdefault("graph", {}).setdefault(
            plan.kb, {"snapshot": None, "fencing": 0, "mode": "DELTA"})
        if plan.snapshot:
            graph_slot["snapshot"] = plan.snapshot
        graph_slot.setdefault("fencing", 0)
        graph_slot["mode"] = "DELTA"

    @staticmethod
    def _index_write_block(plan: IngestPlan) -> Dict[str, Any]:
        """ES/Milvus **只产计划、不写入**（L12 红线）—— 必须在响应里如实说明。

        `index_writer.build()` 只产出 `es_plan` / `milvus_plan`；
        真正写盘是 `index_writer.apply(plan, es_url, milvus_url)`，生产零调用（由 L13 接线）。
        不写这个块，调用方会把「计划成功」读成「三路已落」。
        """
        if plan.write_plan is None:
            return {"status": "NOT_APPLICABLE", "applied": False, "required": False,
                    "reason": "DELETE：只撤权与状态，不写索引"}
        return {
            "status": "PLANNED",
            "applied": False,
            "required": True,
            "reason": "L12 红线：未写线上 ES/Milvus，apply 由 L13 接线",
            "es": {"bodies": len(getattr(plan.write_plan, "es_plan", []) or [])},
            "milvus": {"bodies": len(getattr(plan.write_plan, "milvus_plan", []) or [])},
            "documents": len(plan.chunks),
        }

    def _result(self, plan: IngestPlan, *, status: Optional[str], cursor: Optional[str],
                wanted: List[Dict[str, Any]], graph_result: Any, graph_error: Optional[str],
                index_write: Dict[str, Any], state_committed: bool) -> Dict[str, Any]:
        if status is None:
            landed = (not index_write["required"]) or bool(index_write["applied"])
            # 需要补偿（一侧已写、一侧失败）时不得报 OK —— 同 L12 的 applied 规则
            needs_compensation = bool((index_write.get("compensation") or {}).get("needs"))
            status = ("OK" if landed and graph_error is None and not needs_compensation
                      else "PARTIAL")
        return {
            "status": status,
            "kb": plan.kb,
            "cursor": cursor,
            "diff": plan.diff,
            "diff_source": plan.diff_source,
            "wanted_docs": wanted,
            "removed": list(plan.removed),
            "state_committed": state_committed,
            "index_write": index_write,
            "state_path": str(self._kb_state_path()),
            "artifact": None if plan.artifact is None else {
                "artifact_id": plan.artifact.get("artifact_id"),
                "content_uid": plan.artifact.get("content_uid"),
                "content_hash": getattr(plan.write_plan, "content_hash", None),
                "snapshot": plan.snapshot,
            },
            "projection": {"status": plan.projection_status, "chunks": len(plan.chunks)},
            "graph": {"result": graph_result, "error": graph_error},
        }

    # ------------------------------------------------------------------- run
    def run(self, req: Dict[str, Any]) -> Dict[str, Any]:
        plan = self.plan(req)
        return self.commit(plan)

    # ------------------------------------------------------------------ 内部
    def _kb_state_path(self) -> Path:
        return K._kb_state_path(self.store_root)
