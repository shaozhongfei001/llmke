# T-A1 自证：D7 打开原文（global 分支补 file_id→convertedFilePath 反查）

- 任务：`docs/v2-tasks/TASKS.yaml` → `T-A1`（acceptance D7）
- 执行人：TL（tl-audit）
- 日期：2026-11-03（上传 15:02，验证 15:07）
- 工作树：`/home/szf/data/dev/llmke-v2`，分支 `design/v2-input-engine-adoption-20261030-2101`
- 数据库：**产品库 `gienrag`**（不是隔离库 `gienrag_v2_restore`；后者 `knowledge_base_list` 为空是正常的）

## 0. 状态摘要

| 环节 | 状态 | 依据 |
|---|---|---|
| 真实上传文档（非 F001–F012/999010） | **已取得** | 走产品网关 8088 上传 `coordination/samples/docx-image.docx` 到 **kb_9**，新 id=**999019**（§1） |
| 产品侧已解析的真实文档（用于取产品解析块） | **已取得** | kb_9 既有 `id=333 docx-table.docx`（status=3 已解析），通过产品接口取到 2 个块（§2） |
| Java 编译 | **通过** | `mvn -o -q -pl rag-qa-service compile` 无输出 |
| 反查逻辑（单元级，真实类） | **4/4 PASS** | §4 打私有方法 `enrichReferenceSources`，桩 KbClient/StorageProperties |
| **真实数据全链**（真实文档 → 真实 global → Java 实际输入 → 反查） | **6/6 PASS** | §5：source 变成真实文件的桶内对象键，locator/community 未被破坏 |
| global 分支接线（`question_re` 调它） | 代码已改，**运行实例未生效** | 需重启 `:18083`（未授权，见 §7） |
| 页面「点引用 → 抽屉 → 打开原文 → 高亮」 | **UNVERIFIED** | 需 Java 重启 + 取原文链路（§6 实测 403/404） |

## 1. 上传（按 team-lead 批准的四条边界执行）

用 team-lead 批准的方式：走产品网关 8088，只传 1 份 `coordination/samples` 的真实 docx 到 **kb_9**。

```
$ date '+%Y-%m-%dT%H:%M:%S%z'
2026-11-03T15:02:46+0800
$ python3 /tmp/a1_upload_kb9.py
LOGIN 200 success= True
UPLOAD 200 elapsed 0.2
UPLOAD_BODY {'success': True, ..., 'data': [{'id': '999019', 'kbId': '9', 'fileName': 'docx-image.docx',
  'fileSize': 50185.0, 'filePath': 'http://127.0.0.1:19000/r12-rag/kb_9/docx-image.docx/V0/docx-image.docx',
  'convertedFilePath': None, 'status': 1, 'parseType': 1, ...}]}
```

落库核对（**产品库 gienrag**）：

```
$ mysql -h127.0.0.1 -P13306 -uroot -e "SELECT id,kb_id,file_id,file_name,status,graph_parse_status,is_enable,converted_file_path,gmt_create FROM gienrag.knowledge_base_list WHERE id=999019\G"
                 id: 999019
              kb_id: 9
            file_id: NULL
          file_name: docx-image.docx
             status: 2
         parse_type: 1
 graph_parse_status: 1
          is_enable: 1
converted_file_path: http://127.0.0.1:19000/r12-rag/kb_9/docx-image.docx/V0/docx-image.docx
         gmt_create: 2026-11-03 15:02:47
```

**测试夹具留痕（不删除；删除端点仍 501）**

