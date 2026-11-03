# S1 方向语义：有向谓词的双向事实不得被合并

角色：s1-direction（S1 收口团队）
日期：2026-11-02
工作树：`/home/szf/data/dev/llmke-v2`（分支 `main`，未 commit、未 git add）
外部输入：评审 B01「关系去重用无序键，导致 `甲 -担保-> 乙` 与 `乙 -担保-> 甲` 落成同一条、只留先到者」

## 0. 结论先说（事实 / 判断分开）

- **事实**：改动前，`normalize.build_store` 归一后**没有**把有向谓词的双向事实合并——`甲 -担保-> 乙` 与
  `乙 -担保-> 甲` 是两条断言，两个方向都在。所以 B01 描述的"只留先到者"在 `normalize.py` 这一层**不成立**。
- **事实**：改动前 `normalize.py` 里没有任何方向语义字面量（`grep SYMMETRIC` 在 `normalize.py` 命中 0 次），
  连真正对称的谓词（相似/关联）也没有显式声明；`Assertion.direction` 永远取默认 `forward`。
- **判断（我的，不是评审的）**：`normalize.py` 的缺口不是"事实被丢"，而是"方向语义隐式 + 对称谓词重复存储"：
  对称谓词正反两向落成两条，下游 `store.related()` 只能靠 `direction=="symmetric"` 才双向成立，
  direction 恒为 forward 时对称事实实际被当成有向事实用。这次补的就是这一处。
- **事实（越界风险，见 §5）**：本工作树里真正"无序键 + 丢反向"的位置在
  `index_graph_service/graph_types.py:283 pair_key`（`tuple(sorted(...))`）与
  `index_graph_service/graph_extract.py:489-501`（`EXTRACT_REVERSE_DEDUP` 命中即 `skip_write: True`）。
  这条路径对**所有**谓词生效（含担保/控制/任职），不在本次授权修改范围内。

## 1. 修复前的真实输出（第一次跑，改动前）

脚本：`/tmp/probe_direction.py`（临时文件，未进仓库）；命令：
`PYTHONPATH=services/rag-alg/index_data_service <toolenv>/bin/python /tmp/probe_direction.py`

```
--- 担保(有向) (reversed=False) ---
  input : ['甲 -担保-> 乙', '乙 -担保-> 甲']
  stats : {'facts_in': 2, 'facts_out': 2, 'dropped_no_source': 0, 'dropped_empty': 0, 'numeric': 0, 'relational': 2, 'unmapped_predicates': ['担保']}
  facts : [('乙', '担保', '甲', 1, 'forward'), ('甲', '担保', '乙', 1, 'forward')]
  count : 2
--- 担保(有向) (reversed=True) ---
  facts : [('乙', '担保', '甲', 1, 'forward'), ('甲', '担保', '乙', 1, 'forward')]
  count : 2
  order-independent: True

--- 控制(有向) 双跑 → count 2 / order-independent: True
--- 任职(有向) 双跑 → count 2 / order-independent: True

--- 相似(对称) (reversed=False) ---
  facts : [('乙', '相似', '甲', 1, 'forward'), ('甲', '相似', '乙', 1, 'forward')]
  count : 2
--- 相似(对称) (reversed=True) ---
  count : 2
  order-independent: True

--- 关联(对称) 双跑 → count 2 / order-independent: True
--- 未知谓词(随手写的) 双跑 → count 2 / order-independent: True

--- 同向重复 (reversed=False) ---
  facts : [('甲', '担保', '乙', 1, 'forward')]
  count : 1

--- 三角 (reversed=False) ---
  facts : [('乙', '担保', '丙', 1, 'forward'), ('甲', '担保', '丙', 1, 'forward'), ('甲', '担保', '乙', 1, 'forward')]
  count : 3
```

修复前读数（逐条回答任务书的三个问题）：
1. 两个方向是否只剩一条？—— **否**，两条都在（担保/控制/任职/未知谓词 count 均为 2）。
2. 丢的是哪条？—— **没丢**；被悄悄合并的是**对称谓词**（相似/关联 count=1 应为 1，但实为 2 → 重复而非丢失）。
3. 是否依赖输入顺序？—— **不依赖**，8 个用例对调顺序后 `order-independent: True`。

## 2. 改了什么（`normalize.py`，41 insertions / 3 deletions，只动去重/方向这一处）

- 新增 `SYMMETRIC_PREDICATES = {"相似", "关联"}`：方向语义**显式**陈列，不在表里的一律按非对称处理。
- 新增 `predicate_direction(predicate) -> "symmetric"|"forward"`：唯一判据就是该字典。
- 新增 `dedup_key(predicate, subject_id, object_id)`：**"两条三元组算不算同一事实"的唯一决定点**。
  - 非对称 → `(predicate, subject, object)` 有序键，正反两向键不同，两条都保留；
  - 对称 → 端点先排序再用，无序键，正反两向键相同，交给 `AssertionStore.add` 按内容键合并来源。
- `build_store` 的 rel关系分支改为：`_, subj_id, obj_id = dedup_key(...)`，并显式传
  `direction=predicate_direction(predicate)`；数值分支、阈值、实体归一（`entity_id`/`PREDICATE_MAP`）、
  来源绑定与丢弃计数**未改**。
- 注释里写清了"为什么默认非对称"：误合并会把真实事实整条丢掉且从图里看不出来（`facts_out` 照样计数），
  多留一条最坏只是重复；两类错误代价不对称，所以查不到就保留两条。

