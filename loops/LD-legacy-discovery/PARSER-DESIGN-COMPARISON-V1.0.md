# PDF / DOCX / OCR 设计对比与引用建议 V1.0

- 日期：2026-10-21
- 对比对象：
  - **A 方案 = doc2md**（独立项目，工作区外路径不入库；specs 000–016 + 22 个测试文件）
  - **B 方案 = deepdoc**（生产快照 `alg_doc_parse_service` 的 `deepdoc/`，CODE-01）
- 用途：为 LLMKE S1 决定「PDF / DOCX / OCR 引用哪一套设计」
- 性质：**技术对比与建议**，不含代码改动；不构成复用批准（`decision` 仍为 null）

## 0. 结论（先看这三行）

| 主题 | 建议引用 | 形态 |
|---|---|---|
| **PDF** | **doc2md** | 独立组件（命令行 + 文件产物契约），不复制代码 |
| **OCR / 图片** | **doc2md** | 同上（它已有独立的图片流水线） |
| **DOCX** | **不作为解析内核引用**（见 §1.1 实测修正） | 建议先用 deepdoc 适配，同时向 doc2md 提"DOCX 结构化"需求 |

一句话：**PDF 与 OCR 引用 doc2md 并保持其独立；DOCX 暂不引用 doc2md**——
因为实测其 DOCX 路径只产出段落级文本（`table_count=0`、`figure_count=0`），表格与图片全部丢失。

### 1.1 实测修正（2026-10-21，见 `PARSER-CONTRACT-PROBE-V1.0.md`）

先前的判断有一处错误，以实测为准：

- ❌ 我曾写「markitdown 路径的表格会变成 IR 的 TableCell」。
- ✅ 实测：`build_from_markitdown_text` 的 docstring 与行为都是「降级路径：无 bbox / 无页码 / **无表格结构**」；
  含管道表格与图片引用的 markdown 装配后得到 **4 个 paragraph 块、`table_count=0`、`figure_count=0`**，
  管道表格被当成普通段落文本。`_PipeTableParser` 只服务于 MinerU 那条路径。

## 1. 事实基础（以免结论悬空）

已读（只读）：
- doc2md：`app/core/parser_routing.py`(265)、`app/core/pdf_sniffing.py`(335)、
  `app/services/mineru_pdf_parser.py`(1019)、`app/services/image_parser.py`(1196)、
  `app/services/markitdown_parser.py`(603)、`app/services/document_ir_builder.py`、
  `app/services/document_ir_schema.py`、`app/cli/main.py` 命令表、`specs/000–016` 目录
- deepdoc：`pdf_parser.py`、`image_parser.py`、`docx_parser.py`、`output_object/*`、
  `splitter/*`（此前已做解耦回放，5/5 一致）

**未做**：真实文档的**输出质量基准**（没有标注真值集，也没有跑同一批 PDF 做人工比对）。
因此下表比的是**设计**，不是"谁解析得更准"。

## 2. 六个维度逐项对比

