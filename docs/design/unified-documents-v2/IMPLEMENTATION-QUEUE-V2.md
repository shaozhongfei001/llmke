# LLMKE 统一实施队列 V2（2026-10-30）

本文件是**唯一实施入口**：后续 TL 不需要再拼接旧提示词。
设计与合同基线见 `00_READ_ME_FIRST.md` 与 `contracts/registry.yaml`；本次接入事实见 `ADOPTION_REPORT_20261030.md`。

状态口径：进度只按"真实可用能力 + 已关闭验收"统计，**不用提交数、文件数、行数或准备度**。
任何任务未按 §3 的"验收"给出现场可跑的命令与结果，其状态一律不得写 `DONE`。

---

## 1. 分阶段 Loop 与结束判据

每个阶段统一按五步闭环，**不允许跳到验收**：

`实现 → 组件级反例（先造失败） → 真实消费者集成 → 端到端验收 → 修复并回归`

| 阶段 | 目标 | 结束判据（缺一不可） |
|---|---|---|
| VL0 设计与契约接入 | 设计入库、合同可解析、生成联动可复算 | `make contract-all` 与 `make contract-v2-check` 全 PASS，且失败项只剩既有项并已登记 |
| VL1 贯通切片 | 上传 → 真实 doc2md → 标准产物 → RAG 投影 → 问答 → 点回原文 | 4 类格式真实文件走完整链路；引用能取到 MD 字符区间且 hash 匹配；任一步失败有明确状态 |
| VL2 正确性与抽取窗口 | B01–B05 关闭 + 抽取计划最小版 | 每条缺陷有"变异前失败/修复后通过"的成对证据；`graph_service` 无静默截断 |
| VL3 图引擎隔离 | GraphEnginePort + HippoRAG 适配器 + 隔离索引 | 同一 KnowledgeInputBundle 可被两个引擎重放；返回带 `GRAPH`/`DENSE_FALLBACK` 与真实 trace；公共层无 native ID |
| VL4 社区 / 报告 / global | 全库有效图 → 算法社区 → 带支持组报告 → 真正消费报告的 global | 孤立顶点进入社区；报告结论可追到 SourceRefV2；global 未就绪返回 `NOT_READY` |
| VL5 权限与代次 | 文件级可见集、撤权围栏、代次/租约/发布 CAS | 撤权后旧发布不可读；同请求固定同代；真实 DDL 迁移与恢复演练通过 |
| VL6 精简架构 | Java 合服务、Nacos/MQ 退出、ES 职责迁移 | 每项退出都有"职责已被承接"的实测；ES 停用前 `RetrievalProfile` 达业务判据 |
| VL7 完整交付 | 离线包、干净目标安装、差分升级/恢复、全量业务回归 | 干净机器断网安装成功；全格式 + 真实模型 + DV-01…26 有结果 |

依赖关系：`VL0 → VL1`；`VL2` 与 `VL1` 可并行但 `VL2-06` 依赖 VL1-01 的产物模型；`VL3` 依赖 VL1-01/05；`VL4` 依赖 VL3 的事实导出；`VL5` 与 `VL3/VL4` 并行但发布顺序**不可**绕过；`VL6` 可与 `VL3/VL4` 并行；`VL7` 最后。

---

## 2. 与既有台账的映射（**不重置已完成项**）

| 既有条目 | 现处置 |
|---|---|
| `docs/r15/TASKS.yaml` `T-B01`–`T-B05` | 映射为 VL2-01…VL2-05（B01 已在 R12 工作树实现，见 VL2-01） |
| `TASKS.yaml` `F03/F05/F06/F07/F09/F11/F12/F13` | F03/F05→VL5-02、F06→VL1-04、F07→VL2-07、F09→VL5-03、F11→VL5-04、F12→VL7-03、F13→VL4-03 |
| `TASKS.yaml` `W07`（制品-源码-模型版本映射） | VL5-05 |
| `TASKS.yaml` `A17`（九条验收） | VL2-08（B 项修完后统一重跑） |
| `CAPABILITY-MATRIX` `C01`–`C20` | 仍为交付口径；VL7-03 收口，不因 V2 设计缩减 |
| `evaluation/llmke-document-pipeline-v2.yaml` `DV-01…26` | 新增 V2 场景验收，`NOT_EXECUTED`，由对应阶段各自收口 |
| R12 工作树未提交的 B01 改动 | 不丢：作为 VL2-01 的输入候选，本分支未包含 |

