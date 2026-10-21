# 基线现状评审包 V1.0（供外部评审）

> **用途**：把当前项目基线的事实、已做决策、已知缺陷、未完成项一次性交出去，供外部评审者判断
> 「这套基线与执行方式是否可继续」，并据此**重写项目启动提示词**。
> 本文件自包含，读者无需其他上下文。位置：`docs/baseline/validation/`（不参与源码快照）。

---

## 0. 请评审者做什么

1. 判断当前基线是否**可以作为后续实施的起点**（是/否/有条件）；
2. 指出**执行方式上的系统性缺陷**（不是逐条挑错，而是找会反复发生的模式）；
3. 给出**新的项目启动提示词**（供 AI 编码代理在每次开工时读取）。

请特别关注 §8 的缺陷清单与 §10 的问题清单。

---

## 1. 项目与目标

- 项目：LLMKE（银行知识工程与检索增强平台重构）。
- 目标：把旧 RAG 平台（Java + Python 多服务）重构为新平台，**功能等价**（不是"抽几个模块复用"）。
- 硬约束：合同优先（`contracts/registry.yaml` 为唯一注册入口）、`generated/` 只读、
  门禁必须是可执行命令、开发自检与独立 QA 分离、凭据与个人绝对路径不入库。
- 业务侧现状：**四项 P0 阻断项全部 OPEN**，业务实施批次（L1–L4）全部 BLOCKED。

## 2. 当前基线的事实

| 项 | 值 |
|---|---|
| 技术基线版本标识 | `1.1.0`（`VERSION` / `BUILD-INFO.txt` / `FROZEN-MANIFEST.baseline_version`） |
| 实际内容 | **V1.1.0 + 本地增量，版本号未递增**（见 §3） |
| 合同数 | **18**（api×3 / schema×11 / semantic / evidence / evaluation / rules） |
| 冻结控制文件数 | **198**（补丁原始 196） |
| 源码快照 `source_snapshot_sha256` | `d0530bee289b8bfdf369762bb07a1e0cf8f9ba457c3b10ccf68b0e4b7353689c` |
| 冻结基线 `baseline_sha256` | `c8a73c3736dba301c8771cf7f09a575adcaf8be64763e55da04e746376cece04` |
| 批次目录（含 LOOP.yaml） | **8**：`L0-contract-baseline`、`L0-contract-baseline-r2`、`LD-legacy-discovery`、`LD-legacy-discovery-r2`、`L1`–`L4` |
| 运行环境 | Python 3.12 独立 venv（仅框架依赖）；**无** MySQL/ES/Milvus/Neo4j/LLM 服务 |
| **版本库状态** | **`main` 分支零提交**，400 个文件全部为 staged，未产生任何 commit |

> 最后一条是本次评审必须关注的问题之一（见 §8 R-01）。

## 3. 本次（2026-10-21）做了什么

按时间顺序，共 7 个主题：

### 3.1 应用技术基线覆盖补丁
- 补丁：`LLMKE 业务实施冻结基线覆盖补丁 V1.1.0`（`patch_id=LLMKE-BL-1.1.0-20261020`）。
- 清单：ADD 193 / REPLACE 100 / DELETE 21；旧 L1-implementation 退役为 L1；旧 L0 证据归档 `docs/reviews/original-L0-20261020`。
- 结果：`APPLY_OK`，逐文件 SHA256 校验，替换/删除项均留前像备份。

### 3.2 恢复门禁可运行性
- `framework-verify` 从红到绿（exit 0，127 passed）。
- 修复两类环境缺陷（见 §8 R-02、R-03），建立统一入口 `coordination/{qa-run.sh,run-dev.sh}`。

### 3.3 旧源码核实（LD 批次）
- 定位到可获得源码：Java 后端 `gien-rag`（branch `prod`，commit `2b363e6a…`）、
  Python 后端 `rag-alg-service-api`（branch `dev`，commit `7299b288…`），均有归档 SHA256。
- 交叉验证：12 项资产的申报文件数与实测主语言文件数 **12/12 全等**；506 条接口清单抽样 3/3 命中源文件路径。
- **业主认定**：以该可获得快照作为「生产版本」参照物（并明确否定"降低 P0 关闭标准"）。

### 3.4 506 条接口清单逐条核验
- 工具：`loops/LD-legacy-discovery/tools/verify_interface_inventory.py`（只读，按"方法+拼接后完整路径"建路由表）。
- 结果：**504/506 存在于源码**（Java 438/440、Python 66/66）；
  **1 条仅存在于注释**（`GET /ai/getRerankModelInfos`，独立复现 P0-01 已登记事实）；
  **1 条行号漂移 11 行**；0 条文件缺失。

