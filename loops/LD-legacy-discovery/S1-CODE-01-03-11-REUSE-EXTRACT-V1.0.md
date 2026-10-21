# S1 源码利用清单：CODE-01 / CODE-03 / CODE-11

- 日期：2026-10-21
- 批次：`LD-legacy-discovery`
- 参照物：`docs/approvals/OWNER-RESOLUTION-2026-10-21-PRODUCTION-BASELINE.md` 认定的生产快照
- 策略依据：`REUSE-STRATEGY-V1.0.md`（目标=功能等价；能抄就抄，但必须换壳 + 绑 parity 用例 + 改已知缺陷）
- **性质：分析清单，不是复用决议。** 三项资产的 `decision` 仍为 null，需逐项绑特征回放用例并经 owner 批准。
- 复核方式（只读）：

  ```bash
  SRC=<RAG-SRC/_src>/rag-alg-service-api/rag-alg-service-api
  # 文件数
  find $SRC/alg_doc_parse_service -name '*.py' | wc -l   # 84
  find $SRC/alg_retrieval_service -name '*.py' | wc -l   # 59
  # 依赖
  grep -rhoE "^\s*(from|import) [a-zA-Z_][\w.]*" $SRC/alg_doc_parse_service --include="*.py" | ...
  # Java 纯逻辑占比
  grep -rlE "import org\.springframework|import com\.baomidou|import com\.alibaba" <rag-common>/<包>
  ```

## 0. 一页纸结论

| 资产 | 能直取（A） | 要换壳（B） | 要改/重写（C） | 不搬（D） |
|---|---|---|---|---|
| CODE-01 解析（py 84） | `deepdoc/` 48 py 中的 parser/splitter/vision/output_object/util（约 44 py），**先切断 4 个反向依赖** | `server/` 服务层 14 py：HTTP 入口、mysql、minio、nacos、跨服务调用、日志 | 坐标/offset 语义、图片链接与证据绑定 | `docker/`、`gunicorn_conf.py` |
| CODE-03 召回（py 59） | `operators/retriever` 6、`reranker` 5、`rephraser` 3、`utils` 2（约 16 py） | `operators/client` 8（es/milvus/graph/llm/reranker/web_search）、`app/utils.py`、`app/config` | 四条路由都**不带授权范围**，端口必须强制带 `AuthContext`；多路取数逐个继承范围 | `docker/`、`setup.py`、`app/table_retrieve.py`（依赖外部包 `retrieval_service`） |
| CODE-11 公共库（java 379） | DTO/枚举/请求体/常量/转换器：auth 89、index 114、qa 44、graph 35、sensitive 3、infrastructure 15（合计 **约 300**） | `operation`、`context`、`global`、`auth/authenticate`、`infrastructure` 中的 config/typehandler | `auth/authenticate`（旧 token 体系）、`feign`（改端口） | **整包 pom 不搬**（Spring/MyBatis/Feign/Nacos/Redisson/JWT/actable） |

关键提醒：CODE-11 的 `pom.xml` 带 `mybatis-enhance-actable`（运行期自动建表），这是"隐式 DDL 来源"，
与 P0-02 有关但**不能替代真实 DDL**；搬代码时不得把该依赖带进新模块。

---

## 1. CODE-01 `alg_doc_parse_service`（84 py）

### 1.1 结构（实测）

| 路径 | py 数 | 承担什么 | 主要第三方依赖 |
|---|---|---|---|
| `deepdoc/parser` | 17 | 各格式解析器（pdf/docx/doc/ppt/excel/csv/html/txt/wps/image/mineru/ali/复旦） | `server`(15)、`langchain_core`(14)、`openpyxl`、`magic_pdf` |
| `deepdoc/splitter` | 14 | 分块策略（naive/book/laws/intel/section/table） | `deepdoc`(24)、`numpy`、`pandas` |
| `deepdoc/vision` | 7 | OCR 与版面检测（ONNX 推理） | `numpy`、`huggingface_hub`、`PIL`、`onnxruntime` |
| `deepdoc/output_object` | 4 | 解析结果对象 | `pydantic`、`bs4` |
| `deepdoc/util`、`deepdoc/utils.py`、`deepdoc/config`、`deepdoc/multi_version`、`deepdoc/database_desc` | 7 | 分词（`rag_tokenizer`）、图片链接、多版本、库表描述 | `tiktoken`、`nltk`、`datrie`、`hanziconv`、`jieba`、`pdfplumber` |
| `server/*` | 14 | HTTP 入口、参数、缓存池、mysql 访问、minio、nacos、跨服务索引调用、OCR 池、上报 | `fastapi`、`pymysql`、`minio`、`nacos`、`requests`、`xgboost`、`httpx` |
| `docker/`、`gunicorn_conf.py`、`*_start.py` | 3 | 部署与启动 | `uvicorn`、`setuptools` |

