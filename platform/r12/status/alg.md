# R12 算法侧（Python）服务状态报告

- 角色：alg-ops（Python 算法服务：索引 / 检索 / LLM 编排）
- 工作根：`/home/szf/data/dev/llmke-r12`
- 生成：2026-10-25 05:10（本机时间）
- 覆盖服务：`index_vector_service`(19526)、`index_fulltext_service`(19527)、`alg_retrieval_service`(19995)、`alg_llm_inference_service`(19996)
- 汇报对象：team-lead（TL）

---

## 0. 结论

四个服务**全部启动并完成真实链路验证**，无一处降级为"字符匹配/固定分数/模板拼接"：

| 服务 | 端口 | 状态 | 关键实测 |
|---|---|---|---|
| index_vector_service | 19526 | RUNNING（pid 4177659） | 建库/建集合(dim=1024)/建索引/写 4 条真实向量(8.74s)/换词语义召回 top1=0.7562 |
| index_fulltext_service | 19527 | RUNNING（pid 4172859） | 建索引(IK 生效)/写 4 条中文/中文关键词召回 score=0.9606，41ms |
| alg_retrieval_service | 19995 | RUNNING（pid 4185013） | ES+Milvus 双路 → RRF(score=Σ1/(5+rank)) → rerank（含**次序反转**证据） |
| alg_llm_inference_service | 19996 | RUNNING（pid 4185162） | `/llm_open_chat` 真实流式 22~40 帧、首帧 0.28~0.74s；`/llm_check_model` 三类模型全 200 |

**ES IK 插件已成功安装，未降级**（`analysis-ik 8.13.4` 已加载，中文切词实测见 §4）。

**已改 8 处源码**（编号 01/03/04/05/06/07/08/09，02 为预留未用），全部带 `R12-ADAPT-ALG-0x` 注释编号，明细见 §8：其中 5 处是**服务级硬缺陷**（不修则 500 / import 崩 / 接口 404 / Java 侧解码失败），1 处入口校验前置（500→422），3 处依赖惰性化。

**给上游的两条强约束**（已单独发给 TL 与 parse-ops）：
1. `/llm_check_model` 的 `model_info.type` **必填**（1=LLM / 2=Embedding / 3=Reranker / 4=多模态），不传 → 500 `KeyError: 'type'`。
2. 检索返回链要求 `metadata.file_id` 可 `int()`；Milvus 的 `page_number`/`labels`/`pic_*`/`text_parent_id_list` 必须是**真 list**；`chunk_index`/`status`/`faq_type` 必须是**数字**。

---

## 1. 启动 / 停止 / 健康检查

控制器（我维护，落在 `platform/r12/run/`，只动我这 4 个服务）：

```bash
R12=/home/szf/data/dev/llmke-r12/platform/r12
$R12/run/algctl.sh start|stop|restart|status|logs [服务名|all]
```

单一服务的等价手写命令（`index_fulltext_service` 为例）：

```bash
SVC=/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_fulltext_service/src/index_fulltext_service_pactera
cd $SVC && \
PYTHONPATH=$SVC \
NACOS_SERVER_ADDRESS=http://127.0.0.1:18848 NAMESPACE= DATA_ID=index_data_config_py GROUP=DEFAULT_GROUP \
LOG_LEVEL=INFO \
nohup setsid /home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python -u fulltext_es_api_start.py \
  > /home/szf/data/dev/llmke-r12/platform/r12/logs/index_fulltext_service.log 2>&1 &
echo $! > /home/szf/data/dev/llmke-r12/platform/r12/run/index_fulltext_service.pid
```

四服务的 env 差异（其余相同）：

| 服务 | DATA_ID | 工作目录 / PYTHONPATH | 入口 |
|---|---|---|---|
| index_vector_service | `index_data_config_py` | `.../index_vector_service/src/index_vector_service_pactera` | `vector_milvus_api_start.py` |
| index_fulltext_service | `index_data_config_py` | `.../index_fulltext_service/src/index_fulltext_service_pactera` | `fulltext_es_api_start.py` |
| alg_retrieval_service | `alg_retrieval_config_py` | `.../alg_retrieval_service` **+ `:.../alg_retrieval_service/app`** | `retrieval_api_start.py` |
| alg_llm_inference_service | `alg_llm_config_py` | `.../alg_llm_inference_service` **+ `:.../alg_llm_inference_service/app`** | `llm_api_start.py` |

- **Nacos 环境变量名实测口径**：源码读的是 `NACOS_SERVER_ADDRESS / NAMESPACE / DATA_ID / GROUP`（见各服务 `utils.py`、`*/config/*.py`），**不是** `NACOS_NAMESPACE/NACOS_DATA_ID/NACOS_GROUP`。`algctl.sh` 以源码实际读取名为准，并顺带导出 `NACOS_*` 别名（源码当前不读，纯运维习惯），**未改源码**。
- **PYTHONPATH 必须含 `app/` 目录**（19995/19996）：这两个服务的模块里既有 `from app.base import ...`，也有 `from base import ...`（如 `app/multiple_retrieval.py:15`、`app/llm_service.py:20`）。只设服务根目录会在 import 期 `ModuleNotFoundError: base`。
- **Nacos 必须在其之前可用**：`milvus_kb_config.py`、`es_kb_config.py`、`app/base.py` 在 **import 期**就调用 `get_config()["..."]`，Nacos 缺配置会直接启动失败（不是运行期降级）。
- 健康检查：`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:<port>/docs` → 四端口均 **200**。
- 日志：`platform/r12/logs/<name>.log`；PID：`platform/r12/run/<name>.pid`（与 R12-ENV-CONTRACT 一致）。
- ⚠️ **pid 陷阱（R12 实测踩过，已在 `algctl.sh` 修掉）**：`nohup setsid <python> ... &` 里 `$!` 拿到的是**包装进程**，真正的 uvicorn 可能是它的子进程；只 `kill` pidfile 里的 pid 会留下孤儿监听者，重启时报 `[Errno 98] address already in use`（我 05:35 就撞到过：旧监听者 pid 4193100 仍在占 19996）。
  现在 `algctl.sh` 改为**以端口为准**：`start` 后用 `ss -ltnpH "sport = :<port>"` 解析真实监听 pid 写进 pidfile；`stop` 同时杀 pidfile pid + 端口监听者，并轮询直到端口释放才返回。`status` 也按端口判定，不再出现"文件里 pid 活着但服务已死"的假阳性。

---

## 2. Nacos 配置（我统一发布）

- 发布脚本（幂等、带回读校验）：`platform/r12/nacos/publish.py`（`--verify` 只校验）
- 权威内容同时落盘：`platform/r12/nacos/<data_id>.yaml`
- 目标：`http://127.0.0.1:18848/nacos`，`namespace=public`（tenant 空串），`group=DEFAULT_GROUP`

