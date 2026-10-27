# R14-A 证据（Loop1-A：稳定标识 / 代次 / 幂等）

## 首段：本轮必须记住的两条错法（TL 要求如实记录）

**① 把几分钟前的观察当现状（我犯的）**
13:11 我报"19527 pid=538329 / 19526 pid=587603 仍是旧代次"，实际 TL 在 13:10:41 已把它们换掉（1167266 / 1167862）。
我拿启动前的快照当成了当前态，导致后续判断锚错、TL 据此在 13:24 得出"重解析没生效"的相反结论（他的观测点也确实早于我真正跑成的 13:25:49）。
**规矩**：报服务代次一律"我刚 `ss`/`/proc` 读到并附时间戳"，不复述几分钟前的观察；报数据结论附查询时刻。

**② 把"服务自己的说法"当存储事实（我撞上、靠复查发现）**
13:23 那轮 7 个文件 `POST /parse_sync` 返回 `task_statuses[*].success=true`，实际索引写入失败
（`All connection attempts failed -> 19527`），ES `_id`/`create_time` 一条没动。
**规矩**：`success` 只说明解析进程没抛异常；是否真写进去要查存储（条数 + `create_time`/`update_time` 晚于请求时刻），
两类"假成功"（`file_ids` 参数被忽略、`.md` 解析不支持）属同一族。

采集时刻：2026-10-27T02:19Z 起（本地 10:19+），ES `yellow`（单节点副本无处分派）、`active_primary_shards=27`。
服务：index_fulltext 19527 / index_vector 19526 / index_graph 19529 均由本仓代码启动（重启方式 `platform/r12/run/algctl.sh restart <svc>`）。
改动：`services/rag-alg/index_data_service/index_fulltext_service/src/index_fulltext_service_pactera/controller/es.py`、`.../index_vector_service/src/index_vector_service_pactera/milvus_kb_service.py`（未改 index_graph_service）。
说明：`platform/r12/qa/*.py` 属 F-qa，本目录内脚本只做探测，不改任何既有 QA 脚本。

## 结论一览

