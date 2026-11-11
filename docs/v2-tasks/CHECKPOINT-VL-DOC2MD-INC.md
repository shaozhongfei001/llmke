# CHECKPOINT · VL-DOC2MD-INC（P0 收口 / P1-L1 开工）

- 时间：2026-11-08 02:20+08:00
- 工作流：`docs/dispatch/DOC2MD-INCREMENTAL-LONG-RUN-DISPATCH.md`
- 台账：`docs/v2-tasks/TASKS.yaml`（`T-D2MD-00` VERIFIED / `T-D2MD-01` DOING）
- 角色：TL = 主 agent（切片、规划、baton）；`python-engineer` = 团队 `vl-doc2md-inc` 异步成员；`independent_qa` 待 G-4

> 旧的 `docs/v2-tasks/CHECKPOINT.md`（2026-11-02，VL1）保留不动，本文件是 `VL-DOC2MD-INC` 切片的独立检查点。

---

## 一、Gate 状态

| Gate | 结论 | 依据 / 时点 |
|---|---|---|
| G-5 C1/C2/C3 | **闭环** | Owner 2026-11-08「同意复工」：解除 doc2md 边界、取代旧派工单、重排切片。口径以落盘派工单 + `TASKS.yaml` 为准，Gate 时点按表内「何时必须」列 |
| G-4 独立 QA principal + 公钥 | **未闭环** | 时点为「首个 QA_PASS 签署前」，不阻塞开工；但 Loop 1 走到 `DEV_SELF_CHECK_PASS` 后 baton 必须挂起。TL 不代签、实现角色不自签 |
| G-1 C12 `database_desc` | 未闭环 | Owner，P5-3 前 |
| G-2 改进 4 放行阈值 | 未闭环 | P6 压测数据，P6 放量前 |
| G-3 C9 容量目标 | 未闭环 | 业务方，P6/P7 压测前 |

## 二、已完成

| 项 | 证据 |
|---|---|
| P0-L0 基线冻结 | `docs/dispatch/evidence/hybrid-baseline-doc2md-v2.json`（17 query、ES kb_9=44 / kb_1004=4520），只读脚本，未覆盖旧基线 |
| P0-L0 Gate 收集 | `memory/BLOCKED.md` §二（后追加复工批复段） |
| P0-L0 反例 | 错 `INGEST_READ_PREFIX` → `__wrongprefix_kb_9` HTTP 400 / `v2cand_kb_9` HTTP 404，不静默命中旧索引 |
| 停工登记与复工批复 | `memory/BLOCKED.md` 头部复工段 |
| P1-L1 开发前验证标准 | `docs/v2-tasks/loops/P1-L1-PLAN.md`：A1/A2/A3 可证伪断言、R-1~R-6 反例、验收命令、scope 红线、回滚、baton |
| 台账更新 | `TASKS.yaml`：`T-D2MD-00` → VERIFIED（evidence/artifacts 补齐）、`T-D2MD-01` → DOING（三条 acceptance、blocker 清空） |

## 三、进行中

- **P1-L1** `scan-diff --kb` + `kb_diff.py`：已派工 `python-engineer`（team `vl-doc2md-inc`，`acceptEdits`，异步执行）。
- 任务书要点：外部仓库 `/home/szf/data/dev/doc2md`；新增 `kb_diff.py` / 测试 / 夹具，`cli/main.py` additive 注册 `scan-diff`；先造 6 条反例 FAIL 再实现转 PASS；`DEV_SELF_CHECK_PASS` 证据写入 `docs/v2-tasks/evidence/P1-L1-<timestamp>.log`。
- 已告知红线：不得动既存 modified `document_ir_builder.py`；不得改 `parsed_text.md`；不得越界改 llmke-v2 生产代码/设计包/`MANIFEST.sha256`/`TASKS.yaml`；不触碰 L2~L5 内容。

## 四、G-4 复核结论与自动推进策略（D-01）

### G-4 复核（02:23，全仓级）

| 检索 | 结果 |
|---|---|
| `BEGIN PUBLIC KEY` 全仓命中 | 仅 `QA-HANDOFF-V1.0.md` / `QA-KEY-HANDOVER-V1.0.md` / `INDEPENDENT-QA-PROMPT.md` / `memory/BLOCKED.md`，全部为**占位模板**（`<key_id>`、`qa-external-pending`、`…`）或示例输出（`qa-external-02` / `qa-ed25519-indep`） |
| 信任根 | 只有 `docs/ci/TRUST-ROOT.example.json`（`approved_baseline_sha256: null`），无 `PROTECTED_RUNNER` 实配 |
| 签名工具/产物 | `scripts/qa_sign.py` 存在；无 `verify_envelope.py`；全仓无 `.sig` / `QA_PASS` / attestation 产物 |

**结论：G-4 确未闭环，且不可由 TL 代签或伪造。**

### 策略决策 D-01（依据 Owner 2026-11-08「继续下一轮，后续各阶段如发现结束都完成验证自动进入下一轮」）

把派工单 §七-2 的「阶段收口」拆成**两层**，使长程流不因 G-4 卡死，同时不触碰「不代签」红线：

| 层 | 条件 | 效果 |
|---|---|---|
| **内部推进条件** | `DEV_SELF_CHECK_PASS` + TL 复核（现场命令与真实输出齐备、`git status` 无越界、反例 FAIL→PASS 可复现） | 满足后**自动派工下一 loop，不再请示**（Owner 已授权） |
| **正式签署条件** | `QA_PASS` | 由 `independent_qa` 在 G-4 闭环后，对已完成的全部 loop **批量独立复跑 + 变异测试（mutate→FAIL / restore→PASS）** 后补签 |

约束（不放宽）：
- G-4 闭环前，任何 loop **不得标 `DONE` / `VERIFIED`**；`TASKS.yaml` 保持 `DOING` 并只补 `evidence`；
- TL 不代签、不伪造签署身份；实现角色绝不自签 `QA_PASS`；
- 所有 loop 的 baton 记 `WAIT_QA_ATTESTATION`，按完成顺序排队；
- 若独立 QA 复跑发现反例，`QA_PASS` 驳回的 loop 及其后续依赖 loop 一起回退重做。

### Loop 2 准备

`docs/v2-tasks/loops/P1-L2-PLAN.md` 已锁定开发前验证标准（B1 dry-run 零写入 / B2 失败项带 `fail_reason` / B3 缺路由结果不得入队，R-1~R-6 反例）。**标准先行，不代表已启动实现**；待 Loop 1 内部收口后自动派工。

### 当前成员状态（02:26 更新）

- team `vl-doc2md-inc` 已建，成员已注册且**具备写权限**；催办消息 `read: true`。
- 已产出 `backend/tests/fixtures/kb_diff_corpus/`（未跟踪）：主夹具 `kb-manifest.json` + `F1/F2/F4/F5`，子夹具 `corrupt/`（R-5）、`no_change/`（R-1）。`kb_diff.py`、测试、`scan-diff` 注册、evidence log 尚未产出——符合「先造反例 FAIL → 再实现」的 Loop Engineering 顺序。
- doc2md 既存 `M backend/app/services/document_ir_builder.py` 保持原样，未被覆盖。

### TL 复核证据：夹具可证伪性 PASS（02:26）

```
磁盘实算  F1=c4679e05…  F2=ff65e478…  F4=c4679e05…  F5=5525cb83…
manifest  F1=c4679e05…  F2=df633c4a…  F3=afac1838…  F4=c4679e05…（磁盘无 F3）
推演  added=[F5] removed=[F3] changed=[F2] unchanged=[F1,F4]  → 与 A1 精确一致
```

同时确认夹具覆盖 R-6（F1/F4 同 sha256 不同 `file_id`）、R-5（corrupt manifest 必须抛错而非静默按空库重建）、R-1（NO_CHANGE）。已把复核结果回传成员，避免返工。

### TL 独立复核：阶段 A 桩判别力（02:27）

成员按 Loop Engineering「先造反例 FAIL」产出阶段 A 桩（`kb_diff.py` docstring 明示故意错实现），并 additive 注册 `scan-diff`（`cli/main.py:1216+`）、新增常量 `KB_MANIFEST_FILENAME`（`parsed_paths.py`，仅 5 行）。

```
桩实跑 compute_kb_diff(...) → added=['F1','F2','F4','F5'], removed=[], changed=[], unchanged=[], reason='STUB'
A1 断言对该桩判定 = FAIL  → 判别力成立（FAIL 出现在断言层，不是 ImportError 层）
```

越界自查：`cli/main.py` +77 行纯追加、`parsed_paths.py` +5 行常量；既存 `M document_ir_builder.py` 仍为 `17+/2-`，未被覆盖。测试文件与 evidence log 尚在产出（阶段 B 正式实现将覆盖桩）。

## 五、红线自查（本 checkpoint 前）

未改设计包任何文件（`sha256sum -c MANIFEST.sha256` 9 项通过）；交付包留痕 `79127fae47d3900dc4119ebff47242b8528ed51fde0ebb5e409d06d5d2357a2e` 仍有效；未改 `services/**`、`platform/r12/conf/**`、`contracts/registry.yaml`；未起停服务；未写 `QA_PASS`；未代签。

## 六、P1-L1 内部收口（02:31，D-01 第 1 次自动推进）

TL 独立复跑（不采信成员自证），证据：`docs/v2-tasks/evidence/P1-L1-TL-VERIFY-20261108.log`。

| 判据 | 结果 |
|---|---|
| 阶段 A 桩判别力 | PASS（A1 对桩 FAIL，FAIL 在断言层） |
| 单元测试 | 10 passed（doc2md-toolenv 3.11.7） |
| A1 / A2 / A3 / R-1 / R-4 / R-5 | 全 PASS（含 A3 双夹具口径） |
| 既有命令回归 / 越界自查 | PASS；既存 `M document_ir_builder.py` 仍 17+/2-，未改 `parsed_text.md` |

**三处口径修正（TL 修订 `P1-L1-PLAN.md`，未放宽标准）**
1. 解释器：系统 `python3`=3.10.12 会误报 `datetime.UTC` ImportError；强制用 `/home/szf/data/dev/doc2md-toolenv/bin/python`（3.11.7）。
2. A3 歧义：原 PLAN 未指定夹具，TL 用主夹具得 `FILE_SET_CHANGED` 曾判 FAIL；核对 `02-CONTRACTS.md:269` 优先级后确认实现正确。改为 `no_change/` 主断言 + 主夹具优先级哨兵。
3. 既有测试基线：`pytest backend/tests -q` 的 4 个 collection error 均因既有 venv 缺 `jsonpatch`（`extensions/review/patches.py:34`），相关目录无改动；判据改为「既有 error 数量不增加」。

**状态**：`T-D2MD-01` 保持 `DOING` + `WAIT_QA_ATTESTATION`（不标 DONE/VERIFIED，未签 QA_PASS）；成员需补自己的 `P1-L1-<ts>.log` 与正式回报。按 D-01 内部推进条件满足，**已自动派工 `T-D2MD-02`（L2）**，标准见 `P1-L2-PLAN.md`，未请示。

## 七、成员自证核验与 TL 裁定（02:34）

成员补齐 `docs/v2-tasks/evidence/P1-L1-20261108T023149.log`（23 KB）：结论 `DEV_SELF_CHECK_PASS`、阶段 A `9 failed,1 passed` → 阶段 B `10 passed`、未签 `QA_PASS`、baton 挂起，合规。TL 已把 `T-D2MD-01.evidence` 改指该 log，TL 复核 log 保留为第二份证据。

成员 §6 标注 6 处判断，TL 逐条裁定写入 `P1-L1-PLAN.md` §八：cursor 内容寻址采纳（数值递增归平台 `kb_state.version`）、read_set_digest 退化口径采纳（L3 切换并补回归）、扫描范围采纳、`--parser-fingerprint` additive 采纳、`CONTENT_CHANGED` 无覆盖记为缺口并转成 `P1-L2-PLAN.md` 的 **R-7 反例**、A1 语料笔误由 TL 修订。

**关键裁定：解释器唯一口径**

| 解释器 | 版本 | click | `--help` exit |
|---|---|---|---|
| `/home/szf/anaconda3/bin/python`（成员 L1 log 所用） | 3.11.7 | 8.4.1 | **1**（Typer 0.15.1 兼容缺陷） |
| `/home/szf/data/dev/doc2md-toolenv/bin/python`（项目专用、TL 复核所用） | 3.11.7 | 8.1.8 | **0** |

系统 `python3`=3.10.12 更因 `datetime.UTC` 直接 ImportError。

> **02:37 撤回修正（TL 误判，已改 `P1-L1-PLAN.md` §四）**：02:34 的「唯一用 doc2md-toolenv、禁用 anaconda3」只比较了 `--help` 退出码，未跑全量基线。02:37 补测：
>
> | 解释器 | 全量 `pytest backend/tests -q` | `--help` |
> |---|---|---|
> | anaconda3 3.11.7 / click 8.4.1 | `5 failed, 1507 passed, 133 skipped`（基线 `5 failed, 1497 passed`，失败项同名、passed +10） | exit 1，**既有基线**、改动前后一致 |
> | doc2md-toolenv 3.11.7 / click 8.1.8 | `4 errors during collection`（缺 `jsonpatch`，无法全量比对） | exit 0 |
>
> **新裁定：分用途双解释器**。全量回归基线比对与 `test_kb_diff.py` 用 anaconda3；CLI 独立复跑与生产解析路径用 doc2md-toolenv（TL 的 A1/A2/A3 复核基于此）。两者下 `test_kb_diff.py` 均 10 passed。**成员 L1 log 的 anaconda3 口径有效，无需返工、无需补跑**；已撤回 02:34 的补跑指令，`T-D2MD-01.blocker` 中该条已移除。后续 evidence 必须显式标注解释器与用途。

同时修订 `P1-L1-PLAN.md` §七 原文「未签 QA_PASS 不得启动 L2」——与 D-01 两层收口冲突，已改为内部推进条件满足即自动派工 L2。L2 派工消息确认已送达（`read: true`）。

## 八、成员正式报告核验与证据可提交裁决（02:37）

成员 `send_message` 正式回报 `DEV_SELF_CHECK_PASS`（未签 `QA_PASS`、未标 DONE/VERIFIED），TL 逐项复核其交付物指纹，**全部吻合**：

```
kb_diff.py            e9dc1cdf87433ecfe5eb9863002bdb97
test_kb_diff.py       1c2cca32473aa324a00ab551335af6c2
cli/main.py           50399ad3d1d705366c92fbb8d931c9a5   (+77/-0 纯追加)
parsed_paths.py       2114d7f4ec0150391d6d44d9c183862d   (+5/-0 常量)
document_ir_builder.py bb69758a09333f23673c12d3f128463d  (既存 M，未被覆盖)
```

**证据 `.log` 被 `.gitignore:34 *.log` 忽略**（`:62` 的 negation 只覆盖 `loops/*/evidence/`）。TL 裁决：按同文件 `:59-61` 既有注释「gate evidence IS the delivery record / Without this negation the evidence chain dies at the first commit」的设计意图，补一行 `!docs/v2-tasks/evidence/*.log`（`.gitignore:65`）。影响面：`docs/v2-tasks/evidence/` 下 **6 个 `.log`**（含 4 个历史 VL0/VL1 证据）现为 `??` 可跟踪；**TL 未 git add、未改名、未造冗余产物**，是否入库由 Owner/后续提交决定。

**P1-L1 正式内部收口**：成员自证 log + TL 独立复核 log 双证据；`T-D2MD-01` 保持 `DOING` + `WAIT_QA_ATTESTATION`，`QA_PASS` 待 G-4 闭环后由 `independent_qa` 批量补签。成员报告「未进 P1-L2」已由 TL 回消息澄清：D-01 下 L2 派工有效，继续执行 `T-D2MD-02`。

### 02:39 时序冲突与紧急纠正（异步成员消息队列延迟）

成员回复「YES_WRITE_TOOL」并表示将一律改用 doc2md-toolenv、**在 L1 log 追加更正节并把 anaconda3 记录标为作废** —— 这是按 **02:34 已撤回裁定**执行，而其 inbox 中 02:38:32 的撤回消息已 `read=True`，判断为该回复在收到撤回前生成。

TL 已发紧急纠正（优先级高于 02:34 及该回复）：
1. **L1 evidence log 保持原样**：核实 `P1-L1-20261108T023149.log` 仍为 02:35:02 版、414 行、md5 `0390675bdb358e6ff525082948e570de`，**尚未被追加**；不追加 doc2md-toolenv 更正节、不作废 anaconda3 记录。
2. 有效口径仍是 §七 的**分用途双解释器**；禁止把 doc2md-toolenv 下 `4 errors during collection`（缺 jsonpatch）当全量回归证据。
3. 后续 evidence 只需显式标注解释器与用途。
4. `YES_WRITE_TOOL` 已确认并登记，无需改派；成员直接开始 L2。

**结论**：无文件被污染，无标准被放宽，无返工。

### 02:43 后续核验与 L2 正式派工

02:41 成员仍追加了 L1 log §9.4~§9.6（579 行 / md5 `d27ee87e…`）。TL 复核裁定：
- **§9.5 / §9.6 保留**：A3 双夹具真值（主夹具+错 fp → `FILE_SET_CHANGED` 优先级哨兵；`no_change/` → `PARSER_FINGERPRINT_CHANGED`）、R-7 `CONTENT_CHANGED` 真值预告，均符合裁定。
- **§9.4 一处口径需修**：其「以本节 4 errors 基线为准」把 doc2md-toolenv 的 `4 errors during collection`（缺 `jsonpatch`）误作全量回归裁定口径。已要求成员改为 §七 双解释器口径 —— 全量回归**主判据**是 anaconda3 下「既有 5 failed 数量不增加」，doc2md-toolenv 的 4 errors 仅作环境说明。仅改该句 + 追加一行裁定更正，**不改 `kb_diff.py`**。
- 已发正式 L2 派工：B1/B2/B3 + R-1~R-7 先 FAIL 再 PASS；新增 `parse_queue.py` / `test_parse_queue.py`；替换 `cli/main.py:1076-1083` 两个 placeholder；复用既有服务层不引入第二套解析者；evidence 标注解释器与用途；只回报 `DEV_SELF_CHECK_PASS`。

**当前**：`T-D2MD-01` 内部收口完成、`QA_PASS` 挂起待 G-4；`T-D2MD-02` 已派工，等待成员产出。

## 九、Owner 选 A：G-4 闭环方案与待提供输入（02:5x）

Owner 裁定：**「指定独立 QA 身份并给公钥 → 闭环后批量补签」**。TL 接受该方案，但 G-4 的闭环**需要 QA 一方提供真实输入，TL 不可代劳**——`qa_sign.py` / `verify_envelope` / `loop_guard.py` 三层均强制私钥与主体在实现方之外。

### 必需的三项输入（`QA-KEY-HANDOVER-V1.0.md` §1）

| # | 输入 | 硬约束 |
|---|---|---|
| 1 | `principal_id` | 不得等于实现方（`integration-agent` / `legacy-owner` / `python-engineer` / TL）；`loop_guard.py:234` 会校验 |
| 2 | `key_id` | 写入 trust root 与信封，例 `qa-ed25519-indep` |
| 3 | `public_key_pem` | Ed25519 公钥 PEM（三行含首尾）；**私钥绝不外传** |

QA 侧受保护机器生成（**不可由 TL 在这台开发机生成**：实现方持有私钥即触发 §5 拒绝条件）：

```bash
mkdir -p ~/data/qa-keys && chmod 700 ~/data/qa-keys
openssl genpkey -algorithm ED25519 -out ~/data/qa-keys/llmke-qa.key
chmod 600 ~/data/qa-keys/llmke-qa.key
openssl pkey -in ~/data/qa-keys/llmke-qa.key -pubout -out ~/data/qa-keys/llmke-qa.pub
cat ~/data/qa-keys/llmke-qa.pub    # 只需把这段发给 TL
```

### 信任根（受保护 runner，`LLMKE_TRUST_ROOT` 指向工作区外绝对路径）

```json
{
  "environment": "PROTECTED_RUNNER",
  "approved_baseline_sha256": "16820da6d8ddc75df9701082a78118265f9688edf410bfdd032a2da71ef1b157",
  "principals": {
    "<key_id>": {
      "principal_id": "<principal_id>",
      "roles": ["qa-owner"],
      "public_key_pem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
      "enabled": true
    }
  }
}
```

`approved_baseline_sha256` 已按**当前** `docs/baseline/FROZEN-MANIFEST.json` 实算更新为 `16820da6…`；`QA-HANDOFF-V1.0.md` / `QA-KEY-HANDOVER-V1.0.md` 中的 `c8a73c37…` 是旧基线示例，**不可照抄**。`verify_envelope` 会逐条校验 `environment` / 基线哈希 / `roles` / `principal_id` 是否在 `implementation_principals` 内。

### 批量补签流程（每 loop 逐个；`qa_payload.py` 载荷 1 小时过期，须签署前重生成）

```bash
python3 scripts/qa_payload.py --loop <loop_id> --gate independent_qa_gate \
  --principal-id <principal_id> --out /tmp/qa-payload.json
python3 scripts/qa_sign.py --key-file <工作区外私钥> --key-id <key_id> \
  --payload /tmp/qa-payload.json --out /tmp/qa-attestation.json   # 只能在受保护 runner
python3 scripts/loop_guard.py accept-qa --loop <loop_id> --gate independent_qa_gate \
  --attestation /tmp/qa-attestation.json
python3 scripts/loop_guard.py finish --loop <loop_id>
```

### 03:1x 复核更正：补 `QA_PENDING` 的原方案不可行（TL 误判，已作废）

原文曾写「拿到公钥后补 `loops/<id>/LOOP.yaml` + `loop_guard.py qa-run` 的 `QA_PENDING` 候选运行记录」。TL 03:1x 复核源码发现该路径**会破坏冻结基线**：

```
scripts/freeze_baseline.py:19   for p in (root/'loops').glob('*/LOOP.yaml'): out.append(...)
→ loops/*/LOOP.yaml 属于控制面；FROZEN-MANIFEST.json 已含 loops/
scripts/loop_guard.py:189       frozen = frozen_errors(Path(root)); if frozen: raise ContractViolation(...)
→ run_gate / qa-run / accept-qa 一开头就校验控制面，新建 LOOP.yaml 即报
  'controlled baseline files changed'，全链路失效
```

除非 Owner 授权**重新冻结基线**（改 `FROZEN-MANIFEST.json` 并同步 `approved_baseline_sha256`），否则不能新建 `loops/`。该方案作废。

**可选签署载体（请 Owner 指定）**：

| 路径 | 做法 | 代价 |
|---|---|---|
| **A（推荐，不动基线）** | 轻量签署：独立 QA 主体对「已完成 loop 的证据摘要清单」（每份 evidence 文件 sha256 + 独立复跑结果 + 变异测试结果）生成 Ed25519 签名信封；TL 按信任根公钥验签后记录 `QA_PASS` | 不依赖 `loop_guard`、不碰冻结基线；需 TL 补一个独立验签脚本 |
| **B（需 Owner 授权）** | 重新冻结基线 → 建 `LOOP.yaml` → `qa-run` → `accept-qa` → `finish` | 改 `FROZEN-MANIFEST.json` 与 `approved_baseline_sha256`，影响全部受控门禁 |

两路径都仍需：三项输入到位、独立主体执行 **批量独立复跑 + 变异测试（mutate→FAIL / restore→PASS）**、TL 不代签、实现角色不自签。
另注：`P1-L3` 已于 03:12 产出 `DEV_SELF_CHECK_PASS` evidence，待签队列随之增至 3 个 loop（L1/L2/L3）。

### 待签队列（均 `DEV_SELF_CHECK_PASS`，`QA_PASS` 挂起）

| loop | 任务 | 自证时间 |
|---|---|---|
| P1-L1 | `T-D2MD-01` | 02:31 |
| P1-L2 | `T-D2MD-02` | 02:48 |

### 红线（不放宽）

TL 不代签、不伪造签署身份、不生成 QA 密钥对、不把私钥引入工作区；实现角色绝不自签；G-4 闭环前任何 loop 不得标 `DONE` / `VERIFIED`，`TASKS.yaml` 保持 `DOING` + `WAIT_QA_ATTESTATION`。

## 十、P1-L2 内部收口与 P1-L3 派工（02:55，D-01 第 2 次自动推进）

成员正式回报 `T-D2MD-02` `DEV_SELF_CHECK_PASS`（未自签 `QA_PASS`、未标 DONE/VERIFIED）。TL 按 D-01 做独立复核，结论**通过**，证据 `P1-L2-TL-VERIFY-20261108.log`：

| 复核项 | 结果 |
|---|---|
| 6 个交付物 md5 | 与成员报告全部吻合；`kb_diff.py` / `document_ir_builder.py` 未被改 |
| doc2md `git status` | 8 项（2 additive M + 1 既存 M + 5 新增）；`cli/main.py` 4 行删除逐行核对恰为两个 placeholder |
| `test_parse_queue.py` 独立复跑 | `12 passed in 1.96s` |
| B1 / R-4 | 两次 `--dry-run` `exit=0/0`、`q1==q2`、manifest 未变、无队列文件；items 恰 F5(added)/F2(changed)，字段齐全 |
| B3 | 显式 `--routes {}` → `items=[]`、rejected 2 条带 `ROUTE_RESULT_MISSING` |
| 全量回归主判据（anaconda3） | `5 failed, 1519 passed, 133 skipped`；失败项同名、数量未增（基线 5/1497 → L1 5/1507 → L2 5/1519，+12 = L2 新增 12 测试） |

**解释器口径一次性收口（02:58 修订）**：TL 在 02:43 / 02:55 读到的是补正前快照（L1 579 行 / `d27ee87e…`、L2 378 行），一度判定纠正未生效。02:58 复核确认成员已于 **02:44** 按 02:43 裁定完成补正：L2 头部改分用途双解释器、新增 §9 有效口径表与双解释器真实输出；L1 §9.4 改主判据表述；两 log 末尾各有更正/留痕行。当前指纹 L1 590 行 / `1eb2e84c…`、L2 483 行 / `244ac9f5…`。剩余旧字样均为历史叙述或原文留痕，由 L2 §9 与末尾更正行覆盖。**裁定：口径已一致，L1 封存、不再返工补跑**；有效口径为 §七 分用途双解释器。TL 复核证据 `P1-L2-TL-VERIFY-20261108.log` §4 已同步修订（初版结论基于旧快照，非成员未执行）。

**L2 遗留转 L3**：① 默认路径 `route_type=UNKNOWN` 仍入队 PENDING（`parse_queue.py` 注释已声明），B3 只覆盖显式 `--routes` 缺项路径 → 列为 L3 的 R-7，须先回 TL 确认处置口径；② `DefaultParseRunner` / `DefaultIdempotencyChecker` 只做 `--dry-run` 验收，真实端到端解析属 L3/后续；③ 默认语料根用 L1 夹具，生产由 `--path`/`--cursor` 注入；④ 注入文件应放 `--path` 之外。

**P1-L3 派工**：`docs/v2-tasks/loops/P1-L3-PLAN.md` 已按「开发前锁定断言」写好（C1~C5 + R-1~R-7、幂等键契约、双解释器验收命令、回滚）。明确授权**唯一一个 llmke-v2 文件** `scripts/v2_ingest_doc2md.py`（设计包 `03-IMPLEMENTATION.md:107` 要求移除 `_reset_vault_state` 与 `--force`），要求改动前记录 md5、改动后附 `git diff` 全文；不改运行态、不启用 18096、不启停服务。`TASKS.yaml` 已把 `T-D2MD-02` 补齐双证据、`T-D2MD-03` 置 `DOING`，两者均保持 `WAIT_QA_ATTESTATION`。

### 02:58 R-7 口径裁定（TL 独立核实后批准）

成员填 `P1-L3-PLAN.md` §六 请求确认。TL 现场核实：① L1 夹具 `F1/F2/F4/F5` 无扩展名 → `match_route_type` 返回 `UNKNOWN`；② `parse_queue.py:192-208` `DefaultParseRunner.parse()` 对非 MinerU 类型走 `MarkItDownParserService.parse_markitdown`，`except` 兜底保留失败项（B2）；③ L2 B1 已锁定队列含 F2/F5；④ 平台脚本改动前 md5 `c16e6986…` / sha256 `a7f78bc4…` 与成员记录一致；PLAN 仅 §六 被填写，其它段落未动。

**裁定：批准「默认解析器（保留入队 + 显式登记）」**，不改 L2 `parse_queue.py`、不放宽为「不测」。
**追加约束**：R-7 断言除队列状态外，**必须验证调度事实** —— 用注入替身 / mock 断言 UNKNOWN 项确实被派给 `MarkItDownParserService`（非 MinerU 分支）并返回可观测的 `ParseOutcome`；防止「留在队列」被当作「默认解析器」的假绿。不启停服务、不写 DB/ES/Milvus。

### 03:0x L3 两处语义裁定（TL 复核后给出）

成员阶段 A 反例已落盘（`8 failed, 3 passed`，8 条断言层 FAIL），并提出两处需裁定的设计判断。TL 现场核实：`KbFileContent`（`backend/app/models/file.py:49-69`）无 `kb`/`source_root` 字段、`config/app.yaml` 只有 `name: personal-kb`、`parse-markitdown` CLI 无 `--kb`；`markitdown_parser.py:481/582/646` 三处用 `datetime.now(UTC)` 生成 `generated_at`。

| 裁定 | 结论 |
|---|---|
| A · `kb`/`source_root = None` | **接受为 L3 过渡，但列为已知限制**。四字段必须全部存在且为 JSON `null`（不缺字段、不用空串）；C5 断言须明写「四字段存在，其中两个允许 null」，不得缩水成只查两字段；evidence 标注「真实值由 L1 库级 `kb-manifest.json` 承载」并转后续切片；**`read_set_digest` 的计算不得依赖这两个 null 字段**，否则不同库同内容会算出同一 digest、幂等键失去库隔离 |
| B · `generated_at` 取值语义变更 | 方案「由源文件 sha256 派生确定性 ISO Z 时间」符合 `03-IMPLEMENTATION.md:106` 与 PLAN §三，但与 C5 字面「既有键语义不变」冲突。**裁定：C5 的『语义不变』限缩为「键存在、类型与 ISO 格式不变、既有消费者可解析」**；`generated_at`/`converted_at` 由 `now()` 改为确定性派生是本 loop 唯一授权的取值语义变更，必须在 evidence 显式声明、在 C5 断言写明，不得悄悄绕过。`markitdown_parser.py` 三处 `now()` 须全部覆盖或逐处说明 |

另要求 evidence 给出 `compute_read_set_digest` 与平台 `store.py` 的具体对齐路径 + 一处真值比对，并说明 `parsed_text.md` 仍按原始字节参与摘要（铁律：内容与 hash 不变）。

## 十一、P1-L3 内部收口与 P1-L4 派工（03:18，D-01 第 3 次自动推进）

成员正式回报 `T-D2MD-03` `DEV_SELF_CHECK_PASS`。TL 独立复核**通过**，证据 `P1-L3-TL-VERIFY-20261108.log`：

