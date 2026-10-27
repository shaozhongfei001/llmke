# kb_9 图全量重抽取：前置条件、备份、步骤、验收、回滚

TL 于 2026-10-27 批准对 kb_9 做一次完整重抽取（目的是让 `exact_chunk` 从 0 变 >0），
并明确**顺序必须等 A 完成 C12 步1（`metadata.version` 落库）**。本文记录可执行方案与判据。

## 0. 为什么必须重抽取（不是"效果调优"）

```
图侧 chunk_pk_list 10 个 pk ∩ 当前 ES kb_9 9 个 _id = 0
POST /_search {"ids":["3715198606399299383"]} 全索引 = 0 hits
19529/query_graph_data 返回 2 条块 → 全部 recovered_by=entity_content，exact_chunk=0
```
`chunk_pk_list` 的语义是**抽取时刻 ES 文档 `_id`**（`graph_service.py:551`）。kb_9 经过
acceptance 轮重解析，`_id` 全换（290/328/330/331/332/333/334/343），旧 id 在任何索引里都不存在。
增量抽取只做 merge（append），没有清理悬空 id 的路径，所以只能全量重抽。

## 1. 前置条件（缺一不可）

| # | 条件 | 当前状态 | 判定方式 |
|---|---|---|---|
| 1 | A 的 C12 步1：`metadata.version` 落库 | **未完成**（9 条 chunk 全为 `None`） | `GET /kb_9/_source=metadata` 看 `version` 非 null |
| 2 | 备份已完成 | 已完成 | `backup/kb_9-20261027T041728Z/manifest.json` |
| 3 | 19529 / 19995 / 19526 / 19200 均通 | 是 | 端口探测 |
| 4 | C 的"开图 refs=0"（setdefault 空键致 rerank 400）已修 | **未确认** | 含大写 ASCII 的问句开图 refs≥1 |

条件 4 不修也能重抽取，但**重抽取后的效果无法验证**（refs 恒 0 会掩盖一切），因此重抽取排在 C 修完之后。

## 2. 备份（已完成，可随时重跑）

```bash
NACOS_SERVER_ADDRESS=127.0.0.1:18848 DATA_ID=index_graph_config_py GROUP=DEFAULT_GROUP \
  platform/r12/venvs/graph/bin/python platform/r12/graph/backup_graph.py kb_9
```
产出 `platform/r12/graph/backup/kb_9-<UTC>/`：

```
nebula.json                 87 顶点 + 122 边（全部属性）
milvus_entity.json          53 行（含 chunk_pk_list）
milvus_triples.json         72 行
es_community_summary.json   7 条社区摘要
es_chunks.json              9 条 chunk（含 _id / file_id / version）
manifest.json               行数 + 恢复步骤
```
> 本次实测与 A 的基线逐项一致：**87 / 122 / 53 / 72 / 7 / 9**。这就是"可恢复路径"，回滚时按
> `manifest.json.restore` 逐步回灌即可。

## 3. 重抽取步骤（在条件 1、4 满足后执行）

```bash
# 3.1 先清 Nebula 空间（顶点属性里的 file_id 也是旧代，只 merge 会留下旧属性）
curl -s -X POST http://127.0.0.1:19529/del_space -H 'Content-Type: application/json' \
     -d '{"space_name":"kb_9"}'

# 3.2 全量重抽取（drop 向量两表 + 按当前 ES 文档重抽）
platform/r12/venvs/graph/bin/python platform/r12/graph/rebuild_graph.py kb_9

# 3.3 重建社区摘要（chunk_refs 在这一步落库）
curl -s -X POST http://127.0.0.1:19529/generate_community -H 'Content-Type: application/json' \
     -d '{"space_name":"kb_9","with_summary":true}'
```

## 4. 验收判据（按顺序，任一不过就回滚）

| # | 判据 | 期望 | 说明 |
|---|---|---|---|
| V1 | `ref_validity.before.hit` | **> 0**（当前 0/10） | `m1_normalize_diff.py` 新增指标 |
| V2 | `query_graph_data` 的 `recovered_by` | 至少一条为 `None`（即 `exact_chunk`） | 现全为 `entity_content` |
| V3 | Nebula 顶点 / 边 | 与快照同量级（合并后 79 / 122） | 落差需能逐条解释 |
| V4 | `community_summary` 的 `chunk_refs_stats.resolved` | **> 0**，且 `dangling` 归零 | C15 的硬指标 |
| V5 | global 引用卡片 | `metadata.chunk_pk` 非空、`offset` 为具体块区间 | 不再只有 `gc-<cid>` |
| V6 | local 开图 refs | ≥ 关图，且块 `search_type` 含 `graph` | 依赖 C 的修复 |
| V7 | `entities.rows` / `triples.rows` | 53→52 / 72 | 见 M1 预演 |

## 5. 回滚路径

1. `POST 19529/del_space {"space_name":"kb_9"}` 清掉重抽结果；
2. 按 `backup/<ts>/manifest.json.restore` 回灌 Nebula / Milvus / ES；
3. 回灌后跑 `m1_normalize_diff.py` 与 A 的 `probe_entity_citations.py` 对账，
   确认 87 / 122 / 53 / 72 / 7 / 9 与快照一致。

**禁止**在未确认备份存在的情况下 drop 任何图数据。

## 6. 本轮已完成的代码改动（等重抽取一起验）

| 文件 | 改动 | 目的 |
|---|---|---|
| `graph_summary.py` | 新增 `resolve_chunk_refs()` / `_entity_chunk_pks()` / `_es_chunk_meta()`；摘要落库 `chunk_refs` + `chunk_refs_stats`；旧摘要读取时就地解析 | C15：global 引用能回到 chunk |
| `graph_summary.py` | `_entity_chunk_pks` 读向量实体表（`db_name=graph_base`），**不读顶点 `file_id`** | 顶点上没有 chunk 级引用，早期脚本把 file_id 当 pk 是错的 |
| `retrieval_global_view.py` | 引用 source/offset 优先取第一条 `chunk_ref`；metadata 增 `chunk_refs` / `chunk_pk` / `chunk_index` | 引用卡片可定位到具体块 |
| `m1_normalize_diff.py` | 同时输出实体名集合差 + **引用有效性命中率**（`ref_validity`） | TL 要求堵"pk 集合相等"的假 PASS |
| `backup_graph.py` | 新增只读备份脚本 | 重抽取的可恢复路径 |
