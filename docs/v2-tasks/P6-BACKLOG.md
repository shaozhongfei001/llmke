# P6 BACKLOG（P4-L13-C 期间登记，**本 loop 一律不改**）

> 本文件只登记**已确认**的遗留项，每项含：现象 / 根因 / 影响 / 修法 / 发现 loop / 证据。
> 排序按「误读风险」从高到低，不按工作量。

---

## 1. `/health` 与闭包「两处读取」同一个 env

| | |
|---|---|
| **现象** | `/health.graph_api` 每次请求重读 `os.environ`（`kb_ingest_service.py:338`），而实际用于发请求的是 `_build_service()` 启动时读入并绑进闭包的值（`:254`、`:261`）。当前两者恰好一致。 |
| **根因** | 同一判断两处读取。 |
| **影响** | 若将来支持运行中改 `os.environ`（热更新、测试注入）：`/health` 会显示新值、实际仍用旧值 —— **恰好在「核对自己是否生效」这个最需要它诚实的场景里骗人**。 |
| **修法** | 把**实际绑定的值**存进 app state（例如 `app.state.bound_graph_api`），`/health` 读它而不是重读 env；补一条断言「health 值 == 闭包实际使用的值」。 |
| **发现 loop** | P4-L13-C（TL 21:3x 指出） |
| **证据** | `P4-L13C-C5-RUNBOOK-20261108T183100.log` §6 |

---

## 2. 契约 §2.2 的三项响应字段未实现

| | |
|---|---|
| **现象** | 18094 `POST /v2/graph/delta` 的响应缺：`sources{written,entries}`（现在只有整数 `sources: N`）、`fence{generation,revoked}`、`fallback_reason`。 |
| **根因** | L9 实现时按需拼响应，未对照 §2.2 全字段；缺陷 9 只补了 `apply_result`。 |
| **影响** | 调用方拿不到「sources 是否写成、写了多少条」「本次 fence 代次与撤权集合」「本次是否走了 full 及原因」；§2.2 的完整性无法机器校验。 |
| **修法** | `delta_build` 拼响应时补齐三块；`sources` 从整数改为 `{written, entries}` 会**破坏向后兼容**，需与 Java 侧同步（或加 `sources_detail` 新键）。 |
| **发现 loop** | P4-L13-C（缺陷 9 修复时确认剩余三项） |
| **证据** | `P4-L13C-fix11-9-12-20261108T182854.log` §2 |

---

## 3. 计数口径并列易误读：`documents`（live 行）vs `remaining`（去重文本）

| | |
|---|---|
| **现象** | 同一响应里 `documents=5` 而 `apply_result.remaining=4`。 |
| **根因** | `documents = len(live)`（live 行数，一条 doc 有 N 个 `file_ids` 就 N 行）；`remaining/expected` 是**去重后的文本数**（引擎按文本哈希合并块）。 |
| **影响** | 调用方第一反应是「两个数对不上」，可能误判为漏块或多块；对账脚本会算错。 |
| **修法** | 二选一：① 响应里明示口径（如 `documents` 改名为 `live_rows`，或加 `documents_dedup`）；② 契约 §2.2 注释写死「documents = live 行数，非去重块数」。**倾向 ②**（不改字段名，避免破坏 Java 侧）。 |
| **发现 loop** | P4-L13-C（1:N 验证时实测，TL 22:3x 并入 P6） |
| **证据** | `P4-L13C-C5-DRILL-20261108T200500.log` §8.4 |

---

## 4. HTTP 语义：同一个 `GRAPH_API_UNREACHABLE` 两条路径两种码

| | |
|---|---|
| **现象** | 经 `KbDeltaService.commit()` 捕获 → **207 PARTIAL**（写进 `graph.error`）；经 `kb_pipeline.py:216` 抛出 → **502**。 |
| **根因** | delta 路由把「图不可达」当**软失败**（索引已落、可重放）；L7 旧路径把它当**硬失败**。 |
| **影响** | 调用方无法只看 `code` 判断严重性，必须看 `status`；两个入口对同一故障给出不同结论，容易被写成「同一个错误码两种含义」。 |
| **修法** | **不是死代码，是两条路径两种语义** —— 要么给软失败换独立 code（如 `GRAPH_UNREACHABLE_SOFT`），要么在契约 §5 明确「同 code 在不同入口的 HTTP 码以 `status` 为准」。**改即动 L7 已验收语义，Must 先对齐 P5/P6。** |
| **发现 loop** | P4-L13-C（C5 演练判据 ① 暴露；TL 22:1x 认定判据写错、实现正确） |
| **证据** | `P4-L13C-C5-DRILL-20261108T200500.log` §1、§8.1、§10 |

---

## 5. 命名不一致：`GRAPH_API_UNREACHABLE`（代码）vs `GRAPH_UNREACHABLE`（契约 §5）

| | |
|---|---|
| **现象** | 代码里两处都用 `GRAPH_API_UNREACHABLE`；契约 §5 的表写 `GRAPH_UNREACHABLE`。错误码表里登记了一行「`GRAPH_API_UNREACHABLE` = 契约名 `GRAPH_UNREACHABLE` 的别名」。 |
| **根因** | L7 先实现、契约后统一；改名会动 L7 已验收语义。 |
| **影响** | 文档与代码对不上；新增调用方按契约写会匹配不到。 |
| **修法** | 二选一：① 代码改名 + 表删别名（需 L7 授权）；② 契约 §5 增加「别名」一列，明确两者等价。**倾向 ②**（不动已验收代码）。 |
| **发现 loop** | P4-L13-C（A 段建表时登记） |
| **证据** | `P4-L13C-C3b-C4-INCIDENT-20261108T182000.log` §2/#；`kb_ingest_service.py` `ERROR_HTTP` 注释 |