### 1.2 可直取清单（A）

| 目标 | 内容 | 依据 | 直取前提 |
|---|---|---|---|
| `deepdoc/parser/*.py`（17） | 各格式解析 | 纯解析逻辑，不含 HTTP/DB | 切断 4 个反向依赖（见 1.3） |
| `deepdoc/splitter/*.py`（14，含 `table_utils/`、`xg_splitter.json`） | 分块与表格切分 | 只依赖 numpy/pandas | 同上 |
| `deepdoc/vision/*.py`（7） | ONNX OCR/版面 | 依赖本地模型文件 | 模型文件须随交付或走配置路径 |
| `deepdoc/output_object/*.py`（4） | 结果对象 | 仅 pydantic | 字段需映射到新合同（见 1.4） |
| `deepdoc/util/`、`rag_tokenizer.py`、`image_link.py` | 分词/链接 | 纯算法 | `rag_tokenizer` 依赖 `nltk/datrie/hanziconv`，需确认许可与词典来源 |
| `deepdoc/config/*.py` | 解析配置项 | 纯配置结构 | 改成新配置模型 |

**不建议直取**：`server/data_access_object.py`（直连 mysql）、`server/minio_utils.py`、`server/nacos_utils.py`、
`server/indexing_utils.py`（调别的服务）、`server/ocr_pool.py`（xgboost 池化）、`server/controller.py`。

### 1.3 必须切断的耦合（否则 `deepdoc` 搬不走）

`deepdoc` 反向 import 了服务层 4 个东西（实测）：

| 被依赖项 | 出现位置（示例） | 新方案 |
|---|---|---|
| `server.config.DocParseConfig` | `parser/text_in_parser.py`、`parser/pdf_parser.py`、`parser/mineru_parser.py`、`splitter/table.py` | 换成新 `ParseOptions`（值对象，无全局配置） |
| `server` 的 `ModelInfo` | `deepdoc/utils.py`、`splitter/base.py`、`splitter/table_utils/table_index.py` | 换成 `ModelRef`（只含名称/版本，不含租户/网关信息） |
| `ProcessReporter`（进度上报） | `splitter/table_utils/table_index.py` | 换成 `ProgressPort`（可选，默认无操作） |
| `load_local_ocr` / `create_uuid` / `run_in_thread_pool` | `parser/pdf_parser.py`、`splitter/table.py` | 换成 `OcrPort` / 本地 id 生成 / 线程池工具（自建 util） |

> 这 4 处是"代码能不能搬"的真正门槛，不是体力活，是设计点：搬之前先把 `deepdoc` 变成不依赖 `server` 的库。
>
> **2026-10-21 已验证（`S1-SPIKE-CODE-01-RESULT-V1.0.md`）**：25 处 import、14 个文件改写后，
> 5/5 样本解析结果逐字段一致。但同时发现三条硬条件：`parser/__init__` 全量导入导致原包**无法被导入**；
> docx 导入期需 21 个重型依赖；OCR 在**构造期**就加载模型（`image_parser.py:21`）。
> 因此「可直取」需修正为「切断耦合 + 惰性化重依赖 + 随包携带资源」之后才成立。

### 1.4 需要换壳 / 必须改的边界

| 边界 | 现状 | 新端口/合同 | 必须改的理由 |
|---|---|---|---|
| HTTP 入口（11 条路由：`/parse`、`/parse_without_indexing`、`indicator_*`、库表描述等） | FastAPI + pydantic 请求体 | `ParsePort.parse(doc_ref, options) -> ParsedDocument`；`IndicatorPort.*` 按新合同 | 新系统边界是 `/v1` 内部合同，不复用旧路由 |
| 解析产物坐标 | 旧实现自带 position 字段 | **Unicode 码点左闭右开 + 完整 `text_hash` + `parser_version`** | 合同硬要求；旧语义不可直接沿用 |
| 图片/表格引用 | `image_link.py` + minio 链接 | `AssetRef`（对象存储键 + 哈希 + 页码 + 坐标） | 引用必须可点开原文且可校验 |
| 文档读取 | `loader.py`（本地/远程路径） | `DocumentSourcePort` | 禁止直接读本地路径 |
| 元数据/任务状态 | `data_access_object.py` 直连 mysql | `DocumentRepoPort` / `TaskRepoPort` | 禁止算法侧直连业务库 |
| 对象存储 | `minio_utils.py`（含内网地址硬编码） | `ObjectStorePort` | 硬编码内网地址不得入库 |
| 服务发现/配置 | `nacos_utils.py`（含内网地址硬编码） | 静态配置 + 环境变量 | 同上 |
| 索引写入 | `indexing_utils.py` 用 http 调索引服务 | `IndexWritePort`（走 P0-04 的代次/激活指针） | 旧实现无代次概念，抄了会混代 |
| 日志/追踪 | `log.py`/`loguru` + contextvars | 统一埋点（含 trace_id） | 埋点要唯一命名，不能两套并存 |

