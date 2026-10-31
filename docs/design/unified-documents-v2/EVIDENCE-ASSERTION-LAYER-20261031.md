# 标准断言层：任务书九条业务场景的语义落地（2026-10-31）

模块 `services/rag-alg/index_data_service/graph_engine_adapter/assertions.py`
测试 `tests/test_graph_assertions.py`（11 项）

## 为什么另起一层

设计 §6.3 写明：HippoRAG 的检索图是**算法结构**，它的无向投影与相似边不能当业务关系。
方向、单位、生效期、可见范围、原文支持必须留在平台侧的标准断言里。引擎只负责召回。

所以这里存的是"平台认定的事实"，与引擎图**互不冒充**：断言层能回答业务语义问题，
引擎侧接线（把抽取结果归一进这一层、按生效期与可见集合约束检索）仍未做。

## 九条语义与对应测试

| 场景 | 语义落点 | 测试 |
|---|---|---|
| 同谓词双向不误合并 | 默认 `forward`；只有 `symmetric` 才双向成立 | `test_bidirectional_predicate_is_not_merged_unless_symmetric` |
| 加/减/零调整、总额与分项 | `op=set/add/subtract` 合成总额，零调整不改变结果 | `test_ledger_handles_add_subtract_and_zero_adjustment` |
| 多文件别名与同名异体 | 别名指向 canonical id；同名返回**全部** id，解析不唯一时返回 `None` | `test_alias_resolves_but_homonym_does_not_merge` |
| 同事实多来源删一保留 | 按内容去重合并 SourceRef；删来源只在"全没了"时才弃断言 | `test_multi_source_fact_delete_one_keeps_the_rest` |
| 合法孤点 | 无关系的实体可登记；有实体无断言 → 稠密回退 | `test_orphan_entity_is_legal_but_yields_dense_fallback` |
| 新旧政策有效版本 | `effective_from/to` 的 as-of 查询 | `test_version_window_selects_old_and_new_policy` |
| 不可见文件变化不污染可见构建 | 断言带 visibility scope，查询过滤；删不可见来源不影响可见总额 | `test_invisible_change_does_not_pollute_visible_result` |
| 图禁用/无种子路线准确 | `decide_route` 返回原因：`GRAPH_DISABLED` / `NO_SEED_ENTITY` / `SEEDS_UNKNOWN` / `SEEDS_WITHOUT_ASSERTIONS` | `test_route_decision_explains_itself` |
| 引用失效识别 | `validate_citations` 比对已知来源，列出失效引用 | `test_citation_validation_reports_invalid` |

两条硬约束放在代码里，不靠提醒：
- 数值断言没有单位或没有来源 → 直接抛错（单位不一致时 `ledger` 拒绝相加）；
- 同名异体 `resolve()` 返回 `None`，逼调用方显式选 id，杜绝"名字撞了就合并"。

## Q 的变化

`scripts/v2_q_acceptance.py` 从 **15 PASS / 8 NOT_IMPLEMENTED** 变成
**24 PASS / 0 FAIL / 2 NOT_IMPLEMENTED**。

剩下的 2 项是真没做的，不是被藏起来：

1. `biz:global 报告/引用失效识别（社区/global 真实产物消费）`——引用校验有了，但社区/global
   处理器还没消费真实产物，不得用普通 RAG 顶替；
2. `biz:端到端业务问答（真实文档→引擎→回答）`——断言层语义已验，引擎接线与回答组装没做。

**每条语义 PASS 都带 `boundary: 语义层（构造数据）；端到端未做`**，`tests/test_q_acceptance.py`
强制这个字段存在——没有它，PASS 会被读成"产品能力已通"。

## 能力声明同步

`describe()` 拆成两组，避免拿断言层冒充引擎能力：

- `platform_assertion_layer` = VERIFIED（证据：`tests/test_graph_assertions.py`）；
- `engine_predicate_normalization` / `engine_version_filtering` / `engine_visibility_isolation`
  仍为 NOT_IMPLEMENTED（引擎检索尚未按这些约束执行）。

当前计数：VERIFIED 4 / NOT_VERIFIED 1 / NOT_IMPLEMENTED 7。
