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
