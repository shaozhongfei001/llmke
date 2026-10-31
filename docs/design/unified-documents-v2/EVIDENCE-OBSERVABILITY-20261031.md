# 可观测性收口：指标导出 + 真实告警通道（2026-10-31）

两个新模块 + 一次端到端演练，**演练当场抓出一个只有真跑才会暴露的缺陷**。

## metrics.py：手写 Prometheus 文本

不引入 `prometheus_client`：离线交付每多一个依赖就多一条锁版本/审供应链的链路，
而这里需要的只是"几个计数器写成几行文本"。

三条刻意取舍（都是为了面板不撒谎）：

1. **缺值整条不出现**，不输出 0。没有租约的单实例不该出现 `lease_fencing 0`——
   那会让人以为"有个 fencing=0 的主"，真相是这条序列不存在；
2. **None / nan / inf 整条跳过**。Prometheus 能收 `nan`，但它会穿过 `rate()`/`avg()`
   污染整个查询，面板"有数据"实际全空，比缺指标更难查；
3. **bool 显式转 0/1**（Python 的 `bool` 是 `int` 子类，不拦就输出 `True` 这种非法样本）。

不做直方图：重建耗时没有一手分桶依据，编边界等于编数据。

## alert_sink.py：webhook 通道

`WebhookAlertSink` 的 `__call__` **永不抛异常**（调度器靠这条特性保证"发不出告警 ≠ 服务停摆"），
返回值只给部署侧自检用。重试 `retries` 次、指数退避；去重在**决定发送时**打点而不是发送成功后
——否则 webhook 挂掉时每次重投都会再打一轮，把故障放大成雪崩。

`CompositeSink` 扇出：一个通道配错不该让另一个也收不到。

## 真实 HTTP 200 被记成失败的缺陷（演练抓的）

端到端演练结果很怪：服务端**收到 3 次 POST**，而 `stats` 是 `sent=0, failed=1, attempts=3`。

根因：`_default_post` 返回 `{"status": 200}`（dict），而 `_status_of` 只认 int / 元组 /
带 `status` 属性的对象，**不认 dict** → 每次真实 200 都被判"未确认的响应" → 重试 2 次 →
`failed=1`。也就是说：**告警其实送到了，监控上却显示失败**。

为什么单测没抓到：所有用例都注入 `post` 桩（返回 int 或 None），
`_default_post` + `_status_of` 的真实组合一次都没跑过。这就是桩测试的盲区。

修法：`_default_post` 直接返回 `int(response.status)`；`_status_of` 补 dict 分支；
新增一条用**真实本地 HTTP 服务器**的回归测试（断言 `sent=1 / attempts=1 / 服务端只收 1 次`）。

修后同一演练：

```
alerts=5 → webhook 收到 1 次（4 次被 30s 去重窗口挡下）
sent=1, failed=0, attempts=1, deduped=4
```

## 真实锁等待：客户端超时先到（回答了上一轮留下的问题）

`test_real_mysql_lock_wait_returns_by_read_timeout_not_50s`：另一连接 `SELECT ... FOR UPDATE`
持锁不放（不提交），`acquire` 用 `read_timeout=2`：

- 耗时 `1.0 ~ 15s`，且断言 `elapsed < @@innodb_lock_wait_timeout`（实测服务端 50s）；
- 锁一放掉，第三个实例立刻接管成功（证明失败根因是锁等待，不是连接坏了）。

结论：**客户端 `read_timeout` 先到，不会被服务端的 50s 拖住**。这条从"推理"变成"实测"。

## 演练入口（部署可用）

`scripts/v2_lease_drill.py` 新增 `--metrics-out`（落 Prometheus 文本）与
`--alert-webhook URL`（`on_alert` 同时本地记录 + 真实投递）。

## 还没做

- **服务里没有 `/metrics` 端点**：模块有了，但 answer/graph 服务未挂载，需要部署侧接；
- 告警**不签名、不鉴权**（打算在网关层做）、**不落盘重试队列**（进程死了告警就丢，
  本仓没有可靠本地队列，假装有就是骗人）；
- 只验了本机 HTTP 服务器，**没接企业微信/钉钉/邮件真实网关**；
- 指标无 label 维度（单实例语义），多实例部署时各实例各自统计。
