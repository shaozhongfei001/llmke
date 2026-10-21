# 受控变更窗口任务账本（v1.1.1）

- 分支：`fix-window/v1.1.1`（自 `main@4b1fca8` 开出；`main` 保持不动，历史证据不受影响）
- 授权：业主批准「六项框架缺陷提案进入受控变更窗口」，优先 P-01/P-02/P-03/P-06
- 纪律：实施不得削弱门禁、不得覆盖历史证据、改冻结面必须带版本+影响面+迁移/回退+正反向验收
- 更新规则：每完成一个切片立刻更新本表「状态」列与 `## 检查点`，再提交

## 1. 任务表

| ID | 目标 | 依赖 | 改动范围 | 角色 | 验收命令 | 证据位置 | 状态 | 阻塞原因 |
|---|---|---|---|---|---|---|---|---|
| T-01 | P-01：证据日志不参与「个人绝对路径」判定，但凭据/私钥/连接串仍判定；输出跳过计数 | 无 | `scripts/security_scan.py`、`tests/test_security_scan.py` | tech-lead | `pytest tests/test_security_scan.py -q` + 正反例 | 同左 | **DONE**（13 passed） | — |
| T-02 | P-03：摘要拆 `control_digest` / `doc_digest`，STALE 判定用 control；`traceability_gate` 额外比 doc；旧记录按 `digest_scheme: legacy` 兼容 | T-01 | `scripts/baseline_support.py`、`scripts/loop_guard.py`、新增 `tests/test_digest_scope.py` | tech-lead | `pytest tests/test_digest_scope.py -q` | 同左 | **DONE**（6 passed；实仓端到端见结果文档 §3.1） | — |
| T-03 | P-06：新增 `SUPERSEDED`/`RETIRED` 终态；拒绝执行门禁与 `finish`；终态不参与 STALE 判定；`replaced_by`/`terminal_reason` 可选字段 | T-02 | `scripts/loop_guard.py`、新增 `tests/test_terminal_states.py` | tech-lead | `pytest tests/test_terminal_states.py -q` | 同左 | **DONE**（5 passed；实仓 r3 已置终态并 PASS） | — |
| T-04 | P-04：冻结元数据改由 `docs/baseline/BASELINE-AUTHORITY.yaml` 提供；缺失则拒绝写入；写入 `frozen_at` 与自增 `manifest_revision` | 无 | `scripts/freeze_baseline.py`、新增 `docs/baseline/BASELINE-AUTHORITY.yaml`、新增 `tests/test_freeze_authority.py` | tech-lead | `pytest tests/test_freeze_authority.py -q` | 同左 | **DONE**（5 passed；manifest_revision=2） | — |
| T-05 | P-05：`VERSION` 升 `1.1.1`、`BUILD-INFO.txt` 增「本地增量」段；`freeze_baseline` 版本改为读 `VERSION` | T-04 | `VERSION`、`BUILD-INFO.txt`、`scripts/freeze_baseline.py` | tech-lead | `make baseline-check` | 同左 | **DONE**（PASS） | — |
| T-06 | 窗口收口：唯一一次重冻结 + 全量 `framework-verify` + 新批次重跑门禁 | T-01…T-05 | `docs/baseline/FROZEN-MANIFEST.json`、`loops/L0-contract-baseline-r{3,4}` | tech-lead | `coordination/mk.sh framework-verify` | `docs/baseline/validation/FIX-WINDOW-V1.1.1-RESULT.md` | **DONE（仅分支，未合并）** | 合并需先做结果文档 §6 五步 |
| T-07 | P-02：QA 签名「接受时校验有效期、复核时不校验有效期」，新增 `accepted_at`/`accepted_by`/`revoked_key_ids` | 需 `qa-owner` 确认语义 | `scripts/baseline_support.py`、`scripts/loop_guard.py` | qa-owner + tech-lead | 正例+反例（撤销密钥必须失败） | 同左 | **BLOCKED** | 语义变更涉签名有效性，须 `qa-owner` 书面确认；且会使历史 QA 记录需回填 `accepted_at` |
| T-08 | 锁文件可复现：`requirements.lock` 去重冲突 pin、剥离与框架无关的重型包 | 需 `baseline-owner` 批准（冻结面） | `requirements.lock` | baseline-owner | 洁净容器 `pip install -r` 成功 | `docs/baseline/validation/` | **BLOCKED** | 属冻结面且改变依赖基线，须 owner 批准；本轮只出提案 |
| T-09 | PDF 解析等价性验证（doc2md 路线，禁止静默切 pdfplumber） | 需 doc2md 可运行 + 样本 | `loops/LD-legacy-discovery/spike/` | tech-lead | 两臂实际路径+指纹+断言非空 | spike 报告 | BLOCKED | 待 T-06 收口后启动；PDF 需版面模型可用性确认 |
| T-10 | 37 表/482 字段 DO 对照（P0-02 打底） | M-04 DDL（外部） | `loops/LD-legacy-discovery/` | data-owner + tech-lead | 逐表对照表 | 同左 | BLOCKED | 真实 DDL 不可得；仅能出 `CANDIDATE` |
| T-11 | P0-01 逐端点决议表（504 条） | 调用方在用确认（外部） | `docs/reuse/`（冻结面） | interface-owner | 504 行决议 + 签名 | 同左 | BLOCKED | 「在用」判断需调用日志或调用方确认 |

