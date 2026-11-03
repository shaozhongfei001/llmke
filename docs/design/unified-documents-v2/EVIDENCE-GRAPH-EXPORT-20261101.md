# 图导出（节点/边/事实）与导出差异（2026-11-01）

## 为什么自己写而不 pickle

- pickle 依赖 igraph 版本，换环境读不出来；
- 导出物要能进 `git diff` / 审计台账，必须是**稳定排序的纯文本**；
- 过滤（最小边权）与截断（大图）是导出策略，不该散在调用方。

刻意不做：Neo4j / GraphML 转换。当前没有消费方，写出来无人验证，等于造一个"看起来能用"的假接口。

## 实现

`graph_engine_adapter/export.py`

- `export_graph(graph, out_dir, min_weight, limit_nodes)` → `nodes.jsonl` / `edges.jsonl` / `meta.json`
  - 节点按 id 排序，边按 `(source, target, weight)` 排序 → 同输入两次 sha256 相同；
  - `limit_nodes` 按**度数**取样（按插入顺序截断会让结果跨版本不可比），
    被截断节点的边一并丢弃并如实报 `dropped_edges`，不留悬空边；
  - 写临时文件再 `os.replace`，读者不会看到写了一半的导出物。
- `export_facts(docs, path)` → `facts.jsonl`，按 `(chunk, s, p, o)` 排序。

`scripts/v2_graph_export.py` 增 `--compare <另一个快照>`，直接输出结构化差异。

## 真跑

```
--snapshot /tmp/dual-full --out /tmp/gx-a --compare /tmp/delta-drill/snapshot-...-g0
→ nodes=30, edges=109, facts=50
→ diff: nodes only_b=1, edges only_b=2, facts only_b=1
        ["董事会","审议通过","单笔授信"]
```

差异与 C2（`v2_dual_build_diff.py`）的抽取差异**完全一致**，两条独立路径互相印证。
与第二份全量快照（`dual-full2`）比较则 `identical=true`（三部分 0 差异），说明导出本身可复现。

## 自己踩的坑（静默残缺）

第一版读 `extracted_entities` 导出，得到 **2 条**事实却报成功——真实字段是
`extracted_triples`，而 `extracted_entities` 在同一份结果里**通常是空列表**。
全库实际 50 条。这种"跑通了但内容几乎为空"比报错危险，因为没人会去看条数。

已修：优先读 `extracted_triples`，`extracted_entities` 仅作老格式兜底；
单测加一条"`extracted_entities` 为空但 `extracted_triples` 有值"的回归。

## 能力声明更新

`describe()` 里三条从"未实现"改为"已实现"，都指向本仓可复跑的证据：

| 能力 | 变更 |
|---|---|
| `incremental_update` | NOT_IMPLEMENTED → VERIFIED（C2 证据） |
| `delete_document` | NOT_IMPLEMENTED → VERIFIED（文本差集删除，边界：同文本跨文档会合并） |
| `graph_export` | NOT_IMPLEMENTED → VERIFIED（本文档） |

剩下的真实缺口（未动）：`retrieve_graph_route`（NOT_VERIFIED）、
`engine_predicate_normalization` / `engine_version_filtering` / `engine_visibility_isolation`（NOT_IMPLEMENTED）。

## 还没做

- 大图截断的递归影响（截掉中心节点后子图连通性变化）未评估；
- 未做增量导出（每次全量重写，10 万节点级别的耗时未测）；
- 事实导出未去重（同一三元组来自多个块会出现多行，刻意保留来源）。
