# P1-L1 · Loop 规划（开发前定验证标准）

- 切片：`VL-DOC2MD-INC` / 任务 `T-D2MD-01`（`docs/v2-tasks/TASKS.yaml`）
- 阶段：P1 doc2md 增量能力，Loop 1 `scan-diff --kb` + `kb_diff.py`
- holder：`python-engineer`（实现）→ `DEV_SELF_CHECK_PASS` → baton 挂起待 `independent_qa`
- 前置：G-5 已由 Owner 2026-11-08「同意复工」闭环；T-D2MD-00 已 VERIFIED
- 编写人：TL（规划 loop，不亲自实现）
- 外部仓库：`/home/szf/data/dev/doc2md`（G-5 已授权 additive 改动）

> 本文件在**任何实现代码写入之前**锁定断言。实现角色若认为断言不可达，必须先回 TL 修订本文件，不得擅自放宽退出标准。

---

## 一、Scope（本 loop 允许改什么）

| 允许 | 路径 | 约束 |
|---|---|---|
| 新增 | `backend/app/services/kb_diff.py` | 新文件，纯函数优先，不依赖网络 |
| 新增 | `backend/tests/test_kb_diff.py` | 反例先 FAIL，再实现转 PASS |
| additive 修改 | `backend/app/cli/main.py` | 新增 `@app.command("scan-diff")`，**不得改动既有 20 个命令的签名与行为** |
| additive 修改 | `backend/app/core/parsed_paths.py` | 仅新增清单路径常量 |

| 禁止 | 理由 |
|---|---|
| 改 `parsed_text.md` 内容或 hash | `handoff/external-refactor-2026-10-17/05-data-contracts.md:9-11` 铁律 |
| 改 `parse_manifest.json` 既有键语义 | 只允许 additive（`02-CONTRACTS.md` §4.1） |
| 物理删除源文件 / 扫描时自动删除 | `specs/001-file-inventory/spec.md:21-25` |
| 动 `backend/app/services/document_ir_builder.py` | 该仓库当前已有**既存 modified**（`git status` 显示 `M`），非本 loop 产物，不得覆盖或顺手提交 |
| 动 `llmke-v2` 的 `services/**`、`platform/r12/conf/**`、设计包、`MANIFEST.sha256` | 越界；设计包是评审基线 |
| 触碰 P1-L2~L5 的内容 | 每 loop 独立派工 |

---

## 二、开发前锁定的可证伪断言

每条断言都回答「若没做对，具体哪条会 FAIL」。禁止「测试都绿了」式收口。

### A1 · 精确分集（`02-CONTRACTS.md` §4.3 `DiffResult`）

**语料夹具**：`backend/tests/fixtures/kb_diff_corpus/` 构造「新增 1 + 删除 1 + 修改 1 + 不变 2」共 5 个逻辑文件，配一份上轮 `kb-manifest.json`。

```
给定 manifest 的 ACTIVE = {F1, F2(旧hash), F3, F4}，磁盘 = {F1, F2(新hash), F4, F5}
（F3 仅存在于上轮 manifest、磁盘已删除；TL 02:34 修订：原文误把 F3 写进磁盘，与下方 `removed=["F3"]` 自相矛盾）
期望 DiffResult:
  added     = ["F5"]
  changed   = ["F2"]
  removed   = ["F3"]
  unchanged = ["F1", "F4"]
  reason    = "FILE_SET_CHANGED"
  set_digest = sha256(sorted ACTIVE (file_id, sha256, read_set_digest))
```

**FAIL 条件**：任一集合成员/顺序不符、`set_digest` 不受排序影响、`cursor` 未单调推进、`reason` 错。
**实现要点**：`sha256(文件字节)` 作身份（复用 `backend/app/core/ids.py:13-26` 的 `compute_sha256`）；`file_id` 与 `source_path` 分离；判定优先级 `removed > added/changed > parser_fingerprint 变化 > NO_CHANGE`。

### A2 · TOMBSTONE 与重放幂等

- 删除**不物理删条目**，写 `status: TOMBSTONE` + `revoked_at` + `reason: SOURCE_REMOVED`；
- 用同一份输入重放 `compute_kb_diff` 两次：第二次 `added/changed` 为空、`removed` 不再重复出现、`cursor` 与 `set_digest` **与第一次完全相同**；
- `set_digest` 只覆盖 `status=ACTIVE` 条目。

