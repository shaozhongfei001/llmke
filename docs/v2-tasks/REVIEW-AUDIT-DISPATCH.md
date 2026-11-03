# 评审复核派发（TL 自证 + 评审方独立复核）

> 开工提示词（导读+任务+证据纪律）：同目录 `PROMPT-TL-AUDIT.md`。

日期：2026-11-03。评审会话只读，不碰仓库；TL 是唯一写者。
口径：TL 产“自证证据”（命令+输出+文件:行号+diff）；评审方独立逐行审 + 独立复跑 + 交叉核对。
**TL 的 VERIFIED 必须能被评审方在本机复现，否则打回。**

## T-A1 D7 打开原文自证（P0-1）

- 目标：`question_re` 的 global 分支（`AiServiceImpl.java:390-404`）补 file_id→convertedFilePath 反查
  （复用 publicQuestion `:728-759` 的 R13-GRAPH-11 逻辑），用**真实上传文档**（非 F001–F012/999010）
  跑通“点引用→打开原文→高亮 locator”。
- 自证材料（`docs/v2-tasks/evidence/A1-*.md`）：修改 diff；页面点击→抽屉→原文打开的实录（截图+日志）；
  文件在 KB 表有记录、file_id 匹配、locator 落点正确。
- 禁止：用演示语料、用“reference 有数据”代替“可打开”、只改前端不改 Java 反查。

## T-A2 D6 纯图 route 自证

- 目标：查询接 seed 实体（`query_seed_recognition` → `graph_search_with_fact_entities`），产出
  “无 rerank 兜底、GRAPH trace 命中”与“禁用图对照”两组证据。
- 自证材料：trace（graph_calls>0、facts_after_rerank、weights_assert_skipped 如实）；对照组输出；
  升级 `capabilities.retrieve_graph_route` 为 VERIFIED（附证据路径+sha256），或保持 NOT_VERIFIED 并写明缺项。
- 禁止：用 rerank 兜底后的命中当纯图证据；把 DENSE_FALLBACK 标成 GRAPH。

## T-A3 D4 社区同源自证

- 目标：证明 community.json 的输入 = HippoRAG 抽取事实（openie → normalize 断言 → export_facts →
  build_communities），不是平台自研抽取、不是 HippoRAG 内部相似图。
- 自证材料：一条事实从 openie 到 community.json 的逐跳溯源（脚本+输出）；孤点保留与引用校验 0 失效；
  两次生成的 community.json sha256 相同。
- 禁止：只贴文档不贴命令；用 legacy 图服务数据冒充。

## T-A4 B01 自证与迁移方案

- 目标：r12 工作树复跑 28 tests + 变异 3 组复演 + 基线 20 failed 复演；给出 0bac08a 合入 V2 的迁移方案
  （存量 g_kb_9 清库重写的范围、顺序、回滚）。
- 自证材料：三条命令的原样输出；迁移方案文档。不改 docs/r15/，不动运行中服务。

## 评审方（本会话）并行清单

- R1 逐行审 D7 全链（Java 两分支 + shim documents_list + 前端 drawer 数据流）。
- R2 逐行审 D6（api.query → seed → engine_hipporag.retrieve → route/trace）。
- R3 逐行审 D4（build → openie → normalize → export → community → report）。
- R4 独立复跑 B01（已做：28 passed in 0.03s，r12 工作树）+ 逐行审 patch + 变异复演。
- 交叉核对标准：TL 证据中的每条命令，评审方在本机复跑，输出一致才算通过。
