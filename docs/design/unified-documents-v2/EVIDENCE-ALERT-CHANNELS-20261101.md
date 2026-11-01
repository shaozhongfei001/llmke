# 告警通道：企业微信 / 钉钉的报文与签名（2026-11-01）

模块 `services/rag-alg/index_data_service/graph_engine_adapter/alert_channels.py`，
测试 `tests/test_alert_channels.py`（**16 项，全 PASS**）。本文件只记录事实与边界。

## 为什么还缺这一层

`alert_sink.py` 解决的是"怎么可靠地送"（指数退避重试、去重、永不抛），但它的请求体是
`event` 原样 JSON。真实群机器人不吃这一套：

- 企业微信要 `{"msgtype": "markdown", "markdown": {"content": ...}}`；
- 钉钉还要 `timestamp` + `sign`（`{ts}\n{secret}` → HMAC-SHA256 → base64 → urlencode），
  且**签名从 URL query 读**，不是从 body 读。

没有这一层，接生产网关只能现场改代码并试错——而试错的场景恰好是"告警发不出去"的时刻。

## 分工

| 层 | 内容 | 特点 |
|---|---|---|
| 报文 | `wecom_payload()` / `dingtalk_payload()` | 纯函数，可离线比对 |
| 签名 | `dingtalk_sign()` / `dingtalk_signed_url()` | timestamp 可注入 ⇒ 可复现 |
| 投递 | `WecomChannel` / `DingtalkChannel` | `__call__` 永不抛；重试/状态码判定复用 `alert_sink` |

正文是 markdown（标题 + 级别 + 时间 + 错误 + 影响 + 至多 6 个附加字段），**不是** JSON 转储。

## 单测

```
PYTHONPATH=services/rag-alg/index_data_service <toolenv>/bin/python -m pytest tests/test_alert_channels.py -q
................                                                         [100%]
16 passed in 0.13s
```

（`<toolenv>` = 团队统一的工具环境解释器；系统 `python3` 缺依赖，用它跑会先在 import 处失败。）

覆盖：wecom 结构/附加字段上限/超 4000 字符截断/中文**字节**预算、钉钉签名与独立实现逐字符一致、
只编码一次（`%25` 检查）、timestamp 可复现且对时间敏感、signed_url 的 `?`/`&` 拼接、
HTTP 500 与连接异常返回 False 不抛、`sent/failed/attempts/last_status` 记账、
secret 不外泄（含 query 凭证）、空 secret fail-fast、以及一条真 socket 的本地端到端。

## 本地端到端（127.0.0.1，不连外网）

两条通道各发一条，服务器把收到的 path + body 原样记下来：

```
wecom ok: True
dingtalk ok: True
received requests: 2

PATH[0]: /cgi-bin/webhook/send?key=***
BODY[0]:
{
  "msgtype": "markdown",
  "markdown": {
    "content": "### LLMKE 图引擎告警: LEASE_UNAVAILABLE\n> 级别: P1\n> 时间: 2026-01-01 00:00:00 UTC\n> 错误: OSError: connection refused\n> 影响: 重建停止\n> consecutive: 3"
  }
}

PATH[1]: /robot/send?<access_token 已脱敏>&timestamp=1767225600000&sign=***
（sign 的实际值：P%2BskpcyMSWNB901mMnqSV7NvCEEwU7ysOiNGeCGMD4o%3D，与 body 里那个逐字符相同）
BODY[1]:
{
  "msgtype": "markdown",
  "markdown": {
    "title": "LLMKE 图引擎告警: LEASE_UNAVAILABLE",
    "text": "### LLMKE 图引擎告警: LEASE_UNAVAILABLE\n> 级别: P1\n> 时间: 2026-01-01 00:00:00 UTC\n> 错误: OSError: connection refused\n> 影响: 重建停止\n> consecutive: 3"
  },
  "timestamp": "1767225600000",
  "sign": "P%2BskpcyMSWNB901mMnqSV7NvCEEwU7ysOiNGeCGMD4o%3D"
}

STATS wecom: {"sent": 1, "failed": 0, "attempts": 1, "last_error": null, "last_status": 200,
              "channel": "wecom", "url": "http://127.0.0.1:41051/cgi-bin/webhook/send",
              "retries": 2, "max_chars": 4000, "max_bytes": 4000}
STATS dingtalk: {"sent": 1, "failed": 0, "attempts": 1, "last_error": null, "last_status": 200,
                 "channel": "dingtalk", "url": "http://127.0.0.1:41051/robot/send",
                 "retries": 2, "max_chars": 4000, "max_bytes": 8000}
```

