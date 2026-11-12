# 隔离验证：生产语料 FULL_REBUILD（2026-11-12）

## 目的

在隔离环境验证「以生产规模语料在统一图根上跑 FULL_REBUILD 不削数据」，
为生产 `kb_9`（11 文件 / 46 块）切换窗口提供可直接复用的证据。
前一轮（STEP2-C）发现「切到生产 root 后直接 UPSERT 会按影子 manifest 把图削成
3 个文件」是一个**未经实测的风险假设**；本轮用实测修正它。

## 方法（零生产风险）

- 独立 kb `kb_e2e_fullscale_20261112`，与 `kb_9` 完全隔离。
- 独立 18096 实例（端口 18099）：独立 `artifact-store`、进程环境**不设**
  `LLMKE_V2_GRAPH_ROOT`（从而落盘到 18094 自己的 `.artifacts/api-root`，并重置
  本 kb 查询槽），`LLMKE_V2_GRAPH_API` 指向现有 18094。
- 语料：本机可复用的**标准 doc2md 四件套**（含 `document_ir.json`、无非预期顶层文件）
  只有 2 份 —— `a846ab…`（4 项）、`f49820…`（4 项）。`c5edbe…` 缺 `document_ir.json`
  （旧 3 项格式）、`shadow-backup/artifact-store` 下的 4 份含多余 `artifact.json`
  顶层文件，均被 18096 拒绝，不能作语料。
- 故本演练以 **2 文件规模**验证机制（与生产 11 文件规模机制相同，仅数量差异）。

## 五步实测

| 步 | 操作 | 结果 |
|---|---|---|
| ① | `FULL_REBUILD` 文件1（fid 990101） | `code=200, eff_mode=FULL, documents=3, per_file=[990101]` |
| ② | `UPSERT` 文件2（fid 990102） | `code=200, eff_mode=DELTA, documents=6, reason=FILE_SET_CHANGED` |
| ③ | 查询 `kb_e2e_fullscale_20261112` | `hit_count=6, route=GRAPH, 命中来源=[990101,990102]`（两份都可读） |
| ④ | **再**对文件1 发 `FULL_REBUILD`（模拟生产误用连续 FULL） | `code=200, eff_mode=FULL, documents=6, per_file=[990101,990102]`（**未削**） |
| ⑤ | 指针复核 | `documents=6`，`per_file=[990101,990102]`，与原 2 文件一致 |

## 修正性结论

1. **`FULL_REBUILD` 不是「清空重建单文件」，而是「重建整个 kb（保留所有已注册 file_id）」**。
   首次对空 kb 发 FULL 只 build 传入文件（3 块），是因为彼时 kb 只有该文件；
   当 kb 已含 2 文件时再发 FULL，**结果仍是 6 块 / 2 文件，不削任何数据**。
2. **`UPSERT/DELTA` 是累积语义**：② 在 ① 基础上 +3 块得到 6 块，旧文件完整保留。
3. 因此前一轮「切到生产 root 会按影子 manifest 把图削成 3 文件」是**未实测假设**，
   本轮实测否定了其中「FULL 会削」的子集。剩余真实约束见下。

## 仍成立的生产切换前置（与 STEP2-C 一致，风险比预期小）

1. **18096 图根由进程环境变量 `LLMKE_V2_GRAPH_ROOT` 决定**（当前 = `shadow/graph-root`）；
   切换 = 改该 env 为生产 root 并重启 18096，请求体 `graph_root` 对生产路径无效。
2. **切换窗口内先停 19531 build**（通道互斥，不得并发写同一 root）。
3. **旧软链指针**：生产 `kb_9/current.json` 的 `dir` 仍指向已删除的 `llmke-r12/…`，
   切换后首写需修正（FULL/DELTA 重建会自动刷新指针，但旧路径引用应清理）。
4. **四件套格式门槛**（本课新发现）：生产 `kb_9` 的 11 份四件套切换前须确认是**标准
   doc2md 四件套**（含 `document_ir.json` 且无非预期顶层文件），否则 18096 会
   `MISSING_PART` / `UNKNOWN_TOP_LEVEL_FILE` 拒绝。

## 清理

隔离 18099 实例已停；`/tmp/v2-fullscale` store、`.artifacts/api-root/kb_e2e_fullscale_20261112`
落盘已删；ES/Milvus 精确删除调用均返回「不存在/无需删除」（隔离 build 未写入远端
向量库）；`platform/r12/data` 临时状态已清。生产 `kb_9` 前后一致
（app 根 46 块 / 11 文件、影子根 4 块 / 3 文件），8 个服务端口保持 LISTEN。

## 待办

- 本证据**未提交**，待「提交一次 git」指令一并入库。
- 生产 11 文件真实规模演练需在能拿到 11 份标准四件套的环境进行（本机仅 2 份可用）。
