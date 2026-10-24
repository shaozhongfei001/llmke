# ROUND9 决策记录

## D-R9-01 本轮只做"能跑的链路"，不做文档轮
- 事实起点：模块已有 authz / chunk_store / citation_evidence / citation_flow / index_generation，
  链路做到"检索 → 证据"；**缺"答案与接口输出"**，因此真实请求无法被应答。
- 决定：第一优先补 `modules/answer_api/`，贯通 query → 授权取块 → 证据 → 答案 + 引用 + 审计字段。
- 约束：P0-03 未关 → 授权规则只能标候选；任一缺失一律 fail-closed（拒绝，不降级为"空答案"）。

## D-R9-02 答案层不调用真实 LLM
- 本轮答案文本由证据确定性拼装（模板），不接模型：模型调用不可复现、会把未授权内容带进上下文的风险外包给提示词。
- 接口形状按真实需要考虑（citations/audit/policy_version），将来替换成模型时**不改变响应契约**。

## D-R9-03 答案层落地（R9-T02/T03，VERIFIED）
- 新增 `modules/answer_api/`：`service.py`（纯逻辑）、`sql_adapter.py`（SQL 与执行器分离）、`cli.py`（可运行入口）。
- 结果契约固定为 `answer{text,claims[]} + citations[] + audit{} + policy_state`，
  其中每条 claim 必带 `evidence_id`；`policy_state=CANDIDATE_NOT_RELEASEABLE` 恒在（P0-03 未批）。
- 关键负例（12 条）：
  - 越权块 → `CHUNK_OUT_OF_SCOPE`，且**报错不回显 file_id**（否则报错成为越权探测工具）；
  - 0 条证据 → `NO_EVIDENCE`（不返回"空答案成功"）；
  - 跨文件只给一份全文 → `DOCUMENT_TEXT_MISSING`（防止用 A 文件文本切 B 文件偏移）；
  - 重叠 / 重复 id / 解析器混用 → 复用集合级校验；
  - 篡改库内文本 → `CHUNK_TEXT_MISMATCH`。
- 真库 5 条：授权谓词生效（只看到 f-1）；`chunk_ids=['k2']` 收窄不能放宽（0 行 → 拒绝）；
  整库授权 + 单文件原文 → 拒绝；换授权到 f-2 后可正常回答（防止"拒绝一切"式假安全）。
- 门禁：`make framework-verify` rc=0 / **275 passed / 0 skipped**（252 → 275，新增模块被自动收集）。

## D-R9-04 本轮不接真实模型
- 答案文本由证据确定性拼装，目的是可复现与可断言；接模型会引入不可复现与非确定性，
  且"未授权内容是否进上下文"不该外包给提示词。
- 契约不变，将来替换为模型时只换 `answer.text` 的生成方式，`claims/citations/audit` 不动。

## D-R9-05 r11 因新增代码转 STALE（设计内，不是缺陷）
- 现象：`evidence-check --loop r11` → `FAIL: independent_qa_gate: implementation code changed; evidence STALE`。
- 原因：r11 的 QA 门禁记录含 `code_sha256`（W-01 引入的窄绑定），本轮新增 `modules/answer_api` 改变 `code_digest`。
- 判定：**符合设计**——改业务代码就该让"声称审计过那版代码"的证据失效。8 条开发门禁仍 pass。
- 影响：r11 不能再作为发布候选（它本来也无私钥可签，无额外损失）。新批次留到本轮阶段 D 一次性建立，
  避免"每改一处就重冻结"（这是 r6/r8 的返工来源）。
- 口径：不得因为本轮代码已过 282 条测试就宣称 r11 有效。

## D-R9-06 口径索引首次运行即暴露自身缺陷
- 首版用 `str.split(',')` 解析 `WORK-LEDGER.csv`，带引号的字段被拆开，ROUND8 的 27 行全被判"格式错"。
- 改为 `csv` 模块后正确；同时发现 ROUND8 ledger 的 `state` 列是**自由文本而非枚举**，
  因此任务计数改以 `STATE.json` 为权威，不再从 ledger 推断。
