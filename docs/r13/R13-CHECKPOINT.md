# R13 执行检查点（截至 2026-10-25 14:10 UTC+8）

> 用途：上下文压缩/会话中断后按此继续，不要重新从规划开始。

## 1. 已交付并验证

| 项 | 证据 |
|---|---|
| 对象级授权（知识库/文件/原文流/问答） | `platform/r12/qa/evidence/SEC-20261025T044319Z` **10/10 PASS** |
| 无授权提问返回 403·30016 | 同上 SEC-4 |
| 撤权立即失效 | 同上 SEC-9 |
| MinIO 匿名 GetObject 已撤销 | 直连 19000 与 `/minio` 均 403 |
| 口令 BCrypt + 历史 MD5 透明升级 | `admin $2a$10$`，新账号 `$2b$` |
| 服务间身份传递（Feign 带 X-UserID/X-UserName）+ 授权 fail-closed | 代码 `FeignCustomConfig` / `KbAuthzService` |
| 启动即崩根因修复 | `InitInterface` 自调用失败不再杀进程 |
| systemd 托管 | `r12-models` / `r12-alg` / `r12-docparse` / `r12-java@<svc>` 全 active |

## 2. 本轮新增修复

- **R13-FIX-CFG-01**：`alg_doc_config_py.es_config.port` 由 `19200`（ES 本体）改为 `19527`（ES 代理）。
  原值导致 `POST /search_by_custom_param` 被 ES 以 405 拒绝，多版本预检失败。
- **systemd EnvironmentFile 格式**：`run/doc-parse.env` 带 `export` 前缀，systemd 不识别 → 服务连不上 Nacos。
  已生成 `platform/r12/systemd/doc-parse.env`（无 export）。
- **僵死任务恢复脚本**：`platform/r12/bin/recover-stuck-tasks.sh`（清理 status=5 占槽、status=99 复位）。

## 2.5 图谱链路进展（2026-10-25 15:55）

已完成：
- Nebula 3.8 三件套可用：固定 IP(172.28.0.2/3/4) + `ADD HOSTS 172.28.0.3:9779` → storage ONLINE；
  原 hostname 注册会被 metad 判 `Machine not existed`（这是三天套"Up 但无 space"的真因）。
- 空间与 schema：`rag_graph` 与 `g_rag_graph`（Java 端点强制 `g_` 前缀），TAG `entity`、
  EDGE `relationship`/`relationship_similar`，全字段 (200) 索引，写读探针 OK。
- `rag-graph-service`（18084）可读真实图：cypherSearch 返回顶点，instances 返回 {3000:{nodeCount:2,edgeCount:1}}。
- `index_graph_service`（19529）启动并完成真实抽取：`{"code":200,"msg":"添加成功，新增和更新3条图数据,新增6条实体"}`，
  数据落 `g_kb_9`，实体如 T-CORE-001/单证、日均存款、用电量。
- `query_graph_data` 打通 NER→实体链接→子图→PPR→原文回填，返回带 source/file_id/pk 的真实块。
- 修复：GRAPH-01（requests_llm 改 OpenAI 协议）、GRAPH-02（Nebula 口令误写 user）、
  GRAPH-03（绕开 nebula3 `dict_for_vis()` KeyError）。
- `r12-graphsvc.service` + `r12-java@rag-graph-service` 已由 systemd 托管。

未完成（下一步）：
- ~~**Java 侧图解析入口未接通**~~ → **已接通（2026-10-25 16:45）**：`POST /index/knowledgeBase/file/graphParse`
  用 `knowledge_base_id` + `file_ids` 触发，`graphParseStatus` 由 1→2→**3(成功)**，Nebula `g_kb_9` 累计 15 实体 / 8 关系。
  修复链：GRAPH-04（file_ids 未被消费→文件列表为空）、GRAPH-05（缺 knowledge_base_name 导致 doc-parse 422）、
  GRAPH-06（只抽到实体无三元组时被误判失败）。
