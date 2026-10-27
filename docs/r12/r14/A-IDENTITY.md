# R14 / Loop1-A 代次与稳定标识（A 角色）

日期：2026-10-27（第二轮：ES 恢复后全部重测）
仓库：`/home/szf/data/dev/llmke-r12`，分支 `feature/R12-real-rag`，HEAD `1fc3f6d`（本轮改动未提交，以工作树为准）
运行态：index_fulltext(19527) / index_vector(19526) / index_graph(19529) 均由本仓代码启动（`/proc/<pid>/cwd` 已核对）；ES `_cluster/health`=`yellow`（单节点副本无处分派，非故障），`active_primary_shards=27`。

本文只写事实与可执行改造；`事实 / 推断 / 判断` 在 §8 分开标注。

证据目录：`platform/r12/qa/evidence/R14-A-20261027T021902Z/`
- `before_community_state.json`：改造前两侧社区摘要现状（ES 7 / Milvus 65）
- `parse_twice_before.raw.json`、`parse_twice_after2.json`：重复写入的翻倍缺陷与修复后对比
- `community_twice_after.json`：两次 generate_community 的集合比对
- `probe_community_state.py`、`probe_parse_twice.py`、`probe_community_twice.py`、`probe_parse_twice_e2e.py`：可复跑探针

---

## 1. 结论摘要

1. **chunk 身份在改造前是"写入时随机生成"**：ES `_id` 与 Milvus `pk` 都来自 `create_uuid()`（`uuid4() & (1<<63-1)`）。**本轮已改成内容寻址**（§5.1），现在同一文件同一块重放得到同一主键，且 ES `_id` 与 Milvus `pk` 取同一值（实测 3/3、8/8 全等）。
2. **metadata 的稳定标识仍只到"按对象路径"粒度**：`document_id`(base64(minio 路径))、`file_id`(MySQL 行 id，重传即变)、`chunk_index`(随内容位移)、`version`(字段存在但实测为 `null`)。`parse_generation`、`parser_version`、`chunk_id` **完全不存在**（全仓 grep `parse_generation` 无命中）。
3. **图数据的正文回取绑定的就是这个主键**：`graph_entity_*` / `graph_triples_*` 的 `chunk_pk_list` 存"抽取时刻的 ES `_id`"（`graph_fun_tool.get_document_chunk()`），`file_id` 存 metadata.file_id。改造前 re-parse 一次 id 全换 → 悬空；改造后**内容不变的块 id 不变**（§5.1 实测），内容或 file_id 变了才换 id（属"新代"）。
4. **社区摘要两侧已对齐**：`community_id` 由 B 改为确定性派生（`L<level>-sha1(kb|level|排序成员)[:8]`），主键由 A 改为确定性派生并整代替换，实测两次 generate 后 **ES 7 行 / Milvus 7 行、community_id 集合逐项相同、run1 与 run2 也相同**（§4）。
5. **Milvus 主键不是 AutoID**（pymilvus 实测）：`graph_base._community_summary_kb_9` 与 `_kb_9` 的 `pk` 均为 `INT64, is_primary=True, auto_id=False`；`_kb_9` `num_entities=16` 但 `query` 只 8 行（含墓碑），**判"有没有写进去/有没有重复"必须用 `query` 可见行数，不能用 `num_entities`**。
6. **发现并修复一个会直接造成"重复解析翻倍"的真缺陷**：`add_doc_custom` 按 `source` 预删除时没把 `db_name` 传下去，删除落到配置默认库（`rag_knowledge_base`），而集合实际在 `graph_base` → `is_collection()` 查不到 → `del_doc_by_col` 返回 **200「未执行删除」** → 调用方忽略返回 → 静默跳过删除 → 第二次写入变两代（实测 3 → 6）。修复后 3 → 3（§5.3）。
7. 六元组里仍有 3 项缺口（`version_id` 实际为空、`parse_generation` 与 `parser_version` 不存在），**这 3 项不在 index_data_service 内闭环**：`version` 要 Java 侧传值（C），`parser_version` 要解析配置拼装（C/解析服务），`parse_generation` 需要"整份解析产物哈希"（P1，见 §6）。

---

## 2. ES chunk 文档：字段表（本轮实测）

