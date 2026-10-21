# TL 首次回执 V1.0（LLMKE V1.1.0 覆盖补丁施工）

- 日期：2026-10-21
- 执行身份：Tech Lead（本仓 `loops/*/STATE.json` 的 baton holder 见第 6 节）
- 依据：`00_覆盖与TL执行说明.md` 第 6 节 10 项
- 结论口径：**本补丁只冻结技术合同与执行规则，不等于业务交付。**

---

## 1. 覆盖与备份结果

| 项 | 值 |
|---|---|
| patch_id | `LLMKE-BL-1.1.0-20261020` |
| PATCH-MANIFEST SHA256 | `a02dae35e8fe2cda14c868e639b02bbea4b335b79829db272c21399b20771820` |
| 清单操作 | ADD 193 / REPLACE 100 / DELETE 21（含回执 1 项，共 315 条 action） |
| 基线差异前像已备份 | 3 项：`00-评审导读.md`、`BUILD-INFO.txt`、`MANIFEST.sha256` |
| 备份目录 | 项目根兄弟目录：`../.llmke-baseline-backups/llmke-20261020T165427Z-bdff8c1b` |
| 结果 | `APPLY_OK`；工具已逐文件校验 SHA256，并对每个替换/删除项保存实际覆盖前内容 |
| 退役处理 | `loops/L1-implementation/**` 文件已删除（仅残留空目录，git 不跟踪）；旧 L0 证据另存 `docs/reviews/original-L0-20261020` |
| 无关业务文件 | `apps/`、`modules/`、`services/`、`lib/`、`frontend/` 未在清单内，原样保留 |

## 2. 当前基线摘要

| 项 | 值 |
|---|---|
| `VERSION` | 1.1.0 |
| 合同总数 | **18**（`api`×3 / `schema`×11 / `semantic`×1 / `evidence`×1 / `evaluation`×1 / `rules`×1），全部登记于 `contracts/registry.yaml` |
| 角色 | 12（`docs/roles/ROLE-MATRIX.yaml`） |
| 活动批次 | 6（`L0-contract-baseline`、`LD-legacy-discovery`、`L1`、`L2`、`L3`、`L4`；`_template` 不计） |
| CodeBuddy 规则 | 13（`.codebuddy/rules/**`，原 `backend-local` / `loop-shared-memory` / `p0-closure-gate` 已退役） |
| 基线指纹 `baseline_sha256` | `d40281d8cc30326d6f8000d222f7c29f9d02cb61d0ac950a44c9fdc30f963e47` |
| 源码快照 `source_snapshot_sha256` | `daf1260ff0d3d7a300e51a4edf09e15669d9cba46bc4e89c31cef01a8f272566` |

## 3. 实际测试结果（本环境实跑，非包内历史）

| 命令 | 退出码 | 输出 |
|---|---|---|
| `make framework-verify` | **0** | `generate: PASS (18 contracts)`；`check: PASS (18 contracts, semantic + exact linkage)`；`rule-mirror: PASS`；`trace-check: PASS`；`p0-check: PASS (integrity)`；`security-check: PASS (364 file(s) scanned)`；`127 passed`；`baseline: PASS` |
| `make p0-gate` | **2** | 四项 P0 全部 `strict requires CLOSED; OPEN/ACCEPTED_RISK is not closure`（**正确阻断**） |
| `make run-dev LOOP=LD-legacy-discovery EXECUTOR=legacy-owner` | 0 | `pass: inventory_gate`；STATE revision 1→2 |
| `make discovery-verify` | 0 | `reuse-check: PASS inventory` / `p0-check: PASS (integrity)` / `trace-check: PASS` |
| `make memory-check LOOP=LD-legacy-discovery` | 0 | PASS |

三类状态分开报告：

- **合成/框架测试（本包自带）**：127 passed，0 skipped。
- **开发自检（DEV_SELF_CHECK）**：LD `inventory_gate` pass（revision 2）。
- **独立 QA**：**PENDING / NOT_RUN**——无受保护环境外部签名，开发身份不得自签；
  因此 `L0` 与 `LD` 都不能 DONE（已用 `finish` 负例验证门禁拒绝）。

施工期发现与处理见 `loops/LD-legacy-discovery/FAILURES.md`
（FAIL-2026-10-21-01/02/03）。

