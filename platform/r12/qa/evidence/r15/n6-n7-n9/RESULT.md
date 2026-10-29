# R15 N6 / N7 / N9 收尾记录

> **证据等级 RECORD_ONLY**：这是排障过程记录，**不可独立复跑**（依赖当时的临时夹具/中间态）。不得用作文档所述能力的通过证据；对应的稳定判据见 `platform/r15/acceptance/` 中的断言。


- 时间：2026-10-29 21:40–21:55

## N6 global 完整性（额度构成配对）—— 通过

### 问题

global 只答「8000万元」，不带「其中信用方式不超过1000万元」。7B 拿到"必须完整转述"的
prompt 约束仍然只答一句，属模型能力边界，不能靠 prompt 解决。

### 做法（代码算定 + 代码兜底，模型只表述）

```
1) _join_limits(map_outputs)：把同一主体的"总额度"与"分项上限"确定性配对成一行
   `智造贷 总额度 8000万元（最高额度）；其中 信用部分最高额度 1000万元（分项，不得当成总额度）`
2) 该行进入 reduce 的【代码推导：额度构成】段
3) _ensure_limit_completeness(answer, limits)：若模型仍漏掉分项，
   把分项补到答案末尾并标注同一 community_id（数值全部来自事实，不生成新信息）
```

### 实测（走 UI 同端点 /qa/ai/question_re，global）

```
global 0.8s status=2
智造贷最高额度是8000万元。[L0-8ebd15fe]
其中 信用部分最高额度 1000万元（分项，不属于总额度）[L0-8ebd15fe]
```

A03/A08 的核心判据（同时给出总额度与分项、且带可回指引用）**满足**。

## N9 列表"关系数"口径 —— 结论：代码是对的，但查询侧有同源缺陷

### 口径核对（graph-service instance()）

```
MATCH ()-[e:relationship]->() where properties(e).show_flag=='1' return count(e)
实测：122 条
```

⇒ 统计只算 `relationship` 且 `show_flag=1`，**不含** `relationship_similar`（432 条）。
N9 的原始担心不成立，无需改统计。

### 但发现同源缺陷（已修）

```
统计按 show_flag='1' 过滤，而问答查询 execute_query 没有过滤：
MATCH (v)-[e:relationship]-(v2) ...
→ 历史 show_flag=0 的伪反向边会被当成独立事实喂给下游（全图 164 条里 42 条是这类）
修法：查询侧与统计侧统一 WHERE properties(e).show_flag = '1'
```

## N7 generation 维度 —— 最小切片已落地，未做查询过滤

### 已做

```
1) base.GraphModel 增加 generation 字段（默认空串，行为与旧版一致）
2) 边 schema 增加 generation 列（create_attribute 两处）
3) 写边 INSERT 携带 generation（rank 不变）
4) Java 从 knowledgeBaseFile.getVersion() 下传，Python 传入 InsertModel
5) 现有空间迁移：ALTER EDGE relationship ADD (generation string)  → 成功
```

### 实测

```
gps=3（解析成功）
generation='V1'  → 22 条边（本次新写入）
generation=null  → 46 条边（历史遗留，未回填）
```

### 未做（如实）

```
· 查询/统计尚未按 generation 过滤（当前仍按 file_id 与 status 隔离）
· 历史 46 条边未回填代次
· 社区摘要、ES 文档、响应/引用都还没有 generation 字段
· 契约 layering：contracts/schema 里 generation 是 required，实现只到"边可写"这一层
```

⇒ F05 仍为 PARTIAL：**维度已通，但"一请求固定同代"的能力还没有**。

## 顺带记录：抽取稳定性

同一文件 343 连续三次解析：155 条 / 0 边（统计误判） / 59 条；第四次耗时 3 分钟以上并伴随
`关系行字段不足: ("relationship"::评级授信` 反复重试。

```
结论：抽取链路的**耗时与产出量**波动很大（30s–200s+），
需要 W01 侧改造（单块重试、schema 约束输出、可诊断计数），不能只靠超时兜底。
```
