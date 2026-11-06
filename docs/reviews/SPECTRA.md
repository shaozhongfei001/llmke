# SPECTRA 前端主题重构 实施交付说明
- 基线 commit: e368f62
- 变更 commit: 43be122  分支: feat/spectra-theme

## 1 主题接入位置
- src/styles/spectra.tokens.css：--sp-* 颜色/表面 token，作用于 body[data-spectra-theme=1]
- src/styles/spectraTheme.ts：makeSpectraTheme(base) 在 antTheme 之上合并，不写任何 fontWeight/fontSize/lineHeight
- src/styles/spectra-pages.less：页面级作用域覆盖（外壳/登录/知识库/详情/检索/FAQ），颜色全部取 --sp-*
- App.tsx：ConfigProvider theme=makeSpectraTheme(antTheme)，挂载 data-spectra-theme 作用域属性

## 2 六页改造
- 登录：左侧深色视觉区+纯白章鱼，右侧表单保留账号/密码/验证码/注册/忘记密码/错误提示；无会议室图、无环形构图
- 知识库工作台：卡片列改为整行表格化（名称/说明·文件数·大小·操作），字段全部来自接口，未写死示例数值
- 文档解析：上下文条/文件表/Tabs 换深色；解析状态、版本、来源字段与批量操作、权限判断均未改动
- 检索/原文核验：配置面板、对话区、输入区与发送按钮换肤；未造原文定位值，缺失即按接口返回展示
- FAQ：列表容器/表头/复选框/空态换深色，导入/新建等主操作按钮改暖金；审批、启用、批量操作逻辑未改
- 知识图谱：workbench.less 全量颜色换肤（几何/字号原值保留），默认筛选与详情收起，画布占主内容区 97%（1366）/98%（1920）
- 图谱类型色在 v2/spectraPalette.ts 映射；graphData.ts（逻辑层）未改，仅作未知类型兜底；标签按关联度预算显示，选中/邻域始终可见

## 3 字号基线
- 未设置 html/root 字号，未用 zoom/transform，未批量覆盖 .ant-* 字号；antTheme 的字体链与 18/16/14px 等显式值原样继承
- 实测：KB Tabs 16px/24px（改造前后一致）；表格 14px；图谱实体标签 12/14px 基准（按缩放换算）；详情标题 22px；登录 Input/Button 沿用 AntD
- 例外：无。本轮未对任何元素改动 font-size/font-weight/line-height

## 4 品牌 Logo
- 原始件 sha256: 4fb6095366773f8c9202e7f0e0ebde39e3a92bbe71643f820ab71cde13a927e9（600x405）
- 使用位：登录主视觉、顶栏/侧栏应用 Logo（pages/HomePage LOGO_CONFIG）；业务功能图标仍用各自语义图标

## 5 mock / 真实数据边界
- 所有页面文案与数量均来自真实接口（知识库 2 个、文件 1/12 篇），未硬编码效果图示例值
- GraphLifecycleView/mockAdapter 仍为演示骨架，本轮未接入正式导航、未当作发布能力证据

## 6 运行与查看
- cd frontend/plateform && npx vite --port 15176（网关 8088 已运行）；账号 admin/Admin@12345，验证码从 Redis 读取
- 构建：NODE_OPTIONS=--max-old-space-size=16384 npx vite build（dist/ 受本地 safe-delete 阈值限制，验证时用 --outDir 新目录）

## 7 剩余硬编码与未解决
- 范围外路由（AI 对话、写作、系统管理、敏感词等）仍是浅色组件，后续可复用同一套 --sp-* 变量迭代
- 已知残留：检索消息气泡与原文高亮仍用蓝紫色（在 ChatMessage/richElements 内部），需下一轮逐个替换
- 已知基线问题：tsc --noEmit 存量 475 处报错（与本次无关）；vite 构建对 @mxmweb/zui 第三方 CSS 报 2 处 parse error，改造前即存在
- 构建结果：vite build 成功（15825 模块，3m1s，0 error）；tsc 与构建基线问题见上

