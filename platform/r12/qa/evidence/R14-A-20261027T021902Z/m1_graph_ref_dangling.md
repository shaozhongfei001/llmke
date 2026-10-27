# M1 前置发现：图侧 `chunk_pk_list` 全量悬空（引用无法回指原文）

采集时间：2026-10-27 12:0x～12:2x；服务：ES 19200、Milvus 19630、graph 19529

## 1. 三组集合对比（决定性）

```
实体 pk 去重           = 10
三元组 pk 去重         = 10   （与实体 pk 集合完全相同）
entities pk ∩ ES kb_9 _id(9 条)      = 0
entities pk ∩ Milvus _kb_9 pk(9 行)  = 0
ES kb_9 _id ∩ Milvus _kb_9 pk        = 9   ← 写入层两侧一致
```
即：**ES 与 Milvus 之间是一致的（9/9），但图侧 10 个 pk 与两者都完全不交**。

## 2. 为什么悬空

`graph_service.py:551` 明确语义：`chunk_pk_list` 是"抽取时刻 ES 文档 `_id`"。
图侧记录的 file_id 是 **258 / 268**（product-loan.docx / product-intro.pptx 的旧代），
而当前 ES `kb_9` 的 file_id 已是 **290 / 328 / 330 / 331 / 332 / 333 / 334 / 343**（acceptance 轮重解析）。
旧代 chunk 在 ES **任何索引**里都查不到：
```
POST /_search {"query":{"ids":{"values":["3715198606399299383"]}}}  -> 0 hits（全索引）
POST /_search {"query":{"ids":{"values":["3876504572213913891"]}}}  -> 0 hits（全索引）
```

## 3. 后果（对 M1 / F04 判据的影响）

- `without_refs = 0` 是**假健康**：refs 存在，但指向不存在的 chunk。
- 所有实体/三元组在 `fetch_chunk_documents` 里都必然落到 `entity_content_recovered`（非 `exact_chunk`）。
- **跨副本比较 pk 集合没有意义**：base 与 copy 都悬空，`set 相等` 会给出"全等"的假 PASS。
  M1 若要在副本上验"合并后 refs 守恒"，前提是副本重建时**重新走图抽取**（得到新代 pk），
  否则只能验"合并逻辑本身"，不能验"引用有效性"。

## 4. 对 B 提的两个疑点的裁决

**疑点1（合并后跨文件）**：`5000万元`(file 268) ∪ `人民币5000万元`(file 258) → 4 pk。
跨文件本身成立，但这 4 个 pk 在当前库全部不存在，属"悬空并集"，不是"跨文件引用面扩大"。

**疑点2（同一 pk 挂在两个 file_id 下）**：**不是归属错，是 `file_id` 与 `chunk_pk_list` 不同步**。
- 代码依据：`graph_fun_tool.py:372-374` 与 `404-406`，`file_id` 和 `chunk_pk_list` **各自独立 append**，
  没有"同一 chunk 必须同 file"的约束；
- chunk 级聚合本身是设计，已实测证实：ES `_id=498386897502206386`（fid=290）的同一 chunk 同时含
  `1000万元` / `5000万元` / `30·60·100个基点` → 一个 chunk 被多个实体共同引用是正常的；
- 因此"一个 pk 出现在两个实体的 `file_id` 不同取值下"= 实体行的 `file_id` 只记了它自己那次 mention 的文件，
  而 pk 列表聚合了全部 mention。**读数自相矛盾，但底层引用本身没写错**。

## 5. 建议（不属于 A 的改动范围，供 TL/B 决策）

1. M1 副本必须在**重解析之后**再重建图，否则 `exact_chunk` 恒为 0；
2. 给 `file_id` 与 `chunk_pk_list` 加一致性断言（同一 pk 的所有 mention 必须同 file），
   或改成 `chunk_pk_list` 存 `{pk: file_id}` 映射；
3. 图侧加"引用有效性巡检"（定期用 pk 回查 ES，缺失即标记 `dangling`），否则重解析一次就静默失效。
