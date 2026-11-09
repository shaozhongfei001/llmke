# LLMKE 步骤 5／6：生产切换与退役独立评审

评审编号：`CONVERGE-MAIN-R2`｜日期：2026-11-09｜对象：`REVIEW-PACKAGE-STEP5-6.md` V1.0 §6–§8。

## 一、裁定：NO_GO

**本版方案不能直接用于生产切换或旧目录退役：隔离实例未就绪，拟切换的 `rag-graph-service` 缺少对应构建证据，最终数据迁移点及可执行回退尚未验证。** 可继续准备新配置、补齐制品及做隔离演练。两步分别验收、分别授权。

裁定 A 与原评审 `CONVERGE-MAIN-R1` §五的先后顺序有效。本次对步骤 4 只核对发布所依赖的代码身份；这份意见不是独立 QA 签署、生产授权或删除授权。

**证据口径。** 已阅读完整版提示词、主文档、原评审，并核对 `evidence.zip` 中与切换和退役有关的日志、清单与差异。ZIP 的 115 个文件通过完整性检查；两份同名原评审副本 SHA256 相同。下文“证据”指附件可查的输出，“判断”指基于这些输出的评审意见。当前环境没有原机工作树、发布制品、真实服务或归档实物；实时状态、实际配置、业务验收和恢复均须原机复验，标为 `UNVERIFIED`。附件中的日志复核不等于重新运行生产命令。

## 二、总体意见

1. **代码身份已有证据，制品就绪仍缺证据。** `main-candidate-consistency.log` 记录 PR #3 已合并、双父提交、相同 tree `50bb4828…`、`diff_files=0` 和候选可达。`step5-release-build.log` 的成功模块包含 index、qa，未见 graph-service。不能用 8 个 jar 的数量证明 18084 所用可启动 jar 已构建。
2. **隔离试验是“进程启动，业务未就绪”。** 对 `step5-coldstart.log` 复算：19094 的 `/docs`、`/openapi.json` 各 1 次 200，`/health` 13 次全部 500；无真实图查询。日志定位到发布目录内的 `graph_engine_adapter/api.py`，报 `LLMKE_V2_SNAPSHOT 未设置`。同样的生产 500 是主文档报告值，需现场留存原始响应；即使属既有问题，也不能作为上线通过的判据。
3. **数据复制与业务恢复要分别证明。** 37 个文件无哈希差异支持归档副本可恢复。它不能证明生产最后一批写入、图快照、原文引用和影子状态处在同一可切换点。B3 应使用冻结后核定的数据版本；B7 要区分恢复写入前后的回退。
4. **切换范围来自实际调用关系。** 日志证明 5 个 PID 存在旧路径引用，其中 18096 是 `kb_ingest_service`。它是否承接生产写入或回调仍待核。11 条路径命中含 1 个 `__pycache__` 文件；现有扫描是起点，未覆盖全部实际启动来源和间接依赖。
5. **退役证据需逐对象核销。** 原日志支持 v2 有 33 个、本地 r12 有 2 个提交未成为 main 的祖先。bundle 恢复日志支持历史已归档，但 main 与候选同 tree 无法证明这两个旧分支的有效内容全部保留。旧工作树仍有未提交文件和生产数据，直接 `git worktree remove` 的草案不可执行。

## 三、逐条裁定 Q1–Q12

### Q1｜步骤 4 是否满足原评审要求

**结论：接受代码与候选的一致性，不补做同一轮合并；放行仍须绑定实际发布版本。**

**依据：** `main-candidate-consistency.log` 给出 main `14c392a1b72c036e91eca15bd270d4f66999934e`，候选 `0d3e0c2e341eb6c813c2e9c775ba5f03affb1e94`，相同 tree `50bb48286097d45b6afc961f7be379a8fc5fe058`，候选为 main 祖先。`main-merge-state.log` 的首次 `gh` 查询因字段 `merged` 失败，后续正确字段的结果支持合并事实。该证据满足原评审 §五步骤 4 的代码一致性部分；不能证明门禁签署身份或实际运行版本。

**判据／复验：** 执行附录 V1。以该 main 提交或经同等复核的更新提交固定制品、配置、依赖和数据版本，记录 Java 运行 jar、Python 模块入口及前端实际资源清单；以附录 V2 核对文件校验和。tree 相同仍需验证制品字节与运行路径。

### Q2｜C1–C6 失败，最终 HEAD 通过，是否重切历史

**结论：可接受仅以最终 HEAD 为发布对象的口径，保留失败历史。**