## 8 截图证据
- 目录 spectra-evidence/before（基线 e368f62 worktree）与 after（本分支），同构采集，1366x768 六页 + 1920x1080 三页
- 采集脚本 capture.js：node capture.js <baseUrl> <outDir>，NODE_PATH 指向 my-playwright；需 8088 网关与 Redis 验证码

## 9 扩展菜单页（智能对话/助手配置/敏感词配置/搜索/用户反馈）
- 智能对话：AIChat/config/index.tsx 的 theme.colors 整体改 SPECTRA（primary/背景/侧栏/选中项/悬停/分组边框 22 项），vendor 聊天外壳随主题变量换肤
- 助手配置/敏感词/用户反馈：根容器 bg-white 改 #10181C，页面 style.less 与 styles.less 的底色/表头/悬停改深色，新建按钮由蓝紫渐变改暖金
- 搜索页：搜索框/建议词胶囊/下拉由 tailwind bg-white 统一改深色（主题作用域内的 .bg-white 等原子类重映射）
- 全局（主题作用域）：.ant-table-thead th 表头深色、.bg-white/.bg-gray-50/.border-gray-300/.text-gray-* 原子类重映射，修复各列表页残留白底
- 证据：spectra-evidence/after-menu/ 五张（1366x768）。已知残留：欢迎语标题与输入框描边仍为 vendor 蓝紫渐变

## 10 系统管理 / 写作 / 检索气泡
- 系统管理：organization/config/gradients.ts 按钮与三类图标渐变改 SPECTRA；部门/角色/分组表单主按钮统一暖金；用户树选中行改暖金底
- 写作模块：DocWriting/TemplateM/ResourceM/Indicators 的 23 处蓝紫渐变按钮与卡片改暖金；该模块 admin 无菜单权限，/docWriting 因 HomePage 取不到菜单抛错而不渲染（改造前既有）
- 检索页：ChatMessage/richElements/ChatInput/VoiceInput 的 blue-* 原子类全部改冷青/暖金（气泡头像渐变、引用块、列表标记、录音态、焦点环）
- 证据：spectra-evidence/after-system/（用户部门管理）、after/ 已按最新代码重采（含检索页）
- 遗留：写作模块需有菜单权限的账号才能实拍验证；组织部门树首项图标底色仍为蓝
- 共享展示组件 IconHeader / ParagraphTitle / MultiSelection 的默认蓝紫渐变改暖金（部门树图标底座、段落标题竖条、多选高亮）
- 角色管理：role 列表选中态 bg-blue-50 改暖金底；「添加新角色」按钮文字改深色（原白字压金底对比不足）；全局补 bg-blue-50/100 映射
- 说明：权限树行上看到的白底气泡是浏览器原生 title 提示，属 UA 样式，CSS 不可主题化，非页面残留

## 11 接手轮收口（2026-11-06）

基线 `e368f62`，本轮起始 HEAD `f9b7477a`，分支 `feat/spectra-theme`。本轮只做接续验证与残留收口，未重做主题，未改接口/权限/字段/状态/表单逻辑。

### 11.1 P0 真实浏览器验证

- 采集脚本 `docs/reviews/spectra-evidence/capture-regression.js`：Redis 读验证码登录，逐页 `goto` + 真实接口数据，1366×768；采集 DOM 文本长度、可见节点数、`body` 背景、横向溢出、控制台错误、字号 A/B、蓝色资源与蓝色元素探针。
- 证据：`spectra-evidence/after-p0-20261106/`（改前）、`after-p1-20261106/`（P1-2/P1-3 后）、`after-p1-final-20261106/`（最终），各 14 张 PNG + `report.json`。
- 覆盖：登录、知识库、文档解析、检索测试、知识图谱、FAQ、智能对话、助手配置、敏感词、搜索、用户反馈、系统管理（部门/角色/模型）。
- 结果：14/14 `RENDERED`，无 `PAGEERROR`，无横向溢出（`scrollWidth == 1366`），`body` 背景 `#090D11`；控制台 30 余条（最终轮 34 条）全为 AntD/React deprecation warning，改前改后同类同量（改造前既有，非本次引入）。详情页 URL 为真实库 `/chats/knowledgeBase/1004`，状态与文件数来自接口。
- 字号双证据：① 逐文件比对基线 `e368f62` 与当前 `src` 下 1282 个 `.less/.css/.tsx/.ts` 的 `font-size` 声明值多重集合，差异 **0**；② 同一 DOM 上「挂主题 / 摘 `data-spectra-theme`」A/B 采样，14 页 `fontSizeDiff=0`、`lineHeight` 差异 0，`root font-size` 仍 16px；未设 html/root 字号，未用 zoom/transform，未批量覆盖 `.ant-*` 字号。无超 1px 例外需说明。
- 构建：`NODE_OPTIONS=--max-old-space-size=8192 npx vite build --mode production --outDir <新目录>`（停掉 dev server 独占资源后 8m36s 完成，15825 模块），结论与告警计数见 `spectra-evidence/build-summary.txt`。`[vite:css] Parse error` 与未解析 SVG 告警在改前基线日志中同数量出现，属既有问题，非本次引入。

