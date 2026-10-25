# LLMKE R12 交付报告（真实 RAG 主链恢复）

版本：1.0.0　日期：2026-10-25　分支：`feature/R12-real-rag`　责任人：tech-lead
授权依据：业主 2026-10-25 R12 指令；范围修订见 `docs/baseline/R12-SCOPE-AMENDMENT.yaml`
改造登记：`docs/r12/ADAPTATIONS.md`　环境契约：`platform/r12/R12-ENV-CONTRACT.md`

---

## 0. 结论摘要（先看这四行）

| 维度 | 状态 | 依据 |
|---|---|---|
| **本轮功能验收（R12 主链）** | **达成**（详见 §4） | 32 项自动用例 + 逐场景证据；真实模型/真实索引/真实解析，无 Mock 主链 |
| **五项资源到位** | **到位**（详见 §1-§3） | 源码已入仓、依赖已落到 venv/Maven/容器、四个模型服务实跑、部署制品可复现 |
| **生产 P0** | **未关闭**（保持 OPEN） | 未取得业务政策、真实 DDL、生产环境证据；`make p0-gate` 仍失败，属预期 |
| **独立 QA 签署 / 生产发布** | **未进行 / 未发布** | 本轮为「内部独立复核（非外部签署）」；正式发布需另立 R14 |

---

## 1. 实际使用入口

| 入口 | 地址 | 说明 |
|---|---|---|
| 用户前端（生产形态） | http://127.0.0.1:18088 | nginx 容器 `r12-fe`（host 网络），`dist` 只读挂载 + `/proxy` `/auth` `/index` `/qa` `/minio` 反代；`curl -I /` = 200 |
| 用户前端（开发形态） | http://127.0.0.1:15174 | vite dev server |
| 业务网关（唯一 API 入口） | http://127.0.0.1:8088 | `/auth/**` `/index/**` `/qa/**` `/sensitive/**`（`/graph/**` 见 §5 缺口） |
| 账号 | `admin` / 口令经安全渠道单独交付 | 库内仅存 md5（AES 解密后再 MD5），本轮新建初始化数据 |
| 版本 | 分支 `feature/R12-real-rag`，提交见 §2 表格 | 构建产物：6 个 Spring Boot fat jar + 前端 `dist` |

对外只暴露 8088/18088；模型服务（18090-18093）与中间件均只监听回环或容器内网，**不得直接对外**（A-12）。

## 2. 完整源码与复用路径

### 2.1 原资产（先证明"资产在哪、是什么"）

| 模块 | 原始包（`/home/szf/data/repo/RAG-SRC/`） | 入仓路径 | 规模 |
|---|---|---|---|
| Java 后端 | `gien-rag.zip`（27MB，branch main） | `services/rag-java/` | 1426 文件 |
| Python 算法 | `rag-alg-service-api.zip`（9.1MB，branch dev） | `services/rag-alg/` | 525 文件 |
| 前端 | `ai-plateform.zip`（272MB，branch prod） | `frontend/plateform/` | 2325 文件 |
| 公共组件库 | `mxmodules.zip`（178MB） | **不入仓** | 其产物 `@mxmweb/*`、`@gientech/modual` 已发布在 npm 镜像，前端按版本消费 |

### 2.2 提交序列（本分支）

| 提交 | 内容 |
|---|---|
| `527e1ba` | 三套源码入仓；A-01/A-02/A-03 适配；私有 starter 等价实现；Java 全量构建通过；业务服务可启动 |
| `db413ff` | 上传体积、内部回写端点、知识库空值缺陷、网关放行名单收口 |
| `7d6ebe7` | Office 预处理修复（**中文语料丢失**、PPTX 不可解析） |
| （后续）| 非法 token 500→401、验收脚本强化、部署制品、本报告 |

### 2.3 必要改造（完整清单见 `docs/r12/ADAPTATIONS.md`）

- **A-01** 达梦 DM8 → MySQL 8.4（无 DM 授权实例与驱动）
- **A-02** 内网私有 starter `gien-starter-*` → 本仓等价实现 4 个模块（51 个业务文件零改动）
- **A-03** Nacos 配置中心 → 配置版本化 `application-r12.yml`（Nacos 仅保留服务发现）
- **A-06** 模型独立服务化：bge-m3 / bge-reranker-v2-m3 / Qwen2.5-7B-Instruct / Qwen2.5-VL-3B
- 真实缺陷修复：`R12-FIX-DDL-01/02`（ORM 注解与实际 DDL 冲突）、`R12-FIX-KB-01`、`R12-FIX-UPLOAD-01`、
  `R12-FIX-CONV-01/02/03`、`R12-FIX-AUTH-01`、`R12-SEC-01`

## 3. 部署制品与运行方式

