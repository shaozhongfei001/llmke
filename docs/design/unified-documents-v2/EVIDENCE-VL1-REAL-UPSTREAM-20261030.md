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

## 6. 过程中的 doc2md 修复（U-08 的直接原因）

跑真实产物时确认：`document_ir_builder` 早就存在，但**没有任何解析路径调用它**，所以下游拿不到 IR。
按"发现即修"处理，改动在 doc2md 仓新分支 `fix/017-ir-emission-wiring`（commit `28ec528`，未动其 `main`）：

| 项 | 改动 |
|---|---|
| IR 出口 | `_write_success_artifacts` 内调 `build_from_markitdown_text()` → `validate_document_ir(ir, parsed_text=text)` 自校验 → 写 `document_ir.json`（不自洽就不落盘） |
| 身份字段 | `parsed_metadata.json` 增 `content_uid`（与 manifest/IR 三方一致） |
| 清单 | `parse_manifest.json` 追加 `document_ir_path`、`ir_schema_version`（纯追加） |
| 三件套 | `parsed_text.md` 字节语义未动（仍是证据基准） |

重跑同一份 docx 后：

```
document_ir.json  parsed_metadata.json  parsed_text.md  parse_manifest.json   ← 3 件变 4 件
schema_version=document-ir/1.0，document_uid=doc_a846ab142d8d24af_005_mvp_v1
validate_document_ir(ir, parsed_text=...) → PASS（用 doc2md 自己的纯校验器）
```

登记结果随之升级：`--mode v2` → `llmke-parse-artifact/2.0`，4 件，合同 `PASS`；
但 `quality.state` 被压到 **`PARTIAL`**，因为 markitdown 的 IR 全部是 `inline_text`
（无 bbox、无表格矩阵、block 无页码）—— 平台据此拒绝把它当"结构化完整"。

doc2md 回归：`backend` 全量 **5 failed / 1492 passed / 133 skipped**，改动前后完全一致
（5 项均为既有 typer/click CLI help 版本问题）。新增断言写在 `test_parse_in_scope_success`，
本机因 MySQL 夹具不可用而 skip，需在有库环境执行。

## 7. VL1-03 第一步：快照投影与线上 chunk 只读对照

新增 `services/rag-alg/index_data_service/rag_projection/`：消费已提交快照 → 确定性窗口分块
（段落边界优先、MD 码点区间、`parse_artifact_id` 随每个 chunk），**不写** ES/Milvus/MySQL。
并存开关 `INGEST_PROJECTION_MODE=legacy|snapshot|shadow`，默认 `legacy`，未知值直接拒绝。

真实对照（只读 `_count`，chunk_chars=400、overlap=0）：

| file_id | 文件 | 快照 chunk | 线上 kb_9 | 线上 table_chunks_kb_9 | 差 |
|---|---|---|---|---|---|
| 333 | docx-table.docx | 1（144 字符） | 1 | 1 | **-1** |
| 329 | R12FIX-credit-ledger.xlsx | 1（343 字符） | 0 | 1 | 0 |

差异是**结构性的，不是数量噪声**：

- 线上是**双通道**（正文 chunk 在 `kb_9`、表格块在 `table_chunks_kb_9`）；本投影目前只产出单通道。
- 333 的线上正文 chunk 内容是 `DOCX with table下表为多指标对账口径。`（26 字符，表格内容被切到表格通道）；
  快照正文是 144 字符，**Markdown 表格整段留在正文里**。
- 即：直接切到 `snapshot` 会让表格内容从"独立表格通道"变成"正文里的文本"，检索行为会变。
  所以 `snapshot` 不能直接上线，必须先补表格通道（依赖 MinerU IR 的 `table_ref`/表格矩阵）。

## 8. 隔离索引回环（2026-10-31）

`scripts/v2_es_roundtrip_check.py`：把 `ingest_pipeline` 产出的 chunk 写进**临时索引**、按
`metadata.parse_artifact_id` 查回来、再删除。只允许 `v2rt_` 前缀，不碰 `kb_9` / `table_chunks_kb_9`。

实测（333 docx 快照，只读线上数据）：

```json
{"status":"OK",
 "channels":{"v2rt_kb_9":{"source_index":"kb_9","expected":2,"count":2,"by_artifact":2},
             "v2rt_table_chunks_kb_9":{"source_index":"table_chunks_kb_9","expected":1,"count":1,"by_artifact":1}}}
```

跑完 `_cat/indices/v2rt*` 为空（临时索引已删）。结论只到"载荷形状能被 ES 接收并可检索回"，
不等于线上切换已验证；Milvus/embedding 通道未测。

## 9. 隔离向量回环 + 字段覆盖测量（2026-10-31）

`scripts/v2_milvus_roundtrip_check.py`：真实 bge-m3（18090）编码 → 建**克隆生产 schema 的临时集合**
（`--template _kb_9`，同类型/同 dim/同 ARRAY element_type）→ 写入 → 自检索 top1 → 删除。

实测（生产 Milvus `19630 / rag_knowledge_base`）：

