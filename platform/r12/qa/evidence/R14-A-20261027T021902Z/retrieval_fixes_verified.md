# 检索层三条缺陷修复复验（C 重启 19995 后）

采集：2026-10-27T11:49:30+08:00；19995 单实例 pid 641826（11:47:21 启动）> multiple_retrieval.py mtime 11:43:01 / retrieval_service.py mtime 11:46:36

## 1) FAQ 直答：`faq_result_list` 0 -> 1
```
POST 19995/retrieval_documents query=客户访前准备是否是文档的主要内容？ enabled_faq=true enabled_graph=false enabled_rerank=false
-> code 200 | faq_result_list = 1 | 首条 = 客户访前准备是否是文档的主要内容？
（修复前同命令：faq_result_list = 0）
```

## 2) 大写查询 + 开图：HTTP 500 -> 200
```
信用评级为AAA的公司执行利率需要加多少个基点  enabled_graph=true rerank=false -> 200
PRD-CORP-LOAN-2026-01 的最高额度              + search_policy=2 / 3 / enable_web_search=false / adjacent_chunk_num=2 -> 全 200
大写 + 开图 + rerank=true（B 的 /qa 组合）      -> 200（小写对照同样 200）
（修复前：AAA 大写开图 = 500，KeyError documents[query]）
```

## 3) 多 KB（kb_5 无图空间 + kb_9）：图结果不再被静默丢弃
```
query=智造贷单户最高授信额度是多少  knowledge_base_name=[kb_5,kb_9] enabled_graph=true
-> code 200 | documents_list 4 | 其中 search_type 含 graph 的 3 条
（修复前：kb_5 space_not_found 触发 except->return，kb_9 图检索根本没被请求）
```

## 实例数
- 19995 现为**单实例**（641826），此前的 360263/365443 双实例已消除；
- 19996 仍有两个（103860 @10:17 / 94269 @10:15），属 llm-infer，未收口。

## 未覆盖分支（如实标注）
- `multi_version` 分支（`retrieval_service.py:250/266` 的 `documents[query]`）需要多版本夹具（MySQL version 字段）才能触发；C 用的是 `setdefault(query, [])` 方案（只堵 `:478` 一处），故该分支未验证，属"未知"而非"已修复"。
