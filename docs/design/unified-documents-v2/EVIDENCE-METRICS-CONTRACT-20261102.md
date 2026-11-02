# 指标契约断言：把 quota 系列接进巡检（2026-11-02）

## 之前的问题：检查只问"字符串在不在"

Q 里原有的指标检查是手写循环 + `in` 判断，漏得掉三类真问题：

- `nan`/`inf` 能混过去（它们会污染 `rate()`/`avg()`，但字符串看着像正常样本）；
- `# TYPE` 重复、标签不闭合要等 Prometheus 抓取时才报；
- 配额只有 `used` 没有 `limit`，或者 `used > limit`，面板照样画，没人发现。

而且 worker 侧与 Q 侧各写了一份校验，注定漂移。

## 做法：统一契约层 `scripts/v2_metrics_contract.py`

四类判定：

| 层 | 判据 |
|---|---|
| 语法 | 每行要么注释、要么 `name{labels} value`；标签必须闭合、无重复键 |
| 数值 | 必须是有限数（nan/inf 直接违约） |
| 元数据 | `# TYPE` 每个名字只出现一次；counter 名必须以 `_total` 结尾 |
| 业务 | 配额族必须成对（used/limit 同一组标签），且 `used <= limit`，必须有 `tenant` 标签 |

做成 CLI 即可当巡检用：

```
python scripts/v2_metrics_contract.py --url http://127.0.0.1:18904/metrics --require-quota
```

真跑（worker 带 `--quota-limit 4`，先 POST 一次 `/rebuild`）：

```
{"ok": true, "series": 24,
 "quota": {"tenants": ["kb_9"], "used_series": 1, "limit_series": 1},
 "problems": []}   exit=0
```

## 接进现有巡检

1. **`deploy:常驻进程健康与优雅停机`**：worker 起进程时，有 MySQL 环境就带
   `--quota-limit 3`；探活后先 POST 一次 `/rebuild`（配额族只在有计数时出现），
   再抓 `/metrics` 跑契约，`require_quota=True`。报告里能看到
   `metric_contract={"series":24,"quota":{"tenants":["default"],...}}`。
2. **`graph:指标导出与告警通道`**：把手写的解析循环替换成同一个契约函数
   （`required=("llmke_graph_rebuild_pending",)`），消除两份会漂移的实现。

## 为什么"先 POST 一次"

配额指标来自**当前窗口的实际计数**，空表时 `render_quota` 不输出任何样本。
不先打一次就断言 `require_quota`，等于要求"从没来过的租户也要有指标"——
那会逼实现去造假数据。

## 测试

`tests/test_metrics_contract.py` 11 项：正常文本、nan、TYPE 重复、counter 缺 `_total`、
used 缺 limit、used > limit、缺 tenant 标签、`--require-quota` 开关、缺必需指标、
格式错误行、空文本。

## 边界

- 契约只校验**结构与自洽**，不校验"配额该不该是 5"这种业务值；
- 不解析 `_bucket`/直方图（当前没有直方图，出现时会以"样本缺少 TYPE"报出来，属于有意为之）；
- 未接真实 Prometheus 抓取端（未验证 scrape 侧的 `up`/`scrape_errors`）；
- 巡检 CLI 只支持单目标 URL，没有批量目标与超时重试策略。
