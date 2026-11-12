# STEP2-K `graph_root` 语义澄清与 B-2 条件裁定复核（2026-11-12）

> Owner 问题：①「请求带 `graph_root`/`graph_api`」是否合理且更佳？② `graph_root` 的业务含义是否指知识库中的「一个库」？③ 若按此理解是否就要求「在特定的领域图谱范围内检索」？④ 在此前提下裁定 B-2 = 「`QueryRequest` 增 `root`（需 CR）」。
> 本轮性质：**只读核实 + 纯函数实证**。未改任何代码/契约/数据，未启动/停止/重启服务，未 commit。
> 结论摘要：**② 的前提不成立**（`graph_root` 不是「一个库」，`kb` 才是）；因此 ④ 的条件裁定不自动生效，本轮不执行 (b)，请 Owner 重新裁定。

---

## 一、事实：`graph_root` 是「落盘根 / 环境命名空间」，不是「一个库」

| 证据 | 内容 |
|---|---|
| `02-CONTRACTS.md:24` | `graph_root` 示例值 = `/home/szf/data/dev/llmke-r12/platform/r12/data/graph-root`（一个绝对目录路径） |
| 实测目录 | 同一个 `app/.../data/graph-root/` 下同时有 `kb_9/`（`documents=46`，11 文件）、`kb_1004/`（`documents=4520`，1 文件）、顶层 `current.json`（`documents=3`）与两个顶层单快照 |
| `delta_build.py:51-58` | `_kb_root(kb, root)`：`base = root or LLMKE_V2_ROOT or DEFAULT_ROOT` → `os.path.join(base, kb)`，即**实际落点是 `<graph_root>/<kb>`** |
| `api.py:208-231` | `_resolve_snapshot` 注释：「per-kb 布局：`<root>/<kb>/current.json`（**多库各自建图的落点**）」 |
| `02-CONTRACTS.md` 字段表 | `kb` = primitiveName，如 `kb_9`；契约 `QueryRequest` / `GraphQueryRequest` 用 `kb_id` 表示库 |

**判断**：`graph_root` 是容纳多个库、区分 **shadow 环境 vs app 生产环境** 的存储根；「知识库中的一个库」是 `kb` / `kb_id`。两者是不同层：`root` 决定「哪个环境的数据」，`kb` 决定「哪个库/领域图谱」。

---

## 二、事实：「在特定领域图谱范围内检索」已由 `kb` 实现，且不是 B-2 根因

- 现有链路：`QueryRequest.kb` → `engine_for_kb(kb)` → `snapshot_for(kb)` → `_resolve_snapshot(kb)` → `<root>/<kb>/current.json`；`kb.json` 的 `kb_id` 由 `_snapshot_owner()` 校验，**杜绝串库假数据**（`api.py:168-185`）。
- 真正对应「按库灰度切读」的设计是 `INGEST_READ_MODE=snapshot` + `INGEST_READ_KBS=[kb_9]`（STEP2-F 路径 B、`docs/policies/RUNTIME-SWITCHES.yaml`），其 `scope` 明写「按库灰度」，且 STEP2-F 明确「**无需改图根目录**」。该开关在 18096 当前代码未实现（T-D2MD-17 原设计）。
- **B-2 的真实根因**：18094 启动时只有 `LLMKE_V2_SNAPSHOT`（指向顶层单快照、`documents=3`），**没有 `LLMKE_V2_ROOT`** → `_root_dir()` 回退空的 `.artifacts/api-root` → 按库指针解析失败 → 顶层单快照无 `kb.json` 不被认领 → `NOT_BUILT`。生产 `kb_9` 的 46/11 快照一直在 `<app graph-root>/kb_9/`，只是 18094 没去那儿读。

### 纯函数实证（零风险、可复跑）

```
cd llmke/services/rag-alg/index_data_service
PYTHONPATH=. <hipporag-toolenv>/bin/python -c \
  "from graph_engine_adapter.api import _resolve_snapshot; print(_resolve_snapshot('kb_9'))"

A) 不设 LLMKE_V2_ROOT（现状）        -> None                 # 复现 B-2
B) LLMKE_V2_ROOT=<app graph-root>    -> <app>/graph-root/kb_9/snapshot-20261107212905-365431-g0
```

附带发现：`kb_1004` 在 B 下仍为 `None`，因其 `current.json.dir` 仍指向已删 `llmke-r12/...`（另一个失效指针，与 `kb_9` 已修的同类问题），另立条目，不在本轮处理。

**判断**：方案 (a)「重启 18094 并设 `LLMKE_V2_ROOT`」是**针对根因的最小解**：代码原生支持 per-kb 布局，零契约变更、零代码改动。

---

## 三、判断：「请求带 `graph_root`」是否合理且更佳 —— 必须分层回答

### 写入侧（18096 → 18094 delta / revoke）：合理，是 PLAN 的刻意要求，但非无条件「更佳」

