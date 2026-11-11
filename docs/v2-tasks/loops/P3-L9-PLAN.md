
# P3-L9 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-09`（`docs/v2-tasks/TASKS.yaml`）
- 阶段 **P3 18094 增量端点**，Loop 9 `POST /v2/graph/delta` + `_finalize_snapshot`
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton
- 依赖：`T-D2MD-05`（L5）、`P2-L7`（L7 已停全库建图，本 loop 是恢复图谱更新的关键）
- 状态：**标准已锁定，已派工；R-0 前置核实未完成前不得写实现代码**

> 依据：`03-IMPLEMENTATION.md` §P3-1~P3-2（`:222-260`）、`00-DESIGN.md:422`、`04-ACCEPTANCE.md` C-1 / C-3 / C-5。

---

## 一、Scope

| 允许 | 路径 | 约束 |
|---|---|---|
| 改 | `services/rag-alg/index_data_service/graph_engine_adapter/api.py` | 新增 `POST /v2/graph/delta` 路由 + `DeltaRequest` 模型 + `_finalize_snapshot()`；复用既有 `_kb_root` / `_load_fence` / `_default_build` / `_write_sources`，不重写引擎 |
| 新增 | `graph_engine_adapter/delta_build.py` | `delta_build(req)`：freshness 短路 → FULL/DELTA 分支 → `_finalize_snapshot` |
| 改 | `ingest_pipeline/index_writer.py` | 仅收口 `_binding_input` 残留的 `or "kb"`（L7 边界 3） |
| 新增 | 平台侧测试与 fixtures | 反例先 FAIL 再 PASS |

| 禁止 | 理由 |
|---|---|
| **重启 / 启停 18094**（pid 3189651/3202203 在线服务） | 本 loop 只写代码 + 离线验证；真实端点联调需维护窗口（P4/P6） |
| 写线上图快照 / ES / Milvus / DB | 在线服务运行中 |
| 自动降级：无基准快照时悄悄走 FULL、或 FULL 不带 `fallback_reason` | 设计包明令 `RebuildFailed → REJECTED` |
| 改 `rebuild.py` / `fence.py` / `engine_hipporag.py` 的核心算法 | P3-3（L10）才做 per-kb state 与 fencing |
| 改 L1~L8 已验收语义、设计包 / `MANIFEST.sha256` / `TASKS.yaml` / 运行态配置 / doc2md 仓 | 越界 |

**验证方式（本 loop 的核心约束）**：端点用 **FastAPI `TestClient`**（进程内，不监听端口）验证路由与请求校验；`delta_build` 用 mock 引擎验证分支与 `_finalize_snapshot` 的四文件重算（小规模 fixture）。**不启动任何新进程、不重启 18094。**

---

## 二、R-0 前置核实（回 TL 确认后再写实现）

1. `api.py` 现有路由清单、`_kb_root` / `_load_fence` / `_default_build` / `_write_sources` / `_write_kb_json` 的实际行号与签名；
2. `rebuild_delta` / `rebuild_by_policy` / `check_freshness` 的签名与返回结构（`rebuild.py`）；
3. `global_report.write(target, file_ids)` 的接口、耗时量级、是否写 `community.json`；
4. `fence.py` 的 `is_revoked` / `generation` 语义；
5. `capabilities.py` 现状（`:53-60` 的 `incremental_update=VERIFIED` 是否已声明 HTTP 端点）；
6. 18094 当前进程与「不重启」前提下的验证边界（TestClient 能否覆盖路由）。

---

## 三、可证伪断言（退出标准）

### J1 · 路由与请求校验

```
POST /v2/graph/delta 存在；DeltaRequest 校验：
  requested_mode ∈ {auto, delta, full, skip_if_fresh}；
  requested_mode=full 时 fallback_reason 必填，缺失 → 422/拒绝（不得默认通过）。
```

### J2 · freshness 短路零引擎调用

