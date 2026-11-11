# 07 · 评审后材料合集（评审结论 + 改进落点 + 遗留待办）

> 状态：**评审已完成（独立评审智能体证据级复核），结论＝有条件通过**。本文件是评审产出的唯一入口，汇总结论、证据复核、改进方案落点与遗留待办，供 Owner 裁定与 TL 进入 P1 前对照。

---

## 一、导读提示词（可整段复制转交 Owner / TL / 独立 QA）

```text
你是本方案的复核人（Owner / TL / 独立 QA），不是实现方。请按以下顺序阅读并给出裁定：

1. 先读 00-DESIGN.md §12「明确不宣称的事」与 05-REVIEW.md §3「待裁定项」，确认本方案
   没有越界宣称、且 C1~C12 是否都已给出结论（其中 C12 是本评审新增项，见本文件 §六）。

2. 再读本文件（07-REVIEW-OUTCOME.md）：
   - §二 总体结论与放行条件；
   - §四 三条 Owner 要求的逐条结论；
   - §六 评审发现的 7 个缺口（A~G）与 2 处表述瑕疵；
   - §七 评审补充的 5 条组件级反例；
   - §八 改进方案 6 项及其落点映射；
   - §九 遗留待办（哪些项必须你裁定后才能进 P1）。

3. 裁定前请自证两条红线：
   - 「未开工」声明是否属实（git 工作树 services/platform/contracts 无改动；新增接口
     scan-diff、/v2/graph/delta、index_writer.py/kb_delta.py/delta_build.py 均不存在）；
   - 改进是否已落入 00-DESIGN.md / 02-CONTRACTS.md / 04-ACCEPTANCE.md / 05-REVIEW.md
     的对应章节（见 §八落点表）。

4. 你的裁定出口：对 C1~C12 逐项给出「批准 / 有条件批准 / 驳回 / 需补充材料」，
   并由持私钥的独立 principal 签署；TL 不得代签、不得伪造签署身份。

禁止事项：不得把「设计已写」当「能力已验收」；不得用合理推测补齐找不到的证据；
不得接受静默降级或把 community.json 的 BLOCKED 用普通 RAG 顶替。
```

---

## 二、总体结论

**有条件通过**（条件见 §八改进方案 + §九遗留待办）。

- 方案的工程判断扎实、诚实边界清晰（明确不宣称「增量图更新」、不外推性能、不宣称检索等价、不宣称端到端可复现）。
- 证据链几乎全部可核验：抽查 20+ 处 L1/L2/L3 源码行号，**全部属实**。
- **但有 7 个实质性缺口必须补齐后才能进 P1**，其中 3 个（A/B/C）集中在「全库 wanted docs 组装」这一环节（本方案最薄弱处），1 个（G）直接威胁要求 1 的可行性。

## 三、证据复核结果

| 核验证据 | 出处 | 结果 |
|---|---|---|
| HippoRAG 2.0.0a4 | `METADATA` | ✅ `Version: 2.0.0a4` |
| 「增量抽取 + 全量重建图」 | `engine_hipporag.py:82-84` | ✅ 逐字一致 |
| `apply_delta` 文本差集 | `engine_hipporag.py:76-101` | ✅ 一致 |
| `rebuild_delta` 无基准拒绝 / copytree / 传全量 | `rebuild.py:204-211 / 221 / 200-202` | ✅ 一致 |
| `rebuild_by_policy` 不静默降级 | `rebuild.py:256-281` | ✅ 一致 |
| `api.py` 8 端点无 delta | grep `@app.` | ✅ 一致 |
| `_chunk_pk` 种子 | `projection.py:119-127` | ✅ 一致 |
| `assert_same_artifact` | `artifact_binding.py:179-199` | ✅ 一致 |
| `kb_ingest_service.py:216-218` pop payloads | 同左 | ✅ 一致 |
| `kb_state` 静默 `{}`/固定 `.tmp`/无锁 | `kb_pipeline.py:174-193` | ✅ 一致 |
| 派发 12340 / v2-ingest 空 / 三类辅助接口 | `application-r12.yml:83-86,108-109,140-147` | ✅ 一致 |
| RRF by pk | `reranker_service.py:41-63` | ✅ 一致 |
| Milvus 静默丢字段 | `milvus_kb_service.py:538-540` | ✅ 一致 |
| doc2md 两 placeholder | `cli/main.py:1076-1083` | ✅ 一致 |
| `doc2mdDir` 无赋值点 | grep `setDoc2mdDir` | ✅ 成立 |
| 未开工 | git 工作树 + 新增接口不存在 | ✅ 属实 |

