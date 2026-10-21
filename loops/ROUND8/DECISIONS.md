# ROUND8 决策记录

## D1 采用独立 worktree 而非原分支
- 原因：r5 候选证据绑定原工作树的文件内容；在原树写代码会让 r5 立即 STALE，而 r5 正等 QA 签署。
- 做法：`git worktree add ../llmke-r8 -b round8/delivery HEAD`，所有实现落在独立树。
- 结果：原树 `evidence-check --loop r5` 仍 PASS；main 未动。

## D2 选择「引用证据组装器」作为最小纵向切片
- 判据：① 输入输出由冻结契约强约束（`Evidence/DocumentEvidence/SourceRef/Offset`）；
  ② 不依赖未决 DDL、权限策略或容量阈值；③ 可在本地端到端跑；④ 对 L1 有真实复用价值。
- 拒绝的候选：PDF 解析（两臂不可运行）、接口迁移（需运行时证据）、索引代次（需四套存储）。

## D3 不做 555 行的批量 AI 建议（本轮）
- 原因：无明确建议口径时批量贴标签，会把"推断"包装成"建议"，与项目纪律冲突。
- 处理：登记为 BLOCKED_EXTERNAL，需先定口径（见 WORK-LEDGER R8-T03）。

## D4 未改任何门禁与 P0 状态

## D5 自纠：NEXT-SESSION.md 触犯「宿主绝对路径」规则
- 现象：`security-check` 报 5 处 `PERSONAL_ABSOLUTE_PATH`，全部在本轮新写的续跑文件里。
- 处理：改为 `~/` 写法；重跑门禁确认通过。
- 教训：门禁对"文档"同样生效，续跑文件也必须遵守产物规范。

## D6 入口脚本必须识别工作树（否则会"跑错地方还显示绿"）
- 现象：在 `llmke-r8` 里直接 `make framework-verify` 失败（`openapi_spec_validator` 缺失，
  R-02 的 conda 解释器问题）；而 `coordination/mk.sh` 旧版固定 `cd` 到 `llmke` 主库，
  在 r8 调用会静默跑成主库的门禁。
- 处置：`mk.sh` 与 `verify-all.sh` 改为「优先用当前目录（须含 Makefile + scripts/loop_guard.py + VERSION），
  否则回退主库」，并把 `root=` 打到 stderr，避免跑错地方。
- 复验：在 r8 执行 `mk.sh framework-verify` → exit 0 / 145 passed（`[mk] root=.../llmke-r8`）。

## D7 r8 的代码新增不会让 r5 证据失效（P-03 的实际效果）
- 事实：在 r8 工作树执行 `verify-all.sh`，`evidence-check --loop L0-contract-baseline-r5` 仍 PASS。
- 原因：`digest_scheme=2` 只绑 `control_digest`（契约/策略/门禁），`modules/` 属业务代码不在控制面；
  `doc_digest` 仅对 `traceability_gate` 生效。
- 含义：开发期新增业务代码不会反复作废候选证据；但**合并仍需「拟合并树 == QA 审查树」**，
  所以这不能用来绕过 QA。

## D8 模块测试目前不在 framework-verify 里（已确认，暂不修）
- 实测：`grep -n modules Makefile` 无任何命中；`modules/citation_evidence/tests` 的 35 条
  只能靠 `PYTHONPATH=$PWD pytest modules/...` 手动跑。
- 为什么不能顺手改：`Makefile` 在冻结清单内（`FROZEN-MANIFEST.files` 含 `Makefile`）。
  加一个 target 就改变 `control_digest`，会让 r5 的 7 条门禁与 QA 候选**整体 STALE**。
- 结论：这是真实缺口，但修复必须放在下一次受控冻结窗口里，与"建批次 + 一次收口冻结"合并做，
  否则用一次候选作废换一个 make target，不划算。
- 记入待办：`W-01 把 modules/**/tests 纳入 framework-verify`（依赖：下一次冻结窗口授权）。

## D9 集合级校验的边界（本轮实现）
- 新增 `check_evidence_set` / `assemble_many` / CLI `assemble-set`，只做**加法**，
  不改变 `build_document_evidence` 与冻结契约的既有语义。
