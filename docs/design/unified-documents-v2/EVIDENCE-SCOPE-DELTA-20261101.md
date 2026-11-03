# 按范围的增量重建（2026-11-01）

## 一句话

构建期隔离让每个可见范围各有一份索引，于是"改一份文档"要整份重建**该范围**的索引，
总成本 = 范围数 × 全量。`rebuild.rebuild_delta` 已经能"复制上一份快照 + 只对新增块抽取"，
本次补的是把它**落到某一个范围**上：范围各有根目录、各有指针，而路由清单是**一张总表**。

## 实现（`graph_engine_adapter/partition.py`，只加函数，未改已有函数语义）

- `delta_plan(root, scope, docs)` → `{base, docs, can_delta, reason}`
  - 用已有 `resolve(root, scope)` 找上一份快照；`docs` 按可见范围过滤好（`build_plan`）；
  - 原因码（给日志与断言用，不靠中文消息匹配）：`NO_MANIFEST` / `MANIFEST_UNREADABLE` /
    `SCOPE_NOT_LISTED` / `SNAPSHOT_DIR_MISSING` / `NO_DOCUMENTS` / `OK`；
  - **不兜底**：拿不到基准就 `can_delta=False`。这里若自作聪明回退全量，"增量"就成了无法观测的猜想。
- `scope_delta_build(root, scope, docs, build_fn, apply_fn, *, fencing=None, keep_last=2, allow_full_build=False)`
  - 目标目录固定在 `scope_dir(root, scope)` 下（同范围同根，否则路由与快照不是同一棵树）；
  - 可增量时复用 `rebuild_delta`（`fencing` 原样透传：旧主不能靠这条路绕开写入保护）；
  - 不可增量时**默认拒绝**；只有显式 `allow_full_build=True` 才走 `rebuild`，且返回值带
    `mode="FULL"` 与 `fallback_reason=<原因码>`——谁走了全量、为什么走，一眼可查（拒绝静默降级）；
  - 成功后**读旧清单 → 合并本范围条目 → 整表写回**：`write_manifest` 是整表覆盖，
    写漏一条，那条范围从此 `resolve()` 返回 None；
  - 失败（apply 抛异常 / 清单不可读 / 快照目录不存在）一律不动清单，范围指针也不动：
    路由继续指旧快照，旧快照继续服务；
  - 清单里其它范围的条目**原样带过**，本范围原有字段也保留（只更新 snapshot/documents/mode/
    generation/built_at/chunks）。

### 一处顺手加的保护

`rebuild._promote` 按**目录名排序**决定 `keep_last` 清理顺序，而快照名里的微秒尾巴
（`time.time_ns() % 1000000`）在同一秒内并不单调：同一秒内建两份时，名字序可能不等于时间序。
那是 `rebuild.py` 的既有命名约定（**不在本次改动范围，未修**）。本次只在编排层加了一条：
构建返回的 `current.dir` 若不存在，直接报错、清单留在旧快照上——宁可大声失败，
也不让清单指向空气（那会把"可解析"变成"解析到不存在的目录"）。

## 真跑（`scripts/v2_scope_delta_drill.py`，真实 LLM + 真实 embedding）

```
cd /home/szf/data/dev/llmke-v2
PYTHONPATH=services/rag-alg/index_data_service \
MINERU_TOOLS_CONFIG_JSON=/home/szf/data/dev/models/mineru/magic-pdf.json \
/home/szf/data/dev/hipporag-toolenv/bin/python scripts/v2_scope_delta_drill.py \
  --payloads /tmp/scope-payload.json --root .artifacts/scope-delta \
  --scopes dept-a dept-b --cjk-compat \
  --drop-file s-401 --add-text "补充条款：单笔授信超过五亿元须经董事会审议通过。" \
  --out .artifacts/scope-delta.json
```

语料：`/tmp/scope-payload.json` 10 块；`s-401（五级分类口径）` 只对 `dept-b` 可见，其余 public。
改动 = 删掉 `s-401` 的 1 块 + 在同一份文档（同 file_id、沿用 `["dept-b"]` 可见范围）新增 1 段，
因此**只有 dept-b 的内容集合变了**（这一条不是猜的：脚本用改前/改后两份 `build_plan` 直接比出来）。

阶段 1 —— 两个范围各建一次全量（`allow_full_build=True`，`mode=FULL`、`fallback_reason=NO_MANIFEST`）：

```
dept-a: 64.8s  documents=9   openie=9   dir_sha 2b9c017ed117...
dept-b: 69.3s  documents=10  openie=10  dir_sha 3667d6e8c6f3...
合计 134.2s
```

阶段 3 —— 只重建被影响的 `dept-b`，走增量：

