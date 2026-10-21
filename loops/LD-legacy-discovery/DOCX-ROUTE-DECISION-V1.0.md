# DOCX 解析路线决策 V1.0

- 日期：2026-10-21
- 决策人：Tech Lead（业主授权按建议执行）
- 依据：`PARSER-DESIGN-COMPARISON-V1.0.md`、`PARSER-CONTRACT-PROBE-V1.0.md`（实测）
- 性质：技术选型决策，**不构成复用批准**（`SOURCE-ASSETS.yaml` 的 `decision` 仍为 null）

## 1. 决策

**采用 D3 分治**：

| 文档类型 | 解析实现 | 形态 |
|---|---|---|
| PDF | **doc2md**（嗅探 + MinerU 适配） | 独立组件（子进程 CLI + 文件产物） |
| 图片 / OCR | **doc2md**（015 图片流水线） | 同上 |
| **DOCX** | **deepdoc**（`alg_doc_parse_service` 的 docx 解析内核） | 进程内适配器（满足 3 条硬条件后） |

**并且必须满足一个前置架构条件**（否则分治会变成灾难）：
> LLMKE 侧定义**统一的内部 IR**（块类型、offset、bbox、资产引用），
> 两个适配器各自把产物映射到它。下游只认内部 IR，不认"这文档是哪个解析器来的"。

## 2. 为什么 DOCX 不用 doc2md（实测证据）

| 事实 | 数据 |
|---|---|
| doc2md 的 DOCX 走 markitdown → `build_from_markitdown_text` | 该函数 docstring 明写「降级路径：无 bbox / 无页码 / **无表格结构**」 |
| 含管道表格 + 图片引用的 markdown 装配后 | `block_count=4`、**`table_count=0`**、**`figure_count=0`**，4 块全是 `paragraph`，表格退化为段落文本 |
| 依赖状态 | 其环境未安装 markitdown，`convert()` 抛 `PARSER_IMPORT_ERROR`（行为正确，但当前不可用） |

LLMKE 的对账场景必须有表格结构（多指标 × 数据源 × 口径），图片要能被引用到原文。
**doc2md 的 DOCX 路径在这两点上不满足，且不是配置问题，是路径设计使然。**

## 3. 为什么 PDF / OCR 用 doc2md（实测证据）

| 维度 | 实测结果 |
|---|---|
| 数字版 PDF | `TEXT_LAYER_PRESENT`（677 字符，1/1 页）→ `PDF_DIGITAL` / `pdf_sniff_digital` |
| 扫描版 PDF | `TEXT_LAYER_ABSENT`（0 字符）→ `PDF_SCANNED_OR_IMAGE` / `pdf_sniff_scanned` |
| 加密 PDF | `ENCRYPTED` → 判扫描链路，理由原文「no password attempt」（不试口令） |
| 分流不变式 | 只有 `TEXT_LAYER_PRESENT` 才允许判数字版（import 期 3 条断言强制） |
| OCR 引擎路由 | 48 种输入组合 → 5 种结果，**无一种静默成功**（要么真解析并报实际引擎，要么带 `skip_reason`） |
| 依赖缺失 | `DEPENDENCY_MISSING` / `PARSER_IMPORT_ERROR`，显式失败不降级 |

deepdoc 的 PDF/OCR 恰好相反：进程内加载 ONNX 模型、无分流决策、无依赖缺失状态、无测试。

## 4. 为什么不用 D1（全部 deepdoc）或 D2（全部 doc2md）

- **D1（全 deepdoc）**：会丢掉 PDF 的 fail-closed 分流与 OCR 的真值表约束；这两项直接对应 LLMKE 的
  「不静默降级」红线，不能为了"栈统一"而放弃。
- **D2（全 doc2md）**：需要 doc2md 维护方给 DOCX 补表格/图片结构化，排期不由我们控制；
  且它当前环境连 markitdown 都没装，短期不可用。

**D3 是唯一能立即开工、又不牺牲红线的路径。** 代价是两套栈，用 §1 的统一内部 IR 消化。

## 5. deepdoc DOCX 适配器必须满足的 3 条硬条件（来自 S1 回放实测）

| # | 条件 | 依据 |
|---|---|---|
| 1 | 惰性化 `parser/__init__` 与 `image_parser` 的重依赖导入 | 原包 `import deepdoc.parser` 直接 `ModuleNotFoundError`（缺阿里云 SDK） |
| 2 | OCR 从**构造期**改为**调用期** | `image_parser.py:21` 构造即 `load_local_ocr()['ocr']`，无模型则纯文本 docx 都起不来 |
| 3 | 4 类服务耦合换成端口（25 处 import / 14 文件） | 已验证改写后 5/5 样本解析结果逐字段一致 |
| 4 | 随包携带非代码资源 | `vision/ocr.res`、`splitter/*.pkl`、`xg_splitter.json`；`huqie.txt` 源码本就缺失（降级为默认词典，需显式记录） |

另需明示：deepdoc 的 **DOCX 段落不产出 offset**（`parse_text_document` 只填 source），
表格合并单元格识别是**注释掉的 TODO**。因此 DOCX 的 offset 必须由 LLMKE 侧在切分阶段重新计算并绑定
`text_hash`，不得假装来自解析器。

## 6. 验收标准（本决策落地的判定）

1. 统一内部 IR 的 schema 先落合同（`contracts/schema/`），两个适配器都映射到它；
2. DOCX 适配器在无 ONNX 模型的环境下能解析纯文本 docx（条件 2 生效）；
3. DOCX 表格产出 `table_cells`（含行列位置），图片产出 `asset_path`；
4. PDF/OCR 走 doc2md 时，`DEPENDENCY_MISSING` / `SKIPPED` / `UNSUPPORTED` **原样透传**到 degraded/coverage，
   不得折叠为成功；
5. 同一份 DOCX 用 deepdoc 适配器解析两次，结果一致（可复跑）。

## 7. 未解决 / 遗留

| 项 | 说明 |
|---|---|
| doc2md 的 DOCX 能力 | 已向业主/维护方登记为需求（D2），若其支持表格后可再评估收敛 |
| deepdoc 合并单元格 | TODO，短期按"不合并"处理，并在 IR 里标注 `merge_detected=false` |
| 解析准确率 | 仍无标注真值集（M0 范畴），本决策只解决"用哪套"，不解决"解析得多准" |
| doc2md 环境未装 markitdown | 与本决策无关（DOCX 不走它），但影响其自身 DOCX 能力的可用性 |
