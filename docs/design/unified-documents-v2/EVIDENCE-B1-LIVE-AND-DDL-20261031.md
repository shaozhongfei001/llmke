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

## 6. D-01 拆成两个缺陷（补测后更正）

上一版把上传失败整体归给 LibreOffice，**不完整**。异常栈显示 docx 的失败点在别处：

```
ApplicationException: Cannot parse null string
  at FeignErrorDecode.decode(FeignErrorDecode.java:41)
  at ModelInfoAppServiceImpl.allPage(ModelInfoAppServiceImpl.java:164)   <- userClient.getUserType()
  at ModelInfoAppServiceImpl.getSimpByModeName(:434)
  at FileAppServiceImpl.setModel(:317)
  at FileAppServiceImpl.filesParse(:155)
  at FileParseTaskAppServiceImpl.execTask(:216)
  at FileParseTaskScheduler.scheduleTaskWithCronExpression(:38)          <- 定时线程
```

### D-01a：LibreOffice 缺 Writer（环境）
见 §3。docx/pptx 有回落，txt 等无回落 → 直接失败；已确认安装需 root 且源上 deb 404。

### D-01b：调度线程无用户令牌，模型解析 Feign 返回 500 空体（代码/契约）
- `FeginTokenRequestInterceptor` 只从**当前 HTTP 请求头**取 `Authorization` 再透传
  （`rag-common/.../FeginTokenRequestInterceptor.java:42,53,67`）；
- 定时线程 `FileParseTaskScheduler` 里没有请求头 → 调 auth `getUserType` 时无令牌；
- 实测 `GET http://127.0.0.1:18081/auth/user/getUserType`（不带令牌）= **HTTP 500 且响应体为空**；
- Feign 错误解码器对空体解析失败 → `Cannot parse null string`，把真实原因（未授权）掩盖成解析错误；
- 该异常发生在 `setModel()`，**早于** `/parse` 调用 → 解析服务从未收到请求（与日志一致）。

修复选项（均需重启验证，**本轮未改码**，因涉及权限语义，不猜）：

| 选项 | 做法 | 风险 |
|---|---|---|
| A | 调度线程按任务的 `create_by` 注入用户上下文并透传令牌 | 需令牌可用性；改上下文传播面 |
| B | 内部服务令牌（已有 `internal-token`）允许 auth 内部端点 | 需两端契约变更，最小面可控 |
| C | 调度路径 `needAuth=false` | 绕过模型级授权，**不可在未授权下采用** |
| D | 仅修 Feign 解码器，让 500 展示真实原因 | 只改善可观测性，不解除阻断 |

建议顺序：D（立刻做，零语义变化）→ B（契约化内部调用）→ A（如仍需用户级权限）。

## 7. 重复解析幂等（可靠性实测）

对同一文件、同一 payload 再次 `POST /parse`，等待两轮完整跑完（含表格总结 46s）后计数：

```
ES   kb_10（该文件）           6  -> 6
ES   table_chunks_kb_10（该文件）23 -> 23
Milvus _kb_10（该文件）        6  -> 6
```

结论：**同一 payload 重复解析不产生重复块**（写入按稳定 id 覆盖）。
边界：这不是"代次隔离"证据——换了 chunk 参数/解析器后的新旧共存未测。

## 8. 修复选项 D 已实施并真实执行（Feign 空体不再掩盖真实原因）

改动：`rag-common/.../feign/FeignErrorDecode.java`（**零权限语义变化**，只改错误呈现）

- 空体 / 空白体：返回 `下游服务返回空响应体: <methodKey> HTTP <status>`；
- 非 JSON 体（HTML 错误页等）：返回 `下游响应非 JSON: <methodKey> HTTP <status>`，
  不再让 fastjson 的 `JSONException` 盖掉真实状态码；
- 正常 JSON 错误体：仍原样保留下游 `errorCode/errorMsg`。

验证方式（离线编译 + 真实执行，不是只看编译过）：

```
mvn -o -q -pl rag-common -DskipTests compile      # exit 0
javac -cp <rag-common/target/classes>:<BOOT-INF/lib/*.jar> Probe.java
java  -cp .:<同上> Probe
```

实测五个分支：

```
body=<null>   -> ApplicationException: 下游服务返回空响应体: UserClient#getUserType() HTTP 500
body=''       -> ApplicationException: 下游服务返回空响应体: UserClient#getUserType() HTTP 500
body='  '     -> ApplicationException: 下游服务返回空响应体: UserClient#getUserType() HTTP 500
body=not-json -> ApplicationException: 下游响应非 JSON: UserClient#getUserType() HTTP 500
json-body     -> ApplicationException: 没有token          （下游 errorMsg 保留）
```

