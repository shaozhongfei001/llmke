
# P1-L4 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-04`（`docs/v2-tasks/TASKS.yaml`）
- 阶段 P1 doc2md 增量能力，Loop 4 `PDF 原生第 4 件 document_ir.json`
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton（QA 签署策略见 `CHECKPOINT-VL-DOC2MD-INC.md` §四 / §九）
- 依赖：`T-D2MD-02`（L2 队列）；**须等 L3 收口后派工**（L3 与 L4 都改 `mineru_pdf_parser.py`，并行会冲突）
- 编写人：TL（规划，不亲自实现）
- 状态：**标准已锁定，待 L3 内部收口后派工**（本文件先行准备，不代表已启动实现）

> 任何实现代码写入之前锁定断言。实现角色若认为断言不可达，先回 TL 修订本文件，不得自行放宽。
> 依据：`03-IMPLEMENTATION.md` §P1-4（`:109-113`）、`00-DESIGN.md` `:112`、`01-EVIDENCE.md` `:70`、`04-ACCEPTANCE.md` A-2。

---

## 一、Scope

**四件套口径**（`parsed_paths.py:7-15` / `01-EVIDENCE.md:70`）：
`parsed_text.md` / `parsed_metadata.json` / `parse_manifest.json` / `document_ir.json`

| 允许 | 路径 | 约束 |
|---|---|---|
| 改 | `backend/app/services/mineru_pdf_parser.py`（doc2md 仓） | 在 `_finalize_success_from_staging` 附近（`:626-697` 写三件套之后）调用 doc2md 自己的 `document_ir_builder.build_from_mineru_content_list`（`document_ir_builder.py:274`），写出第 4 件 `document_ir.json`；`parse_manifest` 里对齐 `ir_source_files`；不改 `parsed_text.md` 与前三件套字节 |
| 新增 | `backend/tests/test_pdf_fourth_artifact.py` + fixtures（doc2md 仓） | 反例先 FAIL 再 PASS |
| 只读核对 | `scripts/v2_fill_mineru_ir.py:61-64`、`scripts/v2_ingest_doc2md.py:174`（llmke-v2 仓） | 平台补口已用同一 builder，逻辑可上移；**本 loop 不改这两个文件** |

| 禁止 | 理由 |
|---|---|
| 改 `parsed_text.md` 内容或 hash、前三件套字节 | `05-data-contracts.md:9-11` 铁律；`store._check_source_consistency` 校验 `output_hash == sha256(parsed_text)` 与 IR span |
| 改 `parse_manifest.json` 既有键语义、删既有键 | additive 约束 |
| 改 L1 `kb_diff.py` / `scan-diff`、L2 `parse_queue.py`、L3 幂等键实现的语义 | 已锁定上游契约 |
| 改 llmke-v2 生产代码 / 运行态配置 / 设计包 / `MANIFEST.sha256` / `TASKS.yaml` | 越界 |
| 触碰 L5（表格通道投影） | 后续 loop |
| 启停服务、写 DB / ES / Milvus / 18094、启用 18096 | 本 loop 只做离线单文件解析与静态检查 |

> **范围声明**：`04-ACCEPTANCE.md` A-2 的「上传 pdf/docx/xlsx/txt 各一份」属 **P6 实现验收**，需要真实上传与 DB。本 loop 只做**离线单文件解析**（临时目录 + fixture，不写 DB），把「doc2md 原生产出第 4 件」这一能力补齐并给出可证伪断言；A-2 在 P6 用四类格式真实文件收口。不得把本 loop 的离线通过写成 A-2 通过。

---

## 二、可证伪断言（退出标准）

### D1 · 四件套齐备

```
给定一个 MinerU PDF 解析 fixture（离线、临时目录）
执行 parse-mineru-pdf 的成功收尾路径
期望：产物目录同时出现 parsed_text.md / parsed_metadata.json / parse_manifest.json / document_ir.json；
      parse_manifest.status == SUCCESS
```

**FAIL 条件**：缺任一件（尤其第 4 件）、或 status 非 SUCCESS。

### D2 · 第 4 件由 doc2md 原生产出，不依赖平台补口

```
同一 fixture，不调用 scripts/v2_fill_mineru_ir.py
期望：document_ir.json 已存在且可校验（validate_document_ir 通过）；
      调用点可静态定位到 mineru_pdf_parser.py 内的 build_from_mineru_content_list
```

**FAIL 条件**：产物由平台脚本补齐、或 builder 未被调用。

### D3 · 一致性与 span 对齐

```
期望：store._check_source_consistency 通过；
      sha256(parsed_text.md) == parse_manifest.output_hash；
      IR 的 span 逐字对齐 parsed_text.md 对应片段；三方 content_uid 一致
```

**FAIL 条件**：任一校验失败，或篡改一个字符后仍被判通过（反例 R-2）。

