# 执行检查点

更新时间：2026-11-02T21:10+08:00
任务书：docs/v2-tasks/PROMPT-TL-START.md（base_commit bb32876）
当前工作树/分支/HEAD：/home/szf/data/dev/llmke-v2，design/v2-input-engine-adoption-20261030-2101，bb32876
当前阶段（VL0–VL7）：VL1 进行中

成果位置与当前版本：
- 合同：contracts/（27 份，generate/check 均 PASS）
- 台账：docs/v2-tasks/TASKS.yaml（T-V2-01 VERIFIED、T-V2-02 DOING）
- 环境：MySQL/ES/MinIO/Milvus/Nacos/Redis 容器、模型 18090/18092/18093、解析 12340、legacy 图 19529、Java 8088/18081/18082 已启动

## 已完成且验证
- T-V2-01：`make contract-all` PASS（27 contracts）、`make contract-v2-check` PASS（95 tests）；
  证据 `docs/v2-tasks/evidence/VL0-contract-20261102.log`
- 图路由修复：上游 `rerank_facts` 依赖 DSPy 标记格式，qwen 返回 JSON 导致解析为空，
  `HippoRAG.retrieve` 静默走 dense，图检索一次未跑（实测 `DENSE_FALLBACK / GRAPH_NOT_CALLED`）。
  适配器增加“有候选但过滤为空→按向量分取前 link_top_k”兜底，并记 `rerank_fallback`。
  真实查询复验：`executed_route=GRAPH / GRAPH_CALLED`，trace `graph_calls=1, fact_candidates=5, rerank_fallback=True`；
  证据 `docs/v2-tasks/evidence/VL1-graph-route-20261102.log`
- 回归：`tests/test_graph_engine_hipporag.py` 等 4 文件 30 passed（新增 2 项兜底与还原测试）

## 正在执行
- T-V2-02（VL1 贯通切片）：下一步暴露 HTTP 建图/查询边界（build/query/export），
  再替换产品侧 legacy 图调用；产品页面尚未接线。

## 未完成/失败
- D0 产品接线未开始：Java/前端仍走 legacy；HippoRAG 仅在 adapter 与 scripts。
- 图检索 trace 中 `seed_hits=[]`（未传 seeds），需在查询入口补实体种子。

## 下一精确动作
1. 执行：新增 `graph_engine_adapter/api.py`（FastAPI：/health、/v2/graph/build、/v2/graph/query），
   复用 `rebuild.apply_delta` 与 `pipeline.retrieve`；写接口测试。
2. 检查：起服务后 curl 真实快照查询，确认返回 `executed_route=GRAPH` 与引用来源。
3. 成功后：接 Java/前端最小调用（先用反向代理或配置切换），跑页面 E2E。
4. 失败后：记录断点（端口/契约/字段），缩小复现，不重复相同命令。

## 不得重复或擅自执行
- 已完成的有副作用操作：启动演示环境（容器+模型+Java），未执行发布/推远端
- 用户暂停/待授权事项：无