### 3.5 CODE-01（解析模块）解耦可行性回放
- 把 `deepdoc` 对服务层的 4 类耦合（配置/模型引用/进度上报/运行时工具）改写为端口：
  **25 处 import、14 个文件**。
- 结果：**5/5 样本解析结果逐字段一致**（txt / html / 纯文本 docx / 两份真实 docx，块数 4/1/6/95/71）。
- 同时暴露三条硬约束（见 §8 R-04）。

### 3.6 解析方案选型（PDF / DOCX / OCR）
- 对比对象：旧 `deepdoc` vs 外部独立项目 `doc2md`（规格驱动，22 个测试文件）。
- 实测（6 份自建样本）：数字版 PDF 677 字符 → `PDF_DIGITAL`；扫描版 0 字符 → `PDF_SCANNED_OR_IMAGE`；
  加密件 → `ENCRYPTED`，**不尝试口令**；OCR 引擎路由 48 种组合 → 5 种结果，**无静默成功**；
  **DOCX 路径 `table_count=0`、`figure_count=0`（表格与图片丢失）**。
- 决策：**D3 分治**——PDF/OCR 引用 `doc2md`（独立组件、子进程调用），DOCX 走 `deepdoc` 适配器。

### 3.7 工作区迁移 + P0 政策裁决
- `doc2md` 平移到与 llmke **同级目录**（仍是两个独立 git 仓），建立 `coordination/`（边界声明 B-1…B-5、
  冻结锁、探针样本、统一门禁入口），doc2md 迁移后 014 基线测试 61 passed 未退化。
- P0-03/P0-04 政策裁决：**业主全部采纳建议**（文件级叶子授权、deny 优先、FAQ 继承来源约束、
  图路整 KB 授权才开放；不可变 generation manifest、单原子激活指针、fencing token）。
  **但这两项 P0 仍未关闭**（缺 E1–E8 / S1–S5 证据）。

## 4. 门禁与 QA 现状

| 批次 | 开发门禁 | 独立 QA | 状态 |
|---|---|---|---|
| `L0-contract-baseline` | 曾 pass（旧快照） | 未做 | **superseded**（预算耗尽，证据 STALE，保留失败记录） |
| `LD-legacy-discovery` | 曾 pass | 未做 | **superseded**（同上） |
| `L0-contract-baseline-r2` | **7/7 pass** | **fail（attempts 3/3 耗尽）** | 未 DONE |
| `LD-legacy-discovery-r2` | 1/1 pass | **pass（`VERIFIED_QA`，签名主体 `qa-owner-01`）** | **DONE** |

框架级命令现状：`make framework-verify` = **exit 0 / 127 passed**；`make trace-check` PASS；
`make security-check` PASS；`make baseline-check` PASS；**`make p0-gate` = exit 2（正确阻断）**。

## 5. 四项 P0 现状

| P0 | 主题 | 状态 | 缺什么 |
|---|---|---|---|
| P0-01 | 接口基线不能作为唯一事实源 | **OPEN** | 运行时路由导出、约 380 条"在用"判断的调用日志**或调用方确认**、`/retrieval_qa` 书面决议 |
| P0-02 | 数据库方案按文施工会失败 | **OPEN** | 真实 DDL/索引/约束/版本、生产同版本恢复副本上的迁移与回退记录、`create_by` 值域 |
| P0-03 | 业务裁决权 ≠ 算法侧不执行授权范围 | **OPEN**（政策已裁） | E1 授权上下文规范 + E2–E7 六类负例 + E8 检查对象声明 |
| P0-04 | 新建索引+灰度+切回非一致性协议 | **OPEN**（政策已裁） | S1–S5 五场景 + R1 双代余量实测 + R2 历史引用不断链 |

## 6. 三本资产台账

| 台账 | 条目 | 已决议 | 备注 |
|---|---|---|---|
| `SOURCE-ASSETS.yaml` | 12 | **0** | 全部 `CANDIDATE_UNVERIFIED`，`decision: null` |
| `DATABASE-ASSETS.yaml` | 37 表 / 482 字段 | **0** | `source_schema_strategy: UNDECIDED`，`actual_ddl_sha256: null` |
| `INTERFACE-ASSETS.yaml` | 506（Java 440 / Python 66） | **0** | 全部 `INVENTORY_UNVERIFIED`；静态核验 504/506 存在 |

## 7. 已形成的技术决策（可直接继承）

