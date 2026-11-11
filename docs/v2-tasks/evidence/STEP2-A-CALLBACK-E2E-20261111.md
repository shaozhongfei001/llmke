# 方案 A 落地与直连实测（2026-11-11）

Owner 批准「按 A 开工」：把 doc2md 编排服务化成上传回调入口，产出 `doc2md_dir` 后交 18096。
本轮完成实现与直连实测，**未改生产配置、未重启任何既有服务、未停用 19531**。

## 1. 核准的契约事实

| 事实 | 依据 |
|---|---|
| Java `RemoteV2IngestUtils.ingest` 直接 POST `remote.v2-ingest.url`（完整 URL），请求体为 `kb / file_id / doc2md_dir / file_url / file_name / file_path / file_size` | `RemoteV2IngestUtils.java:101-124` |
| `file_url` = `kbFile.getFilePath()`，实测是完整 MinIO URL：`http://127.0.0.1:19000/r12-rag/kb_9/.../V0/...` | `FileAppServiceImpl.java:649-655`；DB `gienrag.knowledge_base_list` 抽样 |
| 19000 是 `r12-minio` 容器，直连 GET 返回 403；网关 presign 需 token（不带 token 401） | `docker ps` / curl 实测 |
| 18096 `/kb/ingest` 的 `IngestRequest._check_operation()` 强制 UPSERT 必带 `doc2md_dir`，`file_url` 只作元数据 | `kb_ingest_service.py:176-186` |
| 正在跑的 18096 进程 `PWD=/home/szf/data/dev/llmke-runtime/app/services/rag-alg/index_data_service`、`PYTHONPATH=.`，用的是 runtime/app 副本而非主仓 | `/proc/46796/environ` |
| `hipporag-toolenv` 有 `boto3 + requests`；MinIO 凭据在 `r12-minio` 容器环境变量 `MINIO_ROOT_USER/PASSWORD` | 实测 |

因此选择**独立新服务**（不动线上 18096 进程、不改契约），端口 18097。

## 2. 实现

| 文件 | 改动 |
|---|---|
| `scripts/v2_ingest_doc2md.py` | `ingest_file()` 新增 `consume: bool = True` 参数；`consume=False` 时在四件套校验后直接返回 `{status: PARSED_ONLY, doc2md_dir, content_uid, file_name, file_size}`，不写 ES/Milvus/图、不要求冻结锁。**默认 True 保持原脚本行为** |
| `services/rag-alg/index_data_service/kb_parse_service.py`（新增） | `POST /kb/parse-and-ingest`：解析 MinIO URL → boto3 下载原件 → 只跑 doc2md 解析 → POST 18096 `/kb/ingest`（`operation=UPSERT` + `doc2md_dir`）→ 原样透传上游 `code/msg/data`；失败返回结构化 502，不假成功。`GET /health` 暴露依赖状态 |
| `platform/r12/bin/r12-kb-parse-start.sh`（新增） | 自检（模块/解释器/doc2md 配置/18096/18094/MinIO 凭据）+ 幂等启动 + `/health` 确认；凭据只从运行中的容器取，不写进仓库、不回显 |

契约边界：`/kb/ingest` 的 `file_url` 语义不变；新端点的 `file_url` 是「待**首次**解析的原件地址」，不是二次解析。

## 3. 真实实测

### 3.1 原件下载
boto3 + 容器凭据 → `r12-rag/kb_9/e2e-v2-ingest.docx/V0/e2e-v2-ingest.docx`：
`downloaded_bytes=36716`，`content_type=application/vnd.openxmlformats-officedocument.wordprocessingml.document`。

### 3.2 回归（原脚本行为不变）
`py_compile` 通过；重跑上一轮同一条演练命令：
`status=OK, projection.chunks=3, graph.requested=false` —— 与改动前一致。

### 3.3 服务自检与启动
`r12-kb-parse-start.sh --check` → 6 项 `[ok]`、`rc=0`；用脚本重启后 `/health`：
`status=ok, credentials_present=true, ingest_url=http://127.0.0.1:18096/kb/ingest`。

### 3.4 端到端直连（隔离库 `kb_e2e_a_20261111`）
```
POST http://127.0.0.1:18097/kb/parse-and-ingest
{kb, file_id:990002, file_url:<真实 MinIO 原件>, file_name, file_size:36716, build_graph:false}
```
真实响应（18096 原样透传）：

```
schema=llmke.kb-ingest.result/1  code=207  msg=搜索路完成、图谱路失败（PARTIAL）
status=PARTIAL  kb=kb_e2e_a_20261111
diff.reason=FILE_SET_CHANGED  added=[990002]
artifact.artifact_id=b958704bf47d3f53c9495d9223d9b79579ff134eab9ac91d738a47663e3ce851
artifact.content_uid=f4982001defc71791fa7b5af39db08cb953df151d458da2799aca4abb824b3fc
search.status=READY  chunks=3
graph.error=GRAPH_BUILD_HTTP_422 ... freshness.stale=true, reason=NO_POINTER
```

`content_uid` 与上一轮演练的 `a846ab14...` 不同，证明**确实下载了这份新原件并真实跑了 doc2md**，不是复用缓存。
`NO_POINTER` 是隔离库无基线的 fail-closed（不静默降级全量），与上一轮一致；生产库 kb_9 已有基线，不会触发。

## 4. 接线前必须知道的 Java 行为

`RemoteV2IngestUtils.classify()`：HTTP 2xx + `code=200` → `OK`；`code=207` → `RETRY`；
4xx → `PARSE_FAIL`。`FileAppServiceImpl` 对 `RETRY` 会 `updateStatusByIds(..., RETRY)`，
对 `PARSE_FAIL` 写 `PARSE_FAIL`，`OK` 不改状态。

所以产品链若出现 PARTIAL（例如新库第一次上传、或图路失败），文件会进入 `RETRY` 而不是成功。
**这要求 18096 的图路在产品链上能正常 delta，而 19531 仍在以全量 build 写同一份 18094 快照**——
两条通道并发会互相覆盖，故接 Java 之前必须先按 Owner 授权停用/合并 19531。

## 5. 本轮未做（下一步）

1. 按授权停用/合并 19531 全量建图通道，确保 18096 delta 是唯一图写入口（避免并发覆盖）。
2. 填 `remote.v2-ingest.url: http://127.0.0.1:18097/kb/parse-and-ingest`，
   打包并重启 rag-index-service（构建顺序：先 `mvn -o -pl rag-common -DskipTests install`，
   再 `mvn -o -pl rag-index-service -DskipTests package`）。
3. 前端 `npm run build` 重建 dist，浏览器实测「零人工点击」上传。
4. 四类格式（docx / pdf / 图片 / 表格）真实上传 → `file_parse_task` 自动完成 →
   ES / Milvus / 18094 按 pk 对齐，贴日志与截图。
5. 验收通过后 Owner 签收，证据如实标注「非独立 QA」；G-1 保持 `database_desc` 只读子集。

服务 18097 当前在线（由 `r12-kb-parse-start.sh` 启动，日志 `platform/r12/logs/kb-parse-service.log`），
供下一步接 Java 使用。演练产生的 `platform/r12/data/` 临时 kb 状态已清理。
