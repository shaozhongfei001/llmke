# 图根统一隔离验证（2026-11-11 → 11-12）

Owner 已批准按 `2 → 5 → 3 → 4` 顺序推进。上一轮查明三条建图通道写不同图根
（`STEP2-B-INTEGRATION-BLOCKERS-20261111.md`），本轮执行安全顺序第 1 项：
**在独立 kb / 独立数据上验证 18096 写非影子 root 时不削数据、查询槽正确重置**。
全程未改生产配置、未重启任何既有服务、未碰 `kb_9`。

## 1. 先查清的约束（代码事实，决定了验证方式）

| 事实 | 依据 |
|---|---|
| 18096 的图根由**进程环境变量** `LLMKE_V2_GRAPH_ROOT` 决定；当前生产值 `.../shadow/graph-root` | `kb_ingest_service.py:255` `_build_service()`；`/proc/<18096>/environ` |
| 请求体里的 `graph_root` 对生产路径**无效**：`create_app` 在启动时构建 `service`，`/kb/ingest` 走 `service.run(payload)`，delta 的 root 来自启动时注入的 `_delta_runner(graph_api, graph_root)` | `kb_ingest_service.py:221-235,313,344-360` |
| 18094 **没有** `LLMKE_V2_ROOT`，`_root_dir()` = `.artifacts/api-root`（cwd `/home/szf/data/dev/llmke`） | `api.py:188-189`；`/proc/<18094>/environ` 只有 `LLMKE_V2_SNAPSHOT` |
| delta 请求**不带 root** 时，`_kb_root` 也用 `.artifacts/api-root/<kb>`，且 `_is_own_root(_root_dir())` 为真 → 构建成功后**重置该 kb 查询槽** | `delta_build.py:36,51-60`；`api.py:192-204,553-571` |
| 查询按库读 `<root>/<kb>/current.json`，每库独立槽，不串库 | `api.py:208-236,401-414,423-437` |
| `operation=FULL_REBUILD` → `diff.reason=FULL_REBUILD_REQUESTED` → `requested_mode=full`（带 `fallback_reason`）→ 允许无基线建 FULL | `kb_delta.py:62,403,458`；`kb_ingest_service.py:228-235`；`delta_build.py:265-302` |
| `.artifacts/` 已被 `.gitignore:100` 忽略，落盘不污染仓库 | `git check-ignore` |

**结论**：把 18096 的 `LLMKE_V2_GRAPH_ROOT` **去掉**（不设），delta 就会落到 18094 自己的
root 并重置查询槽；不是靠请求参数，也不是改代码。本轮据此设计隔离实例。

## 2. 隔离环境

独立 18096 实例（端口 `18098`，主仓代码）：

```
env -u LLMKE_V2_GRAPH_ROOT                      # 关键：不设图根
    PYTHONPATH=.
    LLMKE_ARTIFACT_STORE=/tmp/v2-e2e-root/artifact-store   # 独立快照仓
    LLMKE_V2_GRAPH_API=http://127.0.0.1:18094              # 复用现有 18094（按 kb 隔离）
    LLMKE_ES_BASE_URL=http://127.0.0.1:19527
    LLMKE_MILVUS_BASE_URL=http://127.0.0.1:19526
    LLMKE_DOC2MD_LOCK=/home/szf/data/dev/coordination/doc2md.lock
    LLMKE_DOC2MD_CONFIG=/home/szf/data/dev/doc2md/config/app.yaml
uvicorn kb_ingest_service:app --host 127.0.0.1 --port 18098
```

`/health` = `status ok / es true / milvus true / store_root=/tmp/v2-e2e-root/artifact-store`。
独立 kb 名 `kb_e2e_root_20261111`（验证前不存在）。
两份真实 doc2md 四件套（`parse_manifest.json` + `document_ir.json` 齐全）：
`a846ab14…`（docx-table.original.docx）、`f4982001…`（e2e-v2-ingest.docx）。

## 3. 五步真实实测