| 对象 | id | 说明 |
|---|---|---|
| kb_9 新上传文件 | `999019` | `docx-image.docx`，49.0 KB，`converted_file_path` 见上，创建 2026-11-03 15:02:47 |
| 解析任务 | `gienrag.file_parse_task.id=642` | status=2（未结束，`end_time=NULL`，`retry_times=0`），该样本是"图文"docx，解析一直未完成 |
| **误建的空知识库** | `gienrag.knowledge_base.id=1003`（`kb_1003`，名 `T-A1-真实文档-150246`） | 上传脚本沿用了"先建库"的模板，忘记删该步。**如实登记**，未删 |
| 批准前已上传（如实登记） | `999017`、`999018`（kb_1002）、`knowledge_base.id=1002`、`1001` | 批准前那次尝试（§ 历史），内容同一份 `docx-plain.docx`；未删 |

不动既有文件：上传前确认 kb_9 内 `docx-image.docx` 记录数为 **0**（`SELECT COUNT(*) … WHERE kb_id=9 AND file_name='docx-image.docx'` → 0），
`docx-table.docx` 已有 34 条（所以没有传它，避免覆盖既有版本）。

## 2. 用于全链验证的真实文档：kb_9 `id=333 docx-table.docx`

选它的理由（三条都是硬条件）：**产品侧真实上传**、**已解析完成**（`status=3`，所以产品接口能取到块）、
**数字 id**（Java `RetrieveMetaData.file_id` 是 Long，非数字 id 会被丢）。
`id=999010`（丙-额度分项.docx）按纪律排除。

取产品解析块（不是本地解析、不是自研抽取）：

```
$ GET http://127.0.0.1:8088/index/knowledgeBase/file/getFileChunks?kbId=9&docId=333&pageNo=1&pageSize=200
200 {'success': True, 'data': {'records': [
   {'id': '1029926531603392361', 'content': 'DOCX with table下表为多指标对账口径。', ...},
   {'id': ..., 'content': '|指标|数据源|口径|\n|日均存款|T-CORE-001|按业务日跨账户汇总/天数|\n|用电量|T-EXT-001|月度同比|', ...}],
   'total': 2, ...}}
```

## 3. 改了什么

`services/rag-java/rag-parent/rag-qa-service/.../application/service/impl/AiServiceImpl.java`

1. **抽出** R13-GRAPH-11 为 `resolveSourceByFileId(JSONObject metadata)`（`:2680` 起）：
   `metadata.file_id` / `file_ids` → `kbClient.getByIds` → `convertedFilePath`；命中回填规范化 `file_id/title`；
   解析不出返回空串（继续走名字回落，绝不拼 `.../null`）。非数字 file_id（如 `F003`）跳过而不抛错。
2. **publicQuestion 原内联块改为调用**（`:733-737`），消除两处各写一份。
3. **新增** `enrichReferenceSources(String reference)`（`:2712` 起）：逐条 `source 空 → 反查 → toBucketKey`；
   解析不到的条目**保留但 source 置空**（不删、不编造）；输入不是 JSON 数组时原样返回（不 500）。
4. **global 分支接线**（`:396-402`）：`reference = enrichReferenceSources(retrievedData.getDocumentString())`。
   改前是原样下发 documents_list —— 社区摘要只有 file_id，页面点引用打不开原文，这正是 D7 指出的缺陷。

新增回归测试 `AiServiceReferenceResolveTest`（4 用例，等价覆盖见 §4 说明）。

## 4. 单元级验证（对已编译的真实类打私有方法）

```
$ cd services/rag-java/rag-parent && mvn -o -q -pl rag-qa-service compile -DskipTests
（无输出 = 成功）
```

离线仓库 `maven-surefire-plugin` 默认 2.12.4 缺 `surefire-junit3`，`mvn test` 在本机跑不起来
（`1 required artifact is missing … dummy:dummy:jar:1.0`），所以用等价手段直接验方法体
（动态代理桩 `KbClient` + Mockito 桩 `StorageProperties`）：

```
$ java @/tmp/t_a1_check/rargs T      # /tmp/t_a1_check/T.java
PASS ① source=桶内对象键
PASS ① title 回填
PASS ① file_id 归一
PASS ① 其它字段未被动
PASS ② 非法 id → source 为空（resolved=0 unresolved=1）
PASS ③ 非数组原样返回
PASS ④ 空引用
ALL PASS (4/4)
```

