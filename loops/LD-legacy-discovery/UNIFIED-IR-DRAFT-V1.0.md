# 统一内部 IR 设计草案 V1.0（llmke-ir/1.0）

- 日期：2026-10-21
- 状态：**草案（未注册为合同）**。正式注册需走 `contracts/` + `registry.yaml` + `make generate/check`，
  且会改变源码快照——按既定纪律，**留待批次窗口一次性处理**（见 §8）。
- 依据：`DOCX-ROUTE-DECISION-V1.0.md`（D3 分治）、`PARSER-CONTRACT-PROBE-V1.0.md`（doc2md 实测）
- 目的：让 doc2md（PDF/OCR）与 deepdoc（DOCX）两个适配器输出**同一种结构**，
  下游（切分、索引、召回、引用）不关心"这份文档是哪个解析器来的"。

## 1. 决策：LLMKE 自有 IR，字段对齐 doc2md，不自造轮子

| 选项 | 取舍 |
|---|---|
| A 直接采用 doc2md 的 `document-ir/1.0` 作为 LLMKE 合同 | 省事，但它是**别人的组件契约**，我们无权扩展；且缺 `text_hash` 绑定，不满足 LLMKE 的引用合同 |
| **B（采纳）LLMKE 定义 `llmke-ir/1.0`，与 doc2md 的字段**无损对齐**，只增加必要增量** | doc2md 无需改一行代码；LLMKE 拿到自己需要的约束 |

**对齐**：块类型闭集、`content_ref`、`bbox`、`coordinate_system` 直接沿用 doc2md 的取值集合，
保证 `doc2md document_ir.json → llmke-ir` 是**字段级可逆映射**（便于对照与回归）。

## 2. 文档级字段

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `schema_version` | string | ✓ | 固定 `llmke-ir/1.0` |
| `doc_id` | string | ✓ | 内容标识（与 `sha256` 同源） |
| `sha256` | string(64) | ✓ | 源文件内容哈希 |
| `source_uri` | string | ✓ | 逻辑来源（**不得写宿主绝对路径**） |
| `parse_engine` | enum | ✓ | `doc2md` / `deepdoc_docx`（哪个适配器产出） |
| `engine_version` | string | ✓ | 适配器版本（doc2md 记 `PARSER_ADAPTER_VERSION`） |
| `parser_profile` | string | ✓ | 解析档位（doc2md 的 `PARSER_PROFILE_*`；deepdoc 记 `docx_naive`） |
| `sniffer_version` | string \| null | — | doc2md 独有；deepdoc 为 null |
| `parse_status` | enum | ✓ | `PASSED` / `PARTIAL` / `DEPENDENCY_MISSING` / `UNSUPPORTED` / `SKIPPED` |
| `status_reasons` | string[] | ✓ | 状态原因（doc2md 的 `skip_reason` / `detail` 原文透传） |
| `page_count` | int \| null | ✓ | **未知就 null，禁止编造**（DOCX 路径恒为 null） |
| `coordinate_system` | object | ✓ | `{unit, origin, page_ref}`；`unit ∈ {pdf_point, pixel, none}` |
| `text_hash` | string(64) | ✓ | **全文**文本哈希（用于 offset 校验与引用绑定） |
| `blocks` | Block[] | ✓ | 见 §3 |
| `tables` | Table[] | ✓ | 无表格时为空数组（不省略字段） |
| `assets` | Asset[] | ✓ | 图片等二进制资产 |
| `stats` | object | ✓ | `block_count / table_count / asset_count / blocks_without_bbox / blocks_low_confidence` |
| `provenance` | object | ✓ | 生成时间、适配器、上游文件哈希等 |

### 相对 doc2md 的 5 个增量（这是 LLMKE 不能被替代的部分）

1. **`text_hash`**：全文哈希，跨解析器可复算；引用必须同时带 `start_offset/end_offset + text_hash`；
2. **`parse_status` + `status_reasons`**：doc2md 的 `DEPENDENCY_MISSING / UNSUPPORTED_WITH_HINT / SKIPPED`
   **原样**变成文档级状态，下游必须据此标 `degraded/coverage`，**不得折叠成"成功"**；
3. **`coordinate_system.unit` 增加 `none`**：DOCX 没有页面坐标，必须显式声明"没有"，而不是给个假的 `pixel`；
4. **`assets[].sha256`**：doc2md 给 `asset_path`，deepdoc 给 base64；统一要求**落成资产文件 + 内容哈希**，
   禁止把 base64 内联进 IR（否则 IR 体积失控且无法去重）；
5. **`tables[].cells[].merge_detected`**：deepdoc 的合并单元格识别是未完成 TODO，
   必须显式标注"未识别合并"，不得让下游误以为行列天然对齐。

## 3. Block 字段

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `block_id` | string | ✓ | 文档内唯一 |
| `type` | enum | ✓ | 与 doc2md 闭集一致：`heading/paragraph/table/figure/formula/caption/header/footer`；未知类型归并为 `paragraph` 并在 `attrs.raw_type` 保留原值 |
| `page_no` | int \| null | ✓ | 未知为 null |
| `bbox` | number[4] \| null | ✓ | `[x0,y0,x1,y1]`；未知为 null 并计入 `blocks_without_bbox`，**禁止估算填充** |
| `reading_order` | int | ✓ | 阅读顺序 |
| `confidence` | number \| null | ✓ | 置信度（无则 null） |
| `content_ref` | object | ✓ | 见 §5 |
| `attrs` | object | ✓ | 解析器特有属性（如 `raw_type`、`title_level`） |

