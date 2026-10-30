# B1 实时链路 + D1 真实 DDL：实物证据（2026-10-31）

> 结论先行：**B1 的隔离候选写入/回退成立**（真实 ES+Milvus，基线逐项未变），
> **D1 的迁移幂等/回退/重放成立**（真实 41 表 schema 的隔离副本）。
> **但"上传→自动解析"在运行栈中被环境缺陷阻断**：本机 LibreOffice 缺 Writer 组件，
> 所有新上传在转换步骤失败，解析服务根本没被调用。缺陷记录见 §3，未修复（需 root 安装）。

## 1. B1-4 隔离候选写入 + 回退演练

脚本 `scripts/v2_snapshot_candidate_apply.py`，三动作 `apply / verify / rollback`：

- 命名空间强制 `v2cand_` 前缀，只操作带前缀的目标；rollback 只删 manifest 登记的四个对象；
- apply 先记线上基线（ES `_count`），rollback 后逐项比对 —— **这是"回退成立"的硬证据**。

### 1.1 333 docx（已有样本）

```
apply   es: v2cand_kb_9=2, v2cand_table_chunks_kb_9=1; milvus 同；baseline kb_9=270, table_chunks=2
verify  es 2/2 ids、2 by_artifact；table 1/1；milvus 2 与 1 行 —— OK
rollback deleted 4 个对象；kb_9 270→270、table_chunks 2→2 unchanged
```

### 1.2 999011 新上传文件（真实新文件）

```
apply   es: v2cand_kb_10=46, v2cand_table_chunks_kb_10=17; milvus 同；baseline kb_10=11, table=24
verify  es 46/46 ids、46 by_artifact；17/17；milvus 46 与 17 行 —— OK
rollback kb_10 11→11、table 24→24 unchanged；无 v2cand_* 残留
```

## 2. B1-3 一份新文件经真实上传链路

### 2.1 上传本身成功（服务 API，非模拟）

`POST /index/api/knowledgeBase/file/uploadFileList`（rag-index-service 18082，context-path `/index`）：

```
999011  M1-实体类型体系与归一化方案.docx  kbId=10  30.6 KB  status=1
999012  v2-upload-sample.txt             kbId=10  256 B    status=1
```

MinIO 落盘已核实：`/data/r12-rag/kb_10/M1-.../V0/M1-.../xl.meta` 31799 B（≈源文件 31365 B）。

### 2.2 自动解析被阻断（真实缺陷，见 §3）

两个文件都停在 `file_parse_task.status=5`，`end_time=NULL`，解析服务日志里**只有**
`/parse/multi_version`，**没有** `/parse`。索引服务 error log：

```
00:52:00.135 NullPointerException: Could not open document: r12conv-14976873283321975892.docx
00:52:00.142 PdfConvertorUtils libreoffice convert filePath:http://127.0.0.1:19000/r12-rag/kb_10/M1-...
00:52:00.169 FileAppServiceImpl 调用文档解析接口出现异常【r12-rag/kb_10/M1-...】: Cannot parse null string
00:55:00.031 libreoffice convert filePath:.../v2-upload-sample.txt
00:55:00.068 调用文档解析接口出现异常【null】: libreoffice错误
```

### 2.3 绕过转换后链路本身是通的

直接按 Java 会发的同形请求调解析服务（bucket 内相对键 `r12-rag/kb_10/...`）：

```
POST /parse -> {"success": true, "msg": "正在执行"}
解析 0.92s；切分告警：54/54 条文档缺 offset/position/page_size/page_number
ES   kb_10          5 -> 11（该文件 6 条），table_chunks_kb_10 该文件 23 条
Milvus _kb_10 该文件 6 行，source 与 legacy 一致（r12-rag/kb_10/.../V0/...）
```

`source` 形态与既有文件一致，证明 §B1 上一轮"source 是文件身份键"的判断在真实数据上成立。

### 2.4 同一文件的快照与投影

doc2md `fix/017-ir-emission-wiring @ 086de3f` 四步真跑（scan/copy-to-vault/route-parsers/parse-markitdown），
产物四件齐全：`parse_manifest.json / parsed_metadata.json / parsed_text.md / document_ir.json`。
commit 后 `artifact_id = 881f68c9…7b95`，`artifact_quality=COMPLETE`。

投影：text 46 块（2824 字符）、table 17 块；legacy：text 6 块（2646 字符）、table 23 条（6174 字符）。

**差异解释（必须解释，不设阈值）**：

