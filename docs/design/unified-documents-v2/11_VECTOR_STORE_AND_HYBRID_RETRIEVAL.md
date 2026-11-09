# 统一向量库与混合检索收敛：设计与派发任务

版本：HybridRetrieval 1.0（并入统一设计 V2.0）
日期：2026-11-05。状态：设计与契约已编制；实现未执行。

## 0. 与既有设计的关系（先读）

本文档是 `05_ES_AND_GRAPH_INPUT_DECISION.md` 与 `06_STANDARD_INPUT_AND_GRAPH_ENGINE.md` 的**检索侧落地方案**，不另起炉灶。继承并引用以下已锁定契约：

- `DP-17`：graph reads immutable parse artifacts without ES or RAG build dependency
- `DP-20`：ES removal preserves lexical/exact/hybrid retrieval through a verified replacement profile
- `DP-22`：engine-neutral input binds canonical MD/IR/assets；**no native engine IDs in source identity**
- `DP-23`：engine swaps preserve public API/source refs；engine indexes rebuildable from standard bundles
- `DP-24`：native content deduplication retains all distinct platform source identities in a multimap
- `DP-25`：engine capability does not imply community/global availability；dense fallback is explicit

**术语修正**：本设计不用「统一切分器」这个说法。正确表述是：

1. **统一标准输入** = doc2md 的 `ParseArtifact`（parsed_text.md / parsed_metadata.json / parse_manifest.json / document_ir.json / assets）。
2. **统一来源身份** = 平台 `pk`（整数 chunk 主键）+ `file_id` + `locator`。**禁止引擎原生 ID（`chunk-<md5>`）作为公共来源身份**（对齐 DP-22）。
3. **各自派生输入单元**：RAG 用 chunk（`rag_projection`，`chunk_chars=800`）；Graph 用完整 MD/IR 的抽取窗口（`GraphExtractionPlan`）。二者粒度不同，但**来源都回指同一个 pk**。

## 1. 现状差距（实测，2026-11-05）

| 维度 | 现状 | 目标 |
|---|---|---|
| 向量存储 | ES 无 `dense_vector`（纯 BM25）；Milvus 无 kb_9/kb_1004 collection；HippoRAG 用私有 parquet 快照 | 统一到 Milvus `kb_<name>` |
| 主键 | ES 用整数 `pk`；HippoRAG 用 `chunk-<md5>` 字符串，对不上 | 全局唯一整数 `pk` |
| chunk 粒度 | RAG 800 字符；HippoRAG 一句话级 | RAG chunk 与 Graph 抽取窗口各自独立，但来源同 pk |
| 召回 | dense 空转 + BM25 + graph 串行 append（score=None） | 三路并行、按 pk RRF |
| 去重 | 按 `page_content` 精确字符串 | 按 `pk` |
| rerank 阈值 | 写死 `0.001` | 相对阈值（top 候选 ×0.3） |

## 2. 目标架构

```
doc2md ParseArtifact（统一标准输入）
   │
   ├── rag_projection ──► RAG chunk（统一 pk）
   │        │
   │        ├──► ES（BM25 / 过滤 / FAQ / 表格）
   │        └──► Milvus（统一向量，bge-m3，同 pk）
   │
   └── GraphExtractionPlan ──► 18094 图引擎（私有索引，来源回指 pk）
            │
            ▼
   三路并行召回（dense + lexical + graph）
            │
            ▼
   RRF 按 pk 融合（k=60）──► rerank 精排 ──► 输出
```

**选型（已定，勿再讨论）**：向量库 = **Milvus**（信创 + 主流）；**ES 保留**（BM25 + 元数据过滤 + FAQ + 表格，与 dense 互补）；embedding = **bge-m3（1024 维）**。

## 3. 详细设计

### 3.1 统一来源身份（pk）

