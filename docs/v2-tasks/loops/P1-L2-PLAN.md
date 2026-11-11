# P1-L2 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-02`（`docs/v2-tasks/TASKS.yaml`）
- 阶段 P1 doc2md 增量能力，Loop 2 `build-parse-queue` / `parse` 替换 placeholder
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton（QA 签署策略见 `CHECKPOINT-VL-DOC2MD-INC.md` §四）
- 依赖：`T-D2MD-01`（Loop 1 的 `DiffResult` + `kb-manifest.json`）
- 编写人：TL（规划，不亲自实现）
- 状态：**标准已锁定，等待 Loop 1 内部收口后派工**（本文件先行准备，不代表已启动实现）

> 任何实现代码写入之前锁定断言。实现角色若认为断言不可达，先回 TL 修订本文件，不得自行放宽。

---

## 一、Scope

| 允许 | 路径 | 约束 |
|---|---|---|
| 替换 placeholder | `backend/app/cli/main.py:1076-1083` | `build-parse-queue` 与 `parse` 两个命令变为真实现；其余 20 个命令签名与行为不变 |
| 新增 | `backend/app/services/parse_queue.py` | 队列构建/消费、失败项保留、`dry-run` 零写入 |
| 新增 | `backend/tests/test_parse_queue.py` + fixtures | 反例先 FAIL 再 PASS |

| 禁止 | 理由 |
|---|---|
| 改 Loop 1 的 `kb_diff.py` / `scan-diff` 语义 | 已锁定的上游契约 |
| 动 `backend/app/services/document_ir_builder.py` | 既存 `M`，非本 loop 产物 |
| 改 `parsed_text.md` 内容/hash、`parse_manifest` 既有键语义 | 铁律 + additive 约束 |
| 触碰 L3（`_reset_vault_state` / `--force` / `generated_at`）、L4（MinerU IR）、L5（表格通道） | 后续 loop 各自派工 |
| 改 llmke-v2 生产代码 / 设计包 / `MANIFEST.sha256` / `TASKS.yaml` | 越界 |

---

## 二、可证伪断言（退出标准）

### B1 · `--dry-run` 零写入

```
给定 Loop 1 产出的 DiffResult{added=[F5], changed=[F2], removed=[F3]}
执行 build-parse-queue --dry-run
期望：stdout 给出待解析清单（sha256 + route_type + parser_adapter_version）；
      kb-manifest.json 的 mtime/sha256 不变；不产生任何报告文件；DB 无新增 parse job 记录
```

**FAIL 条件**：任一文件被写、DB 新增行、或输出清单缺 `route_type`。
**依据**：`handoff/external-refactor-2026-10-17/00-READ-ME-FIRST.md:52`「幂等 + dry-run 是一等公民」；`cli/main.py:203-207,270-274,342-346` 现有 dry-run 语义。

### B2 · 失败项保留且带 `fail_reason`

```
构造一个 route_type=UNSUPPORTED 的 sha256 + 一个正常项
执行 build-parse-queue（非 dry-run）→ parse
期望：正常项进入解析；异常项留在队列，带 fail_reason，不静默丢弃、不阻断其它项；
      再次执行时异常项仍可被重试
```

**FAIL 条件**：异常项被吞掉、无 fail_reason、或整批失败。

### B3 · 反例：缺路由结果的 sha256 不得进入 parse 队列

```
构造 sha256 存在但 parser_router 无结果的条目
期望：build-parse-queue 拒绝入队（明确原因），parse 阶段看不到该 sha256
```

**FAIL 条件**：该条目进入待解析清单、或 parse 抛未处理异常。

### 组件级反例清单（先 FAIL，再实现转 PASS）

