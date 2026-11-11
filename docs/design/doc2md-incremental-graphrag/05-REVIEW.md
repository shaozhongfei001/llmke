# 05 · 评审自证、待裁定项与检查题

> 面向：**独立架构智能体评审角色**。本文件的目标是让评审者不必信任 `00-DESIGN.md` 的叙述，而能按「要求 → 证据 → 设计 → 反例 → 验收」逐条复核并给出可证伪结论。
> 状态：**待评审 / 未开工 / 未修改生产代码**。

---

## 1. 评审方法与证据等级

| 等级 | 含义 | 本包对应 |
|---|---|---|
| L1 运行时数据 | 可直接 curl / 查库复现 | `01-EVIDENCE.md` §1、`04-ACCEPTANCE.md` §1 |
| L2 源码事实 | 文件路径 + 行号 + 原文 | `01-EVIDENCE.md` §2~§6、`02-CONTRACTS.md` 的「现状」标注 |
| L3 上游 SDK 事实 | 安装包内源码 / METADATA | `01-EVIDENCE.md` §5（hipporag 2.0.0a4） |
| L4 设计主张 | 本方案提出、尚未实现 | `00-DESIGN.md` §5~§10、`02-CONTRACTS.md`、`03-IMPLEMENTATION.md` |
| L5 待裁定 | 与既有契约冲突，需 Owner 决定 | 本文 §3 |

**评审判定原则**：L4 的每一条主张都必须能挂到至少一条 L1/L2/L3 依据，并配一个可造的反例；挂不上的应驳回，不要靠「合理推测」放行。L5 未裁定前不得开工（`IMPLEMENTATION-QUEUE-V2.md:3` 唯一实施入口）。

---

## 2. Owner 三条要求逐条自证

### 要求 1：彻底抛弃 12340 的 Java 原始文档解析，全量/增量一律走 doc2md

**现状证据（L2）**

- Java 派发唯一出口 `RemoteFileUtils.java:43-44,339-341` → `remote.file-parse.url` = `http://127.0.0.1:12340/parse`（`application-r12.yml:83-84`）；同步入口 `/parse_sync`（`:85-86`）。
- 请求体 `ParseParam.java:17-138` 与接收体 `server/api_param.py:9-50` 均无 doc2md 字段；`FileParseTaskInfo.doc2mdDir`（`:162-169`）全仓无赋值点。
- `adapter_doc2md/adapter.py` 未接生产；doc2md 只在解析完成后的旁路 `v2-ingest` 出现，且该旁路 `v2-ingest.url=""`（`application-r12.yml:103-109`）、18096 未监听（L1）。
- `R12-ENV-CONTRACT.md:24` 仍登记 12340；`r12-docparse.service`、`r12-watchdog.sh:60`、`up.sh:62-70` 均有启动/守护定义。

**设计（L4）**：`00-DESIGN.md` §5.2/§5.3，`03-IMPLEMENTATION.md` P5。保留 Java 任务表 / 15s 调度 / CAS 抢占 / `TaskReq` 回调协议 / 文件状态机，只替换派发目标为 `18096/kb/ingest`；`FileParseTaskInfo.doc2mdDir` 赋予真实值；删除 `generateGraph` 的 19531 路径；停 12340 进程并移除 systemd/watchdog/up.sh/端口契约条目。`doc2md_dir` 分支成为唯一分支，`file_url` 不再触发第二次解析。

**依据**：`TaskReq.java:11-43` 与 `response_model.py:32-43` 字段一一对应，Java 只消费 `success/task_id/task_statuses[0].revise_date`（`FileParseTaskAppServiceImpl.java:288-303,332`）——这是「不必重写状态机」的硬依据。

**反例**：把 `v2-ingest.url` 留空却停掉 12340 → 摄取链路悬空、文件永远 `PARSE_ING`；P5-3 之前必须留 E2E 通过记录（`03-IMPLEMENTATION.md` P5 回滚窗口）。

**验收**：`04-ACCEPTANCE.md` A-1/A-2/A-3、D-4。**结论：要求 1 已被设计覆盖，但需要 §3-C1/C2/C3/C12 裁定后才能开工。**

