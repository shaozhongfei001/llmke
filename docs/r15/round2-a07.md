# R15 第二轮 · A07 社区覆盖：判据判定（情形 A）

- 结论：**情形 A —— 判据错，不是产品缺口。**
  每条可见边都至少属于一个社区；`Σedge_count < 可见边数` 是**用错了度量方式**，
  不是"有 33 条边没被社区覆盖"。
- 未修改任何代码（本轮只允许改 `graph_community.py`，而本案不需要改）。
- 复算基线：`g_kb_9`，2026-10-29 22:50–22:56，图服务 19529 在线、ES 19200 在线。
- 复现方式：`load_graph("kb_9")` + `detect_communities(g, resolution=1.0,
  min_community_size=3, max_level=2, namespace="kb_9")`，与产品同函数同参数。

## 1. 三个数

| # | 量 | 值 | 取法 |
|---|---|---|---|
| 1 | 可见 relationship 边（`show_flag='1'`） | **94**（有向） | `MATCH (a:entity)-[e:relationship]->(b:entity)` 全量 94 条，`show_flag` 分布 `{'1': 94}`，无隐藏边 |
| 1b | 同一批边在**无向去重**后 | **69** | 18 组端点对存在重复写边，共折叠掉 25 条（94−69） |
| 2 | 社区数 / `Σedge_count` | **11 个**（level0=10、level1=1），`Σ=61` | ES `community_summary_kb_9` 11 条文档，`Σmetadata.edge_count` = 61；实时复算完全一致 |
| 3 | **跨社区边数**（两端分属不同 level0 社区） | **11** | 与 `69 − Σlevel0(58)` **精确相等** |
| 4 | **两端都不在任何社区的边** | **0** | 全图 69 条无向边逐条判定 |
| 5 | 至少一端在社区的边 | **69 / 69（100%）** | `intra(58) + cross(11) = 69 = 全量` |

各社区（实时复算 = ES 现存文档，逐项 `community_id`/成员/`edge_count` 全一致）：

| community_id | level | size | edge_count |
|---|---|---|---|
| L0-e249fcf7 | 0 | 19 | 18 |
| L0-1db44f22 | 0 | 9 | 12 |
| L0-0a5b6050 | 0 | 6 | 5 |
| L0-258925d1 | 0 | 6 | 5 |
| L0-659385b9 | 0 | 6 | 5 |
| L0-97ee05e5 | 0 | 4 | 3 |
| L0-11de0473 | 0 | 4 | 3 |
| L0-4a5dbb3a | 0 | 4 | 3 |
| L0-82838db2 | 0 | 3 | 2 |
| L0-328353e7 | 0 | 3 | 2 |
| L1-8fe3bd78 | 1 | 35 | 3 |

节点覆盖：`union(level0.members) == g.nodes()` → **True（64/64）**。
划分可复现：连跑两次 `detect_communities`，`(community_id, members, edge_count)` 三元组完全相同。

## 2. 缺口 33 条的完整分解账

A07 记录 `Σedge_count=60` vs 可见边 93（本轮实测 61 vs 94，多 1 条边，结构同形）。差额逐项对齐，无残项：

| 项 | 条数 | 性质 |
|---|---|---|
| 有向 → 无向折叠（同一端点对的重复写边） | **25** | 口径问题：`load_graph` 建的是 `nx.Graph`（无向），Nebula 里是 94 条有向边 |
| 跨社区边（两端分属不同社区，任何 `subgraph` 都不含它） | **11** | 数学必然：Louvain 划分的目标就是把跨度大的边切出去 |
| 合计 `94 − 58 = 36`；`Σ` 另含 level1 的 3 条超边 → `61` | | `Σ=61`，`94−61=33` |

即 **33 = 25（口径）+ 11（跨社区）− 3（level1 超边被一并求和）**，加总闭合。
`Σ(level0) = 58` 恰好等于"同一社区内部边"条数，说明 `edge_count` 的计算本身没有 bug。

## 3. 判据判断与理由

1. **"社区内边覆盖全图"在数学上不成立。** `edge_count := g.subgraph(members).number_of_edges()`
   只统计两端同属该社区的边；跨社区边按定义为 0 个社区的收入方。所以
   `Σedge_count ≥ 全图边数` 只有在"全图不划分"（1 个社区）时才成立。
   产品按 `min_community_size=3 / resolution=1.0` 正常切出了 10 个 level0 社区，
   必然产生跨社区边 —— 判据把"正常划分的必然结果"判成缺陷。
2. **`Σ` 还是混合量纲的求和。** level0 的 `edge_count` 是社区内实体边数；
   level1 的 `edge_count` 是**超节点图里的社区间边数**（`super_g.subgraph(part)`，
   本轮 3 条）。把两种含义不同的数相加再和"可见边数"比，本身没有物理意义。
