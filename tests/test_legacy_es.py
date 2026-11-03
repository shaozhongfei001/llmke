"""legacy ES 取块：只读输入适配，失败必须给出可读原因而不是空列表。"""

import pytest

from graph_engine_adapter.legacy_es import fetch_docs


class Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body


def body(rows, total=None, code=200):
    return {"code": code, "msg": "ok",
            "data": {"total_count": total if total is not None else len(rows),
                     "result_data": rows}}


def test_two_chunks_map_file_id_and_locator():
    rows = [
        {"id1": {"page_content": "第一段", "metadata": {
            "file_id": "999010", "page_number": "[0, 0]", "offset": "[[0, 66]]",
            "chunk_index": "0"}}},
        {"id2": {"page_content": "|客户|额度|", "metadata": {
            "file_id": "999010", "page_number": "[1, 1]", "offset": "[[0, 8]]",
            "chunk_index": "1"}}},
    ]
    docs, err = fetch_docs("kb_9", "title", ["丙.docx"], post=lambda url, p: Resp(200, body(rows)))
    assert err is None
    assert [d["text"] for d in docs] == ["第一段", "|客户|额度|"]
    assert docs[0]["file_id"] == "999010"
    # page_number 全 0 = 未分页，不能拼成"第 0 页"；offset/chunk 仍保留
    assert "page=-" in docs[0]["locator"]
    assert "offset=[[0, 66]]" in docs[0]["locator"] and "chunk=0" in docs[0]["locator"]


def test_missing_metadata_falls_back_without_inventing_page():
    rows = [{"id9": {"page_content": "无元数据", "metadata": {}}}]
    docs, err = fetch_docs("kb_9", None, None, post=lambda url, p: Resp(200, body(rows)))
    assert err is None
    assert docs[0]["locator"] == "es:id9"
    assert docs[0]["file_id"] == "kb_9"


def test_empty_result_is_error_not_empty_success():
    docs, err = fetch_docs("kb_9", "title", ["x"], post=lambda url, p: Resp(200, body([], total=0)))
    assert docs == [] and "未查询到" in err


def test_es_code_non_200_is_error():
    docs, err = fetch_docs("kb_9", None, None,
                           post=lambda url, p: Resp(200, {"code": 500, "msg": "index missing"}))
    assert docs == [] and "code=500" in err


def test_connection_exception_is_error_with_reason():
    def boom(url, payload):
        raise TimeoutError("upstream timed out")

    docs, err = fetch_docs("kb_9", None, None, post=boom)
    assert docs == [] and "TimeoutError" in err


def test_space_name_required():
    docs, err = fetch_docs("", None, None)
    assert docs == [] and "space_name" in err
