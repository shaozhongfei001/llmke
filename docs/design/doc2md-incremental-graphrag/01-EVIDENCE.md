# 01 · 现状证据清单（代码级 / 数据 / 框架 SDK）

> 用途：让独立架构智能体**不依赖本方案叙述**、可逐条复核。所有路径为绝对路径；行号对应 2026-11-07/08 工作区文件。本文件只陈述只读核实到的事实，找不到的一律明说。

---

## 1. 运行时数据快照

采集时间：`2026-11-08 00:14:54`（命令见 §7）。

| 项 | kb_9 | kb_1004 |
|---|---|---|
| ES `<kb>/_count` | 44 | 4520 |
| ES `table_chunks_<kb>/_count` | 2 | 无该索引 |
| Milvus `_<kb>` rows（19630 `rag_knowledge_base`） | 44 | 4520 |
| 18094 `/v2/status` documents | 46 | 4520 |
| 18094 `pointer.built_at` | `2026-11-07T21:31:00+0800` | `2026-11-07T01:11:00+0800` |
| 18094 `pointer.mode` | `None`（现有指针未写 mode 字段） | `None` |

对齐口径：ES 44 + table 2 = 46；Milvus 44（表格不做向量）；图 46。与 `HYBRID-RETRIEVAL-STAGE5.md:13-21` 的口径一致。

端口监听（1=监听，0=未监听）：

```
12340:1   18096:0   18094:1   19531:1   19527:1   19526:1   19995:1   19996:1   18082:1   18083:1
```

**18096 未监听**，与 `platform/r12/conf/rag-index-service/application-r12.yml:103-109` 的「关闭」注释一致。

HippoRAG SDK 版本：`hipporag-2.0.0a4.dist-info/METADATA:3` → `Version: 2.0.0a4`。

---

## 2. 代码级证据：解析派发链路（doc2md 不在主链）

| 事实 | 出处 |
|---|---|
| 任务创建（写 DB，不发 HTTP） | `KnowledgeBaseListAppServiceImpl.java:517-604`，`:587` `setTaskInfo(JSON.toJSONString(taskInfo))`；`:597-598` 原 MQ 派发已注释，改 DB 轮询 |
| 15 秒调度 | `FileParseTaskScheduler.java:27-38`，`@Scheduled(cron="*/15 * * * * ?")` → `execTask()` |
| CAS 抢占后派发 | `FileParseTaskAppServiceImpl.java:144-217`，`:216 filesAppParse.filesParse(task)` |
| 请求体组装 | `FileAppServiceImpl.java:102-226`，`:198 remoteFileUtils.fileParse(JSON.toJSONString(BeanUtil.copyProperties(param, ParseParam.class)))` |
| 最终 HTTP | `RemoteFileUtils.java:43-44,339-341` → `remote.file-parse.url` = `http://127.0.0.1:12340/parse`（`application-r12.yml:83-84`） |
| `ParseParam` 字段 | `rag-common/.../ParseParam.java:17-138`：`knowledge_base_id/name`、`task_id`、`files[].file_id/file_path/...`、`chunk_size`、`chunk_overlap`、`need_chunk`、`index_name`、`model_info`、`embedding_model_info`、`multi_model_info`。**无 `doc2md_dir` / `file_url`** |
| 12340 接收模型 | `alg_doc_parse_service/server/api_param.py:9-50`，同样无 doc2md 字段 |
| `doc2mdDir` 从未赋值 | `FileParseTaskInfo.java:162-169` 有声明；全仓 Java 无 `setDoc2mdDir` / `put("doc2md_dir")` 写进 `task_info`；唯一读取是 `FileAppServiceImpl.java:629` → 恒 `null` |
| `adapter_doc2md` 未接生产 | `alg_doc_parse_service/adapter_doc2md/adapter.py:1-189`；全仓引用只有 `tests/test_doc2md_adapter.py` 与 2 份设计文档；该文件 `:17` 自述「不认识 Nebula/ES/Milvus，也不解析原件」 |
| doc2md 只在旁路 | `FileParseTaskAppServiceImpl.java:357-362` → `FileAppServiceImpl.java:619-662` → `RemoteV2IngestUtils.java:53-103` → `18096 /kb/ingest` → `kb_ingest_service.py:158-181` 才调 `scripts/v2_ingest_doc2md.py` |
| 旁路已关闭 | `application-r12.yml:103-109` `v2-ingest.url: ""`；运行仓 `llmke-r12/.../application-r12.yml:93-101` 干脆没有该段 |

