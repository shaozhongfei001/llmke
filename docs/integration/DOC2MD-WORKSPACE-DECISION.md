# 决议：LLMKE 与 doc2md 同工作区、异仓库

- 决议编号：`INT-2026-10-21-WORKSPACE`
- 日期：2026-10-21
- 状态：**已采纳**（业主提出并批准方向；本文件为落地口径）
- 决策人：项目业主
- 执行人：Tech Lead
- 关联：`loops/LD-legacy-discovery/PARSER-DESIGN-COMPARISON-V1.0.md`、
  `loops/LD-legacy-discovery/PARSER-CONTRACT-PROBE-V1.0.md`

## 1. 决策

把 LLMKE 与 doc2md 放进**同一个开发工作区**，以便联调与只读查阅；
但**两者仍是两个独立的 git 仓库、两个独立的 GitHub 项目**，互不包含、互不引用指针。

具体形态（唯一批准形态）：

```text
<workspace-root>/
├── llmke/                        # git 仓 A（不动）
├── doc2md/                       # git 仓 B（平级迁入，通常从原位置移动）
├── llmke-doc2md.code-workspace   # 多根工作区文件（不入任何仓）
└── coordination/                 # 共享协调区（**不入任何仓**，无 .git）
    ├── doc2md.lock               # 冻结版本：commit / adapter / sniffer / routing 版本
    ├── BOUNDARY.yaml             # 仓边界声明（见 §3）
    ├── samples/                  # 探针样本（数字/扫描/加密 PDF + DOCX）
    └── probe/                    # 契约探测产物
```

## 2. 被否决的三种做法（附否决理由）

| 做法 | 否决理由 |
|---|---|
| **monorepo**（一个仓放两个项目） | 违背"GitHub 上两个完全独立项目"；且 LLMKE 的门禁体系按单仓设计，`source_files()` 会把新目录计入源码快照 |
| **submodule** | doc2md 每次更新都要 LLMKE 提交一次指针；指针变化即快照变化，会让 LLMKE 的批次证据失效 |
| **嵌套**（doc2md 放进 `llmke/` 内任意子目录） | ① LLMKE 源码快照会把 doc2md 文件算进去，**已通过的门禁证据全部 STALE**；② `make security-check` 的树扫描（`--all-files`）会命中 doc2md 的 `config/app.yaml`（含明文数据库口令），直接 FAIL |

> 这三条是**硬红线**，不是偏好。任一条件成立，本决议自动失效。

## 3. 仓边界声明（BOUNDARY.yaml 的内容口径）

```yaml
llmke:
  root: ./llmke
  role_in_workspace: writable        # 仅 LLMKE 自己的角色可写
  forbidden_neighbors: [doc2md]      # 禁止在 llmke 会话中修改
doc2md:
  root: ./doc2md
  role_in_workspace: read_only       # LLMKE 侧一律只读
  write_requires: doc2md_own_flow    # 改动必须走 doc2md 自己的角色/流程
shared:
  root: ./coordination
  in_git: false                      # 禁止 commit、禁止指向任一仓
```

**为什么把 doc2md 设为只读**：doc2md 有自己冻结的实现基线（014 相关文件按 md5 冻结）和独立 QA 流程。
LLMKE 侧一旦"顺手改一下"，就会同时破坏两个项目的证据链，且无人能说清是谁改的。

## 4. 针对"跨仓误改"的优化措施（本决议的重点）

### 4.1 五条可执行约束

| # | 约束 | 怎么检查 |
|---|---|---|
| B-1 | **每次操作前先确认自己在哪个仓**：`git rev-parse --show-toplevel` 必须落在目标项目根内 | 手工/脚本；见 4.2 的 `boundary-check` |
| B-2 | **禁止跨仓 `git add`**：两个仓分别显式列路径提交，永久禁止 `git add .` / `git add -A` | `git diff --cached --name-only` 必须全部属于当前仓 |
| B-3 | **doc2md 只读**：LLMKE 会话只允许 `read` / 运行其 CLI 探测；任何文件写入都算越界 | 对 doc2md 关键文件做 md5 复核（见 4.2） |
| B-4 | **共享区不入库**：`coordination/` 不带 `.git`，不被任一仓的 `.gitignore` 之外引用 | `find coordination -name .git` 必须为空 |
| B-5 | **禁止把 doc2md 放进 llmke 目录**：迁移后校验 `llmke/` 下不含 `doc2md` 命名的目录 | `ls llmke \| grep -i doc2md` 必须为空 |

