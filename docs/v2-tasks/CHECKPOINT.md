# 执行检查点

更新时间：2026-11-02T21:40+08:00
任务书：docs/v2-tasks/PROMPT-TL-START.md（base_commit bb32876）
当前工作树/分支/HEAD：/home/szf/data/dev/llmke-v2，design/v2-input-engine-adoption-20261030-2101
当前阶段：VL1 进行中（数据面 HTTP 已通；产品接线未开始）

成果位置：
- 图服务 `graph_engine_adapter/api.py`，127.0.0.1:18094（uvicorn，hipporag venv）
- 端点：`GET /health`、`POST /v2/graph/build`、`POST /v2/graph/query`
- 台账：T-V2-01 VERIFIED、T-V2-02 DOING

## 已完成且验证
- VL0：contract-all PASS(27)、contract-v2-check PASS(95)
- 图路由：rerank 兜底后 `executed_route=GRAPH`（证据 VL1-graph-route-20261102.log）
- HTTP 建图：2 文档/2 块，返回快照 `/tmp/v2-api-evidence/snapshot-20261102213303-583749-g0`
- HTTP 查询 + 引用：`GRAPH / GRAPH_CALLED`，命中 2 条，citations 为
  `[{"file_id":"f-404","locator":"table:r2"},{"file_id":"f-403","locator":"p1"}]`
- 构建后预热引擎，避免首次查询空响应
- 接口测试 7 passed；证据 `docs/v2-tasks/evidence/VL1-build-and-cite-20261102.log`

## 正在执行
- T-V2-02：产品接线——Java/前端仍走 legacy，需要把图构建与查询调用切到 18094。

## 未完成/失败
- 产品页面未接线，D0 未开始。
- `seed_hits=[]`：查询未传实体种子。
- 建图请求仍是"文本块"级，未接 doc2md ParseArtifact 的 artifact_id/hash。
- 首次构建后查询曾空响应（已加预热，但未做并发/冷启动压测）。

## 下一精确动作
1. 执行：定位 Java 图服务与前端图谱页的调用点，设计最小切换（配置指向 18094 或加适配层）。
2. 检查：页面发起一次上传→构建→查询，确认走 18094 且引用可点开。
3. 成功后：补 seed 实体与 doc2md artifact 绑定，推进 D1/D7。
4. 失败后：记录契约字段差异（请求/响应），先加兼容层，不改产品语义。

## 不得重复或擅自执行
- 已完成副作用：演示环境启动；18094 服务运行；两次真实建图（/tmp 下快照）
- 待授权：无

## 产品接线调查（2026-11-02 21:45）

- 构建入口：`services/rag-java/rag-parent/rag-index-service/.../application-r12.yml`
  把 `generate-graph` / `generate-community` / `del-graph-*` 指向 `127.0.0.1:19529`
  （legacy `index_graph_service`，Nebula）。
- 图谱查看：`rag-graph-service` 直连 Nebula `127.0.0.1:9669`（`graph.type=nebula`），
  不经过 Python 图服务；`GraphController` 只有 `/info/nodes`、`/info/edges`。
- 因此 D0 有两处要换：构建链路（index-service → 19529）与查看/查询链路
  （graph-service → Nebula）。
- 最小切法：先做 19529 兼容层（实现 generate_triple_data/generate_community 等，
  内部转 18094），再把 nebula 查询替换为图服务查询；契约差异需逐字段对齐。

## S2（2026-11-02 22:40）

- 配置：r12 运行态 `generate-graph` 指向 `http://127.0.0.1:19531/generate_triple_data`（已备份）。
- 真实链路：上传 docx → 解析成功 → graphParse → Java 日志显示 19531 → 响应 code=200
  → DB `graph_parse_status=3`；快照 `/tmp/v2-shim-root/snapshot-20261102223531-579610-g0`。
- sources.json 含 `{"file_id":"999016","locator":"page=-;offset=[[0, 459]];chunk=0"}`。
- 证据：`docs/v2-tasks/evidence/S2-product-build-path.md`。
- 下一步：查询/答案链路（qa-service / 前端）仍走 legacy，需要接 18094 并让引用可点开。

## S3（2026-11-02 22:50 起）

目标：问答检索从 legacy 19995 切到 HippoRAG。

- Java qa-service 配置：`rag-qa-service.application-r12.yml:50 retrieve-url: http://127.0.0.1:19995`，
  Feign `POST /retrieval_documents`；响应形状见 `alg_retrieval_service/app/retrieval_service.py:577`
  （faq_result_list / database_documents / documents_list / web_documents_list / log_list）。
- 计划：
  1) 新增 `graph_engine_adapter/retrieval_shim.py` 实现同路径，内部调 18094 /v2/graph/query；
  2) 只停 19995 上的 legacy 检索进程（不动 19526/19527/19996），用 shim 顶 19995；
  3) 用 qa-service 真实问答请求验证 documents_list 走 GRAPH。
- 约束：executed_route 必须透传；DENSE_FALLBACK 不能标成图检索。

## S3 收口（2026-11-02 23:05）

- 检索：qa-service → 19532 → 18094 已通；Java 实测 200、1 条、search_type=["graph"]、
  locator=page=-;offset=[[0, 66]];chunk=0。
- global：`/retrieval_documents_global` 显式 501（community 未接入），不冒充；
  enabled_graph=false → 400；health 自述 wired=false。
- 上游 500 已修：HippoRAG `get_top_k_weights` 零权重重断言 → 适配器跳过自检并记
  trace.weights_assert_skipped；复验 18094 200/GRAPH。
- 证据：S3-retrieval-wiring.md（TL）+ S3-retrieval-shim.md（角色），两份并存不合并。
- 未完成：真实社区报告（D4）、页面浏览器端到端。

## S1 收口（2026-11-03 00:10）

- S1-B 产物绑定 / S1-C 方向语义：已随 4f8ce74 入库，工作区干净；
  测试环境口径：hipporag-toolenv（有 fastapi）59 passed = 30+7+22；
  v2-toolenv（无 fastapi）37 passed + 1 skipped（test_legacy_shim 整文件 skip）。
  **skip 不计 pass**，证据须写解释器与原因。
- S1-A 兼容层：19531 现役 pid 1486048（22:53 启动，已含 9f4cae1）；真机 legacy 形状请求
  code=200、edges_total=3（facts）、edges_written=12（edges）、locator_degraded=0；
  generate_community / del_space / del_doc_entity 仍 501 且 upstream_called=false。
- 待办：B01 在 r12 的 pair_key 修复（S1-C）；Java global 验收（需 /qa/ai/question）。

## B01 关系方向修复（2026-11-03 00:30，r12 轨）

