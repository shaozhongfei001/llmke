# R12 前端交付状态（fe-builder）

生成时间：2026-10-25 01:50（本机时间）
工作目录：`/home/szf/data/dev/llmke-r12/frontend/plateform`（分支 `feature/R12-real-rag`）
依据：`platform/r12/R12-ENV-CONTRACT.md` r12.1

## 0. 结论（先看这里）

| 项 | 结果 |
|---|---|
| 依赖安装 | 成功，`added 1745 packages in 6m` |
| 生产构建 | 成功，`✓ built in 7m 1s`（第 1 次失败，已定位并修复，见 §4） |
| dist 产物 | 存在，`147M`（含 gzip）；不含 `.gz` 为 `128M`；js 文件 1304 个，`.gz` 30 个 |
| dev server | 运行中，`0.0.0.0:15174`，PID `3280854`（npm 包装进程 `3280823`） |
| 代理 | `/proxy`、`/cecProxy`、`/auth`、`/index`、`/qa`、`/graph`、`/sensitive` → `http://127.0.0.1:8088`；`/minio` → `http://127.0.0.1:19000` |
| curl 根路径 | `GET /` → **200** |
| curl 代理 | `GET /proxy/auth/user/kaptcha` → **500**（首轮时网关 8088 未起；网关起来后已变 **200 image/jpeg**，见 §14） |
| 生产部署 | nginx 容器 `r12-fe`（`nginx:alpine`）监听 **18088**，dist 直服 + 反代本机网关；`curl -I /` = 200，`/proxy/auth/user/kaptcha` = 200（见 §13） |
| 三段连通 | 前端(18088/15174) → 网关 8088 → rag-auth：带 token `getMenusByUser` = 200，真实菜单 **7 条**（见 §14） |

本次只改 **2 个源文件**，未触碰 `services/**`、`platform/**`（除本人负责的 status/logs/run 产物）、`docs/**`。

## 1. 运行时版本（实测）

- node `v25.0.0`，npm `11.6.2`
- vite `5.4.21`（`package.json` 声明 `^5.0.0`）
- 工程栈：React18 + Vite5 + antd5 + less/tailwind；入口 `src/main.tsx` → `src/App.tsx` → `src/router/config/index.tsx`
- 未使用 nvm 降级：Node 25 下 install/build/dev 全部正常，无需降级（无 incompatible 报错）

## 2. 安装记录

命令（在 `frontend/plateform` 下执行）：

```
npm install --legacy-peer-deps --registry=https://mirrors.tencent.com/npm/
```

- 耗时：`6m`（日志尾部 `added 1745 packages in 6m`）
- 退出码 0；日志：`platform/r12/logs/fe-npm-install.log`
- 私有包 `@mxmweb/*`、`@gientech/modual@2.0.10` 均从腾讯镜像正常解析，无 404/无版本回退
- `~/.npmrc` 已预置 `registry=https://mirrors.tencent.com/npm/`、`prefer-offline=true`、`maxsockets=3`（tarball 下载慢，单包曾达 79s）
- 代价（需知晓）：
  1) 加 `--legacy-peer-deps` 跳过 peer 依赖校验，未解决 peer 冲突（React18 与部分 plate/excalidraw 期望的 React19 之类），运行时若出问题优先查这里；
  2) 新增 `package-lock.json`（原先只有严重滞后的 `pnpm-lock.yaml` / `yarn.lock`）；
  3) 仅 deprecation 告警，无 error：`inflight@1.0.6`、`glob@7`、`rimraf@3`、`eslint@8.57.1`、`react-query@4.0.0`、`@types/marked@6` 等。

## 3. 改动清单（源码仅 2 个文件）

`git status` 事实：`frontend/plateform/` 在本工作树中整体为 **untracked**（`?? frontend/plateform/`），因此 `git diff --stat` 输出为空。为给出等价证据，以下 diff 以同源快照 `/home/szf/data/dev/r12-src/ai-plateform`（mtime 2026-01-21，与本工程逐文件一致）为基线生成。

