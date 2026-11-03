# 合同变更与兼容矩阵

状态：DESIGN_REVISED_NOT_IMPLEMENTED。本包是本地设计补丁，没有冻结旧基线或改变外部批准记录。

## 1. 本次修改的合同

| 文件 | 生产者 → 消费者 | 变更 |
|---|---|---|
| schema/llmke-document-pipeline-v2.json | doc2md适配/协调器/计算worker → 下游与核验器 | 新增不可变解析清单、同域快照、类型化来源、支持组、图窗口、逻辑路线预算、发布及标准输入/语义/引擎对象 |
| api/llmke-document-pipeline-v2.openapi.yaml | 平台/API适配器 → 文档/构建/查询调用方 | 新V2端点，显式版本；尚无HTTP实现 |
| api/llmke-graph-engine-v1.openapi.yaml | 平台协调器 → 引擎适配worker | 首版独立内部GraphEnginePort；不暴露HippoRAG类/原生文件格式 |
| events/llmke-document-pipeline-v2.events.yaml | 解析/协调器 → 投影消费者 | parse提交/失败及来源事件；逻辑传输不强绑新MQ |
| evidence/llmke-source-lineage-v2.yaml | 原文/事实/报告 → 回答组装 | 多来源及AND/OR完整支持；普通RAG可直接引用SourceRef，不依赖图断言 |
| rules/llmke-document-pipeline-v2.yaml | 所有实现 → 检查与运行守卫 | DP-01…26，区分机械/运行/语义验证 |
| evaluation/llmke-document-pipeline-v2.yaml | 实施与验收 → 交付判断 | DV-01…26初始NOT_EXECUTED；不替代原A01–A17/C01–C20 |
| registry.yaml | 合同工具 → 编译/校验 | 增加7个新合同及2个既有本体文件登记，旧registry格式与baseline_version不冒改 |

两个本体lookup文件在原树中已存在但未登记，原通用工具会拒绝。此次只增加`ontology`登记元信息，原payload逐值保持；不是批准另一套类型体系。对应根因/验证见VALIDATION_REPORT.md。

## 2. 兼容性与破坏性变化

| 变化 | 兼容方法 | 不允许的处理 |
|---|---|---|
| SourceRefV2不以chunk_id作原文身份 | V2端点/适配；旧接口和schema保留 | 对旧闭集直接加字段或无依据补parser_version |
| offsets绑定doc2md不可变MD | 校验旧产物解码/换行语义后显式转换；无法转换保留旧证据状态 | 重写MD后沿用旧offset/hash |
| 逻辑路线取代es/milvus预算键 | TokenBudgetV2/新调用方；旧TokenBudget仍原样 | 标es的结果实际上来自新后端却未声明迁移 |
| parsed_text-only升级结构化 | 重新经doc2md或明确legacy导入状态 | 用Markdown后缀冒充完整表格/图像解析 |
| 每文件图→同域库图 | 快照级构建、新代发布和来源并集 | 原地混入新旧事实或人工连边凑跨文件关系 |
| 新语义伴随文件/模型变动 | semantics hash参与输入digest，下游重建 | 修改图片解释却保留旧snapshot/证据摘要 |
| 引擎替换 | 新适配器/隔离索引、对照验证、CAS切换 | 原生chunk/节点ID进入业务公共主键，或承诺私有索引互读 |
| RAG/graph/community分开就绪 | 单一路径可先发布；界面展示真实READY状态 | 将普通RAG回答标成global/GraphRAG已生效 |
| 新PARSE/PIPELINE错误码 | 仅V2 Error；V1使用已定义兼容码映射 | 修改旧闭集而不升级客户端 |

这比原报告只识别3处破坏性变更更广；这是本次设计修订的迁移面，不是已执行迁移清单。

## 3. 数据复用和迁移顺序

1. 保留原件、文件/版本/权限、现有业务表、原解析产物和旧索引；先拿真实DDL，不能只依赖ORM/字段数。
2. 对新逻辑关系做可恢复的增量迁移草案：解析产物、快照bindings、任务租约、构建/发布及来源支持。原doc2md登记库隔离，worker通过协调器操作LLMKE业务状态。
3. 选明确的原格式样本，经真实doc2md产出四件套/资产；原IR纯校验+完整来源+多模态保真，不在Graph/RAG里重解析。
4. 新旧索引并存，V2双路径从相同产物重放；未变化的解析不重复OCR。当前版本和历史比较分开。
5. HippoRAG锁定版本/模型/依赖；构建隔离输入，确认metadata去重来源不丢、graph trace真实、标准事实可导出。社区/报告另验。
6. 去ES替代profile完成全部职责、效果、权限、恢复与断网验证后，在可回退窗口停ES；业务调用方先迁到逻辑路线。
7. 全目标能力、目标环境与发布独立验收；合同样例、schema通过不关闭生产P0。

此顺序描述数据和兼容依赖，不是新的无人值守派工指令。