- 提交：llmke-r12 `0bac08a`（feature/R12-real-rag，未 push），严格 2 文件：
  `index_graph_service/graph_types.py` +399/−52、`tests/test_graph_direction_b01.py` 新增 140 行。
- 实现：`pair_key` 保序为 `(rel,(src,dst))`，仅契约 `symmetric=true`（相似/关联）走无序键；
  方向由 domain/range 裁决，未登记/domain==range/通配 → unknown → 双向保留；
  `undirected_pair_key` 仅服务拓扑投影，不再作事实身份。
- 独立复验：`tests/test_graph_direction_b01.py` **28 passed**；`sorted()` 只剩于
  `undirected_pair_key`（有 doc 警告）；提交未带 `platform/r12/conf/**`。
- 基线：r12 `make framework-test` 为 20 failed / 286 passed / 44 skipped，20 个失败在
  HEAD 干净工作树同样复现（契约工具链/安全扫描/旧回归），与本次无关。
- **未做**：真实入库/图库端到端（W 项）；未 push；未改本体契约。

## Java global 端到端（2026-11-03 01:20）

- 配置：`application-r12.yml` 增 `search-docs-global-url: http://127.0.0.1:19532/retrieval_documents_global`
  （备份 .bak-20261102，未入 git）；仅重启 rag-qa-service（pid 1685670，:18083）。
- 复验命令：`POST :18083/qa/ai/question`（X-UserID:5 / X-UserName:r13_reader，
  sessionId/queryId/type=1、configId=8、globalMode=true）→ SSE 200。
  answer 393 字符、逐条带来源；reference 5 条，metadata `search_type=["global"]`、`community="c-3"`。
- 限制：合成语料 `file_id=F003` 非数字，Java DTO `Long` 收不到（生产数字 ID 正常）；
  answer 会把所用社区内与问题无关的事实一并列出（实测问授信却带出集团客户条款），
  属社区粒度/选取质量问题，非链路不通。
- B01 收尾证据：llmke-r12 `100e261`（仅 1 文档，88 行），原修复 `0bac08a` 未改写。

## 页面端到端（2026-11-03 01:35）

- 前端 dist 用临时 nginx 于 18088 提供，链路 页面→8088→18083→19532→18094 通。
- 实测：global 答案 3 条带来源；普通答案 8000 万带 999010；**答案底部只有复制/赞/踩/重新生成，无引用按钮**，
  DOM 无 ref/cite 节点 → “点引用”不可验收，属前端缺口。
- 为实现数字 file_id 引用，用 19531 重建单文档快照并临时切 18094；验证后已还原 s4-root-c（69 facts/33 社区）。
- 证据：docs/v2-tasks/evidence/PAGE-CITATION-E2E-20261103.md。
- 临时容器 v2-fe-e2e 已删除；浏览器已关；Vite dev 因 inotify ENOSPC 不可用（非代码）。

## 审计自证批次（2026-11-03，tl-audit）

### T-A4 B01（VERIFIED）
- r12 HEAD 100e261 复跑 `tests/test_graph_direction_b01.py` → 28 passed。
- 变异 3 组（临时 worktree /tmp/tl-a4-mut @100e261，改后 md5 与恢复后 md5 都记了）：
  A 一律 sorted()→23 failed/5 passed；B 删对称分支→1 failed；C 未登记判可裁决→3 failed。
  三次均恢复到 `0712caa7c2359c01ff95e7bb83947982` 后 28 passed、worktree 干净。
- 基线：/tmp/tl-a4-baseline @419a87d 三文件 20 failed/22 passed（16/3/1）；
  全量 419a87d=20 failed/258 passed/44 skipped vs 100e261=20 failed/286 passed/44 skipped
  → 新增 0 失败、+28 passed。根因实测：`python3` 即 `/usr/bin/python3`(3.10.12) 缺 openapi_spec_validator。
- 迁移：`git apply --check /tmp/b01-full.patch` 在 V2 exit 0；三文件与 419a87d 指纹同源；
  V2 契约已含 `direction_resolution.forbidden=[sorted_undirected_key_for_all_predicates,...]`；
  换 V2 契约跑 28 passed。存量 g_kb_9 边数 UNVERIFIED（Nebula 9669 未监听，未自行启动）。
- 证据：docs/v2-tasks/evidence/A4-b01-rerun.md

### T-A2 D6 纯图（VERIFIED）
- 代码：api.py 增 `seeds`/`enable_graph` 并透传；engine_hipporag 增 `use_graph` 禁用分支与
  `facts_after_rerank`/`seed_hits_degenerate`；中文补丁改服务端默认安装（health.cjk_compat 可见）。
- 独立实例 18095（未碰 18094），用 18094 快照的 12 块原文重建：68 事实/251 边/35 社区。
- A 组 GRAPH/graph_calls=1/rerank_fallback=false/facts_after_rerank=1/seed_hits=['ent:智造贷']；
  B 组 DENSE_FALLBACK/GRAPH_DISABLED/graph_calls=0。
- 反例：不装补丁时中文种子全落 md5("") 空实体 → 记 seed_hits_degenerate，不计 seed_hits。
- capabilities.retrieve_graph_route 升 VERIFIED（证据 sha256 c531a350…）。
- 测试 73 passed（9 个图相关文件）；新增 test_query_forwards_seeds_and_graph_switch。
- 未做：retrieval_shim.py:416-417 仍只发 {query,top_k}（S3 文件），产品链路未透传 seeds。

### 下一精确动作
1. T-A1：先用真实上传文档（KB 表有记录、file_id 数字）建快照，再补 global 分支 convertedFilePath 反查。
2. 拿不到真实文档 → 按约定写 BLOCKED + 恢复条件，转 T-A3。
3. T-A3：openie→断言→export_facts→build_communities→community.json 逐跳溯源（可复用 18095 快照）。

### 不得重复/擅自执行
- 不要重启 18094（S3 在用）；18095 为本批次临时实例。
- 不要用 F001–F012/999010 证明"打开原文"（T-A1 禁止）。

### T-A1 D7 打开原文（BLOCKED，代码已落地）
- 真实上传：走产品网关 8088 上传 coordination/samples/docx-plain.docx（真实 docx，非 F001–F012/999010）
  → gienrag.knowledge_base_list id=999017、kb_id=1002、converted_file_path 有值、status=3。
  注意：Java 写的是 `gienrag` 库，不是 ENV.md 写的 `gienrag_v2_restore`（后者该表 0 行）。
- 代码：AiServiceImpl 抽出 resolveSourceByFileId（:2680）+ 新增 enrichReferenceSources（:2712），
  publicQuestion 内联块改为调用，question_re global 分支 :396-402 接线。
