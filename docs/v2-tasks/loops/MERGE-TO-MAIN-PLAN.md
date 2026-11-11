# 收敛到 main 的执行计划（R12 worktree 36 项 + v2 130 项）

> 背景：`llmke`(main) / `llmke-v2`(feat/spectra-theme，无远程) / `llmke-r12`(feature/R12-real-rag，落后 main 274 提交) 是**同一仓库的三个 worktree**。
> 依据：`R12-36items-triage-20261108T212000.log`（A12/B9/C6/D9）+ TL 独立核实。

---

## 零、不可跳过的前置

1. **v2 工作区已备份**：`/home/szf/data/dev/llmke-v2-wip-20261108T213218.tar.gz`（174 MB / md5 `3730cd2c…`），**不在 `/tmp`**。
2. **删分支必须在 A 类合并之后** —— 否则 12 项修复蒸发。
3. **不动 `stash@{0}: On main: llmke-main dirty snapshot 20261103`** —— 不是本次产生，去留待 Owner 定。

---

## 一、A 类 12 项：合并顺序与分组

### 组 1 · 可独立直接摘（6 项）

| # | 内容 | 备注 |
|---|---|---|
| 7 | `reranker` `rrf_k 5→60` + 按 pk 去重 | 独立 |
| 10 | `es.py:_to_int_or_raw` | 独立（修 19527 int 强转） |
| 13 | `IdType.AUTO` | **与 14 同批**（同源故障） |
| 14 | `OperationLogAspect` 吞异常 | **与 13 同批** |
| **34** | **`V2GraphProxyController` 整文件替换** | **见 §三 验收判据，最高风险** |
| 36 | `RetrievalEndpointStartupCheck` | **见 §四 硬要求** |

### 组 2 · 必须成组，顺序不可换（5 项）

```
11 (doc2mdDir) → 35 (RemoteV2IngestUtils) → 17/18 (v2Ingest 三件套) → 19
```

- 中间态**编译不过**，必须一次提交或按此顺序连续提交；
- 合入后 `remote.v2-ingest.url` 默认空 ⇒ `enabled()=false` ⇒ **生产行为不变**（这是安全边界，别顺手改）。

### 组 3 · 需改造后再进（1 项）

| # | 改造内容 |
|---|---|
| 9 | `global` 切 18094 —— 把硬编码的 `18094` / `19200` 提为配置项 |

---

## 二、❌ 三项**禁止搬进 main**（搬 = 回退）

| # | 文件 | 为什么 |
|---|---|---|
| 6 | `multiple_retrieval.py` | v2 是 **648 行**（含 `_original_kb()` + `file_id` term）；r12 仅 640 行 → 搬过去**删掉 v2 的修复** |
| 8 | `retrieval_service.py` | v2 已含 `enabled_graph` 早退修复（`:453`） |
| 25 | `AiServiceImpl` | v2 已含 R15-F05 reference 回落（`:395`） |

**这三项在归类里是 D（已被覆盖），不是 A。** 判据是「比对三份代码」，不是「哪边有改动」。

---

## 三、`#34` 的合并验收判据（**最高风险，必须验**）

### 为什么危险

```
origin/main  87 行   spaceName|kb 命中 0
             :45  String url = v2GraphApi + "/v2/graph/view"   ← **不带 kb**
r12 工作区   114 行   spaceName|kb 命中 7                      ← 有 kb 路由
```

**main 上所有库读同一快照。** 若把 114 行版当「新文件」合入（而非整文件替换），缺陷会保留 —— 而接口**照常返回 200**，没人会发现。

### 已实测的基线（当前 114 行部署版）

```
{"spaceName":"kb_9"}           → 200 ｜ nodes=114 ｜ edges=94 ｜ notice=None
{"spaceName":"kb_nonexistent"} → 200 ｜ nodes=0   ｜ edges=0  ｜ notice="知识库 kb_nonexistent 尚未构建图谱"
{}                             → 200 ｜ nodes=0   ｜ notice="缺少 spaceName（知识库标识），无法定位该库图谱"
```

### 合并后必须复现这三行

- **`kb_nonexistent` 必须 0 节点 + notice**；
- **若返回 114** ⇒ 替换没生效，缺陷仍在；
- `{}` 必须走「缺少 spaceName」分支。

**main 的 87 行版做不到第二行**（不带 kb，假库会拿到 kb_9 的快照）—— 这就是判据。

