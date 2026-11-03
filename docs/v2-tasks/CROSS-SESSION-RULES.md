# 跨会话单写者与提交纪律（2026-11-03 起立即生效）

当前共享工作树 `/home/szf/data/dev/llmke-v2` 同时有：后端 TL 会话（T-B1/T-A6/T-A7）、
前端会话（引用入口收口 / T-A5 高亮）。规则如下，违反即打回。

## 1. 提交边界

- **后端 TL**：只提交本批次文件（`index_graph_service/graph_types.py`、
  `tests/test_graph_direction_b01.py`、`docs/v2-tasks/**`、及本批次实际修改的后端文件）。
  禁止 `git add -A`、`git commit -am`；每次提交前 `git status --short` 自查。
- **前端会话**：把自己当前 4 个在途文件立即提交（或切独立分支）：
  - `frontend/plateform/src/components/AiInputer/common/services/apis.tsx`
  - `frontend/plateform/src/components/AiInputer/common/services/servers.ts`
  - `frontend/plateform/src/pages/HomePage/IntelligentChat/AIChat/components/DrawerPreview.tsx`
  - `frontend/plateform/src/pages/HomePage/IntelligentChat/AIChat/index.tsx`
  提交落地前，任何其他会话不得修改这 4 个文件。

## 2. 单写者

- 同一文件同一时间只有一个写者；要改对方在途文件，先等对方提交或明确交接。
- 评审会话只读，不写任何仓库文件。

## 3. 冲突处置

- 发现工作树里有不属于自己的未提交改动：**停下、回报，不代提交、不覆盖**。
- 需要合并时：先 `git status`/`git diff` 核对归属，再逐文件交接。

## 4. 前端会话完成与交接标准（满足后本会话接管前后端）

前端会话宣布“完成”前，必须同时满足：

1. 4 个在途文件（apis.tsx / servers.ts / DrawerPreview.tsx / AIChat/index.tsx）已 commit；
2. T-A5（问答 PDF 预览按 locator 高亮）完成并附证据（截图 + 文件:行号），或明确写“不在本批范围”；
3. 引用可点击入口收口结论（通过/未通过+断点）；
4. 图谱增强页改造若在其范围，交付或明确声明未做；
5. 写交接说明 `docs/v2-tasks/FRONTEND-HANDOFF.md`：完成项/未完成项/在途文件/验证方式；
6. `git status --short` 无该会话的未提交残留。

满足后由评审会话接管 llmke-v2 前后端整体优化（接管计划见评审方《LLMKE_接管计划_20261103.md》）。

## 5. 接管生效（2026-11-03 18:53，用户指令“本会话现在接管开工”；前端已于 78f70e0 提交，工作树干净，前端写域移交本会话）

- **本会话自即日起为后端写者**：可修改并提交后端文件与 `docs/v2-tasks/**`；推送/合并仍待用户确认。
- **前端会话停写**：请立即停止修改并尽快提交其在途 7 项（apis.tsx / servers.ts / GraphBox.tsx /
  DrawerPreview.tsx / AIChat/index.tsx / router/config/index.tsx / KnowledgeBaseZh/v2/）；
  在这些文件提交前，本会话不修改它们（等待交接，避免覆盖）。
- 前端提交后按 §4 补 `FRONTEND-HANDOFF.md`，本会话随后接手前端收尾（T-A5 等）。
