
# P1-L5 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-05`（`docs/v2-tasks/TASKS.yaml`）
- 阶段 P1 doc2md 增量能力，Loop 5 `表格通道投影补齐`（**snapshot 切读硬前置**）
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton（QA 签署策略见 `CHECKPOINT` §四 / §九）
- 依赖：`T-D2MD-03`（L3）、`T-D2MD-04`（L4，doc2md IR 第 4 件）；两者均已内部收口
- 编写人：TL（规划，不亲自实现）
- 状态：**标准已锁定，已派工；R-0 前置裁定未完成前不得写实现代码**

> 任何实现代码写入之前锁定断言。实现角色若认为断言不可达，先回 TL 修订本文件，不得自行放宽。
> 依据：`03-IMPLEMENTATION.md` §P1-5（`:114-120`）、`00-DESIGN.md:112,422`、`IMPLEMENTATION-QUEUE-V2.md:100-106`、`04-ACCEPTANCE.md` B-2 / B-4。

---

## 一、Scope

本 loop **首次改 llmke-v2 平台侧生产代码**，但只改代码、不碰运行态。

| 允许 | 路径 | 约束 |
|---|---|---|
| 改 | `services/rag-alg/index_data_service/rag_projection/projection.py`（表格通道 `:259-267`） | 产出与线上 `table_chunks_<kb>` / `table_summary_<kb>` 对齐的两类载荷；`_table_pk` 口径须经 **R-0 裁定**后方可改 |
| 改 | `services/rag-alg/index_data_service/ingest_pipeline/enrich.py`、`kb_pipeline.build_index_payloads` | 把表格载荷按既有 `build_index_payloads` 形状接出；不改正文通道行为 |
| 新增 | 平台侧测试与 fixtures（放在 `services/rag-alg/index_data_service/` 现有 tests 目录或新建，路径需回报 TL） | 反例先 FAIL 再 PASS |
| 只读 | doc2md `document_ir_schema.py:85-99`、IR 样本；12340 `alg_doc_parse_service/server/utils.py:141-148`；线上 `table_chunks_kb_9`（HTTP `_count` / `_search`） | 对照用，**不改** |

| 禁止 | 理由 |
|---|---|
| 切 `INGEST_PROJECTION_MODE`（保持 `legacy`）、改 `canary` 配置、切读任何库 | `IMPLEMENTATION-QUEUE-V2.md:105-106` 明令「表格通道未补齐前 snapshot 模式不得切换」；本 loop 是补齐能力，**不是**放量 |
| 启停 19995 / 18094 / 19531 / 18082 / 18083 / 19200 / Milvus 等任何服务 | 在线检索服务正在运行 |
| 写线上 ES `table_chunks_*` / `table_summary_*`、Milvus、DB、18094 图快照 | 本 loop 只做离线投影与单元/组件测试；线上写入留待 P6 切读 |
| 改 `parsed_text.md` 内容与 hash、`parse_manifest` 既有键语义、L1~L4 语义 | 铁律 + additive |
| 改设计包 / `MANIFEST.sha256` / `TASKS.yaml` / 运行态配置 / doc2md 仓代码 | 越界 |
| 触碰 P2 及后续（`index_writer` / `delete_scope` / 切读放量） | 后续切片 |

**解释器口径**（R-0 已确认，TL 采纳）：本 loop 是 llmke-v2 平台 Python 服务，**不得机械套用 doc2md 仓的「anaconda3 / doc2md-toolenv 双解释器」**。
- **v2 环境** = `/home/szf/data/dev/llmke-v2-toolenv/bin/python`（3.10.12 / pytest 8.3.5），官方口径见 `docs/v2-tasks/evidence/S1-artifact-binding.md:112-113`；平台 `tests/test_rag_projection.py` 在此环境 `13 passed`。
- **图 / 兼容层** = `hipporag-toolenv`（3.11.15 / pytest 9.2.0），本 loop 除非触及图侧否则不用。
- evidence 每处命令显式标注所用解释器绝对路径、版本与用途；两个仓的回归判据分别给出，不混用。

---

## 二、R-0 前置裁定（**TL 03:4x 已裁定，可进入实现阶段**）

成员 R-0 只读对照见 `docs/v2-tasks/evidence/P1-L5-20261108T033556.log`（§7 由 TL 回填）。TL 独立复算与核实：

