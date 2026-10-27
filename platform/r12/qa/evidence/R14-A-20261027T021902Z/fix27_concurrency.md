# R14-A-FIX-27：并发创建同名索引被当失败（已修 + 反证）

## 缺陷
多篇文件**并发首次入库同一个新库**时，谁先建索引谁赢，其余请求收到
`resource_already_exists_exception`（索引已存在）。这是预期内的并发状态，但原实现把它当异常：

```
get_index_mapping_field_async()
  if not exists: create_index_async()  -> 500 时 raise ValueError
  -> add_documents_async 捕获后 return 500 "创建索引失败"
  -> 解析侧整批零写入；/parse_sync 仍 success=true
```
B 的 `kb_22` 三篇并发即命中：上传 3 篇、只生效 1 篇、界面看不出来。

## 修法（两处，缺一不可）
1. **`resource_already_exists` 视为成功**：命中即 `logger.warning` 后继续取 mapping。
   注意 `create_index_async` 有**两条**"已存在"路径——ES 抛的英文异常，以及它自己的
   `else: return BaseResponse(code=500, msg=f'索引{index_name}已存在')`。**只匹配英文 = 半个修复**。
2. **mapping 刷新延迟**：`create` 成功后立刻 `get_mapping` 仍可能 404（ES 建索引非同步可见），
   加 3 次退避重试（0.5 / 1.0 / 1.5s），取不到才判失败。
   —— 否则竞态修好后症状会从 400 变成 404，看起来像换了个 bug，其实是同一处的两个面。

## 验证（19527 pid=1444778，启动 13:50:48 > es.py mtime 13:47:31）

### ① 修复后：三路并发，两个全新库各一轮
```
轮1 r12a_race_80284  3 路 -> http 200 / body code=200 / "保存数据成功，共保存1条数据"
    count=3   mapping 顶层=['metadata','page_content','question']，metadata 子字段 38 个
轮2 r12a_race_80289b  3 路 -> 全部 200 / code=200；count=3
```

### ② 反证：用**旧逻辑**（exists -> create，无冲突处理）真跑
```
第0 路 created 200
第1 路 400 resource_already_exists_exception
第2 路 400 resource_already_exists_exception
=> 失败 2/3
```
这条是"同一条件下的对照"，不是"现在能过所以改动有效"。

### ③ 边界
```
本轮只写 scratch 索引（r12a_race_*），kb_9 未写入（仍 9 条，create_time 13:25:49–13:26:53）
scratch 已全部删除，无残留
```

## 教训（写进检查点建议）
1. **同一语义可能有两个来源**（英文异常 + 中文分支），只认一个就是半个修复；
2. **"重启过" ≠ "改动生效"**：要比"该改动那一次写入的时刻 < 进程启动时刻"，
   不能用文件最新 mtime（会被后续编辑推后，本次就误判过一次）；
3. **unit 级重启 ≠ 单服务重启**：`systemctl restart r12-alg.service` 会同时重启 19526/19527/19995/19996；
   单服务须用 `algctl.sh restart <svc>` 或 `systemctl --user restart r12-docparse.service`。
   本次误用 unit 级重启是一次误操作，已全队更正并附四个 pid/启动时刻。
