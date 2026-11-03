# T-A4 自证：B01 关系去重键方向性（r12 复跑 + 变异复演 + 基线复演 + 合入 V2 迁移方案）

- 任务：`docs/v2-tasks/TASKS.yaml` → `T-A4`（acceptance D2/D5）
- 执行人：TL（tl-audit）
- 日期：2026-11-03
- 工作树：`/home/szf/data/dev/llmke-r12`（分支 `feature/R12-real-rag`，HEAD `100e261`）
- 解释器：`python3` → `/usr/bin/python3`（Python 3.10.12）。**本次全部命令未设 PYTHONPATH**，`tests/test_graph_direction_b01.py` 自带 `sys.path` 注入。

## 0. 开工前工作树状态（原样）

```
$ cd /home/szf/data/dev/llmke-v2 && git status --short
（空）
$ git branch --show-current
design/v2-input-engine-adoption-20261030-2101
$ git log --oneline -1
6dd3b4f docs(v2): 落盘 T-A1..T-A4 深审自证派任务书与台账

$ cd /home/szf/data/dev/llmke-r12 && git status --short
 M platform/r12/conf/rag-index-service/application-r12.yml
 M platform/r12/conf/rag-qa-service/application-r12.yml
 M platform/r15/acceptance/results/last-run.json
 M services/rag-java/rag-parent/rag-qa-service/src/main/java/com/gientech/ragqaservice/application/service/impl/AiServiceImpl.java
?? platform/r12/conf/rag-index-service/application-r12.yml.bak-20261102
?? platform/r12/conf/rag-qa-service/application-r12.yml.bak-20261102
?? platform/r15/acceptance/results/2026-10-30T20-57-07/
?? platform/r15/acceptance/results/2026-10-30T20-59-12/
$ git branch --show-current
feature/R12-real-rag
$ git log --oneline -3
100e261 docs(reviews): B01 收尾证据 —— 去重键方向性、基线失败归因与未做项
0bac08a fix(r15/b01): pair_key 带方向 + 关系本体分流，禁止 sorted() 压平端点对
419a87d docs(r15): 会话交接文件 —— 状态/成果/未完成/坑/下一步
```

说明（事实，不作推断）：r12 工作树有 4 个已修改 + 4 个未跟踪项，`platform/r12/conf/**` 与 `AiServiceImpl.java` 属另项在途改动，**均不在 `0bac08a` 内**（见 §1 的 `git show --name-only`）。

## 1. 修复本体与文件指纹

```
$ cd /home/szf/data/dev/llmke-r12 && git show --name-only --format="" 0bac08a
services/rag-alg/index_data_service/index_graph_service/graph_types.py
tests/test_graph_direction_b01.py

$ md5sum services/rag-alg/index_data_service/index_graph_service/graph_types.py tests/test_graph_direction_b01.py
0712caa7c2359c01ff95e7bb83947982  services/rag-alg/index_data_service/index_graph_service/graph_types.py
7de6a25fd324cc517f27ac3a218280d0  tests/test_graph_direction_b01.py
```

与 `B01-evidence-100e261.md:21-22` 登记的 md5 逐位一致（`0712caa7…` / `7de6a25f…`）。

三个关键实现位置（绝对路径:行号）：

| 位置 | 内容 |
|---|---|
| `/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service/graph_types.py:442` | `PAIR_KEY_SCHEME = "b01-ontology-directed-v1"` |
| 同上 `:454-467` | `pair_key`：对称谓词走 `tuple(sorted(...))`，其余谓词 `return (r, (a, b))`（**有向**） |
| 同上 `:182-194` | `direction_determinable`：未登记 → `False, "predicate_unregistered"`；`domain==range` / 通配 → `False` |
| 同上 `:517-542` | `is_reverse_duplicate`：方向不可裁决时反向**不**算重复（双向保留） |
| 同上 `:445-451` | `undirected_pair_key`：仅服务拓扑投影，`sorted()` 只剩在这里（且有 doc 警告） |

## 2. 命令一：复跑 28 tests（r12 工作树）

```
$ cd /home/szf/data/dev/llmke-r12 && python3 -m pytest -p no:cacheprovider tests/test_graph_direction_b01.py -q
............................                                             [100%]
28 passed in 0.02s
```