- 历史记录（修复前）：**Java 侧图解析入口未接通**：`POST /index/knowledgeBase/file/graphParse` 用 snake_case
  `knowledge_base_id` + `file_ids` 调用返回 200，但 `file_parse_task` 不产生任务、`graphParseStatus` 恒为 1。
  注意 `FilesParseReq` 用 `@JsonProperty("knowledge_base_id"/"file_ids"/"chunk_size")`，camelCase 会被忽略（曾误判为"知识库不存在"）。
  下一步在 `KnowledgeBaseListAppServiceImpl.graphParse:2352-2406` 断点跟踪 `getFilePathByFolder` 是否把 fileIds 映射进 `files`。
- **多文件抽取已跑通（2026-10-25 17:20）**：docx-plain / product-loan / credit-ledger(xlsx) 三份真实业务文档
  经产品入口 `graphParse` 抽取成功，Nebula `g_kb_9` 累计 **64 实体 / 80 关系**。
  修掉两处真实缺陷：GRAPH-07（ES refresh 延迟导致"未查询到相关文本"→ 有限重试）、
  GRAPH-08（Java 用 convertedFilePath 的 `xxx.xlsx.md` 去匹配 ES `metadata.title` 的 `xxx.xlsx`，必然匹配不到 → 改用原始文件名）。
  ~~仍待解决：抽出的实体含 2000/3000/0/正常/下表/天数/table 等噪声~~ → **已处理（2026-10-25 17:55）**：
  新增 `graph_types.py`（类型体系 v1 + 实体过滤 + canonical 归一），落库前统一收敛；
  存量迁移脚本 `platform/r12/graph/migrate_normalize.py` 清洗 g_kb_9：
  **67 → 49 实体、56 边**，删除 14 个噪声节点（纯数字/结构词/文档标题）、合并 4 组长短名
  （华东→华东精密制造有限公司、江南→江南装备科技有限公司、海川→海川电子材料股份有限公司）、
  类型重判 31 个节点。当前类型分布：单证2/客户4/指标5/机构4/条款3/金额2/业务动作2/期限5/产品3/日期4/评级3/unclassified12。
  仍缺：担保方式类（设备抵押/应收账款质押）、编号（PRD-…）尚无类型；合并审计与回滚、类型版本迁移未做。
- 图检索尚未并入 `/qa/ai/question` 主链与引用结构。
- GraphRAG 本体（社区检测/分级摘要/摘要索引/global map-reduce）未开始。
- 类型体系及版本、canonical 归一、合并审计与回滚、三元组重指向未实现。

## 3. 已解除的阻塞（2026-10-25 15:06 复验 31/31 PASS）

**根因：任务队列被"已删除文件的历史任务"永久占位（R13-FIX-QUEUE-01）**

`FileParseTaskMapper.getTaskList` 原 SQL 只按 `status in (1,3) and retry_limit > retry_times order by id asc`
取任务，**不判断文件是否已删除**。历次验收结束会删除文件，但对应任务仍停在 1/3，
于是每次调度都优先取到最老的、指向已删文件的任务 → 解析必然失败 → 永久占用并发槽（`kb.file-parse.task-nums=5`），
新上传文件永远排不上队，表现为"文件恒为 99、`/parse` 从不被调用"。

修复：SQL 增加 `and file_id in (select id from knowledge_base_list where status <> 0)`。
清理存量：`update file_parse_task set status=-1 where status in (1,3) and file_id in (select id from knowledge_base_list where status=0)`。

同时新增 **R13-FIX-API-02**：`KB_NOT_EXISTS_ERROR` / `KB_FILE_NOT_EXISTS_ERROR` 由 500 改为 **404**；
验收断言由"success=true 且 data=false"（R12-FIX-API-01 记录的历史缺陷）改为"明确拒绝 + 无副作用"。

### 历史记录：修复前的卡点分析（保留备查）