| 复核项 | 结果 |
|---|---|
| 9 个交付物 md5 | 全部吻合；`document_ir_builder.py` / `kb_diff.py` / `parse_queue.py` / `cli/main.py` 未被改 |
| 两仓越界 | doc2md 12 项（5 M + 7 ??）；llmke-v2 仅 `M scripts/v2_ingest_doc2md.py`（唯一授权）；HEAD 版 md5 `c16e6986…` = 成员记录的改动前值，无既存 M |
| 平台脚本 diff | `_reset_vault_state` 定义/调用与 `--force` 已删，`_needs_reparse` 保守重解析（无 manifest / 缺 additive 字段 / 口径不可得 / fingerprint 或 digest 不符 → 一律重解析，不静默跳过）；静态 grep 零命中 |
| R-7 追加断言 | 两条落地：队列状态 + `unittest.mock.patch` 双拦截的调度事实（走 `MarkItDownParserService`、MinerU 未调用、`ParseOutcome` 可观测）✅ |
| TL 语义裁定 A | `compute_read_set_digest` 只扫产物文件、不读 manifest 的 `kb`/`source_root` ✅；digest 与库无关是内容寻址必然，库隔离由库级清单承担 |
| TL 语义裁定 B | `markitdown_parser.py:487/:598` 已改确定性时间；第三处 `:661-662` 在 `_write_report()` 报告文件，不进四件套/摘要 → 接受，需补说明 |
| 反例 FAIL→PASS | 阶段 A `8 failed, 5 passed` → 阶段 B `13 passed`，TL 独立复跑 `13 passed in 0.31s` |
| 全量主判据（anaconda3） | `5 failed, 1532 passed, 133 skipped`；失败项同名、数量未增（L2 `5/1519` → L3 `5/1532`，+13 = 新增 13 条测试） |

**发现 3 处证据层面的小缺口**（均不影响功能、不改实现语义）：① evidence §6 `numstat 48 34` 实为首个 hunk `@@ -62,34 +62,48 @@` 计数误读，现场 `git diff --numstat` = `71 49`（diff 全文 `index` 与 md5 均一致）；② `test_idempotency_key.py` 头部 docstring 仍写「当前不含 R-7」，与已补两条测试矛盾；③ `_write_report` 的 `now()` 与「digest 与库无关」口径未在 evidence 显式说明。已要求成员做注释/数字级补正，不重跑测试。

**P1-L4 派工**：`docs/v2-tasks/loops/P1-L4-PLAN.md` 已锁定（D1~D5 + R-1~R-6，四件套、原生第 4 件、IR span 对齐、三件套字节不变）；L3 收口后 `mineru_pdf_parser.py` 无并行写入冲突 → 已派工 `T-D2MD-04`。PLAN 明确「本 loop 只做离线 fixture，A-2 四类格式真实上传留待 P6」。

### 03:2x L3 增量补强复核（结论不变）

成员按 TL 03:0x / 03:18 裁定做了增量补强，evidence 由 442 行 / `afe3dd6e…` → **569 行 / `206bc4e3…`**（新增 §11.1~11.5，原文留痕保留）。TL 现场复核通过：

- 当前指纹：`markitdown_parser.py 815a447b…`、`test_idempotency_key.py a9928157…` 已变；`parsed_paths.py` / `mineru_pdf_parser.py` / 平台脚本 / L1·L2 产物 / `document_ir_builder.py` 均未变。
- 裁定 A：C5 断言明写四字段 + `null`、未缩水；摘要对 `kb`/`source_root` 不敏感有新增断言；库隔离口径明确由 per-kb 清单与 `(file_id, sha256)` 复合键承担。
- 裁定 B：`:598` 失败 manifest 补改确定性时间（覆盖 parsed_dir 内全部 manifest 写入路径）；`:661/:662` 批次报告保持 `now()` 并逐处说明不受影响。TL 认可 —— 属补齐已授权范围遗漏，非新增语义。
- 裁定 4：平台 `parse_artifact/store.py:160` 与 doc2md `compute_read_set_digest` 同目录真值 `77a4cc1d…` EQUAL=True；`parsed_text.md` 按原始字节参与。
- **变异验证非空转**：`null → ""` 变异令 C5 真实 `1 failed in 0.04s`，恢复后 `13 passed` 且 `parsed_paths.py` md5 精确复原。
- TL 独立复跑 `13 passed in 0.20s`；anaconda3 全量 `5 failed / 1532 passed / 133 skipped`（失败数 5 不变）。

`P1-L3-TL-VERIFY-20261108.log` 已追加 §11 记录补强，头部注明 §1 指纹为 03:18 快照、当前值以 §11 为准。§8 三处补正全部闭环。**`DEV_SELF_CHECK_PASS` 不变，L4 派工继续有效。**

## 十二、P1-L4 内部收口与 P1-L5 派工（03:31，D-01 第 4 次自动推进）

成员回报 L3 三处补正闭环 + `T-D2MD-04` `DEV_SELF_CHECK_PASS`。TL 独立复核**通过**，证据 `P1-L4-TL-VERIFY-20261108.log`：

| 复核项 | 结果 |
|---|---|
| 交付物 / 越界 | doc2md 13 项（5 M + 8 ??）；`mineru_pdf_parser.py 90/2`（L4 纯新增 72 行，2 行删除属 L3 已授权）；平台 `v2_fill_mineru_ir.py` md5 == HEAD 版 `587946bb…`、`v2_ingest_doc2md.py` 仍 `840ebfef…` → **llmke-v2 本轮 0 代码改动** |
| D2 静态断言「收紧」 | 从「字面不出现」改为检查 `fill_mineru_ir(` 调用 / `from scripts.v2_fill_mineru_ir` 导入，保留 `validate_document_ir` + provenance 无 `ir_filled_by` + `ir_source=mineru_content_list` 运行时断言 → **裁定：收紧合理、不构成放宽**；覆盖边界（静态只覆盖显式形式，主防线是运行时 provenance）已记录 |
| 反例 / 独立复跑 | 阶段 A `7 failed, 1 passed` → 阶段 B `8 passed`；TL 复跑 `8 passed in 0.31s`；anaconda3 全量 `5 failed, 1540 passed, 133 skipped`（失败数 5 不变、+8 = 新增 8 条测试） |
| L3 补正 | log 590 行 / `c158bd05…`：numstat `71 49`、docstring「R-7 已补齐两条」、§12 两行口径说明，均注释/数字级 |

**上线注意（如实）**：L4 新增第 4 件后产物集合变化，`read_set_digest` 相对 L3 会改变 → L3 历史 manifest 与新口径不符，`_needs_reparse` 会触发**历史产物一次性重解析**。属预期迁移、非缺陷，但切读/放量前需预估重跑成本并避免与在线链路并发写同一产物目录。本 loop 全为离线 fixture，A-2 留待 P6。

**P1-L5 派工**：`docs/v2-tasks/loops/P1-L5-PLAN.md` 已锁定（E1~E5 + **R-0 前置裁定** + R-1~R-6）。这是**首次改 llmke-v2 平台生产代码**（`rag_projection/projection.py` / `enrich.py` / `kb_pipeline.build_index_payloads`），PLAN 明确：只改代码、不切 `INGEST_PROJECTION_MODE`（保持 legacy）、不启停服务、不写线上 ES/Milvus/DB/18094、不改设计包与运行态配置。

**R-0**：`_table_pk` 存在两套 seed（`projection.py:93-96` 的 `table|index|file_id|ordinal` vs 12340 `server/utils.py:141-148` 的 `table_chunk|table_id|table_pos`），线上 `table_chunks_kb_9` 现有 2 条。要求成员**先做只读对照并回 TL 裁定，裁定前不得写实现代码**，否则同一表格会重复/冲突、违反 B-2/B-4。另明确：L5 是平台 Python 服务，**不得机械套用 doc2md 仓双解释器口径**，evidence 须标注平台测试实际解释器绝对路径与版本。

### 03:3x 时序澄清裁定（L3 指纹 / §12 保留，无文件改动）

成员回报澄清其 03:2x 消息基于 L4 完成前快照，并请 TL 裁定「§12 是否保留、指纹以哪版为准」。TL 核实：03:31 的 L4 复核 + L5 派工消息在其 inbox 已 `read=True`，该澄清生成于读到之前（又一次异步时序错位）。当前 `P1-L3-20261108T031221.log` = **590 行 / `c158bd05fe8408b41ba0b480e438e432`**；`P1-L4-TL-VERIFY-20261108.log` §5 与 `CHECKPOINT` §十二 **已记录该版**，无需更新。

**裁定**：① §12 全部保留（numstat `48 34`→`71 49` 两处更正 + 误读原因、test docstring 说明、两行口径说明、末尾 TL 复核留痕），不回滚、不再改；② 指纹以 **590 行 / `c158bd05…`** 为准；③ §十一 中「569 行 / `206bc4e3…`」是补强时点的历史叙述，作为时间线留痕保留、由 §十二 覆盖，**不构成当前指纹**；④ L1~L4 封存维持，本条澄清**不产生任何文件改动、不重跑测试**。L4 已复核通过，`P1-L5` 派工（§十二）有效，成员立即执行 R-0。

## 十三、P1-L5 R-0 口径裁定（03:4x，TL 认领一处前提误判）

成员 R-0 只读对照（`P1-L5-20261108T033556.log`）**纠正了 TL 03:31 派工单的一处错误前提**：我把线上 `table_chunks_kb_9` 的 2 条当作 12340 `create_table_chunk_pk` 口径线索，并写成「两套 seed 冲突」。R-0 反推 + TL 独立复算证明这 2 条匹配的是 `projection._table_pk` 现口径：

```
sha1("table|kb_9|329|0")[:15] = 1137902847478273881  == 线上 _id
sha1("table|kb_9|333|0")[:15] =  885155839145947657  == 线上 _id
```

`_source.metadata` 带 `parse_artifact_id` / `content_uid` / `channel=table` / `parsed_text_ref=table`、`create_time=2026-11-05 18:49:39` → V2 投影链路（历史增量上传测试）产物，非 12340。12340 `utils.py:125-138` 的 `create_table_pk` 与 `projection._table_pk` **seed 与算法同源同值**，真正不同的只有 `create_table_chunk_pk`（`:141-148`）。TL 已在 PLAN §二 与 evidence §7 明确认领并更正；「须显式裁定」门槛本身保留。

**四项裁定**：

| # | 裁定 |
|---|---|
| 1 | **`_table_pk` 沿用 `projection.py:93-96` 现口径，一字不改**，实现阶段列为禁改区；不引入 `table_chunk` 口径（IR 无 `table_pos` 等价字段、既有 `test_rag_projection.py:161` 已锁定、改口径会与线上分裂并违反 B-2/B-4） |
| 2 | **E2 消歧**：同一 `(kb, file_id, ordinal)` 重投影得到**相同 pk 是正确语义**（按 `_id` 幂等覆盖更新、不产生重复行），「不重复」指不产生重复行 / 不同表格不撞号，不是值必须字面不同；须精确等于线上 2 条真值 |
| 3 | **`table_summary_id` 本 loop 不纳入口径变更**，保持 `summary.py` 的 `v2sum\|...`；线上无 `table_summary_*` 索引、无真值可对齐，记为已知边界转 P6 切读；E1 仍须产出 table_summary 载荷对象 |
| 4 | 解释器采纳 R-0：v2 环境 `llmke-v2-toolenv`（3.10.12 / pytest 8.3.5），图/兼容层 `hipporag-toolenv`（3.11.15）；R-6 基线「11 项」更正为现场实测 **13 条** |

`P1-L5-PLAN.md` §一/§二/§三 已按裁定修订，evidence §7 已由 TL 回填。**R-0 裁定完成，允许进入「反例 FAIL → 实现 → PASS」**；`_table_pk` 禁改、不切 `INGEST_PROJECTION_MODE`、不启停服务、不写线上存储等红线不变。

### 异步时序错位的处理约定（03:39 起生效）

本长程流已多次出现「成员回报/澄清基于 TL 裁定前的旧快照」：02:39（解释器口径）、02:58（L1/L2 补正）、03:0x（L3 阶段 A）、03:2x（L3 补强）、03:3x（L4 待复核）、03:37（R-0 待裁定）。每次均经 TL 现场核实确认**无文件被污染、无标准放宽、无返工**，但造成往返。

**约定**：① TL 裁定一旦写入 `PLAN` / evidence / `CHECKPOINT` 即生效，以**文件当前实况**为准，不以消息文本先后为准；② 实现角色每个 loop 动手前先读 `PLAN` 的 §二/§三 与对应 evidence 的最新指纹/裁定节；③ 若 TL 消息与文件不一致，回报差异并继续推进，**不按旧消息重做、不停等确认**；④ TL 每次复核先核实成员 inbox 的 `read` 状态与文件 md5，再判断是否需要重发。已随派工消息同步给成员。

本条 03:39 澄清**不产生任何文件改动、不重跑测试**：R-0 evidence 已是 312 行 / `757c411f…`（§7 四条裁定齐备）、PLAN §二 已标「已裁定」、平台三文件 `git diff` **当时**为空（L5 实现后为 `26 3`，见 §十四）、`INGEST_PROJECTION_MODE` 仍 unset、线上 `count=2`、关键服务未启停。

**03:49 首次生效验证**：成员 03:47 回报按约定指出「消息里『git diff 仍为空』与文件实况 `26 3` 不一致」，未重做实现、未停等，做法正确。TL 核实其 inbox 中 03:47 的「L5 复核通过 + L6 派工」消息已 `read=True`，确认该回报生成于读到之前；已在 03:49 消息中确认 L5 复核与 L6 派工均已落盘、L1~L5 封存、当前唯一任务为 P2-L6。约定有效，继续沿用。

## 十四、P1-L5 内部收口（P1 阶段完成）与 P2-L6 派工（03:47，D-01 第 5 次自动推进）

成员回报 `T-D2MD-05` `DEV_SELF_CHECK_PASS`。TL 独立复核**通过**，证据 `P1-L5-TL-VERIFY-20261108.log`：

| 复核项 | 结果 |
|---|---|
| 交付物 / 禁改区 | 平台三文件仅 `kb_pipeline.py` 改动（`26/3` additive），`projection.py` / `enrich.py` **0 改动**；`_table_pk`（`projection.py:93-96`）与 `table_summary_id`（`summary.py:30-36`）现场确认原样，符合 R-0 裁定 1/3 |
| 反例 / 复跑 | 阶段 A `3 failed, 4 passed` → 阶段 B `7 passed`（首跑 `4 failed` 中 1 条为测试自身设计问题，改目录隔离后重跑干净 FAIL，未放宽断言） |
| TL 独立复跑 | `llmke-v2-toolenv` 20 passed、交叉 `hipporag-toolenv` 20 passed；**38 键 fixture 与线上 `_source.metadata` EQUAL=True**（差异双向为空） |
| 未切模式 / 未启停 | `INGEST_PROJECTION_MODE` unset、`table_chunks_kb_9/_count=2`、六端口 pid/fd 开工前后逐项一致；grep 仅定义/注释/测试断言 |
| 判断标注 | 不采用 `updated` 回填（线上 38 键无 `table_summary_id`）、`now` 透传而非改默认值、最小 additive 面、E3 双目录验证、真值固化、未宣称 snapshot 可切 —— 逐条认可 |

**计数误差认领**：成员报备 doc2md `git status` 实为 **14 项（5 M + 9 ??）**，而 `P1-L4-TL-VERIFY-20261108.log` §1 写 13 项。TL 现场复核确为 14 项，文件清单与 L4 收口时完全一致、`find backend -newermt 03:29:00` 为空 → **TL 少算一个 `??` fixture 目录的计数误差**，非越界；已在该 log 追加 §8 修订留痕，L4 结论不变（越界判据是文件清单而非计数）。

**P1 阶段收口**：`T-D2MD-01`~`05` 全部 `DEV_SELF_CHECK_PASS` + TL 独立复核通过（各双证据），`QA_PASS` 全部挂起待 G-4。P1 的五项能力（scan-diff / 队列 / 幂等键 / PDF 第 4 件 / 表格通道）均已在**离线与代码层**闭环；`snapshot` 切读仍未放开（硬前置已补齐但切读属 P6）。

**P2-L6 派工**：`docs/v2-tasks/loops/P2-L6-PLAN.md` 已锁定（F1~F5 + R-1~R-7）：新增 `ingest_pipeline/index_writer.py` 的 `build` / `delete_scope` / `apply`，`duplicate_flag=False` 硬约束、`file_id+pk` 精确删除、失败带 `side` 不静默降级、三路 `content_hash` 同源（B-1）。**本 loop 只产写入计划 + mock 端点，不接生产调用点、不写线上 ES/Milvus/DB/18094、默认 `index_prefix=v2cand_` 不碰线上索引名**；生产调用点与 `assert_same_artifact` 闸门留给 `T-D2MD-07`。解释器口径延续 L5（v2 = `llmke-v2-toolenv`，交叉 `hipporag-toolenv`）。

### 10:55 Owner 选定 A 方案：轻量签署已落地（工具 + 自测）

Owner 裁定：签署载体取 **A（轻量签署，不动冻结基线）**；三项输入由 Owner 侧生成提供。

**工具（放 `docs/v2-tasks/tools/`，该目录不在冻结控制面，`freeze_baseline.controls()` 0 命中，新增不改变 `FROZEN-MANIFEST`）**：

| 文件 | 作用 |
|---|---|
| `qa_payload_light.py` | 扫 `TASKS.yaml` 中「`evidence` 非空且 `blocker` 含 `WAIT_QA_ATTESTATION`」的 loop，打 `schema=llmke.qa-attestation-light/1`、`purpose=QA_ATTESTATION` 的**未签名** payload；`--fill-verification` 可对每个 loop 独立复跑验收命令并写入 `verification.rerun`；`--mutation LOOP::说明::结果` 记录抽样变异 |
| `qa_verify_light.py` | 验信任根（`PROTECTED_RUNNER` / `key_id` enabled / `roles` 含 `qa-owner`）、`principal_id` 不在实现方、Ed25519 签名、`batch_digest` 复算、逐个 loop 的 evidence 与 TL 复核文件**当前** sha256 与 payload 一致 |

签名复用既有 `scripts/qa_sign.py`（`openssl pkeyutl -sign -rawin`，私钥必须在工作区外），`canonical` 口径与 `contract_runtime.canonical` 一致，故既有 `verify_envelope` 也能复验。

**10:52 自测（`/tmp` 临时密钥，非 QA 密钥，测完已删除）**：

```
UNSIGNED_QA_PAYLOAD  loops=6  batch_digest=07cb99a69218d0be…
  P1-L1 01b1e140d65b… / P1-L2 d3cb49b8c215… / P1-L3 1189572a0871…
  P1-L4 a8de3362e5eb… / P1-L5 048f83e1dfae… / P2-L6 1948873f63ab…
qa_sign.py            → signed approval written
qa_verify_light.py    → QA_LIGHT_ATTESTATION_VERIFIED（6 loop 全列）
--fill-verification   → 6 个 loop 真实复跑全部 rerun=PASS
篡改 payload 后复验    → FAIL：batch_digest 不一致 + Signature Verification Failure
```

**待 Owner 提供**：`principal_id`（不得为实现方）、`key_id`、Ed25519 公钥 PEM（私钥留在 Owner 侧、绝不入仓）。到位后：`qa_payload_light.py --fill-verification` → Owner 用 `qa_sign.py` 签名 → TL `qa_verify_light.py` 验签 → 逐 loop 记 `QA_PASS` 并更新 `TASKS.yaml`。

## 十五、P2-L6 内部收口与 P2-L7 派工（10:47，D-01 第 6 次自动推进；会话恢复后复核）

**会话恢复说明**：本长程流在 03:55（L6 成员回报）后因模型故障中断，上下文切换后由 TL 从 `CHECKPOINT` + `TASKS.yaml` + 证据文件恢复状态，未丢失任何已完成工作。恢复后第一件事是独立复核 L6。

成员回报 `T-D2MD-06` `DEV_SELF_CHECK_PASS`。TL 独立复核**通过**，证据 `P2-L6-TL-VERIFY-20261108.log`：

| 复核项 | 结果 |
|---|---|
| 交付物 | `index_writer.py db0ddc9b…`（252 行）、`test_index_writer.py d497b8ee…`（11 条）、`fixtures/p2_l6/existing_docs.json 38f0106f…`、evidence 537 行 / `cc645ee3…` 全部吻合 |
| 越界 | 本 loop **0 个 tracked 平台文件改动**；`git diff` 的 `26/3 kb_pipeline.py` 是 L5 产物，md5 `addcbb15…` 与 `P1-L5-20261108T034446.log:276` 逐字一致；`projection.py`/`enrich.py`/`summary.py` 0 改动 |
| L7 边界 | `grep index_writer\|assert_same_artifact kb_pipeline.py` → 无调用 ✅ |
| 实现审查 | `build()` 分组/目标名/ES·Milvus body 字段/`duplicate_flag=False`/document 仅 `{page_content, metadata}`/确定性 `committed_at`/`content_hash` 由 `bind_artifact` 复算 —— 全部符合 F1~F3；`delete_scope` 只产计划且 `forbidden_scope="source"`；`apply` 先 ES 后 Milvus、失败带 `side`/`needs_compensation` |
| 反例 / 复跑 | 阶段 A `9 failed, 2 passed` → 阶段 B `11 passed`（首跑 2 条为测试自身 `urlopen` mock 问题，改 `full_url` 后通过，未放宽断言）；TL 独立复跑两解释器均 **31 passed** |
| 边界 | `INGEST_PROJECTION_MODE` unset、`_count=2`、八端口 pid/fd 前后一致、19526/19527 未发写入请求 |

**L6 判断标注①的落点**：`store.commit()` artifact 不含 `file_id`，`build()` 现阶段回落 `kb`；已写入 `P2-L7-PLAN.md` G1 作为**硬断言**——L7 生产调用点必须注入真实 `file_id`，缺则 fail-closed，不得静默回落。

**P2-L7 派工**：`P2-L7-PLAN.md` 已锁定（G1~G5 + **R-0 前置核实** + R-1~R-6）：`consume_for_kb` 接 `build` + `assert_same_artifact` 生产闸门（不一致时抛 `SOURCE_DIVERGED` 且三路 0 写入）、`kb_state.json` 升级 `llmke.kb-state/2`（`LLMKE_KB_STATE` 路径、flock + 原子替换、损坏抛 `KB_STATE_CORRUPT` 禁静默 `{}`）、`consume_for_kb` 不再全库重建图谱。因 L7 首次改主流程与状态文件，要求先做 R-0 只读核实（调用方、现有路径/schema、契约 §4.2 差异）回 TL 确认后再写实现。红线：不写线上、不启停服务、不切模式、不改 `artifact_binding.py` 算法。

### 11:45 P2-L7 R-0 TL 预研（成员会话未恢复时的并行准备，非代替实现）

成员 11:43 消息 `read=True` 但截至 11:45 无产出、无进程。TL 以**只读**方式先把 R-0 的四个事实查清，作为后续裁定的对照基线（实现角色仍须自行复核并出 evidence）：

| 项 | 现场结论 |
|---|---|
| `consume_for_kb` 调用方 | `kb_ingest_service.py:125`（18096 摄取服务，**已关闭**）、`scripts/v2_ingest_doc2md.py:203`（v2-ingest 关闭态）→ **当前无在线调用方**，改它不影响线上检索；交付时需附调用方 grep 证明 |
| `kb_state.json` 现状 | `_kb_state_path(store_root) = <store_root>/kb_state.json`；`_load_kb_state` 损坏时 `return {}`（**静默，即待修缺陷**）；`_save_kb_state` 用固定 `.json.tmp`；`LLMKE_KB_STATE` 未设置；`platform/r12/data/kb-state/` 不存在；工作区无现存 `kb_state.json` |
| 契约 §4.2 | `llmke.kb-state/2` 含 `schema / version / cursor / set_digest / kb / chunks / graph`；强制绝对路径（禁 `/tmp`）、`flock` 保护读-改-写、pid/uuid 临时名、损坏/schema 不符抛 `KB_STATE_CORRUPT` |
| `assert_same_artifact` | `(a, b)` 两个 `bind` 输出，逐字段比 `artifact_id` + `content_hash`，任一不同即抛 `ArtifactBindingError`；设计包要求「只加调用点、不改算法」 |

**预裁方向（待成员 R-0 对照确认后生效）**：① `LLMKE_KB_STATE` 未设置时默认 `platform/r12/data/kb-state/kb_state.json`（绝对路径，禁 `/tmp`）；② 旧 v1 文件（无 `schema` 字段）→ 只读迁移一次并保留 `.v1.bak`，不静默丢弃；③ 损坏 → `KB_STATE_CORRUPT` 阻断，**不按空库重建**（防 `/tmp` 清空重演）；④ `consume_for_kb` 改动对在线无影响，但 evidence 必须给出调用方 grep 与「无在线入口」结论。

### 11:49 IDE 重启后团队注册丢失与恢复（运维留痕）

Owner 于 11:47 重启 IDE 会话后，`send_message` 报 `Recipient "python-engineer" not found. Known members: none` —— **团队运行时注册随进程丢失**，但 `.codebuddy/teams/.../python-engineer.json`（62 KB 历史）与 `config.json` 仍在磁盘。

**恢复方式**：用团队模式重新 `spawn`（`name=python-engineer` / `team_name=vl-doc2md-inc`），成员按持久化历史恢复并异步执行，无需重建团队目录、不丢历史。**教训**：会话重启后需先重新拉起成员，否则派工消息无人接收；`TASKS.yaml` 与 `CHECKPOINT` 是唯二可靠的跨会话状态源。

### 12:0x P2-L7 R-0 裁定（成员回报 + TL 复核后）

成员 R-0 evidence：`P2-L7-20261108T115004.log`（379 行 / `3add68a364e93c0291052ebeb2944e26`）。TL 现场复核并采纳其三点精确化：① `kb_ingest_service.py:125` 是 `runner = consume or K.consume_for_kb` 的**函数对象绑定**、真实调用在 `ingest_file` 内（结论「无在线入口」不变）；② `platform/r12/data` **整目录不存在**、`store_root` 默认 `.artifacts/artifact-store`（`:39`，相对路径不可审计）；③ `index_writer.build` **无 `file_id` 参数**、`index_writer.py:136` 就是回落点。

| # | 裁定 |
|---|---|
| 1 | **`file_id` 注入 fail-closed**：`build(..., file_id=None)`，优先级 = 显式参数 > `artifact["file_id"]` > 抛 `FILE_ID_MISSING`，**删除 `or kb` 回落**。已核实 `test_index_writer.py:57` 的 artifact 本就含 `file_id="333"` → **L6 的 11 条测试不受影响、无需修改**。新增「两者皆缺 → 抛错」反例 |
| 2 | **默认路径基准纠正**：成员写的 `parents[3]` 实测为 `.../llmke-v2/services`（会算成 `services/platform/...`），**必须用 `parents[4]`**；并加单测断言「基准下 `platform/` 与 `docs/v2-tasks/` 同时存在」；`LLMKE_KB_STATE` 优先、写入时才 mkdir |
| 3 | **v1 迁移**：`"schema" not in doc` → v1（同意）；写 `.v1.bak`，**已存在则追加 `.v1.bak.<pid>.<uuid8>` 不覆盖**；迁移后做 round-trip 校验（能被 `_load_kb_state` 读回、`version/cursor/set_digest` 齐备），失败即 `KB_STATE_CORRUPT` |
| 4 | **`consume_for_kb` 返回体不变**：仅内部改读 `state["chunks"]`，对外 JSON 形状/字段不变（不破坏 `kb_ingest_service.py:216` 与 `v2_ingest_doc2md.py`）；evidence 需给「行为差异说明」表 |

**G2 接入点**采纳成员建议：`build` 只产计划、`_post_json` 在 `apply`，把 `assert_same_artifact` 放两者之间，天然满足「禁止先写后校验」，无需重排写入顺序。R-6 基线路径按实测：`tests/test_rag_projection.py`（仓根）+ `services/rag-alg/index_data_service/tests/{test_table_projection,test_index_writer}.py`，两解释器均 31 passed。

已允许进入「R-1~R-6 反例 FAIL → 实现 → PASS」，不再逐轮请示。

## 十六、P2-L7 内部收口与 P2-L8 派工（12:05，D-01 第 7 次自动推进）

成员回报 `T-D2MD-07` `DEV_SELF_CHECK_PASS`。TL 独立复核**通过**，证据 `P2-L7-TL-VERIFY-20261108.log`：

| 复核项 | 结果 |
|---|---|
| 指纹 | `kb_pipeline.py dc60bd09…`（675 行）、`index_writer.py 1f2fa0ae…`、`test_kb_pipeline_l7.py 0b69477e…`、evidence 1169 行 / `e053d006…` 全部吻合 |
| 反例 / 变异 | 阶段 A `22 failed, 2 passed`（全在断言/行为层，2 条哨兵保留）→ B `24 passed`；变异 5/5 全捕获且恢复后 md5 逐位复原 |
| 独立复跑 | v2 / hipporag 两解释器均 **55 passed**（13+7+11+24） |
| 越界 | 平台仅 `kb_pipeline.py`（`377/55`，含 L5 的 `26/3`，本 loop 净 +299）+ 新增 `index_writer.py`；`projection/enrich/summary/artifact_binding` 与 HEAD 一致；doc2md 仍 14 项 |
| 裁定落地 | `parents[4]` + 锚点单测、`file_id` fail-closed（L6 的 11 条零 RED）、v1 迁移 `.v1.bak` 不覆盖、返回体逐字不变 |
| 红线 | mode/KB_STATE 双 unset、`platform/r12/data` 仍不存在、`_count=2`、八端口 pid 未变 |

**七处判断全部认可**，其中 `status="PARTIAL"` + `graph.error="GRAPH_REBUILD_DEFERRED: …"` + `deferred=true` 是本 loop 最重要的诚实性设计（不把「图没建」谎报成 OK）。

**三条边界裁定**：

| # | 边界 | 裁定 |
|---|---|---|
| 1 | **【高】图谱不再自动更新** | 接受并升级为**硬约束**：当前 18096 未启用、在线无影响；**P4 部署（`T-D2MD-13`）前必须完成 P3（`T-D2MD-09/10/11`）**，否则不得放量；`PARTIAL`+`deferred` 禁改。已写入 `T-D2MD-13.blocker` |
| 2 | 【中】`SOURCE_DIVERGED` HTTP 502 | 接受（类型正确、双基类兜住）；HTTP 409 映射记入 `T-D2MD-12` 待办（`kb_ingest_service.py:211-212` 不在 L7 授权面） |
| 3 | 【低】L6 `_binding_input` 残留 `or "kb"` | 接受（经 `build()` 已不可达）；记入 `T-D2MD-09` 待办一并收口 |

**P2-L8 派工**：`P2-L8-PLAN.md` 已锁定（I1~I5 + R-1~R-6 + **R-0 前置核实**）。**默认模式 A（离线/mock，不创建任何索引）**；模式 B（真实创建 `v2cand_*`）**需 Owner 明确授权**，`T-D2MD-08.blocker` 已标注。

## 十七、P2-L8 R-0 裁定（12:1x，发现 PLAN 三处前提失效）

成员 R-0（`P2-L8-20261108T120209.log`）零代码、零索引创建，查出 PLAN 三处前提**实际不成立**，TL 独立复核全部成立：

1. **命名不一致**：读侧 `"table_chunks_" + "v2cand_kb_9"` = `table_chunks_v2cand_kb_9`，写侧 `_target_name` 产 `v2cand_table_chunks_kb_9` → **snapshot 下表格通道静默空**；错名还被 `tests/test_projection_read.py:20-26` 固化成契约。
2. **图召回断**：`multiple_retrieval.py:463-470` 把非 `faq_/table_chunks_/table_summary_` 前缀者当 kb 名 → `{"kb":"v2cand_kb_9"}`，而 18094 按 `kb_9` 目录组织 → 查不到库。
3. **`shadow` 与 `test_runtime_switches.py:22` 冲突**，且 `resolve()` 内结构上做不到「双读不改结果」。

**键集差异实测（TL 独立跑，纠正成员数字）**：影子 36 键 / 线上 38 键；影子多 `artifact_id`、`content_hash`；影子缺 **`n_cols`、`n_rows`、`parsed_text_ref`、`source`**（成员只报 2 个，漏了表格维度两键）。

