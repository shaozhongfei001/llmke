# 本体契约（ontology）

> 状态：`draft-for-business-review`。27 个类型码已按现有语料落盘，**其中 5 个码位无真实样例**（见下表"待业务确认"），
> 需要业务方确认后才能叫 v1.0.0 正式版。

## 文件

```
entity-types.v1.json   6 大类 27 码：code / label / category / aliases / examples / rule_hint
relations.v1.json      18 个谓词：domain / range / symmetric / cardinality / naming_rules
```

## 程序怎么读

```python
import json
spec = json.load(open("contracts/ontology/entity-types.v1.json", encoding="utf-8"))
ALLOWED_CODES = [t["code"] for t in spec["types"]]          # 27 个
ALIAS_TO_CODE = {a: t["code"] for t in spec["types"] for a in t.get("aliases", [])}

rel = json.load(open("contracts/ontology/relations.v1.json", encoding="utf-8"))
SYMMETRIC = {r["name"] for r in rel["relations"] if r.get("symmetric")}
```

**不要**在代码里再写字面量白名单。当前 `graph_types.py` 的 `ALLOWED_TYPES`（16 类）是待替换的遗留实现。

## 现有 16 类 → 27 码 对账

| 现有（graph_types.py） | 契约 code | 状态 |
|---|---|---|
| 机构 | `org` | 一致 |
| 客户 | `customer` | 一致 |
| 产品 | `product` | 一致 |
| 金额 | `amount` | 一致 |
| 期限 | `term` | 一致 |
| 指标 | `metric` | 一致 |
| 日期 | `date` | 一致 |
| 业务动作 | `action` | 一致 |
| 单证 | `document` | 一致 |
| 条款 | `clause` | 一致 |
| 评级 | `grade` | 一致（但 `AAA级` 未归一） |
| 地点 | `location` | 一致（`制造业` 误判，见下） |
| 担保 | `guarantee_type` | 一致（注意是"方式"不是"主体"） |
| 编号 | `doc_no` | 一致 |
| 口径 | `caliber` | 一致 |
| 其他 | `other` | 一致 |
| **（RULES 产出但不在白名单）时间** | `time_scope` | **缺口，已收编** |
| — | `person_role` | 新增，**无真实样例，待业务确认** |
| — | `guarantor` | 新增，**无真实样例，待业务确认** |
| — | `process_step` | 新增，有样例（受理/评级授信） |
| — | `channel` | 新增，**无真实样例，待业务确认** |
| — | `frequency` | 新增，**无真实样例，待业务确认** |
| — | `rate` | 新增，样例 `60个基点`（现在落在 unclassified） |
| — | `rule` | 新增，**无真实样例，待业务确认** |
| — | `constraint` | 新增，样例 `信用部分不超过1000万元` |
| — | `status` | 新增，**无真实样例，待业务确认** |
| — | `unknown` | 兜底（对应现有 `unclassified`） |

统计：16 类全部有对应码；新增 11 码，其中 5 码无真实样例。

## 已知问题（kb_9 实测）

| 问题 | 证据 | 影响 |
|---|---|---|
| `STOPWORDS` 含"正常"，而 `RULES` 把"正常"判为评级 | 合法评级值被静默丢弃 | 风险分类无法进图 |
| `时间` 由 RULES 产出但不在 `ALLOWED_TYPES` | 图中 `时间` × 1 | 白名单外类型进图 |
| `制造业` 被判为 `location` | 地点样例里出现"制造业" | 行业/产业链维度错位 |
| `AAA级` 未归一成 `AAA` | 评级样例同时有 `AAA` 与 `AAA级` | 按等级取值会漏 |
| `unclassified` 占 58/133 ≈ **44%** | 类型分布实测 | 类型体系对下游近乎无约束力 |

## 谓词命名违规（存量，需清理）

```
数据源->口径         含箭头
担保额度->信用部分   含箭头
加点幅度-            尾部连字符
信用额度上限-        尾部连字符
审批期限-            尾部连字符
```

清理原则：按 `aliases` 归一到契约名，**不删事实**；归一后同端点同谓词同值会坍缩成一条，这是正确的。

## 版本策略

```
v1.0.0  业务确认 5 个空码位后定稿
v1.x    只增不改：新增 code 必须给 aliases + examples（至少 2 个真实实体）
v2.0    删除/改名 code 或改 category —— 需数据迁移，并同步：
        graph_types.py 白名单、抽取 prompt 的类型清单、platform/r15 的 A01 断言
```

## 变更影响面（改契约时要一起改的）

```
1. services/rag-alg/.../graph_types.py    ALLOWED_TYPES / RULES / STOPWORDS
2. 抽取 prompt 里的类型清单（graph_service._resolve_entity_types 传入的 entity_types）
3. platform/r15/acceptance/a01.py         断言里的白名单校验
4. 已入库的 v.type 属性                   需按 aliases 回填归一
```
