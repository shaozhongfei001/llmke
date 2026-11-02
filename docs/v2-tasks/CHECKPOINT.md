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