| data_id | 文件 md5 | 回读 md5 | 使用者 |
|---|---|---|---|
| `alg_common_py` | （含口令占位，见下） | `61d3371a0f0676ac387bdd2dcf1001b6` | 四个服务（被各自 data_id 覆盖合并） |
| `index_data_config_py` | `e3eb5f50f2bccbfa0138e36785310413` | `e3eb5f50f2bccbfa0138e36785310413` | 19526 + 19527 + **doc-parse**（parse-ops 引用，不再自建同名） |
| `alg_retrieval_config_py` | `1f279a07aba1f54981353a961a135e6d` | 同上 | 19995 |
| `alg_llm_config_py` | `1c6abc254db4d883351962ee1ba25196` | 同上 | 19996 |

`publish.py --verify` 输出（实测）：`[OK] alg_common_py ... match=True` / 其余三项一致 → `RESULT: ALL_OK`。

### 2.1 `index_data_config_py`——两套 port 语义严格分开（TL 第 4 条）

| 键 | 值 | 语义 |
|---|---|---|
| `es_server.port` | **19527** | 本服务**对外监听的代理端口**（doc-parse/检索侧调这个） |
| `es_conn_config.es_connect.port` | **19200** | 代理**向上连**的 ES 本体端口 |
| `milvus_server.port` | **19526** | 代理监听端口 |
| `milvus_conn_config.milvus_connect.port` | **19630** | 连 Milvus 本体 |
| `milvus_conn_config.milvus_database` | `rag_knowledge_base` | 连接别名 + 目标库 |

其余关键项：`es_conn_config.index_similarity=BM25`、`verify_certs=false`（单节点无 TLS）、`milvus_kwargs.index_params={HNSW, IP, M=16, efConstruction=200}`、`search_params={IP, ef=64}`、`insert_batch_size=500`、`insert_concurrency=4`、`enable_question_vector=false`。

### 2.2 `alg_common_py`——模型与数据面（唯一事实源对齐）

```yaml
online_embedding_model.bge-m3:   {server_url: http://127.0.0.1:18090/v1/embeddings, model_id: bge-m3, dim: 1024, key: "", max_tokens: 8192}
embedding_model: bge-m3
rerank_server.bge-reranker-v2-m3:{server_url: http://127.0.0.1:18091/v1/rerank, api_key: "", max_tokens: 400}
rerank_model.model_name: bge-reranker-v2-m3
llm_server:                      {host: 127.0.0.1, port: 18092, api_name: v1/chat/completions}
es_config:                       {host: 127.0.0.1, port: 19527}   # 检索侧走代理
milvus_config:                   {host: 127.0.0.1, port: 19526}   # 检索侧走代理
redis_config:                    {host: 127.0.0.1, port: 16379, db: 0}
compatible_flag: false           # 标准 OpenAI 兼容体（非华为 mindia）
retrieval_top_k: 10 / es_threshold: 0.6 / milvus_threshold: 0.3 / score_threshold: 0.05
```

模型名与 Java `model_info` 表登记值一致：`bge-m3` / `bge-reranker-v2-m3` / `qwen2.5-7b-instruct`。

**口令处理（仓库不留明文）**：落盘文件里 `redis_config.password` 写 `${R12_REDIS_PASSWORD}`，`publish.py` 发布前从 `platform/r12/.env` 注入；若仍有未解析的 `${VAR}` 则**直接失败退出**（防止把占位符发到 Nacos 导致服务静默连错 Redis）。当前 Nacos 上是真实隔离环境口令，19996 启动日志实测 `Redis 连接成功: 127.0.0.1:16379, DB: 0`。

---

## 3. venv 与依赖处置（`platform/r12/venvs/alg`，537M，CPython 3.11.15）

创建方式：`uv venv --python /home/szf/.local/bin/python3.11 venvs/alg`；安装用 `uv pip install -i https://mirrors.aliyun.com/pypi/simple/`（pypi.org 直连不通）。

| 包 | 声明 | 实际 | 处置原因 |
|---|---|---|---|
| pyyaml | `==5.3` | **6.0.2** | 5.3 无 cp311 wheel（TL 已预判） |
| pymilvus | `==2.6.2`（vector）/ `2.6.2` | 2.6.2 | 先试 2.5.4 报 `ModuleNotFoundError: pkg_resources`，改用声明版本 |
| setuptools | 未声明 | **80.9.0** | uv 默认 84 已移除 `pkg_resources`，需回退以兼容 |
| httpx | `==0.23.0` | **0.27.2** | 0.23 与 langchain-core 0.3.72 要求冲突；代码仅用 `AsyncClient/AsyncHTTPTransport/Timeout`，0.27 兼容 |
| aiohttp | 未声明（nacos 传递） | 3.11.11 | nacos-sdk-python 2.0.9 要求 `aiohttp>=3.10.11` |
| tqdm | 未声明（`llm_service.py` 直接用） | 4.67.1 | 源码 `from tqdm import tqdm`，不装则 19996 import 崩 |
| protobuf | 未声明（`_upb` 用） | 7.36.2 | `milvus_kb_service.py:18` `from google._upb._message import RepeatedScalarContainer` |
| **dashscope** | `==1.25.2` | **未安装** | TL 指示本轮不装；改惰性导入（`R12-ADAPT-ALG-05`），仅 `qwen_api` 分支需要 |
| **zhipuai** | `==2.1.5…` | **未安装** | TL 指示本轮不装；改惰性导入（`R12-ADAPT-ALG-03/04`），仅联网搜索需要 |
| Cython / pytest / openai | 声明 | 未安装 | 仅 `setup.py cythonize` 打包与自测用，运行期不需要；`openai` 源码未 import |
| nebula / 其它图库 | — | 未安装 | R12 不启用图谱（`enabled_graph=false`） |

最终关键版本：fastapi 0.109.1 / uvicorn 0.30.1 / pydantic 2.10.4 / loguru 0.7.3 / nacos-sdk-python 2.0.9 / elasticsearch 8.13.2 / pymilvus 2.6.2 / langchain 0.3.27 + langchain-core 0.3.72 + langchain-community 0.3.27 / numpy 1.26.4 / pandas 2.2.3 / tiktoken 0.8.0 / redis 5.2.1。

---

## 4. ES 中文分词（IK 插件）——**已安装，未降级**

事实：`elasticsearch:8.13.4` 容器 `r12-es`（宿主 19200）**原本没有任何插件**，而 `es_kb_config.py` 的 4 套 mapping（主/table_summary/table_chunks/database）全部硬写 `analyzer: ik_max_word` + `search_analyzer: ik_smart`，缺插件时 `/create_es_index` 必 400。

