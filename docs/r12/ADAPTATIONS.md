# R12 原资产复用与必要改造登记

版本：1.0.0　更新：2026-10-25　责任人：tech-lead
适用范围：`feature/R12-real-rag` 工作树。所有条目均对应真实提交与可复现命令；
未登记的改动视为越界，不得合并。

## 0. 资产来源（先证明"原资产在哪、是什么版本"）

| 资产 | 原始包 | 解压位置（本仓） | 规模 | 说明 |
|---|---|---|---|---|
| Java 后端 | `/home/szf/data/repo/RAG-SRC/gien-rag.zip`（27MB，git branch main） | `services/rag-java/` | 1426 文件 / 40MB | Spring Boot 3.2.6 + Spring Cloud 2023.0.1 + SCA，8 模块 |
| Python 算法 | `rag-alg-service-api.zip`（9.1MB，git branch dev） | `services/rag-alg/` | 525 文件 / 14MB | 4 组 FastAPI 服务 + deepdoc 解析引擎 |
| 前端 | `ai-plateform.zip`（272MB，git branch prod） | `frontend/plateform/` | 2325 文件 / 322MB | React18 + Vite5 + antd5 |
| 公共组件库 | `mxmodules.zip`（178MB） | **未入仓**（`/home/szf/data/dev/r12-src/mxmodules`） | 216MB | 其产物以 `@mxmweb/*`、`@gientech/modual` 发布在 npm 镜像，前端直接按版本消费；不入仓避免 216MB 冗余 |

核对方式：`unzip -l` 文件数与解压后 `find | wc -l` 一致；三仓 `.git` 均保留提交信息（打包时为 2026-01-21 快照）。
**注意**：`ai-plateform` 的 `public/font/*.TTF`（48MB）与 `dist` 属静态资源/构建产物，随源码入仓但不参与构建逻辑。

## 1. 环境替代（A 系列，均为"缺外部设施"的等价替换，不改业务语义）

| 编号 | 原依赖 | 替代 | 原因（事实） | 影响面 | 复核条件 |
|---|---|---|---|---|---|
| A-01 | 达梦 DM8（`com.dameng:Dm8JdbcDriver18:8.1.1.49`，`${dm.url}` 数据源） | MySQL 8.4（库名仍为 `gienrag`，避免硬编码 schema 报错） | DM 驱动不在公网 Maven、无授权 DM 实例 | 驱动 + 方言；Mapper 中 `gienrag.` 硬编码 schema 因同名而无需改 | 若上线环境为 DM，需回填驱动并按 DM 校验 DDL |
| A-02 | 内网私有 starter `com.gientech:gien-starter-{swagger,file-storage,redisson,easyexcel}:0.0.1-SNAPSHOT` | 本仓等价实现四个模块（artifactId 同名同版本，保持业务 pom 零改动） | 内网 Nexus `10.2.22.20:8082` 不可达，公网无该制品（51 个业务文件 import） | 见 §2 清单；已覆盖 storage/redisson/easyexcel/swagger 全部被引用符号 | 若取得原始 starter jar，可替换并做二进制对比 |
| A-03 | Nacos 配置中心（内网 `10.15.12.13:8848` 等，`spring.config.import: optional:nacos:`） | 配置版本化为各服务 `application-r12.yml`（外置副本 `platform/r12/conf/<svc>/`），Nacos **只保留服务发现** | 内网 Nacos 不可达，且其中的 data-id 内容不在交付物内 | `lb://` 路由与 Feign 服务发现行为不变（已实测 5 服务注册 + 网关转发 200） | 若获得原 Nacos 导出，可做逐键等价核对 |
| A-04 | 达梦/内网 ES/Milvus/MinIO/RocketMQ 地址 | 本机容器（ES 8.13.4 / Milvus 2.5.6 / MinIO / MySQL 8.4 / Redis 7.4 / RocketMQ 4.9.7 / Nacos 2.3.2） | 内网中间件不可达 | 端口全表见 `platform/r12/R12-ENV-CONTRACT.md` | 迁移到目标环境时仅改地址 |
| A-05 | OCR/layout/TSR 权重（`InfiniFlow/deepdoc`，仓库 .gitignore 排除） | 经 `hf-mirror.com` 获取并落 `platform/r12/models/ocr_models`；layout 回退 2024-03 版（新版 postprocess 不兼容，见 §4） | huggingface.co 不可达 | 解析能力（OCR/版面/表格）真实可用，非降级 | 升级 layout 需先修 postprocess |
| A-06 | 内网 LLM/Embedding/Rerank 推理服务 | 本机独立服务化：`bge-m3`(18090, dim1024) / `bge-reranker-v2-m3`(18091) / `Qwen2.5-7B-Instruct-Q4_K_M`(18092, llama.cpp CUDA) | 内网推理服务不可达 | 全部 OpenAI 兼容，业务侧只改 URL | 换模型仅改地址与 `model_info` 登记 |
| A-07 | `jodconverter-spring-boot-starter` 自动装配 | 显式装配 `LocalOfficeManager + LocalConverter`（`R12OfficeConverterConfig`） | 该 starter 4.4.x 用 Boot2 `spring.factories`，Boot 3.2 不加载 → `DocumentConverter` 无 Bean 启动失败 | 仅 doc/ppt→PDF 预览通路 | starter 升级到 Boot3 版本后可回退 |
| A-08 | （新增）无 | `Qwen2.5-VL-3B`(18093) 作为**可选增强** | 解析链路的图片描述需要视觉模型；18092 为纯文本模型 | VLM 不可用时解析必须降级为纯 OCR 且仍 200（`R12-FIX-PARSE D-1`） | 有更强 VLM 时替换 |
| A-09 | —— | `index_data_config_py` 由算法角色单点发布，其余角色只引用 | 多角色并行会互相覆盖同一 data_id | 索引/解析两侧端口口径一致 | — |
| A-10 | —— | doc-parse 写索引走**代理**（`es_server.port=19527`、`milvus_server.port=19526`），本体连接另用 `*_conn_config.*.port`（19200/19630） | 代码中两套端口语义不同，混用会 404 | 解析落库链路 | — |

