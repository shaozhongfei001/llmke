# r5 独立 QA 信任链调查与决策包

- 调查时间：第四轮
- 受审候选：`L0-contract-baseline-r5`（`QA_PENDING`，rev 12）
- 结论速览：**信任链本身是闭环且非循环的，阻塞不在技术，而在「谁有权动锚点、谁有权签名」**
- 本文件不参与源码快照与冻结控制面

---

## 1. 权威来源、签署者与适用范围

| 项 | 事实 | 依据 |
|---|---|---|
| 信任根位置 | 工作区**之外**：`~/data/qa-keys/trust-root.json` | `verify_envelope()` 强制 `trust root must be outside implementation workspace` |
| 权威来源 | 受保护运行环境（`environment: PROTECTED_RUNNER`） | 信任根文件字段 |
| 当前锚定基线 | `approved_baseline_sha256 = c8a73c3736db…`（窗口前 1.1.0 基线） | 信任根文件 |
| 已登记签署者 | `key_id=qa-ed25519-2026-10` → `principal_id=qa-owner-01`，`roles=[qa-owner]`，`enabled=true` | 信任根 `principals` |
| 适用范围 | 仅 `purpose=QA_ATTESTATION` 的信封；且 `required_role=qa-owner` | `verify_qa()` |
| 独立性硬约束 | 签署者 `principal_id` **不得**出现在 `LOOP.yaml.implementation_principals`（r5 为 `["integration-agent"]`） | `loop_guard.verify_qa()` |
| 明文密钥位置 | `~/data/qa-keys/llmke-qa.key`（工作区外） | 文件系统；本轮未读取其内容 |

**结论**：`qa-owner-01` 是唯一已登记签署者；TL（`tech-lead`）与实现者（`integration-agent`）都不是 QA 角色。

---

## 2. `approved_baseline_sha256` 与 r5 的比较方式

比较是**单值相等**，没有版本区间、没有兼容规则：

```
baseline_hash(root) = sha256(文件 docs/baseline/FROZEN-MANIFEST.json 的字节)
if trust.approved_baseline_sha256 != baseline_hash(root): 拒绝
```

| 侧 | 值 |
|---|---|
| 信任根锚定 | `c8a73c3736dba301c8771cf7f09a575adcaf8be64763e55da04e746376cece04` |
| r5 冻结清单 | `213c6ebc203ef846c3edf5397a9640310a683391878ddb5af4c12b8da25cbc52` |

**不等 → 任何签名都会被 `external approved baseline digest mismatch` 拒绝。**
这是唯一一处「必须先更新锚点才能签署」的强绑定，也是本轮的硬阻塞。

---

## 3. 更新信任根是否会落进本次摘要的覆盖范围（关键）

**不会。** 这一点已用数据核实，不是推测：

| 检查 | 结果 |
|---|---|
| `FROZEN-MANIFEST.files` 中是否含 `qa-keys` / `trust` 相关路径 | **空列表**（0 个） |
| `control_digest` 的输入集 | `freeze_baseline.controls(root)` → 仅**仓库内**文件 |
| 信任根物理位置 | 工作区外，`verify_envelope` 显式拒绝工作区内路径 |

因此：**更新锚点 → 冻结清单与候选指纹都不变 → 不存在「改锚点导致候选失效、又要重新冻结」的循环。**

但有一个**必须遵守的时序约束**（否则会造出循环）：

| 顺序 | 动作 | 对候选的影响 |
|---|---|---|
| 1 | 冻结（已做） | 产生 `baseline_sha256` |
| 2 | **qa-owner 更新锚点为该值** | 无（仓库外） |
| 3 | 重新生成 QA 载荷 | 无（`subject` 不变，见 §5） |
| 4 | 签署 → `accept-qa` → `finish` | 无 |
| 5 | 合并 | 无（实测合并结果树 == 分支树） |

**反例（会造出循环，禁止）**：先在仓库里改任何**参与 `snapshot()` 的文件**，再想去生成载荷——
`qa_payload.py` 会以 `candidate evidence changed` 直接拒绝，因为它的校验仍是**整树** `snapshot()`。

> 这就是本轮的第二个控制面缺陷（P-09）：门禁记录用 `control_digest`，载荷生成却用整树 `snapshot()`。
> 结果是「文档改动不会让门禁证据失效，但会让 QA 载荷无法生成」。详见 `ROUND4-PROPOSALS.md`。

**安全操作边界**：本轮所有新增产物都写在 `docs/baseline/validation/` 与 `loops/**`，
这两个位置被 `source_files()` 排除（`loops` 仅 `LOOP.yaml` 参与），因此 r5 候选指纹未变——
已复核 `record.source_sha256 == snapshot(ROOT)` 仍为 `True`。

---

## 4. 谁有权更新锚点、谁有权签署、如何保证独立性

