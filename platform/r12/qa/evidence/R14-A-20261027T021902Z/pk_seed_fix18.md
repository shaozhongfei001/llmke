# R14-A-FIX-18：chunk 主键种子去掉 `document_id`

## 问题（TL 已批）
`document_id` 由**调用方传入的路径形态**决定：
```
r12-rag/kb_9/R12FIX-product-loan.docx/V1/R12FIX-product-loan(1).docx  -> document_id=cjEyLXJhZy9rYl85...
R12FIX-product-loan(1).docx                                            -> document_id=cHJvZHVjdC1sb2FuKDEp...
```
而 `derive_doc_id` 种子含 `document_id` → 同一文件、同一内容、换个入口解析就换一代 id
（实测 `1689901252393637717 → 409721235889955614`）。
图侧 `chunk_pk_list` 缓存的是旧 id → 每次重解析必然悬空，这是 F04 `exact_chunk=0` 的机制根源。

## 改法（已落源码，两侧同口径）
```python
# 旧：derive_doc_id("chunk", index, document_id, file_id, seq, sha1(content))
# 新：derive_doc_id("chunk", index, file_id or title, seq, sha1(content))
_fid = meta.get("file_id")
if _fid in (None, ""):
    _fid = meta.get("title")     # 文件级标识缺失时的退路（不用 document_id）
```
- `es.py`：`controller/es.py` chunk 主键分支
- `milvus_kb_service.py`：`insert_vector_documents_custom` 的 pk 分支
- 两侧必须逐字同源（index_name 已在两侧各自小写化，保持原样）
- 社区摘要 `community_doc_id`（`level + community_id`）**不受影响**

## 预演：现行 9 条 chunk 在新种子下的预期 id（重启+重解析后应逐条命中）
| 现行 _id | 新种子预期 _id | file_id | seq |
|---|---|---|---|
| 120287042403321691 | 897762163454970252 | 290 | 0 |
| 409721235889955614 | 139363536840301567 | 328 | 0 |
| 445478030307964037 | 1117439109309760356 | 330 | 0 |
| 623455035040524818 | 409753011178200524 | 331 | 0 |
| 986447652642970016 | 683665258912140235 | 331 | 1 |
| 99869736860800068 | 989645615430072466 | 332 | 0 |
| 875161562640603273 | 984477748032687541 | 333 | 0 |
| 824962146013202499 | 366245621242201281 | 334 | 0 |
| 1050585778220806563 | 626225001556669433 | 343 | 0 |

（脚本用 ES 现役 `page_content` 的 sha1 复算，口径与代码一致：`seq` 优先 `parsed_chunk_index`，缺失退回 `chunk_index`。）

## 不兼容影响（必须写进交付说明）
1. **所有已有 chunk id 会再变一次**（包括本轮刚重解析的 13 条）；
2. 图的 `chunk_pk_list`、社区摘要的 `chunk_refs`、任何按 pk 缓存的引用全部作废；
3. 因此顺序只能是：**改种子 → 重启两个索引服务 → 重解析 kb_9 → 重建图/社区**，不能先重建图。

## 回归（TL 要求的三组，冻结解除后执行）
1. 同一文件两种 `document_id` 形态解析 → `_id`/`pk` 完全相同；
2. 内容改一个字符 → 只有对应块换 id，其余块不变；
3. `ES._id == Milvus.pk` 逐条成立。

## 状态
源码已改完、语法校验通过（未重启、未写索引，遵守 12:52–13:17 冻结）。
等待 13:17 后统一重启 → 重解析 kb_9 → 出三组回归 + 最终 id 清单给 B。
