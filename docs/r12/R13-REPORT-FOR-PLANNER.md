# R13 交付汇报（面向下一阶段长程任务规划）

> 收件人：R14 长程任务规划者
> 出具人：R13 执行侧（tech-lead）
> 出具时间：2026-10-27
> 代码基线：`feature/R12-real-rag` @ `6f73985`（工作树干净）
> 配套材料：同目录 `MATERIAL-INDEX.md`（材料清单）与 `evidence/`、`scripts/`、`snapshots/` 子目录

---

## 0. 一页结论

**R13 做完了什么**：把一套"能跑但多处假通"的 RAG 私有化系统，推到**本机可复现地全绿**，并具备离线安装条件。

| 维度 | R13 结束状态 | 判定依据 |
|---|---|---|
| 主链功能（建库→上传→解析→问答→引用→原文） | 31/31 PASS | `evidence/20261026T163339Z` |
| 安全（对象授权 / 原文收口 / 口令 / 内部口） | 16/16 PASS | `evidence/SEC-20261026T163542Z` |
| 撤权后全链路失效（含内网旁路探测） | 21/21 PASS | `evidence/REVOKE-20261026T163545Z` |
| 能力矩阵（普通/FAQ/global/多版本/表格/图局部/内部口） | 7/7 PASS | `evidence/CAPS-20261026T163311Z` |
| 部署态监听面 | 7/7 内部端口仅回环，导出面只有 8088/18088 | `snapshots/check-bind.txt`（退出 0） |
| 离线包 | 24G，10 类原缺失资产已补齐，`verify` 8 段真实校验通过 | `snapshots/offline-verify.txt` |

**没做完什么（不缩范围）**：所有"在干净目标机上真正装起来并跑通"的事都没发生。离线包从"装不起来"修到"可安装"，但**从未在第二台机器上装成功过**。这是 R14 的第一件事，也是当前唯一能推翻全部结论的风险点。

**一句话给规划者**：R13 的产出是"**可复现的本地基线 + 一套能识别假绿的验收工具**"，不是"可交付的产品"。下一阶段的重心应从"修功能"转向"**证明它能被交付**"（实装、容量、恢复、升级、发布），并补齐三个已知的**静默失效点**（Nebula 代次漂移、社区摘要重复、快照回退）。

---

## 1. 这份材料怎么用

- 想快速判断"到底做成没有"：看第 6 节验收结果 + `snapshots/` 里的原始输出（不是结论，是命令输出）。
- 想规划 R14：看第 7 节（未关闭/风险）+ 第 8 节（建议工作包 WBS）。
- 想知道某条缺陷的真因：看第 5 节缺陷台账，每条都有编号，代码里可 `grep 编号` 定位注释。
- 想复核数字：`scripts/` 里有四套验收脚本，全部可重跑；`scripts/RUNBOOK.md` 给了逐步命令。

**材料可信度约定**：本报告中所有 PASS/FAIL 均附**证据目录名**（时间戳即采样时刻）。运行态结论一律带采样时刻，因为本环境的服务曾被反复重启，脱离时刻的运行态结论不可比。

---

## 2. 系统与范围

### 2.1 系统是什么

一套**全私有化**的企业知识库问答系统（金融场景，中文为主）：

- 业务能力：知识库管理、文档解析（含 OCR/VLM）、向量+全文混合检索、FAQ 抽取与直答、多版本文档、GraphRAG（社区摘要 + 图局部）、Office 在线预览、表格数值问答、问答引用可回溯到原文。
- 技术栈：Java 21（Spring Boot 微服务）+ Python 3.11（算法服务，FastAPI）+ React/Vite 前端；MySQL 8.4 / Elasticsearch 8.13.4 / Milvus 2.5.6 / NebulaGraph 3.8 / MinIO / Redis / Nacos 2.3.2 / RocketMQ 4.9.7。
- 部署形态：单机 Docker 基础设施 + systemd --user 托管 Java/Python 进程；目标形态是**离线包 + 目标机整栈安装**。

### 2.2 R13 的目标（执行侧理解）

1. 让"看起来能用"的能力**真正可用**（FAQ、GraphRAG、多版本、Office 预览此前多为假通）；
2. 把安全从"登录即可读"推到**对象级授权**；
3. 产出一份**可安装**的离线交付物；
4. 用**可复现的验收**替代"口头说通过"。

