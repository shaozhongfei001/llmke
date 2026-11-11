# 证据索引

| 证据 | 位置 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| framework-verify 日志 | `loops/round10/evidence/T02-framework-verify.log` | 322 条测试通过、0 skip | 业务可用 |
| r16 候选清单 | `loops/L0-contract-baseline-r16/evidence/manifest.json` | 8 门禁 pass + QA_PENDING + 人工检查登记 | 独立签署 |
| 变异实验 | `loops/round10/evidence/T09-clean-repro.txt` | 改代码/控制面/脚本都会让证据失效 | 摘要无漏项 |
| 人工命令绑定 | `loops/round10/evidence/T10-record-check.log` | 改 schema-verify.sh → 证据 STALE | 未登记的命令仍不绑定 |
| 覆盖审计 | `loops/round10/evidence/T12-command-coverage.txt` | P0-01 提取器未绑定（缺点） | — |
| 演示记录 | `loops/round10/evidence/T14-demo.txt` | 5 类 HTTP 响应真实存在 | 参考水平的检索 |
| 依赖盘点 | 本包 `03-FACTS.md` | PyPI 不可达、无模型/中间件 | — |

**注意**：以上证据全部说明"证据链自洽"，**没有一条**证明产品功能完成度。