样例（`POST :19200/kb_9/_search?size=1`）：`_id=498386897502206386`，`metadata.pk=498386897502206386`，`metadata.document_id=cjEyLXJhZy9rYl85L1IxMkZJWC1wcm9kdWN0LWxvYW4uZG9jeC9WMC9SMTJGSVgtcHJvZHVjdC1sb2FuLmRvY3g=`（= base64(`r12-rag/kb_9/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx`)），`file_id=290`，`version=null`，`chunk_index=0`，`knowledge_base_name=kb_9`。

| 字段 | 实际值 | 产生位置 | 稳定性 | 说明 |
|---|---|---|---|---|
| ES `_id` | 63 位正整数 | `controller/es.py:190-210` | **改后稳定**（按内容）/ 改前随机 | 有 `metadata.pk` 用 pk；社区摘要用 `community_doc_id()`；其余有 document_id+chunk_index 用 `derive_doc_id("chunk",...)` |
| `metadata.pk` | 同上 | `es.py:219-220` 回填 | 同上 | 只在缺省时回填，等价于 `_id` |
| `metadata.document_id` | base64(minio 对象路径) | `alg_doc_parse_service/server/utils.py`、`loader.py` | 稳定（按路径） | 路径含 `/V0/` 版本段；同名重复上传同值 → **不能当"本次上传"身份** |
| `metadata.file_id` | `290`（字符串/int） | `loader.py` ← Java 传 `_file.file_id` | 不稳定 | 对应 `gienrag.knowledge_base_list.id`；同名重复上传产生新行 → 新 file_id |
| `metadata.version` | `null` | `loader.py`（R13-VER-10 位置） | 存在但空 | MySQL 同名列实测 `V0`，链路没传下来 |
| `metadata.chunk_index` | `0` | 解析后排序赋号 | 半稳定 | 同内容重切分顺序一致；内容变化整体位移 |
| `metadata.offset/position/page_number/page_size` | 字符串化坐标 | `loader.py` | 半稳定 | PDF 存在全零坐标（R13 已记）；**不是 Unicode 码点区间** |
| `metadata.title/parent_file_name` | 文件名 | `loader.py` | 不稳定（展示级） | 实测存在 parent 写错（kb_9 行 id=283） |
| `metadata.source/file_path` | minio 路径 | Java 传入 | 稳定（按路径） | 现有唯一去重键（按 source 先删后写） |
| `metadata.knowledge_base_name` | `kb_9` | `loader.py` | 稳定 | 等于 ES 索引名，**不是** MySQL `kb_id=9` |
| `content_hash` / `parse_generation` / `parser_version` / `chunk_id` | — | 不存在 | — | 见 §6 |

去重/失效机制（事实）：
- ES：`duplicate_flag=True` 且非 `faq_` 时按 `source` `delete_by_query(refresh=True)` 再插入（`es.py:404-412`）。
- Milvus：同样只在 `duplicate_flag` 且非 `faq_` 时按 `source` 删（`milvus_kb_service.py:658-672`）——**这段在改造前是坏的，见 §5.3**。
- 没有任何按 `document_id`/`version`/内容哈希的代次切换逻辑；读侧也没有"一次查询固定代次"的发布指针。

---

## 3. 图数据：chunk_pk_list / file_id 来源与失效

| 存储 | 字段 | 来源 | 类型 | 失效机制 |
|---|---|---|---|---|
| Milvus `graph_base._graph_entity_<kb>` | `chunk_pk_list` | `graph_fun_tool.attribute_assignment()`（`str(pk)`，pk=ES `_id`） | `ARRAY<VARCHAR>` | 只随 drop 集合/`del_doc_by_col` 消失；无代次字段 |
| 同上 | `file_id` | 同上（ES metadata.file_id） | `ARRAY<VARCHAR>` | file_id 随重传变（MySQL 新行）→ 旧值永久悬空 |
| Milvus `graph_base._graph_triples_<kb>` | `chunk_pk_list`/`file_id`/`page_num` | 同上（增量 merge） | `ARRAY<VARCHAR>` | 同上 |
| Nebula `g_<kb>` TAG `entity` | `name,title,file_id,type` | `graph_service.py` | string（逗号拼接） | **不含 chunk_pk_list**；重抽同名顶点只报"已存在"，旧属性保留 |
| Nebula `g_<kb>` EDGE `relationship` | `name,file_id,show_flag,page_num` | `graph_service.py` | string | 不复写则旧代次 file_id 保留 |
| ES `community_summary_<kb>` | `metadata.community_id/level/member_entities/size/edge_count/kb/file_ids/file_names/sources/create_time` | `graph_summary.py:149-165` + B 新增 sources/triples | 动态 mapping | 现在由写入层整代替换（§5.2） |
| Milvus `graph_base._community_summary_<kb>` | 通用 schema（无 `community_id` 列） | `embed_change.py` 落 `MILVUS_FIELDS` | — | `community_id` 落在通用列 `chunk_doc_id`（A 本轮约定，§5.2） |