**2 处表述瑕疵（已改，不推翻结论）**：
1. 「doSuccess 无条件建图」→ 实际有 `isGraphParse` 勾选位（已改 `00-DESIGN.md` §2.3）。
2. 「api.py 单份 state 无 per-kb 隔离」→ 已有 `engine_for_kb` + `snapshot_kb` 雏形（已改 `00-DESIGN.md` §7.6）。

## 四、三条 Owner 要求逐条结论

| 要求 | 结论 | 关键依据 / 阻塞 |
|---|---|---|
| 1 抛弃 12340 | 有条件通过 | 派发链路证据充分；**阻塞＝缺口 G（database_desc 无 doc2md 承接）**，需 C12 裁定 |
| 2 doc2md 主解析者 + 同源 | 有条件通过 | 同源校验/三路派生设计正确；**阻塞＝缺口 A/B/C（全库 wanted docs 组装）** |
| 3 HippoRAG 图谱增量 | 有条件通过 | 框架定位准确、`_finalize_snapshot()` 抓住 copytree 陷阱；**阻塞＝缺口 E（门禁阈值与框架事实冲突，已改分档）** |

## 五、C1~C12 处理意见

| ID | 处理意见 |
|---|---|
| C1 | 批准解除「不改 doc2md」边界（改动全部 additive + 同步平台白名单） |
| C2 | 有条件批准重排队列，登记新切片 `VL-DOC2MD-INC`（取代而非并行） |
| C3 | 批准取代旧派工单「不重跑 doc2md」；禁止并行两套 |
| C4 | 批准保留 ES（对齐 `11_...:53`/HR-08 权威版本） |
| C5 | 有条件批准影子切换（需先补缺口 A/C 的 pk 稳定持久化） |
| C6 | 批准 P1-5 表格通道为硬前置 |
| C7 | 批准收窄：DELTA 先只用于新增文件；同步修门禁阈值（缺口 E） |
| C8 | 批准 P0 只交附录、P7 登记 |
| C9 | 需业务方重议容量目标（4566 doc≈3.5h vs 目标 10 万块≤8h） |
| C10 | 批准，独立 principal 不代签 |
| C11 | 批准两仓机器比对纳入 P5 门禁 |
| C12 | **本评审新增**：Owner 裁定 `database_desc` 是否在「抛弃 12340」范围内；若否，保留 12340 只读子集 |

## 六、评审发现的缺口（7 个）与表述瑕疵（2 处）

| 编号 | 缺口 | 严重度 | 落点改进 |
|---|---|---|---|
| A | 全库 wanted docs「不重解析投影」无落地方案（kb_state 不存 chunk 文本） | 高 | 改进 1 |
| B | 单文件 content_hash 与全库 wanted docs 的同源校验口径混淆 | 高 | 改进 2 |
| C | 重新投影导致 `seq` 重排、pk 漂移，违背 HR-01 | 高 | 改进 1 |
| D | `DeltaRequest.docs` 一行一个 file_id，无法表达「同文异源 1:N」 | 中 | 改进 3 |
| E | 检索等价性「jaccard=1.0」硬门禁与图全量重建事实冲突 | 中 | 改进 4 |
| F | fencing 递增租约来源未绑定 | 中 | 改进 5 |
| G | `database_desc` 无 doc2md 承接，威胁要求 1「彻底」 | 高 | 改进 6 + C12 |