- 三个新错误码都可机器判定：`DUPLICATE_EVIDENCE_ID`、`SAME_CHUNK_OVERLAP`、
  `CROSS_CHUNK_OVERLAP`；空集合报 `EMPTY_EVIDENCE_SET`，不返回"零证据的成功"。
- 已知局限（不隐瞒）：跨文档的重叠不检测（不同 file_id 允许相同区间）；
  跨 chunk 重叠只能靠**区间相交**发现，若上游切分器给出不重叠但内容重复的块，本校验看不出来
  —— 那种情况要靠 `content_hash` 比对，不在本切片范围。

## D10 parser_version 混用 = 坐标系不可比（本轮实现）
- 判据：`offset` 是码点下标，其**含义**由解析器版本决定。同一 `(kb, file, document_version)`
  下出现两个 `parser_version`，等于同一版本文档存在两套坐标系。
- 处置：集合级直接失败 `PARSER_VERSION_MIXED`，**不在本地折算/对齐**。
  理由：折算需要知道两个解析器版本之间的字符映射，本地猜一个偏移会让"看似修好、实则错位"，
  这在引用回填场景比直接失败危险得多。正确修法在上游：解析器变了就升 `document_version`。
- 顺序：先查版本混用，再查区间重叠 —— 坐标系不可比时重叠判定本身失真，报重叠会误导。
- 边界：不同 `file_id` 允许各自带不同 `parser_version`（多文档检索正常场景），不误伤。

## D11 W-01 实施：窄绑定，不并控制面
- 业主选乙：放弃 r5，W-01 与建批在同一次冻结内完成；批准 `Makefile`/`baseline_support.py`/`loop_guard.py`。
- 结果：门禁内测试 145 → **193**；`DIGEST_SCHEME=3`；`code_digest` 仅被 `independent_qa_gate` 比较。
- 关键验证：`modules/**.py` 追加一行注释 → `evidence-check` **FAIL**（`implementation code changed`）；
  同一实验在 W-01 前是 PASS —— 差异即"绑定生效"的证据。
- 刻意不做：不把业务代码并入 `control_digest`；不改 `VERSION`（W-01 不改契约与 pass 条件）。

## D12 W-01b：evidence-check 曾跳过 QA_PENDING（假绿通道）
- 现象：r6 已产出 QA 候选后改代码，`evidence-check` 仍打印 PASS。
- 根因：`evidence_errors` 有 `if status!='pass': continue`，QA 候选记录整条被跳过；
  真正拦截只发生在 `accept_qa`。
- 修复：`QA_PENDING` 也参与 `stale_reasons`；仅 `pass` 记录才要求签名。
- 代价：修复改动了 `loop_guard.py`，r6 记录绑定的是 revision 7 → r6 置 `SUPERSEDED`，重建 r7。
- 教训：**验收实验必须前移到冻结之前**（与 r3 卡死同一类错误）。

## D13 R-02 又一次：run_batch 直接调 make 也会取到 conda 解释器
- 现象：`python3 scripts/run_batch.py` 在 conda shell 下跑 r6 门禁，`contract_generate_gate` 报
  `ModuleNotFoundError: openapi_spec_validator`。
- 原因：`run_batch` 内部 spawn `make`，子进程 PATH 不是 `.venv`。
- 处置：调用前 `export PATH=~/data/dev/llmke/.venv/bin:$PATH`；长期根治仍待 R-02 提案（Makefile 内固定解释器）。

## D14 业主裁决：弃 r7，直接上补丁包
- 理由：r7 的价值已兑现（193 passed + code_digest 绑定实证）；签名等外部，
  而新批能一次覆盖"9 条门禁 + R-02 根治 + W-04 回归测试"，一次 QA 抵两次。
- 执行：`coordination/window-apply.sh`（仓外脚本，先隔离验证）→ r7 置 SUPERSEDED，建 r9。
- 结果：门禁 8→9；framework-verify 194 passed；evidence-check PASS；p0-gate 仍 2。

## D15 自纠：授权留痕不完整导致 r8 作废
- 事实：应用补丁包时，`BASELINE-AUTHORITY.change_list` 仍只有 `W-01`，
  没有记录 W-05/W-05b/W-02/W-04。r8 冻结后才发现，按其设计属元数据不完整。
