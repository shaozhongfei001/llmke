# 02 · 新增/变更契约（待评审，未实现）

> 本文定义 P1~P6 要新增或变更的**机器可校验契约**。所有 schema 版本从 `v1` 起；字段名沿用现有 `snake_case`；错误码沿用 `v2-only` 命名空间（`contracts/rules/llmke-hybrid-retrieval.yaml:58`）。
> **本包不修改 `contracts/registry.yaml`**（`IMPLEMENTATION-QUEUE-V2.md:414` 规定仅合同变更任务可改）；评审通过后再登记并重跑 `make generate && make check`。

---

## 1. `POST 18096 /kb/ingest`（替换现有裸 dict 请求体）

### 1.1 请求 `IngestRequest` schema `llmke.kb-ingest.request/1`

```json
{
  "kb": "kb_9",
  "file_id": 290,
  "operation": "UPSERT",
  "doc2md_dir": "/abs/path/to/parsed/by_hash/ab/cd/<sha>",
  "file_url": "",
  "file_name": "授信台账.xlsx",
  "file_path": "r12-rag/kb_9/xxx.xlsx",
  "file_size": 12345,
  "index_name": "kb_9",
  "build_graph": true,
  "graph_root": "/home/szf/data/dev/llmke-r12/platform/r12/data/graph-root",
  "graph_api": "http://127.0.0.1:18094",
  "requested_mode": "auto",
  "expected_cursor": "cursor-<sha256>",
  "include_payloads": false,
  "timeout": 1800
}
```

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `kb` | string | 是 | primitiveName，如 `kb_9`；必须匹配 `^[a-zA-Z0-9_]+$`，禁止路径穿越（对齐 `06_...:43`） |
| `file_id` | int/string | 是 | 平台文件 id；作为 `kb-manifest` 主键 |
| `operation` | enum | 是 | `UPSERT` / `DELETE` / `FULL_REBUILD`。`FULL_REBUILD` 必须带 `fallback_reason` |
| `doc2md_dir` | string | 条件 | `UPSERT` 时必填且目录存在、四件套齐全；**不再支持 `file_url` 全自动分支重新解析**（保证「解析只发生一次」） |
| `file_url` | string | 否 | 保留兼容，但只允许用于下载元数据展示，不得触发第二次解析 |
| `expected_cursor` | string | 否 | 乐观并发：与 `kb_state.json` 当前 cursor 不符 → `CURSOR_CONFLICT`，调用方重读重试 |
| `requested_mode` | enum | 否 | `auto`（默认）/ `delta` / `full` / `skip_if_fresh`；`full` 必须带 `fallback_reason` |
| `fallback_reason` | string | 条件 | `full` 必填，写入审计日志与 18094 响应，禁止静默降级 |
| `build_graph` | bool | 否 | 默认 true；false 时只写 ES/Milvus（用于 P2 分阶段验收） |
| `include_payloads` | bool | 否 | 默认 false。**注意**：响应里不带载荷 ≠ 载荷未落库；落库由 `index_writer` 完成（修 `kb_ingest_service.py:216-218` 的语义歧义） |

**与现状的差异**：现请求体是裸 dict、`file_url` 分支会重新跑 doc2md（`kb_ingest_service.py:158-185`）、`source` 读了不传、无 operation/cursor/mode。

### 1.2 响应 `IngestResult` schema `llmke.kb-ingest.result/1`