## 七、评审补充的组件级反例（5 条）

1. **同文异源删除**：两文件含完全相同的 chunk 文本，删除其一 → 若 docs 按 text 去重，`sources.json` 的 1:N 映射丢失但块仍在，`citation_check` 可能误判。预期：sources 保留 1:N，仅剔除被删 file_id 一支。
2. **全库 wanted docs 组装时 pk 漂移**：新增 1 文件后重投影全库，若投影顺序非确定，旧文件 `seq` 重排 → `sources.json` 的 pk 指向错误 chunk。预期：pk 持久化而非重投影。
3. **cursor 与 18094 双写不同步**：平台 diff 后推进 cursor，但 18094 DELTA 失败 → 重放被 `CURSOR_CONFLICT`/`SKIPPED_FRESH` 短路，丢失增量。预期：cursor 推进与三路成功原子绑定。
4. **Milvus 成功 ES 失败**：`index_writer.apply` 先 ES 后 Milvus，ES 失败时 Milvus 已写 → 无跨库事务。预期：补偿任务幂等 + 可重放 + 可观测。
5. **删除文件表格块残留**：删除走 fence revoke + delta 清图，但 `delete_scope` 若未覆盖 table channel，`table_chunks_<kb>` 残留于搜索路。预期：delete_scope 同时覆盖 text + table 两 channel。

## 八、改进方案 6 项及落点映射

| 改进 | 内容 | 落点 |
|---|---|---|
| 1 | 持久化投影结果（kb_state.chunks），替代重投影全库 | `00-DESIGN.md` §7.5.1、`02-CONTRACTS.md` §4.2 |
| 2 | 拆清两层同源校验（单文件层 vs 全库层） | `00-DESIGN.md` §6.4、`02-CONTRACTS.md` §8 |
| 3 | `DeltaRequest.docs` 的 file_ids 数组支持 1:N | `02-CONTRACTS.md` §2.1 |
| 4 | 检索等价性门禁改「分档阈值」 | `04-ACCEPTANCE.md` §3 |
| 5 | fencing 递增绑定 `max(fence.generation, lease_mysql.lease_epoch)` | `00-DESIGN.md` §7.6、`02-CONTRACTS.md` §2.3 |
| 6 | 12340 三类辅助接口承接清单 | `00-DESIGN.md` §5.3、`05-REVIEW.md` §3-C12 |

**评审优化建议落点**（对文档本身的修正）：
- 措辞修正 1（无条件建图）→ `00-DESIGN.md` §2.3
- 措辞修正 2（单份 state）→ `00-DESIGN.md` §7.6
- 门禁阈值与诚实边界互相引用 → `04-ACCEPTANCE.md` §3 ↔ `00-DESIGN.md` §12.4
- 新增 C12 → `05-REVIEW.md` §3

## 九、遗留待办（进 P1 前必须闭环）

| 序号 | 待办 | 责任方 | 阻塞点 |
|---|---|---|---|
| 1 | C12：`database_desc` 承接裁定 | Owner | 要求 1 能否「彻底」 |
| 2 | 改进 4：检索等价性放行阈值 | P6 压测数据 | DELTA 放量 |
| 3 | C9：容量目标重议 | 业务方 | 性能 SLA |
| 4 | C10：独立 QA principal + 公钥 | Owner | 正式签署 |
| 5 | 评审优化建议的措辞修正已落地，需复核 `MANIFEST.sha256` | 评审 | 已完成（见下） |

---

**完整性校验**：本目录所有文件（含本文件）已纳入 `MANIFEST.sha256`，复核命令：
```bash
cd docs/design/doc2md-incremental-graphrag && sha256sum -c MANIFEST.sha256
```
