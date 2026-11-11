
# P2-L7 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-07`（`docs/v2-tasks/TASKS.yaml`）
- 阶段 P2 平台同源链路，Loop 7 `同源校验落生产 + kb_state.json v2 chunks 持久化`
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton（QA 签署策略见 `CHECKPOINT` §四 / §九）
- 依赖：`T-D2MD-06`（L6，`index_writer` 已内部收口）
- 编写人：TL（规划，不亲自实现）
- 状态：**标准已锁定，已派工；R-0 前置核实未完成前不得写实现代码**

> 依据：`03-IMPLEMENTATION.md` §P2-2（`:183-185`）、§P2-3（`:187-194`）、组件级反例（`:200-205`）；`02-CONTRACTS.md` §4.2；`04-ACCEPTANCE.md` B-1 / B-4。

---

## 一、Scope

| 允许 | 路径 | 约束 |
|---|---|---|
| 改 | `ingest_pipeline/kb_pipeline.py` | `consume_for_kb` 内接 `index_writer.build` + `assert_same_artifact` 生产闸门；`_kb_state_path` / `_load_kb_state` / `_save_kb_state` 升级到 v2；**不改** `build_index_payloads` 的 L5 语义 |
| 改 | `ingest_pipeline/index_writer.py` | 仅在需要时 additive（如暴露 `file_id` 注入参数）；不得改 L6 已验收的 body 形状 / `duplicate_flag` / `delete_scope` 语义 |
| 新增 | 平台侧测试与 fixtures（路径回报 TL） | 反例先 FAIL 再 PASS |

| 禁止 | 理由 |
|---|---|
| 写线上 ES(19527) / Milvus(19526) / DB / 18094 图快照 | 在线检索服务运行中；本 loop 用 mock 端点验证「不一致时三路都没写」 |
| 启停服务、切 `INGEST_PROJECTION_MODE`、切读 | 硬前置仍保持 legacy |
| 改 `_table_pk` / `table_summary_id` / `summary.py` / `projection.py` / `enrich.py` | L1~L6 已收口，禁改区延续 |
| 改 `artifact_binding.py` 的校验算法 | 设计包 `:183` 明令「不改算法，只加调用点」 |
| 改设计包 / `MANIFEST.sha256` / `TASKS.yaml` / 运行态配置 / doc2md 仓代码 | 越界 |
| 触碰 P3（18094 delta 端点） / P4 / P5+ | 后续切片 |

**解释器口径**（延续 L5/L6）：v2 主口径 `/home/szf/data/dev/llmke-v2-toolenv/bin/python`（3.10.12 / pytest 8.3.5）；交叉 `hipporag-toolenv`（3.11.15 / pytest 9.2.0）。evidence 每处标注绝对路径、版本与用途。

---

## 二、R-0 前置核实（**未回 TL 确认前不得写实现代码**）

L7 首次改 `consume_for_kb` 主流程与状态文件，风险高于 L6。请先只读核对并回 TL：

1. `consume_for_kb` 的**实际调用方**（18096 摄取服务已关闭；确认是否还有其它入口，避免改动影响在线链路）。
2. `kb_state.json` 当前路径（`store_root` 从哪来）、现有 schema 与内容样本、`LLMKE_KB_STATE` 是否已设置；`platform/r12/data/kb-state/` 是否存在。
3. `02-CONTRACTS.md` §4.2 的 `llmke.kb-state/2` 字段清单，与现有 `_load/_save` 的差异。
4. `assert_same_artifact`（`artifact_binding.py:179-199`）的入参形状与现有调用点，确认「只加调用点、不改算法」的接入位置。
5. 给出「v2 状态文件落盘位置 + 迁移策略（旧 v1 文件如何处理）」的建议。

**TL 确认后才写实现**；不得自行决定落盘路径或静默迁移。

---

## 三、可证伪断言（退出标准）

### G1 · `consume_for_kb` 接 `index_writer.build` 且 `file_id` 必须真实

```
期望：consume_for_kb 内调用 index_writer.build(chunks, artifact, kb=kb, file_id=<真实 file_id>)；
      file_id 不得回落为 kb（L6 判断①已标注该隐患）；
      反例：artifact/file 上下文缺真实 file_id 时 fail-closed 抛明确错误，而不是静默用 kb。
```

**FAIL 条件**：未接 `build`、或 `file_id` 仍回落 `kb`、或缺 file_id 时静默继续。

### G2 · `assert_same_artifact` 成生产闸门，且不一致时三路都不写

```
构造 ES 载荷 content_hash 改一位（或 Milvus / graph 侧改一位）
期望：抛 SOURCE_DIVERGED（ArtifactBindingError）；
      且 ES / Milvus / 图 三路均未收到写入调用（mock 计数为 0）；
      禁止「先写后校验」。
```

