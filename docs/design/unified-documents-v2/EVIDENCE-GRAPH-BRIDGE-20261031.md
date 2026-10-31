# 引擎接线实测：图路径为什么没执行（2026-10-31）

入口：`scripts/v2_graph_bridge.py`（端到端）与 `scripts/v2_hipporag_graph_probe.py`（诊断）。
语料：真实投影载荷 333 docx + 329 xlsx，5 个块。

## 结论先写

**在本机这套模型上，HippoRAG 的图检索从来没有被执行过。**
`retrieve()` 内部的事实重排（DSPy Filter，走 qwen2.5-7b）返回空 JSON `{}`，
pydantic 校验失败 → `facts_after_rerank=0` → 引擎按设计回退稠密。
所以"检索到了 3 条结果"完全不等于"图跑过"。

## 端到端（`v2_graph_bridge.py`）

```
归一：facts_in=52 → facts_out=52，dropped_no_source=0，
      numeric=0，relational=52，未归一谓词 8 个
      （五级分类 / 信用评级 / 到期日 / 口径 / 已用额度(万元) / 所属产业链 / 授信额度(万元) / 数据源）
断言层：entities=29, aliases=58, assertions=28, sources=3
```

| 查询 | 计划路线 | 引擎实际执行 | 强制图验收 |
|---|---|---|---|
| 产品甲的额度是多少 | DENSE_FALLBACK（无种子实体） | DENSE_FALLBACK | 不通过 |
| 指标口径是什么 | GRAPH（有种子有断言） | **DENSE_FALLBACK**，`graph_calls=0` | 不通过 |
| 表格里有哪些字段 | DENSE_FALLBACK | DENSE_FALLBACK | 不通过 |

第二行是重点：**计划走图、引擎内部回退**。这正是设计 §6.5 说的"返回 200/有答案不能证明图路径
实际执行"。我第一版 `pipeline.retrieve` 只看计划路线，因此把它判成了 `passed=True`——
**这是个假通过，已修**：现在 `require_graph` 只认引擎自报的 `executed_route`，
并新增 `route_matches` 字段暴露计划/执行不一致。

## 诊断（`v2_hipporag_graph_probe.py`）

```json
{"retrieve_path":{"executed_route":"DENSE_FALLBACK","reason":"GRAPH_NOT_CALLED","graph_calls":0},
 "rerank":{"facts_before_rerank":5,"facts_after_rerank":0},
 "direct_graph":{"called":true,"docs":5,"scores_finite":true,
                 "warnings":["RuntimeWarning: invalid value encountered in divide"]}}
```

三件事分开说清楚：

1. **重排是卡点**：候选事实 5 条，重排后 0 条。日志里能看到
   `Error parsing field fact_after_filter: ... input_value={}`——模型返回了 `{}`，
   DSPy 的 pydantic 校验把它丢了，引擎于是走稠密。
2. **引擎图检索本身能跑**：绕过重排、直接用候选事实调 `graph_search_with_fact_entities`，
   返回 5 篇文档、得分有限、顶部是"授信台账"表——PPR 有效。也就是说问题不在图上，在重排。
3. **NaN 的 0 除警告这次真的出现了**（前面 C1 只是构造复现）：
   `phrase_weights /= number_of_occurs` 在真实图调用里触发，本次得分仍有限。

## 由此改变的口径

- `describe().capabilities.retrieve_graph_route` 保持 **NOT_VERIFIED**，note 补上实测原因；
- Q 的"端到端业务问答"仍是 NOT_IMPLEMENTED，但原因从"没接线"更新为
  "接线已通、图路径被重排器阻断"，并写进证据；
- **不允许**因为"检索有结果"就把图验收记录成通过——这条已经用测试和 `route_matches` 钉住。

## 还没做

- 换更大/更听话的模型做重排（当前只有 qwen2.5-7b 本地端点）；
- 给 DSPy Filter 提供 demos 或改提示词（属于引擎侧调参，需单独评估是否会引入别的偏差）；
- 事实三元组质量：表头被抽成 `("", "", "5000")` 这类空主谓，说明抽取提示词对表格不友好。