`-p no:cacheprovider` 只是不写 `.pytest_cache`（避免污染 r12 工作树），不影响用例集合。B01 原文（`B01-evidence-100e261.md:33-34`）为 `28 passed in 0.07s`，**用例数与结论一致**，耗时差异属正常抖动。

## 3. 命令二：变异复演 3 组

为不污染 r12 工作树（它已有在途改动），变异在**独立临时工作树**做，基线 HEAD 与被测文件与 r12 一致：

```
$ cd /home/szf/data/dev/llmke-r12 && git worktree add --detach /tmp/tl-a4-mut 100e261
准备工作区（分离头指针 100e261）
```

三组变异都用 python 精确字符串替换（记录 md5 前后值），每次改前/改后用 `git show HEAD:<path>`（**不是 checkout**）恢复。

### 3.0 基线（未变异）

```
$ cd /tmp/tl-a4-mut && md5sum services/rag-alg/index_data_service/index_graph_service/graph_types.py
0712caa7c2359c01ff95e7bb83947982  services/rag-alg/index_data_service/index_graph_service/graph_types.py
$ python3 -m pytest -p no:cacheprovider tests/test_graph_direction_b01.py -q
............................                                             [100%]
28 passed in 0.04s
```

### 3.1 变异 A：`pair_key` 一律无序键（精确复现 B01）

替换 `graph_types.py:465-467` 的非对称分支：

```python
-    return (r, (a, b))
+    return (r, tuple(sorted((a, b))))  # MUT-A: 精确复现 B01——一律无序键
```

```
$ md5sum services/rag-alg/index_data_service/index_graph_service/graph_types.py
0861b5e624a63b11e7392bb8d1078e5c  services/rag-alg/index_data_service/index_graph_service/graph_types.py
$ python3 -m pytest -p no:cacheprovider tests/test_graph_direction_b01.py -q
FAILED tests/test_graph_direction_b01.py::test_pair_key_is_directed_for_every_asymmetric_predicate[\u968f\u624b\u5199\u7684\u8c13\u8bcd]
FAILED tests/test_graph_direction_b01.py::test_domain_range_decided_reverse_is_duplicate_but_key_stays_directed
FAILED tests/test_graph_direction_b01.py::test_existing_pairs_across_batches_are_respected
23 failed, 5 passed in 0.12s
```

→ 与 B01 原文 `23 failed / 5 passed`（`B01-evidence-100e261.md:74`）**逐数一致**。

### 3.2 变异 B：删掉对称分支（真对称谓词被当有向）

```
$ git show HEAD:services/.../graph_types.py > services/.../graph_types.py
$ md5sum services/.../graph_types.py
0712caa7c2359c01ff95e7bb83947982  services/.../graph_types.py      # 已恢复
```

替换 `:465` 的条件：

```python
-    if is_symmetric_relation(rel):
+    if False:  # MUT-B: 删掉对称分支，真对称谓词被当有向
```

```
$ md5sum services/rag-alg/index_data_service/index_graph_service/graph_types.py
822fd1e6c9357a2b8cd2e18143b8e19e  services/rag-alg/index_data_service/index_graph_service/graph_types.py
$ python3 -m pytest -p no:cacheprovider tests/test_graph_direction_b01.py -q
tests/test_graph_direction_b01.py:75: AssertionError
FAILED tests/test_graph_direction_b01.py::test_explicitly_symmetric_predicate_still_merged
1 failed, 27 passed in 0.04s
```

→ 与 B01 原文 `1 failed`（同文件 `:75`）一致，失败用例名相同。

### 3.3 变异 C：未登记谓词误判为"方向可裁决"

```
$ git show HEAD:services/.../graph_types.py > services/.../graph_types.py
$ md5sum services/.../graph_types.py
0712caa7c2359c01ff95e7bb83947982  services/.../graph_types.py      # 已恢复
```

替换 `:185-186`：

```python
     if spec is None:
-        return False, "predicate_unregistered"
+        return True, "predicate_unregistered"  # MUT-C: 未登记谓词误判为方向可裁决
```