**依据：** `PER-COMMIT-VERIFY.json` 记录 C1–C6 的 `contract_all_exit=2`、C7 为 0；`contract-gate-triage.log` 记录旧基线缺少 homonyms 注册；`pre-pr-gate-recheck.log` 与 `step5-release-build.log` 有最终合同门禁通过。Owner 正式裁定原件未附，签署仍为 `UNVERIFIED`。全量 Python 测试不是全绿，lease/MySQL 的同类失败在旧基线也出现。

**判据／复验：** 核对 Owner 原件只适用于逐提交合同口径。对最终发布目录运行项目环境下的 `make contract-all`，保留退出码；用与生产一致的驱动、服务与配置重跑本次所涉租约、摄取和检索测试，例如 `pytest tests/test_lease_mysql.py -q`。逐项说明历史失败是否触达上线链路，按现行门禁处理剩余项。最终合同通过不能覆盖未跑的运行测试。C1–C6 不作为发布或回退版本。

### Q3｜启停次序、停机窗口和观察期

**结论：按真实调用关系及写入职责排顺序，不能从端口号确定。**

**依据：** `g06-postmerge-pathcheck.log` 显示 19531 与 18094 使用同一个旧图根，但不能证明 shim 调用 18094。18096 是有独立状态路径的摄取进程；18082／18084 Java 与现有 rag-qa、网关、回调、调度等服务的依赖未完整记录。五个 PID 有路径依赖，不等于五个必须同时重启的生产服务。

**判据／复验：** 用附录 V3 和 V4 核对实际端点配置、调用源、启动器、队列/租约与写入资源，交付 `服务 → 调用谁 → 读写什么 → 如何停／起／验／回退` 的表。按“先停止接收写入和调度，排空消费者，再停其提供者；启动反序”执行。19531 与 18094 若仅共享只读数据可分开启动；如 shim 调用 adapter，adapter 先就绪。18096 若与生产无调用和状态依赖，保留在独立批次。以一次完整演练实测预算安排窗口，按第五节的截止点和观察规则执行。

### Q4｜快照变量、健康 500、fail-fast

**结论：切换前解决生产就绪探针的 500；`LLMKE_V2_SNAPSHOT` 的具体值待核实，不预填。**

**依据：** 隔离日志中 `_load_engine(slot["snapshot"])` 路径报缺变量。历史合并片段显示可能同时存在按库 `current.json` 与单快照兼容入口；该片段不是最终发布源码。`failfast-static-check.log` 仅证明候选源码的默认值为 `true`、配置可改，未验证生产生效值和各依赖的必需性。

**判据／复验：** 用附录 V4 检查最终发布源码、入口及实际配置优先级，确认每个 KB 的指针、快照归属和无库上下文的兼容逻辑。若旧调用必须用默认快照，指定已核准的有效快照目录，验证其 KB 归属和错误 KB 不会回落到它；若按库模式设计允许无默认快照，应提供契约明确的健康／就绪探针，验证真实生产路由的必要依赖，并切换监控使用它。不得把 `/docs` 200 当 readiness，也不得单为通过探活关闭 fail-fast。隔离注入“必需依赖不可达”和“可选依赖不可达”，分别验证启动／就绪、告警、降级和依赖恢复。生产 18094 现状用同样探针留原始响应。

### Q5｜245 MB 图数据迁移与 `kb_9=44`

**结论：采用先复制、再冻结写入做最终对账、最后切换到独立持久化目录。**

**依据：** `archive-run.log` 记录 37 文件、256491629 字节；`restore-recheck.log` 记录 37/0 哈希不符。`step5-release-build.log` 只有复制退出码及大小；未见应用一致性点。附件没有 `kb_9=44` 的原始采样、字段定义和查询，`two-kb-probe.log` 的 `114/94` 为节点／边数，两者不能互相印证。

**判据／复验：** 核清真实写入者和外部状态后，先将数据预置到版本化持久化位置；窗口内排空写入和回调，记录最后成功任务、租约／队列状态、相关数据版本及每库 `current.json` 原文指纹，再做最终同步。对比相同相对路径的文件类型、大小、SHA256、权限和链接目标；验证每个 `current.json` 指向目标目录内可打开的正确 KB 快照。抽验跨图、原文、索引和状态关联。`44` 若确为代次，须有指针与实际运行响应双证；若是其他指标，写明口径再验证。附录 V5 可复跑。保留旧副本用于回退，避免新旧双写。仍依赖旧工作树源路径的 bind mount 不能作为退役后的持久化方案。只有经验证的权威输入与重建成本允许时才另选重建。

### Q6｜影子目录如何处置

