"""实时摄取链路的集成入口（V2 / VL1-03→B1 之间的一层）。

一次摄取 = 上游解析 → ParseArtifact 快照 → 投影（正文/表格双通道）。

为什么单独一层
--------------
解析服务（`alg_doc_parse_service`）与索引服务（`index_data_service`）是两个容器，
跨容器 import 会把部署绑死。所以链路在这里显式表达：调用方（解析任务 / 批量脚本）
只调 `ingest()`，由它保证"快照先于投影、投影先于索引"，并返回可直接交给索引层的 chunk。

三档开关（`INGEST_PROJECTION_MODE`）
----------------------------------
- `legacy`：不使用快照，直接返回 NOT_APPLICABLE（线上行为不变，不偷偷接新路径）；
- `shadow`：产出 chunk 供对照，**禁止**真正写索引（`apply_index=True` 会被拒）；
- `snapshot`：允许写入，但仍需调用方显式传 `apply_index=True`。

刻意不做
--------
- 不连 ES/Milvus/MySQL：只产出 chunk 载荷与报告，落地由索引层负责。
- 不重新解析原件：快照不存在就返回 `SKIPPED_NO_ARTIFACT`，不在这里兜底解析。
"""

from pathlib import Path

from parse_artifact import store
from rag_projection import projection as P

from .enrich import build_payload

MODES = ("legacy", "shadow", "snapshot")


class IngestRefused(RuntimeError):
    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _chunk_payload(chunk, index_name, file_id, ctx):
    """把投影块转成索引层能直接吃的形状（覆盖生产集合 33 字段，见 enrich.py）。"""
    channel = chunk["channel"]
    meta, fill = build_payload(chunk, index_name=index_name, file_id=file_id,
                               file_name=ctx.get("file_name"), file_path=ctx.get("file_path"),
                               file_size=ctx.get("file_size"))
    # `source` 在本栈里不是"解析产物路径"，而是**文件身份键**（实测消费点）：
    #   · alg_retrieval_service/retrieval_service.py:309-336 用 source 查同文件相邻块、
    #     算该文件最大 chunk_index、按 (source, chunk_index) 去重；
    #   · retrieval_global_view.py:37 记录 Java 侧一律 `endPoint + "/" + source` 拼 URL。
    # 所以这里必须写**每个文件唯一的对象键**。写成 parsed_text.md 会让所有文件共享同一身份：
    # 相邻块扩展到别的文件、跨文件去重、引用 URL 全部指向同一个假路径。
    # V2 的原文回指另行放 parsed_text_ref，不动 source 的既有语义。
    meta["source"] = ctx.get("source") or ctx.get("file_path") or ""
    meta["parsed_text_ref"] = ("parsed_text.md" if channel == "text"
                               else f"table:{chunk['locator'].get('table_id')}")
    fill["source_from"] = "object_key" if meta["source"] else "MISSING"
    if not meta["source"]:
        fill["placeholder"].append("source")
    if channel == "table":
        meta["n_rows"], meta["n_cols"] = chunk.get("rows"), chunk.get("cols")
    return {"index": index_name if channel == "text" else f"table_chunks_{index_name}",
            "page_content": chunk["text"], "metadata": meta, "pk": chunk["pk"], "_fill": fill}


def compare_channels(legacy, projected):
    """对照两臂的通道计数。`legacy` / `projected` 形如 {'kb_9': n, 'table_chunks_kb_9': m}。

    只做差值，不做"必须相等"的判定：两条链路的粒度本来就不同（legacy 合并相邻段落，
    投影按 IR 块切）。差异必须由人解释，不能用一个比例阈值假装通过。
    """
    keys = sorted(set(legacy) | set(projected))
    return {key: {"legacy": legacy.get(key, 0), "projected": projected.get(key, 0),
                  "diff": projected.get(key, 0) - legacy.get(key, 0)} for key in keys}


def ingest(artifact_dir, *, index_name, file_id, mode=None, apply_index=False,
           chunk_chars=800, overlap_chars=0, file_name=None, file_path=None, file_size=None,
           source=None):
    """返回 {'status','mode','artifact_id','channels','counts','chunks','refusals','field_fill'}。"""
    mode = (mode or P.mode_from_env()).strip().lower()
    if mode not in MODES:
        raise IngestRefused("INGEST_MODE_INVALID", f"{mode!r}，允许 {MODES}")
    if mode == "legacy":
        return {"status": "NOT_APPLICABLE", "mode": mode,
                "reason": "legacy 模式仍走现有解析分块，不消费快照"}
    if apply_index and mode != "snapshot":
        # shadow 只观察：写索引会让对照污染线上基准
        raise IngestRefused("APPLY_NOT_ALLOWED_IN_SHADOW", f"mode={mode}")

    policy = P.ProjectionPolicy(index_name=index_name, file_id=str(file_id),
                                chunk_chars=chunk_chars, overlap_chars=overlap_chars)
    result = P.project(Path(artifact_dir), policy, mode=mode)
    if result.status == "NOT_APPLICABLE":
        return {"status": "NOT_APPLICABLE", "mode": mode, "reason": result.stats.get("reason")}

    ctx = {"file_name": file_name, "file_path": file_path, "file_size": file_size,
           "source": source}
    payloads = [_chunk_payload(c, index_name, file_id, ctx) for c in result.chunks]
    fill = {"filled": [], "placeholder": [], "empty_by_design": [], "layout": "unavailable"}
    for item in payloads:
        part = item.pop("_fill")
        fill["source_from"] = part.get("source_from")
        for key in ("placeholder", "empty_by_design"):
            for name in part[key]:
                if name not in fill[key]:
                    fill[key].append(name)
        for name in part["filled"]:
            if name not in fill["filled"]:
                fill["filled"].append(name)
    counts = {}
    for item in payloads:
        counts[item["index"]] = counts.get(item["index"], 0) + 1
    return {
        "status": result.status,
        "mode": mode,
        "artifact_id": result.stats.get("artifact_id"),
        "artifact_quality": result.stats.get("artifact_quality"),
        "counts": counts,
        "channels": {"text": result.stats.get("chunks_text"),
                     "table": result.stats.get("chunks_table")},
        "chunks": payloads,
        "field_fill": fill,
        "refusals": result.refusals,
    }
