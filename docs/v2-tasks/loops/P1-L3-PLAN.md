
# P1-L3 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-03`（`docs/v2-tasks/TASKS.yaml`）
- 阶段 P1 doc2md 增量能力，Loop 3 `kb-manifest.json` + 稳定幂等键
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton（QA 签署策略见 `CHECKPOINT-VL-DOC2MD-INC.md` §四 / §九）
- 依赖：`T-D2MD-02`（L2 队列），其内部推进条件已由 `P1-L2-TL-VERIFY-20261108.log` 复核满足
- 编写人：TL（规划，不亲自实现）
- 状态：**标准已锁定，已派工**

> 任何实现代码写入之前锁定断言。实现角色若认为断言不可达，先回 TL 修订本文件，不得自行放宽。
> 依据：`03-IMPLEMENTATION.md` §P1-3（`:101-107`）、`00-DESIGN.md` `:111`、`01-EVIDENCE.md` `:88,95`。

---

## 一、Scope

| 允许 | 路径 | 约束 |
|---|---|---|
| 改 | `backend/app/core/parsed_paths.py`（doc2md 仓） | additive 新增 `kb-manifest.json` 路径常量；L1 已 +5 行常量保持不变 |
| 改 | `backend/app/services/markitdown_parser.py`、`backend/app/services/mineru_pdf_parser.py`（doc2md 仓） | `parse_manifest.json` additive 增加 `kb` / `source_root` / `read_set_digest` / `parser_fingerprint`；`generated_at` 可复现；复用既有 `_should_skip_idempotent`（`:402-412` / `:867-878`），不重写幂等逻辑 |
| 改 | `scripts/v2_ingest_doc2md.py`（**llmke-v2 仓，唯一例外**） | 仅移除 `_reset_vault_state` 调用（`:122`）与 PDF `--force`（`:136`），改为「仅当 `parser_fingerprint` 或 `read_set_digest` 变化才重解析」；**不改运行态配置、不启用 18096、不启停服务** |
| 新增 | `backend/tests/test_idempotency_key.py` + fixtures（doc2md 仓） | 反例先 FAIL 再 PASS |
| 承接 | L2 遗留 1 | 明确 `route_type=UNKNOWN` 的处置口径（拒绝 / 降级 / 默认解析器），需给出断言，不改 L2 `parse_queue.py` 语义 |

| 禁止 | 理由 |
|---|---|
| 改 `parsed_text.md` 内容或 hash、四件套字节 | `05-data-contracts.md:9-11` 铁律；`store._check_source_consistency` 校验 `output_hash == sha256(parsed_text)` |
| 改 `parse_manifest.json` **既有键**的语义或删除既有键 | additive 约束（新增字段可以，改旧值语义不行） |
| 改 L1 `kb_diff.py` / `scan-diff`、L2 `parse_queue.py` / `build-parse-queue` / `parse` 语义 | 已锁定上游契约 |
| 改设计包 / `MANIFEST.sha256` / `docs/v2-tasks/TASKS.yaml` / llmke-v2 其它生产代码 / 运行态配置 | 越界；`TASKS.yaml` 由 TL 维护 |
| 触碰 L4（MinerU 第 4 件 `document_ir.json`）、L5（表格通道投影） | 后续 loop 各自派工 |
| 启停服务、写 DB / ES / Milvus / 18094、启用 18096 | 本 loop 只做代码与离线测试 |

> **关于 llmke-v2 例外**：L1/L2 红线是「不改 llmke-v2 生产代码」。L3 是设计包 `03-IMPLEMENTATION.md:107` 明确要求的平台侧改动，故仅授权 `scripts/v2_ingest_doc2md.py` 这一个文件、且只改破坏幂等的两处。改动前先记录该文件 md5，改动后附 `git diff` 全文供 TL 复核；不触碰该脚本其它逻辑。

---

## 二、可证伪断言（退出标准）

### C1 · 第二次解析命中幂等

```
给定同一 (parser_fingerprint, read_set_digest) 的同一源文件
连续两次执行解析（非 --force）
期望：第二次跳过解析（日志/计数器可证），四件套字节与 sha256 逐字节不变，无新增产物、无重复写 DB
```

**FAIL 条件**：第二次重新解析、产物 hash 变化、或产生重复记录。
**依据**：`markitdown_parser._should_skip_idempotent:402-412`、`mineru_pdf_parser._should_skip_idempotent:867-878`；设计包 `00-DESIGN.md:111`。

### C2 · `generated_at` 可复现 / `read_set_digest` 稳定