| 项 | 结论 | 证据文件 |
|---|---|---|
| 社区摘要两侧一致 | **PASS**：连跑两次 generate，ES 7 行 / Milvus 7 行，community_id 集合逐项相同，run1=run2，`ES._id==Milvus.pk` 7/7 | `community_twice_after.json`；改造前 65 行见 `before_community_state.json` |
| 社区摘要两侧一致（B 改 global map-reduce 并重启 19529 后复验） | **PASS**：run1/run2 均 7 社区 7 摘要（20.5s / 18.5s），ES 7 / Milvus 7，cid 集合相等，run1.cid==run2.cid，`ES._id==Milvus.pk` | `community_twice_afterB.json`（graph pid 222070） |
| 重复写入不翻倍 | **PASS**：改前 Milvus 3→6（翻倍），改后 3→3；ES 3→3；两次 id 完全相同 | `parse_twice_before.raw.json`、`parse_twice_after2.json` |
| 内容覆盖（同 doc/file/chunk_index、正文变化） | **PASS**：只有变化的第 0 块换 id，第 1/2 块 id 不变；两侧可见行 3→3；旧 id 在 ES 查不到（404） | `content_change.json` |
| 写入点自证 id 来源 | **PASS**：`metadata.id_origin` 四类取值实测落库——`derived_chunk_index`（无 pk）/ `pk_from_caller`（带 pk）/ `random`（缺 document_id+chunk_index）/ `derived_community`（社区摘要） | `probe_id_origin.py`、`id_origin_check.txt` |
| 生产索引上的 id_origin 基线 | 存量（写于 id_origin 上线前）全部 `__MISSING__`：kb_9 8 / faq_kb_9 20 / table_chunks_kb_9 2 / table_summary_kb_9 2 / community_summary_kb_9 7；生产重跑一次 `generate_community` 后 `community_summary_kb_9` = **7 条 `derived_community`** | 见下节"id_origin 基线" |
| 19526 缺 `/del_collection`（社区摘要 Milvus 集合从未删过） | **已补并验证**：新增 `milvus_kb_service.del_collection()` + `/del_collection` 路由；实测 drop 成功、二次调用幂等 `dropped=false`、`has_collection=False` | `del_collection_route_missing.md` |
| `graph-refresh.sh` 半清理（两侧不对称的脚本层根因，属 E） | 事实：`platform/r12/bin/graph-refresh.sh` 共 53 行，**`:47`** `curl -X DELETE "$ES/community_summary_<kb>"` 只清 ES、不清 Milvus；`grep del_collection` 为空。建议删掉 `:47` 或改调 `POST $GRAPH/del_community` | 本条（无独立文件；行号已 `wc -l` + `grep -n` 现取核对） |
| 实体→chunk_pk_list 明细基线（M1 前） | **已跑通**：`_graph_entity_kb_9` 53 实体（with_refs 53 / without_refs 0，ref_len {1:16,2:14,3:10,4:11,7:2}）；`_graph_triples_kb_9` 72 条（without_refs 0，ref_len {1:51,2:13,3:8}）。**口径警告**：Milvus `entity_type` 恒为 `"1"`（53/53），不可当类型维度；类型看 `type`(ARRAY)。M1 判据：`without_refs` 保持 0、无实体 refs 由 >0 变 0 | `probe_entity_citations.py`、`kb_9_entities.json` |
| kb_9 引用对账基线（M1 前） | **PASS**：ES `kb_9` 9 条（`__MISSING__` 8 + `pk_from_caller` 1）、`table_chunks_*` 2、`table_summary_*` 2、`community_summary_*` 7（全 `derived_community`）；Milvus `_kb_9` 9 行；**ES pk 集合 == Milvus pk 集合（9/9，双向差集空）** | `probe_kb_snapshot.py`、`kb_9_snapshot.json` |
| 阈值 × top_k 对候选数的影响 | `th=0.001` → 2(top_k=5)/3(top_k=10)；`th=0.01/0.05` → 1 条（top_k 失效）；**含关键句「AAA级加30个基点」在 6 种组合下恒为 1** → 候选收缩是配置相关、正确依据从未丢失 | `threshold_matrix.md` |
| 图增益为何"不可证"（结构性 + 可判定判据） | 图的回取是 `chunk_pk_list → ES _id → ES 文档`（`graph_fun_tool.get_document_chunk`），**只能返回 ES 已存在的块**，不产生新文本 → 图的价值只能是"召回他路漏掉的块"。判据：出现 `search_type == ['graph']` 的块且关图时缺席。本轮四例 graph 块均为 `['milvus','es',…,'graph']` 合并值，**无"仅图"块** → 增益未证明（可量化，非主观） | 见本节 + B 的 `R14-B-FINAL-*` |
| C12 版本替换（三步） | **步2/3 PASS、步1 BLOCKED**：两代共存（fid 290/V0 5000万 与 328/V1 8000万，pk 不同）；检索只取 V1，V0 在 top_k=20 也未进候选（`document_version()` R13-VER-11 过滤）；**ES `metadata.version` 仍 9/9 为 null**，`/qa` 的 `ver=V1` 来自 `_ver_from_source`（source 正则）而非落库版本。index 服务 pid 474113 启于 11:17:01，target jar(6fd91ccc) 与 staged jar(47de4b6b) md5 不同 | `c12_version_status.md` |
| GLOBAL 唯一 FAIL 归因 | **非产品缺陷，是"无依据题当正例"**：ES `贴现`/`票据` 均 0 命中、Nebula 无对应实体、7 条社区摘要全无该主题 → 拒答是正确行为（C16）；且 `global_answer` 已被 `AiServiceImpl:2189-2196` 消费（FIX-05），不存在"结果被丢弃"。建议改判拒答用例 + 补跨文档语料 | `global_fail_attribution.md` |
| AAA 题归因（检索 vs 生成） | **检索 PASS / 生成 FAIL**：`documents_list` 唯一命中文档正文含「AAA级加30个基点，AA级加60个基点，A级加100个基点」；`/qa` 输出 100/60bp 属 faithfulness 缺陷。另记录"rerank+阈值把候选 2→1"为质量风险（非缺陷） | `aaa_answer_attribution.md` |
| B 的两层正交（运行态样本） | **PASS**：`id_origin=pk_from_caller → identity=stable_derived` 且 `provenance_quality=entity_content_recovered` 同条并存 → 身份层未拉高出处层 | 见下节"两层正交抽样" |
| 检索层三条缺陷修复复验（C 重启 19995 后） | **PASS**：FAQ `faq_result_list` 0→1；大写开图 500→200（含 rerank=true 与 4 种组合）；多 KB `[kb_5,kb_9]` 图结果保留（documents 4 / graph 3）。19995 已单实例（641826@11:47:21）。multi_version 分支未验证 | `retrieval_fixes_verified.md` |
| 开图检索 500（查询含大写 ASCII） | **已定位**：`retrieval_service.py:478 documents[query]` KeyError；`:375` 只把小写串放进 `queries` → `documents` 键为小写。A/B：`AAA`→500、`aaa`→200（同参数）。这是 B 观测"开图 refs=0、答案对"的真因（Java 拿不到 documents_list），**不是 filterDocs 清空** | `uppercase_query_graph_500.md` |
| FAQ 直答失效根因（`retrieval_milvus` offset 解析 `break`） | **已定位**：`multiple_retrieval.py:209-215` 解析失败 `break` 掐断整批召回；影响面含普通向量召回。写入侧已补规范化（缺失→`"[]"`，实测 json.loads 通过），存量 20 行仍 `""` → 读侧修复待 C | `faq_offset_break.md` |
| ES 侧旧代清理真的执行了 | **PASS**：改造前 7 条随机 `_id`（`1071584032174993371` / `1285064802195168642` / `1781325502868850634`）现均为 404，索引仍是 7 条（若未清理应为 14 条） | 见下方"ES 旧代清理"命令 |
| 真实 `/parse_sync` 两次（同文件） | **PASS（C 修完后复验）**：`cn-digital.pdf` 4 块与 `docx-table.docx`（含 table_chunks/table_summary）各两次 → 计数不翻倍、**两次 id 完全相同**、`ES._id==Milvus.pk`、`id_origin=pk_from_caller` | `e2e_stable_afterC.md`、`parse_twice_e2e_afterC.json`、`parse_twice_e2e_afterC_table.json` |
| 真实 `/parse_sync` 两次（同文件，改造前基线） | 历史基线（保留对照）：`fixtures/cn-digital.pdf` chunk_size=120 → 4 块；两次 ES 4→4、Milvus 4→4（不翻倍），每次 `ES._id == Milvus.pk`；但两次 id 不同（根因：解析服务写死随机 pk，见 A-IDENTITY §6.1） | `parse_twice_e2e_multi.json`、`parse_twice_e2e_pdf.json`、`parse_twice_e2e.json` |
| 真实 `/parse_sync` 两次（含表格） | **部分 PASS**：`fixtures/docx-table.docx` → `r12a_parse_idem` 1→1、`table_chunks_*` 1→1、`table_summary_*` 1→1（不翻倍）；三类 `_id` 两次都变且都不等于派生值（表格侧随机 pk 在 `deepdoc/splitter/table.py:33/48/89/107`） | `parse_twice_e2e_table.json` |
| Milvus 主键 AutoID | **否**：`pk INT64 is_primary auto_id=False`（pymilvus 实测，`_community_summary_kb_9` / `_kb_9` 同） | `before_community_state.json` → `milvus.pk_field` |