**文档解析停在 99，`/parse` 未被调用。**

实测链路：`FileParseTaskScheduler` 已取任务 → 调 `POST 12340/parse/multi_version` 返回 200 →
之后**没有** `POST /parse`，文件状态恒为 99，`file_parse_task.status` 停在 1。

排查已排除：
- doc-parse 自身可用（`/docs` 200，`/parse_without_indexing` 曾实测 12 类样本通过）
- Nacos 配置可读（配置变更已被 doc-parse 热加载，日志 `doc-parse更新成功`）
- ES 405 已消失（配置修正后近 5 分钟 0 次）
- RocketMQ：producer 与 `kbFileParseConsume` 容器均已启动，broker 广告地址 `127.0.0.1:10911` 正确

下一步方向：
1. 看 `VersionRec.version_rec()`（`server/controller.py:1065` 上游）在 `have_version` 为空时的返回，
   以及 Java `FileAppServiceImpl.doFileMultiversion` 对空 `data` 的处理是否直接返回而未派发解析。
2. 若确认是"首次上传（无历史版本）被判定为无需解析"，属产品级缺陷，需在 Java 侧改为
   「无历史版本 → 直接进入解析」。
3. 备选快路径：绕过 multiversion，直接触发 `FileAppServiceImpl` 的单文件解析入口验证 `/parse` 链路。

## 4. 未开始/未完成（R13 剩余）

- Nebula 3.8 已 healthy（19669/19559/19779），`rag-graph-service` 未启动（无 `g_` space 前会连接失败）
- Python `index_graph_service`（19529）未运行：缺 `index_graph_config_py`；`requests_llm` 为自研协议需改 OpenAI 协议；`utils.py:122` 密码取 user
- 类型体系/版本、canonical 归一、合并审计与回滚、三元组重指向：**未实现**
- GraphRAG（社区检测/分级摘要/摘要索引/global map-reduce）：**未实现**
- Office 预览容器（18095）：**未建**
- FAQ / 表格问答 / 多版本 / Text2SQL / VLM 多图：**未端到端验收**
- 图片内联访问的授权替代路径（预签名或后端流式）：**未实现**（当前图片直链 403）
- JWT iss/aud/短 TTL：**未加固**

## 5. 恢复命令

```bash
# 全栈
/home/szf/data/dev/llmke-r12/platform/r12/bin/up.sh up
/home/szf/data/dev/llmke-r12/platform/r12/bin/up.sh verify
# systemd
systemctl --user status r12-models r12-alg r12-docparse r12-java@rag-index-service
# 僵死任务
/home/szf/data/dev/llmke-r12/platform/r12/bin/recover-stuck-tasks.sh 10 9
# 安全验收
python3 /home/szf/data/dev/llmke-r12/platform/r12/qa/security_acceptance.py
# 主链验收（注意：当前会卡在 S4）
python3 /home/szf/data/dev/llmke-r12/platform/r12/qa/acceptance.py
```

## 6. 阶段计划（TL，R13 收口路线）

| 阶段 | 目标 | 判定标准 | 状态 |
|---|---|---|---|
| S1 类型与归一 | unclassified 收敛、合并可回滚 | unclassified=0；回滚脚本实测通过 | ✅ 完成 |
| S2 图检索入主链 | `/qa` 走 `enabled_graph`，图块参与引用 | 检索服务调用 19529 返回 200 且 docs 含 graph 标记 | ✅ 完成（GRAPH-09/10；rerank 关闭时 search_type 含 graph） |
| S3 GraphRAG 本体 | 社区检测+分级摘要+摘要索引+global | 跨文档问题走社区摘要且引用可开原文 | ⬜ 未开始 |
| S4 一致性 | Nebula↔Milvus 实体/三元组对齐；删除同步 | 一致性检查输出 0 差异 | ⬜ 未开始 |
| S5 业务能力 | FAQ/表格/多版本/Text2SQL/VLM/Office 预览 | 每项至少一个真实场景通过 | ⬜ 未开始 |
| S6 回归与制品 | 主链 31 项 + 安全 10 项复跑；离线包重建 | 干净环境离线可复现 | ⬜ 未开始 |