| 文件 | v2rt_kb_9 | v2rt_table_chunks_kb_9 | status |
|---|---|---|---|
| 333 docx | inserted 2 / recall@1 2 | inserted 1 / recall@1 1 | OK |
| 329 xlsx | inserted 1 / recall@1 1 | inserted 1 / recall@1 1 | OK |

跑完 `list_collections()` 无 `v2rt_*` 残留；ES 侧同样已清理。

**字段缺口的两次测量（第一次是我数错了，记录在此）**

第一次只按"载荷里有没有这个键"数，得到 23 个空值 —— 这个数**不能**当作缺口。
按 `_kb_9` 全量 270 行逐字段统计填充率后才看出真实结构：

```
270/270（必须补）：title position page_number knowledge_base_name file_path
                  file_size page_size parent_file_name create_time update_time
  0/270（本来就空）：folder_id title_path labels pic_url_list pic_offset_list
                  text_parent_id_list table_name order_num revise_date image_path
                  att_id main_id pic_children_id_list
```

同文件对照（file_id=333 是 docx）：生产里 `position=[[], []]`、`page_number=[0, 0]`、
`page_size=[[], []]` —— Office 文件本来就只有占位值，没有真实版面坐标。

**已补（`ingest_pipeline/enrich.py`）**：10 个必填字段全部给值；13 个恒空字段显式写空值保证
类型/对齐；版面三项写与旧链路同形的占位，并在 `field_fill.layout` 标 `unavailable`、
`field_fill.placeholder` 列出，**不许下游把占位当真实坐标做高亮**。
`offset` 也改成旧链路的 `[[start, end]]` 形状（原先给的是裸整数对）。

补完再跑一次生产 schema 回环（克隆 `_kb_9` 33 字段，写入走 metadata → 字段名直落）：

| 文件 | v2rt_kb_9 | v2rt_table_chunks_kb_9 |
|---|---|---|
| 333 | 2 inserted / recall@1 2 | 1 / 1 |
| 329 | 1 / 1 | 1 / 1 |

`field_fill.filled` = title, parent_file_name, knowledge_base_name, file_path, file_size,
create_time, update_time, offset。

**`source` 的结论（我上一版写错了，这里更正）**

上一版按 V2 契约把 `source` 写成 `parsed_text.md`，理由"要能回指原文"。查消费点后确认这是**错的**：
在本栈里 `source` 是**文件身份键 + URL 片段**，不是解析产物路径。

证据：

| 消费点 | 用法 |
|---|---|
| `alg_retrieval_service/app/retrieval_service.py:309` | `index_dict[metadata.source].add(chunk_index)` —— 按 source 聚合 |
| 同上 `:318` | `query_max_index(metadata.source, ...)` —— 求该文件最大块号 |
| 同上 `:321,326` | `query_es_file_index(metadata.source, index, pos)` —— 查**同文件**相邻块 |
| 同上 `:336` | 按 `(source, chunk_index)` 去重 |
| `app/view/api/retrieval_global_view.py:37` | 注释明确：Java 侧一律 `endPoint + "/" + source` 拼 URL |

若 `source` 写成固定的 `parsed_text.md`，后果不是"展示退化"而是**跨文件串台**：相邻块扩展会
把别的文件的块拉进来、去重会把不同文件的同号块判成重复、所有引用 URL 指向同一个假路径。

**已改成**：`source` = 每文件唯一的对象键（`r12-rag/kb_9/<file>/V0/<file>`，由调用方传入）；
V2 的原文回指另放 `parsed_text_ref`（`parsed_text.md` / `table:<id>`），不动既有语义。
未传 source 时 `field_fill.source_from=MISSING` 并把 source 记进 placeholder —— 显式暴露，
不静默留空（留空会让相邻块检索按空串匹配到所有文件）。

回归测试 `test_source_is_a_per_file_identity_key_not_a_fixed_path` 钉住这条：
两个文件产出的 source 必须不同且互不相交，且不得等于 `parsed_text.md`。

## 10. 仍未解决（不许当成已完成）

1. **U-08 只关闭了"有没有 IR"这一半**：markitdown 路径现在产出 IR，但它是**文本降级 IR**
   （block 全 `inline_text`），表格仍然只剩 Markdown 三行文本，没有单元格坐标与表头路径。
   要真正拿到表格结构，需要 **MinerU 路径的 IR 接线**（`build_from_mineru_content_list` 已存在但同样未被调用）
   \+ 本机装 `magic_pdf`；这一半仍未做。
2. **PDF 路径未通**：`pdf-digital.pdf` 被路由到 MinerU，本机缺 `magic_pdf`（GPU/重依赖），
   属于 U-03/U-09 同类缺口。
3. `parser_profile` 是平台侧补的档位（取自 doc2md 配置 `default_v1`），
   doc2md metadata 里没有该键；这条已写进 adapter 注释，避免下次误以为是上游字段。
4. 没有 loop 登记、没有独立 QA；`generated` 与合同快照未因这次实证变化（未改合同）。