| # | 维度 | doc2md | deepdoc | 判定 |
|---|---|---|---|---|
| 1 | **PDF 分流（数字版 vs 扫描版）** | 有独立嗅探层：6 个状态（有文本层/无文本层/加密/空文档/嗅探失败/依赖缺失）；阈值由 Owner 冻结（100 字符、页均 20、抽样 20 页）；**只有 `TEXT_LAYER_PRESENT` 才允许判数字版**，import 期 3 条断言强制该不变式 | 无显式分流：PDF 解析器构造时即加载 OCR 模型，由 magic_pdf/自研 OCR 内部决定 | **doc2md 明显更好** |
| 2 | **PDF 执行隔离** | `mineru_pdf_parser` 用 **subprocess** 调 magic_pdf CLI；进程内不加载模型；有超时与输出尾部截断 | 进程内直接 import magic_pdf + onnxruntime；实测 `import deepdoc.parser` 即 `ModuleNotFoundError`（缺阿里云 SDK） | **doc2md 明显更好** |
| 3 | **OCR / 图片** | 纯函数真值表（auto / paddleocr / vlm）；低质量图走 VLM；**质量评分作用在源图**（实测 binarize 会把模糊图 Laplacian 从 0.58 拉到 2758，若对预处理产物评分会误判清晰）；依赖缺失 → `DEPENDENCY_MISSING`；mock 引擎 → `UNSUPPORTED_WITH_HINT` 且**零落盘** | 构造期 `load_local_ocr()['ocr']` 直接加载 ONNX 模型；无质量路由、无"依赖缺失"状态、无 mock 诚实性约束 | **doc2md 明显更好** |
| 4 | **结构化输出** | `Document IR`：块类型闭集、`BBox`、`page_no`、`ContentRef{start_offset,end_offset,table_id,figure_id,asset_path}`、`CoordinateSystem{unit,origin,page_ref}`；两条映射路径；**缺 bbox 记 `stats.blocks_without_bbox`，禁止估算填充**；markitdown 路径**不编造页数** | `ParsedText/ParsedTable/ParsedImage`；offset 字段存在但 **DOCX 路径不填**（`parse_text_document` 只填 source）；表格有 cells + HTML + 跨页标志，但**合并单元格处理是注释掉的 TODO** | **doc2md 更好**（doc2md 的 span 与"不编造"规则更贴 LLMKE 合同） |
| 5 | **依赖与可测试性** | 惰性 import + 依赖探测；22 个测试文件、按 spec 编号组织；服务构造函数留测试缝（不装 paddleocr / 不连 MySQL 也能驱动全链路） | 导入期硬依赖（阿里云 SDK / magic_pdf / onnxruntime / tika）；**0 测试** | **doc2md 明显更好** |
| 6 | **可运维性** | 嗅探缓存三重校验（`cache_type`/`sha256`/`sniffer_version`），**环境态与瞬时态不入缓存**（避免"没装 pypdf"被固化成权威判定）；有 quality checker、evidence chain、parse manifest | 无缓存、无版本化、无质量报告；产物直接交给上层写库 | **doc2md 明显更好** |

补充：doc2md 的 CLI 已把能力拆成可单独调用的命令
（`route-parsers` / `parse-mineru-pdf` / `parse-markitdown` / `parse-images` /
`check-parse-quality` / `build-evidence-chain`），产物是
`parsed_text.md + parsed_metadata.json + parse_manifest.json（+ document_ir.json）` 三/四件套。
**这就是"独立组件"的天然形态。**

## 3. 两边的真实优势（不吹一方）

doc2md 的强项在设计约束：
- fail-closed 路由（宁可判"扫描版"也不误判"数字版"）
- 不做假：缺 bbox 就记 `None` 并计数，不估算；缺 page 就不编
- 依赖缺失/引擎 mock 一律显式失败，不静默降级
- 版本化（`sniffer_version`、`PARSER_ADAPTER_VERSION`）让缓存与产物可追溯

deepdoc 的唯一实质优势：
- **DOCX 原生解析能拿到图片 base64 与表格 HTML**（实测 doc2md 的 markitdown→IR 路径
  `table_count=0`、`figure_count=0`，表格退化成段落文本，图片不作为资产输出）；
- 表格单元格带 `is_merged/merged_positions` 字段（虽然合并识别本身是未完成 TODO）。

也就是说：**deepdoc 在 DOCX 上"多一个图片内联能力"，代价是导入期硬依赖 + 无测试 + 无 IR + 合并单元格未完成。**

## 4. 决策建议

### 4.1 分领域决策：PDF/OCR 引用 doc2md，DOCX 暂不引用

理由：
1. PDF 与 OCR 的六维对比中 doc2md 全面领先（嗅探 fail-closed、子进程隔离、依赖缺失显式、真值表无静默成功），
   且实测（`PARSER-CONTRACT-PROBE-V1.0.md`）三种 PDF 的分流结果与理由完全符合预期。
2. **DOCX 是例外**：实测其 markitdown→IR 路径 `table_count=0`、`figure_count=0`，表格与图片丢失。
   LLMKE 的对账场景必须有表格结构，因此 DOCX 不能走这条路。
3. LLMKE 自己的红线（不静默降级、不做假、类型化证据、可复跑）与 doc2md 的设计约束高度同构；
   deepdoc 恰好在这几点上都需要我们额外加约束（这正是 S1 回放里暴露的 3 条硬条件）。
4. doc2md 的产物是**文件契约**，天然支持"独立组件"：LLMKE 不改它的代码，只按 CLI + 产物格式消费。

### 4.1.1 DOCX 的三个可选处置

| 选项 | 内容 | 代价 |
|---|---|---|
| D1 | deepdoc 原生解析（表格 cells + HTML + 图片 base64） | 需满足 S1 的 3 条硬条件；合并单元格仍是 TODO |
| D2 | 在 doc2md 侧补 DOCX 结构化（复用其 IR schema 与 015 图片流水线） | 需其维护方排期，LLMKE 不能自行改 |
| D3 | 分治：PDF/OCR 用 doc2md，DOCX 用 deepdoc | 两套解析栈、两套产物契约 |

