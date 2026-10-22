# 第五轮计划类交付：A4 迁移草案 / PDF 离线前置 / 外部输入包

> 全部为**计划与草案**，未执行、未改控制面、未重冻结、未触碰 r5。

---

## 一、A4：P-08 / P-09 / P-10 迁移方案草案（不执行）

### 共同前提（三项都适用）

| 项 | 说明 |
|---|---|
| 实施窗口 | 必须与「建齐批次 + 版本递增 + 重冻结」合并为**一次窗口** |
| 实施后失效 | `baseline_sha256` 改变 → **r5 全部 7 条门禁证据与 QA 候选立即 STALE**；`LD-r2` 的历史签名亦失效（作历史保留） |
| 需要的准备 | 新批次（r6）已建、计划已登记、`VERSION` 已递增、迁移脚本与回滚步骤已评审 |
| 禁止 | 分批实施（每批都触发重冻结 → 每次作废一次候选） |

### P-08 扫描范围固定化

| 步 | 动作 | 验证 |
|---|---|---|
| 1 | `security_scan.py` 增加 `--scope=source|artifacts|both`（默认 `both`） | `--scope=source` 只扫 `git ls-files` |
| 2 | `source` 轮：五类判定全开 | 源码写宿主路径 → FAIL |
| 3 | `artifacts` 轮：仅凭据/连接串/私钥/生产主机 | 日志写宿主路径 → PASS；日志写真实口令 → FAIL |
| 4 | 输出双计数 `source=NNN artifacts=MMM personal_path_skipped=K` | 两次连跑数字一致 |
| 5 | `Makefile` 的 `security-check` 改为 `--scope=both`（argv 变更需同步 `GATE-CATALOG`） | `framework-verify` PASS |

**回退**：`git revert` + 重冻结一次（因为 `GATE-CATALOG.yaml` 属控制面）。

### P-09 QA 载荷改用 `control_digest`

| 步 | 动作 | 验证 |
|---|---|---|
| 1 | `qa_subject()` 增加 `digest_scheme` 与 `control_sha256` | 记录字段存在 |
| 2 | `qa_payload.py` 的校验改用 `stale_reasons()`（与门禁同一函数） | 改 `docs/**` → 载荷仍可生成 |
| 3 | `accept-qa` 同样改用 `stale_reasons()` | 改 `contracts/**` → 拒绝 |
| 4 | 旧记录 `digest_scheme` 缺失 → `legacy` 整树语义 | 旧 QA 仍可复核 |

**回退**：同上（改 `loop_guard.py` + `qa_payload.py` 属控制面）。

### P-10 信任根增加基线批准审计

| 步 | 动作 | 验证 |
|---|---|---|
| 1 | 信任根新增 `baseline_approvals: [{sha256, approved_by, approved_at, reason, superseded_at}]` | 文件可解析 |
| 2 | `verify_envelope` 改为「当前基线必须命中未撤销条目」 | 命中 → PASS；不命中 → 拒绝并列出已批准值 |
| 3 | 兼容旧标量 `approved_baseline_sha256`（视为单条 legacy） | 旧信任根仍可用 |
| 4 | 撤销某条 → `superseded_at` 填值 | 该基线的签名不再被接受 |

**回退**：信任根在仓库外，回退=恢复文件备份；代码侧 `git revert` 后重冻结。
**注意**：此项需 `qa-owner` 同意审计语义，属其职权范围。

---

## 二、PDF：离线依赖与安装前置（不做等价性结论）

### 2.1 旧解析臂（`alg_doc_parse_service`）缺什么

| 依赖 | 用途 | 缺失后果 |
|---|---|---|
| `magic_pdf` | PDF 版面解析（含模型） | PDF 解析完全不可用 |
| `onnxruntime` | OCR/版面模型推理 | OCR 与图片路径不可用 |
| `cv2` (opencv) | 图像预处理 | 图片/扫描件不可用 |
| `tika` | 文件类型探测（部分路径） | 部分格式走不通 |
| `fitz` (PyMuPDF) | 部分 PDF 兜底路径 | 该路径不可用 |
| 模型目录 | `./ocr_models`、版面模型 | 构造解析器即失败（第四轮已实测 `image_parser.py:21` 构造期加载） |

**安装前置条件（需 `algorithm-owner` 提供）**：
1. `magic_pdf` 的**离线 wheel 或内网源**（该包对版本敏感，需给出配对的 `torch`/`onnxruntime` 版本）；
2. 模型文件清单与校验和（目录名、文件数、总大小、每个文件 sha256）；
3. 是否允许联网拉取（若不允，需完整离线包）。

### 2.2 doc2md 臂缺什么

| 项 | 现状 | 需要 |
|---|---|---|
| 虚拟环境 | 无 `.venv` | 依赖清单或 `requirements.txt` + 支持版本 |
| 包可导入 | `ModuleNotFoundError: doc2md` | 安装方式（`pip install -e .`？） |
| CLI 入口 | 未找到 `console_scripts` | 明确的调用方式（模块路径 / 参数） |

