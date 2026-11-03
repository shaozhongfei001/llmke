"""跨范围合并检索：RRF 融合 + fail-closed 的范围解析。

重点不是"能合并"，而是三条容易被写错的判据：
1. 分数不可比，只能靠名次融合；
2. 同一内容出现在多个范围时要去重并加分，而不是返回两遍；
3. 范围查不到必须跳过并记录，全部查不到就拒绝——绝不回退全量索引。
"""

from graph_engine_adapter import merged, partition


def hit(text, file_id="f1"):
    return {"text": text, "sources": [{"file_id": file_id}]}


class FakeRetriever:
    def __init__(self, hits):
        self._hits = hits
        self.calls = []

    def retrieve(self, query, top_k=5):
        self.calls.append((query, top_k))
        return {"hits": self._hits[:top_k]}


def setup_root(tmp_path, scopes):
    entries = {}
    for scope in scopes:
        snap = tmp_path / scope
        snap.mkdir()
        entries[scope] = {"snapshot": str(snap)}
    partition.write_manifest(str(tmp_path), entries)
    return str(tmp_path)


def test_rrf_prefers_document_hit_by_multiple_scopes():
    a = [hit("公共制度"), hit("仅A的内部通知")]
    b = [hit("仅B的台账"), hit("公共制度")]
    out = merged.rrf_merge([a, b], top_k=3)
    assert out[0]["text"] == "公共制度"          # 被两路召回 → 分数最高
    assert out[0]["scopes_hit"] == [0, 1]
    assert len(out) == 3                          # 去重后 3 条，不是 4 条


def test_rrf_is_deterministic_on_ties():
    a = [hit("甲"), hit("乙")]
    b = [hit("乙"), hit("甲")]
    first = merged.rrf_merge([a, b])
    second = merged.rrf_merge([a, b])
    assert [x["text"] for x in first] == [x["text"] for x in second]


def test_retrieve_merged_uses_each_scope_and_reports(tmp_path):
    root = setup_root(tmp_path, ["dept-a", "dept-b"])
    a = FakeRetriever([hit("A内容"), hit("公共")])
    b = FakeRetriever([hit("B内容"), hit("公共")])
    out = merged.retrieve_merged(["dept-a", "dept-b"], root=root,
                                 loader=lambda snap: a if "dept-a" in snap else b,
                                 query="制度", top_k=3)
    assert out["reason"] == "MERGED"
    assert sorted(out["scopes_used"]) == ["dept-a", "dept-b"]
    assert out["hits"][0]["text"] == "公共"
    assert out["per_scope"] == 2


def test_missing_scope_is_skipped_and_recorded(tmp_path):
    root = setup_root(tmp_path, ["dept-a"])
    out = merged.retrieve_merged(["dept-a", "dept-z"], root=root,
                                 loader=lambda snap: FakeRetriever([hit("A内容")]),
                                 query="制度")
    assert out["scopes_missing"] == ["dept-z"]
    assert out["scopes_used"] == ["dept-a"]
    assert out["hit_count"] == 1


def test_no_resolvable_scope_is_fail_closed(tmp_path):
    root = setup_root(tmp_path, ["dept-a"])
    out = merged.retrieve_merged(["dept-z"], root=root,
                                 loader=lambda snap: FakeRetriever([hit("不该出现")]),
                                 query="制度")
    assert out["hits"] == [] and out["passed"] is False
    assert out["reason"] == "NO_RESOLVABLE_SCOPE"


def test_retriever_error_does_not_kill_other_scopes(tmp_path):
    root = setup_root(tmp_path, ["dept-a", "dept-b"])

    def loader(snap):
        if "dept-a" in snap:
            raise RuntimeError("engine down")
        return FakeRetriever([hit("B内容")])

    out = merged.retrieve_merged(["dept-a", "dept-b"], root=root, loader=loader, query="制度")
    assert out["errors"] and out["errors"][0]["scope"] == "dept-a"
    assert out["hit_count"] == 1 and out["scopes_used"] == ["dept-b"]


def test_empty_scope_list_is_rejected():
    out = merged.retrieve_merged([], root="/nonexistent", loader=lambda s: None, query="q")
    assert out["reason"] == "NO_SCOPE_GIVEN" and out["passed"] is False
