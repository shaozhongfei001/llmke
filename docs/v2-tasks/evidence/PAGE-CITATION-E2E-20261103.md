# 页面端到端：问答链路通，引用点击 UI 缺失（2026-11-03）

## 结论

页面 → 8088 → rag-qa-service → 19532（V2 shim）→ 18094（V2 图服务）链路真实可用，
问答答案能在页面渲染；但**页面上没有可点击的引用入口**，无法完成“点引用看原文”。

这是前端/交互缺口，不是后端链路问题。

## 环境

- 前端：`frontend/plateform/dist`（2026-10-31 构建），用临时 nginx 容器在 **18088** 提供，
  反代配置 `frontend/plateform/nginx/r12-18088.conf`；验证后容器已删除。
- 直接 `npm run dev` 失败：Vite 监听 `dist.bak-0006` 触发 `ENOSPC`（inotify 上限），
  与代码无关；改用静态 dist 验证。
- 登录页不可用（dist 里 `getUrlPrefix()` 为空），按调查结论注入 token：
  `localStorage["gitech_ril:rag_ai"] = {"userInfo":{"token":"…"}}`。
- 页面实际请求：`POST /proxy/qa/ai/question_re`（浏览器 → 8088 → `:18083`）。
- 图服务快照：为验证数字 `file_id` 引用，用 19531 重建单文档快照
  `snapshot-20261103012952-439603-g0`（file_id=999010），验证后 18094 已还原到
  `s4-root-c/snapshot-20261103000343`（facts=69、33 社区）。

## 实测

1. **global 问答渲染**（R13 Global 助手 + 全局开关）：
   页面显示 3 条授信审批事实，带“（来源：F003）”，与 18094 `/v2/graph/global` 输出一致；
   无关的集团客户/20 亿条款已不再出现。
2. **普通问答渲染**（R12 默认助手）：单文档快照下显示
   “星航贷 单户最高授信额度为 8000.0万元（来源：999010）”。
3. **引用入口**：答案底部只有 4 个按钮——复制、赞、踩、重新生成；
   没有“参考来源/引用”按钮，DOM 中也查不到 `ref/cite/source` 相关节点。
   点击第 4 个按钮触发“重新生成”，不是引用。
4. **答案位置**：流式结束后列表会自动滚到推荐问题，答案落在视口上方（y≈-545），
   需要向上滚动才能看到；不是内容丢失。

## 判断

- 后端 `reply.reference` 有数据时（数字 file_id）页面仍不渲染引用列表，
  说明该构建/助手没有启用 vendor 的 `references:click` 入口，或未注册引用渲染配置。
- 因此“点引用看原文（段落/单元格/图片定位）”**当前不可验收**，需前端改动：
  确认 `@gientech/modual` 的 reference list 启用条件，或在宿主接
  `references:click` / `knowledge_referenceFile_title:click` 并渲染抽屉。
- 不建议把“答案里带（来源：xxx）”当成引用交互已验证。

## 复现步骤

```bash
# 1) 临时静态服务（验证后删除）
docker run -d --name v2-fe-e2e --network host \
  -v $PWD/frontend/plateform/dist:/usr/share/nginx/html/rag:ro \
  -v $PWD/frontend/plateform/nginx/r12-18088.conf:/etc/nginx/conf.d/default.conf:ro nginx:alpine
# 2) 注入 token 后打开 http://127.0.0.1:18088/chats/main
# 3) 选 R13 Global 助手 + 全局开关，提问；观察答案底部按钮
```

## 追加：修好「知识溯源」入口（2026-11-03 01:40）

### 根因

`question_re` 的 global 分支（`AiServiceImpl.java`）reference 只取“本次上传文件”：
没上传就恒为 `"[]"`，而 vendor 的「知识溯源」按钮在 `hasAny=false` 时直接 `return null`。
答案里的“（来源：F003）”只是正文文本，不进 reference 数组。

实测确认：修前 `POST /qa/ai/question_re`（globalMode=true）返回 `reference="[]"`。

### 改动（v2 与 r12 同步）

global reduce 分支的 reference 改为三级回落：
上传文件 > `retrievedData.getDocumentString()`（documents_list） > `"[]"`。
前端无需改动；vendor 固定 `referenceMode="button"`，按数组长度渲染。

### 修后实测

- `question_re`：`reference` 由 `"[]"` 变为 327 字节，1 条，metadata 含
  `search_type=["global"]`、`community="c-3"`、`sources[{file_id:F003}]`。
- 页面（dev 15174 / 生产 dist 同源）：答案下方出现 **「知识溯源 1」**；
  点击打开右侧“知识溯源”面板，标签“知识库文档”，条目 1 条。
- 已知不足：条目显示 **“未知文档”**——global reference 的 metadata 只有 file_id，
  没有 title/locator；生产数字 ID 语料仍需验证标题与原文定位是否可打开。

### 修后仍未闭环的一点（不能算通过）

用真实浏览器点击「知识溯源」时，hit-test 报：
`Element is covered by <div.p-3 inside div#root> at its click point`，
即按钮中心被输入区容器覆盖；改用 JS `button.click()` 才能打开面板。

所以当前状态是：**按钮出现、面板能开，但鼠标正常点击可能落不到按钮上**。
需前端确认是输入区容器高度/z-index 覆盖，还是按钮被放在滚动容器边缘；
在真实鼠标可点之前，“点引用”仍不能算验收通过。