| # | 裁定 |
|---|---|
| Q1 | 读侧改「整个索引名前缀」，用**显式 `channel_names` 映射**、禁止字符串拼接；`_target_name` 不动；修正 `test_projection_read.py` 错名断言 + 加读写名字逐字对拍 |
| Q2 | info 增 `graph_kb`（`v2cand_kb_9 → kb_9`），`multiple_retrieval.py` 取 kb 处改用；断言 snapshot 下 graph `kb=kb_9` |
| Q3 | `table_summary` 影子通道本 loop 不新增，info 增 `missing_channels=["table_summary"]`；**已写入 `T-D2MD-17.blocker`：补齐前不得切读** |
| Q4 | 授权改 `RUNTIME-SWITCHES.yaml` + 对应测试；`shadow` 降级为「只解析名字 + 返回 `shadow_names`，不发第二次查询」，真双读留 P6 |
| Q5 | 授权 `index_writer.build` 补 **4 键**（`source` / `parsed_text_ref` / `n_rows` / `n_cols`）；同步更新 L6 F1 断言；evidence 必须写「影子 = 线上 38 + 2 个 V2 溯源键」，不得声称完全一致 |

**授权改动面**（超出须回 TL）：`projection_read.py` / `retrieval_service.py` / `multiple_retrieval.py`（仅 kb 取值一行）/ `index_writer.py`（additive 4 键）/ `RUNTIME-SWITCHES.yaml` / `test_projection_read.py` / `test_runtime_switches.py` / `test_index_writer.py` / 新增 L8 测试与 fixtures。

> **这轮 R-0 的价值**：三处问题都属「看起来能跑、切读那天才炸」的类型（表格通道静默空、图召回查不到库、开关与登记冲突）。若不是强制 R-0 只读核实，会一路带到 P6。**R-0 前置核实机制继续保留。**

### 12:2x P2-L8 复核：条件通过，`source` 语义需修正

成员回报 L8 `DEV_SELF_CHECK_PASS`（`P2-L8-20261108T120810.log`，738 行 / `5d08f083…`）。TL 复核：五项裁定落地**整体认可**（`channel_names` 用列表而非扁平 dict 合理；`test_runtime_switches.py` 一行未改、改 yaml 后自然 PASS 更硬；变异 5/5；Q1 的「错名彻底消失」反向断言到位），但发现一处**实质缺陷**：

**`source` 取错值**：成员实现 `meta["source"] = file_path or ""`，而线上 `source` 不带 scheme/host：

```
线上 source    = r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx
线上 file_path = http://127.0.0.1:19000/r12-rag/kb_9/.../R12FIX-credit-ledger.xlsx
urlparse(file_path).path.lstrip("/") == 线上 source   ← 逐字一致
```

TL 12:1x 裁定里写「`source` 取 `file_path`（与线上语义一致）」**表述不准确**，此处纠正。裁定优先级：**调用点显式 `source`（与 `build_index_payloads:125` 同口径）> `urlparse(file_path).path.lstrip("/")` > `""`**；`build(..., source=None)` additive。

**另两处裁定**：① 清单外改动 `kb_pipeline.py`（+3/-1 传 `file_path`）**接受**，但必须同时传 `source=source`（`consume_for_kb` 已有该变量，`:545`/`:639` 在用）；② 残留拼接点 `multiple_retrieval.py:569` **授权收口**（1 行），`retrieval_service_cec.py:227` 不动（由 Q3 硬前置覆盖）。

**仓根全量测试核实（重要基线事实）**：`3 failed, 1053 passed, 19 skipped`，三个失败**全部既有、非本 loop 引入**：
- `test_scripts_compile` ← `scripts/v2_community_report.py:80` `IndentationError`，**`git show HEAD:` 版同样报错**、本轮未改该文件；
- `test_security_scan` ← `build/systemd/*`、`docs/NEXT.md`、`docs/design/unified-documents-v2/EVIDENCE-*.md` 既有文件命中；
- `test_q_acceptance` ← `scripts/v2_q_acceptance.py` 内部 `FAIL:3`；
- 三个测试文件 `git status` 均未改。

已要求 evidence 写准回归范围（平台侧 116 passed + 上述既有失败说明），**不得**把 1053 passed 说成「全 PASS」，也**不得**去修这 3 个既有失败（不属本切片）。

L8 状态：**条件通过，等修正后重新回报**；`T-D2MD-08` 保持 `DOING`。

## 十八、P2-L8 内部收口与 P3-L9 派工（12:3x，D-01 第 8 次自动推进）

成员按 TL 12:2x 的修正要求完成 `source` 语义修复后重新回报。TL 独立复核**通过**，证据 `P2-L8-TL-VERIFY-20261108.log`：

| 复核项 | 结果 |
|---|---|
| 指纹 | `projection_read 0d965401…` / `multiple_retrieval e0901376…` / `index_writer 1ec116e5…`（347 行）/ `kb_pipeline e1e9f909…`（678 行）/ evidence 1088 行 / `b432b632…` 全部吻合 |
| `source` 修正 | `_resolve_source()` 优先级「显式 > `urlparse(file_path).path.lstrip("/")` > `""`」正确；`kb_pipeline.py:530-531` 已补 `file_path` + `source`；断言用派生真值、无写死路径 |
| 命名收口 | `multiple_retrieval.py:571` 改为 `_channel_name(...)`；裸拼接仅剩 `retrieval_service_cec.py:227`（Q3 硬前置覆盖）；残留登记集从 2 收为 1 |
| 独立复跑 | 平台侧 `63 passed`；加 `artifact_binding` 共 `93 passed`，零失败 |
| 变异 | 6/6 全捕获（M6 = `source` 退回 `file_path` → 3 failed）；成员如实记录 M3 首跑「锚点没匹配 → 判定变异未生效并修锚点」，**未把「没变异成」当「断言满足」** |
| 红线 | `INGEST_READ_MODE`/`INGEST_PROJECTION_MODE` 双 unset、`v2cand*` 0 索引、`kb_9=44`、八端口 pid 未变、模式 B 未进入 |

**仓根 3 个既有失败口径已固化**：`test_scripts_compile`（`v2_community_report.py:80`，`git show HEAD:` 版同错）、`test_security_scan`（既有文件命中）、`test_q_acceptance`（`v2_q_acceptance.py` 判 FAIL，且计数随在线数据漂移）—— 均不属本切片，**不修**，后续 loop evidence 统一写「本 loop 回归范围 + 3 个既有失败无关」。

**P3-L9 派工**：`P3-L9-PLAN.md` 已锁定（J1~J7 + **R-0 前置核实** + R-1~R-6）。本 loop 是**恢复图谱增量更新的关键**（L7 已停全库重建），但 `api.py` 属在线 18094（pid 3189651/3202203）：**禁止重启/启停 18094**，端点用 FastAPI `TestClient` 进程内验证、`delta_build` 用 mock 引擎验证，真实联调留 P4/P6 维护窗口。同时顺带收口 L7 边界 3（`_binding_input` 的 `or "kb"`）。

## 十九、P3-L9 R-0 裁定（13:1x，含 TL 追加的 D-11 严重隐患）

成员 R-0（`P3-L9-20261108T130118.log`，268 行 / `76d19adb…`）零改动。TL 独立核实其核心发现：

1. **PLAN 点名的 4 个 helper 不存在**：`_kb_root` / `_load_fence` / `_write_sources` / `_write_kb_json` 全 0 命中，只有 `_default_build:196`；它们是内联代码，且**四文件写入点分散在三处**（`fence.json`/`sources.json` 在 `_default_build` 内、`kb.json`/`community.json` 在 build 路由内）→ 这正是 J3 的坑。
2. **双解释器在本 loop 不成立**：`llmke-v2-toolenv` 实测缺 `fastapi` / `pydantic` / `starlette`；只有 `hipporag-toolenv` 有。
3. **`rebuild.py:221` 确为 `copytree(base_dir, target)`** → 新目录带着旧四文件，不重算就 J3 必 FAIL。

**TL 追加 D-11（比上述更严重）**：

```
canary.py:43-44   MODES=("full","delta")   DEFAULT_MODE="full"
canary.load(None) → scope=[] mode=full default=full
mode_for("kb_9")="full" / mode_for("kb_1004")="full"
当前无任何 LLMKE_CANARY_* 与 canary.json
```

即 `auto` → `rebuild_by_policy` → `full` → **把 L7 刚停掉的全库重建悄悄恢复**；kb_1004 4520 块全量是小时级。

| # | 裁定 |
|---|---|
| D-11 | **不改 `canary.py` 的 `DEFAULT_MODE`**；`auto` 且 canary 来源为默认值时按 `delta` 处理，响应带 `effective_mode="DELTA"` + `canary_source="default->delta"`；显式配 full 才走 full；**新增硬断言 J8：无配置时 `auto` 必须 delta（`full_build` 计数 0）** |
| D-1 | 新建 4 个模块级私有 helper **只给 delta 用**，build 路由不动；**附加**：helper 产出的 `sources.json` 必须与 `_default_build` 内联写出的逐字节相同（防两份实现漂移） |
| D-3 | 接受「`delta_build` 鸭子类型 + J1 只在 hipporag 验证」；**硬约束** `delta_build.py` 禁 import fastapi/pydantic/starlette，且不得为凑双解释器去 v2 env 装包 |
| D-8 | 授权 `create_app(..., delta_runner=None)` additive（与既有 `engine_factory`/`builder` 注入模式一致，`:288`） |
| D-9 | `read_pointer(root)` 判空（实测返回 `None`）→ `NO_BASELINE_SNAPSHOT → REJECTED`，不做字符串匹配、不改 `rebuild.py` |
| D-10 | `DeltaRequest`：`docs` **改必填**（防漏传建空图）；四枚举语义写死（`auto`/`delta`/`full`+必带 reason/`skip_if_fresh`）；`fencing` 保留但 L9 不推进 `generation`（L10） |

## 二十、P3-L9 内部收口与 P3-L10 派工（13:1x，D-01 第 9 次自动推进）

成员回报 `T-D2MD-09` `DEV_SELF_CHECK_PASS`。TL 独立复核**通过**，证据 `P3-L9-TL-VERIFY-20261108.log`：

| 复核项 | 结果 |
|---|---|
| 指纹 | `delta_build.py bf509721…`（323 行）、`api.py 842a300c…`（735→800）、`index_writer.py d9853ade…`、两个测试文件、evidence 324 行 / `dfb664ea…` 全部吻合 |
| 独立复跑 | 平台侧合集 `77 passed, 1 skipped`（skip 为 v2 env 缺 fastapi 的 J1/D-1 等价性） |
| 变异 | **5/5 全捕获**且 md5 逐位复原：M1 auto→canary full(J8) / M2 不重算 sources(J3) / M3 无基准自动降级(J4a) / M4 `or "kb"`(J5) / M5 freshness 取反(J2) |
| D-11 | `auto` 无配置 → DELTA + `canary_source="default->delta"`；J8 还把「canary 默认是 full」**钉成断言**（自保护），显式配 full 才走 FULL |
| 红线 | 18094 pid `3189651/3202203` 启动于 2026-11-07 01:20/01:21（35.8h）**未重启**；`v2cand*` 0、`kb_9=44`、八端口 pid 未变、doc2md 仍 14 项 |

**三处过程问题的裁定**：

| # | 问题 | 裁定 |
|---|---|---|
| 1 | **先实现后测试**（偏离 L1~L8 流程） | **接受**：变异 5/5 + 首跑 2 红（含 1 条**实现真缺陷**）+ md5 逐位复原，判别力强于形式流程；**但 L10 起恢复「先 FAIL 再 PASS」**，再偏离须在回报首段声明并给等效变异证据 |
| 2 | `_finalize_snapshot` 放 `delta_build.py` 而非 `api.py` | **接受并认可**：`api.py` 顶层 import fastapi，放进去会让 `delta_build` 反向依赖 api、违反 D-3；L10 改 `api.py` 时**不得**把它挪回 |
| 3 | J3 对 `fence.json` 用「格式差异使 sha 必不同」 | **接受**：J3 实际有强内容断言（`idx-old` 不在、`DELETED-FILE` 不在、`file_id` 集合 == `{A,B}`），sha 只是补充；但结论表述须准确 ——「四文件都被重写；sources/community/kb 有内容级断言；fence 只做语义等价 + 重写证明」，不得概括为「sha 全不同 ⟹ 都重算」 |

**首跑打出的真缺陷（成员自行修复，改实现不改测试）**：`_finalize_snapshot` 原按**请求里的 `live`** 写 `sources.json`，未剔除已撤权文件 → sources 会指向快照里不存在的 idx。已改为 `surviving` 过滤。TL 认可：这是真实引擎下必然炸的缺陷。

**P3-L10 派工**：`P3-L10-PLAN.md` 已锁定（K1~K6 + R-0 + R-1~R-6）：`state` 改 `Dict[kb, StateSlot]`、`fencing` 不再固定 1、按 kb `flock`。**关键如实声明**：本 loop 改的是进程内结构，**不重启 18094 就不生效**，代码与运行态在重启窗口前不一致属预期，`T-D2MD-10.blocker` 已标注。同时把 L9 的提醒写入 `T-D2MD-11.next_action`（`capabilities.incremental_update` 现仅声明引擎能力、未声明 HTTP 端点，L11 勿漏）。

## 二十一、P3-L10 R-0 裁定（13:2x，含 TL 发现的一处致命实现地雷）

成员 R-0（7 项全核，未写实现）质量高，且**自己发现了 fencing 并发丢更新**。TL 独立核实后逐条裁定，并追加一处成员未发现的陷阱。

### TL 独立核实的事实

```
api.py:351   state = {"engine","text_to_idx","snapshot","fence","snapshot_kb"}  ← 全局单槽，snapshot_kb 只记录归属、无隔离
api.py:265   result = rebuild(root, fence, live, full_build, fencing=1)         ← 全仓唯一 fencing 写入点
api.py:597   "fencing": (pointer or {}).get("fencing")                          ← 状态回显读指针
_promote     "fencing": fencing if fencing is not None else current_fencing     ← None 时替换为 current（不递增）
_cas_write   fencing = int(payload.get("fencing", current_fencing) or 0)        ← ⚠️ 地雷见下
rebuild()    target = f"snapshot-{stamp}-g{generation}"，stamp = 秒级+纳秒尾巴  ← 同 kb 并发 target 天然唯一
fence.py:37  if changed: self.generation += 1                                   ← 唯一递增点（revoke）
lease_mysql  存在但未接线（需注入 connection_factory，无 LLMKE_LEASE* 环境变量）
```

### ⚠️ TL 发现的致命地雷：`or 0` 使「传 None」直接打死全量建图

```python
fencing = int(payload.get("fencing", current_fencing) or 0)
if current_fencing > fencing: raise StaleFencingError(...)
```

`payload["fencing"] = None` → `int(None or 0) = 0`；只要 `current_fencing >= 1` 就有 `current_fencing > 0` 恒真 → **每一次全量建图都会抛 `StaleFencingError`**。

实测验证：

```
payload fencing=None  -> int(raw or 0) = 0 | cur=1 时 REJECT
payload fencing=0     -> int(raw or 0) = 0 | cur=1 时 REJECT
payload fencing=1     -> int(raw or 0) = 1 | cur=1 时 PASS
```

**因此 Q2「改成不传 None」不能单独做**，必须与 `_cas_write_pointer` 的 None 分支同一提交，否则 L9 已验收的全量建图会在第一次提升时全挂。

### 五项裁定

| # | 问题 | 裁定 |
|---|---|---|
| **Q1** | 自增点锁内还是锁外 | **锁内**（改 `_cas_write_pointer`），`_promote` 不再把 None 替换成 `current_fencing`。实现必须用显式 `raw = payload.get("fencing")` 判 None，**禁止 `or 0`**；`raw is None → new = max(cur, floor) + 1`；`raw is not None` 时保持 `cur > raw → raise`（旧主拒绝不可退化）。`_cas_write_pointer` 须**返回最终 payload** 供 `_promote`/响应回显，否则 `api.py:597` 与实际指针不一致 |
| **Q2** | `api.py:265` 的 `fencing=1` | **改为不传（None → 锁内自增）**。预期：首次 build（cur=0）→ 1；第二次 → 2；显式持 fencing=1 的旧实例再写 → 被拒。**必须有一条断言覆盖「首次建图传 None 不抛异常且 fencing>=1」**，这是上面地雷的守门测试 |
| **Q3** | `fence.py` 是否加「重建代次」 | **不加，本 loop 不改 `fence.py`**。指针 `fencing` 是唯一真相源，再加计数器必漂移。授权面含 `fence.py` ≠ 必须改，evidence 标注「授权未使用」。`fence.generation` 仅作 `floor` 下界保护，非代次真相 |
| **Q4** | K3「同 kb 并发」口径 | **接受「构建并发 + 指针写 CAS 串行」，不加长锁**。TL 已核实 `target` 含纳秒尾巴、天然唯一，**不存在文件级竞态**，最终指针必指向完整快照。要求 evidence 写明「同 kb 并发会浪费一次建图（后到者胜、前者快照被 `keep_last` 清理）」是**已知代价非缺陷**；追加断言：并发后 `current.json.dir` 指向存在且四件套完整的目录、fencing 严格递增 |
| **Q5** | 解释器口径 | **同意**：K1/K4 在 hipporag env **必须真跑绿**、不得变 skip；v2 下 `importorskip` 的条数须在 evidence 单列，**不得计入通过**；fencing 自增 / 旧主拒绝 / per-kb 锁粒度用 `rebuild.py` 层两个临时 root + 线程做决定性验证（采纳成员建议） |

### TL 追加的两条约束

1. **`rebuild_delta` 也走 `_promote`**：增量重建同样会 fencing+1。K2 断言须明确「FULL 与 DELTA 都严格递增」，不分路径。
2. **`fencing` 语义 = 单调递增序号，非重建计数**：因 `floor = fence.generation`，某 kb 撤权多次但重建少时 fencing 会跳变（如 `max(1,100)+1=101`）。断言只测**单调**，不测连续；evidence 写明语义。

## 二十二、P3-L10 内部收口与 P3-L11 派工（13:3x，D-01 第 10 次自动推进）

成员回报 `T-D2MD-10` `DEV_SELF_CHECK_PASS`。TL 独立复核**通过**，证据 `P3-L10-TL-VERIFY-20261108.log`：

| 复核项 | 结果 |
|---|---|
| 指纹 | `api.py 4bf0b21f…`（800→823）、`rebuild.py 782c8be3…`（289→346）、**`fence.py cbb9151f…` 未改**、两个测试文件、evidence 790 行 / `9a186b8a…` 全吻合 |
| 独立复跑 | v2 rebuild 层 `11 passed ×2`（无偶发）、hipporag api 层 `6 passed`、L9 回归合集 `88 passed, 1 skipped`（L9 的 77 + 11） |
| `or 0` 地雷 | **按裁定同一提交落地**：显式判 `None`、无 `or 0`、自增在 `flock` 内、返回 `final` 供响应；守门用例同批落地，变异 M1 → 2 failed |
| 先 FAIL | 阶段 A `8 failed, 2 passed`（rebuild）+ `4 failed, 2 passed`（api）；2 条先行 PASS 为「per-kb 锁现状已成立」与「禁改区哨兵」 |
| 变异 | 5/5 全捕获；**两次变异设计失败如实记录**（M2 初版「锁内取 max」未打中 / M4 初版靠并发概率），成员明确未把「没打中」算通过 |
| 回归 | v2 `145 passed, 3 skipped`、hipporag `163 passed`；**18 个既有失败做了 HEAD 逐行对照**（两侧 `18 failed, 111 passed`，失败项一致） |
| 红线 | 18094 pid 未变（35.9h）、`kb_9=44`、`v2cand*=0`、未执行 uvicorn、`fence.py` 未改 |

### 成员实现中发现的第二个真缺陷（TL 认可）

TL 在 Q4 只核实了「`target` 含纳秒尾巴、天然唯一，无文件级竞态」，**漏了 `keep_last` 清理会删掉另一个写者的在建目录**：

```
A 建好 target_A、尚未 promote（指针仍指旧目录）
B promote 后执行 keep_last 清理 → target_A 被当旧目录删掉
A promote 成功 → 指针指向已不存在的目录（建图成功但图打不开）
```

修复：`makedirs` 后立即写 `.building`；清理时跳过 ①`live_dirs`（当前指针）②带 `.building` 的目录。TL 核验标记时机正确（`rebuild.py:140` 标记 / `:232` 取消 / `:240`+`:242` 双重跳过 / `:278` 增量路径同标记），并补了**确定性**用例（不靠并发撞运气），连跑 15 次全绿。

### 一条必须传给 P4/P6 的结论

本 loop 与 L9 改的都是**进程内结构**，**不重启 18094 就不生效**。线上此刻仍是旧的单槽 `state` 与写死的 `fencing=1`。**P4/P6 部署前必须复核，不能把「代码已合入」当成「线上已具备 per-kb state 与 fencing 递增」。** 已写入 `T-D2MD-10.next_action` 与 `blocker`。

### P3-L11 派工

`P3-L11-PLAN.md` 已锁定（M1~M5 + R-1~R-5）。核心问题：`capabilities.py:53` 的 `incremental_update` 只声明引擎能力、**未声明 `api.py:482` 已有的 `POST /v2/graph/delta`**，导致按能力表判断「能否 HTTP 增量」的调用方得到错误结论。

要求：先做 R-0（capabilities 结构 / 既有端点声明风格 / `/v2` 路由全集 / 消费方 / 既有结构测试）并回 TL；再反例先 FAIL；**M3 要求声明↔路由双向一致**（无幽灵端点、无漏登）；**M1 要求与 `api.py` 路由逐字符比对**而非手抄；只改 `capabilities.py`；禁止重启 18094。

## 二十三、P3-L11 R-0 裁定（13:4x，含 TL 承认的一处 PLAN 前提错误）

### TL 承认的 PLAN 缺陷

`P3-L11-PLAN.md` §三-2 写「是否已有能力项声明过 HTTP 端点 —— 若有，**照它的字段名写**」。TL 写这条时假设存在可照抄的结构化字段。**成员实测证明前提不成立**：

```
SCHEMA = "llmke.graph-engine.describe.v1"，CAPABILITIES = 20 项
全部键的并集 = ['evidence','note','status']        ← 只有三键
含 http/endpoint 的项 = []                          ← 零
唯一提到 HTTP 的是 community_report.note 的**散文**
describe() 用 {k: dict(v)} 复制                    ← 新增字段自动透出
既有测试 tests/test_graph_engine_capabilities.py 无键集断言 ← 加字段不破
capabilities.py md5 32ce3e11f85a9ff4ed59e68cbcd40481（未改）
```

**TL 裁定：PLAN §三-2 作废，Q1 由 TL 直接定字段形状**（不能等"照抄"）。这属 TL 规划失误，记录在案。

### 四问裁定

| # | 问题 | 裁定 |
|---|---|---|
| **Q1** | 字段名/形状 | **B：`http: [{"method","path"}]`**。字段名用 `http`（沿用 `community_report.note` 既有「已接线到 HTTP」措辞，不造第三个词）；列表形状支持一个能力多端点。**`method` 大写、`path` 原样（含 `/v2` 前缀）**。**该字段必须可选**（缺省合法），20 项不得强制全带 |
| **Q2** | 是否允许给别的项加 `http` | **允许**，但边界必须精确 —— 分两类处理：<br>① `community_report`：note **已有散文端点** → **散文保留不删**，只新增 `http`；并加断言「note 中出现的 `/v2/...` 路径必须 ⊆ `http` 列表」，防止散文与结构化漂移<br>② `index_build` / `incremental_update`：note **无任何 HTTP 提及** → 只新增 `http`，**禁止为"对称"去改 note 加散文**（那属改三键、违反 M4） |
| **Q3** | 漏登口径 | **(ii) 全覆盖**：`index_build→POST /v2/graph/build`、`incremental_update→POST /v2/graph/delta`、`community_report→POST /v2/graph/global`。`POST /v2/graph/query` **虽 POST 但只读** → **显式列入不登记白名单**，理由写进**测试常量**（不是注释）；GET 只读路由（status/fence/entities/view）不逐条登记 |
| **Q4** | 解释器拆分 | **确认**：M1（需 import fastapi 解析路由）只在 hipporag 跑；结构与 M2/M4/M5 在 v2 跑；v2 的 skip **单列不计通过** |

**M4 判据（据此修订）**：从「其余能力项整块 sha256 不变」改为「**`status`/`note`/`evidence` 三键 sha256 逐项不变 + 新增键仅允许 `http`**」。这样既允许结构统一，又不许顺手改文案。

**Q5（TL 追加）**：`SCHEMA` 版本号、`describe()` 的 `counts` **不动**。`http` 是可选字段，向后兼容，不升 `v1`；evidence 须写明「旧消费方读不到 `http` 也不受影响」。

### 成员主动提的两条防护：全接受

1. **M3-① 恒真风险**：成员自己发现「声明的每个路径都能在 `api.py` 找到」在**零登记时恒真**是假绿。TL 追加收紧：前置断言不是「≥1 项声明 `http`」，而是**3 条写路由全部已声明**（防止只登 1 条蒙混过关）。
2. **M2 现状已满足**：`incremental_update.note` 已有「增量抽取 + 全量重建图」两句 → 阶段 A 不会红。要求如实标注为「既有满足项 / 守卫用例」，**不得计为本 loop 的修复成果**。

### TL 追加的第三条

**M1 的「逐字符比对」必须是单向真比对**：测试须**从 `api.py` 源码解析**出路由集合（AST 或正则提取 `@app.post(...)`），再与 `capabilities` 的 `http` 声明比对。**禁止在测试里硬编码期望路径**（那等于把同一个字符串写两遍再自比，是自证）。

## 二十四、P3 阶段收口与 P4-L12 派工（13:5x，D-01 第 11 次自动推进）

成员回报 `T-D2MD-11` `DEV_SELF_CHECK_PASS`。TL 独立复核**通过**，证据 `P3-L11-TL-VERIFY-20261108.log`：

| 复核项 | 结果 |
|---|---|
| 指纹 | `capabilities.py 4820fac2…`（218→227）、**`api.py 4bf0b21f…` 未变**（= L10 值，证明只登记未碰路由）、测试 `c8c1b204…`、evidence 355 行 / `d5b6ad04…` |
| `http` 字段实测 | 3 项（`index_build`→`POST /v2/graph/build`、`incremental_update`→`POST /v2/graph/delta`、`community_report`→`POST /v2/graph/global`），`method` 大写、`path` 含 `/v2`；**其余 17 项仍严格三键** |
| Q2 分两类 | `community_report.note` 散文**原样保留**（仍含 `/v2/graph/global`）；`index_build`/`incremental_update` note 未动 |
| Q3 / Q5 | 3 条写路由全覆盖；`NO_REGISTER_POST` 是**测试常量**含理由；`SCHEMA` 未升版、`counts` 未变 |
| 独立复跑 | v2 `20 passed, 1 skipped`、hipporag `17 passed`；既有 `test_graph_engine_capabilities.py` 4 条零退化 |
| 变异 | 6/6；**M6 改 `api.py` 真实路由名 → 2 failed** —— 证明 M1 是「源码真值 vs 声明」而非自证 |
| 阶段 A | 7 红 / 9 绿 / 1 skip，且**逐条标注「修复红」与「守卫绿」**，未让守卫绿冒充成果 |
| 红线 | `api.py`/`rebuild.py`/`fence.py`/`delta_build.py` 全未变；18094 未重启（36.1h）；`kb_9=44`、`v2cand*` 空 |

### TL 采纳成员对 Q4 的修正

TL 在 Q4 裁定「M1 需 import fastapi 解析路由 → 只能 hipporag」，隐含把「比对路由」等同于「建 app 拿 `app.routes`」。**成员实测反驳成立**：AST 解析**源码文本**不需要执行模块，v2 环境即可解析出全部 9 条路由。故 M1/M3 在两环境都能真跑，只有「真建 app 再比一次」的加强用例需 fastapi（v2 侧 1 skip、单列不计通过）。**本 loop 实际强于 Q4 原裁定一档**，该 skip 不构成降级通过。

### P3 阶段代码面收口

**P3 三项（L9 DELTA 端点 / L10 per-kb state + fencing / L11 能力登记）全部内部收口。**

跨 loop 必传结论（已写入 `T-D2MD-10.blocker` / `T-D2MD-13.blocker`）：

| loop | 生效条件 |
|---|---|
| L9 / L10 | 进程内结构，**重启 18094 前不生效**；线上仍是单槽 `state` + 写死的 `fencing=1` |
| L11 | 模块级常量，**不 reload 即旧值**（无 `/capabilities` 端点，故非「缓存」而是「模块已加载」） |

**P4/P6 部署窗口必须复核「是否真正生效」，不得以「代码已合入」代替「线上已生效」。**

### P4-L12 派工

`P4-L12-PLAN.md` 已锁定（B1~B8 + R-1~R-8）。范围：新增 `ingest_pipeline/kb_delta.py`（`KbDeltaService.diff/plan/commit`）+ 改 `kb_ingest_service.py:142-221`（`IngestRequest` Pydantic、删 `file_url` 自动重解析、`source` 真传、去 `pop("payloads")` 歧义）。

**本 loop 两条禁止声明的红线**：

1. **不得声称 A-3 通过** —— A-3 要真实请求/响应样本 + 摄取服务访问日志，需起 18096，属 **P6**；本 loop 只做代码级契约验证。
2. **不得声称 18096 可用** —— 本 loop 结束时 18096 仍未启用。

另禁止：改 `api.py`（18094 侧）、改 P3 四文件、**启停任何服务**、改 Java（P5）、改部署脚本（L13）。

`T-D2MD-13.blocker` 中「P4 部署前必须完成 P3」已由 L9/L10/L11 解除，但**部署本身仍需 Owner 授权**（起 18096 属运行态变更）。

## 二十五、P4-L12 R-0 裁定（14:0x，PLAN 四处前提错误 + 两处环境冲突）

成员 R-0 交出 4 项前提不成立、2 项环境冲突，**均经 TL 现场核实成立**。这是本轮最有价值的一次 R-0 —— 它在写代码前拦住了 4 个会导致返工或架构错误的假设。

### TL 承认的 PLAN 缺陷

| # | 成员指出的问题 | TL 核实 | 责任 |
|---|---|---|---|
| **D-1** | `DiffResult` 只在 doc2md 仓；平台侧 `kb-manifest` **0 命中**；`scan_path`/`previous_manifest` 平台都拿不到 | **成立**（`grep kb-manifest` 平台侧 0、doc2md 侧有） | **TL 漏写 `diff` 的输入** |
| **D-2** | `IngestPlan` 契约不存在（§4.3 只定义 `DiffResult`），PLAN 却说「以 §4.3 为准、不自创」 | **成立** | **设计包与 PLAN 不一致** |
| **D-3** | `fence.revoke` 无 HTTP 面（契约 §3 要 `POST /v2/fence/revoke`，`api.py` 只有 `GET /v2/fence`） | **成立**（grep 0 命中） | **P3 遗漏，非本 loop** |
| **D-4** | 错误码「既有映射机制」不存在，`K.PipelineRefused` 统一 **502**，与契约 §5 冲突 | **成立**（`:206-214` 内联 except 链，`PipelineRefused`→502） | **TL 误判「已有机制」** |
| **D-5** | v2 无 pydantic，`IngestRequest` 在 v2 一条都跑不了 | **成立**（v2 `ModuleNotFoundError: pydantic`；hipporag 2.14.2 / fastapi 0.162.0） | **TL 写错主口径** |
| **D-6** | PLAN 路径笔误：`ingest_pipeline/kb_ingest_service.py` | **成立**，实际 `index_data_service/kb_ingest_service.py`（`ingest_pipeline/` 里是 `kb_pipeline.py` 等） | **TL 笔误** |

**关键一点：D-1 的「读 manifest」不是妥协，是设计包原签名。** `03-IMPLEMENTATION.md:312` 原文即 `def diff(self, kb: str, manifest_path: Path) -> DiffResult`。TL 的 PLAN 只写了「组装 wanted docs 读 `kb_state.chunks` 不重投影」，**没写 `diff` 的输入从哪来**，才让成员以为要跨仓调用或平台重算。

### 七问裁定

