# STEP2-M 生产窗口实录（T-D2MD-17 / 2026-11-12）

> Owner 授权：「放行生产窗口」。依据 `STEP2-L` 判定书 §七 的四步默认序列执行。
> 窗口：**18:20:03 → 18:36:18（+08:00，约 16 分钟）**。
> 纪律：不删失败凑 PASS；事实/判断分离；未 commit、未签 `QA_PASS`、未解锁 `T-D2MD-18`。

---

## 一、窗口前置（只读核对 + 可回滚备份）

### 服务身份（`/proc/<pid>/cmdline` + `cwd` + `environ`，不靠端口号推断）

| 端口 | PID | cwd | 关键 env |
|---|---|---|---|
| 18094 | 1464293 / 1466203 | `/home/szf/data/dev/llmke`（发布树） | `LLMKE_V2_SNAPSHOT=<app>/snapshot-20261111121015-000516-g0`、`PYTHONPATH=services/rag-alg/index_data_service`，**无 `LLMKE_V2_ROOT`** |
| 18096 | 46796 | `llmke-runtime/app/services/rag-alg/index_data_service` | shadow `GRAPH_ROOT`/`ARTIFACT_STORE`/`KB_STATE`、`GRAPH_API=18094`、ES/Milvus=19527/19526 |
| 19531 | 46795 | 同上 | `LLMKE_V2_ROOT=<app>/platform/r12/data/graph-root` |
| 19532 / 18097 | 1464291 / 181090 | 发布树 | upstream 18094 / ingest_url 18096 |

依赖服务实测全在：18090(embed)、18092(llama-server)、19526(Milvus)、19527(ES)、19996。

### 备份（`coordination/p6-window-20261112/`，`MANIFEST.sha256` 留痕）

`prod-kb9-current.json.before`（sha256 `fa650c7d…`）、`runtime-kb-ingest-service.py.before`、三个进程的 `env-*.before`、`cmdline.before`。

### 6 份 fixtures 的生产 file_id 映射（从生产 `sources.json` 提取，非猜测）

```
290    -> R12FIX-product-loan.docx      329 -> R12FIX-credit-ledger.xlsx
330    -> R12FIX-product-intro.pptx     332 -> docx-plain.docx
333    -> docx-table.docx               999019 -> docx-image.docx
（其余 5 个：331/334 为 PDF、343/999016 为 (1) 副本、999020 为 e2e-v2-ingest，本机不可得）
```

**判定**：用**生产原有 6 个 file_id** 做 UPSERT（不用新 id），这样 `wanted_docs` 仍覆盖 11 个 file_id，「不削」判据才成立。

---

## 二、执行序列与真实输出（含失败，不删）

### 1. 停 19531 + 同步运行树代码（18:20:03）

```
19531 STOPPED
md5 发布树 = md5 运行树 = 563be5a1a0608c6a317262987708010d
```

### 2. 重启 18094 设 `LLMKE_V2_ROOT` —— **连续失败，如实记录**

| 尝试 | 结果 |
|---|---|
| #1 | `Started server process [2331575]` → `ERROR: [Errno 98] address already in use`（旧 worker 1466203 未退出） |
| #2 | `kill -9 1466203` 后仍 `Started server process [2339504]` → `address already in use` |
| #3 | `Started server process [2355920]` → `address already in use` |

**根因（查证）**：`r12-watchdog.timer`（`OnCalendar=*-*-* *:*:00,30`，每 30 秒）触发 `r12-watchdog.service` → `r12-watchdog.sh` 自愈 → `r12-graph-v2-start.sh` 会**同时拉起 18094 和 19531**。它拉起的实例（cwd 运行树、`PYTHONPATH=.`）**已带正确的 `LLMKE_V2_ROOT`**，但缺 `LLMKE_V2_SNAPSHOT`，导致 `/health` 500（`RuntimeError: LLMKE_V2_SNAPSHOT 未设置`）。同时 19531 被拉回，破坏了窗口隔离。

