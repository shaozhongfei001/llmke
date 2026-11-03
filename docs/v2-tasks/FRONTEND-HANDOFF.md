# FRONTEND-HANDOFF.md —— 前端会话交接说明（2026-11-03）

> 依据 `docs/v2-tasks/CROSS-SESSION-RULES.md` §4/§5 编写。前端会话已于 78f70e0 提交全部在途文件并停写，
> 由评审会话（后端写者）接管前后端整体优化与前端收尾（T-A5 等）。

## 1. 完成项

| 项 | 内容 | 证据 |
|---|---|---|
| 引用可点击入口（P0） | 知识溯源按钮/抽屉已在 HEAD ee72f79 修好；本会话补齐**点条目打开原文**链路：raw.reference 反查 + file_id 回查 + locator 页码定位 + 可区分失败文案 | 代码 78f70e0；过程证据 `docs/v2-tasks/evidence/FE-CITATION-SKELETON-20261103.md` |
| 图谱增强骨架（第 4 节 IA 第一层） | `KnowledgeBaseZh/v2/`：五段状态机（lifecycle.ts）、可注入 mock 适配层（mockAdapter.ts）、路线徽标（RouteBadge）、顶栏五段状态条（LifecycleBar）、5-Tab 演示页（GraphLifecycleView）；GraphBox 顶部已挂 LifecycleBar；演示路由 `/graphLifecycleDemo` | 4 张截图 `docs/v2-tasks/evidence/screens/FE-20261103/fe-skeleton-*.png` |
| 验收 §9.5 | `npm run build` 通过（18:50 dist 已含全部改动）；tsc 无新增错误（存量报错清单见证据文档） | 同上 |

## 2. 未完成项（明确声明，不在本批范围或待外部条件）

1. **引用 E2E 最终版复测未跑**（断点：后端 8088/18083/19532/18094 在 18:15 左右被外部重启/下线，本会话非操作方）。
   已完成的实测：中间版点条目出现「file_id=空」→ 定位到 vendor 面板剥 metadata → 完成 raw.reference 反查修复；
   最终版预期文案为「该引用未携带可回查的文件标识（file_id=F012）」（F 类合成 id）或数字 id 直接打开原文。
   复测步骤见证据文档 §1.3（18088 已起 nginx 容器 `v2-fe-e2e` 挂载最新 dist；token 注入方式见 PAGE-CITATION-E2E-20261103.md）。
2. **T-A5（PDF 预览按 locator 高亮）不在本批范围**：已实现 locator `page=` 解析 → `initialPage` 定位到页；
   **chunk/单元格级文本高亮需要 position（坐标）数据，检索侧未下发**——属契约缺口，见证据文档第三节第 3 条。
3. **Tab2 实体 / Tab3 社区 / Tab5 构建与更新**只有骨架，真实接口等待后端契约（五段生命周期、社区报告、route trace 的库级接口均未接线，UI 已标"等待后端契约"并自动回落 mock）。
4. 数字 file_id 成功路径需数字 id 快照（当前 18094 为 s4-root-c 合成 F 类 id；`/tmp/v2-shim-root/snapshot-20261103151652` 是 file_id=333 的可开原文快照）+ 18095 preview 服务（当前未运行）。

## 3. 在途文件（本会话已全部提交，无残留）

提交 78f70e0 包含：`apis.tsx`、`servers.ts`、`GraphBox.tsx`、`DrawerPreview.tsx`、`AIChat/index.tsx`、
`router/config/index.tsx`、`KnowledgeBaseZh/v2/*`（5 个新文件）、证据文档与 4 张截图。
`git status --short` 当前仅剩后端会话在途文件（api.py / test_graph_api.py），非前端所有。

## 4. 验证方式（复测引用闭环的精确步骤）

1. 后端恢复后：`curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8088/` 应为 200。
2. 浏览器开 `http://127.0.0.1:18088/chats/main`（nginx 容器 `v2-fe-e2e` 已挂最新 dist；
   token 注入 `localStorage["gitech_ril:rag_ai"]={"userInfo":{"token":"…"}}`，admin token 可由
   `POST /auth/user/simpleLogin`（password 为 AES-128-CBC(key=iv=1234567890123456) Base64）获取）。
3. 选 R13 Global 助手 + 全局开关，问「星航贷单户最高授信额度是多少」→ 知识溯源 1 → 点条目：
   - F 类 id（当前快照）→ 预期「加载失败：该引用未携带可回查的文件标识（file_id=F012），无法定位原文」；
   - 数字 id（切 v2-shim 333 快照后）→ 预期抽屉打开 docx-table.docx（需 18095 preview 服务）并定位到 locator 页。
4. 骨架演示：`http://127.0.0.1:18088/graphLifecycleDemo`（不依赖后端守卫，可离线演示全部状态）。

## 5. 契约缺口清单（回给后端写者，不自行编造接口）

1. global 分支 reference 未补 convertedFilePath（AiServiceImpl.java ~396 行未走 addConvertedFilePath）——前端已 getById 回查兜底，建议后端补齐。
2. 合成 file_id（F001–F012）无 MySQL 记录，点不开原文；真实语料重建图后数字 id 可走通。
3. locator 仅 page/chunk，无 position 坐标 → chunk 高亮做不了。
4. 库级五段生命周期 / route trace / 社区报告的前端接口未接线（期望：生命周期 GET + 问答响应带 route/route_reason）。
5. vendor 引用面板只认顶层字段与 metadata.id；建议后端在 reference JSON 顶层平铺 file_id/title/locator 以绕开 vendor 剥字段。
