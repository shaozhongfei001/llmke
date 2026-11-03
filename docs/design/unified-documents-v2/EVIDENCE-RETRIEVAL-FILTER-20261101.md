# 检索命中后置过滤：生效期 + 可见域（2026-11-01）

模块 `graph_engine_adapter/retrieval_filter.py`（11 项测试），**未接入** `pipeline.retrieve`。

## 为什么在这一层做

`capabilities.py` 里两项一直是 NOT_IMPLEMENTED：

- `engine_version_filtering`：「as-of 过滤在断言层成立；引擎检索尚未按生效期约束」；
- `engine_visibility_isolation`：「查询侧 scope 过滤在断言层成立；构建期按可见集合隔离索引未做」。

但**没有理由要求引擎先学会这两件事**。引擎只负责召回，平台负责认定；`pipeline.retrieve`
已经在结果回来后用 `fence.filter_hits` 拦撤权内容，同样的位置可以再拦"过期"与"越权"。
改引擎等于把平台语义塞进第三方库（HippoRAG）的检索路径：不可测（1.9GB 模型 + 随机性）、
不可回退（升级上游即失效）。后置过滤是纯函数，构造数据就能反证。

## 两条闸方向**刻意相反**

| 维度 | 无法判定时 | 为什么 |
|---|---|---|
| 生效期（as_of） | **保留**，计 `unknown_window` | 绝大多数正常文档不写生效期。把"没写日期"当过期，一开开关就大片误杀，运维只能关掉它——安全机制一旦以误杀为代价就活不下来。只在**能证明过期**（有日期且全部落在窗口外）时丢弃 |
| 可见域（scope） | **丢弃**，计 `unknown_scope_dropped` | 越权是单向不可逆事故（内容已经到用户眼前），版本过期最多是答案旧一点。风险量级不同，所以一个 fail-open、一个 fail-closed |

这与既有口径一致：`fence.assert_index_fresh` 对"索引未声明代次"直接拒绝读，
`assertions.decide_route` 对"认不出种子"直接回退，都不做"看起来没事就放行"。

## 判定细则

- 生效期半开区间：`as_of < effective_from` 或 `as_of >= effective_to` 即失效（到期当天即失效，
  与 `AssertionStore._in_window` 同口径）。测试里用同一批构造事实同时走 `store.facts(as_of=...)`
  与 `filter_hits(as_of=...)` 做交叉校验，防两层漂移。
- 文件内"带日期但全过期"+ "没写日期"混排 → 判过期。没写日期的事实不构成新鲜度证明，
  拿它自证"还有效"等于给过期文档开后门。
- 一个命中多来源：只要还有一个来源在两维上都活着就**保留**，并把失效来源从返回副本里裁掉
  （与 `fence.filter_hits` 同构）。多来源内容不该被单个坏来源拖死，但坏来源也不能留在
  `citations` 里被下游引用。
- 丢弃原因优先级 `SCOPE_DENIED` > `UNKNOWN_SCOPE` > `OUT_OF_WINDOW`：多重原因成立时报可见性，
  因为它不会因为换个日期就变成可读。
- `dropped.text_prefix` 只留 40 字：dropped 会进报告与指标，正文全量会把日志撑爆。
- 入参不可变：裁来源生成新 dict / 新 list；有测试对 deepcopy 快照做全等断言。
- 三个参数全空 → 原样返回、`stats` 全零，保证"引入模块 ≠ 改变行为"。
- 给了 `scopes` 却没给 `doc_scopes` → 全部按 UNKNOWN_SCOPE 丢弃。放行的话"忘记传
  doc_scopes"会静默变成"全部可见"，调用方看不出任何异常——这类静默降级正是权限事故的典型形态。

## 测试（11 项，真实 `AssertionStore`）

```
cd /home/szf/data/dev/llmke-v2 && PYTHONPATH=services/rag-alg/index_data_service \
  /home/szf/data/dev/llmke-v2-toolenv/bin/python -m pytest tests/test_retrieval_filter.py -q
...........                                                              [100%]
11 passed in 0.03s
```

覆盖：窗口内保留 / 窗口外丢弃且 reason=OUT_OF_WINDOW / 到期当天边界 / 无生效期保留且
unknown_window+1 / 多来源部分过期仍保留且裁来源 / scope 命中保留 / scope 不命中 SCOPE_DENIED /
查不到 file_id 的 UNKNOWN_SCOPE（fail-closed）/ 给了 scopes 没给 doc_scopes / 原因优先级 /
无参原样返回 / 只给 as_of 不给 store 不过滤 / 入参不被修改。