```
dept-b: 8.9s  mode=DELTA  documents=10  openie=10
apply: deleted=1 added=1 reused=9 duplicates=0 remaining=10 expected=10 consistent=true
新快照 dir_sha 8f5bec8ac105...（与全量的 3667d6e8... 不同，说明目录是真的换了）
```

耗时：**全量 69.3s（单范围）/ 134.2s（两个范围）vs 增量 8.9s** ——
相对"整份重建这一个范围" **7.8×**，相对"范围数 × 全量" **15.1×**。
同参数在加入上节那条目录守卫**之前**跑过一次：67.9s / 78.7s / 9.9s → 7.9× / 14.8×。
两次量级一致，说明这个倍数不是单次抖动捡来的。

**未变更范围 dept-a**：快照目录、目录内容 sha（`2b9c017ed117...`）、指针文件 sha
三项全部未变（`all_unchanged=true`）。也就是说"改 dept-b 的文档"没有让 dept-a 重建哪怕一次。

**清单**（`scopes.json`）两条都在，且都能解析到存在的快照：

```
dept-a: listed=true resolvable=true snapshot_exists=true mode=FULL  documents=9  chunks=9
dept-b: listed=true resolvable=true snapshot_exists=true mode=DELTA documents=10 chunks=10
```

**内容级核对**（不只看指针，直接读快照里的 openie 落盘）：

```
dept-b 增量快照：10 段 passage，含新句「单笔授信超过五亿元须经董事会审议通过」1 处，
                 旧 s-401 的「次级：…」0 处 —— 删掉的真的没了，加上的真的在
dept-a 全量快照：9 段 passage，含新句 0 处 —— 没有因为 dept-b 的改动被污染
```

## 测试（`tests/test_partition_delta.py`，14 项）

```
PYTHONPATH=services/rag-alg/index_data_service ... -m pytest tests/test_partition_delta.py -q
14 passed in 1.27s      # 连跑两遍结果一致
```

1. 无基线 → `can_delta=False`（`NO_MANIFEST`）；
2. 清单里范围缺失 → `can_delta=False`（`SCOPE_NOT_LISTED`）；
3. 清单写着但快照目录没了 → `can_delta=False`（`SNAPSHOT_DIR_MISSING`）；
4. `delta_plan` 按可见范围过滤文档（别的范围的私有内容不混进来）；
5. **delta 成功后清单里其它范围条目逐字节保留**（回归"整表覆盖"）；
6. apply 抛异常 → 清单不变、旧快照仍可解析且内容还在、另一范围不受影响；
7. 首次全量就失败 → 清单里不会凭空出现这个范围；
8. delta 目标目录在 `scope_dir` 下（同范围同根）；
9. 无基线时**拒绝**而不是静默全量；
10. 显式 `allow_full_build` 时返回 `mode=FULL` + `fallback_reason`；
11. `keep_last` 生效（旧快照被清、当前指针与清单指向存在的目录）；
12. 同一范围连续两次增量：指针/清单/快照内容三者一致，另一范围全程没被牵连；
13. 构建"说成功"但快照目录不存在 → 报错且清单留在旧快照；
14. 清单坏了（非 JSON）→ 当没有，不猜它的内容。

### 变异复验（证明上面不是空转）

- M1：把合并写回改成 `write_manifest(root, {本范围: entry})` → **6 项 FAIL**（含第 5 项）；
- M2：把"快照目录必须存在"弱化成只判 `not base` → 第 3 项 **FAIL**。
两处均已还原并复跑全绿；相邻回归 `test_partition` + `test_rebuild_delta` +
`test_rebuild_policy_dispatch` + `test_scripts_compile` 共 **21 passed**。

## 没做 / 已知边界

- **跨范围合并检索**仍然没做：一个用户属于多个范围时怎么查，仍由调用方按范围分别查（沿用原边界）；
- **撤权 fence 代次**不归本函数管：`scope_delta_build` 内部用的是空 `FenceState`，
  撤权文件要靠调用方先撤权再重建（`rebuild_delta` 会剔除，但代次语义不在这一层）；
- **清单并发写**未加锁：两个进程同时重建不同范围会互相覆盖（last-writer-wins）。
  单进程编排（当前 drill / worker 用法）没问题，多实例并发需要外部租约——这是下一步要补的；
- **`keep_last=1` 与命名序**：上面提到的"同秒内目录名序≠时间序"是 `rebuild.py` 的既有约定，
  本次只在编排层做了"目录不存在就报错"的兜底，**没有改 `rebuild.py`**（不在本次文件边界内）；
- 没有把 `scope_delta_build` 接进 `v2_graph_worker.py` / 重建调度器（只交付可编排的函数 + 真实演练）；
- 不测检索质量（需要重排模型，波动大且与本能力无关）。
