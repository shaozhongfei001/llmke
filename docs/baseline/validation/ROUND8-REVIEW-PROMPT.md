# 评审提示词：LLMKE 第八轮长程任务（2026-10-20 → 2026-10-24）

> 用法：整段复制发给评审方。你（评审方）看不到仓库，所有事实以本文陈述为准；
> 凡我标注「未独立验证」的，请当作"声称"而非"事实"。

---

## 0. 你的角色

你是独立评审，任务是**找问题**，不是背书。请优先回答第 9 节的 10 个问题；
如果我的陈述里有不可验证、循环论证或自我美化，请直接点出编号。

## 1. 项目是什么

LLMKE：企业内部知识引擎（Java/Spring + Python 模块 + MySQL）。
核心工程约束不是"功能跑通"，而是**证据链**：任何"通过"都必须能回答
"哪棵树、哪套门禁、谁签的字、改动后是否仍然有效"。

关键机制（本轮前已存在，本轮有改动）：

| 机制 | 作用 |
|---|---|
| `snapshot` | 整树哈希，任何文件变化都变 |
| `control_digest` | 只覆盖控制面：`scripts/`、`contracts/`、`docs/policies/`、`docs/baseline/`（排除 `validation/`）、`loops/*/LOOP.yaml`、`tests/*.py`、`Makefile`、`docs/PROJECT-PLAN.yaml` 等 |
| `code_digest`（本轮新增） | 业务实现代码 `modules/ apps/ services/ lib/ frontend` 的 `*.py`（排除 tests） |
| `doc_digest` | 17 份说明文档 |
| 批次（loop） | 一次"跑门禁 → 取证 → 送 QA → 签 → 定稿"的单元，落 `loops/<id>/` |
| `evidence-check` | 用记录里的摘要对比当前树，判 STALE |
| QA 签名 | Ed25519 信封，绑定 `subject_sha256`（gate 定义 + 树 + 日志 + 检查集），有效期 1 小时 |

## 2. 本轮范围

- 起点：`a9c2b43`，独立工作树 `llmke-r8`，分支 `round8/delivery`，后合入 `main`
- 规模：**67 个提交**、**27 个任务**、**53 条决策记录**（D1–D54）、**63 份验证文档**
- 关闭：2026-10-23 业主裁定"按 ② 收尾，无独立背书"

## 3. 做了什么（按阶段）

### A. 业务纵向切片
引用证据组装器（`modules/citation_evidence`）：单条装配 → 集合级校验 → 解析器版本一致性 → 支持率审计 → CLI。
测试从 10 条增至 39 条（模块内）。覆盖：伪造 offset、越界、单位错误、重复 `evidence_id`、
同/跨 chunk 区间重叠、空集合 fail-closed、`parser_version` 混用（同一文档两套坐标系）。

### B. 框架缺陷修复（本轮主要工作量，文件均为控制面）

| 编号 | 内容 | 触发事实 |
|---|---|---|
| W-01 | `Makefile` 收集 `modules/`（145 → 193 测试）；新增 `code_digest`；`digest_scheme` 2→3 | 模块测试从不执行；且**改业务代码不作废任何证据**（实测：加一行注释，整树 snapshot 变、`control_digest` 不变、`evidence-check` 仍 PASS） |
| W-01b | `evidence-check` 不再跳过 `QA_PENDING` 记录 | 候选已过期时仍打印 PASS，真正拦截只在 `accept-qa` |
| W-02 | 新增第 9 条门禁 `module_test_gate`（`framework.modules`） | 模块测试粒度不可见 |
| W-04 | 测试锁定"签名有效但候选过期必须被拒" | 顺序依赖无测试，改两行即可放行 |
| W-05 | `Makefile` 固定解释器（`LLMKE_PYTHON`/`PY`，替换 25 处） | R-02：conda shell 下取错解释器，**同一缺陷 3 次事故** |
| W-05b | `scripts/_pin.py` 入口自钉（`os.execve` 重入） | 只改 Makefile 不够：门禁 argv 用 `sys.executable`，入口错则整链错，且只单条门禁失败更难查 |

### C. 数据层
`schema V1.3`：43 表 / 538 列 / 97 模块测试；体检 C1–C6 全 PASS、0 处不一致；
从 ORM 反推候选 DDL（37 表/479 列）并与手写 schema 回环比对。

