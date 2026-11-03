# FE 会话证据：引用可点击闭环 + 图谱增强骨架（2026-11-03）

> 会话：前端实现（按 `graph-rag/LLMKE_图谱增强前端UI交接文件_20261103.md` 开工）。
> 基线 bb32876，工作树 HEAD ee72f79（含交接前 FE 提交），本会话未 commit、未动后端、未动 docs/r15/。

## 一、P0：引用可点击入口（知识溯源 → 点条目 → 打开原文）

### 1.1 根因链（全部有源码证据）

1. 后端 `reply.reference` 有数据：`question_re` global 分支 reference = 检索侧 documents_list
   （`AiServiceImpl.java:396`），条目含 `metadata.file_id/title/locator/sources/position`，但
   `source` 显式为 null（`retrieval_shim.py:_to_document` 注释：留给 Java
   `addConvertedFilePath` 补路径，而 global 分支没走该补全）。
2. vendor `@gientech/modual` 的引用面板把原始文档**重映射成展示条目时剥掉整个 metadata**
   （`index-D0DDewJ2.js` 内 `const{metadata:he,...He}=be`），只保留
   `file_id: metadata.id||uid`——我们的 file_id 在 `metadata.file_id` 而非 `metadata.id`，
   于是条目 `file_id` 恒为空、locator/sources 全丢。
3. 原宿主 `knowledge_referenceFile_title:click` 直接开预览抽屉 →
   `DrawerPreview` `meta.source` 为空 → 「加载失败：缺少原文地址或登录态」。
   （2026-11-03 上午已由评审会话实测复现，见 PAGE-CITATION-E2E-20261103.md。）

### 1.2 前端修复（全部在宿主层，不动 vendor、不动后端）

| 文件:行 | 改动 |
|---|---|
| `AIChat/index.tsx:441-444` | 新增 `references:click` 分支：把 vendor 事件 payload 里的 **raw.reference**（后端原始 JSON 串）存入 `lastReferenceRawRef` |
| `AIChat/index.tsx:446-507` | `knowledge_referenceFile_title:click`：条目点击时按 `file_name` 从 raw.reference 反查原始文档，把原始 `metadata`（file_id/locator/sources）补回条目对象 |
| `AIChat/index.tsx:137-186` | `resolveReferenceSource()`：多级候选提取 file_id（`metadata.file_id` → `metadata.sources[].file_id` → `position.sources[].file_id`，兼容 shim 对非数字 id 置 null 的行为）；数字 id 调 `GET /index/knowledgeBase/file/getById` 回查 `convertedFilePath` 填回 `metadata.source`；查不到写 `__citationOpenError`（可区分原因，不冒充"无权限"） |
| `AiInputer/common/services/apis.tsx:87` + `servers.ts:194-219` | 注册并实现 `api_getKbFileById`（运行时响应为 `{success,data}` 包裹，已按实测解包） |
| `AIChat/components/DrawerPreview.tsx:53-73,83,134` | 优先展示 `__citationOpenError`；解析 `locator`（`page=1;chunk=0`）→ `initialPage` 传给阅读器，打开原文定位到对应页 |

### 1.3 实测（浏览器 E2E，18088 = 新 dist + nginx，admin 登录态注入）

- global 问句「星航贷单户最高授信额度是多少」→ 答案 +「知识溯源 1」真实鼠标可点（沿用 HEAD 的
  自动滚动修复），抽屉条目显示真实文件名「集团客户授信方案.docx」。
- 点条目：**修复前**（旧代码）→ 「加载失败：缺少原文地址或登录态」；
  **修复后（中间版）** → 「加载失败：该引用未携带可回查的文件标识（file_id=空）」——
  由此定位 vendor 剥 metadata，再做 1.2 的 raw.reference 反查。
- 最终版（file_id=F012 非数字 → 预期文案「…file_id=F012…」）与数字 file_id 成功路径
  （快照 333 → `getById?id=333` 200 + convertedFilePath，`GET /index/knowledgeBase/file/getById?id=6`
  实测 `{success:true,data:{convertedFilePath:…}}`）：**后端服务在复测中被外部重启（8088/18083/
  19532/18094 全部下线，非本会话操作），最终版页面复测待后端恢复后补跑**。
- 现状：代码已就绪且类型检查通过（tsc 仅剩 HEAD 既有的 `index最新.tsx/index次新.tsx` 存量报错，
  与本次改动无关）；`npm run build` 通过（18:50 dist 已含全部改动，`grep` 命中新代码标记）。

## 二、图谱增强整页改造骨架（第 4 节 IA 的第一层）

新模块 `frontend/plateform/src/components/KnowledgeBaseZh/v2/`（均为前端骨架，可注入 mock，
真实接口等待后端契约）：