| # | 问题 | 裁定 |
|---|---|---|
| **Q1** | `diff()` 数据源 | **(c) 读 manifest 文件 + 无 manifest 退化**。`IngestRequest` 增可选 `manifest_path`：给了→全库 diff（`removed` 可得）；没给→只处理本请求文件（`added`/`changed` 由请求给、`removed` 空）。**响应必须带 `diff_source: "manifest" \| "request"`**，如实暴露数据来源；退化路径须有明确日志，**不得静默** |
| **Q2** | `IngestPlan` 契约缺位 | **内部 dataclass，不进响应**（响应只含 §1.2 七块）。追加断言：`IngestPlan` 的类型**不得出现在响应模型字段里**，防将来有人塞进响应 |
| **Q3** | `fence.revoke` 无 HTTP 面 | **本 loop 只验调用点与顺序（mock）**；**必须把「契约 §3 的 `POST /v2/fence/revoke` 缺失」显式登记为已知缺口**，转 L13 处理；**任何报告不得暗示「撤权已支持」** |
| **Q4** | 错误码表 | **(i) 建唯一 `ERROR_HTTP` 表**，11 条**逐条对齐 `02-CONTRACTS` §5**（`SOURCE_DIVERGED`/`CURSOR_CONFLICT`/`STALE_FENCING`→409、`NO_BASELINE_SNAPSHOT`/`ALL_REVOKED`→422、`KB_STATE_CORRUPT`/`DELTA_INCONSISTENT`→500、`COMMUNITY_INVALID`→207、`GRAPH_UNREACHABLE`/`INDEX_WRITE_FAILED`→502、`DOC2MD_ARTIFACT_INCOMPLETE`→400）。**表驱动测试**，每个 code 一条断言；**未在表中的 code → 500 + 日志含 code 原文**，不得静默退回 502 |
| **Q5** | `kb_delta.py` 是否可不依赖 pydantic | **允许**。`kb_delta.py` 用 dataclass / 纯 dict；`IngestRequest` 留 `kb_ingest_service.py`。**追加 AST 静态断言**：`kb_delta.py` 的 import 节点不含 `pydantic` / `fastapi`。**B5/B6/B7 必须在 hipporag 真跑**，不得只跑 v2 就声称覆盖 |
| **Q6** | 删 `file_url` 分支是否连 `_download_minio`/`_SCRIPTS_DIR`/boto3 一起删 | **删**，但边界收紧：只删 `kb_ingest_service.py` **文件内**的死代码与 import；**不动 `requirements*.txt`**（boto3 可能被别处用）；删后静态断言三者在该文件**零命中**；全量回归不退化 |
| **Q7** | `kb_state` additive 加 `parser_fingerprint`/`revoked_at` | **允许**。追加约束：**加字段不得触发 `version+1`**（schema 扩展 ≠ 数据变化），断言「只读旧 state 时 version 不变」；`_kb_state_txn` 回读须兼容缺字段的旧 state（按默认值） |

### TL 追加两问

**Q8**：`ProjectionRefused` 的 `code` **不在契约 §5 表内**，但现有映射是 400。请 R-0 补齐：它的 `code` 取值是什么？应归入 `DOC2MD_ARTIFACT_INCOMPLETE`(400) 还是按「表外 code」处理(500)？**不得因为「现在返回 400」就默认正确。**

**Q9**：`K.PipelineRefused` 改成按 `exc.code` 查表后，若 `exc.code` 为 `None` 或不在表内 —— 必须 500 + 日志含 code 原文。这条要有独立断言（防止改写后把未知错误静默成 502 或 200）。

### 成员已核实的可用事实（TL 采信）

```
cursor/version → kb_state.json（L7 已实现），读写 API: _kb_state_txn(store_root)（flock + version+1 + 重算 cursor + 回读校验）
                语义：txn「有变化才推进」→ B1 = 不进 txn；B3 = txn 之外先跑完三路
wanted docs  → kb_pipeline.build_wanted_docs(state, kb)（:453），天然跳过 status != ACTIVE ← B2 现成机制
projection   → kb_pipeline.project_snapshot(...)（:190）← B8 mock 它
source       → :201 本来就真传；真正丢 source 的是 file_url 分支（ingest_file 无该参数），删掉后自然全通
TaskReq/X-Internal-Token → Java 侧齐备，Python 侧 0 命中 → 本 loop 只留调用点
```

## 二十六、P4-L12 错误码表终裁（14:1x，成员 Q8 挖出真 bug）

成员 Q8 答复经 TL 现场核实**全部成立**，并暴露出一个**真实 bug**：`ProjectionRefused` 的 12 个 code 被一律映射 400，其中 **4 条语义不是「调用方产物脏」** —— 算法漏字（`PROJECTION_COVERAGE_LOST`）、切出空块（`PROJECTION_EMPTY_CHUNK`）、投影模式配错（`PROJECTION_MODE_INVALID`）、计划参数非法（`POLICY_INVALID`）都报 400，会让调用方以为是自己产物问题、拿同一份产物反复重试。

### TL 核实的 code 分布

```
rag_projection/projection.py
  :88   PROJECTION_MODE_INVALID          mode 不在 MODES        ← 服务端配置
  :133  POLICY_INVALID  chunk_chars<=0                          ← 服务端默认值
  :135  POLICY_INVALID  overlap 非法                             ← 服务端默认值
  :159  PROJECTION_COVERAGE_LOST         投影漏字               ← 算法问题
  :247  PROJECTION_EMPTY_CHUNK           切出空块               ← 算法问题
  另有 8 条 ARTIFACT_*                   产物不合法             ← 调用方问题

ingest_pipeline/kb_pipeline.py
  :205/:508/:626  KB_REQUIRED            调用方漏传 kb
  :216            GRAPH_API_UNREACHABLE  18094 不可达
                  GRAPH_BUILD_HTTP_<code> / GRAPH_BUILD_NOT_BUILT
  多处            KB_STATE_CORRUPT

kb_ingest_service.py：logger 0 命中（Q9 需新增标准库 logging）
```

### 三问裁定

| # | 问题 | 裁定 |
|---|---|---|
| **①** | `GRAPH_API_UNREACHABLE` 改名对齐契约？ | **不改名**。它在 `kb_pipeline.py`（L7 已验收），改名即改 L7 语义。表里登记 `GRAPH_API_UNREACHABLE → 502` 并注明「契约名 `GRAPH_UNREACHABLE` 的别名」；evidence 显式记录该命名不一致，留到 P6 文档收敛 |
| **②** | `PROJECTION_NOT_APPLICABLE` → 422 | **接受**。语义是「该文件没有可投影内容」，属**前提不满足**，与 `NO_BASELINE_SNAPSHOT` / `ALL_REVOKED` 同族；500 会把调用方引向「服务端故障、重试」的错误动作 |
| **③** | `ArtifactRefused` 40+ code 整体 400 | **接受**。这 40+ code 全属「产物不合法」**同一语义族**，异常类型本身已表达该语义；逐条抄进表会立刻过期（新增 code 即漏）。表只放「契约 11 条 + 表外白名单」，`ArtifactRefused` 一族整体 400 |
| **④** | `POLICY_INVALID` 400 还是 500 | **500**。当前 `chunk_chars` / `overlap` 全来自服务端默认值 → 部署缺陷 → 500 更诚实。**附加条件**：代码处必须注释「若将来 policy 参数进请求体，须改回 400」，并加断言「`POLICY_INVALID` 不得返回 400」 |

### ⚠️ TL 强调：`ProjectionRefused` **不得整体映射**

`ArtifactRefused` 能整体 400，是因为 40+ code 同族；**`ProjectionRefused` 跨三类语义，必须按 code 查表**：

- 8 条 `ARTIFACT_*` → 400（调用方产物问题）
- `POLICY_INVALID` / `PROJECTION_MODE_INVALID` → 500（服务端配置）
- `PROJECTION_COVERAGE_LOST` / `PROJECTION_EMPTY_CHUNK` → 500（算法问题，数据不完整）

若图省事把 `ProjectionRefused` 整体 400，等于把这个 bug 换个位置保留。

### 终版 `ERROR_HTTP` 表

**A · 契约 11 条（逐条对齐 `02-CONTRACTS` §5）**

```
DOC2MD_ARTIFACT_INCOMPLETE  400     SOURCE_DIVERGED        409
KB_STATE_CORRUPT            500     CURSOR_CONFLICT        409
NO_BASELINE_SNAPSHOT        422     ALL_REVOKED            422
STALE_FENCING               409     DELTA_INCONSISTENT     500
COMMUNITY_INVALID           207     GRAPH_UNREACHABLE      502
INDEX_WRITE_FAILED          502
```

**B · 表外白名单（显式登记 + 理由，不得省略）**

```
PROJECTION_NOT_APPLICABLE  422   该文件无可投影内容，前提不满足（同 ALL_REVOKED 族）
DOCS_EMPTY                 422   无可建图块，前提不满足
KB_REQUIRED                422   请求缺 kb，调用方漏传
GRAPH_API_UNREACHABLE      502   契约 GRAPH_UNREACHABLE 的别名（L7 既有命名）
GRAPH_BUILD_HTTP_*         502   动态 code，**前缀匹配**
GRAPH_BUILD_NOT_BUILT      502   18094 返回非成功体
POLICY_INVALID             500   服务端计划参数非法（chunk_chars/overlap），非调用方问题
PROJECTION_COVERAGE_LOST   500   投影漏字，算法问题，数据不完整
PROJECTION_EMPTY_CHUNK     500   切出空块，算法问题
PROJECTION_MODE_INVALID    500   INGEST_PROJECTION_MODE 配置错误，服务端问题
```

**C · 按异常类型整体映射（不进表）**

```
ArtifactRefused → 400   40+ code 同属「产物不合法」
ProjectionRefused → **必须按 code 查表**，禁止整体映射
```

**D · 兜底**

```
表外未知 code → 500 + 日志（含 code 原文 + kb + artifact_id）
```

有了 B 段白名单，Q9 的「表外 → 500」就不会误伤 `PROJECTION_NOT_APPLICABLE`（它是显式 422），这是成员提出 ② 的价值。

### Q9 落地补充（TL 批准）

`kb_ingest_service.py` **无 logger**（0 命中），允许新增 `import logging` + `getLogger(__name__)`（标准库，无新依赖，属文件内改动）。要求日志含 **code 原文 + kb + artifact_id/文件名**，便于排查「表外 code」时定位。

### 一处实现提醒

现有 `:220` 的 `code = 200 if result.get("status")=="OK" else 207` 是**成功路径**的部分失败；`COMMUNITY_INVALID → 207` 是**异常路径**。两者都返回 207 但语义不同（前者图路失败、后者图可用但 global BLOCKED），实现时须保证不互相覆盖，并在测试里各有一条断言。

## 二十七、P4-L12 返工与收口、L13 分段派工（14:3x，D-01 第 12 次自动推进）

### 本轮唯一一次「不予收口」

L12 首次自报时，成员称「三路在进事务之前全部完成 —— B3 是结构性保证」。TL 读源码发现**不成立**，退回返工：

| 必改 | R1 实际 | 后果 |
|---|---|---|
| **B3 顺序** | delta 在 `_state_txn` **之后**，cursor 已推进、失败无回滚 | delta 失败 → cursor 推进 → 重放变 `SKIPPED_FRESH` → **图永远建不起来且每次「成功」返回** |
| **`index_write` 缺失** | `build()` 只产计划，`apply()` 生产零调用；响应无该字段 | L13 Java 侧拿 `status=OK` 会以为三路已落 |

**教训**：成员的描述让 B3 看起来有结构性保证，实际没有。**若只看报告就收口，死锁会带到上线**。这是 TL 独立读源码的价值所在。

### R2 修正（TL 逐行核验通过）

```
:386 revoke → :389 prospective=deepcopy(load_state())+_apply_plan → :392 wanted
→ :402 delta（事务**前**）→ 失败则 return PARTIAL + cursor=plan.cursor_before + state_committed=False
→ :418 全部成功才 with _state_txn(): _apply_plan(state)
```

- `_delta is None` → `PARTIAL + "delta_runner_not_configured"`，不再静默 `OK`；
- `index_write` 如实块：UPSERT `{PLANNED, applied:false, required:true}`、DELETE `{NOT_APPLICABLE, required:false}`；
- status 规则 `landed = (not required) or applied`；**推论：UPSERT 恒 `PARTIAL`/207**。

判定力：阶段 A `6 failed` → 阶段 B v2 `24 passed`（TL 复跑 24 passed）；变异 M11/M12/M13 全捕获。**成员对 M11 的如实标注获认可**：「变异体写的是『不放宽 `if graph_error is not None`』，等价于顺序倒置的可观测后果，不是字面挪代码行；行序由 `test_b3_delta_runs_before_state_commit` 直接锁死」。

### TL 发现成员未记录的一侧边界（收口后补，不阻塞）

新顺序的**反向中间态**：delta 成功（图已改）→ `_state_txn` 抛异常 → **图已更新、kb_state 未提交**。成员只记了「delta 失败→状态不落」，未记这一侧。

TL 评估危害**有限且可收敛**：`_apply_plan` 按 `fid` 写、不覆盖其它文件；重放时 diff 看 state（旧）仍判 `changed` → 再 delta 一次 → 幂等收敛；期间「新图配旧 state」，但图与 18094 侧 sources 一致，**不产生悬空引用**（与 L9 的 `surviving` 缺陷不同质）。**不要求加代码** —— 若改为事务先落再 delta，就退回 R1 的死锁，取舍更差。要求 docstring 与 evidence 补说明。

### L12 交付性质（必须传下去）

**L12 交付「不可独立运行的半链路」**：UPSERT 恒 207、索引未写、delta runner 未配。这不是缺陷，是 PLAN 边界，但 L13 必须补齐，否则上线即故障。

### L13 分段派工

`P4-L13-PLAN.md` 已按三段划分：

| 段 | 内容 | 授权 |
|---|---|---|
| **A** | 让 18096 逻辑完整：接线 `index_writer.apply`、配置 delta runner、补 `POST /v2/fence/revoke` | **可自主**（纯代码 + 离线 mock） |
| **B** | 部署定义（启动脚本/watchdog/up.sh/systemd/env/ENV-CONTRACT）+ Java 回写改造 | 可写文件、**不执行** |
| **C** | 起 18096 + 真实 A-3 + 停 18094 演练 | **需 Owner 显式授权** |

**A 段关键不确定点（R-0 必须先答）**：`POST /v2/fence/revoke` 涉及 18096↔18094 **跨进程状态共享** —— fence 若只在 18094 内存，18096 无法直接 revoke。可能超出 A 段，须 R-0 后回 TL 重新划段。

另必核：Java 侧是按 HTTP 状态码还是 body `code` 判断失败 —— 决定 L12 的 `response.status_code = code` 修复是否必要。

## 二十八、P4-L13A R-0 裁定（14:5x，含 TL 补上的删除端点事实与一处删库高危）

成员 R-0 回答了 7 项，并**主动上报一个可能改变 A 段完成定义的问题**：`delete_scope` 只有计划、无执行点 → 当前「写」是「只增不减」。TL 核实**成立**，且比成员报告更乐观也更有风险。

### TL 核实结果

| 成员结论 | TL 核实 |
|---|---|
| `fence` 已持久化（`save/load` 原子替换） | **成立**：`fence.py:62-75`、`api.py:258/269/452/498`、`delta_build.py:142` → A 段方案可行，**不需改 `fence.py`** ✅ |
| `delete_scope` 只有计划、无执行点 | **成立**：`delete_scope` 的 docstring 明写「离线，不执行删除」「落地由 L7 生产调用点完成」；**全仓生产代码零调用**（仅 `test_index_writer.py` 模拟过滤） |
| `apply` 只发 insert | **成立**：`IndexWritePlan` 只有 `es_plan`/`milvus_plan`，无 delete 字段；`apply` 逐 body POST insert |
| 19527 写后剪枝仅 `duplicate_flag=True` | **成立**：`es.py:479/538`；L6 硬约束 `duplicate_flag=False` → 剪枝不生效 |

### TL 补充：删除端点**存在**（成员未查到）

成员只确认了 insert 端点，判为「删除能力缺失」。TL 查到**两侧都有删除接口**：

```
19527 /del_doc_by_col  → delete_by_col_documents_async → es.delete_by_query(index, body)
19526 /del_doc_by_col  → coll.delete(expr=f'{col_name} in {col_values}')
```

且 `delete_scope()` 的返回结构（`col_name="metadata.file_id"`、`col_values=[fid]`、`targets`）**正是为这两个接口设计的** —— 设计是完整的，缺的只是「L7 该接没接」。

**结论：A 段装得下，不需要重新划段，也不需要改 `index_writer.apply` 的既有语义之外的东西。**

### ⚠️ TL 发现一处删库高危（必须在 A 段加防护）

```1419:1422:index_vector_service/src/index_vector_service_pactera/milvus_kb_service.py
if not del_param.col_name and del_param.collection_name:
    coll.drop()                              # ← col_name 为空 = 删掉整个 collection
elif del_param.col_name:
    delete_res = coll.delete(expr=f'{del_param.col_name} in {del_param.col_values}')
```

**若 `col_name` 传空/传 None，19526 会 `drop()` 整个集合** —— 一个字段拼错就把整库向量删掉。这不是理论风险：`delete_scope` 的 `col_name` 来自常量字符串，一旦被改成 `None`/`""` 就是灾难。

**要求**：A 段必须在调用前断言 `col_name` 非空且等于 `metadata.file_id`、`col_values` 非空且只含目标 fid；并加一条**反例测试**「`col_name` 为空时拒绝发送请求」（在客户端侧拦截，不依赖服务端）。

### 七问裁定

| # | 问题 | 裁定 |
|---|---|---|
| **Q1** | ES/Milvus URL env 名 | 改为 **`LLMKE_ES_BASE_URL` / `LLMKE_MILVUS_BASE_URL`**（不是 `_WRITE_URL`）—— 因为一个 base 要同时支持 insert 与 delete 两个路径。默认 `127.0.0.1:19527` / `127.0.0.1:19526`；A 段只用替身，不真连 |
| **Q2** | A3「显式记录」以什么为准 | 同意 `index_write.compensation={needs, completed_sides, calls}` + 结构化 `logger.error`。**追加**：`needs_compensation=true` 时 **status 不得为 `OK`**（与 L12 的 `applied` 规则同源） |
| **Q3** | `delete_scope` 是否纳入 | **必须纳入**。理由：不纳入则 A1 的 `OK` 是「写了一半的 OK」—— 重摄取缩水文件后旧块残留，检索会命中已删内容；这比「恒 207」更严重（207 是显式失败，这是**静默错误**）。**A1 口径改为「UPSERT 写入完整（insert + delete）」**，不是「apply 已接线」 |
| **Q4** | `GET /v2/fence` 加可选 `kb` | 同意。缺省读 `states[""]` 行为不变；有 `kb` 时读该库 slot 的 fence；断言「按 kb 撤权后 `GET ?kb=` 能读到」 |
| **Q5** | 未建图时撤权无处落盘 | 同意「内存生效 + 响应 `persisted=false`」。**追加**：`persisted=false` 必须显式；并在 B/C 段复核「未建图期撤权在重启后丢失 → 可见性回退」的风险 |
| **Q6** | `post_graph_delta` 放哪 | **新建 `ingest_pipeline/graph_client.py`**。不动 L7/L8 已验收的 `kb_pipeline.py` |
| **Q7（TL 追加）** | 删除的集合范围 | `delete_scope.targets` 含 **4 个目标**（`{prefix}{kb}` 与 `{prefix}table_chunks_{kb}`，各 es/milvus）。**4 个都要删**，不得只删主集合 —— 否则 `table_chunks` 通道残留已删内容（L12 已确认 `table_chunks_kb_9=2` 真实存在） |

### 执行顺序要求

```
delete ES(2 collections) → insert ES → delete Milvus(2 collections) → insert Milvus
```

**per-侧先删后写**，避免「ES 已删、Milvus 未删」的跨侧窗口；也避免「旧块与新块共存」被检索命中。

### 这是谁的遗漏（如实记录）

`delete_scope` 的 docstring 写「落地由 L7 生产调用点完成」，但 **L7 的 `consume_for_kb` 零命中** → **L6 产出正确、L7 未接、本 loop 补**。不是 L12 的缺陷。

## 二十九、L13A R-0 补充裁定（15:0x，字段跨侧错配 + v2cand 双重阻塞）

### 成员新发现：同一个 `col_name` 在 ES / Milvus 两侧语义**相反**

```11:21:index_fulltext_service/src/index_fulltext_service_pactera/controller/es_query.py
def init_field_body(field, value, queryType: QueryType):
    ...
    if queryType != QueryType.PK:
        f = f"metadata.{field}.keyword"      # ← 服务端自动拼 metadata. 前缀 + .keyword 后缀
```

而 `delete_scope()` 返回的 `col_name` 是 `"metadata.file_id"`。**原样发给 19527 会变成 `metadata.metadata.file_id.keyword` → 0 命中 → 静默不删、接口返回 200。**

| 侧 | `col_name` 应传 | 原因 |
|---|---|---|
| ES 19527 | **`file_id`** | 服务端自动拼 `metadata.<col>.keyword` |
| Milvus 19526 | **`metadata.file_id`** | 原样拼 `expr=f'{col_name} in {col_values}'` |

TL 核实 `es_query.py:11-21` 原文，**成立**。这比删库更隐蔽：删库至少报错，这个是**返回 200 但什么都没删**。

**裁定**：客户端**按侧映射** `col_name`，两侧各一条断言。**并且 A2 的断言不能只验证「我们传了 `file_id`」**，要验证「发给 19527 的 body 经 `init_field_body` 变换后 == `metadata.file_id.keyword`」，即**端到端的字段路径正确性**，而非客户端自说自话。

### 成员新发现：`v2cand_*` 是 C 段的第二重阻塞

```
写入目标由 index_writer 固定为 v2cand_<kb> / v2cand_table_chunks_<kb>
_cat/indices/v2cand*  → 0（TL 现场确认）
19527 写入路径先取 mapping，拿不到即 500；删除路径遇不存在索引返回 200「无需删除」
→ 真实运行时：insert 500 + delete "成功" = 「删了但没写」
```

TL 确认：`v2cand*` 为空、19527 在线（HTTP 200）。该推论成立。

**这意味着 L13-C 有双重前置，不是单一授权就能跑**：

| 前置 | 性质 | 归属 |
|---|---|---|
| 起 18096 | 运行态变更 | Owner 授权 |
| 创建 `v2cand_*` 影子索引 | 运行态变更 | **L8 模式 B 授权（Owner 未给）** |

**不得**用「改 `index_prefix` 指向既有索引」绕过 —— 那会把影子写进线上索引，碰 L6/L8 已验收语义，绝对禁止。

已写入 `T-D2MD-13.blocker`。

### 补项答复（TL 采信）

- `delete_scope().targets` 的 `index_name` / `collection_name` 正好匹配 19527 `OperateDataModel.index_name` 与 19526 `DataParamModel.collection_name`；
- 19527 `del_doc_by_col` 只需 `col_name` + `col_values`，`condition_json` 是可选空默认；`IndexModel` 只有 `index_name`，不要求 `document_list`（那是 `InsertDataModel`）。

## 三十、P4-L13A 收口与 B 段派工（15:1x，D-01 第 13 次自动推进）

成员 A 段 `DEV_SELF_CHECK_PASS`。TL 复核**功能通过、有条件转 B**，证据 `P4-L13A-TL-VERIFY-20261108.log`。

| 复核项 | 结果 |
|---|---|
| 指纹 | `kb_delta.py c96f724f…`、`graph_client.py a4488093…`（新）、`api.py af387855…`（新增 revoke）、`fence/index_writer/capabilities/kb_pipeline` **全未变** |
| A1~A6 | 全部核实成立；`do_deletes("es")→do_insert("es")→do_deletes("milvus")→do_insert("milvus")` per-侧先删后写，4 个 target 全删 |
| A2 字段断言 | **从 19527 源码载入 `init_field_body`** 比对，并反证「统一传 `metadata.file_id`」得 `metadata.metadata.file_id.keyword` —— 服务端实现变了测试会红 |
| M17 | 未捕获但**区分正确**：去掉空 col_name 防护仍被相等校验拦下 → 防护有效、该行非判别力来源；补 M17b 证明。「冗余守卫 ≠ 有效断言」 |
| L12 断言改动 | **合规**：事实变了（A1 接真实写入），且保留失败路径 `PARTIAL` 与 `state_committed=False` 断言，未打开「失败也报 OK」的路 |
| L11 守卫 | `NO_REGISTER_POST` 加 `POST /v2/fence/revoke` —— **守卫按设计生效**，走白名单未改 20 项集合 |
| 红线 | 18096 未监听、18094 未重启、`v2cand*` 空、`platform/r12` 0 改动、测试均注入替身 |

### 两处防护缺口（C 段前必修）

| 缺口 | 事实 | 要求 |
|---|---|---|
| **写入端点 fail-open** | `es_base = 参数 or env or DEFAULT("http://127.0.0.1:19527")`；`poster = poster or index_writer._post_json`；TL 实测 19527 **在线** → 默认目标就是真实服务。成员自述「不注入会真的 POST 线上」 | 加 `LLMKE_ALLOW_DEFAULT_WRITE_TARGET` 显式开关；未设且无参/env → 抛 `INDEX_WRITE_FAILED` / 启动 fail-fast，不得回退 `DEFAULT_*` |
| **`do_insert` URL 回退脆弱** | `es_url = url_es or self._es_base + ES_INSERT_PATH`，`side=milvus` 时回退成真实 ES URL；安全性依赖「空 plan 不发请求」的隐含行为 | 改显式 `None`，并断言「`side=milvus` 不产生任何 ES 请求」 |

**判定**：这两项是**加固不是功能缺陷**，不阻塞 B 段（只写脚本不执行），但 **C 段起服务前必须完成**。

### B 段派工

范围：`r12-kb-ingest-start.sh`（幂等启动 + `/openapi.json` 探针）、`r12-watchdog.sh`、`up.sh`、`systemd/`、`R12-ENV-CONTRACT.md`、启动自检 fail-fast、Java `RemoteV2IngestUtils.java:96-100` 回写。

**必核项**：Java 侧按 HTTP 状态码还是 body `code` 判断失败 —— 决定 L12 的 `response.status_code = code` 是否必要。

**B 段红线**：不执行部署脚本、不启停服务；脚本只用 `bash -n`/静态检查；`platform/r12` 每个被改文件须给**改动前 md5 + `git diff` 全文**，不接受口头描述。

## 三十一、L13A 加固裁定：接受「惰性 fail-closed」，但须兑现可观测性（15:2x）

成员完成两处加固后，对 (a) 提了一个与 TL 原要求不同的实现选择，**TL 采纳**。

### 成员的方案与理由

不在**构造期**抛，而在**首次写入时**抛（`INDEX_WRITE_FAILED` 502，永不回退默认）。理由：构造期抛会让 `import kb_ingest_service` 直接炸（模块级 `app = create_app()`），**连 `/health` 都拿不到**，现场无法诊断「为什么起不来」。

**TL 裁定：采纳。** 这是标准的 liveness / readiness 分离，比 TL 原要求（构造期 fail-fast）更好：
- 进程能起 → `/health` 可访问 → 能诊断
- 写入被拒 → 不会带病写线上

**但**——方案把「fail-fast」的一半责任转移给了启动自检与 `/health`，所以**这两项是方案成立的前提，不是可选项**。

### TL 核实：前提尚未兑现

```
kb_ingest_service.py:306-316  /health 返回 schema/status/store_root/graph_api/doc2md_lock/doc2md_config/wired
                              ← 无 write_targets 字段；status 硬编码 "ok"
ingest_pipeline/kb_delta.py:197  write_targets_configured() 已定义
grep 全仓调用点 → **零**（只有定义）
```

**即：惰性 fail-closed 目前等于「写入会拒 + 没有任何可观测信号」。**

### 裁定与硬约束

| # | 约束 | 归属 |
|---|---|---|
| 1 | `/health` 增 `write_targets: write_targets_configured()`，且 `configured=false` 时 `status` **不得为 `"ok"`**（用 `"degraded"`） | **B 段** |
| 2 | 加断言：`configured=false → status != "ok"`、`configured=true → status == "ok"` | **B 段** |
| 3 | B 段启动自检脚本**必须调用 `write_targets_configured()` 并 `exit 1`**（`configured=false` 时不进入可用状态） | **B 段** |

**若 B 段不做这三项，则惰性方案不成立** —— 等于把 fail-closed 降级成「静默带病运行」，届时须回退到构造期 fail-fast 并接受 `/health` 不可达的代价。

### 其余核验

| 项 | 结果 |
|---|---|
| `write_targets_configured()` | 返回 `{es, milvus, allow_default, configured, env, defaults}`，**纯读 env、不连网、不实例化**，适合自检 ✅ |
| fail-closed 点 | 未配置且无开关 → 抛错，错误文案明写「默认目标是线上服务，需 `ALLOW=1` 才允许回退」（`:192-194`）✅ |
| 开关=1 回退 | 有 `logger.warning` 显著告警（`:187`）✅ |
| `do_insert` 显式化 | `url_es = (self.es_base + ES_INSERT_PATH) if side == "es" else None`，不再依赖「空 plan 不发请求」✅ |
| 三层断言 | `fail_closed_without_config` / `default_target_requires_explicit_switch` / `env_configured_needs_no_switch` ✅ |
| 变异 | M19 恢复静默回退 → 1 failed；M20 恢复 `url_es or ...` → 1 failed；md5 复原 ✅ |
| 独立复跑 | `test_kb_delta_l13.py + test_kb_delta_l12.py` = **41 passed**（TL 现场） |

## 三十二、P4-L13B 收口：P4 代码面完成（15:5x，D-01 第 14 次自动推进）

成员 B 段 `DEV_SELF_CHECK_PASS`。TL 复核**通过**，证据 `P4-L13B-TL-VERIFY-20261108.log`。

### 三条硬约束兑付 → 惰性方案成立

`/health` 增 `write_targets`（`configured=false` → `status="degraded"`、HTTP 恒 200）+ 4 条断言；自检调 `write_targets_configured()` 未配置 `exit 1`（`--check` 无 env → exit 1 / 配齐 → exit 0）。**「写入会拒但无可观测信号」的状态已消除。**

### 必核项结论（本轮最有价值的技术判断）

**HTTP 状态码与 body `code` 两者都依赖，缺一不可**：

```
HTTP 4xx/5xx → RestTemplate 抛 HttpStatusCodeException → HTTP 码决定「是否抛」
207 是 2xx   → HTTP 层看不出，必须读 body code 才能识别 PARTIAL
```

→ **L12 的 `response.status_code = code` 必要但不充分**：不修则 Java 当成功继续；只读 HTTP 码则 207 与 200 无法区分、`RETRY` 丢失。**两层都得有。**

`classify` 5 分支核实：`2xx+200→OK`、`2xx+207→RETRY`、`2xx+其它→RETRY`、`4xx→PARSE_FAIL`、`5xx→RETRY`；`HttpStatusCodeException` **就地分类**不再冒到调用方只留 log。

### 成员自己发现的坏味道（TL 特别认可）

`--check` 第一版会 `mkdir -p` 创建 `platform/r12/data/{artifact-store,kb-state}`。成员实跑发现并改为「测最近已存在祖先可写」，删除误建目录。**TL 现场确认 `platform/r12/data` 不存在。**

价值在于：**自检一旦有副作用，「只检查」就不是只读** —— 运维拿 `--check` 排障会污染环境，还会让后续「目录不存在」的判断失真。

### TL 一处误判（如实撤回）

TL 曾担心 `Type=oneshot` + `Restart=on-failure` 无效。核实：既有 `r12-alg.service` 就是 `Type=oneshot` + `RemainAfterExit=yes` + `Restart=on-failure` + `RestartSec=30`，`r12-models`/`r12-java@`/`r12-watchdog` 同为 oneshot。**新 unit 与既有模式完全一致，`systemd-analyze verify` 未报错。TL 撤回疑虑，不做修改要求。**