边界：该修复**不解除** D-01b 阻断（调度线程仍然无令牌），只让下一次上传失败时显式显示"未授权"而不是
"解析失败"；要真正恢复"上传→自动解析"，仍需 A/B 选项之一（涉及权限语义，等授权）。
部署提示：rag-index-service 是 fat jar，`rag-common` 变更后必须重新打包该服务才生效，本轮未重启运行栈。

## 9. D-03（新发现，真实消费者证据）：投影缺 `table_summary` 通道

检索侧在 `enabled_summary=true` 时会把 `table_summary_<kb>` 加进召回索引列表，
并用命中的 `pk` 反向拉 `table_chunks`（`alg_retrieval_service/app/retrieval_service.py:54,70`，
`retrieval_table_chunks()` 就是"总结→明细"两段式）。

而投影只产 text 与 table 两个通道，**没有 LLM 表格总结**。实测 999011：

```
channels {'text': 46, 'table': 17}   missing ['table_summary']
```

严重度更正（按实际代码复核，不夸大）：`retrieval_service.py:56-57` 把 `table_chunks_<kb>`
**无条件**加入召回列表，所以切 snapshot 后表格仍能被**直接**检索到；缺的是
"总结命中 → 按 pk 拉明细"的第二段（`retrieval_table_chunks()`）。
因此后果是**表格匹配质量退化**（失去两段式召回），不是"表格完全检不到"。

但该路径 `retrieval_service.py:397` 把 `enabled_summary=True` **写死**（不是配置项，
`search_config.config_json` 里也没有该键），所以不能靠改配置绕开——要么投影补摘要通道，
要么改消费者。

已做（本轮）：`ingest_pipeline.channel_gaps()` 把缺口显式列进 `missing_channels`，
只要文档含表格就报 `table_summary`；测试 `test_table_summary_channel_gap_is_reported_not_silent` 钉住。
未做（需择一，且有取舍）：① 投影产出表格摘要通道（要接 LLM，成本与一致性另算）；
② 让检索在 snapshot 模式改为 `table_chunks` 直检——改消费者，需契约确认。

## 10. 【更正】任务状态 4 不是失败，是"处理成功"

上一版把 `file_parse_task.status=4` 当成失败并与文件状态 3 对比，**判断错了**。
`ParseTaskStatusEnums` 定义：`PENDING(1) / DEAL_ING(2) / RETRY_ING(3) / SUCESS(4, 处理成功) / DEAL_FAIL(5, 处理失败)`。
所以 51/52/53/54/55（task 4 + file 3）与 999013（task 4 + file 3）都是**一致的正常终态**，
并不存在"状态不一致"缺陷；§13 里"成功路径未回写任务状态"的说法同样作废。

剩余的真实小瑕疵只有一条：成功路径没有清空 `error_msg`，历史 recover 文本会留在行上，
排查时容易被误读（我自己就被误读了一次）。属可观测性问题，不是数据/功能缺陷。

## 11. D-03 补齐：投影产出 `table_summary` 通道（本轮）

实现：`ingest_pipeline/summary.py` + `ingest(..., summarize=...)`。

约定（照检索侧真实用法对齐，不是自造）：
- 表格块写入 `table_summary_id`；
- 总结文档 `pk` = 该 `table_summary_id`（因为检索取的是 `doc.metadata["pk"]`，
  再按 `table_summary_id in [...]` 拉明细，见 `multiple_retrieval.py:164`）；
- id 种子 = `index|file_id|table_id`（**不用正文哈希**，与 legacy `create_table_pk` 的理由一致：
  LLM 摘要文本每次不同）；
- 两档 summarizer：`extractive`（离线/单测，输出带 `[extractive]` 标记）与 `llm`（本地端点），
  LLM 失败自动退回抽取式并保留标记——不把兜底冒充成模型摘要。

实测 999011（17 张表）：

| 档位 | 通道计数 | 兜底条数 | 样例 |
|---|---|---|---|
| extractive | 46 / 17 / **17** | 17（全部） | `[extractive] 表格 t001：文档编号 | RAG-ALG-GRAG-M1-001…` |
| llm（18092） | 46 / 17 / **17** | **0** | `这张表格概述了文档RAG-ALG-GRAG-M1-001的版本信息、上游依据、交付物及覆盖范围，数据源为…共145份素材。` |

`missing_channels` 在生成总结后由 `['table_summary']` 变为 `[]`。