## 关键数字

改造前（`before_community_state.json`）：
```
ES  community_summary_kb_9        docs=7   （_id 随机，metadata.pk=随机）
MV  _community_summary_kb_9       rows=65  distinct_pk=65  create_time 跨 12 个批次
MV  pk_field = {name: pk, dtype: 5(INT64), auto_id: False}
MV  chunk_doc_id/source/knowledge_base_name 全部为空字符串
```

改造后（`community_twice_after.json`）：
```
run1 generate: communities=7 summaries=7 failures=0 (20.4s) | ES 7 行 | MV 7 行/7 pk/7 chunk_doc_id
run2 generate: communities=7 summaries=7 failures=0 (23.1s) | ES 7 行 | MV 7 行/7 pk/7 chunk_doc_id
ES.cid 集合 == MV.cid 集合：run1 True / run2 True      run1.cid == run2.cid：True
ES._id == metadata.pk（7/7）：True        ES ids == MV pks：True
```

重复写入（`parse_twice_before.raw.json` → `parse_twice_after2.json`）：
```
before : ES 3 -> 3（id 两次不同） ; MV 3 -> 6（翻倍，id 两次不同）
after2 : ES 3 -> 3（id 两次相同） ; MV 3 -> 3（id 两次相同） ; ES ids == MV pks
```

