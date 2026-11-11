# 收敛到 main 的解决方案 + 外部专家评审包

> 生成时间：2026-11-08 23:5x
> 目的：供**外部专家独立评审**。文中每条事实均附可复跑命令，**不要求评审者采信本文结论**。
> 作者自述：本会话中作者已发生多次事实性错误（见 §五），因此 §一 只列**可机器验证**的事实，判断类内容一律标注「判断」。

---

## 一、事实卡（每条附验证命令，请独立复跑）

### 1.1 仓库结构：一个仓库、三个 worktree、三个分支

```bash
for d in llmke llmke-v2 llmke-r12; do
  printf "%-10s branch=%-24s head=%s dirty=%s\n" \
    "$d" "$(git -C /home/szf/data/dev/$d branch --show-current)" \
    "$(git -C /home/szf/data/dev/$d log --oneline -1 | cut -d' ' -f1)" \
    "$(git -C /home/szf/data/dev/$d status --porcelain | wc -l)"
done
```

| 目录 | 分支 | HEAD | 未提交项 |
|---|---|---|---|
| `/home/szf/data/dev/llmke` | **main** | `633a3997` | **0** |
| `/home/szf/data/dev/llmke-v2` | `feat/spectra-theme` | `e2534d8b` | **131** |
| `/home/szf/data/dev/llmke-r12` | `feature/R12-real-rag` | `100e261e` | **36** |

三个目录的 `git rev-parse --git-common-dir` 均指向 `/home/szf/data/dev/llmke/.git` ⇒ **同一仓库的三个 worktree**，不是三个独立仓库。

### 1.2 分支关系

```bash
git -C /home/szf/data/dev/llmke rev-list --left-right --count \
  origin/main...origin/feature/R12-real-rag        # → 274  0
git -C /home/szf/data/dev/llmke ls-remote --heads origin feat/spectra-theme | wc -l   # → 0
```

| 分支 | 与 main 的关系 |
|---|---|
| `feature/R12-real-rag` | **main 独有 274 提交，R12 独有 0** ⇒ R12 是 main 的祖先，**无独有提交** |
| `feat/spectra-theme` | **远程 0 条** ⇒ 纯本地分支，**未推送过** |

### 1.3 ⚠️ 关键事实：main 上没有任何本项目工作

```bash
git -C /home/szf/data/dev/llmke show origin/main:docs/v2-tasks/TASKS.yaml 2>/dev/null | grep -c 'T-D2MD'   # → 0
```

**main 分支的 `docs/v2-tasks/TASKS.yaml` 里 `T-D2MD` 命中 0。**

⇒ **本项目（DOC2MD 增量摄取）的 L1~L13 全部工作、文档、证据，均不在 main 上。**

### 1.4 两处「main 上的现存缺陷」（判断 + 可验证）

```bash
# 缺陷 A：main 的 /v2WholeGraph 不支持按 kb 路由
git -C /home/szf/data/dev/llmke show origin/main:services/rag-java/rag-parent/rag-graph-service/src/main/java/com/gientech/raggraphservice/interfaces/V2GraphProxyController.java | wc -l        # → 87
git -C /home/szf/data/dev/llmke show origin/main:...同上... | grep -cE 'spaceName|kb'   # → 0

# 缺陷 B：rag-qa 启动检查默认 fail-fast=true
grep -n 'startup-check.fail-fast' \
  /home/szf/data/dev/llmke-r12/services/rag-java/rag-parent/rag-qa-service/src/main/java/com/gientech/ragqaservice/infrastructure/RetrievalEndpointStartupCheck.java
# → :53  @Value("${rag-qa.startup-check.fail-fast:true}")
```

**判断（需专家复核）**：
- 缺陷 A：main 版把 `/v2/graph/view` 转发给 18094 时**不带 kb 参数** ⇒ 所有知识库读到同一快照。若为真，这是功能性缺陷。
- 缺陷 B：`fail-fast` 默认 `true`，任一被检查端点 TCP 不通即阻断 rag-qa 启动。这属「默认值选择」问题，是否为缺陷取决于设计意图。

### 1.5 其他可验证项