### 1.5 资源与许可（搬之前必须确认）

- ONNX 模型：`deepdoc/vision` 需要 `det/rec .onnx` + `ocr.res` 等本地文件；旧代码从固定目录加载 → 新方案必须配置化并随交付。
- `magic_pdf`、`xgboost`、`onnxruntime`、`tiktoken`、`datrie`、`hanziconv`、`jieba` 的许可与体积需逐项确认。
- 代码里存在 `hf-mirror.com` 与内网地址引用 → **不得复制进仓**。

---

## 2. CODE-03 `alg_retrieval_service`（59 py）

### 2.1 结构（实测）

| 路径 | py 数 | 承担什么 | 说明 |
|---|---|---|---|
| `app/operators/retriever` | 6 | bm25 / embedding / hybrid / db 检索基类与实现 | 召回核心 |
| `app/operators/reranker` | 5 | bge / qwen3 / llm 重排 | 精排核心 |
| `app/operators/rephraser` | 3 | 查询改写 | 依赖 LLM |
| `app/operators/client` | 8 | es / milvus / graph / llm / reranker / web_search 客户端 | **换壳重点** |
| `app/operators/common`、`utils` | 4 | 日志、token 计数 | 可直取 |
| `app/view` | 9 | 4 条路由 + view 基类 | 换壳 |
| `app/*.py`（`retrieval_service.py`、`multiple_retrieval.py`、`retrieval_service_cec.py`、`retrieval_fun_tool.py`、`reranker_service.py`、`table_retrieve.py`、`utils.py`、`config`） | 12 | 多路编排、CE C 变体、表检索 | 编排可直取，配置/服务发现要换 |

### 2.2 可直取清单（A）

| 目标 | 依据 | 前提 |
|---|---|---|
| `app/operators/retriever/*`（6） | 纯检索逻辑，通过 client 抽象取数 | client 换成新端口 |
| `app/operators/reranker/*`（5） | 纯精排逻辑 | 同上 |
| `app/operators/rephraser/*`（3） | 查询改写 | 同上（LLM 端口） |
| `app/operators/utils/token_utils.py` | 纯工具 | — |
| `app/multiple_retrieval.py`、`app/retrieval_service.py`（多路编排） | 编排骨架 | 入参必须新增授权范围 |

### 2.3 换壳边界

| 边界 | 现状 | 新端口 | 必须改的理由 |
|---|---|---|---|
| 4 条检索路由（`/retrieval_documents`、`_cec`、`_table_cec`、`_documents_table`） | FastAPI View，入参只有 query/参数 | `RetrievalPort.search(query, auth_context, filters, top_k, strategy)` | **旧入参不带文件范围**（P0-03 已登记） |
| ES / Milvus / 图 客户端 | 各 client 直连 | `FulltextIndexPort`、`VectorIndexPort`、`GraphIndexPort` | 新边界要带代次（generation）与授权过滤 |
| 重排/LLM 客户端 | `reranker_client`、`llm_client`、`zhipuai` | `RerankPort`、`LlmPort` | 需要预算/超时/取消/追踪 |
| 服务发现 | `app/utils.py` 走 nacos（含内网地址） | 静态配置 | 内网地址不得入库 |
| 表检索 | `app/table_retrieve.py` 依赖外部包 `retrieval_service`（非本仓） | 判定为 **D**（缺依赖，不可直取） | 依赖不可得 |

### 2.4 必须改的语义（比换壳更重要）

1. **授权范围逐路执行**：旧编排在"召回完成后"才做兜底校验；新实现必须在**每次取数**（向量、全文、图、邻近块、图片回查、多版本扩召回）都携带并校验范围。
2. **图路**：`graph_client` 无文件级隔离能力 → 只对"整 KB 已授权"的请求开放，否则降级为 degraded 并如实上报。
3. **降级显性化**：某一路失败/超时必须在结果里体现 `degraded` 与覆盖度，不允许"少返回但不说明"。

