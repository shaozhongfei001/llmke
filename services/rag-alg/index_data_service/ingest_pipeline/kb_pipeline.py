"""同一份解析快照 → 搜索 chunk + 图谱 docs 双路消费（按知识库）。

为什么必须"同一份"
------------------
`artifact_binding.py` 的约束：RAG 与图谱若各拿一份正文，换了解析器版本 / 改了表格抽取时
两边会静默错配，引用指到的原文与实际召回的内容不是同一次解析。所以这里只用**一个**
`store.commit()` 产出的不可变快照，同时喂给投影（搜索）与图构建（图谱），
两边共享 `artifact_id` / `content_uid`。

链路
----
    doc2md 产物目录（四件套）
        └─ store.commit()            → 平台不可变快照（artifact.json + 四件套 + sha256 清单）
             ├─ rag_projection.project()  → chunk（pk / locator / parse_artifact_id）→ 搜索索引载荷
             └─ build_graph_docs()        → BuildDoc → 18094 /v2/graph/build?kb=<kb>（按库落盘）

刻意不做
--------
- 不写 ES / Milvus：第一路只产出"可直接交给索引层"的载荷，落库由索引层负责；
- 不重新解析原件：快照缺失就报错，不在这里兜底解析（解析只在 doc2md 发生一次）；
- 不伪造来源：file_id / locator / pk 全部来自投影，缺就不给，不填占位。
"""

import copy
import fcntl
import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from graph_engine_adapter.artifact_binding import (
    ArtifactBindingError,
    assert_same_artifact,
)
from parse_artifact import store
from rag_projection import projection as P

from . import enrich
from . import index_writer
from . import summary

GRAPH_API_DEFAULT = "http://127.0.0.1:18094"
DEFAULT_CHUNK_CHARS = 800

# `kb_state.json` 契约（`02-CONTRACTS.md` §4.2）：绝对路径 + schema 版本化。
KB_STATE_SCHEMA = "llmke.kb-state/2"
KB_STATE_ENV = "LLMKE_KB_STATE"
# 仓根：services/rag-alg/index_data_service/ingest_pipeline → parents[4]。
# 注意 parents[3] 是 `services/`（差一层），单测里有锚点断言防止将来文件移动再错层。
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_KB_STATE_PATH = _REPO_ROOT / "platform" / "r12" / "data" / "kb-state" / "kb_state.json"


class PipelineRefused(RuntimeError):
    """编排被拒绝（快照不合规 / 图谱服务不可用）。"""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


class SourceDiverged(PipelineRefused, ArtifactBindingError):
    """搜索载荷与图谱 docs 不同源（契约 §5 `SOURCE_DIVERGED`）。

    同时继承 `PipelineRefused`（编排层既有错误族，`kb_ingest_service` 已按它映射 HTTP）
    与 `ArtifactBindingError`（`assert_same_artifact` 的错误语义），
    这样调用方无论按哪一族捕获都能拿到，不会因为类型不匹配而静默放过。
    """

    def __init__(self, detail=""):
        PipelineRefused.__init__(self, "SOURCE_DIVERGED", detail)


def locator_text(chunk: Dict[str, Any]) -> str:
    """把结构化的 locator 压成可读字符串。

    保留 `chunk=<seq>`：`alg_retrieval_service.retrieval_graph` 用它解出 chunk_index；
    再附真实偏移，人工核对时能直接定位到原文第几个字。
    """
    loc = chunk.get("locator") or {}
    seq = chunk.get("seq")
    if loc.get("kind") == "text_span":
        return f"chunk={seq};offset={loc.get('start_offset')}-{loc.get('end_offset')}"
    if loc.get("kind") == "block_ref":
        # MinerU 渲染文本与块文本有空白差异时退化为块级定位：精确到块/页，不到字符
        page = loc.get("page_no")
        page_part = f";page={page}" if page is not None else ""
        return f"chunk={seq};block={loc.get('block_id')}{page_part}"
    if loc.get("kind") in ("table_ref", "table_cell"):
        return f"chunk={seq};table={loc.get('table_id')}"
    return f"chunk={seq}"