**结论：默认分开保留，先判明 18096 的调用与写入，再决定迁移或独立退役。**

**依据：** `g06-postmerge-pathcheck.log` 显示 18096 的 `LLMKE_V2_GRAPH_ROOT`、`LLMKE_ARTIFACT_STORE`、`LLMKE_KB_STATE` 指向影子目录。归档的 37 个图数据文件不能证明这三组影子状态均已备份或一致。

**判据／复验：** 检查生产调用、网关、回调、调度、租约与目标索引；用附录 V3、V4 和一轮实际业务周期日志验证。需要保留时，为影子单独做一致性备份和恢复，保留独立命名空间与权限，确认不会写入生产。无人依赖且不需继续试验时，Owner 单独批准停用与归档。禁止直接把影子三个目录合并到生产图根。若影子数据位置是批准保留的独立目录，G06 判据允许这一合法引用；只要求消除对拟退役工作树的活动依赖。

### Q7｜路径替换清单是否齐全

**结论：当前 11 条命中不足以作为可执行替换清单。**

**依据：** `g06-postmerge-pathcheck.log` 中 11 条包含一个 `.pyc`，其余为部署源文件候选。`PWD`／`OLDPWD` 字符串和启动参数、真实打开文件的含义不同。systemd、crontab 空段没有命令退出码和覆盖范围，不能推断所有用户／计时器均无依赖。

**判据／复验：** 附录 V3 覆盖进程 `cwd/exe/cmdline/fd/maps`、实际启动管理器、systemd unit/drop-in/template/EnvironmentFile 和用户 unit、watchdog/timer/cron、Nacos 生效配置版本、网关、软链接／挂载、JAR 资源与 Python 导入路径。每项列旧路径、目标路径、激活方式、正向验证和回退。检查当前正在用的配置和下一次重启会读到的配置。用已知旧路径作为扫描正对照；核对退出状态和权限。区分生效引用、缓存和历史记录，不能只用一次 `grep` 为空认定脱离。

### Q8｜验收矩阵是否充分

**结论：方向正确，须把可证伪的业务判据补齐。**

| 验收项 | 必须看到的结果 |
|---|---|
| 制品、进程、路由 | 启动入口、运行进程、实际网关响应与固定制品一致。避免直接探新端口通过、入口仍指向旧实例。 |
| 健康与冷启动 | 配置、图及必需依赖在规定时间内就绪。`/docs`、`/openapi.json` 只作存活证据。 |
| 两库隔离 | 同一新制品、固定数据版本下，分别选择 `kb_9` 和 `kb_1004` 的稳定节点／文档／证据锚点；A 有 A 锚点且无 B 锚点，B 反之。另测假库和无权库，不出现默认库或泄漏。节点数可辅助排查，不能单独放行。 |
| 摄取与回调 | 以受控样本验证 DOC2MD 产物、入库、成功／失败回调、重复回调不重复写入，以及开关关闭契约。关开关后行为仍需实测。 |
| 检索与引用 | 固定问题命中正确 KB／版本；返回原文引用可打开且内容、来源和权限正确。缺证据／错误 KB 时行为与合同一致。 |
| 回退 | 切换前在同类隔离环境从新版本实际回到旧制品、旧配置和一致数据，复跑同一组基线，并量出恢复耗时。生产仅在触发回退条件时执行。 |

**依据：** `two-kb-probe.log` 仅记录旧部署的两个图规模和假库返回，尚无新制品的业务结果；`step5-coldstart.log` 无查询及引用。原方案 §6.3 的“不同节点数”可能在错误路由、缓存或数据版本不同的情况下通过。

**判据／复验：** 用附录 V6 对新、旧完整入口执行同一组请求夹具，记录实际路由、制品 ID、返回状态、解析到的 KB、数据版本和脱敏断言。生产写入型验收须使用批准的测试知识库和受控请求；无授权时在隔离环境完成，不用生产数据验证失败写入。

### Q9｜33／2 个独有提交及强制删除

**结论：可用可恢复归档保全历史，强删只能针对逐一审批的本地引用。**

**依据：** `retirement-reachability.log` 报告本地 v2 和 r12 不可从 main 到达，旧远端追踪 r12 可达；bundle 列出旧 main、v2、r12、stash 四个引用。`restore-recheck.log` 记录四个对象可读及隔离 stash 应用成功。归档初次记录 `verify_ok:false`，后续 `all_pass=true`；须关联同一份归档的 SHA256、具体校验命令和结果，保留前后两条记录。候选的 r12 差异复核表主要针对工作区，不能替代本地 r12 两个独有提交的单独核销。