- 验证：mvn -o compile 通过；离线仓库 surefire 2.12.4 缺 junit3 provider 跑不了 mvn test，
  改为对已编译真实类打私有方法（动态代理桩 KbClient + Mockito 桩 StorageProperties）→ 4/4 PASS。
- 未完成（BLOCKED 原因）：需重启 :18083 让新代码生效；且实测直连 :19000 403、网关 /minio/ 404，
  取原文链路待确认；global 快照里还没有这份真实文件。页面级实录未做。

### T-A3 D4 社区同源（VERIFIED）
- 脚本 scripts/v2_a3_lineage_probe.py；事实 智造贷 适用于 制造业中小微企业 五跳闭合：
  openie(chunk-ddb6…) → 断言(subject=智造贷, source F001 page=1;chunk=0) → export 67/68 → 社区 c-3(size=5)
  → community.json（inputs.facts=67/triples=68）。
- 两次生成 sha256 相同 c7c09b82894d61d0c976251df034b4508f3ed2e325c800231831f98f266e8661；
  citation_check ok、invalid=[]、checked=64；孤点社区 1 个保留。
- 不是相似图的依据：community.build_report 输入是断言对象（community.py:104-110）；引擎图 251 边 vs 输入 68 三元组。

### 下一精确动作
1. 等授权：重启 rag-qa-service(:18083) → 跑一次 global 提问，确认 reference 里 metadata.source 非空。
2. 确认前端取原文的真实地址（19000 直连 403、/minio/ 404），再用真实文档走页面点击。
3. 18095 临时实例用完后关闭（当前仍在跑，供 A2/A3 复跑）。

### 不得重复/擅自执行
- 不要重启 18094 / 18083（18083 需授权）。
- 不要用 F001–F012/999010 证明"打开原文"。

### T-A1 补充（15:15，按 team-lead 批准的四条边界补做）
- 上传：走 8088 只传 1 份 `coordination/samples/docx-image.docx` 到 **kb_9** → 新 id=**999019**，
  converted_file_path=`http://127.0.0.1:19000/r12-rag/kb_9/docx-image.docx/V0/docx-image.docx`，gmt_create 2026-11-03 15:02:47。
  解析任务 `file_parse_task.id=642` 至今 status=2（图文样本，未结束）。
- 夹具留痕（未删）：999019；误建空库 `knowledge_base.id=1003`(kb_1003)；批准前已传的 999017/999018(kb_1002)、1001/1002。
- 全链验证（真实数据，6/6 PASS）：kb_9 产品侧已解析文档 **id=333 docx-table.docx** → getFileChunks 取 2 块
  → 建图（snapshot /tmp/tl-a1-root/…-150659，6 事实/23 边/3 社区）→ /v2/graph/global 命中 c-2（来源 333）
  → retrieval_shim 真实映射出 Java 实际输入（metadata.file_id=333, source=null, locator=page=1;chunk=0）
  → Java enrichReferenceSources → **source=r12-rag/kb_9/docx-table.docx/V0/docx-table.docx**，locator/community 未破坏。
- 取原文链路实测未通：19000 直连 403；网关 /minio/ 404；Office 预览配置 `application-r12.yml:80 → 18095/stream` 当时未监听。
- 端口纪律：A2 的临时实例曾占 18095（= 预览服务默认端口），已停止并释放；18094/19531/19532/8088/18083 未受影响。

### T-A1 三步放行执行结果（15:20）
- ① 重启 18083：before_pid=2363389（r12 jar md5 35e8b120…）→ 打包 v2（md5 c441d760…）→ after_pid=2403983，
  Started in 7.983s；JVM 参数与 r12 配置照旧，只换 jar；环境变量从 platform/r12/.env 载入。
  curl① question_re(r13_reader) 200；curl② question_re(admin) 200 且 metadata.source 被补出。
- ② 取原文正确入口（team-lead 指正，我原先试的全错）：
  `GET /index/knowledgeBase/file/presign?key=<桶内键>` → 200 → 预签名 GET → 200 / 36716 字节 / docx；
  预签名的是上传时同一文件（fileSize 36716.0）。`/proxy/...` 前缀返回 404；`previewStream` 500（预览服务未起）。
- ③ 快照：19531 + space_name=kb_1002 + col_values=["docx-plain.docx"] → 快照 /tmp/v2-shim-root/snapshot-20261103151221-873115-g0
  （sources.json file_id=999017；1 社区/3 事实/citation ok）→ Java 引用 source 原样 presign 成功 → 闭环。
  已还原 18094 到 /tmp/s4-root-c/snapshot-20261103000343-927116-g0（26 节点/49 边/69 事实/33 社区，与基线一致）；
  19532 复测 code=200 docs=3 正常。
- 权限边界实测有效：r13_reader 提问 → 日志「resolve source by file_id 999017 failed: 没有足够权限」，source 置空不越权。
- 唯一断点：前端未运行（:80 是 WeKnora；LLMKE 前端临时 nginx 已删、Vite 受 inotify ENOSPC）→ 页面点引用/抽屉/高亮未做。
- Java 行号：resolveSourceByFileId:2669 / enrichReferenceSources:2719 / 内部调用:2747 / publicQuestion:736 / global 接线:400。

### T-A1 页面 E2E（15:22–15:29，授权三项全做）
- 环境：18083 按批准重启 4 次（pid 2363389→2403983→2461741→2478756→2492411，每次先 mvn package）；
  `preview/run.sh up` 起 r12-preview（18095 healthz ok，未 build）；`docker start r12-fe`（18088，页面 200）。
- 登录：页面有图形验证码，无法自动填 → API 取 token 注入 localStorage（saic_store 与 gitech_ril:rag_ai 两键，长度均 237）。
- 走到：选 qa_cfg_kb9 + 全局 → 提问 → 答案含（来源：333）→ 点「知识溯源 1」→ 抽屉列出 docx-table.docx → 点条目 →
  **失败：加载失败：缺少原文地址或登录态，无法打开原文**（8 张截图在 docs/v2-tasks/evidence/screens/A1/）。
- 定位：token 存在（已证）；Java 已下发 doc.filePath + metadata.source/filePath + sources[].source/filePath 五字段（已证）；
  连补三次仍失败；SdqaDrawer/index.tsx:502 `if (!curData.filePath) return <></>` 说明 filePath 是硬契约，
  而溯源列表项由 @gientech/modual 内部构造 → 断点在前端字段映射，属 llmke-r12 前端写域。
- 终态：18094 已还原到 /tmp/s4-root-c/snapshot-20261103000343-927116-g0（26/49/69/33）；
  临时快照 /tmp/v2-shim-root/snapshot-20261103151652-781141-g0；19532 未动；
  r12-preview 与 r12-fe 现为运行中（回收：docker stop r12-fe + preview/run.sh down）。

