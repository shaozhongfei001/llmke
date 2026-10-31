"""`describe` 操作：把"哪些能力真的验证过"变成机器可读，而不是写在文档里靠人记。

合同依据：`contracts/api/llmke-graph-engine-v1.openapi.yaml` 的 describe（服务身份 + 声明能力 +
已验证能力）。设计文档 §5 明确：**增量、删除、图导出、社区/报告要分别声明，不能拿空实现
伪装共同接口**；§6.5 明确 `executed_route=GRAPH` 必须有真实图执行 trace，普通查询允许
DENSE_FALLBACK，但强制图验收不能靠回退通过。

所以这里给三档状态：
- VERIFIED：有实跑证据（脚本/证据文档可指）；
- NOT_VERIFIED：代码路径存在但**没有**能证明它在真实数据上跑过（例如 GRAPH 路线）；
- NOT_IMPLEMENTED：根本还没写，禁止当通过。

`describe()` 只报告事实，不做能力宣称。要把它升成 VERIFIED，必须先有证据文件与实跑脚本。
"""

import json
import os

SCHEMA = "llmke.graph-engine.describe.v1"

# 每项：状态、依据、证据指针（无证据就必须是 NOT_VERIFIED / NOT_IMPLEMENTED）
CAPABILITIES = {
    "index_build": {
        "status": "VERIFIED",
        "note": "hipporag 2.0.0a4 在本机真实 index()：66/83 块、跨文件合并后仍可回指来源",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-C1-HIPPORAG-20261031.md",
    },
    "retrieve_dense_fallback": {
        "status": "VERIFIED",
        "note": "真实载荷检索命中并回指 SourceRef；未判定走的是图还是稠密",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-C1-HIPPORAG-BATCH-20261031.md",
    },
    "retrieve_graph_route": {
        "status": "NOT_VERIFIED",
        "note": "没有 executed_route=GRAPH 的执行 trace；检索命中不能当图执行证据（设计 §6.5）",
        "evidence": None,
    },
    "source_map_multi_source": {
        "status": "VERIFIED",
        "note": "同文异源 1 个引擎 chunk / N 个 SourceRef；删一留一有测试",
        "evidence": "tests/test_graph_engine_mapping.py",
    },
    "incremental_update": {
        "status": "NOT_IMPLEMENTED",
        "note": "首版按隔离快照全量重建；增量未实现",
        "evidence": None,
    },
    "delete_document": {
        "status": "NOT_IMPLEMENTED",
        "note": "撤权 fence 与按文档删除图产物未实现",
        "evidence": None,
    },
    "graph_export": {
        "status": "NOT_IMPLEMENTED",
        "note": "标准事实导出未实现，社区/global 因此无法消费真实产物",
        "evidence": None,
    },
    "community_report": {
        "status": "NOT_IMPLEMENTED",
        "note": "未消费真实社区产物；不得用普通 RAG 顶替",
        "evidence": None,
    },
    "platform_assertion_layer": {
        "status": "VERIFIED",
        "note": "平台标准断言层：方向/单位/生效期/可见范围/多来源/引用校验；"
                "九条业务语义用构造数据反证（引擎侧接线仍缺）",
        "evidence": "tests/test_graph_assertions.py",
    },
    "platform_retrieval_orchestration": {
        "status": "VERIFIED",
        "note": "路线先判（GRAPH/DENSE_FALLBACK + 原因）、require_graph 时回退不算通过、"
                "引用对回断言并校验可见性；用假 retriever 验编排，真实引擎接线仍缺",
        "evidence": "tests/test_graph_pipeline.py",
    },
    "engine_predicate_normalization": {
        "status": "NOT_IMPLEMENTED",
        "note": "断言层已能表达方向与单位，但引擎抽取结果尚未归一进该层",
        "evidence": None,
    },
    "engine_version_filtering": {
        "status": "NOT_IMPLEMENTED",
        "note": "as-of 过滤在断言层成立；引擎检索尚未按生效期约束",
        "evidence": None,
    },
    "engine_visibility_isolation": {
        "status": "NOT_IMPLEMENTED",
        "note": "查询侧 scope 过滤在断言层成立；构建期按可见集合隔离索引未做",
        "evidence": None,
    },
}

ALLOWED = {"VERIFIED", "NOT_VERIFIED", "NOT_IMPLEMENTED"}


def describe(engine_version=None, adapter_version="0.1.0"):
    """返回服务身份 + 能力声明；结构稳定，可直接进报告/接口。"""
    bad = [k for k, v in CAPABILITIES.items() if v["status"] not in ALLOWED]
    if bad:  # pragma: no cover - 防呆
        raise ValueError(f"能力状态非法: {bad}")

    caps = {k: dict(v) for k, v in CAPABILITIES.items()}
    # 没有证据指针的项不许自称 VERIFIED（这条是硬约束，不是提醒）
    lying = [k for k, v in caps.items() if v["status"] == "VERIFIED" and not v["evidence"]]
    if lying:
        raise ValueError(f"声明 VERIFIED 但无证据: {lying}")

    counts = {s: sum(1 for v in caps.values() if v["status"] == s) for s in ALLOWED}
    return {
        "schema": SCHEMA,
        "engine": {"name": "hipporag", "version": engine_version or "2.0.0a4",
                   "mode": "python-library"},
        "adapter": {"version": adapter_version,
                    "mapping_schema": "llmke.graph-engine.mapping.v1"},
        "declared": sorted(caps),
        "capabilities": caps,
        "counts": counts,
        # 强制图验收查询不得以 DENSE_FALLBACK 通过：这条是验收规则，不是能力
        "acceptance_rule": "GRAPH route required for graph-acceptance queries; "
                           "DENSE_FALLBACK is allowed only for ordinary queries",
        "env": {"hipporag_installed": bool(os.environ.get("HIPPORAG_AVAILABLE", ""))},
    }


def to_json(**kwargs):
    return json.dumps(describe(**kwargs), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    print(to_json())
