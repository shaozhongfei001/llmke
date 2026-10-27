# C15 引用可回指（chunk 级）验收与实现说明 — B

> 结论先行：**通过**。判定口径是"形态 + 传输 + 版本"三段，缺任一段都可能出现假绿/假红。
> 所有数字均可用一个命令复算：`platform/r12/venvs/graph/bin/python platform/r12/graph/provenance_stats.py`

## 1 三段判定（缺一不可）

| 段 | 问什么 | 判据 | 当前 |
|---|---|---|---|
| **形态** | 引用是不是"可解析的对象键" | 无 scheme、无重复 host、以 `r12-rag/` 开头 | 通过（C 的 `toBucketKey` FIX-19 收敛三种形态） |
| **传输** | 前端/网关能否真的取到该对象 | `GET /index/knowledgeBase/file/presign?key=` 签名口径（TL 裁 (a)） | 通过（E 已把网关注册自动化） |
| **版本** | 引用是否落在**有效版本** | `pk ∩ ES._id` 命中 > 0，且 `source` 的 `/Vn/` 与有效版本一致 | 通过（重建后命中 2/2） |

> 只做形态 → 链接打得开但是旧版；只做版本 → 取不到对象。所以三段必须一起报。

## 2 chunk 级字段：谁说、谁传、谁能读到

C15 要求 global 的结论能回到**具体 chunk**，而不只是"某个社区"。实现分三层：

```
① 图服务（我的文件）：resolve_chunk_refs()
   社区成员实体 -> 向量实体表 graph_entity_<kb> 的 chunk_pk_list
                -> 按 pk 回查 ES(ids) 取 source/offset/title/chunk_index
   命中才留，悬空的丢弃并计入 chunk_refs_stats{total_pks, resolved, dangling}
② 检索层：retrieval_global_view 优先用第一条 chunk_ref 的 source/offset，
   metadata 增 chunk_refs / chunk_pk / chunk_index
③ 块级响应：provenance_quality / identity_stability / recovered_by / chunk_pk
```

**关键实现事实**：Nebula 顶点上**没有** `chunk_pk_list`，只有 `file_id`（文件 id，逗号串）。
chunk 级引用存在向量实体表 `graph_entity_<kb>`。早期脚本把顶点 `file_id` 当 chunk pk 用，口径是错的。

## 3 本次实测数字（重建后，kb_9）

```
query_graph_data -> blocks=2
  pks = [139363536840301567, 626225001556669433]
  ES kb_9 ids 命中 2/2，两块 prov 均为 exact_chunk
provenance_stats.py ->
  blocks=2  exact_chunk=2 (100%)  stale_version=0  entity_content=0  unknown=0  verdict=PASS
global 正例（三家评级 -> 加点）：
  江南 AAA 30 / 华东 AA 60 / 北方 AA 60，均引 [L0-92b533ae]
  该社区 members 含 30个基点 / 100个基点，即数值所在社区 —— 引用指向正确
```

`chunk_refs_stats` 的价值：`resolved / total_pks` 就是引用命中率，
重建前是 `resolved=0, dangling=7`（全悬空），重建后同一字段应接近 100%。**这个比值可作常规巡检指标。**

## 4 `provenance_quality` 语义（评审最易误读的一点）

```
图来源块   -> provenance_quality ∈ {exact_chunk, entity_content_recovered, stale_version}
ES/Milvus块 -> 该字段为 None（不是"透传丢失"）
search_type 含 graph 但 prov=None -> 该块主来源不是图，是被图"再次命中并合并"
```
因此判据必须写成：**只统计 `prov == 'exact_chunk'` 的块**，不能用 `search_type 含 graph` 当入口。

## 5 两个被这轮踩出来的"静默为空"（已修，记档）

1. **早退绕过标注**：`graph_service.py` 在 `missing_pks` 为空时 `return documents`，不走标注函数。
   重建后 pk 全命中 → 正好走这条早退 → `provenance_quality` 整键消失。已改为每条返回路径都标注。
2. **白名单过滤**：19995 有两份 metadata 显式白名单（`table_retrieve.py`、`retrieval_fun_tool.process_return_results`），
   会把上游字段整批丢掉。已收敛为 `PROVENANCE_FIELDS` 常量 + `provenance_of()`，两处共用一份定义。