- 处置：趁 r8 未签名，补录 `W-02-W05` 条目 → r8 置 SUPERSEDED → 建 r9 → 重跑 9 条门禁。
- 代价：多一个终态批次 + 一次 9 门禁重跑（约 2 分钟）。
- 教训：**补丁包里应当包含授权条目**。凡是"代码改了、authority 没改"，就是 P-04 想避免的
  "元数据与事实不一致"。已把该条加入窗口脚本的待办（下个窗口把 authority 变更也纳入 bundle）。

## D16 P0 闸门红队审计：14/14 拦住，未发现绕过路径
- 动机：四项 P0 是业务唯一硬阻塞，若"填空文件就能置 CLOSED"，则 p0-gate 是装饰品。
- 做法：/tmp 造最小 root，构造"除签名外全绿"的基线，再逐点破坏，断言 check() 必须指向该缺陷。
- 结果：CLOSED 空证据、错 blocker_id、假 snapshot、少答 decision、answer 缺证据、
  哈希不符、空文件、非 PASS 测试、无 approval、ACCEPTED_RISK 无 waiver、删项、篡改 owner/blocks —— 全部拦住。
- 自纠：A10 首轮报 MISSED，实为我断言字符串写错（找 waiver_ref，而错误信息是
  "accepted risk requires separate waiver"）；改正后 14/14。
- 覆盖不到：伪造签名（需私钥）、证据内容真伪（需人工复核）、过期签名窗口。
- 已知不一致（只登记不改）：P0-CLOSURE.yaml 的 baseline_version 仍 1.1.0；
  该文件在 doc_digest 内，改动会让 traceability_gate STALE，故留待窗口处理。

## D17 自纠：审计脚本写死宿主路径，被 security-check 当场拦下
- 现象：把红队脚本入库后，`make framework-verify` 变成 exit 2：
  `PERSONAL_ABSOLUTE_PATH: /home/<user>/`（`docs/baseline/validation/p0-gate-redteam-audit.py:11`）。
- 原因：脚本里写死 `Path("/home/…")` 指向仓库根；`docs/**` 虽不参与 control/doc 摘要，
  但 `security_scan --all-files` 会扫它。
- 处置：改为 `Path(__file__).resolve().parents[3]`；复跑 14/14 仍通过；framework-verify 回 exit 0。
- 补充（同日第二次）：连"引用错误信息"也会带宿主路径——我在本节原样粘贴了报错文本，
  于是 `DECISIONS.md` 也被 security-check 判红。已在文档里改用 `/home/<user>/` 占位。
  结论：**引用报错时一律脱敏**，否则修一个、红一个。
- 意义：这是**门禁自己抓到维护者的违规**，说明 P-01 的豁免只放宽了证据日志，
  没有把文档/脚本里的宿主路径一起放宽——正是当初坚持"只放宽一类"的价值。

## D18 预防：仓外预提交检查（不再靠"记得脱敏"）
- 一天内两次同类违规（脚本写死路径、文档粘贴报错文本），都是事后由 security-check 发现。
- 新增 `~/data/dev/coordination/pre-commit-security.sh`：只扫**已暂存**的文本文件，
  命中宿主路径即拒绝提交并给出脱敏建议；随后再跑整树 `make security-check` 做权威判定。
- 已实测：暂存正常文档 → OK；暂存含 `/home/<user>/` 的文件 → 拒绝并打印行号。
- 支持 worktree（`.git` 为文件的情况）。**未自动安装为 hook**——是否挂到 `.git/hooks/pre-commit`
  由维护者自行决定，脚本内注释给了安装命令。

## D19 P0-02 仪器：先造尺子，等材料
- 台账事实：37 表 / 482 字段 / `actual_ddl_sha256` 全为 null / `CANDIDATE_ONLY_REQUIRES_SOURCE_OR_DDL`。
- 产出 `p0-02-ddl-diff.py`：表集合差异、逐表列数漂移、DLL 指纹（可回填台账）、引擎/字符集。
- 关键设计：指纹先规范化（行尾空白/连续空白/CRLF）再哈希；否则同一张表两次导出得到不同指纹，
  回填台账后无法复现。已用"缩进+CRLF"夹具验证哈希一致。
- 验证：完整匹配 0；缺表/多表/列数漂移均 exit 2 并点名；`--ignore-count-drift` 降级为提示。
- 诚实边界：不判类型/长度/索引/语义——台账没有这些基线，硬判会产生假结论。

