# T-A1 自证：D7 打开原文（global 分支补 file_id→convertedFilePath 反查）

- 任务：`docs/v2-tasks/TASKS.yaml` → `T-A1`（acceptance D7）
- 执行人：TL（tl-audit）
- 日期：2026-11-03
- 工作树：`/home/szf/data/dev/llmke-v2`，分支 `design/v2-input-engine-adoption-20261030-2101`

## 0. 状态摘要（先说清楚哪段验证了、哪段没有）

| 环节 | 状态 | 依据 |
|---|---|---|
| 真实上传文档（非 F001–F012/999010）取得 | **已取得** | 走产品网关 8088 真实上传 `coordination/samples/docx-plain.docx`，落库 `gienrag.knowledge_base_list` id=999017（数字 id、converted_file_path 有值） |
| Java 编译 | **通过** | `mvn -o -q -pl rag-qa-service compile` 无输出（成功） |
| 反查逻辑（file_id → convertedFilePath → 桶内对象键） | **已验证 4/4 PASS** | 对**已编译的真实类** `AiServiceImpl` 打私有方法 `enrichReferenceSources`，桩住 `KbClient`/`StorageProperties`，用真实上传文件的 id=999017 |
| global 分支接线（`question_re` 调用它） | **代码已改，未在运行实例上验证** | 需要重启运行中的 rag-qa-service（:18083）才生效 |
| 页面「点引用 → 抽屉 → 打开原文 → 高亮 locator」 | **UNVERIFIED** | 需同时满足 ①Java 新代码生效 ②global 快照含该真实文件。见 §5 |

## 1. 真实上传文档是怎么来的（不是演示语料）

样本：`/home/szf/data/dev/coordination/samples/docx-plain.docx`（36,716 字节，真实 docx，不属于 F001–F012/999010 演示语料）。

流程：`POST /auth/user/simpleLogin` → `POST /index/knowledgeBase/create` → `POST /index/knowledgeBase/file/uploadFileList`（`isParse=true, isExtract=true, isGraphParse=true`）。脚本 `/tmp/a1_upload.py`。

关键输出（原样）：

```
LOGIN 200 success= True
KB_CREATE 200 {'success': True, ..., 'data': {'id': '1002', 'kbName': 'T-A1-真实文档-145619', 'primitiveName': 'kb_1002', ...}}
KB_ID 1002
UPLOAD 200 elapsed 0.1
UPLOAD_BODY {'success': True, ..., 'data': [{'id': '999017', 'kbId': '1002', 'fileName': 'docx-plain.docx',
   'fileSize': 36716.0, 'filePath': 'http://127.0.0.1:19000/r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx',
   'convertedFilePath': None, 'status': 1, ...}]}
```

第一次上传失败并留证（不是"一次就过"）：`UPLOAD 500 {'errorMsg': "Required request parameter 'uploadFileParam' ... is not present"}` —— 根因是会话级 `Content-Type: application/json` 覆盖了 multipart 的 boundary。

落库事实（**注意：Java 写的是 `gienrag` 库，不是 ENV.md 里写的 `gienrag_v2_restore`**；后者 `knowledge_base_list` 为 0 行）：

```
$ MYSQL_PWD=… mysql -h127.0.0.1 -P13306 -uroot -e "SELECT id,kb_id,file_name,status,graph_parse_status,converted_file_path
    FROM gienrag.knowledge_base_list WHERE kb_id=1002\G"
*************************** 1. row ***************************
                id: 999017
             kb_id: 1002
         file_name: docx-plain.docx
            status: 3
graph_parse_status: 1
converted_file_path: http://127.0.0.1:19000/r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx
```

`SELECT 'v2_restore',COUNT(*) FROM gienrag_v2_restore.knowledge_base_list UNION ALL SELECT 'gienrag',COUNT(*) FROM gienrag.knowledge_base_list;`
→ `v2_restore 0` / `gienrag 540`。

## 2. 改了什么

`services/rag-java/rag-parent/rag-qa-service/src/main/java/com/gientech/ragqaservice/application/service/impl/AiServiceImpl.java`

1. **抽出** R13-GRAPH-11 反查为 `resolveSourceByFileId(JSONObject metadata)`（`AiServiceImpl.java:2680` 起）：
   依次尝试 `metadata.file_id` / `file_ids` → `kbClient.getByIds` → 取 `convertedFilePath`；命中时把规范化
   `file_id/title` 写回 metadata；解析不出返回空串（调用方继续走名字回落，绝不拼 `.../null`）。
2. **publicQuestion 原内联块改为调用该方法**（`:733-737`），消除"两处各写一份"。
3. **新增** `enrichReferenceSources(String reference)`（`:2712` 起）：对 documents_list 逐条
   `source 为空 → resolveSourceByFileId → toBucketKey`，解析不到的条目 **保留但 source 置空**（不删、不编造）。
