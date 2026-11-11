# 03 · 详细开发实施步骤（P0~P7）

> 状态：**待评审，未开工**。每阶段严格按 `IMPLEMENTATION-QUEUE-V2.md:13-15` 五步闭环：`实现 → 组件级反例（先造失败） → 真实消费者集成 → 端到端验收 → 修复并回归`。不允许跳到验收；无现场命令与结果不得标 `DONE`（`:6-7`）。
> 本文的「改动文件」均为**计划**，当前仓库不存在对应实现。

---

## 阶段总览与依赖

```text
P0 评审裁定 + 基线冻结
  └→ P1 doc2md 增量能力（scan-diff / 队列 / kb-manifest / PDF IR / 幂等 / 表格通道）
       └→ P2 平台同源链路（index_writer / 同源校验 / 影子命名空间）
            ├→ P3 18094 增量端点（可并行）
            └→ P4 18096 摄取服务主链路（依赖 P2+P3）
                 └→ P5 Java 切换 + 12340 下线
                      └→ P6 影子切读 + 灰度 + E2E
                           └→ P7 退役与文档收敛
```

P1 的「表格通道补齐」是硬前置：`IMPLEMENTATION-QUEUE-V2.md:105-106` 明令表格通道未补齐前 `snapshot` 模式不得切换；`docs/NEXT.md:400-410` 同样要求先做 4a 表格通道。

---

## P0 · 评审裁定与基线冻结

**目标**：把 `05-REVIEW.md` §3 的待裁定项拿到 Owner/评审结论，冻结可复算基线。

**实施内容**

1. 复核本包 `01-EVIDENCE.md` 全部证据；评审在 `05-REVIEW.md` 的自证清单上逐条签字（独立 QA principal，不得自签：`HYBRID-RETRIEVAL-DISPATCH.md:63-68`）。
2. 冻结基线（只读，不写任何存储）：
   - 用 `scripts/v2_hybrid_baseline_freeze.py` 复跑，产物 `docs/dispatch/evidence/hybrid-baseline-doc2md-v2.json`；
   - 记录 `hybrid-baseline-0.json` 的 10 条 query（kb_9 五条含 `AAA档`/`5000万`/`T-CORE-001`、kb_1004 五条中文 + 五条英文）当前召回与答案；
   - 记录 §1 三路数量与 pk 样本、18094 两库快照 sha256。
3. 新增契约登记申请（不改 `registry.yaml` 本体，只提交附录；批准后再动）。

**组件级反例**：故意用错误的 `projection_read.INGEST_READ_PREFIX` 跑一次基线脚本，必须 FAIL 而不是「静默命中旧索引」。

**验收命令**

```bash
python3 scripts/v2_hybrid_baseline_freeze.py --out docs/dispatch/evidence/hybrid-baseline-doc2md-v2.json
make generate && make check
pytest tests/test_hybrid_rrf.py tests/test_contract_semantics.py -q
```

**回滚**：P0 只读，无回滚成本。

---

## P1 · doc2md 增量能力补齐（外部仓库 `/home/szf/data/dev/doc2md`）

**目标**：doc2md 能按知识库算出「新增/变更/删除」，只解析这一批，并输出可供平台对账的库级清单。

> **需评审裁定**：`HYBRID-RETRIEVAL-DISPATCH.md:25-38` 有「不直接改 doc2md 源码」的边界。本阶段必须改 doc2md，须 Owner 显式解除该边界（见 `05-REVIEW.md` §3-C1）。

### P1-1 `scan-diff --kb` 命令

**改动文件**：`backend/app/cli/main.py`（新增 `@app.command("scan-diff")`）、新增 `backend/app/services/kb_diff.py`、`backend/app/models/kb_manifest.py`（如需新表）。

**签名设计**

