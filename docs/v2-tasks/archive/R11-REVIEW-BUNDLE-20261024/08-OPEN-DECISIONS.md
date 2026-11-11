# 待评审裁定的决策

## D1 路线选择
- A 复刻参考 Java 架构（JDK/Maven/Milvus/ES）
- B Python 重写（需可装包）
- C Java 网关 + Python 算法服务（与参考同构）

## D2 现有资产处置
1,781 行实现中：`authz`(113) / `citation_evidence`(437) / `chunk_store`(134) 可迁移；
`answer_api`(739) 的 HTTP 与错误语义可复用，业务实现需重写；
`index_generation`(275) 的 SQL 与状态机可迁移；`citation_flow`(83) 会被新检索层替代。

## D3 依赖（阻塞项，需业主提供其一）
- 离线 wheel（pypdf/faiss）或开放 PyPI
- 内网 LLM 端点（OpenAI 兼容）
- 可运行 torch/ollama 的机器
- Milvus 已在 19530 监听，但无客户端库

## D4 治理机制去留
现有证据链（13 批次 / digest scheme=4 / 322 测试）在产品阶段是否继续维护？
建议：冻结为"发布门禁"，不再扩张。
