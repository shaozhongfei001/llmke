# HybridRetrieval 阶段 2 验收记录（Milvus 回灌）

日期：2026-11-05。loop：HYBRID-RETRIEVAL-1。执行身份：tech-lead（TL），已获「激活后端索引」授权。

## 结论

| 验收项（HR-04 / 派工单） | 结果 |
|---|---|
| kb_9/kb_1004 出现 Milvus collection | ✅ `_kb_9`=4564、`_kb_1004`=4520 |
| doc 数与 ES 一致 | ✅ ES=4564/4520 == Milvus=4564/4520 |
| pk 一一对齐 | ✅ 交集=全集，仅ES=0、仅Milvus=0 |
| `retrieval_milvus` 返回非空 | ✅ kb_9 召回「二、授信额度」、kb_1004 召回「VEGETABLES TO PLANT」 |

## 回灌方案（scripts/v2_hybrid_milvus_backfill.py）

1. 从 ES（19200）scroll 读 kb_9/kb_1004 全部 chunk，`metadata.pk`（整数）作为 Milvus 主键；
2. 调向量服务（19526）`/insert_vector_documents_custom`，`model_name=bge-m3`（1024 维，IP metric）；
3. 向量服务自动创建 collection（逻辑名 kb_9 → 实际 `_kb_9`，`generate_collection_name_uuid` 加 `_` 前缀）、
   bge-m3 embedding、写入（HR-03：向量只算一次）。

## 关键发现与修复（3 个坑）

1. **Milvus 实例定位**：向量服务（19526）连的是 `r12-milvus` 宿主机 **19630** 的 **`rag_knowledge_base` 库**，
   不是 19530（那是 `yuxi-milvus-1` 的 default 库）。验证必须查 19630 + `rag_knowledge_base`。

2. **duplicate_flag 必须 false**：`add_doc_custom` 的 `duplicate_flag=true` 会「按 source 整文件替换」。
   kb_1004 整本书 4520 chunk 共用一个 source，跨文件分批回灌时每批都删掉上一批同 source 数据 →
   最终 0 条。首次回灌用 `duplicate_flag=false`。

3. **batch 大小与 embed 失败**：batch_size=200 时，每个库最后一批（164/120 条）embed 请求失败
   （重试 3 次耗尽）。降为 40 条/批后 3 批全部成功。根因是 embedding 服务「batch too large (>64)」
   限制 + 向量服务长时间运行的并发/超时压力。脚本保留重试机制 + 每批后 flush。

4. **flush 必须显式**：`batch_insert_async` 用 `AsyncMilvusClient.insert()` 后只 `load_collection`，
   **不 flush**；数据停在 growing segment，REST query 查不到。脚本每批后调 Milvus `/collections/flush`。

## 验收证据

- doc 数：`_kb_9 num_entities=4564`、`_kb_1004 num_entities=4520`（pymilvus 直连 19630/rag_knowledge_base）。
- pk 对齐：ES scroll pk 集合 vs Milvus query pk 集合，交集=全集，差异=0。
- dense 检索：19995 `search_policy=3`（纯 milvus）对 kb_9/kb_1004 均返回非空 `search_type=['milvus']`。

## 遗留（不阻塞阶段 2 结论）

- 回灌脚本默认 batch_size 仍为 200，未来重跑建议改 100 或分文件回灌，降低 embed 失败概率。
- 阶段 2 只回灌 kb_9/kb_1004 正文+表格 chunk；faq_/table_chunks_/community_summary_ 等派生集合不在此范围。