12340 解析与双写的关键事实（`02` 号需求对照用）：

- 一次请求只 `parser.parse()` 一次（`controller.py:837`/`:1005`），内部 `chunk()` 一次（`:619` → `:313-434`）；
- `index_es(document_list=chunks)`（`:877-879` → 19527）与 `index_milvus(document_list=chunks)`（`:894-897` → 19526）**用同一个循环变量 `chunks`**；
- 主键同源：`controller.py:410-416` `create_chunk_pk` = `int(sha1("chunk|<index_lower>|<file_id>|<seq>|sha1(text)")[:15],16)`；ES `es.py:216-218` 用 `metadata.pk` 当 `_id`，Milvus `milvus_kb_service.py:544-545` 用它当主键；
- 无跨库事务：ES 写完才写 Milvus，Milvus 失败 ES 不回滚；
- 回调 `ParseResponse`（`response_model.py:32-43`）不含 chunk 数量/pk 列表。

---

## 3. 代码级证据：doc2md 能力边界

外部仓库 `/home/szf/data/dev/doc2md` 确实存在且功能完整（20 个 CLI 命令、内容寻址、DB 登记链）。

### 3.1 已具备

| 能力 | 出处 |
|---|---|
| 内容寻址 `content_uid == sha256` | `handoff/external-refactor-2026-10-17/02-design-decisions.md:9-12`（D-01）；`backend/app/core/ids.py:13-26` |
| 产物目录 `parsed/by_hash/<2>/<2>/<sha>/` | `backend/app/core/parsed_paths.py:18-33` |
| 四件套定义 | `parsed_text.md` / `parsed_metadata.json` / `parse_manifest.json` / `document_ir.json`（`parsed_paths.py:7-15`；平台 `store.py:39-44` 同口径） |
| `parsed_text.md` 是证据 span 唯一基准，不得改写内容或 hash | `handoff/.../05-data-contracts.md:9-11` |
| `parse_manifest.json` 关键字段 | 真实样本 `docs/demo/pdf-rich-to-text/parse_manifest.json:1-47`：`content_uid / sha256 / parser_name / parser_adapter_version / generated_at / status / output_hash(=sha256(parsed_text)) / asset_files / ir_source_files` |
| `document_ir.json` 结构 | `backend/app/services/document_ir_schema.py:85-99` 13 个顶层键；样本 `docs/demo/pdf-rich-to-text/document_ir.json:1-271` 有 `blocks`(heading/paragraph/table/figure)、`content_ref.text_span.start/end_offset`、`tables[].cells[]`、`figures[]`、`reading_order`、`stats`。**IR 里没有 `chunks`，也没有名为 `locator` 的字段**——两者由平台 `projection.py:234-277` 生成 |
| 单文件幂等 | `markitdown_parser.py:402-412` `_should_skip_idempotent`（`status==SUCCESS && parser_adapter_version==当前`）；`mineru_pdf_parser.py:867-878` 同；`file_content_vault.py:162-186` 按 `original.bin` 哈希跳过 |
| DB 登记链 | `sql/001_init_schema_v1_1.sql:20-254`：`kb_file_instance / kb_file_content / kb_raw_vault_object / kb_parse_job(uk_parse_idempotent) / kb_document / kb_document_chunk / kb_evidence`；`parse_registry.py:1001-1027` 写 `parse_status` |

### 3.2 明确缺失（本方案要求新增的部分）