安装步骤（实测，窗口 16s）：

```bash
curl -sSL -o /tmp/elasticsearch-analysis-ik-8.13.4.zip https://get.infini.cloud/elasticsearch/analysis-ik/8.13.4
# md5 = a4adae33a859804ac96f91c9535e27e0   size = 4,617,322 B   （与 release.infinilabs.com 同包同大小）
docker cp /tmp/elasticsearch-analysis-ik-8.13.4.zip r12-es:/tmp/ik.zip
docker exec r12-es bin/elasticsearch-plugin install --batch file:///tmp/ik.zip
docker restart r12-es     # 16s 后 _cluster/health = green
```

证据：

```
$ curl -s http://127.0.0.1:19200/_cat/plugins?v
name         component   version
16f38a206d3a analysis-ik 8.13.4

$ curl -s -X POST http://127.0.0.1:19200/_analyze -H 'Content-Type: application/json' \
    -d '{"analyzer":"ik_max_word","text":"企业信用贷款管理办法"}'
['企业信用', '企业', '信用贷款', '信用', '贷款', '管理办法', '管理', '办法']   # 8 token

$ curl -s 'http://127.0.0.1:19200/_cluster/health?pretty'
cluster_name: r12-rag   status: green   number_of_nodes: 1
```

建索引后回读 mapping 实测：`page_content` → `{"analyzer":"ik_max_word","search_analyzer":"ik_smart","fields":{"keyword":{...similarity:BM25}}}`。

**结论**：**没有走 `standard` 降级分支**，因此不存在"关键词召回率下降"的问题需要登记。TL 要求的降级观察在本轮不适用。

---

## 5. Milvus

- 连接：`127.0.0.1:19630`（`milvusdb/milvus:v2.5.6`），无认证。`GET /healthz` 在 19530 上返回 404 属正常（健康端口是 9091→宿主 19191）。
- **库**：服务启动时 `ConfigManager.conn_milvus` 自动建库，实测 `db.list_database() = ['default', 'rag_knowledge_base', 'graph_base']`（`graph_base` 是上游代码写死一并创建的）。
- **集合**：`index_vector_service` 建 `_r12_alg_test`（前缀 `_` 来自 `generate_collection_name_uuid`，防数字开头非法）。
- **schema 关键项**：`pk` INT64 主键（auto_id=false）、`text` VARCHAR(50000)、**`vector` FLOAT_VECTOR dim=1024**（取自 `online_embedding_model.bge-m3.dim`）、`chunk_index` INT64、`page_number`/`pic_offset_list`/`labels`/`pic_children_id_list`/`text_parent_id_list` 均为 ARRAY。
- **索引**：HNSW / IP / M=16 / efConstruction=200，`create_index` 实测 2.06s。
- 当前库内集合（含 parse-ops 并发落库的产物，说明上传→解析→落库已通）：
  `['_r12_it_parse_001', '_table_summary_r12_it_parse_002', '_table_chunks_r12_it_parse_002', '_r12_alg_test']`。

---

## 6. 真实链路验证（a~d，全部直调真实端点）

> 一键复跑：`platform/r12/venvs/alg/bin/python platform/r12/run/alg_verify.py`
> 完整原始输出留档：`platform/r12/logs/alg-verify.log`
> 语料：4 条中文（3 条业务制度 + 1 条"关键词密集但无实质内容"的台账反例，用于验证 rerank 价值），`file_id=100001..100004`。

### a. index_fulltext_service(19527) 建索引 → 写中文 → 中文关键词召回

```
[del_index 幂等清理]        200 {"code":200,"msg":"索引r12_alg_test删除成功"}   101ms
[create_es_index]          200 {"code":200,"msg":"索引r12_alg_test创建成功"}   309ms
[索引 mapping]              page_content: analyzer=ik_max_word, search_analyzer=ik_smart
[insert_fulltext_documents x4] 200 {"code":200,"msg":"...保存数据成功，共保存4条数据"}  343ms
[ES _count]                {"count":4,"_shards":{"total":1,"successful":1,"failed":0}}

[search_by_custom_param] query='授信额度' total=2  41ms
   score=0.9606 file_id=100004 授信额度与期限变更台账.xlsx :: 授信额度、贷款期限变更台账：本表仅登记历次授信额度与贷款期限调整的时
   score=0.6630 file_id=100001 企业信用贷款管理办法.pdf   :: 企业信用贷款管理办法规定，单户授信额度最高不超过500万元，贷款期限
```

> 说明：`授信额度` 命中 2 条是正确的（台账那条词频高，BM25 给 0.9606），这正是 §6c2 里 rerank 要纠正的场景。

### b. index_vector_service(19526) 建集合/写真实 1024 维向量/换词语义召回

```
[create_milvus_collection]      集合:r12_alg_test创建成功              27ms
[create_milvus_index]          集合:r12_alg_test的索引创建成功        2.06s
[insert_vector_documents_custom x4] 保存数据成功, insert_count=4       8.74s   ← 含 4 次真实 18090 embedding
[milvus_vector_search] query='小企业想申请贷款，最多能批多少钱，可以贷几年？' hits=3  4352ms
   #1 score=0.7562 source=企业信用贷款管理办法.pdf  :: 企业信用贷款管理办法规定，单户授信额度最高不超过500万元，
   #2 score=0.6829 source=流动资金贷款操作规程.pdf  :: 流动资金贷款用于满足借款人日常生产经营周转需求，单笔金额不得
   #3 score=0.6622 source=固定资产贷款管理办法.pdf  :: 固定资产贷款期限原则上不超过十年，项目资本金比例不得低于国家
[milvus_vector_search] query='盖厂房搞建设的钱能借多久？' hits=3  4638ms
   #1 score=0.6863 source=固定资产贷款管理办法.pdf   ← 换成"盖厂房搞建设"，top1 正确切到固定资产贷款
   #2 score=0.6493 source=企业信用贷款管理办法.pdf
   #3 score=0.6354 source=流动资金贷款操作规程.pdf
```

> 两个 query 与语料**没有任何字面重合**（"能批多少钱"/"盖厂房搞建设"都不在原文里），仍正确召回，说明走的是真实 embedding（bge-m3, 1024 维），不是字符匹配。

### c. alg_retrieval_service(19995) ES+Milvus 双路 → RRF → rerank

query = `流动资金贷款单笔金额和期限有什么限制？`，`search_policy=1`（混合）：