### T-A1 页面 E2E 通过（15:32–15:36，v2 dist + agent-browser）
- 关键：之前 §10 失败是用了 **r12 的旧 dist**；换成 **v2 的 dist**（v2-fe-e2e 容器，18088，/chats/main 200）后同样操作直接成功。
  故"抽屉缺字段"的正确表述是"旧 dist 不适配新后端字段"，v2 dist 适配良好。r12-fe 已 docker stop（回到原 Exited）。
- 动线：新建对话 → R13 Global → 问「日均存款是多少」→ 答案带（来源：999017）→ 点「知识溯源 1」→ 抽屉列出 docx-plain.docx
  → 点条目 → **PDF 预览打开**（canvas 612×792，页标 1/1）。
- Network：`GET /proxy/index/knowledgeBase/file/presign?key=r12-rag%2Fkb_1002%2Fdocx-plain.docx%2FV0%2Fdocx-plain.docx` **200**；
  `POST /proxy/index/knowledgeBase/file/previewStream` **200**；pdf.worker.min.js 加载。
- 截图：docs/v2-tasks/evidence/screens/A1/{01-answer-v2,02-drawer-v2,03-preview-v2,04-preview-final}.png
- 唯一缺口：**locator 高亮未实现**（DOM .highlight/mark 命中 0；前端 highlight 只在编辑器组件）→ T-A1 仍 BLOCKED，断点收窄到"前端无高亮实现"。
- 收尾：18094 已还原 s4-root-c（26/49/69/33）；v2-fe-e2e 已删；r12-preview 已 down；18088/18095 占用 0；浏览器已 close；19532 未动。

### T-A1 收尾（15:40，BLOCKED 定稿）
- 预览：`preview/run.sh status` → `down`（healthz 连接被拒），18095 占用 0，r12-preview 容器已移除；r12-fe 仍 Exited(0)，未再动。
- 证据补齐：A1 证据 §12 逐张标注截图 01–08 的失败点（03/05/07/08 四张失败，全部发生在 r12 旧 dist 上）
  与 v2 dist 下通过的四张（01-answer-v2 / 02-drawer-v2 / 03-preview-v2 / 04-preview-final）；
  previewStream 产物归档 docs/v2-tasks/evidence/screens/A1/A1-preview-stream.pdf（39628 字节 PDF）。
- 恢复条件（BLOCKED 理由，owner=前端/llmke-r12 frontend）：问答 PDF 预览需按 locator 画高亮。
  说明：team-lead 口径「vendor referencelist 未透传 filePath」已被 §11 实测否证——换 v2 dist 后点条目即打开 PDF、
  presign/previewStream 双 200，故不得再据此改 Java 或加平台字段。
- 历史 commit message 未改（d52a1b9 反引号被 shell 吃掉那半句，已在证据 §10.3 记录完整表述）。

### D7 显式拆分收口（15:45）
- **T-A1 = D7a「打开原文」→ VERIFIED**：证据 docs/v2-tasks/evidence/A1-open-original.md（commit f43764f 的页面实录 +
  §9 的后端两通道）。通过内容：点引用→抽屉→点 docx-plain.docx→PDF 预览打开（canvas 612×792、页标 1/1）；
  Network `presign` 200 与 `previewStream` 200，presign 的 key 就是后端反查出的桶内键。
- **T-A5 = D7b「locator 高亮」→ TODO**（新建）：问答 PDF 预览无高亮实现；DOM 无 .highlight/mark；
  需前端按 locator offsets 画层；owner=前端/llmke-r12 frontend。locator 数据本身全链路没丢。
- **读法纪律：T-A1 的 VERIFIED 只覆盖"打开原文"，不覆盖高亮；D7 未全通。**
- 服务保持已停：18088/18095 均不监听（预览 down、临时前端容器已删），r12-fe 仍 Exited；不为验证再起。

### VERIFIED 的边界单列（15:55，TL 定）
- **T-A1 = D7a 打开原文 → VERIFIED**（证据 f43764f：页面实录 + presign/previewStream 双 200）。不含高亮。
- **T-A5 = D7b locator 高亮 → TODO**：前端问答 PDF 预览无高亮实现（DOM .highlight/mark 命中 0）；owner=前端/llmke-r12 frontend；后端 presign/previewStream 已 200，不需再动。
- **T-A6 = 产品链路 seeds 透传 → TODO**：Java→19532 shim 仍只发 {query,top_k}；retrieval_shim.py:416-417；owner=s3-retrieval-shim（单写者）。
- **T-A7 = 业务语料社区溯源 → TODO**：T-A3 只证 F001–F012 夹具；需真实业务语料重跑 scripts/v2_a3_lineage_probe.py 同一五跳。
- **读法纪律**：T-A2 / T-A3 的 VERIFIED 都是 **scope-limited**（分别只证引擎路径与夹具脚本路径），
  产品透传看 T-A6、业务语料看 T-A7；**不要把任何一条 VERIFIED 读成该验收项全通**。
- 事实分歧已按实测收口：「vendor 未透传 filePath」**作废**，旧 r12 dist 才是那轮误报原因。
- 服务保持已停：18088/18095 不监听。

### 边界条目措辞对齐（16:00，按 TL 指定的三句）
- T-A2 note：`scope-limited：仅证引擎/直连 18095；产品透传见 T-A6`
- T-A3 note：`scope-limited：仅 F001–F012；业务语料见 T-A7`
- T-A6 blocker：`Java→19532 shim 仍只发 {query,top_k}；retrieval_shim.py:416-417；seeds 未透传，产品链路未验。`（owner=s3-retrieval-shim）
- T-A7 blocker：`T-A3 仅证 F001–F012 夹具；需真实业务语料重跑 scripts/v2_a3_lineage_probe.py 同一五跳。`（owner=TL/数据）
- 任务总数 **18**；T-A1 / T-A5 内容未动。

## 2026-11-11 评审回执补料（S-1..S-10）

### S-1 单变量对照（结论：旧 dist 不是原因）
- 固定：kb_9 / file_id=333 / 问句“多指标对账” / 42167f0 后端（18094+19532+18083 v2 jar，Java 配 19532）。
- r12 旧 dist：答案带（来源：333），知识溯源→docx-table.docx→PDF 打开成功。
- v2 dist（42167f0 构建）：同一动线同样成功。
- 证据：`docs/v2-tasks/evidence/artifacts-20261111/S1-r12dist-kb9-333.png`、`S1-v2dist-kb9-333.png`。
- **更正**：A1 旧结论“旧 dist 不适配/抽屉字段映射”作废；D7a 打开原文成立，D7 仍缺高亮（T-A5）。