**判据／复验：** 附录 V7 核对每个待删引用的最新完整 OID、独有提交及其内容去向，并在无源对象库依赖的空仓库从 bundle 恢复。有效代码／配置有明确接收位置或批准排除理由，原始提交及脏树可恢复，归档位于拟删目录之外。允许 Owner 指定 `分支名 + 预期 OID + 保留位置` 后单独授权；若审计要求从仓库直接访问历史，可保留只读标签，不必留下常驻工作树。`main` 与候选 tree 一致不表示旧分支历史可达。

**命令勘误：** “`git branch -d` 必然拒绝”不成立。临时仓库实测：相对 main 的祖先检查退出 1，但已合入配置的 upstream 时 `git branch -d` 退出 0。另实测非强制 `worktree remove` 遇脏树退出 128。退役以显式祖先、内容和恢复核对为准，不能把 `-d` 成功或失败当作已安全归档，也不能因移除失败自动升级 `--force`。

### Q10｜退役顺序、观察期和保留期

**结论：在步骤 5 完成后逐个退役，观察期到点本身不放行。**

**判据／复验：** 至少 24 小时且覆盖一个真实写入、调度／watchdog 与备份周期，取较长者；窗口内保留可用的旧配置、制品与一致数据。期间无关键业务失败、回退风险或旧路径活动引用。对附件所列 archive 再做恢复，并核对当前工作树文件哈希；仅状态行数不变不能证明内容未变。候选工作树及 `integrate/converge-main` 可在无构建、运行引用并确认已合并后先退役；旧 v2/r12 目录先处置核准保留的数据和脏文件，干净且无依赖才用 Git 正常移除。分支删除在关联工作树移除之后逐一办理。远端 `integrate/converge-main` 曾存在，补入清单；远端 r12 的实际引用须另查，不能用旧追踪值代替。

**保留建议：** 退役后仍保留至少一个可回退版本及对应归档。没有既有更长规定时，建议保留到至少 30 天且跨过下一次成功受控发布，取较长者；到期复核，不自动清除。归档若含环境配置，按现有权限和备份制度保存。附件还列出 4 个其他历史本地分支，本轮未逐一评审；不能把本轮三个分支退役写成“仓库只剩 main”。`llmke` 继续作为 B-8 规定的 main 发布工作树，开发使用短期分支。

### Q11｜谁签署、何时签署

**结论：技术就绪、独立验证、生产授权、退役批准分别记录。**

**依据：** 附件只提供合并与执行日志，未附当前正式授权单或独立 QA 签署件。`qa-mechanism-probe.log` 中的文件名与工具帮助不证明签署者身份或独立性。§九“不自签”边界正确，仍需绑定签署对象、实际人员和时间窗口。

**判据／复验：** 按第六节执行。用同一 `main SHA + 制品清单摘要 + 配置摘要 + 数据检查点／迁移方案 + 环境` 对照 TL、QA 和 Owner 记录。按本项目当前有效的 QA 流程复核，不能沿用不同提交、不同环境或过期凭据上的结论。实际切换结束要有现场验收与观察记录，退役前再做独立核对。

### Q12｜红线如何解除

**结论：生产重启、数据切换和旧目录退役必须拆开授权。**

**依据：** 原评审 §五要求先脱离、后退役。§6.0 同时要求解除重启与删除限制，扩大了发布授权范围；重启批准也不会自动允许移除旧的 245 MB 源数据。

**判据／复验：** 按第七节将授权绑定准确对象、窗口、操作和禁止项。步骤 5 可允许必要的冻结写入、数据复制、启停与回退；步骤 6 在证据满足后再允许指定旧目录／引用退役。两次动作前分别复核 `final-redline-check.log` 同类项目，新增写入、配置、引用或 PID 漂移时先核销。保留 `git clean -fdx` 和原仓库 stash 操作禁令。

### 追加 Q13｜恢复生产写入之后怎样回退

**结论：B7 不能直接用旧数据目录覆盖新版本已经确认的写入。**

恢复写入前，可切回旧制品和最后一致检查点，验证新实例已停止写入。恢复写入后，优先使用旧版本可读的同一权威数据；若数据不兼容，事先验证受控回放、补偿或恢复后追平，并明确 RPO／RTO。现场演练只验证无写入阶段时，不能签“全时段可回退”。没有可接受的写入后回退方案时，不得开放相应生产写入。

## 四、问题清单

