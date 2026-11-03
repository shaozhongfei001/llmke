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
