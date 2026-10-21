# API与实现分层

Java：interfaces→application→domain；infrastructure实现domain端口。业务规则在领域/用例层，Controller仅协议装配。Python：services封装算法；lib/storage隔离ES/Milvus/Nebula/结构化差异；不得回写业务状态或自行激活代次。

domain/application合同定义稳定业务数据、证据与状态。BFF可转换成前端视图模型；图表组件、ECharts option不进入领域合同。前端按合同消费并实现引用解析、流式状态与错误提示。

同一结构需要跨语言验证；引擎nprobe等参数留在已批准的服务端配置，不能任意透传。图depth/algo作为已批准算法语义显式表达；实际引擎映射在适配器。

新增代码后接入ArchUnit/依赖检查、真实构建与覆盖率；空目录不构成分层验收。首切片必须提交pom质量profile、实际Java验证器/DTO适配和共享正负样本。