| 文件 | md5 | 改动性质 |
|---|---|---|
| `vite.config.ts` | `580d6e0b9d413b99df8b3d025d07e0f4` | 指向本机网关 + 端口 15174 + 补代理前缀 |
| `src/components/ModuleTest/components/FormContainer/index.tsx` | `18b9d88f5614598beaf6c8cec11ab549` | 大小写修正（构建阻塞项） |

### 3.1 `vite.config.ts`

- `CURRENT_SERVER` 由 `SERVER_11 = http://10.15.12.11` 改为 `http://127.0.0.1`（`SERVER_*` 常量原样保留，未删，便于回溯）
- `PORT` 由“按服务器三元判断 8888/8889”改为固定 `"8088"`；新增 `MINIO_PORT = "19000"`
- `server.port` 8888 → **15174**
- `server.proxy`：`/minio` 目标 `:9000` → `:19000`；`/proxy`、`/cecProxy` 目标 → `http://127.0.0.1:8088/`（rewrite 逻辑不变）；新增 `/auth`、`/index`、`/qa`、`/graph`、`/sensitive` 五个直连前缀（无 rewrite）
- 未改动 build/plugins/legacy/manualChunks/optimizeDeps/css 等任何构建配置

```diff
-// eslint-disable-next-line prefer-const
-let CURRENT_SERVER = SERVER_11;
-
-const PORT =
-  CURRENT_SERVER === SERVER_20
-    ? "8889"
-    : CURRENT_SERVER === SERVER_11 || CURRENT_SERVER === SERVER_12
-    ? "8889"
-    : "8888"; //8888
+// R12：前端只连本机 Java 网关（platform/r12 环境契约 §1），不再指向内网 IP
+// eslint-disable-next-line prefer-const
+let CURRENT_SERVER = `http://127.0.0.1`;
+// 网关端口（网关根路径即 /auth /index /qa /graph /sensitive）
+const PORT = "8088";
+// MinIO 端口（R12 与既有 9000 实例隔离）
+const MINIO_PORT = "19000";
...
-      port: 8888,
+      port: 15174,
       proxy: {
         "/minio": {
-          target: `${CURRENT_SERVER}:9000/`,
+          target: `${CURRENT_SERVER}:${MINIO_PORT}/`,
...
         "/proxy": { target: `${CURRENT_SERVER}:${PORT}/`, ... }
+        "/auth":     { target: `${CURRENT_SERVER}:${PORT}`, changeOrigin: true },
+        "/index":    { target: `${CURRENT_SERVER}:${PORT}`, changeOrigin: true },
+        "/qa":       { target: `${CURRENT_SERVER}:${PORT}`, changeOrigin: true },
+        "/graph":    { target: `${CURRENT_SERVER}:${PORT}`, changeOrigin: true },
+        "/sensitive":{ target: `${CURRENT_SERVER}:${PORT}`, changeOrigin: true }
```

### 3.2 `src/components/ModuleTest/components/FormContainer/index.tsx`

```diff
-import IconLink from "@/assets/svg/Icon-link.svg";
+// R12：原写法 Icon-link.svg 在 Linux 大小写敏感文件系统上不存在，实际文件为 icon-link.svg
+import IconLink from "@/assets/svg/icon-link.svg";
```

原因：磁盘实际文件为 `src/assets/svg/icon-link.svg`（小写 i）。原工程在 Windows 上大小写不敏感所以能过；Linux 上构建直接 `ENOENT` 失败。该模块被写作模块页面静态引用（`src/pages/HomePage/Writing/Module/*`），属主链可达模块，必须修。

## 4. 构建

命令：`npm run build`（= `node --max-old-space-size=16384 ./node_modules/vite/bin/vite.js build --mode production`，不跑 tsc）

| 轮次 | 结果 | 耗时 | 日志 |
|---|---|---|---|
| attempt1 | **FAILED** | 1m 51s | `platform/r12/logs/fe-build.attempt1.log` |
| attempt2 | **SUCCESS**（`✓ built in 7m 1s`） | 7m 1s | `platform/r12/logs/fe-build.log` |

attempt1 失败原文（保留，未删除、未隐藏）：

```
✓ 14319 modules transformed.
x Build failed in 1m 51s
error during build:
[vite:asset] Could not load /home/szf/data/dev/llmke-r12/frontend/plateform/src/assets/svg/Icon-link.svg
(imported by src/components/ModuleTest/components/FormContainer/index.tsx): ENOENT: no such file or directory
```

修复 = §3.2 的大小写修正（唯一改动），attempt2 通过。

产物（`dist/`）：

- 总大小 `147M`（含 `.gz`）；不含 `.gz` 为 `128M`
- js 文件 1304 个；`.gz` 30 个（`vite-plugin-compression` threshold 512KB 生效）
- `dist/index.html` 23,076 B，含 `polyfills-*.js` + `index-6OoyH1eC.js`（entry 305K）+ 大量 `modulepreload`
- 最大非 legacy 产物：`Detail-DubWhtSu.js 2.2M`、`vendor-mermaid 1.1M`、`vendor-antd 920K`、`vendor-pdfjs-dist 644K`、`vendor-swagger-ui-react 436K`
- 附带 `dist/cmaps`（pdfjs cmaps 静态拷贝）、`dist/worker/pdf.worker.min.js`、`dist/font/`、`dist/config.json`

## 5. dev server

```
mkdir -p platform/r12/logs platform/r12/run
cd frontend/plateform && nohup npm run dev > platform/r12/logs/fe-dev.log 2>&1 &
```

- 监听：`0.0.0.0:15174`（`ss -ltnp` 实测 pid=3280854）
- PID 文件：`platform/r12/run/fe-dev.pid` = `3280854`（npm 包装进程为 `3280823`）
- 日志：`platform/r12/logs/fe-dev.log`，`VITE v5.4.21 ready in 246 ms`
- 停止：`kill $(cat platform/r12/run/fe-dev.pid)`

## 6. curl 验证（实测输出）

| 请求 | 结果 |
|---|---|
| `GET http://127.0.0.1:15174/` | **200** |
| `GET http://127.0.0.1:15174/login` | **200**（SPA history fallback 正常） |
| `GET http://127.0.0.1:15174/chats/main` | **200** |
| `GET http://127.0.0.1:15174/chats/knowledgeBase` | **200** |
| `GET http://127.0.0.1:15174/proxy/auth/user/kaptcha` | **500** |
| `GET http://127.0.0.1:15174/auth/user/kaptcha` | **500** |

关于 500：`curl http://127.0.0.1:8088/` → `curl: (7) Failed to connect ... 连接被拒绝`（网关尚未启动）。dev 日志同时打印：

```
01:44:02 [vite] http proxy error: /auth/user/kaptcha
Error: connect ECONNREFUSED 127.0.0.1:8088
```

即**代理转发链路是通的，只是后端不在**。注意与任务书的差异：vite 对上游 `ECONNREFUSED` 返回 **500**，不是 502；等网关起来后应复测为 200，不要按 502 判。

另外做了 dev 侧模块编译抽查（`/src/main.tsx`、`/src/App.tsx`、`/src/pages/Login/index.tsx`、`/src/pages/HomePage/IntelligentChat/AIChat/index.tsx`、改动过的 `ModuleTest/FormContainer/index.tsx`）全部 `200`，无 transform 报错。

## 7. 代理映射表（最终态）

| 前端前缀 | 目标 | rewrite | 用途 |
|---|---|---|---|
| `/proxy` | `http://127.0.0.1:8088/` | 去掉 `/proxy` | 主链路：`/proxy/auth/user/kaptcha`、`/proxy/index/knowledgeBase/file/uploadFiles`、`/proxy/qa/ai/question(_re)` |
| `/cecProxy` | `http://127.0.0.1:8088/` | 去掉 `/cecProxy` | 历史前缀，等价 `/proxy` |
| `/auth` | `http://127.0.0.1:8088` | 无 | 网关根直连 |
| `/index` | `http://127.0.0.1:8088` | 无 | 网关根直连（知识库/索引） |
| `/qa` | `http://127.0.0.1:8088` | 无 | 网关根直连（问答） |
| `/graph` | `http://127.0.0.1:8088` | 无 | 网关根直连（图谱，前端 `VITE_CONFIG_SHOW_GRAPH=false` 未启用） |
| `/sensitive` | `http://127.0.0.1:8088` | 无 | 网关根直连（敏感词） |
| `/minio` | `http://127.0.0.1:19000/` | 去掉 `/minio` | 文件预览/下载 |

env 前缀无需改动：`.env.development` / `.env.production` 均为 `VITE_RAG_PREFIX=/proxy`、`VITE_CEC_PREFIX=/cecProxy`、`VITE_MINIO_PREFIX=/minio`（构建后已内联进 entry chunk）。

## 8. 主链页面是否打进了 dist（产物级核验）

| 页面 | 路由 | 产物证据 |
|---|---|---|
| 登录页 | `/login` | entry `dist/assets/index-6OoyH1eC.js` 内含 `"/login"`、`user/kaptcha`（登录接口 `getUrlPrefix()+"/auth/user/kaptcha"`）→ 已打入 |
| 问答页 | `/chats/main` | `dist/assets/index-BRRdsIlf.js` 内含 `/qa/ai/question`；`ppt-D15M4O6d.js` 内含 `concat(r,"_re")`（即 `question_re` 由 `${prefix}/qa/ai/question` + `_re` 运行时拼接，静态 grep 搜不到字面量，勿误判为缺失） |
| 知识库页 | `/chats/knowledgeBase` | `dist/assets/index-BRRdsIlf.js` 内含 `/index/knowledgeBase/file/uploadFiles`、`file/exist`、`file/getFileStatusByUids`、`file/stream` |
| 敏感词页 | `/chats/sensitiveWords` | `dist/assets/index-Bn3aktl2.js`、`detail-DM9-Cx24.js` 内含 `sensitiveWords` |
| 路由表 | — | entry chunk 内 `chats/main`、`knowledgeBase`、`sensitiveWords` 路径字面量均存在 |

上传接口与契约一致：`upload_files: {url:"/index/knowledgeBase/file/uploadFiles", method:"post"}` → 实际请求 `/proxy/index/knowledgeBase/file/uploadFiles`（multipart）。

## 9. 仍存在的构建告警（全部非致命，未屏蔽；逐条影响面见 §15）

| 告警 | 数量 | 说明 |
|---|---|---|
| `[vite:css] Parse error on line 1 ... got unexpected "RPAREN"` | 12 | tailwind 生成的 CSS 里 `calc(var(--x) - var(--line-height, calc(1em * var(--default-line-height))) / 2` 这类嵌套计算，被 less/lightningcss 解析器判为语法错误。**产物仍生成**，但受影响样式块可能被丢弃 → 视觉风险，建议 QA 重点看间距/垂直居中类样式 |
| `... referenced in ... didn't resolve at build time` | 61 | 主要是 `fonts/KaTeX_*.woff2/ttf` 与 `../../../../../assets/setting/setting_file_icon.svg` 等 css `url()` 运行时解析路径，构建期无法定位。运行时可能 404（KaTeX 公式字体、部分图标） |
| `Generated an empty chunk: "vendor-xxx"` | 74 | `manualChunks` 按包名切分产生的空 chunk（仅体积噪声） |
| `Some chunks are larger than 500 kB` | 2 | `vendor-@gientech/modual`（6.9M/legacy 8.2M）等；不阻塞 |
| `Browserslist: caniuse-lite is 10 months old` | 1 | 建议 `npx update-browserslist-db@latest`，本次未动（避免联网改依赖） |

构建日志 17.6 MB，体积主要来自上面 61 条 unresolved 与 74 条 empty chunk 的重复文本。

## 10. 待 TL 确认 / 风险登记（我不擅自处置）

1. **`/graph` 未启用**：`.env.*` 里 `VITE_CONFIG_SHOW_GRAPH=false`，前端不显示图谱入口；契约里 Nebula 也说 R12 不启用 — 一致，仅登记。
2. **网关未起时的状态码**：vite 返回 500（非 502），验收脚本别按 502 写断言。
3. **`git diff --stat` 为空**：`frontend/plateform/` 整体 untracked。若需要可审计 diff，建议 TL 决定是否 `git add` 前端目录（我未执行任何 `git add`）。
4. **`yarn.lock` 在本机 mtime 变为 01:28**（正好在 install 窗口内），内容比 `r12-src/ai-plateform` 少 439 行且缺 `resolved`/`integrity` 字段。**我没有编辑过它**，也无法确认是谁/什么改的（npm 正常不改 yarn.lock）。如需干净基线可从 `r12-src/ai-plateform/yarn.lock` 回退 —— 请 TL 裁定，我未擅自恢复。
5. **生产部署（nginx 18088）未做**：本任务只要求 dev server + dist 产出；`default.conf`/`nginx/` 未改，若要走 18088 需另行分配。
6. **`--legacy-peer-deps` 的隐患**：peer 冲突被静默跳过，若后续出现 React 版本相关的运行时白屏，优先怀疑此项。
7. **构建耗时/资源**：install 6m + build 7m + legacy 产物（legacy chunk 体积约为 modern 的 1.2 倍）；`dist` 128M 主要来自 `vendor-*` 全量切分，未做优化（任务未要求）。

## 11. 复现命令

```
cd /home/szf/data/dev/llmke-r12/frontend/plateform
npm install --legacy-peer-deps --registry=https://mirrors.tencent.com/npm/     # 6m
npm run build                                                                  # 7m1s → dist/
mkdir -p ../../platform/r12/logs ../../platform/r12/run
nohup npm run dev > ../../platform/r12/logs/fe-dev.log 2>&1 &
echo $! > ../../platform/r12/run/fe-dev.pid
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:15174/            # 200
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:15174/proxy/auth/user/kaptcha  # 500（网关未起）
```

日志与 PID：
- `platform/r12/logs/fe-npm-install.log`
- `platform/r12/logs/fe-build.log`（成功）、`platform/r12/logs/fe-build.attempt1.log`（首次失败，已保留）
- `platform/r12/logs/fe-dev.log`
- `platform/r12/run/fe-dev.pid`

---

# 第二批交付（TL 三项裁定 + 任务 A/B）

## 12. 裁定执行记录

**裁定 3 条全部按指示执行：**

| 裁定 | 执行情况 |
|---|---|
| ①git add 由 TL 做 | 未执行任何 `git add`；`frontend/plateform/` 仍为 untracked |
| ②yarn.lock 回退 | **已执行**：`cp /home/szf/data/dev/r12-src/ai-plateform/yarn.lock → frontend/plateform/yarn.lock`；回退后两侧 md5 一致 `e18dea8c618b389d6319aa9b7e45956c`（字节一致，12740→13179 行恢复）；`package-lock.json` 按指示**保留**作安装留痕 |
| ③CSS 告警不改源码 | 未改任何 tailwind/KaTeX/less 源码；影响面写入 §15 |

**未做（按裁定 C）**：未清理 `vite.config.ts.timestamp-*.mjs` 等原工程残留文件，全部保持原样。

## 13. 任务 A：生产构建产物部署到 nginx（18088）

| 项 | 值 |
|---|---|
| 容器名 | `r12-fe` |
| 镜像 | `nginx:alpine`（**本机已有**，image id `1b595815db66`，69MB，7 周前拉取，未联网） |
| 容器 ID | `c270b9fb959a04f9b1f97d4140faa5aea0984ee6d2f0947fbf62693cf662dd3e` |
| 宿主 PID（容器内 nginx master） | **4026697** → 已写 `platform/r12/run/fe-nginx.pid` |
| 监听 | `*:18088`（`--network host`，因此可直接访问宿主 `127.0.0.1:8088`/`19000`） |
| 80 端口 | **未占用**（仍归既有 WeKnora） |
| 配置文件 | `frontend/plateform/nginx/r12-18088.conf`（新增文件，位于我的独占目录 `frontend/plateform/**` 内，未写 `platform/r12/**`） |
| 静态根 | 容器 `/usr/share/nginx/html/rag` ← 宿主 `frontend/plateform/dist`（`:ro` 只读挂载） |

启动命令（原样可复现）：

```
cd /home/szf/data/dev/llmke-r12/frontend/plateform
docker rm -f r12-fe
docker run -d --name r12-fe --network host \
  -v /home/szf/data/dev/llmke-r12/frontend/plateform/dist:/usr/share/nginx/html/rag:ro \
  -v /home/szf/data/dev/llmke-r12/frontend/plateform/nginx/r12-18088.conf:/etc/nginx/conf.d/default.conf:ro \
  nginx:alpine
docker exec r12-fe nginx -t      # syntax is ok / test is successful
```

停止：`docker rm -f r12-fe`

反代映射（与 `default.conf` 同构，仅上游换本机）：

| nginx location | proxy_pass | 与原 default.conf 的差异 |
|---|---|---|
| `/` | `try_files $uri $uri/ /index.html`（root=dist） | 原为 `error_page 404 /index.html`，语义等价 |
| `/proxy/` | `http://127.0.0.1:8088/` | 原 `10.15.12.13:8888` |
| `/cecProxy/` | `http://127.0.0.1:8088/` | 同上 |
| `/auth/` | `http://127.0.0.1:8088/auth/` | 同上 |
| `/index/` | `http://127.0.0.1:8088/index/` | 新增（原工程未单列，R12 前端会直连该前缀） |
| `/qa/` | `http://127.0.0.1:8088/qa/` | 新增；并加 `X-Accel-Buffering: no` 防 SSE 被缓冲 |
| `/sensitive/` | `http://127.0.0.1:8088/sensitive/` | 新增 |
| `/graph/` | `http://127.0.0.1:8088/graph/` | 新增（前端 `VITE_CONFIG_SHOW_GRAPH=false` 未启用） |
| `/minio/` | `http://127.0.0.1:19000/` | 原 `10.15.12.13:9000` |

`client_max_body_size 50m`、`proxy_buffering off`、`proxy_http_version 1.1`、`proxy_set_header Connection ""`、`proxy_read_timeout 180s` 均照搬原配置。

### 验证结果（实测）

| 请求 | 结果 |
|---|---|
| `curl -I http://127.0.0.1:18088/` | **HTTP/1.1 200 OK**，`Server: nginx/1.31.5`，`Content-Length: 23076`（即 dist/index.html） |
| `curl http://127.0.0.1:18088/proxy/auth/user/kaptcha` | **200** `image/jpeg`（网关已起，不再是 500） |
| `curl http://127.0.0.1:18088/auth/user/kaptcha` | **200** `image/jpeg` |
| `curl http://127.0.0.1:18088/login` | **200** `text/html`（SPA fallback 生效） |
| `/assets/index-6OoyH1eC.js` | 200 `application/javascript` 311950 B |
| `/assets/vendor-antd-DNTXxy0A.js` | 200 `application/javascript` 939019 B |
| `/worker/pdf.worker.min.js` | 200 `application/javascript` 1066108 B |
| `/cmaps/Adobe-Japan1-UCS2.bcmap` | 200 `application/octet-stream` 40951 B |
| `/proxy/index/knowledgeBase/list?pageNo=1&pageSize=1`（无 token） | **401** `application/json`（鉴权链真实生效，非 500） |
| `/minio/` | **403** `application/xml`（MinIO 拒绝列 bucket，链路通） |

## 14. 任务 B：三段连通验证（前端 → 网关 → 后端）

1. **网关已起**：`GET http://127.0.0.1:8088/auth/user/kaptcha` → 200 `image/jpeg`（首轮的 500 已消失）。
2. **登录拿到真实 token**：`python3 platform/r12/qa/r12_client.py` 输出 `token: eyJhbGciOiJIUzI1NiIsInR5...` / `user: admin` / `menus: 200` / `kb list: 200`。
3. **带 token 打真数据**（token 由同一 AES 登录链取得，未写进本文档，仅落 `/tmp/r12_token` 600 权限）：

| 入口 | 接口 | 结果 |
|---|---|---|
| nginx **18088** `/proxy` | `GET /auth/resource/getMenusByUser` | **200** `success=true`，`data` 为 list，**长度 7** |
| nginx **18088** `/proxy` | `GET /auth/user/getUserInfo` | **200** `success=true`，`data` 为 dict，**20 个字段** |
| dev **15174** `/proxy` | 同上两个接口 | 结果与 18088 **完全一致**（200 / list 7 / dict 20） |
| nginx 18088 `/proxy`（无 token） | `getMenusByUser` | **401**（反向证明鉴权未被绕过） |

**结论（事实）**：dist 静态资源 → nginx 18088 → `/proxy` 反代本机网关 8088 → 网关鉴权 → rag-auth-service 返回真实菜单（7 条）与用户信息（20 字段）；dev 15174 的 vite proxy 同样通过。**三段连通成立**，数据非 mock。按要求未做 UI 断言。

## 15. 构建告警影响面（TL 裁定：记为已知问题，不改源码）

### 15.1 `[vite:css] Parse error` × 12 —— 同一处，均来自第三方 CSS

- 来源文件：`node_modules/@mxmweb/fv/assets/style.css`（Radix Themes 的 leading-trim 工具类），由 `src/components/FileViewCec/index.tsx`、`src/components/AiEditor/components/FileView/index.tsx`、`src/components/AiEditor/components/FileViewNew/index.tsx`、`src/components/FileView3/index.tsx`、`src/components/KnowledgeBaseZh/KnowledgeAnalyBlock/index.tsx`、`KnowledgeAnalyGraph/index.tsx` 这几处 `import "@mxmweb/fv/style.css"` 重复引入，现代产物+legacy 产物各算一遍 → 合计 12 条。
- 报错声明（源文件原文）：
  `.rt-r-lt-start:before,.rt-r-lt-both:before{ margin-bottom: calc(var(--leading-trim-start, var(--default-leading-trim-start)) - var(--line-height, calc(1em * var(--default-line-height))) / 2) }`
  less 解析器不接受 calc 内的 `/ 2` 写法（`got unexpected "RPAREN"`）。
- **实测后果：规则没有被丢弃**。产物 `dist/assets/vendor-@mxmweb/fv-C3-pONuY.css` 内该条 `margin-bottom:calc(... / 2)` 文本与源一致；`rt-r-lt` 类名在 `dist/assets/vendor-@mxmweb/fv-MYo-RXRa.js` 与 legacy 版中均存在（组件确实用到）。
- 影响面（**仅**）：文件预览器里使用 `rt-r-lt-start` / `rt-r-lt-both` 的文本块，其 `::before` 的 leading-trim 垂直微调（约半个行高）。
  - 页面：知识库-文档预览、知识分析块 / 知识图谱页、写作编辑器内的附件预览、FileViewCec 预览
  - 元素：这些预览器中的**标题/正文首行**的垂直居中（上下留白是否均匀）
- 判定：低风险（规则文本在、类名在、无布局塌陷证据）。若 QA 真看到半行偏移再回来评估。

### 15.2 `... didn't resolve at build time` × 61 —— 2 类

| 类别 | 条数 | 出处 | 运行时影响 |
|---|---|---|---|
| KaTeX 字体（20 个字重 × woff2/woff/ttf） | 60 | `dist/assets/vendor-@gientech/modual-*.css` 里 `url(fonts/KaTeX_*)` | 请求会落到 `/assets/fonts/...`（dist 里没有该目录）→ **公式字体 404，KaTeX 回落系统字体**（字形/基线略变，公式仍能显示，不影响功能）。页面：写作 / 文档编辑 / AI 编辑器里含公式的文档 |
| `../../../../../assets/setting/setting_file_icon.svg` | 1 | `src/pages/HomePage/IntelligentChat/Setting/SelectBox/styles.less:2`、`src/components/Template/components/SelectBox/styles.less:2`（相对路径多越一级，越出 `src/`） | **SelectBox 的文件图标背景 404**（缺图标/空白，不影响布局）。页面：会话设置页、模板页的下拉选择框。注：`Setting/style.less:135` 用 4 级路径，是正常的 |

### 15.3 其余噪声（无功能影响）

74 条 `Generated an empty chunk`（manualChunks 按包名切分产生空块）、2 条 `chunks larger than 500 kB`（`vendor-@gientech/modual` 6.9M / legacy 8.2M）、1 条 browserslist 数据 10 个月旧。

### 15.4 建议 QA 浏览器验收盯这 3 处（可直接转发）

1. 文档预览 / 知识分析 / 写作附件预览：首行是否出现半行垂直偏移（§15.1）
2. 含公式的文档：公式字形是否回落为系统字体（§15.2 类 1）
3. 会话设置页 + 模板页的选择框：文件图标是否空白/破图（§15.2 类 2）