| 编号 | 级别 | 位置 | 影响 | 整改与关闭证据 |
|---|---|---|---|---|
| S56-01 | BLOCKER | §6.1 A1/A3；`step5-release-build.log` | 18084 所需 graph-service 制品没有对应构建与启动证据。 | TL 补齐准确服务清单和完整制品摘要，逐服务做实际启动与入口验收；QA 复核。 |
| S56-02 | BLOCKER | §6.1 A4、§6.3；`step5-coldstart.log` | 仅存活，快照／就绪失败，未验证新链路。 | TL 确定有效快照配置或批准的按库就绪契约；同一发布环境正负例通过。 |
| S56-03 | BLOCKER | §6.2 B2–B4、B6；路径复核日志 | 依赖和写入者不全，可能发生双写、错误启停或下次启动仍依赖旧目录。 | TL 给出生效启动与读写拓扑、实际配置差异、停止及恢复命令；QA 做无旧路径的隔离冷启动。 |
| S56-04 | BLOCKER | §6.1 A2、§6.2 B3；Q5/Q6 | 一次复制未绑定最终一致点，影子处置未定。 | TL 提交写入冻结、最终同步、每库版本和跨资源核验；Owner 核准生产／影子数据范围。 |
| S56-05 | BLOCKER | §6.1 A6、§6.2 B7 | 脱敏环境记录不能直接恢复，已确认写入可能丢失。 | 制作可执行回退包，使用既有凭据来源；演练新到旧的业务恢复，记录时限及写入前后策略。 |
| S56-06 | BLOCKER | §6.3、§6.4 | 两库、摄取、引用、必需依赖负例缺新制品证据。 | 独立 QA 按 Q8 对确切制品和数据验证；各失败不得以旧环境结果抵消。 |
| S56-07 | BLOCKER | §6.5；`retirement-reachability.log`、`restore-recheck.log` | 脏树移除、原始数据删除与强删引用可能造成损失。 | 原机复核待退役清单、活跃引用、独有提交去向、归档恢复和权限；Owner 分项签署。 |
| S56-08 | MAJOR | §6.0、§6.6、§九 | 误将授权当唯一缺口；将发布树说成开发树。 | 分开技术准备、生产切换和退役决定，订正 B-8 发布树用途，附签署原件或明确未签。 |
| S56-09 | MAJOR | §3、§4、§6.5 | 复用历史测试或数量结论会掩盖制品身份和遗留风险。 | Q2 保留真实失败；统一 build/restore 清单，核销 v2 两个 `REVIEW` 工具脚本和 r12 两个独有提交，不扩大本次合并范围。 |

## 五、修正后的执行顺序与回退触发条件

### 5.1 窗口前：完成可签的执行单

1. 固定发布对象。制作新配置副本及逐项差异，列出服务、端点、制品、有效依赖、读写状态、启动账号和数据位置。补齐 18084；如 rag-qa 或其他服务实际纳入切换，也须列明和验证。运行目录与数据目录分别固定，前端整套 `dist` 如纳入发布则绑定完整清单。
2. 在没有旧工作树挂载、不会注册到生产发现或触发生产回调的隔离环境，做一次完整新启动和回退。记录 A7 基线、QA 请求夹具、时间消耗、日志、版本与有效配置。使用实际生效的启动方式和受控凭据来源，避免用无法还原的脱敏 `/proc` 文本充当回退包。
3. 预置数据和回退包，定义最终冻结点、允许写入的资源、切换动作、恢复写入条件及超时。由 TL 和独立 QA 先完成验证，再由 Owner 批准窗口。**删除权限不列为切换前置条件。**

### 5.2 窗口内：先冻结写入，再按依赖切换

| 顺序 | 动作 | 通过条件 |
|---|---|---|
| B1 | 固定当次 PID、端口、配置、基线与回退版本；确认文件和授权未漂移。 | 精确对象与验收件一致，达到窗口起跑条件。 |
| B2 | 暂停入口新增写入、调度和会拉起旧实例的 watchdog；排空工作、回调和租约。按调用图先停受影响的消费者，再停其提供者。 | 最终任务／版本可核对；没有双写和遗留监听。依赖未证明的服务留在其批准范围。 |
| B3 | 做冻结后的最终同步和指针／哈希核对；从预置版本化配置切换运行指向。 | 源数据未被覆盖，目标数据一致，可立即切回旧配置和检查点。 |
| B4 | 先验证存储、发现与模型等实际依赖；启动提供者，等就绪后启动消费者。 | 每步有 PID、入口、制品身份及 readiness 证据。影子若独立，按其专门决定处理。 |
| B5 | 先用真实入口跑只读正负例及受控验收，随后按授权恢复读流量和写入。 | Q8 全部适用项通过，写入后回退条件已验证。 |
| B6 | 值守与观察，核对下一次定时任务、备份、实际启动配置和旧路径引用。 | 约定观察期、实际运行周期和业务验收均通过；另送步骤 6 复核。 |

