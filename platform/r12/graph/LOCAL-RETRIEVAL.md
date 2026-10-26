# R13 本地图检索（GraphRAG local）不可用 —— 根因 / 改法 / 回填 / 实测

范围：`services/rag-alg/index_data_service/index_graph_service/**`（graph 服务 19529）+ `platform/r12/graph/**`
时间：2026-10-26 22:30 ~ 23:00（全部实测本机，未改 Java / 前端 / 检索服务）

---

## 1. 结论（先给答案）

现象是 `POST 19529/query_graph_data` 返回 `code=200` 但 `entity_list=[]`、`result_data=[]`。
它不是一个 bug，而是**四层问题叠加**，其中"实体向量集合不存在"这条前提在当前环境已不成立
（`graph_base` 库里 `graph_entity_kb_9` / `graph_triples_kb_9` 本来就存在且有数据），真正致命的是：

| # | 层 | 事实（源码 + 实测） | 影响 |
|---|---|---|---|
| L1 | 数据代次 | 图实体/三元组的 `chunk_pk_list` 存的是**抽取时刻 ES 文档 `_id`**（`graph_fun_tool.get_document_chunk` 用 `ed["_id"]` 当 pk）。知识库重新解析会生成新 `_id`，旧 id 在 ES/Milvus 都不存在 | 图能查到实体/边，但按 pk 回取正文恒为空 → `result_data=[]` |
| L2 | 返回体 | `query_graph_data` 里 `high_entity_list = []` 定义后**从未赋值**；`cal_ppr_fun` 内部算出的高分实体没有回传 | `entity_list` 永远 `[]`（"图跑通了也是空"的假象来源之一） |
| L3 | 并发 | 全局共享 1 个 Nebula Session，且**每个请求结束都 `release()` 它** | 两路图检索并发 → `RuntimeError: The session has been released` → 500 |
| L4 | 鲁棒性 | `get_chunk_by_ppr_score` 在"高分实体在实体向量表里查不到自身行"时 `hi["metadata"]` KeyError | 单个悬空实体把整个查询打成 500 |

L1 的直接证据（回填前）：

```
graph_entity_kb_9 里 智造贷 的 chunk_pk_list = ['1398973471554581416','1743666879875937608','2687504475867150039']
ES  kb_9  查询 ids=[1398973471554581416,...]        -> total_count 0     （旧 id 已不在）
Milvus _kb_9 查询 pk in (1398973471554581416,...)   -> 0 行              （旧 id 已不在）
→ 图检索最后一步 query_milvus_by_condition(rag_knowledge_base, kb_9, col_name="pk") 恒空
```

---

## 2. 改了哪些文件（全部在允许范围内）

| 文件 | 标记 | 改法 |
|---|---|---|
| `index_graph_service/graph_service.py` | `R13-FIX-GRAPH-14`（L546 `fetch_chunk_documents`） | 正文回取改为 **Milvus pk 优先 + ES `_id` 补齐**：逐条比对命中集合，未命中的 id 用 `search_by_custom_param` 的 `ids` 查询补回，最后按 PPR 候选顺序排序；两者都不存在的才算真悬空并打 `ERROR`（提示重建图） |
| `index_graph_service/graph_service.py` | `R13-FIX-GRAPH-15`（L619 入口 / L641 `_query_graph_data`） | 查询入口按请求从 `ConnectionPool` 取**独立 Session**，`finally` 归还；异常统一兜成 `code=500 + result_data=[]`，不再裸抛 |
| `index_graph_service/utils.py` | `R13-FIX-GRAPH-15`（L106 / L223 / L256） | 新增 `acquire_session/release_session`；共享 Session 加 `RLock` 串行化；`close_session` 不再释放共享 Session |
| `index_graph_service/graph_p_array.py` | `R13-FIX-GRAPH-13`（L127） | `cal_ppr_fun` 返回 `(pk_list, high_entity_list)`，把高分实体回给接口 |
| `index_graph_service/graph_fun_tool.py` | `R13-FIX-GRAPH-16`（L1027） | 高分实体在向量表无对应行时跳过并 `WARNING`（不再 KeyError 打 500）；`index_src/index_dest` 为空也跳过 |
| `index_graph_service/graph_summary.py` | `R13-FIX-GRAPH-17`（L92 / L160 / L188） | TL 同源需求：社区摘要新增 `file_names`（见 §5） |
| `platform/r12/graph/rebuild_graph.py` | 新增 | kb 级回填工具（drop 图向量 → 全量重抽 → 计数 → 自检） |

