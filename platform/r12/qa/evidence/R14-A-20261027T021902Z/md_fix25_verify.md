# R14-A-FIX-25：`.md` 转换产物重解析（先原文件 / 才降级 + 留痕）

改动：
- `server/loader.py`：`ext in {'.md','.markdown'}` 时先按 md 路径反推同名原文件
  （`.../V0/parsed/x.xlsx.md` → `.../V0/x.xlsx`），能取到就解析原文件；取不到才按纯文本解析并置
  `metadata.parser_fallback='md_text'`；格式分发补 `.md`/`.markdown` 走 `TXTParser`。
- `deepdoc/output_object/text.py`：`ParsedTextMetadata` 新增 `parser_fallback` 字段（可空）。

## 验证 A：`.md` 入参 → 命中同名原文件（表格结构保留）
输入就是 Java 主链会传的 converted 路径：
```
file_path = r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/parsed/R12FIX-credit-ledger.xlsx.md
index_name = r12a_md_fix_a（scratch，不写 kb_9）
```
日志：
```
13:35:28.014  .md 转换产物，优先解析原文件：r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx
```
结果：
```
task_statuses[0].success = True
table_chunks_r12a_md_fix_a  = 1 条  (_id=63641194769091487, file_id=329, table_name=授信台账, version=V0, parser_fallback=None)
table_summary_r12a_md_fix_a = 1 条
主索引 r12a_md_fix_a        = 未创建（该文件正文为空，只有表格 → 不产 text chunk，属正常）
```
→ **表格路径没有被吃掉**，且 `parser_fallback` 为空（说明不是降级）。

## 验证 B：只有 `.md`、无同名原文件 → 降级但留痕
MinIO 临时对象 `r12-rag/r12a_md_only/sample.md`（139B，无同名原文件）：
```
日志 13:35:58.667  .md 转换产物且无可用原文件，按纯文本解析（降级，parser_fallback=md_text）
task_statuses[0].success = True
ES r12a_md_fix_b: 1 条 chunk
  metadata = {file_id: 990123, version: 'V0', parser_fallback: 'md_text'}
```
→ 降级可成功，且**留痕可查**。

## 结论（按 TL 的三条判据）
```
① task_statuses[*].success 全 true                      PASS（A/B 两支）
② chunk 数 > 0 且 create_time 晚于请求时刻               PASS（B 有块；A 的块在 table_* 里，1 条）
③ 表格文件仍有 table_chunks/table_summary                PASS（A：各 1 条，file_id=329）
   并用无原文件的 .md 验降级分支                         PASS（parser_fallback=md_text）
```

## 口径更正（避免误判）
TL 要求"329 走原 xlsx 必须仍是 **2 条** table_chunks"——这个 2 是 **kb_9 索引里两个文件的合计**
（台账 329 的 1 条 + docx-table 333 的 1 条）。**台账单独解析只会有 1 条 table_chunks**，
本次 scratch 验证得到 1 条，与"表格没丢"一致。

## 未触碰 kb_9
```
kb_9 count = 9；create_time 区间 13:25:49 ~ 13:26:53（未出现 13:35 的写入）
```
验证全部落在 scratch 索引，跑完已删除（`r12a_md_fix_b` / `table_chunks_r12a_md_fix_a` /
`table_summary_r12a_md_fix_a` 已删，Milvus 对应集合已 drop，MinIO 临时对象已删）。

## 补记（13:4x，给 C 的 `fid=329` 摘要）
kb_9 里的 329 **不是** `.md` 降级产物（重解析时台账特意传原 xlsx），因此它身上没有 `parser_fallback` 载体：
```
kb_9 主索引        hits 0（台账正文为空，仅表格 → 不产 text chunk）
table_chunks_kb_9  1 条  _id=1095912197551331871 file_id=329 V0 table=授信台账 parser_fallback=<无此字段>
table_summary_kb_9 1 条  _id=1137902847478273881 file_id=329 V0 table=授信台账
```
"`.md` 入参仍保留表格"的证据只能来自 scratch 的验证 A（入参 = converted `.md`，产出 `table_chunks=1` + `parser_fallback=None`）。
**判"表格缺失"不要查 `parser_fallback`**：用 `file_id` 查 `table_chunks_<kb>` 条数，0 才是真缺块；
若该文件 text chunk 带 `parser_fallback=md_text`，说明当初只有转换产物，缺表格属预期。

**另一条计数前提**：`.md` 降级块**仍会带 `version`**（请求里给了 V0 就有）。
所以 `no_version_md_text` 的含义是"既无 version、又是 md_text 降级"，不是"降级块一定无版本"；
否则 `J == M` 的等式会在"降级但有版本"的批次里失真（此时应为 `no_version=0`）。

## 剩余风险
1. 原文件定位是**纯路径推导**：若转换产物命名不遵循 `<原名>.<ext>.md`（如 `output.md`），会走降级分支并留痕，不会静默；
2. `parser_fallback` 目前只写在 text chunk 的 metadata 上；表格块来自原文件解析，不需要该标记。
