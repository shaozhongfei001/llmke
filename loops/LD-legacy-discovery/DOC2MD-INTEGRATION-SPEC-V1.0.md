# doc2md 对接规格 V1.0

- 日期：2026-10-21
- 状态：**规格草案**（不涉及代码改动；不改 doc2md、不改 llmke 的冻结控制面）
- 依据：`PARSER-DESIGN-COMPARISON-V1.0.md`、`PARSER-CONTRACT-PROBE-V1.0.md`（实测）、
  `DOCX-ROUTE-DECISION-V1.0.md`（D3）、`UNIFIED-IR-DRAFT-V1.0.md`
- 适用：PDF 与图片/OCR 走 doc2md；DOCX 不走（走 deepdoc 适配器）

## 1. 冻结版本（LLMKE 只认这个锚点）

| 项 | 值 |
|---|---|
| commit | `d9e4f9831f77b8f2d2ab33ead6a744c2562fe39d` |
| 分支 | `main` |
| `PARSER_ADAPTER_VERSION` | `005_mvp_v1` |
| `sniffer_version` | `pdf_sniff_v1` |
| `routing_rules_version` | `004_mvp_v2` |
| IR schema | `document-ir/1.0` |
| 冻结指纹 | 见 `coordination/doc2md.lock`（5 个文件 md5）；不符即 `DOC2MD_FROZEN_DRIFT` |

**规矩**：llmke 侧记录这五个值进自己的 manifest；doc2md 升级必须换锁并重跑本规格 §8 的验收用例。

## 2. 调用方式：子进程，不 import

| 项 | 约定 |
|---|---|
| 调用形态 | 子进程执行其 CLI（`python -m app.cli.main <cmd>`），**不 import 其 Python 模块** |
| 工作目录 | 固定为 doc2md 的 `backend/`（其 `PROJECT_ROOT` 按 `__file__` 推导，与 cwd 无关，但仍建议固定） |
| 解释器 | **doc2md 自己的环境**（其依赖含 magic_pdf / paddleocr），绝不复用 llmke 的 `.venv` |
| 超时 | 单文件默认 600s；`--timeout` 可覆盖；llmke 侧另设总预算 |
| 并发 | 单进程串行即可（其解析器内部有子进程），llmke 侧不假设线程安全 |

命令清单（实测存在）：

| 命令 | 用途 | llmke 是否使用 |
|---|---|---|
| `route-parsers` | 只做路由/嗅探（`--dry-run` 不写产物） | 用于**预判**，可选 |
| `parse-mineru-pdf` | PDF 解析 | ✓ |
| `parse-images` | 图片/OCR 解析 | ✓ |
| `parse-markitdown` | DOCX 等（**llmke 不使用**，见 D3） | ✗ |
| `check-parse-quality` / `build-evidence-chain` | 质量与证据链 | 可选，不进入 llmke 门禁 |

## 3. 输入契约（**这里有一个实测发现的硬障碍**）

| 事实 | 后果 |
|---|---|
| 其 CLI **按数据库中已登记内容的 `sha256` 选择待解析对象**，不接受"给我一个文件路径" | llmke 不能"丢一个文件过去就解析" |
| 实测：`parse-mineru-pdf --sha256 <不存在值> --dry-run` → 全部计数为 0 | 必须先在它的 DB 里登记 |
| 实测：`route-parsers --dry-run --limit 1` → 处理 1 条**已登记**内容 | 同上 |

因此 llmke 侧只有两种集成模式：

### M1（当前唯一可用）复用其登记流程

```text
llmke 写入文件 → doc2md: scan → copy-to-vault → route-parsers → parse-mineru-pdf/parse-images
              → llmke 读取其 parsed 产物 → 映射为 llmke-ir
```

代价：llmke 需要访问 doc2md 的 MySQL（`gits_ke`）与 vault 目录；**跨组件数据耦合**。

### M2（需要 doc2md 提供，当前不存在）按路径解析入口

doc2md 增加一个"输入 = 文件路径 + sha256、输出 = 产物目录"的入口（CLI 或服务层），
不需要 DB 登记。**这是本次对接最大的待办需求**，需其维护方排期。

**规格立场**：llmke 的实现必须先按 M1 设计（可用），把 M2 作为优化项；
不得假设 M2 存在，也不得为了 M2 去 fork doc2md。

## 4. 输出契约

每个内容按内容哈希分目录：`parsed/by_hash/<sha[:2]>/<sha[2:4]>/<sha256>/`，固定 7 项：

| 产物 | 文件 | llmke 是否必需 |
|---|---|---|
| 正文 | `parsed_text.md` | ✓（映射为块文本） |
| 元数据 | `parsed_metadata.json` | ✓ |
| 解析清单 | `parse_manifest.json` | ✓（状态与资产索引来源） |
| 文档 IR | `document_ir.json` | ✓（存在则优先；**缺失须记 `PARTIAL`，不得当成功**） |
| 渲染轨 | `rendered.md` | ✗ |
| 解析器中间件 | `ir_source/` | ✗（排查用） |

## 5. 状态契约（必须原样透传）