### 2.3 明确不在 R13 范围

容量压测、高可用、备份恢复演练、升级回滚、正式发布流程、多租户、审计合规取证——均属 R14 及以后。

---

## 3. 架构与运行基线

### 3.1 组件与端口（R12/R13 自有栈）

| 层 | 组件 | 监听 | 说明 |
|---|---|---|---|
| 接入 | r12-fe（nginx） | 18088 | 前端静态 + `/proxy/` 反代网关 |
| 接入 | rag-gateway | 8088 | 统一入口，AuthFilter 鉴权 |
| 业务 | rag-auth / rag-index / rag-qa / sensitive-words（+ rag-graph） | 18081/18082/18083/18085/18084 | Java 21 |
| 算法 | alg_doc_parse | 12340 | 解析（OCR/VLM） |
| 算法 | alg_retrieval | 19995 | 检索（含 global） |
| 算法 | llm_open_chat | 19996 | 推理编排 |
| 算法 | index_vector / index_fulltext / index_graph | 19526/19527/19529 | 写入与图索引 |
| 算法 | 预览 r12-preview | 18095 | LibreOffice → PDF |
| 模型 | 推理 / 向量 / 重排 / VLM | 18090-18093 | 本地模型服务 |
| 基础设施 | MySQL/ES/Milvus/Nebula/MinIO/Redis/Nacos/RocketMQ | 33xx/19200/19530/19669/19000/16379/18848/19876 | Docker |

**安全基线（R13 收口后）**：上表中除 `8088`（网关）与 `18088`（前端）外，**其余全部只绑 127.0.0.1**。这是 R13 最后一项、也是最重的一项变更（详见 5.6）。

### 3.2 运行环境

- 主机：Linux 6.8.0-47，20 核 / 62G 内存 / RTX 3060 Laptop 6G 显存
- 说明：该机**并非独占**，同时跑着与本项目无关的 hadoop、WeKnora、yuxi 等容器。R13 期间出现过因资源争抢导致的前端构建 OOM（vite 进程 core dump），故所有性能数字都不能当容量基线。
- Java 21.0.11 / Python 3.11.15（另有 3.10 venv 用于解析侧）

### 3.3 数据规模（kb_9 为主测试库）

| 指标 | 值 |
|---|---|
| 知识库 | 11 |
| 文件 | 281 |
| 问答记录 | 239 |
| 接口元数据（网关授权表） | 442 |
| ES：kb_9 / faq_kb_9 / community_summary_kb_9 | 8 / 20 / 7 |
| Milvus：graph_entity_kb_9 / graph_triples_kb_9 | 39 行 / 31 行 |
| Nebula `g_kb_9` | 83 顶点 / 120 边 |

**规模结论**：全部数据在"演示级"量级（万级 chunk 以下），**没有任何容量结论**。

---

## 4. R13 交付内容（按能力域）

### 4.1 安全：从"登录即可读"到对象级授权

- 新增 `KbAuthzService`：知识库/文件/会话的读、写、删、管理四类动作，统一按 `user/dept/group_privilege`（biz_type 0/1/2/3）判定，覆盖 KB 详情/更新/删除/重解析/下载、文件详情/删除/解析、`/stream` 对象键、问答入口。
- Feign 调用传主体；**无主体一律 fail-closed**（R13 末尾补的加固，见 5.6）。
- 原文访问收口三处：MinIO 匿名策略撤销（直连与 nginx `/minio` 反代均 403）、`/preview/` 反代改 403、Office 预览改走 `POST /index/knowledgeBase/file/previewStream`（先对象级鉴权再转 PDF）。
- 口令：MD5 → BCrypt，历史 MD5 登录成功后透明升级。
- 内部回写接口（`uploadParsedFile`、`parseTask/callback`）加共享令牌，未配即拒绝。

### 4.2 问答链：修掉一条"三层叠加"的故障链

现象是"模型暂时无法返回"，实际是三个独立缺陷串联：

1. `getSimpByModeName` 在异步线程里取不到主体 → 抛 `Cannot parse null string`；
2. 失败结果被写回 `config_json` **并持久化**，导致该会话之后**永久**缺 `model_info`（一次偶发 = 永久坏）；
3. 推理服务收到缺字段的请求返 422，`attribute.split_documents` 又因简化文档模式无 `metadata` 抛 `KeyError`，SSE 流中断，前端只看到兜底文案。