```
[rerank=False] 6.47s  code=200
   search_type=['es','milvus'] rrf_rank=1 rrf=0.200000   score=0.6000  file_id=100002 流动资金贷款操作规程.pdf
   search_type=['milvus']      rrf_rank=2 rrf=0.166667   score=0.1667  file_id=100001 企业信用贷款管理办法.pdf
[rerank=True] 11.14s  code=200
   search_type=['es','milvus'] rrf_rank=1 rrf=0.200000   rerank_rank=1 score=0.9882  file_id=100002
   search_type=['milvus']      rrf_rank=2 rrf=0.166667   rerank_rank=2 score=0.0621  file_id=100001

[双路证据] search_type 并集 = ['es','milvus']
[metadata 必备键检查] 缺失 = 无
[顶层必备键检查] page_content/score/rerank_score_rank/rrf_score = True
```

**RRF 计分口径（实测反推，与我读到的源码一致）**：`rrf_k=5`、`query_weight=1`，同一文档被多路/多次命中则**累加** `1/(5+rank)`，命中 3 次且每次都 rank=0 时 `score=0.6`（`log_list.source_rank="[0,0,0]"`）；`rrf_score` 字段是同 `page_content` 去重后的归一化值（0.2）。**去重键是 `page_content`**，`search_type` 会并成 `['es','milvus']`。

返回字段实测：`documents_list[i]` 含 `page_content`、`metadata.{source,file_path,id,search_type,offset,pic_offset_list,chunk_type,position,file_id,page_size,page_number,table_name,labels,chunk_index,revise_date,score,rerank_score_rank,rrf_score,rrf_score_rank}`，顶层含 `score/rerank_score_rank/rrf_score/rrf_score_rank/type/pk/knowledge_base_name/order_num/faq_question/faq_answer`。

### c2. rerank 是否**真的**改变排序（TL 要求的"顺序变化"证据）

同一候选集、同一通道（`search_policy=2` 仅 ES），只切 `enabled_rerank`：

```
query='贷款期限规定'   search_policy=2(仅ES)   rerank=False 0.13s / rerank=True 7.45s
   rerank 前: [(100004, 0.4000), (100003, 0.1667), (100001, 0.1667)]
   rerank 后: [(100003, 0.7065), (100001, 0.6734), (100004, 0.2467)]
   顺序是否变化: True   前=[100004, 100003, 100001]  后=[100003, 100001, 100004]
```

**关键词密集但无实质内容的台账（100004）被从第 1 名压到第 3 名**，两份真正写明"期限规定"的制度被顶上来——证明 rerank（bge-reranker-v2-m3 @18091）的输出真的在决定最终顺序，而不是摆设。
另一组同分决出：query`单户授信额度上限是多少`（仅 ES）rerank 前 `100004:0.2000 | 100001:0.2000`（BM25 同分）→ rerank 后 `100001:0.8826 | 100004:0.0058`。

> ⚠️ **阈值经验（给 Java 侧调参参考，实测 bge-reranker 分值分布极扁）**：强相关 0.67~0.99（0.9882 / 0.8826 / 0.7065），弱相关 0.02~0.25（0.0621 / 0.2467），无关 0.0058 / 0.0000162。`score_threshold` 用 0.05 时，一些"能答但不逐字相同"的问题会被整体清空（实测 query`借钱大概要还多久` 由 2 条 → 0 条）。**建议 Java 侧对非精确匹配场景显式传 `score_threshold`（如 0.001~0.02），不要依赖默认 0.05**。

### d. alg_llm_inference_service(19996) `/llm_open_chat` 真实流式

```
[status] 200 content-type=text/plain; charset=utf-8
[首帧延迟] 0.28s  [总耗时] 0.73s  收到帧数=22
[前 3 帧]
   {"answer": "企业"}
   {"answer": "信用"}
   {"answer": "贷款"}
[最后 3 帧]
   {"answer": "年"}
   {"answer": "。"}
   {"end": ""}
[拼装答案] 企业信用贷款的授信额度通常根据企业的信用评级确定，期限一般为1年至5年。
```

另一轮（`max_tokens=128`）为 40 帧 / 1.65s / 首帧 0.74s；token 级逐帧（"企业"/"信用"/"贷款"…）来自 18092 的 SSE `delta.content`，非本地模板。

### 6.5 耗时汇总（本机，无 GPU 加速，与 parse-ops 并发写库时采样）

| 环节 | 实测 |
|---|---|
| ES 建索引（IK mapping） | 309 ms |
| ES 写 4 条中文（含 refresh） | 343 ms |
| ES 中文关键词检索 | 41 ms |
| Milvus 建集合 / 建索引 | 27 ms / 2.06 s |
| Milvus 写 4 条（4 次真实 embedding） | 8.74 s |
| Milvus 向量检索（top3，含 query embedding） | 4.35 s / 4.64 s |
| 检索全链路 rerank=False（ES+Milvus+RRF） | 6.47 s |
| 检索全链路 rerank=True（+bge-reranker） | 11.14 s |
| LLM 首帧 / 全文（约 40 字） | 0.28~0.74 s / 0.73~1.65 s |

> 单条 embedding / rerank 调用在 CPU 上是百毫秒级，检索链路的主导成本是 **每次请求都要现算 query 向量**（无缓存），以及 rerank 逐条打分；这属于选型事实，不是实现缺陷。

> ⚠️ **时延数据的负载前提（重要，勿直接当性能基线用）**：以上数值全部在**高负载窗口**采样。采样时 `nproc=20`，`load average = 22.6 / 31.0 / 29.7`（1/5/15min），`llama-server`（18090/18091/18092 的后端）单进程占 **1176% CPU**，且 parse-ops 在并发跑解析落库。也就是说 embedding/rerank 的绝对耗时被放大了数倍（同一 Milvus top3 检索在 04:56 是 2.67s，在 05:08 高负载下是 4.35~4.64s）。
> **若要做性能验收，请在安静窗口重测**，或明确标注"含并发 contention"；本报告只主张**功能正确性**（召回/融合/rerank/流式确实生效），不主张性能指标。

---

## 7. 溯源能力与 `/llm_check_model`（两处上游强契约）

### 7.1 `need_trace_source=true` 时引用标签仍能生成（TL 第 3 条要求）

脚本：`platform/r12/run/alg_llm_trace_check.py`，日志：`platform/r12/logs/alg-llm-trace.log`

```
[status] 200  frames=25  耗时=5.65s
[前3帧] ['{"answer": "企业"}', '{"answer": "信用"}', '{"answer": "贷款"}']
[后3帧] ['{"answer": "。"}', '{"answer": "[retrive-tag id=\"trace-001\" image_urls=\"\" fromType=\"0\"][0][/retrive-tag]"}', '{"end": ""}']
[引用标签生成] True
```

即 `text_tracing → trigger_by_rule → attribute()` 全链路可用，`R12-ADAPT-ALG-01` 的修复**没有削弱溯源**（没有删功能、没有改成固定文本）。

**顺带发现的调用约定**：`order_num` 必须放在 document **顶层**。放 `metadata.order_num` 时标签是 `id="None"`（我第一版夹具踩过），移到顶层后变成 `id="trace-001"`。请 Java 侧回传 documents 时按顶层传。