**FAIL 条件**：重放产生新 removed、cursor 变化、或 TOMBSTONE 被物理删除导致条目消失。
**依据**：`02-CONTRACTS.md` §4.1、`EVIDENCE-SCOPE-DELTA-20261101.md:21-24`（清单整表写回、失败不动指针）。

### A3 · 反例：错 `parser_fingerprint`（**TL 2026-11-08 02:30 修订：明确夹具**）

> 修订原因：原表述未指定夹具，TL 用主夹具复跑得到 `FILE_SET_CHANGED`，一度判为 FAIL。经核对 `02-CONTRACTS.md:269` 的判定优先级「显式 FULL_REBUILD_REQUESTED > removed > added/changed > parser_fingerprint 变化 > NO_CHANGE」，**主夹具同时有增删时，文件集合变化优先于 fingerprint 变化是契约正确行为**。歧义在 PLAN，不在实现。此修订不放宽标准，只消除自相矛盾。

- **A3 主断言（用 `no_change/` 独立 KB 根，磁盘与 ACTIVE 完全一致）**：传入与 manifest 不同的 `parser_fingerprint` → 所有 `ACTIVE` 条目标 `changed`，`reason = PARSER_FINGERPRINT_CHANGED`，`added/removed` 为空。
- **A3 优先级哨兵（用主夹具）**：同样错传 fingerprint，因存在 F3 删除 / F5 新增，`reason` 必须仍为 `FILE_SET_CHANGED`，且四集合与 A1 相同 —— 用于固定「文件集合变化优先」的契约语义，防止后续 loop 误改优先级。

**FAIL 条件**：`no_change/` 下出现 added/removed、reason 不是 `PARSER_FINGERPRINT_CHANGED`、或只标了部分 ACTIVE；主夹具下 reason 变成 `PARSER_FINGERPRINT_CHANGED`。

### 组件级反例清单（必须**先 FAIL**，再实现转 PASS）

| # | 反例 | 期望（实现前 FAIL / 实现后 PASS） |
|---|---|---|
| R-1 | 夹具只给 2 个不变文件 | `DiffResult.reason == NO_CHANGE`，四个集合除 unchanged 外全空 |
| R-2 | 删除源文件后再次扫描同一目录 | 不产生第二个 removed，无异常 |
| R-3 | 错 `parser_fingerprint` | A3 行为 |
| R-4 | `scan-diff --dry-run` | 零写入：manifest 文件 mtime / sha256 不变，无报告落盘 |
| R-5 | manifest JSON 损坏 | 抛明确错误（不得静默按空库重建，对齐 `kb_state.json` 的 `KB_STATE_CORRUPT` 口径） |
| R-6 | 两个不同文件字节完全相同（同 sha256） | 不误判为重复而丢失 `file_id`；按 `(file_id, sha256)` 复合键登记 |

---

## 三、CLI 契约（`scan-diff`）

```text
python3 -m app.cli.main scan-diff \
  --kb kb_9 --path <语料目录> --config config/app.yaml \
  [--cursor <path>] [--dry-run]
```

- 输出：stdout 打印 `DiffResult` JSON（含四集合 + cursor + set_digest + reason）；非 `--dry-run` 时写回 `kb-manifest.json`（`llmke.doc2md.kb-manifest/1`，见 `02-CONTRACTS.md` §4.1）。
- `--dry-run`：零写入（对齐 `handoff/.../00-READ-ME-FIRST.md:52`「幂等 + dry-run 是一等公民」）。
- 既有 20 个 CLI 命令的输出与行为不得变化。

---

## 四、验收命令（`DEV_SELF_CHECK_PASS` 的最小证据集）