## 5. 真实数据全链验证（本项最关键的一段）

链路：真实文档产品块 → 建图 → global 提问 → retrieval_shim 的 Java 实际输入 → `enrichReferenceSources`。

**(a) 用产品解析块建图**（file_id=333，locator 保留 `page=1;chunk=N`）：

```
$ POST http://127.0.0.1:18096/v2/graph/build   --data-binary @/tmp/a1-build.json
{"status":"BUILT","snapshot":"/tmp/tl-a1-root/snapshot-20261103150659-907924-g0",
 "documents":2,"chunks":2,"sources":2,"facts":6,"edges":23,
 "community":{"sha256":"e16b4672c62e79c6da60ace7f36d718a6b2ab9febb8c2b20222ac4b61e4e901e",
   "status":"READY","community_count":3,
   "citation_check":{"ok":true,"checked":6,"valid":["c-2:333:日均存款 口径 按业务日跨账户汇总/天数", …]}}}
```

**(b) global 提问（真实社区引用）**：

```
$ POST http://127.0.0.1:18096/v2/graph/global  {"query":"日均存款的口径是什么","max_communities":3}
status: READY
answer: - 日均存款 口径 按业务日跨账户汇总/天数（来源：333）
        - 日均存款 数据源 T-CORE-001（来源：333）
citations: [{"community":"c-2","text":"日均存款 口径 按业务日跨账户汇总/天数","sources":["333"]}, …]
source_meta: {"333": {"file_id":"333","locator":"page=1;chunk=0","title":"docx-table.docx"}}
```

**(c) 用 shim 的真实映射生成 Java 实际收到的 documents_list**：

```
$ python3（import retrieval_shim._global_documents / _to_document）
documents: 1
 community=c-2 file_id=333 source=None locator=page=1;chunk=0
 sources=[{"file_id": "333", "locator": "page=1;chunk=0", "title": "docx-table.docx"}]
```

`source=None` 就是缺陷本体：Java 收到的引用**没有任何可打开路径**。

**(d) 把这份真实 documents_list 喂给 Java 的 `enrichReferenceSources`**（KbClient 桩返回 MySQL 里
id=333 的真实 `converted_file_path`）：

```
$ java @/tmp/t_a1_check/rargs T2 333 docx-table.docx \
    "http://127.0.0.1:19000/r12-rag/kb_9/docx-table.docx/V0/docx-table.docx" \
    "r12-rag/kb_9/docx-table.docx/V0/docx-table.docx"
输入（Java 实际收到的 documents_list，前 260 字）：
  [{"page_content":"- 日均存款 数据源 T-CORE-001（来源：333）\n- 日均存款 口径 按业务日跨账户汇总/天数（来源：333）",
    "metadata":{"file_id":333,"source":null,"position":{"locator":"page=1;chunk=0", …
输出 metadata：
  source=r12-rag/kb_9/docx-table.docx/V0/docx-table.docx
  file_id=333 title=docx-table.docx locator=page=1;chunk=0 community=c-2
PASS 改前 source 为空（正是 D7 缺陷）
PASS 改后 source = 真实文件的桶内对象键
PASS file_id 仍是真实上传文件的 id
PASS title 回填为真实文件名
PASS locator 未被破坏（可高亮）
PASS community 未被破坏
ALL PASS (6/6)
```

即：**一条 real（kb_9 / id=333）文档的社区事实，经过修复后的 Java 反查，得到
`source=r12-rag/kb_9/docx-table.docx/V0/docx-table.docx` 且 `locator=page=1;chunk=0` 原样保留** ——
这就是"点引用能定位到原文位置"所需的两样东西。

## 6. 取原文链路实测（未打通，如实记录）