**时间预算。** 窗口应覆盖排空、最终同步、启动、业务验收、实测回退和安全余量。用演练填写具体分钟数，由业务侧确认最大不可用时间。示例：正向演练 30 分钟、回退 15 分钟、余量 10 分钟，则窗口至少 55 分钟；这不是现场耗时结论。设置最晚决策点＝窗口结束时间减去实测回退预算和余量；到点仍未就绪即回退。建议前 30–60 分钟有人值守，再按 Q10 观察。

**立即停止推进／回退条件。** 制品或配置不符；数据检查点不一致或发现双写；关键服务超过就绪时限；错库、越权、引用失效；关键摄取／检索不可用；超过事先约定的错误率或延迟阈值；到达最晚决策点。读取现有监控与 A7 基线填写阈值。回退先关写入、停新写入者，再按 Q13 选择数据策略，恢复旧制品和配置并复测同源基线。保留失败记录。

### 5.3 步骤 6：退役前最后核对

先验证生产不再依赖待退役对象，达到观察与恢复条件；再对照最终清单审批。把须保留的数据、配置和未提交改动移出待退役范围并验证恢复。逐个处理已满足条件的工作树、再处理其分支；源数据移除、非 main 祖先的本地分支、远端分支分别列明。任何一项不满足只暂停该对象，不把已完成的生产切换回滚成“未执行”。

## 六、分别签署的事项

| 责任 | 切换前 | 切换后／退役前 |
|---|---|---|
| **TL** | 签技术执行单：发布 SHA 与完整制品、有效配置、依赖顺序、数据冻结与检查点、可执行回退及实测预算。 | 签实际启停、变更、同源验收、当前状态、归档和逐对象退役清单。 |
| **独立 QA** | 独立核查相同制品的冷启动、业务正负例、数据恢复及回退，按当前规则签覆盖范围和未通过项。 | 复核生产观察记录、下一次启动路径、原机归档恢复及待删引用。历史测试和本评审均不能代签。 |
| **Owner／授权发布责任人** | 根据技术和 QA 证据，批准窗口、受影响服务、业务停机、数据策略与可接受风险；约定回退触发权限。 | 依据步骤 5 证据单独批准步骤 6，列明工作树、分支、预期 OID、数据处置和保留期；需要强删时单独写明。 |

签署用实际人员或已授权账户，写明时间、对象、适用窗口和证据版本。不能因某个历史环节获得 Owner 裁定而推定本次已获得发布或退役授权。

## 七、红线解除建议

| 红线 | 建议解除范围与时点 |
|---|---|
| 不重启任何服务 | 当前保持。S56-01 至 S56-06 关闭且实际发布授权生效后，按窗口仅允许已列明的服务启停、写入冻结和回退。 |
| 不动 245 MB 数据 | 现有源数据保留。步骤 5 经批准可读取、备份、最终同步并切到独立目标；不得把它理解为可删除、覆盖原始副本。旧源数据处置在步骤 6 明确签署。 |
| 不删分支、不移除工作树 | 步骤 5 全程保持；步骤 6 逐对象核验后由 Owner 单独解除。许可绑定目录、引用、预期 OID 与允许的动作。 |
| 不 `git clean -fdx`，不动 stash | 本次无解除需要。隔离副本恢复与原仓库 stash 变更是两回事。 |

**本轮可立即推进的交付：** 发布制品及依赖清单、快照与有效启动配置、最终数据同步和回退脚本、在隔离环境跑完的 Q8 验收、待退役对象及恢复清单。具备这些证据后，再申请对应授权。

## 附录：原机复跑入口与输入索引

以下为本地核验入口。`REPO`、`RELEASE`、`ARCHIVE`、`OLD_DATA`、`NEW_DATA` 和探针地址由 TL 依据真实部署填写。V5 已用样例验证“同内容通过、内容变化失败”，V7 已用样例验证空仓库独立恢复 v2、r12 与 stash 引用；实际环境仍需复跑。保留退出状态与执行对象；涉及配置和业务响应的原始输出保留在授权环境，对外提供脱敏摘要。附件未提供真实调用请求时，先从实际接口合同和运行配置生成夹具；不猜测路由、请求格式或身份。

### V1｜固定提交、tree 与远端引用

