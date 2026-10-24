# ROUND10 决策记录

## D-R10-01 切片选择：HTTP 入口（而不是再加模块内能力）
- 事实：`modules/answer_api` 已有 query→授权取块→证据→答案，但**没有任何 HTTP 入口**
  （全仓 `grep http.server|BaseHTTPRequestHandler|FastAPI|flask` 无命中）。
  也就是说：这条链只能被测试调用，真实请求进不来。
- 决定：本轮第一条切片做 `modules/answer_api/server.py`（仅标准库，不引新依赖），
  贯通 请求 → 授权上下文 → 取块（ACTIVE 代次）→ 证据 → 答案 → 状态码 + 审计行。
- 约束：P0-03 未批准 → 授权上下文只能按"网关已鉴权"的接入口径接受，结果恒带
  `policy_state=CANDIDATE_NOT_RELEASEABLE`；不得声称这是生产鉴权。

## D-R10-02 入口层不做身份认证（边界写死）
- 授权上下文来自 `X-Authz-*` 请求头，本层**只校验结构与时效**，不做验签。
- 生产上这些头必须由受信网关签发、客户端直连由网络层阻断；否则任何人伪造头即可越权。
- 因此响应恒带 `policy_state=CANDIDATE_NOT_RELEASEABLE`，且 `HANDOFF.md` 明写该边界。
- 决定：不自行实现"网关签名校验"（无公钥、无 E1 规范，属 P0-03），避免造一个看起来安全的假鉴权。

## D-R10-03 500 兜底必须留"异常类型"日志（自纠）
- 首次跑测试时 3 条用例返回 500，客户端只看到 `INTERNAL`，无任何线索；定位花了一轮。
- 处置：服务端在兜底分支写一行 `internal error: <ExceptionType>` 到 stderr（不含消息与栈），
  客户端仍只看到 `INTERNAL`。既不外泄，也不让 500 变成黑洞。
- 同时修了测试自身的缺陷：假执行器按 SQL 形状分流时，chunk 查询含相关子查询 `g.document_version`，
  被误判成代次探针，返回一行版本号 → `IndexError`。判据改为先看 `SELECT chunk_id`。

## D-R10-04 干净树复跑：审查对象 == 执行对象（VERIFIED）
- 在 `/tmp/r10-clean`（detach 于 HEAD `eec8b7a`）复算：control/code/doc/baseline 四个摘要与主树
  **逐字节一致**；`framework-verify` rc=0 / 317 passed；`evidence-check r13` PASS。
- 差异仅一处：`security-check` 扫描文件数 844（干净树）vs 857（主树），来源是未跟踪产物——
  它们不进任何摘要，因此不影响结论，但说明"文件数"不是可信指标。
- 价值：以后不能再把"我在开发树跑绿了"当作"审查对象也绿"；两者必须由摘要证明同构。

## D-R10-05 失效矩阵：两条成立、一条如实暴露局限
- A 改 `modules/answer_api/service.py` → `implementation code changed; evidence STALE`（rc=1）
- B 改 `scripts/loop_guard.py` → `frozen control changed ... control surface changed`（rc=1）
- C 改 `docs/baseline/validation/schema-verify.sh` → **rc=0（未失效）**
- C 是已知局限的直接证据：`command_digest` 只绑定门禁 argv 中的脚本，而
  `schema-verify.sh` 是**人工执行**的验证命令。修法（移入 `scripts/` 或加 `record-check`）
  属控制面变更，登记 `R10-T10 BLOCKED_WINDOW`。
- 记录方式说明：探针在干净树内执行并 `git checkout` 还原，未触碰主树工作区。

## D-R10-06 `record-check` 做成已验证补丁（不应用）
- 动机：T09-C 已证明"改排除前缀里的验证脚本，证据仍 PASS"。`record-check` 让人类把这类
  手工验证登记成凭据：argv 闭包摘要 + 退出码 + 日志哈希，复核时逐项比较。
- 验证（隔离树）：3 条测试通过（脚本被改 / 非 0 退出 / 日志被篡改），全量 **320 passed**；
  `baseline` 红属预期（未冻结的补丁树）。`git apply --check` 对 HEAD OK。
- 不应用的理由：`scripts/` 属控制面，应用会让 r13 STALE；本轮已冻结一次，按纪律推迟到
  `R10-T10` 窗口，与"移入 scripts/"一起做。
- 残留局限（不掩饰）：`record-check` 依赖人主动登记；漏登记的命令仍不被绑定。
  彻底解法是把验证脚本移入控制面，而不是靠自觉。

## D-R10-07 应用 record-check：第二次（也是最后一次）冻结
- 判断：r13 无签名路径，留着已知缺口（人工验证命令不绑定）比多一次冻结更糟；
  内容已稳定（补丁在隔离树 320 passed、apply --check OK），符合"内容稳定后一次冻结"的条件。
- 动作：应用补丁 → 冻 `revision 15` → 建 r14（9 条门禁）→ `record-check` 登记
  `bash docs/baseline/validation/schema-verify.sh`（exit 0，命令闭包 `868af275`）→ qa-run 留 QA_PENDING。
- 验证（主树实测）：改 `schema-verify.sh` 一行 → `manual check schema-verify: command changed;
  evidence STALE`（rc=1）；`git checkout` 还原 → PASS（rc=0）。**T09-C 的缺口已闭合。**
- 代价：r13 转 SUPERSEDED（证据保留）；本轮共两次冻结，均因触及控制面，不属反复试错。

## D-R10-08 覆盖审计：还有一条"验证命令"未被绑定，且它与 P0-01 同源
- 审计对象：QA 文档里要求人执行的命令（3 条）。
- 结果：`make framework-verify` = GATE、`make p0-gate` = CONTROL、
  `python3 docs/baseline/validation/p0-01-route-extract.py` = **UNBOUND**。
- 为什么不能立刻补：该脚本需要 `--src`（Java 源码）与 `--csv`，缺参即 `rc=2`；
  而 `record-check` 只接受退出码 0 的命令（非 0 会让整批证据失效）。
  → 在 P0-01 输入到位前，这条命令**在原理上无法绑定**，登记 `R10-T13 BLOCKED_EXTERNAL`。
- 意义：这是"P0 输入缺失"与"证据绑定"两件事的交点——没有输入，连验证都跑不起来；
  不能靠再写一个工具绕过。
- 工具局限（写进证据文件）：只解析 bash 代码块，正文内联命令不计入，故本审计是下界。

## D-R10-09 演示即验证：两个缺陷只能靠端到端发现
1. **状态码漂移**：`service.py` 抛 `INSUFFICIENT_RELEVANCE`，`handler.STATUS_BY_CODE` 没有它
   → 默认 500。单元测试全绿也发现不了，因为没人断言 HTTP 码与错误码的对应关系。
   修法不是补一行，而是加**静态守卫**：扫描 `AnswerError("CODE")` 必须在映射表内。
   同时发现 `MIXED_DOCUMENT_VERSION`、`UNCITED_CLAIM` 也缺（同批补上）。
2. **审计竞态**：审计写在 `_send` 之后，客户端可能先返回 → 全量门禁里偶发 1 failed。
   改为审计先落盘；测试改轮询。语义边界写进注释：`status` 表示"服务端判定结果"，不宣称送达。
- 教训：**"演示"不是展示，是最便宜的集成测试**。这两个缺陷都逃过了 320 条测试。
