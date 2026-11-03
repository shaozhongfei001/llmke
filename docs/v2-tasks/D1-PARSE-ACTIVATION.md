# D1 产品 doc2md 激活方案（2026-11-03 评估）

## 现状（代码事实）

- 产品解析主链仍是 legacy 后缀分支：`services/rag-alg/alg_doc_parse_service/server/loader.py:239-320`
  （`_file_path.suffix` 分支 + PDFParser）。
- doc2md/ParseArtifact 链已以**影子臂**存在于产品解析服务：
  `services/rag-alg/alg_doc_parse_service/server/controller.py:745-791` `_shadow_report()`：
  当 `INGEST_PROJECTION_MODE=shadow` + `INGEST_ARTIFACT_ROOT`（快照仓）+ `INGEST_SHADOW_DIR` 三个
  条件同时满足时，对每次解析任务跑 `ingest_pipeline.ingest`（ParseArtifact 快照 + RAG 投影），
  写对照报告；任何异常吞掉且不影响主链路（`SKIPPED`/`SKIPPED_NO_MODULE` 留痕）。
- 上游实证：`docs/design/unified-documents-v2/EVIDENCE-VL1-REAL-UPSTREAM-20261030.md`（docx/xlsx 三件套
  text-only、metadata 无 content_uid、快照逐字节一致）。

## 激活路径（影子 → 主链，条件化切换）

1. **对齐窗口**：在隔离库开启 shadow，跑真实四格式样本集，收集 `shadow_*.json` 对照报告；
   验收：每格式 `projected` 计数 > 0、`diff` 可解释、`SKIPPED` 为 0（环境类跳过除外）。
2. **主链切换**：新增 `INGEST_PROJECTION_MODE=primary` 分支——parse_task 用 ingest 产物作为索引输入
   （与 RAG 投影同源），保留 `legacy` 为回退值；先灰度单 KB。
3. **同源绑定**：建图与 RAG 使用同一 ParseArtifact 哈希（`ingest` 的 artifact_id 传入
   `BuildRequest.artifact`，artifact_binding 已校验）。
4. **回滚**：`INGEST_PROJECTION_MODE=legacy` 一键回退；快照仓不变，无数据迁移。

## 验收（D1）

- 四格式真实文件走 primary 后：正文/表格/图片与 legacy 对照无回退；
- 建图请求携带同一 artifact_id/hash（S1B 校验通过）；
- 任一格式失败自动回 legacy 且留痕（不静默）。

## 未做（如实）

- shadow 对齐窗口尚未开跑（需解析服务运行 + 样本集）；primary 分支未实现。