```json
{
  "schema": "llmke.kb-ingest.result/1",
  "code": 200,
  "msg": "摄取完成",
  "data": {
    "status": "OK",
    "kb": "kb_9",
    "cursor": "cursor-<sha256>",
    "diff": {
      "added": ["290"], "changed": [], "removed": [], "unchanged": ["329", "330"],
      "set_digest": "<sha256>", "reason": "FILE_SET_CHANGED"
    },
    "artifact": {
      "artifact_id": "<64hex>", "content_uid": "<64hex>",
      "content_hash": "<64hex>", "read_set_digest": "<64hex>",
      "snapshot": "/abs/path/to/artifact-store/<artifact_id>",
      "parser_fingerprint": "<64hex>"
    },
    "projection": {
      "status": "READY", "chunks": 12,
      "channels": {"text": 11, "table": 1},
      "counts": {"kb_9": 11, "table_chunks_kb_9": 1}
    },
    "index_write": {
      "es": {"index": "v2cand_kb_9", "written": 11, "deleted": 8, "duplicate_scope": "file_id+pk"},
      "milvus": {"collection": "v2cand_kb_9", "written": 11, "deleted": 8, "model": "bge-m3"},
      "same_artifact": true
    },
    "graph": {
      "requested_mode": "auto", "effective_mode": "DELTA",
      "status": "BUILT", "documents": 46,
      "apply_result": {"added": 2, "deleted": 1, "reused": 44, "consistent": true},
      "snapshot": "/abs/graph-root/kb_9/snapshot-...",
      "community": {"status": "READY", "community_count": 28, "sha256": "<64hex>"},
      "fallback_reason": null
    }
  }
}
```

`code` 语义（替换现 `200/207` 只看 `status` 的做法）：

| code | status | 含义 | Java 侧动作 |
|---|---|---|---|
| 200 | `OK` | 三路全部成功 | 写 `PARSE_SUCCESS` |
| 200 | `SKIPPED_FRESH` | diff 为空或 fingerprint 命中，未跑 LLM | 写 `PARSE_SUCCESS`，记 `skipped=true` |
| 207 | `PARTIAL` | 搜索路成功、图谱路可恢复失败 | **回写 `RETRY` 并带原因**，不得假成功 |
| 4xx/5xx | `REJECTED` / `FAILED` | 见 §5 错误码 | 回写 `PARSE_FAIL` / `RETRY` |

### 1.3 回调 Java（沿用 `TaskReq`）

摄取完成后 POST `/index/parseTask/callback`，带 `X-Internal-Token`：

```json
{"success": true, "msg": "", "task_id": 123,
 "task_statuses": [{"file_path": "...", "file_id": 290, "success": true,
                    "fail_reason": "", "revise_date": "2026-11-08 00:00:00"}]}
```

硬约束：`task_id` 非空、`task_statuses` 至少 1 条且 `revise_date` 非空（否则 `FileParseTaskAppServiceImpl.java:302,332` 越界/写空）。

---

## 2. `POST 18094 /v2/graph/delta`（新增端点）

### 2.1 请求 `DeltaRequest` schema `llmke.graph-api.delta/1`

```json
{
  "schema": "llmke.graph-api.delta/1",
  "kb": "kb_9",
  "docs": [
    {"file_ids": ["290"], "text": "...", "locator": "chunk=0;offset=0-512",
     "pk": 318101056057432139, "title": "授信台账.xlsx",
     "parse_artifact_id": "<64hex>", "content_hash": "<64hex>"}
  ],
  "requested_mode": "auto",
  "fallback_reason": null,
  "set_digest": "<sha256>",
  "revoked_file_ids": ["999"],
  "root": "/abs/graph-root",
  "fencing": 7
}
```

**`docs` 必须是该库全量 wanted texts**（§7.2 of `00-DESIGN.md`）。服务端必须校验 `len(docs) > 0`；空请求 400，不得当成「清空图谱」（对齐 `api.py:368-370` 的既有语义）。

**`file_ids` 支持 1:N（同文异源）**：两块完全相同文本（块 id 是文本哈希）在引擎里合并为一块，`file_ids` 数组承载「这块文本同时属于哪些文件」。`apply_delta` 前平台侧按 `text` 去重出 wanted texts，`sources.json` 重建时由 `file_ids` 恢复 1:N 映射；删除单文件时只从对应 `file_ids` 剔除该 file_id，块保留。若某文本只属一个文件，`file_ids` 为单元素数组。

### 2.2 响应