`docs/r15/TASKS.yaml` 中依赖旧边界（"Graph 仅预留"、"社区可选"、"ES 必选"）的派工条目**作废**，
其余条目全部保留并映射如上。作废项只标注，不删除历史。

---

## 3. 任务清单

字段固定：用户结果 / 当前依据 / 复用与改造 / 合同 / 依赖 / 独占范围 / 验收 / 失败下一步 / 角色。

### VL1 贯通切片（P0，先做）

#### VL1-01 ParseArtifact 产物仓与不可变快照
- 用户结果：一份上传文件解析后，平台里存在可校验、不可覆盖的解析产物快照，后续所有派生都引用它。
- 当前依据：`services/rag-alg/alg_doc_parse_service/server/loader.py:451-462` 只落 `parsed/<file>.txt`；`parse_manifest.json`/`document_ir.json` 在 `services/` 下 0 命中。
- 复用与改造：复用 MinIO 对象存储与内容寻址习惯（`server/utils.py:103-148`）；新增产物仓适配器与 `parse_artifact` 表（列以 schema `ParseArtifact` 为准）。
- 合同：`schema/llmke-document-pipeline-v2.json#/$defs/ParseArtifact`（输入：三件套+IR+assets；输出：artifact_id + 逐件 SHA256）。
- 依赖：VL0。
- 独占范围：`services/rag-alg/index_data_service/parse_artifact/**`（新建）、`sql/` 新增迁移、`platform/r12/sql/` 同步 DDL 草案。
- 验收：`examples/artifact/` 与 `examples/multimodal/` 两组样例灌入适配器后产出 ParseArtifact，用 `document_pipeline_v2_validate.py` 的校验器判定 PASS；反例：复制期间源文件变更必须拒绝提交而非混合两次解析。
- 失败下一步：先只读比对源目录与快照差异，定位是复制竞态还是摘要算法不一致；不得放宽为"接受最大努力快照"。
- 角色：python-engineer 实现，integration-agent 接线，TL 验收。

#### VL1-02 doc2md 解析适配器接线
- 用户结果：上传的约定格式文件真的经 doc2md 解析，不再由旧 loader 按后缀挑解析器。
- 当前依据：`loader.py:232-320` 仍按后缀分支调用 PDFParser 等；`/services` 下 `doc2md` 0 命中。
- 复用与改造：保留 doc2md 冻结三件套与 IR 字节；平台只加 adapter + `parser_fingerprint`。doc2md 自身的登记库与 LLMKE 业务库隔离。
- 合同：ParseArtifact + `rules` DP-01…DP-06（产物完整性、不可变、MD 基准）。
- 依赖：VL1-01、U-02（doc2md 制品/授权）。
- 独占范围：`services/rag-alg/alg_doc_parse_service/adapter_doc2md/**`（新建）；不改 `loader.py` 既有分支（并行期保留回退开关）。
- 验收：docx/pdf/xlsx/txt 四类真实文件各 1 份，产出四件套齐全且 `parsed_text.md` hash 与 manifest 一致；反例：txt 不得再走 LibreOffice 转 PDF 老路径（`docs/r15/HANDOFF-20261030.md` 坑 ⑤）。
- 失败下一步：先看适配器与 doc2md 之间的中间产物落盘，区分"doc2md 未出 IR"与"平台未取到"；不允许在 RAG/图侧重解析原件兜底。
- 角色：python-engineer + integration-agent。