相邻既有测试一并复跑（`test_graph_fence` + `test_graph_pipeline` + `test_graph_engine_capabilities`
+ `test_graph_assertions` + 本文件）：

```
40 passed in 0.06s
```

## 真实过滤（`AssertionStore` + 2 条构造事实，一次性脚本在 /tmp，未入库）

场景 A：`as_of=2026-03-01` + `scopes={"dept-a"}`，`doc_scopes={"333": {dept-a}, "444": {dept-b}}`：

```
store.stats = {"entities": 1, "aliases": 1, "assertions": 2, "orphans": 0, "sources": 2}
input hits = 4
kept  hits = 2
kept  texts = ['上半年额度 8000 万元（旧政策原文）', '同一段话命中两个文件']
kept  sources = [['333'], ['333']]
dropped = [{"text_prefix": "下半年额度 9000 万元（尚未生效）", "file_ids": ["444"], "reason": "SCOPE_DENIED"},
           {"text_prefix": "没有来源的命中", "file_ids": [], "reason": "UNKNOWN_SCOPE"}]
stats = {"input": 4, "kept": 2, "dropped": 2, "unknown_window": 0, "unknown_scope_dropped": 1, "trimmed_sources": 1}
immutable(input unchanged) = True
```

读法：444 既未生效又不在 `dept-a` 域内，按优先级报 `SCOPE_DENIED`；多来源命中保留但来源裁成 333；
无来源命中在可见性维不可判定 → 拒。

场景 B：只开生效期闸，`as_of=2026-03-01`：

```
as_of=2026-03-01 input = 4 kept = 3
kept texts = ['上半年额度 8000 万元', '无生效期的事实（适用客群）', '断言层里没有这个文件']
dropped = [{"text_prefix": "下半年额度 9000 万元（尚未生效）", "file_ids": ["444"], "reason": "OUT_OF_WINDOW"}]
stats = {"input": 4, "kept": 3, "dropped": 1, "unknown_window": 2, "unknown_scope_dropped": 0, "trimmed_sources": 0}
-- 只给 as_of 不给 store（应完全不过滤）--
kept = 4 dropped = 0 stats = {"input": 4, "kept": 4, "dropped": 0, "unknown_window": 0, "unknown_scope_dropped": 0, "trimmed_sources": 0}
```

`unknown_window=2` 是真实覆盖率上限信号：4 个命中有 2 个来源无法判定生效期（一条无日期事实 +
一个断言层里没有的文件）。这个数字应该被监控——它高，说明版本过滤基本没在起作用。

## 开发中自纠的一处（不是"跑一次全绿"）

初版把两维判定折成 `DEAD > UNKNOWN > ALIVE` 再与 `ALIVE` 比较，结果版本维的 UNKNOWN（没写日期）
被当成拒绝：`test_file_without_effective_dates_is_kept_and_counted_as_unknown_window` 首次运行
`assert [] == ['命中正文', '命中正文']` 失败。UNKNOWN 的含义完全取决于维度，已改成
`_is_alive(window, scope) = (window != DEAD and scope == ALIVE)` 并写进注释。**这条用例正是本模块
存在的理由**：方向错了，机制就从"少拦"变成"误杀"。

## 没做（不许当成已支持）

- **未接入 `pipeline.retrieve`**：是否默认开启、默认 `as_of`/`scopes` 从哪来（请求上下文？
  租约？）需要 TL 决定。默认零变化的保证由"参数全空即原样返回"提供，但开关本身没动；
- **`capabilities.py` 未改**：`engine_version_filtering` / `engine_visibility_isolation` 仍是
  NOT_IMPLEMENTED。本层是**检索结果后置过滤**，不是引擎执行期约束、更不是构建期索引隔离；
- **构建期按可见集合隔离索引**仍缺（不可见文件的内容照样被引擎召回，只是在这里被丢掉）；
  这与"引擎根本不返回越权块"不是同一件事；
- 正文未重写：保留的命中只裁 `sources`，同一块文本里若混有已过期来源的句子，正文照旧；
- 只有文件级生效期与文件级可见域；断言级（同一文件内不同 `visibility`）没有在这里落地，
  需要时应对 `AssertionStore.facts(scopes=...)` 另做一层；
- 无性能数据：`facts_by_source` 是断言表全表扫描，语料规模上去后要按 `file_id` 建倒排索引。
