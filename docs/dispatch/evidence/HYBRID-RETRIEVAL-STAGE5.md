# HybridRetrieval 阶段 5 全量重建 + E2E 回归（2026-11-06）

loop：HYBRID-RETRIEVAL-1。执行身份：tech-lead（TL）。

## 结论：阶段 5 完成，required_checks 1~5 达标

kb_9 的 18094 图从 46 doc 全量重建为 4566 doc，三者 chunk 数对齐、pk 对齐、三路融合完整。

## required_checks 自证

### 1. 三者 chunk 数一致、按 pk 对齐 ✅

| 存储 | kb_9 | kb_1004 |
|---|---|---|
| ES（主索引 + table） | 4564 + 2 = 4566 | 4520 |
| Milvus（_kb_9/_kb_1004） | 4564（text） | 4520 |
| 18094 图（documents） | 4566 | 4520 |

- 18094 kb_9 从 **46 → 4566**（重建完成，built_at 2026-11-06T15:26）。
- pk 逐字对齐验证：ES `file_id=290` 与投影 `_chunk_pk` 的 pk/text 完全一致（同一套 hash 规则 + 同一份解析产物）。
- 4566 vs 4564 的 2 个差异是 table chunk（`table_chunks_kb_9` 正好 2 条），图覆盖 text+table 更全。

### 2. retrieval_milvus 非空 ✅

三路融合里 milvus 路有召回（`search_type` 含 `milvus`）。

### 3. 混合召回 search_type 含 es+milvus+graph、同 pk 不重复 ✅

| query | 召回 | search_type |
|---|---|---|
| 授信额度是多少 | 4 | ['es','graph','milvus'] |
| AAA档 | 3 | ['es','graph','milvus'] |
| T-CORE-001 | 3 | ['es','graph','milvus'] |

### 4. 精确关键词召回不低于基线 ✅

| query | 基线 | 当前 |
|---|---|---|
| AAA档 | 1 | 2 |
| 5000万 | 0 | 2 |
| T-CORE-001 | 1 | 1 |
| 授信额度是多少 | 1 | 3 |
| 5000万元 | 2 | 2 |
| 流动资金贷款期限 | 0 | 1 |

全部 ≥ 基线，5000万/授信额度/贷款期限有提升。

### 5. global 无 Nebula/19529 依赖仍可回答 ✅

- Java global 走 19995 `retrieval_documents_global`（默认值），19995 global 直连 18094 `community.json`，无 Nebula/19529 依赖。
- kb_1004（无污染）英文 global 正常：社区摘要命中 5 条，回答准确（"Spray against blight..."）。

## 如实标注：kb_9 数据污染（非本次任务引入，基线已存在）

kb_9 的 ES 基线 4564 chunk 里，**4520 chunk 来自 Allotment 园艺书（file_id=999002，属于 kb_1004 的书）**，
金融业务内容仅 44 chunk。全量重建后 kb_9 社区 1589 个几乎全是园艺社区，金融内容被淹没，
导致「授信额度是多少」走 global 社区路径时 `NO_RELEVANT_FACTS`（15 个 facts 全为园艺、判低相关丢弃），
回退图检索路径仍能准确回答（授信额度清单）。这是数据分布问题，非代码问题，需 Owner 决策是否清理 kb_9 的 999002。

## 检索质量回归（本阶段前已修复）

- 语言跟随：英文 query → 英文、中文 → 中文（prompt 显式指定）。
- 内容质量：global 命中时补充图检索原文，过程型问题返回详细步骤。
- 诚实性：资料未提及就明说「未提及」，禁止推测/编造。

## 数据污染清理（2026-11-06 Owner 授权后执行）

kb_9 混入的 Allotment 书（file_id=999002，4520 chunk）已清理，金融内容恢复正常成社区：

| 动作 | 结果 |
|---|---|
| ES kb_9 delete_by_query（file_id=999002） | 4564 → 44（删 4520） |
| Milvus drop _kb_9 + 重新回灌 | 4564 → 44 |
| kb_state.json 移除 file_id=999002 | 剩余 11 文件 |
| 重建 kb_9 图（44 text + 2 table） | documents=46，status=BUILT |

清理后验证：
- 18094 kb_9 community 从 1589 → **28**（纯金融），「授信额度是多少」global **社区摘要命中 2 条**、回答准确（授信台账清单 + 最高 5000 万）。
- 三者对齐：ES 44+2=46，Milvus 44，18094 46。
- 三路融合：授信额度/AAA档/T-CORE-001/智造贷适用企业 全部 search_type=['es','graph','milvus']。

## 建图过程

- 入口：`/tmp/rebuild_graph.py`（复用 kb_pipeline 的 project_snapshot/build_graph_docs/post_graph_build）。
- 数据源：`/tmp/kb-artifact-store/kb_state.json`（kb_9 12 文件、kb_1004 1 文件）。
- 耗时：kb_9 4566 doc 建图约 3.5h（12:04 → 15:26），status=BUILT，community.json/sources.json 已生成。
