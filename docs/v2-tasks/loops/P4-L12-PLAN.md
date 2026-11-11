
# P4-L12 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-12`
- 阶段 P4 18096 摄取服务主链路，Loop 12 `KbDeltaService + IngestRequest`
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton
- 依赖：`T-D2MD-07`（P2 投影）、`T-D2MD-09`（DELTA 端点）
- 状态：**标准已锁定，已派工；R-0 未回 TL 前不写实现**

> 依据：`03-IMPLEMENTATION.md` §P4-1（`:306-325`）、`04-ACCEPTANCE.md` A-3（`:14`）、`02-CONTRACTS` §4.3。

---

## 一、Scope

| 允许 | 路径 | 约束 |
|---|---|---|
| 新增 | `services/rag-alg/index_data_service/ingest_pipeline/kb_delta.py` | `KbDeltaService.diff/plan/commit`；复用既有 `parse_artifact.store`、`projection`、`index_writer`、`artifact_binding`，**不引入第二套写入者** |
| 改 | `services/rag-alg/index_data_service/ingest_pipeline/kb_ingest_service.py` | `:142-221` + 请求体改 Pydantic `IngestRequest`；删 `file_url` 全自动重解析分支；`source` 真传；去掉 `pop("payloads")` 歧义 |
| 新增 | 平台侧测试 / fixtures | 反例先 FAIL 再 PASS |

| 禁止 | 理由 |
|---|---|
| 改 `graph_engine_adapter/api.py` | 18094 由 L9/L10 管；本 loop 只做 18096 侧 |
| 改 `delta_build.py` / `rebuild.py` / `fence.py` / `capabilities.py` | P3 已收口 |
| **启动 18096 / 启停任何服务** | 红线；本 loop 只做离线验证 |
| 改 Java 侧（`RemoteV2IngestUtils.java` 等） | 属 P5 |
| 改 `platform/r12/` 部署脚本 / env / systemd | 属 L13（`T-D2MD-13`） |
| 改设计包 / `MANIFEST.sha256` / `TASKS.yaml` / doc2md 仓 | 越界 |
| 写线上 ES / Milvus / DB / 图快照 | 18094 在线运行 |

### ⚠️ 本 loop 不得做的声明

- **不得声称 A-3 通过**。A-3 要求「全量与增量同入口的真实请求/响应样本 + 摄取服务访问日志」，需起 18096 → 属 **P6**。本 loop 只能做**代码级契约验证**（`IngestRequest` 校验、响应模型、路由签名一致），evidence 必须写明「A-3 的验收证据未产出，属 P6」。
- **不得声称 18096 可用**。本 loop 结束时 18096 仍是未启用状态。

---

## 二、R-0 前置核实（回 TL 确认后再写实现）

1. `kb_ingest_service.py:142-221` 现有分支结构（`file_url` 自动重解析在哪几行、`payloads` 的 `pop` 歧义具体形状、`source` 当前从哪来）；
2. `02-CONTRACTS` §4.3 的 `DiffResult` / `IngestPlan` 字段定义原文（**以此为准，不自创字段**）；
3. `commit()` 要推进的「cursor/version」落在哪个存储（`kb_state`? MySQL? 文件?），有无既有 `kb_state` 读写 API；
4. 「组装全库 wanted docs」现有无既有函数（`consume_for_kb`? `kb_pipeline`?），避免重写；
5. `SourceDiverged` 异常类在哪、是否已有 HTTP 状态码映射机制，避免两套；
6. `parseTask/callback` 的 `TaskReq` 字段与 `X-Internal-Token` 来源（本 loop 只做接口预留还是要实现回写？**按 PLAN 属 L13，本 loop 只留调用点**）；
7. `projection` 的入口函数名（用于 B8 断言「未重投影」时 mock 哪个函数）。

---

## 三、可证伪断言

### B1 · 空 diff 短路（A-6 / C-2 的代码级对应）

```
diff 结果 added/changed/removed 全空 → 返回 SKIPPED_FRESH；
断言：index_writer 零调用、projection 零调用、18094 零调用（mock 计数全 0）、cursor 不推进。
```

### B2 · removed 先 revoke 再 delta

```
removed 非空时：断言 fence.revoke 在 delta 调用**之前**发生（mock 记录调用序）；
且撤权文件不出现在 delta 的 wanted docs 里。
```

### B3 · 三路成功才推 cursor（原子绑定）

```
任一路（artifact / 投影 / index_writer）抛异常 → cursor/version **不推进**；
断言：失败后重放同一 manifest 仍能走完整 plan（事件可重放），不产生「已提交但缺一路」的状态。
```