处置：`getSimpByModeName` 无主体回退不按主体过滤 + `modelBasedInference` 前幂等补齐 `model_info` + `split_documents` 补空 metadata 兜底。

### 4.3 FAQ：从"任务成功但 0 产出"到直答命中

- 抽取侧：`alg_llm_config_py` 缺 `milvus_config/es_config`；`llm_service` 读的是**单例启动缓存**（配置发布+重启都不生效）→ 改实时拉 Nacos；chunk 查询把 `.docx` 改写成 `.pdf` 去匹配 ES `title` → 双匹配。
- 召回侧：Java 侧曾整段丢弃 `faq_result_list`；FAQ 开关只落在 DB 列而 JSON 是旧值；合成 FAQ 条目无 metadata 导致 NPE；直答未标 `resultType`。
- 结果：20 条 `status=1`，命中 score 0.9997，`resultType=2` 单帧直答 1.4s（不调大模型）。

### 4.4 多版本

版本号贯通解析链路；`document_version` 不再只看 `revise_date`；检索只返回当前有效版本（kb_9 同时存在 V0=5000万 / V1=8000万，实测只答 8000万，不再自相矛盾）；引用 metadata 带 `parent_file_name/version`。

### 4.5 GraphRAG

- **local**：根因是 `chunk_pk_list` 存的是**抽取时刻的 ES `_id`**，文档重解析后全部失效（图能查到实体/边，但回填正文恒空）；叠加 `entity_list` 定义后从未赋值、共享 Nebula Session 每请求 release（并发必 500）、悬空实体 KeyError。已修 + 提供 `graph-refresh.sh` 全量回填。
- **global**：社区摘要 map-reduce 接入 `/qa` 主链（`globalMode=true`），前端加开关；引用从"社区"回溯到来源文件（靠 `file_names` 回落，见 4.9）。

### 4.6 Office 预览

自建镜像 `r12/preview-office:r13`（LibreOffice 25.2.3.2），docx/pptx/xlsx → PDF 实测正确（中文、表格）。收口到鉴权端点，浏览器不再能拿对象键匿名取原文。

### 4.7 运维与可观测

`up.sh {up|down|status|verify}` 覆盖 基础设施(含 Nebula)→模型→算法→解析→图谱→业务→预览→前端；`r12ctl.sh` 单服务控制；`graph-refresh.sh <kbId> <kbName>` 图谱全量重建；`check-bind.sh [--samples N] [--expect-loopback]` 监听面验收门。

### 4.8 离线交付

- `offline-kit.sh {pack|verify}`：pack 幂等，verify 8 段真实校验（旧版是**假绿**：缺 10 类资产仍打印"校验通过"）。
- `install-paths.sh`：把 systemd/env/Nacos 里 20 处构建机绝对路径改写为目标机路径，venv 重定位，支持 `--dry-run/--check`，二次执行幂等。
- `init-db.sh` / `init-nacos.sh`：从 `.env` 读口令，等就绪 + 回读校验。
- 产物：24G（images.tar + payload：jar/dist/conf/systemd/preview/graph/venvs/models/services 源码/db 导出/nacos 配置 + SHA256SUMS + INSTALL-OFFLINE.md）。

### 4.9 引用可打开（跨模块的最后一厘米）

引用点了打不开有三个独立原因，逐个修：非 pdf 文件名被改写成 `.pdf`（S6-01）、社区摘要 `file_id` 随重传失效（GRAPH-18，改按 `file_names` + `queryList` 回落同名文件）、`knowledge_base_name` 在请求体里是 `String[]` 而非 `JSONArray`（只判后者会 toString 成 `[Ljava.lang.String;@xxx`）。

---

## 5. 缺陷台账（R13 关闭）

> 编号可在代码中 `grep` 到，注释里写了根因。类别：S=安全 / Q=问答链 / F=FAQ / V=版本 / G=图 / P=预览 / O=交付运维

