# B01 收尾证据：关系去重键必须带方向

- 评审项：外部评审 **B01**（关系去重用无序键 → `甲 -担保-> 乙` 与 `乙 -担保-> 甲` 落成同一条，只留先到者）
- 仓库 / 分支：`llmke-r12` / `feature/R12-real-rag`
- 记录日期：2026-11-03
- 性质：**只加文档**。代码与测试已在 `0bac08a` 入库，本文件不修改任何代码、不改写 `0bac08a`。

## 1. 提交号与文件指纹

- 修复提交：**`0bac08a`** —— `fix(r15/b01): pair_key 带方向 + 关系本体分流，禁止 sorted() 压平端点对`
- 该提交只含 2 个文件（`git show --name-only 0bac08a`）：

| 文件 | md5 |
| --- | --- |
| `services/rag-alg/index_data_service/index_graph_service/graph_types.py` | `0712caa7c2359c01ff95e7bb83947982` |
| `tests/test_graph_direction_b01.py` | `7de6a25fd324cc517f27ac3a218280d0` |

- 未进入该提交的既有工作区改动（与本项无关，未暂存）：`platform/r12/conf/rag-index-service/application-r12.yml`、
  `platform/r12/conf/rag-qa-service/application-r12.yml`、`platform/r15/acceptance/results/last-run.json`
  及其 `.bak-*` / 结果目录。

## 2. 测试原样输出

命令：`python3 -m pytest tests/test_graph_direction_b01.py -q`（工作目录 `llmke-r12`，无需设置 `PYTHONPATH`——测试文件自带路径注入）

```
............................                                             [100%]
28 passed in 0.07s
```

覆盖范围（28 项 = 9 个用例，其中 1 个对全部非对称谓词参数化）：

1. `test_reverse_directed_predicate_is_not_merged`：`担保` 未登记 → 键有向、正反两条都保留、`is_reverse_duplicate` 双向 False；
2. `test_domain_eq_range_predicate_keeps_both_directions`：`办理流程中间`（domain==range）不可裁决 → 双向保留；
3. `test_unknown_predicate_keeps_both_directions`：未登记谓词 → 双向保留；
4. `test_explicitly_symmetric_predicate_still_merged`：`相似`/`关联` 仍合并为一条；
5. `test_symmetry_comes_from_contract_not_from_code`：对称性来自契约（`_REL_REASON == "contract"`），非硬编码；
6. `test_pair_key_is_directed_for_every_asymmetric_predicate`（参数化）：**全部**非对称谓词（16 条契约内 + `担保` + 未登记谓词）均满足 `pair_key(a,b) != pair_key(b,a)` 且端点保序 —— 这条专打 `sorted()` 回归；
7. `test_domain_range_decided_reverse_is_duplicate_but_key_stays_directed`：`利率基准`(product→metric) 键仍有向，反向由本体判为伪反向边；
8. `test_exact_duplicate_still_deduplicated` / `test_existing_pairs_across_batches_are_respected` / `test_alias_predicates_share_one_key` / `test_pair_key_scheme_is_declared`：既有去重能力未被削弱。

## 3. 基线证明：20 个失败是既有失败，本次新增 0 失败

- 本工作区 `make framework-test`（`pytest tests/ modules/ -q`）：**20 failed / 286 passed / 44 skipped**。
- 证明方式：`git worktree add /tmp/r12-baseline HEAD --detach`（HEAD = `419a87d`，即 `0bac08a` 之前，
  不含本次任何改动），在**干净工作树**复跑同样三组文件：

```
$ cd /tmp/r12-baseline && python3 -m pytest tests/test_contract_toolchain.py \
      tests/test_review_regressions.py tests/test_security_scan.py -q
20 failed, 22 passed in 31.68s
```

与本工作区完全一致（同为 20 failed），**故这 20 项与 B01 改动无关**。三组文件与真实原因：

| 文件 | 失败数 | 真实原因（`--tb=line` 实测） |
| --- | --- | --- |
| `tests/test_contract_toolchain.py` | 16 | 沙箱子进程用 `/usr/bin/python3` 调 `scripts/contract_generate.py`，该解释器缺依赖 → `ModuleNotFoundError: No module named 'openapi_spec_validator'`（环境缺依赖，非代码缺陷） |
| `tests/test_review_regressions.py` | 3 | 同一根因（P04/P05/P06 均先调 `contract_generate.py`，同上 `ModuleNotFoundError`） |
| `tests/test_security_scan.py` | 1 | `security_scan.py` 对本仓报 `FAIL (1859 findings)`，例如 `docs/r12/ADAPTATIONS.md:11: PERSONAL_ABSOLUTE_PATH`、`JdbcUtil.java:26-48: REAL_CONNECTION_STRING`（仓内既有卫生问题） |

- 本次新增测试 `tests/test_graph_direction_b01.py` 在上述 20 failed 之外，**新增失败 0 项**（28 passed 全绿）。

### 变异复验（证明断言不空转）

| 变异 | 结果 |
| --- | --- |
| A：`pair_key` 一律 `tuple(sorted(...))`（**精确复现 B01**） | `23 failed / 5 passed` |
| B：删掉对称分支（真对称谓词被当有向） | `1 failed`（`test_explicitly_symmetric_predicate_still_merged`） |
| C：未登记谓词误判为"方向可裁决" | `3 failed`（反向不合并 / 未知谓词双向保留 / 跨批次） |

三次变异均已恢复到 `md5 0712caa7c2359c01ff95e7bb83947982`，恢复后复跑 28 passed。

## 4. 明确未做项

1. **真实入库 / 图库端到端未做**：本次只改"事实身份键 + 反向去重分流"这一层，未跑真实 Nebula/Milvus 写入、
   未对 `g_kb_9` 存量做清库重写、未做 A02/N1 的端到端验收。相关验收属 **W 项**，不在 B01 范围内。
2. **未 push**：`0bac08a` 仅在本地 `feature/R12-real-rag`，未推任何远端分支（尤其未推 v2 分支）。
3. **未改本体契约**：`contracts/ontology/relations.v1.json`、`entity-types.v1.json` 未改；
   `platform/r12/conf/**`（Java 配置）未进入本次提交。
4. 未动运行中的服务（19531 / 19532 / 18094）。

## 5. 一行结论：`担保` 要变成"可裁决方向"必须走契约变更

`担保` 目前不在 `relations.v1.json` 里，所以按"未登记 → 方向不可裁决 → 两个方向都保留"处理；
要让它像 `利率基准` 那样由本体裁决方向（反向即伪反向边），必须在契约里登记 `domain`/`range`
（例：`担保` domain=`guarantor` range=`org`），**这是契约变更（走 CR / 业务确认），不是改代码**——
改代码去猜方向，正是 B01 要消除的形态。