**依据**：`03-IMPLEMENTATION.md:203`。**FAIL 条件**：未抛错、或任一路已写入。

### G3 · `kb_state.json` v2 持久化与损坏保护

```
期望：路径由 LLMKE_KB_STATE 指定（默认 platform/r12/data/kb-state/kb_state.json）；
      schema = llmke.kb-state/2，含 version / cursor / set_digest / graph（chunks 按 file_id+pk）；
      写入用 flock + pid/uuid 临时文件 + os.replace 原子替换；
      文件损坏 → 抛 KB_STATE_CORRUPT，禁止静默返回 {}；
      并发两个写者 → 串行化，不丢更新。
```

**依据**：`03-IMPLEMENTATION.md:191-193,205`。**FAIL 条件**：路径仍指向临时目录、schema 非 v2、损坏被吞成空态、并发丢写。

### G4 · `consume_for_kb` 不再遍历全库重建图谱

```
期望：返回「本次文件的 chunks + 全量 wanted docs 的引用」；
      不再调用 post_graph_build / 全库 docs 重建；重建交给 P3/P4。
```

**依据**：`:194`。**FAIL 条件**：仍触发全库建图。

### G5 · 不写线上 / 行为等价性说明

```
期望：L1~L6 既有测试全 PASS（doc2md 侧不受影响；平台 projection/table/index_writer 回归）；
      consume_for_kb 的改动有 diff 全文 + 「与改动前行为差异」说明；
      INGEST_PROJECTION_MODE 仍 legacy、八端口 pid/fd 前后一致、线上 _count 不变。
```

### 组件级反例清单（先 FAIL，再实现转 PASS）

| # | 反例 | 期望 |
|---|---|---|
| R-1 | `build` 未接或 `file_id` 回落 `kb` | G1 FAIL |
| R-2 | `content_hash` 改一位仍继续写 | `SOURCE_DIVERGED` + 三路 0 写入（G2） |
| R-3 | `kb_state.json` 写坏 | `KB_STATE_CORRUPT`，不得按空库重建（G3） |
| R-4 | 两个写者并发 | 串行化、无丢更新（G3） |
| R-5 | `consume_for_kb` 仍全库建图 | G4 FAIL |
| R-6 | 回归 | 平台既有 `test_rag_projection` 13 + `test_table_projection` 7 + `test_index_writer` 11 全 PASS |

---

## 四、验收命令（`DEV_SELF_CHECK_PASS` 最小证据集）

```bash
cd /home/szf/data/dev/llmke-v2
V2=/home/szf/data/dev/llmke-v2-toolenv/bin/python
HIP=/home/szf/data/dev/hipporag-toolenv/bin/python
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest <新测试> -q
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest \
  tests/test_rag_projection.py .../test_table_projection.py .../test_index_writer.py -q   # R-6
PYTHONPATH=services/rag-alg/index_data_service $HIP -m pytest <新测试 + 回归> -q           # 交叉
printenv INGEST_PROJECTION_MODE ; printenv LLMKE_KB_STATE
curl -s http://127.0.0.1:19200/table_chunks_kb_9/_count
ss -tlnp | grep -E ':(19526|19527|19531|19995|19200|18094|18082|18083)\b'
git -C /home/szf/data/dev/llmke-v2 status --short
git -C /home/szf/data/dev/doc2md status --short
```

证据写入 `docs/v2-tasks/evidence/P2-L7-<timestamp>.log`：含 R-0 核实结果、`consume_for_kb` / kb_state 改动 diff 全文、行为差异说明、反例 FAIL→PASS、端口与 `_count` 前后对比、解释器标注。

---

## 五、Baton 与收口

```text
python-engineer → R-0 只读核实 → 回 TL 确认 → 反例 FAIL → 实现 → PASS
  → DEV_SELF_CHECK_PASS → TL 复核 → 可派工 P2-L8（影子命名空间）
  → QA_PASS 仍由 independent_qa 在 G-4 闭环后统一补签
```

**实现角色只记录 `DEV_SELF_CHECK_PASS`，不自签 `QA_PASS`、不标 `DONE` / `VERIFIED`。**

---

## 六、回滚

恢复 `kb_pipeline.py` / `index_writer.py`，删除新增测试与 fixtures；`kb_state.json` v2 文件若已生成，回滚时保留旧 v1 文件不动。本 loop 不写线上存储、不启停服务，回滚不影响在线检索与 L1~L6 产物。

---

## 七、依赖

`T-D2MD-08`（P2-L8 影子命名空间）依赖本 loop 的状态文件与闸门。`T-D2MD-09`（P3 18094 delta 端点）可与 P2 并行，但需本 loop 的 `wanted docs` 引用格式先定。
