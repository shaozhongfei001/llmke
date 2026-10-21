# S1 可行性验证结果：CODE-01 解析模块「切断服务层耦合 + 固定样本回放」

- 日期：2026-10-21
- 批次：`LD-legacy-discovery`
- 对象：`alg_doc_parse_service`（CODE-01，py 84）
- 参照物：`docs/approvals/OWNER-RESOLUTION-2026-10-21-PRODUCTION-BASELINE.md` 认定的生产快照
- 结论：**可行**，但附带 3 条硬条件（见 §4）。**未覆盖 PDF/OCR/表格切分的图片路径**（缺模型，见 §5）
- 产物：
  - 工具 `spike/build_shimmed.py`（生成解耦副本）、`spike/run_arm.py`（单臂执行）、`spike/parity_check.py`（两臂对比）
  - 报告 `spike/PARITY-REPORT.md`、数据 `spike/parity-report.json`
- 复跑：

  ```bash
  python3 loops/LD-legacy-discovery/spike/parity_check.py \
      --src <RAG-SRC/_src>/rag-alg-service-api/rag-alg-service-api/alg_doc_parse_service \
      --samples /tmp/llmke-spike/samples --work /tmp/llmke-spike \
      --report loops/LD-legacy-discovery/spike/PARITY-REPORT.md \
      --json loops/LD-legacy-discovery/spike/parity-report.json
  ```

## 1. 结论

| 问题 | 答案 |
|---|---|
| 4 类服务层耦合能否切断？ | 能。**25 处 import 语句、14 个文件**，改成 `_shims.*` 后即可独立运行 |
| 切断后解析结果是否一致？ | **5/5 样本逐字段一致**（page_content / type / position / page_number / page_size / offset / title_path / chunk_index / need_filtered） |
| 能否直接搬进新模块？ | **不能原样搬**，必须先做两件事：① 替换 `parser/__init__.py` 为按需导入；② 随包携带非代码资源 |
| 是否有隐藏依赖？ | 有。docx 路径在**导入期**就需要 21 个重型依赖；`image_parser` 在**构造期**就加载 OCR 模型 |

样本与结果：

| 样本 | 大小 | 臂A 块数 | 臂B 块数 | 结论 |
|---|---|---|---|---|
| `sample.txt` | 143 B | 4 | 4 | IDENTICAL |
| `sample.html` | 110 B | 1 | 1 | IDENTICAL |
| `sample-docx-textonly.docx`（自建：标题/段落/表格） | 37 KB | 6 | 6 | IDENTICAL |
| `sample-m0.docx`（仓内 M0 方案） | 41 KB | 95 | 95 | IDENTICAL |
| `sample-m1.docx`（仓内 M1 方案） | 31 KB | 71 | 71 | IDENTICAL |

## 2. 实验设计（为什么这样设计）

| 臂 | 构成 | 作用 |
|---|---|---|
| **A（对照）** | 原始字节 + 只把 `parser/__init__.py` 换成按需导入 + 用 `sys.modules` 注入假的 `server.*` | 隔离变量：不改变任何解析代码 |
| **B（实验）** | 原始字节 + 按需导入 + `server.*` → `_shims.*` 改写（25 处） | 唯一差异：耦合切法 |

两臂都注入同一套第三方桩（显式清单），因此桩的语义不会污染结论。
报告里额外输出「两臂实际解析到的 `docx_parser.py` 绝对路径」，用于证明臂 A 没有被臂 B 顶替。

## 3. 切断清单（实测）

| 耦合点 | 原导入 | 新导入 | 涉及文件数（示例） |
|---|---|---|---|
| 配置（Nacos） | `server.nacos_utils.DocParseConfig` | `_shims.config.DocParseConfig` | 10：pdf/mineru/ali/fudan/text_in/excel/image 解析器、`deepdoc/utils.py`、`splitter/table.py`、`multi_version/version_rec.py`、`database_desc` |
| 模型引用 | `server.api_param.ModelInfo` | `_shims.model.ModelInfo` | 4：`deepdoc/utils.py`、`image_link.py`、`splitter/base.py`、`splitter/table_utils/table_index.py` |
| 进度上报 | `server.process_reporter.ProcessReporter` | `_shims.progress.ProcessReporter` | 1：`splitter/table_utils/table_index.py` |
| 运行时工具 | `server.utils.{load_local_ocr,compile_extension_regex_ignore_case,run_in_thread_pool,create_uuid}` | `_shims.runtime.*` | 5：pdf/image/ali/fudan/mineru/text_in/excel 解析器、`splitter/table.py` |
| 异常类 | `server.exception.custom_exception.*` | `_shims.errors.*` | 1：`mineru_parser.py` |

合计 **25 条 import 语句、14 个文件**。

## 4. 阻断级发现（三条硬条件）

### 4.1 `parser/__init__.py` 是全量导入 → 原包**无法被导入**

实测（未打桩）：

```
$ python -c "import deepdoc.parser"   # 原始目录
ModuleNotFoundError: No module named 'alibabacloud_credentials'
```