#### VL1-03 RAG 投影改为消费快照
- 用户结果：分块/索引来自解析快照，重复建索引不再重复解析。
- 当前依据：`index_fulltext_service`/`index_vector_service` 由 `alg_doc_parse_service` 直接双写（`indexing_utils.py:90-229`、`:287-396`）。
- 复用与改造：保留内容寻址 chunk 主键（`server/utils.py:103-122`）与 ES/Milvus 双写；输入改为 ParseArtifact + IR，chunk 记录 `parse_artifact_id`。
- 合同：ParseArtifact → RAG 投影（`rules` DP-07…DP-10）。
- 依赖：VL1-01、VL1-02。
- 独占范围：`services/rag-alg/index_data_service/index_fulltext_service/**`、`index_vector_service/**`。
- 验收：同一快照重建两次，chunk 主键集合与 `parse_artifact_id` 完全一致；改分块策略不触发重解析。
- 失败下一步：比对两次投影的 chunk 主键差集，先判定是分块参数漂移还是时间戳进入主键。
- 角色：python-engineer。

#### VL1-04 引用可反查（证据闭环）
- 用户结果：点开答案里的引用，能定位到原文文件、版本、MD 字符区间，且 hash 复核通过。
- 当前依据：`retrieval_fun_tool.py:759` 的 `order_num` 是随机 UUID，真实 `pk` 在 `:762`；`AiServiceImpl.java:1905-1926` 按 `order_num` 过滤；`answer.reference` 字段长度 255。
- 复用与改造：`retrive-tag id` 改用持久 chunk 主键或 `pk`；`answer.reference` 换结构化来源（新列/新表，走迁移）。
- 合同：`evidence/llmke-source-lineage-v2.yaml`（SourceRefV2：artifact + locator + quote_hash）。
- 依赖：VL1-01。
- 独占范围：`services/rag-alg/alg_retrieval_service/app/retrieval_fun_tool.py`、`services/rag-java/.../AiServiceImpl.java`（引用过滤段）、`sql/` 迁移。
- 验收：50 条抽样问题，引用 100% 能取到 `file_id+version+offset`，且 `parsed_text.md` 切片 hash 与 `quote_hash` 一致；反例：offset 越界或 hash 不匹配必须显式报 `EVIDENCE_MISMATCH`，不得回落成全量引用。
- 失败下一步：先判"没有 offset"还是"offset 对错文本"，前者补 locator，后者查换行/正规化漂移。
- 角色：integration-agent（跨 Java/Python）。

#### VL1-05 InputSnapshot 与授权有效集合
- 用户结果：一次构建/查询绑定明确的"哪些文件、哪个解析版本"，可复算。
- 当前依据：`InputSnapshot` 仅存在于合同与样例；无实现。
- 复用与改造：以 `knowledge_base_list`（版本/状态/权限）为源头，逐文档 artifact binding；`input_digest` 参与构建失效判定。
- 合同：`schema/.../$defs/InputSnapshot`；`rules` DP-11…DP-14。
- 依赖：VL1-01；与 VL5-01 共用权限查询。
- 独占范围：`services/rag-java/.../snapshot/**`（新建）+ Python 侧读取端。
- 验收：两份等价快照得到同 `input_digest`；删除一个文件后 digest 必须变化并使旧构建 INVALIDATED。
- 失败下一步：核对 digest 输入项是否漏了 semantics hash。
- 角色：integration-agent。

### VL2 正确性与抽取窗口

#### VL2-01 B01 无向去重（实现已在 R12 工作树，合同口径已定稿）
- 用户结果：`甲担保乙` 与 `乙担保甲` 两条事实都保留；`A-利率基准->B` 的反向伪边被拒绝。
- 当前依据：R12 工作树 `graph_types.py` 已按 symmetric/domain/range 改造（**未提交**）；`pair_key` 旧址 `:283-289`。
- 复用与改造：直接复用该实现；合同措辞已由 CR `BL-2.0.0-01`（ADOPTED，2026-10-30）改写，四项判据对候选实现实测全 PASS。
- 合同：`ontology/relations.v1.json`（symmetric/domain/range + `direction_resolution`，CR `BL-2.0.0-01`）。
- 依赖：VL0（已完成）。
- 独占范围：`contracts/ontology/relations.v1.json`（仅 CR 批准后）、`index_graph_service/graph_types.py`。
- 验收：两条反例（互相担保、互相持股不同有效期）逐条 PASS；`--only A02` 不回退。
- 失败下一步：若 A02 的 N1 与"保留双向事实"冲突，先判该谓词是否已登记，再决定登记谓词还是保留冲突。
- 角色：backend/python-engineer + contract-check。

