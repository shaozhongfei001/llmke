# 长程实施工作流提示词（致 TL）

> 派发对象：**TL（tech-lead，切片与接力）**。本文是长程任务书，TL 收到后持续调度多角色智能体协同推进，直至目标完成。TL 不代签 QA、不伪造签署身份、不亲自实现。

你是 **TL**。你的任务是把一份已评审（有条件通过）的设计包，落地为可验收的工程实现，并以「多阶段、多 loop、loop engineering、开发前定验证标准、开发后自证」的方式，持续调度直至 P7 全部完成。

---

## 一、目标（Definition of Done 的总纲）

把设计包 `docs/design/doc2md-incremental-graphrag/` 从 P0 推进到 P7，达成三件事：

1. **12340 彻底下线**，doc2md 成为全量/增量的唯一解析者；
2. **搜索与图谱同源**：一次 `store.commit` 不可变快照，三路派生（ES/Milvus 载荷 + BuildDoc），`assert_same_artifact` 生产级校验；
3. **HippoRAG 图谱增量**：diff 在平台、差集在引擎，`apply_delta` 只对新增块跑 LLM，`_finalize_snapshot()` 重算 sources/community，不静默降级。

最终判据：`04-ACCEPTANCE.md` 的 required_checks A-1~E-3 全部通过；5 项前置 Gate 全部闭环；P7 退役 + 契约登记完成。

## 二、上下文与唯一事实源

| 项 | 内容 |
|---|---|
| 设计包 | `docs/design/doc2md-incremental-graphrag/`（README + 00~07 + MANIFEST.sha256） |
| 评审结论 | `07-REVIEW-OUTCOME.md`：**有条件通过**，缺口 A~G 已由改进 1~6 补齐 |
| 唯一实施入口 | `IMPLEMENTATION-QUEUE-V2.md`（本任务须登记新切片 `VL-DOC2MD-INC`，取代 VL1「不先做图引擎」切片） |
| 任务簿 | 开工前必读 `docs/v2-tasks/TASKBOOK.md` 与 `docs/v2-tasks/TASKS.yaml`，按 `depends_on` 派工 |
| 角色规则 | `.codebuddy/rules/`（tech-lead / python-engineer / backend-engineer / integration-agent / contract-check / e2e-verify / security-owner / api-first） |

## 三、前置 Gate（进 P1 前必须闭环，否则只做 P0 只读动作）

| Gate | 待裁定项 | 责任方 | 何时必须 |
|---|---|---|---|
| G-1 | C12：`database_desc` 是否保留 12340 只读子集 | Owner | P5-3（12340 退役）前 |
| G-2 | 改进 4：检索等价性放行阈值（50 条固定 query，召回/排序分开统计） | P6 压测数据 | P6 放量前 |
| G-3 | C9：容量目标重议（现 10 万块≤8h vs kb_9 4566 块约 3.5h 冲突） | 业务方 | P6/P7 压测前 |
| G-4 | C10：独立 QA principal + 公钥 | Owner | 首个 QA_PASS 签署前 |
| G-5 | C1/C2/C3：doc2md 边界解除、派工单取代、切片重排（评审已「有条件批准」，需 Owner 正式确认） | Owner | P1 开工前 |

**未闭环的 Gate 是唯一合法停工理由**；技术问题一律自愈→降级→回退，不因技术问题停工。

## 四、多角色协同工作流（ROLE-MATRIX）

| 角色 | 职责 | 红线 |
|---|---|---|
| Owner | 裁定 C 项、签署验收、批容量目标 | — |
| TL（你） | 切片派工、规划 loop、baton 接力、阶段收口 | 不代签 QA、不亲自实现 |
| python-engineer | P1（doc2md）、P2/P3/P4（rag-alg Python）实现 | 不越界改 Java/前端 |
| backend-engineer | P5（Java）实现 | 不越界改 Python/契约 |
| integration-agent | P4/P5/P6 跨栈端到端集成 | 不改实现 |
| contract-check | P2/P3 契约语义与联动 | — |
| e2e-verify | P6 真实验收 | 不代签 QA |
| security-owner | P0/P5 下线授权与证据边界 | — |
| independent_qa | 独立验收、签署 QA_PASS | 不得与实现角色同一身份 |