### 7.2 `/llm_check_model` 的必填字段（会阻塞 Java 侧模型登记）

`model_info.type`：**1=LLM**（校验 `choices[0].message.content`）、**2=Embedding**（校验 `data[0].embedding`）、**3=Reranker**（校验 `results[0].relevance_score`）、**4=多模态**。三类实测：

```
[llm_check_model LLM]       http=200 0.37s  {"code":200,"msg":"测试链接成功,模型ID:qwen2.5-7b-instruct符合openai格式,通过'你好'，可返回正确答案:'你好！有什么问题需要我帮忙解答吗？'"}
[llm_check_model Embedding] http=200 4.09s  {"code":200,"msg":"测试链接成功,模型ID:bge-m3符合embedding格式,通过'你好'，可返回正确embedding"}
[llm_check_model Reranker]  http=200 5.75s  {"code":200,"msg":"测试链接成功, Reranker ID:bge-reranker-v2-m3符合格式,通过测试样例可正确进行reranker操作"}
[llm_check_model 缺 type]   http=500 0.01s  服务端 KeyError: 'type'（llm_api_function.py:1020）
```

---

## 8. 源码改动清单（`R12-ADAPT-ALG-xx`）

> 全部改动都只在本人独占目录内（`services/rag-alg/alg_{retrieval,llm_inference}_service/**`、`index_data_service/index_{vector,fulltext}_service/**`），未触碰 `services/rag-java/**`、`alg_doc_parse_service/**`、`frontend/**`。

| 编号 | 文件:行 | 问题（实测） | 改法 | 复验 |
|---|---|---|---|---|
| **R12-ADAPT-ALG-01** | `alg_llm_inference_service/app/llm_service.py:87-134` | `llm_open_chat` 里三处 `text_tracing(full_answer, token, documents)` 与签名 `(token, documents, trace_by_llm, trigger_param, attr_param, web_documents_list, rerank_model_info)->5元组` 不符，尾部还传了不存在的 `finally_flag=True` → `/llm_open_chat` 一进循环就 `TypeError`，接口完全不可用 | 按同文件 `sync_llm_generate()` 的既有正确用法重建溯源状态机（`TriggerConfig` + `AttributeParameter`），逐帧输出格式不变；上游异常 yield `{}` 时跳过（保持原容错意图） | 22/25/40 帧正常流式；`need_trace_source=true` 仍产出 `[retrive-tag id="trace-001"]` |
| **R12-ADAPT-ALG-03** | `alg_retrieval_service/app/multiple_retrieval.py:13` | 模块级 `from zhipuai import ZhipuAI`，R12 未装该包 → 整个检索服务 import 期崩（即使 `enable_web_search=false`） | 删除模块级导入，改注释说明；实际调用走 `WebSearchClient`（已惰性化） | 19995 正常启动；`enable_web_search=false` 检索正常 |
| **R12-ADAPT-ALG-04** | `alg_retrieval_service/app/operators/client/web_search_client.py:6,11,34,51` | 同上（模块级 zhipuai） | 新增 `_load_zhipuai()` 惰性导入，失败抛明确 `RuntimeError`（不静默返回假结果） | 同上 |
| **R12-ADAPT-ALG-05** | `alg_llm_inference_service/app/llm_api_function.py:16,122` | 模块级 `from dashscope import Generation`，R12 未装 → 19996 崩 | 新增 `_load_dashscope_generation()` 惰性导入，仅在 `model_name` 命中 `qwen_api` 分支时使用 | 19996 正常启动；`/llm_check_model` LLM 分支 200 |
| **R12-ADAPT-ALG-06** | `index_vector_service/.../controller/embed_change.py:83-89` | `resolve_vector_dim` 用 `model_name` 索引 `online_embedding_model`，而 `DatabaseConfigModel.model_name` 默认 `None`（Java 调 `/create_milvus_collection` 不带该字段）→ `KeyError` → **接口 500** | `model_name or nacos_config["embedding_model"]` 回落默认模型；优先级（请求体 dim > nacos 模型 dim）不变，不伪造维度 | `/create_milvus_collection` 200，集合 dim=1024 |
| **R12-ADAPT-ALG-07** | `index_fulltext_service/.../base.py`（新增 `StaticCountModel`）、`es_kb_service.py`（新增 `static_count()`）、`view/api/static_count_view.py`（新增）、`view/urls.py`（注册路由） | **接口缺失**：TL 下发的 Java 契约里 19527 需提供 `/static_count`（Java `remote.faq-count.url = http://127.0.0.1:19527/static_count`），但上游源码的全文服务没有该路由，R12 实测 `POST /static_count` → **404**（只有向量服务有） | 新增 `/static_count`：`index_name` 兼容字符串/数组；`col_name`+`col_values` 可选过滤；索引不存在时按 0 计并在 `data.detail` 标 `null`（区分"不存在"与"存在但 0 条"）；返回 `{"code":200,"data":{"count":N,"detail":{index:count}}} ` | 实测：`["r12_alg_test","r12_it_parse_001"]` → `count=5, detail={r12_alg_test:4, r12_it_parse_001:1}`；字符串形式 → `count=4`；不存在索引 → `count=0, detail={idx:null}` |
| **R12-ADAPT-ALG-08** | `index_fulltext_service/.../base.py::InsertDataModel` | 脏 payload 变**不透明 500**：传 `{"type":"text","document_list":[{"id","content_with_weight","source"}]}` 时在 `controller/es.py:169` 抛 `KeyError: 'metadata'`，调用方拿不到"缺哪个字段" | 加 `model_validator` 前置校验（`type=="database"` 除外，它走 columns 结构）：每条必须是 `{"page_content": str, "metadata": object}`，否则 **422** 并给出实际 keys 与修复提示 | 脏 payload → `HTTP 422` + `document_list[0] 结构不合法：… 实际 keys=['id','content_with_weight','source']`；Java 真实形态（`page_content`+`metadata{source,document_id,file_id,folder_id,knowledge_base_name}`）→ 200 且计数 +1 |
| **R12-ADAPT-ALG-09** | `alg_llm_inference_service/app/llm_service.py`（新增 `sse_response()`/`_sse_frames()`，替换 4 处 `StreamingResponse`） | **流式分帧与 Java/前端不兼容**：Java `AiServiceImpl:917-928` 用 WebClient `.accept(TEXT_EVENT_STREAM)` + `.bodyToFlux(String.class)`，Spring 走 `ServerSentEventHttpMessageReader`；而服务原返回 `media_type="text/plain"` + `{"answer":"银行"}\r\n` 单换行帧、无 `data:` 前缀 → Java 抛 `WebClientResponseException: 200 OK`（报错栈在传输/解码层），前端只拿到兜底文案「模型没有返回」 | 统一包一层 SSE：`media_type="text/event-stream"`、每帧 `data: <原 JSON>\n\n`、结束帧 `data: {"end": ""}\n\n`，**JSON 内容一字不改**；附 `Cache-Control: no-cache`、`X-Accel-Buffering: no`。覆盖 4 个流式端点：`/llm_open_chat`、`/llm_generate_sync`、`/llm_rotate_answer`、`/llm_multi_model` | 实测 4 端点均 `content-type: text/event-stream; charset=utf-8`；`/llm_open_chat` 27 data 帧 + 1 end 帧、**非 SSE 行数=0**；`need_trace_source=true` 的引用标签仍在帧内（`[retrive-tag id="trace-001"]`）；`/llm_generate_sync`、`/llm_rotate_answer` 各 28 帧、首帧 `data: {"answer": "企业"}`、末帧 `data: {"end": ""}` |
| （非源码）`R12-ADAPT-ALG-02` | — | 预留编号，**未使用**：核查 `reranker_service.get_reranker_score` 时怀疑返回值类型与 `merge_and_rerank` 不匹配，细读 161-175 行确认**已正确**把 rerank 分数写回 `document.metadata["score"]`，故**未改** | — | §6c2 已证明 rerank 生效 |