```python
def compute_kb_diff(
    *, scan_root: Path, kb: str, manifest_path: Path,
    parser_fingerprint: str, include_tombstones: bool = True
) -> KbDiff:
    """返回 DiffResult（见 02-CONTRACTS.md §4.3）+ 新的 kb-manifest 内容。

    判定顺序：
      1) 现源文件集合 = {sha256(file) -> (file_id, path)}，全量 rglob 但只算哈希
      2) 与 manifest.entries[status=ACTIVE] 比对：
         sha256 新出现 -> added；sha256 同但 file_id/path 变 -> changed
         manifest 有而磁盘无 -> removed（写 TOMBSTONE，不物理删）
      3) parser_fingerprint 与上次不同 -> 全部 ACTIVE 标 changed，reason=PARSER_FINGERPRINT_CHANGED
      4) set_digest = sha256(sorted ACTIVE (file_id, sha256, read_set_digest))
    """
```

**必须复用的既有能力**：`inventory_scanner.compute_sha256`（`core/ids.py:13-26`）、`KbFileContent` 内容寻址（`services/inventory_scanner.py:169-198`）、`KbFileInstance.source_root`（`models/file.py:31`）。

**明确不能做的事**：不自动删除原始文件（`specs/001-file-inventory/spec.md:21-25`）；不在 `scan` 里悄悄改变现有计数语义（保持 `ScanResult` 兼容）。

### P1-2 实现 `build-parse-queue` 与 `parse`

**改动文件**：`backend/app/cli/main.py:1076-1083`（替换 placeholder）、新增 `backend/app/services/parse_queue.py`。

```python
def build_queue(diff: KbDiff, *, config) -> ParseQueue:
    """added/changed 的 sha256 → 带 route_type/parser_adapter_version 的待解析项。
    复用 parser_router 的路由结果，不重新嗅探已有缓存。"""

def consume_queue(queue: ParseQueue, *, dry_run: bool, max_workers: int) -> QueueResult:
    """逐项调用既有 copy-to-vault / route-parsers / parse-markitdown|parse-mineru-pdf。
    失败项保留在队列并带 fail_reason；成功项写 kb-manifest 的 read_set_digest/artifact_id。"""
```

**关键**：`--dry-run` 必须零写入（对齐 `handoff/.../00-READ-ME-FIRST.md:52` 幂等 + dry-run 是一等公民）。

### P1-3 `kb-manifest.json` 与稳定幂等键

**改动文件**：`backend/app/core/parsed_paths.py`（新增清单路径）、`backend/app/services/markitdown_parser.py` / `mineru_pdf_parser.py`（生成清单字段）。

- `parse_manifest.json` additive 增加：`kb`、`source_root`、`read_set_digest`、`parser_fingerprint`（不得改 `parsed_text.md` 或其 hash，见 `05-data-contracts.md:9-11`）；
- `generated_at` 改为可复现：取本次批次的确定性时间（或把它们从 `read_set_digest` 的输入里排除，只对四件套内容做摘要）；
- **移除平台侧 `_reset_vault_state` 与 PDF `--force`**（`scripts/v2_ingest_doc2md.py:65-92,136-138`）：改为「仅当 `parser_fingerprint` 或 `read_set_digest` 变化才重解析」。这样 `markitdown_parser._should_skip_idempotent`（`:402-412`）与 `mineru_pdf_parser._should_skip_idempotent`（`:867-878`）才真正生效。

### P1-4 PDF 原生第 4 件

**改动文件**：`backend/app/services/mineru_pdf_parser.py`（`_finalize_success_from_staging` 附近）。

在 `:626-697` 写三件套之后，调用 doc2md 自己的 `build_from_mineru_content_list`（平台 `scripts/v2_fill_mineru_ir.py` 已在用它，逻辑可上移），写出 `document_ir.json` 并在 manifest 里对齐 `ir_source_files`。**目标**：平台可以删掉 `v2_fill_mineru_ir.py` 补口，`adapter_doc2md/adapter.py:158-165` 的 `UPSTREAM_IR_MISSING` 不再触发。

### P1-5 表格通道投影补齐（平台侧硬前置）

**改动文件**：`services/rag-alg/index_data_service/rag_projection/projection.py`（表格通道）、`ingest_pipeline/enrich.py`、`kb_pipeline.build_index_payloads`。

