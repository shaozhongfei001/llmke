# SPECTRA 前端主题重构 · 交接说明（新会话续作用）

生成时间 2026-11-06。基线 commit `e368f62`，分支 `feat/spectra-theme`。

## 1 现状

- 分支 `feat/spectra-theme`，构建通过：`vite build` 15825 模块 / 0 error。
- 主题已落地页面：登录、知识库工作台、文档解析、检索与原文核验、知识图谱、FAQ、
  智能对话、助手配置、敏感词配置、搜索、用户反馈、系统管理（部门/角色/模型）。
- 交付文档 `docs/reviews/SPECTRA.md`（§1~§10，含决策与残留）。
- 证据 `docs/reviews/spectra-evidence/`：`before/`、`after/`、`after-menu/`、`after-system/`。

## 2 主题架构（4 个入口，改颜色只动这里）

| 文件 | 职责 |
|---|---|
| `src/styles/spectra.tokens.css` | `--sp-*` 颜色/表面 token，作用域 `body[data-spectra-theme="1"]` |
| `src/styles/spectraTheme.ts` | AntD ThemeConfig 工厂，在 `antTheme` 之上合并，不写字号 |
| `src/styles/spectra-pages.less` | 页面级作用域覆盖（外壳/登录/知识库/详情/检索/FAQ/聊天/表格/原子类） |
| `src/App.tsx` | `ConfigProvider theme={makeSpectraTheme(antTheme)}` + 挂载作用域属性 |

约定：所有覆盖以 `body[data-spectra-theme="1"]` 起头；只改颜色/背景/边框/阴影，
不写 font-size / line-height / font-weight；!important 仅用于对抗原有 !important 或 inline。

## 3 关键决策（新会话不要推翻）

1. `v2/graphData.ts` 属逻辑层，**未改**；类型色走 `v2/spectraPalette.ts`，未命中类型用与
   graphData 相同的稳定哈希兜底，保证刷新不变色。
2. `graphData.ts` 的 `typeColor` 仍被 import 作为兜底入参，别删这个 import。
3. 图谱标签按「关联度预算」显示（scale≥1.15 全量 / ≥0.75 取 40 / 否则 16），
   选中与一跳邻域始终可见；不要改成全局放大 SVG text。
4. tailwind 原子类（`.bg-white` / `.bg-gray-50` / `.bg-blue-50` / `.border-gray-300` /
   `.text-gray-*`）在主题作用域内统一重映射——这是修各列表页残留白底的主手段。
5. 智能对话换肤的主开关是 `AIChat/config/index.tsx` 的 `theme.colors`（22 项），
   不要再去逐个改 vendor 组件。
6. `@mxmweb/zui` 的 `--color-primary` 在 `body[data-spectra-theme="1"]` 上覆盖为暖金。
7. 蓝色渐变主按钮（`linear-gradient(99.9deg,#2b69ff,#8f91ff)`）已批量替换为 `#D8BD89`，
   替换时注意「三元表达式里的裸字符串」写法，正则容易漏。

## 4 已知残留（按优先级）

1. **写作模块未实拍验证**：`admin` 无写作菜单权限，`/docWriting` 在
   `pages/HomePage/index.tsx` 里 `_menu` 为 undefined 抛
   `Cannot destructure property 'routes' of '_menu'`，整页白屏（改造前既有）。
   要验证需有菜单权限的账号，或修这处 null 守卫（属逻辑层，需你决定）。
2. 原生 `title` 提示为浏览器白色气泡，CSS 不可主题化，非页面残留。
3. 系统管理个别小图标（SVG 资源自带蓝底）仍需换图。
4. 首批范围外路由未做：写作、数据库、对比、AI 编辑器等。

## 5 新会话开工步骤

```bash
cd ~/data/dev/llmke-v2/frontend/plateform
npx vite --port 15176            # 网关 8088 需在跑
```

登录：账号 `admin` / `Admin@12345`。图形验证码从 Redis 读取（Kryo 首字节跳过、
每字节取低 7 位），脚本见 `docs/reviews/spectra-evidence/capture.js`：