### P4 代码面完成

L12 ✅ + L13-A ✅ + L13-B ✅。`bash -n` 三脚本全 OK，`up.sh` 的 18096 不进 must（正确：未授权时不该让既有 verify 变红，C 段后改 must）。

**剩余 C 段为运行态操作，需 Owner 双重授权**：

| 前置 | 归属 |
|---|---|
| 起 18096 | Owner 授权 |
| 创建 `v2cand_*` 影子索引 | **L8 模式 B 授权** |

C 段其它前置：Java 编译 + `classify` 5 分支单测、`up.sh` 18096 改 must、真实 A-3 样本与访问日志。**生产不得设 `LLMKE_ALLOW_DEFAULT_WRITE_TARGET=1`。**

## 三十三、L13-B 补充产物与停手待命（16:0x）

成员按 TL 指示**未推进 C 段**，只做两件不动运行态的事，TL 核实：

| 产物 | 核实 |
|---|---|
| `RemoteV2IngestClassifyTest.java`（`4fe6775d…`，7 个 `@Test`） | 文件存在、`??` 未跟踪、与 `classify` 同包；**未编译、未跑 maven** |
| `kb-ingest.env` 模板收紧（`4a414911…` → `e4c54537…`） | `LLMKE_ALLOW_DEFAULT_WRITE_TARGET` **无任何示例值**，只有注释「**生产环境禁止设置**」+ 后果说明「会让『配错了』表现为『默默写对了地方』」 |

**红线确认**：18096 未监听、18094 两 pid 未变、`platform/r12/data` 不存在。

### ⚠️ 必须标注：Java 单测是「待验证产物」，不构成覆盖

**7 个用例写在那里但一个都没跑过** —— 可能编译错误、断言写反、JUnit 5 版本不匹配。文件存在 ≠ 测试通过。

**已写入 `T-D2MD-13.next_action`**：C 段第一步必须 `mvn -pl rag-index-service test -Dtest=RemoteV2IngestClassifyTest` 通过，否则该文件不得作为 `classify` 的覆盖证据。

**风险提示**：这类「未执行的测试文件」最容易产生**虚假覆盖感** —— 后来的人看到 7 个用例、看到分支表齐全，就会认为已覆盖，而实际一行都没执行过。与 L9 的 `or 0`、L12 的「三路在事务前」同类：**看起来对，但没被验证**。

### 成员的两条判断（TL 采信）

1. `--check` 的只读性是**硬要求不是洁癖** —— 运维排障时若会建目录/写文件，既污染环境，又让后续「目录不存在」的判断失真；
2. `up.sh` 的 18096 暂不进 must —— 原因已写在代码注释里，避免后人以为漏了。

### C 段 mvn 判据（TL 采纳成员补充，已写入 TASKS）

成员指出：`mvn -pl rag-index-service test -Dtest=RemoteV2IngestClassifyTest` 的判据**不是 `BUILD SUCCESS`**，而是 **`Tests run: 7` 且 failures/errors 为 0**。

原因：`-Dtest` 名字写错、或被 surefire 跳过时，**同样是 `BUILD SUCCESS` 但 tests run 0**。只看 BUILD SUCCESS 等于「跑了但没真跑」—— 与 L12 的「`pytest.raises(Exception)` 被 `NotImplementedError` 蒙过」、以及本轮的「7 个用例没执行过」是同一种假绿。

**已写入 `T-D2MD-13.next_action`。**

另记录可访问性前提：该测试依赖 `classify` 保持 **`package-private static`**。若将来改成 `private` → 编译期失败（有利）；改成 `public` → 无任何提示（不影响正确性，仅记录）。

## 三十四、Owner 授权 L13-C：影子索引 + 起 18096（16:2x）

**Owner 决策**：授权 2+3 ——「先给 2+3，我就能跑通 P4-C 并把影子索引建起来，之后 P5 切读、P6 验收才有基础」。

授权范围严格限定为：① 创建 `v2cand_*` 影子索引；② 启动 18096。**不含**：重启 18094、改 `index_prefix`、写线上索引。

### 基线（TL 16:27 实测）

```
18094 在线 pid 3189651/3202203（2026-11-07 01:20/01:21）
18096 未监听 | 19527/19526 在线 | kb_9=44 | v2cand*=0
```

### TL 发现的两个必须先解决的问题

**① 图隔离可能不成立（最大风险）**

`IngestRequest.graph_root` 默认 `None` → `_build_service` 读 `LLMKE_V2_GRAPH_ROOT` → 若也为空，18094 用**自身默认 root = 线上图**。

**C 段所有 ingest 必须显式带 `graph_root` 指向影子目录**。且 **R-0 须先确认 `POST /v2/graph/delta` 的 `root` 参数是否真被 18094 采纳** —— 若 18094 忽略该参数，则**图无法隔离，C3 必须停止回 TL**，不得为了跑通去改线上图。

**② 设计包的 C5 故障演练不能照做**

原文要求「停掉 18094 → `GRAPH_UNREACHABLE` + Java 回写 `RETRY`」。**18094 是在线服务承载查询，不得停。**

**替代方案**：把 18096 的 `LLMKE_V2_GRAPH_API` 指向**不存在的端口**（如 `127.0.0.1:19999`）→ 模拟不可达，效果等价且零风险。

### C 段 PLAN

`P4-L13C-PLAN.md` 已锁定，**分五步、每步验证后才进下一步，禁止一把梭**：

| 步 | 内容 | 回滚 |
|---|---|---|
| C1 | 建 4 个影子目标（2 ES index + 2 Milvus collection） | 删索引/collection |
| C2 | 起 18096（前置：Java 编译 + `Tests run: 7`） | 杀 18096 pid |
| C3 | 真实 ingest（显式 `graph_root`） | 删影子图 |
| C4 | 幂等 / 撤权 / 删除（缩水文件不残留旧块） | — |
| C5 | 故障演练（**错端口**而非停服务） | 改回 graph_api 重起 |

### 线上保护（每步都验）

`kb_9` 的 `_count` 与 store size 必须逐字节不变；线上图目录 mtime 不变；18094 pid 前后一致。任一不过 → 停在该步回 TL。

### 收尾归属

影子索引/图的**保留还是清理、18096 是否长驻**，由 TL 在 C 段完成后按 P5 计划决定，**成员不得自行删除或停服务**。

## 三十五、L13-C R-0 裁定（16:4x，含成员一处极关键的自我纠正）

成员 R-0 未建索引、未起服务、未写代码。TL 逐项核实，**并补做一个它没做的检查**。

### ⚠️ 成员自我纠正：验证基线取错 = 失败的通过

成员起初按 `DEFAULT_ROOT=".artifacts/api-root"` 推断「线上图 = 本仓 `.artifacts/api-root`」。**它自己读 `/proc/<pid>/environ` 发现错了**：

```
LLMKE_V2_ROOT=/home/szf/data/dev/llmke-r12/platform/r12/data/graph-root   ← 另一个仓
```

**TL 独立核实全部成立**：

| 检查 | 结果 |
|---|---|
| `/proc/3189651/environ` 的 `LLMKE_V2_ROOT` | `.../llmke-r12/platform/r12/data/graph-root` ✅ |
| 真实线上图 `kb_9/current.json` | mtime `2026-11-07 21:31`、`dir=...snapshot-20261107212905-365431-g0`、`fencing=1`、`documents=46`、`generation=0` ✅ |
| `.artifacts/api-root` 是否有 `kb_9/current.json` | **没有**（只有一个旧 snapshot）✅ 更正正确 |

**这是本轮最危险的一处**：若按 `.artifacts/api-root` 做「线上图未变」断言，该目录根本没有 `kb_9` —— **断言会永远通过**，C 段可能真改了线上图而显示「通过」。

**这比「测试没跑」更隐蔽**：测试跑了、通过了，只是**比错了对象**。TL 已把 PLAN §二 的错误路径更正，并要求基线只能取 `/proc/<pid>/environ` 的真实值，不得靠读代码猜默认值。

### 三问裁定

| # | 问题 | 裁定 |
|---|---|---|
| **Q1** | 图隔离用 env 还是改代码优先取 `req.graph_root` | **(A) 用 env `LLMKE_V2_GRAPH_ROOT`**。C 段验证的是**已测版本的运行态行为**，不该同时改代码（否则验证的不是已测版本）。代价：PLAN 里「每次请求显式带 `graph_root`」放宽为「服务级 env 指向影子」<br>**追加双重确认**：① 启动前从 `/proc/<18096 pid>/environ` 确认 env 生效；② 响应里 18094 回显的实际 `root` 必须等于影子路径（`delta_build.py:265` 会回显） |
| **Q2** | C3 首次 ingest 用 `FULL_REBUILD + fallback_reason` | **同意**（空影子 root 首次会 422 `NO_BASELINE_SNAPSHOT`，链路已核通：`FULL_REBUILD` → `requested_mode="full"` → `_resolve_mode` 走 `explicit:full` 绕过 canary → `rebuild()` 建首快照）。<br>**追加硬要求：C3 拆两步** —— `C3a` 用 FULL 建首个影子快照（并注明「首次是全量建图，不是 delta」），`C3b` **再用 UPSERT 验证真正的 DELTA 路径**。只做 C3a 等于整个 C 段没验证增量。 |
| **Q3** | 线上图基线改用 llmke-r12 路径 | **确认**，且基线记三项：`current.json` 的 **mtime + dir + fencing**；C 段结束 md5 必须不变 |

### TL 追加核实：Milvus 集合名 `_` 前缀在两侧**一致**

成员提示「Milvus 服务端给集合名加 `_` 前缀」（`v2cand_kb_9` → `_v2cand_kb_9`）。TL 进一步核实**删除路径是否也加**（若不一致会「删不到」）：

```python
# 统一入口
collection_name = "_" + collection_name.replace("-", "_")        # :182

# 删除路径 del_doc_by_col 也走它
collection_name = generate_collection_name_uuid(del_param.collection_name)   # ← 加过前缀
if not is_collection(collection_name, ...):
    return BaseResponse(code=200, msg='未执行删除，milvus未找到集合: ...')     # ← 静默 200
```

**结论：insert 与 delete 前缀处理一致，不会因前缀错配而「删不到」** ✅

**但有两处必须记录**：
1. **C1 验收要按 `_v2cand_kb_9` 断言**（否则误判「没建成」）；
2. **`generate_collection_name_uuid` 对含中文/非法字符的名称会转 uuid5** → kb 名必须是纯 ASCII。`kb_9` 安全；**将来若 kb 名含中文，ES（不加前缀）与 Milvus（转 uuid）的名字会不一致** —— 这是跨服务的命名耦合隐患，记入后续切片。

另：`del_doc_by_col` 遇不存在集合返回 **200 + 「未执行删除」** —— 印证 C1 必须先建好 collection，否则 C4 的删除会静默失败（与「只增不减」同源）。

### TL 承认的 PLAN 错误

PLAN §二 原写 `platform/r12/data/graph-root` **在本仓不存在**（实为 llmke-r12 运行仓）。已更正，并把「基线只能取 `/proc/<pid>/environ`」写成硬要求。

## 三十六、C1 通过 + 抓出 A 段真缺陷（16:5x，含 TL 复核疏漏）

### C1 结果（4 个影子目标已建）

```
ES      v2cand_kb_9 / v2cand_table_chunks_kb_9    0 条，metadata.file_id.keyword 存在
Milvus  _v2cand_kb_9 / _v2cand_table_chunks_kb_9  pk INT64 / vector dim=1024（集合总数 12）
线上零写入：kb_9=44、table_chunks_kb_9=2、原 5 个索引 docs/store.size 逐字相同
18094 pid 3189651/3202203 未变；线上图 kb_9 mtime 2026-11-07 21:31:00 + current.json md5 e2d0f754… 逐位不变
18096 仍未监听
```

成员踩坑记录：建 Milvus 集合在 **19526 `/create_milvus_collection`**，不在 19630（那是 Milvus 自身 REST，只有 list/describe/query）。

### ⚠️ C1 校验抓出 A 段真缺陷：Milvus 删除字段名写错

TL 独立核实（`describe _v2cand_kb_9`）：

```
fields = ['pk','text','vector','source',...,'file_id','page_number',...]   ← file_id 是**顶层**字段
无 metadata 嵌套字段
```

而代码里：

```85:ingest_pipeline/kb_delta.py
MILVUS_DELETE_FIELD = "metadata.file_id"        ← 错
ES_DELETE_FIELD     = "file_id"                 ← 对
```

拼进 `expr='metadata.file_id in [...]'` → **字段不存在 → 删不到**。后果：C4 的「缩水文件不残留旧块」会是**假的通过**（HTTP 200 + 0 删），与「只增不减」同源。

**正确结论（成员自我更正）**：两侧**都传 `file_id`**，只是理由不同 —— ES 由服务端拼成 `metadata.file_id.keyword`；Milvus 原样拼、顶层字段就叫 `file_id`。「不能统一成 `metadata.file_id`」这条约束仍成立，只是两侧**正确值恰好相同**。

### TL 承认的复核疏漏（必须记录）

A2 时 TL 要求「不许自说自话、要端到端验证服务端真值」。成员给 **ES 侧**做了（从 19527 源码载入 `init_field_body` 比对），但 **Milvus 侧没做**。

**TL 复核时也只核了 ES 侧就通过了，没检查 Milvus 侧是否有对称断言。**

这是**对称要求的不对称检查** —— 我提的要求是对的，但验收时只看了被点名的那一处。代价是这个 bug 活到了 C1。

### 教训：mock 掉的边界，必须有另一层验证补上

该缺陷为什么单测没抓到：`poster` 被 mock，请求不真发；断言只检查「我们发出去的 `col_name` 是什么」，没有一条检查「这个字段名在服务端真实存在」。

**「mock 通过」≠「真跑通过」。** 这正是 C 段存在的意义 —— **C 段的价值不只是「跑通」，而是用真实环境校验单测的假设**。

### Q4/Q5 裁定

| # | 事项 | 裁定 |
|---|---|---|
| **Q4** | `MILVUS_DELETE_FIELD` → `file_id`；改测试；新增从 Milvus `describe` 读真实字段名的断言 | **批准**。测试改名要准确：不是「use different col_name」，而是**两侧都用 `file_id`、理由不同**；并保留反向断言「统一传 `metadata.file_id` 会让 ES 双前缀 + Milvus 找不到字段」。新增断言必须是**服务端真值 vs 我们的值**，不许自说自话 |
| **Q5** | C 段中途改代码是否允许 | **允许**。与 Q1 拒绝「改代码」的区别：Q1 拒绝的是**为了绕过验证障碍而改**（图隔离改用 env）；Q5 允许的是**被真实环境抓出的实现缺陷**。顺序：改 → 重跑 L12/L13 全量 → 再 C2 |

### TL 追加的 C4 硬要求

**删除验证不能只看 HTTP 200**（`del_doc_by_col` 遇不存在集合/字段也返回 200）。必须验「删前 N 条 → 删后 0 条」的实际数据变化（`_count` 或 query），否则「删不到」会表现为「删成功」。

### 另记（成员提出，TL 采信）

`v2cand_kb_9` 的 `metadata.source` **没有** `.keyword` 子字段（`file_id` 有）→ 19527 的「写后按 source 剪枝」在影子索引上 0 命中。当前 `duplicate_flag=False` 不走该路径、删除走 `file_id`，**不影响 C4**；仅记录，防止将来打开 `duplicate_flag` 时误以为剪枝生效。

## 三十七、Q4 修正核实通过 + 放行 C2（17:0x）

### 修改核实

```
kb_delta.py:90/91  ES_DELETE_FIELD = "file_id" / MILVUS_DELETE_FIELD = "file_id"   ✅
md5                d9ed9927 → f29142fb1aef13fed5e7559aefb2bb7f                    ✅
_milvus_schema_fields → ast.parse(milvus_kb_config.py) 取 MILVUS_FIELDS 顶层键     ✅ 与 ES 侧同一标准
复跑                41 → 42 passed（+1 新增 schema 断言）；v2 207/6、hipporag 279     ✅
变异 M21            退回 metadata.file_id → 2 failed；**旧断言对它是绿的**           ✅
```

**M21 那句最关键**：「旧断言对它是绿的」—— 这解释了缺失的断言为何无法发现该 bug，比「已修复」更有信息量。

### C2 放行：全部影子目录、仓外隔离

TL 追加了一个原 PLAN 没有的隔离层：**不只图要影子，`artifact_store` 与 `kb_state` 也要影子**，否则 C3 会把数据写进真实 store。

```
LLMKE_V2_GRAPH_ROOT   = /home/szf/data/dev/llmke-shadow/graph-root
LLMKE_ARTIFACT_STORE  = /home/szf/data/dev/llmke-shadow/artifact-store
LLMKE_KB_STATE        = /home/szf/data/dev/llmke-shadow/kb-state
LLMKE_ES_BASE_URL     = http://127.0.0.1:19527
LLMKE_MILVUS_BASE_URL = http://127.0.0.1:19526
LLMKE_V2_GRAPH_API    = http://127.0.0.1:18094
（禁止 LLMKE_ALLOW_DEFAULT_WRITE_TARGET=1）
```

放仓外的理由：不污染工作区、不产生 git 噪音、**C 段结束后整目录删除即完全回滚**。

### C2 四步与判据

| 步 | 内容 | 判据 |
|---|---|---|
| 1 | `--check`（只读预检） | 必须 `exit 0`；不过不许跳到步 2 |
| 2 | 起服务 | — |
| 3 | 三重验证 | ① `/openapi.json` 含 `/kb/ingest`；② `/health` 的 `write_targets.configured=true` 且 `status="ok"`（**`degraded` 则停**）；③ `/proc/<18096 pid>/environ` 的 `GRAPH_ROOT` 必须是影子路径 |
| 4 | 红线 | 18094 pid 未变、`kb_9=44`、线上图 md5 `e2d0f754…` 未变、`v2cand_*` 仍 0 条 |

**三重验证的第 3 项是「env 真的生效」** —— 只验 `/health` 不够，因为 `/health` 只报告「配了」，不报告「18094 实际用了哪个 root」。真正的证据在 C3 的响应回显。

## 三十八、C2 通过（18096 首次启动）+ 放行 C3a（17:1x）

### TL 独立核实（非转述成员）

```
18096  LISTEN 127.0.0.1:18096 pid=1332063
/health status=ok / write_targets.configured=True / allow_default=False
/proc/1332063/environ
  LLMKE_V2_GRAPH_ROOT=/home/szf/data/dev/llmke-shadow/graph-root
  LLMKE_ARTIFACT_STORE=.../llmke-shadow/artifact-store
  LLMKE_KB_STATE=.../llmke-shadow/kb-state/kb_state.json
  无 LLMKE_ALLOW_DEFAULT_WRITE_TARGET
18094 pid 3189651/3202203 未变 | kb_9=44 | v2cand_kb_9=0 | 线上图 md5 e2d0f754… 未变
llmke-shadow 下只有 artifact-store / kb-state；graph-root 未创建（首次建图才生成）
```

**三重验证第 3 项（读 `/proc`）是本次关键**：证明「env 真进了进程」，而非「以为设了」。

### 成员修的第二个「照抄就错」陷阱

B 段模板里 `LLMKE_DOC2MD_CONFIG` / `LLMKE_DOC2MD_LOCK` 指向**不存在的路径**（按 R12 运行仓猜的）。与「`# ALLOW=1` 示例值」同类：

**模板里的东西会被当成事实照抄，且失败原因看起来像「环境没装好」而不是「模板写错了」** —— 后者更糟：排障的人会去装环境，而不是改模板。已改为实测可用路径并注明原误写。

### C3a 放行（FULL_REBUILD 建首个影子快照）

**Step 0 必做**：先记线上图 `current.json` 的 md5 + mtime 作为基线。

**请求**：`operation="FULL_REBUILD"` + `fallback_reason`；**不带 `graph_root` 字段**（生产路径不读它，带了会造成「隔离靠它」的错觉）。

**六条判据（缺一不可）**：

| # | 判据 | 性质 |
|---|---|---|
| 1 | HTTP 200 / `status=OK` / `state_committed=true` | 基本 |
| 2 | `index_write.applied=true` + `deletes` 含 4 target | 写入完整 |
| 3 | `v2cand_kb_9` 的 `_count > 0` | 影子真写 |
| **4** | **`graph.result` 回显的 `root` == `llmke-shadow/graph-root/kb_9`** | **隔离证据**，若回显 `llmke-r12/...` 立即停 |
| **5** | **线上图 md5 + mtime 与 Step 0 逐位相同** | **事故判据**，不过则停止全部操作 |
| 6 | 线上 `kb_9=44` / `table_chunks_kb_9=2` 未变 | 线上零写入 |

第 4 条是「18094 真的用了影子 root」的唯一证据（`/health` 只报告「配了」，不报告「实际用了哪个」）。第 5 条不过即事故，不许自行「修回来」。

## 三十九、C3a 受阻：19527 的 `int()` 强转与自身 mapping 矛盾（17:2x~17:5x）

### 失败现象

C3a 返回 HTTP 502 `INDEX_WRITE_FAILED: es: insert HTTPError: HTTP Error 500`。**成员按规则停在原地，未绕过、未自行改代码、未重试。**

隔离完好：影子 `kb-state` 空、影子 `graph-root` 不存在、`v2cand_*` 各 0、线上 `kb_9=44`、线上图 md5/mtime 未变、18094 pid 未变。

### 根因（TL 独立核实）

```
19527 controller/es.py:252-255
    if f in ('order_num', "status"):
        actions_dict['_source'][sf][f] = int(v)          # int('') → ValueError → 500

ES mapping  order_num / status → 均为 {"type":"text","fields":{"keyword":...}}
Milvus      order_num → VARCHAR
线上 kb_9   order_num='' / status 键不存在（0 个 doc 带 status）
```

**两侧 schema 都声明是字符串，服务端却 `int()`** —— 不是「线上数据旧」，是**强转与自己的 mapping 矛盾**。

### 一条更大的事实

线上 46 个 doc 的 `order_num` 全是 `''` → **任何经当前 19527 的重建都会 500**，包括 P5 重建线上索引。这是**既有系统缺陷**，非本链独有。

### 方案裁定的三次演进（TL 两次被成员纠正）

| 轮次 | TL 判断 | 成员反驳 | 结果 |
|---|---|---|---|
| 1 | 「整段删掉 `int()` 分支」 | `retrieval_service.py:171` 有 `du.metadata["status"] == 1`（int 比较），删了 FAQ 会静默失效 | **TL 撤回**，改「加空值保护」 |
| 2 | 「`int(v)` 存在是为让 FAQ 存成 int」 | 本仓 4 个 mapping **无 FAQ 专用**；`status` 三处全是 `text`；**ES 对 text 字段写 int 会转字符串** → `int(v)` 无法实现该意图 | **理由推翻、结论保留**，理由改为「最小必要改动，只消除崩溃，不改既有写入行为」 |
| 3 | 空值保护写 `int(v) if str(v).strip() else v` | **`v=None` → `str(None)='None'` 为真 → `int(None)` TypeError**（TL 实测复现） | **TL 采纳成员的写法** |

### 最终方案（第 4 版，采纳成员的 `try/except` 写法）

```python
def _to_int_or_raw(v):
    """可转 int 的转 int，其余原样。校验与转换用同一个动作（int 本身）。"""
    if isinstance(v, bool):
        return v                      # True/False 不当整数
    if isinstance(v, (int, str)):
        try:
            return int(v)
        except ValueError:
            return v
    return v
```

覆盖：`''`→`''`、`'1'`→`1`、`'--1'`→`'--1'`、`'+1'`→`1`、`'1_000'`→`1000`、`'1.5'`→`'1.5'`、`None`→`None`、`1.5`→`1.5`、`True`→`True`。

**不删整段的理由**：FAQ 索引可能由本仓之外创建（另一套 mapping），无法只读确认。空值保护对两种假设都安全。
**若 Owner 问「为什么加保护而不改类型」**：改 mapping 会动检索契约，风险远大于收益。

### 四次演进：TL 的四个版本接连被打回

| # | TL 版本 | 成员打回的证据 |
|---|---|---|
| 1 | 整段删 `int()` | `retrieval_service.py:171` 有 `status == 1`（int 比较），删了 FAQ 静默失效 |
| 2 | 理由「`int()` 是为让 FAQ 存 int」 | 本仓 4 个 mapping 无 FAQ；`status` 三处全是 `text`；**ES 对 text 写 int 会转字符串** → 该意图无法实现 |
| 3 | `int(v) if str(v).strip() else v` | **`v=None` → `str(None)='None'` → `int(None)` TypeError** |
| 4 | `lstrip('-').isdigit()` 版 | **`'--1'` 崩**；且 `'+1'`/`'1_000'` 该转不转 → **实测三处不一致** |

TL 第 4 版实测结果（`int()` 本身对照）：

```
'--1'   → ValueError 崩        int('--1')   → ValueError
'+1'    → '+1'（不转）          int('+1')    → 1        ← 不一致
'1_000' → '1_000'（不转）       int('1_000') → 1000     ← 不一致
```

### 跨 loop 教训：校验与转换必须同源

写 `if looks_like_int(s): int(s)` 等于**维护两份规则并假设它们一致**，必然分叉。`'--1'` 就是分叉的直接后果：`lstrip('-')` 说「是数字」，`int()` 说「不是」。

**修正方式是让校验和转换是同一个动作**（`try/except int()`），不是补 `count('-') <= 1` 之类的单点补丁。

**这条与之前几个缺陷同族**，都是「看起来在验证，实际验证的不是那个东西」：

| 缺陷 | 假在哪 |
|---|---|
| `int(payload.get("fencing") or 0)` | 把 `None` 当 0，然后 `cur > 0` 恒真 |
| `pytest.raises(Exception)` | 骨架的 `NotImplementedError` 也算通过 |
| 7 个 Java 用例写着但没执行 | 文件存在 ≠ 测试跑过 |
| `lstrip('-').isdigit()` + `int()` | 校验规则与转换规则分叉 |

### 可操作的判据（成员提炼，TL 采纳为本切片的工作准则）

> **凡是「判断 + 转换」成对出现的地方，都该问一句「这两个动作用的是同一套规则吗」。**

补充一条关于**为什么这套复核能生效**的观察（成员提出，TL 认同）：

> 这四轮打回不是因为「谁更细心」，而是**每次都把代码/表达式写成了具体实现**。若四轮都是「加个空值保护吧」这种抽象描述，`None` / `'--1'` / `'+1'` 一个都不会浮出来。

**即：具体实现 → 逐值反推 → 反例浮现。** 抽象描述里没有反例，只有看起来合理的意图。这条比「要细心」可操作得多，已作为本切片后续评审方式固定下来：**TL 给方案必须给到可执行代码，成员必须逐值跑并回报真值表。**

### 待 Owner 授权

改 `es.py:252-255` 需 **① 允许改 19527 ② 允许低峰重启**。

**重启影响面**：19527 是 ES 代理，同时承载检索查询 —— 重启窗口内全文检索会短暂失败，Java 侧若无重试即用户可见。

### 成员发现的两个「照抄就错」陷阱（本轮共性）

1. B 段模板里 `LLMKE_DOC2MD_CONFIG` / `LOCK` 指向**不存在路径**（按运行仓猜的）—— 与「`# ALLOW=1` 示例值」同类：**模板会被当事实照抄，且失败原因看起来像「环境没装好」而非「模板写错」**；
2. 线上数据 `order_num=''` 过不了当前 19527 —— 说明「线上能跑」不代表「能被当前代码重新写入」。

## 四十、Owner 授权改 19527 + 重启；TL 查出「改错仓」（17:4x）

### Owner 授权

① 允许改 `es.py`；② 允许低峰重启 19527（接受窗口内全文检索短暂失败）。

### ⚠️ TL 查出决定性事实：**19527 跑的是 `llmke-r12` 仓**

```
19527  pid=23140  cwd=/home/szf/data/dev/llmke-r12/services/.../index_fulltext_service_pactera
       cmd=.../llmke-r12/platform/r12/venvs/alg/bin/python -u fulltext_es_api_start.py
       启动 2026-11-06 17:46:19（47.7h）
18094  cwd=/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service      ← v2
18096  cwd=/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service      ← v2
```

两个仓**物理独立**（非软链），两份 `controller/es.py` md5 当前相同（`2e33981e…`）但**独立副本**。

**若只改 `llmke-v2` 的 `es.py`，重启 19527 后行为完全不变 → C3a 仍 500 → 会误判「改法无效」而去查别的原因。** 这是差点发生的重大误判，代价是至少一轮返工 + 一次无谓重启。

**边界澄清**：`llmke-r12` 里 `api.py` / `rebuild.py` / `kb_delta.py` **都不存在** → 它只同步了 `index_fulltext_service` 部分。所以 **L9/L10/L13 改 `llmke-v2` 是正确的**（18094/18096 都从 v2 加载），CHECKPOINT 此前「重启前不生效」的结论无需修正。

**唯一例外是 19527** —— 它从 `llmke-r12` 加载。

### 执行方案（已下发给成员）

| 步 | 内容 |
|---|---|
| 1 | 改 **两处** `controller/es.py`（`llmke-r12` 为主 + `llmke-v2` 同步），内容完全相同 |
| 2 | 备份 `<llmke-r12>/controller/es.py.bak-p4l13c`，**起不来即恢复** |
| 3 | 记基线（pid/启动时间 + 四个索引 count）→ `kill` → 同命令 `setsid nohup` 重启 |
| 4 | 四个健康信号：`/openapi.json` 含目标路由、**新 pid ≠ 23140**、日志无 traceback 且有 `init config`、**四个索引 count 不变** |
| 5 | 先报「改完+重启完+四项健康」，TL 确认后才发 C3a |

**第 4 项（数据不变）**是「重启没搞坏数据」的证明；**新 pid ≠ 旧 pid** 是「真的重启了」的证明 —— 两条都不能省。

**启动方式已确认**：`fulltext_es_api_start.py` 的 `__main__` 走 `uvicorn.run(es_app, host, port)`，**不是** `start.sh` 的 gunicorn 路径。

## 四十一、19527 修复+重启完成（17:5x）；放行 C3a；另立安全项

### TL 独立核实

```
llmke-r12 es.py  72254b0081600d8f676b7258501d452e
llmke-v2  es.py  72254b0081600d8f676b7258501d452e          ← 逐位相同
备份            2e33981e…（= 改前），.bak-p4l13c 已留
19527           pid 1762713，启动 Sun Nov 8 17:30:30       ← ≠ 23140，真重启
索引 count      kb_9=44 / kb_1004=4520 / db1=41 / table_chunks=2  ← 逐项不变
下游            18094 3189651/3202203、18096 1332063 均未变
服务中断        约 50 秒（17:29:40 → 17:30:30）
```

### TL 承认的判断失误：给的启动命令起不来

TL 依据 `/proc/<pid>/cmdline` 给出 `setsid nohup python -u fulltext_es_api_start.py`，**起不来**（nacos 报 `server address & endpoint must not both none`）。

原因：**nacos 等 env 由 `algctl.sh` 注入，cmdline 里看不到**。正确路径是 `bash platform/r12/run/algctl.sh restart index_fulltext_service`（还会清理同入口孤儿进程）。

**与本节拍反复出现的缺陷同族**：

| 现象 | 检查的载体 ≠ 真实约束 |
|---|---|
| 「看起来是裸启动」 | cmdline 里没有 env |
| `'--1'` / `'+1'` | 字符外形不等于 `int()` 规则 |
| `int(x or 0)` | `None` 被当成 0 |

**教训：给可执行命令前，先确认它的完整依赖（env / 前置服务），不只是命令本身。**

### 成员自查发现：CRLF 归一导致 572 行全文件重写

第一版补丁把 CRLF 归一成 LF → `diff` 变成 572 行全文件重写，**最小改动变得不可审**。已回滚重做、按字节替换保留原换行风格，最终 **42 行**（helper 24 行 + 改 1 行调用）。

