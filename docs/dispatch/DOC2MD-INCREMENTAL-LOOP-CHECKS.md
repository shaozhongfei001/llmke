# DOC2MD-INCREMENTAL Loop 验收命令 + 反例夹具清单

> 用途：TL 开工抓手。每个 loop 给出「验收命令（可执行）+ 反例夹具（造失败输入）+ 通过判据」。开发前 TL 与实现角色据此共同确认「若没做对哪条 FAIL」，开发后据此自证 `DEV_SELF_CHECK_PASS`。反例必须先 FAIL 再证明修复后 PASS。

## Loop 0 · 基线冻结 + Gate 收集（P0，只读）

```bash
python3 scripts/v2_hybrid_baseline_freeze.py --out docs/dispatch/evidence/hybrid-baseline-doc2md-v2.json
make generate && make check
pytest tests/test_hybrid_rrf.py tests/test_contract_semantics.py -q
```
- 反例：`projection_read.INGEST_READ_PREFIX` 故意写错 → 基线脚本必须 FAIL（不得静默命中旧索引）。
- 通过：baseline-doc2md-v2.json 产出，10 条 query（含 `AAA档`/`5000万`/`T-CORE-001`）冻结；G-1~G-5 各得结论。

## Loop 1 · scan-diff --kb（P1）

```bash
cd /home/szf/data/dev/doc2md
python3 -m app.cli.main scan-diff --kb kb_9 --path <语料目录> --config config/app.yaml --dry-run
python3 -c "from app.services import kb_diff; print(kb_diff.selftest())"
```
- 反例：语料「新增1+删除1+修改1+不变2」→ `DiffResult` 精确 `added=[新] removed=[删] changed=[改] unchanged=[2]`；错传 `parser_fingerprint` → 全 ACTIVE 标 changed 且 `reason=PARSER_FINGERPRINT_CHANGED`。
- 通过：删除记 TOMBSTONE 不物理删；重放 diff 幂等。

## Loop 2 · build-parse-queue / parse（P1）

```bash
python3 -m app.cli.main build-parse-queue --kb kb_9 --config config/app.yaml --dry-run
python3 -m app.cli.main parse --kb kb_9 --config config/app.yaml --dry-run
```
- 反例：缺路由结果的 sha256 不得进入 parse 队列。
- 通过：`--dry-run` 零写入；失败项保留在队列带 `fail_reason`。

## Loop 3 · kb-manifest.json + 幂等键（P1）

```bash
# 同一文件连续 parse 两次，第二次应命中幂等跳过
python3 -m app.cli.main parse --kb kb_9 --config config/app.yaml
```
- 反例：改一位 `parsed_text.md` → `output_hash` 失配，`store._check_source_consistency` 抛错。
- 通过：移除 `_reset_vault_state` SQL 与 PDF `--force`；`generated_at` 排除出 `read_set_digest`。

## Loop 4 · PDF 第 4 件（P1）

```bash
cd /home/szf/data/dev/doc2md
python3 -m app.cli.main parse-mineru-pdf --sha256 <样本> --config config/app.yaml
# 校验四件套齐全 + IR span 逐字对齐
```
- 反例：缺 IR 的 PDF 走 markitdown 路径 → 显式报 `UPSTREAM_IR_MISSING`，不静默继续。
- 通过：`document_ir.json` 产出；平台 `scripts/v2_fill_mineru_ir.py` 可删。

## Loop 5 · 表格通道投影（P1，硬前置）

```bash
pytest tests/test_projection.py -q
# 造含合并单元格 + 图片 + 表格的 xlsx/pdf
```
- 反例：IR `cells[]` 与 `parsed_text.md` span 不对齐 → `store._check_source_consistency` 抛错而非产出 PARTIAL。
- 通过：`table_chunks_<kb>`/`table_summary_<kb>` 与线上对齐；完成前 `snapshot` 模式禁切。

## Loop 6 · index_writer + delete_scope（P2）

```bash
python3 -m ingest_pipeline.index_writer --selftest --kb kb_9 --dry-run
curl -s http://127.0.0.1:19200/v2cand_kb_9/_count
```
- 反例：两文件共享 `metadata.source`，写 A 不得删 B 的 chunk（验证 `delete_scope` 按 file_id 而非 source）。
- 通过：`duplicate_flag=False`；ES/Milvus 两份计划字段齐全。

## Loop 7 · 同源校验 + kb_state v2（P2）

```bash
pytest tests/test_artifact_binding.py tests/test_projection.py -q
```
- 反例：① `parse_manifest.output_hash` 改一位 → `store.commit` 必须 `TEXT_HASH_MISMATCH`；② ES 载荷 `content_hash` 改一位 → `assert_same_artifact` 抛 `SOURCE_DIVERGED` 且三路都没写；③ `kb_state.json` 写坏 → `KB_STATE_CORRUPT` 不按空库重建。
- 通过：`kb_state` 含 `chunks` 子结构 + flock + 版本号。

## Loop 8 · 影子命名空间（P2）

```bash
grep -n 'INGEST_READ_PREFIX' services/rag-alg/alg_retrieval_service/app/projection_read.py
```
- 反例：写前缀与 `INGEST_READ_PREFIX` 不一致 → 切读后读空，必须 FAIL。
- 通过：`v2cand_` 与读前缀一致。

## Loop 9 · /v2/graph/delta + _finalize_snapshot（P3）