```bash
set -euo pipefail
review_main=14c392a1b72c036e91eca15bd270d4f66999934e
review_candidate=0d3e0c2e341eb6c813c2e9c775ba5f03affb1e94
git --no-optional-locks -C "$REPO" rev-parse HEAD "$review_main^{tree}" "$review_candidate^{tree}"
git -C "$REPO" log -1 --format='%H %P %s' "$review_main"
git -C "$REPO" merge-base --is-ancestor "$review_candidate" "$review_main"
git -C "$REPO" diff --exit-code "$review_main" "$review_candidate" --
git -C "$REPO" ls-remote --refs origin refs/heads/main refs/heads/integrate/converge-main \
  refs/heads/feature/R12-real-rag refs/heads/feat/spectra-theme
```

验收记录保留 `merge-base` 与 `diff` 退出码；远端查询失败不能折算为空。远端变更需重新核对。合并元数据可用 `gh pr view 3 --json state,mergedAt,mergedBy,mergeCommit,headRefOid,baseRefOid` 补验。

### V2｜确切制品与组件覆盖

```bash
set -euo pipefail
git -C "$REPO" ls-tree -r --name-only "$review_main" -- services/rag-java/rag-parent/rag-graph-service
find "$RELEASE/app/services/rag-java" -type f -name '*.jar' -print
# 由 TL 先生成经复核的 RELEASE.SHA256，涵盖实际启用的全部制品，不只 index.html。
(cd "$RELEASE" && sha256sum -c RELEASE.SHA256)
jar tf "$REVIEW_GRAPH_JAR" | rg '^(META-INF/MANIFEST.MF|BOOT-INF/)'
```

以上只证明文件存在、身份和基本包装；须另保存 `rag-graph-service` 对应构建日志、启动命令、运行 PID 与功能输出。Python 运行解释器、模块加载路径、依赖版本以及前端所用配置与资源也绑定该发布版本。

### V3｜实际启动器、进程及间接依赖

```bash
ss -lntp
readlink -e "/proc/$REVIEW_PID/cwd" "/proc/$REVIEW_PID/exe"
ls -l "/proc/$REVIEW_PID/fd"
systemctl show "$REVIEW_UNIT" -p MainPID -p FragmentPath -p DropInPaths \
  -p WorkingDirectory -p ExecStart -p EnvironmentFiles -p After -p Requires -p Wants
systemctl list-unit-files --type=service,timer
systemctl list-timers --all
findmnt -T "$REVIEW_DATA_PATH" -o TARGET,SOURCE,FSROOT,FSTYPE,OPTIONS
```

非 systemd 服务补实际 supervisor、脚本或容器入口；在真实服务账号下核对其 cron 和用户 unit。查 Nacos 生效 namespace/group/dataId/profile 和版本，核对依赖端点及写入路径。对已知启动目录和部署配置用 `rg -l -F -e '/home/szf/data/dev/llmke-v2' -e '/home/szf/data/dev/llmke-r12' -- <已核实目录>`；必要时检查运行 JAR 内配置资源。对于 `/proc/.../environ` 只读取批准的路径／端点键，禁止将完整内容作为外发证据。

### V4｜快照和依赖契约

```bash
rg -n 'LLMKE_V2_(SNAPSHOT|ROOT|GRAPH_ROOT)|LLMKE_(ARTIFACT_STORE|KB_STATE)|current\.json|/health|_load_engine' \
  "$RELEASE/app/services/rag-alg/index_data_service/graph_engine_adapter" \
  "$RELEASE/app/services/rag-alg/index_data_service/kb_ingest_service.py"
git -C "$REPO" grep -n -E 'rag-qa\.startup-check|RetrievalEndpointStartupCheck' "$review_main" -- services/rag-java
```

源码查找后用实际入口配合同源请求核对，不以静态命中证明生效。隔离环境分别关闭真实必需和可选依赖，记录实际有效配置、启动退出码、就绪响应及恢复行为。影子路径和调用者清单也以实际配置及调用日志确认。

### V5｜最终冻结点文件和指针

```bash
# 冻结并排空后，在同一份相对路径清单上比较。不同预期转换单列审查。
set -euo pipefail
(cd "$OLD_DATA" && find . -type f -print0 | sort -z | xargs -0 -r sha256sum --) > "$REVIEW_OUT/old-data.sha256"
(cd "$NEW_DATA" && find . -type f -print0 | sort -z | xargs -0 -r sha256sum --) > "$REVIEW_OUT/new-data.sha256"
diff -u "$REVIEW_OUT/old-data.sha256" "$REVIEW_OUT/new-data.sha256"
find "$NEW_DATA" -name current.json -print
```

另核对目录、权限、链接和真实指针落点。此命令只比较文件，不能证明跨存储事务一致。同步及重新开放写入必须依业务检查点；源目录如仍在写，停止用此快照做最终验收。