```
不 stale 且 requested_mode ∈ {auto, skip_if_fresh} → 返回 SKIPPED_FRESH；
断言：full_build / delta_apply 调用计数均为 0（mock 计数）。
```

### J3 · DELTA 后四文件由本次输入重算

```
DELTA 成功后：sources.json / community.json / fence.json / kb.json 的 sha256
  与「基准快照」不同（证明不是 copytree 带过来的旧文件）；
  sources.json 不含已删 file_id；community.json 由本次 live 集合重算。
```

**依据**：`03-IMPLEMENTATION.md:252-256`（`rebuild_delta:221` 的 copytree 会带旧文件）。

### J4 · 无自动降级

```
场景 A：无基准快照 → REJECTED（不自动走 FULL）
场景 B：requested_mode=full 且无 fallback_reason → 拒绝
场景 C：delta 失败 → 返回失败原因，不静默改走 FULL
```

### J5 · `_binding_input` 残留收口

```
index_writer._binding_input 不再含 `or "kb"`；直接 bind_chunks(artifact 无 file_id) → 抛 FILE_ID_MISSING。
回归：L6/L7 既有断言不退化。
```

### J6 · 不启停服务 / 不写线上

```
18094 pid 前后一致；八端口 pid/fd 未变；无新监听端口；
v2cand* 仍空；kb_9 / table_chunks_kb_9 _count 未变。
```

### J7 · 回归

```
平台侧既有 93 passed 不退化；doc2md 14 项封存态不变；
仓根 3 个既有失败与本 loop 无关（口径同 L8）。
```

### 组件级反例清单

| # | 反例 | 期望 |
|---|---|---|
| R-1 | `full` 不带 `fallback_reason` | 拒绝（J1/J4） |
| R-2 | 无基准快照却自动 FULL | REJECTED（J4） |
| R-3 | DELTA 后沿用 copytree 的旧 `sources.json` | J3 FAIL（sha 与基准相同） |
| R-4 | `community.json` 未重算 | J3 FAIL |
| R-5 | 已删 file_id 仍出现在 `sources.json` | J3 FAIL |
| R-6 | 回归退化 / `_binding_input` 仍回落 | J5/J7 FAIL |

---

## 四、验收命令

```bash
cd /home/szf/data/dev/llmke-v2
V2=/home/szf/data/dev/llmke-v2-toolenv/bin/python
HIP=/home/szf/data/dev/hipporag-toolenv/bin/python
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest <新测试> -q
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest \
  services/rag-alg/index_data_service/tests/ tests/test_rag_projection.py \
  tests/test_projection_read.py tests/test_runtime_switches.py tests/test_artifact_binding.py -q
$HIP -m pytest <新测试 + 回归> -q
ss -tlnp | grep -E ':(18094|19526|19527|19531|19995|19200|18082|18083)\b'   # pid 前后对比
curl -s http://127.0.0.1:19200/kb_9/_count ; curl -s http://127.0.0.1:19200/table_chunks_kb_9/_count
git -C /home/szf/data/dev/llmke-v2 status --short ; git -C /home/szf/data/dev/doc2md status --short
```

evidence 写 `docs/v2-tasks/evidence/P3-L9-<ts>.log`：R-0 结果、`delta_build.py` 全文 + `api.py` diff、反例 FAIL→PASS、四文件 sha 对比、pid 前后对比、解释器标注。

---

## 五、Baton / 回滚 / 依赖

- **Baton**：`DEV_SELF_CHECK_PASS` → TL 复核 → 可派工 P3-L10（state per-kb + fencing）或 P2-L8 已完成后的 P4。
- **回滚**：删除 `delta_build.py`、回退 `api.py` 路由与 `_finalize_snapshot`；因未重启 18094，线上行为零影响。
- **依赖**：`T-D2MD-10`（per-kb state + fencing）与 `T-D2MD-11`（能力登记）依赖本 loop；P4（`T-D2MD-12/13`）依赖本 loop 的端点；**P4 部署前必须完成 P3**（L7 边界 1）。