新增的非源码交付物（均在本人目录）：`platform/r12/run/algctl.sh`（启停）、`platform/r12/run/alg_verify.py`（a~d 验证）、`platform/r12/run/alg_llm_trace_check.py`（溯源 + check_model）、`platform/r12/nacos/publish.py`（配置发布）。

---

## 9. 降级项与缺失项（无静默降级）

**没有发生任何"降级"**：检索是真的 ES(BM25+IK) + Milvus(HNSW/IP) + RRF + bge-reranker；LLM 是真的 18092 qwen2.5-7b 流式。以下项属**本轮范围外/未启用**，逐条说明：

| 项 | 状态 | 影响 | 依据 |
|---|---|---|---|
| ES IK 插件 | **已装，无降级** | 无 | §4 |
| 图谱检索（`graph_config` → 19529） | 端点未起，`enabled_graph` 默认 false | 图谱通路本轮不验证；配置里保留占位以免 `KeyError` | TL 任务书未列图谱服务 |
| 联网搜索（zhipuai） | SDK 未装，`enable_web_search` 默认 false | 请求 `enable_web_search=true` 会抛明确 RuntimeError（不是返回空列表假装成功） | TL 指示不装 zhipuai |
| FAQ 双向量（`enable_question_vector`） | 关闭 | `faq_*` 集合不建 `question_vector` 索引；FAQ 通路本轮未验证 | 无 `faq_` 集合需求 |
| 多版本 chunk 扩召回 | `multi_version.url` 指向 `http://127.0.0.1:18082/index/kbFile/multiVersion`（**Java 侧不存在该端点**），实测取 404 后按源码 `else` 分支返回 `None` | 多版本扩召回不生效（不影响单版本检索） | 源码 `server_config['multi_version']['url']` 在 try 之外取值，缺键会 KeyError，故必须是占位 URL 而非删键 |
| `qwen_api` / dashscope 分支 | 未安装，运行时抛明确错误 | R12 全部走 OpenAI 兼容 18092 | TL 指示不装 dashscope |
| 表格/数据库问答（`enable_database`） | 无 database 服务 | 默认关闭 | 无对应依赖 |

---

## 10. 与协作方的契约核对

### 10.1 与 parse-ops（doc-parse 落库）

我核对了 `alg_doc_parse_service/server/indexing_utils.py` 的**实际代码**（parse-ops 消息里写的字段名与代码不一致，以代码为准）：

- ES：`indexing_utils.py:27-31` → `{"index_name", "document_list", "duplicate_flag"}` ✅ 与 `InsertDataModel` 一致；首批 `duplicate_flag=true` 会触发"按 source 先删后插"的去重语义。
- Milvus：`indexing_utils.py:197-203` → `{"collection_name", "model_name", "document_list", "db_name", "duplicate_flag"}` ✅ 与 `InsertDataModel` 一致（**不是** `index_name`/`embed_model`）。
- 响应体：两接口成功均为 `{"code":200,"msg":"...","data":null}`，parse-ops 只校验 `code==200` 是正确的。
- 命名：`collection_name` **原样**使用 `index_name`，唯一变化是 `generate_collection_name_uuid()` 加前导 `_`（如 `r12_it_parse_001` → `_r12_it_parse_001`）；ES index 仅小写归一。

#### 10.1.1 集合/索引命名规则的实测真值（用服务里的真函数跑，不是读代码推断）

| 输入 | Milvus 实际集合名 | 说明 |
|---|---|---|
| `r12_it_parse_001` | `_r12_it_parse_001` | 合法名：只加前导 `_` |
| `table_summary_r12_it_parse_002` | `_table_summary_r12_it_parse_002` | 同上 |
| `R12_IT_Parse_001` | `_R12_IT_Parse_001` | **大写保留**（而 ES 侧 `is_index_lower()` 会转小写 → 两侧不一致） |
| `r12-it-parse-001` | `_b874e702_9e02_54b4_a794_d1e8eb6aa260` | 含 `-` → 先 `uuid5(NAMESPACE_DNS,name)` 再 `-`→`_` |
| `中文知识库` | `_e2ca392e_44a2_5c6f_947c_05fba0f4d3ff` | 含中文 → 同样 uuid5 |

**给上游/QA 的命名约束**：ES 与 Milvus 共用的索引名（知识库名）请**只用 `[a-z0-9_]`**。否则 ① 带 `-`/中文时 Milvus 名变成不可预测 uuid5（按名字找不到）；② 带大写时 ES 小写、Milvus 保大写造成两侧不一致。

**给检索侧的口径（易错）**：调我的代理（19526 `/milvus_vector_search`、19995 `/retrieval_documents`、19527 `search_by_custom_param` 的 `index_name`）时**传原始名，不要自己加 `_`** —— 19526 内部 `search_collection()`（`milvus_kb_service.py:698`）会再跑一次同一个函数。只有**直连 pymilvus（19630）做校验**时才用 `_<index_name>`。

**写入量校验口径**：
- **Milvus**：用 `count(*)` 而不是 `num_entities`。实测同一时刻 `_table_summary_r12_it_parse_002`: `num_entities=0` 但 `count(*)=1`（`num_entities` 只统计已 flush/seal 的段）。
- **ES**：本服务 `/insert_fulltext_documents` 在**返回 200 之前**已执行 `es.indices.refresh(index=...)`（`controller/es.py` 末尾），所以**拿到 200 后立刻 `_count` 是准的**，不需要重试。之前我写的"refresh=False 可能导致 _count 偏小"不准确，已更正；只有"多批次仍在并发写入的进程内"才有极短窗口。

