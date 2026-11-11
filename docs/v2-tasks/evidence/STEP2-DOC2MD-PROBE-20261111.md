# 要求 2 开工首轮：实测、改动与发现的阻塞（2026-11-11）

Owner 已批准按 `2 → 5 → 3 → 4` 顺序实施，并同意 G-4 由 Owner 签收（如实标注非独立 QA）、
G-1 暂留 `database_desc` 只读子集。本轮只做第一步，做完实测即停，不进入要求 5。

## 1. 改动前服务基线

`12340 / 18096 / 19531 / 18094 / 19532 / 19995 / 18083 / 8088 / 19526 / 19527` 全部 LISTEN。

**更正过时注释**：`platform/r12/conf/rag-index-service/application-r12.yml:104-106` 称
「18096 无启动定义 / 不写 ES/Milvus」，实测不成立：

- 18096 是 `uvicorn kb_ingest_service:app --port 18096`（pid 46796），`/health` = `status: ok`，
  `write_targets.es=true / milvus=true / configured=true`，`graph_api=http://127.0.0.1:18094`；
- 启动定义在 `platform/r12/bin/r12-kb-ingest-start.sh` 与
  `platform/r12/systemd/r12-kb-ingest.service`（unit 当前 inactive，进程为裸进程）。

## 2. 真实演练：doc2md 解析链（隔离，不碰 kb_9）

```
PYTHONPATH=services/rag-alg/index_data_service \
LLMKE_DOC2MD_LOCK=/home/szf/data/dev/coordination/doc2md.lock \
python scripts/v2_ingest_doc2md.py \
  --file docs/v2-tasks/evidence/artifacts-20261111/docx-table.original.docx \
  --kb kb_e2e_20261111 --file-id 990001 \
  --config /home/szf/data/dev/doc2md/config/app.yaml \
  --store-root /tmp/v2-e2e-store-20261111 --no-graph
```

真实输出要点：

```
status=OK  artifact_quality=COMPLETE
projection.status=READY  chunks=3  channels={text:2, table:1}
artifact_id=bad52b5ee484bf1c8c7e655f2c7f68f52ca111886f36799b8d465fd52023a388
doc2md_dir=/home/szf/data/dev/doc2md/parsed/by_hash/a8/46/a846ab142d8d24afe3f552f95888c4b261dd7c8908921a16a2932c4a7838fa1d
```

结论：**doc2md CLI 可用、四件套完整、搜索路投影成功**，并且产出了 18096 所需的 `doc2md_dir`。
首次演练因漏设 `LLMKE_DOC2MD_LOCK` 被 fail-closed 闸门拒绝，补齐后通过；闸门未绕过。

## 3. 真实实测：18096 消费四件套

`POST http://127.0.0.1:18096/kb/ingest`（`operation=UPSERT`，大写枚举；`build_graph=false`，隔离 kb）

```
code=207  msg=搜索路完成、图谱路失败（PARTIAL）
search.status=READY  chunks=3
diff.reason=FILE_SET_CHANGED  added=[990001]
graph.error=GRAPH_BUILD_HTTP_422: /v2/graph/delta → freshness.stale=true, reason=NO_POINTER
```

`NO_POINTER` 是**预期的 fail-closed 行为**：隔离库没有基线指针，delta 拒绝并要求先 FULL 建基线，
不静默降级全量。这对要求 5（增量）是有用证据，不是故障。

## 4. 本轮已落地改动（源码层，均未重启生效）

| 文件 | 改动 | 验证 |
|---|---|---|
| `frontend/plateform/src/components/KnowledgeBaseZh/components/UploadBox.tsx` | 删除「文档解析」手动 Switch 与 `isParse` state / reset 调用；上传参数改为 `isParse=true`（后端兜底仍在 Java） | `esbuild ... --outfile=/dev/null` rc=0 |
| `.../KnowledgeBaseListAppServiceImpl.java` | `fileParseAndExtract` 中，普通 FILE_LIST 上传在 `isExtract=false` 时无条件 `isParse=true`；FAQ 抽取组合语义不动 | `mvn -o -q -pl rag-index-service -DskipTests compile` rc=0 |
| `platform/r12/bin/r12-kb-ingest-start.sh` | `V2_SVC_DIR` 由已不存在的 `llmke-v2/...` 改为 `llmke/...`，避免 18096 重启失败 | 路径实测存在 |

备份：`/tmp/v2-step1-backup-20261111/`（6 个文件原样）。

## 5. 构建口径修正（既有问题，非本轮引入）

- 单独 `mvn -pl rag-index-service compile` 报 `FileParseTaskInfo.getDoc2mdDir()` 找不到：
  源码 `rag-common/.../FileParseTaskInfo.java:169` 有 `private String doc2mdDir;`，
  但 `~/.m2` 里是旧 `rag-common` jar。
- 用 `-am` 连带编译会撞 `gien-starter-easyexcel` 的
  `-source 8 中不支持 instanceof 中的模式匹配`（既有源码级别问题）。
- 正确顺序（实测均 rc=0）：
  `mvn -o -q -pl rag-common -DskipTests install` →
  `mvn -o -q -pl rag-index-service -DskipTests compile`。
  本轮已执行前者，会更新本地 `~/.m2` 的 rag-common 构件。

## 6. 本轮**没有**做的事，以及原因

**没有改生产配置、没有重启任何服务、没有停用 19531。** 原因是实测发现一个会导致回归的硬约束：

- `kb_ingest_service.py` 的 `IngestRequest._check_operation()` 强制
  `UPSERT 必须带 doc2md_dir（解析只发生在 doc2md 一次）`；`file_url` 仅作元数据，
  **不得触发第二次解析**。
- Java `FileAppServiceImpl.java:629` 从 `FileParseTaskInfo.getDoc2mdDir()` 取值；
  当前 12340 解析链不产出该值，故为 null。
- 因此仅把 `remote.v2-ingest.url` 填上，会让 18096 对每次上传返回 422，
  Java 如实回写失败状态，把原本「解析成功」的文件标成失败——这是回归，不能先做。

## 7. 下一步（要求 2 的剩余接线，待开工）

1. **定接线方式**（需一次架构选择）：
   - A 把 `scripts/v2_ingest_doc2md.py` 服务化为上传回调入口，产出 `doc2md_dir` 后交 18096；
   - B 把 12340 改造成 doc2md 包装器并回填 `doc2mdDir`（与 T-D2MD-16 退役方向冲突）；
   - C 给 18096 新增「文件 URL → 首次解析」端点（需改契约 §1.1 关于 `file_url` 的措辞）。
2. 填 `remote.v2-ingest.url: http://127.0.0.1:18096/kb/ingest`，打包并重启 rag-index-service。
3. 前端 `npm run build` 重建 dist，浏览器实测「零人工点击」上传。
4. 在 18096 链路跑通后停用 / 合并 19531（已授权），避免中间出现「完全不能建图」窗口；
   两条通道不得并发写同一份 18094 快照。
5. 四类格式（docx / pdf / 图片 / 表格）真实上传 → `file_parse_task` 自动完成 →
   ES / Milvus / 18094 按 pk 对齐，贴日志与截图。
6. 验收通过后由 Owner 签收，证据中如实标注「非独立 QA」；G-1 保持 `database_desc` 只读子集，
   12340 退役另立条目。