- doc2md IR 已有 `tables[].cells[]` 矩阵（`document_ir_schema.py:85-99`、样本 `:84-242`）；
- 平台需产出与线上 `table_chunks_<kb>` / `table_summary_<kb>` 对齐的两类载荷，并保持 `_table_pk` 与既有主键口径一致（`projection.py:93-96` vs 12340 `server/utils.py:141-148` 的 `table_chunk|...` 差异必须显式裁定）；
- 完成后才允许把 `INGEST_PROJECTION_MODE` 从 `legacy` 切到 `snapshot`（`IMPLEMENTATION-QUEUE-V2.md:105-106`）。

**组件级反例**：造一份含合并单元格 + 图片 + 表格的 xlsx/pdf，若 IR `cells[]` 与 `parsed_text.md` span 不对齐，`store._check_source_consistency`（`store.py:245-276`）必须抛错而不是产出 PARTIAL 后继续。

**验收命令**

```bash
cd /home/szf/data/dev/doc2md
python3 -m app.cli.main scan-diff --kb kb_9 --path <语料目录> --config config/app.yaml --dry-run
python3 -m app.cli.main build-parse-queue --kb kb_9 --config config/app.yaml --dry-run
python3 -m app.cli.main parse --kb kb_9 --config config/app.yaml --dry-run
# 四类真实文件各一份：pdf / docx / xlsx / txt
python3 -c "from app.services import kb_diff; print(kb_diff.selftest())"
pytest backend/tests -q
```

**回滚**：doc2md 改动全部 additive + 新命令；回滚 = 不启用新命令，现有 20 个 CLI 行为不变。`parse_manifest` 新增键为 additive，平台 `store.collect_parts` 对未知顶层文件会 `UNKNOWN_TOP_LEVEL_FILE`（`store.py:123-142`），所以**必须先同步平台侧校验白名单**再上线（列入 P2 依赖）。

---

## P2 · 平台同源链路（一次快照、三路派生）

**目标**：`store.commit()` 的同一份快照同时喂 ES/Milvus/图谱，且可机器校验同源。

### P2-1 新增 `index_writer` 适配层

**改动文件（新增）**：`services/rag-alg/index_data_service/ingest_pipeline/index_writer.py`

```python
def build(chunks, artifact, *, kb, index_prefix="v2cand_") -> IndexWritePlan:
    """一次投影 → 两份写入计划，返回 content_hash 供同源校验。
    1) 按 chunk.channel 分组：text → <prefix><kb>，table → <prefix>table_chunks_<kb>
    2) 调 enrich.build_payload 生成 metadata，剥掉顶层 pk/_fill
    3) ES 计划：{index_name, document_list, type:"", duplicate_flag:False}
       Milvus 计划：{db_name, collection_name, model_name:"bge-m3",
                     document_list, consistency_level:"Bounded", duplicate_flag:False}
    4) duplicate_flag 必须为 False：改由本层按 file_id+pk 精确删除（见下）
    """

def delete_scope(*, kb, file_id, index_prefix) -> None:
    """写前按 metadata.file_id 删除该文件旧 chunk（ES delete_by_col / Milvus del_doc_by_col）。
    禁止复用 duplicate_flag=True 的按 source 全量替换（会剪掉同 source 的其它文件）。"""

def apply(plan: IndexWritePlan, *, es_url, milvus_url) -> IndexWriteResult:
    """先 ES 后 Milvus；任一侧失败返回带 side 的结果，由调用方登记补偿任务。
    禁止只 log（对齐 ACCEPTANCE-BASELINE.yaml:28 不静默降级）。"""
```

写入端点契约：19527 `InsertFulltextDocumentsView`（`view/api/insert_fulltext_documents_view.py:13-15`，`base.py:39-62`）；19526 `insert_vector_documents_custom_view.py:13-15`（`base.py:58-65`）。

### P2-2 同源校验落到生产

**改动文件**：`ingest_pipeline/kb_pipeline.py`、`ingest_pipeline/index_writer.py`、`graph_engine_adapter/artifact_binding.py`（不改算法，只加调用点）。

