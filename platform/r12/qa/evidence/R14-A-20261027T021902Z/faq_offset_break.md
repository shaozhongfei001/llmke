# FAQ 直答失效：retrieval_milvus 的 offset 解析用 break 掐断整批召回

采集：2026-10-27T11:38:19+08:00（F-qa 定位现象，A 复核到代码行并补写入侧规范化）

## 1) 现象（复现）
```
POST 19995/retrieval_documents  query=客户访前准备是否是文档的主要内容？
     enabled_faq=true enabled_graph=false enabled_rerank=false top_k=10
-> code 200 | faq_result_list=0 | documents_list=1
ES faq_kb_9 命中: _id 77215328111367569  score 8.84  offset=None
     page_content: 客户访前准备是否是文档的主要内容？@@不是，客户访前准备是文档的一部分内容，但不是主要部分。
```

## 2) 代码级根因（services/rag-alg/alg_retrieval_service/app/multiple_retrieval.py）
```
209        # 尝试解析 offset
210        try:
211            if "offset" in x['metadata']:
212                x['metadata']['offset'] = json.loads(x['metadata']['offset'])
213        except Exception as e:
214            logger.error(f"解析 offset 失败: {e}, 数据: {x}")
215            break                      # ← 一个坏行丢掉整批命中
```
FAQ 行在 Milvus 中 offset 为空串 → json.loads("") 抛 Expecting value: line 1 column 1 (char 0) → break。

## 3) 影响面（比 FAQ 更大）
- retrieval_milvus 同时服务普通向量召回：任意一行 offset 非法 → 整批 dense 结果被截断；
- 同文件检索_graph 分支（:459）是 log-and-continue（正确行为），Milvus 分支是唯一用 break 的 outlier。

## 4) 我这侧的处置（写入层，防止新数据再产生空串）
- index_vector_service/milvus_kb_service.py：offset/position/page_size 统一规范化为合法 JSON 字符串（缺失→"[]"）；
- 实测：插入无 offset 文档 → Milvus 实际存 offset='[]' position='[]' page_size='[]'，json.loads 三字段均 ok；
- 19526 已重启（pid 587603）。**存量 faq_kb_9 20 条仍为 ""，读侧 continue 修复仍必须做（C）。**
