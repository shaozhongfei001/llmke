"""P2-L6 · index_writer 适配层（T-D2MD-06）。

把 `rag_projection.project()` 的 chunks + `store.commit()` 的 artifact 适配成
19527 / 19526 写入端点的**写入计划**（离线、不写任何线上存储）。

职责边界（PLAN §一）
------------------
- 只产出计划 / mock 端点测试；**不接生产调用点**（`consume_for_kb` 内接 `build` +
  `assert_same_artifact` 属 L7）。
- 复用 `enrich.build_payload` 生成 metadata、复用 `artifact_binding.bind_artifact`
  计算 `content_hash`；**不重新实现投影 / 摘要 / 主键**。
- 默认 `index_prefix="v2cand_"`，计划只指向候选命名空间，不碰线上索引名。
- `duplicate_flag=False` 硬约束：禁止按 `metadata.source` 全量替换（设计包 :158-160）。

依据：`03-IMPLEMENTATION.md` §P2-1（`:141-165`）、`00-DESIGN.md` §6.3/§6.4、
`01-EVIDENCE.md:114-116`、`04-ACCEPTANCE.md` B-1、`ACCEPTANCE-BASELINE.yaml:28`。
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from graph_engine_adapter.artifact_binding import bind_artifact

from . import enrich

DEFAULT_INDEX_PREFIX = "v2cand_"
ES_MODEL_NAME = "bge-m3"
ES_CONSISTENCY_LEVEL = "Bounded"
# artifact_binding._check_locator 的闭集；table_ref 等投影侧 kind 需归一成字符串。
_BINDING_LOCATOR_KINDS = ("text_span", "table_cell", "figure_asset")


@dataclass(frozen=True)
class IndexWritePlan:
    kb: str
    index_prefix: str
    artifact_id: str
    content_uid: str
    content_hash: str
    binding: dict
    es_plan: list = field(default_factory=list)
    milvus_plan: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kb": self.kb, "index_prefix": self.index_prefix,
            "artifact_id": self.artifact_id, "content_uid": self.content_uid,
            "content_hash": self.content_hash, "binding": self.binding,
            "es_plan": self.es_plan, "milvus_plan": self.milvus_plan,
        }


@dataclass(frozen=True)
class IndexWriteResult:
    status: str
    side: str | None
    error: str | None
    completed_sides: list = field(default_factory=list)
    needs_compensation: bool = False
    calls: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status, "side": self.side, "error": self.error,
            "completed_sides": self.completed_sides,
            "needs_compensation": self.needs_compensation, "calls": self.calls,
        }


class IndexWriterError(ValueError):
    """写入计划构建失败（输入不合法，fail-closed）。"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- 同源绑定
