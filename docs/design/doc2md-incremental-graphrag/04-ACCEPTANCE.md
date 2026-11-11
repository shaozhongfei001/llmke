# 04 · 验收、灰度、回滚与风险登记

> 状态：**待评审**。验收口径遵循 `IMPLEMENTATION-QUEUE-V2.md:6-7`「只按真实可用能力 + 已关闭验收统计，不用提交数/文件数/行数/准备度；无现场可跑命令与结果不得标 DONE」，以及 `:13-15` 五步闭环。
> 所有验收必须在**真实消费者**上跑：Java 智能问答 `/qa/ai/question`、19995 `/retrieval_documents`、19995 `/retrieval_documents_global`、18094 `/v2/graph/global`。

---

## 1. required_checks（评审放行的硬门禁）

| ID | 检查 | 判据 | 现场命令/证据 |
|---|---|---|---|
| A-1 | 12340 彻底退役 | `ss -tlnp` 无 12340；`rag-index-service.log` 无 `/parse`；配置无 `remote.file-parse.*`；watchdog/up.sh/systemd 无 12340 条目 | `ss -tlnp \| grep 12340`；`grep -rn '12340' platform/r12/` |
| A-2 | 唯一解析者 | 上传 pdf/docx/xlsx/txt 各一份，产物目录出现四件套且 `parse_manifest.status=SUCCESS`；`parsed_text.md` hash 与 `output_hash` 一致；IR span 逐字对齐 | `store._check_source_consistency` 通过日志；四件套文件清单 |
| A-3 | 全量与增量同入口 | 全量重建与单文件上传都走 `POST 18096/kb/ingest`，响应 schema 相同 | 摄取服务访问日志 + 请求/响应样本 |
| B-1 | 一次快照三路同源 | ES/Milvus/图三路载荷的 `artifact_id`、`content_uid`、`content_hash` 一致；`assert_same_artifact` 生产调用返回 true | `IngestResult.data.index_write.same_artifact=true`；`tests/test_artifact_binding.py` 扩生产断言 |
| B-2 | pk 三路对齐（HR-01/02） | ES `_id` = Milvus `pk` = 图 `sources[0].pk`，均为整数；无 `chunk-<md5>` 进入 source/引用 | 抽样 100 个 pk 三路比对脚本；`_pick_pk` 无 None |
| B-3 | 三路融合形状不变（HR-05/06/07） | `search_type` 在合适 query 下分别出现 es/milvus/graph；同 pk 不重复；rerank 仍是 top_n×3 + 相对阈值 | `pytest tests/test_hybrid_rrf.py -q`；19995 返回体抽样 |
| B-4 | 向量只算一次（HR-03/04） | Milvus 行数 = ES 对应通道行数；无第二套 embedding 调用 | `v2_hybrid_milvus_backfill.py` 的硬校验逻辑复用到在线写入 |
| C-1 | 真增量生效 | 新增 1 文件时 `effective_mode=DELTA`、`apply_result.reused == 原块数`、`added == 新文件块数`、`consistent=true`；LLM OpenIE 调用计数只增 `added` 量 | `IngestResult.data.graph.apply_result`；LLM 服务调用日志计数 |
| C-2 | 无变化短路 | 重复上传同一文件 / 回调重放 → `SKIPPED_FRESH` 或 `status=SKIPPED_FRESH`，且 `full_build`/`delta_apply` 零调用 | mock 计数断言 + 18094 访问日志 |
| C-3 | DELTA 后报告正确 | 新增/删除后 `<snapshot>/sources.json`、`community.json`、`fence.json`、`kb.json` 均由本次输入重算（与基准快照 sha256 不同）；`citation_check.ok=true`；无已删 file_id 引用 | 四文件 sha256 对比；`/v2/graph/global` 返回体 |
| C-4 | 删除与撤权 | 删除文件后先 fence revoke 再 delta；旧答案不再引用已删文件；`filter_hits` 生效 | `/v2/fence` 与 global 答案抽样 |
| C-5 | 不静默降级 | 无基准快照 / 全撤权 / fencing 落后 → `REJECTED` + 原因码，指针不动；`full` 必带 `fallback_reason`；`requested_mode != effective_mode` 必可审计 | 反例日志 + 指针前后对比 |
| D-1 | 失败不假成功 | 停 18094 或写坏 ES → Java 文件状态为 `PARSE_FAIL`/`RETRY`，前端可见原因；不出现「解析成功但无图/无索引」 | Java 状态表查询 + 摄取响应错误码 |
| D-2 | 双库并发隔离 | kb_9 / kb_1004 交替 build+query，无串库（B 不用 A 的 `text_to_idx`/fence）；`fencing` 递增且旧主写入被拒 | 并发压测脚本 + `states` per-kb 断言 |
| D-3 | 持久化与自愈 | `kb_state.json` / artifact store / graph root 全在非 `/tmp` 路径；18096 有启动定义 + watchdog + HTTP 探针；kill 后能自愈 | `kill` 演练 + `ls -d platform/r12/data/*` |
| D-4 | 启动自检 fail-fast | 故意把 18094/doc2md config 改不可达 → 18096 启动失败并打印具体原因；恢复后启动自检通过 | 启动日志 |
| E-1 | 基线不回退 | `AAA档`/`5000万`/`T-CORE-001`/`授信额度是多少`/`流动资金贷款期限` 召回与答案不低于 `hybrid-baseline-0.json` | 基线对比脚本 |
| E-2 | global 可用 | local 与 global 两种模式均返回正确答案；中英文语言跟随正确；无资料时诚实回答「资料中未提及」 | 15+ 中英文用例 |
| E-3 | 检索等价性（放量门禁） | 新增文件后，**未变更内容**的 top1/ordered/jaccard 不低于阈值；若出现排序漂移，delta 只允许用于新增场景、变更场景走 FULL | 见 §3 |

