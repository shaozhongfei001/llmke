# HANDOFF.md

当前业务阻断项（P0-01/02/03/04）全部 OPEN。尚无外部独立 QA 签署，本批次不得 DONE。

## 本批次定位

替代已耗尽预算的旧批次，在同一组门禁定义下于当前快照重跑，**不放宽任何 pass 条件**。
门禁结果见 `EVIDENCE.md`；开发自检已全部通过，独立 QA 门禁未运行。

## 下一步

| # | 动作 | 责任角色 | 前置 |
|---|---|---|---|
| 1 | 外部独立 QA 在固定快照复跑并签署（`qa_payload` → 独立签名 → `accept-qa` → `finish`） | `qa-external` | 受保护环境 + 信任根配置 |
| 2 | P0-01/02 的材料索取与裁定（见 `loops/LD-legacy-discovery/MATERIALS-REQUEST-V1.0.md`） | 各 owner | 业务侧输入 |
| 3 | 解析方案落地（PDF/OCR 引用 doc2md 独立组件、DOCX 暂不引用） | `tech-lead` | owner 确认 DOCX 取舍 |

## 红线

- 未改 `generated/`；未用白名单掩盖任何命中。
- 未把四项 P0 改为 CLOSED，未清空 `blocks`。
- 未创建提交；仅按文件显式入库。
- 门禁运行必须导出 `MAKEFLAGS=--no-print-directory`，否则证据日志会再次写入宿主绝对路径。

## 终态与限制（2026-10-21 业主决定：接受 B）

| 门禁 | 状态 |
|---|---|
| `contract_generate_gate` | pass |
| `contract_check_gate` | pass |
| `mutation_probe_gate` | pass（13/13） |
| `traceability_gate` | pass |
| `p0_register_gate` | pass（integrity） |
| `security_scan_gate` | pass（426 文件） |
| `baseline_gate` | pass |
| `independent_qa_gate` | **fail（attempts 3/3 耗尽，未通过）** |

### 为什么接受这个状态
1. 该门禁的 argv 是 `make framework-verify`，其覆盖的 8 项检查**已被上面 7 条门禁逐项跑过并全部 pass**，
   所以"技术基线可信"这一结论没有实质缺口；缺的只是**第三方独立背书**。
2. 修复它需要在当前快照上重跑该门禁——但预算已耗尽，按框架规定不得手工重置 attempts。
3. 另开替代批次需要重写 `FROZEN-MANIFEST.json`，而这会同时改变 `baseline_sha256` 与源码快照，
   使**已签并 DONE 的 `LD-legacy-discovery-r2` 的独立 QA 立即失效**（其状态为 DONE，无法重跑）。
   用一个已生效的签名去换另一个签名，净亏。

### 因此本批次不得声称
- 不得声称"合同基线已获独立 QA 签署"；
- 不得据此关闭任何 P0（四项仍 OPEN，`make p0-gate` exit 2）；
- 不得据此解锁 L1–L4（仍 BLOCKED）。

### 恢复时机
当确实需要新增批次（如 L1 切片）时，**一次性**建齐所有批次 → 重冻结一次 → 统一重跑并重签
（届时 `LD-legacy-discovery-r2` 也需随之重签）。不要为单个门禁反复改冻结基线。

---

## 执行轮检查点（2026-10-21，TL 长程执行）

### 状态快照
| 项 | 值 |
|---|---|
| branch / HEAD | `main` / `306f2b3`（本次新建 2 个提交；此前仓库零提交） |
| 工作树 | 干净（仅交付源 zip 未跟踪，刻意不入库） |
| 基线标识 | 版本号仍 `1.1.0`（本地增量未递增，见提案 P-05）；`baseline_sha256=c8a73c37…`、`source_snapshot=d0530bee…` |
| 本批次 | `QA_PENDING`，rev 13，baton `integration-agent` |
| attempts | 7 条开发门禁各 1/3；`independent_qa_gate` **3/3（耗尽）** |
| 另一批次 | `LD-legacy-discovery-r2` = `DONE`，rev 8，QA 由 `qa-owner-01` 签署（已过 1 小时复核窗口） |

### 本轮已完成的工作项
| # | work item | 结果 | 证据 |
|---|---|---|---|
| W1 | staged 审查 + 凭据扫描 + 建立可恢复提交点 | 拆 2 个提交：`7a03b5c`（基线可运行）、`306f2b3`（治理文档）；无凭据、无缓存、无跨仓内容 | `git log`；`security-check` PASS(430) |
| W2 | R-02 运行确定性 | 洁净环境（清 `MAKEFLAGS`/`PYTHONPATH`）复跑 `framework-verify` = **exit 0 / 127 passed**，与带环境变量时一致；确认默认 shell 的 `python3` 是 3.10.12 且 IDE 注入了 `PYTHONPATH` | `/tmp/fw-clean.log`（临时） |
| W3 | R-03 前置检测（不改冻结脚本） | 新增 `coordination/preflight.py`：解释器校验 + 证据日志宿主路径预检 + doc2md 冻结指纹校验；错解释器时 FAIL 并给出正确入口 | 运行输出（PASS/FAIL 双例已验证） |
| W5 | llmke-ir 映射契约测试（SYNTHETIC） | `spike/ir_mapping_check.py`：7 用例（2 正例 + 5 反例）**7/7 passed**；变异测试（取消 `merge_detected` 硬编码 false）→ N-5 正确 FAIL（6/7），证明断言非空转 | 脚本自输出 + `/tmp/ir_mut.py` 变异记录 |
| W4 | 六项框架缺陷提案 | `docs/baseline/validation/FRAMEWORK-DEFECT-PROPOSALS-V1.0.md`（P-01…P-06，含影响面、旧 QA 失效面、验证正反例、实施顺序） | 该文件 |

### 未改的东西（红线）
- 未改任何冻结控制文件（`scripts/**`、`docs/policies/**`、`VERSION`、`PROJECT-PLAN.yaml`、`FROZEN-MANIFEST.json`）；
- 未重置 attempts、未改 STATE/证据状态、未伪造签名；
- P0-01…04 仍全部 OPEN，`make p0-gate` 仍 exit 2；L1–L4 仍 BLOCKED。

### READY / BLOCKED
| 项 | 状态 | 解封条件 |
|---|---|---|
| P-01、P-06 | READY（提案已备） | `baseline-owner` 批准（改冻结面） |
| P-02、P-03 | READY（提案已备） | 同上；P-02 需 `qa-owner` 参与定语义 |
| P-04、P-05 | READY（提案已备） | 与一次重冻结合并 |
| L0-r2 独立 QA | BLOCKED | 预算 3/3 耗尽；需新批次（另需一次重冻结） |
| P0-01/P0-02 | BLOCKED | 生产侧运行时证据 / 真实 DDL 与恢复副本（外部） |
| P0-03/P0-04 | BLOCKED | E1–E8 / S1–S5 需可运行检索链与真实存储 |
| 12 资产 / 37 表 / 506 接口 决议 | BLOCKED | 需 owner 逐项批准；无证据项保持 UNVERIFIED |

### 下一条精确命令
```bash
cd ~/data/dev/llmke
export LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
~/data/dev/coordination/qa-run.sh memory-check --loop L0-contract-baseline-r2
make framework-verify && make p0-gate   # 预期：前者 exit 0，后者 exit 2
```
执行角色：`tech-lead`（只读复核）；任何门禁重跑需先获 `baseline-owner` 对新批次/提案的批准。
