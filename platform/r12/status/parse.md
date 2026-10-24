# R12 解析服务状态报告（alg_doc_parse_service）

- 角色：parse-ops　生成：2026-10-25　更新：2026-10-25（含 TL 决定登记、A/B/C 三项交付）　服务：`0.0.0.0:12340`
- 工作根目录：`/home/szf/data/dev/llmke-r12`

**结论（2026-10-25 晚更新）**：D-1/D-2/D-3 三项 CR 已按 TL 批准实施（编号 `R12-FIX-PARSE-02/03/04`），并在**两种状态**下完成 12 用例回归：**VLM 可用 12 PASS / VLM 不可用 12 PASS**（后者**无任何 500**，C08 由改造前 500/0.37s 变为 **200/1.33s**）。详见 §16。表格、图片、定位字段**没有做"只留纯文本"的降级**；所有降级与阻塞按类写在 §8。**DOCX 内嵌图片**已在 VLM `18093` 就绪后重跑通过（正文块+图片块都在，满足 TL 决定③），但**图片块文字质量存在真实缺陷 D-1**（二次多模态处理自我退化后覆盖，§8-①），需 CR 修复。

**2026-10-25 更新（本机 LLM 就绪后）**：`18092` 已实测可用（`qwen2.5-7b-instruct`，OpenAI 兼容、无鉴权），**表格摘要已由本机端点自证通过**（C07/C09），此前"外部 DeepSeek 一次性验证"的临时记录**已被本机自证取代**（见 §9）。

---

## 0. TL 决定登记（2026-10-25，写入即生效）

| # | TL 判定 | 本报告落点 |
|---|---|---|
| ① | `R12-parse-fix-01` **接受为正式修复**，编号定为 **R12-FIX-PARSE-01**；注释须保留编号与原因 | §5（代码注释已改为 `[R12-FIX-PARSE-01]`） |
| ② | layout.onnx 回退 2024-03 版**接受**，但须留"新版 postprocess 不兼容"实测证据（栈前 20 行）+ 回退版本号/文件 md5，供 R13 复核 | §4 与 §4.1（含 A/B 复现输出与 md5） |
| ③ | docx 含图片 500：18092 起来后**必须重跑**，给出"正文+图片块都在"的证据，否则算未通过 | §8-① 标记为 **未通过（待重跑）**；用例 C08 = BLOCKED_FOR_MM |
| ④ | PPTX 图片通路（上游 `is_ppt=False` 硬关）与 `.doc` 需 tika：**本轮不立项**，作为 R12 已知限制记入 R13 清单 | §8-②、§8-③ 标注"R13 清单 / 不立项" |
| ⑤ | 外部 DeepSeek 只作**一次性验证记录**，不得写入任何正式配置；**不构成 R12 通过证据**；正式通路必须指本机 18092 | §9（明确声明） |
| ⑥ | 加密 PDF `fail_reason` 为空：记缺陷，不修；须写明"错误码 1100 有、原因文本缺" | §8-④ |

### 0.1 追加：本机 LLM 端点就绪后的状态变化（2026-10-25，model-ops 通知 + 我实测）

| 事项 | 变化 |
|---|---|
| `18092` 文本 LLM | **可用**。`GET /health` → `{"status":"ok"}`；`GET /v1/models` → `qwen2.5-7b-instruct`；`POST /v1/chat/completions` 实测返回中文结果（`prompt_tokens=53`，首 token 45ms）。**无鉴权，`ModelInfo.key` 留空**；必须写 `127.0.0.1`，不能用 `[::1]` |
| 表格摘要（C07/C09） | **转为本机自证**：C07 docx 含表格 2.83s、C09 xlsx 1.94s→6.28s（后者含一次 LLM 摘要 + 44 tok/s 生成）。**R12 通过证据成立**（此前外部 DeepSeek 记录仅作历史，不再引用） |
| 多模态（C08 docx 内嵌图片） | **18093 已就绪并重跑通过**（`qwen2.5-vl-3b-instruct`，HTTP 200，正文块+图片块都在）。但发现**缺陷 D-1**：图片块文字被二次多模态处理覆盖为错误结论（根因已定位，§8-①），需 CR 修复。18092 仍**严禁**用于此路径 |
| 容量约束 | 已实测并据此调整：`table_split_max_worker` 由 2 → **1**（避免 4096 共享上下文下并发截断），详见 §9.2 |
| **多图文档（D-2）** | **状态随服务端 ctx 变化**：`18093` 在 ctx=8192 时，2 图（合计 5804 token）与 3 图均**整篇 500**（`failed to process mtmd chunk`）；model-ops 于 03:20 把 18093 ctx 提到 **16384** 后，我用同一批 fixture 重测：**2 图 200 / 675.65s、3 图 200 / 526.96s，均出图**。→ 失败根因是统一 KV 余量（≈71% 水位触发 mtmd 硬失败），不是"图数上限"。**但调用侧仍不可控**：`multi_modal_process` 默认 32 线程池 + 单图失败无降级 → CR 保留（§8-⑨） |

---

## 1. 启动 / 停止 / 健康检查

环境文件（我维护，供 `r12ctl.sh` 引用）：`platform/r12/run/doc-parse.env`

```bash
R12=/home/szf/data/dev/llmke-r12/platform/r12
SVC=/home/szf/data/dev/llmke-r12/services/rag-alg/alg_doc_parse_service
cd $SVC && source $R12/run/doc-parse.env
nohup $R12/venvs/parse/bin/python -u alg_doc_parse_service_start.py \
  > $R12/logs/doc-parse.log 2>&1 &
echo $! > $R12/run/doc-parse.pid
```

env 内容（`NACOS_NAMESPACE` 必须为空串=public）：

```
PYTHONPATH=/home/szf/data/dev/llmke-r12/services/rag-alg/alg_doc_parse_service
NLTK_DATA=/home/szf/data/dev/llmke-r12/platform/r12/venvs/parse/share/nltk_data
OCR_PATH=/home/szf/data/dev/llmke-r12/platform/r12/models/ocr_models
NACOS_SERVER_ADDRESS=http://127.0.0.1:18848
NACOS_NAMESPACE=
NACOS_DATA_ID=alg_doc_config_py
NACOS_GROUP=DEFAULT_GROUP
LOG_LEVEL=INFO
```

- 健康检查：`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:12340/docs` → 200
- **工作目录必须是服务目录**：`deepdoc/splitter/section_splitter.py:40` 用相对路径加载 `deepdoc/splitter/xg_splitter.json`。
- loguru 文件日志目录 `log.py` 硬编码 `./logs/parse`（相对 cwd），已建软链 `services/rag-alg/alg_doc_parse_service/logs/parse -> platform/r12/logs/parse`。
- 停止：`kill $(cat platform/r12/run/doc-parse.pid)`
- 端口占用备注：`127.0.0.1:18099` 是 **legacy 仓**（`/home/szf/data/dev/llmke`，非 `-r12`）的 `modules.answer_api.server` 残留进程（pid 2712973，早于 R12 开工），**与本批次无关**，落库/联调不要用它（model-ops 已核实归属）。

---

## 2. Nacos 配置（已按 TL A 项要求整理成交付文件）

发布目标：`http://127.0.0.1:18848/nacos`，namespace=**public**（tenant 空串）。**投递清单与发布命令见 `platform/r12/nacos/README-parse-configs.md`**，4 个 data_id 内容文件同目录：