```
$ md5sum services/rag-alg/index_data_service/index_graph_service/graph_types.py
1fe4639c1c8fb39d2ab4530646181326  services/rag-alg/index_data_service/index_graph_service/graph_types.py
$ python3 -m pytest -p no:cacheprovider tests/test_graph_direction_b01.py -q
tests/test_graph_direction_b01.py:129: AssertionError
FAILED tests/test_graph_direction_b01.py::test_reverse_directed_predicate_is_not_merged
FAILED tests/test_graph_direction_b01.py::test_unknown_predicate_keeps_both_directions
FAILED tests/test_graph_direction_b01.py::test_existing_pairs_across_batches_are_respected
3 failed, 25 passed in 0.05s
```

→ 与 B01 原文 `3 failed`（同文件 `:76`，列出的三个用例）一致。

### 3.4 三次变异后恢复并复验

```
$ git show HEAD:services/.../graph_types.py > services/.../graph_types.py
$ md5sum services/rag-alg/index_data_service/index_graph_service/graph_types.py
0712caa7c2359c01ff95e7bb83947982  services/rag-alg/index_data_service/index_graph_service/graph_types.py
$ python3 -m pytest -p no:cacheprovider tests/test_graph_direction_b01.py -q
............................                                             [100%]
28 passed in 0.05s
$ git status --short
（空）
```

**结论（事实）**：3 组变异全部被捕获，方向/对称/未登记三条断言都不是空转；恢复后指纹回到 `0712caa7…`，临时工作树无残留改动。

## 4. 命令三：基线 20 failed 在干净 worktree 复演

基线取 `0bac08a` 的父提交 `419a87d`（**不含本次任何改动**）：

```
$ cd /home/szf/data/dev/llmke-r12 && git worktree add --detach /tmp/tl-a4-baseline 419a87d
准备工作区（分离头指针 419a87d）

$ cd /tmp/tl-a4-baseline && git log --oneline -1
419a87d docs(r15): 会话交接文件 —— 状态/成果/未完成/坑/下一步
$ md5sum services/rag-alg/index_data_service/index_graph_service/graph_types.py
61d74ac93dc665469962759224a1f230  services/rag-alg/index_data_service/index_graph_service/graph_types.py
$ ls tests/test_graph_direction_b01.py
ls: 无法访问 'tests/test_graph_direction_b01.py': 没有那个文件或目录
```

（该基线文件 md5 `61d74ac9…` **与 V2 当前文件完全相同**，见 §5.2——这是迁移可行性的依据。）

### 4.1 三组失败文件复跑

```
$ cd /tmp/tl-a4-baseline && python3 -m pytest -p no:cacheprovider \
    tests/test_contract_toolchain.py tests/test_review_regressions.py tests/test_security_scan.py -q
...
FAILED tests/test_contract_toolchain.py::test_domain_layer_ui_binding_fails
FAILED tests/test_contract_toolchain.py::test_bff_layer_ui_binding_passes - A...
FAILED tests/test_contract_toolchain.py::test_duplicate_registry_key_fails - ...
FAILED tests/test_review_regressions.py::test_P04_noop_cannot_certify_stale_output
FAILED tests/test_review_regressions.py::test_P05_empty_output_report_rejected
FAILED tests/test_review_regressions.py::test_P06_unresolvable_ref_rejected
FAILED tests/test_security_scan.py::test_framework_repo_itself_is_clean - Ass...
20 failed, 22 passed in 23.23s
```

按文件拆：

```
$ for f in tests/test_contract_toolchain.py tests/test_review_regressions.py tests/test_security_scan.py; do echo "=== $f"; python3 -m pytest -p no:cacheprovider $f -q | tail -2; done
=== tests/test_contract_toolchain.py
16 failed in 1.84s
=== tests/test_review_regressions.py
3 failed, 10 passed in 1.91s
=== tests/test_security_scan.py
1 failed, 12 passed in 18.96s
```

→ 16 + 3 + 1 = 20，与 `B01-evidence-100e261.md:62-66` 的 16/3/1 一致。

### 4.2 失败根因（实测，不是引用别人的理由）

```
$ /usr/bin/python3 -V
Python 3.10.12
$ /usr/bin/python3 -c "import openapi_spec_validator"
ModuleNotFoundError: No module named 'openapi_spec_validator'
$ which python3
/usr/bin/python3
$ python3 -c "import openapi_spec_validator"
ModuleNotFoundError: No module named 'openapi_spec_validator'
```