TL 认可：这个如果没自查，复核时只能看到「整文件都变了」，无法确认改动范围。**教训：改运行仓文件先确认换行风格。**

### 放行 C3a + 一条排查线索

同一条请求、同一 `doc2md_dir`、不带 `graph_root`；六条判据照旧。

**若仍 500 且错误仍是 `int('')`** → 先查 `controller/__pycache__/es.*.pyc` 的 mtime 是否早于 `es.py`（17:29:25），是则删 pyc 再重启 —— **不要在验证这条之前改代码**。若错误类型变了，说明新代码已生效。

## ⚠️ 独立安全项：nacos 全量配置（含明文口令）被打进 INFO 日志

**成员在重启日志中发现**：`index_fulltext_service` 启动时把 nacos 全量配置（**含明文 Redis 口令**）打进 INFO 日志。

- **性质**：**既有问题，非本 loop 引入**；严重性**高于本切片任何技术细节**；
- **已做处置**：成员在 evidence 中脱敏（`***REDACTED***`），并核对 0 处明文；
- **TL 动作**：记为本切片**独立安全项**（不属 P4 范围），在 Owner 汇报中单列，建议另立任务；
- **后续规则**：凡贴此类日志，**先脱敏再进 evidence**。

## 四十二、19527 修复生效；C3a 撞到第三个「计划 vs 服务端」缺陷（18:1x）

### 19527 修复确认生效（按对的方向修好的）

```
ES insert      不再 500（请求推进到 Milvus 侧）
影子 v2cand_kb_9  1 条
落库 order_num   ''        ← 与线上 46 个 doc **同形态**
4 个 delete     全部执行（2 ES + 2 Milvus）
Milvus delete   未报错 → A2 改的 col_name="file_id" 在真实 Milvus 上跑通
A3 补偿         needs=True, completed_sides=['es'] —— 首次在真故障下触发且记录正确
```

**`order_num=''` 原样落库是最有说服力的一条**：若当时采纳 A/B 方案填 `str(seq)`，影子会是 `'0'`，与线上形态分叉 —— P5/P6 的差异会从这里开始且极难追查。

### 新阻塞：`db_name: kb` 被当成 Milvus database

```
index_writer.py:271   "db_name": kb          ← L6 缺陷
19526 真实 database    ["default","rag_knowledge_base","graph_base"]   无 kb_9
19526 报错            database not found[database=kb_9] → 进自动建集合 → 无连接别名 → 500
19526 默认处理        db_name = db_name or server_config["milvus_database"]   (:262/:304/:364)
```

**不是 19526 的缺陷**：`db_name` 正确时存在性检查返回 True，根本不进建集合分支。`del_doc_by_col` 不传 `db_name` 故一直正常。

**Q10 裁定 = 方案 A**：删掉 `"db_name": kb`，走 19526 默认。理由：Milvus database 是部署级配置，`kb` 是业务维度，硬编码成等号是语义错误；且「不传」是该系统既有约定（`del_doc_by_col` 亦然）。

**追加执行细节**：`index_writer.py` 由 **18096** 加载 → **改完要重启 18096**（不是 19527），否则又是「改了不生效」。

### ⚠️ 跨阶段方法论：计划级验证的盲区（第 3 个同类缺陷）

| # | 缺陷 | 性质 |
|---|---|---|
| 1 | `delete_scope` 从未有生产调用点 | 计划从不执行 |
| 2 | `order_num=''` 被 19527 `int()` 打崩 | 计划值服务端不接受 |
| 3 | `db_name: kb` → Milvus 找不到 database | 计划值语义错 |

**共同根因：L6/L8 的验证全是「计划结构级」，`apply` 生产零调用 —— 计划里的错值从没真发出去过。**

**沉淀为规则**：凡「产计划」的模块，验收必须包含**至少一次「真发出去」的回合**。否则所有计划级断言都在保护一个未被检验的假设 —— 这与 `int(x or 0)`、`lstrip('-').isdigit()`、7 个未执行的用例同族，都是「验证的载体 ≠ 真实约束」。

### 中间态（安全）

影子 `v2cand_kb_9` 1 条、Milvus 0 条、影子 `kb-state` 空、`graph-root` 未创建、线上零变化。重放先删后写不累积 —— 但要求 C3a 重发后确认 count 仍是 **1 而非 2**。

### 附带记录

19526 有**两个** `vector_milvus_api_start.py` 进程（`19144` 监听 / `19860` 不监听）。`ConnectionNotExistException` 可能与连接别名按进程注册有关，但 **`db_name` 错是第一因**；修好后若仍出现再单独查，不合并处理。

## 四十三、A-fix2 完成：`db_name` 已删；发现第 4 类缺陷「测试把 bug 钉成契约」（18:2x）

### 修复核实

```
index_writer.py    db_name 已删，改为注释带依据（:271-273），md5 d27d3884a489dabd1ffa897373215524
18096              pid 1795316（≠ 1332063，已重启）
回归               v2 189 passed / 3 skipped；hipporag 240 passed
变异 M13           加回 "db_name": kb → 1 failed；restore 后 md5 复原
影子 v2cand_kb_9   1 条（未清）｜线上 kb_9=44 未变
```

**「跑的是新代码」的强证据**（成员做法，TL 采纳为规范）：pyc 字节码递归扫描字符串常量 `"db_name"` → **无**。比 mtime 序更强：mtime 只证明「文件比进程新」，字节码扫描证明「进程加载的字节码里确实没有那个字符串」。

**重启方式规范**（由 17:3x TL 判断失误倒逼）：**整份复用 `/proc/<旧pid>/environ` 的 115 个变量**，再逐项核对关键 6 项，不重拼 env。以后重启任何服务按此执行。

### ⚠️ 第 4 类缺陷：测试把 bug 钉成了契约

`tests/test_index_writer.py` 原本：

```python
MV_KEYS = {"db_name", ...}
assert body["db_name"] == "kb_9"        # 把错值钉成契约
```

**这个断言越严，错得越稳** —— L6 的计划级验证不但没发现 `db_name` 错，还把它锁成了必须保留的字段。

**本次改动经 TL 核实为「修正」而非「放宽」**：
- 断言方向相反（`== "kb_9"` → `not in body`），属**收紧**；
- 注释给出外部依据（真实环境报错 + `milvus_kb_service.py:262/:304/:364`），非「改主意」。

**CHECKPOINT 明确记账：L6 的验收标准本身是错的，本次修正的是验收标准，不是绕过它。** 否则 P5/P6 看到该测试变更会误认为动了断言。

### 方法论升级：测试的参照系必须是外部真值

| 缺陷 | 参照系错在哪 |
|---|---|
| A2 的 Milvus 侧只断言「我们发了什么」 | 参照系是**自己的实现** |
| `test_index_writer` 断言 `db_name=="kb_9"` | 参照系是**自己的实现** |
| `delete_scope` 无执行点 | 参照系是**计划**而非执行结果 |

**规则**：测试期望值只能来自**外部真值** —— 服务端 schema（`describe`）、mapping、契约文档、真实环境响应。A2 给 ES 侧做的（从 `init_fulltext_body` 源码取真值）是正确参照系，Milvus 侧当时缺的正是这个。

**这也解释了为什么前三个缺陷「真发一次」能抓、这一个不能**：前三个错在实现，这一个错在**验收标准**本身；错的标准会让正确的实现显出「不符」，也会让错误的实现显出「符合」。

## 四十四、B 方案撤回；18094 重启 runbook 已就绪（18:4x~18:5x）

### 第 5 个缺陷：请求级 `graph_root` / `graph_api` 被静默忽略

| 环节 | 行为 |
|---|---|
| 契约 §1.1 | 请求体**含**这两个字段 |
| 模型 `kb_ingest_service.py:164-165` | **接受** |
| `to_service_request()` | `model_dump()` → 进了 payload |
| `create_app:307` | `service = _build_service()` **不带参数**，只用 env |
| `_delta_runner` | delta 闭包**建 app 时就绑死 env** |
| `run(payload)` | **不读**这两个键 |

**接受、回显、但不生效** —— 与 `order_num`、`db_name` 同一族。

**TL 自己的判断也错了**：C3a 时 TL 要求「不带 `graph_root` 字段，因为生产路径不读它」，以为「不带你就能控落点」。实际两边都是空操作，真正起作用的只有 18096 的 env。**该要求已作废。**

**对前三次 C3a 结论无影响**：隔离靠 env，而 `V2_GRAPH_ROOT=llmke-shadow/graph-root` 在 C2 已读 `/proc/environ` 验证过。

**处置：登记不现在修**（不影响 C 段；修它要动 L12 已验收文件并再重启 18096）。修复方向倾向**删掉这两个字段**而非实现覆盖 —— 多库隔离应靠 env / 独立实例。删字段需同步改契约 §1.1（设计包），需 Owner 授权，单列。

### B 方案（起 18098）撤回

```
18096: _delta_runner 闭包 env 的 graph_root → 每次 post_graph_delta 都带 root=<影子>
18094: _kb_root(kb, root): base = root or env LLMKE_V2_ROOT or DEFAULT_ROOT   ← 请求 root 优先
```

**重启 18094 后 delta 会建到影子 root，不碰生产图。** B 是同一件事换进程做，还要多改一次 18096 env 再重启 —— 两次重启换一次，无收益。**撤回。**

### 18094 的真实结构（TL 之前误判为「双 worker」）

```
systemd --user(1628) → bash r12-graph-v2-start.sh(3189649) → python uvicorn(3189651, 49线程)
                                                                └─ fork 子进程(3202203, 2线程)
ss: LISTEN 18094 users:((pid=3202203,fd=12),(pid=3189651,fd=12))     ← 共用 fd
```

**脚本作者 11-06 已踩过并写进注释**（`r12-graph-v2-start.sh:32-34`）：

> 只判端口不够：uvicorn 主进程被 kill 后，残留子进程仍占着 LISTEN 却已不能处理请求（实测端口在、`/v2/status` 返回空）。用 `openapi.json` 做存活探针。

**因此重启判据必须是「两个 pid 都不在」，不是「端口没有」。**

### runbook 事实核实（TL 逐条）

```
ss 共用 fd=12 ✅ ｜ ppid 关系 ✅ ｜ :55 是 > 覆盖（非追加）✅
HEAD 的 api.py grep "v2/graph/delta" → 0 ✅ 回滚材料成立
diff HEAD: 186+/37-
```

### TL 追加的 5 条执行细节

1. **kill 先子后主**（`3202203` 是 `3189651` fork 的；先杀主会让子变孤儿仍占 fd），并**轮询 30 秒**确认两个 `/proc` 都不存在；
2. **日志备份不放 `$LOGDIR`**（脚本 `>` 会清该目录目标文件），放 `.runtime-bak/` 并记绝对路径；
3. **步骤② 补「只读基线样本」**：记 `/v2/graph/query` 的**实际响应**，不只记 200；
4. **回滚脚本授权前写好并 `bash -n`**；触发条件写死「五条验收任一不过 → 立即回滚，不许试图修」；
5. **显式断言 19531 pid == 435286 未变**（脚本会走「已运行跳过」）。

另确认：**18094 重启后 18096 不需重启**（每次请求新建 HTTP 连接）；若 C3a 出现连接类错误，先查此假设。

## 四十五、Owner 授权 A：重启 18094（18:5x）

### 授权范围（严格限定）

| 项 | 授权 |
|---|---|
| 执行 `l13c-18094-restart.sh`，让 18094 加载 L9/L10/L11 新代码 | ✅ |
| 改任何代码（**含 nacos 明文口令安全项**） | ❌ **本次不做** |

**理由**：本次重启的唯一目的是「让已合入的代码生效」。叠加其他改动会让故障归因失效（分不清是重启引起还是改动引起）。安全项另立任务。

### 执行前材料（TL 已核实）

```
/tmp/l13c-18094-restart.sh  7891803b…  bash -n OK
/tmp/l13c-18094-rollback.sh eb4a88f3…  bash -n OK
/tmp/l13c-18094-compare.py  c9d0fe0f…  干跑 ALL PASS；变异基线 FAIL（判别力已验证）
基线 18094-baseline-174006.json（1366 字符，仅 hash + 计数，无正文）
```

**比对器的可信度依据**：成员先用它检查自己的采集逻辑（抓到 `seeds` 字段漂移、干跑 `expect_delta` 误判两个自身错误），再做变异验证（改 `hit_count=2`/`node_count=999` → FAIL）。**期望值来自外部真值，不是自己比自己** —— 与 L11 M6 同一思路。

### 五条验收（任一 FAIL → 立即回滚，不许现场修）

| # | 判据 |
|---|---|
| 1 | 新 pid ≠ `3189651`/`3202203`，`ss` 只有 18094 |
| 2 | `openapi` 200，paths **9 条**，新增只有 `/v2/graph/delta` |
| 3 | `POST /v2/graph/delta {}` → **400**（路由在），非 404 |
| 4 | `POST /v2/graph/query` 与基线**逐项一致**（`hit_count=3`、`executed_route=GRAPH`、`docs_sha256=a0f3144b…`、`node_count=114`、`edge_count=94`、`documents=46`、`fencing=1`、`built_at` 不变） |
| 5 | `kb_9=44`、`table_chunks=2`、生产图 md5 仍 `e2d0f754…`、19531 pid 仍 `435286` |

**第 4 条是「重启未改变只读行为」的核心判据** —— 200 不等于「返回一样」。

### 执行要点（runbook 已验证）

- **kill 先子后主**（`3202203` 是 `3189651` fork），轮询 30 秒确认两个 `/proc` 都不存在 **且** `ss` 无 18094；
- 日志备份移出 `$LOGDIR`（脚本 `:55` 是 `>` 覆盖）；
- 回滚 = kill（同序）→ `git archive HEAD .../graph_engine_adapter` 到 `/tmp`（不动工作区）→ 用生产 root 起回 18094。

### TL 复核承诺

成员报完后 TL **独立复跑**同一组检查（pid / openapi 9 条 / delta 400 / query 响应 / `kb_9` / 生产图 md5 / 19531 pid），与其报告逐项比对，不采信转述。

## 四十六、18094 重启成功（6 秒）；两条判据是 **TL 写错**（19:0x）

### 执行结果

```
新 pid  2060061（+ fork 子 2064245）；旧 3189651/3202203 已不存在
耗时    6 秒
前置    pid/生产图 md5/kb_9/19531 四项全对
kill    先子后主 → 两个 /proc 都不存在 → 端口释放 → PASS
启动    hipporag-18094 已监听可响应；legacy-shim-19531 已运行跳过
```

### 五条验收（TL 独立复跑，非转述）

| # | TL 实测 | 结论 |
|---|---|---|
| 1 | pid `2064245/2060061`，旧两个已不存在 | PASS |
| 2 | `openapi count=10`，含 `/v2/graph/delta` + `/v2/fence/revoke`，无删除 | **TL 判据写错** |
| 3 | `POST /v2/graph/delta {}` → **422**，`detail` 列 `body.kb`/`body.docs` 缺失 | **TL 判据写错** |
| 4 | `hit_count=3`/`route=GRAPH`；`doc_fingerprints` **逐位等于基线**；`docs_sha256=a0f3144b03766696`；`documents=46`/`fencing=1`/`built_at` 不变；`node=114`/`edge=94` | PASS |
| 5 | `kb_9=44`/`table_chunks=2`/生产图 md5 `e2d0f754…`/`19531 pid=435286` | PASS |

### TL 承认的错误

| 判据 | TL 原写 | 实际 | 错因 |
|---|---|---|---|
| 2 | 「9 条，只新增 delta」 | **10 条**，还新增 `/v2/fence/revoke` | 漏算 L13-A 段新增的 revoke 端点；基线是 11-07 采的，那时 A 段未做 |
| 3 | 「400」 | **422** | `DeltaRequest.kb`/`docs` 必填（`api.py:109-110`），FastAPI body 校验失败标准返回 422。**422 + detail 列出缺失字段恰恰证明路由存在并进了校验**，404 才是路由缺失 |

**讽刺之处**：TL 在 L11 要求成员「M1 与 `api.py` 路由逐字符比对、不许手抄」，却在 C 段**自己手抄了期望值**（「9 条」「400」）。

**规则升级**：**验收判据的期望值也必须来自外部真值**（实际路由数、模型实际必填字段），不能凭记忆写。

### TL 比对时的一次自我纠错

第一次复算 `doc_fingerprints` 用自编算法得 `195e1337…`，与基线不符 —— 差点误判数据变化。**改为取成员脚本里的同一算法**（`{"pk":…, "text":text[:40]}` + `sort_keys`）后，得 `bcc37002…/16446c9f…/16446c9f…` **逐位等于基线**。

**教训：比对时算法必须取同一份**，否则「算法差异」会被误读成「数据差异」。

### 成员未回滚的处置，TL 认可

> 「判据 4 逐项 SAME、判据 5 三项全对 → 不像系统异常，像期望值写错」

**「健康证据」与「判据不符」同时出现时，先怀疑判据** —— 何况它保留了两条独立证据（只读一致 + 数据不变）。且它的动作序列正确：**先跑完剩余只读判据取事实，再报 TL 裁定**，没有自行宣布「判据作废」继续走。

### 附带成果：契约 §3 的 `/v2/fence/revoke` 已真正可用

代码本就在 `api.py`（L13-A 补齐），只是进程未加载。重启后端点进入 openapi —— **从 C 段一开始挂着的「撤权端点缺失」高优缺口，现已解决**。

## 四十七、**C3a 通过（第 7 次）**；契约 §2.1 的 1:N 首次端到端验证（19:3x）

### TL 独立核实全过

```
18094 pid 2129777 + fork 2133657
影子 kb_state.json  version=1 / cursor=cursor-03737d30… / kb.kb_9={'290': status:ACTIVE}
影子 graph-root     current.json + snapshot-20261108181634-804622-g0
影子 sources.json   idx 数=1 → ['290']
生产图 md5          e2d0f754… **未变**
kb_9=44 / v2cand_kb_9=1 / 19531 pid=435286 未变
```

**判据 4（`graph.result.root == llmke-shadow/graph-root/kb_9`）是关键** —— 证明 delta 真建到影子；**生产图 md5 未变**是独立印证。

### A 的实际改动是 4 处，不是 TL 说的 2 处

| # | 位置 | 改动 |
|---|---|---|
| ① | `api.py:80` | `BuildDoc.file_ids: List[str] = Field(min_length=1)` |
| ② | `api.py:264-267` | `live = [... for d in docs for fid in d.file_ids]`（展开 N 行） |
| ③ | `api.py:492` | `community = global_report.write(snapshot, [fid for d in docs for fid in d.file_ids])` |
| ④ | `delta_build.py:217-236` | `_doc_file_ids` + 「一条 doc 有 N 个 file_ids 就产出 N 行」 |

**TL 完整性扫描确认无第 5 处**：`api.py:607/771/780` 的 `src.file_id` 是 `sources.json` 里的 source 对象，不是 `BuildDoc`。

**TL 认错**：裁定 A 时说「只需改 2 处」，只看了 `BuildDoc` 与 `_as_live`，**没扫 `_default_build` 的 live 与 `community`**。②③ 不改会 `AttributeError` / 社区报告少 file_id。

**这与 TL 本轮其他失误同族**：写判据「9 条」（漏 revoke）、`lstrip('-').isdigit()`（手写规则）、比对用自编算法（`195e1337` vs `a0f3144b`）—— **共同点是「只看了主要路径，没做完整性扫描」**。

### 契约 §2.1 三条语义首次真实验证（本轮最有价值的成果）

| 判据 | 实测 |
|---|---|
| 单文件 | `sources`: `chunk-bcbc1301… → ['290']`，1 个 source |
| **同文异源 2 文件** | `BUILT/DELTA`；`→ ['290','291']`，**2 个 source、idx 仍 1 个**（引擎合并成一块） |
| **删其一 + `revoked_file_ids`** | `BUILT/DELTA`；`→ ['290']`，**块保留、剩 1 个 source** |

**这三条此前从未被验证**，而它们是 `source_map_multiple_source` 标 VERIFIED 的全部依据。现在是真实 HTTP + 真实 `sources.json` 的证据。

**易误读点（成员提醒，TL 采纳）**：`documents=2` 是 **live 行数**（一条 doc 展开 2 行），不是块数；块数看 `sources.json` 的 `idx` 数。

### 测试与变异

```
新增 test_delta_1n_l13c.py（双环境，纯函数）：实现前 3 failed → 实现后 4 passed
新增 test_delta_1n_model_l13c.py（仅 hipporag）：5 passed（v2 整文件 skip 单列）
同步改 3 个已验收测试（只改请求构造，不改断言）：test_graph_delta_route_l9 / test_delta_build_l9 / test_graph_state_l10
回归 v2 194 passed/4 skipped、hipporag 262 passed
变异 M16（_as_live 只取首个）1 failed；M17（BuildDoc 改回单值）4 failed
```

### 待办

C3b（真正的 DELTA，`reused == 原块数`）、C4（幂等/撤权/删除，**删除须验 count 不看 200**）、C5（故障演练，改 18096 env 指向错端口，**需单独确认**）。

## 四十八、⚠️ 事故：C4-2 的 DELETE 把撤权写进了**生产** graph-root（19:5x）

### 事故本身

```
生产 snapshot-20261107212905-365431-g0/fence.json
  18:19:16 被写成 {"generation":1,"revoked":{"291":{"generation":1,"reason":"REVOKED"}}}
影子 snapshot fence.json 仍 {"generation":0,"revoked":{}}   ← 影子没被写
```

**根因（缺陷 10）**：

```
graph_client.post_fence_revoke   payload = {"kb","file_ids","reason"}     ← 无 root
FenceRevokeRequest               kb / file_ids / reason                   ← 无 root
graph_client.post_graph_delta    root: Optional[str] = None               ← **有 root**
```

**delta 带 root（隔离生效），revoke 不带 → 18094 用自身 env 的 `LLMKE_V2_ROOT`（生产）。只要经 18096 做 DELETE，撤权就写生产。**

### 影响面（TL 独立核实）

```
生产 current.json md5 e2d0f754… 未变，fencing=1 / documents=46
生产 files = ['290','329','330','331','332','333','334','343','999016','999019','999020']
          → **291 不在其中**，该撤权过滤效果为零
生产两个 snapshot 的 fence.json 均已还原为 {"generation":0,"revoked":{}}
影子两个 snapshot 的 fence.json 均为 {"generation":0,"revoked":{}}
```

**结论：无数据影响；生产目录曾被写入一次，已还原。** 成员处置（备份污染版本 → 还原 → 复测视图 0/0 → 停止 revoke 测试）全部正确。

### 责任：**L13-A 的设计缺陷，在 TL**

- L13-A 要求成员「补 `POST /v2/fence/revoke`」，**未要求 `root` 参数**；
- A5 验收写的是「端点存在、幂等、按 kb 隔离」，**没测「写到哪个 root」**；
- C 段 PLAN 写「所有 ingest 必须显式带 `graph_root`」，**但 revoke 是独立端点，该要求覆盖不到**。

**与 TL 本轮其他失误同族：隔离要求只覆盖了主路径，没覆盖所有写路径。**

### 修法：`root` **必填**，fail-closed（比成员建议更严）

| # | 改动 |
|---|---|
| ① | `api.py`: `FenceRevokeRequest.root: str = Field(min_length=1)`，缺失 → 400，detail 明写「禁止默认落到 env root」 |
| ② | `graph_client.post_fence_revoke` 加 `root` 参数并写入 payload（同 `post_graph_delta`） |
| ③ | `kb_ingest_service._fence_revoke(graph_api, graph_root)` 从 env 绑并转发 |
| ④ | 断言：不带 root → 400，**且 18094 的 `fence.json` 未被写** |

**为什么必填**：事故根源就是「默认落到 env 的生产 root」。做成可选，将来任何调用方漏传就会再写一次生产。**fail-closed 是唯一安全的做法。**

**A5 验收同步补充**：不只验「存在/幂等/按 kb 隔离」，还要验「写到指定 root、不指定的被拒」。

### 缺陷 9：`apply_result` 缺失 —— 数据其实已存在，只是没接出来

```98:101:graph_engine_adapter/engine_hipporag.py
return {"schema": SCHEMA, "deleted": …, "added": len(to_add),
        "reused": len(wanted) - len(to_add), "duplicates": …,
        "consistent": remaining == len(wanted)}
```

`delta_build.py:192` 已 `return engine.apply_delta(texts)`，`rebuild.py:154` 的 `build_result` 也带出。

**修法：不用改引擎、不用新造统计**，只需 18096 从 18094 响应里把 `build_result` 的 `reused`/`added`/`consistent` 映射到 `apply_result`。契约 §2.3 不变式 #2 依赖它（`consistent==true` 且 `remaining==expected==documents`）。

### C3b（真增量）结果成立

`effective_mode=DELTA`、`documents 1→2`、`sources idx 1→2`、`community_count 1→2`、`citation_check ok`、`fencing_used 4→5`。**真增量生效、旧块保留。** 但 C-1 要求的 `reused == 原块数` 具体数字待缺陷 9 修好后补证。

### C4-2（删除）索引侧全对

`ES 2→1`、`Milvus 2→1`、只剩 `290`（**两侧查真实 count，不看 200**）、`state_committed=True`、`diff.removed=['291']`。撤权侧即上述事故。

### C4-1 判据表述修正（成员提出，TL 采纳）

「重复同一请求 → `SKIPPED_FRESH`」**只在带 `content_hash`/`manifest_path` 时成立**；不带时按「可能已变」处理、宁可重摄取（L12 既有设计）。

**判据改为**：「带 `content_hash` 的重复请求 → `SKIPPED_FRESH`；不带的按 `CONTENT_CHANGED` 重摄取，如实记录、不视为幂等失败」。

### 执行顺序

1. **先修缺陷 10**（`root` 必填 fail-closed）+ 反例「不带 root → 400 且 fence 未写」→ 重启 18096
2. 再修缺陷 9（接线 `apply_result`），可与 1 合并为一次重启
3. C4-3（缩水重摄取，走 UPSERT 不触发 revoke）可继续
4. **缺陷 10 修好前，禁止任何 DELETE 测试**

## 四十九、缺陷 10 修复验证 + 缺陷 11 裁定（20:2x）

### 缺陷 10 修复（两道 fail-closed）

| 位置 | 改动 |
|---|---|
| `api.py` `FenceRevokeRequest` | 增 `root`；handler 强制非空 → **400** + 「revoke 必须显式指定 root（禁止默认落到本进程 env 的 root）」 |
| `api.py` `fence_revoke` | `_resolve_snapshot(kb, root=root)` |
| `graph_client.post_fence_revoke` | 增 `root`；空 → **`GRAPH_ROOT_MISSING` 且不发任何 HTTP**；payload 带 root |
| `kb_ingest_service._fence_revoke` | 从 env 绑 `LLMKE_V2_GRAPH_ROOT` 并转发 |

**验证**：真进程 `curl` 不带 root → `HTTP=400` + detail；客户端侧零 HTTP 调用；重做 C4-2 时**生产 fence md5 `857a69b4…` 逐字节未变**；变异 M18/M19 各 2 failed。

**TL 裁定：保留成员的 400（不用 `Field(min_length=1)` 的 422）**。理由：① 已工作已验，再改要再重启；② `root` 缺失语义是「拒绝猜测」（业务规则）而非「格式错」；③ 关键是不落到生产，400/422 都满足。

**记账**：此处用 400 而 `DeltaRequest.kb/docs` 用 422，是**业务规则 vs 格式校验**的区别，非不一致。

### ⚠️ 成员主动加的 `applied_to_memory`（TL 认可，属主动防护）

`fence` 是 18094 **进程级内存态**。成员加了一条：**非本进程 root 时不更新内存**（`applied_to_memory = realpath(root)==realpath(_root_dir())`），响应新增 `applied_to_memory` / `root`。

**若不修**：影子撤权会顺带让 18094 对**生产 kb_9** 的检索丢掉 290。**比写磁盘更隐蔽 —— 不落盘、重启即消失、运行期间真实影响检索，且无文件痕迹可事后排查。**

成员主动识别并修复，属本文档记录的第二次主动防护（第一次为「重启前抓 `/proc/environ`」）。

### 缺陷 11：删到空库时图不收敛

```
库里只剩 290 时 DELETE：
207/PARTIAL  state_committed=false  diff.removed=['290']
graph.error = GRAPH_BUILD_HTTP_422 {"status":"REJECTED","reason":"DOCS_EMPTY"}
```

平台发 `docs=[]` + `revoked_file_ids=["290"]`，18094 `DeltaRequest.docs` 必填 → 422。

**TL 核实的 `commit()` 副作用顺序**：

```
:546  revoke            ← 副作用 1（写 fence.json）
:550  prospective       ← 纯内存
:552  wanted            ← 纯内存
:556  _apply_writes     ← 副作用 2（删/写 ES+Milvus）
:566  _delta            ← 副作用 3
:580  _state_txn        ← 副作用 4
```

**问题**：`revoke` 在最前、`wanted` 的算出在它之后 → 图失败时**索引已删、状态未提交**，产生不一致。

**裁定：方案 (b) + 检测点前移**

```python
prospective = copy.deepcopy(self._load_state())
self._apply_plan(prospective, plan)
wanted = self._build_wanted_docs(prospective, plan.kb)      # 纯内存

if not wanted:
    raise KbDeltaRefused("ALL_REVOKED",
        "删到空库需人工介入（契约 §5），本次零副作用：未撤权、未删索引、状态未动")

if plan.removed: self._revoke(...)                          # 此后才有副作用
```

**检测必须在 `_revoke` 之前**，否则撤权已发、fence 已写，就不叫「零副作用」。

**不选 (a) 的理由**：`rebuild.py:132-133` / `:270-271` **两处都明确拒绝空库**（`"没有存活文件可重建（全部撤权），拒绝生成空快照"`），而那是**契约 §5 `ALL_REVOKED` 的设计意图**。增量 DELETE 不该承担「删空库」职责 —— 那是**下线库流程**。

**同时采纳 (c) 的一半**：**DELETE 路径也回 `index_write` 块**，如实说明索引状态（即使选 b 也该做）。

**验收（第 1 条是「零副作用」的证明，缺一不可）**：

1. 删最后一个 → `ALL_REVOKED` 422，**`v2cand_kb_9` count 不变**、影子 `fence.json` 未变、影子 `kb_state` version 不变；
2. 删非最后一个 → 正常 `BUILT`，count 递减、`index_write` 如实；
3. 反例：检测被绕过必须红。

## 五十、缺陷 11(b)/9/12 修复 + C4-3 完成（20:4x）

### TL 独立核实

```
生产 fence 视图   {"generation":0,"revoked":[],"count":0,"kb":"kb_9"}        ← 干净
生产 graph_view   status=ok / node=114 / edge=94                              ← 生产快照
生产 current.json md5 e2d0f754…                                              ← 未变
生产 fence.json   md5 857a69b4… / {"generation":0,"revoked":{}}               ← 未变
影子 v2cand_kb_9  4 条；state version=11；files=['290','291','292']           ← 影子独立
18094 pid 2227759 ｜ 18096 pid 2207749
```

### 缺陷 11(b)：删到空库 → `ALL_REVOKED` 422，零副作用

`wanted` 计算前移到所有副作用之前；`revoke` 挪到其后。实测：

| 判据 | 实测 |
|---|---|
| HTTP | **422** `ALL_REVOKED: …本次零副作用：未撤权、未改索引、状态未动` |
| 影子 ES count | **仍 1** |
| 影子 `kb_state` version | **仍 4** |
| 影子 `fence.json` | 两份都 `{"generation":0,"revoked":{}}` |
| 删非最后一个（291） | `200/OK`、`index_write.mode=DELETE`、`inserts=None`、4 个 delete、`BUILT/DELTA/documents=1` |

同时采纳 (c) 的一半：**DELETE 如实返回 `mode=DELETE / inserts=None`**（此前报「inserts OK」冒充插入）。变异 M20/M21 各 1 failed。

### 缺陷 9：`apply_result` 纯透传，不新造统计