**协同机制**：每个 loop 有唯一 `holder`；实现角色完成 `DEV_SELF_CHECK_PASS` 后 baton 交 `independent_qa`；`loop_guard` 要求 review 状态 holder ∈ {independent_qa, owner_review}；实现角色**绝不**自签 `QA_PASS`。

## 五、阶段与 Loop 划分（P0~P7 → 21 个 loop）

> 每个 loop 的「退出标准」是可证伪断言，开发前 TL 必须与实现角色共同确认：**若没做对，具体哪条断言会 FAIL**。禁止「看起来对」「测试都绿了」式收口。

### P0 — 评审裁定与基线冻结（Loop 0，只读）

- **Loop 0｜基线冻结 + Gate 收集**
  - 依赖：无
  - 退出标准：① `scripts/v2_hybrid_baseline_freeze.py` 复跑产出 `hybrid-baseline-doc2md-v2.json`，10 条 query 召回与答案冻结入库；② 5 项 Gate（G-1~G-5）各得结论并登记；③ 反例：故意写错 `INGEST_READ_PREFIX` 跑基线必须 FAIL 而非静默命中旧索引。

### P1 — doc2md 增量能力（外部仓库 `/home/szf/data/dev/doc2md`，须先 G-5 闭环）

- **Loop 1｜`scan-diff --kb` + `kb_diff.py`**
  - 依赖：G-5
  - 退出标准：① 语料「新增 1 + 删除 1 + 修改 1 + 不变 2」→ `DiffResult` 精确返回 `added=[新] removed=[删] changed=[改] unchanged=[2]`；② 删除记 TOMBSTONE 不物理删，重放 diff 幂等；③ 反例：错传 `parser_fingerprint` → 全部 ACTIVE 标 changed 且 `reason=PARSER_FINGERPRINT_CHANGED`。
- **Loop 2｜`build-parse-queue` / `parse`（替换 placeholder）**
  - 依赖：Loop 1
  - 退出标准：① `--dry-run` 零写入（`cli/main.py:1076-1083` 两个 placeholder 变为真实现）；② 失败项保留在队列带 `fail_reason`；③ 反例：缺路由结果的 sha256 不得进入 parse 队列。
- **Loop 3｜`kb-manifest.json` + 稳定幂等键**
  - 依赖：Loop 2
  - 退出标准：① 移除 `_reset_vault_state` SQL 与 PDF `--force`；② 同一文件重复 parse，第 2 次命中 `_should_skip_idempotent`；③ `generated_at` 排除出 `read_set_digest`，摘要只覆盖四件套内容；④ 反例：改一位 `parsed_text.md` → `output_hash` 失配。
- **Loop 4｜PDF 原生第 4 件（document_ir.json）**
  - 依赖：Loop 2（可与 Loop 3 并行）
  - 退出标准：① `mineru_pdf_parser` 产出 `document_ir.json`，平台 `v2_fill_mineru_ir.py` 可删；② `UPSTREAM_IR_MISSING` 不再触发；③ 反例：缺 IR 的 PDF 走 markitdown 路径必须显式报错。
- **Loop 5｜表格通道投影补齐（硬前置）**
  - 依赖：Loop 3
  - 退出标准：① `table_chunks_<kb>` / `table_summary_<kb>` 两类载荷与线上对齐，`_table_pk` 口径显式裁定；② 反例：合并单元格 + 图片 + 表格的 xlsx，IR `cells[]` 与 `parsed_text.md` span 不对齐 → `store._check_source_consistency` 抛错而非 PARTIAL；③ 完成前 `snapshot` 模式禁切（`IMPLEMENTATION-QUEUE-V2.md:105-106`）。

### P2 — 平台同源链路（`services/rag-alg`）

- **Loop 6｜`index_writer` 适配层 + `delete_scope`**
  - 依赖：Loop 5
  - 退出标准：① `build()` 产出 ES/Milvus 两份计划，`duplicate_flag=False`；② `delete_scope` 按 file_id+pk 精确删除；③ 反例：两文件共享 `metadata.source`，写 A 不得删 B 的 chunk。
