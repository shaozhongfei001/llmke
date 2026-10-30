# VL1 真实上游实证：LLMKE 知识库文档 → doc2md → ParseArtifact 登记

日期：2026-10-30　性质：**组件级实证**（真实字节 + 真实上游 CLI）
不能推出：结构化能力已上线、图/RAG 已消费、独立 QA、目标机发布。

## 1. 输入：从既有 LLMKE 知识库里选的真实文件

来源库：`gienrag.knowledge_base_list`（库 `kb_9`，`status=3` 生效），对象存 MinIO 桶 `r12-rag`。

| 台账 id | 文件名 | 大小 | MinIO 对象键 | 原件 sha256 |
|---|---|---|---|---|
| 333 | `docx-table.docx` | 36944 B | `kb_9/docx-table.docx/V0/docx-table.docx` | `a846ab14…8fa1d` |
| 329 | `R12FIX-credit-ledger.xlsx` | 5340 B | `kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx` | `53d265c7…02231` |
| 331 | `pdf-digital.pdf` | 3577 B | `kb_9/pdf-digital.pdf/V0/pdf-digital.pdf` | `4a21313b…9f72a` |

取件方式：S3 接口只读 `fget_object`（不落地到任何仓库目录），得到三个真实原件。
选择理由：docx 内含表格（后续可对比"有 IR"与"只有文本"的差别）；xlsx 走 markitdown 的另一条分支；pdf 用来看路由分流。

## 2. 上游环境（隔离，不碰共享算法环境）

- 源码：doc2md `d9e4f98`（设计记载的交接基线 `52a63ec` 是其祖先）。
- 解释器：仓外独立 venv，Python **3.11.7**（doc2md 用到 `datetime.UTC`，3.10 直接 ImportError），
  安装 `typer/click/rich/PyYAML/SQLAlchemy/pymysql/pydantic/pydantic-settings/pypdf/markitdown[all]`；
  `markitdown 0.1.9`、`mammoth 1.13.0`、`pdfminer.six 20260107`、`openpyxl 3.1.5`。
- 配置：把 doc2md `app.yaml` 的全部 storage 根重定向到 `/tmp/doc2md-ws/*`，避免污染 doc2md 仓库目录；
  `parser.default_parser_profile=default_v1`。
- 注册库：沿用 doc2md 自己的 dev 库 `gits_ke`（其 config 注释即如此声明）。**副作用如实登记**：
  scan 新增 3 条 content + 3 条 instance，copy-to-vault 写 vault 目录，route/parse 写报告行；
  **未删除、未修改任何既有行**。

## 3. 命令与结果

全部在 `/tmp/doc2md-ws` 下执行，`PYTHONPATH=<doc2md>/backend`：

| 步骤 | 命令 | 结果 |
|---|---|---|
| 登记 | `-m app.cli.main scan --path /tmp/incoming --config app.yaml` | `New instances: 3 / New contents: 3 / Errors: 0` |
| 入库 | `copy-to-vault --sha256 <uid>`（逐个） | 各 `Copied: 1 / Errors: 0` |
| 路由 | `route-parsers --sha256 <uid>`（逐个） | 无错误；docx→`DOCX`、xlsx→表格路由、pdf→非 markitdown |
| 解析 | `parse-markitdown --sha256 <uid>` | docx `Parsed: 1`；xlsx `Parsed: 1`；**pdf `Skipped: 1`**（路由到 MinerU，本机无 `magic_pdf`） |

产物目录（doc2md 约定 `parsed/by_hash/<aa>/<bb>/<uid>/`）实际只有 **三件套**：

```
parse_manifest.json   parsed_metadata.json   parsed_text.md
```

**没有 `document_ir.json`**，`parsed_metadata.json` 也**没有** `content_uid` —— 与源码阅读结论一致（U-08 由此从"读代码推断"变为"实测确认"）。

docx 的正文（真实、可核对，含表格转写）：

```markdown
# DOCX with table

下表为多指标对账口径。

|  |  |  |
| --- | --- | --- |
| 指标 | 数据源 | 口径 |
| 日均存款 | T-CORE-001 | 按业务日跨账户汇总/天数 |
| 用电量 | T-EXT-001 | 月度同比 |
```

manifest 关键字段：`status=SUCCESS`、`route_type=DOCX`、`parser_name=markitdown`、
`parser_adapter_version=005_mvp_v1`、`output_hash=1f2702dc…f189d`、`content_uid=a846ab14…8fa1d`。

## 4. 平台侧登记（走 CR BL-2.0.0-02 的 text-only 通路）

```bash
PYTHONPATH=services/rag-alg/index_data_service python -m parse_artifact \
  --source /tmp/doc2md-ws/parsed/by_hash/a8/46/a846ab14…8fa1d \
  --store /tmp/pa-real/docx --source-revision doc2md@d9e4f98 \
  --parser-profile default_v1 \
  --runtime-lock-hash <sha256 of doc2md/backend/requirements.txt> \
  --config-hash <sha256 of 实际使用的 app.yaml> \
  --mode text_only --validate
```

两份产物均返回：

```json
{"status":"COMMITTED","schema_version":"llmke-legacy-text-artifact/1.0","parts":3,
 "quality":{"state":"PARTIAL","capabilities":["text","source_alignment"],
            "warnings":["上游未提供 document_ir.json：只登记文本能力，不得声明表格/图片/结构能力"]},
 "contract":"PASS"}
```

字节一致性：快照内 `parsed_text.md` 的 sha256 与上游逐字节相同（`1f2702dc…f189d`），
即"快照=上游字节的不可变副本"，不是重新生成的文本。

## 5. 这次实证排除了哪些借口

| 之前的不确定 | 现在的证据 |
|---|---|
| "真实 doc2md 产物能不能进快照" | 能：两份真实产物 `COMMITTED` + 合同 `PASS` |
| "缺 `content_uid` 是不是样例问题" | 不是：真实 metadata 同样没有，只有 manifest 有 |
| "是不是环境里没跑过 doc2md" | 跑过：真实 CLI 四步全通（docs 有表格被转写成 MD） |
| "text-only 会不会被悄悄当成结构化" | 不会：`state=PARTIAL`，能力枚举不含 `document_ir/table_cells/figure_assets`，schema 层拒绝 |

## 6. 仍未解决（不许当成已完成）

1. **U-08 未关闭**：doc2md 仍不产 IR，所以表格结构、单元格坐标、图表数据都拿不到；
   上面那份 docx 的表格只剩 Markdown 三行文本，**不能**当"表格解析已完成"。
2. **PDF 路径未通**：`pdf-digital.pdf` 被路由到 MinerU，本机缺 `magic_pdf`（GPU/重依赖），
   属于 U-03/U-09 同类缺口。
3. `parser_profile` 是平台侧补的档位（取自 doc2md 配置 `default_v1`），
   doc2md metadata 里没有该键；这条已写进 adapter 注释，避免下次误以为是上游字段。
4. 没有 loop 登记、没有独立 QA；`generated` 与合同快照未因这次实证变化（未改合同）。
