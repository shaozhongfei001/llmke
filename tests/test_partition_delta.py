"""按范围的增量重建：省时间可以，省正确性不行。

这一组钉住的都是"编排层"才会犯的错（`rebuild_delta` 本身的语义由 `test_rebuild_delta.py` 管）：

- **清单是整表覆盖的**：重建 A 范围时若只写 A 的条目，B 就从清单里消失，
  之后 `resolve(root, "B")` 返回 None —— 那条范围从此 fail-closed 查不到。这是本组最重要的一条；
- 没有基准快照时**拒绝**而不是默默全量（静默降级会让"增量"这两个字失去意义），
  但"首次构建"是常态，所以给一个**显式**开关，并把 mode/原因写进返回值；
- 失败时清单与指针都不动：路由还指着旧快照，旧快照继续服务；
- 目标目录必须落在 `scope_dir(root, scope)` 下：同范围同根，否则路由与快照不是同一棵树。
"""

import json
import os
import time

import pytest

from graph_engine_adapter import partition


def doc(fid, text, visibility=None):
    d = {"file_id": fid, "text": text}
    if visibility is not None:
        d["visibility"] = visibility
    return d


def graph_path(target):
    return os.path.join(target, "graph.json")


def _dump(target, texts):
    with open(graph_path(target), "w", encoding="utf-8") as fh:
        json.dump({"chunks": list(texts)}, fh, ensure_ascii=False)


def _load(target):
    path = graph_path(target)
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return list(json.load(fh)["chunks"])


def full_build(live, target):
    os.makedirs(target, exist_ok=True)
    _dump(target, [d["text"] for d in live])
    return {"chunks": len(live)}


def apply_fn(target, texts):
    """假引擎的增量：按文本集合比差异，然后把目录调成"恰好这些文本"。"""
    before = _load(target)
    added = [t for t in texts if t not in before]
    deleted = [t for t in before if t not in texts]
    _dump(target, list(texts))
    return {"deleted": len(deleted), "added": len(added),
            "reused": len(texts) - len(added), "remaining": len(texts),
            "consistent": True}


def setup_two_scopes(root, *, keep_last=2):
    """两个范围各建一次全量：s-401 只对 dept-b 可见，其余 public（两个范围都看得见）。"""
    docs = [doc("s-1", "授信台账 A", ["public"]),
            doc("s-2", "授信台账 B", ["public"]),
            doc("s-401", "五级分类口径", ["dept-b"])]
    for scope in ("dept-a", "dept-b"):
        partition.scope_delta_build(str(root), scope, docs, full_build, apply_fn,
                                    keep_last=keep_last, allow_full_build=True)
    return docs


# ---------------------------------------------------------------- delta_plan

def test_no_baseline_cannot_delta(tmp_path):
    """从没建过：清单都不存在，只能走全量。"""
    plan = partition.delta_plan(str(tmp_path), "dept-a", [doc("s-1", "x")])
    assert plan["can_delta"] is False
    assert plan["reason"] == "NO_MANIFEST"
    assert plan["base"] is None
    assert [d["file_id"] for d in plan["docs"]] == ["s-1"]


def test_scope_missing_from_manifest_cannot_delta(tmp_path):
    """清单里没有这个范围：不猜、不借用别范围的快照。"""
    setup_two_scopes(tmp_path)
    plan = partition.delta_plan(str(tmp_path), "dept-z", [doc("s-1", "x")])
    assert plan["can_delta"] is False
    assert plan["reason"] == "SCOPE_NOT_LISTED"
    assert plan["base"] is None


def test_snapshot_dir_gone_cannot_delta(tmp_path):
    """清单写着但目录没了（被清理/搬走）：仍然只能全量，不能拿清单当真。"""
    setup_two_scopes(tmp_path)
    entry = partition.resolve(str(tmp_path), "dept-b")
    os.rename(entry["snapshot"], entry["snapshot"] + "-moved")
    plan = partition.delta_plan(str(tmp_path), "dept-b", [doc("s-1", "x")])
    assert plan["can_delta"] is False
    assert plan["reason"] == "SNAPSHOT_DIR_MISSING"