`engine.apply_delta()` 早就算好、`rebuild.py:294` 也已放进 `out["apply_result"]`，**只是 `delta_build` 拼响应时漏传**。加一行：

```
apply_result = {"deleted":0,"added":1,"reused":2,"duplicates":0,
                "remaining":3,"expected":3,"consistent":true}
documents=3 / sources=3 / ES=3 / Milvus=3
```

**`reused=2`（= 原有块数）、`added=1`、`consistent=true`** —— **C3b 缺的 C-1 数字补齐**。变异 M22 1 failed。

仍未实现（登记 P6）：§2.2 的 `sources{written,entries}`（现为整数 3）、`fence{generation,revoked}`、`fallback_reason`。

### ⚠️ 缺陷 12（第 2 处隔离泄漏）：影子构建改写 18094 的 kb 内存槽

**现象**：修完缺陷 10 后，生产 `GET /v2/fence?kb=kb_9` 显示 `revoked=["291"]`，而生产 `fence.json` **是干净的**。

**根因**：`api.py` 的 `graph_build` / `graph_delta` **无条件**把 `slot["snapshot"]` / `slot["fence"]` 改成响应里的快照 —— 影子构建也照改。**缺陷 10 的 `applied_to_memory` 只守住了 revoke 端点，没守住 build/delta 处理器。**

**影响**：生产磁盘与检索结果**未受影响**（`fence.json`/`current.json` 未写、`graph_view` 114/94、`query` 正常）；被污染的是**本进程 `slot`**（fence 视图显示影子撤权、slot snapshot 指向影子）。**比磁盘污染更隐蔽 —— 无文件痕迹，只能靠重启清除。**

**TL 完整性扫描（全部写入点）**：

| 位置 | 守卫 |
|---|---|
| `:486-491` `graph_build` | `_is_own_root(base_root)` ✅ |
| `:532-539` `graph_delta` | `_is_own_root(req.root or _root_dir())` ✅ |
| `:721` revoke | `applied_to_memory`（realpath 比较）✅ |
| `engine_for_kb` | `_resolve_snapshot(kb)` **不带 root** → 只用 env root，天然安全 ✅ |

**结论：修复完整，无第 4 处遗漏。**

**TL 建议（非阻塞）**：`applied_to_memory = realpath(root)==realpath(_root_dir())` 与 `_is_own_root(root)` **语义等价但两份实现** —— 应统一调用 `_is_own_root`，避免将来改一处漏另一处。这与本轮反复出现的「同一判断两份规则」同源。

### C4-3：缩水重摄取，旧块不残留（两侧 count + 内容级）

`292` 2 段 → ES=3；改 1 段重摄取 → `CONTENT_CHANGED`、`projection.chunks=1`、4 个 delete、**ES=2**、292 命中 1 条、**旧段落 `match_phrase` 命中 0**、**Milvus 全量 2 行**（290/292 各 1）。

**不是只看 200，是两侧真实 count + 内容级核对。**

### 回归与终态

v2 `200 passed / 4 skipped`、hipporag `273 passed`；M20~M23 各 1 failed。

### C4 收口判断

C4-1（幂等，带 `content_hash`）、C4-2（删非最后 / 删到空库）、C4-3（缩水不残留）**三条全部通过**。**C4 完成。**

剩余：**C5 故障演练**（改 18096 的 `LLMKE_V2_GRAPH_API` 指向错端口 + 重启 18096），属运行态变更，**需 Owner 授权**。

## 五十一、`_is_own_root` 统一 + TL 的进程混淆纠正（21:0x）

### TL 承认的错误

TL 在上一轮写「建议与 C5 一起做，反正要重启 18096」—— **把两个进程混成一个**。

`applied_to_memory` 在 `graph_engine_adapter/api.py`，属 **18094**；C5 动的是 **18096 的 `LLMKE_V2_GRAPH_API`**。**不同进程，须分别重启。** 成员纠正成立。

**若按 TL 原话执行**：C5 只重启 18096，18094 仍是旧代码。本次改动逻辑等价不影响 C5 结论，但会养成「一次重启覆盖两处改动」的习惯 —— 将来遇到非等价改动时，会出现「C5 通过但 18094 跑的是旧代码」的假绿。

### 统一已落地（TL 核实）

```
api.py:721   applied_to_memory = _is_own_root(root)      ← 内联 realpath 已删
静态断言     assert "applied_to_memory = _is_own_root(root)" in src
             assert "os.path.realpath(root) == os.path.realpath(_root_dir())" not in src
          → 真读源码文本（Path(A.__file__).read_text()），非空转
变异 M24     改回内联 realpath → 静态用例 1 failed
```

**TL 指出的静态断言弱点（非阻塞）**：它匹配**精确字符串**。若重构成 `a=realpath(root); b=realpath(_root_dir()); applied_to_memory = a==b` 则抓不到。作为辅助防线可接受 —— 行为断言 `test_revoke_memory_flag_uses_same_rule` 仍在，两者配合。

### ⚠️ TL 查出的代码与运行态差异（必须如实记录）

```
api.py mtime        2026-11-08 18:30:33
18094 启动          2026-11-08 18:28:38   ← 早 1分55秒
18096 启动          2026-11-08 18:25:07
18096 env           LLMKE_V2_GRAPH_API=http://127.0.0.1:18094   ← 未动 ✅
```

**即：18:30:33 的 `_is_own_root` 统一未被运行中的 18094 加载。**

但**缺陷 12 的修复已生效**（活体证明：fence 0/0、view 114/94，且再跑影子 upsert 后仍干净）。差异仅限「等价重构未加载」，**不是「缺陷未修」**。

**如实口径**：运行态缺的是一处**逻辑等价**的重构，行为无差异；下次重启 18094 时自然加载。**不得表述为「代码与线上完全一致」。**

### 回归

v2 `200 passed / 4 skipped`、hipporag `280 passed`（revoke 用例 11 条全绿）。

指纹：`api.py ae321af2…`、`tests/test_fence_revoke_root_l13c.py ccd5ef1b…`、evidence 201 行 / `0a24aa04…`。

### 剩余

**仅 C5**（故障演练），需 Owner 授权。届时须**分两步**：①重启 18094 加载统一；②改 18096 env → 重启 18096 → 演练 → 改回 → 再重启。

## 五十二、C5 runbook 复核（21:1x，TL 追加一个未覆盖场景）

### 成员的时间差佐证（TL 采信）

用 **pyc 的 `co_names`** 区分「磁盘代码」与「内存字节码」：

```
磁盘 pyc（18:30:39 由测试导入生成）
  fence_revoke 的 co_names 含 _is_own_root、不含 realpath   ← 磁盘是新的
18094 进程 18:28:38 已 import 完                            ← 内存是旧字节码
```

**能证明缺陷 12 修复（18:28:38 那次重启加载）已生效**，差异只在等价重构。证据链成立。

### TL 核实的顺序变更：L13-A 把索引写入提到了 delta 之前

```
:562 revoke → :566 index_write=_apply_writes → :576 graph_result=_delta → :590 _state_txn
```

**与 L12 R2 的顺序（delta:402 → index_write:408 → txn:418）不同。**

**TL 裁定：接受，且这个顺序更好。** 理由：

| 顺序 | delta 失败时 | 索引失败时 |
|---|---|---|
| 索引→delta（现状） | 索引已写、图未建、状态未推 → 重放收敛 | **图未动**（delta 没跑），重放干净 |
| delta→索引（L12 顺序） | 索引未写 | **图已按新集合重建但 ES 是旧块** → 图与 ES 不一致，建图代价白费 |

**索引在前，失败时图未动，重放代价最小。** 成员的实现选择正确。

### `_apply_writes` 失败链路（TL 完整核实，无缺陷）

```
_apply_writes 抛 KbDeltaRefused("INDEX_WRITE_FAILED") + exc.payload={"index_write": {已完成一侧}}
→ commit() 不捕获（冒泡）
→ kb_ingest_service.py:362 except Exception
→ :369 payload = exc.payload  → 透传进响应 data ✅（契约 §5 要求「显式记录补偿，不得只 log」）
→ http_status_for → INDEX_WRITE_FAILED 在表 → 502 ✅
→ :368 response.status_code = 502（显式设码）
```

**TL 最初怀疑「异常冒泡未被结构化处理」，核实后不成立** —— 服务层统一捕获、查表、透传 payload，链路完整。且索引失败 502、delta 失败 207 **语义分级正确**（索引是核心写入，delta 是图属性可降级）。

### ⚠️ TL 追加：C5 runbook 缺「索引写失败」场景

当前 C5 只演练 **delta 失败**（改 `LLMKE_V2_GRAPH_API` 指向 19999）。但 `_apply_writes` 是 **「先删后写」**：

```
do_deletes("es") 成功 → ES 中该文件旧块全删
do_insert("es")  失败 → 新块没写
→ ES 中该文件**完全消失**（可见性中断，不是永久丢失）
→ 状态未推 → 重放 → diff 判 changed → 重新写 → 收敛 ✅
```

**这是比 delta 失败更危险的路径**（delta 失败时索引是完整的新数据），而 runbook **完全没覆盖**。

**要求 C5 追加一条（可离线 mock，不必真断 19527/19526）**：

1. 注入 insert 失败 → 断言 `502` + `INDEX_WRITE_FAILED` + **`data.index_write.compensation.completed_sides` 非空** + `state_committed` 不存在（异常路径不含该字段）；
2. **重放同一条请求（恢复正常写入）→ 收敛**：ES count 恢复、state 前进、图与 ES 一致；
3. evidence 写明「先删后写失败会造成该文件在 ES 短暂不可见，重放可恢复」。

### 其余认可

- runbook 分两步不合并 ✅（与 TL 上一轮纠正一致）
- 副作用 1（索引在 graph 前 → 演练后影子 ES 多新文件、state 没有）**属实且是设计的一部分**，写明后不算不一致；
- 副作用 2（撤权在索引前 → C5 只用 UPSERT）**正确且必要**；
- 判据 6 条可判定（`cursor` 逐字符不变、影子 `version` 不变、生产 md5 + count 不变）✅

## 五十三、C5 离线部分完成（21:2x）

### TL 独立核实

```
产品代码零改动   kb_delta.py cef297d6… ｜ kb_ingest_service.py 5a19cc16…（与上轮一致）
独立复跑         tests/test_kb_delta_l13.py -k 'c5_es_insert_failure or a4_delete' → 2 passed
运行态未动       18094 2227759 ｜ 18096 2207749 ｜ kb_9=44
```

### 两条用例的判别力（TL 逐条读断言）

**v2（真跑 `service.run()`，行为级）** —— `test_c5_es_insert_failure_after_deletes_file_becomes_invisible_then_replay`：

| 断言 | 意义 |
|---|---|
| `len(es_deletes) == 2` | 两个 es target **都真的删了** |
| `"del_doc_by_col" in url` | 删除真发出去 —— **这就是「短暂不可见」的成因** |
| `"insert_fulltext_documents" in url` | 插入尝试过（失败点） |
| **`rec.calls["delta"] == 0`** | **索引失败不得继续建图** = 「索引在前」的直接收益证明 |
| `version` 不变 | 状态未推 |
| **重放 → `OK` / `applied=True` / `version` 前进 / `FID` ACTIVE** | **可恢复**，不是只看「失败了」 |

**hipporag（服务层映射）** —— `test_index_write_failure_is_502_with_payload_and_no_state_committed`：

```
502 ✅ ｜ data.index_write.status=FAILED + compensation ✅ ｜ "state_committed" not in data ✅
```

**`state_committed` 不出现**这一条设计得好：异常路径**根本没有「提交/未提交」这个结论**，若出现 `false` 会让人误读成「尝试过提交且失败」，掩盖「压根没进事务」。

**TL 指出的局限（不要求改）**：hipporag 那条用 `FakeService(exc=exc)` 直接构造异常，是**测服务层映射**、不是测索引失败。分工合理（v2 验行为、hipporag 验映射），行为级已由 v2 那条覆盖。

### 变异

**M25**（insert 提到 delete 之前）→ 可见性用例 1 failed —— 锁死「先删后写」顺序；
**M26**（异常路径不透传 `payload`）→ HTTP 用例 1 failed —— 锁死契约 §5 的补偿透传。

### 写入顺序调整已记账

```
现在：revoke → index_write → delta → _state_txn
L12 ：revoke → delta → index_write → _state_txn
```

理由已写入 evidence：**索引在前，失败时图未动，重放代价最小**；L12 的顺序在索引失败时会「图已重建、ES 还是旧块」。

### 既有用例语义调整（同 L12 b2/b3）

`test_a4_delete_with_runner_commits_state` 原「删唯一文件」，按缺陷 11 新语义会红 → **只改种子**（补存活文件 + chunk），**断言一字未动**。

### 回归

v2 `219 passed / 4 skipped`、hipporag `300 passed`。

### ⛔ 唯一剩余：C5 主体

改 18096 `LLMKE_V2_GRAPH_API` → `127.0.0.1:19999` → 重启 → 演练（UPSERT）→ 改回 → 再重启。**需 Owner 授权**。

**P4-L13-C 除 C5 主体外全部完成。**

## 五十四、C5 主体预备核查（21:3x，成员交清单 + TL 追加一处隐患）

### TL 独立核实（四项全成立）

```
curl 18096/health
  graph_api = http://127.0.0.1:18094          ← 确实回显
  write_targets = {es:true, milvus:true, configured:true, allow_default:false}
  store_root = /home/szf/data/dev/llmke-shadow/artifact-store
19999 未监听 ✅
/tmp/make_artifact_blocks.py 存在（2800B，18:25）✅
```

**`graph_api` 绑定时机**（成员判断正确）：

```
:254  graph_api = graph_api or os.environ.get("LLMKE_V2_GRAPH_API", ...)   ← _build_service() 内
:261  delta=_delta_runner(graph_api, ...)                                  ← 闭包捕获
:262  revoke=_fence_revoke(graph_api, ...)                                 ← 闭包捕获
:338  "graph_api": os.environ.get("LLMKE_V2_GRAPH_API", ...)               ← /health 请求时**重新读**
```

**结论：改 env 不重启 = 完全无效**（进程 `os.environ` 是 fork 后的副本，shell 改 env 不影响）。

### ⚠️ TL 追加的隐患：`/health` 与实际使用是**两处读取**

```
_delta_runner 用的 graph_api  ← 启动时读 env，闭包固定
/health 报的 graph_api        ← 请求时重新读 os.environ
```

**当前两者一致**（进程内 env 不变），所以 C5 用 `/health` 核对是可靠的。

**但这是「同一判断两处读取」，与本轮反复出现的模式同源**：`lstrip('-').isdigit()` vs `int()`、`applied_to_memory` vs `_is_own_root`、我写判据「9 条」漏 revoke。

**风险场景**：若将来支持运行中改 `os.environ`（热更新、测试注入），`/health` 会显示新值、实际 `_delta_runner` 仍用旧值 → **`/health` 会骗人**，且恰好是在「核对 env 是否生效」这个最需要它诚实的场景。

**TL 裁定**：**C5 前不必改**（不影响本次演练），但**登记为 P6 收敛项**；修法是把实际绑定的 `graph_api` 存进 app state，`/health` 读它而非重读 env。

### 成员的 9 条坑：TL 逐条采信

| # | 条目 | TL 评价 |
|---|---|---|
| ① | 改 env 不重启 = 无效，判据须「新 pid + `/health.graph_api` 已变」 | **正确**，且 TL 已核实闭包机制 |
| ② | 改回后同样要重启，用「同一条请求恢复正常」收尾 | **正确**，只看端口通不算 |
| ③ | 整份复用 environ，只覆盖目标键，diff 其余 | **最关键的一条**：漏 `LLMKE_V2_GRAPH_ROOT` 会**写到生产**，漏 `LLMKE_DOC2MD_LOCK` 会让 `producer_inputs` 不完整 |
| ④ | 用新文件（293），别动 290/291/292 | **正确**：`_apply_writes` 先删后写，动已有文件会让它在失败窗口短暂消失 |
| ⑤ | 产物先本地校验，否则在投影阶段 400、测不到图路失败 | **正确**，这是「测错东西」的典型 |
| ⑥ | 失败后影子残留 293 的索引数据而 state 没有，须重放收敛 | **正确**，与 C5 离线结论一致 |
| ⑦ | 19999 若被监听，错误变 `GRAPH_BUILD_HTTP_*` 而非 `GRAPH_API_UNREACHABLE`，两者都 502 | **判断细致**：TL 已核实 19999 空闲，按 `GRAPH_API_UNREACHABLE` 断言；并加「`msg` 前缀匹配」兜底 |
| ⑧ | 演练期间不要并发请求 | **正确**，重启会打断在途请求 |
| ⑨ | `write_targets.configured` 前后都应 true，变了说明手滑改了别的 env | **好判据**，能抓「改错键」 |

### TL 追加一条：`/tmp` 脚本要固化

`/tmp/make_artifact_blocks.py` 在 **`/tmp`** —— 重启/清理即丢失，而它是 C5 生成产物的唯一工具。

**要求**：C5 执行前把脚本内容贴进 evidence（或移入仓库 `tests/tools/`），**不得只依赖 `/tmp` 存活**。否则 C5 可能因「工具没了」而做不成。

### 一条口径（成员建议，TL 采纳）

演练结论**分两句写，不混**：

- **图路失败**（C5 主体）：索引已是新数据、图缺 → `PARTIAL`；
- **索引失败**（C5 离线已验证）：图完全没动，但该文件短暂不可见 → 重放收敛。

**两种失败性质不同，C5 主体只覆盖第一种。**

### 现状（未动）

`18094 2227759`、`18096 2207749`（`/health.graph_api=http://127.0.0.1:18094`）、`19531 435286`、`kb_9=44`、生产图 md5 `e2d0f754…`。

## 五十五、C5 主体完成（22:2x）——TL 独立核实

### 演练结果（判据 ① 经裁定更正为 207）

```
POST /kb/ingest  {"kb":"kb_9","file_id":"293","operation":"UPSERT","doc2md_dir":"/tmp/c5-artifact293"}
产物先校验通过 content_uid=fa1577d2c496dcca

HTTP = 207 ｜ status = PARTIAL ｜ state_committed = False
cursor = cursor-4ae14056…331ef（与基线逐字相同）
index_write: APPLIED / deletes=4 / inserts={es:OK, milvus:OK}
graph.error = GRAPH_API_UNREACHABLE: http://127.0.0.1:19999/v2/graph/delta:
              URLError: <urlopen error [Errno 111] Connection refused>
```

### C5 的五条真实目的：全过

| 目的 | 实测 |
|---|---|
| 不把失败伪装成成功 | `status=PARTIAL`，**不是 `OK`** |
| 不推进 cursor | 逐字符相同 |
| 不提交状态 | `state_committed=false`、影子 version 仍 11 |
| 带出失败原因 | `Connection refused` 原文 |
| 生产零影响 | 四项全不变 |

### TL 对判据 ① 的自我更正

**判据 ① 写 502 是 TL 的错**，直接抄了 `ERROR_HTTP["GRAPH_API_UNREACHABLE"]=502`，没看实际路径：

```
kb_delta.py:578   except K.PipelineRefused → graph_error = "GRAPH_API_UNREACHABLE: ..."  → PARTIAL
kb_ingest.py:374  code = 200 if status in ("OK","SKIPPED_FRESH") else 207                → 207
```

**502 只在异常逃出 `commit()` 时生效**；delta 的异常被捕获了。

**且改成 502 反而更糟**：207 让 Java 回写 `RETRY`（保住重放机会），502 可能被回写成 `PARSE_FAIL`（丢重放）。**实现的分级是对的**：图路失败=软失败、索引失败=硬失败。

### 恢复与收敛（TL 核实）

```
18096：2 次重启  2207749 → 2765422（演练态 19999）→ 2773520（恢复 18094）
18094：0 次重启  pid 2227759 未变（ss 中 2774847 是其 fork 子进程，非重启）
19531：0 次      435286

/health.graph_api = http://127.0.0.1:18094 ✅ ｜ configured = True ✅

重放：HTTP 200 / OK / state_committed=True
      cursor-2cb8b470…（前进）
      graph: BUILT / DELTA / documents=5
      apply_result {"deleted":0,"added":1,"reused":3,"remaining":4,"expected":4,"consistent":true}

影子 v2cand_kb_9  5 → 5（**幂等，未变 6**）✅
影子 version      11 → 12 ✅
state files       {290,291,292,293} 全 ACTIVE ✅
生产四项          e2d0f754… / 857a69b4… / kb_9=44 / table=2 **全不变** ✅
```

### 一处数字口径（成员主动说明，TL 核实成立）

`apply_result.expected=4` 而 `documents=5`：

```
expected/remaining = 去重文本数（292 两段不同文本 + 290/291/293 各一段 = 4）
documents          = live 行数（含 292 两行 = 5）
```

**两个数都对，但是两种计数并列出现**，调用方易误读。**并入 P6 的 §2.2 收敛项**（与 `sources{written,entries}` 一起处理）。

### 新登记 P6：同一 code 两种 HTTP 语义

```
GRAPH_API_UNREACHABLE  经 commit() 捕获   → 207 PARTIAL
                       经 kb_pipeline:216 → 502
```

**不是死代码，是两条路径两种语义。** 调用方只看 `code` 无法判严重性，须看 `status`。本 loop 不改（改即动 L7 已验收语义）。

### T-D2MD-13 状态判定（TL）

**保持 `DOING`，不标 DONE。** 理由：

| 验收项 | 状态 |
|---|---|
| D-1（18096 启动脚本/watchdog） | 需核 L13-B 产物是否完整 |
| **D-3（停 18094 → GRAPH_UNREACHABLE + RETRY）** | **用「改错端口」等价模拟，未真停 18094** —— 语义达到，但形式不同，须如实标注 |
| D-4（非 200/207 回写 PARSE_FAIL） | **Java 未编译未单测 → 未验证** |

**C5 覆盖的是「图谱不可达时服务行为」，不等于 D-3/D-4 全部通过。**

## 五十六、D-1 门控补丁 + 双副本发现（22:5x）

### ⚠️ 成员发现的结构性问题：部署脚本有两份

```
Python 代码   只有源码仓一份（llmke-v2/services/rag-alg/index_data_service）
              18096 的 start.sh:23 明确 V2_SVC_DIR=.../llmke-v2/...  ← **有意**
              → 改代码 + 重启即生效，**不需要同步**

部署脚本/env  两份，按需人工同步
  up.sh            v2 d94f9246（有门控） vs r12 12cfa300（无）  **不同**
  r12-watchdog.sh  v2 1bb255d8（有门控） vs r12 ad09d0ce（无）  **不同**
  r12ctl.sh        v2 2617e96c == r12 2617e96c                  **相同**
```

**「不同 + 相同」并存说明是按需人工同步，不是全量镜像。**

**关键澄清**：双副本**只影响 `bin/` 与 `conf/`，不影响 Python 代码** —— L9~L13 的代码改动全部生效。若不澄清，会误判「所有改动都没生效」。

### L13-B 的部署侧产物：6 项全在源码侧

```
M  platform/r12/bin/up.sh
M  platform/r12/bin/r12-watchdog.sh
M  platform/r12/R12-ENV-CONTRACT.md
?? platform/r12/bin/r12-kb-ingest-start.sh
?? platform/r12/conf/kb-ingest.env
?? platform/r12/systemd/r12-kb-ingest.service
```

部署仓 `llmke-r12` 里**一个都没有**（其 `M r12-watchdog.sh` 是此前修 19527 的改动，与我们无关）。**同步必须 6 项一起**。

### 门控补丁（默认关闭，TL 核实通过）

```
up.sh            门控开 → == 6.5 知识库摄取（门控）== 走 r12-kb-ingest-start.sh（自检失败 exit 1）
                 门控开 → verify 四条 must（端口 / /health 200 / graph_api 内容 / configured 内容）
                 门控关 → [skip] 不计入 must（既有行为零改变：must 4 未通过，开/关同为 4）

watchdog         kb-ingest 条目仅 LLMKE_INGEST_ENABLED=1 时加入 TARGETS
                 新增 ingest_content_ok()；unhealthy_ports() 增 group 参数，kb-ingest 组额外校验内容
                 失败记 content:graph_api_or_configured
```

**内容探针的实证价值**：C5 演练时 18096 进程活着、端口在听、但指向 19999 —— **只看端口会判健康**。探针单测 4 例（`graph_api` 错 / `configured=false` / 正常 / 无监听）全过。

### 三处修正（TL 核实）

| # | 问题 | 处置 |
|---|---|---|
| ① | `kb-ingest.env` 注释自指矛盾（说「真实值放 A」，而它自己就在 A） | 改为「模板在源码仓、真实值在部署仓，**同步时不要覆盖部署仓那份**」（`85d8fbb9…`） |
| ② | `WorkingDirectory=llmke-v2` 看起来像笔误 | 加三行注释说明**有意为之**，并警告「同步时不要改成 llmke-r12，那边没这套代码」（`cec80101…`） |
| ③ | `EnvironmentFile=-` 的 `-` | **去掉**。成员实测脚本确实兜得住（`--check` 退出码 1），但那是「systemd 静默通过、脚本再报错」；去掉后失败点更靠前 |

### ⚠️ 当前 unit 处于「不可启动」状态（预期，须记录）

```
EnvironmentFile=/home/szf/data/dev/llmke-r12/platform/r12/conf/kb-ingest.env
部署仓该文件 = ❌ 不存在
→ 现在 systemctl start r12-kb-ingest 会失败
```

**这是 fail-fast 的预期结果**，不是缺陷。但必须写明：**unit 已就绪 ≠ 能启动**，启用前置包含「先同步 6 项」。

**安全性确认**：`r12-watchdog.timer` active，但跑的是**部署侧**（无 18096 条目）→ **不会尝试启动它、也不会重启 2773520**。

### P6 第 7 项：双副本无一致性校验

`up.sh verify` 能验服务健康，但**验不出「部署侧脚本与源码侧不一致」**。建议 `verify`/`doctor` 对比 `bin/` 下关键脚本 md5，不一致 **warn 不 fail**。

**理由**：这次是「改了源码侧忘了同步部署侧」，下次可能是「同步了 up.sh 漏了 watchdog」。**无校验必然再犯。**

### D-1 定稿表述

> **D-1 部分完成**：门控补丁**源码侧**落地并通过离线验收；门控**默认关闭**、18096 仍人工管理；**部署侧 6 项未同步**，运行环境**未生效**。
> 启用前置：①设 `LLMKE_INGEST_ENABLED=1` ②**先同步 6 项到部署仓** ③再启 systemd。

### 零变动

生产图 `e2d0f754…` 未变；`18096 2773520`（`graph_api=18094`、`configured=True`）、`18094 2227759`、`19531 435286` 均未动。

## 五十七、P5-L14 R-0 裁定（23:3x）—— 一个重要事实改变 P5 的性质

### TL 核实的两条关键事实

```
运行中的 jar  llmke-r12/.../rag-index-service/target/rag-index-service-0.0.1-SNAPSHOT.jar
              225 MB / 11-07 02:57
              RemoteV2IngestUtils.class 命中 **0**
              FileAppServiceImpl 无 v2Ingest 方法

源码侧        RemoteV2IngestUtils.java 只有 A（llmke-v2）有，实现正确：
              :133 classify(response.getStatusCode().value(), code)
              :146 解析 body 的 code
              :150/157 4xx→PARSE_FAIL / 连不上→RETRY
              → **与 L13 结论 200=OK / 207=RETRY / 4xx=PARSE_FAIL / 5xx=RETRY 完全一致**
```

### ⚠️ 结论：线上**根本没有 v2-ingest 功能**

**P5 不是「切换」，是「从零启用」。** 这是本项目第一次出现「源码有、线上连类都没有」——比 P4 的「改了没同步」更彻底。

**原因**：B 侧（`llmke-r12`）源码是 **10-29 的旧快照**（953 行 vs A 的 1076 行），jar 虽 11-07 构建，但**构建的是旧源码**。

**后果**：
- 改 A **不会自动上线**，必须「构建 + 部署 + 重启」三步；
- **P5 的工作量比 PLAN 预估大**：不是改调用，而是首次把功能送上线。

### TL 核实的第三点：`v2-ingest` 注释已过时

```yaml
# ② 该链路不写 ES/Milvus，且按 kb_state.json 全库重建图谱，与 19531 并发会互相覆盖；
# ③ 新上传文件的 ES/Milvus 由 12340 解析服务双写，图谱由 19531 以 ES 全库 chunk 重建。
v2-ingest:
  url: ""        ← 显式关闭
```

理由 ② 在 L13-A 接线 `index_writer.apply` 后**已不成立**（现在会写 ES/Milvus）；③ 也将在 P5-3 后失效。**运维若照旧理由继续关，P5 永远上不了线。**

### 「mvn 基线 Tests run 7」不成立（TL 采信）

```
mvn -o -pl rag-index-service test
  ERROR 找不到符号 getDoc2mdDir()（~/.m2 的 rag-common jar 是 10-31 旧版）
加 -am 后编译通过（185 main + 16 test），但 surefire 缺 org.apache.maven.surefire:surefire-junit3:2.12.4 → 离线无法执行测试

「7」= RemoteV2IngestClassifyTest **一个类**的 @Test 数；整模块 @Test 共 21（9 类）
```

**「7」是 TL 从旧记录抄来的数字，实际语义被误解** —— 又一次「数字对、口径错」。

### 七问裁定

| # | 问题 | 裁定 |
|---|---|---|
| **Q1** | 改 A + `rag-common` 参与 reactor | **允许 `-am`**（R-0 已证编译通过），**但不许改 `rag-common` 源码**；构建后须对比 `rag-common` jar 的 class 列表，确认无意外变化（它被多服务依赖） |
| **Q2** | 构建/部署由谁、在哪、什么命令 | **必须 Owner 定**。`bin/` 下 `grep "mvn "` = 0，**零脚本证据**，只能推断「人工在部署仓 `mvn package`」。TL 建议：`llmke-r12` 侧 `mvn -pl rag-index-service -am package -DskipTests` → 重启 18082。**属运行态变更，需显式授权** |
| **Q3** | 207 语义 | **保持现状，不动**。`classify` 已正确（L13 结论已落地在源码里）。D-4 的缺口是**端到端**，不是分类逻辑 |
| **Q4** | r12 conf 加 `v2-ingest.url` + 更新注释 | **同意**，但**加键时值必须是 `""`**（不启用）；注释更新须逐条写明「理由 ②③ 已过时及原因」，**不许只删不解释** |
| **Q5** | 先加开关不删 legacy | **同意**，但追加硬条件：**`v2Ingest` 必须同时写 `graph_parse_status`** —— 否则切过去后该字段永远停在「未做(1)」，前端显示卡死。这是 P5-1 的必要项，不是可选项 |
| **Q6** | mvn 基线 | **先用 `-DskipTests` 做编译基线**；`surefire-junit3:2.12.4` 缺失**登记为环境缺口**，**不许自行联网下载**（环境变更需 Owner 授权） |
| **Q7** | 「P5 代码完成 ≠ 已生效」 | **完全同意且升级**：本轮是「源码有、线上连类都没有」，**必须把「构建+部署+重启」作为独立验收项**，不得以「代码已改」代替 |

### TL 追加三问

**Q8**：`graph_parse_status` 的写入责任归属 —— `doSuccess` 还是 `v2Ingest`？两者都写会冲突吗？需给明确方案。

**Q9（重要）**：**部署仓 Java 源码普遍落后？** B 侧 `FileAppServiceImpl` 是 10-29 快照。要求补查：**所有 Java 模块的「部署仓源码 mtime vs 运行 jar 构建时间」**，确认还有哪些服务的修过但没上线。

> 如果不止一个，说明「Java 侧改动不生效」是**系统性问题**，之前几轮任何「修好了」的 Java 声明都要重新核对。

**Q10**：`remote.file-revise_date.url` 被注入 `RemoteFileUtils:36` 但**未找到使用点** —— 成员标「未决」是正确的（没猜）。P5-3 删键前必须查清，否则不知道能不能删。

