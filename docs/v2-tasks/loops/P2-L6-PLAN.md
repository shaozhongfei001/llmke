
# P2-L6 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-06`（`docs/v2-tasks/TASKS.yaml`）
- 阶段 **P2 平台同源链路**，Loop 6 `index_writer 适配层 + delete_scope`
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton（QA 签署策略见 `CHECKPOINT` §四 / §九）
- 依赖：`T-D2MD-05`（L5）已内部收口；P1 阶段 L1~L5 全部完成
- 编写人：TL（规划，不亲自实现）
- 状态：**标准已锁定，已派工**

> 任何实现代码写入之前锁定断言。实现角色若认为断言不可达，先回 TL 修订本文件，不得自行放宽。
> 依据：`03-IMPLEMENTATION.md` §P2-1（`:141-165`）、`04-ACCEPTANCE.md` B-1、`ACCEPTANCE-BASELINE.yaml:28`。

---

## 一、Scope

| 允许 | 路径 | 约束 |
|---|---|---|
| **新增** | `services/rag-alg/index_data_service/ingest_pipeline/index_writer.py` | 实现 `build(chunks, artifact, *, kb, index_prefix="v2cand_") -> IndexWritePlan`、`delete_scope(*, kb, file_id, index_prefix)`、`apply(plan, *, es_url, milvus_url) -> IndexWriteResult`；复用既有 `enrich.build_payload`，不重新实现投影/摘要/主键 |
| 新增 | 平台侧测试与 fixtures（路径回报 TL） | 反例先 FAIL 再 PASS |
| 只读 | 19527 `InsertFulltextDocumentsView`（`view/api/insert_fulltext_documents_view.py:13-15` / `base.py:39-62`）、19526 `insert_vector_documents_custom_view.py:13-15` / `base.py:58-65` | 核对写入端点契约，**不调用线上写入** |

**本 loop 只产出「写入计划」与 mock 端点测试，不接生产调用点、不写任何线上存储。** 生产调用点（`consume_for_kb` 内接 `build` + `assert_same_artifact`）属 `T-D2MD-07`（P2-2），不在本 loop。

| 禁止 | 理由 |
|---|---|
| 写线上 ES（19527）/ Milvus（19526）/ DB / 18094 图快照 | 在线检索服务正在运行；本 loop 只做离线计划与 mock |
| 用线上索引名（`<kb>` / `table_chunks_<kb>`）作为 `index_prefix` | 默认 `v2cand_`，计划只指向候选命名空间，避免误写线上 |
| 复用 `duplicate_flag=True` 的按 source 全量替换 | 设计包 `:158-160` 明令禁止：会剪掉同 source 的其它文件 |
| `apply()` 只 log 不返回失败侧 | `ACCEPTANCE-BASELINE.yaml:28`「不静默降级」 |
| 改 `kb_pipeline.py` / `projection.py` / `enrich.py` / `summary.py` 的既有语义、改 `_table_pk` / `table_summary_id` | L1~L5 已收口，禁改区延续 |
| 切 `INGEST_PROJECTION_MODE`、切读、启停任何服务 | 硬前置仍保持 legacy |
| 改设计包 / `MANIFEST.sha256` / `TASKS.yaml` / 运行态配置 / doc2md 仓代码 | 越界 |

**解释器口径**（延续 L5 裁定）：v2 主口径 `/home/szf/data/dev/llmke-v2-toolenv/bin/python`（3.10.12 / pytest 8.3.5）；交叉 `hipporag-toolenv`（3.11.15 / pytest 9.2.0）。evidence 每处标注绝对路径、版本与用途。

---

## 二、可证伪断言（退出标准）

### F1 · `build()` 按 channel 分组产出两份计划

```
给定 text + table 混合 chunks 与一个 store.commit() 快照 artifact
build() → IndexWritePlan 含 es_plan / milvus_plan 两份：
  text  → <prefix><kb>；table → <prefix>table_chunks_<kb>
  两份 document_list 由 enrich.build_payload 生成 metadata 后剥掉顶层 pk / _fill
  ES 计划字段：{index_name, document_list, type:"", duplicate_flag:False}
  Milvus 计划字段：{db_name, collection_name, model_name:"bge-m3",
                    document_list, consistency_level:"Bounded", duplicate_flag:False}
```

**FAIL 条件**：分组错误、字段缺失/形状不符、或 index_name 未带 `v2cand_` 前缀。

### F2 · `duplicate_flag=False` 硬约束

```
两份计划的 duplicate_flag 必须均为 False；反例：置 True 时断言 FAIL
```

**依据**：`:157`。**FAIL 条件**：任一为 True 或字段缺失。

