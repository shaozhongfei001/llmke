# P3-L11 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-11`
- 阶段 P3 收尾，Loop 11 `能力登记（capabilities）`
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton
- 依赖：`T-D2MD-09`（DELTA 端点已上线代码）
- 状态：**标准已锁定，已派工**

> 依据：`00-DESIGN.md` 能力矩阵、L9 闭环时成员的提醒。

---

## 一、问题陈述

`graph_engine_adapter/capabilities.py:53` 的 `incremental_update` 目前只声明**引擎能力**：

```
"note": "...（**增量抽取 + 全量重建图**，两件事分开说）。真跑 5 块：全量 32.4s → 增量 7.5s..."
"evidence": "docs/design/unified-documents-v2/EVIDENCE-DELTA-REBUILD-20261031.md"
```

**没有声明 HTTP 端点**。而 `api.py:482` 已有 `@app.post("/v2/graph/delta")`。

后果：任何按 `capabilities` 判断「能不能通过 HTTP 做增量」的调用方（编排层、监控、文档）会得到错误结论 —— 能力登记与实际不符。

同理需核对 `/v2/graph/build`（:422）、`/v2/status`（:598）、`/v2/fence`（:627）是否都已被登记。

---

## 二、Scope

| 允许 | 路径 | 约束 |
|---|---|---|
| 改 | `graph_engine_adapter/capabilities.py` | 补 HTTP 端点登记；`incremental_update` 的 note 保持「增量抽取 + 全量重建图」如实表述 |
| 新增 | 测试（断言登记 ↔ 真实路由一致） | 反例先 FAIL |

| 禁止 | 理由 |
|---|---|
| 改 `api.py` 路由 | 本 loop 只做登记，PHP 路由已由 L9 验收 |
| 改引擎 / `delta_build.py` / `rebuild.py` / `fence.py` | 属前序 loop |
| 重启 18094 | 在线服务运行 35.9h+ |
| 改设计包 / `MANIFEST.sha256` / `TASKS.yaml` / 运行态配置 / doc2md 仓 | 越界 |
| 把 `capabilities` 的 `status` 提到 `VERIFIED` 以上 | `QA_PASS` 未闭环 |

---

## 三、R-0 前置核实（回 TL 确认后再写）

1. `capabilities.py` 顶层结构（`CAPABILITIES` 字典？有无 schema / 版本字段 / `describe()`）；
2. 是否已有任何能力项声明过 HTTP 端点 —— 若有，**照它的字段名写**（不要自创 `endpoints` 键导致两套风格）；
3. `api.py` 的 `/v2` 路由全集（TL 已初查 8 条：`build`/`delta`/`query`/`entities`/`status`/`fence`/`graph/view`/`graph/global`），确认是否还有动态路径或条件注册；
4. `capabilities` 的消费方（谁读它：编排层 / 健康检查 / 文档生成 / 无消费方），决定「端点字段」是给机器读还是给人读；
5. 有无既有测试断言 `capabilities` 结构（避免改结构打破别处）。

---

## 四、可证伪断言

### M1 · DELTA 端点已登记且与真实路由一致

```
capabilities 中 incremental_update 声明了 POST /v2/graph/delta；
断言：声明存在、method == "POST"、path == "/v2/graph/delta"；
并与 api.py 的 @app.post 路径逐字符比对（不是手抄）。
```

### M2 · 表述如实（不夸大、不缩小）

```
incremental_update 的 note 必须同时含「增量抽取」与「全量重建图」两个语义；
反向断言：不得只写「增量重建」而不提图全量重建（那是夸大）。
```

### M3 · 声明 ↔ 路由双向一致（无幽灵、无漏登）

```
① 声明的每个 /v2 路径都能在 api.py 找到对应 route（无幽灵端点）；
② api.py 的每个 /v2 写路由（build/delta/global）都被登记或显式列入"不登记清单"（无漏登）。
   GET 只读路由（status/fence/entities/view）可只登记其能力项，不强求逐条列出。
```

### M4 · 既有能力不退化

```
其余能力项（同文异源、visibility_fence 等）内容一字不变；
断言：除 incremental_update 外的块 sha256 与改动前一致。
```

### M5 · 结构可被消费方解析

```
capabilities 顶层可 import、可 json.dumps、schema 字段未变；
若有 describe()/schema 版本号，保持兼容。
```

### 组件级反例（**先 FAIL 再 PASS**）

| # | 反例 | 期望 |
|---|---|---|
| R-1 | 声明一个 `api.py` 里不存在的端点 | M1/M3-① FAIL（幽灵端点） |
| R-2 | 把 DELTA 说成「全量重建」或只写「增量」 | M2 FAIL |
| R-3 | 完全不登记端点 | M3-② FAIL（漏登） |
| R-4 | 改结构导致 `json.dumps` 或既有消费方报错 | M5 FAIL |
| R-5 | 顺手改了别的能力项 | M4 FAIL |

---

## 五、验收命令

```bash
cd /home/szf/data/dev/llmke-v2
V2=/home/szf/data/dev/llmke-v2-toolenv/bin/python
HIP=/home/szf/data/dev/hipporag-toolenv/bin/python
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest <新测试> -q
PYTHONPATH=services/rag-alg/index_data_service $HIP -m pytest <新测试> -q
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest \
  services/rag-alg/index_data_service/tests/ tests/test_projection_read.py \
  tests/test_runtime_switches.py tests/test_rag_projection.py -q     # 88 passed 不退化
ss -tlnp | grep ':18094\b'
git -C /home/szf/data/dev/llmke-v2 status --short ; git -C /home/szf/data/dev/doc2md status --short
```

`capabilities.py` 改动前记录 md5，改动后附 `git diff` 全文。evidence 写 `docs/v2-tasks/evidence/P3-L11-<ts>.log`，标注解释器与用途。

---

## 六、Baton / 回滚

- **Baton**：`DEV_SELF_CHECK_PASS` → TL 复核 → **P3 阶段收口**，进入 P4（`T-D2MD-12/13` F-1 接线）。
- **回滚**：恢复 `capabilities.py` 到改动前 md5。
- **本 loop 不需重启**：`capabilities` 是静态声明，被读取即生效；但若 18094 有 `/capabilities` 端点缓存，重启前仍是旧值 —— evidence 如实写明。