### 要求 2：doc2md 成为主解析者，搜索与图谱吃同一份四件套，增量真正接起来

**现状证据（L2）**

- 12340 一次 `parse()` + 一次 `chunk()`，同一个 `chunks` 双写 19527/19526（`controller.py:869-906`）；
- 图谱走 Java `generateGraph` → 19531 → **从 ES 全库取块** → 18094 全量 build（`FileAppServiceImpl.java:664-758`、`legacy_shim.py:283-322`）；
- V2 投影链路 `build_index_payloads` 产出的 `payloads` **无任何落库消费者**，且 `kb_ingest_service.py:216-218` 默认 `pop`；「投影载荷 → 19527/19526」适配层不存在；
- `assert_same_artifact`（`artifact_binding.py:179-199`）只有单元测试调用；`bind_artifact` 只在 `api.py:364` 图谱路用；
- `consume_for_kb` 图谱路遍历 `kb_state.json` 全部历史文件全量重建（`kb_pipeline.py:203-207,237-255`），搜索路只回本次（`:228-235`）。

**设计（L4）**：`00-DESIGN.md` §6、`02-CONTRACTS.md` §8、`03-IMPLEMENTATION.md` P2。

1. 一次 `store.commit()` → 一份不可变 `ParseArtifact`（`store.py:448-479` 已具备幂等/冲突/SOURCE_CHANGED）；
2. 一次 `project()` → 一份 `chunks`，三路派生：`index_writer.build()`（ES/Milvus）+ `build_graph_docs()`（BuildDoc）；
3. `content_hash` 按 `artifact_binding.CONTENT_SPEC` 口径同时写入两路，生产调用 `assert_same_artifact`，不一致 → `SOURCE_DIVERGED` 整批不发布；
4. 新增 `index_writer` 补齐缺失适配层，处理三个已证实的陷阱：Milvus 静默丢 schema 外字段（`milvus_kb_service.py:538-540`）、`duplicate_flag=True` 按 source 全量替换（`es.py:476-484,531-557`）、读写前缀不一致（`projection_read.py:24-56`）；
5. `kb_state.json` 升级为版本化 + flock + 持久化路径 + 损坏报错（`02-CONTRACTS.md` §4.2）。

**反例**：改一位 `content_hash` → 必须 `SOURCE_DIVERGED` 且三路都没写；两个文件共享 `source` → 写 A 不得删 B；`kb_state.json` 写坏 → `KB_STATE_CORRUPT` 而不是按空库重建。

**验收**：B-1/B-2/B-3/B-4、P2 四条组件级反例。**结论：要求 2 的「同源」有可机器校验设计；但 pk 会因换解析器全变，必须接受 §3-C5 的影子切换方案，否则不可行。**

### 要求 3：利用 HippoRAG 框架特性设计图谱增量，解决「回调一到就无条件重建」

**现状证据（L2/L3）**

- 没有 diff：`doSuccess` 收到 `success=true` 即 `generateGraph`（`FileParseTaskAppServiceImpl.java:300-303,354-355`），无文件集合/哈希/版本比对，`messageId` 是随机 UUID；
- HTTP 无增量端点：`api.py` 8 个端点无 delta；`_default_build:219` 固定 `rebuild(..., fencing=1)`，不调 `check_freshness`/`rebuild_if_stale`/`rebuild_delta`/`rebuild_by_policy`（这些函数在 `rebuild.py` 里已写好，只被 `scripts/v2_graph_worker.py:341-358` 和测试调用）；
- HippoRAG 2.0.0a4 的 `index()` 复用已有 OpenIE、只对新增块跑 `batch_openie`（`HippoRAG.py:235-240,881-924`），`apply_delta` 按文本集合差集（`engine_hipporag.py:76-101`）——**但图构建仍是全量**（`engine_hipporag.py:82-84`）；
- `rebuild_delta:221` 用 `copytree` 复制基准快照，会把旧 `sources.json`/`community.json` 带进新快照，而 `apply_delta` 不写它们；`global_report` 无局部 patch 接口，社区编号由全局标签传播决定（`community.py:68-97`）。

**设计（L4）**：`00-DESIGN.md` §7、`02-CONTRACTS.md` §2、`03-IMPLEMENTATION.md` P3/P4。