### 成员的一处诚实值得记

它明确写「1 处没查到底：`remote.file-revise_date.url` 虽被注入但未找到直接使用点，标为未决，不敢猜」。

**这比编一个听起来合理的答案有价值** —— P5-3 若照错的结论删键，线上会静默失效。

## 五十八、R-0b 结论：Java 侧**系统性落后**（23:5x）—— 影响范围超出 P5

### Q9 答案：5 个模块内容不一致，jar 全由部署仓构建

| 模块 | 部署仓源码 | 运行 jar | 缺失内容 |
|---|---|---|---|
| `rag-index-service` | **10-29** | 11-07 02:57 | 缺**整个 v2-ingest**（8 个文件，332 行） |
| `rag-common` | 11-07 02:57 | 11-07 02:57 | 部署侧 `FileParseTaskInfo` **无 `doc2mdDir`** |
| `rag-qa-service` | 11-07 20:56 | 11-07 20:57 | `AiServiceImpl` 少 6848 B |
| `rag-graph-service` | **2026-01-21**（10 个月前） | 11-07 02:57 | 缺 `V2GraphProxyController`（jar 内命中 0） |
| `rag-gateway` | 10-26 | **10-28 23:51** | `AuthFilter` 少 385 B |

**jar 时间离散**（auth/index/graph 11-07 02:57、qa 11-07 20:57、gateway 10-28 23:51）⇒ 部署仓「**按需手工 `mvn package`，从未全量重建**」。

### ⚠️ TL 核实的一条**真实功能故障**（不属 P1~P4，但影响 P6）

```
前端 frontend/plateform/.../graphData.ts 引用 v2WholeGraph（dist 已打包）
  ↓
gateway AuthFilter：线上**缺** "/graph/search/v2WholeGraph" 免权限条目 → 走资源权限表检查
  ↓
rag-graph-service V2GraphProxyController：「源码有（11-04 新增）、jar 内命中 0」→ **端点不存在**
  ↓
18094 /v2/graph/view
```

**两环皆断**：网关可能拦、服务端 404。**「图谱增强页」在线上是坏的。**

- 源码仓 gateway 已修（注释写明「仍要求 JWT，只跳过资源权限表查」）；
- 但 gateway jar 停在 **10-28**，修复未上线；
- graph-service jar 里**没有这个 Controller**，连端点都不存在。

**这条不属于 doc2md 增量范围，是既有技术债，被 R-0b 顺带挖出。** 需 Owner 决定：并入 P5 / 另立任务 / 暂不处理（但 P6 若含图谱页 E2E，必须处理）。

### Q8 裁定：`graph_parse_status` 写入责任

成员方案（由「知道结果的一方」写）**采纳**：

| 事件 | 谁 | 值 |
|---|---|---|
| 触发建图 | 现有触发点不变 | 2 PARSE_ING |
| `outcome=OK` | **v2Ingest** | 3 PARSE_SUCCESS |
| **`outcome=RETRY`（207/5xx/连不上）** | **v2Ingest** | **保持 2**（不落 4，否则前端显示失败并停自动重试） |
| `outcome=PARSE_FAIL`(4xx) | **v2Ingest** | 4 PARSE_FAIL |

**成员指出「冲突会真实发生」是对的**：legacy `generateGraph` 与 `v2Ingest` 同时跑会「先 3 后 4」或反之，终值取决于完成顺序。

**TL 追加硬约束**：
1. **删 legacy 必须与「二选一开关」同批**，禁止两条路径同时写同一字段；
2. **加断言**：同一请求内 `graph_parse_status` 只能由一个路径写（可用一次性标记或开关断言）；
3. `RETRY` 保持 2 这条**必须有独立用例** —— 它是「前端不会误显示失败」的唯一保障。

### Q10 结论：`remote.file-revise_date.url` 是死配置

```
RemoteFileUtils:36  @Value("${remote.file-revise_date.url}")
RemoteFileUtils:352 public String filereviseDate(String p)
grep -rn "filereviseDate(" → 仅定义处 1 处，**零调用点**
排除反射（无 getDeclaredField/getFields/getUrlByKey）、未被继承
```

**结论成立**（限本模块内）。P5-3 删键前仍建议人工确认一次 —— 成员主动标注了范围限制，这点正确。

### TL 追加的验收要求（对应 Python 侧的 pyc 扫描）

**凡涉 Java 的 loop，验收必须加一条：运行 jar 内的 class 是否含本次关键符号。**

```
unzip -p <jar> <Class>.class | javap -c -  | grep <关键符号>
或  unzip -l <jar> | grep <Class>.class
```

**理由**：本轮证明「源码改了」「单测绿了」「jar 构建了」三者可以全部为真，而**线上仍是旧行为**（构建的是旧源码）。Python 侧靠 pyc 字节码扫描抓住了这个问题，Java 侧必须有等价手段。

### 对 P1~P4 结论的影响：**无**

P1~P4 全部是 Python 侧（18094/18096/shim），不依赖 Java 构建产物。**这 5 个模块的落后不影响已收口的 L1~L13。**

**但 `T-D2MD-13` 的 acceptance 里「Java 按 HTTP 码还是 body code」的结论须标注**：该结论**基于源码 A 侧**（`classify` 确实同时看两者），**线上未生效**（jar 无该类）。结论本身正确，但不能被读成「线上已验证」。

### P5 执行顺序（TL 建议，需 Owner 批）

**新增前置 P5-0：部署仓源码同步**（5 个模块 A→B），否则「改 A 再构建」构建的仍是 B 的旧源码 —— 白做。

```
P5-0  部署仓源码同步（5 模块）+ 全量重建 → 使线上与源码一致
P5-1  Java 派发切换（改 A、加开关、写 graph_parse_status）
P5-2  两仓配置同步（v2-ingest.url 仍为 ""）
P5-3  启用 v2-ingest + 12340 退役
```

**P5-0 本身是运行态变更**（重建 + 重启 5 个服务），**需显式授权**。

## 五十九、⚠️ 18084 下线事件与根因（02:0x）—— 暴露一个已坏 42 小时的链路

### 事件

P5-0b-2 重启 18084 失败（`exit=1`，5 秒），**旧 jar 同样失败** → 与本次构建无关。已回滚 jar（`a1e40330…` 原件）。

```
Caused by: BeanInstantiationException:
  Failed to instantiate [com.vesoft.nebula.client.graph.SessionPool]:
  Factory method 'getSessionPool' threw exception: java.net.ConnectException
  → NebulaGraph pool init failed.  (NebulaGraphConfig.java:69)
```

### TL 两处错误（同一类：凭记忆写期望值）

| # | 错误 | 后果 |
|---|---|---|
| 1 | **把 18081 当成 graph-service** | 18081 实为 **rag-auth-service**；graph-service 是 **18084**。按 TL 命令探测会得到 404 并**误判「Controller 缺失」** |
| 2 | 采信 R-0b「部署仓缺 `V2GraphProxyController`」 | **部署仓源码本来就有**（5645 B / 11-04，与源码仓一致）；缺的是**旧 jar 里没有这个 class** |

**这正是本轮反复批评成员的「期望值凭记忆写」** —— 轮到 TL 自己犯了两次。成员改用 `/proc/<pid>/cmdline` 做权威端口映射，纠正成立。

### 根因链（TL 查证）

```
① Nebula 三容器 42 小时前 Exited(0)（FinishedAt 2026-11-07 03:04:52）
   RestartPolicy=unless-stopped 却未自动拉起 ⇒ **被显式 stop**
② 这是**有意的 V1 迁移动作**：HYBRID-RETRIEVAL-RECOVERY-20261106.md 恢复动作第 6 条
   「停 19529 + Nebula×3，mask r12-graphsvc.service，同步 r12.target | ✅ 100s 未复活」
   —— mask 正是为了防 watchdog 每 45s 把 V1 拉回来
③ 但 graph-service **仍依赖 Nebula 启动**：NebulaGraphConfig 的
   `@Bean(name="nebulaGraphSessionPool")` 在启动时 eager 初始化 SessionPool
④ TASKS.yaml T-D0「剩：前端 GraphCanvas 改接 18094 视图 + **Java graph-service 脱离 Nebula**」
   ⇒ **该待办未做**
⑤ graph-service 旧进程 lstart 2026-11-07 03:04:38，比 Nebula 退出（:52）**早 14 秒**
   ⇒ 连接池建于 Nebula 死前，之后 42 小时所有走 Nebula 的图查询一直是失败的
```

**「图谱增强页两环皆断」实为三环** —— 第三环（graph-service 依赖已停的 Nebula）42 小时前就断了。

### TL 查证的修复路径（关键：有设计好的条件装配）

```
graph.type: nebula        ← 当前配置

四处 @ConditionalOnProperty(name="graph.type", havingValue="nebula")：
  NebulaGraphConfig / NebulaGraphTemplate
  GraphNebulaSearchAppServiceImpl / GraphNebulaQueryDomainServiceImpl

但 GraphTemplate **只有一个实现**（NebulaGraphTemplate，条件装配）
且 GraphDataParser 是**无条件 @Component** 并注入 GraphTemplate
⇒ **改 graph.type 会因 GraphTemplate 无实现而注入失败** —— 不能靠改配置脱 Nebula

SessionPool 的两种获取方式：
  NebulaGraphTemplate  → @Resource NebulaGraphConfig，直接调 getSessionPool(spaceName)  ← 运行时懒加载
  @Bean nebulaGraphSessionPool → **没有任何注入点**，但 Spring 启动时 eager 创建  ← **启动失败的真凶**
```

### 裁定：方案 B（`@Lazy`），不是重启 Nebula

| 方案 | 动作 | TL 评价 |
|---|---|---|
| **A** 重启 Nebula ×3 | `docker start` | ❌ **回退一个已完成的迁移决策** —— RECOVERY 专门 mask 过 service 防复活，重启即违背 |
| **B** `@Bean` 加 `@Lazy` | 一行注解 + 重建 + 重启 18084 | ✅ **正是 T-D0「脱离 Nebula」的第一步**；该 Bean 无人注入 → `@Lazy` 后永不初始化 → 启动不连 Nebula；`/v2WholeGraph` 不碰 Nebula，正常工作 |
| **C** 保持下线 | 不动 | 图谱页继续坏 |

**B 的预期效果**：
- 服务能起（`/v2WholeGraph` → 18094 → 114 节点 / 94 边）；
- 旧 Nebula 端点第一次调用时抛异常（500）—— **但它们已坏 42 小时**，不会更坏；
- **`/v2WholeGraph` 本就是「不依赖 Nebula」的新路径**，正好顶上。

**B 是改 Java 代码（1 行注解），需 Owner 授权。**

### 现状（等待授权）

```
18084   未监听；jar 已回滚 a1e40330…；src 已同步（源码在、未生效）
18082   正常 pid 3130060（P5-0a 成果保持）
18094 / 18096 / 19526 / 19527 / 19531 / 8088 / 18081 / 18083 / 18085  pid 全部未变
生产图 e2d0f754… / kb_9=44 未变
```

**doc2md 链路（18094/18096）完全不受影响** —— P4/P5 主线未被波及。

## 六十、graph-service 端点可用性清单（03:0x，为 `@Lazy` 方案与 P6 准备）

### 全部 17 个端点（TL 从源码逐一提取）

| 控制器 | 端点 | Nebula 依赖 |
|---|---|---|
| `GraphController` (`/info`) | `GET /nodes`、`GET /edges` | **是** |
| `GraphDataStatisticsController` (`/graphStatistics`) | `GET /getWholeGraphStatistics` | **是** |
| `GraphSearchController` (`/search`) | `GET /instances`、`POST /nodeSearch`、`POST /edgeSearch`、`GET /keywordSearch`、`POST /pathSearch`、`POST /cypherSearch`、`POST /searchNodesByIds`、`POST /nodeStepSearch`、`POST /wholeGraphSearch`、`GET /canSearchNodeOneStep`、`POST /commonNeighbourSearch`、`GET /subGraph`、`GET /ping`、`GET /file/pageNum` | **是**（`GraphSearchAppService` 唯一实现是 `GraphNebulaSearchAppServiceImpl`，条件装配 nebula） |
| `V2GraphProxyController` (`/search`) | **`POST /v2WholeGraph`** | **否**（纯 `RestTemplate` 转发 18094 `/v2/graph/view`） |

**合计：16 个依赖 Nebula，1 个不依赖。**

### `@Lazy` 方案后的预期状态（必须提前写清，否则 P6 会当成新问题）

```
18084 能启动 ✅
POST /graph/search/v2WholeGraph  → 200 + nodeList（114 节点 / 94 边）✅
其余 16 个端点                    → 首次调用 500（Nebula 连接失败）⚠️
```

**16 个端点不可用 ≠ 本次改动造成的回归**，而是 **`T-D0`「graph-service 脱离 Nebula」未完成**的既有事实 —— 它们**已经坏了 42 小时**（Nebula 于 11-07 03:04:52 停止，graph-service 连接池建于停止前 14 秒）。

**P6 必须把这份清单写进验收文档**：否则会有人把「nodeSearch 500」当成新 bug 去查，查到最后发现是「V1 已退役、服务还没迁完」。

### `@Lazy` 的边界（写进 evidence）

`@Lazy` **只解决启动期**。若将来有人 `@Resource SessionPool`，会拿到代理并在**首次调用**抛同样的错。**这是「把启动失败推迟到运行时」，不是「修好了 Nebula 依赖」** —— 真正的修复是 `T-D0` 的「脱离 Nebula」。

### V1 退役证据（成员独立复核，TL 采信）

```
systemctl is-enabled r12-graphsvc.service → Failed to get unit file state: No such file or directory
systemctl status  r12-graphsvc.service → Unit ... could not be found
ls /etc/systemd/system | grep -iE 'graphsvc|nebula|19529' → 无
ss -tlnpH | grep ':19529' → 未监听
docker: nebula graphd/storaged/metad → Exited(0)，RestartPolicy=unless-stopped 未自启
```

**判读**：不只是 mask，**unit 文件已被删除**；配合 `19529` 未监听与 RECOVERY 文档记录，**「V1 图谱栈彻底退役」是有意为之**。**A 方案（启容器）被证据排除。**

## 六十一、✅ 里程碑：P3/P4 图谱成果首次被 Java 侧看见（03:4x）

### `@Lazy` 生效，**`v2WholeGraph` 返回 114 节点 / 94 边**

TL 独立核实（非转述）：

```
18084  pid 3203006   lstart 21:20:30 > jar 21:20:18
       jar: rag-graph-service/target/rag-graph-service-0.0.1-SNAPSHOT.jar

POST /graph/search/v2WholeGraph {"spaceName":"kb_9"}
  → HTTP 200 ｜ nodeList=114 ｜ edgeList=94 ｜ notice=null
  样例节点  {"vid":"ent:#docx","name":"# DOCX","nodeType":"实体","properties":{"kind":"entity",...}}
  样例边    {"src":{"vid":"ent:#智造贷企业流...","name":"loan product manual"}} → ent:loanproductmanual

GET /graph/search/ping → 200 {"data":true}

生产零影响  current.json e2d0f754… 未变｜18094 2227759 / 18096 2773520 / 18082 3130060 未变
Nebula     三容器仍 Exited(0) 42h（**未启**）
```

**114/94 与生产 `graph_view` 完全一致，样例节点/边是真实生产数据** —— 不是空壳。

### 两处变更的贡献（TL 要求分清，已分清）

| 变更 | 贡献 |
|---|---|
| `V2GraphProxyController`（上轮同步进 B 源码） | **让 `/v2WholeGraph` 有路由** |
| `@Lazy`（本次） | **让进程能起来**（启动段 0 次 `NebulaGraph pool init failed`） |

### 改动面：`diff` 新增 9 行 / 删除 0 行（非 TL 预期的 +2）

成员如实报备：1 个 `import`（`org.springframework.context.annotation.Lazy`，不加编译不过）+ 7 行注释 + 1 个 `@Lazy`，**任何既有代码行未动**（`diff` 无 `<` 行）。

**TL 认可**：不硬凑「+2 行」而隐瞒 import 是对的。**判据应是「既有代码零改动」，不是「行数符合预期」** —— 我给的「+2」是估算，不是规范。

### 端点计数：TL 数错，成员正确

TL 说「17 个端点、16 个依赖 Nebula」，成员逐端点核为 **18 个**：

```
GraphController 2 + GraphDataStatisticsController 1 + GraphSearchController **14** + V2GraphProxyController 1 = 18
可用：v2WholeGraph + ping = 2
不可用：16（依赖 Nebula）
```

**TL 把 `GraphSearchController` 数成 13，漏了 `GET /file/pageNum`。** 差 1 个虽不影响结论，但「逐条数」这种活我该数准。**这轮第 N 次「大概数了一下」。**

### 运行时行为验证（`@Lazy` 的预期语义）

旧 Nebula 端点 → **500 + `NebulaGraph pool init failed`**，栈为：

```
NebulaGraphConfig:78 → NebulaGraphTemplate:52 → execute:103 → callCypher:384
```

**运行时才触发，不是启动时** —— 这正是 `@Lazy` 的预期：**把启动失败推迟到实际使用**。

按 TL 要求如实记录为「**迁移未完成，本就如此（已坏 42 小时），不是本次回归**」。

### 成员写进 evidence 的两个读数陷阱（TL 采纳）

1. **graph-service 有全局响应包装**：`nodeList` 在 `data` 里，不在顶层 —— 按顶层取会得到 0，**误报「200 但空列表」**；
2. `instances` 不带 `fileIds` 时返回 500「参数缺失」，**看起来像 Nebula 失败其实只是校验**，必须带齐参数才测得到后端错误。

**这两条都是「同一个 200/500 有两种含义」的典型**，与本轮反复出现的「同一判断两处规则」同族。

### 剩余缺口

| 缺口 | 状态 |
|---|---|
| **gateway 的 `/graph/search/v2WholeGraph` 免权限** | **未做** —— 前端走 8088 仍会 401/403 |
| 16 个依赖 Nebula 的端点 | 不可用，属 `T-D0` 未完成 |
| `V2GraphProxyController` 的 `@Lazy` 后续风险 | 若将来有人 `@Resource SessionPool`，首次调用会抛同样错 |

**前端链路现在是「服务端通了、网关还没通」。**

## 六十二、`@Lazy` 收口 + **A/B 一致性规则**（04:1x，TL 独立核实）

### TL 核实（非转述）

```
A llmke-v2/.../NebulaGraphConfig.java   md5 01fdb13b…  @Lazy 3
B llmke-r12/.../NebulaGraphConfig.java  md5 01fdb13b…  @Lazy 3
cmp 逐字节一致 ✅ ｜ diff 行数 0 ✅

行号对齐  A:78 = throw new ConnectException("NebulaGraph pool init failed.")
          A:83 = throw new RuntimeException(e)          ← 与运行时栈一致

jar  a4d9f340… / 21:24:54 / 内含 Lorg/...annotation/Lazy
18084 pid 3234127 / lstart 21:25:44 > jar 21:24:54
v2WholeGraph → 200 / nodes=114 / edges=94
生产 current.json e2d0f754… 未变
```

### ⚠️ 本轮最隐蔽的坑：`@Lazy` 起初只落在 B，A 没有

```
处置前  A 77 行 md5 62eb48db… Lazy=0 ｜ B 91 行 md5 01fdb13b… Lazy=3
```

**后果**：下次任何 A→B 同步会把 `@Lazy` 覆盖 → 18084 重新起不来，且「同步」看起来是无害操作，极难归因。

**这解释了整轮那个谜**：为什么部署仓 Java 会系统性落后？

**因为改动在 B 直接做、A 不更新 → 两边分叉。** 之前只看到「B 落后 A」，现在是「B 超前 A」—— **同一机制的两个方向**。

**TL 也有责任**：执行令写「改 `NebulaGraphConfig.java`」但**没写哪个仓**，成员按构建位置理解为 B 是合理推断。

### 🆕 新增流程规则（写入 P6-BACKLOG）

> **① Java 任何改动必须先落 A（源码仓），再同步 B（部署仓）构建。禁止直接在 B 上改。**
> 判据：改完 `diff A B` 该文件必须为空。
>
> **② 跨仓操作在报告/执行令里必须显式写 A 或 B。**
> 理由：两个仓都叫「源码」，「源码」这个词本身就是歧义源 —— 本轮两处误判都源于此。

### 成员报备的两条操作教训（TL 采信并记录）

1. **跨仓文件必须显式写 A/B** —— 见上；
2. **`git status --short -- <绝对路径>` 在本仓不匹配 pathspec** —— 必须用**相对仓库根**的路径。成员因此一度误判「A 未跟踪」。

> **第 2 条 TL 也踩过同类**：先前核实 `V2GraphProxyController` 时用的是 `git -C llmke-r12 status --short -- '相对路径'`（对的），若换成绝对路径会静默返回空 → **误判「文件不存在」**。

### 成员主动承担责任的一处

> 「P5-0b 全程我按 A→B 同步，本轮却在本应写 A 时写了 B。你的执行令没写仓是事实，但我在同一 loop 内已有『A 是源』的上下文，至少应先问一句或先落 A。」

**TL 评价**：**执行令没写仓是 TL 的缺失，不是成员的理解错误**。但成员在已有上下文下主动认这一步，比推给我有价值 —— **这类「双方都有责任」的事，先认的一方能让复盘快一步**。

### 现状（全部正常）

```
18084  3234127  v2WholeGraph 114/94  ✅
18082  3130060  P5-0a 成果保持       ✅
18094  2774847+2227759  ｜ 18096 2773520  未变
生产图 e2d0f754… / kb_9=44  未变 ｜ Nebula 三容器 exited（未启）
```

## 六十三、仓库结构真相与 36 项归类（05:2x）

### ⚠️ TL 的重大理解更正：不是两个仓库，是一个仓库三个 worktree

```
/home/szf/data/dev/llmke        ← 主工作区，检出 **main**
  └── .git                      ← 唯一 git 目录（common-dir）

/home/szf/data/dev/llmke-v2     ← **worktree**，检出 feat/spectra-theme（**无远程分支**）
/home/szf/data/dev/llmke-r12    ← **worktree**，检出 feature/R12-real-rag（**落后 main 274 提交且无独有提交**）
```

**因此 P4/P5 中 TL 讲的「A 源码仓 / B 部署仓」「双副本同步」前提不成立。** 二者是同一仓库的两个**分支工作区**，不是主从关系。

**已做的修正**：`diff A B` 判据仍有效（保证两处一致），但表述应改为「分支合并」而非「同步」。`@Lazy` 两边一致仍然必要（否则合并时丢失）。

**衍生事实**：
- `llmke-v2` **130 项未提交**（109 新增 + 21 修改）= **L1~L13 全部工作**
- `llmke-r12` **36 项未提交**
- **生产混跑两个 worktree**：Python（18094/18096）跑 `llmke-v2` 未提交代码；Java 跑 `llmke-r12` 的 R12 分支
- `feat/spectra-theme` **无远程分支** ⇒ 130 项工作只存在于一个工作区

**TL 已备份**：`/home/szf/data/dev/llmke-v2-wip-20261108T213218.tar.gz`（174 MB / 3487 项 / md5 `3730cd2c…`）。**特意不放 `/tmp`** —— 该项目曾因 `/tmp` 被清空丢失图数据与 `kb_state`（`HYBRID-RETRIEVAL-RECOVERY-20261106.md`）。

### 36 项归类结果：A 12 / B 9 / C 6 / D 9

**A（修 bug，必须进 main）12 项**：7 reranker(`rrf_k 5→60` + 按 pk 去重)、9 global 切 18094、10 `es.py:_to_int_or_raw`、11 `doc2mdDir`、13 `IdType.AUTO`、14 `OperationLogAspect` 吞异常、17/18/19 v2Ingest 三件套、34 `V2GraphProxyController`(114 行)、35 `RemoteV2IngestUtils`、36 `RetrievalEndpointStartupCheck`

**B（留部署侧）9 项**：1 watchdog、2 index yml、3 qa yml、4 r12.target、16 `@Lazy`、21 `GraphDomainServiceImpl`、23 `RemoteGraphUtils`、27 `r12-graph-v2-start.sh`、30 `platform/r12/data/`(245 MB)

**C（可丢）6 项**：5 `last-run.json`、28/29 `*.bak-20261102`、31/32 两个验收结果目录、33 `es.py.bak-p4l13c`

**D（已被覆盖）9 项**：6、8、12、15、20、22、24、25、26

### ⚠️ TL 核实的三条最高风险判断（全部成立）

**① main 的 `/v2WholeGraph` 是坏的 —— 所有库读同一快照**

```
main  (origin/main)  87 行  spaceName|kb 命中 **0**
      :45  String url = v2GraphApi + "/v2/graph/view"     ← **不带 kb 参数**
r12 工作区           114 行  spaceName|kb 命中 7            ← 有 kb 路由
```

**所以 #34 不是「新增文件」，是「替换 main 的旧版」**。若当新文件合入，会保留「所有库读同一快照」的缺陷 —— **而直接切生产到 main 会让图谱页读错库**。

**这是「切 main 前必须修」的第一项。**

**② 三项搬进 main 反而是回退**

```
#6  multiple_retrieval.py   v2 648 行含 _original_kb()+file_id term ｜ r12 仅 640 行
#8  retrieval_service.py    v2 已含 enabled_graph 早退修复（:453）
#25 AiServiceImpl           v2 已含 R15-F05 reference 回落（:395）
```

**把 r12 这份搬进 main = 删掉 v2 已有的修复。** 归类为 D（已被覆盖）正确。

**③ `platform/r12/data/` 245 MB 未 ignore**

```
du -sh → 245M ｜ git check-ignore → ❌ 未 ignore
```

挂在 `git status` 里既拖慢又易误提交。**建议立即加 `.gitignore`（不进 main）。**

### 合并顺序（成员建议，TL 采纳）

- **可独立直接摘（6 项）**：7、10、13、14、34、36
  - **13+14 同批**（同源故障）
  - **36 进 main 前必须改**：`fail-fast` 默认改 false、去掉 `platform/r12/...` 硬编码路径
- **必须成组（5 项）**：`11 → 35 → 17/18 → 19`，顺序不可换，否则中间态编译不过
  - 合入后 `remote.v2-ingest.url` 默认空 ⇒ `enabled()=false`，**生产行为不变**
- **需改造后再进（1 项）**：9（把 `18094`/`19200` 硬编码提为配置）
- **B 里建议顺手进 main（1 项）**：16 `@Lazy` —— 环境无关、无副作用；不进则 main 将来退役 Nebula 时会以同样方式起不来

### 两条额外发现

1. **`/commonSearch` 接口下线不能单独搬**：`#12/15/24/26` 是同一组改动，只搬常量删除或只搬类删除都会**编译失败**（引用还在）。迁 main 需先由 Owner 决定是否废弃该对外契约。
2. **v2 存在一条既有 stash**：`stash@{0}: On main: llmke-main dirty snapshot 20261103 (before ff to origin/main)` —— **不是成员建的**，需 Owner 确认是否还有价值。

### 边界

成员全程只读：r12 `git status` 仍 36 项，未 `add/commit/stash/checkout`，未重启服务，未动 245 MB 数据目录。evidence 写在 v2（v2 未跟踪计数 130→131，仅新增该 evidence 文件）。

## 六十四、DoD 进度

`04-ACCEPTANCE.md` required_checks A-1~E-3：**0 / 16**（尚未进入 P6 实现验收）。P0 VERIFIED；**P1（L1~L5）+ P2（L6/L7/L8）+ P3（L9/L10/L11）+ P4-L12 全部正式内部收口**（各双证据、`QA_PASS` 挂起）；**P4-L13：A/B 段完成、C 段代码面全部完成（C1~C4 + C5 主体 + C5 离线 + D-1 门控补丁），但有 3 项形式未达成**；P5~P7 未开始。**待签队列 12 个 loop**（L1~L12）。

**阶段进度**：P1 ✅ / P2 ✅ / P3 ✅（代码面）/ **P4 代码面 ✅、形式 3 项未完** / P5~P7 未开始。

### 运行态实际状态（**C5 演练后**）

```
18094   pid 2227759    生产图根 .../llmke-r12/platform/r12/data/graph-root（**全程 0 次重启**）
18096   pid 2773520    影子；/health.graph_api=http://127.0.0.1:18094、configured=True
                       （C5 演练：2207749 → 2765422 指 19999 → 2773520 恢复，共 2 次重启）
19531   pid 435286
影子索引 v2cand_kb_9 = 5 条；影子 state version=12（290/291/292/293 全 ACTIVE，**293 为 C5 演练产物**）
生产 kb_9 = 44、table_chunks_kb_9 = 2、current.json e2d0f754…、fence.json 857a69b4…、graph_view 114/94
```

### P4-L13 的三项未达成（**不得写成通过**）

| 项 | 实际 | 阻塞 |
|---|---|---|
| **D-1** | 门控补丁源码侧就绪、默认关闭；**部署侧 6 项未同步**；**unit 因部署仓缺 `kb-ingest.env` 现不可启动**（fail-fast 预期） | 运行态变更，需 Owner 授权 |
| **D-3** | 用「改 18096 指向 19999」**等价模拟**，**未真停 18094** | 影响生产查询，不建议现在做 |
| **D-4** | Java 非 200/207 回写 `PARSE_FAIL` **未编译未单测** | 需 Java 构建环境 |

**C5 覆盖的是「图谱不可达时服务行为」**（207/PARTIAL/不推 cursor/不提交状态/生产零影响），**不等于 D-1/D-3/D-4 通过**。

### ⚠️ 结构性风险：部署脚本双副本

```
Python 代码   单份（源码仓），改完 + 重启即生效 —— **L9~L13 代码改动全部生效**
部署脚本/env  两份（llmke-v2 / llmke-r12），**按需人工同步**，无任何一致性校验
```

**本次教训**：L13-B 的 6 项产物全在源码侧，部署侧一个都没有。`up.sh verify` 能验服务健康，**验不出「两份脚本不一致」**。已登记 P6 第 7 项（建议对比关键脚本 md5，不一致 warn 不 fail）。

### 跨 loop 待办（传给部署窗口）

1. L9/L10 是进程内结构、**重启 18094 前不生效**；L11 是模块级常量、不 reload 即旧值；
2. **L13-A 的 `_is_own_root` 统一（18:30:33）未被 18094 加载**（18094 启动于 18:28:38）—— 仅**逻辑等价重构**，行为无差异，下次重启自然加载；**不得表述为「代码与线上完全一致」**；
3. L12 的 `response.status_code = code` **必要但不充分** —— Java 侧还需读 body `code` 才能识别 207（两层缺一不可）；
4. L13-A 的写入端点 **fail-closed**：未配 env 且无 `LLMKE_ALLOW_DEFAULT_WRITE_TARGET=1` → `INDEX_WRITE_FAILED`；**生产禁止设该开关**；
5. **「同一判断两份实现/两处读取」系统性问题**（本轮出现 6 次）：`lstrip('-').isdigit()` vs `int()`、`test_index_writer` 把错值钉成契约、`applied_to_memory` vs `_is_own_root`（已统一）、`/health` 重读 env vs 闭包（缺陷 13）、`GRAPH_API_UNREACHABLE` 两路径两种 HTTP 码、TL 写判据抄 `ERROR_HTTP` 表而实际走 `PARTIAL`。**部署窗口应集中扫一遍。**

### 未决于 Owner

1. **G-4 三项输入**（`principal_id` / `key_id` / Ed25519 公钥 PEM）；
2. **L8 模式 B 授权**（影子索引已建，如需正式化请确认）；
3. **`table_summary` 是否另立任务**；
4. **P4 三项形式是否补做**（D-1 部署侧同步 / D-3 真停 18094 / D-4 Java）；
5. **下一步走 P5（Java 侧）还是 P6（验收）**。
4. **C5 主体授权**（改 18096 env + 两次重启）；
5. **L13-B 部署脚本是否先做**（可写不执行的替代路径）。