```python
# consume_for_kb 内，写库与建图之前
a = index_writer.build(chunks, artifact, kb=kb)
b = build_graph_docs(chunks, file_id=file_id, ..., content_hash=a.content_hash)
assert_same_artifact(
    {"artifact_id": artifact["artifact_id"], "content_hash": a.content_hash},
    {"artifact_id": artifact["artifact_id"], "content_hash": b.content_hash},
)  # 不一致 -> SOURCE_DIVERGED，整批不发布
```

`assert_same_artifact`（`artifact_binding.py:179-199`）目前只有测试调用，本步骤把它变成生产闸门。

### P2-3 `kb_state.json` 升级

**改动文件**：`ingest_pipeline/kb_pipeline.py:174-193`（`_kb_state_path` / `_load_kb_state` / `_save_kb_state`）、`:196-286` `consume_for_kb`。

- 路径改绝对：`platform/r12/data/kb-state/kb_state.json`（`LLMKE_KB_STATE` 环境变量）；
- schema 升级到 `llmke.kb-state/2`（`02-CONTRACTS.md` §4.2），含 `version/cursor/set_digest/graph`；
- `flock` + pid/uuid 临时文件 + `os.replace`；损坏抛 `KB_STATE_CORRUPT`，禁止静默 `{}`；
- `consume_for_kb` 不再遍历全库重建图谱，改为返回「本次文件的 chunks + 全量 wanted docs 的引用」，把重建交给 P3/P4。

### P2-4 影子命名空间

**改动文件**：`alg_retrieval_service/app/projection_read.py`（对齐前缀）、`index_writer.py` 的 `index_prefix`。

**组件级反例**

1. 把 `parse_manifest.output_hash` 改一位 → `store.commit` 必须 `TEXT_HASH_MISMATCH`；
2. 把 ES 载荷的 `content_hash` 改一位 → `assert_same_artifact` 必须抛 `SOURCE_DIVERGED`，且 ES/Milvus/图**都没有写入**；
3. 两个文件共享同一 `metadata.source` → 写 A 不得删掉 B 的 chunk（验证 `delete_scope` 按 file_id 而非 source）；
4. `kb_state.json` 写坏 → 必须 `KB_STATE_CORRUPT`，不得按空库重建（防 `/tmp` 清空重演）。

**验收命令**

```bash
pytest tests/test_artifact_binding.py tests/test_projection.py -q
python3 -m ingest_pipeline.index_writer --selftest --kb kb_9 --dry-run
# 影子索引可查
curl -s http://127.0.0.1:19200/v2cand_kb_9/_count
curl -s -X POST http://127.0.0.1:19630/v2/vectordb/entities/query \
  -H 'Content-Type: application/json' \
  -d '{"collectionName":"v2cand_kb_9","dbName":"rag_knowledge_base","limit":1,"outputFields":["pk"]}'
```

**回滚**：影子命名空间独立，删掉新索引即可；旧 `<kb>` / `_kb_9` 不动。

---

## P3 · 18094 增量端点（可与 P2 并行）

**目标**：把已有但没接线的 `rebuild_delta` / `rebuild_by_policy` / `check_freshness` 接成产品端点，并补齐 DELTA 后置正确性。

### P3-1 `api.py` 新增 `POST /v2/graph/delta`

**改动文件**：`graph_engine_adapter/api.py`（新增路由 + `DeltaRequest` 模型）、新增 `graph_engine_adapter/delta_build.py`。

```python
def delta_build(req: DeltaRequest) -> Dict[str, Any]:
    root   = _kb_root(req.root, req.kb)                  # 复用 api.py:371-375
    fence  = _load_fence(root)                           # api.py:208-212 语义
    live   = [d for d in req.docs if not fence.is_revoked(d.file_id)]

    fresh  = check_freshness(read_pointer(root), live, fence)
    if not fresh["stale"] and req.requested_mode in ("auto", "skip_if_fresh"):
        return _skipped_fresh(fresh, root)

    def full_build(items, target): ...                   # 复用 _default_build:214-217
    def delta_apply(target, texts):
        return HippoRAGEngine(save_dir=target, **urls).apply_delta(texts)

    if req.requested_mode == "full":
        assert req.fallback_reason, "FULL 必须带 fallback_reason"
        result = rebuild(root, fence, live, full_build, fencing=req.fencing)
        result["effective_mode"] = "FULL"
    else:
        result = rebuild_by_policy(root, fence, live, req.kb, canary.load(...),
                                   full_build, delta_apply, fencing=req.fencing)
        # 无基准快照 -> RebuildFailed -> REJECTED，禁止自动降级

    return _finalize_snapshot(root, req, result, live, fence)
```