## 内容覆盖（`content_change.json`）
```
v1: ES 3 行 / MV 3 行，第0块 id=275016707213128010
v2（第0块正文改 3000→5000 万元，同 document_id/file_id/chunk_index）:
    ES 3 行 / MV 3 行，第0块 id=519226191378293716；第1/2块 id 不变
    old_id 在 ES 查询命中 0 条（404）→ 明确失效，不会错指新文本
```

## id_origin 基线（只读聚合 + 一次生产重建）
```
# 存量（均写于 id_origin 上线前）
kb_9                    total 8  -> __MISSING__ 8
faq_kb_9                total 20 -> __MISSING__ 20
table_chunks_kb_9       total 2  -> __MISSING__ 2
table_summary_kb_9      total 2  -> __MISSING__ 2
community_summary_kb_9  total 7  -> __MISSING__ 7

# 生产重跑一次 generate_community(kb_9) 后（7 社区/7 摘要/es_ok=milvus_ok=true）
community_summary_kb_9  total 7  -> derived_community 7
```
聚合命令：
```bash
curl -s -X POST 127.0.0.1:19200/<index>/_search -H 'Content-Type: application/json' \
  -d '{"size":0,"aggs":{"o":{"terms":{"field":"metadata.id_origin.keyword","missing":"__MISSING__"}}}}'
```

## 端到端两次真实解析（`parse_twice_e2e_multi.json`）
```
POST 12340/parse_sync  fixture=r12-rag/fixtures/cn-digital.pdf  chunk_size=120  index=r12a_parse_idem
run1: 200 / 3.6s | ES 4 行 | Milvus(rag_knowledge_base) 4 行 | chunk_index [0,1,2,3]
run2: 200 / 2.6s | ES 4 行 | Milvus(rag_knowledge_base) 4 行 | chunk_index [0,1,2,3]
每次 ES._id == Milvus.pk：True        两次 id 是否相同：False（见下方根因）
```
根因（不在 index_data_service）：解析服务在交给索引层之前就给 chunk 写死随机 pk
`services/rag-alg/alg_doc_parse_service/server/controller.py:407`（图片 `:499`、PPT `:565`）
`chunk.metadata.pk = create_uuid()` → 写入层保留"pk 优先"兼容规则 → 内容寻址分支被短路。
不能单边在索引层改 pk：`deepdoc/image_link.py` 把 `metadata.pk` 写进 `text_parent_id_list`（图片→文本块引用），改了会断链。
建议（C 侧）：同一行改成确定性派生
`pk = int63(sha1("chunk|"+index_name+"|"+document_id+"|"+file_id+"|"+parsed_chunk_index+"|"+sha1(page_content)))`
（`parsed_chunk_index` 在 `:406` 刚赋值、且在 linking 之前，所以图文引用照旧成立；表格块本就没在 `:407` 赋 pk，已走我的派生分支）。