def _binding_input(chunks: list, artifact: dict) -> dict:
    """把投影 chunks 归一成 `bind_artifact` 的输入。

    `bind_artifact._check_locator` 只认 `text_span/table_cell/figure_asset`；
    投影表格块的 `table_ref` 不在闭集，故按 `sort_keys` 序列化成稳定字符串
    （与 `_locator_key` 同一口径），保证三路派生用同一份输入、同一份哈希。
    """
    # P3-L9（收口 L7 边界 3）：不再回落字符串 "kb" —— 那会让 `bind_chunks` 在缺
    # file_id 时"看起来成功"，而 `build` 走的是 fail-closed。两条路径口径必须一致，
    # 否则同源校验的两份输入一个真一个假，比对就失去意义。
    file_id = str(artifact.get("file_id") or "").strip()
    if not file_id:
        raise IndexWriterError(
            "FILE_ID_MISSING",
            "_binding_input 缺 file_id（artifact 未带且未注入），不得回落 'kb'")
    norm = []
    for chunk in chunks:
        locator = chunk.get("locator") or {}
        if isinstance(locator, dict) and locator.get("kind") not in _BINDING_LOCATOR_KINDS:
            locator = json.dumps(locator, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"))
        norm.append({"text": chunk["text"], "locator": locator,
                     "file_id": file_id})
    return {"artifact_id": artifact["artifact_id"],
            "document_id": file_id, "chunks": norm}


def bind_chunks(chunks: list, artifact: dict) -> dict:
    """复用既有 `bind_artifact` 产出同源绑定（artifact_id + content_hash）。"""
    return bind_artifact(_binding_input(chunks, artifact))


def _target_name(channel: str, *, kb: str, index_prefix: str) -> str:
    """text → <prefix><kb>；table → <prefix>table_chunks_<kb>。"""
    if channel == "text":
        return f"{index_prefix}{kb}"
    return f"{index_prefix}table_chunks_{kb}"


def _resolve_source(source: str | None, file_path: str | None) -> str:
    """`metadata.source` 取值（P2-L8 · TL 12:2x 裁定，纠正「直接取 file_path」）。

    线上真实形态是 MinIO 对象键（无 scheme/host），而 `file_path` 是完整 URL：

        线上 source    = r12-rag/kb_9/<file>/V0/<file>
        线上 file_path = http://127.0.0.1:19000/r12-rag/kb_9/<file>/V0/<file>
        urlparse(file_path).path.lstrip("/")  ==  线上 source   （逐字一致）

    所以优先级：**调用点显式 `source` > `urlparse(file_path).path.lstrip("/")` > `""`**。
    直接写 `file_path` 会带上 `http://host/` 前缀，`metadata.source.keyword` 精确匹配会失配。
    """
    if source:
        return str(source)
    if not file_path:
        return ""
    parsed = urlparse(str(file_path))
    path = parsed.path if parsed.scheme else str(file_path)
    return path.lstrip("/")


def _fill_read_side_keys(meta: dict, chunk: dict, *, channel: str,
                         source: str | None, file_path: str | None) -> None:
    """补读侧真实依赖的 4 个键（P2-L8 · TL 裁定 Q5）。

    - `source`：文件身份键（见 `_resolve_source`）；`retrieval_fun_tool` 用
      `metadata.source.keyword` 精确匹配，`reranker_service` 用它拼「文件名 + 正文」；
    - `parsed_text_ref`：审计/引用定位，表格块为 `"table"`、正文块为 `parsed_text.md`
      （与 `kb_pipeline.build_index_payloads` 同口径）；
    - `n_rows` / `n_cols`：表格维度，取 IR 真值（`rows` / `cols`）；拿不到就是 `None`，
      **不编造** 0 或 1。
    """
    meta["source"] = _resolve_source(source, file_path)
    meta["parsed_text_ref"] = "table" if channel == "table" else "parsed_text.md"
    if channel == "table":
        rows = chunk.get("rows", chunk.get("n_rows"))
        cols = chunk.get("cols", chunk.get("n_cols"))
        meta["n_rows"] = rows
        meta["n_cols"] = cols


def _check_index_prefix(index_prefix: str, kb: str) -> None:
    """前缀必须把计划明确指向独立命名空间（P2-L8 · I1-b / R-1）。

    拒绝三种「看起来有前缀、其实会打线上」的写法：
    空串；不带尾下划线（`v2cand` + `kb_9` 会拼成 `v2candkb_9`，不是声明的命名空间）；
    等于库名（`kb_9` / `kb_9_` 拼出来就是旧索引名）。
    """
    prefix = (index_prefix or "").strip()
    if not prefix:
        raise IndexWriterError("INDEX_PREFIX_EMPTY", "index_prefix 不得为空（防误写线上索引）")
    if not prefix.endswith("_"):
        raise IndexWriterError(
            "INDEX_PREFIX_INVALID",
            f"index_prefix={index_prefix!r} 必须以 '_' 结尾（否则拼出的名字不是独立命名空间）")
    if prefix.rstrip("_") == kb:
        raise IndexWriterError(
            "INDEX_PREFIX_INVALID",
            f"index_prefix={index_prefix!r} 等于库名，拼出来就是旧索引名（防误写线上）")


def _resolve_file_id(artifact: dict, file_id: str | None) -> str:
    """解析真实 `file_id`：显式参数 > `artifact['file_id']` > `FILE_ID_MISSING`。

    刻意**不回落 `kb`**（P2-L7 裁定 1）：`store.commit()` 的 artifact 没有 `file_id`，
    回落会把「库」当「文件」，同库多文件在 ES metadata 上撞成同一 file_id，
    删除范围与邻块召回都会跨文件错配。
    """
    for candidate in (file_id, artifact.get("file_id")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        if candidate is not None and not isinstance(candidate, str):
            return str(candidate)
    raise IndexWriterError(
        "FILE_ID_MISSING",
        "缺真实 file_id：artifact 不含 file_id 且调用点未注入（不得回落 kb）")


# --------------------------------------------------------------------------- build
def build(chunks: list, artifact: dict, *, kb: str,
          index_prefix: str = DEFAULT_INDEX_PREFIX,
          file_id: str | None = None,
          file_path: str | None = None,
          source: str | None = None) -> IndexWritePlan:
    """按 channel 分组产出 es_plan / milvus_plan 两份写入计划。

    - 每份计划按目标 index/collection 拆成 body（text / table 分别一组）；
    - document_list 的每项 = `{page_content, metadata}`，顶层 `pk` / `_fill` 已剥掉
      （metadata 由 `enrich.build_payload` 生成，仅补 `metadata.pk` 与同源三元组）；
    - `duplicate_flag=False` 硬约束；`v2cand_` 前缀不碰线上索引名；
    - `content_hash` 由 `bind_artifact` 从同一份 chunks 复算，写入每份 metadata。

    P2-L7 additive：`file_id` 由调用点注入（`consume_for_kb` 的真实平台文件 id）。
    解析优先级 **显式参数 > `artifact['file_id']` > 抛 `FILE_ID_MISSING`**，
    **不再回落 `kb`**：`store.commit()` 的 artifact 不含 `file_id`，回落 `kb` 会把
    「按知识库」当成「按文件」写进 ES metadata / 删除范围，同一库多文件必然互相覆盖。

    P2-L8 additive（TL 12:1x 裁定 Q5）：补齐读侧真实依赖的 4 个 metadata 键
    `source` / `parsed_text_ref` / `n_rows` / `n_cols`。影子 metadata = 生产载荷键集
    **+** `artifact_id` / `content_hash` 两个 V2 溯源键（B-1 同源校验必需，不能删），
    二者都要在，不声称与线上完全一致。
    """
    if not chunks:
        raise IndexWriterError("CHUNKS_EMPTY", "chunks 为空，无法构建写入计划")
    artifact_id = artifact.get("artifact_id")
    content_uid = artifact.get("content_uid")
    if not artifact_id or not content_uid:
        raise IndexWriterError("ARTIFACT_IDENTITY_MISSING",
                               "artifact 缺 artifact_id / content_uid")
    _check_index_prefix(index_prefix, kb)

    resolved_file_id = _resolve_file_id(artifact, file_id)
    now = artifact.get("committed_at")  # 确定性：来自快照，不用当前时间
    # 绑定输入也带上解析后的 file_id：否则 ES 计划写的是真实文件 id、binding.docs 里
    # 却是回落值，同源校验的两份输入口径不一致（content_hash 不含 file_id，但溯源会错）。
    binding = bind_chunks(chunks, {**artifact, "file_id": resolved_file_id})
    content_hash = binding["content_hash"]

    groups: dict[str, list] = {}
    for chunk in chunks:
        groups.setdefault(chunk.get("channel", "text"), []).append(chunk)

    es_plan: list[dict] = []
    milvus_plan: list[dict] = []
    for channel in ("text", "table"):
        if channel not in groups:
            continue
        target = _target_name(channel, kb=kb, index_prefix=index_prefix)
        documents: list[dict] = []
        for chunk in groups[channel]:
            meta, _fill = enrich.build_payload(
                chunk, index_name=kb, file_id=resolved_file_id, now=now)
            # metadata.pk 保留（ES 用它当 _id，Milvus 用它当主键）；
            # 顶层 pk / _fill 不进 document_list（端点契约只收 page_content + metadata）。
            meta["pk"] = chunk["pk"]
            meta["artifact_id"] = artifact_id
            meta["content_hash"] = content_hash
            _fill_read_side_keys(meta, chunk, channel=channel, source=source,
                                 file_path=file_path)
            documents.append({"page_content": chunk["text"], "metadata": meta})

        es_plan.append({
            "index_name": target,
            "document_list": documents,
            "type": "",
            "duplicate_flag": False,
        })
        milvus_plan.append({
            # 不传 db_name：`kb` 与 Milvus database 是两个维度，把 `kb` 发下去会让
            # 19526 收到 `database not found[database=kb_9]`（真实库是 rag_knowledge_base）。
            # 19526 侧统一兜底 `db_name = db_name or server_config["milvus_database"]`
            # （milvus_kb_service.py:262 / :304 / :364），`del_doc_by_col` 也一直不传 ——
            # 「不传」是本系统的既有约定。
            "collection_name": target,
            "model_name": ES_MODEL_NAME,
            "document_list": documents,
            "consistency_level": ES_CONSISTENCY_LEVEL,
            "duplicate_flag": False,
        })

    return IndexWritePlan(
        kb=kb, index_prefix=index_prefix,
        artifact_id=artifact_id, content_uid=content_uid,
        content_hash=content_hash, binding=binding,
        es_plan=es_plan, milvus_plan=milvus_plan,
    )


# --------------------------------------------------------------------------- delete_scope
def delete_scope(*, kb: str, file_id: Any,
                 index_prefix: str = DEFAULT_INDEX_PREFIX) -> dict:
    """按 `file_id + pk` 精确删除的**计划**（离线，不执行删除、不写线上）。

    明确拒绝 `duplicate_flag=True` 的按 `metadata.source` 全量替换：同一 source
    下其它文件的 chunk 必须保留（PLAN F4 / R-3）。写前按 `file_id` 清理、
    写后按本批 `pk` 集合剪枝的落地由 L7 生产调用点完成，本 loop 只产计划。
    """
    fid = str(file_id)
    targets = []
    for name in (f"{index_prefix}{kb}", f"{index_prefix}table_chunks_{kb}"):
        targets.append({"side": "es", "index_name": name})
        targets.append({"side": "milvus", "collection_name": name})
    return {
        "kb": kb,
        "file_id": fid,
        "index_prefix": index_prefix,
        "scope": "file_id+pk",
        "duplicate_flag": False,
        "forbidden_scope": "source",
        "col_name": "metadata.file_id",
        "col_values": [fid],
        "pk_field": "metadata.pk",
        "targets": targets,
        "note": "写前按 file_id 清理、写后按本批 pk 集合剪枝（L7）；不按 source 全量替换",
    }


# --------------------------------------------------------------------------- apply
def _post_json(url: str, body: dict) -> None:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - 端点由调用方给定
        resp.read()


def apply(plan: IndexWritePlan, *, es_url: str, milvus_url: str) -> IndexWriteResult:
    """按 **先 ES 后 Milvus** 顺序把计划 POST 到给定端点（本 loop 只跑 mock）。

    任一侧失败立即返回带 `side` / `error` 的结果，供调用方登记补偿任务；
    **禁止只 log 后返回成功**（`ACCEPTANCE-BASELINE.yaml:28`）。
    """
    es_bodies = plan.es_plan if hasattr(plan, "es_plan") else plan["es_plan"]
    mv_bodies = plan.milvus_plan if hasattr(plan, "milvus_plan") else plan["milvus_plan"]
    calls: list[dict] = []
    completed: list[str] = []
    for side, url, bodies in (("es", es_url, es_bodies),
                              ("milvus", milvus_url, mv_bodies)):
        for body in bodies:
            target = body.get("index_name") or body.get("collection_name")
            try:
                _post_json(url, body)
            except Exception as exc:  # noqa: BLE001 - 失败必须带原因返回
                return IndexWriteResult(
                    status="FAILED", side=side,
                    error=f"{type(exc).__name__}: {exc}",
                    completed_sides=list(completed),
                    needs_compensation=(side == "milvus"),
                    calls=calls,
                )
            calls.append({"side": side, "url": url, "target": target})
        completed.append(side)
    return IndexWriteResult(
        status="OK", side=None, error=None,
        completed_sides=completed, needs_compensation=False, calls=calls,
    )