#### VL2-02 B02 总额/分项不得数值裁决
- 用户结果：旧政策 5000 万 + 新政策 8000 万不再被改造成"总额/分项"。
- 当前依据：`graph_types.py:487-490` `max(values)` 推定总额；`:439-510` `split_total_predicate` 整体。
- 复用与改造：删除数值裁决与"主体名含信用即分项"，改为原文显式限定抽取，判不了就保留候选 + `conflict` 状态。
- 合同：`rules` DP-15…DP-17；`schema` 中断言的 `role`（total/item）字段。
- 依赖：VL2-01。
- 独占范围：`graph_types.py`（与 VL2-01 串行）、`graph_service.py` 审计输出。
- 验收：同一文档两个政策额度并存时，两条事实都保留且带 `policy_version`/`role=CANDIDATE`；反例：任何未经原文限定的 total 归类必须失败。
- 失败下一步：回到原文比对，确认是抽取缺失还是裁决规则越权。
- 角色：python-engineer。

#### VL2-03 B03 数值符号与单位分字段
- 用户结果：`基准+30BP` 与 `基准-30BP` 在存储、摘要、答案三处都不混淆。
- 当前依据：`graph_types.py:228` `NUMERIC_PREFIX` 把 `加/减` 抹平；`:231-242` `numeric_canon`。
- 复用与改造：数值/单位/正负/基准/条件分字段（Decimal 字符串），缺字段前不得合并。
- 合同：`schema` 的 rate/amount 断言结构。
- 依赖：VL2-01。
- 独占范围：`graph_types.py`、`graph_service.py` 序列化、`graph_summary.py` 投影。
- 验收：三条成对样例（+30/-30/无符号）在图中 `sign` 不同、在摘要与答案中措辞不同；变异测试：把 `sign` 抹掉必须 FAIL。
- 失败下一步：判"归一阶段丢符号"还是"投影阶段丢"，分别在两处断言。
- 角色：python-engineer。

#### VL2-04 B04 无来源不得进可发布图
- 用户结果：任何边都能追到 file_id/chunk_ref；追不到就不发布，并留下可重试任务。
- 当前依据：`graph_service.py:731-734` 溯源键缺失时 `_src={}` 降级，写出空 `file_id`（现网 A17 边即此因）。
- 复用与改造：断言与来源一次转换，缺来源 fail-closed；补重试任务而非静默写空。
- 合同：`rules` DP-18…DP-20；`evidence` SourceRefV2。
- 依赖：VL1-04（引用身份）。
- 独占范围：`graph_service.py` 写入段（与 VL2-02/03 串行）。
- 验收：构造缺 `triples_attribute` 的批次，写入必须被拒且任务状态可诊断；反例：任何 `file_id=''` 的边入库即判失败（现网存量另计，见 VL2-08）。
- 失败下一步：先修上游 key 拼装（`TRIPLE_SEP` 一致），再判是否要重建历史边。
- 角色：python-engineer。

#### VL2-05 B05 社区不得漏孤立顶点
- 用户结果：66 个孤立顶点（含评级档位）进入社区视野或在报告中显式登记。
- 当前依据：`graph_community.py:38-40` 只 MATCH 有边实体；`:66-88` 小簇处理已存在。
- 复用与改造：构图改为全顶点 + 有向事实无向加权投影；保留现有小簇/确定性社区 ID。
- 合同：`rules` DP-21…DP-22。
- 依赖：VL2-04（来源校验后才可靠）。
- 独占范围：`graph_community.py`。
- 验收：同一份 `g_kb_9` 快照，社区成员并集 == 全部有效顶点集；反例：成员数 < 顶点数即失败。
- 失败下一步：核对是否有顶点被类型过滤误删。
- 角色：python-engineer。