```json
{
  "schema": "llmke.graph-api.delta-result/1",
  "status": "BUILT",
  "kb": "kb_9",
  "requested_mode": "auto",
  "effective_mode": "DELTA",
  "mode": "DELTA",
  "snapshot": "/abs/graph-root/kb_9/snapshot-<stamp>-g7",
  "documents": 46,
  "freshness": {"stale": true, "reason": "SNAPSHOT_OUT_OF_DATE",
                "missing": ["290"], "removed": ["999"], "changed": []},
  "apply_result": {"deleted": 1, "added": 2, "reused": 44,
                   "duplicates": 0, "remaining": 46, "expected": 46, "consistent": true},
  "sources": {"written": true, "entries": 46},
  "community": {"path": ".../community.json", "sha256": "<64hex>",
                "community_count": 28, "citation_check": {"ok": true}, "status": "READY"},
  "fence": {"generation": 7, "revoked": ["999"]},
  "fallback_reason": null
}
```

`status` 枚举：

| status | effective_mode | 触发 | 是否写指针 |
|---|---|---|---|
| `BUILT` | `FULL` / `DELTA` | 重建成功 | 是 |
| `SKIPPED_FRESH` | `SKIP` | `check_freshness` 判 fresh 且 `requested_mode in (auto, skip_if_fresh)` | 否 |
| `REJECTED` | `NONE` | 无基准快照 / 全撤权 / fencing 落后 / `consistent=false` | 否，保留旧指针 |

### 2.3 服务端不变式（可机器断言）

1. `SKIPPED_FRESH` 时 `snapshot` 必须等于当前指针目录，且不得调用 `full_build`/`delta_apply`；
2. `effective_mode=DELTA` 时 `apply_result.consistent == true` 且 `remaining == expected == documents`；
3. 任何 `BUILT` 后，`<snapshot>/sources.json`、`community.json`、`fence.json`、`kb.json` 四个文件都必须存在且由本次输入重算（**不是 copytree 带过来的旧文件**）；
4. `requested_mode != effective_mode` 时必须有非空 `fallback_reason`；
5. `community.citation_check.ok` 为 false 时返回 `PARTIAL`（`status=BUILT` 但带 `community.status=BLOCKED`），禁止把不可用报告当成功；
6. `fencing` 落后 → `StaleFencingError`，指针不动（`rebuild.py:167-172`）；
7. `fencing` 取值 = `max(fence.generation, lease_mysql.lease_epoch)`，`fence.generation` 由平台 `kb_state.json.version` 派生：同机 `flock` 串行、跨机 `lease_mysql` 唯一，保证 generation 单调递增。

### 2.4 与既有 `/v2/graph/build` 的关系

`/v2/graph/build` **保持 FULL 语义不变**，供离线全量重建与存量调用方使用。新增 `/v2/graph/delta` 不修改 build 的请求/响应结构。两者共用 `_finalize_snapshot()`（§7.4）。

---

## 3. `POST 18094 /v2/fence/revoke`（新增，删除前置）

```json
{"kb": "kb_9", "file_ids": ["999"], "reason": "DOCUMENT_DELETED", "generation": 7}
```

响应：`{"schema": "llmke.graph-api.fence/1", "generation": 7, "revoked": ["999"], "pointer": "..."}`。

语义继承 `fence.py:25-39`：重复撤权幂等（不重复推进 generation）；`filter_hits`（`:120-132`）在重建完成前先挡读。删除流程必须是「revoke → delta → 重算报告」，顺序不可换。

---

## 4. 库级数据结构

### 4.1 `kb-manifest.json`（doc2md 侧新增，schema `llmke.doc2md.kb-manifest/1`）

```json
{
  "schema": "llmke.doc2md.kb-manifest/1",
  "kb": "kb_9",
  "cursor": "cursor-<sha256>",
  "set_digest": "<sha256 of sorted active entries>",
  "generated_at": "2026-11-08T00:00:00+08:00",
  "parser_fingerprint": "<64hex>",
  "entries": [
    {"file_id": "290", "sha256": "<64hex>", "source_path": "...",
     "read_set_digest": "<64hex>", "artifact_id": "<64hex>",
     "status": "ACTIVE", "route_type": "XLSX", "parser_adapter_version": "005_mvp_v1"},
    {"file_id": "999", "sha256": "<64hex>", "status": "TOMBSTONE",
     "revoked_at": "2026-11-08T00:00:00+08:00", "reason": "SOURCE_REMOVED"}
  ]
}
```