写入验证（隔离索引 `v2cand_*`，ES 三通道）：apply 46/17/17 → verify 全部按 pk 与
`parse_artifact_id` 命中 → rollback 后 `kb_10 11→11`、`table_chunks 24→24`、
`table_summary 2→2` 未变。

**未做**：Milvus 侧 `_table_summary_kb_10` 集合写入（候选脚本模板只覆盖 text/table，
需要按集合模板分别克隆）；检索侧"总结→明细"两段式的端到端联调（需切 snapshot 读路径）。

## 12. "总结 → 明细"两段式端到端联调（本轮，含两个真 bug）

按检索真实查法在隔离集合上跑通：先用查询向量在 `v2cand_table_summary_kb_10` 取 top1，
再按 `table_summary_id in ['<pk>']` 到 `v2cand_table_chunks_kb_10` 拉明细。

```
{"summary_pk": 346757280400448423, "score": 0.5752,
 "linked_chunks": 1, "link_ok": true,
 "sample": "文档编号 | RAG-ALG-GRAG-M1-001\n版本 / 状态 | V1.0 / 待评审\n上游依据 | 《Grap…"}
```

过程中撞到并修掉两处**真实**类型/主键错误：

1. **id 类型反了**：生产 `_table_chunks_*` 的 `table_summary_id` 是 **VARCHAR**，
   `_table_summary_*` 的 `pk` 是 **INT64**。最初写成"表格块存 int"，Milvus 直接拒绝：
   `cannot parse expression: table_summary_id == 64, comparisons between VarChar and Int64 are not supported`。
   现改为：总结 pk 用 int，写到表格块上转十进制字符串。
2. **候选写入脚本把主键改成自增序号**，导致总结 pk 变成 1..17、与 `table_summary_id` 对不上，
   表现为 `linked_chunks=0`。现改为使用投影里登记的 `pk`（总结 pk 必须等于关联值）。

这两条都说明：**"字段名对上"不等于"类型与主键语义对上"**，只有真跑关联查询才暴露。

## 13. D-01b 解除并部署验证（本轮，真实上传跑通）

按"系统上下文"口径修了三处，并**实际换掉运行中的 index-service jar** 验证：

| 改动 | 原因 | 位置 |
|---|---|---|
| 无用户上下文时按平台配置解析模型（`effectiveNeedAuth`） | 调度线程无令牌，auth 的 getUserType/getAllPermission 必 500 | `FileAppServiceImpl.setModel` |
| task_info 缺 `user_id` 时回填并告警 | 解析服务校验 "传入knowledge_base_id时必须使用user_id"（422） | `FileAppServiceImpl.filesParse` |
| 纯文本类跳过 LibreOffice 转换 | 缺 writer，txt 无回落直接失败 | `PdfConvertorUtils.isNeedConvert` |
| Feign 空体/非 JSON 显式报错 | 原先把 500 空体伪装成 "Cannot parse null string" | `FeignErrorDecode`（上一轮） |

部署事实：`mvn -o -pl rag-index-service -am package -DskipTests -Dmaven.compiler.source=17 -Dmaven.compiler.target=17`
（只 `-pl` 构建会缺依赖，实测启动即 `NoClassDefFoundError: cn/hutool/core/date/DateUtil`；
用 reactor `-am` + 显式 source/target 才能得到可运行 jar），jar 起在 18082，原 r12 实例已停。

真实链路结果（file 999013 = `v2-sysctx-sample.txt`，kb_10）：

```
11:00:45  ERROR 用户不存在            <- 回填 userId=0，解析服务校验失败（诚实记录）
11:02:30  parse 服务收到 POST /parse  <- 按真实 UI 任务形态补 user_id=1 后
ES   kb_10 该文件 1 条，type=text，source=r12-rag/kb_10/v2-sysctx-sample.txt/V0/...
Milvus _kb_10 该文件 1 行
任务状态 4（SUCESS）/ 文件状态 3
```

即：**上传 → 调度 → 模型解析 → /parse → 切分 → ES+Milvus 写入**全链路通了（此前卡在模型解析，永不派发）。

遗留两条真实问题（不掩盖）：

1. `error_msg` 在成功路径未清空，会残留上一轮 recover 文本（状态 4=SUCESS 本身是对的，见 §10 更正）；
2. **user_id 必须来自 task_info**：缺失时回填 `create_by`（用户名）或 `0` 仍会 "用户不存在"。
   真实 UI 上传由 UserContext 写入 user_id 才有；纯 API/脚本入库的任务需要在入队时补数字 id，
   或由服务端按用户名反查 id —— 属待定契约，本轮未擅自改。