## 2. 阻塞包（缺什么/谁提供/什么格式/阻塞谁/可先做什么）

| 编号 | 缺什么 | 由谁提供 | 格式要求 | 阻塞任务 | 可先做 |
|---|---|---|---|---|---|
| B-01 | 运行时路由导出或调用方确认 | `interface-owner` + 各服务负责人 | 服务+方法+原始大小写路径+handler，逐条标注调用方 | T-11、P0-01 | 静态抽取已完成（504/506） |
| B-02 | 真实 DDL / 索引 / 约束 / 版本 | `data-owner` | 逐表 `SHOW CREATE TABLE`（脱敏） | T-10、P0-02 | DO 实体对照可先做，结论标 CANDIDATE |
| B-03 | `create_by` 身份语义 | `data-owner` / 业务 | 值域+生成方+与用户主体关系+历史分布 | P0-02 | 无 |
| B-04 | E1 授权上下文规范 + E2–E7 六类负例可复跑 | `security-owner` | 规范文档 + 可执行负例 | P0-03 关闭 | E1/E8 可先写（不需运行环境） |
| B-05 | S1–S5 五场景 + 双代余量实测 | `index-owner` | 可复跑脚本 + 实测数字 | P0-04 关闭 | 模拟验证可先行，须标「模拟」 |
| B-06 | `qa-owner` 对 P-02 语义确认 | `qa-owner` | 书面确认 | T-07 | 提案已完成 |
| B-07 | `baseline-owner` 对锁文件与重冻结批准 | `baseline-owner` | 书面批准 | T-06、T-08 | 提案与影响面已备 |

## 3. 检查点

（每轮追加；格式：时间 / HEAD / 已完成 / 验证结果 / 下一条命令）

### CP-01 2026-10-21 开窗

- HEAD：`4b1fca8`（`policy: 建窗口分支` 前）
- 已完成：状态复核（snapshot `d0530bee`、baseline `c8a73c37`、控制面 198 文件、authority 仍为硬编码旧文案）、开分支、本账本
- 验证：`git branch --show-current` = `fix-window/v1.1.1`
- 下一条命令：实现 T-01，然后 `pytest tests/test_security_scan.py -q`

### CP-02 2026-10-21 窗口代码完成（T-01…T-06）

- HEAD：`fix-window/v1.1.1`（本检查点提交）
- 已完成：P-01/P-03/P-04/P-05/P-06 全部落地；18 条新测试；重冻结两次（第二次为收口，revision=2）
- 验证：`pytest tests/ -q` → **145 passed**；`make framework-verify` → **exit 0**；`make p0-gate` → **exit 2**
- 实仓证据：`L0-contract-baseline-r4` 7 条开发门禁全 pass + `evidence-check` PASS；
  `r3` 因「门禁执行中间重冻结」被置 `SUPERSEDED` 且 `evidence-check` PASS（P-06 实证）
- P-03 实证：加一份 `docs/**` 文档 → 仅 `traceability_gate` STALE（旧行为是 7 条全废）
- **教训（已固化）**：重冻结必须一次性收口；在批次门禁执行中间重冻结会卡死该批次
- 下一条命令：`git checkout main`（保持主线）或按结果文档 §6 决定合并顺序；
  当前不合并，因合并需先建齐批次 + 唯一一次冻结 + 外部 QA 重签

### CP-03 2026-10-21 对抗验证（证明未削弱门禁）

| 对抗动作 | 期望 | 实测 |
|---|---|---|
| 往 `contracts/` 加一个文件（控制面变化） | 全部记录 STALE | **7/7 STALE** + `frozen control file set changed` |
| 往某条证据日志追加一行（篡改） | 哈希不匹配 | `baseline_gate: evidence hash mismatch` |
| 复原两项后 | 证据重新有效 | `evidence-check: PASS` |
| `make p0-gate` | exit 2 | **exit 2** |

结论：本次放宽仅限「说明性文档是否算候选输入」与「机器生成的证据日志中的宿主路径」，
控制面与凭据类判定未放宽。已提交 `75e7267`（分支 `fix-window/v1.1.1`）。