### 11.2 P1-2 SVG 自带蓝底（提交 `5711a7ea`）

用 DOM 坐标 + `backgroundImage`/`img.src` 探针定位 6 个实际被引用且自带蓝色 `fill`/`stop-color` 的 SVG（系统管理页可见的是导航 3px 渐变条，其余在搜索页与侧栏选中态）：

| 新资源 | 原色值 | 新色值 | 引用处 |
|---|---|---|---|
| `assets/navbarBg_spectra.svg` | `#BD9CFF #3C6DFF #0359FF` | `#E7CFA1 #D8BD89 #A98D62` | `components/Dashboard/index.tsx` |
| `assets/svg/icon-title_spectra.svg` | `#075BFF #AC96FF` | `#A98D62 #D8BD89` | `KnowledgeSearch/index.tsx` |
| `assets/svg/icon-search-bar_spectra.svg` | `#1538FF #7F81FF` | `#6FA9AE #94CED2` | `KnowledgeSearch/components/SearchInput.tsx` |
| `assets/svg/icon-zoomOut_spectra.svg` | `#2B69FF #8F91FF` | `#6FA9AE #94CED2` | 同上 |
| `assets/svg/duihua2_spectra.svg` | `#D9EAFF #1538FF #7F81FF` | `#D8BD89 #A98D62 #D8BD89` | `HomePage/hooks/useMenus.tsx` |
| `assets/svg/knowlegeBase2_spectra.svg` | 同上 | 同上 | 同上 |

- 每个新文件与原文件**除颜色 token 外逐字节一致**（把所有 `#RRGGBB` 归一为 `#COLOR` 后两文件相同，颜色 token 数相同），形状/尺寸/触须等几何完全未动；原文件全部保留。
- 引用改为 `*_spectra.svg`，未使用 CSS `filter` 反色。改后运行时 `blueSvg` 资源命中数由 6 降为 0。
- **边界声明**：`KnowledgeSearch/index.tsx` 在 `FRONTEND-STYLE-VS-RETRIEVAL-BOUNDARY.md` §3.2 属逻辑层禁改文件，本轮仅替换 1 行图标 import，未触碰 `fetchAssisList`/`configId`/可见性刷新等逻辑，该行可独立回滚；未发现与检索重构的样式冲突。

### 11.3 P1-3 残留硬编码色（提交 `776d7f2b` + P0 残留收口提交）

- 6 个 `.tsx` 的 `linear-gradient(99.9deg, #2B69FF, #8F91FF)`（含 2 处三元表达式裸字符串）与 `PasswordModal/utils/constants.ts` 的 JS 常量 → `#D8BD89` 底 + `#111915` 字。复验 `grep -rl "linear-gradient(99.9deg" src --include=*.tsx | wc -l` = **0**。
- `src/assets/styles/` 中 7 处同名 less 渐变与第三方 `@mxmweb/somelib/index.js` 的 1 处内联渐变：**不改原文件**，在 `body[data-spectra-theme="1"]` 作用域内覆盖；vendor 的 inline style 与 `knowledgeSearch.less` 的原有 `!important` 按规则用 `!important` 对抗。
- `blue-[0-9]` 原子类 20 个 `.tsx` **保留源类名**（交接文档 §3 决策 4：主题作用域内统一重映射），在 `spectra-pages.less` 补齐 `text-/bg-/border-/hover:/focus:/from-to-` 全量映射，避免与并行工作流在 `roles/*` 等文件上正面冲突。逐文件书面理由见 §11.5。
- 逐页复查补漏：`text-[#305eba]`（文档解析文件名）、FAQ `#055aff`（含 `.more-action-row` 原有 `!important`）、模型页分页 `inline #4E6EF2`、`AntD geekblue` 标签、AntD 4 Slider `#1890FF`、`.fat-header-btn-wrap` 按钮。改后运行时蓝色 DOM 元素计数：模型页 26→0、角色页 12→0、全 14 页 0。蓝色像素同构对比见 `spectra-evidence/blue-pixel-diff.txt`。