### P3-2 `_finalize_snapshot()`（FULL/DELTA 共用，本方案最关键的补充）

```python
def _finalize_snapshot(root, req, result, live, fence):
    target = result["current"]["dir"]
    _write_sources(target, live)                # 复用 api.py:223-238，DELTA 后必须重算
    fence.save(os.path.join(target, FENCE_FILE))
    community = global_report.write(target, [d.file_id for d in live])   # 全量重算，不沿用 copytree 的旧文件
    _write_kb_json(target, req.kb)
    _update_per_kb_state(req.kb, snapshot=target, fence=fence)
    return _pack_delta_result(result, target, community, ...)
```

**必须处理的证据**：`rebuild_delta:221` 的 `copytree` 会把旧 `sources.json`/`community.json` 带进新快照；`apply_delta` 不写它们；`global_report` 无局部 patch 接口；社区编号由全局标签传播决定（`community.py:68-97`）。

### P3-3 `state` per-kb 化与 fencing 递增

**改动文件**：`api.py:305-331,382-385`、`rebuild.py:158-189`、`fence.py`。

- `state` 改成 `states: Dict[str, StateSlot]`，`engine_for_kb` / `idx_map` / `fence_state` 全按 kb 取；
- `fencing` 不再固定 `1`（`api.py:219`），改由 `fence.generation` 或 MySQL lease 递增，使 `_promote` 的「旧主拒绝」真正生效；
- 按 kb 加 `flock`（复用 `.pointer.lock` 语义，`rebuild.py:135-155`），跨机仍靠 `lease_mysql`。

### P3-4 能力登记与描述

**改动文件**：`graph_engine_adapter/capabilities.py`（`capabilities.py:53-60` 已标 `incremental_update=VERIFIED`，需补 DELTA HTTP 端点声明）、`api.py /health` 增列端点；`docs/NEXT.md` 的「`describe()` 未登记 DELTA」（`:190-191`）关闭。

**组件级反例（必须先造失败）**

1. 删掉基准快照目录 → `NO_BASELINE_SNAPSHOT`，`REJECTED`，指针不变，旧图仍可查；
2. 传入与指针 fingerprint 完全一致的 docs → `SKIPPED_FRESH`，用 mock 断言 `full_build`/`delta_apply` **零调用**；
3. DELTA 后检查 `<snapshot>/community.json` 的 sha256 与基准快照不同、且不含已删 file_id 的引用；
4. 两库交替并发 build/query → 断言 B 库查询不会用 A 库的 `text_to_idx` / fence；
5. `fencing` 落后的写入 → `STALE_FENCING`，指针不动；
6. `apply_result.consistent=false` → `DELTA_INCONSISTENT` 且目录回滚。

**验收命令**

```bash
pytest tests/test_rebuild_delta.py tests/test_rebuild_policy_dispatch.py tests/test_graph_rebuild.py -q
python3 scripts/v2_delta_drill.py --kb kb_9 --full-vs-delta
curl -s -X POST http://127.0.0.1:18094/v2/graph/delta \
  -H 'Content-Type: application/json' -d @tests/fixtures/delta_request.json | python3 -m json.tool
```

**回滚**：`/v2/graph/build` 语义不变；新端点停用即可；指针由 `rebuild.py` 的失败回滚保证不切。

---

## P4 · 18096 摄取服务主链路

### P4-1 `KbDeltaService`

**改动文件（新增）**：`services/rag-alg/index_data_service/ingest_pipeline/kb_delta.py`；改 `kb_ingest_service.py:142-221`。

