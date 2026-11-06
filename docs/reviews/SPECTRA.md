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
