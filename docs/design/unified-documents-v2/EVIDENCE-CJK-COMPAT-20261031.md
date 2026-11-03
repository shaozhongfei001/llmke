# 图路径为什么没跑：上游把中文事实清空了（2026-10-31）

## 根因（一行代码）

`hipporag 2.0.0a4` 的 `utils/misc_utils.py:54`：

```python
def text_processing(text):
    return re.sub('[^A-Za-z0-9 ]', ' ', text.lower()).strip()
```

`index()` 对每个三元组调用它（`HippoRAG.py:252`）。**所有非 ASCII 字符被替换成空格**，于是：

```
("产品甲", "最高额度为", "8000万元")  →  ("", "", "8000")
("多指标对账口径", "是", "下表")      →  ("", "", "")
```

实测 `fact_embedding_store` 18 行：`('', '', '1800')`、`('', '', '')`、`('', '', 'aaa')`……
主谓全空。连锁反应正好解释了上一轮观察到的现象：

1. 重排器看到空壳事实 → 模型返回 `{}` → `facts_after_rerank=0`；
2. 引擎按设计回退稠密 → `graph_calls=0`；
3. 就算重排硬撑过去，图上实体也是空串，PPR 没有意义。

**所以上一轮把它归因为"本地 7B 模型不听话"是不准的**——模型是对的：空事实本来就不该保留。

## 补丁（显式偏离，默认不装）

`graph_engine_adapter/hipporag_compat.py`：

```python
re.sub('[^0-9A-Za-z\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff ]', ' ', text.lower())
```

只保留"汉字 + 字母数字"，中文标点仍清成空格（实体名混标点会让同一实体分裂）。
必须装到**两个**位置：`hipporag.utils.misc_utils.text_processing` 与
`hipporag.HippoRAG.text_processing`（后者是 `from ... import *` 的副本，
且 `import hipporag.HippoRAG as X` 拿到的是类不是模块，得走 `sys.modules`）。

默认不安装——否则"我们跑通了"会掩盖上游缺陷。`is_patched()` 返回 True/False/None（无 hipporag）。

## 打完补丁的真跑结果

```
{"cjk_compat":{"patched":["...misc_utils.text_processing","...HippoRAG.text_processing"],
               "effective":true},
 "routes":[{"q":"多指标对账口径是什么","planned":"GRAPH","executed":"GRAPH","passed":true},
           {"q":"授信额度是多少","planned":"DENSE_FALLBACK","executed":"GRAPH","passed":true}]}
```

- 查询 1：`graph_calls=1`，`seed_hits=['ent:多指标对账口径','ent:指标']`——PPR 真有起点；
- 查询 2：计划判 `DENSE_FALLBACK`（我们按实体名精确匹配认种子，没认出"授信额度"），
  但引擎内部走了图并 `executed_route=GRAPH`。**计划与执行不一致已经暴露出来**（`route_matches`），
  这说明我们的种子识别比引擎的事实匹配更弱，属于待改进点，不是通过项。

## 能力口径

`describe()` 拆成两条，不许混为一谈：

- `retrieve_graph_route`：**NOT_VERIFIED**（未打补丁的上游行为）；
- `retrieve_graph_route_with_cjk_patch`：**VERIFIED**，证据指本文。

产品路径要不要默认打补丁，得单独评估（这是对上游语义的偏离，需要跟引擎升级策略绑定）。

## 仍未做

- 事实质量：`("", "", "5000")` 消除后仍有 `("", "", "aaa")` 之类的抽取噪声（表头被当事实）；
- 回答组装：图检索出候选后怎么组织答案与引用，属于端到端，未做；
- 补丁对上游升级的兼容性：升级 hipporag 后必须重跑本验证，否则结论失效。