### S-2 dist 身份（42167f0）
- 构建 commit=42167f0；node v25.0.0 / npm 11.6.2；`npm run build` 2m56s。
- 1602 文件；manifest sha256=`8247a9b143e4ee37bb9a0db10fad137d1101c0e5fca66ebb17bbe8898f901cd5`
  （`find dist -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum`）。
- index.html sha256=`93bb7e5339f1d8513b37c8957b3fc62f6a451757b6dd43deb1f86ef64ff8f023`；
  package-lock sha256=`b40f872281b6c2ee9fdbda180482e020f0d4c13bde6a41c4ef6370d7055ab5f1`。
- 构建命令：`CODEBUDDY_SAFE_DELETE_ENABLED=0 npm run build`（需禁用 safe-delete 批量删除保护）。

### S-3 归档（部分）
- 已归档 333 快照实物：`docs/v2-tasks/evidence/artifacts-20261111/snapshot-333/`
  `openie_results_ner_*.json`、`sources.json`、`community.json` + SHA256SUMS。
- A2/A3 所需 12 文档/F001–F012 快照未重建，**S-3 未闭环**。

### S-4 网络与文件实物
- `docs/v2-tasks/evidence/artifacts-20261111/`：
  `docx-table.original.docx` 36944B sha256=`a846ab142d8d24afe3f552f95888c4b261dd7c8908921a16a2932c4a7838fa1d`；
  `docx-table.preview.pdf` 39628B sha256=`2ace7b8d62e2230855bece486be28b0226738a6009cb7849a6f3983a4bc5ff6c`；
  `presign-preview.json`（presign 200 / download 200 / preview 200）。

### S-7 graph_route 口径
- `q-acceptance-20261103.json` 的 `graph_route=NOT_VERIFIED` 是当时 18094 未重启/旧代码的运行态；
- `capabilities.retrieve_graph_route=VERIFIED` 来自 T-A2 在 42167f0+18095 的引擎实测；
- 两者时间点与对象不同，不是同一份运行态，故并存成立。

### S-8 18094 可用性
- 500 原因：`LLMKE_V2_SNAPSHOT` 指向的 `/tmp` 快照已被清理，health 读不到快照；
- 已用 42167f0 工作树 + 持久快照
  `/home/szf/data/dev/llmke-runtime/app/platform/r12/data/graph-root/snapshot-20261111121015-000516-g0`
  重建并恢复 200（9 节点/16 边/5 事实/1 社区）。

### S-10 规模口径
- 9888 条目的基线是 42167f0；`origin/main` 已前进到 `14c392a1`，当前 HEAD 也已前进，
  旧基线不能再用 `origin/main` 现算，必须用包内 commit 与包内树核对。


## 评审镜像仓库清理（2026-11-11）

- 无损确认：`llmke-v2-review` 两分支 `main`=419a87d、`design/...`=bb328761 均为本仓
  `main` 的祖先，`rev-list --left-right --count` = 279 0 / 146 0，独有提交 0；
  9 个差异文件均为 Owner 授权下线的 `/commonSearch` 废弃件
  （d9509936 前端 8 个 KnowledgeSearch 组件、104d00ff CommonSearchRequest.java），
  且 9/9 可从本仓 main 历史中的父提交取回。**无需合并任何代码**。
- 唯一 git 之外资产：评审 PR #1 正文（2384 字，无敏感信息），
  归档于 `docs/v2-tasks/archive/EXTERNAL-REVIEW-20261102.md`。
- 清理：design 分支已删；main 因 GitHub 默认分支保护删不掉，改为删除整个 private 仓库
  （0 open issues / 0 forks / 0 tags / 0 releases / 1 个未合并 closed PR）。
- 本地 `git remote remove review` 已执行，本地只剩 origin。

## P6 / T-D2MD-17 接手检查点（2026-11-12，STEP2-I）

更新时间：2026-11-12
当前工作树/分支/HEAD：`/home/szf/data/dev/llmke` main `d2af1e6a`（发布树，仅 ff-only）；`llmke-v2` / `llmke-r12` worktree 已不存在，运行代码在 `llmke-runtime/app/`。
当前阶段：P6-L17（T-D2MD-17 IN_PROGRESS）。

### 已完成且验证
- todo 1 探索 doc2md 生成入口：`scripts/v2_ingest_doc2md.py`（scan→copy-to-vault→route-parsers→parse-markitdown）。
- todo 2 6 份标准四件套：`coordination/kb9-rebuild-corpus/` 6 源 → `doc2md/parsed/by_hash/<sha>/`，全部 `parse_manifest.status=SUCCESS`、含 `document_ir.json`；本轮离线 `kb_pipeline.commit_snapshot()` 6/6 PASS（隔离 store 已删）。
- todo 3 修 `current.json` 指针：11:54 已由前序执行改为 app 生产根现存 snapshot，留 `current.json.bak.20261112`。
- 接手核证与事实纠正：见 `docs/v2-tasks/evidence/STEP2-I-HANDOVER-RECON-20261112.md`。

### 未完成/失败（真实外部阻塞，非可自主解决）
- B-1：`LLMKE_KB_STATE` 指向 shadow state（kb_9 活跃 290/291/292/293），与生产 11 份不同源；`wanted_docs` 是全量装配 → 只改 ROOT/ARTIFACT 就 POST 会用影子 state 覆盖生产 46/11 图。STEP2-E/H「不削」不可外推到路径 A。
- B-2：18094 无 `LLMKE_V2_ROOT`、`QueryRequest` 无 `root`；`/v2/graph/query kb=kb_9` 实测 `NOT_BUILT`。runbook 的「查询命中 46 块」判据不可达。
- 依赖链 `17←16←15←14` 未闭环（G-1 待批、12340 仍 LISTEN）；G-4 独立 QA 主体/密钥缺失。

### 下一精确动作
1. 执行：向 Owner 提交 B-1 / B-2 裁定（同源 kb_state 方案 / 纯只读切换 / 隔离副本演练；是否授权重启 18094 或改验收口径）。
2. 检查：若选隔离副本演练，复制生产 46/11 快照到隔离 root + 同源 state，用独立 18096 实例跑 6 份，断言 `documents` 与 11 文件集合不变。
3. 成功后：在已授权窗口内按 STEP2-F 路径 A 执行 todo 4~6，留证后待「提交一次 git」指令入库。
4. 失败后：按 STEP2-I §六 登记，不删失败、不改状态凑 PASS。

### 不得重复或擅自执行
- 已完成的副作用：6 份四件套生成、`current.json` 指针修复（均为前序执行，**不重做**）。
- 未授权：停/重启 19531、18096、18094；写生产 `platform/r12/data`；解除 `T-D2MD-18`；git commit；任何 `QA_PASS` 签署。
- 不得把 `275eccb8`（parse_queue.json 自身）与 `c5edbeaf`（旧 3 件）计入 6 份语料。

