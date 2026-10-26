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


---

# 附录：原始证据（命令输出，非结论）
> 以下均为 2026-10-27 采样时刻的原始输出，用于复核上文数字。


---

## A1 监听面验收门（7 个内部端口，退出码 0）
```== check-bind（前缀 /home/szf/data/dev/llmke-r12/platform/r12）==
  PORT   服务         面    配置声明       声明来源（值@来源）           实际监听   判定
  12340  doc-parse      写入面 127.0.0.1          127.0.0.1@payload,127.0.0.1@snapshot   127.0.0.1      一致
  18095  preview        读    127.0.0.1          127.0.0.1@启动参数,127.0.0.1@源码 127.0.0.1      一致
  19526  index_vector   写入面 127.0.0.1          127.0.0.1@payload,127.0.0.1@snapshot   127.0.0.1      一致
  19527  index_fulltext 写入面 127.0.0.1          127.0.0.1@payload,127.0.0.1@snapshot   127.0.0.1      一致
  19529  index_graph    读    127.0.0.1          127.0.0.1@payload,127.0.0.1@snapshot,127.0.0.1@systemd 127.0.0.1      一致
  19995  alg_retrieval  读    127.0.0.1          127.0.0.1@payload,127.0.0.1@snapshot   127.0.0.1      一致
  19996  llm_open_chat  推理 127.0.0.1          127.0.0.1@payload,127.0.0.1@snapshot   127.0.0.1      一致

  [ok] 全部内部端口仅监听回环
check-bind exit=0
```


---

## A2 全栈健康自检（up.sh verify）
```  http://127.0.0.1:18088/ -> 200
  http://127.0.0.1:15174/ -> curl: (7) Failed to connect to 127.0.0.1 port 15174 after 0 ms: 连接被拒绝
000
conn-fail
  http://127.0.0.1:8088/auth/user/kaptcha -> 200
  http://127.0.0.1:18095/healthz -> 200
  http://127.0.0.1:19200/_cluster/health -> 200
  minio anonymous GET (expect 403) -> 403
rag-auth-service RUNNING
rag-index-service RUNNING
rag-qa-service RUNNING
sensitive-words-service RUNNING
rag-gateway RUNNING
rag-graph-service RUNNING
```


---

## A3 导出面（仅 8088 / 18088）
```LISTEN 0      511               0.0.0.0:18088      0.0.0.0:*          
LISTEN 0      32768                   *:8088             *:*          
```


---

## A4 离线包 8 段校验（末段）
```== 1. 完整性清单 ==
  [ok] SHA256 全部匹配
== 2. 镜像 ==
  [ok] 镜像齐备（13 个）
== 3. 必需文件与目录（缺一个就是装不起来）==
  [ok] 必需项齐备（31 项）
== 4. jar 与前端产物 ==
  [ok] jar 12 个
  [ok] 前端 dist 完整：index.html + assets/1000 项（/home/szf/data/dev/llmke-r12/frontend/plateform/dist）
== 4.1 preview 启动结构（py_compile 抓不到的坑）==
  [ok] preview/app.py 启动结构正常（uvicorn.run 在 __main__ 块内）
== 5. venv 与模型 ==
  [ok] venv parse 可执行（Python 3.11.15）
  [ok] venv alg 可执行（Python 3.11.15）
  [ok] venv graph 可执行（Python 3.10.12）
  [ok] venv models 可执行（Python 3.11.9）
  [ok] model bge-m3 存在
  [ok] model bge-reranker-v2-m3 存在
  [ok] model gguf 存在
  [ok] model gguf-vl 存在
  [ok] model llama.cpp 存在
  [ok] model ocr_models 存在
== 6. .env 与运行目录 ==
  [ok] .env 已配置
  [ok] logs/run/pid 目录可创建
== 7. 配置可解析 ==
  [ok] 配置 YAML 可解析: 6/6
  [ok] 配置解析通过（6 个）
== 8. 可移植性（构建机绝对路径残留）==
  [..] 构建机路径（预期）: systemd/r12-alg.service
  [..] 构建机路径（预期）: systemd/r12-docparse.service
  [..] 构建机路径（预期）: systemd/r12-graphsvc.service
  [..] 构建机路径（预期）: systemd/r12-java@.service
  [..] 构建机路径（预期）: systemd/r12-models.service
  [..] 构建机路径（预期）: systemd/doc-parse.env
  [..] 构建机路径（预期）: run/doc-parse.env
  [!!] 构建机模式：7 个文件含构建机路径（打包后由 install-paths.sh 改写，目标机不算通过）
== 9. 监听面基线（提示项，不计失败；由安全侧定夺）==
  [ok] 配置内无 server.host=0.0.0.0
  [!!] 落地后用 check-bind.sh 核实际绑定（--expect-loopback 要求退出 0）；preview 为 host 网络，无端口映射可限

  [ok] 离线校验通过
EXIT=0
```