### D. 批次链

| 批次 | 状态 | 备注 |
|---|---|---|
| r5 | SUPERSEDED | 原始候选 |
| r6 | SUPERSEDED | **我作废**：验收实验做在冻结之后（与 r3 同类错误） |
| r7 | SUPERSEDED | 业主弃用（换取一次 QA 覆盖四项改动） |
| r8 | SUPERSEDED | **我作废**：补丁包漏了授权条目，`change_list` 与事实不一致 |
| r9 | SUPERSEDED | 被 r10 取代 |
| r10 | **DONE** | 业主授权自签（实现方持私钥），签名已过期，九条全 STALE |
| r11 | **QA_PENDING** | 无签名；`attempts` 中 QA 门禁 2/3 |

### E. 收尾
外部 QA 复核：技术 PASS（252/0、43-538-97-6、p0 rc=2、四组对抗全部按要求失效），
但**未出具独立签名**：`qa-ed25519-indep` 私钥被 `shred` 且无副本、无交付证据 → 公钥悬空。
业主裁定关闭，记为 `CLOSED_WITHOUT_ENDORSEMENT`。

## 4. 当前证据（可复现，命令与退出码）

```
make framework-verify        rc=0   252 passed, 0 skipped   （需先启 MySQL 实例，否则 29 skipped）
schema-verify.sh             rc=0   43 表 / 538 列 / 97 测试 / C1–C6 PASS / 0 不一致
make p0-gate                 rc=2   P0-01~04 全 OPEN（预期拒绝）
evidence-check r11           rc=0   PASS（8 pass + independent_qa_gate=QA_PENDING, scheme=3）
freeze-check                 rc=0   revision 12 / 215 文件 / 1.1.1
```

摘要值：`baseline_sha256=4a4bfa74…`（== trust-root anchor）、`code_sha256=19517fe1…`、
r11 `subject_sha256=84251565…`。

**四组对抗（QA 独立复跑，非转述）**：
改实现代码 → 仅 QA 门禁 STALE；控制面加文件 → 9 条全 STALE；
改文档 → 仅 `traceability_gate`；篡改日志 → `evidence hash mismatch`；还原后 PASS。

## 5. 我判定为"已完成"的边界

- 25 / 27 任务 VERIFIED；
- 1 项 `CLOSED_WITHOUT_ENDORSEMENT`（T04 独立 QA 签署：技术 PASS、无签名）；
- 1 项 `BLOCKED_EXTERNAL` 结转（T05 真实 DDL/路由/E1/S1–S5）。
- **业务不可开工**：`p0-gate` rc=2，L1–L4 BLOCKED。
- 明确禁止的表述：不得写"第八轮全部完成"或"已通过独立 QA"。

## 6. 本轮出现的失误（不美化，全部留痕）

| # | 失误 | 代价 | 处置 |
|---|---|---|---|
| 1 | r6 作废：验收实验放在冻结后 | 多一个终态批次、重跑 9 条门禁 | 记 D12 |
| 2 | r8 作废：补丁包未含授权条目 | 同上 | 记 D15 |
| 3 | `evidence-check` 曾跳过 `QA_PENDING`（假绿） | 读数误判 | 修 W-01b |
| 4 | W-07 补丁方向错误（用未签名 `STATE.json`/`ran_at` 作审计时钟） | 被外部 QA 否决 | 移出仓库，改立 `BL-1.1.1-01` |
| 5 | 提交声称"独立签名"但无 attestation | `finish` 正确拒绝，已 `reset` | 记 `FAIL-2026-10-22-01` + 三条规则 |
| 6 | `shred` 先于 custody proof | 私钥永久丢失，无法背书 | 记 D54，规则改为"先验证再删" |
| 7 | 前置检查脚本假红（从载荷读 `key_id`） | 浪费一轮排查 | 已修，并加"不得复用旧钥"检查 |
| 8 | 文档两次写入宿主绝对路径 | `security-check` 判红两次 | 脱敏 + 仓外预检 |

## 7. 已知缺口（我认为尚未解决）