即**当前 `python3` 就是 `/usr/bin/python3`，且缺 `openapi_spec_validator`**。子进程证据（`--tb=line`）：

```
$ python3 -m pytest -p no:cacheprovider "tests/test_contract_toolchain.py::test_duplicate_registry_key_fails" -q --tb=line | tail -6
     +    where <built-in method lower of str object at 0x...> = ''.lower
     +      where '' = CompletedProcess(args=['/usr/bin/python3', '/tmp/tl-a4-baseline/scripts/contract_check.py', '--root', '/tmp/pytest-of-...spec_validator import validate as validate_openapi\nModuleNotFoundError: No module named 'openapi_spec_validator'\n').stdout
/tmp/tl-a4-baseline/tests/test_contract_toolchain.py:198: AssertionError: assert (1 != 0 and 'duplicate' in '')
1 failed in 0.11s
```

`tests/test_contract_toolchain.py` 16 项失败输出中含 `openapi_spec_validator` 的行数：`24` 行（`grep -c`）。

security_scan 那 1 项：

```
$ python3 -m pytest -p no:cacheprovider tests/test_security_scan.py::test_framework_repo_itself_is_clean -q --tb=line | tail -4
/tmp/tl-a4-baseline/tests/test_security_scan.py:100: AssertionError: FAIL: docs/r12/ADAPTATIONS.md:11: PERSONAL_ABSOLUTE_PATH: /home/szf/
1 failed in 17.26s
```

→ 仓内既有绝对路径卫生问题，与 B01 无关。

### 4.3 全量对比（最能说明"新增 0 失败"的一组）

```
# 基线 419a87d（不含 B01）
$ cd /tmp/tl-a4-baseline && python3 -m pytest -p no:cacheprovider tests/ modules/ -q | tail -3
20 failed, 258 passed, 44 skipped in 66.20s (0:01:06)

# 修复后 100e261（含 B01）
$ cd /tmp/tl-a4-mut && python3 -m pytest -p no:cacheprovider tests/ modules/ -q | tail -3
20 failed, 286 passed, 44 skipped in 66.46s (0:01:06)
```

| 口径 | failed | passed | skipped |
|---|---|---|---|
| 419a87d（B01 前） | 20 | 258 | 44 |
| 100e261（B01 后） | 20 | 286 | 44 |
| 差 | **0** | **+28** | 0 |

**结论（事实）**：`+28 passed` 恰为新增测试数，失败集合不变 → B01 未引入新失败。B01 原文写的是"20 failed / 286 passed / 44 skipped"（`B01-evidence-100e261.md:50`），与本次 100e261 复跑逐数一致；本次额外补了"基线也是 20 failed"这一半。

## 5. 合入 V2 的迁移方案

### 5.1 补丁可移植性（实测，非推断）

```
$ cd /home/szf/data/dev/llmke-r12 && git format-patch -1 0bac08a --stdout > /tmp/b01-full.patch
$ cd /home/szf/data/dev/llmke-v2 && git apply --check --stat /tmp/b01-full.patch
 .../index_graph_service/graph_types.py             |  399 +++++++++++++++++---
 tests/test_graph_direction_b01.py                  |  140 +++++
 2 files changed, 487 insertions(+), 52 deletions(-)
$ git apply --check /tmp/b01-full.patch; echo "APPLY_CHECK_EXIT=$?"
APPLY_CHECK_EXIT=0
```

`exit 0` = 补丁在 V2 当前树上可干净应用（仅 check，**未实际落地**）。

原因（实测指纹，三文件全部同源）：

| 文件 | 419a87d（补丁父提交） | V2 当前 |
|---|---|---|
| `services/rag-alg/index_data_service/index_graph_service/graph_types.py` | `61d74ac93dc665469962759224a1f230` | `61d74ac93dc665469962759224a1f230` |
| 同目录 `graph_service.py` | `cdf2224f59eb8862038d968cedc114d2` | `cdf2224f59eb8862038d968cedc114d2` |
| 同目录 `graph_extract.py` | `2699b4445360d126e0d1ce1755d6d7c9` | `2699b4445360d126e0d1ce1755d6d7c9` |

### 5.2 契约兼容性（V2 的 relations 契约已声明 B01 规则，且语义等价）