```bash
du -sh /home/szf/data/dev/llmke-r12/platform/r12/data          # → 245M
git -C /home/szf/data/dev/llmke-r12 check-ignore -v platform/r12/data   # → 无输出 = 未忽略
git -C /home/szf/data/dev/llmke-v2 stash list                  # → stash@{0}: On main: llmke-main dirty snapshot 20261103
```

---

## 二、歧义已裁定：**解读 A**（2026-11-08，Owner 确认）

原文两种解读：

| 解读 | 含义 | 后果 | 裁定 |
|---|---|---|---|
| **A. 代码基线以 main 为准** | 收敛目标 = main；v2/r12 中**尚未合并的有效修复**需合入 main | L1~L13 的工作得以保留 | ✅ **已采纳** |
| B. v2 与 r12 的一切作废 | main 即唯一真相；131 + 36 项全部丢弃 | **L1~L13 全部丢失**（main 上 `T-D2MD` 命中 0） | ❌ 未采纳 |

**裁定结果**：**以 main 作为代码基线，v2 与 r12 中尚未合并的有效修复合并进 main，L1~L13 保留。**

### 该裁定下的三条硬约束

1. **main 不被回退** —— 合并以 main 为基底，不是用 v2 覆盖 main；
2. **「有效修复」需逐项判定** —— 不能整批搬（见 §3.1 三项禁止搬）；
3. **合并完成前不删除任何分支** —— 否则 A 类 12 项修复失去来源。

### 支撑事实

- `llmke-v2` 的 131 项**全部未提交**，`feat/spectra-theme` **无远程分支**；
- 工作区已打包：`/home/szf/data/dev/llmke-v2-wip-20261108T213218.tar.gz`（174 MB，md5 `3730cd2cb30a86b6a30591ce8ce373aa`）；
- `main` 上 `T-D2MD` 命中 0 ⇒ **本项目全部工作在 main 之外**，这是必须合并而非覆盖的原因。

---

## 三、收敛方案

### 3.0 🔑 核心发现：r12 对 main 的净增量是 **0**

**逐文件比对 r12 工作区 36 项与 `llmke-v2` 工作区**：

```bash
for f in $(git -C /home/szf/data/dev/llmke-r12 status --porcelain | awk '{print $2}'); do
  [ -f "/home/szf/data/dev/llmke-r12/$f" ] || continue
  if [ ! -f "/home/szf/data/dev/llmke-v2/$f" ]; then echo "r12独有: $f"
  elif cmp -s "/home/szf/data/dev/llmke-r12/$f" "/home/szf/data/dev/llmke-v2/$f"; then echo "相同: $f"
  else echo "不同: $f"; fi
done
```

**结果**：

| 分类 | 数量 | 说明 |
|---|---|---|
| 与 v2 **逐字节相同** | **23** | 含 A 类 `#17/18` v2Ingest、`#19` doSuccess、`#11` doc2mdDir、`#34` V2GraphProxy、`#35` RemoteV2IngestUtils、`#23` RemoteGraphUtils(+9 行) |
| 与 v2 **不同** | **6** | `r12-watchdog.sh`(B)、`application-r12.yml`(B)、`last-run.json`(C)、`multiple_retrieval.py`(**D，v2 更新**)、`retrieval_service.py`(**D**)、`AiServiceImpl.java`(**D**) |
| **r12 独有（v2 无）** | **3** | **全部是 `.bak-*` 备份文件**（`*.yml.bak-20261102` ×2、`es.py.bak-p4l13c`）— C 类可丢 |

**逐项抽验**：

```
#34  V2GraphProxyController        v2 md5 == r12 md5（9758ee94）    ✅ 完全相同
#35  RemoteV2IngestUtils           v2 184 行，与 r12 相同           ✅
#36  RetrievalEndpointStartupCheck v2 127 行                        ✅ 存在
#10  es.py                          v2 596 行                       ✅ 存在
#11  FileParseTaskInfo(doc2mdDir)   两边相同                        ✅
#7   reranker rrf_k                 两边均为 60                     ✅
#9   global 切 18094                V2_GRAPH_URL=18094 两边相同      ✅
#16  @Lazy                          v2 命中 3                        ✅
#23  RemoteGraphUtils(+9 行)        两边完全相同                     ✅
```

**结论（待专家复核）**：

> **r12 工作区对 main 的净增量 = 0。**
> 所有 A 类修复均在 v2 中；r12 独有的只有 3 个 `.bak-*` 备份文件。