**处置**：
1. `systemctl --user stop r12-watchdog.timer` → `inactive`；清理两个残留 `r12-graph-v2-start.sh` 进程。
2. `kill -9` watchdog 拉起的 18094 实例与 19531 实例，确认端口 `18094 FREE`。
3. 用**完整 env** 重启 18094（发布树代码，与原实例及 D-2 实证同源）：
   `LLMKE_V2_ROOT=<app graph-root>` + `LLMKE_V2_SNAPSHOT=<顶层单快照>` + `PYTHONPATH=services/rag-alg/index_data_service`。

**结果**：pid 2370351（+ worker 2371946），`/health` 200 `status=ok`。

> 附带发现：发布树 `graph_engine_adapter/api.py` md5 `4a58363c…` ≠ 运行树 `ae321af2…`（P6-BACKLOG #7 双副本问题延伸到 Python 图服务）。本窗口以发布树为准；恢复 timer 后 watchdog 用 `/openapi.json` 200 判定跳过，未替换该实例。

### 3. D-2 验收：按库查询不再 `NOT_BUILT`

```
POST /v2/graph/query {"kb":"kb_9","query":"智造贷","top_k":3,"enable_graph":true}
HTTP 200  executed_route=GRAPH  reason=GRAPH_CALLED  hit_count=3
seeds=["智造贷"]  seeds_source=auto  graph_calls=1  rerank_fallback=false
```

窗口前同一请求为 `{"status":"NOT_BUILT","hit_count":0}`。**D-2 判定成立**：(a) 零契约变更解决 B-2。

### 4. 同源 state 与生产 artifact-store 落地

- `kb-state/kb_9-prod-derived.json`：**46 行 / 11 file_id**，sha256 `9618b7d6…`（从生产快照 `sources.json` + openie passage 派生的重建态，非原始解析产物）。
- 新建 `data/artifact-store/`、`data/kb-state/`，**无既有文件被覆盖**（`ls` 确认目录此前不存在）。

### 5. 重启 18096 切生产 env

pid 2381144，`/health` 200 `configured=true`，env 核实：
```
LLMKE_V2_GRAPH_ROOT=<app>/platform/r12/data/graph-root
LLMKE_ARTIFACT_STORE=<app>/platform/r12/data/artifact-store
LLMKE_KB_STATE=<app>/platform/r12/data/kb-state/kb_9-prod-derived.json
```

### 6. POST 6 份（`scripts/p6_window_ingest.py`，先 `--dry-run` 核对请求体）

请求显式带 `graph_root`（`P4-L13C-PLAN.md:29` fail-closed 要求）。全部成功：

```
file_id=290    http=200 code=200 status=OK
file_id=329    http=200 code=200 status=OK
file_id=330    http=200 code=200 status=OK
file_id=332    http=200 code=200 status=OK
file_id=333    http=200 code=200 status=OK
file_id=999019 http=200 code=200 status=OK
```

响应细节（完整留痕 `ingest-responses.json`）：`diff.reason=CONTENT_CHANGED`、`state_committed=True`、`index_write.status=APPLIED`、`graph.result.root=<app>/graph-root/kb_9` ✔ 请求级 graph_root 生效。

---

## 三、验收结果（如实，不夸大）

| 判据 | 结果 | 说明 |
|---|---|---|
| 生产图不削 | **PASS** | `current.json` after sha256 `fa650c7d…`，与 before **`cmp` 逐字节相同**；`documents=46`、11 个 file_id 全在、`generation=0`、无新快照目录 |
| 查询可读 | **PASS** | 6 份 POST 后复跑 query：`HTTP 200` / `GRAPH` / `hit_count=3` |
| 重复请求短路 | **PASS** | 重发 290（带落盘 `content_hash`）→ `SKIPPED_FRESH` / `diff=NO_CHANGE` / `state_committed=False` / `index_write=NOT_APPLICABLE` / 零 delta 调用 |
| 请求级 graph_root 生效 | **PASS** | delta 响应 `root=<app>/graph-root/kb_9`，与请求体一致 |
| 服务可用性 | **PASS** | 8 个端口全 LISTEN；18094/18096/19531/19532 `/health` 全 200；timer `active` |

