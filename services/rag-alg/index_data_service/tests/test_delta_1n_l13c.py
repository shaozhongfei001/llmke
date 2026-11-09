"""P4-L13-C · 契约 §2.1 的 `file_ids` 1:N 语义（**不依赖 fastapi，双环境都必须跑**）。

契约原文（`02-CONTRACTS.md:138`）：

> 两块完全相同文本（块 id 是文本哈希）在引擎里合并为一块，`file_ids` 数组承载
> 「这块文本同时属于哪些文件」…**删除单文件时只从对应 `file_ids` 剔除该 file_id，块保留**。

这三条语义此前**从未被验证**（L9 的实现只支持单值 `file_id`，两侧单测各自绿）。

本文件只测**纯函数**（`_as_live` / `_write_sources`），不需要 pydantic/fastapi；
请求模型层的断言在 `tests/test_delta_1n_model_l13c.py`（仅 hipporag）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from graph_engine_adapter import delta_build as D


class _FakeEngine:
    """按 text 给 idx：同一 text 永远同一个 idx（引擎按文本哈希合并块）。"""

    def __init__(self, mapping):
        self._mapping = mapping

    def openie_docs(self):
        return [{"passage": t, "idx": i} for t, i in self._mapping.items()]


def _doc(fids, text, locator=None, title=None, pk=None):
    """鸭子类型 doc（与 `BuildDoc` 同形）：`file_ids` 是**数组**。"""
    class _D:
        pass

    d = _D()
    d.file_ids = list(fids)
    d.text = text
    d.locator = locator or "chunk=0"
    d.title = title
    d.pk = pk
    d.parse_artifact_id = "c" * 64
    return d


# --------------------------------------------------------------- 判据 1：单元素数组
def test_single_file_id_yields_one_source(tmp_path: Path) -> None:
    text = "唯一的正文"
    engine = _FakeEngine({text: "idx-single"})

    live = D._as_live([_doc(["290"], text)])
    assert len(live) == 1 and live[0]["file_id"] == "290"

    sources = D._write_sources(str(tmp_path), live, engine)
    assert list(sources) == ["idx-single"]
    assert len(sources["idx-single"]) == 1
    assert sources["idx-single"][0]["file_id"] == "290"


# --------------------------------------------------------------- 判据 2：同文异源
def test_same_text_two_files_merge_block_but_keep_two_sources(tmp_path: Path) -> None:
    """两块完全相同文本 → 引擎**一块**；`sources` 该 idx 下 **2 个** source。"""
    text = "两文件共有的正文"
    engine = _FakeEngine({text: "idx-shared"})

    live = D._as_live([_doc(["290", "291"], text)])
    assert len(live) == 2, f"_as_live 应把 file_ids 展开成多行，实际 {len(live)} 行"
    assert {row["file_id"] for row in live} == {"290", "291"}
    assert {row["text"] for row in live} == {text}, "同一 text 的多行必须文本一致"

    sources = D._write_sources(str(tmp_path), live, engine)
    assert list(sources) == ["idx-shared"], "同一文本只应产生一个 idx（引擎合并块）"
    assert len(sources["idx-shared"]) == 2, (
        f"该 idx 应有 2 个 source（1:N），实际 {json.dumps(sources, ensure_ascii=False)}")
    assert {s["file_id"] for s in sources["idx-shared"]} == {"290", "291"}


# --------------------------------------------------------------- 判据 3：删一个文件块保留
def test_delete_one_of_two_files_keeps_block(tmp_path: Path) -> None:
    """契约 §2.1 原话：删除单文件时只从 `file_ids` 剔除该 id，**块保留**。"""
    text = "两文件共有的正文"
    engine = _FakeEngine({text: "idx-shared"})

    D._write_sources(str(tmp_path), D._as_live([_doc(["290", "291"], text)]), engine)
    # 重建：291 被删，只剩 290
    sources = D._write_sources(str(tmp_path), D._as_live([_doc(["290"], text)]), engine)

    assert "idx-shared" in sources, "删掉一个来源后块必须保留（不能整块消失）"
    assert len(sources["idx-shared"]) == 1
    assert sources["idx-shared"][0]["file_id"] == "290"


# --------------------------------------------------------------- 兜底：不得静默丢块
def test_as_live_does_not_silently_drop_doc(tmp_path: Path) -> None:
    """`file_ids` 缺失/为空时不得静默丢块（宁可留空 id，也不要让正文消失）。"""
    text = "没有 file_ids 的正文"
    engine = _FakeEngine({text: "idx-x"})

    live = D._as_live([_doc([], text)])
    assert len(live) == 1, "空 file_ids 也要保留一行，否则正文静默消失"
    assert live[0]["file_id"] == ""