```
$ curl -I http://127.0.0.1:19000/r12-rag/kb_9/docx-table.docx/V0/docx-table.docx
403        # 直连对象存储未签名
$ curl -I http://127.0.0.1:8088/minio/r12-rag/kb_9/docx-table.docx/V0/docx-table.docx
404        # 网关 /minio/ 前缀下不存在该对象
```

另发现：Office 文档的预览通道在 Java 配置里是
`platform/r12/conf/rag-index-service/application-r12.yml:80 → url: http://127.0.0.1:18095/stream`，
而该端口在本次开工时**没有监听**（`ss -ltn` 当时只有 18094/19531/19532）——
即"Office 原文预览服务当时没起"。这是 D7 页面级的真实缺口，不是 Java 反查能补的。

（相关处置：本批次 A2 的临时实例曾占用 18095，已停止并释放，详见
`docs/v2-tasks/evidence/A2-pure-graph-route.md` §10。）

## 7. 未完成项与恢复条件

| 项 | 恢复条件 |
|---|---|
| Java 新代码在运行实例生效 | 重启 `rag-qa-service(:18083, pid 2363389)` —— **需 team-lead 授权**，本次未擅自重启 |
| 页面点引用 → 抽屉 → 原文打开 | 上面一项 + 取原文链路可用（§6：`/minio/` 404、预览服务 18095/stream 未运行） |
| 抽屉/截图实录 | 需前端起来（上次页面 E2E 的临时 nginx 容器已删除） |
| `999019`（docx-image.docx）的解析 | 解析任务 642 至今 status=2 未结束；该样本是图文 docx。不影响本项结论（全链用的是 id=333） |

## 8. 一行结论

反查逻辑已抽成唯一实现并接进 global 分支，**用 kb_9 真实上传、产品侧已解析的 id=333 文档跑通了
"真实文档 → 真实 global 社区事实 → Java 实际输入 → 反查 → source=真实桶内对象键 + locator 保留" 全链（6/6 PASS）**；
仍缺的只剩两件需外部动作的事：重启运行中的 `:18083`，以及打通取原文/预览通道（实测 `/minio/` 404、18095/stream 未运行）。

## 9. 补充（2026-11-03 15:20）：按 team-lead 放行的三步做实，端到端在 API 层跑通

### 9.1 重启 18083（先打包，只重启 qa-service）

运行中的 18083 原本跑的是 **r12 工作树的 jar**，新代码在 v2 —— 所以是"换 jar 部署"，不是原地重启：

| 项 | 值 |
|---|---|
| 重启前 pid | `2363389` |
| 重启前 jar | `/home/szf/data/dev/llmke-r12/.../rag-qa-service-0.0.1-SNAPSHOT.jar`，md5 `35e8b1200a98c11203adcee26cf7b7c3`（回滚基准） |
| 打包 | `mvn -o -q -pl rag-qa-service -DskipTests package` → v2 jar md5 `c441d760cf3bb4e074151d0ff9838fb3` |
| 重启后 pid | `2403983`，`Started RagQaServiceApplication in 7.983 seconds` |
| 启动参数 | 与原进程一致的 JVM 参数 + `--spring.profiles.active=r12 --spring.config.additional-location=file:/home/szf/data/dev/llmke-r12/platform/r12/conf/rag-qa-service/`，只把 `-jar` 换成 v2 的包 |
| 环境变量 | 从 `platform/r12/.env` 载入（首次未载入时启动失败过一次：`Could not resolve placeholder 'R12_REDIS_PASSWORD'`，如实记录） |
| 未动 | 8088 / 18094 / 19532 |

**curl ①（重启后服务可用性）**：`POST /qa/ai/question_re`，`X-UserID:5 / X-UserName:r13_reader`，globalMode=true

```
http=200
data:{"sessionId":"t-a1-restart-check","queryId":"q1",...,"reply":{"content":"- 集团客户授信方案 规定 集团客户统一授信额度为20亿元（来源：F012）",...
```