| data_id | 文件 | 关键内容 |
|---|---|---|
| `alg_doc_config_py` | `alg_doc_config_py.yaml` | server 12340 / chunk 512 / overlap 100 / use_* false / bypass true / log_path / layout_garbage_path / 批量重试参数 / `other-nacos` 三项 |
| `alg_doc_parse_java_common` | `alg_doc_parse_java_common.yaml` | `server.host-ip=127.0.0.1`、`minio.uri=http://${server.host-ip}:19000`、`minio.access-key/secret-key`、`mysql`（url/user/pwd/table_name/**schema**） |
| `alg_doc_parse_java_gateway` | `alg_doc_parse_java_gateway.yaml` | `server.port=8088`（save_to_minio / 异步回调） |
| `alg_doc_parse_index` | `alg_doc_parse_index.yaml` | `es_server.port=19200`、`milvus_server.port=19630`、`milvus_conn_config.milvus_database=rag_knowledge_base` |

要点（给 TL 合并时避坑）：
1. 上述 4 个 data_id 全是**解析服务私有**，不含跨服务共享配置；TL 权威发布时**覆盖同 data_id** 即可。若要改名为共享 data_id，只需同步改 `other-nacos` 三项的 `data-id`。
2. `other-nacos` 引用的 data_id **必须同时存在**：`nacos_utils.create_client` 对缺失配置不兜底（`yaml.load(None)` 直接崩）。
3. `alg_doc_config_py.mysql: {}` 必须保留为空 map（`process_reporter.py:48` 先取 `config['mysql']` 再 `.update(java_common['mysql'])`）。
4. **bucket 不是配置项**：`minio_utils.py:52` 用 `file_path` 第一段做 bucket → `r12-rag/fixtures/a.pdf` = bucket `r12-rag` + object `fixtures/a.pdf`。这是调用约定，需周知其它角色。
5. `alg_doc_parse_java_common.mysql.schema` 是我按代码实际列反推的**最小 DDL**（非原厂），TL 若有正式 schema 直接覆盖。

---

## 3. 依赖处置表（venv `platform/r12/venvs/parse`，CPython 3.11.15，1.5G）

安装：`uv pip install --python <venv>/bin/python -i https://mirrors.aliyun.com/pypi/simple/`（pypi.org 不通）。

| 包/项 | 声明 | 实际 | 处置 |
|---|---|---|---|
| pyyaml | requirements `==5.3` | **6.0.3** | 5.3 无 cp311 wheel；按 pyproject `>=6.0.3`。代码仅用 `yaml.load(FullLoader)`，行为一致 |
| opencv-python + headless | 两者都声明 | **仅 headless 4.8.1.78** | 同时装两份会互相覆盖 `cv2/` 导致随机崩溃；解析只用图像变换，headless 足够 |
| onnxruntime | `==1.15.1` | 1.15.1 | 正常（CPU EP） |
| xgboost | `==2.0.3` | 2.0.3 | 正常（加载旧 binary 有 warning） |
| datrie | `==0.8.3` | 0.8.3 | 源码编译成功 |
| alibabacloud_docmind_api20220711 | `==1.3.1` | 1.3.1 | **首轮漏装**：`ali_parser.py:9` 无条件 import，`use_ali=false` 也要求存在 → 补装 |
| tika / tika-server.jar | `tika==2.6.0` | 库已装，**jar 未装** | 仅 `.doc` 需要（§8-③） |
| magic-pdf(mineru) | 注释掉 | 未装 | `use-mineru=false`，仅 INFO 提示 |
| reportlab / pillow | 未声明 | 5.1.0 / 13.0.0 | 仅用于造中文测试样本，非运行依赖 |

关键版本：fastapi 0.109.1 / uvicorn 0.30.1 / pydantic 2.14.1 / langchain 0.3.27 / langchain-community 0.3.27 / numpy 1.26.4 / pandas 2.0.3 / mysql-connector-python 9.1.0 / nacos-sdk-python 2.0.9 / nltk 3.9.2 / jieba 0.42.1 / tiktoken 0.12.0 / pdfplumber 0.11.5 / pypdf 3.9.0。

---

## 4. 模型与词典资产（`platform/r12/models/ocr_models`，152M，`OCR_PATH`）

网络事实：`huggingface.co`、`raw.githubusercontent.com` 不通；`hf-mirror.com`、`cdn.jsdelivr.net` 可用。

| 资产 | 来源 | 文件 md5 | 备注 |
|---|---|---|---|
| det.onnx | `hf-mirror.com/InfiniFlow/deepdoc@main` | `99ca4e01884f8cfabe76acfd777d8cea` | 4,745,517 B |
| rec.onnx | 同上 | `a8b210ea11e6afd4d261fec71fe6a74e` | 10,826,336 B |
| ocr.res | 同上 | `0eecb02b7413c25597dfc06c56b7242a` | 26,249 B |
| tsr.onnx | 同上 | `4465045b74159a4c8fb468d99d3170dc` | 输出 `[1,11,8400]` |
| **layout.onnx / layout.laws / layout.manual / layout.paper（当前生效）** | **`InfiniFlow/deepdoc@c8ee91cf943f81e8f0fa58364e51990997b82c85`（2024-03-25 "Upload layout.onnx"）、`@5d4559cc…`（layout.paper）、`@14ec39e4…`（layout.manual）、`@adf4d036…`（layout.laws）** | **`78868d818a53b4415a3ac94f910ab877`**（四个文件内容相同，12,246,134 B，输入 `[1,3,640,640]`，输出 `[1,15,8400]` = 4+11 类） | **R12 生效版本**；R13 升级时按此 md5+commit 复核 |
| layout 主分支 2026 版（**已回退，仅留档**） | `InfiniFlow/deepdoc@main`（2026-09-04） | `927b8bd7437459c948a18a61955a7722`（75,726,930 B，输入 `[1,3,1024,1024]`，输出 `[1,300,6]`） | 备份名 `layout.2026-newformat.onnx.bak`，**勿直接替换**，原因见 §4.1 |
| updown_concat_xgb.model | `hf-mirror.com/InfiniFlow/text_concat_xgb_v1.0` | `53ec2b6f54de28c953cc10d771fc6efa` | 5,906,150 B；`ocr_pool` 无条件加载 |
| huqie.txt + huqie.txt.trie | `hf-mirror.com/InfiniFlow/huqie` | — | 放 `deepdoc/huqie.txt(.trie)`;**未降级**，实测 `上海浦东发展银行2025年年度报告` → `上海浦东发展银行 2025 年 年度报告` |
| nltk_data（punkt/punkt_tab/wordnet） | `cdn.jsdelivr.net/gh/nltk/nltk_data@gh-pages` | — | 放 `venvs/parse/share/nltk_data`（nltk 默认搜 `sys.prefix/share/nltk_data`，同时显式设 `NLTK_DATA`）。`omw-1.4.zip` 在 gh-pages 404 未装 → 影响仅非英文词形还原 |

### 4.1 layout.onnx 回退证据（TL 决定②要求）

新版模型输出已是**后处理过的 `[1,300,6]`**（x0,y0,x1,y1,score,class），而本仓 `deepdoc/vision/recognizer.py:postprocess` 期望原始 YOLO 输出 `[1,4+nc,8400]`，按 `np.squeeze(boxes).T` 解释后 `class_ids` 会取到 ≥11 的下标，撞上 `label_list`（11 类）越界。A/B 复现（同一段代码、同一张图，仅换模型）：

```
[2026新版] input=[1, 3, 1024, 1024] output=[1, 300, 6] label_list=11 -> IndexError: list index out of range
[2024-03回退版] input=[1, 3, 640, 640] output=[1, 15, 8400] classes=11 label_list=11 -> postprocess OK, boxes=0
```

新版栈（前 20 行，实测）：

```
Traceback (most recent call last):
  File "<stdin>", line 10, in probe
  File "/home/szf/data/dev/llmke-r12/services/rag-alg/alg_doc_parse_service/deepdoc/vision/recognizer.py", line 427, in postprocess
    return [{
           ^^
  File "/home/szf/data/dev/llmke-r12/services/rag-alg/alg_doc_parse_service/deepdoc/vision/recognizer.py", line 428, in <listcomp>
    "type": self.label_list[class_ids[i]].lower(),
            ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
IndexError: list index out of range
```

（本报告首轮真实解析中的同一异常出现在调用链 `pdf_parser._layouts_rec → layout_recognizer.__call__ → recognizer.postprocess`，`server/loader.py:452` 记录 `list index out of range`，返回 `code=1100`。）

结论：**不是配置问题、不是模型损坏**，是导出格式断代。R13 若要升级到 2026 版模型，必须同步改造 `Recognizer.postprocess`（+ 输入 1024 尺寸与类别映射），属代码改动，需单独 CR。

---

## 5. 代码改动（唯一一处）

`services/rag-alg/alg_doc_parse_service/server/controller.py`（chunk 排序，**TL 已接受为 R12-FIX-PARSE-01**）：

```python
# 原：含表格的 docx 会因表格块 page_number 为空列表而整篇 500
self.all_chunks = sorted(self.all_chunks, key=lambda x: [x["metadata"]["page_number"][0], ...])
# 改后（注释中保留编号与原因）
# [R12-FIX-PARSE-01] 表格类chunk（如docx内表格）可能没有页码/页尺寸（page_number为空列表），
# 原实现直接取 page_number[0] 会抛 IndexError 导致整篇解析 500；此处对缺失页码降级为 0。
self.all_chunks = sorted(self.all_chunks, key=lambda x: [(x["metadata"].get("page_number") or [0])[0], ...])
```

- 性质：崩溃修复，不改变解析内容、不丢字段、不绕过断言；对正常数据排序语义不变。
- 触发样本：`docx-table.docx`（TL 提供），改前 `HTTP 500 IndexError`，改后 `200 + text块 + table块`。

---

## 6. 实测矩阵（`POST /parse_without_indexing`，need_chunk=true，chunk_size=512，overlap=100，file_type=naive）

样本全部经 MinIO 真实取文件（bucket `r12-rag`，key `fixtures/*`）：TL 提供的 6 个 + 我生成的 5 个中文/表格/图片样本。

| # | 样本 | HTTP | 耗时 | chunks | 类型 | 首块前 80 字 | offset | page_number | position |
|---|---|---|---|---|---|---|---|---|---|
| 1 | pdf-digital.pdf | 200 | 0.32–1.04s | 2 | text×2 | `Digital PDF sample····2,983,333.33 CNY. This page has a real text layer.Paragrap` | ✔ `[[0,464]]` | ✔ `[1,…]` | ✔ 8 组 bbox |
| 2 | cn-digital.pdf（我造，中文文本层） | 200 | 0.31–0.38s | 1 | text | `附件二：客户访前准备·授信审批材料（数字版）客户名称：上海浦东发展集团有限公司客户编号：CUST-CORP-0001日均存款：2,983,333.33 元（口径` | ✔ `[[0,236]]` | ✔ | ✔ |
| 3 | pdf-scanned.pdf | 200 | 0.47–0.54s | 1 | text | `SCANNED PAGE-notex layene 10 of alocume nt imagne 11 of a 9ine 13 of a scanned docume…`（OCR 输出，含识别噪声） | ✔ `[[0,103]]` | ✔ | ✔ |
| 4 | cn-scan.pdf（我造，**无文本层**中文扫描件） | 200 | 0.51–0.53s | 1 | text | `附件三：授信审批意见通知书客户名称：上海浦东发展集团有限公司授信金额：人民币5000万元审批结论：同意，期限12个月签发日期：2026年10月20日编号：SPDB-2026-PJ-00871` | ✔ `[[0,95]]` | ✔ | ✔ |
| 5 | pdf-encrypted.pdf | 200（业务失败） | 0.04–0.06s | 0 | — | `success=false`、`code=1100`、**`fail_reason` 为空字符串**（§8-④） | — | — | — |
| 6 | docx-plain.docx | 200 | 0.07–0.08s | 1 | text | `Plain DOCX第一段：客户访前准备。第二段：日均存款 2,983,333.33 元。` | ✔ `[[0,45]]` | 有字段但恒 `[0]` | ✘ `[[0,0]×4]` |
| 7 | docx-table.docx | 200 | 2.83s（本机 18092，含表格摘要） | 2 | text+**table** | `DOCX with table下表为多指标对账口径。` / 表格块 `\|指标\|数据源\|口径\|\n\|日均存款\|T-CORE-001\|按业务日跨账户汇总/天数\|…` | ✔（表格块=单元格坐标 `[[r,c],…]`） | 表格块为空 | 表格块为空 |
| 8 | docx-image.docx | 200 | **505.92s** | 2 | **text+image** | 正文：`DOCX with image下面内嵌一张图片。` / 图片块：`图片中包含了一张扫描的文档图片，图片上没有文字信息。`（**该句为缺陷 D-1 的错误结论**，见 §8-①） | 图片块 offset 为零长 `[[26,26]]` | 图片块 `[]` | 图片块 `[]`（但 `metadata.boxes=16`） |
| 9 | table-ledger.xlsx（6 列 5 行中文表） | 200 | 6.28s（本机 18092，含表格摘要） | 1 | **table** | `\|客户编号\|客户名称\|授信额度(万元)\|已用额度(万元)\|五级分类\|到期日\|` + 4 行数据 | ✔（单元格坐标） | ✘ 空 | ✘ 空 |
| 10 | image-slide.pptx（含图片） | 200 | 0.04–0.05s | 1 | text | `2026年上半年风险资产分析\n不良率 1.12%，较年初下降 0.08 个百分点；关注类占比上升。区域风险分布图` | ✔ `[[0,56]]` | 有字段但恒 `[0]` | ✘ `[[0,0]×4]`；**无图片块**（§8-②） |
| 11 | scan-text.png（中文文本图） | 200 | 0.30–0.41s | 1 | text | `附件三：授信审批意见通知书客户名称：上海浦东发展集团有限公司授信金额：人民币5000万元审批结论：同意，期限12个月签发日期：2026年10月20日编号：SPDB-2026-PJ-00871` | ✔ `[[0,95]]` | ✔ | ✔ |
| 12 | cn-digital.pdf + cn-scan.pdf（**单请求 2 文件**） | 200 | 0.77–0.81s | 2 | text×2 | 两文件各自成块，未见串档 | ✔ | ✔ | ✔ |

判定：
- **chunk>0 且含中文正文**：cn-digital、cn-scan、docx-plain、docx-table、xlsx、pptx、png、C12 批次 —— 满足；pdf-digital/pdf-scanned 的 TL 样本原文是英文（非解析问题）。
- **定位信息至少一类**：全部成功样本满足；值 0/空的逐项标注如上。
- **扫描件确实走 OCR**：pdf-scanned 输出为典型 OCR 噪声且该 PDF 无文本层；cn-scan.pdf 是我用 PIL 把中文图转 PDF（纯图像、无文本层），OCR 结果与图中文字逐字一致（含 `SPDB-2026-PJ-00871`）→ OCR 分支真实生效且中文识别正确。
- **表格未降级为纯文本**：`metadata.type=table`、markdown 管道表格、行列完整、带单元格坐标；表格摘要走 LLM 生成 `table_summary`（只进索引，不进 `/parse_without_indexing` 返回体，属上游设计）。

---

## 7. 定位能力矩阵（供索引/前端引用定位参考）

| 来源 | page_number | position(bbox) | page_size | offset 语义 |
|---|---|---|---|---|
| 数字 PDF / 扫描 PDF / 图片 | ✔ 页号 | ✔ 每块多组 bbox | ✔ 页像素尺寸 | 拼接原文的字符区间 |
| DOCX 正文段 | 字段存在但恒 `[0]` | ✘ 全 0 | ✘ `[0,0]` | 字符区间 |
| DOCX / XLSX 表格块 | ✘ 空 | ✘ 空 | ✘ 空 | **单元格坐标** `[[row,col],…]` |
| PPTX | 字段存在但恒 `[0]` | ✘ 全 0 | ✘ `[0,0]` | 字符区间 |

结论：PDF/图片可达行级定位（bbox+页码）；Office 类（docx/xlsx/pptx）无版式坐标，只能字符区间/单元格坐标。此结论源自上游实现，非本次降级。

---

## 8. 缺失 / 降级能力（按 TL 决定④⑤⑥标注）

**① DOCX 内嵌图片：结构已通过（正文块+图片块都在），但发现真实缺陷 D-1（TL 决定③已满足"重跑并给证据"，内容质量未达标）**

C08 用本机 VLM `18093` 重跑结果（`logs/parse/cases/c08-vlm/C08-docx-image.docx.json`，HTTP 200，**505.92s**）：

| chunk | type | page_content | 定位字段 |
|---|---|---|---|
| [0] | text | `DOCX with image下面内嵌一张图片。`（正文，24 字） | offset `[[0,24]]`，page_number `[0]`，position 全 0 |
| [1] | **image** | `图片中包含了一张扫描的文档图片，图片上没有文字信息。`（26 字） | offset `[[26,26]]`（零长）、page_number `[]`、position `[]`；`is_parsed=True`、`boxes=16` |

→ "正文 + 图片块都在"**成立**；`multi_modal_process` 不再 500。

**但图片块的文字是错的，且比 OCR 更差 —— 缺陷 D-1（根因已定位、可复现）**：
- 同一张图（`word/media/image1.png`，1240×1754）直连 18093 提问"逐字读出文字"，**能正确读出** `SCANNED PAGE - no text layer / line 1 of a scanned document image / …`（17–19s）；OCR 也抽出过 347 字。
- 我按链路真实 prompt 复刻两次调用，逐字定位根因：
  - 第一轮 prompt（`PROMPT_TEMPLATE`(OCR 文本) + `QUERY`）→ 输出**正确**（"图片中的文字内容如下：SCANNED PAGE - no text layer…"）
  - 第二轮 prompt（把第一轮输出当成"图片内文字内容"再问）→ 输出 **`图片中包含了一张扫描的文档图片，图片上没有文字信息。`** ← **与最终 chunk 逐字一致**
- 结论：**根因是 `parse()` 里"二次多模态处理"把上一轮 VLM 输出当作输入再问一遍，自我退化后用错答案覆盖**（不是模型能力问题，也**不是** `data:image/jpeg` 硬编码导致——我把同一 PNG 分别按 `image/png` 与 `image/jpeg` 声明，两次都能正确读出文字，llama.cpp 按字节嗅探）。
- 附带损失：图片块 `page_content` 被 VLM 输出**覆盖**，OCR 的 347 字文字丢失（只剩 26 字描述）。
- 建议修法（属代码改动，**本轮未修，需 CR**）：①二次多模态处理做成幂等（跳过已有 VLM 产出的图片）；②图片块内容改为"OCR 文本 ∪ VLM 描述"合并而非覆盖；③若保留二次处理，第二轮 prompt 不得把首轮输出当作"图片内文字内容"。
- 另注：**18092 是纯文本模型，绝不可用于此路径**（会胡编）；本路径只认 `18093`。

**多图实测补充（16384 下 2 图 / 3 图）：我方链路的质量损失来自 D-1 二次覆盖，不是模型多图拼接**
| 文档 | 图片块质量 |
|---|---|
| `docx-2images.docx`（2 图） | 1/2 **逐字正确**（506 字，含 `SCANNED PAGE - no text layer` 与全部 line）；1/2 为简短概述（正确但信息量低） |
| `docx-3images.docx`（3 图） | 1/3 **逐字正确**（567 字，含两行标题）；1/3 概述有内容；1/3 **退化为空泛改写**（`第一行：扫描文档图像中的第1行…`，实际信息基本丢失） |

**归因（重要，已排除两个错误方向）**：
- **不是模型多图拼接导致的**：我方 `multi_modal_process` **本来就是"一图一请求"** —— 代码 `server/controller.py:186-189` 每次只塞 `MultiModalMessage(type="image", content=base64.b64decode(单张图))`；实测日志也印证：3 图文档产生 **3 次独立 chat 调用**（03:45:02.882/884/885 三条，第二轮 3 条在 03:47:43.68x）。
- **不是 max_tokens 截断**：model-ops 用 `max_tokens=1024` 复测，`finish=stop` 且输出仅 57 token，预算充足。
- **是我方 D-1（二次多模态覆盖）**：我已用同一张图做 A/B —— 第一轮 prompt（OCR 文本 + QUERY）输出**正确**；第二轮 prompt（把首轮输出当"图片内文字内容"再问）输出退化为"没有文字信息"式回答。逐图质量参差正是"第二轮以首轮结果为输入"的后果。

**模型侧真实边界（model-ops 决定性证据，我方代码未触碰，但必须写成红线）**：
- **3 图单请求**（`prompt=8387`、`max_tokens=1024`、`finish=stop`）→ 输出仅 **57 token**：**①英文页 140 token 的内容整图丢失；②凭空虚构"扫描页副本 3：客户 3 日均存款 123 万"**（该图不存在）。
- **2 图单请求**（英文页 + 中文页，`prompt=5581`、`max_tokens=256`）→ 输出 131 token **只含英文行**，中文页 `扫描页副本 1：客户 1 日均存款 137 万` **整段消失**。
- **单图单请求**：3/3 全部逐字正确（含英文页 140 token 全 14 行）。
- **性质判定：不是"改写/漂移"，是"整图丢失 + 按模式补全虚构"**；`finish=stop` 且输出远未触顶 ⇒ **排除 max_tokens 截断**，也排除"随机性"。
- **为什么这个区别决定实现取舍**：若只是"输出不稳定"，可以用重试/多票投票修；但"整图丢失+虚构"是**确定性**的（每次稳定丢掉同一张并补一条假的），**重试无效** → **唯一解是一图一请求**。
→ 红线：**逐字转录/证据提取必须一图一请求**；多图拼接只能用于整体摘要/分类，其结果绝不能当文本源；**不得用重试/投票掩盖**。
（我方现状：`multi_modal_process` **已是一图一请求**，未违反该红线；我方 2 图样本两块都有产出（1 块逐字、1 块概述），不构成"丢图"证据 —— 见下条归因。）

**改造前基线（我今天实测，用于验收对比）**：把 `multi_model_info.url` 指向关闭端口（127.0.0.1:18100）→ `docx-image.docx` **HTTP 500，0.37s**，栈为 `ModelRequestInternalError: 多模态模型请求失败…Connection refused`。即**当前 VLM 是硬依赖**。model-ops 明确提醒：**18093 属契约外端口，TL 若不批他会撤服务** → 因此 D-1 必须做到"**VLM 不可用时自动降级为纯 OCR**"（见 §15.1 验收判据 4）。

结论：图片块文本必须 `OCR（覆盖稳、带 bbox、有噪声）+ VLM（单图、精确）` 并存，且 **VLM 不得覆盖 OCR 已有正确文本**；同时 **D-1 的二次处理必须去掉/幂等化**，否则再准的单图结果也会被第二轮污染。
另：所有图片块均**无定位字段**（offset 零长、page_number/position 空），即使 `metadata.boxes` 有 OCR 框；若要图片级溯源，需在 D-1 修复时一并补。

**② PPTX 图片通路 = R12 已知限制（本轮不立项，R13 清单，TL 决定④）**
`server/controller.py:451` 硬编码 `is_ppt = False # ppt解析存在bug，先关掉等优化好打开`，故 pptx 只出文字块、**不产出图片块**，position/page_size 全 0。图片内容与位置不可得，属真实降级，原因在上游代码，未擅自改动。PPTX 文本链路正常（C10 PASS）。

**③ `.doc`（老 Word）= R12 已知限制（本轮不立项，R13 清单，TL 决定④）**
`DOCParser` 走 tika REST，需要 `tika-server.jar`（约 50MB），本环境无稳定来源，未获取。`.docx/.xlsx/.pptx/.pdf/.png` 均不依赖它。若 R12 必须支持 `.doc`，需 TL 提供 jar 或改 tika 容器服务。

**④ 加密 PDF：错误码有、原因文本缺（记缺陷，不修，TL 决定⑥）**
返回体：`success=false`、`task_statuses[0].code=1100` ✔、`fail_reason=""`（空字符串）✘。定位：`pdf_parser` 抛出的异常 message 为空，`loader.py:456` 直接 `FileParseFailedError(str(e))`。**错误码可用于前端分类，但缺人可读原因**，建议 R13 补异常文案（不阻塞本任务）。

**⑤ 两处仍未确定、我**没有编造**的 URL（阻塞 B 项）**
`server/indexing_utils.py` 的 `es-insert` / `milvus-insert` 只做 `.format(ip=…, port=…)`，路径必须写死在模板里。当前不知道两个接口的**路径**，也不知道该指 **ES/Milvus 本体（19200/19630）** 还是 **代理服务（`index_fulltext_service` 19527 / `index_vector_service` 19526）** —— 契约里两组端口并存，逻辑上 `{index_name, document_list}` 这类业务 JSON 应由代理接收。**需 TL 给出口径与路径**（详见 `platform/r12/nacos/README-parse-configs.md` §4），我给完 5 分钟内补进配置并跑 B 项。
另：`/parse`（带索引）还要求 index_* 服务可用；ES 19200 当前未监听。

**⑥ 其它未验证接口**：`/parse/ocr`、`/parse/revise_date`、`/parse/multi_version`、`/indicator_*`、`/parse/database_desc` 未做端到端验证（不在本次验收范围）。

**⑨ 缺陷 D-2：多图文档的上下文水位风险（服务端已加余量，调用侧仍不可控）**

失败与恢复的完整两段实测（同一批 fixture，A4 整页扫描页 1240×1754 ≈2728 image token/张）：

| 18093 ctx | 场景 | 合计 prompt | 占 ctx | 结果 |
|---|---|---|---|---|
| 8192 | 2 图 | ~5804 | ~71% | ❌ **HTTP 500**，191.47s（`failed to process mtmd chunk`，task 938/1037） |
| 8192 | 3 图 | ~8322 | >100% | ❌ **HTTP 500**，290.40s |
| **16384** | **2 图** | ~5581–5804 | ~34% | ✅ **200**，675.65s，chunk = text×1 + **image×2** |
| **16384** | **3 图** | ~8355 | ~51% | ✅ **200**，526.96s，chunk = text×1 + **image×3** |

model-ops 补充的服务端证据（解释了我为什么在 71% 挂、他在 68% 偶尔能过）：
```
W decode: failed to find a memory slot for batch of size 2
W srv decode: failed to find free space in the KV cache, retrying with smaller batch size …
```
失败三态分界：**≤60% 正常 / ~68% 出 KV 警告但可能成功 / ~71% mtmd 硬 500 / >100% `Context size is exceeded`**。

结论（更新后）：
- **不再把"多图文档必然 500"当作当日阻断**：16384 下 2/3 图均通过（本报告已更新实测）。但这是**靠服务端加内存换来的**（RSS 2.6G→3.9G），**不是调用侧修好了**。
- **缺陷仍在（降级为高风险 + 缺降级）**：①`multi_modal_process` 仍用 `run_in_thread_pool(max_workers=None)` → 默认线程池最多 32，**N 图文档会同时发 N 个请求，水位不可控**；②**单图/单请求失败仍整篇 500**，没有"返回正文 + 标注失败图片"的降级；③水位安全线依赖服务端 ctx，R12 换模型/改 ctx 就会再现。
- CR 建议（**本轮仍未改代码**）：①加 `multi_modal_max_workers` 配置（**默认 1**；实测并发无吞吐收益，1.08×，但单请求内含 2–3 图是安全的，可允许）；②单图失败降级，不得整篇失败；③按 `ctx ≤60%` 水位做准入（`Σ(prompt+max_tokens) ≤ 0.6×ctx`）。

**服务端槽位模型已变更（model-ops 2026-10-25 04:35，需按此理解 D-2）**：
- 旧：`n_slots=4 + kv_unified=true` → **4 槽共享 16384**，71% 占用即 `failed to process mtmd chunk`；
- **新：`--parallel 2 --ctx-size 32768`** → **2 槽、每槽私有 16384**（日志 `n_slots = 2, n_ctx_slot = 16384, kv_unified = 'false'`），RSS 起步 4.5G（旧配置多图后峰值 7.7G）；
- model-ops 实测 4 个并发请求全部 200、零 mtmd/KV 错误（c0 716.9s / c1 405.7s / c2 259.7s / c3 574.4s，墙钟 716.9s），**第 3、4 个请求排队而非报错**。
- 因此 D-2 的措辞修正为：**并发不再导致整篇 500，而是"排队 + 延迟线性拉长"**；500 现在只会在**单个请求自身超 16384** 时发生（`Context size has been exceeded`）。
- **但并发上限仍然要加**，理由从"防 500"改为"**防排队长尾 + 防 worker 线程被拖死**"（叠加 D-3 无 timeout 时就是永久阻塞）——结论不变：默认 1。
- 单请求可用上限：1 图 2802 ✅ / 2 图 5581 ✅ / 3 图 8355 ✅ / 4 图约 11000（67%，不推荐）。

**⑦ `use_multi_modal=false` 的含义**：只关掉 `load_files` 里"对文档内图片再做一次 OCR/VLM"的开关；PDF/PNG 的 OCR 由 parser 自身完成，不受影响（已由 C03/C04/C05 证明）。文档内图片若需要 VLM 摘要，须 `use_multi_modal=true` + VLM 可用。

---

## 9. LLM 依赖（本机 18092 已自证；18093 VLM 待就绪）

解析链路两条强 LLM 依赖：
- **表格切分**：`deepdoc/splitter/table_utils/table_index.py:summarize_table()` → `llm_chat()`，OpenAI 兼容 `/v1/chat/completions`，每张表一次；失败使整篇 500（`TableSplitter` 中 `table_chunk_summary=True` 硬编码，无开关）。
- **文档内图片**：`multi_modal_process()` → 需**多模态**模型（消息体含 `image_url` base64）。

### 9.1 本机端点事实（我实测，2026-10-25）

| 项 | 结论 |
|---|---|
| 端点 | `http://127.0.0.1:18092/v1/chat/completions`（**纯文本**，Qwen2.5-7B-Instruct，llama.cpp/llama-server） |
| 可用性 | `GET /health` → `{"status":"ok"}`；`GET /v1/models` → `qwen2.5-7b-instruct`；对话实测返回中文且合理（`prompt_tokens=53`、`completion_tokens=30`、首 token 45ms） |
| 鉴权 | **无鉴权**。`ModelInfo.key` 留空即可（带任意 `Authorization` 也不校验） |
| 地址写法 | 必须 `127.0.0.1`，**不能用 `[::1]`**（只绑 IPv4 回环） |
| **不能做的事** | **不能用 18092 跑 `multi_modal_process()`**——它没有视觉能力，会返回胡编的图片描述（比报错更糟）。文档内图片必须等 `18093`（Qwen2.5-VL-3B） |
| VLM 端点 | `http://127.0.0.1:18093/v1/chat/completions`（OpenAI 兼容 `image_url` + base64 data URL），**写此报告时尚未监听**；属 R12 契约（18090/18091/18092）之外的新增端口，model-ops 已报 TL 审批 |

### 9.1.1 VLM 端点（18093）实测事实

| 项 | 结论 |
|---|---|
| 端点/模型 | `http://127.0.0.1:18093/v1/chat/completions`，model 填 `qwen2.5-vl-3b-instruct`（Qwen2.5-VL-3B Q4_K_M + mmproj-f16，llama.cpp mtmd），无 key，仅 127.0.0.1 |
| 能力（我实测） | 对 `docx-image.docx` 内嵌原图（1240×1754 PNG）提问「逐字读出文字」→ **全部正确**（`SCANNED PAGE - no text layer` / `line 1..5 of a scanned document image`），17–19s（低负载） |
| 与 mime 无关 | 同一 PNG 分别按 `data:image/png` 与 `data:image/jpeg` 声明，两次都正确 → `MultiModalClient` 硬编码 `image/jpeg` **不是**问题（llama.cpp 按字节嗅探） |
| 负载敏感度 | 机器 load ≈ 25（20 核）时，服务端单次 prompt eval 81.6s、生成 **0.28 tok/s**；同图低负载下正常。model-ops 报的 16–38s 属低负载值 |
| 必须遵守 | ①客户端超时 **≥120s**（解析代码 `requests.post` **无 timeout**，靠客户端兜）；②图片并发 **≤2**（与 embedding/rerank 共享 20 核）；③prompt 里带列名/客户名，指向具体字段更准 |
| 我已做的配置加固 | `alg_doc_config_py.online_multi_modal_model.qwen2.5-vl-3b-instruct.output_max_tokens = 256`（`MultiModalClient` 默认 **4096**；高负载 0.28 tok/s 下 4096 token 要等数小时，必须收紧） |

**图片分辨率 vs 准确率（我实测，重要反直觉结论）**

model-ops 给的拟合公式 `image_tokens ≈ (W/28) × (H/28)`，并建议"送进模型前把长边压到 ≤1024"。我用 `docx-image.docx` 的内嵌原图（1240×1754，整页小字扫描件）实测，**压到 1024 反而读不出文字**：

| 送入尺寸 | 预估 image tokens | 首次耗时 | 是否读出图中文字（`SCANNED PAGE - no text layer…`） |
|---|---|---|---|
| **1240×1754（原始）** | 2774 | 215.4s | ✅ 正确 |
| 723×1024（长边 1024） | 944 | 38.1s；重复请求 0.7–9.6s（prompt 命中缓存） | ❌ **三次全为 `NO_TEXT`** |
| 542×768（长边 768） | 531 | 237.6s | ⚠ 只读出正文行，**漏掉页眉 `SCANNED PAGE`** |

结论（供 R12/R13 决策，勿盲目照搬"压缩到 1024"）：
1. **小字扫描件不能按长边压缩**：本样本原尺寸能读、1024 档读不出、768 档丢页眉。降采样的收益（token/延迟）与代价（文字可读性）必须**按文档类型分别标定**。
2. 本链路当前**不做任何缩放**，直接送原图 → 优点是"能读"，代价是 image token 高（本样本 2774）→ 单图在负载下 100–250s。
3. 若 R12 要控延迟，正确做法不是"一刀切压到 1024"，而是：**先按 `min(短边)` 或字号估计判断是否小字件**，小字件保持原分辨率；大图/照片类可压到 1024。这需要 CR 才能加进链路（且需真实扫描件集标定）。
4. 另注：重复相同请求会被 llama-server prompt cache 命中（0.7–9.6s），**评估延迟必须用不同图片**，否则会严重低估。

**model-ops 独立复验（合成图，结论与我的真实扫描件不同，属素材差异；其"漏页眉"部分已确认为输出截断，见下）**：他用合成 A4 小字页（13px 无噪声）测——原始 1240×1754（2802 token）正文全读对（456.8s）；缩到 723×1024（992 token）**仍读对**（91.1s）。与我的真实扫描件（1024 → `NO_TEXT`）**不矛盾**，说明：
- 可读性由「**有效字形像素高度 + 扫描噪声**」决定，**合成图不能替代真实扫描件**；**不存在通用长边阈值**，必须在真实扫描件集上标定。
- ~~页眉/页脚是稳定盲区~~ **【已更正，此前判断错误】**：我最初据"768 档漏页眉 + model-ops 合成图漏页眉"写过"VLM 页眉盲区、与分辨率无关"，**这条已撤回**。原分辨率下 VLM **能逐字读对页眉**：我定向提问"页面最上方正文之前那一行英文是什么"→ `SCANNED PAGE - no text layer`（finish=stop）；model-ops 在 `docx-image.docx` 上独立复验同样逐字正确（286.8s）。他此前在合成图上"漏页眉"的真实原因是**输出预算耗尽**（`max_tokens=220` 被正文抄写打满，末尾只剩半句 `Th`），不是看不清；我的 768 档漏页眉则是**降分辨率导致小字丢失**。
- 由此得到的正确分工（替代原结论）：**OCR 负责覆盖度与定位（快、有 bbox、有噪声，如 `SCANNED PAGE-notex layene…`）；VLM 负责精确转录（慢、贵，但同一行字更干净）**。两者**互补**，所以 D-1 仍应改成"OCR ∪ VLM 并存"，其中 **VLM 只补充、不得覆盖 OCR 已有的正确文本**（依据：①单图单请求逐字正确率高，但**多图拼进一个请求会整图丢失+虚构**，故 VLM 只能单图；②我方二次多模态覆盖会污染单图结果 —— 两者都见 §8-①）。

**TL 决定⑤的历史执行情况**：18092 就绪前，为不留"链路未验证"的黑洞，曾用真实外部 LLM（DeepSeek `deepseek-chat`，请求体 `model_info` 传入、样本全为自造合成数据）一次性跑通表格摘要；该记录**未写入任何 Nacos 配置**（`platform/r12/nacos/*.yaml` 中无任何 key），且当时已声明不构成 R12 通过证据。**现已被本机 18092 自证取代**（C07 2.83s / C09 6.28s，均 HTTP 200 且表格块完整）。

### 9.1.2 VLM 并发与 token 预算（model-ops 实测 + 我的反证）

model-ops 给出的约束模型（18093：`n_ctx_slot=8192 + kv_unified=true`，即 **8192 是 4 槽共享总池**）：

| model-ops 场景 | 合计 prompt tokens | 实测 |
|---|---|---|
| 4 并发 × 508（4 张不同小图） | 2032 | 全 200，答案与串行一致；总 37.8s vs 串行 88.9s（并发 2.35× 更快） |
| 2 并发 × 2513（2048×956） | 5026 | 全 200，各 184.6s，答案正确 |
| 2 并发 × 4489 | 8978 > 8192 | **两个请求同时 500**（`Context size has been exceeded`），**连带打挂同批另一个** |

预算公式：`Σ(prompt_tokens + max_tokens) ≤ 8192`；`N = floor((8192 - 512 - max_tokens) / 每图 token)`；`image_tokens ≈ (W/28)×(H/28)`。
关键性质（对解析服务很致命）：**超预算不是静默截断，而是硬 500，且会连累同批请求** —— 而本服务 LLM 失败是异常冒泡 → 整篇解析 500。

**model-ops 后续自我更正（2026-10-25，与我的结论一致）**：
- 他先前"4 并发比串行快 2.35×"是**踩了 prompt cache**（那 4 张图串行阶段已被编码，并发阶段命中"相同图片+相同 prompt 前缀"缓存，3 个请求 3.1s 返回）。**干净实验（8 张全新图、各 ~515 token）**：串行 4 张共 **94.9s**（单张 19.8–32.5s）；并发 4 张共 **87.7s**，但**每个请求都要等 87.7s** → **加速比仅 1.08×，单请求延迟放大 4 倍**。
- 结论更正为：**纯 CPU 的 VLM 是算力受限，并发不换吞吐 → 并发应取 1**。这与我的 D-2 实验（2 并发直接 mtmd 失败）方向一致，两条独立证据共同支持"**默认并发 1**"。
- 缓存陷阱同时被双方复现（我：首次 38.1s / 重复 0.7s、9.6s；他：2.0s / 111.5s）→ **延迟只能按首次请求、且每次换新图测量**。

**服务端 final 参数（2026-10-25 03:20，model-ops 已重启 18093）**：`n_ctx = 16384`（原 8192），RSS 2.6G→3.9G（纯 RAM）；`verify_vl.py` 回归全 PASS。他给出的**安全水位**：`Σ(prompt + max_tokens) ≤ 0.6 × ctx`；失败三态 **≤60% 正常 / ~68% KV 警告但可能成功 / ~71% mtmd 硬 500 / >100% `Context size is exceeded`**；按 60% 水位反推 T≈2728（整页扫描件）时 **N≤3**、T≈1000 时 N≤8（受 n_slots=4 限制为 4）。我据此在 §8-⑨ 复测 2/3 图均通过。
注意：**并发对吞吐仍无收益（1.08×）**，所以运行时并发建议仍是 1；有价值的是"**单请求内含 2–3 图**"（KV 连续，比多请求碎片化安全）——这恰好也是解析服务的自然形态（一个文档的图在同一请求内），但需要调用侧显式控并发，不能靠默认 32 线程池。

**我的反证（重要）**：model-ops 最初建议"不要限 1，限 2"，并建议"更优解是压到 ≤1024"。这两条在 A4 整页扫描件上都不成立（他随后已撤回）：
- **限 2 也会失败**：2 张 1240×1754（约 2700 token/张，合计 5400 + 256 < 8192，**未超预算**）仍然 500，VLM 报 `failed to process mtmd chunk, res = -1`。→ 瓶颈是 **mtmd 图像编码并发**，先于 token 预算触发；安全并发取决于单图 token 数，A4 扫描件目前只有**串行（1）**可靠。
- **压到 1024 会读不出字**：见 §9.1.1 分辨率实验（3/3 次 `NO_TEXT`）。→ 降采样只能按文档类型分流，不能一刀切。

### 9.2 容量约束实测（model-ops 提示的截断风险，已量化）

`llm_chat` 里 `max_tokens=1000` 是**硬编码**，`summarize_table` 对表格内容在 **5000 字符**处截断（`len(table_content) >= 5000` → 截断 + `...`）。我按代码原样构造 prompt 并送 18092 实测 token 数：

| 送入表格字符数 | prompt_tokens | 备注 |
|---|---|---|
| 258（本次 xlsx 实测量级） | **470** | 固定开销约 350（system prompt） |
| 1500 | 1413 | |
| 3000 | 2552 | |
| **5000（代码上限）** | **4069** | 单请求几近吃满 4096 共享上下文 |

推论与处置：
1. 18092 当前 `--ctx-size 4096` 且 **4 个并发槽共享**该预算 → 单请求 prompt 4069 就会挤掉其它槽，且**超出部分被静默截断（不报错）**，摘要会变差但不报错。
2. 触发条件已核实：小表（<1000 字符）与**规则大表**（代码只对前 9 行 `row_range=(0,8)` 做摘要）prompt 都很小；**真正的风险面是"不规则大表"走 `compress_table` 后送 5000 字符**，以及被并发放大的整体预算占用。
3. 我已把 `table_split_max_worker` 由 2 → **1**（配置变更，已发布、watcher 热生效），避免同一文档内多表并发摘要互相挤占；解析服务侧无法控制跨请求并发，需 model-ops 侧兜底。
4. **model-ops 已把 18092 ctx 由 4096 提到 8192**；我复测同一 5000 字符表：`prompt_tokens=4066` 被正常受理、无截断。4066 + 1000 ≈ 5066 < 8192 → 单请求安全；`table_split_max_worker=1` 进一步避免同请求内并发。
5. 若 R12 需处理超大不规则表，两个硬编码（5000 字符 / max_tokens=1000）应改为可配置项——**属代码改动，需 CR**，本轮未动。

### 9.3 大表端到端验证（我造 40 行 × 8 列 xlsx）

`big-table.xlsx`（40 行 × 8 列，总计 4229 字符）→ HTTP 200、**3.71s**、**14 个 table chunk**（每块 307–313 字符，表头在每块重复，末块 179 字符），无 500、无内容丢失。说明规则大表走"按行切分 + 表头重复"路径，摘要用前 9 行，ctx 压力可控。

---

## 10. 自愈记录（真实踩坑 → 处置）

| # | 现象 | 根因 | 处置 |
|---|---|---|---|
| ① | 启动即崩 `KeyError: 'layout_garbage_path'` | Nacos 配置缺键（`pdf_parser.py:50` 必读） | 补键并重发，Nacos watcher 热生效 |
| ② | 解析 PDF 抛 `IndexError`（recognizer.py:428） | 主分支 layout.onnx 为新导出格式 `[1,300,6]` | 回退 2024-03 版（§4.1），新版留档 `.bak` |
| ③ | docx-table `HTTP 500` | `controller.py:532` 取 `page_number[0]`，表格块该字段为空列表 | **R12-FIX-PARSE-01**（§5，TL 已接受） |
| ④ | import 期 `XGBoostError: Opening deepdoc/splitter/xg_splitter.json failed` | 该模型用相对路径，cwd 不对 | 规定 cwd=服务目录 |
| ⑤ | import 期 `ModuleNotFoundError: alibabacloud_docmind_api20220711` | `ali_parser` 无条件 import | 补装 SDK |
| ⑥ | `unzip: End-of-central-directory signature not found`（omw-1.4） | jsdelivr 上该包 404 | 记录影响（非英文词形还原），不阻塞 |
| ⑦ | MySQL 建表 `1064 syntax error near ')'` | 我拼的 DDL 列表末尾多逗号 | 修生成脚本重发；`CREATE TABLE IF NOT EXISTS` 幂等 |
| ⑧ | 新增 `other-nacos`（java-gateway/index）后未生效 | watcher 只回写被改的 data_id，`other-nacos` 增删在启动期解析 | 重启服务（pid 已更新，health=200） |

---

## 11. 性能（单文件，模型已预热，CPU）

| 样本 | 耗时 |
|---|---|
| 数字版 PDF（1 页） | 0.31–1.04s |
| 扫描版 PDF（1 页，含 OCR） | 0.47–0.54s |
| 中文图片（1000×420，OCR） | 0.30–0.41s |
| DOCX 纯文本 | 0.07–0.08s |
| DOCX 含表格（+1 次本机 LLM 摘要） | 2.83s |
| XLSX（1 表 5 行，+1 次本机 LLM 摘要） | 6.28s（≈256 completion token @ 44 tok/s） |
| XLSX 大表（40 行 × 8 列 → 14 table chunk） | 3.71–3.96s |
| **DOCX 内嵌图片（单图，含 2 次 VLM 调用，load≈25）** | **505.92s**（服务端单次 VLM 100–250s；低负载同图仅 17–19s） |
| DOCX 含 2 张整页扫描图 | 8192 ctx：❌ 191.47s 后 500 → **16384 ctx：✅ 675.65s**（text×1 + image×2） |
| DOCX 含 3 张整页扫描图 | 8192 ctx：❌ 290.40s 后 500 → **16384 ctx：✅ 526.96s**（text×1 + image×3） |
| PPTX（2 页文字） | 0.04–0.08s |
| 双文件同请求 | 0.77–1.07s |

> 含 LLM 摘要的耗时主要由本机 LLM 生成速度决定（实测 44 tok/s，`max_tokens=1000` 上限、实际输出约 200–300 token），不是解析本身慢；PDF/DOCX 纯文本与 OCR 链路均在 1s 内。

- 首次请求额外 **6–8s**（OCR/layout/tsr/updown 模型加载，`ocr_pool` 进程内缓存，约 150MB 常驻；进程 RSS ≈ 1.1GB）。
- 冷启动到 `/docs` 可访问：**约 18–20s**（Nacos 拉取 + MySQL 建表 + import）。

---

## 12. C 项交付：可重跑回归脚本

路径：`platform/r12/parse/fixtures/`

| 文件 | 作用 |
|---|---|
| `run-parse-cases.sh` | **入口**。健康检查（服务未起直接 `exit 2`，避免误判）+ venv 依赖自检 + 调 python 执行 12 用例 |
| `parse_cases.py` | 样本清单/来源、生成逻辑、MinIO 上传、HTTP 调用、**逐用例断言**、结果落盘 |
| `generated/` | 生成的样本（png/xlsx/pptx/cn-digital.pdf/cn-scan.pdf，首次运行自动生成） |

- 样本来源在 `SAMPLES` 里标注 `sample`（TL 提供 6 个，从 `/home/szf/data/dev/coordination/samples` 复制）或 `gen`（脚本生成 5 个）。
- 断言在 `CASES` 里显式声明：`http_200` / `chunks_gt_0` / `has_type_text|table` / `contains_chinese` / `locator_present`（offset 或 page_number 或 position 非全 0）/ `table_is_markdown` / `table_contains_*` / `ocr_contains_*` / 负例 `business_flagged_failure + error_code_expected`。
- 实际输出落盘：`platform/r12/logs/parse/cases/<UTC 时间戳>/`（每用例原始响应 `<Cxx>-<file>.json` + `result.json` + `summary.md`）。`CASES_OUTDIR` 可覆盖。
- LLM/VLM 缺失时按 `BLOCKED_FOR_LLM` / `BLOCKED_FOR_MM` 分类，**不计 PASS**；退出码仅在有 FAIL 时为 1。
- **图片块数廉价断言**：凡带 `expect_image_chunks` 的用例，断言 `type==image` 的 chunk 数 **== 输入图片数**（model-ops 建议）。少一条 = "拼接丢图"类（红线，我方一图一请求天然不触发）；条数对但文字变糙 = "覆盖退化"（D-1）。
- **多图用例 C14/C15**（`docx-2images` / `docx-3images`，默认跳过，加 `--with-vlm-heavy` 才跑；单次 500–700s、VLM RSS 峰值 7.7G，**必须串行**）。
- **附加大表压力用例 C13**（默认跳过，加 `--with-stress` 才跑）：40 行 × 8 列 xlsx → 断言 14 个 table chunk、表头关键词存在；实测 `PASS 3.96s / 14 chunks`。

**自测结果（三次，已落盘）**
- 无 LLM 环境：`PASS=9 FAIL=0 BLOCKED=3`（C07/C08/C09）→ `logs/parse/cases/20261024T174456Z/`
- 带外部 LLM（一次性验证，已作废）：`PASS=11 FAIL=0 BLOCKED=1` → `logs/parse/cases/20261024T174507Z/`
- **带本机 18092（R12 自证，有效）**：`PASS=11 FAIL=0 BLOCKED=1`（C08 等 VLM 18093）→ `logs/parse/cases/20261024T180221Z/`
  - 复现命令：`LLM_URL=http://127.0.0.1:18092/v1/chat/completions LLM_MODEL=qwen2.5-7b-instruct ./run-parse-cases.sh --skip-upload`
  - 本机 LLM 实测耗时：C07 2.83s、C09 4.90–6.28s（其余用例 ≤1.07s）
- **带本机 18092 + 附加大表用例**：`PASS=12 FAIL=0 BLOCKED=1`（C13 大表 14 chunk / 3.96s）→ `logs/parse/cases/20261024T180422Z/`
  - 复现：`... ./run-parse-cases.sh --skip-upload --with-stress`
- **带本机 18092 + 18093（全绿）**：`PASS=12 FAIL=0 BLOCKED=0`（C08 505.92s，正文块+图片块都在）→ `logs/parse/cases/c08-vlm/`
  - 复现：`LLM_URL=http://127.0.0.1:18092/v1/chat/completions LLM_MODEL=qwen2.5-7b-instruct MM_URL=http://127.0.0.1:18093/v1/chat/completions MM_MODEL=qwen2.5-vl-3b-instruct ./run-parse-cases.sh --skip-upload`
  - ⚠ C08 的 PASS 只代表「结构与接口链路通」，**图片块文字质量缺陷 D-1 未修**（§8-①），不构成「图片理解可用」的结论

---

## 13. A / B / C 三项状态

| 项 | 状态 | 说明 |
|---|---|---|
| **A** Nacos 配置整理交付 | ✅ 完成 | `platform/r12/nacos/` 4 个 data_id 文件 + `README-parse-configs.md`（含 TL 要求补齐的全部键、取值出处、发布命令）。已按此内容在本机发布并重启验证（health=200） |
| **B** `/parse` 带索引落库 | ✅ 已跑通 | 走代理（19527/19526）；`cn-digital.pdf` → ES 1 / Milvus 1 == chunk 1；`table-ledger.xlsx` → 表摘要与表格块各 1（ES+Milvus）。详见 §16.4 |
| **C** 12 用例固化脚本 | ✅ 完成 | `platform/r12/parse/fixtures/{run-parse-cases.sh,parse_cases.py}`；本机 18092 自测 **11 PASS / 0 FAIL / 1 BLOCKED**（C08 等 VLM）；加 `--with-stress` 为 12 PASS（C13 大表 14 chunk） |
| **G** 超时健壮性（D-3） | ✅ 已修（4 处补 timeout） | 4 处 LLM/VLM/embedding 调用均未传 timeout，`except Timeout` 不可达；端点挂住 → 线程永久阻塞。修法见 §14-10 |
| **F** 多图文档可用性 | ✅ 调用侧已修（并发=1） | 8192 时 2/3 图整篇 500；**16384 后 2 图 200/675.65s、3 图 200/526.96s**。仍缺：并发上限（默认 32 线程池）+ 单图失败降级 |
| **E** VLM(18093) 接入（新增） | ✅ 已修复并验收 | C08 从 500 变 200（正文块+图片块都在），但发现 **D-1**：二次多模态处理以首轮输出为输入 → 自我退化为「没有文字信息」并覆盖 OCR 文本（根因已复现，需 CR） |
| **D** 本机 LLM 接入（新增） | ✅ 完成 | C07/C09 表格摘要已由 `18092` 自证（§9.1）；容量约束实测并已把 `table_split_max_worker` 降为 1（§9.2）；大表端到端 200/14 chunk（§9.3） |

---

## 14. 待办 / 需 TL 决策

1. **【已解除】18092 文本 LLM**：已实测可用，C07/C09 已转本机自证（§9.1）。
2. **【已解除】VLM `18093`**：已就绪并重跑 C08，正文块+图片块都在（证据见 §8-①）。**但发现缺陷 D-1（见第 5 条）**；另 18093 是 R12 契约外新增端口，仍**需 TL 明确批准**（model-ops 已上报 `platform/r12/status/models.md §6.8`）。
3. **【已解除】`es-insert` / `milvus-insert` 与 B 项验收**：按 TL 口径走代理（19527/19526），已用两个真实文件验证 ES+Milvus 双落库且计数与 chunk 数一致（§16.4）。遗留一个待确认项：Milvus 集合名多一个前导 `_`（`_<index_name>`），已向 alg-ops 确认是否刻意约定。
4. **【已解除】ctx 已扩容**：`18092`(LLM) 8192 —— 我复测 5000 字符表 `prompt_tokens=4066` 正常受理无截断（§9.2）；`18093`(VLM) 16384 —— 2/3 图已通过（§8-⑨）。
5. **【已实施 R12-FIX-PARSE-02】缺陷 D-1：图片块被二次多模态处理覆盖**（§8-①，实施与验证见 §16）。**归因已定**：我方本来就是"一图一请求"（代码 + 日志双证），单图单请求 VLM 逐字正确率高（model-ops 3/3），**图片块质量损失的唯一我方原因是"二次多模态处理以首轮输出为输入"**，与多图拼接、max_tokens 都无关。修法：①二次处理幂等化（跳过已有 VLM 产出的图片）或直接去掉；②图片块 `page_content` 改为「OCR 文本 ∪ VLM 描述」合并而非覆盖；③若保留二次处理，第二轮 prompt 不得把首轮输出当作「图片内文字内容」。**修前图片块文字不可信，且会丢掉 OCR 已抽到的文字**。
   ④**调用粒度必须一图一请求 —— 这属 D-1 的修复要求（正确性问题），不放在 D-2 的并发里**：多图单请求会"整图丢失+虚构"，且**重试无效**（确定性行为）。我方现状已满足（代码 + 日志双证），此处是防止 R13 做"多图摘要"时误用。
   另立**红线**（来自 model-ops 决定性证据，我方代码目前不违反）：**逐字转录/证据提取必须一图一请求**；多图拼进同一 VLM 请求会「整图内容丢失 + 虚构条目」（他实测 3 图输出仅 57 token、`finish=stop`，丢失整页并虚构"副本3/客户3/123万"）。R13 若做"多图摘要"，其结果**绝不能当文本源**。
6. **【已实施 R12-FIX-PARSE-03】缺陷 D-2：多图文档水位不可控 + 无降级**（§8-⑨，实施见 §16）。服务端 ctx 提到 16384 后 2/3 图已能过，**但这是加内存换来的**：`multi_modal_process` 仍是默认 32 线程池、失败仍整篇 500。建议：①加 `multi_modal_max_workers`（默认 1，允许单请求内 2–3 图）；②单图失败降级为"返回正文 + 标注 `image_parse_failed`"；③准入按 `Σ(prompt+max_tokens) ≤ 0.6×ctx`。**换模型/改 ctx 即可能再现，不能当已解决。**
7. **【需 CR】两处硬编码**（本轮未动）：`llm_chat` 的 `max_tokens=1000`、`summarize_table` 的 5000 字符截断。若 R12 要支持超大不规则表，应改为可配置项。
8. **【已撤回，改为低优先提示，不需 CR】原"页眉/页脚盲区"结论作废**：原分辨率下 VLM **能逐字读对页眉**（我定向提问实测 `SCANNED PAGE - no text layer`，finish=stop；model-ops 在真实 fixture 上独立复验一致）。此前"漏页眉"的真实原因是：①他的合成图 `max_tokens=220` 被正文抄写**打满导致输出截断**；②我的 768 档**降分辨率**导致小字丢失。
9. **【需 CR，需标定】图片预处理策略**：实测"长边压到 1024"会让小字扫描件读不出文字（§9.1.1 表，3/3 次 NO_TEXT），**不能当无损优化照搬**；当前链路不缩放（能读但单图 2774 image token、负载下 100–250s）。建议按文档类型标定后再决定是否引入缩放。
10. **【已实施 R12-FIX-PARSE-04】缺陷 D-3：所有 LLM/VLM/embedding 调用都没有 timeout**
 实测代码（`requests.post` 全部无 `timeout=` 参数）：`deepdoc/utils.py:72`（表格摘要 `llm_chat`）、`deepdoc/utils.py:99`（`llm_completions`）、`deepdoc/utils.py:152`（`embedding_func`，图片关联用）、`server/multi_modal_utils.py:108`（VLM）。
 后果：任意一个端点挂住（负载高、进程假死、网络半开），对应 worker 线程**永久阻塞**，FastAPI 请求永不返回；`multi_modal_utils.py:109` 的 `except Timeout` **实际不可达**（因为从没传 timeout）。model-ops 建议"客户端超时 ≥600s"，但**客户端根本没有超时**。
 修法（各加一行 + 配置项）：`timeout=config.get('llm_timeout', 300)` / `multi_modal_timeout` 默认 600。
11. **【协作约束】VLM 资源与批量跑测**：18093 在 ctx=16384 下 RSS 起步 3.9G、跑过多图任务峰值 **7.7G**（本机 available 一度只剩 7G）。因此：**图片用例必须串行**（解析侧并发默认置 1）、**不要为压时间开多个解析 worker**、**几十张图的批量跑测前先与 model-ops 打招呼**（他会先清缓存并确认内存）。另：**评估延迟不得用重复请求**（缓存命中会得到 1–10s 假值，双方各自踩过）。
12. `alg_doc_parse_java_common.mysql.schema` 若有正式 DDL，请覆盖；发布时按 `README-parse-configs.md` §5 覆盖同名 data_id。
13. R13 清单立项：PPTX 图片通路修复（上游 `is_ppt=False`）、`.doc` tika 制品、layout.onnx 2026 版 postprocess 适配（§4.1）、加密 PDF 异常文案、缺陷 D-1 修复、缺陷 D-2 修复。

---

## 15. 附录：D-1 / D-2 / D-3 改动草案（**已于 2026-10-25 按 TL 裁定实施，实施记录见 §16**）

> 目的：让 TL 一次看清改动面与风险，批准后我按此实施并回归。所有改动都在 `services/rag-alg/alg_doc_parse_service/**`（我的独占范围），不改接口契约、不改返回体结构（只**新增**可选 metadata 字段）。

### 15.1 D-1（正确性）

| # | 位置 | 改动 | 理由 |
|---|---|---|---|
| 1 | `deepdoc/output_object/image.py` | `ParsedImageMetadata` 新增两个**有默认值**的字段：`ocr_text: str \| None = None`、`vlm_text: str \| None = None`、`vlm_status: Literal['ok','failed','skipped'] \| None = None` | 把"OCR 文本"和"VLM 描述"分开存，才有合并的基础；pydantic 加默认字段对下游兼容 |
| 2 | `server/controller.py:multi_modal_process()` | 入口处 `md.ocr_text = md.ocr_text or image.page_content`（保存 OCR 原文）；调用成功后写 `md.vlm_text = response`；**不再直接 `image.page_content = response`** | 去掉"覆盖"，改为并存 |
| 3 | 同上（合并语义） | 最终 `page_content = "\n\n".join([x for x in (md.ocr_text, md.vlm_text) if x])`；**VLM 文本不得覆盖 OCR 已有内容** | 双方共识：OCR 覆盖稳/有 bbox，VLM 精确但会丢会编 |
| 4 | 同上（幂等） | 进入 worker 前 `if md.vlm_status == 'ok': return` | 去掉"二次多模态处理拿首轮输出再问"的自我退化（**D-1 主因**） |
| 5 | 同上（失败降级） | 单图 VLM 调用包 `try/except`：失败只置 `vlm_status='failed'` + `logger.error`，**不抛异常**；`page_content` 保留 OCR 文本 | 满足"单图失败不得整篇 500"（D-2 的可用性要求，与 D-1 同一处改） |
| 6 | 同上（定位补全） | 若 `md.boxes` 非空：`position = [boxes 的并集四角]`、`page_size = md.image_size`；**page_number 仍留空**（docx 无分页，不编造） | 图片块目前零长 offset/空 position，补"页内 bbox"但不伪造页码 |
| 7 | `server/multi_modal_utils.py:MultiModalClient.chat()` | `requests.post(self.url, json=payload, headers=self.headers, timeout=DocParseConfig().config.get('multi_modal_timeout', 600))` | **当前代码没有 timeout**：`except Timeout` 分支实际**不可达**，VLM 挂住会把工作线程与整篇请求无限期占死。model-ops 要求客户端超时 ≥600s，但客户端根本没传 |
| 8 | 同文件 / controller | 失败按 error kind 打标（见 §15.1.1），而不是统一 `ModelRequestInternalError` | 便于观测、重试策略与验收判定（"不可用"与"超预算"处置不同） |

### 15.1.1 `vlm_status` 分档（依据 model-ops 实测的错误形态清单）

| 客户端观测 | 含义 | `vlm_status` |
|---|---|---|
| `Connection refused`（秒级） | 18093 未运行 | `unavailable` |
| HTTP 500 `{"error":{"code":500,"message":"Context size has been exceeded."}}` | 总 token 超 ctx（**会连累同批**） | `over_budget` |
| HTTP 500 `failed to process mtmd chunk, res = -1` | KV 连续空间不足（并发/大图叠加） | `kv_starved` |
| 客户端超时（我们设 600s） | 首次大图在负载下可能 200–500s | `timeout` |
| 其它 4xx/5xx、返回体格式错误 | 未知异常 | `failed` |
| 正常返回 | — | `ok` |

⚠ 实现要点：前两种都是 **HTTP 500 且返回体是 JSON**，`multi_modal_utils.py:115-120` 已把 `response.text` 拼进异常消息 → 可据此分档；但**字符串匹配脆弱**，建议同时引入结构化 `error_kind` 字段（属 CR 范围内的小改动）。超时是纯客户端侧，服务端不返回，**必须先补 `timeout=`**（见上表第 7 行）才可能产生 `timeout` 档。

回归判据（实施后必须满足）：
- C08 图片块 `page_content` **同时含 OCR 文本与 VLM 文本**，且 OCR 的 347 字不再丢失；
- 同一文档两次解析，图片块文本**一致**（幂等）；
- 图片块 `position` 非空（有 boxes 时），`page_number` 仍为空（如实）；
- 人为让 VLM 不可用（把 `multi_model_info.url` 指向关闭端口，如 18100）→ 请求**仍 200**，正文与 OCR 文本正常返回，图片块 `vlm_status='unavailable'`（按 §15.1.1 分档）。
  **改造前基线：今天实测为 HTTP 500 / 0.37s（硬依赖）**；且 18093 属契约外端口，TL 不批则 service 会被撤 → 这条判据是"能否在 18093 缺席时继续交付"的分水岭。

### 15.2 D-2（并发与水位）

| # | 位置 | 改动 | 理由 |
|---|---|---|---|
| 1 | `server/controller.py:multi_modal_process()` | `run_in_thread_pool(..., max_workers=DocParseConfig().config.get('multi_modal_max_workers', 1))` | 默认 1；配置文件可调，但**不暴露成"32"** |
| 2 | `alg_doc_config_py`（Nacos） | 新增 `multi_modal_max_workers: 1` | 与 §9.1.2 的"并发无吞吐收益、并发≥2 会 mtmd 失败"一致 |
| 3 | `deepdoc/utils.py:72/99/152` | 三处 `requests.post` 补 `timeout=DocParseConfig().config.get('llm_timeout', 300)`（embedding 用 `embedding_timeout`，默认 60） | 与 VLM 同理：无 timeout 会把线程永久占死；见 §14-10 缺陷 D-3 |
| 4 | 准入（可选，需额外代码） | 单图预估 `image_tokens ≈ (W/28)×(H/28)`，`Σ(prompt+max_tokens) ≤ 0.6×ctx` 才提交，否则排队 | 防止大图/多图把 18093 打穿；若 TL 认为过重，可先只做 1+3 两项 |

### 15.3 不做的事（避免越界）
- **不改** VLM 参数（ctx/量化/offload），那是 model-ops 与 TL 的域；
- **不引入图片缩放**（§9.1.1 已证"≤1024"会毁小字件可读性，需真实件标定）；
- **不改** 返回体字段类型、不改现有字段语义（只新增有默认值的 metadata 字段）；
- **不做** 多图拼接（红线，见 §8-①）。

### 15.4 需要 TL 额外拍板的一项（来自 model-ops 建议）
若 D-1/D-2 实施后"一图一请求 + 串行"的吞吐仍不可接受（每张 100–450s 是硬成本；R12 的一个 20 页扫描 docx 可能要 1–2 小时），可考虑**把 7B 的 offload 降下来换 VLM 上 GPU**。这属服务端资源配置，需 TL 决定，我不擅自动。

---

## 16. 实施记录（TL 于 2026-10-25 全部批准后执行）

批准内容：18093 纳入契约（可选增强）、D-1/D-2/D-3 三项 CR、编号统一 `R12-FIX-PARSE-xx`、**不批降低 7B offload**、B 项走代理（19527/19526）。

### 16.1 代码改动清单（全部在我的独占目录内）

| 编号 | 文件:位置 | 改动 |
|---|---|---|
| **R12-FIX-PARSE-01** | `server/controller.py` chunk 排序 | （此前已落地）表格块 `page_number` 为空时兜底为 0，修复 docx 含表格整篇 500 |
| **R12-FIX-PARSE-02** | `deepdoc/output_object/image.py` | `ParsedImageMetadata` 新增 `ocr_text` / `vlm_text` / `vlm_status`（均有默认值，下游兼容） |
| | `server/controller.py:multi_modal_process()` | ①OCR 文本固化为 `ocr_text` 基线；②**VLM 结果不再覆盖**，`page_content = OCR ∪ VLM`；③**幂等**（`vlm_status=='ok'` 直接跳过，消灭"二次处理拿首轮输出再问"的自我退化）；④prompt 的"图片内文字"改取 `ocr_text`（切断反馈污染）；⑤单图失败只打标不抛异常；⑥有 `boxes` 时补页内 `position`，`page_size=image_size`，**`page_number` 不伪造仍为空** |
| **R12-FIX-PARSE-03** | `server/controller.py:multi_modal_process()` | `run_in_thread_pool(..., max_workers=config.get('multi_modal_max_workers', 1))`；配置默认 1 |
| **R12-FIX-PARSE-04** | `server/multi_modal_utils.py` | ①`requests.post(..., timeout=config.get('multi_modal_timeout', 600))`（原**无 timeout**，`except Timeout` 不可达）；②错误分档 `err.kind ∈ {timeout, unavailable, over_budget, kv_starved, failed}`，两种 500 按 body message 区分 |
| | `deepdoc/utils.py:72/101/156` | 补 `llm_timeout`(300) / `embedding_timeout`(60) 三处 timeout |
| **R12-FIX-PARSE-05** | `server/multi_modal_utils.py:chat()` | 增加 `return_meta=True` 时返回 `finish_reason`/`usage`（默认 False，旧调用方不受影响） |
| | `deepdoc/output_object/image.py` + `server/controller.py` | 新增 `vlm_finish_reason` 字段；`finish_reason=='length'` ⇒ `vlm_status='truncated'`（文本不完整，不可当完整转录源）；`output_max_tokens` 由 **256 → 512** |
| | Nacos `alg_doc_config_py` | 新增 `multi_modal_max_workers:1`、`multi_modal_timeout:600`、`llm_timeout:300`、`embedding_timeout:60`、`es-insert`、`milvus-insert`；`other-nacos.index` 改为**引用 alg-ops 的 `index_data_config_py`**（不再重复发布同名 data_id） |

### 16.2 双状态回归（TL 要求：VLM 可用 / VLM 指向关闭端口，后者不得 500）

| 状态 | 结果 | 证据目录 |
|---|---|---|
| **VLM 可用**（18093） | **12 PASS / 0 FAIL / 0 BLOCKED** | `logs/parse/cases/20261024T202339Z/` |
| **VLM 不可用**（multi_model_info.url → 127.0.0.1:18100 关闭端口） | **12 PASS / 0 FAIL / 0 BLOCKED**，**无任何 500** | `logs/parse/cases/20261024T203136Z/` |

**验收判据核对（§15.1 四条全部达成）**
| # | 判据 | 实测 |
|---|---|---|
| 1 | 图片块同时含 OCR 与 VLM，OCR 不丢 | ✅ image chunk `len=892` = `ocr_text 347` + `vlm_text 543`，`vlm_status='ok'` |
| 2 | 幂等（两次解析一致） | ✅ 本次请求 **VLM 调用次数=1**（改造前为 2），"二次多模态处理"耗时 **0.01s**（跳过） |
| 3 | `position` 非空、`page_number` 仍空（不伪造） | ✅ `position=[[26.67,30]…]`、`page_size=[1240,1754]`、`page_number=[]` |
| 4 | **VLM 不可用时仍 200 + 纯 OCR 降级** | ✅ **C08 = HTTP 200 / 1.33s**（改造前 **500 / 0.37s**），`vlm_status='unavailable'`，`ocr_text` 347 字保留、`vlm_text=None` |
| 5 | 超时路径（D-3 新分支） | ✅ 把 `multi_modal_timeout` 临时调成 **2s** → C08 **HTTP 200 / 15.61s**，`vlm_status='timeout'`、`ocr_text` 347 保留、`vlm_text=None`；随后**已恢复 600s**（live 值已核对），正常路径复测 `vlm_status='ok'`、`ocr_text 347 + vlm_text 548 = 897` |
| 6 | **输出截断分档（R12-FIX-PARSE-05）** | ✅ 把 `output_max_tokens` 临时调成 **1** → C08 **HTTP 200 / 27.79s**，`vlm_status='truncated'`、`vlm_finish_reason='length'`、`vlm_len=3`、`ocr_text` 347 保留（合并 352）；随后**已恢复 512**（live 值已核对）。另测 `output_max_tokens=24` 时模型自然 `stop`（输出 37 字）→ 说明"描述型"输出天然短，**截断风险主要出现在"逐字转录型"用法**，故用 `finish_reason` 断言兜底而非无限加大预算 |

### 16.3 C08 单列：质量与容量双维度（按 TL 要求，不并入"12 全 PASS"单一结论）

| 维度 | 结论 |
|---|---|
| **质量** | VLM 可用时图片块 = `OCR 347 字 + VLM 543 字` 并存（不再互相覆盖）；分档 `vlm_status` 可区分 `ok/unavailable/over_budget/kv_starved/timeout/failed`；图片块有页内 `position`，但**无页码**（docx 无分页，如实为空） |
| **容量** | 单图实测：**105.72s**（`20261024T203443Z`）、**115.62s**（VLM 超时恢复后复测）；**VLM 不可用时 1.33s**（纯 OCR）。⚠ **不算配置收益**：348.12s / 505.92s 与 105.72s 的差异来自**测量窗口的机器负载不同**，不是 2 槽私有配置带来的提速 —— 见 §16.5 的权威判据（服务端 `prompt eval` 速率）。配置变更的真实收益只有两条：**消除跨请求 KV 争抢导致的 500（改为排队）** 与 **RSS 7.7G→4.5G** |
| **验收含义** | 质量维度已达 D-1 判据；**容量维度是限制项**：20 页扫描件按 348s/页估算约 **1.9 小时**，不满足交互式解析，需在 R13 容量清单处理（TL 已明确不为此降低 7B offload） |
| **C14/C15 多图容量：仍未取到数（窗口失效，如实记录）** | 05:33 窗口 `load1=10.38 / available=9G` 时启动 **2 图 v2 新样本**（1240×1754 密排、带唯一时间戳编号，**物理上不可能命中 prompt cache**）；期间**邻居 `kb_5/*` 任务与本请求抢占同一 VLM 进程的槽**（prefill 21.1 tok/s 正常、生成降到 **0.73 tok/s**，非机器慢 —— 根因见 **§16.9-1**）（单图 eval 374.6s/276 token），请求 20 分钟未完成被客户端中止 → **无有效数据**。v2 样本（`docx-2images-v2.docx` / `docx-3images-v2.docx`）与取数口径（`cache_n ≤5%×prompt_n`）已就绪，等**专属低负载窗口**（load1≲10 且无其它角色压测）再测。 |
| **口径注记** | 348.12s = 旧共享池配置；**105.72s = 新配置（2 槽 × 私有 16384）**，两者都非"最优值"。**load1 > 15 时 VLM 会退到 0.18 tok/s（model-ops 实测）**，此时耗时不具代表性 → 回归脚本已加 `--max-load`（默认 15，可 `R12_MAX_LOAD` 覆盖）**自动跳过 VLM 用例并打印跳过原因**；我已用 `R12_MAX_LOAD=1` 实测跳过分支生效（`[C08] SKIP(load1=20.0 > 1.0)`，PASS=11）。**C14/C15 多图容量仍未在新配置下测过**，需**独占 VLM 槽的窗口**（判据改为 `measure_window.py`：VLM cpu<0.25 核 且 load1/load5≤10，见 §16.9-2）再跑，跑前会与 model-ops 确认内存 |

### 16.4 B 项（/parse 带索引）——**已跑通（ES + Milvus 双落库）**

配置与代码：`es-insert`/`milvus-insert` 按 TL 口径（`/insert_fulltext_documents`、`/insert_vector_documents_custom`，走代理）；`index` 引用 alg-ops 的 `index_data_config_py`；探针 `platform/r12/parse/fixtures/index_probe.py` 走 `/parse_sync`（与 `/parse` 共用 `index_es`/`index_milvus`，不需 java-gateway 回调）。

**实测（真实文件 → 代理 → ES/Milvus，代理 19526/19527 由 alg-ops 于 05:0x 起）**

| 用例 | `/parse_sync` | ES（本体 19200 只读） | Milvus（`rag_knowledge_base`） | 一致性 |
|---|---|---|---|---|
| `cn-digital.pdf` → `r12_it_parse_001` | **200 / success=true / 17.75s**（高负载窗口，含 embedding 争用；不可当性能基线） | `r12_it_parse_001` = **1** | `_r12_it_parse_001` = **1**（`source=r12-rag/fixtures/cn-digital.pdf`） | ✅ chunk 1 == ES 1 == Milvus 1 |
| `table-ledger.xlsx` → `r12_it_parse_002` | **200 / success=true / 22.52s**（同上，高负载窗口） | `table_summary_r12_it_parse_002` = **1**、`table_chunks_r12_it_parse_002` = **1** | `_table_summary_…` = **1**、`_table_chunks_…` = **1** | ✅ 表格块与表摘要双写；该样本无正文块故 `r12_it_parse_002` 未创建（符合预期） |

服务端日志佐证：`index_vector_service.log` → `集合:r12_it_parse_001创建成功` + `POST /insert_vector_documents_custom 200 OK`。

**接口契约与数据约束核对（alg-ops 反馈 + 我方实测落库类型）**
- **payload 键名以代码为准**（我此前在消息里口述的 `index_name`/`embed_model` 是错的，已更正文档）：
  - ES：`{"index_name", "document_list", "duplicate_flag"}`（`indexing_utils.py:27-31`）
  - Milvus：`{"collection_name", "model_name", "document_list", "db_name", "duplicate_flag"}`（`indexing_utils.py:197-203`）
  - 响应均校验 `code == 200`（成功 `msg` 形如 `…共保存3条数据` / `{'insert_count': 3, 'ids': [...]}`）
- **落库后实测字段类型**（`_r12_it_parse_001`，33 字段）：`file_id="9001"`（字符串，检索侧会 `int()`，必须纯数字）、`chunk_index=0`（int）、`page_number=[1,1,…]` / `labels=[]` / `pic_offset_list=[]` / `text_parent_id_list=[]`（ARRAY）、`offset="[[0, 203]]"` / `position="[[[183.0,174.0],…]]"` / `page_size="…"`（JSON 字符串）、`vector` dim=**1024**、`source`/`knowledge_base_name` 正确。
- 结论：**解析侧现有 payload 天然满足 alg-ops 的三条约束**（file_id 数字、数组传真 list、chunk_index 数字），无需改代码。

**两个必须记下的跨服务事实**
1. **Milvus 集合名带前导下划线（已由 alg-ops 用 `generate_collection_name_uuid()` 实测确认规则）**：传 `index_name=r12_it_parse_001` → 实际集合 **`_r12_it_parse_001`**；ES 索引名**原样使用**（仅小写归一）。
   - **更正（我先前写错）**：**调代理检索不需要加 `_`**（19526 `/milvus_vector_search`、19995 `/retrieval_documents`、19527 `search_by_custom_param` 都传**原始名**，代理内部自己再跑一遍该函数）；**只有直连 pymilvus 的校验脚本**才用 `_<index_name>`。
   - **索引名约束（重要）**：只用 `[a-z0-9_]`。含 `-` 或中文 → 上游 `uuid5` 成不可预测名（QA 按规则找不到）；含大写 → **ES 小写化、Milvus 保大写**，两侧不一致。
   - `embed_model` 必须精确等于 `alg_common_py.online_embedding_model` 的键名（当前仅 `bge-m3`，dim=1024），填错 500。
2. **Milvus 行数校验要用 `count(*)`**：`get_collection_stats().row_count` 有延迟（我第一查返回 0，实际 `count(*)`=1），校验一律用 `count(*)`。

另：ES 集群 `_cluster/health` 在创建索引后由 green 变 **yellow**（单节点副本未分配，非错误）；`get_collection_stats` 的行数延迟同理。TL 提到的 alg-ops IK 插件重启窗口未撞上。

**alg-ops 侧旁证（基础设施视角，与我方读到的完全一致）**：Milvus `rag_knowledge_base` 集合 `_r12_it_parse_001` / `_table_summary_r12_it_parse_002` / `_table_chunks_r12_it_parse_002`（`num_entities` 已累加），ES 三个同名索引各 1 doc；**两道代理无 500/422，payload 与其 pydantic 模型对齐**。
两个后续要注意的事实（记入 R13 参考）：
1. **ES 的 `table_summary_*` / `table_chunks_*` 会自动切到专用 mapping**（`ES_INDEX_MAPPING_SUMMARY` / `_CHUNKS`），无需解析侧先建索引；`/create_es_index` 传这些名字也走专用 mapping。
2. **Milvus 集合 schema 建成即固定**（当前 `enable_question_vector=false`，无 `question_vector` 字段）——后续若要启用 FAQ 双向量必须**重建集合**，不能靠 upsert 加字段。
### 16.5 容量口径纠正（重要，避免 R13 规划高估）

我最初把 "C08 348.12s → 105.72s" 写成配置收益，**该结论已被 model-ops 证伪、我复核后撤回**。

**权威判据：服务端 `prompt eval` 速率**（单图请求只占一个槽，槽位模型对它没有影响）
| 观测 | prompt tokens | prompt eval 速率 | 说明 |
|---|---|---|---|
| 我的 105.72s 那次（`task 44`） | 2949 | **28.58 tok/s**（103.19s） | 低负载窗口 |
| model-ops 的 125.2s 那次（`task 549`） | 2778 | **29.25 tok/s**（94.96s） | load1≈13 |
| 我早前 348.12s 那次 | ~2900 | 折算 **≈11–13 tok/s** | 高负载窗口（load1≈20–25） |
| model-ops 高负载 4 并发那次 | 2801 | **13.21 tok/s**（212s） | load1≈29.6；**旧 4 槽共享池配置下同为 13.21 tok/s** |

→ 同一负载下新旧配置单图吞吐一致，所以：
1. **单图延迟由 load1 决定**（20 核机器上大致 `load1≈13 → ≈29 tok/s`、`load1≈25–30 → ≈13 tok/s`，近似反比）；
2. **配置变更收益 = 消除并发 500（改排队）+ RSS 7.7G→4.5G，不是单图提速**；
3. **C08 容量数值必须带负载上下文引用**。

**已落实的取数纪律**
- 回归脚本记录每用例前后 `load1`（`result.json` 的 `load1_before/load1_after`、`summary.md` 增 load 列），容量结论按 `≤10 / 10–15 / >15` 三档引用；
- 引用延迟**优先用服务端 `prompt eval` 速率**（`logs/model-vlm.log` 的 `print_timing`），比 `uptime` 客观——我实测到 load1 读数滞后（请求结束后读到 25.96，而该请求实际 28.6 tok/s）；
- `load1 > 15` 时 VLM 用例直接 SKIP（`--max-load`），不产出假数据。

### 16.6 `output_max_tokens` 由 256 → 512（依据 model-ops 实测 + 我方复验）

- **外部证据**：model-ops 在新配置下补测"单请求 3 图"：3×1240×1754、prompt **8374** token → **HTTP 200**、零 mtmd/KV 错误、**613.3s**（load1 18→27）→ 2 槽 × 私有 16384 对 3 图容量足够，**C14/C15 不会被 500 干扰**。
- **但同请求 `max_tokens=600` → `finish_reason=length`**：只抄完【图1】14 行即截断，图2/图3 无输出，且图1 页眉被略过（先抄正文、预算耗尽）。他估算：单张 A4 逐字 **150–200 token**，3 图需 **≥1500**。
- **我方处置**：`output_max_tokens` **256 → 512**；新增 `finish_reason` 采集、`vlm_status='truncated'` 分档、回归断言 `image_text_not_truncated`。**未直接拉到 1024/1500**：本服务是**一图一请求**，512 对单图逐字有 2–3 倍余量，且高负载下不浪费生成时间；真出现长转录需求再按图调整。
- **实测分支**：`output_max_tokens=1` → **200 / 27.79s**，`truncated` + `finish_reason=length`、`vlm_len=3`、OCR 347 保留；`=24` → **200 / 187.89s**，自然 `stop`（37 字）→ 说明"描述型"输出天然短，**截断风险集中在"逐字转录型"用法**；已恢复 512（live 值核对）。

**密排页定标（model-ops 实测，推翻我"2–3 倍余量"的说法）**
| 页面密度 | 逐字输出 | `max_tokens=512` 余量 |
|---|---|---|
| 稀疏（我 fixture 14 行） | 140–200 token | **2.5×** |
| **密排中文 A4（36 行条款、约 1000 汉字）** | **427 token**（`finish=stop`、wall 249.7s、pp 29.3 tok/s、`cache_n=16`） | **仅 1.2×** |
经验比 ≈**1.65 字/token** ⇒ 512 ≈ **840 汉字**，超过即 `length`。
→ **处置：`output_max_tokens` 提到 768**（密排页 1.8× 余量；代价只在"真的写长"时产生，`stop` 不影响耗时）；并**100% 依赖 `finish_reason=='length' → truncated`** 作为安全网。
→ **R13 提醒**：真实合同/条款页必须用**密排页**重新标定（别用稀疏 fixture 外推），再决定 512/768/1024。

**"truncated 会不会被合并掩盖"已实测排除**：`max_tokens=1` 那次返回的图片块 `vlm_status` 仍为 **`truncated`**、`vlm_finish_reason='length'`，即使 `page_content` 合并了 OCR 347 字（merged 352）。因为 `vlm_status` 是**图片块自身字段**、合并只改 `page_content`，**不存在文档级状态覆盖图片级状态**；回归断言 `image_text_not_truncated` 也按"任一块 truncated 即 FAIL"判定。
### 16.7 取数机制与"字符级误识"（吸收 model-ops 实测，并已落到代码）

**1) 用响应体 `timings` 判断测量是否干净（已采集进 metadata）**
`llama-server` 非流式响应自带 `timings.prompt_n / cache_n / prompt_per_second / predicted_per_second`。我已在 `chat(return_meta=True)` 里带上 `timings`，并写入图片块 `vlm_prompt_n` / `vlm_cache_n`。
判据（model-ops 口径）：**`cache_n ≤ 5% × prompt` 才算干净测量**；`cache_n` 接近 `prompt_n` 说明整段命中 prompt cache，耗时不能代表首次开销。

**我方实测印证（同一张图重复解析，我们自己也踩了缓存）**：
| 次 | 耗时 | `prompt_n` | `cache_n` | 结论 |
|---|---|---|---|---|
| 首次 | 79.86s | 2865 | — | 冷 |
| 第二次 | **14.71s** | **1** | **2865** | 全量缓存命中，**假快** |
| 第三次 | 51.56s | **1** | **2962** | 仍是全量缓存 |
→ **C08/C14/C15 的容量数字必须用"新图/新文档"测**，否则量到的是缓存命中时延。回归脚本复用固定 fixture，因此其秒数**只能看量级**，不能作为容量结论（已在脚本头部注明）。

**2) 跨图 KV 污染不存在（model-ops 实测，对我方链路是好消息）**
他连续用 3 张同尺寸不同内容的图、同一问题请求：`CASE-AAA111→AAA111`✅、`CASE-BBB222→BBB222`✅、`CASE-CCC333→CASE-CC333`❌。前两例证明**不会答出前一张的内容**（跨图污染排除），我方"一图一请求"链路安全。
第三例是**字符级误识**（三个连续 `C` 丢了一个），且 `prompt_n` 是全量、非缓存 → 真实识别错误，不是缓存导致。

**3) 字符敏感字段必须交叉校验（已实现标记）**
`ParsedImageMetadata` 新增 `vlm_needs_crosscheck` + `vlm_sensitive_tokens`；`_Parser._detect_sensitive_tokens()` 用 4 条正则抽取：≥6 位数字串、金额（两位小数）、日期（`2026年10月20日`/`2026-10-20`）、带连字符编号（`SPDB-2026-PJ-00871`、`CASE-AAA111`）。
- 实测：`编号：CASE-CCC333 金额 1,250.00 元，日期 2026年10月20日，账号 6222001234567890` → `['6222001234567890', '1,250.00', '2026年10月20', 'CASE-CCC333']`；`SCANNED PAGE - no text layer` → `[]`（不误报）。
- 语义：**这些片段不得只靠 VLM**，下游需用 OCR 文本 / 正则 / 校验位交叉校验后才能进证据字段。这条同时是"OCR ∪ VLM 并存"的实证理由：两者错误不同源（VLM 语言顺但会丢字，OCR 字符稳但有噪声）。

**4) 一次真实 bug 与降级路径的正向证据**
`_detect_sensitive_tokens` 首次接入时我误写成裸函数名（漏 `self.`），运行抛 `NameError` → **被 D-1 的失败降级兜住**：`vlm_status='failed'`、OCR 347 字保留、**HTTP 200**、日志有明确错误行。修复后复测 `vlm_status='ok'`。
→ 说明"单图增强失败不得整篇失败"这条设计**不仅防端点故障，也防增强路径自身的代码缺陷**。
### 16.8 TL 追加要求与后续修复（2026-10-25 05:4x）

**1) 配置对齐（TL 在 live 上补了两个键，我已回写权威副本）**
TL 直接在 Nacos `alg_doc_config_py` 上补了异步链路必需的
`async-callback: "http://{ip}:{port}/index/parseTask/callback"`、
`minio-upload: "http://{ip}:{port}/index/knowledgeBase/file/uploadParsedFile"`，
以及只读的 `es_config` / `retrieval_top_k` / `multi_version.url` / `url_table_indicator.url`。
→ 我已把 **live 内容原样回写** `platform/r12/nacos/alg_doc_config_py.yaml`（避免我下次发布覆盖掉），并核对 4 个键齐备。

**2) 异步 `/parse`（不是 `/parse_sync`）复验**
| 证据 | 结果 |
|---|---|
| Python 日志 | **`KeyError` 计数 = 0**；`回调接口成功` 多条（task_id 23/25/27，URL `http://127.0.0.1:8088/index/parseTask/callback`） |
| Java `file_parse_task` | id 23/25/26/27 **status=4（成功）**，均有 `end_time`（05:41:06–05:41:25），无 `error_msg`（id25 首次尝试有一次 ES 建索引失败，retry_times=1 后成功） |
| Java `knowledge_base_list` | 对应行 **status=3**、`parsed_file_path` 非空、`source_url` 指向 MinIO |
| ES 侧 | `kb_5/6/7/8` 分别 5/3/2/4 docs，`table_summary_kb_5/kb_8`、`table_chunks_kb_5/kb_8` 各 1 → `getFileChunks` 有数据 |
| 我另做的独立异步验证（不写 Java 表） | `POST /parse` → 200「正在执行」(0.01s)；后台 `index服务插入索引总花费时间：4.75s`；ES `r12_it_parse_003`=1、Milvus `_r12_it_parse_003`=1 |

**3) 新增两处修复**
- **R12-FIX-PARSE-06（正确性）**：`vlm_status=='truncated'` 时 **VLM 残句不再并入 `page_content`**（只保留 OCR）。理由：截断残句常是半句/半词/半个数字（`金额 1,250.0`），拼进正文无法分辨，比缺文本更有害。
- **R12-FIX-PARSE-07（健壮性）**：`revoke_callback` 在 **task_id 为空时跳过回调**并 warn（非 Java 主链调用会触发 Java NPE `task is null` 并把后台任务打成 500），并给回调 `requests.post` 补 `gateway_timeout`(默认 60s)。
- **R12-FIX-PARSE-08（落库阻断修复）**：ES 侧 payload **剔除 `metadata.boxes` / `base64`**。
  实测证据：`docx-image.docx` → `r12_it_parse_004` 报
  `Mapper for [metadata.boxes] conflicts with existing mapper: Cannot update parameter [dims] from [4] to [2]` → 整批 400 + 回滚 → **含图片的文档完全无法落库**。
  修复后同文档 → `r12_it_parse_005`：**ES count=2（成功）**，且文档里 `vlm_status=ok / vlm_finish_reason=stop / vlm_needs_crosscheck=False / vlm_prompt_n=1` 均可查回。

**4) 一个新发现的跨服务限制（需 alg-ops 决策）**
`vlm_status` 等状态字段**只在 ES 里存在，Milvus 里没有**：Milvus schema 建成即固定（首批文本块决定 schema），后续图片块的 `vlm_*` 键被服务端按 schema 过滤。
→ 影响：只走 Milvus 通道的召回看不到"该文本来自一次截断/需交叉校验的 VLM 输出"。当前 R12 检索是 ES+Milvus 混合，**证据链校验请以 ES 通道为准**；若要 Milvus 也带上，需 alg-ops 在其 schema 增加 `vlm_status` / `vlm_needs_crosscheck` 两列（属其服务改动）。

**5) `file_path` 接口契约（实测澄清）**
解析侧 `FileParams.file_path` 要求 **MinIO `bucket/object`**（如 `r12-rag/fixtures/x.pdf`）；我传完整 `http://127.0.0.1:19000/...` 会被当成 bucket=`http:` → `invalid bucket name http:`。
Java 主链不受影响（其任务参数在调用前已归一化为 `r12-rag/kb_x/...`，Python 侧日志可见该形态）。

**6) 取数纪律补充（model-ops）**：`load1` 的瞬时低点会骗人（我 05:17 以 load1=10.38 开跑，3 分钟内爬到 29.25）。回归脚本 `--max-load` 已改为 **load1 与 load5 同时 ≤ 阈值**才跑 VLM 用例。

**7) 敏感字段正则补强（model-ops 反馈）**：日期尾部 `日/号` 纳入；新增「万元/亿元金额」「百分比/年化利率」「LPR±BP」三类。字段级要求（TL 已采纳进 R12 验收）：**编号/账号/金额/日期/利率不得只靠 VLM，必须 OCR/正则/校验位交叉校验**；对应可核对条目 = 图片块 `vlm_needs_crosscheck` / `vlm_sensitive_tokens`。
### 16.9 容量口径再纠正（model-ops 定位根因：槽间争抢，不是机器慢）+ 三个新结论

**1) "慢"的真因是槽间争抢，不是整机负载 —— 532s 那条记录改判**
模型服务端日志对同一条请求（task 2663）的分段实测：
- prefill：**157.9s / 3331 token = 21.1 tok/s（正常）**
- generation：**374.6s / 276 token = 0.73 tok/s（被饿死）**

同一时刻另一个槽在跑 **3871 token** 的长请求（`kb_5/*`）。⇒ **prefill 正常说明模型没退化、KV 没爆、配置没问题**，是"邻居的 prefill 抢走了本请求生成阶段的 CPU"。
**结论改写**：本轮 C14/C15 未完成**不是容量结论**，应记为「**槽争抢导致生成饿死，非容量结论**」。两者对 R13 的指导完全相反：前者要**排期（独占窗口）**，后者会误导成"需要更强机器"。

**2) 用 load1 当闸门是循环论证，已改用 `measure_window.py`**
VLM 自己 `--threads 20`，一个在飞请求就吃 8.49 核 ⇒ 开跑后 load1 抬升有一部分是我自己的请求造成的。回归脚本 `parse_cases.py` 已把 VLM 用例闸门换成 model-ops 的窗口工具，**核心判据 = VLM 进程 `cpu < 0.25 核`（两槽都空闲）**，辅以 `load1 与 load5 同时 ≤ 阈值`、`MemAvailable ≥ 4G`、`Swap=0` 风险提示；工具缺失时退回 load 双阈值并打印降级说明。实测样例（05:57）：
```
load1=19.67 load5=26.49 nproc=20 | MemAvailable=8.0G SwapTotal=0.0G
VLM cpu=0.00 核 | embedding 0.01 核 | rerank 0.00 核
NO-GO：✗ 负载未达标（load1/load5 要求都 ≤10）
```
注意这条样例说明：**当前 load 高但不是 VLM 在忙（cpu=0.00）** —— 即"机器忙"和"模型槽被占"是两件事，必须分开测。

**3) 落库幂等性实测（model-ops 提出的"回调重复会不会重复建索引"）**
同一文件（`cn-digital.pdf`）对同一 index（`r12_it_idem`）连续落库两次：
- 第一次 6.23s → ES count=1；第二次 9.11s → ES count=**1**；Milvus `_r12_it_idem` count=**1**。
- 机制：`index_es` / `index_milvus` 均以 `duplicate_flag=True` 走"**先按 source 删除旧数据再插入**"。
⇒ **回调重试不会造成重复文档**（同一 task_id 重复回调 = 覆盖写），这条可作为 R12 幂等结论。

**4) `boxes` vs `position` 的边界必须写死（ES 400 的根因归纳）**
`metadata.boxes` 是「维度不定的嵌套数组」（多框 × 4 点 × 2 坐标），ES 动态 mapping 只认第一批文档的形状：
**先落 4 层文档、后落 2 层（或反之）必然 `dims` 冲突，且是整批 400 + 回滚** —— 不是"这一批坏了"，而是"这类文档根本进不去"。
因此边界定义为：
- **`boxes` = 解析中间态**（用于构建 `position` 与图片关联），**不进检索存储**；
- **`position` = 下游定位字段**（页内 bbox），**必须保留**（D-1 的修复目标之一就是图片块补定位）。
⚠ 后续若有"为了完整把 boxes 塞回 ES"的改动，会立刻复现本次 400，**请以本节为禁止项依据**。

**5) Milvus 侧状态字段的可行方案（实测 schema 后修正 model-ops 的建议）**
`_r12_it_parse_005` schema 共 **33 个字段**，**不存在 `meta_json` 之类可复用的通用 VARCHAR**（最接近的 `title_path` 已被标题层级占用）。
⇒ 打包方案需要 alg-ops **新增一列**（建议 `meta_json VARCHAR(65535)`），我们把 `vlm_status` / `vlm_finish_reason` / `vlm_needs_crosscheck` / `vlm_prompt_n` / `vlm_cache_n` 打包进去，**以后加标记不用再改表**。
在此之前的口径不变：**证据链校验以 ES 通道为准，Milvus 只做向量召回**。
### 16.10 质量状态字段的权威口径（alg-ops 决策 ②：Milvus 不加列，已实测确认）

**决策（alg-ops 2026-10-25，含三处消费者核查）**：**Milvus 不加列，`vlm_*` 以 ES 为唯一权威。**

**写死口径（QA 可直接引用）**：
> `vlm_status` / `vlm_needs_crosscheck` **只存在于 ES**（路径 `metadata.vlm_status`、`metadata.vlm_needs_crosscheck`）；
> **Milvus 不含这两个字段，任何"在 Milvus 里找不到该字段"都不算缺陷。**
> 职责划分：**ES = 全文与质量状态**；**Milvus = 纯向量召回**。

**决策依据（对方给的证据，我认可）**：
| 核查点 | 结果 |
|---|---|
| index_data / retrieval / llm 三服务是否消费 `vlm_*` | grep **0 命中** |
| 检索返回是否透出 | `process_return_results()` 白名单式固定 20 key，未登记字段返回前即被丢弃 |
| Java 侧 `Document` DTO | 无 `vlm`、无 `boxes`（grep 0 命中） |
| 更硬的理由 | Milvus schema **按集合固定**，老集合(001/002/003/005)已建成改不了 → 加列会造成"同链路不同知识库字段不一致"，QA 脚本更易踩坑 |

**我在真实 mapping 上复核过（不是照抄）** —— `r12_it_parse_005`：
```
metadata 字段数 = 49（基础 37 + 动态映射 12）
vlm_status            : text + keyword(ignore_above=256)
vlm_finish_reason     : text + keyword(ignore_above=256)
vlm_needs_crosscheck  : boolean
vlm_prompt_n / vlm_cache_n : long
position              : text + keyword
boxes                 : （无此字段，已按 R12-FIX-PARSE-08 剔除）
```
**可执行查询样例（实测均命中）**：
- 值过滤必须用 keyword 子字段：`{"term":{"metadata.vlm_status.keyword":"ok"}}` → total=1（image 块）
- 布尔过滤直接 term：`{"term":{"metadata.vlm_needs_crosscheck":false}}` → total=1
- 直接用 `metadata.vlm_status` 会走分词，匹配不准 —— **QA 脚本请按上面两条写**。

**两个辅助口径（alg-ops 提供，已入我文档）**：
1. `metadata` 字段数 37 → 49 **是 ES 动态映射的正常行为，不是 mapping 被污染**；只要核心字段（`page_content` 的 `ik_max_word`、`metadata.pk/file_id/offset/position/chunk_index`）在，检索与溯源不受影响。
2. `/static_count` 与 ES `_count` 同源，且对方在接口返回前已 `indices.refresh` ⇒ **写入拿到 200 之后立刻查是准的**；若将来并发/批量写，采样点必须是"每批 200 之后"。

**`boxes` 结论（双方一致，已定案）**：ES 基础 mapping 的 37 个 metadata 字段里**没有 `boxes`**（有 `position`），故 `boxes` 必然走动态映射 → 变深数组按首篇文档推断 dims → 层数不同即冲突（我撞到的 `dims 4→2`）。**保持剔除，不改回数组**；前端若要做图片区域高亮，正确载体是 **`position`**（已是字符串、mapping 已有、检索透传）。

**R13 参考（若真要让 Milvus 带状态，三处一起改，缺一处即死数据）**：
① `milvus_kb_config.py` 的 `MILVUS_FIELDS` 加列（仅对新集合生效，需明确是否重建历史集合）；② `process_return_results()` 白名单放行；③ Java `Document` DTO 加字段。
### 16.11 窗口闸门升级为双模式（C08 首次在忙机器上跑通）

**变化**：我那条"load1=19.67 但 VLM cpu=0.00"的反例，直接促使 model-ops 把工具拆成两档；我把两档接进回归脚本：
- `--mode capacity`：`load1/load5` **且** 槽空闲 **且** 内存够，三项全过才 GO → **耗时数据可作容量引用**（C14/C15 多图容量走这档）；
- `--mode functional`：只要**槽空闲 + 内存够**（负载只提示不阻塞）→ **断言/功能回归走这档**，避免"邻居在编译 Java 就把功能用例全 SKIP"造成覆盖率白丢。

**实测退出码**（正确测法，不被管道吞）：`functional → 0(GO)`、`capacity → 1(NO-GO)`；同一时刻 `load1=10.46/load5=21.73`、VLM 槽空闲 —— 正好演示"机器忙但模型闲"。

**直接收益（本次回归）**：
```
— 测量窗口检查（mode=functional）—
[C08] PASS http=200 56.23s chunks=2  DOCX 内嵌图片（需VLM）
PASS=12 FAIL=0 BLOCKED=0
```
→ **C08 首次在"load1 11→20"的忙机器上跑通**（此前一直被 load 闸门 SKIP）；同时也再次验证 R12-FIX-PARSE-06（截断不并入正文）与 07（回调跳过）未破坏图片块产出（chunks=2：text + image）。

**证据补强：这不是"我和邻居"的问题，是多角色共享 20 核**
model-ops 采样到 **`rerank cpu=17.73 核`（瞬时大 batch，2 秒后回 0）**、`embedding 曾 1.5 核`、`VLM 8.49 核（kb_5 在飞）`、`MemAvailable 5.9G`。
⇒ 向 TL 申请窗口的证据已扩为三行：**VLM 8.49 核（kb_5 在飞）/ rerank 17.73 核（瞬时大 batch）/ MemAvailable 5.9G**。**只有 TL 能排期**，不由角色间互等。