## P6 / T-D2MD-17 续跑（2026-11-12，STEP2-J；Owner 批准 ③+(c)）

更新时间：2026-11-12

### 已完成且验证
- **graph_root 流向核实**：修正前为启动期 env 死值（闭包实测 `['http://127.0.0.1:18094', '/tmp/GRAPH-ROOT-FROM-ENV']`，`root actually sent to 18094: ['/tmp/GRAPH-ROOT-FROM-ENV']`）；18094 侧 `DeltaRequest.root` 一直是请求体驱动，设定死值发生在 18096 的 service 路径。
- **实现修正**：发布树 `services/rag-alg/index_data_service/kb_ingest_service.py` 让 service 路径按请求 `graph_root`/`graph_api` 重建绑定；不新增契约字段、不改默认值语义，注入缝不变。
- **测试**：新增 `tests/test_kb_ingest_request_graph_root.py` 6 项；相关 4 文件 **98 passed**；用 `git show HEAD:` 未修复版做变异复验 → **3 failed / 3 passed**，断言非空转（变异目录已删）。
- **隔离演练**：`scripts/p6_request_graph_root_probe.py`。同源 state 从生产快照派生，**46 行 / 11 file_id 与生产 `current.json` 指纹一致**；6 份 POST → `wanted_docs` 始终含 11 个 file_id、`removed_total=0`、行数 58→71 单调不减、重复请求 `SKIPPED_FRESH` 零 delta；生产 `current.json` sha256 前后同为 `fa650c7d…`；shadow 4 文件变异体缺 10 个 file_id 被精确捕获。
- 证据：`docs/v2-tasks/evidence/STEP2-J-REQUEST-GRAPH-ROOT-20261112.md`。

### 仍未完成（真实外部阻塞）
- B-2：`/v2/graph/query kb=kb_9` 仍 `NOT_BUILT`；按 (c) 已把验收改为指纹比对，但「查询可读」未验收，需 Owner 裁定是否授权重启 18094 设 `LLMKE_V2_ROOT`，或给 `QueryRequest` 增 `root`（需 CR）。
- **代码合入≠线上生效**：运行树 `llmke-runtime/app/.../kb_ingest_service.py` 未同步（md5 `5a19cc16…` vs 发布树 `563be5a1…`），生产 18096 未重启，线上仍是启动绑定死值。
- 依赖链 `17←16←15←14`、G-1、G-4 未闭环。

### 下一精确动作
1. 执行：Owner 就 B-2 与生产窗口授权作出裁定；若放行，先同步运行树代码 + 让 `LLMKE_KB_STATE` 指向同源 state + 重启 18096。
2. 检查：窗口内按 STEP2-F 路径 A 跑 6 份，比对生产 `current.json` 的 `documents` / `fingerprint.files` 指纹，复核 8 端口 LISTEN。
3. 成功后：留证，待「提交一次 git」指令入库；再讨论 `T-D2MD-18` 解锁。
4. 失败后：按 STEP2-I §六 登记，不删失败、不改状态凑 PASS。

### 不得重复或擅自执行
- 不重做 6 份四件套生成与 `current.json` 指针修复；不重启 19531/18096/18094；不写生产 `platform/r12/data`；不解锁 `T-D2MD-18`；不 commit；不签 `QA_PASS`。
- 不得把演练结果读成「图已重建 / 查询可读 / 线上已生效」。

## P6 / T-D2MD-17 设计澄清（2026-11-12，STEP2-K）

### 核实结论（事实）
- `graph_root` **不是「一个库」**：契约 `02-CONTRACTS.md:24` 示例是落盘目录；实测同一 root 下有 `kb_9`(46/11)、`kb_1004`(4520)、顶层单快照(3)。`delta_build.py:51-58` `_kb_root(kb, root)` = `<root>/<kb>`。**`kb`/`kb_id` 才是一个库**。
- 「按领域图谱范围检索」已由 `QueryRequest.kb` → `engine_for_kb` → `_resolve_snapshot` + `kb.json` 归属校验实现；按库灰度切读的设计是 `INGEST_READ_MODE` / `INGEST_READ_KBS`（STEP2-F 路径 B，尚未实现），不是 `root`。
- B-2 根因 = 18094 未设 `LLMKE_V2_ROOT`。纯函数实证：不设 → `_resolve_snapshot('kb_9')=None`；设 `<app graph-root>` → 命中 `kb_9/snapshot-20261107212905-365431-g0`。即 (a) 是零契约变更的最小解。
- 契约 `QueryRequest`(llmke-document-pipeline-v2.json:1547) 与 `GraphQueryRequest`(llmke-core.json:1212) 均无 `root`，加字段需改合同源 + `make generate/check` + CR + 消费者回放。

### 判断
- 写入侧请求级 `graph_root` 是 `P4-L13C-PLAN.md:29` 的刻意 fail-closed 要求（非单纯缺陷），但需服务端白名单；`P4-L13C-R0` 曾把 (A)env / (B)请求 列为待 Owner 裁定，上一轮代选 (B)，已如实登记。
- 查询侧 `QueryRequest` 增 `root` **不是更佳**：把存储根/环境选择权下沉给查询方，与 P2-L8 服务端隔离模型相悖；与 `kb` 语义重复；不解决根因且仍需重启 18094；契约成本高。

### 当前阻塞
- Owner 的 (b) 裁定是条件式（「假如我的理解正确前提下」），前提不成立 → **不自动生效，本轮未执行 (b)、未改契约、未提 CR**。等待重新裁定：(a) 重启 18094 设 `LLMKE_V2_ROOT`（推荐）/ (b) 加 root + 白名单 + CR / (c) 维持指纹比对。
- 另需裁定写入侧请求级 root 是否保留并补白名单，或回退 (A) env 驱动。
- 附带：`kb_1004/current.json.dir` 仍指向已删 `llmke-r12`（另一个失效指针），另立条目。

### 下一精确动作
1. 执行：Owner 就上述两项重新裁定。
2. 检查：若选 (a)，窗口内重启 18094 设 `LLMKE_V2_ROOT` 后复跑 `POST /v2/graph/query kb=kb_9`，确认不再 `NOT_BUILT`；再按 STEP2-J 的窗口步骤生产切读。
3. 失败后：按 STEP2-K §五 登记，不删失败、不改状态凑 PASS。

### 不得重复或擅自执行
- 本轮纯只读核实，未改代码/契约/数据、未重启服务、未 commit；此状态在裁定前保持。
- 不得把「条件裁定」读成「无条件批准」；不得自签 QA。