两个观察到的事实：

1. **`stats()` 里的 `url` 已去掉 query**（`?key=` / `?access_token=` 不进记账），
   所以能在工单里贴 `stats()`；
2. **body 里的 `sign` 与 query 里的 `sign` 逐字符相同**，同一个时间戳算出，排查 310000 时可直接对照。

## 签名：三重交叉验证

| 实现 | 来源 | 值（seed 为夹具值，ts=1767225600000） |
|---|---|---|
| 被测代码 | `dingtalk_sign()` | `P%2BskpcyMSWNB901mMnqSV7NvCEEwU7ysOiNGeCGMD4o%3D` |
| 测试内独立重算 | 照文档 `{ts}\n{secret}` → HMAC → base64 → urlencode | 同左，逐字符一致 |
| OpenSSL | `openssl dgst -sha256 -hmac` + base64 + urlencode | 同左，`cross-check: MATCH` |

第三条是必要的：测试里的"独立实现"和被测代码都用 Python `hmac`，如果两者对
"`\n` 是不是 `\r\n`、base64 还是 base64url、要不要 urlencode"犯了同一个错，前两条会一起错。
OpenSSL 是另一套实现，它对上才算签名字节级正确。

`timestamp` 可注入 ⇒ 同一输入永远同一输出（测试断言两次调用相等、`+1ms` 则签名不同）。

## 为什么两个预算：字符 + 字节

企业微信 markdown 上限是 4096 **字节**，而中文是 3 字节/字。只按"4000 字符"截，
一条中文长告警会被网关整体拒绝（看起来"发出去了"，群里没有内容）：

```
wecom_payload({"kind":"CJK","error":"中"*2000}) → 正文 1384 字符 / 3998 字节
```

2000 字被压到 1384 字——**字符预算没超，字节预算先到**。被截断时正文尾部留
`…（已截断：原文 N 字符 / M 字节）`，不静默丢内容。

## secret 的边界（这条最容易被顺手破坏）

- 只进 HMAC，**不进** `stats()` / 异常消息 / `repr()` / 请求体；
- 连"前 4 位"都不给（对机器人 secret 来说那是可爆破的锚点），sha256 指纹也不给
  （本场景没有"确认轮换"的需求，多一个派生值就多一条泄漏面）；
- 失败记账统一过 `_scrub()`：先把 query 里的凭证值抹成 `***`，再抹 secret 的三种编码形态
  （原文 / 严格 urlencode / quote_plus）——底层报错把完整 URL 拼进异常时不会把凭证带出来。

`_scrub` 保留 `sign`（不抹）：它不是长期凭证，而排查 310000 必须靠它比对。

测试用 `assert <seed> not in json.dumps(...)` 覆盖 stats / repr / body / 异常文本四个面，
并且专门造了一个"post 异常里故意拼上 seed"的用例，验证抹除真的生效（而不是"碰巧没出现"）。

## fail-fast：空 secret 不许发出去

空 secret 发出去只会拿到 `errcode=310000 sign not match`，在线上表现为"告警收不到"，
把**配置错**伪装成**网络抽风**，排查方向全错。所以 `DingtalkChannel` 在**构造期**就抛
`ValueError`，消息里写清"由部署侧注入（环境变量 / 密钥文件）"，不打印任何值。

## 没做 / 边界（不要外推）

- **没有真实企业微信 / 钉钉机器人账号**，未验证网关侧是否接受这些报文
  （签名正确性只有"算法三重一致"这一层证据；`errcode=0` 是本地桩返回的，不是网关返回的）；
- **不做去重**：去重语义留在 `WebhookAlertSink`（窗口在"决定发送"时打点）。本通道若直连调度器，
  装配侧必须自己保留去重，否则 webhook 抖动时每轮告警都各打一遍网络；
- **不做限流退避**：钉钉有 20 条/分钟频控，本模块只有"失败重试"的指数退避，没有"发送速率"控制；
- **不做 access_token 轮换 / 过期处理**：钉钉 timestamp 有效窗口是 1 小时，实践里重试跨度远小于它，
  但没有"时间不同步（NTP 漂移）"的检测，那会直接表现为 310000；
- **企业微信 markdown 语法只用了子集**（标题/引用），没用 `<font color>` 等富文本；
- 未改 `alert_sink.py` / `rebuild_scheduler.py`，也未把它们接到本模块上——装配是下一步的事。