| 文件 | 内容 |
|---|---|
| `lifecycle.ts` | 五段状态机（READY/READY_EMPTY/PENDING/RUNNING/FAILED/INVALIDATED）、代次/发布版本、global READY/NOT_READY/PARTIAL、路线 RouteKind（GRAPH/COMMUNITY_REPORT/DENSE_FALLBACK）、状态机文案常量（与交接文件 §5 逐条对齐） |
| `mockAdapter.ts` | `GraphLifecycleAdapter` 数据契约 + `mockAdapter`（覆盖状态机全部取值）+ `httpAdapter`（抛"等待后端契约"，调用方自动回落 mock） |
| `RouteBadge.tsx` | 全站统一路线徽标：GRAPH（蓝）/社区报告（紫）/DENSE_FALLBACK+原因（黄）+ 禁用图对照样式 |
| `LifecycleBar.tsx` | 顶栏：KB 名｜代次/发布版本｜五段徽标（tooltip 带失败原因）｜可见域｜刷新/全量/增量重建｜构建中横幅（"新版本构建中，当前展示旧版本（代次 N）"）与图空横幅 |
| `GraphLifecycleView.tsx` | 5 Tab 骨架演示（库级图谱占位/实体/社区/全局问答/构建与更新），含 global NOT_READY/PARTIAL 禁用、BACKPRESSURE 倒计时+重试、引用校验未过折叠、权限拒绝统一话术 |

接线（低侵入，不影响现有文件列表）：

- `GraphBox.tsx:28,63`：图谱页顶部挂 `LifecycleBar`（后端未接线时自动回落 mock 并显示 mock 来源标记）。
- `router/config/index.tsx:469`：顶层演示入口 `/graphLifecycleDemo`（不依赖知识库守卫，
  后端离线也能演示）；`router/config/index.tsx:262`：预留正式入口 `knowledgeBase/graphLifecycle/:id`
  （HomePage 守卫在后端可用后生效）。

### 浏览器实测（/graphLifecycleDemo，后端离线状态下全部通过）

- 全部就绪 / 构建中（代次 8，构图·进行中+spin，横幅"新版本构建中，当前展示旧版本（代次 7）"）
  / 图空 READY_EMPTY / 失败+失效混合态（抽取·失败、构图·已失效、社区·已失效、发布·待处理），顶栏随组合切换；
- Tab4：GRAPH 徽标 + 类型化引用（file_id/locator 展示）；DENSE_FALLBACK 黄色徽标带原因 +
  "未通过引用校验（答案已折叠）"；global PARTIAL 时输入禁用 + 提示。
- 截图：`docs/v2-tasks/evidence/screens/FE-20261103/fe-skeleton-{building,dense-fallback,graph-route,mixed-states}.png`

## 三、契约缺口清单（回给评审会话，不自行编造接口）

1. **global 分支未补 convertedFilePath**：`AiServiceImpl.java` global reduce 分支（约 396 行）
   reference 直接取 `retrievedData.getDocumentString()`，未像普通路径走 `addConvertedFilePath`。
   前端已用 `getById` 回查兜底；建议后端在 global 分支补同样逻辑（与 R13-GRAPH-11/18 反查一致）。
2. **合成 file_id（F001–F012）在 MySQL 无记录**：当前 18094 快照（s4-root-c）的引用点不开原文
   （非数字 id 且无 KB 记录）。真实语料用数字 file_id 重建图后即可走通打开原文。
3. **locator 只有 page/chunk**：chunk 级文本/单元格高亮需要 position（段落/单元格/图片坐标）数据，
   检索侧未下发；当前实现定位到页，高亮待契约。
4. **五段生命周期/route trace/社区报告 的库级前端接口未接线**：骨架全部走 mock 适配层，
   已在 UI 上标注"等待后端契约"。期望契约：`GET 库级生命周期（generation/published_version/五段状态/
   global 状态）`、问答响应带 `route` 与 `route_reason` 字段。
5. **vendor 引用面板剥 metadata**：面板条目丢失 file_id/locator/sources，宿主靠 `references:click`
   的 raw.reference 反查兜底（脆）。建议后端在 reference JSON **顶层**平铺 `file_id/title/locator`
   （vendor 只认顶层/`metadata.id`），可绕开 vendor 限制。

## 四、验收对照（交接文件 §9）

1. ✅（骨架）五段状态条 + 库级视图骨架，mock 演示全部状态（截图）；真实库级图数据待后端契约。
2. ⏳ 画布有向边/光晕/孤点开关为占位说明；实体详情面板待真实数据。
3. ✅（骨架）社区/global 状态与徽标、回退演示（截图）；真实社区报告待契约。
4. ⏳ 构建 Tab 骨架就绪；撤权/版本回退真实接口待契约。
5. ✅ `npm run build` 通过（18:50）；截图 + 文件:行号见上。
6. ✅ 契约缺口清单见第三节。

## 五、本会话未完事项（下一步）

- 后端恢复后：跑 P0 引用最终版页面 E2E（失败分支 F012 文案 / 数字 file_id 成功路径需 18095
  preview 服务 + 数字 id 快照），补截图；
- 真实图谱页（knowledgeBase/:id）实测 LifecycleBar 挂载效果（守卫需要后端）；
- Tab2/Tab3/Tab5 真实接口对接（等契约）；画布自研方案沿用 GraphCanvas 的确认（交接文件 §10）。