---

## 2. 验收用例矩阵

| 类别 | 用例 | 期望 |
|---|---|---|
| 格式 | pdf / docx / xlsx / txt / md 各 1 份（含中文路径、含表格与图片） | 四件套齐全、IR 校验通过、四路索引可查 |
| 全量 | 用 kb_9 全库做一次 `FULL_REBUILD` | `effective_mode=FULL`，三路 chunk 数对齐，global 可用 |
| 增量·新增 | 上传 1 个新文件 | `DELTA`，`reused == 原块数`，新内容可被问答检索到 |
| 增量·修改 | 覆盖上传同名文件、内容改变 | 旧块被 `to_delete` 清除，新块可查；不出现新旧并存 |
| 增量·删除 | 删除 1 个文件 | 先 revoke 再 delta；引用与向量/全文/图三路都清除 |
| 幂等 | 连续重复上传同一文件 3 次 | 第 2/3 次 `SKIPPED_FRESH`，LLM 调用零增长，pk 集合不变 |
| 并发 | 同库 2 个文件并发上传；两库交替上传 | 按 kb 串行化，无丢更新、无串库 |
| 失败 | 18094 停 / MinIO 403 / ES 写失败 / `kb_state.json` 损坏 / 基准快照被删 | 分别命中 `GRAPH_UNREACHABLE` / `DOC2MD_ARTIFACT_INCOMPLETE` / `INDEX_WRITE_FAILED` / `KB_STATE_CORRUPT` / `NO_BASELINE_SNAPSHOT`，且状态可诊断 |
| 问答·中文 | kb_1004「如何种植西红柿」、kb_9「授信额度是多少」「智造贷的贷款利率是多少」 | 中文答案，含具体数值/步骤 |
| 问答·英文 | kb_1004「How should I grow tomatoes」「When should I plant potatoes」、kb_9「What is the maximum credit limit」 | 英文答案，语言跟随正确 |
| 问答·否定/跨库 | kb_9 问园艺、kb_1004 问贷款、问不存在的「申请材料」 | 诚实「资料中未提及」，不编造 |
| global | kb_9 / kb_1004 各中英文 2 条 | 社区摘要命中、答案与引用一致、`citation_check.ok=true` |
| 引用 | 点击答案引用 | `retrieval_global_view._resolve_sources` 能从 ES 查到 `metadata.source` 并打开原文 |

---

## 3. 检索等价性门禁（放量前必须通过）

`docs/NEXT.md:442-458` 记录同语料 full vs delta 的检索等价性实测：top1 `0.667`、ordered `0.5`、jaccard `0.75`，3 条 DIFF；`:586-592` 明确「第三条说明增量路径可能改变了未变更内容的检索排序……决定 delta 能不能上生产」。`EVIDENCE-DELTA-REBUILD-20261031.md:64-72` 也把「检索质量未测」列为未做项。

**本方案把门禁设为「分档阈值」，而非单一 `jaccard=1.0` 硬指标**——因为图是「增量抽取 + 全量重建图」（`engine_hipporag.py:82-84`）：`add_fact_edges` 全量遍历 + `add_synonymy_edges` 全量 KNN + 社区编号全局重排（`community.py:68-97`），新增块会改变旧内容的图结构与排序。要求「未变更内容召回 jaccard=1.0」与框架事实冲突，会永久卡死放量（与 `00-DESIGN.md` §12.4 诚实边界互相印证）。

