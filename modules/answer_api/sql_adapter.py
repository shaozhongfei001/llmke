"""取块的 IO 适配：SQL 由 citation_flow 生成，执行器由调用方注入。

为什么把 runner 抽成参数：
    单测要能验证"SQL 里确实带了授权谓词"，又不想每次都起数据库；
    真库测试则注入 mysql 客户端。同一段建 SQL 的逻辑被两条路径复用，
    避免"测试用的 SQL"和"生产用的 SQL"分叉。
"""
from __future__ import annotations

from typing import Callable

from modules.citation_flow.service import fetch_chunks_sql, rows_to_chunks
from modules.answer_api.service import AnswerError
from modules.authz.context import compile_chunk_predicate

Runner = Callable[[str], list[list[str]]]


def fetch_chunks(runner: Runner, ctx: dict, kb_id: str, *,
                 chunk_ids: list[str] | None = None, limit: int = 50) -> tuple[list[dict], str]:
    """返回 (chunks, 实际执行的 SQL)。SQL 一并返回，便于日志留痕与断言。"""
    sql = fetch_chunks_sql(ctx, kb_id, chunk_ids, limit)
    rows = runner(sql)
    return rows_to_chunks(rows), sql


def probe_active_generation(runner: Runner, kb_id: str) -> str | None:
    """返回该 KB 当前激活代次对应的 document_version；无激活/状态不对 → None。

    单独暴露出来，是为了让"索引还没就绪"与"查询没命中"能给出不同错误：
    前者是运维/发布问题（503），后者是业务结果（404/422）。
    """
    sql = ("SELECT g.document_version FROM index_generation_activation a "
           "JOIN index_generation g ON g.generation_id = a.generation_id "
           f"WHERE a.kb_id = '{kb_id.replace(chr(39), chr(39)*2)}' AND g.state = 'ACTIVE'")
    rows = runner(sql)
    if not rows or not rows[0]:
        return None
    return rows[0][0] or None


def fetch_chunks_active(runner: Runner, ctx: dict, kb_id: str, *,
                        chunk_ids: list[str] | None = None,
                        limit: int = 50) -> tuple[list[dict], str]:
    """只取**当前激活代次**的块。

    为什么必须做在 SQL 里：
        `document_chunk` 只有 `document_version`，没有 `generation_id`（schema 现状）。
        若在 Python 里事后比对，RETIRED 代次的块已经进了内存、进了日志；
        "未授权内容不进上下文"的不变式要求它在**取数时**就被排除。

    做法（不新增列即可用）：
        用相关子查询取 `index_generation_activation` 指向的代次，
        要求 `state='ACTIVE'`，且块版本等于该代次的 `document_version`。
        无激活行 / 状态不是 ACTIVE → 子查询为 NULL → `document_version = NULL` 恒不成立 → 0 行。
        这就是 fail-closed：指针缺失时不是"返回旧数据"，而是"什么都取不到"。

    已知局限（必须登记，勿当成完整解决方案）：
        - 一个代次只对应一个 `document_version`；同一 KB 内若多文件版本不同代，
          本查询无法区分（这是缺 `generation_id` 的直接后果）。
        - 正确修法是在 `document_chunk` 增加代次列或建 `chunk_generation` 映射，
          属 P0-04（设计仍 PROPOSED），需 index-owner 裁定，不在本层用代码绕过。
    """
    pred = compile_chunk_predicate(ctx, kb_id)          # 授权谓词恒在
    extra = ""
    if chunk_ids:
        quoted = ",".join("'" + c.replace("'", "") + "'" for c in chunk_ids)
        extra = f" AND chunk_id IN ({quoted})"
    active_version = (
        "SELECT g.document_version FROM index_generation_activation a "
        "JOIN index_generation g ON g.generation_id = a.generation_id "
        f"WHERE a.kb_id = '{kb_id}' AND g.state = 'ACTIVE'"
    )
    sql = ("SELECT chunk_id,kb_id,file_id,document_version,chunk_index,offset_start,offset_end,"
           "offset_unit,text,text_hash,content_hash,parser_version,chunk_strategy "
           f"FROM document_chunk WHERE ({pred}){extra} "
           f"AND document_version = ({active_version}) "
           f"ORDER BY chunk_index LIMIT {int(limit)}")
    rows = runner(sql)
    if not rows:
        # 0 行有两种原因，必须分开报：代次未就绪 vs 范围内确实没有命中。
        # 混成一个 NO_EVIDENCE，会让运维在"索引没激活"时去查业务数据。
        if probe_active_generation(runner, kb_id) is None:
            raise AnswerError("INDEX_NOT_READY", "该知识库没有处于 ACTIVE 的代次，索引未就绪")
    return rows_to_chunks(rows), sql