```python
class KbDeltaService:
    def diff(self, kb: str, manifest_path: Path) -> DiffResult: ...      # 见 02-CONTRACTS §4.3
    def plan(self, diff: DiffResult) -> IngestPlan:
        """diff 为空 -> SKIP_PLAN（不写索引、不调 18094）
           removed 非空 -> 先 revoke，再 delta
           added/changed -> doc2md 产物校验 + commit + 投影 + index_writer
           最后组装全库 wanted docs（从 kb_state 里所有 ACTIVE 快照投影，不重新解析）"""
    def commit(self, plan, result) -> None:
        """三路成功后才推进 cursor/version；失败不推进，事件可重放"""
```

`kb_ingest_service.py` 改造点：请求体改 Pydantic `IngestRequest`（现为裸 dict）、删除 `file_url` 全自动重解析分支（`:158-185`）、`source` 真正传给 runner、去掉默认 `pop("payloads")` 的歧义（`:216-218`）、`code` 语义按 `02-CONTRACTS` §1.2。

### P4-2 回调与失败回写

- 成功后按 `TaskReq` POST `/index/parseTask/callback`（带 `X-Internal-Token`）；
- 非 `OK`/`SKIPPED_FRESH` → Java 侧写 `PARSE_FAIL`/`RETRY`，**改掉 `RemoteV2IngestUtils.java:96-100` 只记日志的行为**。

### P4-3 部署定义（当前完全缺失）

**改动文件**：`platform/r12/bin/`（新增幂等启动脚本，参照 `r12-graph-v2-start.sh:40-67`）、`platform/r12/bin/r12-watchdog.sh:57-71`、`platform/r12/bin/up.sh:130-135,210`、`platform/r12/systemd/`（新增 unit）、`platform/r12/R12-ENV-CONTRACT.md:9-36` 端口表。

- 存活探针用 FastAPI `/openapi.json`（`r12-graph-v2-start.sh:32-38` 的既有判据：只判端口不够）；
- 环境变量在启动脚本里显式注入：`LLMKE_DOC2MD_CONFIG`、`LLMKE_DOC2MD_LOCK`、`LLMKE_ARTIFACT_STORE`（绝对持久化路径）、`LLMKE_KB_STATE`、`LLMKE_CANARY_FILE`、`R12_MINIO_*`；
- 新增启动自检（参照 `RetrievalEndpointStartupCheck`）：doc2md 可执行 + `app.yaml` 可读 + MySQL 可达 + 18094 可达 + artifact store 可写；不通 fail-fast。

**组件级反例**：停掉 18094 → 摄取必须返回 `GRAPH_UNREACHABLE` 且 Java 文件状态为 `RETRY`，**不能出现「文件显示解析成功但图没建」**。

**验收命令**

```bash
bash platform/r12/bin/r12-kb-ingest-start.sh
curl -s http://127.0.0.1:18096/openapi.json | python3 -c "import sys,json;print(sorted(json.load(sys.stdin)['paths']))"
curl -s -X POST http://127.0.0.1:18096/kb/ingest -H 'Content-Type: application/json' -d @tests/fixtures/ingest_upsert.json
grep -E 'SKIPPED_FRESH|REJECTED|GRAPH_UNREACHABLE' platform/r12/logs/kb-ingest-18096.log
```

**回滚**：`v2-ingest.url` 置空即退回旧链路（但 P5 之后 12340 已下线，故 P4/P5 之间必须有可回退窗口，见 P5 说明）。

---

## P5 · Java 切换与 12340 下线

### P5-1 派发切换

**改动文件**：`FileAppServiceImpl.java:102-226`（`filesParse`）、`:229-330`（`filesParseSync`/`doParse`）、`:612-662`（`v2Ingest`）、`:664-758`（`generateGraph`）；`RemoteV2IngestUtils.java:25-104`；`RemoteFileUtils.java`；`FileParseTaskAppServiceImpl.java:310-363`（`doSuccess`）。