### 4.2 护栏脚本（放在 `coordination/`，不入库）

`coordination/boundary-check.py` 建议做三件事（只读检查，不修任何东西）：

1. 打印当前 cwd 所属 git 仓根与分支；
2. 若在 `llmke/` 内，检查 `git diff --cached --name-only` 是否越界，并断言 `llmke/` 下无 `doc2md` 目录；
3. 对 doc2md 的冻结文件清单做 md5 复核，与 `coordination/doc2md.lock` 中记录的值比对，
   不一致即判 `DOC2MD_FROZEN_DRIFT`（说明有人改了 doc2md）。

> 为什么放 `coordination/` 而不是任一仓：它是**跨仓**约束，放进任一仓都会造成"用一个仓管另一个仓"的错觉。
> 代价是它不可版本化——所以本文件（可入库）负责**声明规则**，脚本负责**执行规则**，两者互补。

### 4.3 会话/角色边界

- LLMKE 的角色（含 Tech Lead）在 doc2md 上**只有读权限**；
- 需要修改 doc2md 时，必须**另开会话**，并在会话说清"当前项目 = doc2md"，按其 `docs/role_prompts/*.md` 的角色执行；
- 同一会话内**不允许**出现"改完 doc2md 顺手改 llmke"的操作顺序（跨仓一次提交是被禁止的）。

## 5. 针对"明文凭据"的优化措施

### 5.1 现状（实测）

- `doc2md/config/app.yaml` 含 **1 处明文数据库口令**，且该文件**已被 git 跟踪**；
- LLMKE 侧实测：`security_scan.py --all-files` 只扫自己 root（`rglob` 不越界），
  所以只要 doc2md 是兄弟目录，LLMKE 的扫描**不会**命中它——但嵌套就会命中。

### 5.2 迁移期建议（doc2md 侧执行，LLMKE 不代劳）

1. **轮换口令**：既然要动，先假定它已泄露于版本历史。
2. `config/app.yaml` 改为**不含口令**的模板；口令改由环境变量提供（如 `DOC2MD_MYSQL_PASSWORD`）。
3. 本地覆盖文件 `config/app.local.yaml` 加入 `.gitignore`；
   `git rm --cached config/app.yaml` 后重新以模板形式提交（历史仍在，故必须轮换）。
4. 若短期做不到，退一步：**至少确保 doc2md 永远不在 llmke 目录内**（B-5），并把该文件列为"已知风险"。

### 5.3 顺带清理（迁移时一起做）

- `raw_vault/*/file_metadata.json` 记录了源文件绝对路径（32 个 json）：
  这些是**历史产物**，迁移后不必修，但**不得**被拷进 `coordination/samples` 或任何共享目录
  （避免把个人目录结构扩散到联调材料里）。
- `.ua/.trash-*` 临时目录里的脚本残留旧绝对路径，建议迁移前删除。

## 6. 迁移检查清单

### 6.1 doc2md 侧（逐项打勾）

| # | 检查 | 通过标准 |
|---|---|---|
| 1 | 迁移前记录锚点 | `git rev-parse HEAD`（本次为 `d9e4f98`）、`git status` 干净 |
| 2 | 平级迁移 | 位于 `<workspace-root>/doc2md`，**不在** `llmke/` 内 |
| 3 | 路径推导自检 | `PROJECT_ROOT = parents[3]` 指向新根；`./raw_vault`、`./parsed`、`./sniff_cache` 均解析到新根 |
| 4 | 测试基线复跑 | 014 两测试文件共 61 passed；全量 4 个既有 `--help` 失败**不在本次范围**（勿修） |
| 5 | 文档路径更新 | 67 个 md 中的绝对路径（尤其 `docs/role_prompts/*.md`）指向新根 |
| 6 | 历史产物保留 | `raw_vault/`、`parsed/`、`sniff_cache/` 不做内容修改 |
| 7 | 凭据处置 | 按 §5.2 执行，或书面记录为已知风险 |