```bash
NODE_PATH=/home/szf/env/my-playwright/node_modules \
  node capture.js http://127.0.0.1:15176 <outDir>
```

改前改后对比必须同构采集；字号口径「同元素计算值原则上不变，超 1px 逐条解释」。

## 6 重要风险：分支混入了外部提交

`git log e368f62..HEAD` 中有两个**不属于本次工作**的提交：
`827880e7 fix(operation-log)`、`c5267fae fix(r12-runtime)`。

另外 `eb57e43d` 用 `git add -A frontend/plateform/src` 提交时，把另一条工作流对
`system/organization/{departments/components/drawerContent.tsx, roles/index.tsx,
roles/PermissionForm.tsx, roles/RoleList.tsx, groups/...}` 的大量改动一并带了进来
（多为整体重排/换行差异）。**后续不要再使用 `git add -A <dir>`**，改为显式列文件。

若需要干净主题分支，建议用 cherry-pick 重建：
`git checkout -b feat/spectra-theme-clean e368f62` 后逐个 cherry-pick 下列提交，
并在冲突文件上只保留颜色相关 hunk。

## 7 本次 SPECTRA 提交（可 cherry-pick）

| commit | 内容 |
|---|---|
| `43be1224` | 主题地基 + 六页首轮（登录/知识库/文档/检索/图谱/FAQ） |
| `a10c22a7` | 交付说明 SPECTRA.md |
| `d568340d` | before/after 截图与采集脚本 |
| `153d97e9` | 扩展五个菜单页（智能对话/助手配置/敏感词/搜索/反馈） |
| `eb57e43d` | 系统管理 + 写作 + 检索气泡换肤（**含外部改动，见 §6**） |
| `d04c5274` | 文档 §10 |
| `838d698b` | 共享展示组件暖金化 + 角色列表选中态 |
| `33ecc238` | 文档补充 |

## 8 接手轮收口状态（2026-11-06）

- §4 残留 1（写作模块无法实拍）：**CLOSED（路径 B）**。Owner 2026-11-07 批准 `2f35b613` 的 `_menu` null 守卫并接受权限行为变更；白屏崩溃消除，四页已实拍（`after-writing/`）。admin 无权限时 main/template 因接口 401 重定向登录页、resource/indicator 停留原页，完整写作功能页仍需有权限账号（路径 A）。详见 `SPECTRA.md` §11.6。
- §4 残留 2（浏览器原生 `title` 白气泡）：仍存在，属 UA 样式，CSS 不可主题化，非页面残留。
- §4 残留 3（SVG 自带蓝底）：**CLOSED**，提交 `5711a7ea`。实测把定位范围从系统管理扩展到全局 6 个蓝 SVG（导航 3px 条、搜索标题/星形/放大镜、侧栏选中态图标），每个新文件与原文件除颜色 token 外逐字节一致。
- §4 残留 4（范围外路由）：仍 OPEN，归 P2。
- **新增发现**：`/system/models` 整页浅色（第三方 `@gientech/modual`），与 §1「系统管理（部门/角色/模型）已落地」不符；已在 `body[data-spectra-theme="1"]` 作用域内补深色表面/暖金主按钮/冷青操作文字（`c1f94213`、`699829e1`），见 `SPECTRA.md` §11.4。
- P0 逐页验证、字号双证据、构建结论、截图与蓝色像素对比、全部剩余项书面理由：`SPECTRA.md` §11 与 `docs/reviews/spectra-evidence/`。
- 本轮所有提交均显式列文件，未使用 `git add -A <目录>`；工作区里 `docs/ui-graph-workbench/TASKS.yaml` 等其它工作流改动未纳入。
- 2026-11-07 用户追加需求：智能对话欢迎区蓝紫鲸鱼图标换成同尺寸白色章鱼（唯一形状源透明版）、欢迎词改为 `Pierce the mist`；实现口径、字号证据与限制见 `SPECTRA.md` §12、`chat-brand-evidence.txt`。
- 2026-11-07 用户反馈：智能问答消息气泡白底白字不可读，已在主题作用域内把问题/答案卡片改为 SPECTRA 深色表面（含思考状态条），见 `SPECTRA.md` §13、`chat-bubbles-20261107/`。