现场事实：`graph_base` 集合名带前导下划线（`generate_collection_name_uuid()` 会加 `_` 前缀）；实测 `_graph_entity_kb_9` 的一条实体 `chunk_pk_list=['794663329353800421', ...]`，与当时的 ES `_id` 一致。

---

## 4. 社区摘要两侧：本轮前后对比（实测）

| 项 | 改造前 | 改造后（连跑两次） |
|---|---|---|
| ES `community_summary_kb_9` | 7 行（全是随机 `_id`，`metadata.pk`=随机） | run1 7 行 / run2 7 行 |
| Milvus `graph_base._community_summary_kb_9` | **65 行**（create_time 跨 12 个批次，10-25 22:01 ~ 10-26 23:52，同主题重复 2~11 份） | run1 7 行 / run2 7 行（distinct pk 7） |
| distinct community_id | ES 7 个；Milvus 侧**无该列**，无法对账 | 两侧各 7 个，**集合逐项相同** |
| `ES._id == metadata.pk == Milvus.pk` | 否（各自随机） | 是（7/7） |
| run1 与 run2 的 community_id 集合 | 每次全新（uuid4） | 完全相同 |
| 读路径 | `/query_community mode=local` 可用 | 仍可用（用真实成员实体命中 1 个社区） |

命令与原始输出见 `probe_community_twice.py` / `community_twice_after.json`。

---

## 5. 最小改造方案与已落地部分（优先不改表结构）

### 5.1 P0-1 内容寻址主键（已实施，两侧同算法）

```
chunk  : id = int63(sha1("chunk|"       + index_name + "|" + file_id(or title) + "|" + seq + "|" + sha1(page_content)))
table  : id = int63(sha1("table|"       + index_name + "|" + file_id + "|" + table_ordinal))
community: id = int63(sha1("community|" + index_name + "|" + level   + "|" + community_id))
```

> **R14-A-FIX-18（2026-10-27，TL 批准）：`document_id` 已从种子中移除。**
> 原因：`document_id` 是 base64(调用方传入的路径形态)，同一文件用"完整对象键"与"裸文件名"会算出两个不同 base64
> → **谁调的决定了存什么 id** → 图侧 `chunk_pk_list`（存抽取时刻的 ES `_id`）每次重解析必然悬空，F04 `exact_chunk=0` 修不好。
> 改后 pk 只由 `(库, file_id, 块序号, 内容哈希)` 决定，跨入口稳定；`file_id` 缺失时退回 `title`（仍不含调用路径）。
> **真正生效点在解析服务**：`alg_doc_parse_service/server/utils.py:103 create_chunk_pk` / `:116 create_table_pk`
> （解析服务把 `metadata.pk` 写进块，索引层 `es.py` / `milvus_kb_service.py` 只做透传，`metadata.pk` 缺失时才走上面的派生兜底）。
> 教训：先改索引层是空转——**必须确认"算 pk 的"和"写 `_id` 的"是同一处**，否则只会改一半。

- 落地位置：`index_fulltext_service/.../controller/es.py:38`（`derive_doc_id`）、`:48`（`community_doc_id`）、`:196-210`（build_actions 分支）；`index_vector_service/.../milvus_kb_service.py:190/199`（同算法）、`:600-611`（pk 分支）。
- 两侧必须同源同实现（独立服务不能互相 import），已在两处 docstring 写明"改一处必须同步另一侧"。
- 优先级：`metadata.pk` 存在时仍以 pk 为准（保持对既有调用方兼容）。
- 效果（实测）：同一份 3 块内容连续写两次 → ES 3→3、Milvus 3→3，两次 `_id` 完全相同，且 `ES._id == Milvus.pk`。
- 边界（必须如实说）：**内容或 file_id 变化就是新 id**（新代），旧 `chunk_pk_list` 会指向已删除的旧 id → 表现为"查不到正文"，这是"明确失效"，不是错指同名新文件；要做到"旧引用打开旧版本"，需要 P1 的按代保留 + 发布指针（§6）。
- 为什么含 `file_id`：只用 document_id+chunk_index+文本时，同一路径下两个 file_id 行（重复上传）会塌成一条，会改变"同一文件有几块"的计数语义。
- **写入点同时落 `metadata.id_origin`**（`es.py:194-213` 判定、`:238` 落库、`:190` database 分支固定 `random`）：取值 `pk_from_caller` / `derived_community` / `derived_chunk_index` / `random`。这是"这个 `_id` 是怎么来的"的**唯一知情处**记录，供图侧/审计侧判定 provenance，避免下游靠重算哈希去猜（猜错就会出现"同一块两个都合法的 id"）。实测四类取值均能落库（`id_origin_check.txt`）。
  - 注意：`pk_from_caller` 只说明"id 由调用方传入"，**不等于稳定**——当前解析服务传的是随机 pk（§6.1），所以这个值现在应视为"来源明确但稳定性未知"。Milvus schema 无该列，会被丢弃，以 ES 为权威。