**这使方案从「两路合并」简化为「单路合并」**：只需把 `llmke-v2` 的工作合入 main，**无需从 r12 搬运任何代码**。

---

### 方案 A（推荐，保留 L1~L13）

#### 阶段 0 · 冻结与归档（不改任何分支）

1. 归档 v2 工作区（已完成）：`llmke-v2-wip-20261108T213218.tar.gz`
2. 归档 r12 工作区（**待做**）：同法打包 36 项
3. **不动** `stash@{0}`（11-03，来源不明）

#### 阶段 1 · 处理 r12（风险最低，先做）

事实：`feature/R12-real-rag` **无独有提交**（main 独有 274，R12 独有 0）。
⇒ 该分支**可直接删除**（内容全在 main 里）。

但 r12 **工作区有 36 项未提交改动**，其中经逐项比对：

| 类别 | 数量 | 内容 |
|---|---|---|
| **A 修 bug（必须进 main）** | **12** | `#7` reranker `rrf_k`、`#10` `es.py:_to_int_or_raw`、`#11` `doc2mdDir`、`#13` `IdType.AUTO`、`#14` `OperationLogAspect`、`#17/18/19` v2Ingest 三件套、`#34` `V2GraphProxyController`(114 行)、`#35` `RemoteV2IngestUtils`、`#36` `RetrievalEndpointStartupCheck` |
| B 环境配置（留部署侧） | 9 | watchdog、yml、r12.target、`@Lazy`、245MB 数据目录 等 |
| C 临时调试（可丢） | 6 | `*.bak-*`、验收结果目录 |
| **D 已被覆盖（禁止搬，搬 = 回退）** | **9** | 见 §3.1 |

#### 3.1 ⚠️ 三项禁止搬进 main（会删掉 v2 已有的修复）

| # | 文件 | 依据 |
|---|---|---|
| 6 | `multiple_retrieval.py` | v2 648 行（含 `_original_kb()` + `file_id` term）；r12 仅 640 行 |
| 8 | `retrieval_service.py` | v2 已含 `enabled_graph` 早退修复（`:453`） |
| 25 | `AiServiceImpl` | v2 已含 R15-F05 reference 回落（`:395`） |

**这三项在 r12 侧有改动，但 v2 侧更新。若按「r12 有改动就搬」处理，会回退。**

#### 阶段 2 · 合并 A 类 12 项（三组，顺序固定）

- **组 1（可独立）**：`7`、`10`、`13+14`（同批）、`34`、`36`
- **组 2（必须成组，顺序不可换）**：`11 → 35 → 17/18 → 19`（中间态编译不过）
- **组 3（需改造）**：`9`（把 `18094`/`19200` 硬编码提为配置）

**合入后安全边界**：`remote.v2-ingest.url` 默认空 ⇒ `enabled()=false` ⇒ 生产行为不变。

#### 阶段 3 · 切生产启动路径

待决策（见 §四）。

---

### 方案 B（若选解读 B：一切作废）

1. 确认 tar 归档可恢复；
2. 删除 `feat/spectra-theme`、`feature/R12-real-rag` 等本地分支；
3. 生产直接以 main 部署；
4. **接受 L1~L13 工作全部不进生产**。

**风险**：main 上存在 §1.4 的两个缺陷，会随部署进入生产。

---

## 四、待评审/待裁定问题（请专家给出独立意见）

| # | 问题 | 为什么需要外部判断 |
|---|---|---|
| 1 | **§二 的歧义应取解读 A 还是 B** | 决定 L1~L13 是否保留，作者无权代选 |
| 2 | **§1.4 缺陷 A 是否真为缺陷** | 作者判断「不支持 kb 路由 = 所有库读同一快照」，需验证 18094 侧 `/v2/graph/view` 是否真的只认单一快照 |
| 3 | **§1.4 缺陷 B 的 `fail-fast:true` 是否符合设计意图** | 可能是「宁可不起也不带病起」的有意设计 |
| 4 | **「三项禁止搬」（§3.1）是否成立** | 需逐文件比对 v2 与 r12 的实际内容 |
| 5 | **A 类 12 项的分组是否会导致中间态编译失败** | 需实际构建验证 |
| 6 | **是否应保留 `stash@{0}`** | 来源不明，可能含他人工作 |
| 7 | **245 MB 生产数据是否应进 `.gitignore`** | 作者认为应进，但可能与其他环境约定冲突 |