## D20 找到真实源码与上游清单，两项仪器从"猜"变成"跑"
- 源码：`~/data/repo/RAG-SRC/_src/gien-rag/gien-rag/rag-parent`（1003 个 java）。
- 上游：`docs/upstream/` 有接口总表 CSV（506 = Java 440 + Python 66）与字段明细 CSV（482 行）。
- P0-01 实测：排除 27 个 Feign 客户端后，源码活路由 440，清单 Java 440；
  清单有源码无=1（`/ai/getRerankModelInfos`，注解已在 `AiController.java:135` 注释掉，
  清单还把它记成 `audioUploadAndIdentify`）；源码有清单无=1（`/version/getCurrentVersion`）。
  两个 440 相等是巧合、差异方向相反互相抵消 —— 总数核对会得出"清单准确"的错误结论。
- P0-02 升级为字段级：接入字段明细 CSV，能判列名/类型长度/可空，4 类差异均验证。

## D21 仪器自身的三次假差异（都已修）
- 处理函数取到 `@OperationLog` → 198 条假 HANDLER_DIFF；
- 无 class 声明时起始下标误设为 len(matches) → 注释路由永远为 0；
- `@GetMapping` 可无括号 → 漏 3 条 `/roleResource`，把清单误判成多记。
结论：工具也会造假差异，每条差异都要回到源码行确认。

## D22 P0-02 基线换源：ORM 注解取代二手 CSV
- 发现：`docs/upstream/数据库表结构-字段明细.csv` 是从 DO 推导的二手材料，且不忠实：
  81 处不符 = 29 条用 Java 字段名（re_embedding_* 三表）+ 7 个 `@TableField(exist=false)` 被当列 + 13 处类型/长度不符。
- 权威来源：`@TableName/@Column(name,type,length,isNull,isKey)`，实体 37 表 / **491 列**（CSV 482）。
- 端到端：实体基线 ↔ 实体生成 DDL = **PASS 0 差异**；旧 CSV 基线 ↔ 同一 DDL = **FAIL 85 差异**。
  同一份 DDL 因基线不同得出相反结论 —— 基线选择决定结论。
- 类型差异两个方向都有（既有 CSV 偏小会截断，也有偏大浪费），不能假设"按 CSV 建表就安全"。
- 降噪修掉 5 个自身缺陷（显示宽度、单侧长度、可空三态 ×2 个工具、带初始值字段漏解析），
  其中"可空三态"在两个工具里都要一致，否则各自通过、合起来错。

## D23 create_by 语义定案（代码级证据）
- 结论：`create_by` 存的是**登录账号 user_name 字符串**，不是用户 ID、不是姓名。
- 五源一致：@Column(comment="创建人") + CustomMetaObjectHandler(getUserName()) +
  各 Repository setCreateBy(userName)（15 处，无一处用 ID）+ XML `create_by=#{userName}` +
  查询侧 `.eq(...getCreateBy, userName)`；`user_info` 无 user_id 列。
- 迁移风险：create_by 长度 30×6/50×19/128×4/**255×1**(DepartmentInfo)；
  更新人列名分裂 update_by×23 / modify_by×7；30/37 表有 create_by，7 张没有。
- 例外：3 处更新时复制 `old.getCreateBy()`（不覆盖创建人），迁移回填若写"当前操作人"会破坏语义。
- 代码答不了、需 owner 裁定：账号可否改名及历史值处理、跨系统账号唯一性、缺失 7 表是否补列、列名是否统一。

## D24 表耦合实测：9/37 跨服务 + 1 张双实体
- 跨服务读写的表 9 张，且**双向**：权限表被索引服务读（5），业务表被权限服务读（4）。
- `user_operate` 有两个 DO（auth 显式 @Column / common 隐式驼峰），任一侧改动另一侧不报错。
- 对 D-01 的含义：选独立新库时，成本集中在"拆这 9 张表的写路径"，而不是"建 37 张表"；
  且必须先定 `user_operate` 以哪份实体为准。
- 注意：`user_operate` 有 user_id 列，但不影响 "dialogue 无 user_id" 那条（不同表），不可外推。
- 下一步（已写入文档）：按语句类型拆分读/写，成本量级差别更大。