**curl ②（真实文件 global 提问）**：同端点，`X-UserID:1 / X-UserName:admin`

```
http=200
answer: - 客户 拥有 日均存款（来源：999017）
        - 日均存款 金额 2,983,333.33元（来源：999017）
reference[0].metadata.source = "r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx"     ← 修复后补出来
reference[0].metadata.file_id = 999017
reference[0].metadata.locator = "page=-;offset=[[0, 45]];chunk=0"                        ← locator 未丢
```

### 9.2 取原文：按 team-lead 给的两个真实入口实测

```
GET  /index/knowledgeBase/file/presign?key=r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx
  -> 200 {"success":true,"data":{"url":"http://127.0.0.1:19000/r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx?....X-Amz-Signature=..."}}
GET  <presigned url>
  -> 200 bytes=36716 ct=application/vnd.openxmlformats-officedocument.wordprocessingml.document
```

`36716` 与上传时的 `fileSize=36716.0` **逐字节相等** —— 拿到的就是那份真实上传文件，不是我拼的路径。

补充事实（与我上一版的错误尝试对照，team-lead 的判断正确）：

| 入口 | 实测 |
|---|---|
| `/proxy/index/knowledgeBase/file/presign` | **404**（网关没有 `/proxy` 前缀映射） |
| `/index/knowledgeBase/file/presign` | **200**，签发成功（对象级授权 + `statObject` 存在性检查） |
| `/index/knowledgeBase/file/previewStream` | **500 `源文件转换格式失败`（6001）** —— 因为 Office→PDF 预览服务 `18095/stream` 当时没起（§6） |
| 直连 `19000` / 网关 `/minio/` | 403 / 404（都不对，已作废） |

### 9.3 建进 global 快照 → 引用→原文闭环

按放行要求用 **19531**、`space_name=kb_1002`、`col_values=["docx-plain.docx"]`（ES 取块，file_id 来自 legacy 元数据）：

```
$ curl -X POST http://127.0.0.1:19531/generate_triple_data \
   -d '{"space_name":"kb_1002","col_name":"title","col_values":["docx-plain.docx"],...}'
http=200 {"code":200,"msg":"V2 建图完成 docs=1 chunks=1 facts=3 edges=4",
 "data":{"snapshot":"/tmp/v2-shim-root/snapshot-20261103151221-873115-g0",
         "es":{"es_docs_used":1,"locator_degraded":0}, ...}}
```

新快照 `sources.json` 确认绑定到真实上传文件：

```json
{"chunk-d452c50cbac0c9ebc94f52e1c9351cd6":[{"file_id":"999017",
  "locator":"page=-;offset=[[0, 45]];chunk=0","title":"docx-plain.docx"}]}
```

该快照 `community.json`：1 社区 / 3 事实 / `citation_check.ok=true`、`invalid=[]`。

chain 闭环（同一份 source 串原样喂 presign）：

```
Java 下发的 source = 'r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx'
presign -> 200
presigned GET -> 200 bytes= 36716 ct= application/vnd.openxmlformats-officedocument.wordprocessingml.document
locator = page=-;offset=[[0, 45]];chunk=0
```

**两个快照路径（按要求记录）**

| 用途 | 路径 |
|---|---|
| 临时（含真实文件 999017） | `/tmp/v2-shim-root/snapshot-20261103151221-873115-g0` |
| 已还原（原基线） | `/tmp/s4-root-c/snapshot-20261103000343-927116-g0` |

18094 还原后实测：`{"status":"ok","snapshot":"/tmp/s4-root-c/snapshot-20261103000343-927116-g0","nodes":26,"edges":49,"facts":69,"community":{"communities":33,"citation_check_ok":true,"status":"READY"}}`，
与 CHECKPOINT 记录的基线一致；19532 检索链路复测 `POST /retrieval_documents` → `code=200 查询成功 docs=3`，未受影响。
（一次还原失败留证：漏了 `PYTHONPATH` 导致 `ModuleNotFoundError: No module named 'graph_engine_adapter'`，补上后起来。）