def test_plan_filters_docs_by_visibility(tmp_path):
    """该范围该喂哪些文档由 plan 算好：别的范围的私有内容不许混进来。"""
    docs = setup_two_scopes(tmp_path)
    plan = partition.delta_plan(str(tmp_path), "dept-a", docs)
    assert plan["can_delta"] is True
    assert plan["reason"] == "OK"
    assert "s-401" not in [d["file_id"] for d in plan["docs"]]
    assert [d["file_id"] for d in partition.delta_plan(
        str(tmp_path), "dept-b", docs)["docs"]] == ["s-1", "s-2", "s-401"]


# ------------------------------------------------------- 清单合并（核心回归）

def test_delta_keeps_other_scope_entries(tmp_path):
    """重建 A 不能让 B 从清单里消失——`write_manifest` 是整表覆盖。"""
    docs = setup_two_scopes(tmp_path)
    b_before = partition.resolve(str(tmp_path), "dept-b")
    assert b_before is not None

    changed = [d for d in docs if d["file_id"] != "s-1"] + [doc("s-9", "新增条款")]
    out = partition.scope_delta_build(str(tmp_path), "dept-a", changed, full_build, apply_fn)

    assert out["mode"] == "DELTA"
    assert out["other_scopes"] == ["dept-b"]
    a_after = partition.resolve(str(tmp_path), "dept-a")
    b_after = partition.resolve(str(tmp_path), "dept-b")
    assert a_after is not None and b_after is not None
    assert b_after == b_before                       # B 的条目逐字节没变
    assert a_after["snapshot"] == out["current"]["dir"]
    # 落盘清单里也确实是两条，不只是内存里对
    raw = json.loads(open(os.path.join(str(tmp_path), partition.MANIFEST_NAME),
                          encoding="utf-8").read())
    assert sorted(raw["scopes"]) == ["dept-a", "dept-b"]


def test_failed_apply_keeps_manifest_and_old_snapshot(tmp_path):
    """增量炸了：清单不动、指针不动、旧快照照样解析得到。"""
    docs = setup_two_scopes(tmp_path)
    manifest_path = os.path.join(str(tmp_path), partition.MANIFEST_NAME)
    before_manifest = open(manifest_path, encoding="utf-8").read()
    before_entry = partition.resolve(str(tmp_path), "dept-a")

    def boom(target, texts):
        raise RuntimeError("引擎删除失败")

    with pytest.raises(partition.ScopeDeltaError) as excinfo:
        partition.scope_delta_build(str(tmp_path), "dept-a", docs, full_build, boom)

    message = str(excinfo.value)
    assert "dept-a" in message and "旧快照继续服务" in message
    assert open(manifest_path, encoding="utf-8").read() == before_manifest
    assert partition.resolve(str(tmp_path), "dept-a") == before_entry
    assert os.path.isdir(before_entry["snapshot"])
    assert _load(before_entry["snapshot"])                    # 旧快照内容还在
    assert partition.resolve(str(tmp_path), "dept-b") is not None


def test_failed_full_build_leaves_scope_absent(tmp_path):
    """首次构建就失败：清单里不该凭空出现这个范围（否则路由指向不存在的快照）。"""
    def boom(live, target):
        raise RuntimeError("模型加载失败")

    with pytest.raises(partition.ScopeDeltaError):
        partition.scope_delta_build(str(tmp_path), "dept-a", [doc("s-1", "x")],
                                    boom, apply_fn, allow_full_build=True)
    assert partition.resolve(str(tmp_path), "dept-a") is None


# ------------------------------------------------------------- 编排与目录

def test_delta_target_stays_under_scope_dir(tmp_path):
    """同一范围同一根：快照落在 scope_dir 下，而不是另起一棵树。"""
    docs = setup_two_scopes(tmp_path)
    expected_root = partition.scope_dir(str(tmp_path), "dept-a")
    out = partition.scope_delta_build(str(tmp_path), "dept-a", docs, full_build, apply_fn)
    assert out["root"] == expected_root
    assert os.path.dirname(out["current"]["dir"]) == expected_root
    assert out["current"]["dir"].startswith(expected_root + os.sep)


def test_no_baseline_is_refused_not_silently_full(tmp_path):
    """没有基准时默认**拒绝**——静默降级会让"增量"变成一句无法观测的承诺。"""
    with pytest.raises(partition.ScopeDeltaError) as excinfo:
        partition.scope_delta_build(str(tmp_path), "dept-a", [doc("s-1", "x")],
                                    full_build, apply_fn)
    assert "NO_MANIFEST" in str(excinfo.value)
    assert partition.resolve(str(tmp_path), "dept-a") is None