1. **平台侧 `KbDeltaService.diff()`** 基于 doc2md `kb-manifest.json`（新增 `scan-diff --kb`）与平台 `kb_state.json` 算 `added/changed/removed/unchanged`；diff 空 → `SKIPPED_FRESH`；
2. **引擎侧**传**全库 wanted texts**（`rebuild.py:200-202` 的硬约束），由 `apply_delta` 自己算 `to_add/to_delete`，只对新增块跑 LLM；
3. 新增 `POST /v2/graph/delta`：`check_freshness` 第一道短路 → `rebuild_by_policy` 选 FULL/DELTA → 无基准快照/全撤权/fencing 落后 `REJECTED`，显式 `full + fallback_reason` 才走 FULL，**不静默降级**；
4. **`_finalize_snapshot()`**：FULL/DELTA 共用，强制重算 `sources.json` + `community.json` + `fence.json` + `kb.json`（这是相对「直接接 rebuild_delta」最关键的补充，否则 global 会给幽灵引用）；
5. 删除先 `FenceState.revoke` 挡读；`state` 改 per-kb + 按 kb flock + fencing 递增；
6. Java 侧不再无条件建图，状态由摄取响应回写。

**框架依据（L3）**：`hipporag-2.0.0a4.dist-info/METADATA`；`HippoRAG.py:215-275,277-356,414-423,1141-1219`；`embedding_store.py:44-90`；`config_utils.py:65-74`；`capabilities.py:53-60`（`incremental_update=VERIFIED`、4.3×）；`EVIDENCE-DELTA-REBUILD-20261031.md:45-53`（openie 5→3 与期望相等、指针 `mode=DELTA`）。

**性能诚实边界**：只能宣称「省掉未变更块的 LLM 抽取」，不能宣称「增量图更新」或「耗时随变更比例线性下降」。5/10 块实测 4.3×/8.7× 不可外推（`08_...:3,31`；`metrics.py:17`）。

**反例**：删基准快照 → `REJECTED` 且指针不动；fingerprint 一致 → `SKIPPED_FRESH` 且 `full_build`/`delta_apply` 零调用；DELTA 后 `community.json` sha256 必须变且不含已删 file_id；两库并发不串库。

**验收**：C-1~C-5、D-2、E-2/E-3、§3 检索等价性门禁。**结论：要求 3 已被设计覆盖，且明确利用了 HippoRAG 的 OpenIE 复用/文本差集/快照 CAS/fence 能力；但必须接受 §3-C7 的 delta 适用范围收窄（先只用于新增文件）。**

---

## 3. 待裁定项（未裁定不得开工）

