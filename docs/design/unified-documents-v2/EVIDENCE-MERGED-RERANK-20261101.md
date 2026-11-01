# 合并结果重排（2026-11-01）

`merged.py` 的 RRF 融合有一个已实测的副作用：**一条只在单个范围出现的相关文档，会排在
多范围重复出现的不相关文档之后**——RRF 奖励"多路共识"，本身不判断相关性
（见 `EVIDENCE-MERGED-SCOPE-20261101.md`：五级分类口径排在授信台账之后）。

这一层在 `merged.py` **之上**加一次可注入的相关性重排，不改 RRF 本身。

## 做法

`graph_engine_adapter/merged_rerank.py`

- `rerank(query, hits, *, scorer, top_k=5, max_candidates=20, timeout_s=None)`：
  只对前 `max_candidates` 条打分，按分数稳定排序后截断到 `top_k`；
- `scorer(query, [{"id","text"}, ...]) -> {id: score}` 可注入：真实用 LLM，测试用桩；
- 候选 `id` 是**下标字符串**（`"0"`, `"1"`, …），与提示词要求模型输出的
  `{"scores": {"0": 0.9}}` 对齐——正文超长/重复/被截断时用正文当 key 会对不上；
- `llm_scorer(llm_call, *, model=None)`：把 `llm_config.make_llm_call` 的返回值包成 scorer，
  要求模型**只输出 JSON**；模型与温度不设默认值，`model=None` 时连该参数都不传。

三条判断写进了行为里：

1. **超出 `max_candidates` 的候选不打分**，直接丢弃。对没打分的候选排序等于编造分数，
   比不重排更坏（结果更"新鲜"，排序依据却无从追责）。
2. **任何失败都回退到 RRF 顺序且结果非空**，`reranked=False`，`reason` 取
   `SCORER_ERROR` / `TIMEOUT` / `EMPTY_SCORES`，`detail` 记原始错误。
   把"重排失败"变成"没结果"是最坏的降级：用户看到"查不到"，而真相是"打分器坏了"。
3. **同分保持原 RRF 名次**（稳定排序），两次调用结果一致，否则"谁排第一"每次不同。

未处理的情形一律**保留原样**：空 `hits`（`EMPTY_HITS`）、无 `scorer`（`NO_SCORER`）、
`top_k<=0`（`TOP_K_NON_POSITIVE`）、`max_candidates<=0`（`MAX_CANDIDATES_NON_POSITIVE`）。
模型漏给的候选**不丢**：排在已打分候选之后、保持原相对顺序，`unscored` 计数。
返回里出现**候选集合之外的下标**视为打分器不可信 → 回退（不猜、不忽略）。

## 真实运行（`.artifacts/scoped`，dept-a + dept-b，复用已有两份索引，未重建）

问题：「五级分类口径中的关注是什么意思」，`retrieve_merged(..., top_k=20)` 得 10 条候选。

RRF 顺序（前 4 与全部下标）：

```
rrf [('## 授信台账  | 客户名称 ', 0.032522), ('## 授信台账  | 客户名称 ', 0.032002),
     ('## 授信管理办法  第一章 总', 0.031498), ('## 授信管理办法  第一章 总', 0.03101)]

0 0.032522 [0, 1] '## 授信台账  | 客户名称 | ...'
1 0.032002 [0, 1] '## 授信台账  | 客户名称 | ...'
2 0.031498 [0, 1] '## 授信管理办法  第一章 总则。...'
3 0.031010 [0, 1] '## 授信管理办法  第一章 总则。...'
4 0.030536 [0, 1] '台账说明：本表为季度末时点数，...'
5 0.030077 [0, 1] '台账说明：额度单位为万元，...'
6 0.029631 [0, 1] '附则：本办法由总行授信管理部负责解释，...'
7 0.029199 [0, 1] '## 担保方式说明  保证担保：...'
8 0.028778 [0, 1] '附则：本办法由总行授信管理部负责解释，...'
9 0.016393 [1]    '## 五级分类口径  正常：借款人能够履行合同，...'
```

对同一批候选跑**规则 scorer**（文本含「五级分类」+0.6、「关注」+0.3、含「授信台账/授信管理办法」-0.2）：