路由决策闭集：`ROUTE` / `UNKNOWN` / `UNSUPPORTED`
解析决策闭集：`PARSED` / `SKIPPED` / `DEPENDENCY_MISSING` / `UNSUPPORTED_WITH_HINT`
嗅探状态闭集：`TEXT_LAYER_PRESENT` / `TEXT_LAYER_ABSENT` / `ENCRYPTED` / `EMPTY_DOCUMENT` / `SNIFF_ERROR` / `DEPENDENCY_MISSING`

映射到 `llmke-ir.parse_status`：

| doc2md | llmke-ir | 下游要求 |
|---|---|---|
| `PARSED` 且 `document_ir.json` 存在 | `PASSED` | 正常入库 |
| `PARSED` 但 `document_ir.json` 缺失 | `PARTIAL` | 标 degraded，仍可入库但引用能力受限 |
| `SKIPPED` | `SKIPPED` | **不入库**，计入覆盖率缺口 |
| `DEPENDENCY_MISSING` | `DEPENDENCY_MISSING` | **不入库**，报运维（缺 magic_pdf/paddleocr 等） |
| `UNSUPPORTED_WITH_HINT` | `UNSUPPORTED` | **不入库**，`status_reasons` 保留其 hint 原文 |

**红线**：任何非 `PARSED` 都不得被 llmke 折叠成"成功"；`skip_reason` 必须原样保留。

## 6. 失败处理矩阵

| 场景 | doc2md 行为（实测/代码） | llmke 侧动作 |
|---|---|---|
| 加密 PDF | 嗅探判 `ENCRYPTED`，**不尝试口令**，走扫描链路 | 记录原状；若最终未产出，标 `UNSUPPORTED` + reason `encrypted`；**不得静默当空文档** |
| 扫描版 PDF | `TEXT_LAYER_ABSENT` → `PDF_SCANNED_OR_IMAGE` | 正常走 OCR 链路 |
| 空文档 | `EMPTY_DOCUMENT` | 标 `SKIPPED` + reason，不计入解析成功率分母之外 |
| 嗅探失败/损坏 | `SNIFF_ERROR`（异常不外抛） | 标 `PARTIAL`/`UNSUPPORTED`，保留 `detail` |
| 依赖缺失 | `DEPENDENCY_MISSING`（不降级） | 不入库 + 报运维 |
| 子进程超时 | 由其 `--timeout` 控制 | llmke 侧强杀并记 `TIMEOUT`（llmke 自定义状态，落在 `status_reasons`） |
| 进程崩溃 | 非 0 退出码 | 记 `CRASH` + 保留尾 800 字节输出（其 `_process_output_tail` 同款思路） |

## 7. 只读与隔离边界

| 项 | 约定 |
|---|---|
| doc2md 源码 | llmke 侧**只读**；不 fork、不打补丁、不改 config |
| doc2md 产物目录 | llmke **只读**其 `parsed/`；若需独立输出，走 M2 或复制到 llmke 自己的 `parsed` |
| doc2md DB | M1 模式需要只读访问；**禁止写其业务表**（登记动作由 doc2md 自己的 CLI 完成） |
| 凭据 | doc2md 的 `config/app.yaml` 含明文口令 → llmke 侧不得读取该文件，只通过其 CLI 间接使用 |
| 快照缓存 | 其 `sniff_cache/` 三重校验（cache_type/sha256/sniffer_version）；llmke 不复制该缓存 |

## 8. 验收用例（来自实测，必须可复跑）

样本在 `coordination/samples/`（3 PDF + 3 DOCX）。

| 样本 | 期望路由/状态（实测） |
|---|---|
| `pdf-digital.pdf` | `TEXT_LAYER_PRESENT`（677 字符，1/1 页）→ `PDF_DIGITAL` / `pdf_sniff_digital` |
| `pdf-scanned.pdf` | `TEXT_LAYER_ABSENT`（0 字符）→ `PDF_SCANNED_OR_IMAGE` / `pdf_sniff_scanned` |
| `pdf-encrypted.pdf` | `ENCRYPTED`（pages_total=0）→ `PDF_SCANNED_OR_IMAGE` / `pdf_sniff_encrypted`，reason 含 `no password attempt` |
| 3 份 DOCX | `DOCX` / `ext_docx` / `MARKITDOWN_FAMILY`（**llmke 不走此路**） |

OCR 引擎真值表：48 种输入组合 → 5 种结果，**无静默成功**（详见 probe 报告 §4）。
对接实现必须至少覆盖：`PARSED/paddleocr`、`PARSED/vlm`、`DEPENDENCY_MISSING`、`UNSUPPORTED_WITH_HINT×2`。

## 9. 待 doc2md 提供的两项（本次对接的外部依赖）

| # | 需求 | 影响 | 优先级 |
|---|---|---|---|
| D2-1 | **按路径解析入口**（不需要 DB 登记） | 消除 M1 的跨组件数据耦合 | 高 |
| D2-2 | **DOCX 表格/图片结构化**（`table_count>0`、`figure_count>0`） | 若提供，可把 DOCX 也收敛到 doc2md，取消双栈 | 中（当前由 D3 的 deepdoc 适配器兜住） |

## 10. 本规格不做的事

- 不改 doc2md 代码、不提 PR、不 fork；
- 不定义 doc2md 的内部实现（只约束它对外可见的命令、产物与状态）；
- 不把"用 M1 能跑通"当成"集成完成"——M1 只证明链路通，生产可用性还需并发/超时/重试实测；
- 不涉及解析准确率（M0 题库范畴）。
