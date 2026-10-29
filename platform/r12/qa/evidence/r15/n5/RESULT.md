# N5 gps 状态收敛：一次自我引入的误判 + 修复后验证（INTEGRATION）

> **证据等级 RECORD_ONLY**：这是排障过程记录，**不可独立复跑**（依赖当时的临时夹具/中间态）。不得用作文档所述能力的通过证据；对应的稳定判据见 `platform/r15/acceptance/` 中的断言。


- 时间：2026-10-29 21:05–21:15
- 结论：状态机本身是好的；**605/606 的"零产出失败"是我加的闸门读错字段造成的**

## 一、先说我引入的 bug

N3 加零产出闸门时，统计只加在 `batch_insert_vertex` 的返回里：

```
batch_insert_vertex → data{triples_total, edges_total, edges_failed, edges_written}
```

但 Java 实际调用的是上层 `generate_triple_data`，它最后**重新构造**了返回：

```python
return BaseResponse(code=200, msg='添加成功，新增和更新97条图数据…',
                    data={"error_edge_data_list": …, "error_tag_data_list": …, "type_report": …})
```

⇒ data 里没有统计字段 → Java 读到 0 → 判定"零产出" → gps=4（失败）。

日志铁证：

```
21:08:47 开始插入graph图数据，需保存97     ← Python 确实写了 97 条
20:53:57 图解析零产出，判失败：fileId=343 triples_total=0 edges_total=0 edges_written=0
```

**两条日志互相矛盾，说明是透传丢失，不是真的零产出。**

## 二、修复

`generate_triple_data` 的返回 data 透传统计字段（4 个）。重启图服务后重跑。

## 三、修复后验证（task 606 之后新任务）

```
t= 20s  task=4(成功)  gps=2(解析中)
t= 40s  task=4(成功)  gps=2(解析中)
t= 60s  task=4(成功)  gps=3(解析成功)   ← 收敛正确
```

文件侧：`file343_edges 38 → 55`（+17），全图 `total_edges=139`，`similar_edges=430`。

## 四、结论与遗留

```
✅ 任务状态与文件图谱状态能正确收敛（2 → 3），N5 通过
✅ 零产出闸门逻辑成立，但它的"失败反例"仍未用真实零产出构造（N8 待做）
⚠️ similar_edges 430 条 >> 业务边 139 条：辅助边不参与社区（load_graph 只查 relationship），
   但列表"关系数"若把 similar 算进去会虚高，属展示口径问题，已登记
```