#### VL2-06 GraphExtractionPlan 最小版（禁静默截断）
- 用户结果：长文抽取有预算、有覆盖、能证明尾部没被丢。
- 当前依据：`graph_service.py:552-558` 15000 字符硬截断且无标记；设计 `01_UNIFIED_DESIGN_V2.md:143-145` 要求窗口计划。
- 复用与改造：在现有 chunk 级循环上包一层计划（MD 字符区间、tokenizer 预算、IR 块覆盖、尾部检查），先不换引擎。
- 合同：`schema` GraphExtractionPlan；`rules` DP-23…DP-24。
- 依赖：VL1-01（MD/IR 可读）。
- 独占范围：`index_graph_service/extraction_plan/**`（新建）+ `graph_service.py` 调用点。
- 验收：对 3 万字符文档，覆盖并集 == 非空 MD 区间，尾部块必须有状态；反例：故意把窗口数减 1 必须 FAIL。
- 失败下一步：若模型输出被截断，先分"输入预算"还是"输出预留"，分别调整。
- 角色：python-engineer。

#### VL2-07 F07 27 码受控类型落地
- 用户结果：实体类型来自受控清单，`unclassified` 占比有据可查。
- 当前依据：`contracts/ontology/entity-types.v1.json` 已登记（27 码），代码 `ALLOWED_TYPES` 已改为读契约（R15/A01）；`unclassified` 44% 仍未收敛。
- 复用与改造：补齐 `rule_hint` 与归一规则（`AAA级`→`AAA`、`制造业` 不得判 location）。
- 合同：ontology + `rules` DP-25。
- 依赖：VL2-01。
- 独占范围：`graph_types.py` 的规则表。
- 验收：同一语料类型分布可复算，`unclassified` 比例下降且每类有样例；反例：`AAA级` 出现在 `grade` 之外必须失败。
- 失败下一步：判是规则缺口还是 prompt 未给类型约束。
- 角色：python-engineer + algorithm-owner 复核。

#### VL2-08 A17 九条重跑与存量清理
- 用户结果：A17 九条检查有可复跑的通过/失败记录，存量脏边有清理方案。
- 当前依据：`platform/r12/qa/evidence/r15/a17/RESULT.md`（首轮 NOT PASS）、`g_kb_9` 存量空 `file_id` 边。
- 复用与改造：复用 R15 举证包（`platform/r15/verify.sh`）；清理用代次重建，不用就地 UPDATE 掩盖。
- 合同：`evaluation` DV 场景 + A17。
- 依赖：VL2-01…VL2-06。
- 独占范围：`platform/r15/acceptance/**`、`platform/r12/qa/evidence/r15/**`。
- 验收：九条逐条给出断言与原始输出；失败项如实保留。
- 失败下一步：按 A17 分项归因，不合并为一个"图不行"。
- 角色：integration-agent + 独立 QA（不得自签）。

### VL3 图引擎隔离

#### VL3-01 GraphEnginePort 适配层骨架
- 用户结果：业务侧只面对四个操作（describe/build/get index/retrieve），换引擎不动业务。
- 当前依据：`contracts/api/llmke-graph-engine-v1.openapi.yaml` 已定义 4 个 operation；`index_graph_service/base.py:88` 的 `query_type` 默认写着 `"hippo"` 但无实现。
- 复用与改造：新增 adapter 包，业务层禁止 `import hipporag`。
- 合同：graph-engine-api-v1。
- 依赖：VL1-05。
- 独占范围：`services/rag-alg/index_data_service/graph_engine/**`（新建）。
- 验收：用桩引擎跑通 4 操作；反例：业务层出现 vendor 类型即静态失败。
- 失败下一步：判是接口粒度不足还是业务泄漏。
- 角色：integration-agent。