### 5.2 P0-2 社区摘要确定性主键 + 整代替换（已实施）

- ES：`community_summary_*` 的 `_id` 用 `community_doc_id()`；写后 `_prune_stale_community_docs()`（`es.py:349`、`:454`）删除"本次集合之外"和"同 community_id 但 `_id` 非派生值"的旧行（`delete_by_query` 按 `_id`，不 drop 索引，mapping 不丢）；清理失败返回 500，不静默通过。
- Milvus：`is_community_collection` 分支（`milvus_kb_service.py:471/602/613/643`）——确定性 pk；`chunk_doc_id` 承载 community_id（schema 无该列，见 §3）；写前"删整代 → 轮询确认 `pk>=0` 不可见 → 写新代"，确认不了（默认等 6s）返回 500 中止。
- 语义：整代替换 = 不丢索引 mapping、不 drop 集合、不留两代；同时清掉了 65 行历史堆积（R13 遗留）。
- 直接证据：改造前 ES 里 7 条随机 `_id`（`1071584032174993371` / `1285064802195168642` / `1781325502868850634`）现在都是 `404`，索引仍 7 条（未清理的话 run1 后应为 14 条）。
- 已知上限：ES 清理按 `size=5000` 扫描本索引，社区数超 5000 时会漏删（社区量级远小于此，暂不引入 scroll）。

### 5.3 P0-3 按 source 去重的真缺陷修复（已实施）

- 缺陷：`milvus_kb_service.add_doc_custom` 里构造 `DataParamModel(collection_name=..., col_name="source", col_values=add_sources)` **未传 `db_name`**，默认取配置 `milvus_conn_config.milvus_database`=`rag_knowledge_base`；若集合在别的库（如 `graph_base`），`del_doc_by_col` 的 `is_collection()` 查不到 → 返回 `code=200 "未执行删除，milvus未找到集合"` → 调用方只看 code → **静默跳过删除** → 第二写入变两代。
- 实测影响：同一 source 连续两次写入，Milvus 可见行 3 → **6**；ES 3 → 3（ES 侧删除是 `refresh=True`，无此问题）。
- 修复（`milvus_kb_service.py:658-672`）：显式 `db_name=insert_model.db_name`；删除后 `_wait_until_deleted()` 轮询确认旧行对 `query` 不可见（实测删除可见延迟 ~0.7s，上限 6s）再插入；等满仍可见则返回 500 中止，**宁可不写也不写两代**。
- 修复后实测：3 → 3。

### 5.4 未实施（需他人/需 DDL）

| 项 | 缺口 | 归属 |
|---|---|---|
| `version` 真值 | `metadata.version` 实测 `null`；MySQL `knowledge_base_list.version='V0'` | C（Java 传值） |
| `parser_version` | 解析器/配置版本未落库；不能区分"换了解析器"造成的代次 | C（解析服务）+ A（写入 metadata） |
| `parse_generation` | 无内容哈希、无递增代次、无"当前代"指针 | A（P1：`sha1(sorted(chunk_text_hashes))[:12]` 落 metadata） |
| 发布指针 | 读侧一次查询固定代次 | 需 DDL：`knowledge_base_list` 加 `parse_generation`/`parser_version`，新增 `kb_publish_pointer`（P2，需 TL+CR） |
| Nebula 边旧代次 | 重抽同名顶点/边只报"已存在"，旧 file_id 保留 | B |
| 文本定位不可变快照 | offset 指向 MinIO `parsed/*.txt`（按路径覆盖写）→ 旧 chunk 的 offset 可能指向新快照；且无 Unicode 码点区间 | A/C（需快照命名 + 区间契约） |