#### 10.1.2 B 项旁证（parse-ops 落库，我方只读核验）

- ES：`r12_it_parse_001`=1、`table_summary_r12_it_parse_002`=1、`table_chunks_r12_it_parse_002`=1（`_cat/indices`；`health=yellow` 是单节点 1 副本的正常态，不影响读写）
- Milvus：`_r12_it_parse_001`=1、`_table_summary_…`=1、`_table_chunks_…`=1（`count(*)`），字段形态抽检：`file_id="9001"`（可 int）、`chunk_index=0`(int)、`page_number=[1×6]`(真 ARRAY)、`offset="[[0, 203]]"`(JSON 串)、`source="r12-rag/fixtures/cn-digital.pdf"`、`vector` dim=1024
- `embed_model` 传 `bge-m3` 是正确值（必须精确等于 `online_embedding_model` 的键名，否则 `resolve_vector_dim` 抛"未在nacos配置中找到模型 XXX 的向量维度"→ 500）

#### 10.1.3 跨链路端到端验证：**解析侧真实落库 → 我的检索服务**

用 parse-ops 真实解析落库的 `r12_it_parse_001`（`cn-digital.pdf`，1 chunk）直接打 `19995 /retrieval_documents`，`search_policy=1`、`top_k=5`：

| query | docs | search_type | rerank score | file_id | 耗时 |
|---|---|---|---|---|---|
| 上海浦东发展集团的授信额度和审批结论是什么？ | 1 | `['es','milvus']` | **0.9976** | `9001`（**int**） | 1.99 s |
| 哪家客户已用额度 3200 万，五级分类正常？ | 1 | `['es','milvus']` | **0.9157** | `9001`（int） | 0.87 s |

返回 metadata 完整：`offset="[[0, 203]]"`、`page_number=[1,1,1,1,1,1]`、`position=[[[183.0,174.0],…]]`、`chunk_index=0`；`file_id` 经 `int()` 后为 `9001`（验证了 §9 那条"file_id 必须可 int"的约束在真实数据上成立）。
→ **"解析 → 落库 → 双路召回 → RRF → rerank"全链路在真实数据上成立**，不是只在自造语料上成立。

**发现一处上游元数据不一致（低危，已告知 parse-ops）**：该文档 `metadata.knowledge_base_name = "r12-index-probe"`，而索引/集合名是 `r12_it_parse_001`。不影响检索（集合名来自请求参数），但检索结果会**原样回显**该字段（`retrieval_service.py:268`、`retrieval_fun_tool.py:159` 写进 `log_list`），若 Java/QA 用返回的 `knowledge_base_name` 做归属展示或二次过滤，会与用户所选知识库不符。建议解析侧把该字段对齐为真实知识库名。
- 已提醒 parse-ops 的 3 个数据约束：`file_id` 必须可 `int()`；ARRAY 字段传真 list；`chunk_index/status/faq_type` 传数字、`offset/position` 传字符串。
- 旁证：Milvus 现已出现 parse-ops 的 `_r12_it_parse_001`、`_table_summary_/table_chunks_r12_it_parse_002`，ES 亦有对应 index，说明**上传→解析→落库确实已打通**。

### 10.2 与 Java 侧（rag-qa / rag-index）

- `POST /retrieval_documents` 请求：`query`、`knowledge_base_name`、`top_k`、`top_n`、`search_policy`(1混合/2仅ES/3仅Milvus)、`enabled_faq`、`enabled_rerank`、`score_threshold`、`rerank_model_info`、`condition_json`、`condition_logic_operations`、`dense_weight` 等（见 `app/base.py::QARetrieveConfig`）。
- 返回：`{faq_result_list, database_documents, documents_list, web_documents_list, log_list}`，`documents_list` 每项含 `page_content` / `metadata.{source,file_id,offset,page_number,position,chunk_index,…}` / `score` / `rerank_score_rank` / `rrf_score`（实测已验证，§6c）。
- 向量/全文端点：Java 侧配的 8+10 个路径在 `view/urls.py` 中逐个存在（`/create_milvus_collection`、`/insert_vector_documents_custom`、`/milvus_vector_search`、`/del_doc_by_col`、`/get_doc_by_col`、`/update_by_id`、`/create_milvus_db`、`/create_milvus_index`；`/create_es_index`、`/insert_fulltext_documents`、`/del_doc_by_col`、`/del_index`、`/search_by_custom_param`、`/search_by_page`、`/update_by_id`、`/update_doc`、`/del_by_id`、`/static_count`）。
- `/llm_check_model`：**必须带 `type`**（见 §7.2）。

### 10.3 Java ↔ Python 路由覆盖核对（2026-10-25 05:2x，逐条对照 yml 与实际 `/openapi.json`）

| Java 侧配置（rag-index-service/rag-qa-service `application-r12.yml`） | 我的实际路由 | 结论 |
|---|---|---|
| `19527/insert_fulltext_documents`（faq-sava、faq-sava-es） | ✅ | 通 |
| `19527/update_doc`、`19527/update_by_id` | ✅ | 通 |
| `19527/search_by_page` ×3、`19527/search_by_custom_param` | ✅ | 通 |
| `19527/del_doc_by_col`、`19527/del_index`、`19527/del_by_id` | ✅ | 通 |
| `19527/static_count`（faq-count） | ❌ 原缺失 → **本轮新增（R12-ADAPT-ALG-07）** | 已补 |
| `19996/llm_check_model`、`llm_faq_generate`、`polish_answer_llm`、`llm_simi_question` | ✅（19996 共 14 条路由） | 通 |
| `19995/retrieval_documents`（qa-service `search-docs-url`） | ✅（另有 cec/table 变体） | 通 |
| `19526` 作为 base url + `/del_doc_by_col` | ✅（19526 共 14 条路由） | 通 |
| `/create_es_index` | ✅ 存在，但**Java 源码里没有调用点**（grep 全仓 `.java` 无引用） | 索引实际由 `get_index_mapping_field_async` 在写入时按需自动创建 |

**两条给 Java 的提醒（我不改 Java）**：
1. `/create_es_index` 对**已存在**的索引返回 `code=500 "索引已存在"`（非幂等）。当前无调用点所以无影响；若后续用它做"建库前置"，请先判存在或把 500+`已存在` 当成功，否则重试会被误判为失败。
2. `mapping_body` 语义实测：**传 `{}` 与不传，结果完全一致**（`index_model.mapping_body or ES_INDEX_MAPPING`，空 dict 为假值 → 回落默认）。两个新索引对比实测：`顶层字段=[metadata,page_content,question]`、`page_content.analyzer=ik_max_word/search_analyzer=ik_smart`、`metadata 字段数=36`，完全相同。若观察到"不同"，实际是第二次调用命中了"索引已存在"分支（500）。