- 结论：统计口径必须只有一处实现（`coordination/round9-index.py`），否则每处都会算出不同的数。

## D-R9-07 相关性筛选：默认关闭，显式开启（R9-T06）
- 打分用 CJK bigram + 拉丁词覆盖度，确定性、可写 golden 断言；不引入向量/模型（不可复现）。
- `rank=False` 为默认：现有调用方行为不变；开启后丢弃项必须写进 `audit.dropped_chunks`，
  不允许"静默筛掉"——否则复盘时无法回答"为什么这条证据没进答案"。
- 全无关 → `INSUFFICIENT_RELEVANCE`（拒绝），而不是返回一条没有依据的答案。

## D-R9-08 同文件多版本并列引用 = 重复计数（R9-T07）
- 缺陷：集合级校验以 `(kb,file,document_version)` 为"文档身份"，因此**同一文件的 v1 与 v2
  被当作两份文档**，重叠检测失效，答案会把新旧版本同时引用，读者看到的是重复依据。
- 处置：`MIXED_DOCUMENT_VERSION` 显式拒绝；正确修法是上游只保留一个有效版本（属检索/代次职责）。
- 局限（如实）：本守卫只能发现"一次答案里混版本"；跨请求的版本漂移仍靠 generation 指针约束。

## D-R9-09 代次守卫只能"按版本对齐"，这是 schema 缺口（不隐瞒）
- 实测：`document_chunk` **没有 `generation_id`**（schema V1.3 第 679–699 行），只有
  `document_version`。因此"某块属于哪一代"没有直接证据。
- 本轮实现（`fetch_chunks_active`）：相关子查询取激活指针指向的代次，要求 `state='ACTIVE'`，
  且 `c.document_version = g.document_version`；指针缺失/状态不符 → 子查询为 NULL → 0 行 → 拒绝。
  这条路径是 fail-closed 的（不降级为"用最后一版"），已用真库 4 条测试锁定。
- **局限（登记，不当作已解决）**：同一 KB 内若不同文件处于不同版本代次，本守卫无法区分；
  严格说它证明的是"版本对齐"，不是"块属于该代次"。
- 正确修法：`document_chunk` 增 `generation_id`，或建 `chunk_generation(chunk_id, generation_id)` 映射；
  属 P0-04（设计仍 PROPOSED），需 index-owner 裁定。已登记 `R9-T09 BLOCKED_EXTERNAL`。
- 教训：这一处如果只在 Python 里"取回后再过滤"，旧代次内容会先进内存与日志，
  违反"未授权内容不进入上下文"的不变式——所以必须做在 SQL 里。

## D-R9-10 P0-02 dry-run：37/478 → 43/538 的差异被完整解释（但仍未关闭 P0-02）
- 输入全部来自仓内产物：`target-schema-v1.sql`、`schema-v1.3.sql`、`target-schema-v1-mapping.csv`；
  不重跑 ORM 生成器（它要 `--src` 指向仓外 Java 源码，路径一变数字就不可复现）。
- 实测：
  - 旧目标 schema **37 表 / 478 列**；v1.3 **43 表 / 538 列**；
  - 差异 = **6 张新表 / 60 列**：`document_chunk`、`document_evidence`、`index_generation`、
    `index_generation_activation`、`index_outbox`、`index_write_lease`；
  - 原 37 表**列集合完全未变**（0 新增、0 删除、0 类型变化）。
- 顺带修正一处长期口径偏差：映射文件 **480 行 = 478 个真列 + 2 条注释**
  （`seq（去掉 AUTO_INCREMENT）`、`(merged into table_file_paths)` 被写进了 `new_column` 字段）。
  工具首版把 `retrieve_recall_Param` 也当注释（正则只允许小写），已修正为大小写兼容。
- **仍未回答**（故 P0-02 保持 OPEN，登记 `R9-T10 BLOCKED_EXTERNAL`）：
  真实生产 DDL 是否等于 `target-schema-v1.sql`；37 表遗留库与 ORM 推导是否一致；
  迁移能否在恢复副本上执行；新增对象是否有业务需求或 owner 决策支撑。