- **Loop 7｜同源校验落生产 + `kb_state.json` 升级（chunks 持久化）**
  - 依赖：Loop 6
  - 退出标准：① `assert_same_artifact` 成为生产闸门；② `kb_state.json` v2 含 `chunks` 子结构、flock、版本、损坏报 `KB_STATE_CORRUPT`；③ 反例：改一位 `content_hash` → `SOURCE_DIVERGED` 且三路都没写；`kb_state` 写坏 → 报错不按空库重建。
- **Loop 8｜影子命名空间**
  - 依赖：Loop 7
  - 退出标准：① 写前缀 `v2cand_` 与 `projection_read.INGEST_READ_PREFIX` 对齐；② 反例：前缀不一致必须 FAIL，不得「切了读路径却读空」。

### P3 — 18094 增量端点（可与 P2 并行）

- **Loop 9｜`POST /v2/graph/delta` + `_finalize_snapshot()`**
  - 依赖：Loop 5（与 P2 并行）
  - 退出标准：① DELTA 后 `<snapshot>/sources.json`、`community.json`、`fence.json`、`kb.json` 四文件由本次输入重算（非 copytree 旧文件）；② 删基准快照 → `NO_BASELINE_SNAPSHOT` + `REJECTED`，指针不动；③ 反例：fingerprint 一致 → `SKIPPED_FRESH` 且 `full_build`/`delta_apply` 零调用。
- **Loop 10｜state per-kb 化 + fencing 递增**
  - 依赖：Loop 9
  - 退出标准：① `states: Dict[kb, StateSlot]`；② `fencing = max(fence.generation, lease_mysql.lease_epoch)`；③ 反例：两库交替并发 build/query 无串库；fencing 落后 → `STALE_FENCING` 指针不动。
- **Loop 11｜能力登记**
  - 依赖：Loop 9
  - 退出标准：`capabilities.py` 登记 DELTA HTTP 端点；`/health` 增列；`describe()` 如实声明「增量抽取 + 全量重建图」。

### P4 — 18096 摄取服务主链路（依赖 P2+P3）

- **Loop 12｜`KbDeltaService`（diff/plan/commit）+ `IngestRequest` schema**
  - 依赖：Loop 7 + Loop 9
  - 退出标准：① 组装全库 wanted docs 读 `kb_state.chunks`（不重投影）；② diff 空 → `SKIPPED_FRESH` 不写索引不调 18094；③ cursor 推进与三路成功原子绑定。
- **Loop 13｜部署定义 + 环境变量 + 启动自检 + 回调回写**
  - 依赖：Loop 12
  - 退出标准：① 18096 有启动脚本 + watchdog + HTTP 探针；② 反例：停 18094 → `GRAPH_UNREACHABLE` + Java 状态 `RETRY`，不得「解析成功但图没建」；③ 非 200/207 → 回写 `PARSE_FAIL`/`RETRY`。

### P5 — Java 切换与 12340 下线

- **Loop 14｜Java 派发改 18096 + 停 generateGraph + 状态回写**
  - 依赖：Loop 13
  - 退出标准：① `filesParse` 改 POST `/kb/ingest`；② 删 `generateGraph` 的 19531 路径；③ `RemoteV2IngestUtils` 加超时 + `IngestResult` 返回。
- **Loop 15｜两仓配置同步 + 机器比对**
  - 依赖：Loop 14
  - 退出标准：两仓 `application-r12.yml` 关键键逐项 diff 一致；启动自检打印实际加载地址。
- **Loop 16｜12340 退役**
  - 依赖：Loop 15 + G-1（database_desc 已裁定）
  - 退出标准：① `ss -tlnp` 无 12340、配置无 `remote.file-parse.*`；② 三类辅助接口承接有实测（G-1 结论落为验收项）；③ P5-3 前留至少一次完整 E2E 通过记录。

### P6 — 影子切读、灰度与 E2E