### 必须如实说明的三点（避免把「没写」读成「重建后不削」）

1. **图并未被重建**：6 份 delta 响应 `freshness.stale=False, reason=OK` → 走 `SKIPPED_FRESH` 零重建，因此 `current.json` 逐字节不变。原因是同源 state 派生的 46 行文本与生产快照指纹一致，新四件套投影文本未改变 set_digest。
   → 因此本次**没有验证「delta 重建分支执行后仍不削」**，只验证了「切读配置生效 + 全链路跑通 + 幂等短路」。该缺口登记为剩余项，不声称 17 已全验收。
2. **ES/Milvus 有真实写入**：`index_write=APPLIED`，按 file_id 先删后写，目标为 `v2cand_kb_9` / `v2cand_table_chunks_kb_9` 等**影子命名空间**前缀（P2-L8 隔离），生产 `kb_9` 主索引未被直接改写。
3. **18096 侧 `diff=CONTENT_CHANGED` 与 18094 侧 `freshness=不 stale` 口径不一致**，导致「索引写了、图没写」。这是同源性隐患，登记为发现项（本窗口不擅自修）。

### 已知过渡风险（窗口后）

- watchdog timer 已恢复（`active`），18:37 巡检自愈把 **19531 拉回**（pid 2411825）。窗口内 POST 期间 19531 确为停用、满足通道互斥；窗口后 18096 与 19531 都指向同一 `graph-root`，形成**双写通道并存**。二者均为被动写入（无自动并发），但一旦 Java `generate-graph` 与 18096 ingest 同时发生会互相覆盖。
  → 收口路径是 `T-D2MD-13/14/16` 的 v2-ingest 接线与 19531 退役；本窗口按「不扩大范围」判定不改部署脚本，登记为已知风险。
- 19531 被拉回期间，Java `generate-graph.url` 仍指向 19531，`v2-ingest.url` 为空。

---

## 四、回滚预案（未触发，保留可执行）

备份目录 `coordination/p6-window-20261112/` 含 before 快照、env、cmdline、运行树代码原件与 `MANIFEST.sha256`。回滚步骤：
1. 停 `r12-watchdog.timer`；停当前 18094/18096/19531。
2. 恢复 `runtime-kb-ingest-service.py.before`、`prod-kb9-current.json.before`。
3. 按 `env-*.before` / `cmdline.before` 用原 env 重启三个服务；恢复 timer。
4. 删除本窗口新建的 `data/artifact-store/`、`data/kb-state/`（新增目录，无既有数据）。
5. `v2cand_*` 影子索引按 file_id 可重放收敛，不物理删生产数据。

---

## 五、纪律留痕

- 窗口内所有服务身份均用 `/proc/<pid>/cmdline` + `environ` 核实；未把端口号当服务。
- 失败（3 次 `address already in use`、watchdog 实例 `/health` 500）**全部保留**在 `18094.log` 与本文件，未删除、未凑 PASS。
- 未执行 `git add` / `git commit`；未改 `contracts/`、`generated/`；未 `make generate`；未提 CR；不签 `QA_PASS`。
- `T-D2MD-17` 保持 `IN_PROGRESS`（窗口部分验收，见 §三）；`T-D2MD-18` 保持 `TODO`；G-4 独立 QA 主体/密钥仍缺失。
- 证据目录含：`ingest-responses.json`、`repeat.json`、`query-after.txt`、`query.txt`、`18094.log`、`18096.log`、`ingest.stdout`、before 备份。