### D4 · `ir_source_files` 对齐

```
期望：parse_manifest 的 ir_source_files 与实际用于构建 IR 的 MinerU content_list 文件一致；
      既有键全部保留
```

**FAIL 条件**：字段缺失、指向不存在的文件、或既有键被删改。

### D5 · additive 与三件套不变

```
期望：解析前后 parsed_text.md / parsed_metadata.json 字节与 hash 不变；
      parse_manifest 既有键语义不变（只 additive 增加/对齐 ir_source_files）
```

**FAIL 条件**：三件套任一字节变化。

### 组件级反例清单（先 FAIL，再实现转 PASS）

| # | 反例 | 期望 |
|---|---|---|
| R-1 | 桩版 `build_from_mineru_content_list` 未被调用 | 第 4 件缺失 → D1/D2 FAIL |
| R-2 | 把 `parsed_text.md` 改一个字节 | `_check_source_consistency` 拒绝 / hash 不等 → D3 FAIL |
| R-3 | manifest 缺 `ir_source_files` 或指向不存在文件 | D4 FAIL |
| R-4 | 产物依赖 `v2_fill_mineru_ir.py` 才有第 4 件 | D2 FAIL |
| R-5 | 三件套哈希与改动前不一致 | D5 FAIL |
| R-6 | 非 PDF 路径回归（L3 的 `markitdown` / L2 队列） | 既有测试全 PASS，不受影响 |

---

## 三、CLI 与产物契约

```text
python3 -m app.cli.main parse-mineru-pdf --sha256 <sha> --config config/app.yaml
```

- 复用既有 `document_ir_builder.build_from_mineru_content_list` / `validate_document_ir`，**不重新实现 IR 构建**。
- `document_ir.json` 的 schema 与平台 `v2_fill_mineru_ir.py` 当前产出保持一致（同一 builder）。
- 不引入第二套解析者（Owner 要求 1：doc2md 唯一解析者）。

---

## 四、验收命令（`DEV_SELF_CHECK_PASS` 最小证据集）

```bash
cd /home/szf/data/dev/doc2md
# CLI / 生产解析路径 → doc2md-toolenv
PYTHONPATH=backend /home/szf/data/dev/doc2md-toolenv/bin/python -m pytest backend/tests/test_pdf_fourth_artifact.py -q
PYTHONPATH=backend /home/szf/data/dev/doc2md-toolenv/bin/python -m pytest backend/tests/test_idempotency_key.py -q   # L3 不回归
PYTHONPATH=backend /home/szf/data/dev/doc2md-toolenv/bin/python -m pytest backend/tests/test_parse_queue.py -q      # L2 不回归
PYTHONPATH=backend /home/szf/data/dev/doc2md-toolenv/bin/python -m pytest backend/tests/test_kb_diff.py -q         # L1 不回归
# 全量回归主判据 → anaconda3：既有 5 failed 数量不增加
timeout 300 env PYTHONPATH=backend /home/szf/anaconda3/bin/python -m pytest backend/tests -q --tb=no
# 越界自查（两仓）
git -C /home/szf/data/dev/doc2md status --short
git -C /home/szf/data/dev/llmke-v2 status --short
```

证据写入 `docs/v2-tasks/evidence/P1-L4-<timestamp>.log`（现场命令 + 真实输出 + 两仓 `git diff`）。
**每处命令显式标注解释器与用途**（`CHECKPOINT` §七 双解释器口径）；如实标注「离线 fixture，A-2 留待 P6」。

---

## 五、Baton 与收口

```text
python-engineer → DEV_SELF_CHECK_PASS → TL 复核（现场输出 + 两仓 git status 无越界
  + 反例 FAIL→PASS 可复现 + 四件套 hash 对比）
  → 内部推进条件满足 → 可派工 L5
  → QA_PASS 仍由 independent_qa 在 G-4 闭环后统一补签（CHECKPOINT §四 / §九）
```

**实现角色只记录 `DEV_SELF_CHECK_PASS`，不自签 `QA_PASS`、不标 `DONE` / `VERIFIED`。** G-4 闭环前 `TASKS.yaml` 的 `state` 不得写 `VERIFIED`。

---

## 六、回滚

恢复 `backend/app/services/mineru_pdf_parser.py`，删除 `test_pdf_fourth_artifact.py` 与 fixtures。不影响 L1/L2/L3 产物、既有解析链路与在线服务。

---

## 七、依赖与并行约束

`T-D2MD-05`（L5 表格通道）依赖本 loop 的 `document_ir.json` 中 `tables[].cells[]`，且是 `snapshot` 切读的硬前置（`IMPLEMENTATION-QUEUE-V2.md:105-106`）。
**本 loop 必须等 L3 内部收口后再派工**：L3 也在改 `mineru_pdf_parser.py`（manifest additive 四字段），并行写入会互相覆盖。
