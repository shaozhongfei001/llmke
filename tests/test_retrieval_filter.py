"""检索命中的后置过滤：as-of 与 scope 两道闸，方向刻意相反。

用**真实** `AssertionStore` / `Assertion` 而不是假 store：这两道闸的判定全靠
`facts_by_source` 与 `effective_from/effective_to` 的真实语义，假 store 只能证明
"我调用了自己写的 stub"，证明不了与断言层口径一致。
"""

import copy

from graph_engine_adapter.assertions import Assertion, AssertionStore, SourceRef
from graph_engine_adapter.retrieval_filter import (
    REASON_OUT_OF_WINDOW, REASON_SCOPE_DENIED, REASON_UNKNOWN_SCOPE, filter_hits)


def ref(file_id, locator="0-10"):
    return SourceRef(file_id=file_id, artifact_id="a" * 64, channel="text", locator=locator)


def store_with_windows():
    """三个文件、三种生效期形态：有明显过期、有未生效、有根本没写日期。"""
    s = AssertionStore()
    s.register_entity("p", "产品甲")
    # 333：2026 上半年有效
    s.add(Assertion(subject="p", predicate="额度", object_value=8000, unit="万元", key="额度",
                    effective_from="2026-01-01", effective_to="2026-07-01",
                    sources=[ref("333")]))
    # 444：2026 下半年才生效
    s.add(Assertion(subject="p", predicate="额度", object_value=9000, unit="万元", key="额度",
                    effective_from="2026-07-01", effective_to="2026-12-31",
                    sources=[ref("444")]))
    # 555：事实存在但**没有生效期**——不能当过期，也不能当有效期的证明
    s.add(Assertion(subject="p", predicate="适用客群", object_entity="ent:corp",
                    sources=[ref("555")]))
    return s


def hit(file_id, text="命中正文"):
    return {"text": text, "sources": [{"file_id": file_id}]}


# ---------------------------------------------------------------- 生效期
def test_as_of_inside_window_is_kept_and_agrees_with_assertion_layer():
    s = store_with_windows()
    out = filter_hits([hit("333")], as_of="2026-03-01", store=s)

    assert len(out["hits"]) == 1
    assert out["dropped"] == []
    assert out["stats"]["unknown_window"] == 0
    # 交叉校验：断言层在同一个 as_of 下也认为这条事实有效，两层口径一致
    assert [a.object_value for a in s.facts("p", "额度", as_of="2026-03-01")] == [8000]


def test_as_of_outside_window_is_dropped_with_reason():
    s = store_with_windows()
    long_text = "上半年" * 50          # 超过 40 字，用来验证日志截断
    out = filter_hits([hit("333", long_text)], as_of="2026-08-01", store=s)

    assert out["hits"] == []
    assert out["stats"] == {"input": 1, "kept": 0, "dropped": 1,
                            "unknown_window": 0, "unknown_scope_dropped": 0,
                            "trimmed_sources": 0}
    rec = out["dropped"][0]
    assert rec["reason"] == REASON_OUT_OF_WINDOW
    assert rec["file_ids"] == ["333"]
    assert len(rec["text_prefix"]) == 40          # 只留 40 字，不把正文灌进日志

    # 右开区间：到期当天即失效（与 AssertionStore._in_window 一致）
    assert filter_hits([hit("333")], as_of="2026-07-01", store=s)["hits"] == []
    assert len(filter_hits([hit("333")], as_of="2026-06-30", store=s)["hits"]) == 1


def test_file_without_effective_dates_is_kept_and_counted_as_unknown_window():
    """没写日期不能当过期：那会把大量正常内容误杀，安全机制一开就活不下去。"""
    s = store_with_windows()
    out = filter_hits([hit("555"), hit("999")], as_of="2026-08-01", store=s)

    # 555 是"有事实但无生效期"，999 是"完全没有事实"，两者都不可判定 → 都保留
    assert [h["text"] for h in out["hits"]] == ["命中正文", "命中正文"]
    assert out["dropped"] == []
    assert out["stats"]["unknown_window"] == 2      # 按 (命中, 来源) 对计数