def test_explicit_full_build_reports_why(tmp_path):
    """首次构建走显式开关：返回值必须说清跑的是全量、以及为什么。"""
    out = partition.scope_delta_build(str(tmp_path), "dept-a", [doc("s-1", "x")],
                                      full_build, apply_fn, allow_full_build=True)
    assert out["mode"] == "FULL"
    assert out["fallback_reason"] == "NO_MANIFEST"
    assert partition.resolve(str(tmp_path), "dept-a")["chunks"] == 1


def test_keep_last_prunes_old_snapshot_but_pointer_resolves(tmp_path):
    """keep_last=1：旧快照目录被清掉，但当前指针与清单仍指向**存在**的新快照。

    这里刻意让两次构建相隔一秒：`rebuild._promote` 是按快照目录名排序决定清理顺序的，
    名字里的微秒尾巴（`time_ns() % 1000000`）在同一秒内并不单调，同一秒内建两份时
    排序可能与真实时间相反（那是 `rebuild.py` 既有的命名约定，不在本次改动范围内）。
    用一秒间隔让名字序 = 时间序，这条测试才钉的是 keep_last 语义而不是命名巧合。
    """
    deps = setup_two_scopes(tmp_path, keep_last=1)
    first = partition.resolve(str(tmp_path), "dept-a")["snapshot"]
    time.sleep(1.05)
    out = partition.scope_delta_build(str(tmp_path), "dept-a", deps, full_build, apply_fn,
                                      keep_last=1)
    second = out["current"]["dir"]
    assert second != first
    assert not os.path.isdir(first)                  # 旧快照已被清理
    assert os.path.isdir(second)
    assert partition.resolve(str(tmp_path), "dept-a")["snapshot"] == second


def test_repeated_delta_twice_still_usable(tmp_path):
    """同一范围连续两次增量：指针、清单、快照内容三者一致，且第二次仍能读到第一次的成果。"""
    docs = setup_two_scopes(tmp_path)
    step1 = partition.scope_delta_build(str(tmp_path), "dept-a", docs, full_build, apply_fn)
    assert _load(step1["current"]["dir"]) == ["授信台账 A", "授信台账 B"]

    docs2 = [d for d in docs if d["file_id"] != "s-2"] + [doc("s-3", "补充条款")]
    step2 = partition.scope_delta_build(str(tmp_path), "dept-a", docs2, full_build, apply_fn)

    assert step2["current"]["dir"] != step1["current"]["dir"]
    assert _load(step2["current"]["dir"]) == ["授信台账 A", "补充条款"]
    entry = partition.resolve(str(tmp_path), "dept-a")
    assert entry["snapshot"] == step2["current"]["dir"]
    assert entry["documents"] == 2
    assert entry["chunks"] == 2
    assert partition.resolve(str(tmp_path), "dept-b") is not None   # 另一范围始终没被牵连


def test_missing_new_snapshot_dir_keeps_manifest(tmp_path, monkeypatch):
    """构建"说成功了"但快照目录不在：清单不能跟着指向空气，必须留在旧快照上。"""
    docs = setup_two_scopes(tmp_path)
    before = partition.resolve(str(tmp_path), "dept-a")

    def fake_delta(root, fence, live, apply_fn, *, keep_last=2, fencing=None):
        return {"current": {"dir": os.path.join(root, "snapshot-gone"),
                            "documents": 1, "mode": "DELTA", "generation": 0}}

    monkeypatch.setattr(partition, "rebuild_delta", fake_delta)
    with pytest.raises(partition.ScopeDeltaError) as excinfo:
        partition.scope_delta_build(str(tmp_path), "dept-a", docs, full_build, apply_fn)
    assert "快照目录不存在" in str(excinfo.value)
    assert partition.resolve(str(tmp_path), "dept-a") == before
    assert os.path.isdir(before["snapshot"])


def test_unreadable_manifest_is_not_guessed(tmp_path):
    """清单坏了就当没有：不许"猜"它的内容，也不许拿空表去覆盖别人的条目。"""
    setup_two_scopes(tmp_path)
    with open(os.path.join(str(tmp_path), partition.MANIFEST_NAME), "w",
              encoding="utf-8") as fh:
        fh.write("{ 这不是 JSON")
    plan = partition.delta_plan(str(tmp_path), "dept-a", [doc("s-1", "x")])
    assert plan["can_delta"] is False
    assert plan["reason"] == "MANIFEST_UNREADABLE"