def build_graph_docs(chunks: List[Dict[str, Any]], *, file_id: Any,
                     title: Optional[str] = None) -> List[Dict[str, Any]]:
    """投影块 → 18094 BuildDoc（带 pk / parse_artifact_id，供溯源回指）。"""
    docs: List[Dict[str, Any]] = []
    for chunk in chunks:
        text = str(chunk.get("text") or "")
        if not text.strip():
            continue
        doc: Dict[str, Any] = {
            "file_id": str(file_id),
            "text": text,
            "locator": locator_text(chunk),
            # pk 是平台 chunk 主键：图召回命中时带回去，Java 引用才能指到"哪一段"
            "pk": chunk.get("pk"),
        }
        if title:
            doc["title"] = str(title)
        artifact_id = chunk.get("parse_artifact_id")
        if artifact_id:
            doc["parse_artifact_id"] = str(artifact_id)
        docs.append(doc)
    return docs


def build_index_payloads(chunks: List[Dict[str, Any]], *, index_name: str, file_id: Any,
                         file_name: Optional[str] = None, file_path: Optional[str] = None,
                         file_size: Optional[int] = None,
                         source: Optional[str] = None,
                         now: Optional[str] = None,
                         summarizer: Optional[Any] = None) -> List[Dict[str, Any]]:
    """投影块 → 索引层可直接落库的载荷（覆盖生产集合字段，形状由 enrich 统一）。

    P1-L5 additive：
    - ``now`` 透传给 ``enrich.build_payload``，使同一 IR 两次投影的载荷逐字节相同
      （不传时行为与改动前一致：正文通道仍用当前时间）；
    - 产出 ``table_summary_<kb>`` 载荷，复用 ``summary.build_summary_payloads``
      既有契约（不重新实现摘要 / 主键）。正文通道行为不变。
    """
    payloads: List[Dict[str, Any]] = []
    for chunk in chunks:
        meta, fill = enrich.build_payload(chunk, index_name=index_name, file_id=file_id,
                                          file_name=file_name, file_path=file_path,
                                          file_size=file_size, now=now)
        # `source` 在本栈里是"文件身份键"，不是解析产物路径（见 ingest._chunk_payload 注释）
        meta["pk"] = chunk["pk"]
        meta["source"] = source or file_path or ""
        meta["parsed_text_ref"] = ("parsed_text.md" if chunk.get("channel") == "text"
                                   else "table")
        if chunk.get("channel") == "table":
            meta["n_rows"], meta["n_cols"] = chunk.get("rows"), chunk.get("cols")
        payloads.append({
            "index": index_name if chunk.get("channel") == "text" else f"table_chunks_{index_name}",
            "page_content": chunk["text"],
            "metadata": meta,
            "pk": chunk["pk"],
            "_fill": fill,
        })
    # P1-L5 additive：补齐表格总结通道（E1 / R-1）。复用 summary.py 既有
    # build_summary_payloads 契约产出 table_summary_<kb> 载荷，不重新实现摘要/主键。
    # 刻意不采用其返回的 updated（会给表格块回填 table_summary_id）：线上
    # table_chunks_kb_9 的 _source.metadata 为 38 键、无该键，E1 要求字段集与线上
    # 一致（多字段判 FAIL）。主键对齐按 §二 裁定 3 记为已知边界转 P6 切读。
    table_payloads = [p for p in payloads
                      if p["index"] == f"table_chunks_{index_name}"]
    if table_payloads:
        if summarizer is None:
            summarizer = summary.extractive_summarizer
        summaries, _updated = summary.build_summary_payloads(
            table_payloads, index_name=index_name, summarizer=summarizer)
        payloads.extend(summaries)
    return payloads


def commit_snapshot(doc2md_dir, store_root, *, producer_inputs: Dict[str, Any],
                    artifact_id: Optional[str] = None):
    """把 doc2md 产物封成不可变快照；返回 (artifact, 快照目录)。

    artifact_id 默认由**产物内容摘要**（read_set_digest）派生，而不是源文件哈希。
    原因（实测）：doc2md 的 parse_manifest 带 `generated_at`，同一份文件重新解析会产出
    不同字节；若用源文件哈希做 id，二次解析必然 ARTIFACT_CONFLICT（不可覆盖）。
    用产物摘要派生后：
      - 同一份产物重复提交 → 同 id → 幂等；
      - 产物确实变了（重新解析/换解析器）→ 新 id → 新版本，不覆盖旧快照。
    """
    if artifact_id is None:
        parts = store.collect_parts(Path(doc2md_dir))
        artifact_id = store.read_set_digest(parts)
    artifact, target = store.commit(Path(doc2md_dir), Path(store_root), producer_inputs,
                                    artifact_id=artifact_id)
    return artifact, Path(target)