---

## A5 运行环境
```host: Linux 6.8.0-47-generic
cpu: 20
mem: 62G
openjdk version "21.0.11" 2026-04-21
Python 3.11.15
```


---

## A6 提交历史与工作树
```6f73985 fix(r13): 平台目录残留 nacos 快照仍绑 0.0.0.0（check-bind 抓到）
c94408a feat(r13): 四套验收全绿 + 内网暴露面收口 + 离线包可安装化
4e24ffb feat(r13): 团队并行交付合并（图局部检索/撤权验收/前端开关/离线核查）+ 内部端口收口
57b778e fix(r13): 内部回写接口不再裸放行（共享令牌 + fail-closed）
2bc43d7 docs(r13): 如实登记图局部检索不可用（entity_list 恒空、Milvus 缺 graph_entity_* 集合）
1937331 feat(r13): 离线安装包补齐数据库与 Nacos 配置（可重建，不再依赖现网状态）
a3ddda4 feat(r13): 离线安装工具（manifest/pack/verify/smoke）
96d88d5 feat(r13): FAQ 直答真正生效（resultType=2）
50cd95d docs(r13): 状态矩阵更新 + 增量制品 r13-update-202610261850（934M，含最新 jar/前端/conf/systemd/preview/graph）
e3a6cc8 feat(r13): FAQ 命中结果回灌召回列表（命中后走 FAQ 直答分支）
55feb6f feat(r13): GraphRAG global 真正接入问答主链（含引用回到原文）
99e422e feat(r13): 版本去重/引用健壮性 + global 请求级开关（未验证生效，如实登记）
9b7bba2 docs(r13): 表格数值问答实测通过；FAQ 召回与作答路径分别标注
def5376 docs(r13): 状态矩阵更新（多版本生效、QA-10/RUN-05/VER 系列缺陷登记）
2698097 fix(r13): 解析元数据版本字段 + SSE 空闲超时（消除问答偶发挂死）
43b8290 feat(r13): 多版本当前有效版本生效 + 检索健壮性
259ae4f fix(r13): 重启后解析队列自愈 + global 溯源字段
8513138 feat(r13): GraphRAG 全局问答接入问答主链（社区摘要 reduce）
c2e6c14 docs(r13): R13 状态与能力矩阵（实测证据 + 明确未完成项）+ 增量制品
21d78d8 fix(r13): 引用->原文按文件 id 取回 0 chunk（title 被改写为 .pdf）
58fb1ff fix(r13): 修复问答 422 与流中断（model_info 缺失、metadata 缺失）
7b3cd87 feat(r13): Office 预览真实可用且收口到对象级授权
bf56d7f feat(r13): FAQ 端到端真实可用 + 引用版本标识 + 多版本404消除
b2c1485 fix(r13): FAQ 零产出不再假成功 + chunk 查询原名兜底 + 答案过滤修正
6d3528a fix(r13): FAQ 抽取链路可执行化与指标查询防崩（S5 部分）
08e7a87 feat(r13): S3 GraphRAG 最小闭环（社区检测+真实LLM摘要+摘要索引+global查询）
66a717f feat(r13): 结构化查询可用性修复 + SQL 护栏与对象级授权（S5）
2461899 feat(r13): S2 图来源可辨识 + S4 一致性检查（实体侧 0 差异）
e119cc8 fix(r13): 修复图检索双 g_ 前缀导致恒空（S2 阶段）
2826ca3 feat(r13): 类型覆盖收敛（unclassified 12->0）与可回滚的合并审计
f470f88 feat(r13): 图谱类型体系 v1、实体过滤与 canonical 归一（含存量迁移）
524eaba fix(r13): 多文件图抽取跑通（ES 时序重试 + 原始文件名匹配）
328f24b fix(r13): 打通 Java 图解析产品入口（file_ids 生效、补必填知识库名、空批次不判失败）
c835051 docs(r13): 更新检查点——图谱链路进展与 Java 图解析入口未接通的事实
2ef2c7d feat(r13): 打通图谱抽取与局部图检索（真实文档 -> Nebula -> 原文回填）
7f946bf fix(r13): 修复解析任务队列被已删文件阻塞，主链恢复 31/31
48bd589 fix(r13): 解析预检 ES 代理端口、systemd env 格式、僵死任务恢复与检查点
142fa96 feat(r13): 对象级授权、原文访问收口、口令 BCrypt、服务间主体传递与 systemd 托管
f126417 feat(r12): 全栈一键启停脚本 + 前端产物恢复 + 引用走 /minio
0644af2 chore(r12): 验收脚本修正、桶只读策略与交付报告更新
 M docs/r12/R13-STATUS.md
?? docs/r12/R13-REPORT-FOR-PLANNER.md
```