**关于集合名口径**：不动。`query_graph_data` 用 `graph_entity_<kb>`（无 `g_` 前缀），与写入侧
`generate_triple_data` 完全一致；向量服务内部统一 `generate_collection_name_uuid()` 加下划线前缀
（实际集合名 `_graph_entity_kb_9`）。Nebula 侧才有 `g_<kb>` 前缀，两边各自自洽，**不需要统一**，
强行统一会破坏 `del_doc_entity`/`static_count` 等既有调用。所以本仓库未改集合命名。

---

## 3. 回填命令（kb 级，可重复执行）

```bash
cd /home/szf/data/dev/llmke-r12
platform/r12/venvs/graph/bin/python platform/r12/graph/rebuild_graph.py kb_9
#   --no-drop        只增量 merge，不 drop 图向量集合
#   --skip-extract   只做计数与自检（不会 drop）
#   --probe "票据贴现"  自检问题
```

脚本做的事：drop `graph_base._graph_entity_kb_9 / _graph_triples_kb_9` → `POST 19529/generate_triple_data`
（`space_name=kb_9`，全量 ES 文档重抽）→ 打印 Nebula 顶点/边 + Milvus 可见行数 → 跑一次 `query_graph_data` 自检。

**为什么要 drop 而不是只重抽**：写入侧 `query_like_entity`/`update_triples_data` 只做 merge（append chunk id），
没有任何清理旧 id 的路径；不 drop 就会"旧悬空 id + 新 id"混在同一行里，靠 top_k=1 命中哪一行全看运气。

等价的 Java 入口（需网关/登录，本机 8088 当前未起，未用）：
`POST /index/knowledgeBase/file/graphParse {"knowledge_base_id":9,"file_ids":[...]}`（异步，之后必须重跑
`/generate_community`，TL 提供的 `platform/r12/bin/graph-refresh.sh 9 kb_9` 封装了这条链路）。

> ⚠️ 操作纪律：**任何 kb 重新解析之后都必须重跑一次本回填**。ES 与 Milvus 的代次一旦错开，图数据里的
> chunk 引用立刻失效。这是当前环境的硬性顺序（本次实测就踩到：22:37 回填完，22:37:00 那批解析又把
> ES `_id` 全换了一遍，图数据立刻变旧）。

---

## 4. 实测输出（原始）

> ⚠️ **取证边界（安全声明，qa-authz 2026-10-26 提出，已用 `ss -ltn` 逐端口核对）**：
> 本机 7 个端口监听 `0.0.0.0` 且无鉴权：`19529`(graph) / `19995`、`19996`(retrieval、llm) / `18095`(preview stream) /
> `19526`(index_vector) / `19527`(index_fulltext)，外加 `18088`(前端 nginx，真正的对外入口)。
> 本文件 §4 的全部 curl 都不带 `Authorization` 头却返回 200 + 正文，即为旁证。
> 边界另一侧（不要扩大处置范围）：Java 服务 `18081-18085` 与模型服务 `18090-18093` 实测均为 **127.0.0.1 回环**，
> 与本次取证无关，不需要动。
> 因此：**直连内部端口的证据只能证明"检索能力可用"，不能证明授权边界**。
> 这条路径既是自证捷径，也是撤权旁路（qa-authz 实测：撤权后不带 token 调 `19995/retrieval_documents` 仍能取到
> kb_9 正文、`18095/stream` 仍能取到 PDF）。授权必须在网关/Java 侧另做验收，不要引用本文件的 §4 作为安全证据。

### 4.1 计数（回填后）

```
nebula g_kb_9                       vertices=83  edges=120        （回填前 56 / 70，增长）
Milvus graph_base._graph_entity_kb_9  num_entities=39             （回填前 74，全部为悬空旧行）
Milvus graph_base._graph_triples_kb_9 num_entities=31
Milvus graph_base.community_summary_kb_9 = 30（含历史重复，见 §6）
ES    community_summary_kb_9        = 7
```

`generate_triple_data` 返回（原始）：

```json
{"code":200,"msg":"添加成功，新增和更新44条图数据,新增39条实体",
 "data":{"error_edge_data_list":[],"error_tag_data_list":[],
 "type_report":{"schema_version":"v1","kept_entities":39,
  "filtered":[{"name":"业务日","reason":"stopword"},{"name":"天数","reason":"stopword"},
              {"name":"放款日全国银行间同业拆借中心公布的一年期贷款市场报价利率加点形成","reason":"too_long"},
              {"name":"R12验收测试夹具","reason":"test_fixture"}],
  "unclassified":["1年期LPR","受理","30~100BP","BP","..."],"dropped_triples":3}}}
```