## 4. Table / Asset

**Table**：`table_id`、`block_id`（所属块）、`caption`（可空）、`n_rows`、`n_cols`、
`cells[]{row, col, row_span, col_span, text, is_header, merge_detected}`、`html`（可空）。

**Asset**：`asset_id`、`kind`（`image` / `chart`）、`asset_path`（相对资产目录）、`sha256`、`ext`、
`page_no`（可空）、`bbox`（可空）、`ocr_text`（可空，OCR 结果）、`linked_block_id`（图文关联，可空）。

## 5. content_ref（引用定位）

沿用 doc2md 的 kind 闭集，但 `text_span` 必须带 `text_hash`：

| kind | 必需键 |
|---|---|
| `text_span` | `text`, `source`, `start_offset`, `end_offset`, **`text_hash`** |
| `inline_text` | `text` |
| `table_ref` | `table_id` |
| `figure_ref` | `figure_id` |
| `asset_ref` | `asset_id` |

**offset 语义（合同硬约束）**：Unicode **码点**、左闭右开；与 `text_hash`、`parser_version` 一起绑定；
跨字段与真实解析都要测。

## 6. 两个适配器的映射

### 6.1 doc2md → llmke-ir（PDF / OCR）

| doc2md | llmke-ir | 备注 |
|---|---|---|
| `content_uid` / `sha256` | `doc_id` / `sha256` | 直接取 |
| `blocks[].type` | `type` | 闭集一致，无需翻译 |
| `blocks[].bbox` / `page_no` | 同名 | doc2md 已知"缺就不填"，与我们的规则一致 |
| `blocks[].content_ref.start_offset/end_offset` | 同名 | **必须补 `text_hash`**（用 `text_hash(全文)`） |
| `tables[]` / `figures[]` | `tables[]` / `assets[]` | `figure_id → asset_id` |
| `provenance.parser_adapter_version` | `engine_version` | |
| `document_ir.json` 缺失（read_bridge 记为可选） | `parse_status=PARTIAL` + reason | **不得当成功** |
| `DEPENDENCY_MISSING` / `UNSUPPORTED_WITH_HINT` / `SKIPPED` | `parse_status` 同名映射 | 原样透传 |

### 6.2 deepdoc（DOCX）→ llmke-ir

| deepdoc | llmke-ir | 备注 |
|---|---|---|
| `ParsedText.page_content` | `blocks[].content_ref.text` | |
| `ParsedTextMetadata`（source/file_path） | `source_uri` | 只取逻辑标识，**不得写宿主绝对路径** |
| `offset`（当前 DOCX 路径**不填**） | 由 LLMKE 在切分阶段重算并绑 `text_hash` | **不得假装来自解析器** |
| `ParsedTable.table_cells[]{value, position:(row,col), is_merged, merged_positions, is_header}` | `tables[].cells[]`，`merge_detected=false`（因为识别未完成） | |
| `ParsedTableMetadata.table_html_content` | `tables[].html` | |
| `ParsedImage.base64` | 落成 `assets/` 文件 + `sha256` + `asset_path` | 禁止内联进 IR |
| `page_no`（DOCX 无页概念） | `null` + `coordinate_system.unit="none"` | 显式声明"没有" |
| 解析进度/上报 | 丢弃（`ProgressPort` 为空实现） | |

## 7. 不变量（可测）

| # | 不变量 | 违反即 FAIL |
|---|---|---|
| I-1 | `page_count` 与 `page_no` 不得凭空出现（DOCX 恒 null） | 编造页码 |
| I-2 | `bbox` 缺失必须 null + 计入 `blocks_without_bbox` | 估算填充 |
| I-3 | `text_span` 的 `start_offset/end_offset` 必须是码点、左闭右开，且与 `text_hash` 同快照 | 用字节或 UTF-16 计数 |
| I-4 | `parse_status ≠ PASSED` 时，下游必须据此标 `degraded` | 静默当成功 |
| I-5 | `assets[]` 每项必须有 `sha256`，且文件真实存在 | 引用断链 |
| I-6 | 未知 `block.type` 归并 `paragraph` 且保留 `attrs.raw_type` | 丢信息或报错崩溃 |

## 8. 注册计划（待批次窗口）

**现在不做**，原因：`contracts/**` 属冻结控制面，改动会同时改变源码快照与 `baseline_sha256`，
使 `LD-legacy-discovery-r2` 已签的 QA 立即失效（其状态 DONE 无法重跑）。

批次窗口内的一次性动作：

1. 新增 `contracts/schema/llmke-unified-ir.json`（`llmke-ir/1.0`）；
2. `contracts/registry.yaml` 登记（含 `generator` 与 `outputs`），`make generate` 产出快照；
3. `make check`（结构/分层/哈希联动）；
4. `TRACE.yaml` 增补追溯记录；
5. 与其它待办批次合并后**统一重冻结**，再统一重跑门禁与重签 QA。

## 9. 本草案明确不做

- 不修改 doc2md 任何代码或 schema（它是独立组件，我们只映射）；
- 不把 doc2md 的 `document-ir/1.0` 直接当成 LLMKE 合同；
- 不在草案阶段改 `contracts/`、不改 `generated/`；
- 不解决"解析准确率"（那是 M0 题库范畴）。
