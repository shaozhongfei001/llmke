# 本轮验证记录

日期：2026-10-30。性质：设计/合同自查，不是独立QA或产品运行验收。

## 最终实测

| 检查 | 实测结果 | 能证明的范围 |
|---|---|---|
| `python -m pytest tests/test_contract_semantics.py tests/test_document_pipeline_v2_contracts.py -q` | **95 passed** | 旧合同语义样例兼容、新合同及跨对象正反例 |
| `python scripts/document_pipeline_v2_offline_check.py` | **27 contracts PASS；network_attempts=0** | registry、schema、仓内引用、完全本地打包的OpenAPI结构 |
| `python scripts/document_pipeline_v2_validate.py` | **PASS** | 合成样例清单/摘要、快照、来源、支持、窗口、逻辑预算和引擎输入输出一致性 |
| 原doc2md `validate_document_ir` | **文字/多模态2组PASS；非法cell confidence按预期拒绝** | 提供源码的纯IR规则；详见UPSTREAM_IR_CHECK.json的源码SHA256 |
| 与3fea44e逐文件比对 | **原schema/API文件字节均未改** | LEGACY_COMPATIBILITY_CHECK.json列出15个已有文件（含目录占位文件），不是15份合同 |
| 原两个本体lookup逐值比对 | **原payload相同** | 只增加登记元信息；不表示本体类型已获业务批准 |

## 反例覆盖的实际边界

错部件hash/路径穿越、MD被改仍沿用旧来源、混代/过期授权、缺支持前提、RAG独立于graph、global暗中回退、上下文超限、窗口漏尾/非法排除、未验证后端冒充可发布、隐藏ES依赖、图检索无trace、重复文本丢来源、表头指向不存在cell、图片hash错误、语义伴随文件未绑定输入digest等均有拒绝样例。

这些检查只能核验被提供的对象和声明：不能证明实际模型已经执行、token计数真实、授权签发方可信或金融命题被原文充分支持。还需真实服务/模型/语料与运行trace。

## 工具限制与本轮修正

1. 通用`contract_generate.py`尝试被自动审批拦截。审批理由是绝对`$ref`可能触发未验证主机访问、存在对外披露私有契约风险。本轮没有重试该命令或间接调用它；改用**仅解析仓内资源、内存改写本地ref并禁止socket/URL网络访问**的独立检查器。
2. 因此原`contract_generate/check`结果记为**NOT_RUN_AFTER_AUTO_REVIEW_REJECTION**，不冒充PASS。registry中新增generated输出尚未生成，既有generated不能当V2同步制品；后续须在安全本地解析配置下完成标准生成联动。
3. 原ontology两个lookup未登记；按既有registry规则会拒绝。新增登记及最小元信息，原本体payload保持。
4. 多模态合成样例首版误写capabilities为tables/figures，4项测试拒绝；修正为已定义table_cells/figure_assets，重算清单/快照后最终95通过。没有放宽枚举来换绿。
5. 为避免普通RAG反向依赖图事实，支持组允许直接原文项；为避免去ES仍被预算键绑住，V2预算改用逻辑路线，旧V1保留。

独立工具环境清单见validation-requirements.lock；它不是生产运行依赖锁，不沿用仓库中混入无关依赖的全量锁。

## 未执行

- doc2md真实全格式解析、OCR/VLM、最新代码与CLI统一出口；
- HippoRAG安装/运行/锁定版本/模型/标准事实导出/真实图trace；
- 另一个真实图引擎的替换和索引重建；
- 去ES职责迁移、中文检索效果/容量/P95、离线包净减；
- UI业务验收、真实权限非干扰、崩溃/并发/撤权、DDL恢复迁移；
- 独立QA签署、原业务P0关闭、目标机发布或生产安全验收。

DV-01…26仍为NOT_EXECUTED；95条设计/合同测试不能替代这26类产品场景。