`chunk_pk` 做三级回退 `meta.pk -> doc.pk -> doc._id`，因为代码里**同时存在三种 doc 形态**
（图块 / 白名单重组后的 doc / ES 原生只有 `_id`）。另注：`metadata.pk` 在响应里**不存在**（不是空值），
块身份对外统一用 `chunk_pk`。

## 6 仍未闭合的部分（如实记录）

- `metadata.id` 当前语义是 `document_id`，与 `_id`/pk 易混。方案定为"双写 + 弃用"，**今天不动**，
  删除需同时满足：D 确认前端不再读 / F 脚本 grep 无引用 / 一次完整 acceptance 通过；
- community 摘要正文仍偏短（86–259 字）且 `file_ids` 是旧代——**不影响 global 的事实来源**
  （map 读 Nebula 三元组，不读摘要正文），但属版本治理项，重建社区后应一并刷新。

## 7 相邻缺陷（影响"引用可回指"的前提）：**零召回仍作答，因为拒答分支从未被走到**

> 归因要说准：**不是"模型幻觉率高"，是"该拒答的分支是死代码"**。前者无解，后者一行 SQL。

### 7.1 复现（B 独立复现，C 先发现）

```
经 /qa（configId=1）问"恒星项目的归口部门是哪个？"（kb_9 中没有对应 chunk）
  B: http=200  refs=0  answer="恒星项目的归口部门是阿里云智能。"
  C: 同题同配置            answer="恒星项目的归口部门是阿里巴巴达摩院。"
=> 同一缺陷的两次独立采样：零引用 + 确定性断言，且两次取值不同
   -> 说明该答案来自自由生成，不是检索结果
```

### 7.2 根因（代码条件由 B 逐行核对；配置读数由 C 提供，B 无 MySQL 权限未复核）

> **证据分级**（TL 统一口径）：B 亲自执行并看到输出的写"核对"；他人提供未复核的写"由 C 提供"。

```java
// services/rag-java/.../AiServiceImpl.java:369-378（B 已核对行号与条件）
if (Objects.nonNull(config.getDependOnKb()) && config.getDependOnKb() == 1
        && (Objects.isNull(retrievedData) || !retrievedData.existDocs())
        && CollectionUtils.isEmpty(files)) {
    String answer = "抱歉未能找到您要的答案";      // 正确的拒答分支
    Integer resultType = AIResultTypeEnum.DEPEND_ON_KB.getCode();
    ...
}
```
```
search_config.depend_on_kb 是**独立列**（int DEFAULT 0），不是 config_json 里的键
  id in (1,2,6,8,9,12) 全部为 0（C 只读查得；B 未复核）
-> Objects.nonNull(...) 为 true 但 == 1 为 false -> 整段短路 -> 0 命中照样进 LLM
前端 SettingDetail/index.tsx:104  dependOnKb 默认 false（C 提供）
=> “允许无依据作答”是**产品默认姿态**，不是某个人漏配
```
（更正：初稿写成"全表 NULL"，那是查错了位置——JSON 里没有该键，列里是 0。
 两者对结论无影响，但表述必须准确，否则评审去查列会以为我们没查对地方。）
`AIResultTypeEnum.DEPEND_ON_KB` 这个"拒答"结果类型因此**从未被返回过**。

### 7.3 为什么它与 C15 强相关

C15 要求"每条关键结论可回指"。当 `refs=0` 而答案仍给出事实断言时：
- 引用区为空，用户会理解为"省略了出处"，而不是"没有依据"；
- 于是"可回指"在最该生效的场景（无依据）反而完全失效。

### 7.4 判据建议（给 F）

```
refs == 0 且 answer 含事实性断言（实体名/数值/日期）-> 判 FAIL（无依据作答）
不能只看 http=200 / status / 有无 answer —— 这三者都会通过
```

### 7.5 处置（C 已给两案，等 TL 裁）

```
A 数据侧（立即生效、不重启）：给强关联助手置 dependOnKb=1（1 条 SQL）
B 代码侧（下轮）：条件放宽为"开了检索且 0 命中就拒答"，覆盖所有助手，需同步改 F 断言
```
本文档不主张任何一侧，只记录机制与复现方式；**采用哪案需同时更新 §1 的三段判据**，
否则"形态/传输/版本"全绿仍可能出现"零引用有答案"。