| 缺口 | 直接证据 |
|---|---|
| 按库/目录的 `added/changed/deleted` 集合 | `inventory_scanner.py:88-95` 全量 `rglob`；`ScanResult`（`:32-53`）只有计数；`is_available=0` 只在扫描异常分支（`:277-311`）；服务层搜 `new_files\|changed_files\|deleted_files\|delta\|incremental\|fingerprint` 仅 1 处无关命中（`document_ir_builder.py:221-223` 循环变量） |
| 队列命令是 placeholder | `backend/app/cli/main.py:1076-1083` 原文：`typer.echo("build-parse-queue placeholder")` / `typer.echo(f"parse placeholder limit={limit}")` |
| 无 `--kb` 参数 | `--source-root` 只出现在 `cli/main.py:53-64`，作用是写入 `KbFileInstance.source_root` 标签，不进产物清单、不参与下游过滤 |
| `reconcile-parsed-artifacts` 不是增量扫描 | `parse_registry.py:1092-1114` 用 `by_hash.glob("*/*/*/parse_manifest.json")` 扫**已存在产物**回填 DB |
| 扩展层增量同步是设计候选 | `backend/app/extensions/sources/base.py:35-57` 有 `EVENT_TYPES`/`capabilities`；但 `extensions/cli.py:269-276` 非 dry-run 一律 `E_NOT_IMPLEMENTED`，`cli_contract.json:3` `"state": "DESIGN_CANDIDATE"` |
| README 的「只重建受影响表」是文档内表格级订正 | `README.md:17,90,203` 指 `review/correction.apply_correction`；`extensions/review/correction.py:17` 原文 "Only affected tables are rebuilt" |
| PDF 不产第 4 件 | `mineru_pdf_parser.py:626-697` 只写三件套 + `assets/` + `ir_source/`；平台 `scripts/v2_fill_mineru_ir.py:2-9` 补口 |
| 平台脚本主动破坏幂等 | `scripts/v2_ingest_doc2md.py:65-92` `_reset_vault_state` 的 SQL `update kb_file_content set vault_status='NOT_COPIED', vault_path=NULL, parse_status=NULL`；`:136-138` PDF 固定 `--force`；`kb_pipeline.py:118-134` 说明 `generated_at` 每次变，故 artifact_id 用产物摘要而非源文件哈希 |
| 双路同源校验未落生产 | `artifact_binding.py:179-199` `assert_same_artifact` 全仓只有 `tests/test_artifact_binding.py:163-204` 调用；生产里 `bind_artifact` 仅 `api.py:364` 图谱路使用 |
| `data/` 下无四件套样本 | 真实样本只有 `docs/demo/pdf-rich-to-text/` 与 `handoff/.../10-artifacts/`；`data/` 只有输入语料 |
| 无 `config/app.yaml` | 只有 `config/app.example.yaml`；`backend/app/core/config.py:8-10,59-66` 回落到 example |

### 3.3 平台侧与 doc2md 的既有契约

- `scripts/v2_ingest_doc2md.py:109-142` 四步 CLI：`scan --path <单文件临时目录> --source-root <kb>` → `_reset_vault_state` → `copy-to-vault --sha256` → `route-parsers --sha256` → `parse-mineru-pdf --force` 或 `parse-markitdown`；`:144-163` 校验四件套齐全；`:165-188` 组 `producer_inputs` 并调 `K.consume_for_kb(...)`。
- `parse_artifact/store.py:119-170` `collect_parts` / `read_set_digest`（对 `(role, relative_path, sha256, size_bytes)` 规范序 sha256）；`:245-276` `_check_source_consistency`（`output_hash` 对齐、三方 `content_uid` 一致、IR span 逐字一致、asset 哈希对齐）；`:448-479` `commit` 幂等 / `ARTIFACT_CONFLICT` / `SOURCE_CHANGED`。
- `graph_engine_adapter/artifact_binding.py:32` `CONTENT_SPEC = "llmke.artifact-binding.chunks/1"`；`:171-173` `content_hash = sha256(canonical_json({schema, chunks: manifest}))`。

---

## 4. 代码级证据：V2 摄取与投影（改造点）

