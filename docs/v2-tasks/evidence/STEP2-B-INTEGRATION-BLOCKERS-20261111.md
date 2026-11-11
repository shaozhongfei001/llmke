# 接 Java 前的三处阻断（2026-11-11，只读核查）

按方案 A 完成 18097 回调服务与直连实测后，准备「填 `v2-ingest.url` → 打包重启 rag-index-service」。
本轮先做只读核查，发现三处会让产品链行为不正确的事实，因此**没有改配置、没有部署 jar、没有重启任何服务**。

## 1. 两条建图通道写的是不同图根，且规模差异巨大

| 通道 | 写入根 | 依据 | 是否影响 18094 查询 |
|---|---|---|---|
| 19531 `legacy_shim` → `/v2/graph/build` | `/home/szf/data/dev/llmke-runtime/app/platform/r12/data/graph-root` | 19531 进程 `LLMKE_V2_ROOT`；`legacy_shim.py:314` | 是，18094 health 的 snapshot 就在这个根下 |
| 18096/18097 → `/v2/graph/delta` | `/home/szf/data/dev/llmke-runtime/shadow/graph-root/<kb>` | 隔离库实测 422 响应里的 `root=`；18096 health `store_root=.../shadow/artifact-store` | **否**，影子通道 |

`graph_engine_adapter/api.py:564-571` 明确：delta 构建成功后，只有 `req.root` 等于 18094 进程 env root
时才重置该库查询槽；影子 root 不动槽（注释写明"否则生产的内存视图会被影子快照覆盖（缺陷 12）"）。
所以影子通道写入的内容**不会**被 18094 查询读到，这是设计使然，不是故障。

规模实测：

- 生产 `app/.../graph-root/kb_9/current.json`：`documents=46`，`per_file=11`；
- 影子 `shadow/graph-root/kb_9/current.json`：`documents=4`，`per_file=3`；
- 影子 artifact-store 的 kb manifest 只含少量演练产物。

**风险**：若此刻把 18096 的 `graph_root` 直接切到生产根，`consume_for_kb` 会按影子 manifest 的
"该库全部存活文档"重建图谱，把生产图削成 3~4 个文件。因此停用 19531 / 统一图根之前，
必须先做一次与生产语料对齐的全量基线摄取并原子切换，属于要求 5 的范畴。

另注：生产 `kb_9/current.json` 的 `dir` 仍指向已删除的旧软链路径
`/home/szf/data/dev/llmke-r12/platform/r12/data/graph-root/...`，该指针本身也需校正。

## 2. 普通上传仍是 12340 + doc2md 双解析

- `FileParseTaskAppServiceImpl.java:310-361`：12340 解析成功 → `doSuccess` → 写 `PARSE_SUCCESS` →
  `if (!isExtract) filesAppParse.v2Ingest(...)`；
- `RemoteV2IngestUtils.ingest` 在 `doc2mdDir=null` 时靠 `file_url`（MinIO 地址）发请求，
  18097 正好据此下载并跑 doc2md。

也就是说填 URL 后链路能通，但**同一文件会被 12340 与 doc2md 各解析一次**，不满足要求 2
「doc2md 作为唯一文档解析基础组件」。要去掉 12340，需要改 Java 让上传后跳过旧解析任务、
由 18097 的回调驱动状态回写，这是比"填配置"更大的改造。

补充：`generateGraph`（19531）只在 `isGraphParse=true` 时调用（`FileParseTaskAppServiceImpl:353-355`），
前端该开关默认 false，所以**普通上传本来就不走 19531**。停用 19531 主要影响"图谱解析"开关，
不是普通上传的阻断项；但它目前仍是生产图谱唯一的更新入口。

## 3. rag-index-service 存在双实例，现役用的是旧 jar

| 项 | 实测 |
|---|---|
| 端口 | `application-r12.yml:44` = `18082` |
| 现役进程 | pid `46793`（11-09 启动）占用 18082 |
| systemd unit | `r12-java@rag-index-service.service` 于 11-11 20:34 另起了 pid `3293253`，二者并存 |
| jar | 两者都指向 `llmke-runtime/app/.../rag-index-service-0.0.1-SNAPSHOT.jar`（md5 `6a3e80fc…`） |
| 本轮新打包 jar | 主仓 `llmke/services/.../target/...jar`（md5 `8225b095…`），`mvn package` rc=0 |

直接 kill/重启容易触发 unit 自动重启、端口抢占或两个实例同时写同一份状态，需要先理清实例归属。

## 本轮完成的准备（无生产副作用）

- 新 jar 打包成功：`mvn -o -q -pl rag-index-service -DskipTests package` → rc=0（依赖
  `rag-common` 已按上一轮口径先 `install`）。
- 确认 Java 传给 18097 的 `file_url` 形态与 18097 入参完全匹配（MinIO 完整 URL）。
- 服务端口全览正常：`12340 / 18096 / 18097 / 19531 / 18094 / 19995 / 18083 / 8088` 均 LISTEN。

## 建议的安全顺序（替代原先「先停 19531 再填 URL」）

1. **隔离验证图根统一**（零生产风险）：在独立 kb / 独立 root 上完整跑一次
   FULL 基线 → 后续 DELTA，证明 18096 写非影子 root 时不会削数据、查询槽正确重置。
2. **生产切换窗口**：把影子 manifest 与生产语料对齐 → 原子切换 18094 查询根 →
   校正 `kb_9/current.json` 的旧软链指针 → 再停用/合并 19531（Owner 已授权）。
3. **去掉 12340 双解析**：改 Java 上传回调，让 doc2md 成为唯一解析者并正确回写状态。
4. **清理双实例 + 部署新 jar + 填 `v2-ingest.url` + 重启 rag-index-service**。
5. 前端 rebuild dist → 四类格式真实上传实测 → ES/Milvus/18094 按 pk 对齐 → Owner 签收。

要求 3 / 4 / 5 均未动；本轮未产生任何生产写入。