### 6.2 LLMKE 侧

| # | 检查 | 通过标准 |
|---|---|---|
| 1 | 无嵌套 | `ls llmke \| grep -i doc2md` 为空 |
| 2 | 快照未变 | 迁移 doc2md **不应**改变 LLMKE 的快照指纹（doc2md 不在其扫描范围内） |
| 3 | 安全扫描未命中 | `make security-check` 仍 PASS |
| 4 | 门禁证据仍有效 | `make evidence-check LOOP=<当前批次>` 仍 PASS |

> 本决议文档本身写在 `docs/integration/`，**会**改变 LLMKE 的源码快照（见 §7.1）。

## 7. 已知代价与残余风险

### 7.1 本决议对 LLMKE 门禁的代价（已发生，透明记录）

`docs/integration/` 不在快照排除前缀内（排除项为 `docs/reviews/`、`docs/approvals/`、
`docs/baseline/validation/`、`docs/registers/closures/`、`contracts/build/`），
因此**新增本文件会让 LLMKE 既有批次的门禁证据判为 STALE**，需重跑恢复。

处置：写入后重跑受影响批次的门禁，并占用其修复预算。**后续文档类产出应批量合并**，
或优先落在上述排除目录 / `loops/**`（不参与快照），避免反复消耗门禁预算。

**实测后果（2026-10-21，已登记为阻断）**：写入本文件后重跑，
L0 有 5 条门禁在新快照恢复 pass，但 `security_scan_gate` 失败、
6 条门禁 attempts 达 3/3（预算耗尽）；LD 的 `inventory_gate` 同样 STALE 且 3/3。
失败根因不是本文件的内容，而是**安全门禁自污染**：父 make 把 `w` 传给子 make，
子 make 打印 `make[1]: 进入目录“<项目绝对路径>”` 写入 `loops/*/evidence/*.log`，
而 `security_scan.py --all-files` 会扫描这些日志 → 命中 `PERSONAL_ABSOLUTE_PATH` → 失败输出又写回日志。
详见 `loops/L0-contract-baseline/FAILURES.md`（FAIL-2026-10-21-04）与 `memory/BLOCKED.md`。

**结论**：本决议的收益（跨仓纪律 + 凭据处置）成立，但它**以两个批次的门禁预算为代价**；
恢复需按 `BLOCKED.md` 的选项 A 开新批次，并在重跑前导出 `MAKEFLAGS=--no-print-directory`。

### 7.2 残余风险

| 风险 | 缓解 |
|---|---|
| 同工作区内 agent 误跨仓写 | §4 五条约束 + `boundary-check.py` 护栏 |
| 两个解释器混用（LLMKE 3.12 venv / doc2md 3.11 带 magic_pdf、paddleocr） | 每个项目固定自己的解释器，调用时用绝对路径；不共享 venv/conda 环境 |
| doc2md 演进导致解析行为漂移 | `coordination/doc2md.lock` 冻结 commit 与四个版本号；LLMKE 侧记录这些版本 |
| 共享区被误提交 | `coordination/` 无 `.git`；B-4 检查 |
| doc2md 明文口令泄露面扩大 | §5.2 轮换与改造；B-5 保证不嵌套 |

## 8. 验收标准（迁移完成的判定）

1. 目录树与 §1 一致，`coordination/` 存在且无 `.git`；
2. doc2md 测试基线复跑结果与迁移前一致（61 passed 基线不退化）；
3. LLMKE：`make evidence-check` 与 `make security-check` 均为 PASS；
4. `boundary-check.py` 三项检查全绿（含 doc2md 冻结文件 md5 与 lock 一致）；
5. `coordination/doc2md.lock` 记录了 commit + `parser_adapter_version` + `sniffer_version` + `routing_rules_version`。

## 9. 本决议不涉及的事

- 不改变两个项目的远端仓库归属（仍是两个独立 GitHub 项目）；
- 不引入 submodule、不共享依赖、不合并 CI；
- 不改变 doc2md 的解析实现（PDF/OCR 引用其独立组件、DOCX 暂不引用，见对比报告）；
- 不解决 doc2md 的凭据问题本身（只提出处置建议，由其维护方执行）。