> **TL 2026-11-08 02:30 修订 / 02:34 裁定 / 02:37 撤回修正（解释器口径：分用途双解释器）**
>
> 系统 `python3`=3.10.12 因既有 `backend/app/cli/main.py:4` 的 `datetime.UTC`（3.11+）必然 ImportError，**全程禁用**。
>
> **撤回 02:34「唯一用 doc2md-toolenv、禁用 anaconda3」的裁定**：该裁定只比较了 `--help` 退出码，未跑全量基线，属 TL 误判。02:37 实测：
>
> | 解释器 | click | 全量 `pytest backend/tests -q` | `--help` |
> |---|---|---|---|
> | `/home/szf/anaconda3/bin/python` 3.11.7 | 8.4.1 | `5 failed, 1507 passed, 133 skipped`（基线 `5 failed, 1497 passed`，失败项同名、passed +10 恰为新增测试） | exit 1（既有基线缺陷，改动前后一致） |
> | `/home/szf/data/dev/doc2md-toolenv/bin/python` 3.11.7 | 8.1.8 | `4 errors during collection`（缺 `jsonpatch`，无法完成全量比对） | exit 0 |
>
> **新裁定（分用途，两者都有效、互不替代）**：
> - **全量回归基线比对 + `test_kb_diff.py`**：用 anaconda3。只有它能跑完整套件并给出可比的 `5 failed → 5 failed` 基线；`--help exit 1` 记为既有基线（`test_cli_help_documents_contract` 等 5 项），不是本 loop 引入、不需要修。
> - **CLI 独立复跑 / 生产解析路径**：用 doc2md-toolenv（`scripts/v2_ingest_doc2md.py:36` 的项目既定解释器）。TL 的 A1/A2/A3/R-1/R-4/R-5 复跑证据基于此，仍有效。
> - 两个解释器下 `test_kb_diff.py` 均 10 passed。**成员 L1 log 的 anaconda3 口径有效，无需返工、无需补跑**；撤回 02:34 要求成员补复跑的指令。
> - 后续每个 loop 的 evidence 必须**显式标注所用解释器及用途**，避免再次误判。

```bash
cd /home/szf/data/dev/doc2md
PY=/home/szf/data/dev/doc2md-toolenv/bin/python
export PYTHONPATH=backend
# 反例与断言
$PY -m pytest backend/tests/test_kb_diff.py -q              # 6 条反例 + 3 条断言 + 1 回归哨兵全 PASS
python3 -m app.cli.main scan-diff --kb kb_9 \
  --path backend/tests/fixtures/kb_diff_corpus --config config/app.yaml --dry-run \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['reason'],d['added'],d['removed'],d['changed'],d['unchanged'])"
# 幂等重放：两次 --dry-run 输出必须逐字节相同
diff <(python3 -m app.cli.main scan-diff ... --dry-run) <(python3 -m app.cli.main scan-diff ... --dry-run)
# 既有命令未回归
$PY -m app.cli.main --help
$PY -m pytest backend/tests -q                                # 见下方「既有测试基线」
# 越界自查
git status --short                                           # 只应出现本 loop 的新增/ additive 文件；
                                                             # document_ir_builder.py 的既存 M 保持原样
```

**既有测试基线（TL 02:30 实测）**：`$PY -m pytest backend/tests -q` 在 `backend/tests/extensions/` 下有 4 个既有 collection error，原因均为 `ModuleNotFoundError: No module named 'jsonpatch'`（`backend/app/extensions/review/patches.py:34` 导入），属该 venv 既有缺依赖，与本 loop 无关（相关文件 `git status` 无改动）。因此本 loop 的回归判据是：`test_kb_diff.py` 全 PASS + `--help` 既有命令仍在 + 既有 collection error 数量**不增加**；不得把既有 4 个 error 记为本 loop 引入。

`DEV_SELF_CHECK_PASS` 定义：以上命令全部有真实输出并满足断言，且 `git status` 无越界改动。实现角色**只记录 DEV_SELF_CHECK_PASS，不自签 QA_PASS**。

---

## 五、Baton 与收口

```text
python-engineer  → DEV_SELF_CHECK_PASS（含现场命令与真实输出）
  → baton 交 independent_qa
  → 独立复跑 + 变异测试（mutate → FAIL / restore → PASS）
  → QA_PASS（需 G-4：真实 principal_id / key_id / public_key_pem）
```

