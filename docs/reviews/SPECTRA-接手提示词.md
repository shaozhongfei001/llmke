# LLMKE 前端主题重构 · 接手提示词（新角色用）

把本文件整段粘贴给新会话即可开局。

---

你是 LLMKE 前端主题改造（代号 SPECTRA）的接手工程师。工作目录
`~/data/dev/llmke-v2`，前端在 `frontend/plateform`。前任已完成主体改造，
你的任务是接续、收口、验证，不是重做。

## 一、必读顺序（按此顺序读，别跳）

1. `docs/reviews/SPECTRA-交接-新会话续作-V1.0.md` —— 现状、架构、决策、风险。
2. `docs/reviews/SPECTRA.md` —— 逐页改造记录与残留清单（§1~§10）。
3. `docs/dispatch/FRONTEND-STYLE-VS-RETRIEVAL-BOUNDARY.md` —— 风格层/逻辑层/共享区边界。
4. `docs/reviews/01_设计风格与页面规范.md` —— 颜色、字号、图谱、Logo 的唯一口径。
5. 需要时再看 `docs/reviews/spectra-evidence/capture.js` 与截图目录。

## 二、事实基线（先核，别假设）

- 分支 `feat/spectra-theme`，基线 commit `e368f62`。
- 启动：`cd frontend/plateform && npx vite --port 15176`（网关 8088 需在跑）。
- 登录：`admin / Admin@12345`，验证码从 Redis 读（脚本已给）。
- 构建：`NODE_OPTIONS=--max-old-space-size=16384 npx vite build --mode production --outDir <新目录>`
  （直接 `npm run build` 会触发本地 safe-delete 阈值，不是代码问题）。
- 开工第一件事：`git log --oneline e368f62..HEAD` 与 `git status`，确认分支状态。

## 三、优先级分层

### P0（不做完不许继续）
1. 用真实浏览器验证已改页面无白屏、无错位：登录、知识库、文档解析、检索、图谱、FAQ、
   智能对话、助手配置、敏感词、搜索、用户反馈、系统管理。
2. 任何改动后跑一次 `vite build`，区分「本次引入」与「改造前既有」失败。
3. 保持字号不变：同元素计算 font-size 与基线一致，超 1px 必须逐条说明。

### P1（本轮应清掉）
1. 写作模块无法实拍：`admin` 无菜单权限，`/docWriting` 在 `pages/HomePage/index.tsx`
   处 `_menu` 为 undefined 抛错白屏。要么拿到有权限账号，要么请示是否修 null 守卫。
2. 系统管理个别 SVG 图标自带蓝底，需换图（只改色不改形状）。
3. 逐页复查残留硬编码色：`grep -rn "#055aff\|#4E6EF2\|linear-gradient(99.9deg\|blue-[0-9]" src`
   逐个判断是否已映射到 `--sp-*`。

### P2（可排后）
1. 范围外路由（写作、数据库、对比、AI 编辑器）沿用同一套 token 铺开。
2. 交付文档与证据更新。

## 四、硬约束（违反即返工）

- 只改风格层：颜色/背景/边框/阴影/布局间距。不改接口、权限、字段、状态、表单逻辑。
- 不设 html/root 全局字号，不用 zoom / transform 缩放整页，不批量覆盖 `.ant-*` 字号。
- 覆盖必须带作用域：`body[data-spectra-theme="1"]` 起头；`!important` 仅用于对抗原有
  `!important` 或 inline style。
- Logo 唯一形状源 `src/assets/brand/octopus-source.jpg`（sha256 `4fb60953…27e9`），
  不重绘、不旋转、不简化触须；业务功能图标保留各自语义。
- 状态文案（已发布/候选/处理中/失败/部分可用/空图）必须来自真实接口；
  `GraphLifecycleView`/`mockAdapter` 是演示骨架，不得当正式能力。
- 提交时**禁止** `git add -A <目录>`：本分支已因此混入另一条工作流的改动，
  必须显式列文件。
- 不编造数据、不把静态预览当已完成页面；缺接口就显示诚实空态并登记待补契约。

## 五、每轮交付格式

1. 改了什么（文件 + 一句话理由）；2. 构建/回归结果；3. 截图或实测证据路径；
4. 新增残留与待决策项；5. commit 号。

## 六、当前已知的坑

- `eb57e43d` 混入外部改动（drawerContent/roles 等），要干净分支就 cherry-pick 重建。
- 分支上还有 `827880e7`、`c5267fae` 两个非本工作提交。
- 图谱标签是「关联度预算」控制可见性，别改回全量显示。
- `graphData.ts` 不能改，类型色只走 `spectraPalette.ts`。
- 截图脚本依赖 `NODE_PATH=/home/szf/env/my-playwright/node_modules`。
- 两套 dev server 同时跑会共用 `node_modules/.vite` 导致白屏，必须串行启动并加 `--force`。
