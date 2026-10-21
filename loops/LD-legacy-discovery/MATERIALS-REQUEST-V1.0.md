# LD 资料索取清单 V1.0

生成日期：2026-10-21
所属批次：`loops/LD-legacy-discovery`（kind: diagnostic，baton holder: `legacy-owner`）
用途：向真实资产维护方索取**不可变原始材料**，作为 12 源码资产 / 37 表 482 字段 / 506 接口清单
逐项复用决议（KEEP/ADAPT/REWRITE/RETIRE）的输入。

本清单是**索取登记**，不是复用结论。未取得材料前，所有台账保持
`CANDIDATE_UNVERIFIED` / `INVENTORY_UNVERIFIED`，不得标记可直接复用。

## 1. 必取材料（7 项，缺一即对应 P0 保持阻断）

> **2026-10-21 修正（用户确认）**：原有生产版本**不可获得**，现有代码即可获得的全部。
> 因此 M-01/M-02/M-03 的「生产发布」口径**永久不可满足**，已改为「可获得快照 + 局限登记」，
> 事实登记见 `evidence/M01-OBTAINABLE-SNAPSHOT.yaml`。M-04 是否同样不可获得，须由 `data-owner` 书面确认。

| 编号 | 材料 | 交付形式与硬性要求 | 对应 P0 | 索取对象 |
|---|---|---|---|---|
| M-01 | ~~发布源码标签/提交与源码归档~~ → **可获得快照的版本钉定** | 归档 SHA256 + 分支 + 40 位 commit + 提交时间；**必须标注「非生产发布基线」** | P0-01 | 已完成（见 evidence 文件），待 owner 确认口径 |
| M-02 | ~~发布制品摘要~~ → **可获得归档摘要** | 每个归档的 SHA256（已实测：Java `506344a4…24e5`、Python `af008271…a1e`） | P0-01 | 已完成，待 owner 确认口径 |
| M-03 | ~~dev ↔ prod 差异~~ → **不可获得，登记为事实** | 无另一侧可比对；须在 P0-01 关闭决议中显式写明该局限 | P0-01 | 不可获得 |
| M-04 | 实际数据库结构快照 | `SHOW CREATE TABLE`（逐表脱敏）、索引、约束、触发器、字符集/排序规则、引擎与数据库版本 | P0-02 | data-owner（**须书面确认生产库是否可导出**） |
| M-05 | 运行时路由与调用方 | 由运行时导出的 `服务 + 方法 + 原始大小写路径 + handler`，排除被注释代码；逐条标注调用方 | P0-01 / P0-03 | 各服务负责人（**若运行时已不可用，须出具「不可获得」书面说明**） |
| M-06 | `create_by` 身份语义 | 值域、生成方（用户 ID/账号/姓名）、与用户主体的关联关系、历史数据分布 | P0-02 | data-owner / 业务 |
| M-07 | 目标授权政策与 M0 题库/签署 | 授权粒度（文件/目录/KB）、合并与拒绝优先级、FAQ 继承规则、图路替代路径；M0 题库与业务签署人 | P0-03 / P0-04 | security-owner / 业务 |

补充必答：**380 / 435 两个数字如何核算**（`380 + 新增 20 ≠ 435`），以及 `/retrieval_qa`
保留或废弃的书面决议——均属 P0-01 的决策项。

## 2. 台账状态（截至本次施工）

| 台账 | 文件 | 条目 | 已决议 | 状态 |
|---|---|---|---|---|
| 12 源码资产 | `docs/reuse/SOURCE-ASSETS.yaml` | 12 | **0** | 全部 `CANDIDATE_UNVERIFIED`；`baseline.status: NOT_PROVIDED`，`released_commit`/`released_artifact_sha256` 均为 null |
| 37 表 / 482 字段 | `docs/reuse/DATABASE-ASSETS.yaml` | 37（字段合计 482） | **0** | 全部 `CANDIDATE_UNVERIFIED`；`source_schema_strategy: UNDECIDED_SHARED_OR_NEW_DATABASE`，`actual_ddl_sha256` 均为 null |
| 506 接口清单 | `docs/reuse/INTERFACE-ASSETS.yaml` | 506（Java 440 / Python 66） | **0** | 全部 `INVENTORY_UNVERIFIED`；`runtime_evidence` 命中 0 条 |