| 事实 | 出处 |
|---|---|
| 18096 只有 `POST /kb/ingest` 与 `GET /health`；**无 `/kb/rebuild`** | `kb_ingest_service.py:130,142`；`/health` 的 `wired` 只列 `POST /kb/ingest` |
| 请求体是裸 dict；字段 `kb/file_id/doc2md_dir/file_url/...` | `kb_ingest_service.py:142-205` |
| `source` 被读取但未传给 runner | `:191-205` |
| 默认 `result["projection"].pop("payloads")`；`code=200/207` 只看 `status` | `:216-221`；`RemoteV2IngestUtils.java:96-100` 只把非 200/207 记日志 |
| **投影 `payloads` 无任何落库消费者** | 全仓只有生产方 `kb_pipeline.py:263-286`、丢弃方 `kb_ingest_service.py:216-218`/`scripts/v2_ingest_doc2md.py:219`；「payload→19527/19526」适配层不存在 |
| `consume_for_kb` 图谱路遍历 `kb_state.json` 全部历史文件全量重建 | `kb_pipeline.py:203-207,237-255`；`:174-193` `_load_kb_state` 损坏静默 `{}`、无锁、固定 `.json.tmp` |
| 搜索路只回本次 payloads | `kb_pipeline.py:228-235` |
| `_chunk_pk` 规则 | `rag_projection/projection.py:119-127`；表格 `_table_pk` `:93-96` |
| `build_index_payloads` 产出 `{index, page_content, metadata, pk, _fill}` | `kb_pipeline.py:91-115`；metadata 字段清单 `ingest_pipeline/enrich.py:44-112`（33 字段 + `parse_artifact_id/content_uid/channel/table_id`） |
| 写入端点契约 | 19527 `index_fulltext_service/.../base.py:39-62` `InsertDataModel{index_name, document_list, type, duplicate_flag}`、`controller/es.py:144-278`；19526 `index_vector_service/.../base.py:58-65`、`milvus_kb_service.py:413-700` |
| Milvus 静默丢 schema 外字段 | `milvus_kb_service.py:538-540` `if k not in i_name: continue` |
| `duplicate_flag=True` 是按 `metadata.source` 全量替换 | `es.py:476-484,531-557`；`milvus_kb_service.py:683-700` |
| 读写前缀不一致风险 | `projection_read.py:24-56` `INGEST_READ_PREFIX` 默认 `v2cand`，而 `build_index_payloads` 用 `index_name=kb` |

---

## 5. HippoRAG 2.0.0a4 SDK 依据（框架性）

| 项 | 证据 |
|---|---|
| 包位置与版本 | `/home/szf/data/dev/hipporag-toolenv/lib/python3.11/site-packages/hipporag/`；`hipporag-2.0.0a4.dist-info/METADATA:1-19`（`Name: hipporag`、`Version: 2.0.0a4`、`Home-page: github.com/OSU-NLP-Group/HippoRAG`、`Requires-Python >=3.10`、依赖 `torch==2.5.1/transformers==4.45.2/vllm==0.6.6.post1/networkx==3.4.2/python_igraph==0.11.8`） |
| 版本锁 | `docs/design/unified-documents-v2/locks/hipporag-2.0.0a4-requirements.txt:44` `hipporag==2.0.0a4`；`EVIDENCE-C1-HIPPORAG-20261031.md:9-16` 记录 wheel sha256 与 CPython 3.11.15 |
| 适配层构造 | `engine_hipporag.py:24-57`：`BaseConfig(save_dir, llm_name, llm_base_url, embedding_model_name, embedding_base_url, openie_mode="online")` → `HippoRAG(global_config=cfg)` |
| `index()` | `HippoRAG.py:215-275`：`OpenIE` → `chunk_embedding_store.insert_strings(docs)` → `load_existing_openie` → `batch_openie(仅新块)` → `save_openie_results` → `Encoding Entities/Facts` → `add_fact_edges` / `add_passage_edges` → `add_synonymy_edges` / `augment_graph` / `save_igraph` |
| `delete()` | `HippoRAG.py:277-356`：只清理「不再被任何存活块引用」的三元组/实体；`:280` 原文 "triples and entities which are indexed from chunks that are not being removed will not be removed" |
| `apply_delta` | `engine_hipporag.py:76-101`：按**文本集合差集**，`wanted/existing/to_delete/to_add`，返回 `deleted/added/reused/duplicates/remaining/expected/consistent` |
| 图仍是全量重建 | `engine_hipporag.py:82-84` 原文；`HippoRAG.py:250-267,753-756,837-851` |
| 产物文件 | `<working_dir>/{chunk,entity,fact}_embeddings/vdb_*.parquet`（`embedding_store.py:39-41,109-120`）；`openie_results_ner_<llm>.json`（`HippoRAG.py:151,990-998`）；`graph.pickle`（`HippoRAG.py:179-195,1083`）。**SDK 不写 graphml** |
| 关键配置 | `utils/config_utils.py:65-74` `force_openie_from_scratch=False` / `force_index_from_scratch=False`；`:109-120` `openie_mode="online"`；`:148-167` `synonymy_edge_topk=2047` / `sim_threshold=0.8`；`:172-183` `damping=0.5` |
| 检索语义 | `HippoRAG.py:414-423`：`len(top_k_facts)==0` 就走 DPR；`prepare_retrieval_objects` `:1141-1219`，`delete` 也会触发 `:288-289` |
| 增量实测 | `EVIDENCE-DELTA-REBUILD-20261031.md:3-4,45-53`：全量 32.4s → 增量 7.5s（4.3×），`openie 5→3` 与期望相等，指针 `mode=DELTA`；`08_CAPACITY_AND_PERFORMANCE.md:24-31` 另有 10 块 63.5s→7.3s（8.7×）；`EVIDENCE-SCOPE-DELTA-20261101.md:69-70` 8.9s / 7.8× |
| 不可外推 | `08_CAPACITY_AND_PERFORMANCE.md:3,31` 「样本很小（5–10 块），不可外推」；`metrics.py:17` 无 build 期分段计时；`EVIDENCE-REBUILD-20261031.md:50` 「真实库规模未测」 |