```
$ diff <(python3 -m json.tool /home/szf/data/dev/llmke-r12/contracts/ontology/relations.v1.json) \
       <(python3 -m json.tool /home/szf/data/dev/llmke-v2/contracts/ontology/relations.v1.json)
340c340,351
<   "reverse_dedup": "写入前用 (name, 无序端点对) 判重；..."
---
>   "reverse_dedup": "写入前判重口径按谓词对称性分流：symmetric=true 用 (name, 无序端点对)…"
>   "direction_resolution": {
>       "symmetric_true": "same_fact_unordered_key_keep_one",
>       "symmetric_false_domain_range_known": "reverse_is_spurious_only_when_endpoint_types_violate_domain_range",
>       "symmetric_false_unresolved": "keep_both_directions_and_record_direction_unresolved",
>       "cross_batch": "…方向不可裁决时不以新边覆盖已有反向边",
>       "forbidden": ["sorted_undirected_key_for_all_predicates", "first_writer_wins"],
>       "change_request": "BL-2.0.0-01"
>   },
```

即：**V2 的契约比 r12 更严**——它已经把 `sorted_undirected_key_for_all_predicates` 与 `first_writer_wins` 列为 forbidden，但 V2 的代码（`graph_types.py:283-289`）仍是 `return (clean_name(rel), tuple(sorted(...)))`，即**契约已声明、代码未落实**。

结构等价性核对：

```
$ python3 - <<'EOF'
import json
r12=json.load(open('.../llmke-r12/contracts/ontology/relations.v1.json'))
v2 =json.load(open('.../llmke-v2/contracts/ontology/relations.v1.json'))
...
EOF
r12 relations: 18  v2 relations: 18
only r12: []
only v2: []
r12 symmetric: ['关联', '相似']
v2 symmetric: ['关联', '相似']
r12 domain+range count: 18  v2: 18
v2 missing domain/range: []
```

用 **V2 自己的契约文件**替换后，B01 全部用例仍通过：

```
$ cd /tmp/tl-a4-mut && cp /home/szf/data/dev/llmke-v2/contracts/ontology/relations.v1.json contracts/ontology/relations.v1.json
$ md5sum contracts/ontology/relations.v1.json
12071229b10c011c3dab8b1756fa870b  contracts/ontology/relations.v1.json
$ python3 -m pytest -p no:cacheprovider tests/test_graph_direction_b01.py -q
............................                                             [100%]
28 passed in 0.02s
$ git show HEAD:contracts/ontology/relations.v1.json > contracts/ontology/relations.v1.json
$ md5sum contracts/ontology/relations.v1.json
eea66a8c37d152f517b4aaaea75ac6a7  contracts/ontology/relations.v1.json
$ git status --short
（空）
```

→ r12 与 V2 的 relations 契约在 `name/symmetric/domain/range` 三个决定分支的字段上等价，28 项判定不因换契约而变。

### 5.3 迁移步骤（合入路径）

前提事实：`0bac08a` 只改 2 个文件，**不改 Nebula schema、不改边 rank 算法**（`_edge_rank` 在 `graph_service.py:23-35`，仍是 `sha1(src␟rel␟dst)`），故存储格式零变更。

| 步 | 动作 | 判据 |
|---|---|---|
| M1 | `git apply /tmp/b01-full.patch` 打到 V2（2 文件：`graph_types.py`、新增 `tests/test_graph_direction_b01.py`） | `git apply --check` exit 0（已验，§5.1） |
| M2 | `cd /home/szf/data/dev/llmke-v2 && python3 -m pytest -p no:cacheprovider tests/test_graph_direction_b01.py -q` | 28 passed（依据：本文件 §3.0 + §5.2 换 V2 契约后仍 28 passed） |
| M3 | 全量回归：`python3 -m pytest tests/ modules/ -q` | 失败集合与迁移前一致（本文件 §4.3 给出对照基线与增量口径） |
| M4 | 清库重写存量图（仅 `index_graph_service` 写的 Nebula space，见 §5.4） | 见 §5.5 校验判据 |
| M5 | 记录 `PAIR_KEY_SCHEME=b01-ontology-directed-v1` 与新报告字段（r12 已把 `pair_key_scheme` 写进 report，`graph_types.py:1019` 附近） | 报告字段可读 |