```
同一批次内容、仅 `generated_at` 不同，重建两次
期望：read_set_digest 相同（generated_at 不进摘要，或取 manifest 确定性时间）；
      parse_manifest 既有键值不变；parsed_text.md 内容与 hash 不变
```

**FAIL 条件**：digest 随时间变化，或四件套任一字节变化。

### C3 · 变更才触发重解析

```
分别只改 ① 源文件内容（read_set_digest 变） ② parser_fingerprint
期望：两种情形都重新解析；未变项仍跳过
```

**FAIL 条件**：变更后仍跳过，或未变项被重解析。

### C4 · 平台脚本不再主动破坏幂等

```
静态检查 scripts/v2_ingest_doc2md.py
期望：不再有 _reset_vault_state 调用、不再有 --force；
      仅当 parser_fingerprint / read_set_digest 变化才走重解析分支
```

**FAIL 条件**：残留 `_reset_vault_state` 调用或 `--force`，或无条件重解析。

### C5 · additive 与四件套不变

```
解析前后对比
期望：parse_manifest 既有键全部保留且语义不变；
      parsed_text.md 内容/hash 不变；ir span 与 content_uid 对齐（store._check_source_consistency 通过）
```

**FAIL 条件**：删改既有键、改 `parsed_text.md`、或一致性校验失败。

### 组件级反例清单（先 FAIL，再实现转 PASS）

| # | 反例 | 期望 |
|---|---|---|
| R-1 | 相同输入连跑两次 | 第二次跳过，产物 hash 不变（C1） |
| R-2 | 仅 `generated_at` 不同 | `read_set_digest` 相同、跳过（C2） |
| R-3 | 源文件字节改变 | digest 变、重解析（C3） |
| R-4 | `parser_fingerprint` 改变 | 重解析（C3） |
| R-5 | 平台脚本仍含 `_reset_vault_state` / `--force` | 反例判 FAIL；移除后转 PASS（C4） |
| R-6 | 企图改 `parsed_text.md` 一个字节 | 一致性校验拒绝（C5） |
| R-7 | 队列里 `route_type=UNKNOWN` 的条目（L2 遗留 1） | 按本 loop 锁定的处置口径给出明确结果与断言，不得静默丢弃、不得整批失败 |

> R-7 要求先由实现角色在 §六 记录选定的 UNKNOWN 口径并回 TL 确认，再写断言；**不得自行放宽为「不测」**。

---

## 三、幂等键契约

```
parse_manifest.json（additive）
  + kb                 : 知识库 id
  + source_root        : 源目录标签
  + read_set_digest    : 正式幂等键（四件套内容摘要；generated_at 不纳入）
  + parser_fingerprint : 解析器指纹
  - generated_at       : 改为可复现（取 manifest 确定性时间或从摘要输入中排除）

kb-manifest.json（库级，路径常量由 parsed_paths.py 提供）
  (kb, file_id, sha256, read_set_digest, artifact_id, parser_fingerprint,
   status=ACTIVE|TOMBSTONE, cursor)
```

不引入第二套幂等键；`read_set_digest` 是唯一正式口径（`kb_pipeline.py:118-134`）。

---

## 四、验收命令（`DEV_SELF_CHECK_PASS` 最小证据集）

```bash
cd /home/szf/data/dev/doc2md
# CLI 复跑 / 生产解析路径用 doc2md-toolenv
PYTHONPATH=backend /home/szf/data/dev/doc2md-toolenv/bin/python -m pytest backend/tests/test_idempotency_key.py -q
PYTHONPATH=backend /home/szf/data/dev/doc2md-toolenv/bin/python -m pytest backend/tests/test_parse_queue.py -q   # L2 不回归
PYTHONPATH=backend /home/szf/data/dev/doc2md-toolenv/bin/python -m pytest backend/tests/test_kb_diff.py -q      # L1 不回归
# 全量回归主判据用 anaconda3：既有 5 failed 数量不增加
timeout 300 env PYTHONPATH=backend /home/szf/anaconda3/bin/python -m pytest backend/tests -q --tb=no
# 平台脚本静态检查
grep -n '_reset_vault_state\|--force' /home/szf/data/dev/llmke-v2/scripts/v2_ingest_doc2md.py
# 越界自查（两仓）
git -C /home/szf/data/dev/doc2md status --short
git -C /home/szf/data/dev/llmke-v2 status --short
```

证据写入 `docs/v2-tasks/evidence/P1-L3-<timestamp>.log`（现场命令 + 真实输出 + 两仓 `git diff`）。
**evidence 必须显式标注每处命令所用解释器及用途**（`CHECKPOINT` §七 双解释器口径；02:34「唯一用 doc2md-toolenv、禁用 anaconda3」已撤回，不得沿用）。

