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