### 5.4 存量 `g_kb_9` 清库重写：范围 / 顺序 / 回滚

**范围（可静态取证的部分）**

- 受影响写路径 = `services/rag-alg/index_data_service/index_graph_service/`（写 Nebula）。去重唯一入口链：`graph_service.py:362` → `graph_types.py:355` `filter_reverse_duplicates` → `:283` `pair_key`；批内去重在 `graph_types.py:672-678`。
- **HippoRAG 适配器路径不受 B01 影响**（不同实现、已是有向键）：`services/rag-alg/index_data_service/graph_engine_adapter/normalize.py:54-68` `dedup_key` —— 仅 `SYMMETRIC_PREDICATES = {"相似","关联"}`（`:46`）走无序，其余 `return (predicate, subject_id, object_id)` 有序。故迁移**不需要**重写 HippoRAG 侧 `community/facts` 数据。
- 空间命名：`g_kb_<kb_id>`，Java 侧注释确认 `g_kb_9`（`services/rag-java/rag-parent/rag-index-service/.../FileAppServiceImpl.java:629`）。
- 受影响 KB 的**具体清单与边数**：**UNVERIFIED**。原因见 §5.7（Nebula 9669 当前未监听），不敢用旧记录冒充。

**顺序（依据既有清库工具的行为，不自造流程）**

1. **冻结写入**：先使 `generate-graph` 不再写该 space（停 index-service 图任务或改指向），避免清洗期间新边混入。理由：跨批次去重依赖写入前回读（`graph_service.py:355-368`），并发写会让"清理后仍出现反向重复"。
2. **快照（回滚底牌）**：`platform/r12/qa/tools/r15_w09_clean_graph.py --dry-run` —— 该脚本首行注释即"**先备份再改**"，`--dry-run` 只统计与导出快照，`--apply` 才执行，快照落 `platform/r12/qa/evidence/r15/w09-clean/`（同文件 `:8-24`）。
3. **清空**：`graph_service.py:180-206` `del_space_data`，`condition_json` 为空时执行 `DROP SPACE IF EXISTS <space>`（`:193`）。按 **KB 粒度**逐个 space 清，不做跨 KB 批量。
4. **重建**：按原文档集重新走"抽取 → `normalize_graph_data` → `filter_reverse_duplicates` 写边"，**不复用旧边做增量修补**。
5. **校验**：见 §5.5。

**为什么必须"清库重写"而不是就地修复（论证，基于代码事实）**

旧实现用无序键 + 先到者，丢失发生在**写之前**：`graph_types.py` 内 `filter_reverse_duplicates` 把反向视作同一事实后，被丢的那条**根本没有进 Nebula**。所以存量里"两条互相担保"只剩一条，属于**存储中不存在的数据**，只能从源 facts 重建；就地改 `pair_key` 无法把它们变回来。

**回滚**

- 代码回滚：`git revert` B01 补丁即可（不改 schema、不改 rank 算法，回滚无数据兼容风险）。
- 数据回滚：用步骤 2 的快照重建 space；或 `DROP SPACE` 后按快照导入。
- 风险声明：若步骤 1 未做到（写入未冻结）就 `DROP SPACE`，会丢掉冻结期间新抽取的边——这是本次迁移唯一不可逆点，必须在步骤 1 之后、步骤 2 之前确认无在跑图任务。

### 5.5 重写后的校验判据（可复算）

1. 同一谓词、同一无序端点对、**两端 domain/range 可裁决** → 反向边条数 = 0；
2. 未登记谓词（如 `担保`）、`domain==range`、通配 → 双向边条数 = 2（`graph_types.py:517-542` 语义）；
3. 对称谓词（`相似`/`关联`）→ 合并为一条；
4. 断言总数：重建后 ≥ 重建前（旧实现丢事实，重建只会更多，不该更少）；
5. 报告里 `pair_key_scheme = b01-ontology-directed-v1`。

## 6. 未做项与阻塞（不补理由，只报事实）