- `filesParse` 改 POST `18096/kb/ingest`（`IngestRequest`）；
- **删除 `generateGraph` 的 19531 路径**，建图统一由 `/kb/ingest` 内的 `post_graph_delta` 负责；`graph_parse_status` 改由摄取响应写；
- `doSuccess` 不再无条件触发建图，只保留状态机 + 回调；
- `RemoteV2IngestUtils` 加超时、`IngestResult` 返回、失败回写。

### P5-2 配置与两仓同步

**改动文件**：两仓 `platform/r12/conf/rag-index-service/application-r12.yml`。

| 键 | 处置 |
|---|---|
| `remote.file-parse.url` / `file-parse-sync.url` / `file-revise_date.url` / `file-multi-version.url` / `tl-database-table-description.url` | 删除或改指新服务 |
| `remote.generate-graph.url` / `generate-community.url` / `del-graph-space.url` / `del-graph-entity.url` | 停用（删除语义走 fence） |
| `remote.v2-ingest.url` | 源码版补键、部署版由 `""` 改 `http://127.0.0.1:18096/kb/ingest` |
| `kb.file-parse.task-nums/task-timeout/retry-limit` | **保留**（调度器与超时判定仍依赖；注意 `task-timeout` 单位是分钟，源码版 3600 vs 部署版 60 的漂移需统一） |
| `file-parse.types` / `embedding-models` | 保留 |

**两仓一致性必须机器校验**：`diff v2仓/application-r12.yml r12仓/application-r12.yml` 的关键键逐项比对（上次故障正是双仓漂移导致 `search-docs-url` 仍指 19532）。

### P5-3 12340 退役（P5 最后一步，必须在 P4 全绿之后）

- 停 `alg_doc_parse_service` 进程；
- 移除 `r12-docparse.service`、`r12-watchdog.sh:60`、`up.sh:62-70,130-135,210`、`R12-ENV-CONTRACT.md:24` 条目标注退役；
- `RemoteFileUtils` 的「多版本解析 / revise_date / 按 documentId 取 chunk」三类辅助接口逐项给出「职责已被承接」的实测，否则不得标完成（VL6 判据）。

**回滚窗口**：P5-1~P5-2 期间 12340 仍在，可随时把 `v2-ingest.url` 置空回退；一旦执行 P5-3，回滚需重启 12340 并恢复配置，代价上升。因此 P5-3 必须在 P6 灰度之前留出至少一次完整 E2E 回归通过记录。

**验收命令**

```bash
# 全量 / 增量 / 删除 三类事件
curl -s -X POST http://127.0.0.1:18082/index/knowledgeBase/rebuildNew ... # 按实际接口
curl -s -X POST http://127.0.0.1:18096/kb/ingest -d @tests/fixtures/ingest_upsert.json
curl -s -X POST http://127.0.0.1:18096/kb/ingest -d @tests/fixtures/ingest_delete.json
# 12340 无流量
ss -tlnp | grep 12340 || echo "已退役"
grep -c '12340' platform/r12/logs/java/rag-index-service/rag-index-service.log
```

---

## P6 · 影子切读、灰度与 E2E 回归

### P6-1 按库灰度

`projection_read.py:24-56` 已有 `INGEST_READ_MODE` / `INGEST_READ_PREFIX` / `INGEST_READ_KBS`；`canary.py:188-231` 已有 full/delta 灰度策略（默认 `full`）。放量顺序：

1. `kb_9` 单库切 `v2cand` 读 + delta 策略（最小数据、便于对账）；
2. 跑 `04-ACCEPTANCE.md` 全部 required_checks；
3. 通过后再放 `kb_1004`；
4. 变更场景（内容修改）先保持 `FULL`，只让「新增文件」走 `DELTA`——因为 `docs/NEXT.md:442-458,586-592` 记录增量检索排序漂移未查清。

### P6-2 E2E 回归

- 中英文用例各 ≥10 条（过程型/事实型/清单型/数值型/时间型/否定型/跨库无关）；
- local / global / Java 智能问答三条入口；
- 基线 query 不回退（`AAA档`、`5000万`、`T-CORE-001`、`授信额度是多少`、`流动资金贷款期限`）；
- 删除与重复上传：删除后 global 引用不含已删文件；重复上传返回 `SKIPPED_FRESH`。

