# C1 HippoRAG 扩到真实投影载荷（2026-10-31）

## 跑的是什么

`scripts/v2_hipporag_smoke.py --payloads /tmp/ingest-333.json /tmp/ingest-329.json`：
用 `ingest_pipeline` 产出的**真实投影载荷**（docx 333 + xlsx 329，含表格通道块）当语料，
不再用手写 4 句。3 条查询，抓 NaN 与告警。

## 结果

```json
{"status":"OK",
 "mapping":{"units":5,"engine_chunks":5,"shared_chunks":0},
 "expected_engine_chunks":5,"actual_engine_chunks":5,
 "files_in_corpus":2,"hit_count":6,
 "nan_scores":[],
 "warnings":["ResourceWarning: unclosed file openie_results_ner_qwen2.5-7b-instruct.json",
             "RuntimeWarning: invalid value encountered in divide"]}
```

- **跨文档成立**：2 个文件 5 个块，检索结果按 `native_key` 回指到 333 / 329 各自的
  `source`（对象键），引用可拼出 URL；
- **scale 一致**：引擎 chunk 数 == 平台去重正文数（5 == 5），`chunk-<md5>` 规则在真实载荷上仍成立；
- **`nan_scores` 为空**：`invalid value encountered in divide` 的告警**出现了**，但没有把分数变成
  NaN/Inf（脚本对每条结果逐个 `isfinite` 检查）。

## 两个真实问题（没修，先记录）

1. **告警仍在**：`phrase_weights /= number_of_occurs` 在整除时触发 RuntimeWarning。
   现在结果是正常的，但这属于"靠数据躲过去"——一旦某次检索里所有候选的 occurrence 为 0，
   分数就会变 NaN。判定标准已写进脚本：出现非有限分数即 FAIL。
2. **OpenIE 有空抽取**：日志里 `qwen2.5-7b-instruct` 对某个块返回 ```{}```，即该块没有抽出三元组。
   图会因此变稀疏（该块只能靠 dense 召回），但**不报错、不降级提示**。这不是映射层能修的，
   属于 LLM 提示词/模型能力问题，需要在图阶段处理（空抽取要计数并告警）。

## 边界

- 只证明"真实载荷能进 HippoRAG 并检索回来、来源不丢"；**没有**消费社区/global、没有接 Nebula、
  没有做多跳问答质量评测；
- 语料只有 5 个块，远小于真实知识库；NaN 退化路径未被真实命中。