### 4.2 自证 a：单实体 `智造贷`

```
POST 19529/query_graph_data
{"query":"智造贷","space_name":"kb_9","top_k":10,
 "model_info":{"model_id":"qwen2.5-7b-instruct","url":"http://127.0.0.1:18092/v1/chat/completions","key":"sk-r12-local"}}

code 200 | 查询成功，共3条文本数据
entity_list: ['智造贷', '江南装备科技有限公司', '装备制造']
  pk 332999700890475178 title R12FIX-product-loan(1).docx | “智造贷”企业流动资金贷款产品说明书文件编号：PRD-CORP-LOAN-2026-01（R12 验
  pk 603679223195613463 title R12FIX-product-loan.docx     | “智造贷”企业流动资金贷款产品说明书文件编号：PRD-CORP-LOAN-2026-01（R12 验
  pk 794663329353800421 title R12FIX-product-intro.pptx    | “智造贷”产品要点 适用对象：制造业中小微企业 最高额度：5000万元（信用部分不超过1000万元）
```

### 4.3 自证 b：多跳 `智造贷的授信额度和票据贴现是什么关系`

```
code 200 | 查询成功，共4条文本数据
entity_list: ['智造贷', '江南装备科技有限公司', 'T-EXT-001', '装备制造', '三个工作日内放款']
  pk 603679223195613463 title R12FIX-product-loan.docx      | “智造贷”企业流动资金贷款产品说明书…
  pk 332999700890475178 title R12FIX-product-loan(1).docx   | “智造贷”企业流动资金贷款产品说明书…
  pk 794663329353800421 title R12FIX-product-intro.pptx     | “智造贷”产品要点…
  pk 1024737308141832299 title docx-table.docx              | |指标|数据源|口径| |日均存款|T-CORE-001|按业务日跨账户汇总/天数|…
```

### 4.4 自证 c：`POST 19995/retrieval_documents`（`enabled_graph:true, enabled_rerank:false`）

```
code 200 | 查询成功    documents_list 3
  pk 603679223195613463 | search_type= ['milvus','milvus','es','es','es','es','graph','graph'] | R12FIX-product-loan.docx
  pk 3383444681648446129 | search_type= ['milvus','es','es']                                | R12FIX-credit-ledger.xlsx
  pk 794663329353800421 | search_type= ['milvus','es','es','graph']                        | R12FIX-product-intro.pptx
```

**如何识别"来自图检索"**：看 `documents_list[*].metadata.search_type` 里是否含 `"graph"`。
图服务把来源写在 `metadata.search.type=["graph"]`（`multiple_retrieval.retrieval_graph`），
检索侧 `retrieval_fun_tool.process_return_results` 会把它并进 `search_type` 并做去重合并，
所以同一个 chunk 可能是 `['milvus','es','graph']`（多路都命中）——`graph` 出现即代表图检索贡献过这一条。

### 4.5 自证 d：并发（L3 修复）

```
4 路并发 POST /query_graph_data（query=票据贴现和授信额度的关系）
par1 code 200 entities 3 docs 3
par2 code 200 entities 3 docs 3
par3 code 200 entities 3 docs 3
par4 code 200 entities 3 docs 3
日志 session has been released 计数：16（全部在 22:49:45 重启之前的旧日志，压测后计数不变）
```

---

## 5. TL 同源需求：社区摘要 `file_names`（选了"方案 1"）

**选择**：不只给 `query_community` 加字段，而是**落库时就多存一份** `file_names`（选项 1，成本 ~30 行，只动
`graph_summary.py`，没有改多处）。

- 落库：`generate_community` 每条社区记录里，除原有 `metadata.file_ids` 外新增
  **`metadata.file_names`**（`file_id → ES metadata.title`，去重保序；取不到就是 `[]`）。
- 读出：`_load_summaries` 同时返回 `file_ids` 与 `file_names`，因此
  `query_community`（global 与 local 两种模式）返回的 `data.communities[*]` 都带
  **`file_names: ["R12FIX-product-loan.docx", ...]`**。
- 旧摘要（无该字段）读出来是 `[]`，Java 侧判空即可，不会报错。

实测（`query_community mode=local, query=智造贷`）：

```
code 200 | 命中 2 个社区
L1-05af3770 | file_ids= ['119','120','226','234','252','258','259','260']
            | file_names= ['R12FIX-product-intro.pptx','R12FIX-product-loan.docx','R12FIX-product-loan(1).docx']
L0-4d1442b9 | file_ids= ['119','226','234','252','258','260']
            | file_names= ['R12FIX-product-intro.pptx','R12FIX-product-loan.docx','R12FIX-product-loan(1).docx']
```