---

## 6. `POLICY_INVALID` 的 HTTP 码依赖「参数来源」

| | |
|---|---|
| **现象** | 现在 `POLICY_INVALID` → **500**（chunk_chars / overlap 非法，均来自服务端默认值 = 部署缺陷）。 |
| **根因** | 参数目前在服务端配置里，不在请求体。 |
| **影响** | 若将来 policy 参数进请求体，「用户传了非法值」返回 500 会误导调用方排查服务端。 |
| **修法** | **代码处已注释**：「若将来 policy 参数进请求体，须改回 400」，并已有断言「`POLICY_INVALID` 不得返回 400」。届时改表一行 + 改断言方向。 |
| **发现 loop** | P4-L13-C（Q8 建表时登记） |
| **证据** | `kb_ingest_service.py` `ERROR_HTTP` 注释；`P4-L12` 证据 Q8 段 |

---

---

## 7. 部署脚本「双副本」无任何一致性校验

| | |
|---|---|
| **现象** | `platform/r12/bin/` 有**两份**：源码仓 `llmke-v2` 与部署仓 `llmke-r12`，人工同步。实测 `up.sh`（`d94f9246` vs `12cfa300`）、`r12-watchdog.sh`（`1bb255d8` vs `ad09d0ce`）**不同**，而 `r12ctl.sh` 两侧**相同**（`2617e96c`）—— 说明是「按需人工同步」，不是镜像。 |
| **根因** | 没有校验机制。`up.sh verify` 只能验服务健康，**验不出「部署侧脚本与源码侧不一致」**。 |
| **影响** | 本次事故形态 =「改了源码侧、忘了同步部署侧」；下次可能是「同步了 `up.sh`、漏了 watchdog」。**没有校验就必然再犯。** 另注意：**Python 代码只有源码仓一份**（`r12-kb-ingest-start.sh:23` 的 `V2_SVC_DIR` 指向 `llmke-v2`，是有意设计），所以「双副本」只影响 `bin/` 与 `conf/`，不影响 L9~L13 的代码生效。 |
| **修法** | `up.sh verify` 或 `r12ctl.sh doctor` 增加一段：对比 `bin/` 下关键脚本（至少 `up.sh`、`r12-watchdog.sh`、`r12ctl.sh`）的 md5，与源码仓不一致 → **warn**（不 fail，避免阻碍正常运维），并在输出里给出两侧路径与 md5。 |
| **发现 loop** | P4-L13-C 收尾（补 D-1 门控时发现：`up.sh:132` 的 18096 条目只在源码仓） |
| **证据** | `P4-L13C-D1-GATE-20261108T204500.log` §1；本次 md5 对比见 §6 |

## 附录 A（**不属于 P6**）：L13-B 的 D-1 —— **补丁已落地、门控默认关闭**

| | |
|---|---|
| **当前状态** | 代码支持**已就绪**，但**门控默认关闭**、18096 仍由**人工手动管理** ⇒ **D-1 只算部分完成，不能写「D-1 通过」** |
| **落地位置** | `llmke-v2/platform/r12/bin/up.sh`（`d94f9246…`）、`llmke-v2/platform/r12/bin/r12-watchdog.sh`（`1bb255d8…`） |
| **改动内容** | ① `up.sh`：`up)` 门控启动（走 L13-B 的 `r12-kb-ingest-start.sh`，自检失败即 `exit 1`）；`verify)` 门控 must 三条（端口 / `/health` 200 / **`graph_api` 内容** / **`configured` 内容**）<br>② `r12-watchdog.sh`：`kb-ingest` 条目由「硬编码无条件纳管」改为「`LLMKE_INGEST_ENABLED=1` 才追加」；新增 `ingest_content_ok()`，**探针必须校验内容**，不只看端口 |
| **为什么探针要校验内容** | C5 演练实证：18096 进程活着、端口在听，但 `graph_api` 指向 `19999` —— 只看端口（甚至只看 `/openapi.json` 200）都会判健康，而每次摄取都是 207/PARTIAL。「进程活着但功能坏了」的典型 |
| **启用前置** | **Owner 决定把 18096 正式纳管时**，才在部署环境设 `LLMKE_INGEST_ENABLED=1`；开启后 watchdog 会接管 18096（含自愈重启），当前手动实例属「人工管理」 |
| **⚠️ 双副本问题（本节关键）** | 部署脚本有**两份**：`llmke-v2/platform/r12/bin/`（源码侧，本次改动在此）与 `llmke-r12/platform/r12/bin/`（**实际运行侧**，systemd `ExecStart` 指向它）。**部署侧两份文件至今仍无任何 18096 引用**（`grep -c 18096` 均为 0）⇒ 本次改动**在运行环境不生效**，需随部署同步。这正是「代码已合入 ≠ 线上已生效」 |
| **发现 loop** | 形态：P4-L13-C 收尾（只读核对）；双副本：P4-L13-C 补门控时发现 |