| 编号 | 类别 | 根因（一句话） | 修复要点 | 验证 |
|---|---|---|---|---|
| SEC-A1 | S | 只有登录校验，按 id 可直读他人 KB | 对象级授权覆盖 6 类入口 + Feign 传主体 | SEC-1..9,12,16 |
| SEC-A2 | S | MinIO 桶匿名可读 + `/minio` 反代 | 撤匿名策略 + `/stream` 按对象键反查 | SEC-3,15 |
| SEC-A2b | S | `/preview/` 对浏览器直开放 | 反代改 403 + 新增鉴权预览端点 | SEC-11..14 |
| SEC-A3 | S | 口令仅 MD5 | BCrypt + 登录时透明升级 | SEC-10 |
| SEC-A4 | S | 权限不足映射成 500 | 统一 403 | SEC-1..7 |
| SEC-NET-01 | S | 7 个内部端口绑 `0.0.0.0` | 全部改回环（配置+快照+镜像 CMD+systemd 四处同改） | REVOKE-R15..18 |
| SEC-A2(补) | S | 授权断言在"取不到配置/库名"时 fail-open | 改 fail-closed | SEC-16 |
| Q-07 | Q | 异步线程无主体 → `Cannot parse null string` → `model_info=null` | 无主体回退不按主体过滤 | 问答 200/6.7s |
| Q-08 | Q | 缺 `model_info` 被写回 `config_json` 持久化，永久坏 | 推理前幂等补齐 | 同一问题复测 |
| Q-09 | Q | 简化文档模式无 `metadata` → `KeyError` → SSE 中断 | 补空 metadata 兜底 | SSE 完整 |
| Q-10 | Q | 上游断流无终止帧 → Flux 等不到 onComplete | 空闲超时收敛 | 长问答不挂死 |
| S6-01 | Q | 非 pdf 名改写 `.pdf` 匹配 title（实存原名） | 双匹配 | S6 原文核对 |
| F-04/06/07 | F | chunk 标题改写 / 缺 `milvus_config` / 读启动期配置缓存 | 三处同修，配置改实时拉取 | FAQ 抽取 20 条 |
| F-08..12 | F | `faq_result_list` 被丢弃 / 开关落 DB 列而 JSON 旧值 / 合成条目无 metadata NPE / 未标 resultType | 逐项修 | CAPS-FAQ |
| V-10..15 | V | 版本未贯通；`ParsedTextMetadata` 无 `version` 字段致整批解析失败；`document_version` 排序 NPE | 贯通 + 容错 | VERSION 组 |
| G-13..17 | G | `chunk_pk_list` 存抽取时刻 `_id`；`entity_list` 从未赋值；Nebula Session 每请求 release；悬空实体 KeyError | 修 + 全量回填 | 图 local 4 并发 |
| G-18 | G | 社区 `file_id` 随重传失效 | 按 `file_names` 回落 | CAPS-GLOBAL |
| P-01/02/03 | P | 预览 500（二进制响应被包成 CommonResponse）/ nginx 匿名反代 / 网关缺角色映射 | 三处同修 | SEC-11..14 |
| O-01..16 | O | 离线包缺 10 类资产、20 处构建机路径、verify 假绿、快照带 0.0.0.0 | 重写 pack/verify/install-paths | offline-verify |

**共性教训（对规划者最有价值的三条）**：

1. **"成功"要验证到产出物**。FAQ 报"抽取成功"但产出 0 条；GraphRAG 报 200 但 `entity_list` 恒空。判据必须落到"下游能否消费"。
2. **一次偶发失败会被持久化放大**。Q-08 把失败结果写回配置并持久化，把偶发变成永久。
3. **"改了"≠"生效"**。R13 撞到四次：配置缓存（F-07）、`daemon-reload` 缺失（systemd）、镜像 CMD 硬编码（`app.py` 改动是死代码）、本地快照回退（配置改对了但服务读快照）。**验收必须看运行态，不能看 git diff。**

---

## 6. 验收结果与口径

### 6.1 四套脚本

| 套件 | 条数 | 结果 | 覆盖 |
|---|---|---|---|
| `acceptance.py` | 31 | 31/31 | 中文 DOCX/XLSX/PPTX/数字 PDF/扫描 PDF(OCR)/纯文本/含表格；加密 PDF 预期失败；坏文件、伪造 token、越权删除被拒 |
| `security_acceptance.py` | 16 | 16/16 | 匿名/越权/伪造 token/对象键直取/预览/存储直连/无法归属的对象键 |
| `revoke_acceptance.py` | 21 | 21/21 | 先证可用→撤权→六链路全拒（复用旧 sessionId 也不行）→恢复→KB 本体不变；含内网旁路探测 |
| `r13_full_check.py` | 7 | 7/7 | 普通/FAQ/global/多版本/表格/图 local/内部口收口 |