（SubAgent 在本环境只有只读工具，实际用于勘察与评审；代码与运行时改动由 TL 执行。）

### S2 关键事实与修复
- 问答侧**本来就有**图开关：config JSON 的 `enabled_graph` 被原样透传给检索服务；检索服务 `retrieval_service.py:473-478` 在开启时调用 `retrieval_graph` 并把结果并入同一 documents。
- **R13-FIX-GRAPH-09**：检索服务在 `multiple_retrieval.py:431` 把 space 拼成 `"g_"+kb`，而图服务内部 `query_graph_data` 又拼一次 `"g_"`（graph_service.py:557）→ 实际查 `g_g_kb_9`，恒报"空间不存在"，图检索永远空。已改为传原始名。
- 已补 `alg_retrieval_config_py.graph_config`（127.0.0.1:19529），否则 `retrieval_graph` 取不到地址。
- 实测：检索服务日志出现 `POST http://127.0.0.1:19529/query_graph_data 200`（0.54s），图召回已触发。
- **R13-FIX-GRAPH-10**：`process_return_results` 只读 `metadata.search_type`，而图结果写的是 `metadata.search.type`；
  且同 pk 去重把后到的图结果整条丢弃 → "图检索执行了但引用看不出"。已改为：统一把 `search.type` 并入 `search_type`，
  去重时把来源标记合并到保留项。
- 实测（rerank 关闭）：docs[0].metadata.search_type = `['milvus','es','es','graph']` → 图来源可辨识。
- 实测（rerank 开启）：该块 rerank 分数低于 threshold 被过滤，属排序策略而非链路故障；S3 用更大图语料复验。

### S4 一致性
- 新增 `platform/r12/graph/consistency_check.py`：Nebula `g_<kb>` 实体 ↔ Milvus `graph_entity_<kb>` 比对，`--fix` 清理悬空向量。
- 首次运行：Nebula 47 / Milvus 67，**20 条悬空向量**（正是迁移时从图里删掉的噪声实体，仍会被实体链接命中）。
- `--fix` 后复核：Nebula 47 / Milvus 47，**0 差异**。
- 未做：`graph_triples_<kb>` 与 Nebula 边的比对；`del_space_data` 删除时不联动 Milvus（源码缺口，需改 Python）。

### S5 进展（结构化查询）
- 环境缺陷：`tools_database` / `tools_table` / `tools_table_column` / `tools_table_file` 四张表**从未创建**
  （tools 模块不在 actable 的 model 扫描包内），导致 `/index/database/*` 全部 500。已补 DDL：`platform/r12/sql/tools_ddl.sql`。
- **R13-SEC-D1**：`queryData` 增加对象级授权（超管 / 库创建人 / user|dept|group_privilege bizType=12 读权限），
  实测 `r13_noauth` 调用 → **403 + 30016**。
- **R13-SEC-D2**：SQL 校验收紧——SELECT/WITH 开头、禁止 `;`、危险关键字黑名单
  （INTO OUTFILE / INTO DUMPFILE / LOAD_FILE / SLEEP( / BENCHMARK( / INSERT / UPDATE / DELETE / DROP / ALTER /
  TRUNCATE / CREATE / GRANT / REVOKE / CALL / LOAD DATA / SET GLOBAL / SHUTDOWN），无 LIMIT 时强制 `LIMIT 500`。
- 实测：`select count(*) from user_info` → 200 `[{"c":5}]`；`select sleep(3)` → 拒绝；`select ... into outfile` → 拒绝。
- 仍缺：只读账号机制（连接级）、语句级 `queryTimeout`（当前只有行数与关键字层面）、LLM 生成 SQL 的 EXPLAIN 校验。
