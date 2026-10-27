# 新缺陷：`converted_file_path` 以 `.md` 结尾的文件无法重解析

## 现象
kb_9 台账 `fid=329` 的 `converted_file_path` 是转换后的 markdown：
```
r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/parsed/R12FIX-credit-ledger.xlsx.md
```
`POST 12340/parse_sync` 返回 200，但 `task_statuses[0].success=false`：
```
server/loader.py:298  NotImplementedError: 不支持格式“.md”
server/loader.py:455  ...xlsx/V0/parsed/R12FIX-credit-ledger.xlsx.md解析失败
```
（Java 侧 `fillFilesByIds` 正是用 `convertedFilePath` 去掉 endpoint 前缀传给解析服务的，
所以产品链路上这类文件**重解析必失败**，不是我的脚本特有。）

## 范围
```
kb_9 : 273 行中 29 行 converted 为 .md
全库 : 383 行中 40 行 converted 为 .md
当前代次(kb_9 8 个文件)：仅台账 fid=329 受影响
```
`fid=314`（同文件旧行）`converted_file_path=NULL` → 回退到原始 `.xlsx`，解析成功（7.2s），
所以 `table_chunks_kb_9` / `table_summary_kb_9` 里现在挂的是 **file_id=314**，而不是当前的 329。

## 后果
1. 台账引用回指到旧行 314（KB 当前行 329），C12"引用落当前有效版本"会判错；
2. 任何"重解析 converted 为 .md 的文件"在验收里都会失败，且失败信息埋在 `task_statuses` 里（HTTP 仍 200），
   只看 HTTP 状态会误判成功——与 `filesParse` 的 `file_ids` 假成功同一族。

## 建议修法（二选一，均可小改）
- **A（解析侧）**：`server/loader.py` 增加 `.md` 分支，按纯文本读取（`ext in ('.md', '.markdown')` → text loader）；
- **B（Java 侧）**：`fillFilesByIds`/`fillFiles` 里当 `convertedFilePath` 以 `.md` 结尾时优先用原始 `filePath`（xlsx/docx 本就能解析）。

A 更彻底（转换产物本来就是给检索用的文本）；B 改动更小但会让"表格解析"走回原文件路径，产出可能不同。

## 临时规避（我在下一轮重解析里做）
对 `fid=329` 传**原始 xlsx 路径** + `file_id=329`，让表格索引里的 `file_id` 归一到 329；
这只是绕过，不替代上面的修复。