| 编号 | 决策 | 依据文档 |
|---|---|---|
| J-1 | 生产基线 = 可获得源码快照（业主认定），但不降低 P0 关闭标准 | `docs/approvals/OWNER-RESOLUTION-2026-10-21-PRODUCTION-BASELINE.md` |
| J-2 | PDF/OCR 引用 `doc2md` 独立组件；DOCX 走 `deepdoc` 适配器（D3 分治） | `loops/LD-legacy-discovery/DOCX-ROUTE-DECISION-V1.0.md` |
| J-3 | LLMKE 自有统一 IR `llmke-ir/1.0`，与 doc2md IR 字段无损对齐 | `loops/LD-legacy-discovery/UNIFIED-IR-DRAFT-V1.0.md`（草案，未注册为合同） |
| J-4 | 两项目同工作区、异仓库；doc2md 对 llmke 角色只读；5 条边界约束 | `docs/integration/DOC2MD-WORKSPACE-DECISION.md` |
| J-5 | P0-03/P0-04 政策口径（见 §3.7） | `docs/approvals/DRAFT-P0-0{3,4}-RESOLUTION-V1.0.md` |
| J-6 | 门禁一律通过 `coordination/qa-run.sh` / `run-dev.sh` 执行 | `docs/baseline/validation/WORKSPACE-MIGRATION-RECORD-V1.0.md` |

## 8. 已知缺陷与风险（请重点评审）

| 编号 | 问题 | 性质 | 当前处置 |
|---|---|---|---|
| **R-01** | **版本库零提交**：main 无任何 commit，400 文件全 staged | 工程纪律 | **未处置**。所有"证据链/审计"都建立在未提交的工作树上 |
| R-02 | 门禁解释器不固定：`make` 内部 `python3` 取自 PATH，调用方未激活 venv 时缺依赖（实测 `openapi_spec_validator` 缺失） | 环境 | 用包装器固定 PATH |
| R-03 | **证据日志自引用**：门禁运行期间磁盘上是上一次日志；若上次是失败 traceback（含宿主绝对路径），安全扫描命中它 → 本次失败又把命中写回同一文件 → 永久污染 | 框架缺陷 | 移出污染日志 + 包装器（治标） |
| **R-04** | `deepdoc` 三条硬约束：`parser/__init__` 全量导入导致原包**导入即失败**；docx 导入期需 21 个重型依赖；**OCR 在构造期就加载 ONNX 模型** | 依赖设计 | 已在 spike 中验证可解，未落地到正式模块 |
| R-05 | **QA 签名载荷只有 1 小时有效期**，而 `evidence-check` 对已接受记录会重新验签并检查窗口 → 1 小时后复核报 `invalid approval validity window` | 框架缺陷 | 已登记，等批次窗口修 |
| R-06 | **重冻结基线会让已签 QA 失效**：`FROZEN-MANIFEST` 在源码快照内，改它即改 `baseline_sha256` 与快照 | 设计后果 | 采用"批量合并到窗口"策略 |
| R-07 | `freeze_baseline.py` 把 `authority` 文本硬编码，重冻结后元数据仍是旧文案 | 脚本缺陷 | 未修（属冻结面） |
| R-08 | `VERSION` 仍是 1.1.0，但内容已有本地增量（+2 批次、+1 目录、控制文件 196→198） | 版本纪律 | 建议升 1.1.1，待窗口 |
| R-09 | 旧批次 `L0-contract-baseline` / `LD-legacy-discovery` 停在 `IN_DEV` 且证据永久 STALE（预算耗尽，框架无 retire 状态） | 状态治理 | 保留失败记录，不伪造状态 |
| R-10 | `doc2md` CLI **按数据库登记的 sha256 选内容，不接受文件路径** → 集成需访问其 MySQL/vault（跨组件数据耦合） | 集成障碍 | 已写入对接规格，作为对 doc2md 的需求 D2-1 |
| R-11 | `doc2md` 的 `config/app.yaml` 含**明文数据库口令**且已被 git 跟踪 | 安全 | 已提处置建议（轮换 + 环境变量），由其维护方执行 |
| R-12 | 解析准确率**无任何证据**（无标注真值集），当前只做了"用哪套"的选型 | 能力证据 | 属 M0 题库范畴，未启动 |

## 9. 未完成 / 阻塞清单

