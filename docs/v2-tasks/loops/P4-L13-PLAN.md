# P4-L13 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-13`
- 阶段 P4 收尾，Loop 13 `部署定义 + 启动自检 + 回调回写`（**分三段推进**）
- holder：`python-engineer`
- 依赖：`T-D2MD-12`（已内部收口）
- 状态：**A 段已派工；B 段随 A 收口后派；C 段需 Owner 授权**

> 依据：`03-IMPLEMENTATION.md` §P4-2 / §P4-3（`:326-350`）。

---

## 零、三段划分（这是本 PLAN 最重要的部分）

| 段 | 内容 | 可否自主推进 | 验收方式 |
|---|---|---|---|
| **A** | **让 18096 逻辑完整**：接线 `index_writer.apply`、配置 delta runner、补 `POST /v2/fence/revoke` | **可**（纯代码 + 离线） | 单测（mock ES/Milvus/18094），**不起服务** |
| **B** | 部署定义：启动脚本 / watchdog / up.sh / systemd / env / `R12-ENV-CONTRACT.md`；Java 侧非 200/207 回写 | 可（写文件，**不执行**） | 脚本语法检查 + 自检逻辑单测 + 静态断言，**不跑部署脚本** |
| **C** | 起 18096 + 真实 A-3 验收 + 停 18094 演练 | **需 Owner 显式授权** | 真实请求/响应样本、访问日志 |

**A 段本次派工范围。** B 段随 A 收口后派；C 段等 Owner 授权。

---

## 一、A 段为何必须先做（L12 传递的两条硬约束）

L12 交付的是**不可独立运行的半链路**：

```
UPSERT → index_write = {status:"PLANNED", applied:false, required:true}
       → landed = false → status = "PARTIAL" → HTTP 207（恒）
```

后果（若直接进部署）：**Java 按 207 回写 RETRY → 无限重试，永远「成功」返回但不推进**。这是「删不掉的重试」。

同理：`delta runner` 未配置时 DELETE 停在 `PARTIAL / state_committed=false`（撤权已发出但状态未落）。

**A 段就是把这两条补齐，让 18096 能真正返回 `OK`。**

---

## 二、A 段 Scope

| 允许 | 路径 | 约束 |
|---|---|---|
| 改 | `ingest_pipeline/kb_delta.py` | 增加 `apply` 调用点；`index_write` 块改为如实反映 `applied`；**不改已验收的 delta 前移顺序与 `state_committed` 语义** |
| 改 | `kb_ingest_service.py` | 构造 `IndexWritePlan` 执行链、注入 `es_url`/`milvus_url`、注入 delta runner |
| 改 | `graph_engine_adapter/api.py` | **新增 `POST /v2/fence/revoke`**（契约 §3 缺口） |
| 新增 | 测试 | 反例先 FAIL |

| 禁止 | 理由 |
|---|---|
| **执行任何部署脚本 / 启停 18096 / 重启 18094** | C 段，需授权 |
| 写线上 ES(19527) / Milvus(19526) / DB | 红线 |
| 改 `platform/r12/` | B 段 |
| 改 Java | B 段 |
| 改设计包 / `MANIFEST.sha256` / `TASKS.yaml` / 运行态配置 / doc2md 仓 | 越界 |
| 改 L9/L10/L11 已验收语义（`delta_build`/`rebuild`/`fence`/`capabilities`） | P3 已收口 |

---

## 三、R-0 前置核实（回 TL 确认后再写实现）

1. `index_writer.apply(plan, *, es_url, milvus_url)` 的返回 `IndexWriteResult` 字段（成功/部分失败如何表达）；
2. `es_url` / `milvus_url` 的来源（env? 配置? `_urls()`?），与 `api.py` 的 `_urls()` 是否同一套；
3. `apply` 失败时是否有「一侧已写」的补偿语义（契约 `INDEX_WRITE_FAILED` 要求「已写的一侧显式记录补偿任务」）；
4. `apply` 是否为幂等（重放同一 plan 会不会重复写）；
5. `POST /v2/fence/revoke` 的 18096↔18094 跨进程问题：18096 不能直接调 `FenceState.revoke`（内存态），必须先解决「状态共享」—— 是走新端点 `POST /v2/fence/revoke`（18094 侧持久化 fence）还是共享文件；
6. `fence.py` 的 `revoke` 是否持久化到磁盘（`fence.json`），18094 重启后是否保留；
7. delta runner 的注入点（L12 已留 `self._delta`），是否有现成 HTTP 客户端可调 18094 的 `POST /v2/graph/delta`。

**第 5 项是本段最大的不确定点** —— 若 18096 与 18094 是两个进程且 fence 只在内存，则「撤权」需要新设计（跨进程状态），可能超出本段。**R-0 必须先回答，必要时回 TL 重新划段。**

---

## 四、A 段断言

### A1 · `index_writer.apply` 已接线，UPSERT 能返回 `OK`

```
UPSERT 成功路径：apply 被调用 1 次，index_write = {status:"APPLIED", applied:true, required:true}
→ landed = true → status = "OK" → HTTP 200
反例：不接线 → 恒 PARTIAL/207 → A1 FAIL
```

