# 派工单：统一向量库与混合检索收敛

- loop_id：HYBRID-RETRIEVAL-1
- revision：HybridRetrieval 1.0（并入统一设计 V2.0）
- baton holder：TL 指派（未定则 PENDING）
- 已批准目标：把「三套割裂存储、chunk 主键不对齐」收敛为「统一向量库 + 统一来源身份(pk) + dense/lexical/graph 三路按 pk 融合」
- 不做范围：不重跑 doc2md 解析；不替换 bge-m3；不重新选型；不新造第二套切分器/主键

## 契约与设计（权威，先读）

| 文件 | 用途 |
|---|---|
| `contracts/rules/llmke-hybrid-retrieval.yaml` | 契约 HR-01~HR-10（权威约束） |
| `docs/design/unified-documents-v2/11_VECTOR_STORE_AND_HYBRID_RETRIEVAL.md` | 设计 + 任务书 |
| `docs/design/unified-documents-v2/06_STANDARD_INPUT_AND_GRAPH_ENGINE.md` | 统一文档 V2 总设计（术语对齐） |
| `contracts/rules/llmke-document-pipeline-v2.yaml` | DP-01~DP-26（HR 冲突时以 DP 为准） |

## 现状基线（实测 2026-11-05）

- ES `19200`：`kb_9`(4564) / `kb_1004`(4520) / `table_chunks_kb_9` / `community_summary_kb_9`。纯 BM25，无 dense_vector。
- Milvus `19530`：只有旧测试集合，kb_9/kb_1004 无 collection。
- HippoRAG `18094`：快照 parquet，主键 `chunk-<md5>` 字符串，与 ES 整数 pk 对不上。
- 召回：dense 空转 + BM25 + graph 串行 append；去重按 page_content 字符串；`score_threshold=0.001` 写死。

## 允许改动路径

```
services/rag-alg/index_data_service/rag_projection/projection.py
services/rag-alg/index_data_service/ingest_pipeline/kb_pipeline.py
services/rag-alg/alg_retrieval_service/app/multiple_retrieval.py
services/rag-alg/alg_retrieval_service/app/retrieval_service.py
services/rag-alg/alg_retrieval_service/app/reranker_service.py
services/rag-alg/alg_retrieval_service/app/retrieval_fun_tool.py
services/rag-alg/index_data_service/graph_engine_adapter/api.py
services/rag-alg/index_data_service/graph_engine_adapter/engine_hipporag.py
```

禁止写入/激活边界：不直接改 doc2md 源码；不删 Nebula/19529 前必须先完成 global 切换（阶段 4 前置）。

## 任务分解（严格按序，每阶段独立可回滚）

- **阶段 0 基线冻结**：记录 kb_9/kb_1004 各 5 条典型 query（含 `AAA档`/`5000万`/`T-CORE-001`）召回快照。
- **阶段 1 来源身份对齐**：图检索 `sources[].pk` 回指统一整数 pk。验收：图 pk 与 ES `_id` 一致。
- **阶段 2 embedding 回灌 Milvus**：RAG chunk 的 bge-m3 向量写 `kb_<name>` collection。验收：doc 数与 ES 一致、pk 一一对应。
- **阶段 3 检索融合**：三路并行；RRF 按 pk（k=60）；阈值改相对。验收：`search_type` 覆盖 es/milvus/graph，同 pk 不重复。
- **阶段 4 下线 V1 冗余**：global 切 18094 `community.json`；下线 Nebula×3、19529、19532、Milvus 旧集合、`community_summary_<kb>` 生成链路。
- **阶段 5 全量重建 + E2E 回归**：kb_9/kb_1004 重建投影+回灌+建图；跑基线 query 对比无回退。

## 真实验收命令（required_checks）

1. ES、Milvus、18094 三者 chunk 数一致、按 pk 对齐。
2. `retrieval_milvus` 对 kb_9/kb_1004 非空。
3. 混合召回 `search_type` 同时含 es+milvus+graph、同 pk 不重复。
4. 精确关键词 query 召回/答案不低于基线。
5. global 无 Nebula/19529 依赖仍可回答。

## 失败预算、STOP 条件、回退

- 每阶段独立提交；任一阶段验收不过，回滚该阶段即可，不影响已上线链路。
- STOP 条件：阶段 2 回灌失败不得阻塞（BM25 + graph 仍可兜底）；阶段 4 下线前必须确认 global 已切 18094。
- 回退：停 Nebula/19529 前保留原 19529 进程与 Nebula 数据可重启。

## 独立 QA principal / 外部签署

- 独立 QA principal：`qa-external-03`（角色 `qa-owner`，受保护 runner trust root 之外的外部执行主体；沿用 L0 r11/r16 的 `qa-external-02` 编号序列，取下一序号）。
- 外部签署方式：受保护环境独立复跑 `required_checks` 后，以 trust root 签名 QA_ATTESTATION 载荷（`key_id=qa-ed25519-indep`，principal=`qa-external-03`）。
- 独立性约束：`qa-external-03` ∉ 本切片 `implementation_principals`（实现主体为 `algorithm-owner` / `python-engineer`），满足 `qa_principal_must_not_be_implementation_principal: true`。
- 如实标注（非阻塞）：真实 principal/公钥配置仍为 PENDING（`ROLE-MATRIX.independence.key_provisioning`），签署前须先完成公钥配置；TL 不代签、不伪造签署身份。
