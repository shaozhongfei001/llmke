# 506 条接口清单 vs 生产快照 核验摘要

- 清单总数：506
- 解析源文件数：52
- 结果分布：`{"OK": 504, "PATH_ONLY_COMMENTED": 1, "LINE_DRIFT": 1}`
- 非 OK/LINE_DRIFT 项：1

| asset_id | 服务 | 清单方法 | 清单路径 | 状态 | 源码实际 |
|---|---|---|---|---|---|
| API-0345 | rag-qa-service | GET | `/ai/getRerankModelInfos` | PATH_ONLY_COMMENTED | L135 |
