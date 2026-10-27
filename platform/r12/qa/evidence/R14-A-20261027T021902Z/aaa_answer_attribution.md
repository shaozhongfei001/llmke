# AAA 题归因：检索正确、答案数值错误属生成侧（不是检索/图缺陷）

采集：2026-10-27T11:51:23+08:00；19995 单实例 641826

## 检索结果（enabled_graph=true, enabled_rerank=true, top_k=10）
```
documents = 1
[0] search_type=[milvus, es, es, graph]  file=R12FIX-product-loan.docx  len=459  含"30个基点"=True
    …加点幅度根据客户信用评级确定：AAA级加30个基点，AA级加60个基点，A级加100个基点。…
```

## 判读
- **检索侧 PASS**：命中文档正文就写着 AAA=30bp / AA=60bp / A=100bp，ramp 与 ground truth 一致；
- 因此"AAA 题答 100bp / 60bp"是**生成侧（模型取值/prompt）缺陷**，不是检索或图召回缺陷；
- 唯一可归于检索的质量问题：`enabled_rerank=true` + score_threshold 把候选从 2 条收敛到 **1 条**（top_k=10 却只回 1 条），上下文过窄会放大模型取值错误，建议 C 复核阈值是否过激（这是"质量风险"，不是"链路缺陷"）。

## 建议的断言分层（给 F）
1. 检索层：AAA 题 `documents_list` 中**必须存在**含 "AAA级加30个基点" 的块 → 现在是 PASS；
2. 生成层：答案数值必须与上下文一致（faithfulness）→ 现在是 FAIL，属模型/prompt；
3. 两条分开记，避免"200 + refs 非空"掩盖数值错误，也避免把生成错误归到检索/图上。