### 2.3 两臂就绪后的验证步骤（不得跳过）

1. 各自输出**实际加载的解析器文件路径**与 SHA256，并断言两臂路径**不同**（防上一轮那种「自己和自己比」）；
2. 按覆盖矩阵跑 6 份样本（文本/扫描/加密 PDF + 纯文本/表格/图片 DOCX）；
3. 任一侧 `ok=False` → 判 `FAILED`（禁止 `None == None`）；
4. 输出块数、页码、offset、字符数，全部做非空断言；
5. **61 项组件测试只作回归证据**，不写进等价性结论。

---

## 三、外部输入包（一页一份，可直接转发）

### 3.1 给 `interface-owner`（P0-01）

| 项 | 内容 |
|---|---|
| 要什么 | 506 条中承载业务流量的接口的**运行时在用状态** |
| 三种格式任选 | 路由导出（`samples/route-export-sample.csv`）／访问日志（`samples/access-log-sample.csv`）／调用方确认（`samples/caller-confirmation-sample.md`） |
| 填写对象 | `loops/LD-legacy-discovery/evidence/interface-decision-table.csv`（已备 506 行） |
| 完整性 | 覆盖全部 service；`IN_USE` 需给出可核查调用位置；允许 `UNKNOWN` |
| 卡住什么 | P0-01 关闭、L1/L3 |
| 不可接受 | 只有 path 没有调用方；本地开发日志冒充生产；口头「大概在用」 |

### 3.2 给 `data-owner`（P0-02）

| 项 | 内容 |
|---|---|
| 要什么 | ① 逐表 `SHOW CREATE TABLE`（脱敏）② 索引/约束/触发器/引擎/字符集/版本 ③ 同版本恢复副本上的迁移与回退记录 ④ `dialogue.create_by` 值域与生成方 ⑤ **字段名清单**（台账当前只有计数） |
| 格式 | 文本 DDL + 执行日志（含时间戳与执行者） |
| 优先回答 | `user_operate` 台账 13 / 实体 12 的差异方向（见 `A2-FIELD-ATTRIBUTION.md`）；`dialogue.user_id` 是否存在 |
| 卡住什么 | P0-02 关闭、L1/L2/L3 |
| 不可接受 | 「和源码一致」；实体类当 DDL；只给字段数 |

### 3.3 给 `security-owner`（P0-03）

| 项 | 内容 |
|---|---|
| 要什么 | ① E1 正式规范（`AuthContext` 字段、签名、失效语义）② E2–E8 六类负例在真实链上的结果 |
| 现状 | 已有六类负例**模拟**（7/7 场景、7/7 变异体被拒），策略来自草案，**未获批** |
| 格式 | 规范文档 + 可执行负例 + 运行日志（含环境标识） |
| 卡住什么 | P0-03 关闭、L1/L3/L4 |
| 不可接受 | 用模拟结果当实测；用测试夹具当生产证据 |

### 3.4 给 `index-owner`（P0-04）

| 项 | 内容 |
|---|---|
| 要什么 | ① S1–S5 在真实四后端上的执行结果 ② 双代存储与内存余量实测数字（P2 前必须，不得推 P3）③ 历史引用所需快照的保留验证 |
| 现状 | 模拟已备（5/5 场景 + 5/5 变异体被拒），纯内存模型 |
| 格式 | 可复跑脚本 + 实测数字 + 资源曲线 |
| 卡住什么 | P0-04 关闭、L1–L4 全部 |

### 3.5 给 `qa-owner`（批准与签署）

| 项 | 内容 |
|---|---|
| ① | 把信任根 `approved_baseline_sha256` 更新为 `213c6ebc203ef846c3edf5397a9640310a683391878ddb5af4c12b8da25cbc52` |
| ② | 签署 r5（命令见 `QA-TRUST-CHAIN.md` §6；载荷 1 小时有效，过期重跑 `qa_payload.py` 即可） |
| ③ | P-02 三选一（`DECISION-PACK-V1.1.1.md` D-01） |
| ④ | P-10 审计语义是否同意 |
| 卡住什么 | ① ② → **合并唯一拦路条件**；③ → 历史 QA 复核能力 |

### 3.6 给 `baseline-owner`（依赖与控制面）

| 项 | 内容 |
|---|---|
| ① | `requirements.lock` 收敛：2 处版本冲突（`pip` 25.0.1/26.2.1、`idna` 3.19/3.20）+ 14 个无关重型包（105 行 / 95 唯一包） |
| ② | P-08 / P-09 批准与实施窗口 |
| 卡住什么 | ① → 环境可复现性声明；② → 扫描可复算、QA 载荷一致性 |

---

## 四、这些文件都不是审批

上述三节全部是**请求与方案**。仓库中不存在任何对应的批准记录；
在责任方给出可追溯签署前，不得写成「已批准」「已通过」「已关闭」。
