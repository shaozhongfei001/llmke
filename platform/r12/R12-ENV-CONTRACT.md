# R12 环境契约（唯一共享事实源）

版本：r12.1　生成时间：2026-10-25　维护：TL
本文件是 R12 各角色共享的端口/路径/命令事实。任何角色发现与本文件不符，先记录到
`platform/r12/status/<role>.md`，不要私自改别人的目录。

## 1. 拓扑与端口（全部与机器上既有 WeKnora/yuxi/GITS 演示环境隔离）

| 组件 | 地址 | 说明 |
|---|---|---|
| MySQL 8.4 | 127.0.0.1:13306 | db=`gienrag`，root 口令见 `platform/r12/.env` |
| Redis 7.4 | 127.0.0.1:16379 | 带 requirepass，见 .env |
| Elasticsearch 8.13.4 | http://127.0.0.1:19200 | 单节点，security 关闭 |
| MinIO | 127.0.0.1:19000（console 19001） | AK/SK 见 .env，bucket=`r12-rag` |
| Milvus 2.5.6 | 127.0.0.1:19630 | standalone（etcd+minio 在 compose 内网） |
| Nacos 2.3.2 | http://127.0.0.1:18848/nacos | 配置中心 + 服务发现，auth 关闭 |
| RocketMQ 4.9.7 | namesrv 127.0.0.1:19876 / broker 127.0.0.1:10911 | 解析任务 MQ |
| Java 网关 | 0.0.0.0:8088 | 对外唯一入口 `/auth/** /index/** /qa/** /graph/** /sensitive/**` |
| rag-auth-service | 0.0.0.0:18081 | context-path 见 Nacos 配置 |
| rag-index-service | 0.0.0.0:18082 | |
| rag-qa-service | 0.0.0.0:18083 | context-path `/qa` |
| rag-graph-service | 0.0.0.0:18084 | |
| sensitive-words-service | 0.0.0.0:18085 | |
| alg_doc_parse_service | 0.0.0.0:12340 | Python 解析 |
| alg_llm_inference_service | 0.0.0.0:19996 | Python LLM 编排 |
| alg_retrieval_service | 0.0.0.0:19995 | Python 混合检索 |
| index_vector_service | 0.0.0.0:19526 | Milvus 代理 |
| index_fulltext_service | 0.0.0.0:19527 | ES 代理 |
| index_structure_service | 0.0.0.0:19528 | MySQL 代理 |
| index_graph_service | 0.0.0.0:19529 | Nebula 代理（R12 不启用） |
| embedding 服务 | http://127.0.0.1:18090/v1/embeddings | OpenAI 兼容 |
| rerank 服务 | http://127.0.0.1:18091/v1/rerank | 兼容 `{query,documents}` |
| 本地 LLM | http://127.0.0.1:18092/v1/chat/completions | OpenAI 兼容，支持 stream；Qwen2.5-7B-Instruct Q4_K_M |
| 本地 VLM | http://127.0.0.1:18093/v1/chat/completions | OpenAI 兼容，支持 image_url；Qwen2.5-VL-3B，**仅 CPU、串行、慢**；属“可选增强”，VLM 不可用时解析必须降级为纯 OCR 且仍 200 |
| 前端 dev | 0.0.0.0:15174 | vite |
| 前端生产 | 0.0.0.0:18088 | nginx 静态 + 反代 |

## 2. 目录所有权（并行修改边界）

| 角色 | 独占目录 |
|---|---|
| TL（主控） | `platform/r12/**`（除 models/）、`services/rag-java/**`、`docs/r12/**`、根 pom |
| 前端 | `frontend/plateform/**` |
| 模型与制品 | `platform/r12/models/**`、`platform/r12/venvs/models/**` |
| 解析 | `services/rag-alg/alg_doc_parse_service/**`、`platform/r12/venvs/parse/**` |
| QA | 只读；产物写入 `platform/r12/qa/**` |

禁止：`git add` 整目录、删除他人文件、修改 `docs/policies/**` 与既有 `contracts/**`。

## 3. 统一运行约定

- Java 一律 `-Dspring.profiles.active=r12`，JVM 21。
- Python 服务一律独立 venv，禁止装进系统 Python。
- 所有服务日志写 `platform/r12/logs/<name>.log`，PID 写 `platform/r12/run/<name>.pid`。
- 启停入口统一用 `platform/r12/bin/r12ctl.sh`（运行中逐步补齐）。

## 4. 适配决议（TL 已决，需在各角色输出中引用编号）

| 编号 | 决议 | 影响 |
|---|---|---|
| A-01 | 达梦 DM8 → MySQL 8.4（无 DM 授权服务与驱动制品） | 驱动与方言；库名保留 `gienrag` |
| A-02 | 私有 starter（gien-starter-*）以本仓 `gien-compat` 模块等价实现 | 仅边界适配，业务代码不改 |
| A-03 | Nacos 由内网 10.x 改为本机 18848，配置由 `platform/r12/nacos/publish.py` 落库 | 配置内容等价重写 |
| A-04 | 服务发现保留 `lb://`，由 Nacos 注册表解析 | 网关/Feign 不改 |
| A-05 | OCR/layout/tsr 权重缺失时由 hf-mirror 拉取并落到 `platform/r12/models/ocr_models` | 首次需联网 |
| A-06 | LLM/Embedding/Rerank 独立服务化，OpenAI 兼容 | 不把本机装 torch 当唯一前提 |
| A-08 | VLM（18093）纳入 R12 契约，但定位为可选增强 | 含图片文档在 VLM 不可用时必须降级为纯 OCR（R12-FIX-PARSE D-1），不得整篇失败 |
| A-09 | `index_data_config_py` 为索引侧唯一权威配置，由 alg-ops 发布，其它角色只引用不覆盖 | 避免多角色互相覆盖同一 data_id |
| A-10 | doc-parse 写索引走**代理**：`es_server.port=19527`、`milvus_server.port=19526`；本体连接另用 `es_conn_config.es_connect.port=19200` / `milvus_conn_config.milvus_connect.port=19630` | 两套端口语义不可混用 |
| A-11 | Java 侧配置不依赖 Nacos 配置中心（版本化为 `application-r12.yml`），Nacos 仅用于服务发现 | 配置可 diff、可回滚；避免配置中心成为单点 |
| A-12 | 本地 LLM/VLM 未设 API Key 且仅监听回环，**不得直接对外暴露**，对外一律经 Java 服务 | 安全边界 |