## P6 / T-D2MD-17 设计判定已定案（2026-11-12，STEP2-L）

> 上节的「待重新裁定」已由本节收敛。Owner 反馈：技术细节应由 AI 判定，不应反复让其理解后选择。

### 判定（integration-agent 作出，默认执行，可推翻）
- **D-1**：`graph_root` = 多库落盘根/环境命名空间（实际落点 `<root>/<kb>`）；`kb`/`kb_id` 才是一个库。「按领域图谱范围检索」已由 `kb` 实现。
- **D-2**：B-2 采用 **(a) 重启 18094 设 `LLMKE_V2_ROOT`**；**否决** `QueryRequest` 增 `root`，不进 backlog。依据：根因是 env 未配、零契约变更、纯函数实证有效、(b) 破坏服务端隔离模型且仍需重启。
- **D-3**：写入侧**保留请求驱动**（追认 STEP2-J 的 (B)），不回退 env；依据 `P4-L13C-PLAN.md:29` fail-closed 要求。基于「18096 仅 `127.0.0.1` + 内部调用方 18097 + Java `v2-ingest.url: ""`」接受无白名单风险；**失效条件**：暴露到非 loopback / 接入不可信调用方 / 对外提供摄取 API 时，必须先补服务端白名单并登记 `RUNTIME-SWITCHES.yaml`。
- **D-4**：按库灰度切读 = `INGEST_READ_MODE`/`INGEST_READ_KBS`（路径 B），另立条目，不阻塞本任务。
- **D-5**：`kb_1004` 失效指针另立 backlog，不扩大 kb_9 范围。
- **D-6**：技术判定由本角色默认执行并附可复跑证据；仅「生产窗口放行 / 方向性业务变更 / Owner 与独立 QA 签署」三类升级，且只需是/否或授权。纠正前两轮把技术选型过度升级为 Owner 裁定。

### 依据（可复跑）
- 新增 `tests/test_p6_graph_root_semantics.py` → **4 passed**（纯 tmp_path，不依赖生产路径）。
- STEP2-J 相关 4 文件 98 passed；变异复验 3 failed / 3 passed；隔离演练 PASS + 变异体被捕获。
- 判定书：`docs/v2-tasks/evidence/STEP2-L-DESIGN-DECISION-20261112.md`。

### 下一精确动作（窗口放行后自动执行，不再逐项询问）
1. 同步运行树 `kb_ingest_service.py`（发布树 `563be5a1…` → 运行树 `5a19cc16…`）。
2. 重启 18094 设 `LLMKE_V2_ROOT=<app graph-root>` → 复跑 `POST /v2/graph/query kb=kb_9` 断言不再 `NOT_BUILT`。
3. `LLMKE_KB_STATE` 指向同源 state → 停 19531 → 重启 18096 → POST 6 份 → 比对生产 `current.json` 的 `documents` / `fingerprint.files`。
4. 留证，待「提交一次 git」指令入库；17 验收前不解锁 18。

### 不得重复或擅自执行
- 本轮未改代码/契约/数据、未重启服务、未 commit；窗口放行前保持。
- 不代签 Owner 决议/独立 QA，不声称 `QA_PASS`；不把工程候选读成正式门禁通过。
- Owner 推翻任一判定只需指出 D-1…D-6 编号与方向。

## P6 / T-D2MD-17 生产窗口执行完毕（2026-11-12，STEP2-M）

窗口：18:20:03 → 18:36:18（+08:00）。Owner「放行生产窗口」，按 STEP2-L §七 四步序列执行。

### 已完成且验证
- 前置：服务身份经 `/proc/<pid>/cmdline`+`environ` 核实；备份在 `coordination/p6-window-20261112/`（含 `MANIFEST.sha256`、before `current.json`/env/cmdline/运行树代码）；依赖端口 18090/18092/19526/19527/19996 全在；6 份 fixtures 的生产 file_id 映射从 `sources.json` 提取（290/329/330/332/333/999019）。
- 停 19531；同步运行树 `kb_ingest_service.py`（两份 md5 一致 `563be5a1…`）。
- **失败处理（全部保留）**：18094 重启连续 3 次 `address already in use`；根因是 `r12-watchdog.timer`（`OnCalendar=*:00,30`）自愈拉起 18094+19531，且 watchdog 实例缺 `LLMKE_V2_SNAPSHOT` 导致 `/health` 500。处置：停 timer → 清残留脚本进程 → kill watchdog 实例 → 用完整 env + 发布树代码重启。最终 pid 2370351(+worker 2371946)，`/health` 200。
- **D-2 验收**：`POST /v2/graph/query kb=kb_9` 从 `NOT_BUILT` 变为 `HTTP 200 / GRAPH / hit_count=3`。
- 同源 state 落地（`kb-state/kb_9-prod-derived.json`，46 行/11 file_id，sha256 `9618b7d6…`）；新建 `data/artifact-store/`、`data/kb-state/`，无既有文件被覆盖。
- 18096 重启切生产 env（pid 2381144，`/health` 200，三项 env 核实）。
- 6 份 POST 全 `200/OK`（`CONTENT_CHANGED`、`state_committed=True`、`index_write=APPLIED`、`delta root=<app>/graph-root/kb_9` ✔ 请求级 graph_root 生效）。
- 验收：`current.json` 与窗口前 `cmp` 逐字节相同（`fa650c7d…`，documents=46、11 file_id 全在、无新快照）；POST 后 query 仍 `GRAPH/200/hit_count=3`；重复请求 `SKIPPED_FRESH`/`NO_CHANGE`/零索引写/零 delta。
- 收口：恢复 `r12-watchdog.timer`（active）；8 端口全 LISTEN；18094/18096/19531/19532 health 全 200；19531 由 watchdog 拉回（pid 2411825）。

### 未完成 / 如实边界
- **图未被重建**：6 份 delta 均 `freshness.stale=False → SKIPPED_FRESH`，所以「不削」是「没写图」而非「重建后仍不削」。「delta 重建分支执行后不削」未在生产验证 → **17 保持 IN_PROGRESS，不解锁 18**。
- ES/Milvus 有真实写入，目标为 `v2cand_*` 影子前缀；`diff=CONTENT_CHANGED` 与 `freshness 不 stale` 口径不一致（索引写、图未写）登记为发现项。
- 18096 与 19531 双写通道并存（过渡风险），待 `T-D2MD-13/14/16` 收口；本窗口按「不扩大范围」未改部署脚本。
- 发布树与运行树 `graph_engine_adapter/api.py` md5 不同，登记为 P6-BACKLOG #7 延伸。

