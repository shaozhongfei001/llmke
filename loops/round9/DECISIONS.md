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
