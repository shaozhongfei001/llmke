# STEP2-J 请求级 graph_root 核实、实现修正与隔离演练（T-D2MD-17 / 2026-11-12）

> Owner 指令（本轮）：同意 STEP2-I 的 ③+(c)（隔离副本演练 + 指纹比对验收）；**确认 GRAPH_ROOT 来自请求而不是设定死的值**。
> 本轮性质：只读核实 + 实现修正 + 回归/变异复验 + 隔离演练。**未启动/停止/重启任何服务，未写生产图根、未写 ES/Milvus，未执行 `git add`/`git commit`。**
> 纪律：事实 / 推断 / 判断分开；每条结论附可复跑命令与实测输出。

---

## 一、核实结论：`graph_root` 当前**不是**来自请求（与 Owner 预期相反，已如实上报并修正）

### 18096 侧（问题所在）

运行时实测（不是读代码推断）：

```
cd llmke-runtime/app/services/rag-alg/index_data_service
LLMKE_V2_GRAPH_ROOT=/tmp/GRAPH-ROOT-FROM-ENV LLMKE_ARTIFACT_STORE=/tmp/P6-PROBE-STORE \
PYTHONPATH=. <hipporag-toolenv>/bin/python -c "... _build_service() ... s._delta(plan) ..."

closure: ['http://127.0.0.1:18094', '/tmp/GRAPH-ROOT-FROM-ENV']
root actually sent to 18094: ['/tmp/GRAPH-ROOT-FROM-ENV']
service reads req.graph_root? False
```

- **事实**：`kb_ingest_service.py:255` `graph_root = graph_root or os.environ.get("LLMKE_V2_GRAPH_ROOT")` 只在 `create_app()` 启动时执行一次；`:261` 把它绑进 `_delta_runner` 闭包；`:262` 同样绑进 `_fence_revoke`。
- **事实**：`IngestRequest.graph_root`（`:164`）只是字段声明；`kb_delta.plan()`（`:441-515`）与 `commit()`（`:518-596`）**从不读取** `graph_root`。`grep -rn graph_root` 全链路只有 8 处，`kb_pipeline.py:504` 注释明说该参数「保留是为了不改调用方签名」。
- **事实**：旧 runner 兼容缝（`:350-357`）确实把 `graph_root` 透传给 `consume`，但生产默认 `runner is None` → 走 `service.run()`，该缝不生效。
- **判断**：因此 STEP2-F「请求体 `graph_root` 对生产路径无效」成立，但根因不是 18094 拒绝，而是 **18096 的 service 路径静默丢弃该字段**。

### 18094 侧（本来就是请求驱动）

- **事实**：`DeltaRequest.root`（`api.py:123`）是请求体字段；`delta_build.py:273` `root = _kb_root(kb, getattr(req, "root", None))`，`:51-58` 展开为 `<root>/<kb>`；`graph_client.post_graph_delta()`（`:115-116`）在 `root` 非空时写入 `payload["root"]`。
- **判断**：18094 一直按请求体 root 落盘（`_is_own_root()` 为假时只落盘、不改内存槽，`api.py:563`）。**设定死的值发生在 18096 这一层**，与 18094 无关。

### 本次最小实现修正（发布树 `llmke/services/.../kb_ingest_service.py`）

```python
# create_app(): 标记默认构造的 service
service_is_default = True/False

# ingest(): 请求给了就按请求绑定，没给仍回退 env
active_service = service
if service_is_default and (req.graph_root or req.graph_api):
    active_service = _build_service(graph_api=req.graph_api, graph_root=req.graph_root)
result = active_service.run(payload)
```

- **判断**：`graph_root` / `graph_api` 本就在契约 §1.1 的 `IngestRequest` 字段集中，本次**不新增边界、不改字段集、不改默认值语义**（不传时仍用启动 env），仅修复「实现未消费已有字段」的缺陷，与旧 runner 缝行为对齐。若 Owner 认为属边界变更，可要求补 CR。
- **事实（重要，代码合入 ≠ 线上生效）**：运行树 `llmke-runtime/app/services/.../kb_ingest_service.py` **未同步修改**，md5 仍为 `5a19cc16…`，发布树改为 `563be5a1…`。生产 18096（pid 46796）自 11-09 起运行，加载的是旧模块，**线上仍是启动绑定死值**；代码就位后需在授权窗口内同步 + 重启 18096 才生效。本轮按 ③ 不进窗口，不重启。

---

## 二、回归测试与变异复验（证明断言非空转）

新增 `tests/test_kb_ingest_request_graph_root.py`（6 项）：请求 root 覆盖 env、两次请求不同 root、`graph_api` 同样请求驱动、不传时保持启动绑定、注入 service 兼容缝不被替换、真实 `_build_service` 闭包携带请求 root。

```
PYTHONPATH=services/rag-alg/index_data_service <hipporag-toolenv>/bin/python -m pytest \
  tests/test_kb_ingest_request_graph_root.py tests/test_kb_ingest_l12.py \
  tests/test_kb_delta_l12.py tests/test_kb_delta_l13.py -q
→ 98 passed in 0.38s
```

**变异复验**：把 `kb_ingest_service.py` 换成 `git show HEAD:...`（未修复版本）置于 `PYTHONPATH` 首位，同一测试文件：

```
FFF... [100%] → 3 failed, 3 passed, MUTANT_EXIT=1
（test_request_graph_root_overrides_startup_env / test_two_requests_bind_different_roots /
  test_graph_api_is_request_driven_too 全部 FAIL，报 assert None == '/req/ROOT-A' 等）
```

变异目录 `coordination/.p6-mut/` 已删除。**断言对缺陷有判别力，不是空转。**

