# 提交包 · interface-owner（P0-01）

**要什么**：506 条接口中承载业务流量的接口的「运行时在用状态」。

## 三选一（任一份即可，优先级从上到下）

| 形式 | 文件 | 关键字段 |
|---|---|---|
| 路由导出 | `samples/route-export-sample.csv` | service, method, path(原始大小写), handler, framework, environment, exported_at |
| 访问日志 | `samples/access-log-sample.csv` | observed_at, service, method, path, status, **caller_service**, count, window_start/end |
| 调用方确认 | `samples/caller-confirmation-sample.md` | asset_id, 判断(IN_USE/NOT_IN_USE/UNKNOWN), 依据方式, 调用位置 |

## 字段含义要点

- `path` **必须原始大小写**，不要规范化——规范化后无法与清单自动比对；
- `caller_service` 不可省：只有 path 没有调用方，**不能证明在用**；
- `environment` 必须写真实环境；本地开发日志**不充当**生产证据；
- `判断` 允许 `UNKNOWN`，**不确定就写 UNKNOWN，不要猜**。

## 必须脱敏

请求体、用户标识、IP、token、URL 查询串中的业务参数。只保留聚合维度。

## 验收规则

1. 覆盖 506 条涉及的全部 service；
2. 有 `exported_at` 与 `environment`；
3. `IN_USE` 必须给出可核查调用位置（文件行号/网关配置/页面）；
4. `NOT_IN_USE` 必须给出检索方式与命中数。

## 常见拒收

无调用方；无时间窗；环境不明；只给截图；用「大概在用」表述。

## 对应与影响

P0-01 关闭、L1/L3。填表对象：`loops/LD-legacy-discovery/evidence/interface-decision-table.csv`。

## 无法提供时必须做的决定

书面说明「运行时不可得」，并选择：① 以静态抽取视同运行时口径（需明示风险）；
② 以调用方确认替代；③ 保持 P0-01 OPEN。