### 6.2 两道"门"（防假绿的关键装置）

- **监听面门**：`check-bind.sh --samples N --expect-loopback`，退出 0 才算收口。它比对"配置声明值（Nacos 内容/本地快照/源码/启动参数）"与"实际 ss 绑定"，能识别**静默抵消**（配置已收紧但运行态外露）。发明它的原因：只看配置文件会误判"已修好"。
- **离线包门**：`offline-kit.sh verify`，8 段真实校验。旧版在缺 10 类资产的沙箱里仍打印"通过"，是**假绿**；新版在构建机 PASS、在缺资产沙箱 FAIL。

### 6.3 证据可信度说明

- 每条结论都带证据目录时间戳；
- 授权态断言允许最多 3 次重试（依赖外部模型服务），**拒绝态断言一律单发不重试**；
- 连接中断记为 `http=0`，**绝不当成"被拒绝"**；
- 期间确实遇到服务被反复重启，靠上述三条才没有把环境抖动写成 FAIL 或假 PASS。

---

## 7. 未关闭项与风险（规划者重点看这一节）

### 7.1 阻断级（R14 若不解决，R13 结论不可交付）

| # | 风险 | 现状 | 影响 |
|---|---|---|---|
| R1 | **从未在干净目标机实装** | 包已可安装（10 类资产补齐、路径改写脚本就绪），但第二台机器上没跑过 | 一切"可交付"结论未验证；安装文档的正确性未证 |
| R2 | **数据面代次漂移** | Milvus 图数据已回填，Nebula 边上的 `file_id/page_num` 仍是旧代次 | 任何 kb 重解析后图引用会指向已删文件；彻底修复需停机 `del_space` 重建（R13 未擅自动） |
| R3 | **Nacos 快照回退** | 5 个 Python 服务在配置中心不可达时按本地快照启动（仅 doc-parse 关了 `no_snapshot`） | 加固会"静默失效"；运维侧一旦 Nacos 抖动，绑定/路径回到旧值 |

### 7.2 中危（影响质量或可维护性）

| # | 风险 | 现状 |
|---|---|---|
| R4 | 图抽取覆盖度与质量受限于 LLM | kb_9 仅 7 社区/39 实体；实体归并质量差（"授信额度"被并成"5000万元"） |
| R5 | `community_summary` 重复 | Milvus 30 行 vs ES 7 条（只 insert 未按 `community_id` 去重） |
| R6 | 内部服务不做鉴权，只信任回环 | 回环内可无凭据直连 `19995/18095` 取数据。**属既定边界**，装机前提须写死"单租户主机、仅本机调用" |
| R7 | 前端与后端各自可用，端到端未逐个点验 | FAQ 管理页、Office 预览、多版本历史、global 开关都"存在且接口通"，但没有"从页面点一遍"的证据 |
| R8 | 容量/性能无基线 | 全部数据为演示级；主机非独占，性能数字不可用 |
| R9 | 离线包体积 24G | 含 models 13G + venvs；目标机磁盘与拷贝时延未核算 |

### 7.3 环境类（影响复现，不影响产品）

- 构建机同时跑无关容器（hadoop/WeKnora/yuxi），曾导致前端构建 OOM；
- `up.sh` 第 8 步 `npm run dev` 在离线环境必失败（静默），应裁剪；
- systemd `--user` + `enable-linger` 的启用与否需目标机决策。

---

## 8. 对 R14 的建议工作包（供规划者裁剪，不是结论）

> 原则：**先证明能交付，再优化效果**。顺序不可倒——R1 未闭环前，任何效果类工作都可能白做。

### WBS-A｜离线实装（最高优先，阻断一切）

- A1 目标机准备：OS/内核、Docker、python 3.11 + 3.10 各一套（与 `pyvenv.cfg` 同小版本）、磁盘 ≥40G、端口 8088/18088 可用
- A2 填 `.env` 4 项口令 → `install-paths.sh` → `init-db.sh` → `init-nacos.sh` → `up.sh up`
- A3 装后验收：`up.sh verify` + `check-bind.sh --expect-loopback` 退出 0 + 四套脚本（至少 acceptance 与 security）
- A4 产出：安装日志、失败点清单、修正后的 INSTALL 文档
- **验收判据**：目标机上主链 ≥28/31（允许 OCR/模型相关项降级）、安全 16/16、绑定门退出 0
- **风险**：pyvenv 版本不匹配、镜像导入耗时、端口冲突（r12-fe 用 host 网络直接占 18088）

