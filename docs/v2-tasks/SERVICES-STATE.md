# 服务状态（2026-11-03T20:35+08:00，本会话经用户授权启动）

| 端口 | 服务 | 状态 | 说明 |
|---|---|---|---|
| 8088 | rag-gateway（v2 jar，r12 conf+env） | UP | 本次构建 jar 后启动 |
| 18081 | rag-auth-service | UP | 本次构建 jar 后启动 |
| 18082 | rag-index-service | UP | v2 jar 已有 |
| 18083 | rag-qa-service（v2 jar） | UP | 重写检索地址→19532（env 覆盖 spring.ai.gt.*） |
| 18094 | V2 图服务（hipporag venv） | UP | 快照 /tmp/r20-root/snapshot-…g0 |
| 19532 | retrieval_shim | UP | upstream 18094 |
| 19995/19996 | legacy retrieval/llm（r12 alg venv） | UP（原有） | 未动 |
| 18088 | v2-fe-e2e nginx（前端） | UP（原有） | 服务最新构建的 dist |
| 18090/18091/18092/18093 | 模型服务 | UP（原有） | 未动 |

- 关键改写：qa-service 的 `spring.ai.gt.search-docs-url/retrieve-url/search-docs-global-url` 从 19995
  改指 19532（v2 检索 shim）；global 走 `/retrieval_documents_global`。
- 验证：`POST /qa/ai/question_re`（经 8088 登录→提问）http=200，答案=社区 global 答案（与直连 18094
  `/v2/graph/global` 同文）——**产品链路 global 与图同源首次在页面 API 层闭环**。
  物证：`docs/v2-tasks/evidence/PAGE-FLOW-INTEGRATION-20261103.json` + `r25-question-re-utf8.txt`。