3. **真正该验的性质已经 100% 成立**：每条可见边都至少属于一个社区；不存在
   "两端都无归属"的边。F08 的小簇并入策略之后，节点覆盖达到 64/64，边覆盖由此自动 100%。

因此判定：**情形 A，判据错**。按任务要求不改代码、不调 `min_community_size`、不造重叠社区。

## 4. 给 F12 的判据修正建议（不改 F12 文件，仅交文字）

把 N1 由"求和 ≥"改为"分类完备 + 零无归属"，并显式声明无向口径：

```python
# N1 反例：不存在两端都不在任何社区的可见边
# 口径：Nebula relationship 是有向边，社区检测在无向图上做（load_graph 用 nx.Graph）。
#       比较前必须先按 (min(id_a,id_b), max(id_a,id_b)) 无向去重，否则"有向条数 − 无向条数"
#       会被误读成未覆盖边。
vis_undirected = {(min(e["sid"], e["did"]), max(e["sid"], e["did"])) for e in vis}
undirected_total = len(vis_undirected)

# 1) 节点全覆盖：union(members) == 图节点集（覆盖的根，边覆盖由它推出）
# 2) 边分类完备：intra(两端同社区) + cross(两端不同社区) + orphan(两端都无归属) == undirected_total
# 3) 反例：orphan == 0（这才是"真缺口"），并登记 cross 条数（跨社区边只报数不判负）
checks.append(C.chk(
    "N1 反例：不存在两端都不在任何社区的可见边",
    orphan == 0,
    f"无向可见边={undirected_total}（有向 {len(vis)} 条去重而来），"
    f"社区内边={intra}，跨社区边={cross}，两端无归属={orphan}"))
```

配套两条口径说明（建议写进 `a07.py` docstring，避免下一轮再被读成"未覆盖 33 条"）：
- `edge_count` 是**社区内部边数**，跨社区边不属于任何 `subgraph`，故 `Σedge_count`
  天然小于总边数，**不能**用作覆盖判据。
- 若仍想保留"求和型"指标，只能同层级可比：`Σ(level0 edge_count) == intra`
  （本轮 58 == 58，成立即证明 `edge_count` 统计正确）。

补充提示（不改判据）：P2"每个社区都有成员与边"里的 `edge_count == 0` 对 level1 不适用
（level1 的 `edge_count` 是超边数，孤立超节点为 0 属正常）。

## 5. 为什么没有改 `graph_community.py`

情形 B 的两个必须条件都不成立：
- `g.nodes() == union(communities.members)` → 已成立（64/64），没有未归属端点；
- "每条边至少有一端在社区内" → 已成立（69/69），"两端都不在社区"的边 **0 条**。

即产品侧没有可修的缺口。按要求也不去调 `min_community_size` / 制造重叠社区来"凑绿"。
本轮 `graph_community.py` 的 md5 未变（见 §7）。

## 6. 遗留（不属于 A07，供其他 F 项参考）

1. **重复写边 25 条（18 组端点对）**——事实：全部属于 `file_id=343`、`generation=V1`
   （当前代次），组内既有方向相反的（如 `智造贷 -利率基准-> 1年期LPR` 与
   `1年期LPR -利率基准-> 智造贷`），也有同向不同谓词的（`利率指标` / `利率基准`）。
   推断：属抽取侧同一实体对重复产出，与 F02"写边不造反向边"的修复范围相关；
   **未验证**当前代码是否仍会新产（需重新解析一次才能证伪/证实，本轮只读不做）。
   若 F12 采纳"有向口径"的判据，这 25 条会伪装成新缺口，故必须在判据里先无向去重。
2. **`level1.edge_count` 语义不一致**：存的不是"社区内边数"而是"超节点间边数"，
   与 level0 同名不同义。任何跨层级 `Σ` 都无意义；如需统一，属 `graph_summary.py`
   范围（本轮禁止改）。
3. **可见边数漂移**：A07 记录 93，本轮实测 94（`Σedge_count` 60 → 61）。
   差值来自本轮新增 1 条 V1 边，不改变结论；F12 复跑时按当次实测值报数即可。

## 7. 复现命令与文件状态

```bash
cd /home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service
NACOS_SERVER_ADDRESS=127.0.0.1:18848 NAMESPACE= DATA_ID=index_graph_config_py \
GROUP=DEFAULT_GROUP PYTHONPATH=. \
  /home/szf/data/dev/llmke-r12/platform/r12/venvs/graph/bin/python /tmp/a07_probe.py
# probe2：有向重复边构成；probe3：ES↔实时对齐 + 复现性 + 分类完备
```

`graph_community.py` 未修改：`git diff HEAD` 为空，md5 = `e6b846a140492020bb6ed8803fccaaee`。
该文件已在 graph venv（`platform/r12/venvs/graph/bin/python`，3.10）下被上述探针实际 import 并调用
（`load_graph` / `detect_communities` 均成功执行），`ast.parse` 亦通过；本轮无代码变更故无回归面。
