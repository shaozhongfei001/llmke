# 阶段 B：把限流接进回答段（2026-11-01）

Q：**49 PASS / 0 FAIL / 0 SKIP / 1 NOT_IMPLEMENTED**（仍是 Office 转换能力缺失）。

## 分工

- 角色（budget-role）：`llm_budget.py` —— 解析 `LLMKE_ANSWER_RATE`、按次计数的 `CallBudget`、
  复用既有 `TokenBucket`，不重写令牌桶；
- TL：接线 `llm_config.resolve/make_llm_call`、端到端演练 `v2_rate_limit_drill.py`、Q 检查。

## 契约（接线方与模块的唯一接口）

```
LLMKE_ANSWER_RATE="6/60"   # 每 60 秒 6 次；不配 = 不限流（保持原行为）
CallBudget.before_call()   # 没额度抛 RateLimitedError（带 retry_after）
CallBudget.stats()         # capacity/refill_per_s/allowed/denied/tokens
```

## 真正跑出来的结果

`scripts/v2_rate_limit_drill.py` 起一个**假 OpenAI 兼容服务**，用真实 `make_llm_call` 打它：

```
不限流：3 次全过，服务端收到 3 次
2/60  ：前 2 次过，第 3 次 RateLimitedError，服务端只收到 2 次
retry_after > 0；describe() 不含密钥明文
```

**"服务端只收到 2 次"才是关键断言**：它证明限流拦在**发请求之前**。
如果只 mock 传输层，就分不清"没发出去"和"发出去了再丢弃"——后者照样计费。

## 三个真实 bug（都在这一轮修掉）

1. **变量遮蔽**：我在 `_call` 外层写了 `budget = cfg.get("budget")`，而 `_call` 内部本来就有
   `budget = payload["max_tokens"]`（max_tokens 预算）。同名让外层赋值变成不可见的局部变量 →
   `UnboundLocalError`。改名 `call_budget` 才通。
2. **演练报告序列化失败**：把 `CallBudget` 对象直接塞进 report，`json.dump` 中途抛错，
   留下**截断的半个 JSON 文件**；Q 读取时 JSONDecodeError 直接把整轮验收带崩。
   修法：只序列化 `stats()`；Q 侧对"文件存在但解析失败"单独判 FAIL 而不是抛异常。
3. **我自己重复犯的引号错**：中文说明里嵌 ASCII 双引号（`"只验"限流"，未验…"`），
   `pytest` 收集时不报，跑几分钟后才在检查函数处炸。加 `tests/test_scripts_compile.py`
   对 `scripts/` 做 compileall——这类错误应该在 0.1 秒内被拦住，而不是几分钟后。

## 边界

- 限流是**单进程内计数**：多 worker/多实例各自一份桶，总配额会被放大（要分布式配额得走 Redis，未做）；
- 重试不计入限流（按"一次回答"计），这是刻意选择：截断重试是同一次回答的一部分；
  但代价是"重试风暴"不会被限流挡住；
- `LLMKE_ANSWER_RATE` 非法值会让 `resolve()` 直接抛错（fail-fast），没有"降级为不限流"的逃生门；
- 只有回答段接入；图重建/embedding 调用未接；
- 未做配额耗尽告警（`stats()["denied"]` 目前只有本地可见）。