| 动作 | 有权者 | 不能是谁 | 如何留痕 |
|---|---|---|---|
| 更新 `approved_baseline_sha256` | `qa-owner` 或受保护运行环境运维人（业主） | **实现者 / TL**（会构成自签） | 变更前后值写入 QA 记录/交接单（当前信任根无内建审计字段，见 P-10） |
| 签署 `QA_ATTESTATION` | 持有 `qa-ed25519-2026-10` 私钥的 `qa-owner-01` | **`integration-agent`（实现者）**；框架会拒绝 | 信封 `key_id` + `payload.principal_id` + `payload.subject_sha256` 全部入库 |
| 接受签名（`accept-qa`） | 任意执行者，但证据必须是**当前候选** | 无法伪造（需私钥） | `evidence/manifest.json` 的 `attestation` 字段 |
| 收口（`finish`） | 同上 | 未通过全部门禁时会被拒 | `STATE.json` |

**独立性由框架强制**：`verify_qa()` 会拒绝「签署者出现在 `implementation_principals` 里」的信封。
换言之，即使我用 `qa-owner-01` 的私钥签名，`principal_id=qa-owner-01` 不在 `["integration-agent"]` 中，
框架**不会**拦截——**框架拦不住「实现者拿别人的钥匙签」这件事**。
所以独立性只能靠流程保证：**钥匙与执行者分离**，且签署前由 QA 自行复核（清单见 `R5-QA-HANDOFF.md` §4）。

这条必须说清：**不要以为门禁能自动保证独立性**，它只能保证「签名者不是声明的实现者」。

---

## 5. 一小时有效期的起算点、重建规则、是否改变被签署对象

| 问题 | 答案 |
|---|---|
| 起算点 | `issued_at` = **生成载荷的本地时刻**（UTC ISO8601），`expires_at = issued_at + 1h` |
| 校验区间 | `issued_at - 5min <= now < expires_at`，且 `expires_at - issued_at <= 7 天` |
| 过期后 | **不延长**；重新执行 `qa_payload.py` 生成新载荷（旧文件覆盖即可） |
| 重建是否改变被签署对象 | **不改变**。被签署的是 `subject_sha256`，其内容是 `{loop_id, gate_id, gate_spec_sha256, source_sha256, baseline_sha256, log_sha256, result, executed_checks}`，**不含任何时间字段** |
| 重建前提 | 候选（树 + 冻结清单 + 门禁定义 + 日志哈希）必须**完全未变**，否则 `qa_payload.py` 直接拒绝 |

> 也就是说：过期只是「签名窗口」过期，不是「被批准的内容」过期。这正是 P-02 想解决的复核问题——
> 现在复核也校验有效期，导致历史签名一小时后无法复核。

---

## 6. 精确签署操作单（由 qa-owner 执行，TL 不代做）

```bash
cd ~/data/dev/llmke

# ① 更新锚点（仓库外；这是「批准某条基线」的治理动作，不是配置）
#    目标值：213c6ebc203ef846c3edf5397a9640310a683391878ddb5af4c12b8da25cbc52
#    文件：~/data/qa-keys/trust-root.json 字段 approved_baseline_sha256
#    更新前后值须抄录到签署记录（当前信任根无审计字段，见 P-10）

# ② 立即重生成载荷（1 小时窗口从此开始）
python3 scripts/qa_payload.py --loop L0-contract-baseline-r5 \
  --gate independent_qa_gate --principal-id qa-owner-01 \
  --out docs/baseline/validation/qa-payload-r5.json

# ③ 签署
LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json \
python3 scripts/qa_sign.py --key-file $HOME/data/qa-keys/llmke-qa.key \
  --key-id qa-ed25519-2026-10 \
  --payload docs/baseline/validation/qa-payload-r5.json \
  --out docs/baseline/validation/qa-envelope-r5.json

# ④ 接受 + 收口
python3 scripts/loop_guard.py accept-qa --loop L0-contract-baseline-r5 \
  --gate independent_qa_gate --attestation docs/baseline/validation/qa-envelope-r5.json
python3 scripts/loop_guard.py finish --loop L0-contract-baseline-r5
```

**预期结果**

| 步 | 成功标志 | 失败信息 |
|---|---|---|
| ② | `UNSIGNED_QA_PAYLOAD; no QA approval granted` | `candidate evidence changed` / `successful QA candidate run required` |
| ③ | `signed approval written; verify in protected runner before acceptance` | 私钥不匹配 |
| ④ | `QA accepted for exact signed source/baseline/gate/log; DONE still requires finish` → `finish: PASS` | `external approved baseline digest mismatch` / `QA candidate evidence STALE` / `independent QA principal participated in implementation` |

**失败回退**

| 失败点 | 处置 |
|---|---|
| 锚点未更新 | 回到 ①；**不要**改 `LOOP.yaml.implementation_principals` 去绕过 |
| 载荷过期 | 重跑 ②（subject 不变，无需重跑门禁） |
| `QA candidate evidence STALE` | 说明仓库在 `qa-run` 之后被改过；需重建候选（r6），不得就地重跑 |
| 签名被拒（subject 不符） | 核对 `subject_sha256`，**不得**改载荷内容 |

---

## 7. 本轮不做什么

- **不修改信任根**（会构成自签）；
- **不使用** `llmke-qa.key` 签署（即使技术上可行、框架也不会拦）；
- **不**把 `QA_PENDING` / `LOCAL_QA_CANDIDATE` / 开发门禁 7/7 / 本地 exit 0 表述为 QA 通过。