def project_snapshot(snapshot_dir, *, index_name: str, file_id: Any,
                     chunk_chars: int = DEFAULT_CHUNK_CHARS) -> P.ProjectionResult:
    """从平台快照投影召回单元（只读快照，不写索引）。"""
    policy = P.ProjectionPolicy(index_name=index_name, file_id=str(file_id),
                               chunk_chars=chunk_chars)
    return P.project(Path(snapshot_dir), policy, mode="snapshot")


def post_graph_build(kb: str, docs: List[Dict[str, Any]], *, root: Optional[str] = None,
                     graph_api: Optional[str] = None,
                     timeout: float = 1800) -> Dict[str, Any]:
    """把 docs 交给 18094 建图；按 kb 落盘（各库图谱互不覆盖）。"""
    import requests

    if not kb:
        raise PipelineRefused("KB_REQUIRED", "建图必须指定知识库标识，否则会写进默认库")
    if not docs:
        raise PipelineRefused("DOCS_EMPTY", "没有可建图的块（空请求不能建图）")

    base = (graph_api or os.environ.get("LLMKE_V2_GRAPH_API") or GRAPH_API_DEFAULT).rstrip("/")
    payload: Dict[str, Any] = {"docs": docs, "kb": kb}
    if root:
        payload["root"] = root
    try:
        resp = requests.post(f"{base}/v2/graph/build", json=payload, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - 连不上要带原因，不吞
        raise PipelineRefused("GRAPH_API_UNREACHABLE",
                              f"{base}: {type(exc).__name__}: {exc}") from exc
    if resp.status_code != 200:
        raise PipelineRefused("GRAPH_BUILD_HTTP_" + str(resp.status_code),
                              str(resp.text)[:300])
    body = resp.json()
    if body.get("status") != "BUILT":
        raise PipelineRefused("GRAPH_BUILD_NOT_BUILT", json.dumps(body, ensure_ascii=False)[:300])
    return body


def _kb_state_path(store_root=None) -> Path:
    """状态文件绝对路径：`LLMKE_KB_STATE` 优先，否则仓内受控默认位置。

    刻意**不再从 `store_root` 派生**：`store_root` 默认值是相对路径
    `.artifacts/artifact-store`，随进程 CWD 漂移，且曾出现过 `kb_state.json`
    落在 `/tmp` 后被清空、图谱按空库重建的事故（`scripts/v2_graph_rebuild_from_es.py:9`）。
    契约 §4.2 要求绝对路径，相对路径同样不可审计，故直接拒绝。
    """
    env = os.environ.get(KB_STATE_ENV)
    if env:
        path = Path(env).expanduser()
        if not path.is_absolute():
            raise PipelineRefused(
                "KB_STATE_PATH_NOT_ABSOLUTE",
                f"{KB_STATE_ENV}={env!r} 必须是绝对路径（契约 §4.2，禁相对路径与 /tmp）")
        return path
    return DEFAULT_KB_STATE_PATH


def _empty_kb_state() -> Dict[str, Any]:
    return {"schema": KB_STATE_SCHEMA, "version": 0, "cursor": None,
            "set_digest": None, "kb": {}, "chunks": {}, "graph": {}}


def _canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _compute_set_digest(state: Dict[str, Any]) -> str:
    """只覆盖 `status=ACTIVE` 的条目（契约 §4.2）。"""
    active = []
    for kb_name in sorted(state.get("kb") or {}):
        for file_id in sorted(state["kb"][kb_name] or {}):
            entry = state["kb"][kb_name][file_id] or {}
            if entry.get("status", "ACTIVE") != "ACTIVE":
                continue
            active.append([kb_name, str(file_id),
                           entry.get("content_hash") or entry.get("artifact_id") or ""])
    return _canonical_sha256(active)


def _compute_cursor(state: Dict[str, Any]) -> str:
    return "cursor-" + _canonical_sha256(
        {"schema": KB_STATE_SCHEMA, "version": state.get("version"),
         "set_digest": state.get("set_digest")})


def _backup_one_v1(path: Path) -> Path:
    """把旧 v1 文件复制一份备份；**绝不覆盖已有备份**。

    若某个既有备份与当前 v1 内容逐字节相同，直接复用（否则每次只读迁移都会
    新增一个冗余备份，把目录刷满）。
    """
    source_bytes = path.read_bytes()
    base = path.with_name(path.name + ".v1.bak")
    candidates = [base] + sorted(p for p in path.parent.iterdir()
                                 if p.name.startswith(base.name + "."))
    for candidate in candidates:
        if candidate.is_file() and candidate.read_bytes() == source_bytes:
            return candidate
    target = base
    if target.exists():
        target = path.with_name(f"{base.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}")
        attempt = 1
        while target.exists():
            target = path.with_name(
                f"{base.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.{attempt}")
            attempt += 1
    target.write_bytes(source_bytes)
    return target


def _migrate_v1(path: Path, doc: Dict[str, Any]) -> Dict[str, Any]:
    """v1（顶层直接是 `{kb: {file_id: {...}}}`、无 `schema`）→ v2，保留 `.v1.bak`。"""
    backup = _backup_one_v1(path)
    state = _empty_kb_state()
    for kb_name, files in (doc or {}).items():
        if not isinstance(files, dict):
            raise PipelineRefused("KB_STATE_CORRUPT",
                                  f"{path}: v1 条目 {kb_name!r} 形状非法（期望对象）")
        bucket = state["kb"].setdefault(str(kb_name), {})
        for file_id, entry in files.items():
            item = dict(entry or {})
            item.setdefault("status", "ACTIVE")
            bucket[str(file_id)] = item
        state["chunks"].setdefault(str(kb_name), {})
        state["graph"].setdefault(str(kb_name),
                                  {"snapshot": None, "fencing": 0, "mode": "DELTA"})
    state["version"] = 1
    state["set_digest"] = _compute_set_digest(state)
    state["cursor"] = _compute_cursor(state)
    state["migrated_from"] = str(backup)  # 留痕：告诉运维这次迁移读的是哪个备份
    return state


def _load_kb_state(store_root=None) -> Dict[str, Any]:
    """读状态：**损坏 / schema 不符一律抛 `KB_STATE_CORRUPT`，禁止静默返回空态**。

    静默空态等于「按空库重建」：历史文件全部从 wanted docs 消失，图谱被覆盖，
    而且没有任何告警——这正是 L7 要修掉的缺陷（`03-IMPLEMENTATION.md:193`）。
    """
    path = _kb_state_path(store_root)
    if not path.is_file():
        return _empty_kb_state()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PipelineRefused("KB_STATE_CORRUPT",
                              f"{path}: {type(exc).__name__}: {exc}") from exc
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise PipelineRefused("KB_STATE_CORRUPT", f"{path}: JSON 解析失败 {exc}") from exc
    if not isinstance(doc, dict):
        raise PipelineRefused("KB_STATE_CORRUPT", f"{path}: 顶层必须是对象")
    if "schema" not in doc:
        return _migrate_v1(path, doc)
    if doc.get("schema") != KB_STATE_SCHEMA:
        raise PipelineRefused(
            "KB_STATE_CORRUPT",
            f"{path}: schema={doc.get('schema')!r} 期望 {KB_STATE_SCHEMA!r}")
    for key in ("version", "kb", "chunks", "graph"):
        if key not in doc:
            raise PipelineRefused("KB_STATE_CORRUPT", f"{path}: 缺字段 {key}")
    doc.setdefault("cursor", None)
    doc.setdefault("set_digest", None)
    return doc


def _save_kb_state(state: Dict[str, Any], store_root=None) -> None:
    """原子写：pid+uuid 临时文件 + `os.replace`，不留固定 `.json.tmp`。

    注意签名相对 L7 之前变化（原为 `(store_root, state)`）：改成「数据在前」
    以免把 store_root 误当状态对象写进去；调用点仅本模块内（已逐一更新）。
    """
    path = _kb_state_path(store_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True),
                       encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _verify_kb_state_round_trip(store_root=None) -> None:
    """落盘后回读校验（TL 裁定 3）：字段不齐 → `KB_STATE_CORRUPT`，不继续。"""
    path = _kb_state_path(store_root)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PipelineRefused("KB_STATE_CORRUPT", f"{path}: 回读失败 {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != KB_STATE_SCHEMA:
        raise PipelineRefused("KB_STATE_CORRUPT", f"{path}: 回读 schema 不符")
    if not isinstance(doc.get("version"), int):
        raise PipelineRefused("KB_STATE_CORRUPT", f"{path}: 回读缺 version")
    for key in ("cursor", "set_digest"):
        if not doc.get(key):
            raise PipelineRefused("KB_STATE_CORRUPT", f"{path}: 回读缺 {key}")


@contextmanager
def _kb_state_lock(path: Path):
    """读-改-写全程独占 `flock`（锁文件与数据文件分开，避免 `os.replace` 换掉锁 inode）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    handle = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(handle, fcntl.LOCK_UN)
        finally:
            os.close(handle)


@contextmanager
def _kb_state_txn(store_root=None):
    """状态事务：加锁 → 读 → 交给调用方改 → 有变化才推进 version/cursor 并原子写 → 回读校验。

    「有变化才写」让同内容重摄取保持幂等（不空推进 `version`/`cursor`）。
    """
    path = _kb_state_path(store_root)
    with _kb_state_lock(path):
        state = _load_kb_state(store_root)
        before = copy.deepcopy(state)
        yield state
        if state == before:
            return
        state["schema"] = KB_STATE_SCHEMA
        state["version"] = int(state.get("version") or 0) + 1
        state["set_digest"] = _compute_set_digest(state)
        state["cursor"] = _compute_cursor(state)
        _save_kb_state(state, store_root)
        _verify_kb_state_round_trip(store_root)


def _chunk_state_records(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """投影块 → `chunks` 落盘记录（契约 §4.2 必备 5 字段 + 2 个溯源字段）。

    `seq` 与 `parse_artifact_id` 是契约清单之外 additive 的：`seq` 已编进 `locator`
    （`chunk=<seq>`），但重建 BuildDoc 时要能回指 `parse_artifact_id`，否则
    「wanted docs 引用」失去溯源，图谱侧的引用就不可复核。
    """
    records: List[Dict[str, Any]] = []
    for chunk in chunks:
        text = str(chunk.get("text") or "")
        records.append({
            "pk": chunk.get("pk"),
            "text": text,
            "locator": locator_text(chunk),
            "channel": chunk.get("channel", "text"),
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "seq": chunk.get("seq"),
            "parse_artifact_id": chunk.get("parse_artifact_id"),
        })
    return records


def build_wanted_docs(state: Dict[str, Any], kb: str) -> List[Dict[str, Any]]:
    """从 `kb_state.chunks` 组装该库「全量 wanted docs 的引用」——**不重新投影**。

    契约 §4.2：`chunks` 是 wanted docs 的唯一装配来源；投影只算一次落盘，
    `seq` 在文件首次投影时分配后固定。重新投影会让 `seq` 重排 → pk 变化 →
    图谱 source.pk 与 ES `_id` 脱钩（`00-DESIGN.md` §7.5.1）。
    """
    docs: List[Dict[str, Any]] = []
    files = (state.get("kb") or {}).get(kb) or {}
    chunks_by_file = (state.get("chunks") or {}).get(kb) or {}
    for file_id in sorted(files, key=str):
        entry = files[file_id] or {}
        if entry.get("status", "ACTIVE") != "ACTIVE":
            continue
        for chunk in chunks_by_file.get(file_id) or []:
            doc: Dict[str, Any] = {
                "file_id": str(file_id),
                "text": chunk.get("text", ""),
                "locator": chunk.get("locator", ""),
                "pk": chunk.get("pk"),
            }
            if entry.get("file_name"):
                doc["title"] = str(entry["file_name"])
            if chunk.get("parse_artifact_id"):
                doc["parse_artifact_id"] = str(chunk["parse_artifact_id"])
            docs.append(doc)
    return docs


def consume_for_kb(doc2md_dir, store_root, *, kb: str, file_id: Any,
                   producer_inputs: Dict[str, Any], index_name: Optional[str] = None,
                   file_name: Optional[str] = None, file_path: Optional[str] = None,
                   file_size: Optional[int] = None, source: Optional[str] = None,
                   chunk_chars: int = DEFAULT_CHUNK_CHARS, artifact_id: Optional[str] = None,
                   build_graph: bool = True, graph_root: Optional[str] = None,
                   graph_api: Optional[str] = None, timeout: float = 1800) -> Dict[str, Any]:
    """按库摄取：封快照 → 同源校验 → 落状态（本次 chunks）+ 返回 wanted docs 引用。

    P2-L7 三处行为变更（对外 JSON 形状不变，`03-IMPLEMENTATION.md` §P2-2/§P2-3）
    -----------------------------------------------------------------------
    1. **同源闸门前移到写入之前**：`index_writer.build` 只产写入计划、`apply` 才发请求，
       所以把 `assert_same_artifact` 放在两者之间即可「不一致时三路 0 写入」，
       不需要重排写入顺序、也不需要给写入加回滚。
    2. **不再全库重建图谱**：原实现遍历 `kb_state` 里全部历史文件、逐个**重新投影**再
       `post_graph_build`，于是每次摄取都是「该库全量重建」。现在改为把本次 chunks
       落进 `kb_state.chunks`（投影只算一次），再返回「本次 chunks + 全量 wanted docs
       引用」，全量/delta 重建交给 P3/P4。`build_graph=True` 时如实返回
       `PARTIAL` + `GRAPH_REBUILD_DEFERRED`，**不谎报图谱已建好**。
    3. **`file_id` 必须真实**：缺则 `FILE_ID_MISSING` fail-closed，不再回落 `kb`
       （回落会让同库多文件在 ES metadata 上撞成同一个 file_id）。

    `graph_root` / `graph_api` / `timeout` 保留是为了不改调用方签名，
    本 loop 内不再使用（建图已移交 P3/P4）。
    """
    if not kb:
        raise PipelineRefused("KB_REQUIRED", "必须指定知识库标识")
    index = index_name or kb
    real_file_id = "" if file_id is None else str(file_id).strip()
    if not real_file_id:
        raise PipelineRefused(
            "FILE_ID_MISSING",
            "consume_for_kb 必须收到真实 file_id（平台文件 id），不得回落 kb")

    artifact, snapshot = commit_snapshot(doc2md_dir, store_root,
                                         producer_inputs=producer_inputs,
                                         artifact_id=artifact_id)

    current = project_snapshot(snapshot, index_name=index, file_id=real_file_id,
                               chunk_chars=chunk_chars)
    if current.status == "NOT_APPLICABLE":
        raise PipelineRefused("PROJECTION_NOT_APPLICABLE", str(current.stats.get("reason")))
    chunks = current.chunks

    # G1：生产写入计划（真实 file_id 注入，缺则 IndexWriterError → 统一成编排错误族）
    # P2-L8：`file_path` / `source` 一并注入 —— `source` 是 metadata 的文件身份键，
    # 与 `build_index_payloads(source=...)` 同口径（不传则按 file_path 去掉 URL 前缀派生）。
    try:
        plan = index_writer.build(chunks, artifact, kb=index, file_id=real_file_id,
                                  file_path=file_path, source=source)
    except index_writer.IndexWriterError as exc:
        raise PipelineRefused(exc.code, exc.detail) from exc

    # G2：图谱侧用**同一份 chunks + 同一 file_id** 复算，任何一侧被改写都在这里被拒。
    # 位置刻意放在 apply / 建图之前 —— 禁止「先写后校验」。
    graph_binding = index_writer.bind_chunks(
        chunks, {**artifact, "file_id": real_file_id})
    try:
        assert_same_artifact(plan.binding, graph_binding)
    except ArtifactBindingError as exc:
        raise SourceDiverged(str(exc)) from exc

    payloads = build_index_payloads(chunks, index_name=index, file_id=real_file_id,
                                    file_name=file_name, file_path=file_path,
                                    file_size=file_size, source=source)

    # G3：状态落盘（同源校验通过之后才写），chunks 只算这一次
    entry = {
        "artifact_id": artifact["artifact_id"],
        "snapshot": str(snapshot),
        "content_uid": artifact.get("content_uid"),
        "content_hash": plan.content_hash,
        "file_name": file_name,
        "status": "ACTIVE",
        # 以下三个是既有字段（契约未列但历史落盘有），保留以免丢信息
        "file_path": file_path,
        "file_size": file_size,
        "source": source,
    }
    with _kb_state_txn(store_root) as state:
        state["kb"].setdefault(kb, {})[real_file_id] = entry
        state["chunks"].setdefault(kb, {})[real_file_id] = _chunk_state_records(chunks)
        slot = state["graph"].setdefault(
            kb, {"snapshot": None, "fencing": 0, "mode": "DELTA"})
        slot["snapshot"] = str(snapshot)
        slot.setdefault("fencing", 0)   # 不推进：本 loop 不建图，不能假造 fencing
        slot["mode"] = "DELTA"

    # G4：wanted docs 只从 state.chunks 组装（引用），不重投影、不触发全库建图
    wanted = build_wanted_docs(state, kb)
    per_file: List[Dict[str, Any]] = []
    for fid in sorted((state.get("chunks") or {}).get(kb) or {}, key=str):
        count = len((state["chunks"][kb][fid]) or [])
        per_file.append({"file_id": fid, "chunks": count} if count
                        else {"file_id": fid, "chunks": 0, "skipped": "chunks_missing"})

    deferred = bool(build_graph)
    graph_error = ("GRAPH_REBUILD_DEFERRED: 全库/增量图谱重建已移交 P3/P4 delta 链路；"
                   "本 loop 只在 kb_state 记录 wanted docs 引用") if deferred else None

    counts: Dict[str, int] = {}
    for item in payloads:
        counts[item["index"]] = counts.get(item["index"], 0) + 1

    return {
        "status": "OK" if graph_error is None else "PARTIAL",
        "kb": kb,
        "artifact_id": artifact["artifact_id"],
        "content_uid": artifact.get("content_uid"),
        "artifact_quality": (artifact.get("quality") or {}).get("state"),
        "snapshot": str(snapshot),
        "projection": {
            "status": current.status,
            "chunks": len(chunks),
            "channels": {"text": current.stats.get("chunks_text"),
                         "table": current.stats.get("chunks_table")},
            "counts": counts,
            "payloads": payloads,
        },
        "graph": {
            "requested": bool(build_graph),
            "docs": len(wanted),
            "files": per_file,
            "result": None,
            "error": graph_error,
            # additive：显式标出「建图已移交」，调用方不会把 result=None 当成功
            "deferred": deferred,
        },
        "doc2md_dir": str(doc2md_dir),
    }


def consume(doc2md_dir, store_root, *, kb: str, file_id: Any, index_name: Optional[str] = None,
            producer_inputs: Dict[str, Any], file_name: Optional[str] = None,
            file_path: Optional[str] = None, file_size: Optional[int] = None,
            source: Optional[str] = None, chunk_chars: int = DEFAULT_CHUNK_CHARS,
            artifact_id: Optional[str] = None, build_graph: bool = True,
            graph_root: Optional[str] = None, graph_api: Optional[str] = None,
            timeout: float = 1800) -> Dict[str, Any]:
    """一次摄取 = 封快照 → 投影（搜索）+ 建图（图谱），两路共用同一份快照。

    返回两路各自的产物与统计；任何一路失败都带原因，不静默跳过。
    """
    if not kb:
        raise PipelineRefused("KB_REQUIRED", "必须指定知识库标识")
    index = index_name or kb

    artifact, snapshot = commit_snapshot(doc2md_dir, store_root,
                                         producer_inputs=producer_inputs,
                                         artifact_id=artifact_id)
    projected = project_snapshot(snapshot, index_name=index, file_id=file_id,
                                 chunk_chars=chunk_chars)
    if projected.status == "NOT_APPLICABLE":
        raise PipelineRefused("PROJECTION_NOT_APPLICABLE", str(projected.stats.get("reason")))

    chunks = projected.chunks
    payloads = build_index_payloads(chunks, index_name=index, file_id=file_id,
                                    file_name=file_name, file_path=file_path,
                                    file_size=file_size, source=source)
    docs = build_graph_docs(chunks, file_id=file_id, title=file_name)

    graph_result: Optional[Dict[str, Any]] = None
    graph_error: Optional[str] = None
    if build_graph:
        try:
            graph_result = post_graph_build(kb, docs, root=graph_root, graph_api=graph_api,
                                            timeout=timeout)
        except PipelineRefused as exc:
            # 搜索那一路已经可交付；图这一路失败必须显式带回，不装成成功
            graph_error = f"{exc.code}: {exc.detail}"

    counts: Dict[str, int] = {}
    for item in payloads:
        counts[item["index"]] = counts.get(item["index"], 0) + 1

    return {
        "status": "OK" if graph_error is None else "PARTIAL",
        "kb": kb,
        "artifact_id": artifact["artifact_id"],
        "content_uid": artifact.get("content_uid"),
        "artifact_quality": (artifact.get("quality") or {}).get("state"),
        "snapshot": str(snapshot),
        "projection": {
            "status": projected.status,
            "chunks": len(chunks),
            "channels": {"text": projected.stats.get("chunks_text"),
                         "table": projected.stats.get("chunks_table")},
            "counts": counts,
            "payloads": payloads,
        },
        "graph": {
            "requested": bool(build_graph),
            "docs": len(docs),
            "result": graph_result,
            "error": graph_error,
        },
    }