1. 独立 QA：L0-r2 未通过（预算耗尽）；LD-r2 已 DONE 但签名已过复核窗口。
2. P0-01/02：**生产侧运行时证据与真实 DDL 不可获得**，按现行口径无法关闭。
3. P0-03/04：政策已裁，证据（E1–E8 / S1–S5）未产出，且需要可运行的检索链与真实存储。
4. 12 项资产 / 37 表 / 506 接口：**零决议**（`decision` 全为 null）。
5. `llmke-ir/1.0` 合同未注册（草案，避免破坏已签证据）。
6. 版本号未递增、`authority` 元数据过期。
7. **从未提交过代码**（R-01）。

## 10. 请评审者回答的 8 个问题

1. 在「零提交 + 400 文件 staged」的状态下继续工作，风险是否可接受？应如何补救（一次性初始提交 / 分批提交 / 先补 .gitignore 审计）？
2. 门禁证据绑定"源码快照哈希"导致**任何文档改动都使证据失效**——这个设计是否过严？是否应按"控制面 vs 非控制面"分层绑定？
3. QA 签名 1 小时有效期 + 复核时重新验签，是否为设计错误？正确语义应是"签名时有效"还是"始终可复核"？
4. P0-01/P0-02 在生产侧材料不可获得的前提下，除了"永久 OPEN"或"降低标准"，是否存在第三种既诚实又能推进的路径（如"影子验证 + 显式局限声明"）？
5. 用"业主认定可获得快照为生产版本"来建立参照物，是否构成对 P0 关闭标准的实质放宽？如何在文档上避免这种认定被滥用？
6. D3 分治（PDF/OCR 用外部组件、DOCX 用旧代码适配）带来的双栈成本，是否值得？有没有更优的收敛路径？
7. 当前的批次/预算机制（per-gate attempts=3，耗尽即 BLOCKED）在实践中反复触发"为一个小改动开新批次 + 重冻结"，应如何调整？
8. 请据此给出**新的项目启动提示词**：应包含哪些"不可协商的红线"、哪些"必须自检的动作"、哪些"必须停下来问人的情形"？

## 11. 现有启动提示词（供改写参考）

### 11.1 `AI_GUIDE.md`（现用，36 行摘要）

- 权威顺序：本次兼容性决议 > 未替代的上游决议 > `contracts/registry.yaml` > 门禁目录/批次计划 > 实现。
- `FROZEN-MANIFEST` 固定技术控制文件字节，**不代表业务风险关闭、不代表真实环境验证、不代表业主验收**。
- 四项 P0 全 OPEN；L0/LD 可工作，L1–L4 默认 BLOCKED；不能清空 `blocks` 或自改 CLOSED/DONE 放行。
- 十二条纪律：合同先行、`generated/` 只读、门禁只执行目录内 argv、禁止 `|| true`、失败先记后修、
  开发可自检但独立 QA 必须外部受保护环境签署、审查 staged diff、凭据不入库、506 是清单数不是运行时能力、
  派生上下文须按当前权限复核、offset 为 Unicode 码点并绑 `text_hash`、降级必须显式。
- 开始工作前读 README → 当前 LOOP → STATE → FAILURES → HANDOFF；仅 baton holder 执行。

### 11.2 补丁给的 TL 提示词（10 条，摘要）

1. 运行覆盖工具、保存备份路径与清单摘要；2. 读核心文档并只按 registry 改合同；
3. 独立环境跑 `framework-verify`、确认 `p0-gate` 拒绝、三类状态分开报；
4. 启动 LD 取得真实材料、建逐项复用决议、不得只按文件数承诺复用率；
5. P0 按 D01… 逐项回答、挂真实哈希证据、owner 与 baseline-owner 在受保护环境批准；
6. 复用计划批准与最终迁移证明分开；7. 只有前置满足才 `arm/transfer`，不手改权威状态；
8. CASE-REGISTRY 绑真实测试文件、不得删条件/skip/恒真；9. 外部 QA 在固定快照复跑并签名；
10. 首次回执只提交：覆盖/备份、基线摘要、测试结果、台账状态、P0 状态、下一项可执行工作。

### 11.3 本次实践暴露的提示词缺口

| 缺口 | 说明 |
|---|---|
| 未规定"零提交"处置 | 导致 400 文件 staged 却无 commit |
| 未规定门禁运行环境 | 解释器与 `MAKEFLAGS` 未固定，反复踩坑 |
| 未规定"证据日志会被扫描" | 日志自引用污染无预警 |
| 未规定"改冻结面的连锁反应" | 未提示会让已签 QA 失效 |
| 未规定文档落盘位置 | 写成 `docs/**` 会消耗门禁预算 |
| 未规定"签名窗口" | 1 小时有效期的后果未写进操作流程 |