### 5.1 适配层已有的增量/一致性组件（本方案直接复用）

| 组件 | 出处 |
|---|---|
| `docs_fingerprint(docs)` | `rebuild.py:48-58`，按 `file_id` 分组的 text sha256 列表 |
| `check_freshness` | `rebuild.py:61-87`，返回 `stale/reason/missing/removed/changed`；`:66-68` 只报告不阻止读 |
| `rebuild`（FULL） | `rebuild.py:102-132` |
| `rebuild_delta`（DELTA） | `rebuild.py:192-237`，`:204-211` 无基准快照**拒绝**；`:221` `copytree` 复制整个基准快照 |
| `rebuild_if_stale` | `rebuild.py:240-253`，fresh → `SKIPPED_FRESH` |
| `rebuild_by_policy` | `rebuild.py:256-281`，`:263-266` 禁止静默降级，返回 `requested_mode`/`effective_mode` |
| `_promote` / `_cas_write_pointer` | `rebuild.py:158-189,135-155`，flock CAS + fencing；`:138` 明说 flock 不跨机 |
| `FenceState` | `fence.py:25-143`，`revoke` / `is_revoked` / `filter_hits` / `assert_index_fresh` |
| `canary.load` | `canary.py:188-231`，文件 > 环境变量 > 默认，默认 `full` |
| `global_report` | `global_report.py:1-6,218-306`；`community.py:61-144` 全局标签传播；**无局部 patch 接口** |
| `api.py` 现有 8 端点 | `:333 health`、`:356 /v2/graph/build`、`:415 /v2/graph/query`、`:468 /v2/entities`、`:511 /v2/status`、`:539 /v2/fence`、`:547 /v2/graph/view`、`:634 /v2/graph/global`；**无 delta 端点** |
| `state` 单份全局字典 | `api.py:305-331,382-385`，无 per-kb 隔离、无锁 |
| 社区报告后置 | `api.py:404-413` 只在 FULL build 路径调 `global_report.write`；`sources.json` 只在 `_default_build:223-238` 写 |

---

## 6. 既有契约、派工与故障证据

### 6.1 契约规则 HR-01~HR-10

`contracts/rules/llmke-hybrid-retrieval.yaml:8-56`（逐条 requirement 与 verification_class），`contracts/registry.yaml:295-305` 登记（`:305` `x-lifecycle: DESIGN_REVISED_NOT_IMPLEMENTED`，无 `checker` 字段），`contracts/README.md:13-15` 说明 2026-11-05 登记、共 28 项且「合同通过不代表已实现」。

与本方案最相关：HR-01（整数 pk 三者一致）、HR-02（禁原生 ID 进 source）、HR-03（向量只算一次）、HR-04（Milvus `kb_<name>`，禁把 parquet 当向量库）、HR-05/06（三路并行 + RRF by pk）、HR-08（ES 保留）、HR-09（图读完整 MD/IR、命中回指 pk/file_id/locator）、HR-10（global 以 community.json 为源）。