### A2 · `apply` 失败 → `INDEX_WRITE_FAILED` / 502，且状态不提交

```
apply 抛错或返回失败 → 映射 INDEX_WRITE_FAILED(502)；
state_committed=false、cursor 不推进（复用 L12 的顺序保证）。
```

### A3 · `apply` 部分成功（一侧已写）必须显式记录

```
若 es 写成功、milvus 失败 → 响应/日志必须显式记录「已写的一侧」，
不得只 log（契约 §5 INDEX_WRITE_FAILED 的调用方动作要求「已写的一侧显式记录补偿任务」）。
断言：响应含 compensate 信息，或日志含结构化记录。
```

### A4 · delta runner 已配置，DELETE 能落状态

```
DELETE + removed 非空 + runner 已配 → graph 成功 → state_committed=true → HTTP 200；
反例：未配 runner → PARTIAL + state_committed=false → A4 FAIL
```

### A5 · `POST /v2/fence/revoke` 存在且行为正确

```
契约 §3 端点存在；调用后 fence.revoked 含该 file_id、generation 递增（幂等：重复撤权不重复递增）；
GET /v2/fence 能读到刚撤权的项。
跨进程问题按 R-0 第 5 项的裁定实现。
```

### A6 · 不破坏 L12 已验收语义

```
delta 仍在状态事务之前（`test_b3_delta_runs_before_state_commit` 仍绿）；
`state_committed` 语义不变；错误码表 11+9 条不退化。
```

### 组件级反例（**先 FAIL 再 PASS**）

| # | 反例 | 期望 |
|---|---|---|
| R-1 | `apply` 未接线 → 恒 207 | A1 FAIL |
| R-2 | `apply` 失败仍提交状态 | A2 FAIL |
| R-3 | 部分成功只 log 不记录 | A3 FAIL |
| R-4 | 未配 runner 时 DELETE 报 OK | A4 FAIL |
| R-5 | `POST /v2/fence/revoke` 不存在（当前状态） | A5 FAIL |
| R-6 | 改坏了 delta 顺序 | A6 FAIL |

---

## 五、验收命令

```bash
cd /home/szf/data/dev/llmke-v2
V2=/home/szf/data/dev/llmke-v2-toolenv/bin/python
HIP=/home/szf/data/dev/hipporag-toolenv/bin/python

PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest tests/test_kb_delta_l12.py tests/test_kb_delta_l13.py -q
PYTHONPATH=services/rag-alg/index_data_service $HIP -m pytest tests/test_kb_delta_l13.py tests/test_kb_ingest_l12.py tests/test_graph_state_l10.py -q

# 回归（L12 收口基线 v2 189/4、hipporag 251）
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest \
  services/rag-alg/index_data_service/tests/ tests/ -q

# 红线
ss -tlnp | grep -E ':(18094|18096)\b'    # 18094 pid 不变；18096 必须仍不存在
curl -s -m 5 http://127.0.0.1:19200/kb_9/_count
curl -s -m 5 'http://127.0.0.1:19200/_cat/indices/v2cand*?h=index'
git -C /home/szf/data/dev/llmke-v2 status --short ; git -C /home/szf/data/dev/doc2md status --short
```

evidence 写 `docs/v2-tasks/evidence/P4-L13A-<ts>.log`。

---

## 六、B 段与 C 段（预告，本次不做）

**B 段**：`platform/r12/bin/r12-kb-ingest-start.sh`（幂等启动，参照 `r12-graph-v2-start.sh:40-67`）、`r12-watchdog.sh:57-71`、`up.sh:130-135,210`、`systemd/` unit、`R12-ENV-CONTRACT.md:9-36` 端口表；env 注入 `LLMKE_DOC2MD_CONFIG` / `LLMKE_DOC2MD_LOCK` / `LLMKE_ARTIFACT_STORE` / `LLMKE_KB_STATE` / `LLMKE_CANARY_FILE` / `R12_MINIO_*`；启动自检（doc2md 可执行 / `app.yaml` 可读 / MySQL 可达 / 18094 可达 / artifact store 可写，fail-fast）；Java `RemoteV2IngestUtils.java:96-100` 改回写 `PARSE_FAIL`/`RETRY`。
**验收**：`bash -n` 语法检查、自检逻辑单测（mock 各依赖验证 fail-fast）、静态断言引用正确；**不执行部署脚本**。

**C 段（需 Owner 授权）**：`bash platform/r12/bin/r12-kb-ingest-start.sh` 起 18096 → `curl /openapi.json` 验路由 → `POST /kb/ingest` 跑 `tests/fixtures/ingest_upsert.json` → 真实 A-3 样本与访问日志 → 停 18094 演练 `GRAPH_UNREACHABLE` + Java 回写 `RETRY`。

---

## 七、Baton / 回滚

- **Baton**：A 收口 → B → C（授权）→ P4 阶段收口 → P5。
- **回滚**：A 段恢复三个文件的 md5；因 18096 未启用，线上零影响。
- **必核项**：Java 侧是按 HTTP 状态码还是 body `code` 判断失败 —— 决定 L12 的 `response.status_code = code` 修复是否必要（两者都应在 B 段确认）。