**门禁分三档**：

| 档位 | 度量对象 | 放行阈值 | 说明 |
|---|---|---|---|
| 召回集合 | 未变更内容是否仍被「召回」 | 理想 `jaccard=1.0`；**放行阈值 P6 压测后用 50 条固定 query 实测定**（预计 0.9 量级） | 度量「该出现的块是否还在」，是硬指标 |
| 排序漂移 | 召回结果的相对顺序 | 单独度量、逐条记录 DIFF；「新增文件」场景允许有限漂移 | 图结构重排导致，不必然等价于「质量下降」 |
| 答案正确性 | 答案是否仍正确、语言跟随 | 与 §2 用例矩阵一致（中英文各 ≥10 条） | 最终以答案正确性为准 |

**两条硬约束不变**：

1. 放量前必须用固定 50 条查询集做 full vs delta 对照，记录 top1 / ordered / jaccard 与逐条 DIFF，**把「召回集合漂移」与「排序漂移」分开统计**；
2. 若实测召回集合出现明显漂移（低于放行阈值），按 `docs/NEXT.md:586-592` 的建议收窄：**DELTA 只用于「新增文件」场景，「内容修改/删除」仍走 FULL**，并把该限制写进 `canary` 策略与能力声明，不得隐瞒。

压测方法按 `08_CAPACITY_AND_PERFORMANCE.md:40-52`：合成阶梯语料 1 千/1 万/10 万块，记录构图时间、内存峰值、磁盘占用，以及 1%/10% 变更下的增量耗时。**现有 32.4s→7.5s（4.3×）、63.5s→7.3s（8.7×）来自 5/10 块样本，不得外推为生产指标**（`08_...:3,31`；`metrics.py:17`）。

---

## 4. 灰度放量

```text
Step 1  kb_9 影子读 + canary mode=delta（仅新增文件）
Step 2  跑 §1 全部 required_checks + §2 用例矩阵 + §3 等价性门禁
Step 3  kb_1004 切读（4520 块，验证规模）
Step 4  放开「内容修改」场景的 delta（仅当等价性达标）
Step 5  全量切读，旧命名空间保留 N 天只读
```

开关全部走配置/文件热改，不重启：`INGEST_READ_MODE` / `INGEST_READ_PREFIX` / `INGEST_READ_KBS`（`projection_read.py:24-56`）、`canary.load` 每次重读盘（`canary.py:188-231`）、`LLMKE_CANARY_FILE`。**回退不用重启**（`canary.py` 的设计意图）。

---

## 5. 回滚剧本

| 层级 | 回滚动作 | 依据 |
|---|---|---|
| 读路径 | `INGEST_READ_MODE=legacy`，读回 `<kb>` / `_kb_9` | `projection_read.py:24-56` |
| 图指针 | 回退到 `pointer.previous` 指向的快照；`fence` 代次同步恢复 | `rebuild.py:174-180` 的 `previous` 字段；`EVIDENCE-ROLLBACK-20261101.md` |
| 平台清单 | `kb_state.json` 回退到上一 `version`（P2 版本化 + flock 保证） | `02-CONTRACTS.md` §4.2 |
| 索引 | 影子命名空间整体停用；旧 `<kb>` / `_kb_9` 未改动 | P2 影子双写 |
| 建图模式 | `canary` 改回 `full`（默认即 full），或直接停用 `/v2/graph/delta` | `canary.py:43-44`；`/v2/graph/build` 语义不变 |
| 整链回退（P5-3 之前） | `remote.v2-ingest.url=""` + 恢复 12340 派发配置 | 双仓配置同步校验 |
| 整链回退（P5-3 之后） | 需重启 12340 并恢复 4 个 `remote.*` 配置，代价上升 | 故 P5-3 之前必须留完整 E2E 通过记录 |

**破坏性动作**（删旧索引/集合、停 12340、归档数据）需 Owner 单独授权，参照阶段 4 下线的做法（每步停后验证主链路 + global 正常）。

---

## 6. 风险登记表