- `cursor` 单调推进，`set_digest` 只覆盖 `status=ACTIVE` 条目；
- 删除用 TOMBSTONE，不物理删条目（保证可审计、可重放）；
- 路径基准是受控对象 ID，不允许任意主机路径（对齐 `06_...:43`）。

### 4.2 `kb_state.json`（平台侧升级，schema `llmke.kb-state/2`）

```json
{
  "schema": "llmke.kb-state/2",
  "version": 7,
  "cursor": "cursor-<sha256>",
  "set_digest": "<sha256>",
  "kb": {
    "kb_9": {
      "290": {"artifact_id": "<64hex>", "snapshot": "/abs/...", "content_uid": "<64hex>",
              "content_hash": "<64hex>", "file_name": "...", "status": "ACTIVE"},
      "999": {"status": "TOMBSTONE", "revoked_at": "..."}
    }
  },
  "chunks": {
    "kb_9": {
      "290": [
        {"pk": 318101056057432139, "text": "...", "locator": "chunk=0;offset=0-512",
         "channel": "text", "content_hash": "<64hex>"}
      ]
    }
  },
  "graph": {"kb_9": {"snapshot": "/abs/...", "fencing": 7, "mode": "DELTA"}}
}
```

强制要求（针对 `kb_pipeline.py:174-193` 的现存缺陷）：

- 绝对路径存储：`platform/r12/data/kb-state/kb_state.json`，**禁止 `/tmp`**；
- `flock` 保护读-改-写；写临时文件名带 pid/uuid，不用固定 `.json.tmp`；
- JSON 损坏 / schema 不符 → 抛 `KB_STATE_CORRUPT`，**禁止静默返回 `{}`**；
- `version` 与 `cursor` 参与乐观并发；`expected_cursor` 不符 → `CURSOR_CONFLICT`；
- `chunks` 是「全库 wanted docs」的唯一组装来源：投影结果**只算一次落盘**，`seq` 在文件首次投影时分配后固定；组装 wanted docs 读 `chunks[*]` 拼接，不重新投影（否则 `seq` 重排破坏 pk 一致，见 `00-DESIGN.md` §7.5.1）。

### 4.3 `DiffResult` schema `llmke.kb-diff/1`

```json
{"kb": "kb_9", "added": ["290"], "changed": [], "removed": ["999"],
 "unchanged": ["329","330"], "cursor": "cursor-<sha256>",
 "set_digest": "<sha256>", "reason": "FILE_SET_CHANGED", "computed_at": "..."}
```

`reason` 枚举：`FILE_SET_CHANGED` / `CONTENT_CHANGED` / `PARSER_FINGERPRINT_CHANGED` / `NO_CHANGE` / `FULL_REBUILD_REQUESTED`。判定优先级：显式 `FULL_REBUILD_REQUESTED` > removed > added/changed > parser_fingerprint 变化 > `NO_CHANGE`。

---

## 5. 错误码（`v2-only` 命名空间）

| code | HTTP | 语义 | 触发点 | 调用方动作 |
|---|---|---|---|---|
| `DOC2MD_ARTIFACT_INCOMPLETE` | 400 | 四件套缺失或不合法 | `store.collect_parts` / `_check_source_consistency` | 不写任何索引，回写 `PARSE_FAIL` |
| `SOURCE_DIVERGED` | 409 | 搜索载荷与 BuildDoc 的 `content_hash` 不一致 | `assert_same_artifact` 生产调用点 | 整批不发布 |
| `KB_STATE_CORRUPT` | 500 | 清单损坏/版本不符 | `kb_state` 读取 | 停止摄取并告警，禁止按空库重建 |
| `CURSOR_CONFLICT` | 409 | 并发写同一库 | `expected_cursor` 校验 | 重读后重试（指数退避） |
| `NO_BASELINE_SNAPSHOT` | 422 | DELTA 无基准快照 | `rebuild_delta:204-211` | 显式带 `full + fallback_reason` 重试，禁止自动降级 |
| `ALL_REVOKED` | 422 | 全部文件撤权，拒绝生成空快照 | `rebuild.py:111-112` | 人工介入 |
| `STALE_FENCING` | 409 | fencing 落后 | `rebuild.py:167-172` | 放弃本次写入 |
| `DELTA_INCONSISTENT` | 500 | `apply_result.consistent=false` 或 count 不符 | `engine_hipporag.py:97-101` | 指针不动，回滚目录 |
| `COMMUNITY_INVALID` | 207 | 报告引用校验不通过 | `global_report.py:91-121` | 图可用但 global 返回 `BLOCKED`，不得用普通 RAG 顶替 |
| `GRAPH_UNREACHABLE` | 502 | 18094 不可达 | HTTP 客户端 | 回写 `RETRY`，前端显示原因（禁止静默降级） |
| `INDEX_WRITE_FAILED` | 502 | ES/Milvus 写入失败 | `index_writer` | 已写的一侧显式记录补偿任务，不得只 log |