它一次 import 14 个解析器，把 `magic_pdf`、`onnxruntime`、阿里云 DocMind SDK、`tika` 全部变成**导入期**硬依赖。
→ 新模块必须改成按需注册表（本次已在副本里验证：`__getattr__` 惰性加载）。

### 4.2 docx 路径在导入期就要 21 个重型依赖

即使只解析纯文本 docx，`docx_parser` → `image_parser` → `mineru_parser` 的 import 链也会拉入：
`magic_pdf`、`onnxruntime`、`cv2`、`huggingface_hub`、`pyclipper`、`shapely`、`tika`、`pandas`、`openpyxl`、`xlrd`、`datrie`、`hanziconv`、`nltk` 等（实测 21 个桩）。
→ 要么装齐，要么把 `image_parser` 对 `MinerUParser/TextInParser` 的导入也改成惰性（建议后者）。

### 4.3 OCR 在**构造期**加载，不在调用期

`image_parser.py:21`：`self.ocr = load_local_ocr()['ocr']`，而 `load_local_ocr()` → `ocr_pool.load_ocrs('./ocr_models')`。
→ 即使文档里没有图片，只要构造 docx 解析器就会去加载 ONNX 模型。**这是"直取"最容易踩空的点**：没有模型目录，连纯文本 docx 都起不来。
新方案必须把 OCR 改成"用到才取"的惰性端口，且模型路径配置化。

### 4.4 非代码资源必须一起搬

`deepdoc/` 下除 `.py` 还有：`vision/ocr.res`（OCR 字典）、`splitter/*.pkl`（章节/表格规则数据）、`splitter/xg_splitter.json`。
另外 `rag_tokenizer` 尝试读取 `deepdoc/huqie.txt`——**该文件在源码里就不存在**，运行时降级为默认词典（只打 warning，不报错）。
→ 直取时要连资源一起搬，并且要显式记录「词典缺失导致的降级」，不能当成"和原系统一致"。

## 5. 未覆盖部分（不冒充已验证）

| 未覆盖 | 原因 | 影响 |
|---|---|---|
| PDF 解析（`pdf_parser`） | 依赖 `magic_pdf`/`onnxruntime` 与版面模型 | 客户文档多为 PDF，**这是最大缺口** |
| 图片解析与图文关联（`image_parser`、`image_link`） | 需要 OCR 模型与向量模型 | 图文混排文档的引用会缺失 |
| 表格切分（`splitter/table*`） | 依赖 `ProcessReporter` 的 DAO 与模型 | 表格类知识未验证 |
| 分块策略（`splitter/*`） | 本次只跑到解析，未跑 chunking | chunk 边界与 offset 一致性未验证 |
| 版式/多模态 | 需要视觉模型 | 版面还原能力未验证 |

## 6. 对《S1 源码利用清单》的修正

原清单说「`deepdoc/` 约 44 个文件可直取」。经本次验证，修正为：

> `deepdoc/` 的**解析内核**可直取，但**必须先做三件事**：① 惰性化 `parser/__init__` 与 `image_parser` 的重依赖导入；
> ② 把 4 类服务耦合换成端口（本次已验证 25 处改写不改变输出）；③ 把 OCR 从构造期改为调用期，并随包交付模型/词典资源。
> 未做这三件事之前，**不能声称"可直取"**。

## 7. 施工过程自纠（防止"假绿"，如实记录）

| # | 问题 | 后果 | 修正 |
|---|---|---|---|
| 1 | 臂 A 用 `sys.path.insert(0, shimmed)` 注入 `_shims` | 臂 A 实际加载了**臂 B 的 deepdoc**，对比退化成"自己和自己比"，5/5 一致是假绿 | 改为 `append`；并在报告里输出两臂实际文件路径作为防伪列 |
| 2 | 兜底打桩（任何缺失模块都打桩） | 掩盖真实缺失，且在 bs4/zstd 导入期访问桩属性，报出与真实行为无关的 `TypeError` | 改回显式桩清单；缺什么就装什么（补装 `pdfminer.six`、`html5lib`） |
| 3 | 判定逻辑 `A.blocks == B.blocks` | 两侧都失败时 `None == None` → 误判 IDENTICAL | 改为任一侧 `ok=False` 即判 `FAILED` |
| 4 | 直接在原仓跑 | 可能污染旧仓 | 全程只读原仓，所有副本落在 `/tmp`，仓库只存脚本与报告 |

## 8. 下一步

1. **PDF 先验证**（最重要）：需确认 `magic_pdf` 可否离线安装 + 是否有版面模型文件；否则 PDF 只能走 `pdfplumber` 兜底，能力与旧系统不等价，必须写成显式缺口。
2. 把本次的 3 条硬条件回写到 `S1-CODE-01-03-11-REUSE-EXTRACT-V1.0.md` 的判定里（已在 §6 修正）。
3. 同法验证 CODE-03（召回）：把 `operators/client/*` 换成端口后，用固定 query 回放召回结果。
4. 本验证**不构成复用批准**；`SOURCE-ASSETS.yaml` 的 `decision` 仍为 null。
