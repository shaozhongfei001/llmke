# HANDOFF.md

当前业务阻断项（P0-01/02/03/04）全部 OPEN。尚无外部独立 QA 签署，本批次不得 DONE。

## 本次已完成（2026-10-21，TL 覆盖施工）

1. 覆盖工具应用成功：`APPLY_OK`；备份目录为**项目根的兄弟目录** `../.llmke-baseline-backups/llmke-20261020T165427Z-bdff8c1b`
   （绝对路径记在该备份目录的 `JOURNAL.json` 内，不写入仓库）
   - 清单：ADD 193 / REPLACE 100 / DELETE 21（共 314 项目，含回执 1）；3 项基线与本地有差异，前像已备份。
   - 旧 `loops/L1-implementation` 退役为 `loops/L1`；旧 L0 证据备份至 `docs/reviews/original-L0-20261020`。
   - 未列入清单的业务文件（如 `apps/`、`modules/`、`frontend/` 占位）保留未动。
2. 合同：`make generate` / `make check` 均 `PASS (18 contracts)`（api×3 / schema×11 / semantic / evidence / evaluation / rules）。
3. `make framework-verify` → **exit 0**（7 个子门禁全绿，pytest `127 passed`）。
4. `make p0-gate` → **exit 2**，四项 P0 全部因 `strict requires CLOSED` 被拒（正确阻断）。
5. LD 启动：`make run-dev LOOP=LD-legacy-discovery EXECUTOR=legacy-owner` → `inventory_gate` pass，STATE revision 2。
6. 负例三组全部按预期拒绝（见 `EVIDENCE.md`）。
7. 506 条接口清单已对生产快照逐条核验：**504/506 存在**（Java 438/440、Python 66/66），
   1 条仅存在于注释（`API-0345 /ai/getRerankModelInfos`，独立复现 P0-01 已知事实），
   1 条行号漂移（`API-0425`）。产物与复跑命令见 `evidence/INTERFACE-INVENTORY-DIFF-V1.0.md`。

## 生产基线认定（2026-10-21 业主决议）

1. 业主确认：**原有生产版本不可获得，现有代码即可获得的全部**（登记于
   `evidence/M01-OBTAINABLE-SNAPSHOT.yaml`）。两份后端归档的 SHA256、分支、commit、提交时间齐全，
   并有 12/12 文件数全等、3/3 抽样路径命中、`git diff -w` 为空三项交叉验证。
2. 业主进一步决议：**认定该可获得快照即「生产版本」，作为 P0 核验与复用判断的参照物**，
   并**明确否定「降低 P0 关闭标准」**。
   依据：`docs/approvals/OWNER-RESOLUTION-2026-10-21-PRODUCTION-BASELINE.md`。
3. 由此：M-01/M-02 可登记（附「业主认定」标签）、M-03 按定义同源（标注非实测）。
4. **仍然缺**（关闭标准未变，缺一不可）：
   - P0-01：运行时路由口径裁定、约 380 条在用判断的调用日志**或调用方确认**、`/retrieval_qa` 书面决议；
   - P0-02：真实 DDL/索引/约束/版本、生产同版本恢复副本上的迁移与回退记录、`create_by` 值域；
   - P0-03/P0-04：M-07（授权政策、M0 题库/签署），与源码无关。
5. `make p0-gate` 仍失败，L1–L4 仍 `BLOCKED`；本决议不构成任何放行。

## 未完成 / 下一步（按可执行顺序）

| # | 动作 | 责任角色 | 前置 |
|---|---|---|---|
| 1 | 索取 M-01…M-07 七项原始材料（`loops/LD-legacy-discovery/MATERIALS-REQUEST-V1.0.md`） | `legacy-owner` → 各资产维护方 | 无 |
| 2 | 12 源码资产逐项 KEEP/ADAPT/REWRITE/RETIRE；保留成熟内部算法，仅在外边界做端口/适配器适配 | `index-owner` / `algorithm-owner` | M-01、M-02、M-03 |
| 3 | 37 表 / 482 字段逐项核对实际 DDL 与索引决策（含 `dialogue` 的 `create_by` 值域） | `data-owner` | M-04、M-06 |
| 4 | 506 条清单逐条对照运行时路由与调用方 | `interface-owner` | M-05 |
| 5 | 外部独立 QA 在固定快照复跑并签署（`qa_payload` → `accept-qa` → `finish`） | `qa-external` | 1–4 |
| 6 | 业务实施批次的武装与推进（L1 需四 P0 全 CLOSED） | `tech-lead` | 5 + P0 关闭 |

## 红线保持

- 未改 `generated/`；未改冻结控制文件（`.gitignore`、`.security-allowlist` 等在 `FROZEN-MANIFEST.json` 内）。
- 未把四项业务 P0 改为 CLOSED，未清空任何 `blocks`，未以 `ACCEPTED_RISK` 换放行。
- 未创建任何提交；本次仅按文件/目录显式入库（未使用 `git add .`）。
- 覆盖回执已移出仓根（副本在备份目录 `receipt.json`），避免个人绝对路径入库。
