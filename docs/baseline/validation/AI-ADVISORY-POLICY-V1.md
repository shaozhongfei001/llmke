# AI 建议口径 V1（本轮由业主授权）

授权范围：**只授权"如何给建议"，不授权任何处置结论**。AI 建议与 owner 决定严格分栏。

## 1. 允许的取值

`advisory_action ∈ {KEEP_CANDIDATE, ADAPT_CANDIDATE, REWRITE_CANDIDATE, RETIRE_CANDIDATE, INSUFFICIENT_EVIDENCE}`

## 2. 硬约束

| 约束 | 说明 |
|---|---|
| 置信上限 **MEDIUM** | 无 DDL、无运行时数据，不允许 HIGH |
| 必须给依据 | 引用已有证据文件或实测结论，禁止"业务上应该" |
| 必须给阻塞输入 | 缺什么才能定（DDL/路由/日志/E1/实测） |
| 必须给影响面 | 影响哪个 P0 与哪个 L 批次 |
| **owner 字段保持空** | `decision_status` 恒为 `DECISION_PENDING`；`approved_by/approved_at/approval_evidence` 不由 AI 填写 |
| 不确定就写 `INSUFFICIENT_EVIDENCE` | 这是合法且推荐的结论，不是失败 |

## 3. 本轮分发结果（555 行）

| AI 建议 | 行数 |
|---|---|
| `INSUFFICIENT_EVIDENCE` | **542** |
| `ADAPT_CANDIDATE` | 9 |
| `KEEP_CANDIDATE` | 2 |
| `REWRITE_CANDIDATE` | 1 |
| `RETIRE_CANDIDATE` | 1 |
| **owner 已批准** | **0** |

置信分布：MEDIUM 4 / LOW 551 / HIGH 0。

> 542 行给不出建议，**这是真实结论**：506 条接口缺运行时证据、37 张表缺 DDL。
> 把 542 行硬填成 KEEP/REWRITE 会让矩阵看起来"更有用"，实际是把推断包装成建议。

## 4. 少数给出建议的依据

| 对象 | 建议 | 依据 |
|---|---|---|
| `CODE-01` 解析 | ADAPT（MEDIUM） | S1 实测：25 处耦合可切断、5/5 样本一致 |
| `CODE-05` 鉴权 | REWRITE（MEDIUM） | 旧 token 体系与新 AuthContext 契约不兼容 |
| `CODE-09` 敏感词 | KEEP（MEDIUM） | 纯函数逻辑、依赖少 |
| `API-0345` | RETIRE（MEDIUM） | 路径与方法仅存在于注释 |
| `API-0425` | KEEP（LOW） | 路径与 handler 均命中，仅行号漂移 |

## 5. 与 owner 决定的关系

AI 建议**不构成**任何批准。owner 可以整体推翻、逐条拒绝或修改；`OWNER_DECISION` 字段由 owner 填写后，
`decision_status` 才可能从 `DECISION_PENDING` 变为其它值。