---

## 3. CODE-11 `rag-common`（379 java）

### 3.1 按包统计（实测：总文件 / 无框架 import 的纯逻辑文件）

| 包 | 总 | 纯 | 判定 | 说明 |
|---|---|---|---|---|
| `auth` | 98 | **89** | A（dto/enums/request/convertor）+ **C**（`authenticate` 3 个全框架耦合） | `auth/authenticate/**` 是旧鉴权入口，**必须重写** |
| `index` | 129 | **114** | A | `enmus` 36/36、`request` 48/54、`dto` 22/28、`constant` 2/2、`utils` 2/2 |
| `qa` | 54 | **44** | A（`entity` 1 个依赖 MyBatis，不搬） | `enmus` 14/14、`request` 18/18 |
| `graph` | 44 | **35** | A/B | `entity` 8/11（部分带 MyBatis 注解） |
| `infrastructure` | 28 | **15** | A（`exception` 3/3、`utils` 8/12；`config`/`typehandler`/`metdahandler`/`application`/`template` **不搬**） | 带 MyBatis/Redisson |
| `operation` | 6 | 1 | B | 操作日志，需换端口 |
| `context`、`global` | 10 | 4 | B | 用户上下文/全局配置 |
| `sensitive` | 4 | 3 | A | 敏感词，纯逻辑 |
| `feign` | 5 | **0** | **D** | 服务间调用改新端口 |
| `library` | 1 | 1 | A | 单个工具类 |

**可直取合计约 300 个 java 文件**（DTO/枚举/请求体/常量/转换器），这是 S1 里最省力的部分。

### 3.2 不许搬的东西

| 项 | 原因 |
|---|---|
| 整个 `pom.xml` | 会带入 Spring Boot 3 + MyBatis-Plus + OpenFeign + Nacos + Redisson + JWT + `actable`（自动建表）+ PDFBox/POI + Ansj |
| `mybatis-enhance-actable` | **运行期自动建表**，是隐式 DDL 来源；与 P0-02 的真实 DDL 冲突，且会绕过迁移管理 |
| `auth/authenticate/**` | 旧 token/会话体系，与新 `AuthContext` 冲突 |
| `feign/**` | 硬编码服务名与 Nacos 依赖 |
| `infrastructure/config`、`typehandler`、`application` | 绑定旧框架生命周期 |

### 3.3 搬进来之后的红线

- 只搬"纯"文件，搬之前按包跑一次 `grep -rlE "import org\.springframework|import com\.baomidou|import com\.alibaba"` 复核（本文件的方法是抽样判据，不是绝对）。
- DTO 的字段名可以保留（便于对照旧数据），但**枚举值必须逐字核对**（M1 的 27 个类型码不得改写成 7 类）。
- `actable` 自动建表出来的表结构，只能作为"参考线索"，**不能**当作 P0-02 的真实 DDL。

---

## 4. S1 组装后的端口清单（建议）

| 端口 | 由谁实现 | 被谁调用 |
|---|---|---|
| `ParsePort` | 新 `services/parse`（内核=deepdoc） | KB 写入流程 |
| `ChunkPort` | 同上（内核=deepdoc/splitter） | 同上 |
| `IndexWritePort` | 新 `services/index`（带 generation/激活指针） | 同上 |
| `RetrievalPort` | 新 `services/retrieval`（内核=operators） | 问答服务 |
| `FulltextIndexPort` / `VectorIndexPort` / `GraphIndexPort` | 适配器（ES/Milvus/图库） | retrieval |
| `EmbeddingPort` / `RerankPort` / `LlmPort` | 适配器（模型服务） | parse/retrieval/qa |
| `ObjectStorePort` / `DocumentRepoPort` / `TaskRepoPort` | 适配器（minio/mysql） | parse/index |
| `ProgressPort` | 可选实现（默认空） | parse |

## 5. 待验证项（本清单不承诺）

1. **行为等价未验证**：没有 MySQL/ES/Milvus/Neo4j/模型服务，无法跑通回放；本清单只做静态判定。
2. `deepdoc` 的 4 个耦合点切断后能否保持解析结果一致，需用固定样本回放证明。
3. `magic_pdf`/`xgboost`/`onnxruntime` 等依赖的许可、体积、离线可用性未确认。
4. `rag-common` 的"纯逻辑"判定基于 import 抽样（框架 import 有无），未逐文件审阅业务语义。
5. 复用决议仍为 `decision: null`；本文件不构成 KEEP/ADAPT 批准。