## ES 旧代清理（直接证据）
```
curl -s -o /dev/null -w '%{http_code}' 127.0.0.1:19200/community_summary_kb_9/_doc/1071584032174993371   -> 404
curl -s -o /dev/null -w '%{http_code}' 127.0.0.1:19200/community_summary_kb_9/_doc/1285064802195168642   -> 404
curl -s -o /dev/null -w '%{http_code}' 127.0.0.1:19200/community_summary_kb_9/_doc/1781325502868850634   -> 404
curl -s 127.0.0.1:19200/community_summary_kb_9/_count                                                     -> 7
```
（改造前这 3 个是真实存在的随机 `_id`；若清理未执行，run1 写入后应为 14 条。）

## `probe_entity_citations.py` 输出字段表（避免两个分布被混用）
```
entities.rows (int)                = 53   Milvus 实体行数
entities.ref_len_distribution      = {1:16, 2:14, 3:10, 4:11, 7:2}   (合计 53)
entities.without_refs              = 0
entities.entity_type_raw_values    = ['1']  ← 恒 "1"，不能当类型维度
triples.rows (int)                 = 72
triples.ref_len_distribution       = {1:51, 2:13, 3:8}               (合计 72)
triples.without_refs               = 0
```
注意：**没有 `count` 键，也没有 `ref_distribution` 键**（取 `ref_distribution` 必得 None）。
实体分布(53) 与 三元组分布(72) 是两个不同对象，报告里必须分列，不能互相校验。
Nebula 顶点数（87）与 `entities.rows`（53）口径不同，属正常差异。

## 复跑命令

```bash
cd /home/szf/data/dev/llmke-r12/platform/r12/qa/evidence/R14-A-20261027T021902Z
P=../../../venvs/alg/bin/python
$P probe_community_state.py kb_9            # 只读：两侧 schema/行数/community_id
$P probe_parse_twice.py <tag>               # 同一解析产物两次写入（scratch: r12a_idem_parse）
$P probe_community_twice.py kb_9 <tag>      # 两次 generate_community（真调 LLM）
$P probe_parse_twice_e2e.py <tag>           # 真实 /parse_sync 两次（需 12340 在跑）
```

## 清理
本轮 scratch 已清理（ES `r12a_content_chg` / `r12a_idem_parse` / `r12a_parse_idem` 均 200 删除；Milvus `graph_base._r12a_content_chg` / `graph_base._r12a_idem_parse` / `rag_knowledge_base._r12a_parse_idem` 已 drop）。探针脚本复跑时会自动重建。

## 代码改动位置（本轮）

`index_fulltext_service/src/index_fulltext_service_pactera/controller/es.py`
- `:35` `COMMUNITY_INDEX_PREFIX`；`:38` `derive_doc_id()`；`:48` `community_doc_id()`
- `:196-210` build_actions：社区摘要 → 确定性 `_id`；KB/表格块 → 内容寻址 `_id`
- `:194-213` `id_origin` 判定（`pk_from_caller` / `derived_community` / `derived_parsed_chunk_index` / `derived_chunk_index` / `random`），`:238` 落 `metadata.id_origin`，`:190` database 分支固定 `random`
  - 派生序号：优先 `parsed_chunk_index`，缺失退回 `chunk_index`；`index_name` 两侧统一 `.lower()`（ES 原本有小写化，Milvus 本轮对齐）
- `:349` `_prune_stale_community_docs()`；`:454` 写入后整代替换清理

`index_vector_service/src/index_vector_service_pactera/milvus_kb_service.py`
- `:190/199` 同一算法的 `derive_doc_id()` / `community_doc_id()`
- `:206/219` `_visible_count()` / `_wait_until_deleted()`（删除可见性校验）
- `:471` `is_community_collection`；`:600-611` pk 分支；`:613` `chunk_doc_id` 承载 community_id
- `:643` 社区集合整代替换；`:658-672` 按 source 去重修复（补 `db_name` + 删除后校验，失败 500 中止）
