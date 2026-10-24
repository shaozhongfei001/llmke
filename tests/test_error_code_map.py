"""守卫：源码里抛出的每个错误码，必须在 HTTP 状态表里有映射。

为什么需要
    演示时发现 `INSUFFICIENT_RELEVANCE` 被抛出了，但状态表没登记 → 返回 500，
    而正确语义是 422。这类"两处字符串漂移"不会让任何测试变红，只会让线上状态码出错。
    本测试用静态扫描把这种漂移变成红灯。
"""
from __future__ import annotations

import re
from pathlib import Path

from modules.answer_api.handler import STATUS_BY_CODE

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_WITHOUT_MAP = {"INTERNAL"}


def _codes_in_source() -> set[str]:
    codes: set[str] = set()
    for f in (ROOT / "modules/answer_api").glob("*.py"):
        codes |= set(re.findall(r'AnswerError\(\s*["\']([A-Z_]+)["\']', f.read_text(encoding="utf-8")))
    return codes


def test_every_raised_code_has_status_mapping():
    missing = sorted(_codes_in_source() - set(STATUS_BY_CODE) - ALLOWED_WITHOUT_MAP)
    assert not missing, f"缺少状态码映射: {missing}"


def test_key_semantics_are_correct():
    """几个容易记错的语义，单独钉死。"""
    assert STATUS_BY_CODE["INSUFFICIENT_RELEVANCE"] == 422      # 请求合法但答不了
    assert STATUS_BY_CODE["NO_EVIDENCE"] == 422
    assert STATUS_BY_CODE["INDEX_NOT_READY"] == 503             # 索引没激活，属运维
    assert STATUS_BY_CODE["MIXED_DOCUMENT_VERSION"] == 409      # 数据自相矛盾
    assert STATUS_BY_CODE["KB_NOT_AUTHORIZED"] == 403