**G-4 未闭环**：baton 在 `DEV_SELF_CHECK_PASS` 后**挂起**，本 loop 不得标 `DONE`/`VERIFIED`。TL 不代签、实现角色不自签（`loop_guard`：review holder ∈ {independent_qa, owner_review}）。

证据归档：`docs/v2-tasks/evidence/P1-L1-<timestamp>.log`，含现场命令与真实输出；`TASKS.yaml` 的 `T-D2MD-01.evidence` 待 QA_PASS 后填写。

---

## 六、回滚

本 loop 全部为新增文件 + 一处 additive 命令注册。回滚 = 删除 `kb_diff.py` / 测试夹具 / `scan-diff` 命令注册，恢复 `parsed_paths.py`；不影响 doc2md 既有解析链路与任何在线服务。

---

## 七、与后续 loop 的依赖（TL 02:34 按 D-01 修订）

`T-D2MD-02`（Loop 2 `build-parse-queue`/`parse`）依赖本 loop 的 `DiffResult` 与 `kb-manifest.json`；`T-D2MD-03`（Loop 3 幂等键）依赖 Loop 2。

> 原文写「本 loop 未完成 QA_PASS 前不得启动 Loop 2 的实现」，与 `CHECKPOINT-VL-DOC2MD-INC.md` §四 的 **D-01 两层收口**（Owner 2026-11-08 授权自动推进）冲突。已修订为：内部推进条件（`DEV_SELF_CHECK_PASS` + TL 复核）满足即自动派工 L2；`QA_PASS` 由 `independent_qa` 在 G-4 闭环后批量补签。L2 实现**不得**反过来修改 L1 已锁定的 `DiffResult`/`kb-manifest` 语义。

## 八、TL 对成员 6 处「判断」的裁定（02:34）

成员 `P1-L1-20261108T023149.log` §6 诚实标注了 6 处判断，TL 逐条裁定，避免 L2 依赖时产生歧义：

| # | 成员判断 | TL 裁定 |
|---|---|---|
| 1 | `cursor = "cursor-" + set_digest` 内容寻址，A1「单调推进」操作化为「与上一轮不同」 | **采纳**。A2 要求重放 cursor 不变，数值递增与之冲突；真正单调递增的是平台 `kb_state.json.version`（`02-CONTRACTS.md` §4.2），不是 doc2md `kb-manifest.cursor`。L2 按内容寻址依赖。若独立 QA 在 G-4 闭环后坚持数值递增，再回 TL 修订，不影响 L2 当前实现 |
| 2 | 本 loop 无四件套，`read_set_digest` 退化为「源文件读取集」规范序 sha256，L3 后改 `store.read_set_digest` | **采纳，且是正确分层**。L3 必须显式完成口径切换并补一条回归断言 |
| 3 | 扫描枚举所有普通文件、跳过隐藏项与 `kb-manifest.json`、隔离子夹具目录 | **采纳**。PLAN 未要求递归/扩展名过滤，不构成放宽；L2 若需按 `route_type` 过滤，在队列层做，不改 `kb_diff` 扫描语义 |
| 4 | CLI additive 新增可选 `--parser-fingerprint` | **采纳**。A3 需要该入参，且默认沿用上轮登记值，不改变既有命令 |
| 5 | `CONTENT_CHANGED` 分支本 loop 无断言覆盖 | **记为已知覆盖缺口**，不阻塞 L1 内部收口；要求 L2 补一条 R-7 反例（仅内容变、文件集不变 → `CONTENT_CHANGED`），写入 `P1-L2-PLAN.md` |
| 6 | `--help` exit 1 是既有基线缺陷 | **02:37 修正：成员判断成立**。anaconda3 下改动前后 exit 1 且 `TypeError` 行逐字一致、5 个失败项同名；doc2md-toolenv 下 exit=0 但缺 `jsonpatch` 无法跑全量。按 §四 分用途双解释器裁定，成员原口径有效，无需返工 |
| 7 | A1 语料正文误把 F3 写进磁盘 | **PLAN 笔误，已修订**（见 §二）。成员按期望分集构造夹具是对的，无需返工 |

**R-7 新增反例（L2 承接）**：语料「文件集合不变、仅 1 个文件字节改变」→ `reason=CONTENT_CHANGED`、`added/removed` 为空、`changed=[该文件]`。