## D-R9-11 outbox：用 `next_attempt_at` 兼任可见性超时（不改 schema 的近似解）
- 现状缺口（实测）：`index_outbox` 只有 `state/attempts/next_attempt_at`，
  **没有 `claimed_at`/`lease_expires_at`**；schema 注释写的状态是 `PENDING/SENT/FAILED`，
  而代码一直在用 `SENDING` —— 注释与实现不一致。
- 本轮实现：领取时写 `next_attempt_at = NOW()+lease`，回收时判 `state='SENDING' AND next_attempt_at < NOW()`。
  这样"消费者崩溃后卡住的 SENDING"变成**可判定**的，而不是永远卡住。
- 语义代价（如实）：无法区分"慢消费者"与"已崩溃"，只能靠租约时长近似；
  回收后可能重复投递（至少一次），下游必须幂等。
- 已测（真库 3 条）：领取后不可重复领取；`mark_sent` 后为 SENT 且不可再领；
  失败退避 4 次后第 5 次落 FAILED（attempts=5）；租约到期可回收并重新领取（attempts 递增）。
- 登记 `R9-T12 BLOCKED_EXTERNAL`（index-owner）：加 `claimed_at`/`lease_expires_at` 与统一状态枚举。

## D-R9-12 实测：证据能证明"树没变"，不能证明"验证脚本没变"
- 实验（`coordination/r9-digest-gap-probe.py`）：在 `docs/baseline/validation/schema-verify.sh`
  末尾追加一行注释 → `control/code/doc` 三个摘要**全部不变**，`evidence-check` 仍判有效；还原后一致。
- 原因：该脚本位于冻结排除前缀，而它不是"文档"，是**被当作验证命令执行的程序**。
  排除前缀的本意是"说明性文件不参与摘要"，现在被一个可执行文件占了位。
- 同理：解释器版本（3.12.13）、MySQL 版本（8.0.41）、已安装包集合，都不在任何摘要内。
  同一棵树在不同环境可能得到不同结论，记录却完全一致。
- 边界（不夸大）：`make framework-verify` / `p0-gate` 的入口在 `Makefile` 与 `scripts/`，
  都在控制面内，改它们会让摘要变化；本缺口针对"被当门禁执行的排除前缀脚本"与"运行环境"。
- 建议修法：门禁记录增加 `command_digest`（B），并把脚本移入 `scripts/`（A）；两者同窗口做。
  已登记 `R9-T14 BLOCKED_WINDOW`，本轮只测不改。

## D-R9-13 command_digest 可行性已验证（仍未实施）
- 探针 `coordination/command-digest-probe.py`：取门禁 argv → 解析解释器与脚本 → 对命令闭包
  （脚本 + 脚本内一层引用的本地文件）算 sha256 → 一次可控改动后复算。
- 实测：改 `schema-verify.sh` 时 `command_digest` **变化**，而 `control/code/doc` 三个摘要**全不变**；
  `git checkout` 还原后两者都回到原值。这正好补上 R9-T13 暴露的洞。
- 局限（写进探针文档）：只覆盖 argv 里显式出现的脚本；不解析动态 import 与环境变量展开；
  解释器只取版本号不取二进制哈希（跨机可复现更好，但弱于内容哈希）。
- 状态：`VERIFIED_DRYRUN`。落地需改 `loop_guard`/`baseline_support`（控制面），
  与 R9-T14 同窗口做；本轮不动，避免作废候选。

## D-R9-14 "索引未就绪"必须与"查无结果"分开
- 现状：`fetch_chunks_active` 在无激活代次/状态不符时返回 0 行，上层一律报 `NO_EVIDENCE`（422）。
- 问题：切换中断时运维会去查业务数据，而真正原因是索引没激活。
- 处置：新增 `probe_active_generation`；取数为 0 行时区分两种原因 → `INDEX_NOT_READY`（503），
  其余仍是 `NO_EVIDENCE`（422）。真库测试同步改判（原用例期待 0 行，现期待 503 语义）。
- 注意：这不是放宽——两种情况仍然都是拒绝，只是错误码与排查方向不同。
