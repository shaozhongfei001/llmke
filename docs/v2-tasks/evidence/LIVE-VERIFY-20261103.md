# 真机验证实录（2026-11-03 23:00，本会话自起 18094/19532，验证后已停并恢复原状）

- 环境：18090/18092（模型端点）在听；18094/19532 空闲。本会话起 18094（s4-root-c 快照）+19532，
  跑 `scripts/v2_live_verify.sh`；结束前已停两实例并确认端口释放。

## 结果（4 PASS / 1 FAIL，FAIL 根因已定位为非代码）

| 项 | 结果 | 输出要点 |
|---|---|---|
| D6-B 禁用图对照 | PASS | DENSE_FALLBACK / GRAPH_DISABLED / graph_calls=0 |
| D0 /v2/graph/view | PASS | status=ok nodes=26 edges=49（HippoRAG 引擎图） |
| D9 health.cjk_compat | PASS | installed=true，两处 patched |
| shim global 未命中分层 | PASS | 200 + NO_RELEVANT_FACTS（不 501） |
| D6-A GRAPH+seed_hits | **FAIL（快照陈旧，非代码）** | route=GRAPH、graph_calls=1，但 seed_hits=[]、rerank_fallback=true：s4-root-c 为补丁前构建，
  实体键为 md5("") 退化键，种子必然不命中 |

## D6-A 的正例证据（补丁后构建的快照，已在本会话 T-A 复核期独立核验）

- `/tmp/a2-A.json`（A2 证据同款，18095 上补丁后重建的 68 事实快照）：
  `GRAPH / GRAPH_CALLED / graph_calls=1 / seed_hits=["ent:智造贷"] / rerank_fallback=false / facts_after_rerank=1`。
- 结论：**代码链路成立；运行快照必须为补丁后构建**——生产首次建图默认装补丁（D9 已落地），
  不存在“线上拿到退化键快照”的路径；s4-root-c 是历史存量，重建即正常。

## 环境终态

- 18094/19532 已停止、端口释放；18088（前端 nginx）、18090/18092、19529（legacy graph）为原有状态未动。

## 追加（2026-11-03 23:55）：D10 首次真实上传文档语料运行（id=333 产品解析块，A1 证据 §2）

- 环境：自起 18094（LLMKE_V2_ROOT=/tmp/r20-root），建图 2 docs/6 facts/3 社区 citation_ok；
  验证后已停并释放 18094。
- 问句 T-02「日均存款的对账口径是什么」：
  - A 组：GRAPH / graph_calls=1 / **seed_hits=["日均存款"]（seeds_source=auto）** / rerank_fallback=false /
    facts_after_rerank=1 → **D6-A 在新鲜构建上成立**（此前 live_verify FAIL 根因确认为存量快照）；
  - B 组：DENSE_FALLBACK / GRAPH_DISABLED（对照成立）；
  - global：READY，答案含「日均存款 口径 按业务日跨账户汇总/天数」「数据源 T-CORE-001」均带（来源：333）；
    另有 2 条“DOCX contains/is table”抽取噪声（语义质量留 M4/用户判，如实记录）。
  - d10_eval 结构判定：T-02 检索链路 PASS、global PASS。
- 物证：`docs/v2-tasks/evidence/d10-run-T02-real-corpus.json`。