### 9.4 Java 改动行号（评审逐行核对用）

| 位置 | 内容 |
|---|---|
| `AiServiceImpl.java:2669` | `private String resolveSourceByFileId(JSONObject metadata)`（R13-GRAPH-11 唯一实现） |
| `AiServiceImpl.java:2719` | `private String enrichReferenceSources(String reference)` |
| `AiServiceImpl.java:2747` | 内部逐条调用 `resolveSourceByFileId` |
| `AiServiceImpl.java:736` | publicQuestion 内联块改为调用（原 26 行内联被替换） |
| `AiServiceImpl.java:400` | global 分支接线 `reference = enrichReferenceSources(...)` |

### 9.5 权限边界是有效的（不是缺陷）

同一问题用 `X-UserName:r13_reader` 提问时，日志给出：

```
WARN … resolve source by file_id 999017 failed: 没有足够权限
INFO … T-A1 enrichReferenceSources: items=1 resolved=0 unresolved=1
```

即：**看不到这个知识库的用户，不会因为反查而拿到原文路径**。此时 `metadata.source` 被置空（前端显示不可点），
而不是给出一个越权可下载的链接。这条与 D8 的可见性要求方向一致。

### 9.6 剩下的唯一断点

**页面级（浏览器）「点引用 → 抽屉 → 原文 → 高亮」未做**，原因是前端没在跑：
`http://127.0.0.1/`（80）返回的是另一个产品（`<title>WeKnora</title>`）；LLMKE 前端此前用临时 nginx 提供，
容器已删除，Vite dev 受 inotify ENOSPC 限制起不来（CHECKPOINT 已记，非代码问题）。

复现条件：把 LLMKE 前端起来（nginx 指向 dist 或解决 inotify），用 admin 登录、对 kb_1002 提问
"日均存款是多少"、点引用；预期请求 `GET /index/knowledgeBase/file/presign?key=<source>` 返回 200。
在此之前 T-A1 保持 BLOCKED（断点=前端未运行），其余链路（上传→图→global→反查→presign→取回字节→locator）已全部实测通过。

## 10. 页面 E2E 实测（2026-11-03 15:22–15:29）：**断点在前端"知识溯源"抽屉**

### 10.1 环境（三个都被授权，全部留痕）

| 组件 | 处置 | 实测 |
|---|---|---|
| `rag-qa-service :18083` | 按批准重启，共 4 次（每次先 `mvn -o -q -pl rag-qa-service -DskipTests package`） | pid 链：`2363389`(旧, r12 jar `35e8b120…`) → `2403983` → `2461741` → `2478756` → **`2492411`**（现役）；每版 jar md5：`c441d760…` → `4d16f96a…` → 当前包 |
| 预览服务 `r12-preview` | `platform/r12/preview/run.sh up`（镜像 `r12/preview-office:r13` 已存在，**未 build**） | `[ok] r12-preview up on 18095`；healthz `{"ok":true,"soffice":"LibreOffice 25.2.3.2",...}` |
| 前端 `r12-fe` | `docker start r12-fe`（原 `Exited (0) 19 hours ago`） | `http://127.0.0.1:18088/` 200，页面标题 `智能对话` |

登录方式说明：页面有**图形验证码**，无法自动填写。改用"API 取 token + 注入 localStorage"（两个键都要：
`saic_store` 与 `gitech_ril:rag_ai`，形状 `{userInfo:{token}}`），实测两键 token 长度均为 237，页面因此正常进入并成功发问。

### 10.2 走到哪一步

