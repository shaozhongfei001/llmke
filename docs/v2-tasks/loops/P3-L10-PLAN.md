
# P3-L10 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-10`（`docs/v2-tasks/TASKS.yaml`）
- 阶段 P3 18094 增量端点，Loop 10 `state per-kb 化 + fencing 递增`
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton
- 依赖：`T-D2MD-09`（L9 已内部收口，`delta_build.py` / `_finalize_snapshot` 已就位）
- 状态：**标准已锁定，已派工；R-0 前置核实未完成前不得写实现代码**

> 依据：`03-IMPLEMENTATION.md` §P3-3（`:262-270`）。

---

## 一、Scope

| 允许 | 路径 | 约束 |
|---|---|---|
| 改 | `graph_engine_adapter/api.py` | 全局 `state` 改 `states: Dict[str, StateSlot]`；`engine_for_kb` / `idx_map` / `fence_state` 按 kb 取；`fencing` 不再固定 1 |
| 改 | `graph_engine_adapter/rebuild.py` | 按 kb 的 `flock`（复用 `.pointer.lock` 语义）；fencing 透传与递增 |
| 改 | `graph_engine_adapter/fence.py` | `generation` 递增点（仅新增撤权 +1 的现有语义不变，新增「重建代次」独立字段或复用说明） |
| 新增 | 平台侧测试与 fixtures | 反例先 FAIL 再 PASS |

| 禁止 | 理由 |
|---|---|
| **重启 / 启停 18094** | 在线服务运行 35.8h+；本 loop 只改代码 + 离线验证 |
| 把 `_finalize_snapshot` 挪回 `api.py` | L9 裁定 3.2：避免 `delta_build` 反向依赖 fastapi |
| 改 `engine_hipporag.py` 的 `apply_delta` / 建图核心 | 属引擎层，不在本 loop |
| 改 L1~L9 已验收语义、设计包 / `MANIFEST.sha256` / `TASKS.yaml` / 运行态配置 / doc2md 仓 | 越界 |
| 写线上 ES / Milvus / DB / 图快照 | 在线服务运行中 |

**必须如实记录的一件事**：本 loop 改的是 `api.py` 的进程内结构，**不重启 18094 就不会生效**。代码合入后到重启窗口之间，磁盘代码与运行态不一致，属预期；P4/P6 重启时才会用上 per-kb state 与 fencing。evidence 必须写明这一点，不得暗示「已生效」。

---

## 二、R-0 前置核实（回 TL 确认后再写实现）

1. `api.py` 当前 `state` 形状（全局单槽？字段有哪些：`engine` / `idx_map` / `fence_state` / `snapshot`）；
2. `api.py:219` 附近 `fencing=1` 的实际写法与所有调用点；
3. `rebuild.py:135-155` 的 `.pointer.lock` flock 实现（`fcntl.flock` 还是文件锁库）、粒度、释放时机；
4. `fence.py` 的 `generation` 递增点（`revoke()` 内），是否存在「重建代次」概念；
5. `lease_mysql` 现状：是否可用、未配置时的行为、与 `fence.generation` 的优先级；
6. `_promote` 的「旧主拒绝」逻辑读的是哪个 fencing 字段；
7. `TestClient` 下能否构造两个 kb 并发访问（同进程线程 vs 顺序调用）。

---

## 三、可证伪断言（退出标准）

### K1 · per-kb state 隔离

```
kb_A 建图后：kb_B 的 engine / idx_map / fence_state / snapshot 指针不受影响；
断言 states["kb_A"] 与 states["kb_B"] 是不同对象、字段独立；
反例：共用一个 idx_map → kb_B 查到 kb_A 的块 → K1 FAIL。
```

### K2 · fencing 严格递增且旧主被拒

```
连续两次 rebuild：fencing 严格递增（f2 > f1）；
旧 fencing 的写/提升被拒绝（读 `_promote` 的拒绝路径）；
断言 f1/f2 都非固定 1（反例：仍写死 1 → K2 FAIL）。
```

### K3 · 按 kb 的 flock

```
同 kb 两个重建并发 → 串行化（第二个等待或明确拒绝，不得交错写）；
不同 kb 并发 → 不互相阻塞（不串行）。
```

### K4 · state 结构变更不破坏既有读取

```
/health、/v2/status、/v2/graph/query、/v2/graph/global 的响应字段不变；
查询路径按 kb 取 state 的行为与改动前一致（同一 kb 下结果相同）。
```

### K5 · 不启停服务 / 不写线上

```
18094 pid 前后一致（当前 3189651 / 3202203，启动于 2026-11-07 01:20/01:21）；
v2cand* 仍空、kb_9=44、table_chunks_kb_9=2 未变；八端口 pid 未变。
```

### K6 · 回归

```
L9 的 14(v2) / 26(hipporag) 不退化；平台侧合集 77 passed 不退化；
仓根 3 个既有失败与本 loop 无关（口径同 L8/L9）。
```

### 组件级反例清单（**先 FAIL 再 PASS，本 loop 恢复该流程**）

| # | 反例 | 期望 |
|---|---|---|
| R-1 | `state` 仍全局单槽 | K1 FAIL（跨 kb 污染） |
| R-2 | `fencing` 仍固定 1 | K2 FAIL |
| R-3 | 无 flock 或 flock 粒度错（全局锁） | K3 FAIL（跨 kb 被串行） |
| R-4 | `/v2/status` 字段因 state 重构变化 | K4 FAIL |
| R-5 | 旧 fencing 仍能写 | K2 FAIL（拒绝路径未生效） |
| R-6 | 既有测试退化 | K6 FAIL |

---

## 四、验收命令

```bash
cd /home/szf/data/dev/llmke-v2
V2=/home/szf/data/dev/llmke-v2-toolenv/bin/python
HIP=/home/szf/data/dev/hipporag-toolenv/bin/python
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest <新测试> -q
PYTHONPATH=services/rag-alg/index_data_service $HIP -m pytest <新测试 + L9 路由测试> -q
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest \
  services/rag-alg/index_data_service/tests/ tests/test_projection_read.py \
  tests/test_runtime_switches.py tests/test_rag_projection.py -q      # K6
ss -tlnp | grep ':18094\b'                       # pid 前后对比
curl -s http://127.0.0.1:19200/kb_9/_count ; curl -s 'http://127.0.0.1:19200/_cat/indices/v2cand*?h=index'
git -C /home/szf/data/dev/llmke-v2 status --short ; git -C /home/szf/data/dev/doc2md status --short
```

evidence 写 `docs/v2-tasks/evidence/P3-L10-<ts>.log`：R-0 结果、`api.py`/`rebuild.py`/`fence.py` diff 全文、反例 FAIL→PASS、变异（mutate→FAIL / restore→md5 复原）、pid 与 `_count` 前后对比、**「改代码未重启、尚未生效」显式声明**。

---

## 五、Baton / 回滚 / 依赖

- **Baton**：`DEV_SELF_CHECK_PASS` → TL 复核 → 派工 `T-D2MD-11`（能力登记，快速收口）或 P4。
- **回滚**：恢复三个文件到 HEAD 版即可；因未重启 18094，运行态零影响。
- **依赖**：P4（`T-D2MD-12/13`）依赖本 loop 的 per-kb state；`T-D2MD-11` 是把 `capabilities.ts` 的 DELTA HTTP 端点声明补齐（L9 提醒项）。