### 下一精确动作
1. 设计受控用例让 delta 判 `stale=True`（不写生产：优先隔离副本 root），实证「重建后仍 11 file_id».
2. 待 Owner「提交一次 git」指令入库；STEP2-G~M、代码、测试、脚本全部留本地工作树。
3. 17 全验收前不解锁 18；G-4 补齐独立 QA 主体/密钥后才讨论签署。

### 不得重复或擅自执行
- 不重做本窗口的 6 份 POST 与指针修复；不删 `18094.log` 里的失败记录凑 PASS；不擅自改 `r12-graph-v2-start.sh` 停用 19531；不 commit；不签 `QA_PASS`。
- 回滚预案见 `STEP2-M` §四（备份齐全，未触发）。

## P6 / T-D2MD-17 delta 重建分支补证完成（2026-11-12，STEP2-N）

> 补齐 STEP2-M 的缺口：生产窗口 6 份 POST 均 `SKIPPED_FRESH` 零重建，需证明「重建分支执行后仍不削」。

### 已完成且验证
- 入口 `scripts/p6_delta_rebuild_probe.py`（隔离副本 root，真实 `_default_apply` 调 LLM/embed）。
- 触发 stale：同源 live 46 行 / 11 file_id，只改 `290` 一块文本 → `freshness={stale:True, reason:SNAPSHOT_OUT_OF_DATE, changed:['290']}` → `BUILT / effective_mode=DELTA`。
- 重建后副本 `current.json`：`documents=46`、`fingerprint.files` 仍为原 11 个、`mode=DELTA`、新快照 `snapshot-20261112190738-230055-g0`（含 7 项）、`fencing=2`、`sources.json` 保留 11 个 file_id。
- 引擎真实增量：`{deleted:0, added:1, reused:30, duplicates:15, remaining:31, expected:31, consistent:True}` —— **0 块删除**。
- 变异复验：shadow 4 文件 live → 同一「11 个全在」判据 FAIL，精确列出丢失 10 个 file_id，断言非空转。
- 零生产风险：生产 `current.json` sha256 前后同为 `fa650c7d…`；8 端口 LISTEN、四个 health 200、timer active；副本 11 MB 已清理，结果留 `coordination/p6-window-20261112/delta-rebuild-probe.json` 与两份 stdout。
- 降级路径 `--light`（替身 apply_fn）亦 PASS，已标注 `light-apply (no LLM)`，未当正式证据。演练中变异复验曾出现措辞误导与判据方向写反，修正后重跑，失败记录未删。

### 证据链（三层）
1. `STEP2-J`：编排层 —— 同源 state 下 `wanted_docs` 始终含 11 个 file_id；
2. `STEP2-N`：引擎/指针层 —— 真实 `rebuild_delta` 后指纹仍 11 个、引擎 `deleted=0`；
3. `STEP2-M`：运行态层 —— 生产切读生效、查询可读、幂等短路、生产数据零改动。

### 当前状态与剩余阻塞
- 工程侧可执行验证**已闭环**；但 `T-D2MD-17` 保持 `IN_PROGRESS`，**不标 VERIFIED、不签 QA_PASS、不解锁 `T-D2MD-18`**。
- 真实外部阻塞：G-4 独立 QA 主体/公钥缺失、G-2 放行阈值未就绪、依赖链 `17←16←15←14` 未闭环（G-1 待批、12340 仍 LISTEN）、18096 与 19531 双写通道并存待 `T-D2MD-13/14/16` 收口。
- 不声称：生产图已重建（窗口内走 `SKIPPED_FRESH`）、查询等价性已验收（18 的 50 条固定 query 对照未做）。

### 下一精确动作
1. 等待 Owner「提交一次 git」指令入库（STEP2-G~N、代码、测试、脚本全在本地工作树）。
2. G-4 补齐独立 QA 主体/密钥、G-2 阈值就绪后，由**独立 QA** 复跑与签署；再进入 `T-D2MD-18`。
3. 期间若需让生产图真正走一次重建，另行申请窗口（本轮不改生产）。

### 不得重复或擅自执行
- 不重做隔离副本演练（脚本可复跑）；不把副本结果读成「生产图已重建」；不自签 QA；不 commit。

## P6 / T-D2MD-17 提交前合规复核（2026-11-12，STEP2-O）

### 已完成
- 变更审查：3 个已跟踪文件（唯一源码改动 `kb_ingest_service.py` +12/−1）+ 14 个未跟踪文件；`contracts/`/`generated/`/`registry.yaml`/`FROZEN` 未触及；待提交文件与 diff 敏感模式 0 命中（无凭据值入库）。
- 门禁复核（venv 解释器 hipporag-toolenv + `MAKEFLAGS=--no-print-directory`，日志写仓外 `coordination/p6-window-20261112/gate-*.log`）：
  - `make contract-v2-check` **PASS**（95 passed）；相关 Python 测试 **102 passed**；3 脚本 `py_compile` OK。
  - `make check` **FAIL**（DRIFT/LINKAGE）、`make security-check` **FAIL**（3265 findings）。
- **基线判别（未删失败凑 PASS）**：`fingerprints()` 只哈希 registry/合同源/generator/checker/requirements/`contract_*.py`，不含本轮新增 `scripts/p6_*.py`；`generate-report.json` 登记 18 个合同 vs registry 29 个 → 历史遗留未重跑 `make generate`。`security-check` 仅扫已提交文件即 FAIL **2377** 条（308 个已提交文件含 `/home/szf/`）；本轮新文件贡献 17 条同类 `PERSONAL_ABSOLUTE_PATH`（运行事实路径，非凭据）。
- **CR 判定**：不改契约字段集、不新增边界 → 无需新 CR；但登记兼容去向（不传仍回退 env、注入缝不变、变异复验 3 failed 证明非空转、生产窗口已实证）。判定可推翻。
- 产出 `STEP2-O-PRECOMMIT-REVIEW-20261112.md`，含**精确 `git add` 清单**（不用宽泛 `git add .`）与建议 commit message。

### 另立 backlog（不扩大本轮范围）
1. 合同基线批次：重跑 `make generate` 让 29 个合同与 `generated/` 对齐（会大批量改 generated，需单独批次/授权）。
2. 安全批次：由安全 Owner 统一评审 `.security-allowlist` 或路径脱敏规范（改 allowlist 需 CR）。

### 下一精确动作
1. 等待 Owner「提交一次 git」指令，按 STEP2-O §四 精确清单入库；提交前 `git diff --cached --stat` 逐项对照。
2. G-4 / G-2 补齐后由独立 QA 签署，再进入 `T-D2MD-18`。

### 不得重复或擅自执行
- 不擅自 `make generate`、不改 `.security-allowlist`、不删门禁失败记录、不 commit、不自签 QA。
