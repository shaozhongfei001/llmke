# BLOCKED · VL-DOC2MD-INC 长程实施停工登记（已复工，转为历史记录）

> **复工批复（2026-11-08，Owner）：「同意复工」**
> - **G-5 正式闭环**：批准 C1/C2/C3 —— 解除「不直接改 doc2md 源码」边界、取代旧派工单「不重跑 doc2md 解析」、重排 `VL-DOC2MD-INC` 切片（取代 VL1「不先做图引擎」）。
> - **口径裁决**：以落盘派工单 `docs/dispatch/DOC2MD-INCREMENTAL-LONG-RUN-DISPATCH.md` 与 `docs/v2-tasks/TASKS.yaml` 为准；Gate 时点按表内「何时必须」列，不按 §三表头的死锁字面。
> - **G-4 仍未闭环**（无独立 QA `principal_id`/`key_id`/`public_key_pem`），其时点为「首个 QA_PASS 签署前」，不阻塞开工；**TL 不代签、实现角色不自签**。Loop 1 走到 `DEV_SELF_CHECK_PASS` 后 baton 挂起等待 `independent_qa`。
> - G-1（P5-3 前）、G-2（P6 压测数据）、G-3（P6/P7 前）按各自时点闭环。
> - 复工第一个动作：P1-L1 开发前定验证标准 → 派工 `python-engineer`。
> 本文件保留为停工证据，**不再代表当前状态**；当前状态见 `TASKS.yaml` 与 `docs/v2-tasks/loops/P1-L1-PLAN.md`。

- 登记时间：2026-11-08 02:12+08:00
- 触发工作流：`docs/dispatch/DOC2MD-INCREMENTAL-LONG-RUN-DISPATCH.md`（长程实施工作流提示词，致 TL）
- 当前位置：**P0 / Loop 0 完成；P1 未开工**
- 停工依据：派工单 §三「未闭环的 Gate 是唯一合法停工理由；Gate 未闭环时只做 P0 只读动作」、§七-4「只有 5 项 Gate 未裁定才是合法停工，停工登记 memory/BLOCKED.md」；`07-REVIEW-OUTCOME.md` §九 5 项待办
- 状态：**合法停工，等待 Owner / 业务方 / QA 批复。非技术阻塞。**

---

## 一、P0（Loop 0，只读）已完成的三件事

| 退出标准 | 结果 | 证据 |
|---|---|---|
| ① 基线冻结入库 | 通过 | `docs/dispatch/evidence/hybrid-baseline-doc2md-v2.json`（7436 B，2026-11-08 02:11:59+08:00）。`schema=llmke.hybrid-retrieval-baseline.v1`、`stage=0`、`queries=17`、`es.kb_9=44`、`es.kb_1004=4520`。由 `scripts/v2_hybrid_baseline_freeze.py --out ...` 只读复跑生成，**未覆盖**旧基线 `hybrid-baseline-0.json` |
| ② 5 项 Gate 各得结论并登记 | 通过（结论均为「未闭环」） | 见本文 §二；检索证据见 §三 |
| ③ 反例：错 `INGEST_READ_PREFIX` 必须 FAIL 而非静默命中旧索引 | 通过 | `GET /__wrongprefix_kb_9/_count` → HTTP 400；`GET /v2cand_kb_9/_count` → HTTP 404（影子索引尚未建立，符合预期）。错误前缀解析出的索引在 ES 中不存在，读路径会失败而非回落旧索引 |

补充核对：设计包 `docs/design/doc2md-incremental-graphrag/` 本轮**未改动**，`sha256sum -c MANIFEST.sha256` 9 项全通过；交付包 `...-reviewed-20261108.tar.gz` 的 `79127fae…` 留痕仍有效。

---

## 二、5 项 Gate 逐项状态（全部未闭环）

| Gate | 待裁定项 | 责任方 | 派工单要求的时点 | 当前证据 | 结论 |
|---|---|---|---|---|---|
| G-1 | C12：`database_desc` 是否保留 12340 只读子集 | Owner | P5-3 前 | `07-REVIEW-OUTCOME.md` §五 C12 原文「**Owner 裁定**…若否，保留 12340 只读子集」；`application-r12.yml:140-147` 三个辅助 URL 仍绑 12340 | 未闭环 |
| G-2 | 改进 4：检索等价性放行阈值（50 条固定 query，召回集合/排序漂移分开统计） | P6 压测数据 | P6 放量前 | `04-ACCEPTANCE.md:62-71` 已改三档，但「放行阈值 P6 压测后用 50 条固定 query 实测定」；压测未开始 | 未闭环（依赖 P6 数据，按设计属阶段内闭环） |
| G-3 | C9：容量目标重议（10 万块≤8h vs kb_9 4566 块约 3.5h） | 业务方 | P6/P7 压测前 | `07` §五 C9「需业务方重议」；`08_CAPACITY_AND_PERFORMANCE.md:14-15` 目标仍是建议值 | 未闭环 |
| G-4 | C10：独立 QA principal + 公钥 | Owner | 首个 QA_PASS 签署前 | `docs/baseline/validation/QA-KEY-HANDOVER-V1.0.md` 只是「我需要的三样输入」模板（`principal_id` / `key_id` / `public_key_pem`），**未包含任何真实 principal 或公钥** | 未闭环，且不可由 TL 代签/伪造 |
| G-5 | C1/C2/C3：doc2md 边界解除、派工单取代、切片重排 | Owner | **P1 开工前** | `07` §五仅给出评审意见「批准 / 有条件批准 / 批准取代」；派工单 G-5 原文「评审已『有条件批准』，**需 Owner 正式确认**」 | 未闭环（P1 的硬门槛） |

