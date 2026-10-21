# doc2md 接口契约实测记录 V1.0

- 日期：2026-10-21
- 目的：把 `PARSER-DESIGN-COMPARISON-V1.0.md` 里"建议的契约"落到**实跑证据**上
- 约束：**只读**。不修改 doc2md 仓库、不写其 DB/vault/parsed 目录、不安装/卸载其依赖
- 样本：`/tmp/llmke-probe/doc2md/`（6 份，自建）
- 执行环境：doc2md 自有解释器（CPython 3.11.7）+ `PYTHONPATH=backend`

## 1. 样本

| 文件 | 大小 | 构造方式 | 预期用途 |
|---|---|---|---|
| `pdf-digital.pdf` | 3.5 KB | PyMuPDF 写入真实文本层 | 数字版 |
| `pdf-scanned.pdf` | 6.5 MB | 纯图片页（无文本层） | 扫描版 |
| `pdf-encrypted.pdf` | 4.4 KB | 对数字版做 AES-256 加密（user/owner 双口令） | 加密 |
| `docx-plain.docx` | 36 KB | python-docx：标题 + 2 段 | 纯文本 |
| `docx-table.docx` | 36 KB | python-docx：标题 + 3×3 表格 | 含表格 |
| `docx-image.docx` | 50 KB | python-docx：标题 + 内嵌 PNG | 含图片 |

## 2. 实测①：路由决策（纯函数，零副作用）

调用 `match_route_type(file_ext=*, mime_type=None)`；生效规则版本 `004_mvp_v2`。

| 样本 | 嗅探前 route_type | rule_name | 解析器族提示 |
|---|---|---|---|
| 3 份 `.docx` | `DOCX` | `ext_docx` | `MARKITDOWN_FAMILY` |
| 3 份 `.pdf` | `PDF_DIGITAL` | `ext_pdf_digital` | `MINERU_FAMILY` |

**契约要点**：`route_type` 在嗅探前对**所有 PDF 一律返回 `PDF_DIGITAL`**，
扫描版必须在嗅探之后才会被改判。⇒ 调用方**不能只看 route_type 就决定走哪条链**，必须走嗅探后的结果。

## 3. 实测②：PDF 嗅探（真实文件，只读打开）

配置来自 `config/pdf_sniffing.yaml`（实测生效值）：`pages_max=20`、
`digital_min_total_chars=100`、`digital_min_avg_chars_per_page=20`、`cache_enabled=True`，
`sniffer_version=pdf_sniff_v1`。

| 样本 | 嗅探 status | text_chars | pages_sampled/total | 嗅探后 route_type | rule_name | 拒绝理由（原文） |
|---|---|---|---|---|---|---|
| `pdf-digital.pdf` | `TEXT_LAYER_PRESENT` | **677** | 1/1 | `PDF_DIGITAL` | `pdf_sniff_digital` | — |
| `pdf-scanned.pdf` | `TEXT_LAYER_ABSENT` | **0** | 1/1 | `PDF_SCANNED_OR_IMAGE` | `pdf_sniff_scanned` | `pdf text layer absent: 0 chars over 1/1 pages` |
| `pdf-encrypted.pdf` | `ENCRYPTED` | 0 | 0/0 | `PDF_SCANNED_OR_IMAGE` | `pdf_sniff_encrypted` | `pdf is encrypted; text layer not readable (no password attempt)` |

**契约要点**：
- 加密件**不尝试口令**，直接判为"扫描版链路"，reason 明确写出未尝试解密；
- 扫描件与加密件都落到 `PDF_SCANNED_OR_IMAGE`（fail-closed：不确定就不当数字版）；
- 每份结果都带 `evidence()` 结构（status/text_chars/pages_*/avg/from_cache/sniffer_version），可直接进报告。

## 4. 实测③：OCR 引擎路由真值表（穷举 48 种组合）

调用 `resolve_engine_route(requested, is_clear, quality_available, paddleocr_available, vlm_is_mock)`。

| 决策 | 实际引擎 | skip_reason | 命中组合数 |
|---|---|---|---|
| `PARSED` | `paddleocr` | — | 10 |
| `PARSED` | `vlm` | — | 15 |
| `DEPENDENCY_MISSING` | — | `engine_dependency_missing` | 8 |
| `UNSUPPORTED_WITH_HINT` | — | `no_trusted_engine` | 7 |
| `UNSUPPORTED_WITH_HINT` | — | `vlm_adapter_is_mock` | 8 |

**契约要点**：48 种输入组合**没有一种**是"静默成功"——要么真解析并给出实际引擎，
要么给出带 skip_reason 的显式未解析。这正是 LLMKE 需要的"不静默降级"语义。

## 5. 实测④：DOCX 路径（**这条推翻了先前的判断**）

### 5.1 依赖缺失时的行为

```
MarkItDownAdapter().convert(input_path=<docx-plain>, route_type=RouteType.DOCX)
→ MarkItDownAdapterError(code=PARSER_IMPORT_ERROR,
   message="Failed to import markitdown: No module named 'markitdown'")
```

doc2md 当前环境**没有安装 markitdown**（其 `requirements.txt` 里有 `markitdown[all]`，但本机环境未装）。
行为是**显式报错**，不是静默返回空文本——这一点符合其设计红线。

### 5.2 markitdown 文本 → Document IR：**表格与图片全部丢失**

用含管道表格与图片引用的 markdown 调 `build_from_markitdown_text(...)`，实测：