校验工具：`Makefile:12-18` `make generate/check`；`scripts/contract_toolchain.py:34-60` 对 `rules` 类型**只校验顶层 `rules` 键存在**，HR 无自定义 checker；`tests/test_hybrid_rrf.py:1-9` 只覆盖 HR-06；`scripts/v2_hybrid_milvus_backfill.py:9-18,195` 覆盖 HR-03/04 的回灌校验。

### 6.2 设计文档约束

- `11_VECTOR_STORE_AND_HYBRID_RETRIEVAL.md:4` 「设计与契约已编制；实现未执行」；`:17-21` 统一标准输入/统一来源身份/禁止引擎原生 ID；`:36-51` 写入链路；`:53` ES 保留（选型已定）；`:57-61` pk 规则；`:96-102` 5 条硬性验收；`:106` HR 与 DP 冲突以 DP 为准。
- `06_STANDARD_INPUT_AND_GRAPH_ENGINE.md:8` 业务接口不保存 HippoRAG 类/pickle/native ID；`:30-43` 四件套清单；`:105` 增量/删除/社区能力分别声明、不用空实现伪装；`:117-124` 6 条适配约束（第 6 条 pickle 禁令）；`:147-155` 同一 KnowledgeInputBundle 重放不重跑 doc2md。
- `08_CAPACITY_AND_PERFORMANCE.md:7-15` 目标表（10 万块 ≤ 8h / 变更 1% ≤ 30min，**建议值需业务确认**）；`:17-22` 瓶颈顺序；`:40-52` 压测必须补做。
- `IMPLEMENTATION-QUEUE-V2.md:3` 唯一实施入口；`:6-7` 只按真实能力统计；`:13-15` 五步闭环；`:71-88` VL1-02（上游缺 IR 抛 `UPSTREAM_IR_MISSING`、不写快照、不允许 RAG/图侧重解析兜底）；`:100-106` **表格通道未补齐前 `snapshot` 模式不得切换**；`:388-400` 首个切片 VL1-01~04、不先做图引擎；`:414` registry/TRACE 仅合同变更任务可改。
- `EVIDENCE-DELTA-REBUILD-20261031.md:64-72` 未做清单：检索质量未测、同文本合并、磁盘成本、未接调度器、`describe()` 未登记 DELTA。
- `EVIDENCE-SCOPE-DELTA-20261101.md:121-131` 未做清单：跨范围合并检索、fence 不管、清单并发写未加锁、未接 worker、不测检索质量。
- `docs/NEXT.md:185-191,400-410,442-458,586-592`：`snapshot` 不得先切、表格通道/MinerU IR 待补、**增量检索排序漂移待查**（top1 0.667 / ordered 0.5 / jaccard 0.75，3 条 DIFF，建议先只对新增文件场景用 delta）。

### 6.3 派工与证据文档

`docs/dispatch/HYBRID-RETRIEVAL-DISPATCH.md:3-7` 已批准目标与「不做范围」（`:7` **不重跑 doc2md 解析**；`:25-38` **不直接改 doc2md 源码**）；`:40-47` 阶段划分；`:49-55` required_checks；`:63-68` 独立 QA 不得自签。

`docs/dispatch/evidence/` 7 个文件：`HYBRID-RETRIEVAL-STAGE0-1-3.md`、`STAGE2.md`、`STAGE3.md`、`STAGE4-阻塞.md`、`STAGE5.md`、`RECOVERY-20261106.md`、`hybrid-baseline-0.json`。关键数值：`STAGE5.md:13-21` 三者对齐表、`:86` kb_9 4566 doc 建图约 3.5h；`STAGE3.md:50-51` 单一 query 不保证三路同时出现；`hybrid-baseline-0.json:2-5` schema/stage/generated_at，`:29-138` kb_9 五条 query（含 `AAA档` hits=1、`5000万` hits=0、`T-CORE-001` hits=1、`5000万元` hits=2），`:139-280` kb_1004 中文全 0 / 英文各 1；所有 `docs[].metadata_pk` 为 `null`（`:37,66,85`）。

### 6.4 已知故障