### WBS-B｜数据一致性闭环

- B1 Nebula 停机重建（`del_space g_kb_9` → 全量回填），验证边属性与 ES 对齐
- B2 `community_summary` 按 `community_id` 去重（upsert 而非 insert），Milvus/ES 计数一致
- B3 把 `graph-refresh.sh` 挂到"文档重解析完成后"的自动触发（当前靠人工）
- **验收判据**：重解析 → 引用仍可打开（无需人工干预）；Milvus 与 ES 计数一致

### WBS-C｜交付形态硬化

- C1 快照回退：统一 `no_snapshot=True` 或启动时校验（消除静默失效）
- C2 内部服务鉴权（若跨机部署）：内网共享令牌或 mTLS
- C3 离线包瘦身与分层（models 单包、增量升级包）
- C4 备份恢复 / 升级回滚演练（各 1 次，留证）

### WBS-D｜效果与体验（可与 A/B 并行，但验收独立）

- D1 图抽取质量：实体归并、覆盖度；给出"可答问题集"与基线
- D2 global 逐步引用（当前只到社区→文件级）
- D3 前端端到端点验（FAQ 管理、预览、多版本历史、global 开关）× 4 条
- D4 容量基线：在独占机上跑 10/100/1000 并发的退化曲线

### 建议里程碑

| 里程碑 | 内容 | 判定 |
|---|---|---|
| M1（1 周） | WBS-A 完成 | 目标机四套脚本绿 + 绑定门 0 |
| M2（1 周） | WBS-B + C1 | 重解析后引用自动可打开、无静默失效点 |
| M3（1–2 周） | WBS-D | 效果基线与前端点验留证 |
| M4 | C3/C4 + 发布流程 | 备份恢复/回滚演练通过 |

---

## 9. 度量与口径（建议 R14 沿用）

1. **PASS 必须可复现**：同一脚本连跑两次结果一致（撤权验收已做到连跑 4 轮一致）。
2. **拒绝态单发**：安全类断言不重试，避免"重试到通过"。
3. **运行态优先**：任何"已修复"必须附运行态证据（端口/进程/接口返回），不接受 git diff 作为证据。
4. **假绿零容忍**：验收工具本身要被反向验证（缺资产/错配置时必须 FAIL）。R13 的 `verify` 与 `check-bind` 都做过变异测试。
5. **降级要声明**：允许"该项在目标机不可用"，但必须在报告里显式列出，不得静默缩范围。

---

## 10. 规划者可能需要追问的点（我未给出结论）

1. **交付性质**：是"给客户装机"还是"内网自用"？前者需要 R6 的内部鉴权与合规取证，后者可接受回环信任边界。
2. **规模预期**：文档量/并发量决定是否需要拆库、是否要 Milvus 分片、是否要 GPU 升级（当前 6G 显存跑 VLM 已接近上限）。
3. **多租户**：当前授权是"用户-部门-用户组"三层，是否要跨租户隔离？
4. **国产化约束**：是否有信创 OS/数据库/中间件要求（当前栈为开源组件，未见信创适配）。
5. **R14 是否含"替换模型"**：模型服务当前为本机 llama.cpp/vLLM 形态，若换云 API，`model_info` 机制需重新验证。

---

## 附：材料清单

见同包 `MATERIAL-INDEX.md`。核心文件：

- `R13-STATUS.md`（本包内）：能力矩阵与未完成项
- `R13-REPORT-FOR-PLANNER.md`（本文）：面向规划的汇总
- `INSTALL-FINDINGS.md`：离线安装 16 项缺陷（10 阻断）与修复
- `LOCAL-RETRIEVAL.md`：图局部检索根因与回填手册
- `evidence/<四套终版>/`：summary.md + detail.json
- `scripts/`：四套验收脚本 + 客户端 + RUNBOOK
- `snapshots/`：`check-bind`、`ss -lnt`、`up.sh verify`、`offline-kit verify`、`git log`、`docker ps` 的原始输出