def test_multi_source_hit_survives_when_one_source_is_still_valid():
    """多来源内容不能被单个过期来源拖死，但过期来源要从 citations 里裁掉。"""
    s = store_with_windows()
    h = {"text": "同一段话来自两个文件",
         "sources": [{"file_id": "333"}, {"file_id": "444"}]}
    out = filter_hits([h], as_of="2026-03-01", store=s)

    assert len(out["hits"]) == 1
    assert out["hits"][0]["sources"] == [{"file_id": "333"}]
    assert out["stats"]["trimmed_sources"] == 1
    assert out["stats"]["dropped"] == 0
    # 入参没被改（裁来源是生成新副本，不是就地扣）
    assert [s["file_id"] for s in h["sources"]] == ["333", "444"]


# ---------------------------------------------------------------- 可见域
def test_scope_hit_is_kept_and_out_of_scope_is_denied():
    doc_scopes = {"333": {"public", "dept-a"}, "444": {"dept-b"}}
    kept = filter_hits([hit("333")], scopes={"dept-a"}, doc_scopes=doc_scopes)
    assert len(kept["hits"]) == 1 and kept["dropped"] == []

    denied = filter_hits([hit("444")], scopes={"dept-a"}, doc_scopes=doc_scopes)
    assert denied["hits"] == []
    assert denied["dropped"][0]["reason"] == REASON_SCOPE_DENIED
    # 明确的越权不是"不可判定"，不许记到 unknown_scope_dropped 里去
    assert denied["stats"]["unknown_scope_dropped"] == 0


def test_unknown_scope_is_dropped_fail_closed():
    """可见性方向必须 fail-closed：查不到可见域就当无权限。"""
    doc_scopes = {"333": {"dept-a"}}
    out = filter_hits([hit("999")], scopes={"dept-a"}, doc_scopes=doc_scopes)

    assert out["hits"] == []
    assert out["dropped"][0]["reason"] == REASON_UNKNOWN_SCOPE
    assert out["stats"]["unknown_scope_dropped"] == 1


def test_scopes_without_doc_scopes_drops_everything():
    """调用方给了 scopes 却没给 doc_scopes：宁可全丢，也不能静默变成"全部可见"。"""
    out = filter_hits([hit("333"), hit("444")], scopes={"dept-a"})
    assert out["hits"] == []
    assert {d["reason"] for d in out["dropped"]} == {REASON_UNKNOWN_SCOPE}
    assert out["stats"]["unknown_scope_dropped"] == 2


def test_scope_and_window_denied_reports_visibility_reason():
    """多重原因同时成立时报可见性那条：它不会因为换个日期就变成可读。"""
    s = store_with_windows()
    out = filter_hits([hit("333")], as_of="2026-08-01", store=s,
                      scopes={"dept-b"}, doc_scopes={"333": {"dept-a"}})
    assert out["hits"] == []
    assert out["dropped"][0]["reason"] == REASON_SCOPE_DENIED


# ---------------------------------------------------------------- 默认不变 / 不可变
def test_without_filters_returns_input_unchanged():
    """没开闸就一点行为都不能变：否则"引入安全模块"会悄悄改掉默认语义。"""
    hits = [hit("1", "第一段"), hit("2", "第二段"), hit("3", "第三段")]
    out = filter_hits(hits)
    assert out["hits"] == hits
    assert [h["text"] for h in out["hits"]] == ["第一段", "第二段", "第三段"]
    assert out["dropped"] == []
    assert out["stats"]["input"] == 3 and out["stats"]["kept"] == 3
    assert out["stats"]["unknown_window"] == 0


def test_as_of_without_store_does_not_filter():
    """只给日期不给断言层：没有事实可查，猜日期等于编造，所以不过滤。"""
    hits = [hit("333")]
    out = filter_hits(hits, as_of="2099-01-01")
    assert out["hits"] == hits and out["dropped"] == []


def test_input_hits_are_not_mutated():
    s = store_with_windows()
    hits = [{"text": "A", "sources": [{"file_id": "333"}, {"file_id": "444"}]},
            {"text": "B", "sources": [{"file_id": "444"}]}]
    snapshot = copy.deepcopy(hits)

    out = filter_hits(hits, as_of="2026-03-01", store=s,
                      scopes={"dept-a"}, doc_scopes={"333": {"dept-a"}, "444": {"dept-a"}})

    assert hits == snapshot                      # 内容、顺序、来源列表全都没动
    assert len(hits) == 2
    assert out["hits"] is not hits               # 返回的是新列表
    assert out["stats"]["kept"] == 1 and out["stats"]["dropped"] == 1