4. **global 分支接线**（`:396-402`）：`reference = enrichReferenceSources(retrievedData.getDocumentString())`。
   改前是 `reference = retrievedData.getDocumentString()`，原样下发 —— 社区摘要只有 file_id，
   页面点引用打不开原文（这正是评审 D7 指出的缺陷）。

新增回归测试：`src/test/java/.../AiServiceReferenceResolveTest.java`（4 个用例）。

## 3. 编译与运行验证（真实类，非纸面）

```
$ cd /home/szf/data/dev/llmke-v2/services/rag-java/rag-parent && mvn -o -q -pl rag-qa-service compile -DskipTests
（无输出 = 成功）
```

离线仓库里 `maven-surefire-plugin` 默认 2.12.4 缺 `surefire-junit3`，`mvn test` 在本机跑不起来
（`1 required artifact is missing ... dummy:dummy:jar:1.0`），所以改用"直接对已编译类打私有方法"的等价验证
（`/tmp/t_a1_check/T.java`，用动态代理桩住 `KbClient`、Mockito 桩住 `StorageProperties`）：

```
$ javac -nowarn @/tmp/t_a1_check/args -d . T.java && java @/tmp/t_a1_check/rargs T
PASS ① source=桶内对象键
PASS ① title 回填
PASS ① file_id 归一
PASS ① 其它字段未被动
INFO  … T-A1 enrichReferenceSources: items=1 resolved=0 unresolved=1
PASS ② 非法 id → source 为空
WARN  … reference 不是 JSON 数组，原样返回: illegal input, offset 1, char {
PASS ③ 非数组原样返回
PASS ④ 空引用
ALL PASS (4/4)
```

输入用的是真实上传文件的 id，输出逐条：

| 断言 | 期望 | 实测 |
|---|---|---|
| ① global 引用（`metadata.file_id="999017"`，无 source） | `source = r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx` | PASS（由 `http://127.0.0.1:19000/...` 归一为桶内对象键，与前端 `/minio/${source}` 契约一致） |
| ① title / file_id 回填、`community` 字段不被破坏 | `docx-plain.docx` / `999017` / `c-3` | PASS |
| ② 非数字 file_id（`F003`） | 不抛异常、source 为空 | PASS（`resolved=0 unresolved=1`） |
| ③ 输入不是 JSON 数组 | 原样返回 | PASS |
| ④ 空引用 | 原样返回 | PASS |

## 4. 为什么必须归一成"桶内对象键"而不是绝对 URL

前端契约（R14-C-FIX-13 注释，`AiServiceImpl.java:2650` 附近）：前端是 `/minio/${source}`。
若下发绝对 URL，会变成 `/minio/http://host/...` → 点开必 404/403。
本次验证实测的旁证：

```
$ curl -s -o /dev/null -w "%{http_code}\n" -I http://127.0.0.1:19000/r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx
403                       # 直连对象存储，未签名 → 403（不能当前端链接）
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8088/minio/r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx
404                       # 网关 /minio/ 下该对象 404，说明这条链路的取原文还需确认（见 §5 第 2 条）
```

## 5. 未完成项（逐条给恢复条件，不补理由）

1. **Java 新代码未生效**：运行中的 rag-qa-service（`:18083`，pid 2363389）是旧代码。
   需要重启该服务。**未擅自重启**——它是 S3/页面链路在用的服务。
   恢复条件：取得"允许重启 18083"的授权（或由持有该服务的人重启）。
2. **原文对象取回未打通**：`converted_file_path` 是 MinIO 地址，直连 403、网关 `/minio/` 404。
   在页面点开原文前，需要先确认前端实际使用的取流地址（可能是签名 URL 或 `getFileStream` 接口）。
   这是"打开原文"的最后一段，未验证，不计入通过。
3. **global 快照里没有这份真实文件**：当前 19532→18094 的 global 读的社区报告基于 F001–F012。
   要让 global 引用指向 999017，需要把真实文件解析文本建进快照（本批次已在 18095 具备建图能力，
   但 18094 未重启、未换快照）。
4. **页面级实录（截图+抽屉）**：未做。前一次页面 E2E 的临时 nginx 容器已删除。

## 6. 一行结论

反查逻辑与 global 接线**已在代码层落地并经真实类运行验证（4/4 PASS）**，用的是走产品网关真实上传的
`docx-plain.docx`（id=999017，非演示语料）；但"点引用打开原文"的**端到端仍未打通**，
卡在两处可执行但需授权的动作：重启 `:18083` 让新代码生效、以及确认前端取原文的实际地址（实测 `/minio/` 404）。