#### VL3-02 HippoRAG 适配器与来源映射
- 用户结果：图检索真实执行，且每条命中能回到平台 SourceRef。
- 当前依据：`06_STANDARD_INPUT_AND_GRAPH_ENGINE.md:107-134`（未实现）；HippoRAG 未锁定版本。
- 复用与改造：native chunk 内容 hash 去重后保留多来源映射；返回 `executed_route` 与 trace。
- 合同：graph-engine-api-v1 + `evidence` SourceRefV2。
- 依赖：VL3-01、U-03。
- 独占范围：`graph_engine/hipporag_adapter/**`（新建，独立环境）。
- 验收：同一 bundle 两引擎重放，公共字段与来源一致；强制图查询不得以 `DENSE_FALLBACK` 通过。
- 失败下一步：先判"图没执行"（trace 缺失）还是"执行了但映射丢来源"。
- 角色：python-engineer。

#### VL3-03 隔离索引与 CAS 切换
- 用户结果：换引擎/换模型不污染线上，失败可回退。
- 当前依据：无 release/engine_index_id 概念落地。
- 复用与改造：新索引 staging 校验后 CAS 切指针；旧索引保留可回退。
- 合同：`schema`（engine index/release）+ `rules` DP-26。
- 依赖：VL3-02、VL5-03（发布 CAS）。
- 独占范围：`graph_engine/index_registry/**`。
- 验收：切换失败时旧 release 仍可答且状态可见；反例：未校验完即标 READY 必须失败。
- 失败下一步：核对 CAS 版本与 fencing token。
- 角色：integration-agent。

### VL4 社区 / 报告 / global

#### VL4-01 全顶点构图与算法裁定
- 用户结果：社区来自全库有效图，孤点不消失；算法选择有依据。
- 当前依据：`graph_community.py:30-50,64`（只取有边点、Louvain）。
- 复用与改造：见 M-1/M-2；先出 Louvain vs Leiden 的差异说明（连通性/稳定性/层级），再决定是否替换。
- 合同：`rules` DP-21。
- 依赖：VL2-05。
- 独占范围：`graph_community.py`（与 VL2-05 同一所有者，串行）。
- 验收：社区成员并集 == 有效顶点集；算法变更前后有对照记录。
- 失败下一步：回到构图输入核对，不在算法参数上凑指标。
- 角色：python-engineer。

#### VL4-02 结构化报告与支持组
- 用户结果：报告每条结论带 AND/OR 支持组，能追到原文或受支持断言。
- 当前依据：`graph_summary.py:375-453` 只生成摘要文本，无 findings/支持组。
- 复用与改造：在现有摘要链路上加 structured findings，保留 `chunk_refs/sources`。
- 合同：`evidence` support + `schema` report。
- 依赖：VL4-01。
- 独占范围：`graph_summary.py`。
- 验收：抽 10 条结论逐条核 support 完整性；反例：删掉一个前提仍判 supported 必须 FAIL。
- 失败下一步：判是前提抽取缺失还是支持判定过宽。
- 角色：python-engineer。

#### VL4-03 global 消费报告与 NOT_READY
- 用户结果：global 用的是本次发布的报告；未就绪时明确返回 `NOT_READY`，不用普通 RAG 冒充。
- 当前依据：`graph_summary.py:886-971` 直接读 ES 摘要作答；`AiServiceImpl.java:2278-2283,859-864` 无 NOT_READY 语义。
- 复用与改造：状态机按设计 §9.2 分离；global 只在 report READY 时可用。
- 合同：`rules` + `evaluation` DV 场景。
- 依赖：VL4-02、VL5-03。
- 独占范围：`graph_summary.py`、`AiServiceImpl.java`（global 分支）。
- 验收：报告未就绪时接口返回 NOT_READY 且前端可见；反例：暗中回退普通 RAG 必须失败。
- 失败下一步：先查发布目录状态，再查前端展示。
- 角色：integration-agent。

### VL5 权限与代次