- 唯一 chunk 主键生成：`_chunk_pk(index_name, file_id, seq, text)`，seed = `chunk|{index_lower}|{file_id}|{seq}|{sha1(text)}`，取 `sha1(seed)` 前 15 位 hex 转 int64。
- ES `_id` = pk；Milvus 主键 = pk；图检索回指 `source.pk` = pk。
- 废除 `chunk-<md5>` 作为公共身份（仅引擎内部兼容字段保留，不得进入 `source`/引用）。

### 3.2 统一 embedding

- 模型 `text-embedding-bge-m3`（1024 维）。
- RAG chunk 的向量**只算一次**，写 Milvus。Graph 抽取不预先向量化正文（对齐 `05` §3.6）；图引擎内部自有 embedding 不承担平台 dense 检索职责。

### 3.3 Milvus collection 设计

```
collection: kb_<name>
字段:
  pk          int64   primary key（= ES _id）
  embedding   float_vector[1024]  bge-m3
  file_id     int64   （索引，元数据过滤）
  chunk_type  varchar （text / table）
  version     varchar （可选，版本过滤）
索引: HNSW（metric 与 bge-m3 归一化方式一致）
```

### 3.4 三路召回与融合

- 并行：`retrieval_milvus`（dense）+ `retrieval_elastic`（BM25）+ `retrieval_graph`（图，返回 chunk 而非 fact）。
- 融合：RRF 按 `pk` 去重（`k=60`），替换当前「按 page_content 字符串去重」。
- rerank 只做精排：top_n 之前取 top_n×3 候选；阈值改相对（top 候选最高分 ×0.3）。

## 4. 任务分解（严格按序，每阶段独立可回滚）

- **阶段 0 基线冻结**：记录 kb_9/kb_1004 各 5 条典型 query 的召回快照；确认端口健康。
- **阶段 1 来源身份对齐**：改 `engine_hipporag.py`/`api.py`，图检索 `source.pk` 回指统一 pk（废除 chunk-<md5> 作为公共身份）。验收：`/v2/graph/query` 的 `sources[].pk` 与 ES `_id` 一致。
- **阶段 2 embedding 回灌 Milvus**：`consume_for_kb`/建图流程把 RAG chunk 的 bge-m3 向量写进 `kb_<name>`。验收：kb_9/kb_1004 出现 collection，doc 数与 ES 一致、pk 一一对应。
- **阶段 3 检索融合改造**：`multiple_retrieval.py` 三路并行；`reranker_service.py` RRF 按 pk；阈值改相对。验收：`search_type` 覆盖 es/milvus/graph，同 pk 不重复。
- **阶段 4 下线 V1 冗余**：global 社区摘要完全切到 18094 `community.json`（不再走 19529→Nebula Louvain）；下线 Nebula×3、19529、19532、Milvus 旧集合、`community_summary_<kb>` 生成链路。验收：停服后主链路与 global 仍正常。
- **阶段 5 全量重建 + E2E 回归**：kb_9/kb_1004 重建投影+回灌+建图；跑基线 query 对比，无回退。

## 5. 验收标准（硬性）

1. ES、Milvus、18094 三者 chunk 数一致，按 pk 完全对齐。
2. `retrieval_milvus` 对 kb_9/kb_1004 返回非空。
3. 混合召回 `search_type` 同时出现 `es` + `milvus` + `graph`，同 pk 不重复。
4. 精确关键词 query（`AAA档`、`5000万`、`T-CORE-001`）召回/答案不低于基线。
5. global 模式切到 18094 后仍可回答，无 Nebula/19529 依赖。

## 6. 契约锁定

本设计的硬性约束以 `contracts/rules/llmke-hybrid-retrieval.yaml`（id `llmke-hybrid-retrieval-invariants-v1`）为准，编号 HR-01 起，已在 `contracts/registry.yaml` 登记。HR 不变量是 DP 系列在「向量库统一 + 混合检索融合」上的补充，不与 DP 冲突；冲突时以 DP 为准（DP 是统一文档 V2 的总契约）。
