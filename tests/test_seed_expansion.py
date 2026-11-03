"""种子规范名补进查询：让引擎"按库里的写法"再认一次实体。

背景实测（同一份索引）：
- 问「华东精密制造有限公司的授信额度」→ 引擎执行 GRAPH，答 3000 万元；
- 问「华东精密的授信额度」→ 计划 GRAPH，但**引擎内部回退稠密**（它认不出简称）。
补规范名后简称问句也能真正走图。这里只测"补没补、补得对不对"，真跑在证据里。
"""

from graph_engine_adapter.assertions import Assertion, AssertionStore, SourceRef
from graph_engine_adapter.pipeline import retrieve

REF = SourceRef(file_id="333", artifact_id="a" * 64, channel="text", locator="0-10")


class RecordingRetriever:
    last_executed_route = "GRAPH"

    def __init__(self):
        self.queries = []

    def dense(self, query, top_k):
        self.queries.append(("dense", query))
        return [{"text": "块1", "sources": [{"file_id": "333", "artifact_id": "a" * 64,
                                             "channel": "text", "locator": "0-10"}]}]

    def graph(self, query, seeds, top_k):
        self.queries.append(("graph", query, tuple(seeds)))
        return [{"text": "块1", "sources": [{"file_id": "333", "artifact_id": "a" * 64,
                                             "channel": "text", "locator": "0-10"}]}]


def store():
    s = AssertionStore()
    s.register_entity("ent:hua", "华东精密制造有限公司")
    s.add(Assertion(subject="ent:hua", predicate="额度", object_value=3000, unit="万元",
                    key="额度", sources=[REF]))
    return s


def test_abbreviated_query_is_expanded_before_engine_call():
    r = RecordingRetriever()
    out = retrieve("华东精密的授信额度", store=store(), retriever=r)
    assert out["route"] == "GRAPH"
    method, query, seeds = r.queries[0]
    assert method == "graph"
    assert "华东精密制造有限公司" in query          # 补了规范名
    assert query.startswith("华东精密的授信额度")    # 原问句没被改写
    assert seeds == ("ent:hua",)


def test_full_name_query_is_not_duplicated():
    r = RecordingRetriever()
    retrieve("华东精密制造有限公司的授信额度", store=store(), retriever=r)
    _, query, _ = r.queries[0]
    assert query.count("华东精密制造有限公司") == 1


def test_query_without_seed_is_passed_through():
    r = RecordingRetriever()
    out = retrieve("今天天气怎么样", store=store(), retriever=r)
    assert out["route"] == "DENSE_FALLBACK"
    _, query = r.queries[0]
    assert query == "今天天气怎么样"