| ID | 风险 | 概率 | 影响 | 缓解 | 责任阶段 |
|---|---|---|---|---|---|
| R-01 | 换解析器导致 pk 全变，新旧 pk 混写破坏 RRF | 高 | 致命 | 影子命名空间 + 别名原子切换；禁止原地覆盖；切换前后基线对比 | P2/P6 |
| R-02 | DELTA 沿用 copytree 带来的旧 `sources.json`/`community.json`，global 出现幽灵引用 | 高 | 高 | `_finalize_snapshot()` FULL/DELTA 共用，四文件强制重算；C-3 反例 | P3 |
| R-03 | 增量检索排序漂移（未变更内容召回变化） | 中 | 高 | §3 等价性门禁；不达标则 delta 只用于新增场景 | P6 |
| R-04 | 图仍是「增量抽取 + 全量重建图」，大库构图不随变更比例下降 | 高 | 中 | 明示不宣称；压测 1千/1万/10万；`08_...` 目标值重议；图分片列为后续 | P6/P7 |
| R-05 | 同文异源合并成一块，来源 1:N 映射丢失 | 中 | 中 | `sources.json` 保留 `native_key -> [SourceRef]`（`06_...:86-90`）；验收用重复内容文件 | P3 |
| R-06 | `kb_state.json` 并发丢更新 / 被 `/tmp` 清空 | 中 | 致命 | 持久化路径 + flock + 版本 + 损坏报错（不再静默 `{}`） | P2/P4 |
| R-07 | 双仓配置漂移再次发生 | 中 | 高 | 两仓关键键机器比对 + 启动自检打印实际加载地址 + fail-fast | P5/P4 |
| R-08 | doc2md 改动触及 `parsed_text.md` hash 或四件套契约 | 中 | 致命 | 全部 additive；`output_hash`/IR span/`content_uid` 三方校验；反例先造失败 | P1 |
| R-09 | PDF 第 4 件补口失败，触发 `UPSTREAM_IR_MISSING` | 中 | 高 | P1-4 原生实现；切换前四类格式真实跑通；`snapshot` 不得先切 | P1 |
| R-10 | 表格通道未补齐就切 `snapshot`，`table_chunks_*` 数据缺失 | 中 | 高 | 遵守 `IMPLEMENTATION-QUEUE-V2.md:105-106` 硬禁令，P1-5 作为硬前置 | P1/P6 |
| R-11 | `state` 单份全局导致串库 | 中 | 高 | per-kb `StateSlot` + 按 kb flock + D-2 并发验收 | P3 |
| R-12 | 摄取失败仍显示解析成功（假成功） | 高 | 高 | 错误码 + Java 状态回写；D-1 反例；禁止只 log | P4/P5 |
| R-13 | LLM 抽取非确定，两次构建结果不同 | 高 | 中 | 不宣称端到端可复现；`community.json` 只保证同快照输入逐字节一致；基线容差按 `EVIDENCE-BASELINE-NOISE` | 全程 |
| R-14 | 目录复制 + `keep_last` 造成磁盘膨胀 | 中 | 中 | 配额/清理策略（`EVIDENCE-DELTA-REBUILD-20261031.md:64-72` 未做项）；压测记录磁盘峰值 | P6 |
| R-15 | 契约登记时破坏既有 28 项 registry | 低 | 高 | P0 只交附录，批准后才改；`make generate && make check` | P0/P7 |

---

## 7. 证据归档要求

每阶段产出 `docs/dispatch/evidence/DOC2MD-INCREMENTAL-P<n>.md`，必须含：

1. 现场可跑命令与**真实输出**（不是叙述）；
2. 组件级反例的失败证据（先造失败，再证明修复）；
3. required_checks 对应项的通过/未通过表；
4. 回滚演练结果；
5. 如实标注的「未做 / 边界」（对齐 `EVIDENCE-DELTA-REBUILD-20261031.md:64-72` 的写法）。

**状态口径**：任何一个 required_check 未通过，该阶段不得标 `DONE`；不得用「代码已提交」代替「能力已验收」（`IMPLEMENTATION-QUEUE-V2.md:6-7`）。

---

## 8. 明确不可宣称的验收结论（防止评审被误导）

1. 不能写「图谱支持增量图更新」——只能写「增量抽取 + 全量重建图」（`engine_hipporag.py:82-84`）。
2. 不能写「构建耗时随变更比例线性下降」——无大库实测（`08_...:3,31`）。
3. 不能写「检索质量已等价」——除非 §3 门禁通过（现 `NEXT.md:442-458` 有 3 条 DIFF 未查清）。
4. 不能写「端到端可复现」——LLM 抽取非确定（`:43-49`；`06_...:140`）。
5. 不能写「同文异源可区分」——块 id 是文本哈希（`:68-69`）。
6. 不能写「global 跨机确定性已验证」（`06_...:145`）。
7. 不能把 `graph.pickle` 当公共资产（`06_...:124`）。
8. 不能把 `community.json` 的 `BLOCKED` 用普通 RAG 顶替（`HR-10`；`06_...:122-123`）。