---

## 三、③ 隔离副本演练 + (c) 指纹比对验收

可复跑入口：`scripts/p6_request_graph_root_probe.py`

```
cd /home/szf/data/dev/llmke
<hipporag-toolenv>/bin/python scripts/p6_request_graph_root_probe.py
```

### 演练边界（如实标注，避免假绿）

- **真实跑**：FastAPI `TestClient` → `create_app()` 路由 → `IngestRequest` 校验 → `KbDeltaService.plan()`（`commit_snapshot` / `project_snapshot` / `index_writer.build` / 同源闸门）→ `commit()` → `wanted_docs` 全量装配 → 状态事务 → `_result()`。
- **替身**：`_apply_writes`（不写 ES/Milvus）、delta runner（不调 18094 真实建图，只记录 `root` 与 `wanted_docs`）。
- **因此不声称**：「图已重建」「查询可读」「线上已生效」。本演练只证明下列三条可证伪判据。

### 同源 state 的构造与硬校验

生产 `kb_9/snapshot-20261107212905-365431-g0/sources.json`（idx → file_id/locator/title，30 条）+ `openie_results_ner_*.json`（idx → passage）派生出 v2 `kb_state`：

```
derived_state.rows = 46          == 生产 current.json.documents = 46
derived_state.file_ids = 11 个    == 生产 fingerprint.files = 11 个
```

这是**从生产快照派生的重建 state**，不是原始解析产物，已在脚本注释中如实标注。它正好复现了 B-1 所缺的「与生产图根同源的 kb_state」。

### 实测输出（本轮最终运行）

```
verdict: PASS
prod_current_sha256_before: fa650c7de99237ad0690e673f83d8788054f20f6c928c810a880b82756ab97d6
prod_current_sha256_after : fa650c7de99237ad0690e673f83d8788054f20f6c928c810a880b82756ab97d6
env_fixed_root : /env/FIXED-STARTUP-ROOT
request_graph_root: coordination/.p6-replica-probe/graph-root
main: posts=6  delta_calls=6  request_roots=7  prod_file_ids_kept=11
      n_docs_first=58 → n_docs_last=71（单调不减）  removed_total=0
      repeat: 200 / SKIPPED_FRESH / delta_calls=0
mutation.detected: true
mutation.reason: wanted_docs 缺生产 file_id: ['329','330',...,'999020']（10 个）
mutant_file_ids: ['290','291','292','293','990301']
[cleanup] removed coordination/.p6-replica-probe
```

判据逐条：

| # | 判据 | 结果 |
|---|---|---|
| ① | 每次 delta 的 `root` == 请求体 `graph_root`，且 `request_roots=7`（6 POST + 1 重复）≠ `env_fixed_root` | PASS |
| ② | 6 次 `wanted_docs` 均含生产 11 个 file_id；`removed_total=0`；行数单调不减 | PASS |
| ③ | 生产 `current.json` 前后 sha256 逐字节相同 | PASS |
| ④ | 重复请求按真实幂等键（state 落盘 `content_hash`）返回 `SKIPPED_FRESH`、零 delta 调用 | PASS |
| ⑤ | 变异复验：换成 shadow 4 文件 state，② 必须 FAIL | PASS（确被捕获，缺 10 个 file_id） |

**⑤ 的意义**：它精确复现了 STEP2-I 的 B-1 风险形态 —— 只要 `kb_state` 是 shadow 态，`wanted_docs` 就会丢掉生产 10 个 file_id。因此「不削」的前提是**同源 state**，不是 `removed` 恒空。

---

## 四、阻塞状态更新

| 阻塞 | 本轮后状态 |
|---|---|
| **B-1**（KB_STATE 与生产图根不同源 → 覆盖生产图） | **隔离层已证伪风险路径并给出可复跑的同源 state 构造法**；但生产窗口仍须先让 18096 的 `LLMKE_KB_STATE` 指向同源 state，且需 Owner 确认授权窗口。未在生产执行。 |
| **B-2**（`/v2/graph/query kb=kb_9` 实测 `NOT_BUILT`；`QueryRequest` 无 `root`，18094 无 `LLMKE_V2_ROOT`） | **仍然成立，未解决**。本轮按 (c) 把验收改为 `current.json` 的 `documents`/`fingerprint.files` 指纹比对，不依赖查询端点；但若要求「查询可读」，仍需 Owner 在 (a) 授权重启 18094 设 `LLMKE_V2_ROOT`、(b) `QueryRequest` 增 root（需 CR）之间裁定。 |
| 依赖链 `17←16←15←14`、G-1、G-4 | 未变，仍为真实外部阻塞。 |

---

## 五、纪律留痕

- 未启动/停止/重启任何服务；8 个生产端口保持 LISTEN；生产 `platform/r12/data` 未被写入（指纹前后相同）。
- 演练的所有写盘都在 `coordination/.p6-replica-probe/`（已自动删除）；变异目录 `coordination/.p6-mut/` 已删除；离线 `commit_snapshot` 的 `.p6-probe-store` 已删除。
- 未执行 `git add` / `git commit`；未改 `generated/`；未改合同；未自签 QA、未声称 `QA_PASS`。
- `T-D2MD-17` 保持 `IN_PROGRESS`，`T-D2MD-18` 保持 `TODO`（17 未验收）。
- 新增文件：`services/.../kb_ingest_service.py`（M）、`tests/test_kb_ingest_request_graph_root.py`、`scripts/p6_request_graph_root_probe.py`、本证据文件；`TASKS.yaml` / `CHECKPOINT.md`（M）。**全部待「提交一次 git」指令入库。**
