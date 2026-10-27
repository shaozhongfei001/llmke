# 端到端两次真实解析：代次稳定 PASS（C 改完后复验）

采集：2026-10-27T11:44:48+08:00；12340 进程 pid 619641（11:43:31 启动，晚于文件改动）；scratch 索引/集合用后即删

## A) 纯文本 PDF（fixtures/cn-digital.pdf，chunk_size=120）
```
run1 200/4.2s   ES 4 行   Milvus(rag_knowledge_base) 4 行
run2 200/1.4s   ES 4 行   Milvus 4 行
ES ids 两次完全相同 : True
Milvus pks 两次完全相同 : True
每次 ES._id == Milvus.pk : True
落库 metadata.id_origin : pk_from_caller 4/4
落库 metadata.parsed_chunk_index : 存在（C 已不再 pop）
```

## B) 含表格 DOCX（fixtures/docx-table.docx，chunk_size=512）
```
run1  ES: r12a_parse_idem 2 / table_chunks_* 1 / table_summary_* 1
run2  ES: 同上（计数不翻倍）
三类索引 ids 两次完全相同 : True
```
（table_summary 正文是 LLM 生成、两次文字不同，但 id 由 C 的 (kb,document_id,file_id,table_ordinal) 派生 → 稳定，验证了"表格不能用正文哈希"这条约束是对的。）

## 判据（B 的 pk_from_caller 收敛三判据 + 我补的第四条）
1. C 已改且 12340 已重启（启动时间晚于文件 mtime）— 满足；
2. 两类夹具各跑两次，两次 id 完全相同 — 满足；
3. 落库 metadata.id_origin 仍为 pk_from_caller（稳定来自解析侧确定性 pk，不是写入层接管）— 满足；
4. C 保留 parsed_chunk_index 到索引入参（写入层同字段派生）— 满足（实测 ES metadata 有该字段）。