### F3 · `content_hash` 同源可校验（B-1）

```
build() 返回同一份快照派生的 content_hash；
三路（ES 计划 / Milvus 计划 / graph docs）的 artifact_id、content_uid、content_hash 一致；
assert_same_artifact 对该三元组返回 true（本 loop 只验证可构造与一致，不接生产闸门）
```

**依据**：`04-ACCEPTANCE.md` B-1。**FAIL 条件**：任一不一致或 hash 不可复算。

### F4 · `delete_scope` 按 `file_id + pk` 精确删除

```
构造同一 source 下有 A/B 两个 file_id 的旧 chunk
delete_scope(kb, file_id=A) → 仅删除 A 的 pk；B 的 chunk 必须保留；
禁止按 source 全量替换（反例 R-3 用 duplicate_flag=True 路径必须 FAIL）
```

**依据**：`:158-160`。**FAIL 条件**：B 被误删、或退化为按 source 删除。

### F5 · `apply()` 失败带 `side`、不静默降级

```
mock ES / Milvus 端点：令任一侧失败
期望：先 ES 后 Milvus；返回 IndexWriteResult 带 side 与失败原因，供调用方登记补偿任务；
      禁止只 log 后返回成功
```

**依据**：`:162`、`ACCEPTANCE-BASELINE.yaml:28`。**本 loop 的 apply 只跑 mock，不触线上端点**。

### 组件级反例清单（先 FAIL，再实现转 PASS）

| # | 反例 | 期望 |
|---|---|---|
| R-1 | 缺 table channel 或 table 未进 `table_chunks` 计划 | F1 FAIL |
| R-2 | `duplicate_flag=True` | F2 FAIL |
| R-3 | 同 source 下 B 文件被 `delete_scope` 误删 | F4 FAIL |
| R-4 | ES 侧 mock 失败 | `IndexWriteResult.side="es"` 且非成功（F5） |
| R-5 | Milvus 侧 mock 失败 | `IndexWriteResult.side="milvus"` 且非成功（F5） |
| R-6 | 三路 `content_hash` 不一致 | F3 FAIL |
| R-7 | 回归 | 既有 `tests/test_rag_projection.py` 13 条 + `tests/test_table_projection.py` 7 条全 PASS |

---

## 三、验收命令（`DEV_SELF_CHECK_PASS` 最小证据集）

```bash
cd /home/szf/data/dev/llmke-v2
V2=/home/szf/data/dev/llmke-v2-toolenv/bin/python
HIP=/home/szf/data/dev/hipporag-toolenv/bin/python
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest <新测试> -q
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest tests/test_rag_projection.py .../test_table_projection.py -q   # R-7
PYTHONPATH=services/rag-alg/index_data_service $HIP -m pytest <新测试 + 回归> -q                                        # 交叉
printenv INGEST_PROJECTION_MODE                       # unset → legacy
curl -s http://127.0.0.1:19200/table_chunks_kb_9/_count   # 仍 2，未写线上
ss -tlnp | grep -E ':(19527|19526|19995|18094|19531|19200|18082|18083)\b'   # 开工前后 pid 对比
git -C /home/szf/data/dev/llmke-v2 status --short
git -C /home/szf/data/dev/doc2md status --short
```

证据写入 `docs/v2-tasks/evidence/P2-L6-<timestamp>.log`：现场命令 + 真实输出 + `index_writer.py` 全文 + 两仓 `git diff`、开工前后端口 pid、线上 `_count` 对比、每处解释器标注。

---

## 四、Baton 与收口

```text
python-engineer → DEV_SELF_CHECK_PASS → TL 复核（现场输出 + 两仓无越界
  + 反例 FAIL→PASS 可复现 + 未写线上 / 未启停服务）
  → 内部推进条件满足 → 可派工 P2-L7（同源校验落生产）
  → QA_PASS 仍由 independent_qa 在 G-4 闭环后统一补签
```

**实现角色只记录 `DEV_SELF_CHECK_PASS`，不自签 `QA_PASS`、不标 `DONE` / `VERIFIED`。**

---

## 五、回滚

删除新增 `index_writer.py` 与测试/fixtures 即可；本 loop 不接生产调用点、不写线上存储、不启停服务，回滚不影响在线检索与 L1~L5 产物。

---

## 六、依赖

`T-D2MD-07`（P2-2）在 `consume_for_kb` 内接 `index_writer.build` + `assert_same_artifact` 生产闸门，并做 `kb_state.json` v2 chunks 持久化；依赖本 loop。`T-D2MD-08`/`09` 等继续按 `TASKS.yaml` 依赖链推进。