---

## 6. 状态机（不变项与新增项）

### 6.1 沿用（不得改语义）

```text
文件: PARSE_WAIT(99) → PARSE_ING(2) → PARSE_SUCCESS(3) | PARSE_FAIL(4) | RETRY(98)
任务: PENDING(1) → DEAL_ING(2) → SUCESS(4) | RETRY_ING(3) | DEAL_FAIL(5)
图谱: NORMAL(1) → PARSE_ING(2) → PARSE_SUCCESS(3) | PARSE_FAIL(4)
```

出处：`KbFileStatusEnums.java:3-14`、`ParseTaskStatusEnums.java:3-11`、`GraphParseStatusEnums.java:3-8`；写入序列 `KnowledgeBaseListAppServiceImpl.java:602`、`FileAppServiceImpl.java:202`、`FileParseTaskAppServiceImpl.java:321,336`、`doFail:421-434`。

**新增约束**：摄取响应非 `OK`/`SKIPPED_FRESH` 时，必须回写 `PARSE_FAIL`/`RETRY`（修 `RemoteV2IngestUtils.java:96-100` 只记日志的缺陷）。

### 6.2 新增：重建模式状态机

```text
         ┌─────────────── check_freshness = fresh ──────────────→ SKIP
事件 ──→ diff 非空
         └─ stale ─┬─ 有基准 & policy=delta → DELTA ──┐
                    ├─ 显式 full + fallback_reason → FULL ─┤→ _finalize_snapshot → CAS 切指针
                    └─ 无基准 / 全撤权 / fencing 落后 → REJECTED（指针不动）
```

`requested_mode` 与 `effective_mode` 必须同时返回，供审计对账（`rebuild_by_policy:279-281`）。

---

## 7. pk 与索引命名契约

### 7.1 pk 规则（不变）

```text
_chunk_pk(index_name, file_id, seq, text)
  seed = "chunk|{index_name.lower()}|{file_id}|{seq}|{sha1(text).hexdigest()}"
  pk   = int(sha1(seed.encode()).hexdigest()[:15], 16)
_table_pk: seed = "table|{index_lower}|{file_id}|{ordinal}"（同取前 15 hex）
```

出处：`projection.py:119-127,93-96`；与 12340 `server/utils.py:103-122`、ES `es.py:38-45`、Milvus `milvus_kb_service.py:622-636` 算法同源。**但 `seq` 口径不同**（投影枚举序 vs `parsed_chunk_index`），故切换解析器必然换 pk，见 §7.3。

### 7.2 三路必须给出的字段（检索侧消费形状不改）

| 来源 | 字段 | 消费方 |
|---|---|---|
| ES `_source.metadata` | `pk`(int)、`file_id`、`chunk_index`、`source`、`title`、`offset`、`chunk_doc_id`、`document_id`、`type`、`knowledge_base_name`、`parse_artifact_id`、`content_uid`、`content_hash` | `multiple_retrieval.py:120-134`；`reranker_service.py:41-63` RRF by pk；`retrieval_service.py:309-347` 邻块；`retrieval_global_view.py:212-242` 反查 source |
| Milvus row | `pk`(int 主键)、`text`、`vector`、`source`、`chunk_doc_id`、`document_id`、`chunk_index`、`metadata.*`（schema 内字段） | `multiple_retrieval.py:142-230` |
| 18094 docs / `sources.json` | `pk`(int)、`file_id`、`locator`（含 `chunk=<seq>`）、`title`、`parse_artifact_id` | `multiple_retrieval.py:435-447,493-521`；`global_report.py:59-88` |