口径：506 是**清单记录数**，不是运行时可路由能力；在未取得 M-05 之前，
「复用率 / 节省人日」一律不填，也不承诺 90% 或 21 周。

## 3. 逐项决议模板（每项决议必填，缺项不算决议）

- `decision` ∈ `KEEP` / `ADAPT` / `REWRITE` / `RETIRE`（REWRITE、RETIRE 必须写 `decision_reason`）
- `decision_owner_role`（必须是 `docs/roles/ROLE-MATRIX.yaml` 中已注册角色）
- `approved_decision_ref`（受保护环境签署信封路径）
- `characterization_case_ids`（特征回放用例，绑定 `docs/acceptance/CASE-REGISTRY.yaml` 中真实测试文件）
- `contract_ids_and_hashes` / `migration_case_ids`（源码类）；`actual_ddl_sha256`、`migration_script_ref`、
  `new_old_write_owners_ref`、`new_old_compatibility_evidence`、`rollback_evidence`（表类）
- `measured_person_days`（理解 / 边界适配 / 实现 / 回归 / 迁移，三个切片测量后填）

## 4. 与 P0 关闭的关系

- P0-01 关闭需 M-01、M-02、M-03、M-05 与 `/retrieval_qa` 决议。
- P0-02 关闭需 M-04、M-06，且同版本恢复副本上的迁移/回填/回退执行记录。
- P0-03 关闭需 M-07 中的授权政策与六类负例结果。
- P0-04 关闭需 M-07 中的 M0 题库/签署，以及五场景不混代证明。
- 每项关闭必须由对应 owner 与 baseline-owner 在受保护环境批准；
  `ACCEPTED_RISK` 不得清空 `blocks`，也不得通过 strict。

## 5. 生产基线不可获得导致的关闭路径缺口（需 owner 决定）

`P0-CLOSURE.yaml` 现有关闭口径写死了「生产侧输入」，而生产侧已确认不可获得，因此：

| P0 | 缺的是哪个不可获得的输入 | 后果 | 需谁决定 |
|---|---|---|---|
| P0-01 | dev↔prod 差异（M-03）、运行时路由导出与调用日志（M-05） | 按现行口径**永远无法关闭** | `interface-owner` + baseline-owner |
| P0-02 | 生产真实 DDL 快照（M-04）、生产同版本恢复副本迁移记录 | 按现行口径**永远无法关闭** | `data-owner` + baseline-owner |
| P0-03 | 无（授权政策属业务输入，可正常索取） | 可正常推进 | `security-owner` |
| P0-04 | 无（M0 题库/签署属业务输入） | 可正常推进 | `index-owner` |

可选处置（**只能由 owner 选择，TL 不代签**）：

1. **改关闭标准**：把「生产侧证据」改为「可获得快照 + 显式局限声明 + 特征回放」，
   写成新的 P0 决议版本；这等于降低验收强度，必须由 owner 明示同意。
2. **保持 OPEN**：承认 P0-01/P0-02 永久 OPEN，则 L1–L4 永久 BLOCKED（技术基线仍可用）。
3. **单独立项**：把「生产侧不可获得」作为一批新的风险接受（`ACCEPTED_RISK`），
   但按 `P0-POLICY` 与门禁实现，接受风险**不能**通过 strict、也不得清空 `blocks`，
   因此**不会**解锁 L1–L4。

## 5.1 实际处置（2026-10-21 业主决定）

业主选择**第 4 种：认定当前可获得源码快照即「生产版本」**，并**明确否定第 1 种（不降低关闭标准）**。
依据：`docs/approvals/OWNER-RESOLUTION-2026-10-21-PRODUCTION-BASELINE.md`。

- **解决**：M-01/M-02 可登记；M-03 按定义同源（须标注「由认定得出，非实测」）。
- **不解决**：P0-01 的运行时路由口径/调用方确认/`/retrieval_qa` 决议；P0-02 的真实 DDL 与恢复副本。
- **不产生效果**：`make p0-gate` 仍失败，L1–L4 仍 BLOCKED，复用决议仍需签名信封。

下一步并行推进：P0-01 侧做「506 条清单 vs 生产快照静态路由」差异报告（只读）；
P0-02 侧向 `data-owner` 确认数据库能否导出 DDL；P0-03/P0-04 按原计划索取 M-07。