```bash
pytest tests/test_rebuild_delta.py tests/test_rebuild_policy_dispatch.py tests/test_graph_rebuild.py -q
curl -s -X POST http://127.0.0.1:18094/v2/graph/delta -H 'Content-Type: application/json' -d @tests/fixtures/delta_request.json | python3 -m json.tool
```
- 反例：① 删基准快照目录 → `NO_BASELINE_SNAPSHOT` + `REJECTED`，指针不动；② fingerprint 一致 → `SKIPPED_FRESH` 且 `full_build`/`delta_apply` 零调用；③ DELTA 后 `community.json` sha256 与基准不同且不含已删 file_id。
- 通过：四文件（sources/community/fence/kb）由本次输入重算。

## Loop 10 · state per-kb + fencing（P3）

```bash
pytest tests/test_d8_fence_cas.py -q   # fence/CAS 既有回归
```
- 反例：两库交替并发 build/query → 断言 B 库查询不用 A 库的 `text_to_idx`/fence；fencing 落后 → `STALE_FENCING` 指针不动。
- 通过：`states: Dict[kb, StateSlot]`；`fencing=max(fence.generation, lease_mysql.lease_epoch)`。

## Loop 11 · 能力登记（P3）

```bash
curl -s http://127.0.0.1:18094/health | python3 -m json.tool   # 端点列表含 /v2/graph/delta
```
- 通过：`capabilities.py` 登记 DELTA；`describe()` 如实声明「增量抽取 + 全量重建图」。

## Loop 12 · KbDeltaService（P4）

```bash
curl -s -X POST http://127.0.0.1:18096/kb/ingest -H 'Content-Type: application/json' -d @tests/fixtures/ingest_upsert.json | python3 -m json.tool
grep -E 'SKIPPED_FRESH|REJECTED|GRAPH_UNREACHABLE' platform/r12/logs/kb-ingest-18096.log
```
- 反例：diff 空 → `SKIPPED_FRESH` 不写索引不调 18094；cursor 推进与三路成功必须原子（18094 失败时 cursor 不推进，可重放）。
- 通过：wanted docs 读 `kb_state.chunks` 拼接，不重投影。

## Loop 13 · 部署定义 + 启动自检（P4）

```bash
bash platform/r12/bin/r12-kb-ingest-start.sh
curl -s http://127.0.0.1:18096/openapi.json | python3 -c "import sys,json;print(sorted(json.load(sys.stdin)['paths']))"
```
- 反例：停 18094 → 摄取返回 `GRAPH_UNREACHABLE` + Java 状态 `RETRY`，不得「解析成功但图没建」。
- 通过：18096 有启动脚本 + watchdog + HTTP 探针；非 200/207 回写 `PARSE_FAIL`/`RETRY`。

## Loop 14 · Java 派发切换（P5）

```bash
# 全量/增量/删除 三类事件各发一次，核对 Java 状态表
```
- 反例：`v2-ingest.url` 留空却停 12340 → 链路悬空、文件永远 `PARSE_ING`（P5-3 前必须留 E2E 记录）。
- 通过：`filesParse` 改 POST `/kb/ingest`；删 `generateGraph` 19531 路径；`RemoteV2IngestUtils` 加超时。

## Loop 15 · 两仓配置同步（P5）

```bash
diff <仓库A>/application-r12.yml <仓库B>/application-r12.yml   # 关键键逐项比对
```
- 通过：两仓关键键一致；启动自检打印实际加载地址。

## Loop 16 · 12340 退役（P5，须 G-1）

```bash
ss -tlnp | grep 12340 || echo "已退役"
grep -c '12340' platform/r12/logs/java/rag-index-service/rag-index-service.log
```
- 通过：无 12340 进程/流量、无 `remote.file-parse.*`；三类辅助接口承接有实测（G-1 结论）。

## Loop 17 · kb_9 影子切读（P6）

```bash
curl -s http://127.0.0.1:19200/v2cand_kb_9/_count
```
- 通过：`INGEST_READ_MODE=snapshot` + `INGEST_READ_KBS=[kb_9]` 读 `v2cand` 可查。

## Loop 18 · required_checks + 等价性门禁（P6，须 G-2）

```bash
# 50 条固定 query 做 full vs delta 对照，召回集合/排序漂移分开统计
```
- 反例：未变更内容召回集合低于放行阈值 → DELTA 收窄只用于新增文件，写进 `canary` 策略。
- 通过：A-1~E-3 全过；召回/排序分档统计达标（G-2 阈值）。

## Loop 19 · kb_1004 放量 + E2E（P6）

```bash
# 中英文各 ≥10 条，local/global/Java 三入口；基线 query 不回退
```
- 通过：基线 query（`AAA档`/`5000万`/`T-CORE-001`）召回不低于 baseline；删除后 global 引用不含已删文件。

## Loop 20 · 退役 + 契约登记 + 归档（P7）

```bash
make generate && make check
```
- 通过：契约登记进 `registry.yaml` 且 make check 通过；证据 `DOC2MD-INCREMENTAL-P<n>-loop<m>.md` 含现场命令与真实输出；破坏性操作 Owner 单独授权。

---

**通用纪律**：每个 loop 的证据文件落到 `docs/dispatch/evidence/DOC2MD-INCREMENTAL-P<n>-loop<m>.md`，必须含「现场命令 + 真实输出 + 反例失败证据 + 修复后通过」，不得只写叙述（对齐 `IMPLEMENTATION-QUEUE-V2.md:6-7`）。任一反例未先 FAIL，该 loop 不得标 `DEV_SELF_CHECK_PASS`。