可见 `file_ids` 里 `119/120/234/252/259` 已经是失效旧 id（ES 里查不到），而 `file_names` 正确给出了
当前文件名 —— 正是 TL 要的"按文件名回落"依据。

---

## 6. 仍缺什么（诚实清单，未做）

1. **Nebula 边的 `file_id/page_num` 仍是旧代次**。本次只重建了 Milvus 图向量，没有 `DROP SPACE g_kb_9`。
   顶点按实体名做 vid、边按(名,名)重复插入只会报"已存在"，所以图结构本身没坏，但边上属性仍是老解析的
   `file_id`（上面 §5 里 `file_ids` 出现 119/120 就是它）。要彻底一致需要：
   `POST 19529/del_space {"space_name":"kb_9"}` → 再跑 `rebuild_graph.py kb_9`（会重建 space + TAG/EDGE +
   两次固定 sleep ≈ 50s）。属于停机操作，未擅自执行。
2. **`community_summary_kb_9` 有重复行**（Milvus 30 行 vs ES 7 条）：`write_summary_indexes` 只有 insert，
   没有按 `community_id` upsert/去重。PDF 只影响 global 的 reduce 输入冗余，不影响正确性。
3. **实体覆盖取决于 LLM 抽取**：本次 39 个实体（旧代次 74 个是更多文档/更多 chunk 的产物），
   `授信额度`、`评级授信` 这类词在新抽取里被模型归并成了 `5000万元`/`人民币5000万元`。
   查 `授信额度` 现在仍可能命中不到图（因为它不是实体行）——这是抽取质量问题，不是链路问题。
4. **ES/Milvus 代次漂移是环境级隐患**：本次实测亲眼看到 `kb_9` 在 22:36-22:37 被重新解析，ES `_id` 全换，
   图数据瞬间变旧。回填后我加的 ES `ids` 补齐让"ES 新、Milvus 旧"的情况也能取到正文，但根治要靠
   解析/图抽取的编排顺序（解析完成事件 → 图抽取 → 社区重建），不在本目录范围。
5. **`static_count` 不能当"有没有写进去"的判据**：它走 Milvus `num_entities`，只统计已 flush 段，
   刚 insert 完稳定返回 0（实测 39 条数据、static_count=0）。判据请用 `get_doc_page` 的 `total_count`
   （回填脚本已改为以可见行为准）。
6. **产品链路取证要避开 `search_config.id=9` 的坑**（qa-authz 2026-10-26 实测）：`search_config.id=9` 的
   `is_del=0`，而 `ConfigIsDelEnums` 语义是 NO=1 / YES=-1，所以 `getConfigById(9)` 恒返回 null，
   **configId=9 实际不生效**，qa-service 回落到 `getDefaultConfig()`（create_by=当前用户、is_default=1、is_del=1）。
   admin 恰好有 id=1 的默认配置（也指向 kb_9），所以用 admin 跑看起来正常；**换任何非 admin 账号就会回落到
   nacos `defaultSearchConf`（`{}`）→ 422 无答案，且配置里没有 `knowledge_base_name`，问答的对象级授权检查
   与 `enabled_graph` 等开关一并失效**。要给非 admin 账号测图谱/global，需给该账号准备自有默认配置
   （create_by=该账号、is_default=1、is_del=1、config_json 复制 config 1）+ `user_privilege(biz_type=3, target_id=1/3)`。
   另外 `/qa/ai/question` 的 `reply.content` 是**累计全文**不是增量，拼帧会重复，取最后一帧才是完整答案。

   > 对本文件 §4 取证的影响：**不影响能力取证，但不得当作授权证据**。§4.2/§4.3 直连 19529（`model_info`
   > 在请求体里，与 search_config 无关），§4.4 直连 19995 且 `enabled_graph`/`enabled_rerank` 都在请求体里显式给值，
   > 所以"检索能力"结论成立；但这两个端口 0.0.0.0 且无鉴权（见 §4 取证边界），直连方式绕过了鉴权与对象级授权，
   > **不能用来证明授权边界**。只有"前端 → Java QA（configId=9）"那条产品链路的取证会受上述回落影响，
   > 届时别把"图开关被吞掉"误判成图检索缺陷。
   7. 未跑 `platform/r12/qa/acceptance.py`（按纪律禁止），未 `git add/commit`。