---

## 6. 必测清单与状态（Loop1-A 退出条件对应）

| 场景 | 判定方式 | 状态（本轮实测） |
|---|---|---|
| 同文件重复写入两次 | ES/Milvus 可见行数不翻倍，id 集合完全相同 | **PASS**（3→3；id 全等） |
| 内容覆盖（同名同路径新内容） | 新 id 出现、旧 id 明确删除 | **PASS**（`content_change.json`）：只有正文变化的第 0 块换 id（`275016707213128010`→`519226191378293716`），第 1/2 块 id 不变；两侧可见行 3→3；旧 id 在 ES 查询 0 命中（404） |
| 同名跨目录 / 同名跨库 | 用 `document_id`(路径) 区分，不按 `title` 回落 | id 含 index_name + 路径派生，成立；页面层仍存在按文件名回落（B/F03 域） |
| 版本替换（V0→V1） | `version` 参与 id；两代可共存 | **阻塞**：`metadata.version` 仍为 null（C） |
| 删除后重传 | 旧引用"明确失效"，不返回同名新文件 | 旧 id 查不到（明确失效）；"按文件名回落"仍可能指向同名新文件（展示级兜底，不得当版本身份） |
| `generate_community` 连跑两次 | ES/Milvus community_id 集合完全相同（不是只比数量） | **PASS**（7/7 逐项相同，run1=run2） |
| 端到端两次 `/parse_sync`（同文件、真实解析服务） | 不翻倍 + 主键稳定 | **PASS（C 修完后复验）**：`cn-digital.pdf`(chunk_size=120) 4 块、`docx-table.docx`（含 `table_chunks_*`/`table_summary_*`）各连解析两次 → 计数不翻倍、**两次 id 集合完全相同**、`ES._id == Milvus.pk` 全等、落库 `id_origin=pk_from_caller` 4/4（稳定来自解析侧确定性 pk）。见 `e2e_stable_afterC.md` |

### 6.0 命名约束（读写两侧必须一致，已实测）

派生主键的种子包含 `index_name`，因此**索引名/集合名的形态必须是稳定且两侧一致的**：

| 事实 | 值/位置 |
|---|---|
| 索引名来源列 | MySQL `gienrag.knowledge_base.primitive_name`（不是 `kb_name`，后者是中文显示名） |
| 当前取值 | 实测 16/16 全为 `kb_1 … kb_16`（小写 ASCII），**无大写、无中文** |
| ES 侧约束 | ES 索引名本身**不允许大写**，代码里 `is_index_lower()` 会强制小写（`es.py:34-41`、`add_documents_async` 入口） |
| Milvus 侧 | 集合名源自原样的 `collection_name`，本轮已改为 `.lower()` 后再进派生种子（否则大小写 KB 名会让 ES `_id` 与 Milvus `pk` 不同） |

**约束（读写两侧都要遵守）**：
1. 写侧：派生种子里的 `index_name` 一律 `str(name).lower()`（ES 已由 `is_index_lower()` 保证，Milvus 本轮对齐**仅作用于种子**）；
2. 读侧：**查询 ES 索引名时同样必须 `.lower()`**（ES 只接受小写索引名；`community_summary_<kb>`、`table_chunks_<kb>`、`table_summary_<kb>` 都适用）；
3. **实际集合名/索引名不要"顺手一起 lower"**：
   - ES 侧是**被迫** lower（ES 硬限制，不允许大写索引名）；
   - Milvus 侧集合名**保持原样**（`normalize = "_" + collection_name`，见 `milvus_kb_service.py:434`），只有进派生种子的那一路 lower（`:613`）。原因：Milvus 允许大写，若社区摘要写入方把集合名 lower、而 chunk/table/faq 写入方保留原样，同一个 KB 会出现**两个集合**（`_KB_17` 与 `_kb_17`），社区摘要写进一个、读另一个，表现为"社区摘要凭空消失"——比大小写不一致更隐蔽。
   - 若要统一 lower 集合名，必须**所有写入方一起改**并做迁移，不能只改某一类。
4. Nebula 图空间名 `g_<kb>` **不要 lower**（与上面无关，图空间按原始名创建）；把 lower 一路套到图空间会造成"图空间不存在"。

当前该约束是"空转安全"的（16/16 全小写），属于**为将来出现大写 `primitive_name` 预留的一致性要求**；读侧若要改，只是加一行 `.lower()`。

