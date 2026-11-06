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

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from parse_artifact import store
from rag_projection import projection as P

from . import enrich

GRAPH_API_DEFAULT = "http://127.0.0.1:18094"
DEFAULT_CHUNK_CHARS = 800


class PipelineRefused(RuntimeError):
    """编排被拒绝（快照不合规 / 图谱服务不可用）。"""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


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
                         source: Optional[str] = None) -> List[Dict[str, Any]]:
    """投影块 → 索引层可直接落库的载荷（覆盖生产集合字段，形状由 enrich 统一）。"""
    payloads: List[Dict[str, Any]] = []
    for chunk in chunks:
        meta, fill = enrich.build_payload(chunk, index_name=index_name, file_id=file_id,
                                          file_name=file_name, file_path=file_path,
                                          file_size=file_size)
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


def _kb_state_path(store_root) -> Path:
    return Path(store_root) / "kb_state.json"


def _load_kb_state(store_root) -> Dict[str, Dict[str, Any]]:
    path = _kb_state_path(store_root)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}


def _save_kb_state(store_root, state: Dict[str, Dict[str, Any]]) -> None:
    path = _kb_state_path(store_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def consume_for_kb(doc2md_dir, store_root, *, kb: str, file_id: Any,
                   producer_inputs: Dict[str, Any], index_name: Optional[str] = None,
                   file_name: Optional[str] = None, file_path: Optional[str] = None,
                   file_size: Optional[int] = None, source: Optional[str] = None,
                   chunk_chars: int = DEFAULT_CHUNK_CHARS, artifact_id: Optional[str] = None,
                   build_graph: bool = True, graph_root: Optional[str] = None,
                   graph_api: Optional[str] = None, timeout: float = 1800) -> Dict[str, Any]:
    """按库摄取：把本次文件并入该库清单后，用**该库全部文件**重建图谱。

    为什么必须合并（实测缺陷）：`/v2/graph/build` 是全量重建，只传本次文件的 docs 时，
    该库之前文件的图谱会被整体覆盖——多文件库传完第二个文件，第一个就"消失"了。
    这里维护 `<store_root>/kb_state.json`（kb → file_id → 快照），每次用全量重建。
    """
    if not kb:
        raise PipelineRefused("KB_REQUIRED", "必须指定知识库标识")
    index = index_name or kb

    artifact, snapshot = commit_snapshot(doc2md_dir, store_root,
                                         producer_inputs=producer_inputs,
                                         artifact_id=artifact_id)

    state = _load_kb_state(store_root)
    state.setdefault(kb, {})[str(file_id)] = {
        "artifact_id": artifact["artifact_id"],
        "snapshot": str(snapshot),
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "source": source,
    }
    _save_kb_state(store_root, state)

    # 本次文件的投影（搜索路载荷只回传本次，避免响应过大）
    current = project_snapshot(snapshot, index_name=index, file_id=file_id,
                               chunk_chars=chunk_chars)
    if current.status == "NOT_APPLICABLE":
        raise PipelineRefused("PROJECTION_NOT_APPLICABLE", str(current.stats.get("reason")))
    payloads = build_index_payloads(current.chunks, index_name=index, file_id=file_id,
                                    file_name=file_name, file_path=file_path,
                                    file_size=file_size, source=source)

    # 图谱这一路：该库**全部文件**的 docs（本次 + 历史）
    all_docs: List[Dict[str, Any]] = []
    per_file: List[Dict[str, Any]] = []
    for fid, meta in sorted(state[kb].items()):
        snap = meta.get("snapshot")
        if not snap or not Path(snap).is_dir():
            per_file.append({"file_id": fid, "chunks": 0, "skipped": "snapshot_missing"})
            continue
        proj = project_snapshot(snap, index_name=index, file_id=fid, chunk_chars=chunk_chars)
        docs = build_graph_docs(proj.chunks, file_id=fid, title=meta.get("file_name"))
        all_docs.extend(docs)
        per_file.append({"file_id": fid, "chunks": len(docs)})

    graph_result: Optional[Dict[str, Any]] = None
    graph_error: Optional[str] = None
    if build_graph:
        try:
            graph_result = post_graph_build(kb, all_docs, root=graph_root,
                                            graph_api=graph_api, timeout=timeout)
        except PipelineRefused as exc:
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
            "status": current.status,
            "chunks": len(current.chunks),
            "channels": {"text": current.stats.get("chunks_text"),
                         "table": current.stats.get("chunks_table")},
            "counts": counts,
            "payloads": payloads,
        },
        "graph": {
            "requested": bool(build_graph),
            "docs": len(all_docs),
            "files": per_file,
            "result": graph_result,
            "error": graph_error,
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
