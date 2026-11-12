# STEP2-G 生产四件套缺失核对（2026-11-12）

## 背景

Owner 于 2026-11-12 授权图根 env 生产变更（T-D2MD-17 阻塞④解锁），按 STEP2-F 路径 A
（图根式切读）推进。本文件记录路径 A 执行前的最终核对发现，定位到比「artifact-store
缺失」更根本的阻塞。

## 核对方法与真值

- `ps` 实测 18096（pid 46796）/ 19531（pid 46795）均运行（自 11-09 起）。
- 18096 当前 env：`LLMKE_V2_GRAPH_ROOT=shadow/graph-root`、
  `LLMKE_ARTIFACT_STORE=shadow/artifact-store`、
  `LLMKE_KB_STATE=shadow/kb-state/kb_state.json`、`GRAPH_API=18094`、`ES=19527`、`MILVUS=19526`、
  `DOC2MD_CONFIG=doc2md/config/app.yaml`、`DOC2MD_LOCK=coordination/doc2md.lock`。
- 生产 `kb_9/current.json`（`llmke-runtime/app/platform/r12/data/graph-root/kb_9/current.json`）：
  `documents=46`，`per_file` 列出 11 个 file_id（290/329/330/331/332/333/334/343/999016/999019/999020），
  `dir` 指向 `/home/szf/data/dev/llmke-r12/platform/r12/data/graph-root/kb_9/snapshot-20261107212905-365431-g0`。
- `ls /home/szf/data/dev/llmke-r12` → **不存在**（readlink 失败）→ `current.json` 的 `dir` 是**失效指针**。
- 生产 app 根同级 `llmke-runtime/app/platform/r12/data/` 仅有 `graph-root`，**无 artifact-store**。
- 全局搜 `999016`：
  - 所有 `document_ir.json`：**0 匹配**。
  - `llmke-runtime` 全文件：31 命中，均为 `community.json`/`sources.json`/`current.json`/`config/`
    （图数据与配置）及 venvs 内 scipy 测试噪声——**无任何 artifact 四件套目录**命中。
  - `doc2md` 全文件：**0 匹配**。
- 生产 `graph-root` 存在**三副本**（均含 46/11 图）：
  1. `llmke-runtime/app/platform/r12/data/graph-root/kb_9/`（runbook 称「生产 app 根」）
  2. `llmke-runtime/data/graph-root/kb_9/`
  3. `llmke-runtime/legacy-r12/platform/r12/data/graph-root/kb_9/`
- 代码 `kb_ingest_service.py`：
  - 请求体含 `doc2md_dir`（直接指向四件套目录）；`KbDeltaService(_store_root(), ...)`
    从 `_store_root()` + `doc2md_dir` 读四件套。
  - `to_service_request()` 仅做 `model_dump` + operation 字符串化；`service.run` 硬依赖四件套存在。

## 结论

1. **路径 A 的「重建 46/11」硬依赖生产 11 份标准四件套，而四件套本机不可得**
   （随 `llmke-r12` 删除，未迁移到 `llmke-runtime`；doc2md 产物区亦无对应 11 份）。
   即使新建 `artifact-store` 也无四件套可填，`POST /kb/ingest` 会命中
   `DOC2MD_ARTIFACT_INCOMPLETE` / `ARTIFACT_MANIFEST_MISSING`（400，**失败前不写图**，不削）。
2. **`current.json` 指针失效**：`dir` 指向已删 `llmke-r12`，即便仅改 ROOT 做查询验证，
   18096/18094 按指针定位 snapshot 也会失败，需先修复指针到实际有效副本路径。
3. 生产 `graph-root` 三副本并存，需先确认 18094（GRAPH_API）实际读取哪一个，
   切读才有明确落点。

## 待 Owner 决策

- 选项 A：从 doc2md 重新生成 11 份标准四件套（需先确认 file_id 290/…/999020 对应的
  原始文档来源是否在本机；目前未知），补齐后再执行路径 A。
- 选项 B：放弃「重建」，仅验证「18096 改 ROOT 指向有效副本 + 修复 current.json 指针后
  查询可读 / 重复请求短路」，不动四件套、不重建。
- 选项 C：仅将授权与缺口登记入台账，不立即动生产；待补齐四件套后另约窗口。

## 进一步核对：源文档可得性（2026-11-12 续）

从生产 snapshot `sources.json` 提取 11 个 file_id 的 title 映射，确认这 11 份文档实为
doc2md 的 QA/解析 fixtures（非业务文档）：

- 可得（8 份）：`docx-image.docx`、`docx-plain.docx`、`docx-table.docx`、`pdf-digital.pdf`、
  `pdf-scanned.pdf`、`R12FIX-credit-ledger.xlsx`、`R12FIX-product-intro.pptx`、
  `R12FIX-product-loan.docx`（位于 `llmke-runtime/app/platform/r12/qa/fixtures` 与
  `parse/fixtures/generated`）。
- **缺失（3 份，本机全局不可得）**：`e2e-v2-ingest.docx`（独立文档）、
  `R12FIX-product-loan(1).docx`、`R12FIX-product-intro(1).pptx`（两副本）。
- `legacy-r12` 仅含 `graph-root` 副本，**无 artifact-store**，无法作为完整四件套来源。

结论：完整「重建 46/11」不可行（缺 3 份源，其中 `e2e-v2-ingest.docx` 为独立文档，
其 chunks 无法从四件套恢复）。`290` 与 `999016` 同为 `R12FIX-product-loan` 两副本（chunks
完全重叠），缺 `(1)` 副本不影响内容覆盖；`e2e-v2-ingest.docx` 缺失则为真正内容缺口。

## 纪律留痕

本核对为只读操作（ps / ls / grep / 读代码），未启动/停止任何生产进程，未改动任何文件。