---

## 四、`#36` 的合并硬要求

### TL 原判断被修正

我原以为风险是「配置键在 main 对不上」。**实际不是**：

```
main 的 NacosConfig 已有：
  @Value("${spring.ai.gt.search-docs-global-url:http://127.0.0.1:19995/retrieval_documents_global}")
```

**`@Value` 自带默认值 ⇒ 5 个键全部能解析出非空值 ⇒ 不会因「键缺失」fail-fast**。

**因此 `#3（qa yml 加 key）` 不需要搬进 main。**

### 真正的风险：可达性

main 拓扑（19995/19996）与 r12 不同。端口不可达时，`fail-fast=true` 会**阻止服务启动**。

### 硬要求（收敛为一条）

> **`rag-qa.startup-check.fail-fast` 默认必须是 `false`。**
> `true` 只允许在明确知道拓扑的环境（r12）里显式打开。

**这比「去硬编码路径」更关键**：硬编码只影响提示文案，`fail-fast` 直接影响可用性。

---

## 五、待 Owner 决策（四项）

| # | 决策点 | TL 建议 |
|---|---|---|
| 1 | **A 类 12 项怎么切 commit** | 按 §一 的三组；组 2 的 5 项一次提交（保证可编译） |
| 2 | **`/commonSearch` 是否废弃** | `#12/15/24/26` 是一组，**只搬一半会编译失败**。需先确认该对外契约去留；若不废弃，这 4 项暂不动 |
| 3 | **`stash@{0}` 去留** | 11-03 的 `llmke-main dirty snapshot`，非本次产生。**收敛前先确认是否有价值**，别顺手清 |
| 4 | **`platform/r12/data/` 245 MB** | **立即加 `.gitignore`**（不进 main）。现未 ignore，挂 `git status` 里拖慢且易误提交 |

---

## 六、B 类里唯一建议进 main 的（1 项）

| # | 内容 | 理由 |
|---|---|---|
| 16 | `@Lazy` | **main 已经有 87 行版 `V2GraphProxyController`，说明 main 的图谱页也走 18094 ⇒ 同一个 `@Bean` 是「已埋在 main 里的坑」，不是「将来可能」。** main 退役 Nebula 时会以同样方式起不来，而那时没人记得为什么 |

**这是「现存缺陷」而非「前瞻建议」。**

---

## 七、验收总判据（合并后逐条跑）

> ⚠️ **初版五条有 3 条会给出错误信号**（1 个假故障 + 2 个假通过），已按实测修正。
> 教训：**判据必须指向正确的证据源** —— 查 yml 而值在 Java、curl 缺 header 返回 500，都会让人得出相反结论。

```bash
# 0) 必须在模块根目录跑，否则 -pl 解析不到模块
cd services/rag-java/rag-parent

# 1) 编译（组 2 之后必须能过）
mvn -o -pl rag-index-service,rag-qa-service -am -DskipTests package

# 2) v2-ingest 未启用（安全边界）
#    ⚠️ 该键**在两个仓的 yml 里都不存在**（关闭靠 Java @Value 默认空串），
#       查 yml 会 0 命中，分不清「未启用」和「命令写错」。必须查两处：
grep -c 'v2-ingest' platform/r12/conf/rag-index-service/application-r12.yml   # 期望 0
grep -n 'remote.v2-ingest.url:' services/rag-java/rag-parent/rag-index-service/src/main/java/com/gientech/ragindexservice/infrastructure/RemoteV2IngestUtils.java
#    期望：@Value("${remote.v2-ingest.url:}")   ← 默认空 ⇒ enabled()=false

# 3) #34 的分 kb 判据（见 §三）
#    ⚠️ 必须带 Content-Type: application/json —— 不加会返回 500
#       （Content-Type 'application/x-www-form-urlencoded' is not supported）
#       会把「接口正常」误判成「合并改坏了」
curl -s -X POST http://127.0.0.1:18084/graph/search/v2WholeGraph \
  -H 'Content-Type: application/json' \
  -d '{"spaceName":"kb_nonexistent"}' \
| python3 -c 'import json,sys;i=json.load(sys.stdin)["data"];print(len(i.get("nodeList") or []), i.get("notice"))'
#    期望：0 知识库 kb_nonexistent 尚未构建图谱
#    若输出 114 ⇒ 替换没生效，main 的「所有库读同一快照」缺陷仍在

# 4) fail-fast 默认必须是 false
#    ⚠️ **默认值在 Java，不在配置**：
#       RetrievalEndpointStartupCheck.java:53  @Value("${rag-qa.startup-check.fail-fast:true}")
#       只在 yml 加 fail-fast: false 是**无效**的 —— main 没该配置时仍按 Java 默认 true 阻断启动
grep -n 'startup-check.fail-fast' \
  services/rag-java/rag-parent/rag-qa-service/src/main/java/com/gientech/ragqaservice/infrastructure/RetrievalEndpointStartupCheck.java
#    期望：@Value("${rag-qa.startup-check.fail-fast:false}")

# 5) 245 MB 不被跟踪
#    ⚠️ 三个 worktree 共用 .git，`git -C` 指错会给出永远 OK 的假阳性
git -C /home/szf/data/dev/llmke-r12 check-ignore -v platform/r12/data
#    期望：有输出（命中 .gitignore 规则）；无输出 = 未忽略
```

