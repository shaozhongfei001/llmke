# STEP2-H 用 8 份重建决策与前置核实（2026-11-12）

## 决策

Owner 于 2026-11-12 选定：**对可得的 8 份 doc2md fixtures 重生成四件套 + 修复
`current.json` 指针后执行路径 A（图根式切读）**，重建 8 文件，旧图保留 `e2e-v2-ingest`
等 3 份 chunks；**接受 8/11 数据完整性底线**（3 份源文档本机不可得，完整重建不可行）。
授权图根 env 生产变更与动 19531/18096 仍有效。

## 前置核实（执行前只读）

### 19531 身份

- `19531` (pid 46795) = `graph_engine_adapter.legacy_shim:app`（uvicorn），env
  `LLMKE_V2_ROOT=/home/szf/data/dev/llmke-runtime/app/platform/r12/data/graph-root`。
  → **生产图查询适配器（legacy shim）**，读生产 graph-root。
- 停它符合 runbook「隔离写入面」，但会**短暂中断生产 kb_9 查询**（受限窗口可接受）。
- `18096` (pid 46796) = `kb_ingest_service:app`（摄取写入，env GRAPH_API=18094）。
- `18094` (pid 1466203/1464293) = graph API（另一实例，双 worker）。

### 18096 不移除未提交 file_id（切读不削核心保证）——已代码确认

`kb_delta.py` `diff()` 逻辑（325-396 行）：

- **request 模式（无 manifest，逐文件 UPSERT）**：`removed` 只在 `operation=DELETE`
  时填充（355-357 行）；否则**恒空**。注释 9-11、393-394 明确：无 manifest 时退化为
  「单文件 vs `kb_state`」，removed 恒空非 bug 而是数据来源决定。
- 18096 `IngestRequest` 模型含 `file_id` 字段 → 逐文件请求 → 走 request 模式。
- 结论：对 8 份逐文件 UPSERT，`removed` 恒空，**不会移除另外 3 份 file_id**
  → 切读不削成立。
- manifest 模式（有 kb-manifest）才会 `removed = set(active) - set(incoming)`
  （339-340 行），但 18096 走 request 模式，不触发该分支。

### current.json 指针

生产 `kb_9/current.json` 的 `dir` 指向已删 `llmke-r12`（失效）。18096 切到生产 root
后首写会刷新 `current.json.dir` 指向新 snapshot；为稳妥，切读前手动修复 `dir` 指向
现存有效 snapshot（`snapshot-20261107212905-365431-g0`）。

## 待执行（见 todo 2-8）

1. 探索 doc2md 生成四件套方法（CLI/配置/输出目录/artifact_id 映射）。
2. 用 doc2md 对可得 8 份 fixtures 重生成四件套到可控 artifact-store。
3. 修复 `current.json` 指针。
4. 停 19531 + 改 18096 ROOT/ARTIFACT + POST ingest 8 份。
5. 验证：生产 root 图不削（仍 11 文件）+ 查询可读 + 重复请求短路。

## 追加核实：doc2md 解析依赖（2026-11-12 续）

路径 A 用 8 份重建需先由 doc2md 把 fixtures 解析成四件套。探查 doc2md 运行环境：

- doc2md backend（pid 3798）由 root 用裸 `python` 启动（无自有 venv），经 `uv` 管理。
- `/usr/bin/python3`(3.10.12) 解析依赖实测：`markitdown` **可用**（docx/xlsx/pptx 可解析）；
  `magic_pdf`(MinerU PDF 解析器) **导入失败（不可用）**。
- 结论：8 份 fixtures 中 `pdf-digital.pdf`、`pdf-scanned.pdf` 两份 PDF **无法在本机生成四件套**。

叠加 STEP2-G 的 3/11 源缺失 → 「用 8 份重建」实际至多重建 **6 份非 PDF fixtures**
（docx-image/docx-plain/docx-table/R12FIX-credit-ledger.xlsx/R12FIX-product-intro.pptx/R12FIX-product-loan.docx）。
整条链路（doc2md 生成 6 份 → 改 ROOT/ARTIFACT → 停 19531 → POST 6 份 → 验证）操作复杂、
对生产 root 有写入风险；且产出为 6/11 而非 46/11。

`kb_pipeline.commit_snapshot` 已确认：`doc2md_dir` 即 doc2md 产物目录（`store.collect_parts`
收集部件、`store.commit` 复制到 `store_root`），`artifact_id` 由产物内容摘要派生（非源 hash，
规避二次解析冲突），重生成四件套 content_hash 不同只更新 state、不触发 SourceDiverged。

## 纪律留痕

本文件为决策与只读核实记录，未改动任何生产进程或数据。
