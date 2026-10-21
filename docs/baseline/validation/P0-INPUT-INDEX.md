# 四项业务 P0 的外部输入索引（合并后持续工作用）

- 用途：一页看清「缺什么、谁给、什么格式、卡住谁、现在能做什么」
- 权威登记：`docs/registers/P0-CLOSURE.yaml`（四项均 **OPEN**、`evidence: []`、`blocks` 未清空）
- 详细索取单：`loops/LD-legacy-discovery/MATERIALS-REQUEST-V1.0.md`（M-01…M-07）

---

## P0-01 接口清单与运行时在用判定

| 项 | 内容 |
|---|---|
| 缺什么 | ① 运行时路由导出（服务+方法+原始大小写路径+handler）② 约 380 条「在用」的调用日志**或**调用方逐条确认 ③ `/retrieval_qa` 书面决议 |
| 谁提供 | `interface-owner` + 各服务负责人 |
| 格式 | 表格式，逐条标注调用方与首次观测时间；不接受截图或口头说明 |
| 卡住谁 | 504 条逐端点决议、L1/L3 |
| **现在能做** | 静态核验已完成：**504/506 存在于源码**（Java 438/440、Python 66/66）；1 条仅存在于注释（`API-0345 getRerankModelInfos`）；1 条行号漂移（`API-0425`） |
| 不能做的 | 静态存在**不得**认定为运行时在用 |
| 证据 | `loops/LD-legacy-discovery/evidence/INTERFACE-INVENTORY-DIFF-V1.0.md`、`interface-inventory-check.json`、工具 `tools/verify_interface_inventory.py` |

## P0-02 数据库结构与字段语义

| 项 | 内容 |
|---|---|
| 缺什么 | ① 逐表 `SHOW CREATE TABLE`（脱敏）+ 索引/约束/触发器/引擎/字符集/版本 ② 同版本恢复副本上的迁移/回填/回退执行记录 ③ `dialogue.create_by` 值域与生成方 |
| 谁提供 | `data-owner`（`create_by` 另需业务方） |
| 格式 | 文本 DDL + 执行日志（含时间戳与执行者） |
| 卡住谁 | 37 表/482 字段复用决议、L1/L2/L3 |
| **现在能做** | DO 实体与台账字段对照（结论只能标 `CANDIDATE`）；源码已确认 `dialogue` 无 `user_id`，设计文档要求建该索引——冲突已登记 |
| 不能做的 | **源码不能替代 DDL**；实体类字段数 ≠ 实际表结构 |
| 证据 | `docs/reuse/DATABASE-ASSETS.yaml`（37 表/482 字段，全部 `CANDIDATE_UNVERIFIED`、`actual_ddl_sha256=null`） |

## P0-03 授权模型

| 项 | 内容 |
|---|---|
| 缺什么 | E1 授权上下文规范（`security-owner` 出）+ E2–E7 六类负例的可复跑结果 + E8 检查对象声明 |
| 谁提供 | `security-owner` |
| 格式 | 规范文档 + 可执行负例脚本 + 运行日志 |
| 卡住谁 | P0-03 关闭、L1/L3/L4 |
| **已确定口径** | 业主 2026-10-21 裁决：叶子权限落文件、deny 优先、撤权即时生效、**FAQ 命中后按来源文档复核**、图路仅整 KB 授权时开放 |
| **现在能做** | E1/E8 可先写（不需运行环境）；六类负例可写脚本，但结果须标「模拟」 |
| 不能做的 | 口径确定 ≠ P0 关闭；模拟验证不得计入关闭证据 |
| 证据 | `docs/approvals/OWNER-ACCEPTANCE-2026-10-21-P0-03-04.md`、`DRAFT-P0-03-RESOLUTION-V1.0.md` |

## P0-04 代次与切换

| 项 | 内容 |
|---|---|
| 缺什么 | S1–S5 五场景可复跑结果 + R1 双代余量实测数字 + R2 历史引用不断链证明 |
| 谁提供 | `index-owner` |
| 格式 | 可复跑脚本 + 实测数字 + 日志 |
| 卡住谁 | P0-04 关闭、L1–L4（全部） |
| **已确定口径** | generation manifest 不可变；每 KB 单原子激活指针；写入必须带 `(kb_id, generation_id, fencing_token)`，非当前代返回明确错误 |
| **现在能做** | 场景脚本与断言可先写（标「模拟」） |
| 不能做的 | 需可运行检索链与真实存储（MySQL/ES/Milvus/Neo4j/LLM），当前均不可得 |
| 证据 | 同上 |

---

## 统一声明

- 四项 P0 的 `evidence` 均为空数组，`blocks` 未清空 → `make p0-gate` **exit 2**、L1–L4 **BLOCKED** 是正确状态。
- 任何「口径已裁决」「开发自检通过」「框架门禁全绿」都**不构成** P0 关闭。
- 关闭需：对应 owner + `baseline-owner` 在受保护环境批准，并挂真实非空哈希证据；
  `ACCEPTED_RISK` 不清空 `blocks`、不通过 strict。