**TL 倾向**：先按 **D3** 落地（可立即开工、风险最低），同时提 **D2** 需求；
doc2md 支持 DOCX 表格后再收敛为一套。

### 4.2 "独立组件"的边界（建议，不写代码）

| 项 | 建议 |
|---|---|
| 调用方式 | 子进程调用 doc2md 的 CLI 命令（每文件一条），不 import 其 Python 模块 |
| 输入契约 | 文件绝对路径 + `sha256` + 处理选项（引擎选择、是否 dry-run） |
| 输出契约 | `parsed_text.md`、`parsed_metadata.json`、`parse_manifest.json`、`document_ir.json` |
| 状态契约 | 复用其闭集决策（`ROUTE/UNKNOWN/UNSUPPORTED`、`PARSED/SKIPPED/DEPENDENCY_MISSING/UNSUPPORTED_WITH_HINT`）；LLMKE 侧**必须**把这些状态原样透传到 `degraded/coverage`，不得折叠成"成功" |
| 版本契约 | 记录 `sniffer_version` + `PARSER_ADAPTER_VERSION` + `schema_version=document-ir/1.0`，写进 LLMKE 的 manifest |
| 失败处理 | `DEPENDENCY_MISSING` / `UNSUPPORTED_WITH_HINT` / `SKIPPED` 一律算"未解析"，不允许上游当成功入库 |
| 边界红线 | doc2md 只读源文件；LLMKE 只读取其产物目录，不写它的 vault/parsed（或约定独立输出目录） |

### 4.3 deepdoc 的处置

- **不作为解析内核引用**；
- 保留为**对照基线**：我们已有可跑通的 docx/txt/html 回放脚本（`spike/`），
  可用于"新旧解析结果比对"。若将来 doc2md 的 DOCX 输出被质疑覆盖不足，
  用这份基线做差异举证。
- 12 项资产台账里 CODE-01 的 `decision` 建议改为 **ADAPT（只保留对照用途）** 或 **RETIRE**，
  但这两者都需要 owner 批准，本文件只是建议。

## 5. 前提与风险（采纳前必须知道）

1. **未做质量基准**：本对比不证明 doc2md 解析结果更准。若客户要"解析准确率"证据，
   需要一批带标注的真值文档做盲测——这属于 M0 题库范畴，目前没有。
2. **doc2md 是独立项目**（有其自己的团队与 spec 流程）：引用它意味着 LLMKE 依赖一个外部组件的演进节奏，
   需要约定**版本冻结点**（例如锁定某个 commit 作为 LLMKE 的解析基线）。
3. **依赖仍在**：magic_pdf、paddleocr 仍是重依赖；doc2md 只是把它们关到"惰性 + 子进程"里，不是消除。
   部署时仍需确认模型文件与许可（`paddleocr`、`magic_pdf` 的商用许可要单独核）。
4. **DOCX 结构化缺口（已实测确认，不再是"可能"）**：markitdown→IR 路径 `table_count=0`、`figure_count=0`，
   表格与图片都不作为结构化资产产出。若业务要求 DOCX 表格/图片保留（LLMKE 证据合同需要 `asset_path`），
   doc2md 当前不满足，需其维护方补（复用 015 流水线）。**这是不引用 doc2md 做 DOCX 的决定性理由。**
5. **坐标系**：doc2md IR 的 `CoordinateSystem` 默认 `unit/origin/page_ref` 由上游给定；
   LLMKE 合同要求 offset 为 Unicode 码点左闭右开——`ContentRef.start_offset/end_offset` 是 Python 字符下标，
   语义吻合，但**仍需一次真实样本的逐字符核对**才算证明。

## 6. 若采纳，建议的最小动作（不写代码）

1. 业务确认 §5.4（DOCX 内嵌图片是否必须作为独立资产）。
2. 约定 doc2md 的**冻结版本**（commit + 版本号）。
3. 用同一批样本（3 份 PDF：数字版/扫描版/加密；3 份 DOCX：含表格/含图片/纯文本）各跑一遍 doc2md，
   记录其状态输出与产物，**作为接口契约的实测依据**（不是质量基准）。
4. 把上述结果回写 `S1-CODE-01-03-11-REUSE-EXTRACT-V1.0.md` 的判定与 `SOURCE-ASSETS.yaml` 的决策建议（待 owner 批准）。