| 线索 | 现场结论 |
|---|---|
| 线上 `table_chunks_kb_9` 2 条 | `_id` = `1137902847478273881` / `885155839145947657`；`sha1("table\|kb_9\|329\|0")[:15]` / `sha1("table\|kb_9\|333\|0")[:15]` **精确匹配** |
| 这 2 条的来源 | `_source.metadata` 带 `parse_artifact_id` / `content_uid` / `channel=table` / `parsed_text_ref=table`，`create_time=2026-11-05 18:49:39` → **V2 投影链路（历史增量上传测试）写入**，非 12340 产物 |
| `projection._table_pk` vs 12340 | 同文件 `utils.py:125-138` 的 `create_table_pk` seed 同为 `table\|index\|file_id\|ordinal`、算法同为 `sha1[:15]→int`，数值一致；**真正不同的只有 `create_table_chunk_pk`（`:141-148`）** |
| doc2md IR | `IrTable`（`document_ir_schema.py:1469-1494`）有 `table_id: str`，**无 `table_pos` 等价字段**，`cells[].row/col` / `bbox` 不能替代 → 无法重建 `table_chunk` seed |
| 既有基线 | `tests/test_rag_projection.py` **13 条**，`:161` 已断言 `table["pk"] == P._table_pk("kb_9","333",0)` |
| `table_summary_*` | 线上**无该索引**（`_cat/indices/table*` 只有 `table_chunks_kb_9 2`）；`summary.py:30-36` 用 `v2sum\|index\|file\|table_id` |

> **TL 认领一处误判**：03:31 派工单把「线上有 2 条」当作 12340 `create_table_chunk_pk` 口径的线索，并据此写成「两套 seed 冲突」。R-0 反推证明这 2 条匹配的是 `projection` 现口径，且 `create_table_pk` 与之同源。**该前提错误已更正**，不影响「须显式裁定」这道门槛本身。

### 裁定

1. **`_table_pk` 沿用 `projection.py:93-96` 现口径，一字不改**；`create_table_chunk_pk` 口径不引入。依据：线上真值精确匹配、与 12340 `create_table_pk` 数值一致、IR 无重建条件、既有测试已锁定、改口径会与线上 2 条分裂并违反 B-2/B-4。
2. **E2 判据消歧**（见 §三）：内容寻址下同一 `(kb, file_id, ordinal)` 重投影得到**相同 pk 是正确语义**（按 `_id` 幂等覆盖更新，不产生重复行），不是「值必须不同」。E2 要求的是「稳定命中 + 不同表格不撞号」。
3. **`table_summary_id` 本 loop 不纳入口径变更**，保持 `summary.py` 现有 `v2sum|...` 不动；E1 在**产出侧**仍须能产出 table_summary 载荷对象（形状按 `summary.py` 既有契约），但线上无 `table_summary_*` 真值可对齐，主键对齐记为**已知边界转后续切片 / P6 切读**。不得引入未经线上验证的隐式口径变更。

裁定后进入「反例 FAIL → 实现 → PASS」。

---

## 三、可证伪断言（退出标准）

### E1 · 两类表格载荷与线上形状对齐

```
给定含合并单元格 + 图片 + 表格的 IR fixture
执行投影 → 期望产出 table_chunks / table_summary 两类载荷；
table_chunks 字段集与线上 table_chunks_kb_9 抽样 _source.metadata 对照一致
  （真值字段：pk / chunk_doc_id / file_id / chunk_index / table_id / channel /
    parse_artifact_id / content_uid / n_rows / n_cols / parsed_text_ref，TL 03:4x 现场读取）
table_summary 载荷对象按 ingest_pipeline/summary.py 既有契约产出；
  线上无 table_summary_* 索引，主键对齐按 §二 裁定 3 记为已知边界，本 loop 不判 FAIL
```

**依据**：`03-IMPLEMENTATION.md:116`、`04-ACCEPTANCE.md` B-4。缺/多 `table_chunks` 字段均判 FAIL。

### E2 · `_table_pk` 稳定命中且不撞号（TL 03:4x 消歧）

```
口径：沿用 projection._table_pk（§二 裁定 1），不得改 seed。
期望：pk 为整数、确定性；
      同一 (kb, file_id, ordinal) 重投影 → pk 值必须相同（稳定 id 幂等命中同一行，
        按 _id 覆盖更新而非 append；这是正确语义，不是「值必须不同」）；
      必须精确等于线上既有 2 条的 pk（1137902847478273881 / 885155839145947657）；
      不同表格（不同 file_id 或不同 ordinal）→ pk 不得撞号；
      不产生重复行；三路（ES/Milvus/图）pk 形状对齐 B-2。
```

**FAIL 条件**：口径被改、`pk` 非整数 / 不稳定、与线上真值不匹配、不同表格撞号、或产生重复行。
> 「不重复」指**不产生重复行 / 不同表格不撞号**，不是「pk 值必须字面不同」。TL 03:31 初版的「与线上既有 pk 不重复、不覆盖」表述有歧义，此处更正。