- `docs/v2-tasks/loops/P4-L13C-PLAN.md:29`：「**C 段所有 ingest 请求必须显式带 `graph_root`**，指向影子目录」，理由是 `graph_root=None` 会默认落到 18094 的线上图；`FenceRevokeRequest` 更因 P4-L13C 事故（影子撤权写进生产 `fence.json`）要求「revoke 必须显式指定 root，禁止回落到 env」。
- 因此 `IngestRequest.graph_root` / `DeltaRequest.root` 作为**请求字段**是刻意的 fail-closed 设计，不是「字段写错了」。**更正 STEP2-J 的表述**：上一轮称其为「实现未消费已有字段的缺陷」不够准确，准确说法是「`service.run` 路径未兑现 PLAN 的『显式带 root』要求」。
- **缺口**：请求级 root 必须有服务端白名单/校验，否则任意调用方可指定任意路径写图。上一轮的修正**没有白名单**，不能无条件称为「更佳」；补白名单需 CR + 兼容去向。

### 查询侧（`QueryRequest` 增 `root`）：不是更佳，且不对症

1. **语义错位**：查询方（Java/前端经 19532）不应能选择「读哪个环境/存储根」；这把部署级配置下沉为请求参数，与 P2-L8「隔离由服务端 `INGEST_READ_*` 运行时开关控制、默认 legacy、运行态零注入」相悖。
2. **语义重复**：「限定领域图谱范围」已由 `kb` / `kb_id` 完成，再加 `root` 并不提供该能力。
3. **不解决根因**：B-2 是 18094 env 没设；加 `root` 后仍须改 `query` 路由 → `snapshot_for(kb, root)` → `_resolve_snapshot`（后者已支持 root 参数），**且仍要重启 18094** —— 与 (a) 同等重启成本，却多背一个契约边界。
4. **契约成本实打实**：`QueryRequest` 登记在 `contracts/schema/llmke-document-pipeline-v2.json:1547` 与 `contracts/api/llmke-document-pipeline-v2.openapi.yaml:576`；`GraphQueryRequest` 在 `contracts/schema/llmke-core.json:1212` / `api/llmke-graph.openapi.yaml:158`。两者字段集**均无 root**、均以 `kb_id` 表示库。加字段要改合同源 → `make generate && make check` → CR → 消费者（19532 / Java）回放。
5. **安全面扩大**：调用方可跨 shadow/生产读，且 `kb.json` 归属校验只防串库、不防跨环境。

---

## 四、历史裁定回溯（如实登记，避免代做决定）

- `docs/v2-tasks/evidence/P4-L13C-R0-20261108T162933.log:45-65` 曾把「(A) 用 env（无需改代码） vs (B) 改代码让 `_delta_runner` 优先取 `req.graph_root`」列为**需 Owner 裁定**，并写「PLAN 要求所有 ingest 必须显式带 graph_root，这条没有例外 —— 所以这条必须你定」。**未见裁定结论**。
- **如实登记**：上一轮（STEP2-J）我直接按 (B) 修改了发布树 `kb_ingest_service.py`，等于代做了一次未裁定的设计决定。该改动方向符合 PLAN「显式带 root」意图，但缺白名单，且未经 CR/兼容决议；本轮不擅自回退（Owner 上一条明确要求请求驱动），留待本次裁定一并确认。

---

## 五、条件裁定的处理与待裁定项

Owner 的裁定是**条件式**的（「假如我的理解正确前提下」）。经 §一 核实，`graph_root = 一个库` 的前提**不成立**，故 **(b)「`QueryRequest` 增 root」不自动生效，本轮未执行、未改契约、未提 CR**。请 Owner 在澄清后重新裁定：

| 选项 | 内容 | 成本 | 备注 |
|---|---|---|---|
| **(a) 推荐** | 授权窗口内重启 18094 并设 `LLMKE_V2_ROOT=<app graph-root>` | 零契约/零代码改动，一次重启 | 已由纯函数实证对 `kb_9` 有效；`kb_1004` 指针另修 |
| (b) | `QueryRequest` 增 `root` + 白名单 + CR + 合同源 generate/check + 消费者回放 | 高，且仍需重启 18094 | 需说明「为何查询方应能选择存储根/环境」这一设计前提 |
| (c) | 维持 STEP2-J 的 (c)：验收只看 `current.json` 的 `documents`/`fingerprint.files` 指纹，「查询可读」记为已知限制 | 零 | B-2 保持未验收，不解锁 18 |
| 另立 | 若目标是「按库灰度切读」，应实现 `INGEST_READ_MODE` / `INGEST_READ_KBS`（路径 B） | 独立工作量 | 属 T-D2MD-17 原设计，与 `root` 无关 |

另需一并裁定：写入侧请求级 `graph_root` 是否保留（(B)），若保留须补白名单 + CR；或改回 (A) env 驱动，隔离演练改用独立实例 env 注入。

---

## 六、纪律留痕

- 本轮仅执行 `grep` / `cat` / `sed` / 只读 `python -c`（`_resolve_snapshot` 纯函数），无写盘、无网络调用、无服务重启。
- 8 个生产端口未变；生产 `platform/r12/data` 未写入；未改 `contracts/`；未 `make generate`；未提 CR。
- 未执行 `git add` / `git commit`；`T-D2MD-17` 保持 `IN_PROGRESS`、`T-D2MD-18` 保持 `TODO`；未签 `QA_PASS`。
- 事实（§一/§二）与判断（§三）分离；判断为基于代码路径与契约登记的推断，可由 Owner 裁定推翻。