| ID | 冲突 | 双方出处 | 需要谁的结论 |
|---|---|---|---|
| C1 | **「不直接改 doc2md 源码」** vs 本方案必须新增 `scan-diff`、实现两个 placeholder、改 MinerU 产 IR | `HYBRID-RETRIEVAL-DISPATCH.md:25-38` ↔ `03-IMPLEMENTATION.md` P1 | Owner 显式解除该边界，或指定由 doc2md 上游团队实施并给出交付契约 |
| C2 | **「首个切片不先做图引擎」** vs 本方案要求图谱增量 | `IMPLEMENTATION-QUEUE-V2.md:388-400` ↔ Owner 要求 3 | Owner 重排实施队列；本包建议登记为新切片 `VL-DOC2MD-INC` |
| C3 | **「不做范围：不重跑 doc2md 解析」** vs 「doc2md 成为唯一解析者」 | `HYBRID-RETRIEVAL-DISPATCH.md:3-7` ↔ Owner 要求 1 | Owner 确认是取代旧派工单，还是并行两套（并行会违反唯一解析者） |
| C4 | ES 去留口径矛盾 | `11_...:53`「ES 保留（选型已定）」/ HR-08 ↔ `00_READ_ME_FIRST.md:10`「目标部署不强制 ES」/ VL6-04 | 评审确认本方案「保留 ES」符合当前权威版本；若按 DP 优先需重列 |
| C5 | pk 全变是否允许影子双写 + 别名切换 | `projection.py:119-127` vs `server/utils.py:103-122` 的 `seq` 差异；`reranker_service.py:41-63` | 架构评审批准迁移窗口、旧索引保留期、切换期读写一致性方案 |
| C6 | 表格通道未补齐前 `snapshot` 不得切换 | `IMPLEMENTATION-QUEUE-V2.md:105-106`、`docs/NEXT.md:400-410` | 确认 P1-5 为硬前置，任何库不得提前切读 |
| C7 | 增量检索排序漂移未查清 | `docs/NEXT.md:442-458,586-592`（top1 0.667 / ordered 0.5 / jaccard 0.75，3 条 DIFF） | 批准「DELTA 先只用于新增文件，修改/删除走 FULL」，或要求先查清漂移再放量 |
| C8 | 契约登记权限与方式 | `IMPLEMENTATION-QUEUE-V2.md:414`（registry/TRACE 仅合同变更任务可改）；`contracts/README.md:11`「合同通过不代表已实现」 | 批准 P0 只交附录、P7 才登记，还是要求先登记再实施 |
| C9 | 容量目标与实测冲突 | `08_...:14-15`（10 万块 ≤ 8h）↔ `STAGE5.md:86`（kb_9 4566 doc 约 3.5h）、`RECOVERY…:31`（kb_1004 约 3h18m） | 业务方重新确认目标值；压测按 `08_...:40-52` 补做 |
| C10 | 独立 QA 不得自签 | `HYBRID-RETRIEVAL-DISPATCH.md:63-68`；`IMPLEMENTATION-QUEUE-V2.md:218,384` | 指定独立 principal 与公钥；TL 不代签 |
| C11 | 双仓配置漂移的治理责任 | 运行仓无 `v2-ingest` 段、v2 仓有；`.bak-20261102` 指向 19529/19532 | TL 确认「两仓关键键机器比对」纳入 P5 门禁 |
| C12 | **12340 三类辅助接口的 doc2md 承接** | `application-r12.yml:140-147`：`file-revise_date`/`file-multi-version`/`tl-database-table-description` 均绑 12340；doc2md 无 `database_desc` 能力 | Owner 裁定 `database_desc` 是否在「抛弃 12340」范围内；若否，保留 12340 只读子集（承接清单见 `00-DESIGN.md` §5.3） |

---

## 4. 给独立架构评审的检查题（可证伪）

1. `apply_delta` 接受的是「新增文件 docs」还是「全库 wanted texts」？如果方案写成前者，会删掉什么？（`rebuild.py:200-202`）
2. DELTA 快照里的 `community.json` 若沿用 copytree 带来的旧文件，`/v2/graph/global` 会返回什么？如何机器检测？（`global_report.py:218-271`）
3. 为什么 `sources.json` 必须在 DELTA 后重算，且必须在 `global_report.write` 之前？（`api.py:223-238`、`:404-413`）
4. 本方案说「利用 HippoRAG GraphRAG 特性」，具体复用了哪三个 SDK 行为？为什么不能说「增量图更新」？（`engine_hipporag.py:82-84`）
5. `check_freshness` 能不能当权限用？（`rebuild.py:66-68`）本方案把它放在哪一层？
6. 换解析器后 pk 为什么必然变？如果新旧 pk 同库混写会破坏什么？（`reranker_service.py:41-63`）
7. `duplicate_flag=True` 为什么不适合文件级增量？（`es.py:476-484`、`milvus_kb_service.py:683-700`）
8. Milvus 会静默丢 `content_hash`，那么同源校验应该放在哪？（`milvus_kb_service.py:538-540`）
9. 为什么 `kb_state.json` 损坏不能返回 `{}`？（`kb_pipeline.py:178-185`、RECOVERY 证据）
10. 无基准快照时 `rebuild_delta` 的行为是什么？本方案如何做到「不静默降级」又可恢复？（`rebuild.py:204-211,263-266`）
11. `fencing=1` 固定会让哪个保护失效？本方案怎么改？（`api.py:219`、`rebuild.py:167-172`）
12. 单份全局 `state` 在多库并发下会产生哪两类串库？（`api.py:305-331,382-385`）
13. 删除文档为什么要先 revoke 再 delta？（`fence.py:1-13,120-132`）
14. `TaskReq` 沿用的两个硬约束是什么？违反会怎样？（`FileParseTaskAppServiceImpl.java:302,332`）
15. 为什么 P1-5 表格通道是硬前置？（`IMPLEMENTATION-QUEUE-V2.md:105-106`）
16. 检索等价性门禁为什么是放量前必须？（`docs/NEXT.md:442-458`）
17. 现有 4.3×/8.7× 为什么不能写进生产 SLA？（`08_...:3,31`、`metrics.py:17`）
18. 本方案有没有违反 HR-09「图读完整 MD/IR 不依赖 RAG chunk」？请给出设计里的对应条款。（`00-DESIGN.md` §6.2）
19. 如果评审拒绝改 doc2md 源码（C1），本方案哪几条要求会立即失效？有没有不改动 doc2md 的替代路径？
20. 本包声称「未修改生产代码」，请核对 git 工作树与 `00-DESIGN.md` 里所有标注「待实现」的新接口是否确实不存在。

