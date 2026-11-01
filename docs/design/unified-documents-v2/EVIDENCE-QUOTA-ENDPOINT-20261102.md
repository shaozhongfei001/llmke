# 配额接进真实请求入口 + 并发验证（2026-11-02）

上一步的 `SharedQuotaCounter` 没有调用方——模块写好却没人用，等于配额不存在。
这次给它一个真实入口，并用**并发**验证（配额最容易错的地方正是并发：两个请求同时读到
`used=limit-1`，就都放行）。

## 入口：`POST /rebuild`

worker 新增 POST 入口（`/rebuild`，可带 `?kb=` 或 `X-KB-Id`）：

| 情况 | 响应 |
|---|---|
| 放了 | `202 {"status":"QUEUED","pending":n,"tenant":...}` |
| 该库配额用尽 | `429 {"status":"TENANT_QUOTA","retry_after_s":...}` + `Retry-After` 头 |
| 全局积压满 | `429 {"status":"BACKPRESSURE",...}` |
| 配了 `--request-token` 但没带/带错 | `401` |
| 没配 coordinator | `503` |

两个刻意的取舍：

1. **被配额拒掉的请求不碰 coordinator**（有测试钉住）。否则限流只是"晚一点被处理"，
   队列照样涨。
2. **配额库不可用时 fail-open + 大声告警**（`build_quota` 返回 None 并在 stderr 说明）。
   配额是保护措施，不是正确性前提；DB 抖一下就把所有重建拒掉，比没有配额更糟。
   这条与租约的 fail-closed 方向相反，是因为两者性质不同：租约错了会写坏快照，配额错了只是少挡几次。

## 并发真跑（真 MySQL + 真 HTTP 入口）

```
30 个并发 POST，limit=5
accepted=5  denied=25  used_in_db=5  coordinator_calls=5  control_tenant_allowed=true
status=PASS
```

四条判据全中：放行数恰好等于 limit；被拒都是 429；**库里 used=5 而不是 30**
（被拒的没有占额度）；另一个租户不受影响。

## 并发压出来的两个问题（都是脚手架/部署问题，不是配额逻辑）

1. **`ConnectionResetError` ×5**：默认 `HTTPServer` 的 backlog 只有 5，30 并发时一部分
   连接被内核直接 RST，看起来像"请求被拒"。两个修法都做了：drill 里调大
   `request_queue_size`，worker 改用 **`ThreadingHTTPServer`**——单线程 server 还有个更隐蔽的
   问题：一次慢请求（配额要查 MySQL）会把 `/healthz` 一起堵住，探针会误判进程已死。
2. **`used_in_db` 读到 0**：drill 在外部用 `int(time.time()//window_s)*window_s` 猜窗口起点，
   和计数器自己的口径对不上。改成读该租户**最新一行**——窗口怎么算由实现决定，
   外部不要重复推导。

## 测试

`tests/test_worker_rebuild_api.py` 7 项（真 HTTPServer + 真 urllib）：
202 入队、429+Retry-After、租户从 header/query 取、token 校验、BACKPRESSURE→429、
**被拒不进队列**、未知路径 404。

## 边界

- 只压了单进程 30 并发；**多副本跨进程**仍是各自连同一个 MySQL 计数（SQL 原子性保证，
  但没有压测数值）；
- 固定窗口在边界允许最多 2×limit 瞬时突发（未做滑动窗口/GCRA）；
- 热租户同一行 UPDATE 串行，吞吐受单行 RT 限制；
- 未做租户维度的指标导出（`stats()` 有数据，没接 /metrics）。