## 2. A-02 兼容模块提供的能力面（与业务调用点一一对应）

| 包 | 类 | 被引用次数 | 关键语义 |
|---|---|---|---|
| `com.gientech.start.storage.utils` | `FileStorageUtils` | 12 文件 | `putObject/putObjects/getInputStreamByUrl/getInputStream/getMediaTypeByteArrayByUrl/getObjectNameFromUrl/isExistedFile/listFolderFiles`；`filePath = endPoint/bucket/object` |
| `com.gientech.start.storage.properties` | `StorageProperties` / `Properties` | 8 文件 | `getDefaultStorageProperties().getEndPoint()/getBucketName()/getDomain()`、`getDefaultPlatform()`、`getByPlatform()` |
| `com.gientech.start.storage.model` | `FileInfo` | 6 文件 | `getFilePath/getFileName/getObjectName/getFileSize(Double)`——注意 `setFileSize` 调用方为 `Double` |
| `com.gientech.start.storage.exception` | `FileStorageException` | 16 文件 | 运行时异常 |
| `com.gientech.start.redisson.utils` | `RedissonUtils` | 15 文件 | `set/get/exists/deleteKey/expireKey/hashPut/hashGet/zscoreAddAsync/getFixZSetMembers/removeZSetMemberAsync/removeAllZSetMembers`，含 `Long`+`ChronoUnit`/`TimeUnit` 重载 |
| `com.gientech.start.redisson.lock` | `RedissonLock` | 1 文件 | **必须可注入**（`@Autowired private RedissonLock`），非注解 |
| `com.gientech.start.easyexcel.template` | `BaseExcelService<T>` | 5 文件 | `importData(file, clazz[, objects...])`、`exportData(name, data, clazz, ExcelTypeEnum, response)`；失败行由子类写入传入 `failList` |
| `com.gientech.start.easyexcel.result` | `ExcelImportResult<T>` | 2 文件 | `getFailList/setFailList/getSuccessList` |
| `com.gientech.start.easyexcel.dto` | `BaseDTO` | 6 文件 | 带 `errorMsg` |
| `com.gientech.start.easyexcel.utils` | `SpringContextUtil` | 1 文件 | `getBean(Class)` |
| `com.gientech.start.swagger` | `GienSwaggerConfiguration` | 5 处 `scanBasePackages` | 最小 OpenAPI 元数据 + springdoc 依赖传递 |

## 3. 编译/启动期缺陷修复（R12-FIX，均为原工程在"空库 + 公网依赖"下暴露的真实缺陷）