**硬约束**：`pk` 必须是整数（`_pick_pk` 对字符串 `"chunk-<md5>"` 一律返回 None），否则 Java `RetrieveDoc.pk`（Long）`parseLong` 抛异常、RRF 拆条。

### 7.3 影子命名空间（切换期）

```text
ES:      v2cand_<kb>, v2cand_table_chunks_<kb>, v2cand_table_summary_<kb>
Milvus:  v2cand_kb_<name>
图:      <graph-root>/<kb>/ 不变（指针 CAS 已是原子的）
读:      projection_read.INGEST_READ_PREFIX = v2cand, INGEST_READ_KBS = [kb_9] 灰度
```

写入前缀与 `INGEST_READ_PREFIX` 必须一致，否则切读会读空。切换完成后旧命名空间保留 N 天只读；回滚 = 切回旧前缀 + 图指针回退到 `pointer.previous`。

---

## 8. 同源校验契约

```text
content_hash = sha256(canonical_json({
  "schema": "llmke.artifact-binding.chunks/1",
  "chunks": [ {"locator_key": ..., "text_sha256": ...} ... ]   # 顺序是内容的一部分
}))
```

- 计算口径复用 `artifact_binding.py:32,167-173`；
- `index_writer.build()` 与 `post_graph_delta()` 各自算一次，摄取服务用 `assert_same_artifact`（`artifact_binding.py:179-199`）比对 `artifact_id` 与 `content_hash`；
- 任一不一致 → `SOURCE_DIVERGED`，整批不发布；
- 因 Milvus 会丢弃 schema 外字段（`milvus_kb_service.py:538-540`），同源校验**必须在平台侧写入前完成**，不得依赖 Milvus 持久化 `content_hash`。

**两层校验，口径不同（不可混用）**：

| 层 | 对象 | 手段 | 失败处置 |
|---|---|---|---|
| 单文件层 | 同一文件 `chunks` 的 ES/Milvus 载荷 vs BuildDoc | `assert_same_artifact`（artifact_id + content_hash） | `SOURCE_DIVERGED` 整批不发布 |
| 全库层 | 传给 18094 的全库 wanted docs 完整性 | 18094 `docs_fingerprint` + 平台 `set_digest` | `SKIPPED_FRESH` / 重建 |

`content_hash` 只用于单文件同源性；全库 wanted docs 的完整性由指纹/摘要校验，两者不互相替代。

---

## 9. 兼容承诺（供评审核对「不改检索侧」）

| 承诺 | 依据 |
|---|---|
| 19995 三路检索的请求/响应形状不变 | `multiple_retrieval.py:91-139,142-230,450-523`；`retrieval_service.py:486-564` |
| RRF 仍按 `metadata.pk`（k=60），rerank 仍是 top_n×3 + 相对阈值 | `reranker_service.py:27-74,178-250`；HR-06/07 |
| global 仍读 18094 `/v2/graph/global` 与 `community.json` | `retrieval_global_view.py:16-81`；`api.py:634-730` |
| 19527/19526 写入端点不改 | 本方案只新增 `index_writer` 调用方 |
| `/v2/graph/build` 语义不变 | 新增 `/delta` 为独立端点 |
| 回调 `TaskReq` 协议不变 | `TaskReq.java:11-43` 与 `response_model.py:32-43` 一一对应 |

---

## 10. 契约校验落地方式（评审批准后）

1. 把 §1/§2/§4/§5 的 schema 登记进 `contracts/registry.yaml`（新增 1 份 `api` + 1 份 `rules`），`x-lifecycle` 标 `DESIGN_REVISED_NOT_IMPLEMENTED`；
2. 为该契约写 `checker`（现 `contract_toolchain.py:34-60` 对 `rules` 只校验顶层键存在，不能保证 HR/新不变量逐条生效）；
3. `make generate && make check` + `pytest tests/test_contract_semantics.py tests/test_hybrid_rrf.py -q`；
4. 新增运行时断言测试：三路 pk 一致、同源 hash 一致、`SKIPPED_FRESH` 不跑 LLM、`DELTA` 后四文件重算、失败不切指针。