1. 选 `qa_cfg_kb9` 配置 + 开 `全局(GraphRAG)` + 提问"日均存款的口径是什么" → 页面渲染出
   `日均存款 口径 按业务日跨账户汇总/天数（来源：333）`，并出现 **`知识溯源 1`** 按钮。截图：
   `/home/szf/data/dev/llmke-v2/docs/v2-tasks/evidence/screens/A1/01-answer.png`
2. 点 `知识溯源 1` → 抽屉打开，列出 `知识库文档 / docx-table.docx`（真名，不是 file_id）。截图：
   `…/screens/A1/02-drawer.png`
3. 点该条目 → **失败**：`加载失败：缺少原文地址或登录态，无法打开原文` + `重 试`。截图：
   `…/screens/A1/03-after-click-item.png`、`…/05-preview.png`、`…/07-preview3.png`、`…/08-preview4.png`

### 10.3 定位（三层都试过，逐条给证据）

前端报错只有两个触发条件（`components/KnowledgeBaseZh/components/FileViewCom.tsx:61`、
`AIChat/components/DrawerPreview.tsx:70`）：`!meta.source || !meta.token`。

| 假设 | 验证 | 结论 |
|---|---|---|
| token 缺失 | 浏览器内读出两键 token 长度均为 237（`CHK2 passTokLen=237 saicTokLen=237`）；同一页面的 axios 请求全部带 Authorization 并通过 | **否认** |
| Java 没下发路径 | 直接打 `question_re` 看响应：`doc.filePath`、`metadata.source`、`metadata.filePath`、`sources[0].source`、`sources[0].filePath` **五个字段全部有值** = `r12-rag/kb_9/docx-table.docx/V0/docx-table.docx` | **否认** |
| 抽屉条目没带路径 | 连点三次（分别只补 `metadata.source`、再补 `metadata.filePath`+`sources[].source`、再补顶层 `doc.filePath`），**三次都报同一句**；`SdqaDrawer/index.tsx:502` 是 `if (!curData.filePath) return <></>` —— 说明抽屉对 `filePath` 是硬契约，而 `知识溯源` 列表项由 `@gientech/modual` 组件内部构造，不吃平台 `reference` 里新增的字段 | **成立** |

即：**Java 反查这一段已经做到位（五个字段齐全、presign 200、原文 36716 字节可取），断点在"知识溯源抽屉条目 → 预览组件"的字段映射**，
该映射在 `frontend/plateform`（llmke-r12 树）与 `@gientech/modual` 里，**不在本批次写域**。

### 10.4 结论：T-A1 保持 BLOCKED，断点=前端抽屉字段映射

- 已验证（可复跑）：上传 → 建图（file_id 333）→ Java global 引用带 `source`/`filePath`/`locator` →
  `presign` 200 → 预签名 GET **200 / 36716 字节**（与上传大小相等）→ locator `page=-;offset=[[0,0]…[2,2]];chunk=1` 未丢。
- 未通过（页面）：`知识溯源 → 条目 → 预览/高亮`，因抽屉条目缺 `filePath`（组件硬契约），报
  "缺少原文地址或登录态"。
- 恢复条件（二选一，都需要前端/前端 vendor 改，属另一写域）：
  ① `知识溯源` 列表项透传 `filePath`（= 桶内对象键）；
  ② `FileViewCom`/`DrawerPreview` 在 `filePath` 为空时回落到 `metadata.filePath || metadata.source`。
  任一落地后，本证据 §10.2 的三步即可复跑通过，无需再改 Java。

### 10.5 环境终态

- `18094` 已还原：`/tmp/s4-root-c/snapshot-20261103000343-927116-g0`（health 实测 26 节点/49 边/69 事实/33 社区）。
  临时快照（含 333）：`/tmp/v2-shim-root/snapshot-20261103151652-781141-g0`。
- `19532` 未动；`r12-preview` 与 `r12-fe` 现为**运行中**（此前分别是 Exited/未起），如需回收可
  `docker stop r12-fe` + `preview/run.sh down`。