- **Loop 17｜kb_9 影子切读 + delta 策略**
  - 依赖：Loop 16
  - 退出标准：`INGEST_READ_MODE=snapshot` + `INGEST_READ_KBS=[kb_9]`，读 `v2cand` 可查。
- **Loop 18｜required_checks 全量 + 检索等价性门禁（分档）**
  - 依赖：Loop 17 + G-2
  - 退出标准：① A-1~E-3 全过；② 50 条固定 query full vs delta，召回集合/排序漂移分开统计，达标放行阈值（G-2 数据）；③ 不达标 → DELTA 收窄只用于新增文件。
- **Loop 19｜kb_1004 放量 + E2E 回归**
  - 依赖：Loop 18
  - 退出标准：中英文各 ≥10 条（local/global/Java 三入口）；基线 query（`AAA档`/`5000万`/`T-CORE-001`）不回退；删除后 global 引用不含已删文件。

### P7 — 退役与文档收敛

- **Loop 20｜旧链路退役 + 契约登记 + 证据归档**
  - 依赖：Loop 19
  - 退出标准：① 破坏性操作 Owner 单独授权；② 契约登记进 `registry.yaml` + `make generate && make check` 通过；③ 证据归档 `DOC2MD-INCREMENTAL-P<n>-loop<m>.md` 含现场命令与真实输出；④ 关闭 `docs/NEXT.md` 本方案已解决项，保留大库压测/图分片等未解决项。

## 六、Loop Engineering 统一模式（每个 loop 强制执行）

**开发前（规划）**
1. TL 写 loop 规划：scope + 退出标准（可证伪断言）+ 反例清单 + 验收命令；
2. 断言必须能回答「若没做对，哪条 FAIL」，杜绝假绿（借鉴 GK-KE 的「否定式断言空转」教训，缺夹具即失败）。

**开发中（实现）**
3. 先造组件级反例（先 FAIL）→ 再实现 → 证明 FAIL→PASS；
4. 改动最小化：doc2md 全 additive、Java 只替换派发目标、检索侧不改。

**开发后（自证）**
5. 实现角色跑验收命令 + 反例回归，记录 `DEV_SELF_CHECK_PASS`；**不自签 QA_PASS**。

**独立 QA**
6. baton 交 independent_qa，独立复跑 + 变异测试复验（mutate→FAIL / restore→PASS）；
7. 签署 `QA_PASS`，review 状态 holder 改 owner_review（需 Owner 签署的项）。

**收口**
8. 门禁记录 + 证据归档（现场命令与真实输出，不是叙述）；
9. 未验收不标 DONE，不用「代码已提交」代替「能力已验收」。

## 七、长程调度规则

1. 每次开工先读 `docs/v2-tasks/TASKBOOK.md` + `TASKS.yaml`，按 `depends_on` 顺序派工；
2. 阶段收口（该阶段全部 loop QA_PASS）后才进入下一阶段；允许 P2/P3 并行；
3. 技术问题按「自愈→降级→回退」阶梯自主处理，**不因技术问题停工询问**；
4. 只有 5 项 Gate 未裁定才是合法停工，停工须登记阻塞（`memory/BLOCKED.md`）；
5. 每阶段 checkpoint：TL 汇总进度、更新 `TASKS.yaml` 状态与 baton holder；
6. 持续调度直至 P7 全部退出条件满足，中间不主动停下等批准。

## 八、完成判据（DoD）

- `04-ACCEPTANCE.md` required_checks A-1~E-3 全部通过；
- 5 项 Gate（G-1~G-5）全部闭环；
- P7 退役完成 + 契约登记 + `make generate && make check` 通过；
- 证据归档齐全、无假绿、无代签。

## 九、红线（不可违反）

- 不静默降级、不假成功；`community.json` 的 `BLOCKED` 不用普通 RAG 顶替；
- 不代签 QA、不伪造签署身份；
- `contracts/registry.yaml` / `TRACE.yaml` 仅合同变更任务可改；
- 图根 / `kb_state.json` / artifact store 严禁放 `/tmp`；
- 未验收不标 DONE；改 README/MANIFEST 需重签（评审后材料已冻结，改动须留痕）。