### 6.1 端到端复跑时暴露的最后一个身份缺口（根因不在 index_data_service）

实测：同一 PDF（`fixtures/cn-digital.pdf`，chunk_size=120）连续两次 `/parse_sync`，可见行数稳定（ES 4→4、Milvus 4→4），但两次 `_id`/`pk` 不同（`parse_twice_e2e_multi.json`）。取 `fixtures/cn-docx-direct.docx` 那一次的单块样本核对（`parse_twice_e2e.json`）：

```
ES _id          = 603542041454166576      ← 解析服务给定的 pk
派生值          = 876305758685260282      ← derive_doc_id("chunk", ...) 应得的值
```

原因：`alg_doc_parse_service` 在交给索引层之前就给每个 chunk **写死随机 pk**，共 7 处（不是 1 处，实测表格类文档也一样不稳定）：

| 位置 | 作用对象 | 关联字段 |
|---|---|---|
| `server/controller.py:407` | text / image 块 | `image_link` 把它写进 `text_parent_id_list` / `pic_children_id_list` |
| `server/controller.py:499` | 合并后的图片块 | 同上 |
| `server/controller.py:565` | PPT 分支 | 同上 |
| `deepdoc/splitter/table.py:33` | 表格全表摘要 `table_summary` | 被 chunks 的 `table_summary_id` 引用 |
| `deepdoc/splitter/table.py:48` | 表格块 `table_chunks` | 引用上者 |
| `deepdoc/splitter/table.py:89` | FinancialTableSplitter 摘要 | 被 `table_summary_id` 引用 |
| `deepdoc/splitter/table.py:107` | FinancialTableSplitter 表格块 | 引用上者 |

```407:407:services/rag-alg/alg_doc_parse_service/server/controller.py
                chunk.metadata.pk = create_uuid()
```

而我的写入层保留了"`metadata.pk` 存在则优先"的兼容规则（否则会破坏既有调用方），所以派生分支在真实解析链路上被这个随机 pk 短路。**这不是写入层能单边修的**：`deepdoc/image_link.py` 把 `metadata.pk` 写进 `text_parent_id_list`（图片→关联文本块的引用），表格侧 `table_summary_id` 也指向摘要 pk；在索引层改写 pk 会让这些引用指向不存在的 id。

实测（`parse_twice_e2e_table.json`，`fixtures/docx-table.docx` 连解析两次）：`r12a_parse_idem` 1→1、`table_chunks_*` 1→1、`table_summary_*` 1→1（**不翻倍**），但三类 `_id` 两次都变，且三者都不等于 `derive_doc_id` 的结果（说明 pk 是解析服务给的，不是写入层派生的）。

结论与建议（待 C 侧实施，属 `alg_doc_parse_service`）：
- 不要"取消设 pk"（会打断 `text_parent_id_list` / `table_summary_id` 的构造），而是**把 `create_uuid()` 换成确定性派生**。**序号必须用 `parsed_chunk_index`，不能用 `chunk_index`**——实测 `chunk_index` 的最终值在 `controller.py:644-646` 才产生（全局按 `page_number/parsed_chunk_index` 重排后重编号，并 `pop` 掉 `parsed_chunk_index`），在 `:407` 处不可知：
  ```
  :405  parsed_chunk_index = i          # sorted_all_chunks 全序，此时可用
  :407  pk = create_uuid()              # 要改的位置：此刻 chunk_index 还不存在（表格块是 table_i）
  :592  link_images_text(...)           # 图文关联用 pk，pk 必须在此前定好
  :644-646 最终排序 + chunk_index=i + pop(parsed_chunk_index)
  ```
  - text/image 块：`pk = int63(sha1("chunk|" + index_name.lower() + "|" + document_id + "|" + file_id + "|" + parsed_chunk_index + "|" + sha1(page_content)))`，在 `:407` 处即可算（`parsed_chunk_index` 于 `:405` 已赋），且早于 linking，引用关系不变。**需保留 `parsed_chunk_index` 到索引入参**（`:645` 不要 pop，或另存一份），否则写入层看不到它。
  - 表格摘要/表格块：**不能**用正文哈希做种子——`table_summary` 的正文是 LLM 生成的，同一张表两次解析文字不同，哈希必然漂移。应改用解析稳定量：`table_id = int63(sha1("table|index|document_id|file_id|table_ordinal"))`，块用 `(table_id, table_pos)`，`table_pos` 必须规范化序列化（`json.dumps(pos, sort_keys=True, separators=(",",":"))`），并保留 `table_summary_id = table_id`；同一 table 内 `(table_id, table_pos)` 必须唯一（重复会静默覆盖一块）。
  - `version` **不进种子**：`document_id` 已含 base64 路径 `/V0/` 段，版本变化天然换 id；把 version 加进种子会让"同代内 null 与 V0"算出不同 id。
