# 执行检查点

更新时间：2026-11-02T21:30+08:00
任务书：docs/v2-tasks/PROMPT-TL-START.md（base_commit bb32876）
当前工作树/分支/HEAD：/home/szf/data/dev/llmke-v2，design/v2-input-engine-adoption-20261030-2101
当前阶段（VL0–VL7）：VL1 进行中（图查询 HTTP 边界已通，产品接线未开始）

成果位置与当前版本：
- 合同：contracts/（27 份，generate/check 均 PASS）
- 图服务：`graph_engine_adapter/api.py`，127.0.0.1:18094（uvicorn，hipporag venv）
- 台账：docs/v2-tasks/TASKS.yaml（T-V2-01 VERIFIED、T-V2-02 DOING）
- 环境：MySQL/ES/MinIO/Milvus/Nacos/Redis、模型 18090/18092/18093、解析 12340、legacy 图 19529、Java 8088/18081/18082 已启动

## 已完成且验证
- T-V2-01：contract-all PASS(27)、contract-v2-check PASS(95)；
  证据 `docs/v2-tasks/evidence/VL0-contract-20261102.log`
- 图路由修复：上游 rerank 解析失败会静默退 dense；适配器加候选兜底并记 `rerank_fallback`。
  真实查询：`executed_route=GRAPH / GRAPH_CALLED`；
  证据 `docs/v2-tasks/evidence/VL1-graph-route-20261102.log`
- HTTP 边界：`GET /health` 返回 97 节点/258 边/76 事实；`POST /v2/graph/query` 返回
  `executed_route=GRAPH`、trace、top_k 文档；接口测试 4 passed；
  证据 `docs/v2-tasks/evidence/VL1-graph-api-20261102.log`

## 正在执行
- T-V2-02：补 `/v2/graph/build`（payload → 隔离快照）与来源映射（chunk idx → file_id/locator），
  然后把产品（Java/前端）从 legacy 图调用切到本服务。

## 未完成/失败
- 建图 HTTP 端点未实现（当前只能用脚本建快照）。
- 引用来源未接：`sources_available=false`，因为快照里没有 file_id/locator 映射。
- `seed_hits=[]`：查询入口未传实体种子，PPR 起点依赖引擎自身 NER。
- 产品页面仍走 legacy，D0 未开始。

## 下一精确动作
1. 执行：实现 `/v2/graph/build`，输入标准 payload（chunks+metadata），输出 snapshot 路径与
   `{nodes, edges, facts}`；测试用 2 块合成数据。
2. 检查：curl build 后立刻 query，确认新快照可读且路线 GRAPH。
3. 成功后：建 chunk→来源映射，填 `citations` 并置 `sources_available=true`。
4. 失败后：记录 payload 形状/字段差异，缩小到单块复现。

## 不得重复或擅自执行
- 已完成的有副作用操作：启动演示环境；启动 18094 图服务（仍在运行）
- 用户暂停/待授权事项：无
