# LLMKE 技术施工基线 V1.1.0

本次覆盖修订由业主于 2026-10-20 授权；约束契约、角色、流程与门禁。完整发布源码、实际 DDL、业务政策与独立 QA 仍按真实证据裁决。

## 权威与状态

1. 本次 `docs/baseline/COMPATIBILITY-DECISIONS.yaml` 中明确修订的技术决议优先；其余继续服从未被替代的上游决议。
2. `contracts/registry.yaml` 是合同唯一注册入口；冲突登记 CR，不能在实现里猜或静默修改。
3. `docs/policies/GATE-CATALOG.yaml`、`docs/PROJECT-PLAN.yaml` 和 `loops/*/LOOP.yaml` 定义执行边界。
4. `FROZEN-MANIFEST.json` 固定技术控制文件字节，不代表业务风险关闭、真实环境验证或业主验收。
5. 原四项业务 P0 全部 OPEN；L0/LD 可工作，L1–L4 默认 BLOCKED。不能清空 blocks 或自改 CLOSED/DONE 来放行。

## 开始工作

先读 README、当前 LOOP、STATE、FAILURES、HANDOFF；仅当前 baton holder 执行。STATE 是唯一状态权威，memory 下均为可重建视图。角色见 ROLE-MATRIX；受信身份由外部 runner 配置证明，CLI 角色名没有验收权。

## 十二条纪律及实际检查

1. 改边界先改合同源并作兼容决议，再 generate/check，最后实现与消费者回放。提交先后仍需审计。
2. generated 只由空目录生成后发布；check 对完整集合和输入/工具链摘要校验，不能手改。
3. 门禁只执行 catalog 中精确 argv；禁止 shell、`|| true`、打印 PASS 代替断言。
4. 命令必须有测试资产和可检查结果；自然语言 pass_condition 不会自动执行。
5. 失败先追加日志，再更新权威状态；达到修复预算停止，由 TL 开新修复批次，不删失败。
6. 开发可自检，独立 QA 必须受保护环境复跑并签署当前源码/门禁/基线/日志；`--role qa` 不能代签。
7. 提交审查 staged diff 和敏感文件集合；不声称 CI 能还原 `git add .` 命令历史。
8. 凭据不入库，扫描命中不回显原值；模式扫描不是完整保密证明。
9. 506 是旧接口清单记录数；运行时路由、调用方和目标合同核验后才决定复用。
10. 派生上下文须已发布、完整来源且按当前权限复核；最终结论绑定足够的类型化证据，不伪装原文 offset。
11. offset 为 Unicode 码点左闭右开区间，与完整 text_hash、parser_version 和准确快照绑定；跨字段及实际解析均测试。
12. 通路失败、预算裁剪和覆盖不足必须体现在 degraded/coverage/答案状态；以故障回放验收。

## 源码与数据库

优先保留成熟内部实现，按契约适配外边界；12项源码、37表/482字段、506条接口的登记在 docs/reuse。未经发布基线、特征回放、实际 DDL、迁移/回退证据与批准，不标记直接复用。禁止凭模型字段清单编造生产 DDL。

规则源为 docs/policies/AGENT-RULES.yaml；两 IDE 的规则和六个通用工作流由它生成。没有第二个 OpenAPI 事实源。Oracle 工具为可选独立工具，不证明 RAG MySQL 37表已完成核验。