1. **无独立背书**：签名密钥与实现方同机/同手，`implementation_principals` 只拦主体名，拦不住"同一双手换身份"。
2. **可审计性欠账**：签名窗口 1 小时，`BL-1.1.1-01`（签名消费回执）仍 `PROPOSED` 未实现 → 已定格批次在窗口外必然报"时间失效"。
3. **孤儿批次**：`r2` 仍 `QA_PENDING`、`r4` 仍 `IN_DEV`，非本轮产生，既未 DONE 也未终态，账本未覆盖。
4. **`docs/baseline/validation/` 是冻结排除前缀**：63 份文档在此，可"无痕"放入文件而不改任何摘要；已加目录约定，但未纳入控制面。
5. **STALE 清单顺序不稳定**（set 遍历），将来 golden-file 断言会 flake；`BL-1.1.1-02` 已登记未做。
6. **provenance 偏弱**：r11 的 `qa-run` 执行者是实现方，`accept-qa` 会覆盖 executor。
7. **attempts 预算**：r11 的 QA 门禁 2/3，再失败即耗尽，须 TL 批准新批次。
8. **业务侧零进展**：P0-01~04 全 OPEN，本轮未动业务代码路径。

## 8. 我做了什么来防止"自欺"

- 每个"已修"都配反例：改一行注释必须让证据失效；只改 STATE 不得放行；错误公钥必须验签失败。
- 变异测试：删掉 `accept-qa` 的 stale 检查，新用例必须失败（证明测试有牙）。
- 红队审计 P0 闸门：14 种伪造路径，14/14 被拦（空证据、假 snapshot、错 blocker_id、无 waiver 等）。
- 对"我的工具"也做负向测试：缺信任根必须退出码 2 并解释，而不是伪装成 PENDING。

## 9. 请你回答的 10 个问题

1. **关闭是否合规**：在"技术 PASS、无独立签名、业务闸门仍关"的情况下，把本轮记为"已关闭（技术完成、无背书）"，属于合理收尾还是掩盖未完成？
2. **证据链真实性**：我列出的四组对抗与 252/0 是否足以支撑"做的和被审的是同一棵树"？你认为还缺哪一条最关键的对抗？
3. **`control_digest` 的粒度**：控制面包含 `tests/*.py` 与 `loops/*/LOOP.yaml`，这意味着"新建批次"必然作废前一批证据。这是必要代价，还是设计缺陷？
4. **`code_digest` 的窄绑定**（只有声明依赖代码的门禁才比较）是否会留下新的假绿通道？
5. **批次链 r5→r11 作废 6 次**：这说明流程不成熟，还是说明门禁在正常工作？如何区分？
6. **孤儿批次 r2/r4**：应清理、归档，还是保留？清理会不会破坏审计连续性？
7. **`BL-1.1.1-01`（消费回执）**：我提议"accept-qa 写一份纳入 `control_digest` 的回执，审计只认回执"。这个设计有没有更简单且不引入新信任假设的做法？
8. **1 小时签名窗口**：在"无回执"的前提下，任何窗口外复查都会判红。是否应改为"长有效期 + 一次性消费"？
9. **独立性定义**：同机、同用户、不同密钥、不同主体名，是否构成独立？如果不构成，最小可操作标准是什么？
10. **最根本的问题**：如果只能改一处设计来提升这套证据体系的可信度，你会改哪里？

## 10. 复现命令（如你在有仓库的机器上评审）

```bash
cd <repo>
export PATH=$PWD/.venv/bin:$PATH LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
~/data/dev/coordination/mysql-probe.sh start
make framework-verify > /tmp/fv.log 2>&1; echo "rc=$?"; tail -3 /tmp/fv.log
bash docs/baseline/validation/schema-verify.sh; echo "rc=$?"
make p0-gate > /tmp/p0.log 2>&1; echo "rc=$?（期望 2）"
~/data/dev/coordination/evidence-check.sh L0-contract-baseline-r11
```

## 11. 诚实声明

- 第 4 节数字来自我与外部 QA 的实际执行；第 6 节失误全部有提交/文档留痕。
- 以下内容**未独立验证**，请按"声称"处理：r2/r4 的历史成因；`code_digest` 覆盖率数字；
  63 份文档中我未逐篇复核的部分。
- 我未做：业务功能验证（P0 未关，不具备条件）、压力/性能测试、安全渗透测试。
