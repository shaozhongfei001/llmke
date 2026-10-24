"""答案层 CLI：把一次请求跑成 JSON 响应，便于端到端演示与回归。

输入（JSON）：
    {"query": "...", "kb_id": "...", "ctx": {...},
     "chunks": [...], "document_texts": {"f-1": "全文..."}}

输出：`{"ok": true, "data": {...}}` 或 `{"ok": false, "error": {...}}`
退出码：0 = 有答案；2 = 拒绝（fail-closed）；3 = 输入不合法。

为什么不在这里连数据库：
    本命令要能在没有 MySQL 的环境复现"拒绝"行为；连库版本在 `tests/test_answer_db.py`
    与将来的服务入口里，两者共用同一个 `build_answer`。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from modules.answer_api.service import AnswerError, build_answer, to_api_error, to_api_response


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="answer_api")
    ap.add_argument("--input", type=Path, required=True, help="请求 JSON")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)

    try:
        req = json.loads(a.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _emit({"ok": False, "error": {"code": "ILLEGAL_INPUT", "message": str(e)}}, a.out)
        return 3

    try:
        result = build_answer(req["query"], req["ctx"], req["kb_id"],
                              req["chunks"], req["document_texts"])
    except AnswerError as e:
        _emit(to_api_error(e), a.out)
        return 2
    except KeyError as e:
        _emit({"ok": False, "error": {"code": "FIELD_MISSING", "message": str(e)}}, a.out)
        return 3

    _emit(to_api_response(result), a.out)
    return 0


def _emit(payload: dict, out: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if out:
        out.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