### G-4 的连锁硬阻塞（即使 G-5 视为已确认）

派工单 §四规定：每个 loop 实现角色完成 `DEV_SELF_CHECK_PASS` 后 baton 交 `independent_qa`，由独立 QA 复跑 + 变异测试并签署 `QA_PASS`；`loop_guard` 要求 review 状态 holder ∈ {independent_qa, owner_review}；实现角色绝不自签。P1 Loop 1 收口即需要真实 principal 与公钥。**在 QA-KEY-HANDOVER 的三样输入到位前，P1 的第一个 loop 无法合法收口**，因此即便 G-5 获批，也不能凭「中间不主动停下」推进。

### 派工单内部的两处口径差异（请 Owner 一并确认）

1. §三表头写「5 项 Gate 全部闭环才能进 P1」，但表内 G-2/G-3 的时点是「P6 放量前 / P6-P7 压测前」，其依赖的压测数据只有在 P1~P5 完成后才存在。若按表头字面执行会形成死锁。本登记采用表内「何时必须」列：G-5 是 P1 门槛，G-1/G-2/G-3/G-4 在各自时点前闭环。
2. 本轮用户消息写「20 个 loop」，落盘派工单 §五标题写「21 个 loop」；`07` §九第 5 项是「MANIFEST 复核（已完成）」，而派工单 G-5 是 C1/C2/C3。`TASKS.yaml:439-625` 已登记 `VL-DOC2MD-INC` 的 `T-D2MD-00`~`T-D2MD-20`。请以落盘派工单与 `TASKS.yaml` 为准或明示修订。

---

## 三、Gate 批复证据的检索记录（避免误判）

```
# 11-08 之后新增的、文件名含 decision/approval/gate/attest/sign 的文档
find docs -newermt '2026-11-08 00:00' -type f \( -iname '*decision*' -o ... \)  → 无命中

# 内容级：G-5 已闭环 / C1-C3 Owner 正式确认 / qa_principal 公钥
grep -rnE 'G-5.{0,40}(已闭环|已批准|已确认)|C1/C2/C3.{0,30}(Owner.{0,10}批准|正式确认)|qa_principal.{0,40}BEGIN PUBLIC KEY' docs/  → 无命中
```

备注：一次粗搜曾用 `sign` 作关键词，误匹配了路径 `docs/design/`（design 含 sign），已用文件名级与内容级精确检索重做，结论不变。`docs/v2-tasks/CHECKPOINT.md` 更新时间为 2026-11-02、内容为旧 VL1 检查点，与 `VL-DOC2MD-INC` 无关，不能作为 Gate 批复依据。

---

## 四、本轮未做的事（红线自查）

- 未进入 P1；未改动 `/home/szf/data/dev/doc2md` 任何源码；
- 未改动 `services/**`、`platform/r12/conf/**`、任何运行配置或数据库；
- 未启动/停止任何服务；P0 只读脚本仅额外写出一份证据 JSON；
- 未修改 `docs/v2-tasks/TASKS.yaml` 的任务状态、未转移 baton、未写 `QA_PASS`；
- 未改 `README.md` / `MANIFEST.sha256` / 设计包内任何文件；
- 未改 `contracts/registry.yaml` / `TRACE.yaml`；
- 未代签、未伪造任何签署身份。

---

## 五、复工条件与复工后第一个动作

复工需同时满足：

1. **G-5**：Owner 对 C1/C2/C3（doc2md 边界解除、派工单取代、`VL-DOC2MD-INC` 切片重排）给出正式确认，并明确本轮消息是否已构成该确认；
2. **G-4**：QA 一方按 `QA-KEY-HANDOVER-V1.0.md` 提供 `principal_id` / `key_id` / `public_key_pem`（私钥留在工作区外），使 `independent_qa` 可合法签署首个 `QA_PASS`；
3. 确认 §二「两处口径差异」采用哪一版。

G-1 / G-3 可按派工单在 P5-3 / P6 前再闭环；G-2 由 P6 压测数据产出。

复工后第一个动作：**Loop 1 开发前定验证标准** —— 与 `python-engineer` 共同确认三条可证伪断言（语料「新增1+删除1+修改1+不变2」的 DiffResult 精确分集、TOMBSTONE 重放幂等、错 `parser_fingerprint` → 全 ACTIVE 标 changed），先造反例使其 FAIL，再实现转 PASS；随后按 §四 baton 交 `independent_qa`。

---

登记人：TL（切片与接力）。本文件仅记录停工状态，**不代替 Owner 裁定、不代替 QA 签署**。
