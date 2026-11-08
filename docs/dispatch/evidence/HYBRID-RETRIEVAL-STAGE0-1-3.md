# HybridRetrieval 阶段 0/1/3 验收记录（TL）

日期：2026-11-05。loop：HYBRID-RETRIEVAL-1。执行身份：tech-lead（TL）。

## 结论速览

| 阶段 | 状态 | 关键证据 |
|---|---|---|
| 0 基线冻结 | ✅ 完成 | `docs/dispatch/evidence/hybrid-baseline-0.json` |
| 1 来源身份对齐(pk) | ✅ 验收通过（运行环境已生效） | 图检索 source.pk 整数化，与 ES `_id` 对齐 |
| 2 Milvus 回灌 | ⛔ 未实现（前置已确认） | Milvus 无 kb_9/kb_1004 collection |
| 3 三路融合 | ⚠️ 代码改造完成（RRF 按 pk + 相对阈值），待部署 | `reranker_service.py` + `tests/test_hybrid_rrf.py` |
| 4 下线 Nebula | ⛔ 未实现（高风险，需先确认 global 切 18094） | — |
| 5 重建 + E2E | ⛔ 未实现（依赖 2/3/4） | — |

## 阶段 0：基线冻结（只读）

- ES doc 数：`kb_9=4564`、`kb_1004=4520`（与派工单基线一致）。
- ES 主键真值：`_id` == `_source.metadata.pk`（整数 pk，二者一致），
  kb_9 例 `318101056057432139`，kb_1004 例 `1015827570681113966`。
- 端口健康：18094(HippoRAG)/19529/19530(Milvus)/19532(shim)/19200(ES)/19669(Nebula) 全在线。
- 召回快照（19995 legacy `/retrieval_documents`）：
  - kb_9 中文：`AAA档`=1、`T-CORE-001`=1、`授信额度是多少`=1、`5000万元`=2；
    `5000万`=0（**tokenization 现象**：数据里是「5000万元」，单查「5000万」命中 0，如实记录）。
  - kb_1004 是英文语料（DK 园艺书 *Allotment month by month*），中文 query 全 0；
    英文 query（`allotment`/`vegetable`/`gardening`/`compost`/`sowing`）各 1 条，检索正常。

## 阶段 1：来源身份对齐（pk）

- 实现已落地于工作树：`projection._chunk_pk`（统一整数 pk）、
  `api.BuildDoc.pk/parse_artifact_id`（图构建写进 sources.json）、
  `multiple_retrieval.retrieval_graph` 直连 18094 + `_pick_pk`（只收整数 pk）。
- 验收实测（运行环境）：`POST 18094 /v2/graph/query` 的 `docs[].sources[].pk` 已是整数 pk
  （如 `606479882502856278`），`idx` 仍为引擎私有 `chunk-<md5>`（符合 HR-02，私有 ID 不出公共身份）。
- 与 ES 对齐：`5000万元` 的 ES 召回顶层 pk 含 `606479882502856278`，与图检索 source.pk 一致 ✅。
- **发现的位置不一致（阶段 3 需注意）**：ES/Milvus 召回结果的 pk 在**顶层 `pk` 字段**
  （`process_return_results` 第 762 行），而图检索的 pk 在 `metadata.pk`（`retrieval_graph`）。
  RRF 融合按 `metadata.pk` 去重时，图路有值、ES 路需确认（ES 的 `_source.metadata.pk` 有值，
  融合阶段 Document.metadata.pk 有值，故按 pk 去重可行）。

## 阶段 3：三路融合（RRF 按 pk + 相对阈值）

改造 `services/rag-alg/alg_retrieval_service/app/reranker_service.py`：

1. `merge_and_get_rrf_score`：去重 key 由 `page_content` 精确字符串改为**平台 pk**，`rrf_k` 默认 5→60（HR-06）；
   pk 缺失时用进程内唯一占位，不把不同来源错误合并。
2. `merge_and_rerank`：rerank 前按 RRF score 粗排取 `top_n×3` 候选；阈值改**相对阈值**
   `max(score_threshold, top 候选最高分 × 0.3)`（HR-07），日志记录 `rerank_filter_threshold` 为实际生效值。

验证（`tests/test_hybrid_rrf.py`，用 r12 venv 内联复跑）：
- 相同 pk 不同正文 → 合并 1 条、search_type 合并 ✅；
- 不同 pk 相同正文 → 保留 2 条 ✅；
- pk 缺失 → 不错误合并 ✅；
- rrf_k=60、rank0 → 1/60 ✅。

## 阶段 2 前置盘点（未实现，如实登记）

- embedding 服务 `bge-m3`（18090）、reranker `bge-reranker-v2-m3`（18091）、LLM（18092）均在线可用。
- Milvus 19530 仅有 `kb_ve38vlwzwf*` 3 个 collection，**无 kb_9/kb_1004**（dense 召回空转）。
- 待做：创建 `kb_9`/`kb_1004` collection（pk int64 主键 + embedding float_vector[1024] + file_id + chunk_type），
  对 9084 个 chunk 计算 bge-m3 向量并写入，断言 doc 数与 ES 一致、pk 一一对应（HR-04）。
- 属**后端索引激活**，涉及生产数据变更，落地前需 Owner/algorithm-owner 授权。

## 阶段 4/5 前置与红线

- 红线：阶段 4 下线 Nebula/19529/19532 前，必须先确认 global 已切 18094 `community.json`
  （`retrieval_global_view.py` 已有 V2 回退，但未做下线切换），否则停 Nebula 会断链。
- 红线：禁止把 18094 parquet 快照当持久化向量库（HR-04）。

## 待办

1. 阶段 2：Milvus collection 创建 + bge-m3 回灌（需授权）。
2. 阶段 3：改造部署到运行环境（reranker_service.py 需重启 19995 生效，属服务变更）。
3. 阶段 4：确认 global 切 18094 → 下线 Nebula×3/19529/19532/旧集合。
4. 阶段 5：kb_9/kb_1004 重建投影 + 回灌 + 建图，跑基线 query 对比无回退。