### E3 · span 不对齐时 fail-closed

```
造 IR cells[] 与 parsed_text.md span 不对齐的 fixture
期望：store._check_source_consistency 抛明确错误，而不是产出 PARTIAL 后继续
```

**依据**：`03-IMPLEMENTATION.md:119`、`store.py:245-276`。**FAIL 条件**：降级为 PARTIAL 或静默产出。

### E4 · 投影确定性

```
同一 IR 连续投影两次
期望：载荷逐字节相同、seq 与 pk 稳定；正文通道输出与改动前一致
```

### E5 · 不切模式（硬前置不被绕过）

```
期望：INGEST_PROJECTION_MODE 仍为 legacy；无切读、无 canary 变更、无在线写入；
      静态与运行时均可证 snapshot 在本 loop 未被启用
```

**FAIL 条件**：任何切模式/放量动作，或未完成就宣称 snapshot 可切。

### 组件级反例清单（先 FAIL，再实现转 PASS）

| # | 反例 | 期望 |
|---|---|---|
| R-1 | 表格载荷缺 `table_summary` | E1 FAIL |
| R-2 | pk seed 用未裁定口径 / 与线上撞号 | E2 FAIL |
| R-3 | IR `cells[]` 与 span 不对齐 | `TEXT_HASH_MISMATCH` 类错误，不产出 PARTIAL（E3） |
| R-4 | 同一 IR 两次投影结果不同 | E4 FAIL |
| R-5 | 试图切 `INGEST_PROJECTION_MODE=snapshot` | E5 FAIL（静态/运行时可证） |
| R-6 | 正文通道回归 | `tests/test_rag_projection.py` 既有 **13 条**测试全 PASS（现场实测 13，PLAN 初版写 11 已更正），正文载荷不变 |

---

## 四、验收命令（`DEV_SELF_CHECK_PASS` 最小证据集）

```bash
cd /home/szf/data/dev/llmke-v2
# 解释器：先确认平台服务现有测试环境并在 evidence 标注绝对路径与版本
<PLATFORM_PY> -m pytest services/rag-alg/index_data_service/... -q      # E1~E5 + R-1~R-6
<PLATFORM_PY> -m pytest <rag_projection 既有 11 项测试> -q              # R-6 正文通道不回归
# R-0 只读对照（裁定前）
#   IR tables[] 字段清单、线上 table_chunks_kb_9 抽样 pk 与 seed 反推
# 静态边界
grep -rn 'INGEST_PROJECTION_MODE' <配置/代码>        # 仍 legacy，无切读
ss -tlnp | grep -E ':(19995|18094|19531|19200)\b'   # 服务状态与开工前一致（未启停）
# 越界自查（两仓）
git -C /home/szf/data/dev/llmke-v2 status --short
git -C /home/szf/data/dev/doc2md status --short
```

证据写入 `docs/v2-tasks/evidence/P1-L5-<timestamp>.log`：现场命令 + 真实输出 + **R-0 对照与 TL 裁定记录** + 两仓 `git diff`（平台三文件全文）+ 解释器绝对路径与用途 + 服务端口开工前后对比。

---

## 五、Baton 与收口

```text
python-engineer → R-0 只读对照 → 回 TL 裁定 _table_pk
  → 裁定后写反例 FAIL → 实现 → PASS → DEV_SELF_CHECK_PASS
  → TL 复核（现场输出 + 两仓无越界 + 反例可复现 + 未切模式/未启停服务）
  → 内部推进条件满足 → 可派工 P2
  → QA_PASS 仍由 independent_qa 在 G-4 闭环后统一补签
```

**实现角色只记录 `DEV_SELF_CHECK_PASS`，不自签 `QA_PASS`、不标 `DONE` / `VERIFIED`**；G-4 闭环前 `TASKS.yaml` 的 `state` 不得写 `VERIFIED`。

---

## 六、回滚

恢复 `projection.py` / `enrich.py` / `kb_pipeline.py` 三个平台文件，删除新增测试与 fixtures。因本 loop 不切模式、不写线上存储、不启停服务，回滚不影响在线检索与 L1~L4 产物。

---

## 七、依赖

本 loop 是 `snapshot` 切读的**硬前置**（`IMPLEMENTATION-QUEUE-V2.md:105-106`）；完成后才允许在后续切片讨论 `INGEST_PROJECTION_MODE` 切换与 `parse_artifact_id` 落库迁移。P2（`T-D2MD-06` `index_writer` 适配层 + `delete_scope`）依赖本 loop。
