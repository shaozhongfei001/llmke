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
        # P3-L11 additive：登记 HTTP 面。`http` 是**可选**字段（旧消费方读不到也不受影响），
        # 形状 [{method, path}]，method 大写、path 含 /v2 前缀。不含它也能构造合法能力项。
        "http": [{"method": "POST", "path": "/v2/graph/build"}],
    },
    "retrieve_dense_fallback": {
        "status": "VERIFIED",
        "note": "真实载荷检索命中并回指 SourceRef；未判定走的是图还是稠密",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-C1-HIPPORAG-BATCH-20261031.md",
    },
    "retrieve_graph_route": {
        "status": "VERIFIED",
        "note": "2026-11-03 独立实例 18095 真跑两组对照（12 块语料/68 事实/251 边）："
                "A 组 enable_graph=true → executed_route=GRAPH、graph_calls=1、"
                "seed_hits=['ent:智造贷']、rerank_fallback=false、facts_after_rerank=1；"
                "B 组 enable_graph=false → DENSE_FALLBACK + reason=GRAPH_DISABLED、graph_calls=0。"
                "成立前提有两条，都落在代码里而不是口头：①HTTP 层 QueryRequest 有 seeds/enable_graph "
                "并把种子传给引擎；②服务端默认安装中文补丁（上游 text_processing 会把中文清成空串，"
                "不装则事实恒为 ('','',x)、中文种子换算撞 md5('') 空实体，命中记 seed_hits_degenerate "
                "而不计入 seed_hits）。产品链路（Java→19532 shim→18094）透传 seeds 仍未接，见证据 §9",
        # 指纹变更记录：初版 c531a350…；2026-11-03 15:10 追加 §10（临时实例占用预览端口 18095 的处置与复跑改端口）
        # 后为下列值，初版 sha 已写在该文件 §10 内，便于审计"改了什么、为什么改"。
        "evidence": "docs/v2-tasks/evidence/A2-pure-graph-route.md"
                    " (sha256 59eebfe865c1550ec144e41fd3da5a92d419ce69eb32e26809c64e6b96f53969)",
    },
    "source_map_multi_source": {
        "status": "VERIFIED",
        "note": "同文异源 1 个引擎 chunk / N 个 SourceRef；删一留一有测试",
        "evidence": "tests/test_graph_engine_mapping.py",
    },
    "incremental_update": {
        "status": "VERIFIED",
        "note": "复制上一份快照后就地应用差异：hp.delete 去掉多余块、hp.index(to_add) 复用 "
                "load_existing_openie 只对新块抽取（**增量抽取 + 全量重建图**，两件事分开说）。"
                "真跑 5 块：全量 32.4s → 增量 7.5s（4.3×），删 3 增 1 复用 2，"
                "openie 5→3 == 期望 5-3+1；检索层 full vs delta 命中完全一致",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-DELTA-REBUILD-20261031.md",
        # P3-L11 additive：此前只声明引擎能力、没声明怎么调用，导致「按 capabilities 判断
        # 能不能通过 HTTP 做增量」会得到错误结论。note 保持「增量抽取 + 全量重建图」原样。
        "http": [{"method": "POST", "path": "/v2/graph/delta"}],
    },
    "visibility_fence": {
        "status": "VERIFIED",
        "note": "撤权后先验索引代次再按来源过滤：旧内容即使被引擎返回也会被拦下；"
                "代次落后直接拒绝读。引擎侧增量删除/全量重建编排仍未实现",
        "evidence": "tests/test_graph_fence.py",
    },
    "isolated_snapshot_rebuild": {
        "status": "VERIFIED",
        "note": "撤权后用存活文件在新目录重建快照，指针原子切换并带 fence 代次；"
                "真实演练：撤 329 后新快照仅 333 的 3 块、无撤权正文，旧代次被拒、新代次可读",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-REBUILD-20261031.md",
    },
    "delete_document": {
        "status": "VERIFIED",
        "note": "删除走**文本差集**而非命令式 delete(document_id)：调用方给全量存活文档，"
                "apply_delta 先 hp.delete(多出来的块) 再增量，删除在隔离快照内完成、"
                "指针切换后才对读者可见。真跑删除 3 块后快照内已无被删正文、检索不再命中。"
                "边界：同文本来自不同文档时会合并成一块（无法只删其一）",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-DELTA-REBUILD-20261031.md",
    },
    "graph_export": {
        "status": "VERIFIED",
        "note": "节点/边/事实导出为稳定排序的 JSONL（同输入两次 sha256 相同），"
                "支持最小边权过滤与按度数截断（不留悬空边）；`--compare` 直接给结构化差异。"
                "真跑 30 节点/109 边/50 事实；full vs delta 差异恰为 1 节点/2 边/1 事实"
                "（董事会-审议通过-单笔授信），与 C2 抽取差异一致",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-GRAPH-EXPORT-20261101.md",
    },
    "community_report": {
        "status": "VERIFIED",
        "note": "社区/global 只消费经校验的标准事实导出（断言层），确定性标签传播，"
                "报告引用逐条校验；真实语料 29 事实→5 社区、0 失效引用。"
                "已接线到 HTTP：建图后写 community.json，POST /v2/graph/global 返回 answer+citations，"
                "19532 /retrieval_documents_global 转发；12 篇语料 68/72 事实→33/34 社区、引用 0 失效。"
                "限制：answer 只逐条拼装带来源事实，不做自然语言综合；相关社区用字符二元组重合度；"
                "同一快照报告逐字节可复现，但端到端因上游 LLM 抽取非确定（68/72）不可复现",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-COMMUNITY-REPORT-20261031.md；"
                    "docs/v2-tasks/evidence/S3-retrieval-shim.md",
        # P3-L11 additive：note 里的散文端点（`POST /v2/graph/global`）**原样保留**，
        # 这里补结构化版本。测试断言「note 里出现的 /v2 路径 ⊆ 本列表」，防散文与结构化漂移。
        "http": [{"method": "POST", "path": "/v2/graph/global"}],
    },
    "platform_assertion_layer": {
        "status": "VERIFIED",
        "note": "平台标准断言层：方向/单位/生效期/可见范围/多来源/引用校验；"
                "九条业务语义用构造数据反证（引擎侧接线仍缺）",
        "evidence": "tests/test_graph_assertions.py",
    },
    "retrieve_graph_route_with_cjk_patch": {
        "status": "VERIFIED",
        "note": "仅在安装中文兼容补丁后成立：上游 text_processing 会把中文事实清成空串，"
                "打补丁后真实语料 graph_calls=1、executed_route=GRAPH（未打补丁时恒为 0）",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-CJK-COMPAT-20261031.md",
    },
    "scope_incremental_rebuild": {
        "status": "VERIFIED",
        "note": "按可见范围增量重建：复用 rebuild_delta，每个范围有自己的根与指针，"
                "清单是**一张总表**（成功后读旧清单→合并本范围条目→整表写回，"
                "否则重建 A 范围会把 B 范围从清单里抹掉，B 从此 fail-closed 查不到）。"
                "无基线默认拒绝（不静默降级全量），失败不动清单/指针。"
                "真跑：全量 78.7s → 增量 9.9s（7.8×；相对'范围数×全量' 15.1×），"
                "未变更范围 dept-a 的目录/内容 sha/指针 sha 三项全未变",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-SCOPE-DELTA-20261101.md",
    },
    "cross_scope_merged_retrieval": {
        "status": "VERIFIED",
        "note": "跨可见范围合并检索：RRF（名次融合，k=60）而非比分数——不同索引的分数不可比。"
                "去重按文本、平手按 sha256 排序（结果可复现）。范围查不到跳过并记录，"
                "全查不到 fail-closed（不回退全量）。真跑 dept-a/dept-b：单范围用户看不到"
                "只属于 dept-b 的文档，双范围用户能取到。副作用：RRF 奖励多路共识，"
                "只在单范围出现的相关文档可能排在多范围重复出现的文档之后（未做语义重排）",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-MERGED-SCOPE-20261101.md",
    },
    "query_seed_recognition": {
        "status": "VERIFIED",
        "note": "查询侧种子识别：精确子串 → 去机构后缀 → 中间省略简称（最短 4 字），"
                "歧义按解析出的**实体 id** 判（同一实体的 ent:名 与原名不算歧义）。"
                "真实索引 50 个名字：3 条简称问句 seeds 0→1；概念式问句仍 0（抽取缺口，非匹配问题）。"
                "配套：pipeline 调引擎前把规范名补进查询——简称问句从\"计划 GRAPH/执行稠密\""
                "变成真正执行 GRAPH，答 3000 万元 + 1 条引用",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-SEED-MATCH-20261101.md",
    },
    "platform_answer_assembly": {
        "status": "VERIFIED",
        "note": "回答组装 + 引用核验（quote 必须是原文子串，空白归一；只在 citable=True 的材料里找）。"
                "回答模型默认 DeepSeek-V4.1-Flash（deepseek-flash）：18 次真实采样 18 通过；"
                "本地 qwen2.5-7b 同套问句 7/12，短板集中在\"标题句+数据行\"联合",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-ANSWER-ASSEMBLY-20261031.md",
    },
    "platform_retrieval_orchestration": {
        "status": "VERIFIED",
        "note": "路线先判（GRAPH/DENSE_FALLBACK + 原因）、require_graph 时回退不算通过、"
                "引用对回断言并校验可见性；用假 retriever 验编排，真实引擎接线仍缺",
        "evidence": "tests/test_graph_pipeline.py",
    },
    "engine_predicate_normalization": {
        "status": "VERIFIED",
        "note": "normalize.build_store 把引擎 openie 三元组归一进断言层：谓词只查**显式字典**"
                "（查不到原样保留，不猜不模糊匹配）、数值解析（万元等）、来源绑定（对不上来源"
                "丢弃并计数）。真跑 dual-full：facts_in=50 → assertions=26 / entities=26 / "
                "orphans=0；未映射谓词 8 个如实列出（五级分类/信用评级/到期日/已用额度(万元) 等）；"
                "把来源查找换成空列表 → dropped_no_source=50（fail-closed，不挂空来源）",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-WAVE3-CLOSEOUT-20261101.md",
    },
    "engine_version_filtering": {
        "status": "NOT_VERIFIED",
        "note": "检索后置过滤已接进 pipeline（可选参数 as_of/filter_scopes，默认关闭不改变原行为）："
                "按断言 effective_from/to 判窗口，部分来源过期不误杀整块，"
                "无日期事实计入 unknown_window 而非直接过期；丢了多少回传 version_filter.stats。"
                "16 项测试（11 过滤 + 5 接线）。仍是**平台侧过滤**，引擎自身没变——所以不写 VERIFIED",
        "evidence": "tests/test_retrieval_filter.py",
    },
    "engine_visibility_isolation": {
        "status": "VERIFIED",
        "note": "构建期隔离：partition.build_plan 只把可见文档喂给该范围的索引（public 全局可见），"
                "scopes.json 路由查不到即 fail-closed（绝不回退全量）；worker --scope 按范围建库。"
                "真跑 10 块语料：dept-a 5 文档/9 块、dept-b 6 文档/10 块，"
                "只对 dept-b 可见的文本在 dept-a 索引里检索不到（contains_target=false），dept-b 能检索到。"
                "代价：索引数×磁盘/时间、共享内容重复抽取；跨范围合并检索未做",
        "evidence": "docs/design/unified-documents-v2/EVIDENCE-SCOPE-PARTITION-20261101.md",
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
