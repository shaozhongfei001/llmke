# kb_9 全量重解析后状态（C12 步1 交付）

时间：2026-10-27 12:50–13:05；路径：`12340 /parse_sync`（Java `filesParse` 当时 500，见下）

## 1. 结果三数

```
kb_9                 9 条   version 非空 9/9
table_chunks_kb_9    2 条   version 非空 2/2
table_summary_kb_9   2 条   version 非空 2/2
合计 13 条，version 非空 13/13 = 100%
```
重解析前后条数一致（kb_9 9→9，Milvus `_kb_9` 9→9，distinct pk 9），**无翻倍、无丢失**；
但 13 条的 `_id` 全部变成新值（原因见 §4）。

## 2. 当前代次 file_id ↔ 文件名 ↔ version ↔ _id（交给 B 重建图用）

| index | file_id | version | title | _id |
|---|---|---|---|---|
| kb_9 | 290 | V0 | R12FIX-product-loan.docx | 120287042403321691 |
| kb_9 | 328 | V1 | R12FIX-product-loan(1).docx | 409721235889955614 |
| kb_9 | 330 | V0 | R12FIX-product-intro.pptx | 445478030307964037 |
| kb_9 | 331 | V0 | pdf-digital.pdf (chunk 0) | 623455035040524818 |
| kb_9 | 331 | V0 | pdf-digital.pdf (chunk 1) | 986447652642970016 |
| kb_9 | 332 | V0 | docx-plain.docx | 99869736860800068 |
| kb_9 | 333 | V0 | docx-table.docx | 875161562640603273 |
| kb_9 | 334 | V0 | pdf-scanned.pdf | 824962146013202499 |
| kb_9 | 343 | V1 | R12FIX-product-intro(1).pptx | 1050585778220806563 |
| table_chunks_kb_9 | 314 | V0 | R12FIX-credit-ledger.xlsx | 1145021270768877382 |
| table_chunks_kb_9 | 333 | V0 | docx-table.docx | 200221935568348543 |
| table_summary_kb_9 | 314 | V0 | R12FIX-credit-ledger.xlsx | 1072981982792313557 |
| table_summary_kb_9 | 333 | V0 | docx-table.docx | 355827159772508698 |

## 3. 有效版本判定规则（建议写入验收）

1. **权威字段 = `metadata.version`**（来源 `knowledge_base_list.version`，由 `file.setVersion(kbFile.getVersion())` 传入）；
2. 同一 `parent_file_name`（无父名则用 `title`）下取 **version 数值最大**者为"当前有效版本"；
3. 仅当 `metadata.version` 为空时才退回 `source` 里的 `/V\d+/`（即现状 `_ver_from_source`），并把该次退回计入打点；
4. 表格：`table_summary` 的 `chunk_index=-1` 属正常（汇总行），不要当脏数据。

## 4. 已知问题（与本次重解析相关）

**① 13 条 `_id` 全变**：`document_id` 由调用方传入的路径形态决定，`derive_doc_id` 种子内含 `document_id`。
同一个文件走不同入口（文件名 vs 完整对象键）会产生不同 id。
→ 建议把种子改为 `index + file_id + chunk_index + sha1(page_content)`（A 侧可改，等 TL 批）。

**② `table_*` 的 file_id 是旧行 314，而 KB 当前台账行是 329**
```
table_chunks_kb_9 / table_summary_kb_9: fid=314（R12FIX-credit-ledger.xlsx, V0）
knowledge_base_list 当前行:              id=329（同名, V0）
```
引用回指台账时会落到 314 而不是 329，需在图重建时统一。

**③ 检索侧"兜底"仍未归 0**（重解析后实测）
```
13:04:32  blocks=5 兜底=5 无版本行=0
12:54:59  blocks=5 兜底=4 无版本行=0
```
ES 已 100% 有 version，但 `document_version()` 收到的块里 Milvus 命中的没有 version
（`Milvus _kb_9` schema 无 version 列）→ 只能退回 source 正则。**需 C 在合并处用 ES 的 version 回填 Milvus 块**。

## 5. 图引用（未变，等重建）

```
图侧 pk 去重 10   ∩ ES(kb_9+table) 命中 = 0
```
符合预期：图还是旧代，重抽取后才能命中（B 的 M1b / F04）。

## 6. 过程说明（如实记录）

`reparse_kb9_full.py` 按 `kb_id=9` 取文件，实际命中 **273 行历史记录**（不是 9 行），逐行各触发了一次解析。
后果评估：ES `kb_9` 仍 9 条、Milvus `_kb_9` 仍 9 行、无重复无丢失（因为按 source 去重 + 内容寻址主键收敛到同一批）。
但这是对共享语料的批量写操作，**不符合"验证性写操作只在 scratch 库做"的原则**，本文件如实记录，后续不再重复。