- 编排：`platform/r12/docker/docker-compose.infra.yml`（MySQL/Redis/ES+IK/Milano 见文件/MinIO/etcd/Milvus/Nacos/RocketMQ）
- 配置：`platform/r12/conf/<svc>/application-r12.yml`（口令走环境变量，`.env` 不入库）
- 启停：`platform/r12/bin/r12ctl.sh {start|stop|status}`；模型：`platform/r12/models/start-all.sh {up|down|status}`
- 初始化：`platform/r12/seed/seed_auth.py`（角色/账号/菜单/接口权限，幂等）、`seed_models.py`（4 个模型登记，含真实连通性校验）
- 打包：`platform/r12/bin/build-bundle.sh` → `platform/r12/dist/r12-bundle-<ts>.tar.gz` + `MANIFEST.sha256`
- 安装/健康检查/备份恢复：`platform/r12/README.md`
- **全栈一键启停（按依赖顺序、幂等）**：`platform/r12/bin/up.sh {up|down|status|verify}`
  —— 机器/会话重启后用它恢复（实测：5 个 Java 服务 + 4 个模型 + 4 个算法 + 解析 + 前端全部恢复，主链复跑 31/31 PASS）

## 4. 验收结果（逐场景）

主证据目录：`platform/r12/qa/evidence/<UTC 时间戳>/`（每次运行一个目录：`results.json` + `summary.md` + 各场景原始返回）。
自动用例：`platform/r12/qa/acceptance.py`；独立复核：`platform/r12/qa/qa_suite/` + `QA-R12-REPORT.md`。

| 场景 | 用例 | 预期 | 实测 | 证据 |
|---|---|---|---|---|
| S1 登录 | simpleLogin + 菜单 + 用户信息 | 200 且菜单非空 | 200，菜单 7 条，user=admin | evidence/*/results.json |
| S1 登录 | 图形验证码 | 200 且返回图片 | 200，JPEG 110×40（经网关 8088） | 同上 |
| S2 建库 | 创建知识库 | 200 且模型四项齐全 | kbId 有效，`embeddingModelName=bge-m3`、`modelName=qwen2.5-7b-instruct` | 同上 |
| S3 上传 | PDF/DOCX/XLSX/PPTX/扫描件 | 均 200 并生成 fileId | 5 类全部 200（含 6.5MB 扫描件，413 已修） | 同上 |
| S3 上传 | 加密 PDF | 入库但解析必须失败 | 上传 200；解析 status=4（失败） | 同上 |
| S3 上传 | 坏文件（随机字节） | 明确拒绝或解析失败 | 上传被服务端拒收（`data: []`） | 同上 |
| S4 状态 | 7 个正常样本 | status 99→2→3 | 全部 3（成功），最长 30s | 同上 |
| S4 状态 | 加密 PDF | status 4 | 4（失败），601s（任务超时路径） | 同上 |
| S5 帧状态 | SSE 收尾语义 | `status=2` 为正常结束（1=RUN/2=结束/3=异常） | 实测收尾帧 `status=2` | 同上 |
| S5 问答 | 换措辞提问「我们这种做汽车零部件的中型企业，最多能借多少钱、能借多久？」 | 真实模型流式回答 | 200，SSE 79-111 帧，答案 213-293 字，含 3000万/5000万/3年 | evidence/*/s5_answer.json |
| S5 引用 | 回答带引用 | 引用 ≥1 条 | 1-2 条（xlsx 台账 / pptx 或 docx 产品说明） | 同上 |
| S6 原文 | 服务端独立取回原文 | 不随请求传正文即可取回 | `getFileChunks` 200，内容为**中文完整正文**（459 字） | evidence/*/s6_chunks.json |
| S6 支撑 | 答案要点被原文支撑 | 关键要点可在引用块找到 | 命中 `['5000','1000','三年','授信额度']`，其中 `['5000','授信额度']` 在引用块中逐字出现 | 同上 |
| S7 历史 | 会话/对话恢复 | 200 且数据非空 | `getDialogBySessionId`、`dialogue/list` 均 200 | evidence/*/s7_history.json |
| S8 负例 | 无 token | 401 | 401 | 同上 |
| S8 负例 | 伪造 JWT（alg=none） | 401 | 401 | 同上 |
| S8 负例 | 非 JWT 串（`Bearer forged.token.value`） | 401 | **修复前 500**，修复后 401（R12-FIX-AUTH-01） | 同上 |
| S8 负例 | 未授权访问已收口端点 | 401 | `/index/knowledgeBase/file/list`、`/file/multiple/version` 修复前 200（后者泄漏 SQL），现 401 | 同上 |
| S8 负例 | 查询请求不含正文 | 请求体无 document_texts | 请求体仅 `sessionId/queryId/content/type/configId`，正文由服务端按 file_id 取 | 同上 |

**检索真实性证据**（区别于"字符匹配"）：
- 问句「最多能借多少钱、能借多久」与文档原文「单户最高授信额度为人民币5000万元…期限最长三年」**无相同长串**，仍正确召回；
- 检索侧实测 `search_type=['es','milvus']` 双路命中、RRF 融合、rerank 重排（见 `platform/r12/status/alg.md`）：
  同一候选集仅 ES 通道时，`query='贷款期限规定'` rerank 前 `[100004,100003,100001]` → 后 `[100003,100001,100004]`。