### P6-3 原子切读与回滚

```text
切读：INGEST_READ_MODE=snapshot + INGEST_READ_KBS=[kb_9] → 观察 → 扩库
回滚：INGEST_READ_MODE=legacy（读回旧 <kb>/_<kb>）
      图指针回退到 pointer.previous（rebuild.py:174-180 已保存）
      kb_state.json 回退到上一 version（P2 的 flock + 版本化保证）
```

旧命名空间保留 N 天只读，不物理删除，直至 P7。

---

## P7 · 退役与文档收敛

1. 确认 12340、19531 遗留路径、`community_summary_*` 无新流量后，归档旧索引/集合（**破坏性操作需 Owner 单独授权**）；
2. 更新 `R12-ENV-CONTRACT.md`、`up.sh`、`r12-watchdog.sh`、两份 `application-r12.yml`、`docs/NEXT.md`、`IMPLEMENTATION-QUEUE-V2.md` 的对应条目状态；
3. 把 `capabilities.py` 的 DELTA 能力、`describe()` 输出、新增契约登记进 `contracts/registry.yaml` 并 `make generate && make check`；
4. 归档证据到 `docs/dispatch/evidence/`：`DOC2MD-INCREMENTAL-P<n>.md`，每份含现场命令与真实输出（对齐 `IMPLEMENTATION-QUEUE-V2.md:6-7`）；
5. 关闭 `docs/NEXT.md:190-191,400-410,442-458,586-592` 里本方案解决的待办；保留「大库压测」「图分片」「跨范围合并检索」等未解决项。

---

## 改动文件总表（评审可据此评估影响面）

| 仓库 | 文件 | 阶段 | 类型 |
|---|---|---|---|
| doc2md | `backend/app/cli/main.py`（scan-diff / 两个 placeholder）、`services/kb_diff.py`（新）、`services/parse_queue.py`（新）、`services/mineru_pdf_parser.py`、`services/markitdown_parser.py`、`core/parsed_paths.py`、`config/app.yaml`（新） | P1 | 新增 + additive |
| llmke-v2 / rag-alg | `index_data_service/ingest_pipeline/index_writer.py`（新）、`kb_delta.py`（新）、`kb_pipeline.py`、`enrich.py`、`kb_ingest_service.py`、`rag_projection/projection.py`、`parse_artifact/store.py`（白名单）、`graph_engine_adapter/api.py`、`delta_build.py`（新）、`capabilities.py`、`rebuild.py`、`fence.py`、`artifact_binding.py`（加调用点） | P2/P3/P4 | 新增 + 改造 |
| llmke-v2 / rag-java | `FileAppServiceImpl.java`、`RemoteV2IngestUtils.java`、`RemoteFileUtils.java`、`RemoteGraphUtils.java`、`FileParseTaskAppServiceImpl.java`、`FileParseTaskInfo.java` | P5 | 改造 |
| llmke-v2 / platform | 两仓 `conf/rag-index-service/application-r12.yml`、`bin/r12-kb-ingest-start.sh`（新）、`bin/r12-watchdog.sh`、`bin/up.sh`、`systemd/*`、`R12-ENV-CONTRACT.md`、`.env` 或启动 env | P4/P5/P7 | 配置 + 部署 |
| llmke-v2 / contracts | `registry.yaml` + 新 api/rules 契约（**评审批准后**） | P0 申请 / P7 登记 | 契约 |
| llmke-v2 / docs | `docs/dispatch/evidence/DOC2MD-INCREMENTAL-*.md`、`docs/NEXT.md`、`IMPLEMENTATION-QUEUE-V2.md` | 全程 | 证据 |

**明确不改**：`alg_retrieval_service/app/multiple_retrieval.py`、`reranker_service.py`、`retrieval_service.py`、`retrieval_global_view.py`、19527/19526 写入端点、`/v2/graph/build` 语义、`TaskReq` 协议、HR-01~HR-10 规则本体。