- **写入层已同步对齐**（本轮）：派生序号改为"优先 `parsed_chunk_index`，缺失退回 `chunk_index`"；`index_name` 统一 `.lower()`（ES 侧本来就有 `is_index_lower()`，Milvus 侧本轮对齐，否则大小写 KB 名会算出不同 id）；`id_origin` 相应输出 `derived_parsed_chunk_index`（实测两分支均生效）。
- 在此之前，端到端口径只能说"**不翻倍、两侧一致**"，不能说"**代次稳定**"。

已知副作用（需在 C 实施时一并约定，勿留双公式）：写入层的派生种子用的是 `chunk_index`（loader 落的序号），而解析服务 `:407` 那一行执行时只有 `parsed_chunk_index`（`:406` 赋的全局序号）。两者在"纯文本、无图无表"的文档里数值一致，但在图文表混排文档里不保证一致 → 同一个块会因"走解析服务的 pk"还是"走写入层派生"得到不同 id。建议二选一并在两处写死：
- 方案 A（推荐）：解析服务派生时也用 `chunk_index`，若该字段此刻为空，就先按 loader 同一规则算好再赋（保证后续 loader 不再改写）；
- 方案 B：写入层派生优先取 `parsed_chunk_index`（存在时），解析服务用同一字段。
无论选哪个，**必须保证 ES 里能看到的序号字段与派生种子里的值是同一个**，否则 `id_origin` 判定会出现"同一块两种合法值"的歧义。

---

## 7. 复跑方式

```bash
cd /home/szf/data/dev/llmke-r12/platform/r12/qa/evidence/R14-A-20261027T021902Z
# 社区摘要两侧现状（只读）
../../../venvs/alg/bin/python probe_community_state.py kb_9
# 同一解析产物连续两次写入索引（scratch 索引 r12a_idem_parse，不碰 kb_9）
../../../venvs/alg/bin/python probe_parse_twice.py <tag>
# 连续两次 generate_community（会真调 LLM，约 20s/次）
../../../venvs/alg/bin/python probe_community_twice.py kb_9 <tag>
# 真实解析两次（需要 12340 在跑）
../../../venvs/alg/bin/python probe_parse_twice_e2e.py <tag>
```

改动加载方式：`platform/r12/run/algctl.sh restart index_vector_service`、`... restart index_fulltext_service`（只重启这两个，不动 graph/retrieval/parse）。

---

## 8. 事实 / 推断 / 判断

- **事实**：`derive_doc_id` 系列派生已落在两侧代码并以运行态数据验证（ES 3 行 id == Milvus 3 pk，两次写入 id 不变）；Milvus 四类集合 `pk` 均 `auto_id=False`（pymilvus 实测）；`_community_summary_kb_9` 由 65 行降为 7 行且两侧 community_id 集合逐项相同；`add_doc_custom` 未传 `db_name` 导致删除落到 `rag_knowledge_base`，实测重复写入 3→6；`metadata.version` 实测 `null`；`_kb_9` `num_entities=16` 而可见 8 行。
- **推断**：R13 报告的"社区摘要重复"是"只 insert 不删 + id 每轮随机"两者叠加，只改 `community_id` 稳定性而不改写入层，下一轮仍会产生同主题多行——本轮用"确定性 id + 整代替换"同时掐掉两个根因，实测验证成立。
- **判断**：F04 的"按文件名回落"只能当展示级兜底，不能当版本身份；内容寻址主键是投入最小、能同时解决"重复事件幂等"和"引用不可变"的一步，但它只保证"同内容同 id"，**跨代并存 + 读侧固定代次仍需 P1/P2**（`parse_generation` + 发布指针），而 `version` 传值仍卡在 Java 侧。
- **未验证/不夸大**：本轮没有跑完整 `r13_full_check` 主链（属 F 的域，且 F 正在改断言）；没有验证"删除后重传是否有页面级错指"；e2e `/parse_sync` 两次未完成（服务未在监听）。

---

## 9. 2026-10-27 定稿状态（FIX-18 / FIX-25 之后）

