# 构建期可见集合隔离（2026-11-01）

## 与查询期过滤的区别（一句话）

- 查询期过滤（`retrieval_filter`）：内容**在**索引里，命中后被丢掉 —— "检索到但不给看"；
- 构建期隔离（本模块）：内容**压根不在**这份索引里 —— "检索都检索不到"。

后者才是隔离。前者只要过滤逻辑写错、或有人绕过 pipeline 直接查引擎，就会漏。

## 实现

`graph_engine_adapter/partition.py`（纯函数）：

- `doc_visibility(doc)`：取 `visibility` / `metadata.visibility`，缺省 `["public"]`
  （缺省必须是"最不惊讶"的那个：空集合会让未标注内容上线第一天就查不到）；
- `build_plan(docs, scopes)`：`public` 对所有范围可见，范围私有内容只进自己的；
- `scope_dir(root, scope)`：目录名 = 清洗后的名字 + sha256 前缀 —— 范围名来自外部，
  直接拼路径会被 `../` 穿越；
- `resolve(root, scope)`：读 `scopes.json` 清单，**查不到返回 None（fail-closed）**，
  绝不回退到"默认全量索引"——回退一次就等于隔离作废。

`scripts/v2_partition_drill.py`：按范围分别建索引 + 写清单 + 隔离探针。
`v2_graph_worker.py --scope <name>`：只把该范围可见的文档喂给引擎（`--root` 必须含 `{scope}`）。

## 真跑（10 块语料，其中 `五级分类口径` 只对 dept-b 可见）

```
dept-a: 5 documents / 9 chunks
dept-b: 6 documents / 10 chunks
exclusive_documents=1  shared_documents=5
探针「五级分类口径：正常：借款人能够履行合同」
  dept-a: hits=3, contains_target=false   ← 根本检索不到
  dept-b: hits=3, contains_target=true    ← 能检索到
problems=[]
```

同时检查了快照内容本身：dept-a 的 openie 落盘里**没有任何**超出它可见集合的文本。

## 测试

`tests/test_partition.py` 9 项：public 全局可见、私有只进自家、metadata 里的 visibility、
清单往返、快照被清理后解析为 None、未知范围不放大、路径穿越安全、
以及"worker 读文档时必须把 visibility 带下来"（丢了会让 `--scope` 把所有人当 public）。

## 代价（必须说清，不能只说好处）

- 每个范围一份索引 → 磁盘与构建时间随范围数线性增长；
- 跨范围共享的内容会被**重复抽取**，LLM 成本翻倍；
- 跨范围查询需要合并多份索引，本模块**不做**；
- 所以默认不开启：`scope=None` 时行为与单索引完全一致。

## 未做

- 跨范围合并检索（一个用户同时属于多个范围时怎么查）；
- 范围变更后的增量重建（当前是整份重建该范围的索引）；
- 索引层面的"文档级可见性变化"（同文档不同块不同范围）——当前按文档/块粒度，未做继承。
