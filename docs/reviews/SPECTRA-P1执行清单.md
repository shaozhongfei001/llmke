# SPECTRA · P1 三项执行清单

配套 `SPECTRA-接手提示词.md` 使用。每项按「定位 → 改动点 → 验收」三步做，
做完更新 `docs/reviews/SPECTRA.md` 的残留章节。

---

## P1-1 写作模块无法实拍验证

### 定位

```bash
cd ~/data/dev/llmke-v2/frontend/plateform/src/pages/HomePage
grep -n "const { routes } = _menu" index.tsx        # 实际在第 77 行
```

现象：浏览器访问 `/docWriting` 白屏，控制台
`TypeError: Cannot destructure property 'routes' of '_menu' as it is undefined`。

成因：`navBarData` 来自 `useMenus()`，`admin` 账号没有写作菜单项，
`navBarData.find(...)` 返回 `undefined`，第 77 行直接解构。

### 两条路径，先请示再动手

**路径 A（推荐，零代码）**：用一个具备写作菜单权限的账号登录后实拍。
需要 DBA/管理员给 `admin` 加写作资源，或提供测试账号。走到这步要停下问人。

**路径 B（改代码，属逻辑层，必须请示）**：在 77 行前加守卫

```ts
if (!_menu) return;          // 无该模块权限时不重定向
```

注意：这会改变「无权限访问 `/docWriting`」的行为（由白屏崩页变为停留原页），
属权限相关行为变更，不得自行决定。

### 验收

- 路径 A：`/docWriting/main`、`/docWriting/template`、`/docWriting/resource`、
  `/docWriting/indicator` 四页各一张 1366×768 截图，无白底块、无蓝紫按钮，
  存 `spectra-evidence/after-writing/`。
- 路径 B：同上，另需说明无权限时的行为变化并记录进文档。

---

## P1-2 系统管理个别图标自带蓝底

### 定位

残留来自 SVG/位图资源自带的底色或渐变，不是 CSS。用浏览器探针找：
打开目标页 → 在疑似蓝块中心取点，读 `backgroundImage`。

已知的一处历史成因（已修，留作方法参考）：
`pages/Components/IconHeader/index.tsx` 默认值
`linear-gradient(-50deg, #7FC0FB, #4088F4)`，影响部门/分组/角色图标底座。

```bash
cd ~/data/dev/llmke-v2/frontend/plateform/src
grep -rn "7FC0FB\|4088F4\|3162FF" --include=*.tsx --include=*.ts --include=*.less .
grep -rln "4E6EF2" ../../node_modules/@mxmweb/zui-theme/assets/style.css
```

### 改动点

1. 若为 CSS/内联渐变：按 `#A98D62 → #D8BD89`（暖金）或 `#6FA9AE → #94CED2`（冷青）替换。
2. 若为 SVG 资源自带底色：**另存一份 `*_spectra.svg`，只替换 fill 色值，形状与尺寸不变**
   （参照 `assets/knowledgebase/knowledge_base_title_icon_spectra.svg` 的做法），
   原文件保留，避免影响未迁移页面。
3. 不要用 CSS filter 反色硬调，会在深底上失真。

### 验收

- 同页改造前后同构截图对比，蓝块消失；
- `grep -c "spectra" ` 确认新资源被引用、旧资源仍在（未被删除）；
- 记录「哪个文件、哪几行 fill、新色值」到 SPECTRA.md。

---

## P1-3 残留硬编码色逐页复查

### 定位（当前实测基线，2026-11-06）

```bash
cd ~/data/dev/llmke-v2/frontend/plateform/src
grep -rl "linear-gradient(99.9deg" --include=*.tsx . | wc -l   # 6
grep -rl "blue-[0-9]"              --include=*.tsx . | wc -l   # 20
```

已知还剩蓝紫渐变的 6 个文件：

```
pages/HomePage/IntelligentChat/Setting/PermissionConfig/PermissionConfig.tsx
pages/HomePage/Writing/EditSegmentedTemplate/index.tsx
pages/Components/PermissionConfig/index.tsx
components/progressDrawer/index.tsx
components/UploadFileType/index.tsx
components/AiEditor/components/editor/plugins/customPlugin/aiWriter/aiWriter.tsx
```

### 改动点

- 主操作按钮：`#D8BD89` 底 + `#111915` 字。
- 次级/链接：`#94CED2`。
- 危险操作：`#E28683`。
- 替换 `blue-*` 原子类时优先改为 `[#94CED2]` / `[#D8AED9]` 形式，
  或依赖 `spectra-pages.less` 里已有的全局映射（`.bg-white` / `.bg-gray-*` /
  `.bg-blue-50` / `.border-gray-300` / `.text-gray-*`）——先确认是否已被映射，避免重复改。
- **坑**：三元表达式里的裸字符串（`cond ? "a" : "linear-gradient(...)"`）正则易漏，
  替换后必须 `grep` 复验为 0。

### 验收

- 两条 `grep` 计数归零，或每处剩余都有书面理由（例如第三方组件无法覆盖）。
- 受影响的页面各一张截图，确认无突兀亮块。
- `npx vite build` 通过（用 `--outDir` 新目录 + `NODE_OPTIONS=--max-old-space-size=16384`）。

---

## 通用执行纪律

1. 一次只做一项，做完立即提交（显式列文件，禁止 `git add -A`）。
2. 每项提交信息格式：`fix(ui): <页面> <问题> 改 SPECTRA`。
3. 若某项需要改逻辑层（P1-1 路径 B），先停下问，不要顺手改。
4. 三项全部完成后，把 `SPECTRA.md` §「已知残留」更新为实际状态，并在
   `SPECTRA-交接-新会话续作-V1.0.md` 里标注 P1 已收口。