### 9.1 kb_9 最终代次（13:25:49–13:26:53 写入，13 块）

| 文件 | file_id | version | 块数 | _id |
|---|---|---|---|---|
| product-loan.docx | 290 | V0 | 1 | 897762163454970252 |
| product-loan(1).docx | 328 | V1 | 1 | 139363536840301567 |
| product-intro.pptx | 330 | V0 | 1 | 1117439109309760356 |
| pdf-digital.pdf | 331 | V0 | 2 | 409753011178200524 / 683665258912140235 |
| docx-plain.docx | 332 | V0 | 1 | 989645615430072466 |
| docx-table.docx | 333 | V0 | 1 | 984477748032687541 |
| pdf-scanned.pdf | 334 | V0 | 1 | 366245621242201281 |
| product-intro(1).pptx | 343 | V1 | 1 | 626225001556669433 |
| credit-ledger.xlsx（table_chunks / table_summary） | 329 | V0 | 1 / 1 | 1095912197551331871 / 1137902847478273881 |
| docx-table.docx（table_chunks / table_summary） | 333 | V0 | 1 / 1 | 177410851220727056 / 885155839145947657 |

校验：`ES._id == Milvus.pk` 13/13 逐条；`version` 13/13 非空；`table_*` 的 `file_id ∈ {329,333}` 且**不含陈旧 id 314**。
V0（290/330）**保留在索引**（历史可查），重建图时只抽有效版本（V1 与无更高版本者）。

**判据澄清（易错）**：`table_chunks_kb_9` 的 **2 条** = 台账 1 条 + docx-table 1 条；
**台账单独解析只产 1 条**。按"2"去判台账会误红。`331` 是**一个文件两块**，块数要算 2。

### 9.2 `.md` 转换产物（FIX-25，已实施）

`converted_file_path` 可能是 `.../V0/parsed/x.xlsx.md`，而解析服务原先不支持 `.md`
（`NotImplementedError: 不支持格式".md"`，全库 383 行中 40 行受影响）。仅加 `.md` 分支**不能**用：
`.md` 是转换产物，按纯文本读会丢 `table_chunks/table_summary`，且 `success=true` —— 静默降级。

现行规则：
```
① 由 md 路径反推同名原文件（.../V0/parsed/x.xlsx.md → .../V0/x.xlsx），取得到就解析原文件
② 取不到 → 纯文本解析，并落 metadata.parser_fallback = "md_text"（降级留痕）
```
实测（`md_fix25_verify.md`）：`.md` 入参 → 命中原文件，`table_chunks=1 / table_summary=1 / parser_fallback=None`；
无原文件的 `.md` → `success=true` + 1 块 + `parser_fallback=md_text`。
判"表格缺失"应查 `file_id` 在 `table_chunks_<kb>` 的条数，**不要**在 `table_*` 里找 `parser_fallback`。

### 9.3 本轮教训（写进证据首段，防复犯）

1. **把几分钟前的观察当现状**：13:11 报的 pid 是重启前快照，TL 据此得出相反的结论。
   规矩：服务代次只报"刚 `ss`/`/proc` 读到并附时间戳"，数据结论附查询时刻。
2. **把服务自己的说法当存储事实**：`task_statuses[*].success=true` 但索引写入失败（`All connection attempts failed -> 19527`），
   7 个文件"解析成功、库没变"。规矩：查条数 + `create_time` 晚于请求时刻。`file_ids` 参数被忽略、`.md` 不支持，同族。
3. **批量写先 dry-run 报 N**：上一版脚本按 `kb_id` 扫全表误跑 273 行（靠内容寻址主键才没翻倍）。
4. **改对逻辑、改错层**：pk 真正的生成点在解析服务，索引层只是透传——先确认"算的和写的是同一处"。

### 9.4 仍未解决（如实）

| 项 | 现状 | 归属 |
|---|---|---|
| 兜底比例未归 0 | `blocks=5 兜底=4~5`；ES 已 100% 有 version，Milvus schema 无 version 列 | C（合并时用 ES 回填） |
| `ES同pk回填=0` | 数据已同源（13/13），是查询实现问题（首版压根没发 ES 请求） | C |
| 解析侧 `query_position_by_content` 裸下标 | 短文档必中，日志累计 1296 次（最早 10-25），`except` 吞异常后 `success=true` 但零写入 | C（已给 4 行补丁建议） |
| 图侧引用 | 重建后 `exact_chunk=2/2`、命中有率 100%（B 已完成） | B |
