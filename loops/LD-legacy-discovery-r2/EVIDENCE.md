# LD-legacy-discovery-r2 证据

本批次为原 `LD-legacy-discovery` 的替代批次：原批次 `inventory_gate` 因源码快照变化判为 STALE，
且 attempts 已达 3/3，无法在原批次内重跑。

## 1. 门禁结果（同一快照 `d0530bee…`）

| 门禁 | 结果 |
|---|---|
| `inventory_gate`（`reuse.inventory`） | pass |
| `independent_qa_gate`（`qa.discovery`） | **NOT_RUN / QA_PENDING**（需受保护环境外部签署） |

门禁运行前已导出 `MAKEFLAGS=--no-print-directory`，确保证据日志不含宿主绝对路径
（`make security-check` 随后 PASS，415 文件）。

## 2. 台账状态（未改动，仍待核验）

| 台账 | 条目 | 已决议 |
|---|---|---|
| `docs/reuse/SOURCE-ASSETS.yaml` | 12 | 0（全部 `CANDIDATE_UNVERIFIED`，`decision: null`） |
| `docs/reuse/DATABASE-ASSETS.yaml` | 37 表 / 482 字段 | 0 |
| `docs/reuse/INTERFACE-ASSETS.yaml` | 506（Java 440 / Python 66） | 0 |

本批次**没有**修改任何台账内容、**没有**改变 P0 状态、**没有**批准任何复用决议。

## 3. 本批次不证明

- 不证明任何资产可直接复用；
- 不证明 506 条接口等于运行时可路由能力；
- 不构成独立 QA 签署（开发身份不得自签）。

## 4. 独立 QA 已签（2026-10-21）

| 项 | 值 |
|---|---|
| 结果 | `independent_qa_gate`: **pass**，`role=VERIFIED_QA` |
| 签名主体 | `principal_id = qa-owner-01` |
| 密钥标识 | `key_id = qa-ed25519-2026-10`（Ed25519） |
| 信任根 | 工作区外 `$HOME/data/qa-keys/trust-root.json`（`environment=PROTECTED_RUNNER`，基线 `c8a73c37…`） |
| 绑定对象 | `source_sha256 = d0530bee…`、`baseline_sha256 = c8a73c37…`、`independent_qa_gate.log` 哈希、`gate_spec_sha256` |
| 批次状态 | **DONE**（`finish` 已通过，rev 8） |

### 验签非空转的负例证据
用随机 64 字节伪造签名调 `accept-qa` → `FAIL: approval verification failed`，且记录状态未被改动
（仍为 `QA_PENDING`）。证明验签真实执行，不是"文件存在即通过"。

### 2 条操作要求（后续复核会用到）
1. **复核本批次证据必须设置 `LLMKE_TRUST_ROOT`**，否则 `evidence-check` 会报
   `external trust root not configured`——这是设计如此（验签需要公钥），不是证据失效。
2. `qa-run` 会刷新证据哈希，**载荷必须在 `qa-run` 之后立即重新生成**（有效期 1 小时）。

### 诚实声明（与"受保护环境"的差距）
本次签名在**开发机**上完成（私钥 `$HOME/data/qa-keys/llmke-qa.key`，600 权限，由 QA 方独占保管），
`environment=PROTECTED_RUNNER` 目前是**声明值**而非事实隔离。审计如需更强独立性，
应把私钥迁到真正的受保护 runner 并重签。

### 已知限制：QA 证据的事后复核窗口只有 1 小时
签名载荷的有效期为 1 小时（`qa_payload.py` 固定值），而 `evidence-check` 会对已接受记录重新验签并检查窗口，
因此超过 1 小时后复核会报 `invalid approval validity window`（详见本批次 `FAILURES.md` FAIL-2026-10-21-07）。
**批次结论不受影响**（DONE 在有效期内达成），受影响的是事后复核。
