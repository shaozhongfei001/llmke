---
name: oracle-metadata-catalog
description: >-
  Oracle 元数据目录与血缘采集工具链 — read-only 门禁流水线（gate0~gate7）：
  连接探测 → 全量对象清点 → PL/SQL 源码提取 → 静态解析 → 对象/字段血缘 →
  指标与派生字段 → 中文业务描述/问题登记 → 开发自检。Use when the user asks to
  采集/梳理 Oracle 元数据、表/字段/存储过程清单、血缘分析、指标口径提取,
  or build a metadata catalog SQLite from an Oracle database.
---

# Oracle Metadata Catalog

**Mindset**: 只读采集、门禁化流水线、完备性用分子/分母记账。账号即使有写权限也全程只读。

工具位置：`scripts/oracle_metadata/`（Python + python-oracledb，Thick 模式经 ORACLE_CLIENT_DIR）。

## 前置条件

1. `pip install oracledb`，本机有 Oracle Instant Client（`ORACLE_CLIENT_DIR`）
2. 凭据只从环境变量 / 本地未提交 `.env` 读（`ORACLE_HOST/PORT/SERVICE/USER/PASSWORD`；框架不含任何项目专属前缀或默认值）
3. 会话强制 `SET TRANSACTION READ ONLY`；日志中密码自动 `***REDACTED***`

## 配置（环境变量）

| 变量 | 默认 | 说明 |
|------|------|------|
| `ORACLE_METADATA_ENV_FILE` | `<repo>/.env` | 凭据文件 |
| `ORACLE_METADATA_REPORT_DIR` | `reports/oracle-metadata` | 报告输出目录 |
| `ORACLE_METADATA_RUN_PREFIX` | `run` | 快照 ID 前缀（`<prefix>-<UTCts>`） |
| `ORACLE_METADATA_FOCUS_SCHEMA` | `EDWCRM` | 深度解析的业务 Schema（其余仅 inventory） |
| `ORACLE_METADATA_LOOP_DIR` | `oracle-metadata-lineage` | loops 下批次目录名 |

## 门禁流水线（顺序执行，每门有独立命令与产出）

| Gate | 脚本 | 产出 | 通过条件 |
|------|------|------|----------|
| 0 连接/权限探测 | `gate0_readonly_probe.py` | `gate0-connection-report.{md,json}` | 字典视图（ALL_*/DBMS_METADATA/Scheduler）全部可读 |
| 1 全量清点 | `gate1_inventory.py` | SQLite + `gate1-profile.json` | 对象数与 ALL_OBJECTS 对账 分子=分母 |
| 1v 清点复核 | `gate1_verify.py` | reconcile 报告 | 无缺口 |
| 2 源码提取 | `gate2_source.py` | program_unit/argument 入 SQLite | 焦点 Schema 程序 31/31 类全覆盖 |
| 3 静态解析 | `gate3_parse.py` | 语句登记 + 调用图 `program-call-graph.json` | 字符串内 DML 不计入调用图 |
| 4 血缘 | `gate4_lineage.py` | object/field lineage | 目标列无脏名、跨语句无错位 |
| 5 指标 | `gate5_metrics.py` | metric catalog + derived fields | Owner 已确认指标公式**零改动**（保护集） |
| 6 中文描述 | `gate6_cn_descriptions.py` | 程序业务描述 | 头注释+参数+调用链三源佐证，无自相矛盾 |
| 6i 问题登记 | `gate6_issues.py` | `analysis_issues` 表 + privilege-gaps.md | 权限缺口全部登记 |
| 7 开发自检 | `gate7_qa.py` | `dev-self-check-report.json` + `COMPLETENESS.md` | BLOCKER=0/MAJOR=0 |

```bash
cd scripts/oracle_metadata
python gate0_readonly_probe.py && python gate1_inventory.py && python gate1_verify.py \
  && python gate2_source.py && python gate3_parse.py && python gate4_lineage.py \
  && python gate5_metrics.py && python gate6_cn_descriptions.py && python gate6_issues.py \
  && python gate7_qa.py
```

## SQLite 目录（`data/metadata/oracle_metadata_catalog.sqlite`，gitignore）

核心表：`db_snapshot`（每次采集一行，含 code_commit/库指纹）· `accessible_schema` · `db_object` ·
`table_metadata` / `column_metadata`（含 comment）· `program_unit` / `program_argument` ·
`statement_register` · `call_edge` · `object_lineage` / `field_lineage` · `metric` / `derived_field` · `analysis_issue`。

快照制：每次采集生成 `snapshot_id = <prefix>-<UTC时间>`，历史可对比。

## 红线（从实战教训固化）

1. **全程只读**——即使账号有 DBA 角色；探测脚本不执行任何 DDL/DML/过程
2. **完备性用 x/y 记账**——"71752/71752 objects" 而不是"基本完成"；分母来自数据库字典对账
3. **QA 独立**——`gate7` 只是开发自检（DEV_SELF_CHECK）；`QA_GATE` 只能由**独立 QA Agent**抽样复核后置位，开发自签是 MAJOR 违规
4. **Owner 确认集保护**——Owner 已确认的指标/公式进保护集，后续 gate 不得改动
5. **源码存储策略**——哈希+行号段进报告；全量源码只在本地 gitignored 目录（默认禁止入库）
6. **静态解析保守降级**——动态 SQL / 字符串内 DML 标 `PARTIALLY_DYNAMIC`，血缘宁缺毋假

## 排障

| 现象 | 处理 |
|------|------|
| `DPI-1047` 找不到 Client | 设 `ORACLE_CLIENT_DIR` 指向 instant client |
| 某字典视图不可读 | 记入 privilege-gaps.md，该域降级为缺口登记，不伪造数据 |
| LONG 类型字段（SEARCH_CONDITION） | 标记 PARTIAL，列入后续补采 |