- `/tmp` 清空：`HYBRID-RETRIEVAL-RECOVERY-20261106.md:14-23` —— `/tmp/tl-a2-root`（图快照）、`/tmp/kb-artifact-store`（`kb_state.json` + 四件套）、`/tmp/doc2md-fullrun` 全丢；`:24-35` 恢复动作（新建持久化图根 `platform/r12/data/graph-root`、从 ES 统一 pk 重建、不重解析）。
- 静默降级：`docs/r12/r14/D-JOURNEYS.md:239`（`F-D-04`）、`CAPABILITY-MATRIX.md:75`（`F19`）、`docs/policies/ACCEPTANCE-BASELINE.yaml:28`（`RET-01: coverage/degraded 准确且不静默降级`）、`docs/reviews/R14-EXTERNAL-REVIEW-20261029.md:287-296`「静默失败是本项目的主导故障模式」。
- 双仓配置漂移：v2 仓 `application-r12.yml:93-109`（V2 注释 + `v2-ingest: url: ""`）vs 运行仓 `llmke-r12/.../application-r12.yml:93-101`（无该段、注释仍是「R15 W03」）；运行仓另有 `.bak-20261102` 指向 19529/19532。
- **明确找不到**：`docs/reviews/` 中没有以「双仓配置漂移」「19532 下线后检索静默降级」为题的专门证据文档；`docs/dispatch/evidence/` 中也没有。上述结论由配置对比与同型判据构成。

### 6.5 部署拓扑

- `R12-ENV-CONTRACT.md:9-36` 端口表**无 18094/19531/19532/18096**；`:24` 12340；`:27-28` 19526/19527；`:69` A-10 两套端口语义不可混用。
- `r12-graph-v2-start.sh:15-18,52,66-67`：V2 图栈 18094 + 19531，`LLMKE_V2_ROOT` 注入持久化图根；`r12-watchdog.sh:61-64,417-421` 守护 V2、移除 Nebula。
- **18096 无任何启动定义**：`platform/r12` 全量搜 `18096` 只命中一个 `sources.json` 里的数字子串；不在 `algctl.sh:170` ALL、不在 `r12-watchdog.sh:57-71` TARGETS、不在 `up.sh:130-135,210`、不在任何 systemd unit、不在端口表。唯一「启动命令」是 `kb_ingest_service.py:18-20` 的 docstring。
- 环境变量：`LLMKE_DOC2MD_CONFIG` / `LLMKE_DOC2MD_LOCK` / `LLMKE_ARTIFACT_STORE` **两仓 `.env` 与 `platform/r12` 均未定义**；`LLMKE_V2_ROOT` 仅 `r12-graph-v2-start.sh:52` 定义；`R12_MINIO_ACCESS_KEY/SECRET_KEY` 在 `.env:6-7` 已有，`ENDPOINT/BUCKET` 未定义。

---

## 7. 评审可自行复核的命令

```bash
# 1) 数据现状
for kb in kb_9 kb_1004; do
  curl -s http://127.0.0.1:19200/$kb/_count; echo
  curl -s http://127.0.0.1:19200/table_chunks_$kb/_count; echo
  curl -s http://127.0.0.1:18094/v2/status?kb=$kb | python3 -m json.tool
done

# 2) doc2md 不在主链
grep -rn 'doc2mdDir\|doc2md_dir' services/rag-java/rag-parent/ | head
grep -n 'file-parse' platform/r12/conf/rag-index-service/application-r12.yml

# 3) 18096 无启动定义
grep -rn '18096' platform/r12/ | head
ss -tlnp | grep -E ':(12340|18096|18094|19531)\b'

# 4) HippoRAG SDK 与增量边界
grep -m1 '^Version:' /home/szf/data/dev/hipporag-toolenv/lib/python3.11/site-packages/hipporag-2.0.0a4.dist-info/METADATA
sed -n '76,101p' services/rag-alg/index_data_service/graph_engine_adapter/engine_hipporag.py
sed -n '192,237p' services/rag-alg/index_data_service/graph_engine_adapter/rebuild.py
grep -n '@app\.' services/rag-alg/index_data_service/graph_engine_adapter/api.py

# 5) doc2md placeholder
sed -n '1076,1084p' /home/szf/data/dev/doc2md/backend/app/cli/main.py

# 6) 契约
sed -n '8,56p' contracts/rules/llmke-hybrid-retrieval.yaml
make check
```
