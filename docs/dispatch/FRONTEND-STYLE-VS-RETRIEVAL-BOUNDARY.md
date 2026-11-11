# 前端设计风格同步 与 检索重构 的协作边界

日期：2026-11-06。状态：生效（两条工作流并行，需各自遵守本边界）。

## 1. 背景

两条并行工作流，会同时碰「知识图谱工作台」前端：

1. **前端设计风格同步**（SPECTRA 主题 / 图谱工作台 UI 重设计）——改前端视觉层。
2. **检索方式重构**（派工单 `HYBRID-RETRIEVAL-DISPATCH.md`）——阶段 3/4 会改前端召回展示层。

二者目标不同、文件域高度重叠，为避免相互覆盖，特立此边界。

## 2. 核心边界：风格层 vs 逻辑层

| 层 | 归属 | 内容 |
|---|---|---|
| **风格层** | 前端设计风格同步（可自由改） | 主题 token、配色、字号/间距、布局、组件视觉、`less/css`、图例/计数/面板的视觉样式 |
| **逻辑层** | 检索重构阶段 3/4（前端设计禁止改） | `graphData.ts` 的 fetch 数据流与 kb 路由、`search_type` 三路来源展示、图召回 trace、global 切换、降采样算法、助手列表数据绑定 |

原则：**一个改样式，一个改数据绑定，互不进入对方的层。**

## 3. 文件分类清单

### 3.1 风格层（前端设计可自由改）

- `frontend/plateform/src/components/KnowledgeBaseZh/v2/workbench.less`
- `frontend/plateform/src/components/KnowledgeBaseZh/v2/knowledge-graph.less`
- 主题 token / 配色 / 组件视觉相关文件

### 3.2 逻辑层（前端设计禁止改，留给检索重构）

- `frontend/plateform/src/components/KnowledgeBaseZh/v2/graphData.ts`（fetch、adaptGraphV2、kb 路由）
- `frontend/plateform/src/pages/HomePage/IntelligentChat/KnowledgeSearch/index.tsx`（助手列表 fetchAssisList、configId 传递、可见性刷新）

### 3.3 共享区（可改样式，不可改逻辑）

- `frontend/plateform/src/components/KnowledgeBaseZh/v2/GraphWorkbench.tsx`
  - 可改：JSX 结构、className、图例/计数/面板的视觉排版
  - 不可改：`visible` 计算、`RENDER_LIMIT` 降采样、`loadGraph`/`loadCommunity` 数据绑定、`truncated` 逻辑
- `frontend/plateform/src/components/KnowledgeBaseZh/v2/GraphCanvasV2.tsx`
  - 可改：节点/边的视觉渲染、标签样式、图例
  - 不可改：确定性力导向布局算法、相机/平移/缩放逻辑、`PROMINENT_TYPES`

## 4. 共享区协作规则

1. 动「共享区」文件前，commit message 里注明改的是**样式**还是**逻辑**，便于区分和回滚。
2. 若前端设计风格同步**必须**改动逻辑层文件，先与检索重构方对齐，不允许静默覆盖。
3. 检索重构阶段 3/4 改 `GraphWorkbench.tsx` / `graphData.ts` 的数据逻辑时，**保留现有样式 className 结构**，不在逻辑提交里夹带大范围样式改动。

## 5. 时机说明

检索重构刚派发，阶段 0~2 全部在后端（来源身份对齐、embedding 回灌），尚未碰前端。**前端设计风格同步应趁此窗口先落地**，避免检索重构推进到阶段 3/4（召回展示改动）时在共享区正面冲突。

## 6. 当前已冻结的前端改动（2026-11-06 已提交 e368f62）

以下 4 个文件的前端改动已提交，属检索/图谱功能修复，前端设计风格同步若需改动这些文件，请以本次提交为基线：

```
GraphCanvasV2.tsx   PROMINENT_TYPES 统一 v2 实体类型
GraphWorkbench.tsx  画布渲染上限(400) + truncated 提示
graphData.ts        按库路由(kb) + V2 优先 + adaptGraphV2
KnowledgeSearch/index.tsx  助手列表聚焦刷新 + 保留选中
```
