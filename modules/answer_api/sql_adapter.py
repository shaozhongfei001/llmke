"""取块的 IO 适配：SQL 由 citation_flow 生成，执行器由调用方注入。

为什么把 runner 抽成参数：
    单测要能验证"SQL 里确实带了授权谓词"，又不想每次都起数据库；
    真库测试则注入 mysql 客户端。同一段建 SQL 的逻辑被两条路径复用，
    避免"测试用的 SQL"和"生产用的 SQL"分叉。
"""
from __future__ import annotations

from typing import Callable

from modules.citation_flow.service import fetch_chunks_sql, rows_to_chunks

Runner = Callable[[str], list[list[str]]]


def fetch_chunks(runner: Runner, ctx: dict, kb_id: str, *,
                 chunk_ids: list[str] | None = None, limit: int = 50) -> tuple[list[dict], str]:
    """返回 (chunks, 实际执行的 SQL)。SQL 一并返回，便于日志留痕与断言。"""
    sql = fetch_chunks_sql(ctx, kb_id, chunk_ids, limit)
    rows = runner(sql)
    return rows_to_chunks(rows), sql