| 项 | legacy | 投影 | 说明 |
|---|---|---|---|
| text 块数 | 6 | 46 | 分块粒度不同（legacy 512 窗口合并，投影按 IR 块） |
| text 字符 | 2646 | 2824 | 覆盖基本一致（+6.7%），差值来自切分边界 |
| table 条数 | 23 | 17 | 同一份 17 张表；legacy 额外产出摘要行 |
| 合计字符 | 8820 | 2824（text）+ 表格正文 | parsed_text.md 11828 字符中含 159 行 Markdown 表格语法（管道符/分隔线），属格式开销 |

结论：**没有整段丢失**。上一轮"legacy 只覆盖 22%"的猜法被这张表推翻——差异是分块与格式开销，不是内容缺失。

## 3. 缺陷 D-01（真实、未修复）：LibreOffice 缺 Writer 组件，阻断所有新上传

- 现象：任何新上传（docx/txt）在 `kbFile2Pdf` 阶段失败，docx 走"回落直接解析"分支后仍抛
  `Cannot parse null string`；txt 走 else 分支直接 `libreoffice错误`。
- 根因证据：
  - `dpkg -l | grep libreoffice` 只有 `calc / impress / draw / core / math`，**没有 `writer`**；
  - `/usr/lib/libreoffice/share/registry/` 有 `calc.xcd / impress.xcd / draw.xcd`，**没有 `writer.xcd`**；
  - 本机 `soffice --headless --convert-to pdf <docx>` 直接报 `Error: source file could not be loaded`
    （此前用退出码判断"转换成功"是假象：soffice 失败也返回 0，已纠正）。
- 影响：验收判据"用户上传→自动任务→有效产物→检索→问答"在运行栈上**不成立**；
  与 V2 代码无关，是环境缺件。
- 解锁条件：`apt-get install libreoffice-writer` 需要 root；当前 `sudo` 需密码，
  且 tsinghua/archive/security 源上 `1:7.3.7-0ubuntu0.22.04.5` 与 `.12` 的 deb 均 404（实测），
  因此**不能自行解除**，属真实外部阻塞（只阻塞"上传自动解析"这一条，其余实现继续）。
- 建议补丁（未实施，需部署验证）：`PdfConvertorUtils.isNeedConvert()` 对 deepdoc 原生支持的格式
  （docx/xlsx/pptx/txt/md/html/csv/pdf）直接返回 false，跳过 LibreOffice，避免整条链依赖缺失组件。

## 4. D1 真实 DDL 与迁移验证

### 4.1 只导结构

```
mysqldump --no-data --skip-comments --skip-add-drop-table --single-transaction \
  --set-gtid-purged=OFF gienrag  >  db/ddl/gienrag-schema-20261031.sql
```

833 行、41 个 `CREATE TABLE`、**0 条 INSERT**（已 `grep -c '^INSERT'` 核验），无口令、无数据。

### 4.2 隔离恢复副本

`gienrag_v2_restore`：导入后 `information_schema.tables` 计数 = 41，与源库一致。

### 4.3 迁移草案 `db/migrations/V2_0001_parse_artifact.sql`

给 `knowledge_base_list` / `file_parse_task` 增加 `content_uid / parse_artifact_id / artifact_generation`
与三个索引，全部可空、不建外键、不改既有列；用 `information_schema` 判定实现幂等。

`scripts/v2_migration_check.py`（库名必须含 `restore/v2`，口令走环境变量）实测：

```
baseline_columns      kbl=35  fpt=19
apply_twice_idempotent 两跑无报错，列齐（idempotent）
indexes               idx_kbl_parse_artifact, idx_kbl_content_uid, idx_fpt_parse_artifact
semantic_probe        LIKE 影子表插入 artifact_id + generation，按前缀查回 = 1
rollback_twice_idempotent 列全部消失，无残留
replay_after_rollback 再正向跑一次仍成功
status = OK
```

## 5. 下一步（自动接续，不等确认）

1. 缺陷 D-01 的真实解锁只有两条：root 安装 `libreoffice-writer`，或在候选实施 §3 的跳过转换补丁
   并部署验证；二者都需要改动运行栈，先做补丁 + 单测，部署待窗口。
2. C1：固定 HippoRAG 版本、独立环境安装、native_id→input_unit→SourceRef 映射（与 D-01 无依赖，可并行）。
3. A2：MinerU/OCR 路线核实（本机 `magic_pdf` 未安装，日志已确认；查离线包/许可）。