```
stats      = {block_count: 4, table_count: 0, figure_count: 0, blocks_without_bbox: 4}
page_count = None
blocks     = 4 个，类型全部是 paragraph
首块 bbox  = None；page_no = None
管道表格   = 被当成普通段落文本（"| 指标 | 数据源 | 口径 |" 原样出现在段落里）
```

`build_from_markitdown_text` 的 docstring 明确写着「降级路径：无 bbox / 无页码 / **无表格结构**」。
⇒ **doc2md 的 DOCX 路径只产出段落级文本**：`table_count=0`、`figure_count=0`。

> 修正：我在 `PARSER-DESIGN-COMPARISON-V1.0.md` 里曾写"markitdown 路径的表格会变成 IR 的 TableCell"，
> 这是**错的**。`_PipeTableParser` / `_cells_from_html` 只在 **MinerU 内容列表 → IR** 那条路径使用。
> 以本次实测为准。

## 6. 实测⑤：CLI 的 DB 前置契约

| 命令 | 结果 |
|---|---|
| `route-parsers --dry-run --limit 1` | 处理 1 条**已登记内容**：`PDF sniffed: 1 / PDF digital: 1 / cache hits: 1`，末行 `Dry run: no sniff cache or route report written` |
| `parse-mineru-pdf --sha256 deadbeef… --dry-run` | `Failed/Empty/Timeouts/Partial/Errors` 全 0，`Dry run: True` |

**契约要点（重要）**：doc2md 的命令**不接受"给我一个文件路径"**，它按 **DB 中已登记的 `sha256`** 选择内容，
文件必须先经 `scan` + `copy-to-vault` 进入 vault。⇒ 若要把它当独立组件调用，
LLMKE 侧要么**复用其 DB 登记流程**，要么**给它的服务层加一个"按路径解析"的入口**（后者是改动，不在本次范围）。

## 7. 实测⑥：产物契约（从 `parsed_paths.py` 读取，未落盘）

每个内容按内容哈希分目录：`parsed/by_hash/<sha[:2]>/<sha[2:4]>/<sha256>/`，目录下固定 7 项：

| 产物 | 文件名 | 本次是否实测到文件 |
|---|---|---|
| 正文 | `parsed_text.md` | 否（只读约束，未写盘） |
| 元数据 | `parsed_metadata.json` | 否 |
| 解析清单 | `parse_manifest.json` | 否 |
| 文档 IR | `document_ir.json` | 否（但 IR 结构已由 §5.2 实测） |
| 渲染轨 | `rendered.md` | 否 |
| 解析器中间件 | `ir_source/`（目录） | 否 |

## 8. 对推荐的影响（必须改的那一条）

| 主题 | 原建议 | 实测后的建议 |
|---|---|---|
| **PDF** | 引用 doc2md | **维持**。嗅探 fail-closed、加密不试口令、证据块完整，实测符合预期 |
| **OCR** | 引用 doc2md | **维持**。真值表 48 组无静默成功 |
| **DOCX** | 引用 doc2md | **改为"不能直接引用"**：其 DOCX 路径**丢掉表格与图片**（table_count=0/figure_count=0），而 LLMKE 的对账场景必须有表格结构 |

DOCX 的三个可选处置：

1. **deepdoc 原生解析**（表格 cells + HTML + 图片 base64）——但需先满足 S1 回放发现的 3 条硬条件，
   且合并单元格识别仍是未完成 TODO；
2. **在 doc2md 侧补 DOCX 结构化**（复用其 IR schema 与图片流水线）——属于对 doc2md 的功能请求，
   需其维护方排期；LLMKE 不能自行改它；
3. **分治**：DOCX 用 deepdoc，PDF/OCR 用 doc2md——代价是两套解析栈、两套产物契约。

**TL 倾向**：先按 (3) 落地（PDF/OCR 引用 doc2md 独立组件、DOCX 走 deepdoc 适配），
同时向 doc2md 提出 (2) 的需求；等 doc2md 支持 DOCX 表格后再收敛为一套。

## 9. 本次没做到的（不冒充）

| 未做到 | 原因 | 影响 |
|---|---|---|
| 真实产物文件（`parsed_text.md` 等） | 只读约束：不写其 DB/vault/parsed | 产物**命名与目录结构**已确认，**内容格式**未取样 |
| `parse-mineru-pdf` 全链路（真跑 magic_pdf） | 需先把样本登记进其 DB（写操作） | PDF 的**解析产物质量**未测，只测了**分流决策** |
| DOCX 真实 markitdown 输出 | 其环境未装 markitdown，且我不改其环境 | §5.2 用的是**合成 markdown**，只能证明 IR 装配行为，不能证明 markitdown 对真实 docx 的转换结果 |
| 解析准确率 | 无标注真值集 | 属 M0 题库范畴 |

## 10. 复跑方式

```bash
# 路由 + 嗅探（纯函数，零副作用）
cd <doc2md>/backend && PYTHONPATH=. python - <<'PY'
from pathlib import Path
from app.core.parser_routing import match_route_type, route_pdf_with_sniff
from app.core.pdf_sniffing import load_sniff_config, sniff_pdf
cfg = load_sniff_config()
for f in sorted(Path('/tmp/llmke-probe/doc2md').glob('*.pdf')):
    print(f.name, sniff_pdf(f, config=cfg).evidence())
PY

# OCR 真值表 / IR 装配 / CLI dry-run 见本文 §4、§5.2、§6
```