| 编号 | 现象 | 根因 | 修改 | 影响 |
|---|---|---|---|---|
| R12-BUILD-01 | `NoSuchFieldError: JCTree$JCImport.qualid` | Lombok 1.18.24 不支持 JDK21 | `lombok.version` 1.18.24 → 1.18.32 | 编译期；不改代码 |
| R12-BUILD-02 | `程序包 org.apache.tika.utils 不存在` | tika 原由内网 starter 传递提供 | 根 pom 显式声明 `tika-core:2.9.2` | 编译期 |
| R12-BUILD-03 | 构建卡在 `10.2.22.20:8082` | 根 pom 声明了内网 Nexus `repositories`/`distributionManagement` | 删除内网仓库声明，改用镜像 settings（`platform/r12/maven/settings-r12.xml`） | 仅构建可达性 |
| R12-BUILD-04 | `No spring.config.import property has been defined` | SCA 的 import-check 在无 Nacos 配置时强校验 | `spring.cloud.nacos.config.import-check.enabled=false`（配置侧） | 不影响服务发现 |
| R12-FIX-DDL-01 | `department_info` 建表失败：`Incorrect table definition; there can be only one auto column` | `DepartmentInfoDO.seq` 误标 `isAutoIncrement=true` | 去掉该列的 `isAutoIncrement` | 该列由业务赋值，不自增 |
| R12-FIX-DDL-02 | `knowledge_base_list` 建表失败：`Duplicate column name 'table_file_paths'` | `KnowledgeBaseListDO.sourceId`（Long）被 `@Column(name="table_file_paths")` 误映射 | 标 `@TableField(exist=false)`（全仓无读写） | Java 字段保留，不落库 |
| R12-FIX-DDL-03 | 启动失败 `redissonLock ... could not be found` | 兼容模块把 `RedissonLock` 实现成注解 | 改为可注入 Bean（同时保留 lock/unlock API） | 调用点原本已注释 |
| R12-FIX-BOOT-01 | `DocumentConverter` 无 Bean | 见 A-07 | 显式装配 | 见 A-07 |
| R12-FIX-BOOT-02 | `FeignClientSpecification ... already defined` | 同名 Feign 客户端重复注册 | `spring.main.allow-bean-definition-overriding=true` | 全局配置项 |

> 说明：`R12-FIX-DDL-01/02` 是"ORM 推导 ≠ 实际 DDL"的直接证据——生产库此前是人工 DM 表结构，
> 这两个错误在真实建表时才暴露；本仓因此对 `gienrag` 库采用 **actable 自动建表 = 新建空库初始化**，
> 不声称"旧库兼容已验证"（见 §6）。

## 4. 解析侧改造（parse 角色提交，编号沿用其报告）

| 编号 | 内容 | 性质 |
|---|---|---|
| R12-FIX-PARSE-01 | `controller.py` 排序取 `page_number[0]` 时 docx 表格块该字段为空 → 整篇 500；改为兜底 0 | 真实缺陷修复 |
| A-05-layout | `layout.onnx` 回退 2024-03 版（新版输出格式与仓内 postprocess 不兼容，实测 IndexError） | 版本回退，留 `.bak` 与非兼容证据 |
| R12-FIX-PARSE D-1/D-2/D-3 | 图片块文本改为 `OCR ∪ VLM` 且 VLM 不覆盖；二次多模态幂等化；`multi_modal_max_workers` 默认 1 + 单图失败降级；四处补 timeout | 由 TL 批准，见 `platform/r12/status/parse.md` §15 |

## 5. 算法服务改造（alg 角色提交）

| 编号 | 内容 |
|---|---|
| R12-ADAPT-ALG-01 | `llm_service.py` 中 `text_tracing(...)` 实参与签名不符（且传入不存在的 `finally_flag`）导致 `/llm_open_chat` 必崩；按同文件正确用法修复，保留溯源能力 |
| （其余见 `platform/r12/status/alg.md`） | 依赖版本处置（pyyaml 6.x 等）、可选依赖惰性化、ES IK 插件安装或降级登记 |

## 6. 数据库语义声明（必须与验收报告口径一致）

- 本环境 `gienrag` 库为 **actable 依据实体新建的空库初始化**（30 张业务表），
  不是从生产 DM 迁移而来；因此**不声称"旧库兼容/迁移已验证"**。
- 字段类型、可空、默认值来自实体注解，与生产实际 DDL 可能不同（`R12-FIX-DDL-01/02` 即为反例）。
- 若后续要验证迁移，必须取得真实 DM DDL 快照后另立任务，不能复用本环境结论。

## 7. 前端改造（fe 角色提交）

| 编号 | 内容 |
|---|---|
| R12-FE-01 | `vite.config.ts`：后端由内网 `10.15.12.11` 改为本机网关 `127.0.0.1:8088`，dev 端口 8888→15174，补 `/auth`、`/index`、`/qa`、`/sensitive`、`/graph`、`/proxy`、`/cecProxy`、`/minio` |
| R12-FE-02 | `ModuleTest/FormContainer/index.tsx` 中 `Icon-link.svg` → `icon-link.svg`（Windows 大小写不敏感遗留，Linux 构建 ENOENT） |
| 已知问题 | 12 条 `[vite:css] Parse error`（tailwind calc 嵌套）与 61 条 css url 未解析（KaTeX 字体），不阻塞构建，样式风险由 QA 抽样确认 |

## 8. 明确**未**做的事（防止被误读）

- 未 fork 或另写 Python 平台；未把 Java 缩成网关；未引入 SaaS 多租户。
- 未把模板拼接/字符 bigram/演示 HTTP 服务作为正式链路的替代（主链真实调用 18090/18091/18092）。
- 未删除任何失败场景、未降低断言、未扩大忽略目录。
- 未关闭任何 P0，未伪造独立 QA，未声称生产可发布。
- GraphRAG 未从三轮范围删除，R12 只做"图谱服务可启动性"与缺口登记，实体/PPR/社区摘要留 R13。