副作用（已在代码注释与本文件写明）：对称谓词的断言以"排序在前的端点"作 subject，
`store.facts(某端点)` 对对称谓词只命中排序在前的一侧；方向无关查询请用 `store.related()`
（它认 `direction="symmetric"`，两个方向都返回 True）。

## 3. 修复后的真实输出（同一脚本，改动后）

```
--- 担保(有向) (reversed=False) ---
  facts : [('乙', '担保', '甲', 1, 'forward'), ('甲', '担保', '乙', 1, 'forward')]   count : 2
--- 担保(有向) (reversed=True) ---
  facts : [('乙', '担保', '甲', 1, 'forward'), ('甲', '担保', '乙', 1, 'forward')]   count : 2
  order-independent: True
--- 控制(有向) / 任职(有向) 双跑 → count 2 / order-independent: True

--- 相似(对称) (reversed=False) ---
  facts : [('乙', '相似', '甲', 1, 'symmetric')]   count : 1
--- 相似(对称) (reversed=True) ---
  facts : [('乙', '相似', '甲', 1, 'symmetric')]   count : 1
  order-independent: True
--- 关联(对称) 双跑 → count 1 / direction=symmetric / order-independent: True
--- 未知谓词(随手写的) 双跑 → count 2 / order-independent: True
--- 同向重复 → count 1
--- 三角 → count 3
```

修复前后差异（一句话）：有向谓词**前后都是 2 条**（本来就没错，本次加断言把它钉住，防回归）；
对称谓词从 **2 条 → 1 条**且 `direction` 由 `forward` 变 `symmetric`（正反两向不再是两条并列事实）；
其余用例条数与顺序无关性不变。**没有任何用例的"事实条数"变少**，即没有以丢事实换去重。

## 4. 测试与变异（不空转的证据）

`tests/test_semantics_direction.py`，9 项：

1. `test_directed_predicate_keeps_both_directions`：担保双向 → 2 条，且两个方向 `related()` 都为 True；
2. `test_directed_predicates_control_and_employment_both_kept`：控制/任职各双向 → 4 条，全 forward；
3. `test_result_does_not_depend_on_input_order`：输入顺序对调 → 断言集合与条数完全相同；
4. `test_same_direction_duplicate_merges_sources`：同向重复（两个 doc）→ 1 条、来源 `{chunk-0, chunk-1}` 合并；
5. `test_symmetric_predicate_merges_both_directions`：相似双向（两个 doc）→ 1 条、`direction=symmetric`、来源合并、`related()` 双向 True；
6. `test_symmetric_predicate_guanlian_merged_too`：关联同上 → 1 条；
7. `test_unknown_predicate_defaults_to_forward_and_keeps_two`：未知谓词双向 → 2 条，不全在 `SYMMETRIC_PREDICATES`；
8. `test_dedup_key_is_ordered_for_asymmetric_and_unordered_for_symmetric`：`dedup_key` 有序/无序契约的直接单测；
9. `test_triangle_triples_are_not_merged`：`甲→乙 / 乙→丙 / 甲→丙` → 3 条，不误合。

```
$ PYTHONPATH=services/rag-alg/index_data_service /home/szf/data/dev/llmke-v2-toolenv/bin/python -m pytest tests/test_semantics_direction.py -q
.........                                                                [100%]
9 passed in 0.08s
```

相邻既有测试（无回归）：

```
$ ... -m pytest tests/test_graph_normalize.py tests/test_graph_assertions.py tests/test_graph_engine_capabilities.py \
      tests/test_graph_pipeline.py tests/test_graph_api.py tests/test_semantics_direction.py -q
39 passed, 1 skipped in 0.11s
```

变异复验（证明断言不是恒真）：

- 变异 1：`SYMMETRIC_PREDICATES = set()`（对称表清空）→ `4 failed, 5 passed`
  （`test_result_does_not_depend_on_input_order`、两个 symmetric 用例、dedup_key 契约用例）。
- 变异 2：`dedup_key` 去掉对称判据、所有谓词都用无序键（**精确复现 B01**）→ `6 failed, 3 passed`
  （有向双向量、控制任职、顺序无关、未知谓词、dedup_key 契约、三角全部报警）。
- 两次变异后均已恢复：`md5sum normalize.py` = `111dc21dce0643d5daaf237c1ab27442`（与备份一致），复跑 `16 passed`。

## 5. 我没做的部分（边界，务必按此交叉核对）

1. **没有修 `index_graph_service` 的真实丢事实路径**。本工作树 `graph_types.pair_key`（283 行）用
   `tuple(sorted((src, dst)))` 做无序键，`graph_extract.py:489-501` 在 `EXTRACT_REVERSE_DEDUP=1`（默认开）
   时把反向三元组标 `skip_write: True` 直接不写。这条对**所有**谓词生效，正是 B01 描述的形态，
   但不在我被授权的 3 个文件内 —— 且 R15 的修法在另一个工作树、未提交，不能拷。
   **结论：`normalize.py` 这一层现在是对的，但端到端 B01 仍未关闭。**
2. 没有改 `assertions.py`（`content_key` 未动，`Assertion.direction` 语义未动）。
3. 没有改阈值、`PREDICATE_MAP`、`entity_id` 归一规则、来源绑定/丢弃计数逻辑。
4. 没有给 stats 增加新计数键（保持 `facts_in/facts_out/dropped_*/numeric/relational/unmapped_predicates` 原样）。
5. 没有 git add / commit；没有跑全量测试；没有碰同团队另外两个角色的文件。
6. 没有把 相似/关联 加进 `PREDICATE_MAP`，因此它们仍会出现在 `unmapped_predicates` 里（谓词归一字典
   与方向语义字典是两件事，未合并以免改变既有统计口径）。