### 10.4 流式端点分帧契约：标准 SSE（R12-ADAPT-ALG-09，2026-10-25 05:4x）

Java `AiServiceImpl:917-928` 的调用方式决定了分帧必须走 SSE：

```java
webLlmOpenChatClient.post().uri(llmOpenChatUrl)
    .contentType(APPLICATION_JSON).body(BodyInserters.fromValue(alParams))
    .accept(MediaType.TEXT_EVENT_STREAM)   // 声明要 SSE
    .retrieve().bodyToFlux(String.class)   // String + text/event-stream → Spring 的 SSE reader
```

**改前**（不兼容）：`text/plain` + `{"answer":"银行"}\r\n`，无 `data:` 前缀 → Java 侧 `WebClientResponseException: 200 OK`（栈顶在 `reactor.netty.channel.FluxReceive.startReceiver`，属解码层），前端显示兜底文案「模型没有返回，请稍后再试!!!」。注意：用 `curl` 直连是**完全正常**的（逐帧 `{"answer":"银行"}`），所以这个问题只在 Java 的 SSE reader 上暴露，靠自测 curl 发现不了。

**改后**（实测）：

```
$ curl -sS -D- -o out.txt -X POST 19996/llm_open_chat -H 'Accept: text/event-stream' -d @body.json
HTTP/1.1 200 OK
cache-control: no-cache
x-accel-buffering: no
content-type: text/event-stream; charset=utf-8

$ head -6 out.txt
data: {"answer": "企"}

data: {"answer": "业"}

data: {"answer": "信"}

$ tail -2 out.txt
data: {"answer": "。"}

data: {"end": ""}
```

- 帧统计：`/llm_open_chat` → **27 个 data 帧 + 1 个 end 帧**，`grep -vcE '^data: |^$'` = **0**（无非 SSE 行）
- 其余三个流式端点同样生效：`/llm_generate_sync` 28 帧、`/llm_rotate_answer` 28 帧、`/llm_multi_model` 同机制
- 溯源未被破坏：`need_trace_source=true` 时末尾帧为 `data: {"answer": "[retrive-tag id=\"trace-001\" image_urls=\"\" fromType=\"0\"][0][/retrive-tag]"}`，`has_citation=true`
- 每帧 JSON 仍可 `JSON.parseObject`（内容未改，只加了 `data: ` 前缀与 `\n\n` 分隔）

**兼容性说明**：`stream` 字段默认 `True`（`LLMOpenChatConfig.stream`），Java 不传也会走流式并收到 `{"end": ""}` 收尾帧；SSE 是 Spring 与浏览器 `fetch-event-source` 的公共标准，前端无需改动。

---

### 10.5 Java 侧真实 payload 形态（供我这边对齐，已实测通过）

`FAQAppServiceImpl` / `FileAppServiceImpl` 构造的是**正确形态**，与我的 `InsertDataModel` 完全一致：

```json
{"index_name": "<kbName>",
 "document_list": [{"page_content": "<chunk.content>",
                    "metadata": {"source": "<filePath>", "document_id": "<fileId>", "file_id": "<faqFileId>",
                                 "folder_id": "<faqFileId>", "knowledge_base_name": "<primitiveName>"}}],
 "duplicate_flag": true}
```

实测该形态写入 `r12_tl_ok` → `code=200`、计数 +1。反而**手工探测**用 `{id, content_with_weight, source}` 这种自定义键会 500（现已被 `R12-ADAPT-ALG-08` 改为 422 + 明确提示）。`type` 字段是 `str`（默认 `""`）；传数字 `1` 会 422（pydantic v2 不做 int→str 转换），Java 侧本来也不传该字段。

---

## 11. 复验命令（可整段重跑）

```bash
R12=/home/szf/data/dev/llmke-r12/platform/r12
cd /home/szf/data/dev/llmke-r12

# 1) 配置
python3 $R12/nacos/publish.py --verify           # 期望 RESULT: ALL_OK

# 2) 服务
$R12/run/algctl.sh status                        # 期望四个 RUNNING
for p in 19526 19527 19995 19996; do curl -s -o /dev/null -w "$p=%{http_code}\n" http://127.0.0.1:$p/docs; done

# 3) a~d 全链路（会重建 ES index / Milvus 集合，仅动 r12_alg_test）
$R12/venvs/alg/bin/python $R12/run/alg_verify.py | tee $R12/logs/alg-verify.log

# 4) 溯源 + 三类模型连通性
$R12/venvs/alg/bin/python $R12/run/alg_llm_trace_check.py | tee $R12/logs/alg-llm-trace.log

# 5) 基础设施旁证
curl -s http://127.0.0.1:19200/_cat/plugins?v
curl -s -X POST http://127.0.0.1:19200/_analyze -H 'Content-Type: application/json' \
  -d '{"analyzer":"ik_max_word","text":"企业信用贷款管理办法"}'
```

清理（仅测试索引，勿在生产库执行）：`curl -X POST http://127.0.0.1:19527/del_index -d '{"index_name":"r12_alg_test"}' -H 'Content-Type: application/json'`；Milvus 集合 `_r12_alg_test` 用 pymilvus `utility.drop_collection("_r12_alg_test", using="rag_knowledge_base")`。

---

## 12. 证据文件清单

| 文件 | 内容 |
|---|---|
| `platform/r12/logs/alg-verify.log` | a~d + rerank 反转用例的完整原始输出 |
| `platform/r12/logs/alg-llm-trace.log` | 溯源引用标签 + 三类 `/llm_check_model` 实测 |
| `platform/r12/logs/index_vector_service.log` / `index_fulltext_service.log` / `alg_retrieval_service.log` / `alg_llm_inference_service.log` | 服务运行日志（含启动时打印的完整生效配置） |
| `platform/r12/nacos/*.yaml` + `publish.py` | Nacos 权威内容与发布/校验脚本 |
| `platform/r12/run/algctl.sh` | 启停控制器 |
| `platform/r12/run/alg_verify.py`、`alg_llm_trace_check.py` | 可复跑的验证脚本 |

---

## 13. 仍缺失 / 待他人确认

1. **Java 侧 `model_info.type`** 是否已按 1/2/3 传入 `/llm_check_model`（不传则模型登记 500）。
2. `multi_version.url` 的真实端点（当前占位指向 18082，无实际多版本扩召回）。
3. 图谱服务（19529）本轮未起，`enabled_graph=true` 的请求需要在图谱侧就绪后再验。
4. `score_threshold` 的最终取值需业务侧按语料标定（实测分布见 §6c2 提示）。