---

## 五、Baton 与收口

```text
python-engineer → DEV_SELF_CHECK_PASS → TL 复核（现场输出 + 两仓 git status 无越界
  + 反例 FAIL→PASS 可复现 + 平台脚本 diff 全文）
  → 内部推进条件满足 → 可派工 L4 / L5
  → QA_PASS 仍由 independent_qa 在 G-4 闭环后统一补签（CHECKPOINT §四 / §九）
```

**实现角色只记录 `DEV_SELF_CHECK_PASS`，不自签 `QA_PASS`、不标 `DONE` / `VERIFIED`。** G-4 闭环前所有 loop 的 `QA_PASS` 挂起，`TASKS.yaml` 的 `state` 不得写 `VERIFIED`。

---

## 六、R-7 口径确认槽（实现角色填写后回 TL）

> 填写人：`python-engineer`（2026-11-08），**待 TL 确认**；确认前不写 R-7 断言、不改 L2 `parse_queue.py` 语义。
>
> **TL 02:58 已确认（批准默认解析器口径 + 追加调度事实断言）**：上一行「待 TL 确认」原文留痕保留、不删除，状态以本行为准。追加要求：除队列状态断言外，必须用注入替身 / `unittest.mock.patch` 拦截 `MarkItDownParserService.parse_markitdown`，验证 UNKNOWN 项确实走默认解析器分支（同时 patch Mineru 分支并断言未被调用）、传入 sha256 一致、返回可观测 `ParseOutcome`；仍不改 L2 `parse_queue.py` 一行、不放宽为「不测」。

```
route_type=UNKNOWN 的处置口径：默认解析器（保留入队 + 显式登记，不静默降级、不改写路由结果）

理由与依据：
  (1) L1 夹具 F1/F2/F4/F5 无扩展名，既有 app.core.parser_routing.match_route_type
      对无扩展名返回 UNKNOWN；L2 已锁定的 B1 断言要求队列含 F2/F5 且带 route_type。
      若改为「拒绝」会让 B1 队列为空，破坏 L2 已锁定语义（本 loop 禁改 parse_queue.py）。
  (2) 若改为「降级」（把 UNKNOWN 改写成某已知 route_type）需改 L2 代码（禁止），
      且属于静默改写路由结果，违反 02-CONTRACTS.md「禁止静默降级」口径。
  (3) 现状 DefaultParseRunner 对非 MinerU route_type（含 UNKNOWN）走
      MarkItDownParserService（默认解析器）；UNKNOWN 项保留在 items、status=PENDING、
      不进 rejected（未被静默丢弃），其它项不受影响（不整批失败）——已满足
      R-7「不得静默丢弃、不得整批失败」。本 loop 仅把该口径显式登记到 PLAN §六
      与 evidence，使其不再是无记录的隐式行为；不改 L2 parse_queue.py 一行。

对应断言（TL 确认后写入 test_idempotency_key.py）：
  test_r7_unknown_route_explicit_default_parser：
    构造 routes 含 {sha_unknown: RouteInfo("UNKNOWN", ...)} + 一个正常项，
    调用 L2 build_parse_queue（只调用、不修改其语义），断言：
      - UNKNOWN 项出现在 items 且 route_type == "UNKNOWN"、status == "PENDING"、
        fail_reason is None、rejected 不含该 sha；
      - 正常项仍为 PENDING；队列长度 == 2；
      - 即「明确结果 + 不静默丢弃 + 不整批失败」，不得整批 FAILED、不得进 rejected。
```

未回 TL 确认前，不得开始该条实现。

---

## 七、回滚

doc2md 仓：恢复 `parsed_paths.py` / `markitdown_parser.py` / `mineru_pdf_parser.py`，删除 `test_idempotency_key.py` 与 fixtures。
llmke-v2 仓：恢复 `scripts/v2_ingest_doc2md.py` 单个文件（改动前 md5 需记录）。
不影响 L1/L2 产物、既有解析链路与在线服务。

---

## 八、依赖

`T-D2MD-04`（Loop 4 PDF 第 4 件）与 `T-D2MD-05`（Loop 5 表格通道）依赖本 loop 或 L2；`T-D2MD-05` 是 `snapshot` 切读的硬前置（`IMPLEMENTATION-QUEUE-V2.md:105-106`）。L4 可与 L3 并行派工（两者都只依赖 L2），但本轮先单派 L3，避免同时改 `mineru_pdf_parser.py` 造成冲突。