---

## 5. 与既有约束的对照矩阵（评审勾选用）

| 既有约束 | 出处 | 本方案条款 | 是否冲突 |
|---|---|---|---|
| HR-01/02 统一 pk、禁原生 ID | `llmke-hybrid-retrieval.yaml:8-16` | `00` §6.2、`02` §7 | 否（但需 C5 迁移批准） |
| HR-03/04 向量只算一次、Milvus | `:18-26` | `00` §6.3、`03` P2-1 | 否 |
| HR-05/06/07 三路并行 + RRF + rerank | `:28-41` | 检索侧不改 | 否 |
| HR-08 ES 保留 | `:43-46` | `00` §6.3 | 否（口径矛盾见 C4） |
| HR-09 图读 MD/IR、命中回指 pk | `:48-51` | `00` §6.2、§7.4 | 否 |
| HR-10 global 独立 | `:53-56` | `00` §7.4 | 否 |
| DP 系列优先于 HR | `11_...:106` | `00` §3 | 需评审确认 |
| 增量语义口径 | `EVIDENCE-DELTA-…:36-37` | `00` §7.1、§12.1 | 否，明确遵守 |
| 不静默降级 | `EVIDENCE-SCOPE-DELTA…:15-26` | `00` §7.6、`02` §5 | 否，明确遵守 |
| pickle 禁令 | `06_...:124` | `00` §12.6 | 否 |
| 能力不许假绿 | `06_...:105` | `03` P3-4 | 否 |
| 五步闭环 / 状态口径 | `IMPLEMENTATION-QUEUE-V2.md:6-15` | `03` 全程、`04` §7 | 否 |
| 不改 doc2md 源码 | `HYBRID-RETRIEVAL-DISPATCH.md:25-38` | `03` P1 | **是 → C1** |
| 不先做图引擎 | `IMPLEMENTATION-QUEUE-V2.md:388-400` | `03` P3 | **是 → C2** |
| 不重跑 doc2md 解析 | `HYBRID-RETRIEVAL-DISPATCH.md:7` | `00` §5 | **是 → C3** |
| snapshot 禁切（表格通道） | `IMPLEMENTATION-QUEUE-V2.md:105-106` | `03` P1-5 硬前置 | 否，已遵守 |
| 图根不得放 /tmp | `r12-graph-v2-start.sh:8-9` | `00` §9 | 否 |
| 独立 QA 不得自签 | `HYBRID-RETRIEVAL-DISPATCH.md:63-68` | 本文件 §6 | 否 |

---

## 6. 评审结论与签署

请独立架构评审角色按以下格式给出结论（**TL 不代签、不伪造签署身份**）：

```text
评审对象：doc2md-incremental-graphrag 设计包（README + 00~05）
复核方式：□ 证据逐条复核  □ 检查题逐题回答  □ 反例可造性核对
结论：□ 通过  □ 有条件通过（列条件）  □ 驳回（列理由）
待裁定项 C1~C11 处理意见：
对 §4 检查题 1~20 的回答（另附）：
签署 principal / 公钥：
```

**未经评审通过，本包不得进入 P1；P0 的基线冻结与契约附录提交属只读动作，可先行。**
