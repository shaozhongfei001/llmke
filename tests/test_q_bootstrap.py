"""验收载荷自举 + 积压提示：两件事都堵"看起来通过"的口子。

- 载荷缺失时 Q 会整片 SKIP，报告仍然是"PASS"，但少测了半边；
- 积压满时只返回一个状态码，用户不知道要等多久、该做什么。
"""

import importlib.util
import json
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "q_acc", os.path.join(REPO, "scripts", "v2_q_acceptance.py"))
q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(q)

from graph_engine_adapter.backpressure import describe_backpressure  # noqa: E402


def write_payload(path, chunks=1):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"chunks": [{"text": f"块{i}"} for i in range(chunks)]}, fh)


def test_valid_payloads_do_not_call_generator(tmp_path):
    calls = []
    for p in q.payload_paths(str(tmp_path)):
        write_payload(p)
    paths = q.ensure_payloads(str(tmp_path), generator=lambda ids, d: calls.append(ids))
    assert len(paths) == 2
    assert calls == []                     # 不许"顺手重造"，那是覆盖真实样本


def test_missing_payload_is_generated(tmp_path):
    calls = []

    def gen(ids, d):
        calls.append(sorted(ids))
        for fid in ids:
            write_payload(os.path.join(d, f"ingest-{fid}.json"))

    paths = q.ensure_payloads(str(tmp_path), generator=gen)
    assert calls and set(calls[0]) == {"333", "329"}
    assert all(os.path.isfile(p) for p in paths)


def test_broken_json_is_regenerated(tmp_path):
    paths = q.payload_paths(str(tmp_path))
    write_payload(paths[0])
    with open(paths[1], "w", encoding="utf-8") as fh:
        fh.write('{"chunks": [')            # 截断
    calls = []

    def gen(ids, d):
        calls.append(sorted(ids))
        for fid in ids:
            write_payload(os.path.join(d, f"ingest-{fid}.json"))

    q.ensure_payloads(str(tmp_path), generator=gen)
    assert calls == [["329"]]               # 只补坏的那个


def test_generator_failure_raises_not_skips(tmp_path):
    """造不出验收数据是环境问题，必须抛；退化成 SKIP 会让报告看起来仍然全绿。"""
    def boom(ids, d):
        raise OSError("no space left")

    with pytest.raises(q.PayloadBootstrapError):
        q.ensure_payloads(str(tmp_path), generator=boom)


def test_generator_that_produces_nothing_still_raises(tmp_path):
    with pytest.raises(q.PayloadBootstrapError):
        q.ensure_payloads(str(tmp_path), generator=lambda ids, d: None)


def test_backpressure_message_has_wait_and_action():
    out = describe_backpressure({"status": "BACKPRESSURE", "pending": 12,
                                 "max_pending": 10, "rejected": 3})
    assert out["code"] == "REBUILD_BACKPRESSURE"      # 真实代码用的是这个码
    assert "12" in out["message_zh"] and "已满" in out["message_zh"]
    assert out["retry_after_s"] > 0
    assert out["user_action"]


def test_non_backpressure_returns_none():
    assert describe_backpressure({"status": "OK"}) is None
    assert describe_backpressure(None) is None