### V6｜真实入口请求样例

```bash
# REVIEW_CURL_AUTH 为经审核的本地认证配置；响应和请求夹具留在隔离、受权目录。
curl -sS --connect-timeout 3 --max-time 30 -o "$REVIEW_OUT/health.json" -w '%{http_code}\n' \
  "$REVIEW_GRAPH_BASE/health"
for review_kb in kb_9 kb_1004 kb_nonexistent; do
  jq -nc --arg kb "$review_kb" '{spaceName:$kb}' > "$REVIEW_OUT/$review_kb.request.json"
  curl -sS --config "$REVIEW_CURL_AUTH" --connect-timeout 3 --max-time 60 \
    -H 'Content-Type: application/json' --data-binary "@$REVIEW_OUT/$review_kb.request.json" \
    -o "$REVIEW_OUT/$review_kb.response.json" -w '%{http_code}\n' \
    "$REVIEW_GATEWAY/graph/search/v2WholeGraph"
done
```

成功收响应不等于通过；须断言状态、真实 KB、版本、正向锚点与负例。另准备无权身份及摄取、回调、查询、引用、回退夹具，全部沿实际调用链，不在生产做未经授权的写入。

### V7｜归档、可达性与退役复核

```bash
set -euo pipefail
git --no-optional-locks -C "$REPO" worktree list --porcelain
git -C "$REPO" for-each-ref --format='%(refname) %(objectname) %(upstream:short)' refs/heads
git -C "$REPO" stash list --format='%gd %H %gs'
# REVIEW_TIP 为逐个待审本地或实际远端引用的固定完整 OID。
if git -C "$REPO" merge-base --is-ancestor "$REVIEW_TIP" "$REVIEW_FINAL_MAIN"; then
  printf '%s\n' 'ancestor_check_exit=0'
else
  review_ancestor_rc=$?
  printf 'ancestor_check_exit=%s\n' "$review_ancestor_rc"
  test "$review_ancestor_rc" -eq 1
fi
git -C "$REPO" log --format='%H %s' "$REVIEW_FINAL_MAIN..$REVIEW_TIP"
(cd "$ARCHIVE" && sha256sum -c SHA256SUMS)
# REVIEW_AUDIT_REPO 为批准使用的全新隔离目录，不引用源仓库对象库。
git init --bare "$REVIEW_AUDIT_REPO"
git -C "$REVIEW_AUDIT_REPO" bundle verify "$ARCHIVE/git-objects.bundle"
git -C "$REVIEW_AUDIT_REPO" fetch "$ARCHIVE/git-objects.bundle" \
  refs/heads/feat/spectra-theme:refs/review/v2 \
  refs/heads/feature/R12-real-rag:refs/review/r12 \
  refs/stash:refs/review/stash
git -C "$REVIEW_AUDIT_REPO" fsck --full
git -C "$REVIEW_AUDIT_REPO" rev-parse refs/review/v2 refs/review/r12 refs/review/stash
```

另按实际 `converge_archive.py restore` 的隔离约束重演工作区恢复，校验当前状态、文件内容、删除项及忽略项，核对归档的凭据保护和数据恢复。独有提交逐项审阅，不能只比提交数量；没有证据覆盖的对象不得清理。本附录无生产启停或删除命令。

### 随附材料与未附证据

| 材料 | 本次使用 |
|---|---|
| `REVIEW-REQUEST-PROMPT.md` | 采用“完整版提示词”的范围与七节输出。 |
| `REVIEW-PACKAGE-STEP5-6.md` | 评审 §6–§8，抽核 §3–§5。 |
| `evidence.zip` → `evidence/` | 检查完整性并交叉核对代码、构建、冷启动、路径、恢复与可达性日志。SHA256：`d76aacdab0f321d853d6a5bf2753b3adc1629697fd8f86bae4438a5c741ea7e4`。 |
| `LLMKE_main收敛方案_独立评审_V1.0_20261108.md` | 沿用裁定 A、§五步骤 5／6 条件和 G02/G03/G05/G06 证据要求。 |

需现场取得：实际 `BOUNDARY.yaml` 与交接／授权原件、签署记录、A5 生效配置和依赖清单、A6 可恢复的旧制品与启动配置、A7 同源基线、真实归档与恢复报告、图／影子最终一致性点、新制品完整功能及回退证据。这些由 TL 在原机整理，独立 QA 复核，无须把未脱敏生产数据或凭据发给评审者。

本次只评最后两步的执行方案，不重开 A/B 方案选择。