---

## 五、作者在本会话中已发生的错误（供评审者评估本文可信度）

**事实性错误（已被他人纠正）**：

| # | 错误 | 纠正者 |
|---|---|---|
| 1 | 将端口 `18081`（rag-auth-service）误认为 graph-service（实为 `18084`），**连续两次** | 成员 |
| 2 | 采信「部署仓已有 `V2GraphProxyController`」，实际是 `cp -p` 保留 mtime 造成的假象 | 成员 |
| 3 | 端点计数 17，实际 18（漏 `GET /file/pageNum`） | 成员 |
| 4 | 把「同一仓库三 worktree」当成「两个独立仓库」，据此设计了不存在的「A→B 同步规则」 | 自查后更正 |
| 5 | 验收命令 3 处会给出错误信号（查 yml 而值在 Java、curl 缺 `Content-Type` 致 500、`fail-fast` 查错位置） | 成员 |
| 6 | 判据 `HTTP 502` 实际应为 `207`（误抄 `ERROR_HTTP` 表，未看实际路径） | 自查 |

**根因（作者自我分析）**：多次以「记忆中的端口/路径/数字」代替现查，属方法问题而非偶发。

**因此建议评审者对本文所有「判断」类内容独立验证，仅将 §一 的可复跑事实作为起点。**

---

## 六、给外部专家的评审提示词（可直接复制使用）

```text
你是外部技术评审专家。请独立评审一份「代码分支收敛方案」，不要预设方案正确。

## 背景
一个仓库（github: shaozhongfei001/llmke）有三个 worktree：
  /home/szf/data/dev/llmke      → main（干净，无未提交改动）
  /home/szf/data/dev/llmke-v2   → feat/spectra-theme（131 项未提交，无远程分支）
  /home/szf/data/dev/llmke-r12  → feature/R12-real-rag（36 项未提交，落后 main 274 提交且无独有提交）

所有者要求「以 main 为准，其他都是无效的」，并希望把分散的工作收敛到 main。

待评审文档：/home/szf/data/dev/llmke-v2/docs/v2-tasks/CONVERGE-TO-MAIN-EXPERT-PACKAGE.md
配套材料：/home/szf/data/dev/llmke-v2/docs/v2-tasks/loops/MERGE-TO-MAIN-PLAN.md
证据日志：/home/szf/data/dev/llmke-v2/docs/v2-tasks/evidence/R12-36items-triage-*.log

## 你的任务
1. **独立复跑**文档 §一 的每条验证命令，确认数字是否属实。不要采信文中结论。
2. **判断 §二 的歧义**（「其他都无效」= 代码基线以 main 为准，还是 v2/r12 全部丢弃）。
3. **逐项复核 36 项分类**（A 修 bug 12 / B 配置 9 / C 可丢 6 / D 已被覆盖 9）是否正确，特别是：
   - 被判 D（禁止搬）的 #6/#8/#25 是否真的「v2 更新」；
   - 被判 A 的 #34 `V2GraphProxyController` 是否真的「替换而非新增」。
4. **验证 §1.4 两个缺陷是否成立**：
   - main 的 `/v2WholeGraph` 是否真的不支持按 kb 路由（若成立，所有库会读同一快照）；
   - `fail-fast:true` 是否为有意设计。
5. **评估合并顺序**（§三 阶段 2 的三组）是否真的能保证每一步可编译。
6. **指出文档中任何未经验证就下结论的地方**。

## 约束
- 所有操作**只读**：不 commit / 不 merge / 不 delete branch / 不重启服务。
- 不要相信作者的历史结论——文档 §五 已列出作者 6 次事实性错误。
- 若发现文档事实有误，请明确列出「文档说 X，实测 Y」。

## 交付
- 每条结论附：命令 + 原始输出 + 你的判断；
- 明确列出「可确认 / 不可确认 / 文档有误」三类；
- 对 §四 的 7 个问题逐一给出你的意见；
- 最后给出：**你推荐的收敛路径**，以及**你认为最可能造成不可逆损失的步骤**。
```

---

## 七、作者的最后一句

本文不请求信任，只提供可复跑的验证入口。**若 §一 任一数字与实测不符，请以实测为准。**
