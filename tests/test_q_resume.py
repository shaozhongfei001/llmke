"""Q 断点续跑：整轮 40+ 分钟，被超时打断也必须知道"哪些是真过了"。

只测续跑判定，不跑真实检查（真跑在 Q 里）。
"""

import importlib.util
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "q_acc", os.path.join(REPO, "scripts", "v2_q_acceptance.py"))
q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(q)


def write_ckpt(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_all_pass_function_is_skipped_and_replayed(tmp_path):
    q.RESULTS.clear()
    calls = []
    q.check_fake = lambda: calls.append(1)
    ck = str(tmp_path / "ck.jsonl")
    write_ckpt(ck, [{"item": "graph:假检查", "status": "PASS", "evidence": {"n": 1},
                     "boundary": None, "fn": "check_fake"}])

    state = q.install_resume(ck)
    q.check_fake()                      # 应被替换成空操作

    assert state["resumed_functions"] == ["check_fake"]
    assert calls == []                  # 没有真的执行
    assert [r["item"] for r in q.RESULTS] == ["graph:假检查"]
    assert q.RESULTS[0]["evidence"] == {"n": 1}


def test_function_with_mixed_status_is_rerun(tmp_path):
    """有 SKIP/FAIL 就必须重跑：SKIP 常常是环境变了，不能当成"上次过了"。"""
    q.RESULTS.clear()
    calls = []
    q.check_mixed = lambda: calls.append(1)
    ck = str(tmp_path / "ck.jsonl")
    write_ckpt(ck, [{"item": "a", "status": "PASS", "evidence": None, "fn": "check_mixed"},
                    {"item": "b", "status": "SKIP", "evidence": None, "fn": "check_mixed"}])

    state = q.install_resume(ck)
    q.check_mixed()

    assert state["count"] == 0
    assert calls == [1]
    assert q.RESULTS == []


def test_missing_checkpoint_is_noop(tmp_path):
    q.RESULTS.clear()
    state = q.install_resume(str(tmp_path / "nope.jsonl"))
    assert state["resumed_functions"] == []
    assert "checkpoint 不存在" in state["reason"]


def test_broken_line_does_not_crash(tmp_path):
    """半个 JSON 行（进程正好在写）不能让续跑整体失败。"""
    q.RESULTS.clear()
    q.check_ok = lambda: None
    ck = str(tmp_path / "ck.jsonl")
    with open(ck, "w", encoding="utf-8") as fh:
        fh.write('{"item": "x", "status": "PASS", "fn": "check_ok"}\n')
        fh.write('{"item": "y", "status": "PA')      # 截断
    state = q.install_resume(ck)
    assert state["resumed_functions"] == ["check_ok"]


def test_record_writes_checkpoint_with_function_name(tmp_path):
    ck = str(tmp_path / "ck.jsonl")
    q.CHECKPOINT = ck
    q.RESULTS.clear()
    try:
        q.record("手写项", "PASS", {"v": 1})
    finally:
        q.CHECKPOINT = None
    row = json.loads(open(ck, encoding="utf-8").read().strip())
    assert row["item"] == "手写项" and row["status"] == "PASS"
    assert row["fn"] == "test_record_writes_checkpoint_with_function_name"
