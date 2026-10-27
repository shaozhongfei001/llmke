# FIX-34 并发剪枝会静默丢数据 → FIX-35（按 source 串行化）

采集：2026-10-27 14:45–14:52；环境：19527 fulltext_es_api（单进程），scratch 索引 `r14a_conc_probe`（用后已删）。

## 1 现象：并发同源写入后，块数变成 0，接口仍返回 200

同 source 并发 3 次（同一内容），连跑三轮：

```
第1轮 同源并发3次 -> http=[200,200,200]  索引总数=5  same_src=1
第2轮 同源并发3次 -> http=[200,200,200]  索引总数=4  same_src=0   ← 丢掉
第3轮 同源并发3次 -> http=[200,200,200]  索引总数=4  same_src=0   ← 丢掉
```
每次响应都是 `{"code":200,"msg":"r14a_conc_probe保存数据成功，共保存1条数据"}`。

服务日志（`platform/r12/logs/index_fulltext_service.log`）同一时刻：
```
14:48:48.811 ERROR controller.es:delete_by_col_documents_async:322 - 删除失败 ConflictError(409, ...)
14:48:48.842 INFO  controller.es:add_documents_async:514 - 写后按 source 剪枝 2 条
14:48:48.842 WARNING add_documents_async:517 - 剪枝失败（不影响本次写入）: ConflictError(409, ...)
14:48:50.934 INFO  写后按 source 剪枝 2 条
14:48:50.949 INFO  写后按 source 剪枝 1 条
```

## 2 机制：剪枝是"最后完成者胜"，但无法保证"胜者的行还在"

`controller/es.py` FIX-34 的写后剪枝：
```
delete_by_query( filter: metadata.source.keyword in source_paths,
                 must_not: ids = keep_ids(本批 _id) )
```
A/B/C 三个并发请求各自执行"删掉同 source 里不属于自己的行"。交错时序下：

1. A 插入 -> A 剪掉 B、C（此时 B、C 可能已插入）
2. B、C 的插入被剪掉后，B/C 自己的剪枝仍继续，把 A 也剪掉
3. 最后剩下 0 条，而三个请求都已返回 200

写前 `delete_by_col_documents_async` 在并发下还会抛 `ConflictError(409)`（被 catch 后只记 error 日志），
这使"删-写-剪"三段更容易交错。

## 3 修法 FIX-35：进程内按 source 串行

`add_documents_async` 变成薄包装：按 `document_list[*].metadata.source` 去重排序，
逐把 `asyncio.Lock` 获取后调用实现体 `_add_documents_async_impl`，finally 逆序释放。
（本服务单进程，进程内锁即可；跨进程再重时依赖 ES 版本冲突重试。）

## 4 验证（重启后 19527 pid=1823402 @14:49:45）

```
同源并发 R1 http=[200,200,200] -> total/same = (5,1)
同源并发 R2 http=[200,200,200] -> total/same = (5,1)
同源并发 R3 http=[200,200,200] -> total/same = (5,1)      ← 三轮都稳定 1 条，无丢无重
异源并发     http=[200,200,200] -> diffF=3                ← 未误删他人
```

## 5 判据（可复用）

```
正向：同 source 并发 N 次 -> 1 条
反向：不同 source 并发 N 次 -> N 条（不能"收敛"成误删）
重复：以上两轮各跑 3 次，任一轮结果偏离即判失败
```
只跑一次会误判：本次"同源并发"第 1 轮是对的（1 条），第 2/3 轮才是 0 条。
**"跑一遍通过"在并发缺陷上等于没验。**

## 6 影响面

- 该缺陷只在**并发写同一 source** 时触发；串行解析不受影响（所以静置数据普查查不出重复、也查不出丢失）。
- 对 B 的重建：重抽若并发处理同一文件的多个块批次，可能整文件块消失且接口返回成功 →
  post 快照只验"顶点/边代次"看不出来，必须同时比对 ES chunk 数。