### B4 · SourceDiverged → 409

```
同一 content_uid 出现不同 content_hash → 抛 SourceDiverged → 映射 409；
断言：映射走既有 HTTP 异常机制，不自建第二套状态码表。
```

### B5 · `IngestRequest` 强校验

```
缺必填字段 → 422；未知字段 → 拒绝（或显式忽略并记录，二者择一但要有断言）；
断言：用 Pydantic 模型，非裸 dict；`source` 字段真实传递到 runner（mock 断言收到的 source 值）。
```

### B6 · 全量与增量同入口、同响应 schema（A-3 的代码级部分）

```
全量（manifest 全量更新）与增量（单文件 upsert）走同一函数入口、返回同一 Pydantic 响应模型；
断言：两者响应模型的字段集相同（反射取 model_fields）。
```

### B7 · 删掉 `file_url` 自动重解析分支

```
静态断言：kb_ingest_service.py 中不再存在「传 file_url 就自动全量重解析」的分支；
若保留 file_url 字段，必须有显式 REJECTED 或忽略记录，不得静默重解析。
```

### B8 · wanted docs 读 `kb_state`，不重投影

```
组装全库 wanted docs 时，projection 入口函数**零调用**（mock 断言）；
断言：wanted docs 来源是 kb_state 的 ACTIVE 快照投影记录，不是重新投影。
```

### 组件级反例（**先 FAIL 再 PASS**）

| # | 反例 | 期望 |
|---|---|---|
| R-1 | 空 diff 仍写索引 | B1 FAIL |
| R-2 | 先 delta 后 revoke | B2 FAIL（顺序错） |
| R-3 | 一路失败仍推 cursor | B3 FAIL |
| R-4 | `SourceDiverged` 返回 500 或 200 | B4 FAIL |
| R-5 | 请求体仍裸 dict / 未知字段静默接受 | B5 FAIL |
| R-6 | 全量与增量走两个不同入口 | B6 FAIL |
| R-7 | file_url 仍触发自动全量重解析 | B7 FAIL |
| R-8 | wanted docs 重新投影 | B8 FAIL |

---

## 四、验收命令

```bash
cd /home/szf/data/dev/llmke-v2
V2=/home/szf/data/dev/llmke-v2-toolenv/bin/python
HIP=/home/szf/data/dev/hipporag-toolenv/bin/python

# 主口径（v2，不依赖 fastapi）
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest tests/test_kb_delta_l12.py -q
# 若涉 FastAPI 路由签名，另在 hipporag 跑一次；v2 的 skip 单列不计通过
PYTHONPATH=services/rag-alg/index_data_service $HIP -m pytest tests/test_kb_delta_l12.py -q

# 回归（L11 收口基线 165 passed / 4 skipped）
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest \
  services/rag-alg/index_data_service/tests/ tests/test_projection_read.py \
  tests/test_runtime_switches.py tests/test_rag_projection.py \
  tests/test_capabilities_http_l11.py -q

# 红线
ss -tlnp | grep -E ':(18094|18096)\b'      # 18094 pid 不变；18096 必须**仍不存在**
curl -s -m 5 http://127.0.0.1:19200/kb_9/_count
curl -s -m 5 'http://127.0.0.1:19200/_cat/indices/v2cand*?h=index'
git -C /home/szf/data/dev/llmke-v2 status --short ; git -C /home/szf/data/dev/doc2md status --short
```

evidence 写 `docs/v2-tasks/evidence/P4-L12-<ts>.log`：R-0 结果、`kb_delta.py` 全文要点、`kb_ingest_service.py` 改动前后 md5 + `git diff` 全文、阶段 A 真实红灯、B1~B8 真值、变异（mutate→FAIL / restore→md5 复原）、两仓越界自查、**「A-3 未验收、18096 未启用」显式声明**。

---

## 五、Baton / 回滚 / 依赖

- **Baton**：`DEV_SELF_CHECK_PASS` → TL 复核 → `T-D2MD-13`（部署定义 + 启动自检 + 回调回写）。
- **回滚**：删 `kb_delta.py`、`kb_ingest_service.py` 恢复到改动前 md5。因 18096 未启用，线上零影响。
- **下游依赖**：L13 的部署脚本与启动自检依赖本 loop 的入口签名；`T-D2MD-13.blocker` 中「P4 部署前必须完成 P3」已由 L9/L10/L11 收口解除，但**部署本身仍需 Owner 授权**（起 18096 属运行态变更）。