| 项 | 状态 | 依据 |
|---|---|---|
| 补丁**实际落地**到 V2 | 未做（任务要求的是"迁移方案"） | 本文件只做 `git apply --check`（exit 0），V2 工作树 `git status` 仍为空 |
| 存量 `g_kb_9` 边数 / 反向重复计数 / 丢失事实数 | **UNVERIFIED** | Nebula 9669 未监听，见 §5.7 |
| 真实入库 + 图库端到端验收 | 未做（属 W 项） | 同 `B01-evidence-100e261.md:82-83` |
| 推送远端 | 未做 | `0bac08a` / `100e261` 仅在 r12 本地分支 |

### 5.7 存量数据无法取证的原因（实测）

```
$ ss -ltnp | grep -E ":9669|:19531|:19532|:18094"
LISTEN 0  2048  127.0.0.1:18094  0.0.0.0:*  users:(("python",pid=855454,fd=12),("python",pid=853838,fd=12))
LISTEN 0  2048  127.0.0.1:19531  0.0.0.0:*  users:((\"python\",pid=1486048,fd=12))
LISTEN 0  2048  127.0.0.1:19532  0.0.0.0:*  users:((\"python\",pid=833544,fd=12))
$ ss -ltn | grep -c ":9669"
0
```

Nebula graphd（9669）未启动 → 无法只读取证 `g_kb_9` 存量。按纪律"不动运行中服务"，**未自行启动 Nebula**。恢复条件：取得"允许启动 Nebula 只读查询"的授权后，执行

```
ngql: SHOW SPACES;  USE g_kb_9;
      MATCH ()-[e:relationship]->() RETURN count(e) AS edges;
# 反向对计数：按 (relationship, 无序端点对) 分组取 count>1 的组
```

## 7. 一行结论

B01 在 r12 的 28 项测试、3 组变异（23/1/3 failed）、基线 20 failed（与 B01 前全量 258 passed 对照 → 修复后 286 passed，失败数不变）**三条全部按原文复现**；补丁对 V2 可干净应用（`git apply --check` exit 0，三文件指纹同源、契约字段等价、换 V2 契约仍 28 passed），存储格式零变更，迁移路径 = 打补丁 + 按 KB 清库重建；**存量 `g_kb_9` 的实际边数与丢失量 UNVERIFIED，因 Nebula 9669 未启动**。

## 8. 更正（2026-11-03 15:25）：Nebula **是在跑的**，只是宿主端口是 19669

§5.7 当时写"Nebula 9669 未监听 → 无法取证"。这句话本身没错（宿主机 9669 确实没监听），但**结论容易被误读成"Nebula 没跑"**，必须更正：

```
$ docker ps --format '{{.Names}} {{.Ports}}' | grep -i nebula
r12-nebula-graphd    19669-19670/tcp, 127.0.0.1:19669->9669/tcp      ← 宿主 19669 → 容器 9669
r12-nebula-storaged  9777-9780/tcp, 127.0.0.1:19779->19779/tcp
r12-nebula-metad     9559-9560/tcp, 127.0.0.1:19559->19559/tcp
```

即 Nebula graphd 以容器形式在跑，客户端应连 **127.0.0.1:19669**。

**仍未取证的真正原因**（不是"Nebula 没起"）：本机两个可用解释器都没有 nebula3 客户端；
容器 `r12-nebula-graphd` 内也没有 `nebula-console`（`docker exec … ls /usr/local/bin` 无输出）。

```
$ /home/szf/data/dev/hipporag-toolenv/bin/python -c "import nebula3"
ModuleNotFoundError: No module named 'nebula3'
$ /home/szf/data/dev/llmke-v2-toolenv/bin/python -c "import nebula3"
ModuleNotFoundError: No module named 'nebula3'
```

**补齐方式**（拿到 nebula3 客户端后一条命令即可，不涉及写库）：

```python
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
cfg = Config(); pool = ConnectionPool(); pool.init([("127.0.0.1", 19669)], cfg)
s = pool.get_session("root", "nebula")          # 口令见 platform/r12/.env，不入日志
s.execute("USE g_kb_9")
print(s.execute("MATCH ()-[e:relationship]->() RETURN count(e) AS edges").rows())
# 反向对：按 (relationship, 无序端点对) 分组取 count>1
```

结论不变：**B01 的代码/测试/变异/基线四条已复演；存量边数与反向重复计数仍 UNVERIFIED**，
但现在给出的是真实原因（缺客户端），而不是"Nebula 没跑"。