```
reranked True RERANKED candidates 10 dropped 5 unscored 0
 RR 0 0.9 0.016393 '## 五级分类口径  正常：借款人能够履行合同，...'
 RR 1 0.7 0.032522 '## 授信台账  | 客户名称 | ...'
 RR 2 0.7 0.032002 '## 授信台账  | 客户名称 | ...'
 RR 3 0.0 0.031498 '## 授信管理办法  第一章 总则。...'
 RR 4 0.0 0.031010 '## 授信管理办法  第一章 总则。...'
```

对同一批候选跑**真实 LLM**（本地端点 `127.0.0.1:18092`，`llm_config.make_llm_call()`，
`llm_scorer(llm)`，`timeout_s=90`）：

```
LLMScorer reranked= True reason= RERANKED detail= 参与打分 10 条，未返回分数 0 条
scores= {'0': 0.9, '1': 0.1, '2': 0.0, '3': 0.0, '4': 0.0, '5': 0.0, '6': 0.0, '7': 0.0, '8': 0.0, '9': 1.0}
 LLM 0 1.0 0.016393 '## 五级分类口径  正常：借款人能够履行合同，...'
 LLM 1 0.9 0.032522 '## 授信台账  | 客户名称 | ...'
 LLM 2 0.1 0.032002 '## 授信台账  | 客户名称 | ...'
 LLM 3 0.0 0.031498 '## 授信管理办法  第一章 总则。...'
 LLM 4 0.0 0.031010 '## 授信管理办法  第一章 总则。...'
```

两轮都把「五级分类口径」从第 10（最后）提到第 1，`rrf_score` 原样保留（0.016393 是全场最低，
说明它只被 dept-b 一路召回）。**RRF 输出未被修改**——重排只读 `hits`，另起一层。

## 回退路径（同一批真实候选）

```
fallback: False SCORER_ERROR RuntimeError: scorer 端点 500 n= 5 dropped= 5
fallback 顺序 == RRF 前5: True
坏输出回退: False SCORER_ERROR n= 5
```

打分器抛异常、`llm_scorer` 解析到非 JSON，两条路径都是：顺序回到 RRF、**结果仍是 5 条非空**。

## 测试

`tests/test_merged_rerank.py`：**18 passed**（`tests/test_merged.py` + 本文件合计 25 passed）。

覆盖：第 3 条被打到第一且 `reranked=True`；scorer 抛异常回退且非空；漏给的 id 不丢（排在后面 +
`unscored` 计数）；空 dict 回退；非 dict / 越界下标 / 非数值分数判 `SCORER_ERROR`；`top_k` 截断与
`dropped`；`max_candidates=20` 时第 21 条不参与打分（断言 scorer 只收到 20 个 id 且 `"20"` 不在
`scores`）；同分稳定且两次调用一致；空 hits / 无 scorer / `top_k=0` 原样返回；`timeout_s` 超时回退
（`TIMEOUT` 且非空）；`llm_scorer` 解析 ```json 围栏、不塞默认 model/temperature、提示词含下标与
"只输出 JSON"；坏输出（非 JSON / 越界 / 非数值 / `scores` 非对象 / 空串）抛 `ScorerError`；
`llm_scorer` 报错经 `rerank` 变成回退而不是空结果。

```
cd /home/szf/data/dev/llmke-v2 && PYTHONPATH=services/rag-alg/index_data_service \
  /home/szf/data/dev/llmke-v2-toolenv/bin/python -m pytest tests/test_merged_rerank.py -q
..................                                                       [100%]
18 passed in 0.12s
```

## 边界（没做的部分）

- **`timeout_s` 约束的是"等待"，不是底层调用本身**：超时后后台线程可能仍在跑，其结果被丢弃。
  真实 LLM 调用应自己带 connect/read 超时（`llm_config` 有 `LLMKE_ANSWER_TIMEOUT`），这里只是
  兜底别让一次查询被打分器拖死。
- 只做相关性重排：**不改 `rrf_score`、不重新融合多路结果、不做范围权重、不合并同一内容来自
  多个范围的 `sources`**（后者是 `merged.py` 的既有边界）。
- `max_candidates` 之后被丢弃的候选**没有"可能本来更相关"的兜底**：这是有意的取舍（不打分不排序），
  代价是召回上界被 `max_candidates` 卡住；要更大召回应调高它，而不是让未打分候选混进结果。
- 未做 scorer 结果的缓存与批量合并（多查询共用一次打分调用）。
- 未改 `merged.py`，未改任何既有测试与配置。
