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
