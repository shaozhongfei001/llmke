# ROUND8 派发与文件所有权

| 角色 | 文件责任区 | 当前任务 |
|---|---|---|
| tech-lead（集成） | `loops/ROUND8/**` | 状态、账本、集成与门禁 |
| python-parser-agent | `modules/citation_evidence/**` | 纵向切片实现与测试（已完成） |
| source-reuse-agent | `loops/LD-legacy-discovery/evidence/**` | 555 矩阵 AI 建议（待口径） |
| data-orm-agent | 只读源码 + `evidence/*.json` | DDL 校验器（未启动） |
| security-agent | 隔离原型目录 | 授权/代次原型（未启动） |

**规则**：不同角色不得同时改同一文件；跨区改动须经 tech-lead 合并。