| # | 反例 | 期望 |
|---|---|---|
| R-1 | `DiffResult` 四集合全空 | 队列为空，`parse` 不触发任何解析，退出码 0 |
| R-2 | `removed` 含 TOMBSTONE 条目 | 不进入解析队列（删除不是解析任务），且不复活 |
| R-3 | 同一 sha256 重复出现 | 队列去重，不重复入队（按内容寻址身份） |
| R-4 | `--dry-run` 连续两次 | 输出逐字节相同，磁盘/DB 零变化 |
| R-5 | `parser_adapter_version` 与 manifest 不一致 | 该条目被标 changed 并重排队，而非复用旧产物 |
| R-6 | 解析过程中断后重放 | 已完成项幂等跳过（复用 `markitdown_parser._should_skip_idempotent`）、未完成项保留 |
| R-7 | **TL 02:34 新增，承接 L1 覆盖缺口**：文件集合不变、仅 1 个文件字节改变 | 调用 `compute_kb_diff` 得 `reason=CONTENT_CHANGED`、`added/removed` 为空、`changed=[该文件]`。用于固定 `02-CONTRACTS.md` §4.3 的 `CONTENT_CHANGED` 分支；不得修改 L1 的 `kb_diff.py` 语义，只加回归断言 |

---

## 三、CLI 契约

```text
python3 -m app.cli.main build-parse-queue --kb kb_9 --config config/app.yaml [--dry-run]
python3 -m app.cli.main parse --kb kb_9 --config config/app.yaml [--limit N] [--dry-run]
```

- 输入：Loop 1 的 `DiffResult` / `kb-manifest.json`；输出：待解析清单（含 `sha256 / file_id / route_type / parser_adapter_version`）。
- 复用既有 `copy-to-vault` / `route-parsers` / `parse-markitdown` | `parse-mineru-pdf` 的服务层，**不重新实现解析**。
- 不引入第二套解析者（对齐 Owner 要求 1：doc2md 唯一解析者）。

---

## 四、验收命令（`DEV_SELF_CHECK_PASS` 最小证据集）

```bash
cd /home/szf/data/dev/doc2md
pytest backend/tests/test_parse_queue.py -q                 # B1~B3 + R-1~R-6 全 PASS
python3 -m app.cli.main build-parse-queue --kb kb_9 --config config/app.yaml --dry-run > /tmp/q1.json
python3 -m app.cli.main build-parse-queue --kb kb_9 --config config/app.yaml --dry-run > /tmp/q2.json
diff /tmp/q1.json /tmp/q2.json                              # B1/R-4：逐字节相同
sha256sum backend/tests/fixtures/kb_diff_corpus/kb-manifest.json  # dry-run 前后不变
python3 -m app.cli.main --help                              # 既有命令无回归
pytest backend/tests -q                                      # 既有测试不新增失败
git status --short                                          # 无越界；document_ir_builder.py 既存 M 保持原样
```

证据写入 `docs/v2-tasks/evidence/P1-L2-<timestamp>.log`（现场命令 + 真实输出）。

---

## 五、Baton 与收口

```text
python-engineer → DEV_SELF_CHECK_PASS → TL 复核（现场输出 + git status 无越界）
  → 内部推进条件满足 → 可派工 L3
  → QA_PASS 仍由 independent_qa 在 G-4 闭环后统一补签（见 CHECKPOINT §四）
```

**实现角色只记录 `DEV_SELF_CHECK_PASS`，不自签 `QA_PASS`、不标 DONE。** 在 G-4 闭环前，所有 loop 的 `QA_PASS` 挂起，`TASKS.yaml` 的 `state` 不得写 `VERIFIED`。

---

## 六、回滚

新增文件 + 两处 placeholder 替换。回滚 = 恢复 `cli/main.py:1076-1083` 两行 placeholder、删除 `parse_queue.py` 与测试；不影响既有解析链路与在线服务。

---

## 七、依赖

`T-D2MD-03`（Loop 3 幂等键 / 移除 `_reset_vault_state` 与 `--force`）依赖本 loop 的队列；`T-D2MD-04`（Loop 4 PDF 第 4 件）可与 Loop 3 并行（依赖 Loop 2）。L5 表格通道是 `snapshot` 切读的硬前置（`IMPLEMENTATION-QUEUE-V2.md:105-106`）。