| 步 | 请求 | 实测结果 |
|---|---|---|
| ① FULL 基线 | `POST 18098 /kb/ingest`，`operation=FULL_REBUILD` + `fallback_reason`，file_id `990101` | `code=200 / 摄取完成 / status=OK`；`graph.result.status=BUILT`、`requested_mode=full`、`canary_source=explicit:full`、`freshness.NO_POINTER`（full 允许）；指针 `current.json`：`documents=3, per_file=[990101]` |
| ② 基线查询 | `POST 18094 /v2/graph/query`，同 kb | **`hit_count=3, executed_route=GRAPH, docs=3, sources_available=True`**，不是 `NOT_BUILT` → 查询槽已正确重置 |
| ③ DELTA 增量 | `operation=UPSERT`，file_id `990102`，第二份四件套 | `code=200 / OK`；`diff.reason=FILE_SET_CHANGED, added=[990102], removed=[]`；`graph.result.status=BUILT, requested_mode=auto, effective_mode=DELTA, canary_source=default->delta`（**真增量，未降级 full**）；`freshness=SNAPSHOT_OUT_OF_DATE/missing=[990102]` |
| ④ DELTA 后查询 | 同 ②，问句「对账口径」 | **`hit_count=6, executed_route=GRAPH, docs=6`；命中来源 `file_id` 集合 = `['990101','990102']`** → 两份都在，旧数据未被削掉 |
| ⑤ 重复请求短路 | 重发 ③ 完全相同请求 | `code=200 / OK`；`graph.result.status=SKIPPED_FRESH, effective_mode=SKIPPED, freshness.reason=OK, stale=false`；指针 `documents=6, per_file=[990101,990102]` 与 ③ 后**完全相同**（未重建） |

③ 后指针：`documents=6`（3→6）、`per_file=['990101','990102']`、
`dir=.artifacts/api-root/kb_e2e_root_20261111/snapshot-20261112000054-708656-g0`。

**五步合起来证明**：18096 写到 18094 自己的 root 时，FULL 能建基线、DELTA 是真增量、
旧文件完整保留、查询槽重置且查询能读到全部内容、重复内容自动短路不重建。

## 4. 清理与生产未受影响

- 停掉隔离实例 `18098`；删 `.artifacts/api-root/kb_e2e_root_20261111/`、删 `/tmp/v2-e2e-root/`；
  删隔离实例写出的 `platform/r12/data/kb-state/`（内容只含 `kb_e2e_root_20261111` 键）。
- 精确调用 `/del_collection`（19526）与 `/del_index`（19527）删除独立 kb 的 3 个名称，
  服务均回「不存在/无需删除」，说明本轮未产生搜索路集合残留。
- 生产 `kb_9` 指针前后一致：app 根 `documents=46 / per_file=11`，影子根 `documents=4 / per_file=3`。
- 端口 `12340 / 18096 / 18097 / 19531 / 18094 / 19995 / 18083 / 8088` 全部保持 LISTEN。
- 唯一内存残留：18094 进程内 `kb_e2e_root_20261111` 的 per-kb 槽仍指向已删快照；
  该槽与本库绑定、不影响其它 kb，需重启 18094 才清。为不中断生产，本轮**未重启 18094**。

## 5. 结论与仍在生产切换之前的前置

**技术路径已验证可行**：统一图根的正确实现是让 18096 不带 `LLMKE_V2_GRAPH_ROOT`
（与 18094 默认 root 对齐），而不是改请求参数或改代码。

但**生产切换仍需先解决三件事**（否则会把生产图削掉）：

1. **基线语料对齐**：影子 manifest 只有 3 个文件，生产 `kb_9` 有 11 个文件 / 46 块。
   直接把 18096 切到生产 root 后对 `kb_9` 做 UPSERT，会按影子 manifest 的
   "全库存活文档"把生产图削成 3 个文件。需先以生产语料跑一次
   `operation=FULL_REBUILD`（本轮已验证该机制可用），或让 18096 的 store 从生产
   ES/Milvus 读全量 chunks 建立同口径 manifest。
2. **校正旧软链指针**：生产 `kb_9/current.json` 的 `dir` 仍指向已删除的
   `/home/szf/data/dev/llmke-r12/...`，切换前必须改成有效路径。
3. **通道互斥**：19531 的 build 与 18096 的 delta 不得并发写同一 root；切换窗口内
   先停 19531（Owner 已授权），再做原子切换。

此外 `STEP2-B` 记录的另外两项仍未解决：12340 + doc2md 双解析、rag-index-service 双实例 + 旧 jar。

## 6. 下一步建议

1. 设计一次**生产语料 FULL_REBUILD 基线**（以 ES 全量 chunks 或全量 doc2md 四件套为 wanted），
   在隔离 root 上先演练一次 11 文件 / 46 块规模，确认不削数据后再切生产 root。
2. 生产切换窗口：停 19531 → 去掉 18096 的 `LLMKE_V2_GRAPH_ROOT` 并重启 → 校正 `kb_9` 指针 → 验证查询。
3. 之后才轮到去掉 12340 双解析、清理双实例、部署新 jar、填 `v2-ingest.url`、rebuild dist 与四类格式实测。

本轮未产生任何生产写入，未提交任何改动。