### 11.4 新增残留修复：系统管理/模型管理页

P0 实拍发现 `/system/models` 整页仍为浅色（白底表格、蓝底「新建」、蓝色操作文字），与本交接文档 §1「系统管理（部门/角色/模型）已落地」不符，属**改造前既有残留**。已在主题作用域内为第三方 `@gientech/modual` 的 `.xviewer-container` / `.dynamic-table-*` / `.zui-button` 补深色表面、暖金主按钮、冷青操作文字与深底输入，未改任何接口、表单或状态。改前后截图：`after-p0-20261106/14-system-models.png` 与 `after-p1-final-20261106/14-system-models.png`。

### 11.5 剩余项与逐文件书面理由

`grep -rl "blue-[0-9]" src --include=*.tsx | wc -l` 仍为 20：这些类名是 tailwind 语义类，按既定架构由主题层重映射，源码保留可避免与另一条工作流冲突；运行时实测蓝色 DOM 元素为 0。

| 文件（`src/` 下相对路径） | 涉及类名 | 保留理由 |
|---|---|---|
| `components/KnowledgeBaseZh/KnowledgeAnalyBlock/index.tsx` | `text-blue-400` | 主题层统一重映射 |
| `components/KnowledgeBaseZh/KnowledgeAnalyGraph/index.tsx` | `text-blue-400` | 同上 |
| `components/KnowledgeBaseZh/KnowledgeAnalyVideo/index.tsx` | `text-blue-400` | 同上 |
| `components/SdqaDrawer/index.tsx` | `bg-blue-600/700` | 同上（含 hover 变体） |
| `components/SplitLayout/LeftPanel.tsx` | `bg-blue-50` | 同上，已有全局映射 |
| `components/SplitLayout/RightPanel.tsx` | `bg-blue-500` | 同上 |
| `components/layouts/AppNavLayout.tsx` | `bg-blue-500 text-blue-500/600` | 同上（含 hover 变体） |
| `components/layouts/ChatLayout.tsx` | `bg-blue-50` | 同上，已有全局映射 |
| `pages/HomePage/IntelligentChat/Setting/PublishPannel/ApiDocRender.tsx` | `bg-blue-50 border-blue-200 text-blue-700` | 同上 |
| `pages/HomePage/IntelligentChat/Setting/SettingDetail/index.tsx` | `bg-blue-50 border-blue-200` | 同上（6 处） |
| `pages/others/NotFound.tsx` | `text-blue-200` | 同上 |
| `pages/others/PageLoading.tsx` | `bg-blue-300/500 border-blue-100/500` | 同上（10 处加载动画球） |
| `pages/system/models/AuthModelForm.tsx` | `bg-blue-500 text-blue-600` | 同上 |
| `pages/system/models/ModelForm.tsx` | `focus:border-blue-400` | 同上（含 focus 变体） |
| `pages/system/models/oldIndex.tsx` | `text-blue-500` | 同上 |
| `pages/system/organization/groups/components/GroupList.tsx` | `text-blue-600` | 同上 |
| `pages/system/organization/roles/PermissionTree.tsx` | `bg-blue-50 border-blue-100 text-blue-600` | 同上 |
| `pages/system/organization/roles/RoleList.tsx` | `bg-blue-50 hover:text-blue-500` | 同上（含 hover 变体） |
| `pages/system/organization/roles/UserAssignForm.tsx` | `to-blue-500/600` | 同上（渐变端点映射） |
| `pages/system/organization/roles/index.tsx` | `to-blue-500/600` | 同上（渐变端点映射） |