## 4. LD 资料清单与三本台账状态

索取清单：`loops/LD-legacy-discovery/MATERIALS-REQUEST-V1.0.md`（M-01…M-07）。

| 台账 | 条目 | 已决议 | 状态 |
|---|---|---|---|
| `docs/reuse/SOURCE-ASSETS.yaml`（12 源码资产） | 12 | **0** | 全部 `CANDIDATE_UNVERIFIED`；`baseline.status: NOT_PROVIDED`，`released_commit` / `released_artifact_sha256` 均为 null |
| `docs/reuse/DATABASE-ASSETS.yaml`（37 表 / 482 字段） | 37（字段合计 482，与盘点一致） | **0** | 全部 `CANDIDATE_UNVERIFIED`；`source_schema_strategy: UNDECIDED_SHARED_OR_NEW_DATABASE`；`actual_ddl_sha256` 均为 null |
| `docs/reuse/INTERFACE-ASSETS.yaml`（506 接口清单） | 506（Java 440 / Python 66） | **0** | 全部 `INVENTORY_UNVERIFIED`；`runtime_evidence` 命中 **0** 条 |

口径：506 为清单记录数，不等于运行时可路由能力；在 M-05 未取得前不填复用率与节省人日，
不承诺 90% 或 21 周。

## 5. 四项业务 P0 状态

| 编号 | owner | status | evidence | blocks |
|---|---|---|---|---|
| P0-01 接口基线不能作为机器执行唯一事实源 | `interface-owner` | **OPEN** | 空 | L1, L3 |
| P0-02 数据库方案存在按文施工即失败项 | `data-owner` | **OPEN** | 空 | L1, L2, L3 |
| P0-03 业务裁决权 ≠ 算法侧可不执行授权范围 | `security-owner` | **OPEN** | 空 | L1, L3, L4 |
| P0-04 新建索引+灰度+切回尚非一致性/回滚协议 | `index-owner` | **OPEN** | 空 | L1, L2, L3, L4 |

`make p0-gate` 以退出码 2 拒绝，与登记表一致。关闭路径：逐项 D01… 回答 + 真实非空哈希证据 +
当前快照 + 对应 owner 与 `baseline-owner` 在受保护环境批准；`ACCEPTED_RISK` 不得清空 `blocks`，也不得通过 strict。
发布源码与实际 DDL 未提供 → 保持阻断并已在索取清单列明缺什么。

## 6. 批次状态与 baton

| Loop | revision | status | holder | attempts |
|---|---|---|---|---|
| `L0-contract-baseline` | 15 | IN_DEV | `integration-agent` | 7 门禁各 2（包内已跑开发自检，本次未重复消耗预算） |
| `LD-legacy-discovery` | 2 | READY | `legacy-owner` | `inventory_gate`: 1 |
| `L1` | 1 | BLOCKED | `tech-lead` | — |
| `L2` | 1 | BLOCKED | `tech-lead` | — |
| `L3` | 1 | BLOCKED | `tech-lead` | — |
| `L4` | 1 | BLOCKED | `tech-lead` | — |

负例：`arm --loop L1` 被拒（P0 未关闭）；`finish --loop L0-*` 被拒（无独立 QA）；
`run-gate --executor tech-lead`（非 holder）被拒。

## 7. 下一项可执行工作

1. 向资产维护方发出 `loops/LD-legacy-discovery/MATERIALS-REQUEST-V1.0.md` 的 M-01…M-07 索取（阻断所有业务批次的前置）。
2. 取得 M-01/M-02/M-03 后，12 项源码资产逐项 KEEP/ADAPT/REWRITE/RETIRE，保留内部算法、仅在外边界做端口/适配器适配。
3. 取得 M-04/M-06 后，37 表 / 482 字段逐项核对实际 DDL 与索引（含 `dialogue.create_by` 值域）。
4. 取得 M-05 后，506 条清单逐条对照运行时路由与调用方。
5. 外部独立 QA 固定快照复跑 → `qa_payload` → 独立签署 → `accept-qa` → `finish`。

待人工/授权事项（不自行代签或放行）：首次提交授权；`requirements.lock` 去重修订（baseline-owner）；
四项 P0 的 owner 与 baseline-owner 批准；外部 QA 信任配置与签名。