### 三个「假信号」的成因（避免再犯）

| # | 症状 | 成因 | 危害 |
|---|---|---|---|
| 2 | grep 0 命中 | 键不在 yml，在 Java `@Value` 默认值里 | **假通过**：以为「未启用」，实际可能配了 |
| 3 | curl 返回 500 | 缺 `Content-Type: application/json` | **假故障**：以为合并改坏接口 |
| 4 | grep 0 命中 | `fail-fast` 默认值在 `.java:53`，不在 yml | **假通过**：以为默认已 false，实际仍 `true` 会阻断启动 |

**第 4 条是当前真实风险**：`@Value(...:true)` 意味着 main 上「启动检查端点不可达 → rag-qa 起不来」。**这是已存在的缺陷，不是合并引入的。**

### 可复用模板：负例必须配同源正例

```bash
neg=$(grep -c "$KEY" "$FILE")          # 期望 0
pos=$(grep -c "$KNOWN_KEY" "$FILE")    # 期望 ≥1（**同一文件、同一命令**）
[ "$neg" = 0 ] && [ "$pos" -ge 1 ] \
  && echo "PASS: $KEY 确实不存在（并已证明 grep 有效）" \
  || echo "FAIL/无法判定"
```

**理由**：「0 命中」既可能是「符合预期」，也可能是「文件读错 / 命令写错 / 证据源找错」。**只有配同源正例，0 才能被证伪。**

### 已实测的负例 + 正例（可直接抄）

| 判据 | 负例（期望） | 同源正例（证明命令有效） |
|---|---|---|
| `v2-ingest` 未配置 | `grep -c 'v2-ingest' application-r12.yml` → **0** | `grep -c 'generate-graph'` → **2**；`grep -c 'py-milvus-url'` → **1** |
| `fail-fast` 默认改为 false | `grep -c 'startup-check.fail-fast:false' RetrievalEndpointStartupCheck.java` → **0**（合并前） | `grep -c 'startup-check.fail-fast:true'` → **1**（现状）；`grep -c 'startup-check.enabled'` → **3** |
| 分 kb 判据 | `kb_nonexistent` → **0 + notice** | **同一管道**对 `kb_9` → **114** ⇒ 证明 0 不是解析失败/缺 header/端口不通 |

---

## 八、两个「已埋在 main 里的坑」的优先级（TL 排序，采纳成员判断）

| 风险 | 触发条件 | 排序 |
|---|---|---|
| **`fail-fast:true`**（`RetrievalEndpointStartupCheck.java:53`） | **5 个端点中任一个 TCP 不通**就触发；**默认值就是 true**，无人配置也生效 | **① 优先** |
| `@Lazy` 缺失（`NebulaGraphConfig` `@Bean`） | 仅当「Nebula 已退役 + 该环境启动 graph-service」时触发 | ② 次之 |

**结论**：`fail-fast` **概率更高**（拓扑差异大、端点任一不通即炸），且**默认值生效无需人配** —— 应排在 `@Lazy` 之前。

**修复只需一行**：`RetrievalEndpointStartupCheck.java:53` 的 `:true` → `:false`。

**无行为副作用**：r12 等明确知道拓扑的环境仍可在配置里显式写 `fail-fast: true`。

**这一条与合并无关，是独立缺陷** —— 即使不做收敛，也建议先修。