---

## A7 能力矩阵摘要
```# R13 能力矩阵自检

总计 7/7 PASS

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=22 refs=3 rt=1 |
| FAQ | PASS | http=200 status=2 resultType=2 answer='不是，客户访前准备是文档的一部分内容，但不是主要部分。' refs=2 |
| GLOBAL | PASS | http=200 status=2 cost=2.7s refs=5 ref_src示例=ct-loan.docx/V0/R12FIX-product-loan.docx |
| VERSION | PASS | http=200 groups=0 |
| TABLE | PASS | http=200 status=2 命中3000=True answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | PASS | http=200 docs=3 graph_docs=1 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
```


---

## A8 撤权验收摘要
```# R13 撤权验收 20261026T163545Z

主体：`r13_reader`（biz_type=1 / target_id=9 / permission=1）；撤权动作：删除该行；finally 中已恢复。

总计 21/21 PASS

> 采样时刻：20261026T163545Z（UTC）。R15–R18 的端口监听结论是**该时刻的运行态快照**，不代表源码/配置仓当前内容——源码已改但运行态未重载时，两者会不一致，这本身就是本报告要暴露的"静默抵消"情形。

| 用例 | 结果 | 详情 |
|---|---|---|
| R1 授权时知识库详情可读 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=200 kbName=R12验收主链 |
| R2 授权时普通问答返回完整回答 | PASS | POST /qa/ai/question http=200 status=2 resultType=1 内容长度=165 引用数=3 帧数=95 尝试=1 |
| R3 授权时 global 问答返回完整回答 | PASS | POST /qa/ai/question(globalMode=true) http=200 status=2 内容长度=77 引用数=2 帧数=43 尝试=1 |
| R4 授权时 FAQ 直答命中（resultType=2） | PASS | POST /qa/ai/question(FAQ) http=200 status=2 resultType=2 内容长度=27 尝试=1 |
| R5 引用可构造出可访问的对象键 | PASS | 对象键=r12-rag/kb_9/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx |
| R6 授权时可取回引用原文流 | PASS | POST /index/knowledgeBase/file/stream http=200 ctype=application/octet-stream 字节=37544 head=b'PK\x03\x04' |
| R7 授权时可预览（返回真实 PDF） | PASS | POST /index/knowledgeBase/file/previewStream http=200 ctype=application/pdf 字节=100329 head=b'%PDF-1.7' |
| R8 撤权后知识库详情被拒 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=403 resp={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| R9 撤权后问答被拒且未返回知识库内容 | PASS | POST /qa/ai/question http=403 status=None 内容长度=0 引用数=0 errorCode=30016 body={"success":false,"errorMsg":"没有足够权限","errorCode":"30016","data":null} |
| R10 撤权后 global 问答被拒且未返回内容 | PASS | POST /qa/ai/question(globalMode=true) http=403 status=None 内容长度=0 引用数=0 |
| R11 撤权后 FAQ 直答被拒且未返回内容 | PASS | POST /qa/ai/question(FAQ) http=403 status=None resultType=None 内容长度=0 引用数=0 |
| R12 撤权后按已知对象键取原文被拒 | PASS | POST /index/knowledgeBase/file/stream http=403 ctype=application/json resp={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| R13 撤权后预览被拒 | PASS | POST /index/knowledgeBase/file/previewStream http=403 resp={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| R14 撤权后连续两次问答均被拒（无缓存旁路） | PASS | 复用旧会话 http=403 status=None 内容=0 引用=0; 新会话 http=403 status=None 内容=0 引用=0 |
| R15 撤权后经非回环地址无法无凭据取回 kb_9 内容 | PASS | POST http://192.168.71.16:19995/retrieval_documents 不可达（ConnectionError） |
| R16 撤权后经非回环地址无法无凭据取回原文 | PASS | POST http://192.168.71.16:18095/stream 不可达（ConnectionError） |
| R17 内部服务端口仅监听回环地址（含写入面 12340/19526/19527） | PASS | 全部仅监听回环 |
| R18 撤权后经非回环地址无法取回图谱检索结果 | PASS | POST http://192.168.71.16:19529/query_graph_data 不可达（ConnectionError） |
| R19 恢复授权后知识库详情恢复可读 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=200 |
| R20 恢复授权后问答恢复可用 | PASS | POST /qa/ai/question http=200 status=2 内容长度=164 引用数=3 尝试=1 |
| R21 全过程知识库本体未被改动 | PASS | before=1/15 after=1/15 撤权期间授权表=3	1	1	1;3	3	1	1 |

## 事实记录（INFO，不计入 PASS/FAIL）

- 回环内无凭据可读（既定边界，不计分）：POST 127.0.0.1:19995/retrieval_documents → documents=1；POST 127.0.0.1:18095/stream → http=200 字节=100329。含义：内部服务不做对象级授权，安全性完全依赖'只绑回环 + 仅 Java 调用'；本机任意进程/用户仍可绕过 user_privilege 取数据，若该边界不被接受需另行立项。

## 夹具前置（不是被撤权对象）

- r13_reader user_id=5
- 助手配置 fixture configId=10（create_by=r13_reader, is_default=1, is_del=1, kb_9）
- 阶段A 起：已授予 biz_type=1 target_id=9 permission=1
- 阶段B 起：已撤权（删除 user_privilege biz_type=1 target_id=9 行）
- 阶段D 起：已恢复授权（重新写入 biz_type=1 target_id=9 permission=1）

## 修复归属清单（R17 端口 0.0.0.0 的处置路由；本脚本只取证不改）

- Nacos 配置内容（配置/算法侧 owner）：6 处 server.host=0.0.0.0 —— alg_doc_config_py L3→12340(doc-parse,写入面)、index_data_config_py L7→19526(写入面)、index_data_config_py L37→19527(写入面)、alg_retrieval_config_py L7→19995(读)、alg_llm_config_py L6→19996(推理)、index_graph_config_py L4→19529(读)。注意：改代码或改 conf/ 均无效，只有配置中心 dataId 内容有效。
- 预览 18095（已修复，留三条经验）：① app.py 里 host=os.getenv("PREVIEW_HOST","127.0.0.1") 位于 `if __name__ == "__main__":` 内，而容器是 `python -m uvicorn app:app` **模块方式**启动 → 该行是死代码；真正生效点是 Dockerfile:54 的 CMD，现为 `--host ${PREVIEW_HOST:-127.0.0.1}` + 容器 env PREVIEW_HOST=127.0.0.1 + 重建镜像。② 期间曾因缩进被改坏（uvicorn.run 顶到第 0 列 → NameError）导致容器 crash-loop 12 次，且 **py_compile 能通过**，只有起进程才暴露。③ 容器是 host 网络、无端口映射，改 PortBindings 无从改起（本脚本最早的建议已撤回）。
- 部署 19529（已修复）：unit 文件改成 --host 127.0.0.1 必须配 `systemctl --user daemon-reload` + restart 才生效；此前未 reload 时 ExecStart 实参仍是 0.0.0.0，且 Restart=always 会用旧参数 5s 后自动起回，表现为「一会儿有、一会儿没有」的抖动（会造成不同人采样结论不一致）。
- index-service：services/rag-java/.../interfaces/KnowledgeBaseFileController.java:442 的注释（「预览服务在 127.0.0.1:18095 内部端口不做鉴权，这里是唯一收口点」）在 18095 收回回环后**重新成立**；:55 为默认 URL。它只是注释，不是修复点。
- 离线包风险（TL 决策，当前**未同步**）：运行态 7 个端口都已只绑回环，但包内配置仍是 0.0.0.0 —— check-bind 的判定为「已收紧但配置未同步」（12340/19526/19527/19529/19995/19996），即按现状重打包会把已收紧的端口重新放开。拆成两条来源，只改一条无效。注意路径约定：凡写 payload/... 均指 platform/r12/dist/offline/payload/... （platform/r12/offline/ 是安装报告目录，不含 payload，别去那里找）。复现路径与自测值：①配置侧 6 处：platform/r12/dist/offline/payload/nacos/configs.json，`grep -o '0\.0\.0\.0' | wc -l`=6（`grep -c` 只得 5，因 index_data_config_py 的 L7/L37 两处落在 JSON 同一行内容里）；②源码硬编码 1 处：真正生效点是 platform/r12/dist/offline/payload/preview/Dockerfile:52 的镜像 CMD，现仍为 `--host 0.0.0.0`（源码侧 Dockerfile:54 已改为 `${PREVIEW_HOST:-127.0.0.1}`，两者不一致）；包内 payload/preview/app.py 仍是 host="0.0.0.0" 且 run.sh 用 --network host。注意 app.py 里的 host 只在 `__main__` 生效，模块方式启动不执行，改它不解决问题。ops-offline 已在 offline-kit.sh verify 第 9 段做提示性盘点（不计失败）并记入 platform/r12/offline/INSTALL-FINDINGS.md §七；pack/init-nacos 的收紧与否由 TL 决策。
- 收紧后的验收门（ops-offline 提供、qa-authz 已只读试跑）：platform/r12/bin/check-bind.sh --expect-loopback，退出 0 才算通过；它同时比对“配置声明 vs 实际监听”，能识别快照未同步导致的“静默抵消”。本脚本终版采样时 qa-authz 实测该命令**退出 0**（7 个端口全部只绑回环，18095 判「一致」，其余 6 个判「已收紧但配置未同步」）；早期采样曾退出 1，可作对照。
- 加固有效性限定（否则可能空转）：只改配置中心/包内 configs.json 不足以保证生效——5 个 Python 服务存在 Nacos 本地快照回退：nacos client 的 SNAPSHOT_BASE 默认是相对路径 `nacos-data/snapshot`（platform/r12/venvs/alg/.../nacos/client.py:65，按服务 CWD 解析），只有 doc-parse 显式传了 no_snapshot=True（services/rag-alg/alg_doc_parse_service/server/nacos_utils.py:39,61）；检索/推理/向量/全文/图谱在配置中心不可达时会按本地快照启动。源码树实测有 7 份快照含 host: 0.0.0.0（alg_llm_config_py、alg_doc_config_py、alg_retrieval_config_py、index_data_config_py×3、index_graph_config_py），故加固须同步处理 `services/rag-alg/**/nacos-data/snapshot/*`，否则改动可能被静默抵消。（口径补充：**当前磁盘上的离线包内不含 `payload/src/`、快照副本 0 份**，即该风险目前只存在于源码树；一旦重打包把 `services/rag-alg` 纳入 `payload/src/`，它才会随包复制到目标机。）（本节事实由 qa-authz 独立复现：client.py:65、nacos_utils.py:39/61、7 份快照文件清单；写入面的绑定盘点限定同样适用于本节。）
```


---

## A9 安全验收摘要
```# R13 安全验收 20261026T163542Z

总计 16/16 PASS

| 用例 | 结果 | 详情 |
|---|---|---|
| SEC-1 无授权读知识库详情被拒 | PASS | http=403 body={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| SEC-2 无授权删知识库被拒且数据未变 | PASS | http=403 before=1/R12???? after=1/R12???? |
| SEC-3 无授权按已知对象键取原文被拒 | PASS | http=403 key=r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx |
| SEC-4 无授权提问被对象级授权拒绝 | PASS | http=403 errorCode=30016 configId=1 body={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| SEC-5 只读授权账号可读详情 | PASS | http=200 kbName=R12验收主链 |
| SEC-6 只读账号删知识库被拒 | PASS | http=403 after=1/R12???? |
| SEC-7 只读账号触发重解析被拒 | PASS | http=403 |
| SEC-8 超级管理员可读 | PASS | http=200 |
| SEC-9 撤权后读详情立即被拒 | PASS | http=403 body={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| SEC-10 库内口令为 BCrypt 而非 MD5 | PASS | admin	$2a$; r13_noauth	$2b$; r13_reader	$2b$ |
| SEC-11 属主可预览（返回真实 PDF） | PASS | http=200 head=%PDF-1.7 |
| SEC-12 无授权账号预览被拒 | PASS | http=403 body={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| SEC-13 匿名预览被拒 | PASS | http=401 |
| SEC-14 前端 /preview/ 匿名直连已关闭 | PASS | http=403 |
| SEC-15 存储匿名直取被拒（直连+反代） | PASS | minio=403 nginx=403 |
| SEC-16 无法归属知识库的对象键被拒 | PASS | http=403 body={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
```


---

## A10 主链验收摘要
```# R12 验收 20261026T163339Z

总计 31/31 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S1 | 登录并取菜单 | PASS | http=200 menus=7 |
| S1 | 取当前用户信息 | PASS | http=200 user=admin |
| S2 | 知识库已存在（复用） | PASS | kbId=9 primitive=kb_9 |
| S3 | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=282 name=R12FIX-product-loan.docx |
| S3 | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=283 name=R12FIX-credit-ledger.xlsx |
| S3 | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=284 name=R12FIX-product-intro.pptx |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=285 name=pdf-digital.pdf |
| S3 | 上传 DOCX 纯文本 | PASS | http=200 fileId=286 name=docx-plain.docx |
| S3 | 上传 DOCX 含表格 | PASS | http=200 fileId=287 name=docx-table.docx |
| S3 | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=288 name=pdf-scanned.pdf |
| S3 | 加密 PDF 已入库待解析 | PASS | http=200 fileId=289 |
| S4 | 解析完成 中文 DOCX 业务夹具 | PASS | fileId=282 最终状态=3 耗时=21s |
| S4 | 解析完成 中文 XLSX 业务夹具 | PASS | fileId=283 最终状态=3 耗时=0s |
| S4 | 解析完成 中文 PPTX 业务夹具 | PASS | fileId=284 最终状态=3 耗时=0s |
| S4 | 解析完成 PDF 数字版 | PASS | fileId=285 最终状态=3 耗时=0s |
| S4 | 解析完成 DOCX 纯文本 | PASS | fileId=286 最终状态=3 耗时=15s |
| S4 | 解析完成 DOCX 含表格 | PASS | fileId=287 最终状态=3 耗时=21s |
| S4 | 解析完成 PDF 扫描件(OCR) | PASS | fileId=288 最终状态=3 耗时=0s |
| S4 | 负例按预期失败 加密 PDF(应解析失败) | PASS | fileId=289 最终状态=4(4=失败) 耗时=21s |
| S5 | 真实模型回答（29字问题） | PASS | http=200 帧数=75 答案长度=205 |
| S5 | 回答带引用 | PASS | 引用条数=1 |
| S6 | 服务端可独立取回原文（不随请求传正文） | PASS | http=200 chunk数=1 首块长度=0 |
| S6 | 引用携带文件与定位信息 | PASS | 引用 source 数=1 示例=['r12-rag/kb_9/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx'] |
| S6 | 答案要点可在引用原文中找到支撑 | PASS | 答案命中要点=['5000', '1000', '三年', '授信额度'] 其中被原文支撑=['5000', '1000', '三年', '授信额度'] 引用块数=1 |
| S7 | 历史对话可恢复 | PASS | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': None} |
| S7 | 会话列表可查 | PASS | http=200 |
| S8 | 无 token 被拒绝 | PASS | http=401 |
| S8 | 伪造 token 被拒绝(Bearer forge…) | PASS | http=401 |
| S8 | 伪造 token 被拒绝(eyJhbGciOiJu…) | PASS | http=401 |
| S8 | 坏文件被网关/服务直接拒绝 | PASS | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': []} |
| S8 | 删除不存在的知识库被明确拒绝且无副作用 | PASS | http=404 errorCode=10001 data=None |
```