#### VL5-01 文件级可见集下发
- 用户结果：检索/图/社区只吃用户可见文件，不靠最终答案过滤补救。
- 当前依据：`AiServiceImpl.java:1150-1159` 只校验 KB 级；文件级 deny 仅存在于列表 SQL（`KnowledgeBaseListMapper.xml:385-390,464-469`）。
- 复用与改造：复用 `user/group/dept_privilege` 与递归 CTE，把可见集合作为检索与构建入参。
- 合同：`schema` scope + `rules`。
- 依赖：VL1-05。
- 独占范围：`rag-qa-service`、`rag-index-service` 权限查询、Python 检索入参。
- 验收：构造"同 KB 内 A 可见 B 不可见"的夹具，B 的 chunk 不得出现在 A 的任何通路；反例：只在最终答案过滤必须 FAIL。
- 失败下一步：判定是可见集未下发还是后端忽略入参。
- 角色：backend-engineer。

#### VL5-02 代次/清单/租约/outbox 落地
- 用户结果：一次构建有代次、可回滚、可重放，任务不丢。
- 当前依据：`docs/baseline/validation/artifacts/schema-v1.3.sql:711-764` 标注 PROPOSED；运行库无这些表；`file_parse_task` 是唯一任务表。
- 复用与改造：以 target schema 为草案，先拿真实 DDL 再迁移；outbox 复用 MySQL 而非新 MQ。
- 合同：`schema` generation/manifest + `rules`。
- 依赖：U-07（真实 DDL）。
- 独占范围：`sql/**`、`platform/r12/sql/**`、Java 任务/租约代码。
- 验收：恢复副本上跑迁移 + 回滚 + 崩溃续跑三组。
- 失败下一步：先补 DDL 差异清单，不在生产库试。
- 角色：backend-engineer + DBA。

#### VL5-03 撤权 fence 与发布 CAS
- 用户结果：撤权后旧发布立刻不可读；发布只允许在同一快照上原子切换。
- 当前依据：无 fence/pointer；`docs/policies/AUTHORIZATION.md:5,7` 要求未落地。
- 复用与改造：先写 query fence 再异步清理；release 指针 CAS。
- 合同：`rules` + `schema` release。
- 依赖：VL5-02。
- 独占范围：`rag-qa-service` 查询前置检查、`index_generation_activation` 相关代码。
- 验收：撤权后 1 秒内的查询被拒；反例：旧 release 绕过权限必须 FAIL。
- 失败下一步：查 fence 写入与读取是否同一事务视界。
- 角色：backend-engineer。

#### VL5-04 F11 检索预算与多 KB 隔离
- 用户结果：多知识库并发互不串，预算裁剪在响应里可见。
- 当前依据：`TokenBudget` 为旧闭集；V2 改为逻辑路线预算但未实现。
- 合同：`schema` TokenBudgetV2。
- 依赖：VL5-01。
- 独占范围：`alg_retrieval_service`。
- 验收：两 KB 并发查询结果不串；超预算时 `degraded/coverage` 如实。
- 失败下一步：判是入参隔离还是缓存键缺 KB。
- 角色：python-engineer。

#### VL5-05 W07 制品-源码-模型版本映射
- 用户结果：任一运行结果可回溯到代码/模型/配置的具体版本。
- 当前依据：`platform/r12/nacos/alg_common_py.yaml` 只有端点与维度，无制品 hash。
- 合同：`schema` parser_fingerprint/model_fingerprint。
- 独占范围：`platform/r12/nacos/**`、模型服务启动参数。
- 验收：一次问答能导出完整指纹三元组。
- 失败下一步：缺模型制品时登记为外部输入，不编造。
- 角色：integration-agent。

### VL6 精简架构

#### VL6-01 Java 服务合并（先 sensitive + graph）
- 用户结果：业务进程数下降，路由与权限不变。
- 当前依据：`r12.target:26-34` 只含 5 个服务，不含 graph；`sensitive-words-service` 单表单职责；各服务 datasource 相同。
- 独占范围：`services/rag-java/rag-parent/**`、`platform/r12/systemd/**`、`r12ctl.sh`。
- 验收：合并后 `/sensitive/**`、`/graph/**` 冒烟等价；回滚脚本可用。
- 角色：backend-engineer。