其它剩余（均有书面理由，不属本次可改范围）：

1. 登录页验证码图片为后端 kaptcha 接口返回的位图（蓝色字符），前端不可主题化；状态文案与图片均来自真实接口。
2. 智能对话欢迎语鲸鱼 Logo、搜索页下拉小机器人图标来自 `@gientech/modual` 第三方品牌资源（`defaultWeLogo.svg` 等），检索页另有少量第三方图形蓝色像素（`blue-pixel-diff.txt`：04-retrieve 216px，运行时蓝色 DOM 元素为 0）；改图需产品/第三方决策，未擅自重绘。
3. 浏览器原生 `title` 白气泡属 UA 样式，CSS 不可主题化。
4. 范围外路由（写作、数据库、对比、AI 编辑器）仍沿用旧浅色 token，归 P2；本轮只把其中内联蓝紫渐变按风格层清掉，未铺开整套主题。
5. `GraphLifecycleView/mockAdapter` 仍是演示骨架，未接入正式导航、未当作能力证据；图谱标签仍按「关联度预算」控制可见性，`graphData.ts` 未改。

### 11.6 P1-1 写作模块：已收口（Owner 批准路径 B，2026-11-07）

Owner 在请示中选定路径 B 并接受权限行为变更，提交 `2f35b613`：在
`HomePage/index.tsx:77` 的 `const { routes } = _menu;` 前加 `if (!_menu) return;`
（1 行逻辑层改动，其余代码未动；该崩溃点在基线 `e368f62` 即存在）。

**实测的权限行为变化**（`after-writing/report.json`，真实浏览器、admin、Redis 验证码）：

| 访问路径 | 守卫前 | 守卫后（实测） |
|---|---|---|
| `/docWriting/main`、`/docWriting/template` | 解构异常 `Cannot destructure property 'routes'`，整页白屏 | 不再崩溃；写作模块接口返回 401，被全局拦截器重定向到 `/login`（重新登录后重试一次仍如此，属稳定权限边界，非登录态时序） |
| `/docWriting/resource`、`/docWriting/indicator` | 同上白屏 | 停留在原页，显示真实空数据界面（深色表面、`暂无数据`/`指标管理` 等接口文案） |

- `destructureError=[]`、`PAGEERROR=[]`：白屏崩溃已消除；四页均 `RENDERED`，无横向溢出，`root font-size` 仍 16px。
- 证据：`spectra-evidence/after-writing/` 四张 1366×768 PNG + `report.json`，采集脚本 `capture-writing.js`（对跳登录页的路由会重新登录重试并记录首次/重试 URL）。
- **诚实声明**：`admin` 无写作菜单权限，因此四张截图中 `01-main`、`02-template` 是登录页（权限边界证据），`03-resource`、`04-indicator` 是无权限下的空数据外壳；它们**不是**完整写作功能页，未注入静态预览、未伪造数据。要验收完整写作页仍需路径 A（提供有写作菜单权限的账号）。
- 新增残留：`04-indicator` 仍有 7 个蓝色元素与一条白底表格，属范围外路由的 P2 铺开项，本轮未扩大改动；`01/02` 的 401 重定向是既有权限链路行为，未在本次改动范围内修改。

### 11.7 本轮提交

按「一项一提交、显式列文件」执行，未使用 `git add -A <目录>`：`5711a7ea`（P1-2 换图）、`776d7f2b`（P1-3 清渐变与映射）、`c1f94213`（P0 残留收口：模型页换肤 + 补漏）、`699829e1`（滑块/FAQ 工具条映射提权）、`df965009`（文档与 P0/P1 证据）、`2f35b613`（P1-1 守卫，Owner 批准路径 B）、P1-1 文档与写作四页证据提交。完整序列见 `git log --oneline 5711a7ea~1..HEAD`。工作区里 `docs/ui-graph-workbench/TASKS.yaml` 等其它工作流改动未纳入。