**解析真实性证据**：ES `page_content` 含完整中文 459 字（「智造贷」产品说明书全文）；扫描 PDF 走 OCR
（parse 侧证据见 `platform/r12/status/parse.md`）；表格以 `type=table` + markdown 行列进入索引。

> 说明：`R12FIX-*` 前缀文件是**标注为测试夹具**的构造样本（真实业务文件未提供），
> 报告中一律按夹具标注，不冒充业务验收数据。

## 5. 剩余差距与已知缺陷（不静默缩范围）

### 5.1 R13 及以后必须补齐（功能面）

1. **图谱 / GraphRAG**（指令要求纳入最终交付，R12 未启动）：Nebula 未部署、`rag-graph-service` 无法启动
   （`NebulaGraphPool init failed`）、实体/关系抽取、别名归一化、PPR、社区摘要与全局问答、`19529` 图索引服务未起。
2. **多模态/容量**：VLM 单图 100-450s（load1 相关），20 页扫描件 ≈1.9 小时 → 需后台批处理与容量规划；
   多图文档 C14/C15 仅在高负载窗口外可测。
3. **Office 预览**：本机 LibreOffice 缺 writer/impress 过滤器（无 sudo 安装权限），docx/pptx **无 PDF 预览**
   （正文解析已用原文直读保证保真）。修复路径：安装 `libreoffice-writer/impress` 或改用 remote UNO 转换服务。
4. **.doc（老格式）**：需要 tika-server.jar（未取到），R12 未覆盖。
5. **FAQ / 表格问答 / 多版本 / 数据问答（Text2SQL）**：接口与代码在，但本轮未做端到端验收；
   `remote.faq-*` 到 python 的路径映射仅做静态核对，**未声称已验证**。
6. **数据级权限**：现只有 URL 级鉴权，无文档级 ACL / 属主校验（QA D-04 已登记）。
7. **知识库重命名/多版本**：`/parse/multi_version` 在 python 侧报 `es_config` 已补但 Java 侧无对应端点，功能未闭环。

### 5.2 已知缺陷（本轮未修，已登记）

| 编号 | 描述 | 影响 | 处置 |
|---|---|---|---|
| R12-KNOWN-01 | 解析回写入口 `uploadParsedFile`、`parseTask/callback` 无 token 可达（解析服务不带凭证） | 若网关被外部直接访问，存在索引投毒面 | R13 加内部共享令牌 + 仅内网暴露 |
| R12-KNOWN-02 | `/index/knowledgeBase/file/multiple/version` 曾未认证可达且回显 SQL/表名/列名 | 信息泄漏 | **已收口（现 401）** |
| R12-FIX-API-01 | 部分接口拒绝时仍返回 `success=true`（如删除不存在的知识库 `data=false`） | 语义误导 | 记录，未改（影响面广需 CR） |
| R12-KNOWN-03 | 加密 PDF 失败要等 601s（任务超时路径），失败反馈慢 | 体验 | R13 提前失败 |
| R12-KNOWN-04 | `/create_es_index` 非幂等（已存在返回 500） | 运维风险 | 当前无 Java 调用点，R13 改幂等 |
| R12-KNOWN-06 | **D-04 数据级授权缺失**：非属主账号可 200 读取、200 删除他人私有库文件（`create_by` 只作用于列表层，按 id 直读/直删无校验） | **高危**：具备 index 菜单权限的账号可遍历 kbId/docId 读写全平台文档 | 需产品决策（private_kb+create_by 判定 / KB 级 ACL），R12 不修，**不声称安全通过** |
| R12-KNOWN-07 | 引用装配依赖"模型输出 retrive-tag"：`score_threshold` 过大（0.1）时检索结果被全部过滤 → 无 doc、无 tag、`reference=[]` 且不报错 | 用户拿到无出处答案 | 已把默认配置阈值调为 0.001（实测引用 1-2 条）；"缺失引用应显式降级"登记 R13 |
| R12-KNOWN-05 | 前端 12 条 CSS parse error（@mxmweb/fv Radix leading-trim）+ 60 条 KaTeX 字体未解析 | 预览器行距、公式字体回落 | 不阻塞构建，QA 抽样确认 |

### 5.3 安全缺口（明确声明"未通过"）

- 上述 R12-KNOWN-01 未修 → **本轮不声称"安全验收通过"**。
- 生产 P0（业务政策、真实 DDL、数据合规、密钥托管）**全部保持 OPEN**，未用本轮证据替代。

## 6. 状态区分（四态，不可合并表述）

| 状态 | 结论 |
|---|---|
| 本轮功能验收（R12 主链） | 达成（§4 表；自动用例 + 证据目录 + 独立复核报告） |
| 五项资源 | 到位（源码/离线依赖/真实模型/部署环境/部署制品） |
| 生产 P0 | 未关闭（OPEN，未清空 blocks） |
| 独立 QA / 生产发布 | 未签署（本轮仅内部独立复核）/ 未发布 |