#### VL6-02 Nacos 配置退出
- 当前依据：Java 侧 `spring.cloud.nacos.config.enabled=false` 已退出；Python 仍有 4+4 data_id 依赖（`platform/r12/nacos/publish.py:29-34`）。
- 验收：配置改由文件/环境注入且回读校验等价；反例：缺键必须启动失败而非静默默认。
- 角色：integration-agent。

#### VL6-03 MQ 退出
- 当前依据：仅 2 个 consumer 在用，4 个整文件注释（`KbConfConsume.java` 等）。
- 验收：解析任务全部由持久任务/outbox 承接，停 broker 后链路仍可跑。
- 依赖：VL5-02。
- 角色：backend-engineer。

#### VL6-04 ES 职责迁移与 RetrievalProfile
- 当前依据：ES 承担 BM25、keyword 过滤、chunk 主存、图抽取取块（`graph_fun_tool.py:908-957`）与社区摘要存储。
- 复用与改造：按 `05_ES_AND_GRAPH_INPUT_DECISION.md` §5 六类证据逐项迁移；候选 Milvus BM25 / MySQL ngram 需实测，不预设等价。
- 合同：`schema` RetrievalProfile（样例 `retrieval-profile-verified-synthetic.json` 只是结构样例）。
- 验收：六类证据齐备 + 同快照同题对照；未达判据保留 ES 适配器并记差值。
- 角色：integration-agent + algorithm-owner。

### VL7 完整交付

#### VL7-01 离线包必需件补齐
- 当前依据：`platform/r12/db/gienrag.sql`、`platform/r12/nacos/configs.json` 仓库内 0 命中，而 `offline-kit.sh:72` 列为必需。
- 验收：`offline-kit.sh` 在干净目录产出 AND 清单校验通过。
- 角色：integration-agent。

#### VL7-02 干净目标安装与差分升级/恢复
- 验收：断网干净机安装 + 升级 + 回滚 + 恢复演练全通过，记录配置/包/commit 映射。
- 角色：integration-agent + 独立 QA。

#### VL7-03 全格式回归与 DV-01…26 收口
- 验收：4 类格式 × 真实模型 × 真实语料回归；DV-01…26 逐条有结果；C01–C20 不因 V2 缩减。
- 角色：独立 QA（不得自签）。

---

## 4. 建议执行顺序

```
VL0(完成) ─┬─ VL1-01 → VL1-02 → VL1-03 ─┬─ VL1-04 → VL1-05 → VL3-01 → VL3-02 → VL3-03 → VL4-01 → VL4-02 → VL4-03
           │                            │
           └─ VL2-01 → (02|03|07) → VL2-04 → VL2-05 → VL4-01
                                          VL2-06(依赖 VL1-01)
VL5-01/02/03 与 VL3/VL4 并行准备，但发布顺序不可绕过来源与代次
VL6-01/02/03 可与上层并行；VL6-04 需 VL6-02 后
VL7 最后
```

首个开发切片 = **VL1-01 + VL1-02 + VL1-03 + VL1-04**（一条真实文件从上传到可点回原文的通路），不先做图引擎。

## 5. 独占修改范围（同一文件只允许一名写入者）

| 文件/目录 | 归属任务 |
|---|---|
| `contracts/ontology/*.json` | VL2-01（仅 CR 批准后） |
| `index_graph_service/graph_types.py` | VL2-01 → VL2-02 → VL2-03 → VL2-07（严格串行） |
| `index_graph_service/graph_service.py` | VL2-04 → VL2-06 |
| `index_graph_service/graph_community.py` | VL2-05 → VL4-01 |
| `index_graph_service/graph_summary.py` | VL4-02 → VL4-03 |
| `alg_retrieval_service/**` | VL1-04、VL5-04 串行 |
| `rag-java/**/AiServiceImpl.java` | VL1-04 → VL4-03 |
| `sql/**`、`platform/r12/sql/**` | VL5-02 独占 |
| `docs/baseline/TRACE.yaml`、`contracts/registry.yaml` | 仅合同变更任务（需重跑 generate/check） |
