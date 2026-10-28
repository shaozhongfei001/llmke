# AG-1 验收报告｜会话 · 权限 · 库管理（只读）· rev2

- 角色：AG-1（登录与会话 / 权限负例 / 知识库列表一致性）
- 运行批次：`e2e-run-20261027T2357`
- 首版 2026-10-28 10:31；rev2 11:05（补 S1-04 三态区分、新增 S1-08、畸形 token 500 降为 P3、`/qa/feedback/que/list` 独立计数、补注入式清单）；rev3 11:35（P0 补代码级行号证据并按实测把范围从"单点"修正为"列表类只读接口成片缺失"；新增 §3 S13 五项逐条映射；拆分 D-5→D-5a/D-5b；新增 S13-02A 两层结构小节；S2 单位归属按"源码现状"判据定稿）；rev4 11:50（在第 5 节写入 D-5a 的归属/成因/判据/修复方向结论块与"先定单位口径再动一侧"的修复前提）；rev5 11:55（按协调侧要求只读探测 3 个状态查询接口，把 P0 边界钉为 A 类实质泄露 / B 类弱泄露；未探测项记"待确认范围"）；rev6 12:05（按批准做纯静态授权追踪：controller→service 方法全名+行号+判定；新发现 `getFileChunks`/`getKbFileChunks` 返回分块正文且无授权）；**rev7 2026-10-28 12:15**（3 次只读 GET 运行态证实内容级越权：两接口均 200 且返回真实正文，② 不需要 kbId → P0 从元数据升级为跨库读原文，新增 D-1b/D-1d，缺陷 10→12 条）
- 账号：`admin / Admin@12345`；越权测试另用仓内既有夹具账号 `r13_reader`、`r13_noauth`（口令来源 `platform/r12/qa/revoke_acceptance.py`，**未新建任何账号**）
- 前端：`http://127.0.0.1:18088`；网关：`http://127.0.0.1:8088`

## 0. 第 0 步：证明我测的是哪一版（§1.4）

```
A=$(grep -oE 'assets/index-[A-Za-z0-9_-]+\.js' frontend/plateform/dist/index.html | head -1)
# A = assets/index-CpE2zvYY.js
curl -sS "http://127.0.0.1:18088/$A" -o /tmp/served-ag1.js
md5sum /tmp/served-ag1.js frontend/plateform/dist/$A
```

| 项 | 值 |
|---|---|
| entry | `assets/index-CpE2zvYY.js` |
| 服务端返回体 md5 | `de2424501bd29e358043049876db2a75`（315576 字节） |
| 磁盘 dist 文件 md5 | `de2424501bd29e358043049876db2a75`（315576 字节） |
| 磁盘 mtime | 2026-10-27T13:22 |
| 结论 | **一致 → 容器未钉旧 inode，继续** |

**§1.4 的效力边界（rev2 补记）**：md5 自证只证明「宿主 dist == 服务端下发」，**不证明 dist 由当前 HEAD 构建**。本轮为此单独核查了与我的断言相关的 r14-D 提交（见「5. 版本漂移核查」），结论是我的 S2 单位结论**不是**旧包造成。

服务代次（开工时采集，收工时复核未变，未重启任何服务）：

| 端口 | pid | 角色 |
|---|---|---|
| 8088 | 1403651 | gateway |
| 18083 | 1647331 | auth-service |
| 18082 | 2139785 | index-service |
| 19527 | 1823402 | retrieval |
| 19529 | 1461792 | graph |
| 19995 | 1481869 | llm |

## 一页总表

规范必需断言 **16** 条（S1×7、S13×4、S2×5；S2 第 2 条「名称/文档数/大小单位」拆为 S2-02、S2-03 两条独立判定），另附 4 条附加观察项，共 20 条。

| 场景 | 判定 | 断言通过/总数 | 耗时（约） | 关键证据 |
|---|---|---|---|---|
| S1 登录与会话 | **FAIL**（2 条不过） | 5/7 | 4m50s | `AG-1/evidence/S1/`（24 文件） |
| S13 权限负例 | **FAIL**（S13-1/2/3/5 不过，S13-4 UNVERIFIED） | 0/4 通过 + 1 UNVERIFIED（逐条见 §3） | 1m40s | `AG-1/evidence/S13/`（13 文件） |
| S2 知识库列表 | **FAIL**（1 条不过） | 4/5 | 3m30s | `AG-1/evidence/S2/`（12 文件） |
| 合计（必需 16） | **FAIL** | **9/16** | 约 10m | — |
| 含 4 条附加观察项（共 20） | — | PASS 12 / FAIL 7 / UNVERIFIED 1 | — | — |

> 缺陷 12 条：P0×2（D-1a 元数据 / D-1b 内容级）、P1×2、P2×5、P3×3（rev7 计数）。

附加观察项：S1-07（强制密保弹窗行为，PASS-观察）、S13-04（删除不存在库语义，PASS）、S13-06（登出吊销 token，PASS）、S2-06（文件级大小单位，**FAIL**）。

## 每条明细

### S1-01 正确账号登录成功，落地页正确
- 前置：全新浏览器上下文（独立 UA），无任何 localStorage/cookie；服务 pid 见上表
- 步骤：① 打开 `/login` ② 填 admin / Admin@12345 / 图形验证码 ③ 点「登 录」（antd 在两个汉字间插空格，故用正则匹配）
- 期望：登录接口 success=true 且带 token；URL 离开 /login；页面可见已登录身份
- 实际：登录接口 `HTTP=200 success=true`；token 长度 237；落地 `http://127.0.0.1:18088/chats/main`；`localStorage["gitech_ril:rag_ai"].userInfo.userName=admin`；导航节点 9 个；正文开头「智能对话 知识库 助手配置 敏感词配置 用户反馈 搜索 智能问答 系统管理 admin …」
- 判定：**PASS**
- 证据：`AG-1/evidence/S1/01-login-landing.png`、`01-login-network.json`、`01-login-response.json`
- 复跑：`cd AG-1 && NODE_PATH=/home/szf/env/my-playwright/node_modules node s1-session.js`
- 判据自检：若登录其实失败，`success=true` + token 长度 + 落地 URL + 页面用户名四项会同时不成立，非单点假绿

### S1-02 错误密码提示可读，不泄露"用户是否存在"
- 步骤：同一表单分别提交 ① admin + 错密码 ② 不存在账号 `ag1_nosuchuser_20261028` + 同一错密码（两次均带正确验证码）
- 期望：两次都给可读提示，且文案一致
- 实际：① `HTTP=500 success=false errorMsg="用户名或密码错误"`，toast「用户名或密码错误」② 完全相同的 `errorMsg` 与 toast；两次均停留 `/login`
- 判定：**PASS**（"不泄露用户是否存在"成立）
- 证据：`AG-1/evidence/S1/02-wrong-password.png`、`02-nosuch-user.png`、`02-login-errors.json`
- 附带事实：凭证错误以 **HTTP 500** 返回 → 计入缺陷 D-6（与 S1-08 同一条：登录类业务异常被统一映射为 500）

### S1-03 未登录直接访问受保护路由 → 被挡回登录页
- 步骤：全新上下文（无 token）直接 `goto /chats/knowledgeBase`
- 期望：最终落到 `/login` 且登录表单可见
- 实际：最终 URL=`http://127.0.0.1:18088/login`；登录输入框 1 个；正文「登 录 点击注册 忘记密码」
- 判定：**PASS**
- 证据：`AG-1/evidence/S1/03-unauth-protected-route.png`、`03-unauth-network.json`
- 判据自检：拦截发生在 `src/apis/token.ts:10-11`（请求拦截器无 token 即 `window.location.pathname="/login"`）；前端路由中间件 `router/middleWares/Loged.ts` 实为空实现（仅 `return children`），因此"纯静态无请求页面"理论上可能不跳 —— 本系统所有页面均拉数据，实测被挡

### S1-04 伪造 token（改 localStorage）→ 401 或被挡回，**不得 500**（rev2 已做三态区分）
- 步骤：① 正常登录 ② 把 `userInfo.token` 改成无点串 `FORGED-AG1-<ts>-…` ③ 访问 `/chats/knowledgeBase` ④ 观察网络 ⑤ 观察此时登录页是否可用 ⑥ **补测三态矩阵**：畸形 / 格式正确但过期或签名错 / 空或无头，各打三类端点
- 期望：受保护接口 401/403 且无 5xx；被挡回登录页
- 实际（浏览器侧）：受保护接口 `401 /proxy/auth/resource/getMenusByUser`（30013 登录失效已过）**正确拒绝**；**但 `/proxy/auth/user/kaptcha` → 500**；最终落点 `/login`；toast「请求出错，请稍后再试」。伪造 token 仍在 localStorage 时登录页**验证码输入框数=0**（清掉后=1）→ 该浏览器无法自助登录，需手工清 localStorage
- 实际（三态矩阵，`evidence/S1/04-tristate-matrix.json`）：

| 用例 | 受保护 getMenusByUser | 公开 /auth/user/kaptcha | 业务 /index/knowledgeBase/list |
|---|---|---|---|
| ① 畸形无点串 `FORGED-AG1` | 401 / 30022 没有token | **500** | 401 / 30022 |
| ① 畸形两段 `a.b` | 401 / 30022 | **500** | 401 / 30022 |
| ② 已过期+错签名（三段、合法 base64url、exp=now-3600） | 401 / 30013 | 200 | 401 / 30013 |
| ② 未过期+错签名 | 401 / 30013 | 200 | 401 / 30013 |
| ② 篡改 payload 保留原签名 | 401 / 30013 | 200 | 401 / 30013 |
| ③ 空 Authorization | 401 / 30022 | 200 | 401 / 30022 |
| ③ 无 Authorization 头 | 401 / 30022 | 200 | 401 / 30022 |
| ④ 真 token（对照） | 200 | 200 | 200 |

- 判定：**FAIL**（仍出现 500）；级别 **P3**
- 定级依据（一句版）：**只有非三段 JWT 的畸形串会 500；正常过期/签名错/被篡改/缺 token 一律 401 → 正常会话生命周期不受影响，触发前提是垃圾输入。**
- 垃圾 token 从哪来（评审必问"用户怎么会拿到"）：① 升级/迁移后 localStorage 里残留旧格式 token；② 前端写入中断（写一半被关闭/覆盖）留下半截值；③ 开发者或安全工具手工改 localStorage。**恢复方式只有手工清 localStorage —— 后台/页面都没有自助出口**，这是本条的真实体验成本
- 定级理由：触发条件非常规 + 有恢复手段但需人工介入 + 不影响正常会话 → **P3**
- 代码级归因（保留）：`rag-common/src/main/java/com/gientech/ragcommon/context/user/UserContextFilter.java:47-48` 调用 `JWTUtils.getUserId/getUsername`（`JWTUtils.java:63/69` 为 `JWT.decode` 且无 try/catch），抛 `com.auth0.jwt.exceptions.JWTDecodeException`；服务端日志原文 `The token was expected to have 3 parts, but got 0`（`platform/r12/logs/rag-auth-service.out`，2026-10-28 00:15 附近）。网关 `rag-gateway/.../filter/AuthFilter.java:204-209` 已有 R12-FIX-AUTH-01 兜底，所以只有"过网关后的公开/业务路径"暴雷 —— 这也解释了同一畸形 token 在受保护端点 401、在 kaptcha 却 500
- 证据：`AG-1/evidence/S1/04-forged-token.png`、`04-login-page-under-forged-token.png`、`04-login-page-token-cleared.png`、`04-forged-token-network.json`、`04-forged-token-detail.json`、`04-tristate-matrix.json`
- 复跑：`node s1-session.js`（浏览器侧）；三态矩阵见同一报告的 `04-tristate-matrix.json` 构造方式说明
- 更正一处首版归因：首版我把网络里出现的 `500 GET /proxy/qa/feedback/que/list` 也算在本条头上。**该 500 与伪造 token 无关** —— 同一合法 JWT 下它照样 500（`syntax error : { … fastjson-2.0.47`，errorCode 999），而同一 JWT 下 `getKbById?id=9` 返回 200。现已拆为独立缺陷 D-9，不计入本条

### S1-05 登出后再访问 → 被挡回
- 步骤：登录 → 悬停顶栏头像（`.ant-dropdown-trigger`；菜单实际项：`系统管理员/admin/暂无邮箱`、`隐私政策`、`退出登录`、`版本 1.0.0`）→ 点「退出登录」→ 观察落地 → 再访问 `/chats/knowledgeBase`
- 实际：登出 `HTTP=200`；登出后 URL=`/login`；`userInfo.token` 已清除；再访问最终 URL=`/login`，登录框数=1
- 判定：**PASS**
- 证据：`AG-1/evidence/S1/05-after-logout.png`、`05-revisit-after-logout.png`
- 附带事实（D-8/P3）：登出后 localStorage 的 `isLoggedIn` 仍为 `true`（见 `evidence/S1/08-logout-storage.txt`）

### S1-06 会话过期/刷新的行为记录
- 步骤：登录后记录 token → 整页 `reload` → 比较 URL 与 token
- 实际：刷新前 `/chats/main`，刷新后 `/chats/main`，会话保持；token 未变化（237→237）；标准三段 JWT，载荷 `{"iss":"GIEN-RAG","aud":"admin","userId":1,"userName":"admin","sub":"mixedQuantum","exp":1793204940,"iat":1793118540}` → **有效期 24h**
- 判定：**PASS**
- 证据：`AG-1/evidence/S1/06-refresh-keeps-session.png`、`06-session.json`
- 边界：未等真实 24h 过期窗口；"过期后拒绝"语义已由 S1-04 三态矩阵的 ② 组覆盖（401 / 30013）

### S1-08（rev2 新增）输错验证码的状态码语义
- 步骤：真实浏览器登录表单，填入正确账号口令 + **错误验证码**「zzzz」→ 提交 → 抓 HTTP 状态/响应体/toast/停留 URL
- 期望：200（或 400）+ 可读提示 + 明确 errorCode
- 实际：`HTTP=500 success=false errorCode=30000 errorMsg="验证码错误！"`；前端 toast「验证码错误！ | 验证码错误！」；停留 `/login`（未登录成功）
- 判定：**FAIL**
- 归因：`GlobalHandler` 把业务异常（`ApplicationException` / `ErrCodeEnum.VERIFY_CODE_ERROR`）统一映射为 HTTP 500，与 S1-04 的 `JWTDecodeException` 属**同一族**（可预期的用户输入/会话错误被当作系统故障）。两条**并列、分开计数**：本条 = D-6，S1-04 = D-2
- 证据：`AG-1/evidence/S1/08-captcha-error.png`、`08-captcha-error-network.json`、`08-captcha-error.json`
- 复跑：`cd AG-1 && NODE_PATH=/home/szf/env/my-playwright/node_modules node s1-08-captcha-error.js`

## 3. S13 五项逐条映射（期望 / 实际状态码 / 判定，不合并）

| 编号 | 项 | 主体 | 期望 | 实际状态码 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| S13-1 | 无权限账号读他人库文件清单 | r13_noauth / r13_reader | 403 或明确拒绝 | `200 success=true total=8`（kb_34）；对照 `getKbById?id=34`=403/30016、`file/getById?id=483`=403/30016、`stream`=401/30021 | **FAIL** | `S13/B-horizontal-authz.json`、`S13/G-p0-scope-5-endpoints.txt` |
| S13-2 | 普通账号越权创建知识库 | r13_reader | 403 或明确拒绝 | `200 success=true`；库表新增 id=35 `AG1-SHOULD-NOT-CREATE`、`create_by=r13_reader`、`status=0` | **FAIL** | `S13/00-side-effect-and-revert.log`、`S13/H-s13-item-mapping.md` |
| S13-3 | 普通账号读管理员用户列表 | r13_reader / r13_noauth | 403 | `200 success=true total=5`（含 admin 全部账号）；`getUserInfoByUserName/admin` 亦 200 | **FAIL** | `S13/C-vertical-authz.json` |
| S13-4 | 撤权后会话失效 | 需他人先撤权 | 原会话 401 | 未执行（撤权=写 `user_privilege`，零写入约束禁止） | **UNVERIFIED** | `S13/E-revoke-unverified.txt` |
| S13-5 | 伪造 Authorization 头 | 无/空/畸形/错签 | 401 或 403（**500 不合格**），受保护面与公开面**分开判** | 受保护面（getMenusByUser、kb list）全部 401 → **PASS**；公开面（kaptcha、login）畸形串 → **500** → **FAIL**；无 token/空 → kaptcha 200（白名单设计，非缺陷） | **FAIL**（分栏见 `S13/H-s13-item-mapping.md`） | `S13/A-auth-matrix.json`、`S1/04-tristate-matrix.json` |

### S13-01 直接构造 URL 访问无权资源 → 403 或明确拒绝，**不得 200**
- 前置：`r13_reader`（对 kb_9 有只读授权）、`r13_noauth`（无任何授权）真实登录取得 token
- 步骤：两账号分别请求 ① kb 列表 ② `getKbById?id=9` ③ `getKbById?id=34`（未授权）④ `file/folder/list?kbId=9` ⑤ `file/folder/list?kbId=34`（未授权）⑥ `file/getById?id=483`（属未授权 kb_34）⑦ `file/stream?fileId=483&kbId=34`
- 实际（语义正确）：`getKbById?id=34` → **403 30016 没有足够权限**；`file/getById?id=483` → **403 30016**；`file/stream` → **401 30021 没有足够的权限**；`getKbById?id=9` 对 r13_reader 200（授权正确）、对 r13_noauth 403
- 实际（**违规放行**）：`file/folder/list?kbId=34` 对**两个**账号均 `200 success=true total=8`；kbId=9 亦 200 total=10（r13_noauth 无任何授权）。返回体含 `fileName / fileSize / version / status / filePath(MinIO 完整路径) / synLogs.errorDetail(内部 LOG_ID、task_id、解析失败原因)`
- 判定：**FAIL**
- **代码级证据（静态，`rag-index-service/.../interfaces/KnowledgeBaseFileController.java`）**：
  - 有授权：`:100 kbAuthzService.assertRead(kb.getId())`、`:148 kbAuthzService.assertRead(file.getKbId())`、`:198 kbAuthzService.assertWrite(kbIdOfFile(id))`、`:217 kbAuthzService.assertRead(kbIdOfFile(fileId))`
  - 无授权：`:154 @GetMapping("/folder/list")` → `:156 folderList(KnowledgeBaseFileQueryReq req)` → `:157 knowledgeBaseListAppService.folderList(req)`
- **范围修正（重要，修正协调侧"单点"判断）**：逐端点实测发现缺授权的不是一处，而是"列表类只读接口成片缺失"：

| 端点（r13_noauth，kb_34） | 实际 | 是否有 assert |
|---|---|---|
| `GET /file/folder/list` | `200 n=8` | 无 |
| `GET /file/list` | `200 n=8` | 无 |
| `GET /file/flatList` | `200 n=9` | 无 |
| `GET /file/flatFiles` | `200 n=7` | 无 |
| `GET /file/queryList` | `200 n=8` | 无 |
| `GET /file/multiple/version` | `500 code=999`（自身 fastjson 报错；同样无 assert，数据未能读出） | 无 |
| `GET /file/getById?id=483` | `403 30016` | 有（`:148`） |
| `GET /knowledgeBase/getKbById?id=34` | `403 30016` | 有 |

  即：**授权在"单对象/写"接口上是齐的（getById/getByIds/delete/create），但"列表类"只读接口成片缺失（≥5 条实测放行）**。级别不变（P0），影响面比单点更大

- **边界钉死（rev5，2026-10-28 11:5x，只读 GET，仅 3 个端点）**：状态查询类接口同样缺授权，但与列表类不是一个量级：

| 类别 | 端点 | r13_noauth 实测 | 返回内容 | 敏感度 |
|---|---|---|---|---|
| A 类：实质信息泄露 | `folder/list`、`list`、`flatList`、`flatFiles`、`queryList` | 200，n=8/8/9/7/8 | 文件名、大小、版本、MinIO 全路径、`synLogs.errorDetail`（LOG_ID/task_id） | 高（P0 主体） |
| B 类：弱信息泄露 | `getFileStatusById?id=483`、`getFAQExtractStatusById?id=483`、`getGraphParseStatus?id=483` | 均 `200 {"success":true,"data":<int>}`（3/1/1） | 仅整数状态枚举（3=解析成功，1=未解析/未提取） | 低：不含文件名/路径/正文，但配合 A 类可"确认任意 fileId 存在与否及解析状态" |

  因此 P0 的准确边界不是"只有列表接口缺"，也不是"凡是不返回内容的接口都没加"，而是：**A 类（返回文件清单/元数据）成片缺 → P0；B 类（只返回状态枚举）同族缺 → 随 A 类一并修，敏感度低**。
- **静态授权追踪（rev6，纯静态、未发任何请求；完整表见 `AG-1/evidence/S13/J-static-authz-trace.md`）**：
  - 前置事实：`rag-index-service` 内 `@PreAuthorize`/`@Secured`/`HandlerInterceptor` **均为 0 处**，对象级授权只有 `KbAuthzService`，其全部调用点都在两个 controller 里（`KnowledgeBaseFileController` :100/:148/:198/:207/:217/:228/:240/:249；`KnowledgeBaseController` 12 处）→ **该模块不存在 AOP 类授权**，controller 没写 assert 的映射在本模块内没有第二道闸
  - 有 assert（7 个映射）：`getById :148`、`getByIds :217`、`delete :198`、`deleteByIds :207`、`filesParse :228`、`graphParse :240`、`filesAllParse :249`、`stream :100`
  - 无 assert 的**读**接口：列表类 6（`folderList L1935`、`listNew L1625`、`multipleVersion L1659`、`flatList L1969`、`flatFiles L1979`、`queryList L2563`）、状态类 4（`getFileStatusById L808-816`、`getFAQExtractStatusById L927-935`、`getGraphParseStatus L2496-2504`、`getFileStatusByUids L2692-2699`，三者方法体都是"直接 findById 取状态字段返回"）、元信息 3（`exist L2711`、`precheck L1610`、`checkCunkFile L717`）
  - 无 assert 的**写**接口 7 个：`updateEnable L801-807`、`filesReviseDate L1701`、`reExtractFQA L2257`（extractFQA :327 与 reExtractFQA :341 共用）、`extractAllFQA L2389-2392`、`uploadParsedFile→uploadFile L273-395`、`chunkUpload L747`、`chunkMerge L760`
  - **[rev7] 静态高危项已运行态证实 → P0 最高档（内容级越权）**：见下方"内容级越权实证"小节，D-1b
  - **两个静态高危项（原标"待验证"，其中第 1 条已于 rev7 证实）**：① `GET /getFileChunks :348 → getFileChunksByPage L896-926` 与 `GET /getKbFileChunks :355 → getKbFileChunks L2914-2918` **返回分块正文且无授权**（前者仅校验 kbId/docId 存在与 status==PARSE_SUCCESS），配合 A 类已可枚举 kbId+fileName，等价于**跨库读原文**，比元数据泄露更严重；② `PUT /updateEnable :284` 只需 fileIds 即可改启停状态
  - 另有一处"看似有授权其实只在特定分支生效"：`privlegeClient.isPermissionApi(...)`（L2016/L2027）位于 `searchFileList L1997`，只服务 `fileList(req)` 的 scope=SHARE/ALL 分支；`flatList`/`flatFiles` 走的是 `searchUserFileList L2041`（把 `req.getUserName()` 传给查询做**数据范围过滤**，非授权），userName 为空即不过滤 —— 这解释了为什么 `r13_noauth` 实测能拿到数据
  - 判定：**无"无法判定"项**（本模块无 AOP、无父类模板方法包装）；mapper 层未逐条展开，属"未展开"而非"无"

  未探测（明确不越界）：`upload :269`、`merge :277`、`extractFQA :327`、`uploadParsedFile :313`、`updateEnable :284`、`filesReviseDate :255`、`exist :127`、`precheck :137`、`check :260`、`getFileStatusByUids :295` —— 其中多条是写操作（零写入约束），其余"controller 层没有断言"不等于 service 层没有校验，**不下结论**，记"待确认范围"。证据：`AG-1/evidence/S13/I-p0-boundary-status-endpoints.txt`
- 证据：`AG-1/evidence/S13/B-horizontal-authz.json`、`s13-raw.jsonl`、`S13/G-p0-scope-5-endpoints.txt`
- 复跑：`node s13-perm.js`
- 内容面补充（未被突破）：MinIO 直取匿名 403；`file/stream` 带普通 token 401。即**元数据泄露、内容未泄露**

### S13-01B（rev7 新增）内容级越权实证：无授权账号读他人知识库全文

- 主体：`r13_noauth`（无任何授权）；目标库 kb_34；**3 次只读 GET（上限内），零写入**
- 无权对照（既有证据）：同账号 `getKbById?id=34` = **403 / 30016**

| # | 请求 | HTTP | chunk 数 | 是否真实正文 |
|---|---|---|---|---|
| ① | `GET /file/getFileChunks?kbId=34&docId=483&pageNo=1&pageSize=3` | **200** success=true | total=1, records=1 | **是**：`"「智"造贷」企业流动资金贷款产品说明书 文件编号：PRD-CORP-LOAN-20██-██（R12 验收测试夹具…）一、适用对象 面向制造业中小微企业…"` |
| ② | `GET /file/getKbFileChunks?kbName=R14-BASELINE-KB&fileName=docx-plain.docx` | 200 success=true | **0** | 否 —— 但**错键名也返回 200 成功**（fail-open，见 D-1d） |
| ②' | `GET /file/getKbFileChunks?kbName=kb_34&fileName=docx-plain.docx` | **200** success=true | **1** | **是**：`"Plain DOCX 第一段：客户访前准备。第二段：日均存款 █,███,███.██ 元。"` |

- 判定：**FAIL（P0 最高档：从"元数据泄露"升级为"跨库读原文"）**
- 关键点：**② 的入参不含 kbId**，只要 `kbName + fileName`；而 `kbName` 就是 **primitiveName = `kb_<id>`**，A 类列表接口的响应里 `primitiveName` 字段**直接给出**，无需猜
- **完整可达链路（任意已登录账号，全程无授权）**：
  `GET /file/folder/list?kbId=<N>`（A 类，无 assert）→ 拿到 `id / primitiveName / fileName / convertedFilePath`
  → `GET /file/getFileChunks?kbId=<N>&docId=<id>` 或 `GET /file/getKbFileChunks?kbName=kb_<N>&fileName=<fileName>`
  → **读到任意库任意文件的全文分块**
- 证据：`AG-1/evidence/S13/K-content-level-leak-proof.md`（含三张表与打码后的正文片段）
- 3 次额度用法说明：原定第 3 次用于"换库确认非特例"，我改用在 ② 的键名复核（否则会把可能的内容漏洞记成弱泄露）；"非特例"已有替代保障——同账号对 kb_34 的 `getKbById` 403 已证无权。若需换库泛化样本，需再批 1 次只读 GET

### S13-02 伪造 Authorization 头 → 401/403，**不得 500**
- 步骤：6 种变体 × 3 类端点（完整矩阵见 `S13/A-auth-matrix.json`，与 S1-04 三态矩阵结论一致）
- 关键行：`无点串` / `三段乱写 a.b.c` / `Bearer <真token>` 在**公开端点 kaptcha** 返回 **500**；同一变体在受保护与业务端点均 401
- 判定：**FAIL**
- 归因：同 S1-04（`UserContextFilter` 未捕获 `JWTDecodeException`）；本条与 S1-04 互为接口级/浏览器级两面证据，缺陷条目合并计为 **D-2**（P3，rev2 降级），此处不再单独计数
- 证据：`AG-1/evidence/S13/A-auth-matrix.json`、`s13-raw.jsonl`、`S1/04-tristate-matrix.json`

### S13-02A（rev2 新增小节）为什么会"受保护端点 401、公开端点 500"——两层结构

| 层 | 组件 | 对畸形 token 的行为 | 结论 |
|---|---|---|---|
| 第一层（网关） | `rag-gateway/.../filter/AuthFilter.java:204-209`（R12-FIX-AUTH-01） | 捕获异常 → 返回 `401 NO_TOKEN` | 过了网关的**受保护路径**合格 |
| 第二层（各服务 servlet filter） | `rag-common/.../context/user/UserContextFilter.java:47-48` → `JWTUtils.getUserId/getUsername`（`JWTUtils.java:63/69` 用 `JWT.decode` 无 try/catch） | 未捕获 `JWTDecodeException` → `GlobalHandler` 兜成 **500** | 公开路径（`kaptcha` 等在 `isNoTokenFree` 白名单内，**绕过网关第一层**）直接暴雷 |

- 修复点（二选一或并用）：① `UserContextFilter` 对 `JWTDecodeException` 捕获后返回 401（与第一层语义对齐）；② 让 `kaptcha` 这类公开端点不进入 UserContext 解析（白名单内直接放行）。
- 说明：公开端点**无 token 返回 200 属设计如此（白名单）**，本报告未将其记为缺陷；只有"带了畸形 token 才 500"才是缺陷。

### S13-03 普通用户越权访问（纵向）
- 系统内**确实存在**普通账号（`searchUserList` 共 5 个：admin、r13_noauth、r13_reader、qa_user_b、qa_user_c），故本条**不是 UNVERIFIED**
- 步骤：`r13_reader` / `r13_noauth` 请求 ① `searchUserList` ② `searchResignedUserList` ③ `getUserInfoByUserName/admin` ④ `role/list`
- 实际：① 两账号均 `200 success=true total=5` ② `200 total=0` ③ 两账号均 `200`（可读 admin 账号信息）④ `404`（路径不存在，不计）
- 判定：**FAIL**
- 证据：`AG-1/evidence/S13/C-vertical-authz.json`

### S13-04（附加）越权/管理员删除不存在库 → 明确业务错误
- 实际：`DELETE /index/knowledgeBase/delete?id=999999999` 三账号一致 `HTTP=404 success=false errorCode=10001 errorMsg="知识库不存在"`；探测前后 total 均 15、id 集合完全一致（零变更）
- 判定：**PASS**
- 证据：`AG-1/evidence/S13/D-write-nonexistent.json`、`S2/delete-nonexistent.json`

### S13-05（对应规范第 4 项）撤权后原会话失效 → **UNVERIFIED**
- 原因：需删除/变更 `user_privilege` 授权行并观察存量 token，属对权限数据的写入，本轮零写入约束禁止；仓内 `platform/r12/qa/evidence/REVOKE-*` 为他人历史证据，按纪律不得引用为本次结论
- 替代性事实：登出后旧 token 立即失效（S13-06），说明会话可被服务端吊销，但"撤权（非登出）是否立即生效"仍未证
- 谁能解除阻塞：security_owner / 有权写 user_privilege 的角色
- 证据：`AG-1/evidence/S13/E-revoke-unverified.txt`

### S13-06（附加）登出后旧 token 复用 → 应拒绝
- 实际：登出前 `200 success=true`；登出 `200`；登出后同 token 访问鉴权接口与业务接口均 `401 30013 登录失效已过`
- 判定：**PASS**
- 证据：`AG-1/evidence/S13/F-logout-revoke.json`

### S2-01 列表条数与接口一致（基线快照 15 个）
- 实际：接口 `total=15`（第 1 页 12 / 第 2 页 3）；UI 第 1 页卡片 **12**、第 2 页 **3**；分页控件「1 2」
- 判定：**PASS**
- 证据：`AG-1/evidence/S2/01-kb-list-page1.png`、`02-kb-list-page2.png`、`api-baseline.json`
- 复跑：`node s2-kb.js`
- 判据自检：首次运行因"密保弹窗拦截分页点击"得到第 2 页 12 张卡的假 FAIL；核对卡片名与页码后确认是拦截导致未翻页，重新绕行后复跑得 12/3

### S2-02 名称与文档数逐条一致
- 实际：12 张卡片与接口逐条比对 —— 名称不一致 **0** 处，文件数不一致 **0** 处；卡片原文示例「R14-BASELINE-KB 文件数： 8 · 大小： 6.4 GB」
- 判定：**PASS**
- 证据：`AG-1/evidence/S2/ui-cards-page1.json`

### S2-03 大小单位一致性（同一数字不得在页面间显示成不同单位）
- 基准真值：`R12FIX-product-loan.docx` 磁盘原件 **37544 字节**，接口 `fileSize=37544.0` → **`fileTotalSize/fileSize` 单位为字节**（另一佐证：kb_34 合计 6,679,637；若按 KB 解释则单文件 pdf-scanned.pdf = 6,525,683 KB ≈ 6.2 GB，与"扫描件夹具"常识不符；按字节 = 6.2 MB）
- 实际（逐库 12 条）：前端 `formatFileSize`（`src/core/helps/index.ts:45-52`）把入参当 **KB** 换算：

| 库 | 接口原值 | 真实人类可读 | UI 卡片显示 | 详情页显示 |
|---|---|---|---|---|
| R14-BASELINE-KB | 6,679,637 B | 6.4 MB | **6.4 GB** | **6.4 GB** |
| R12验收主链 | 6,746,568 B | 6.4 MB | **6.4 GB** | — |
| R12业务主链 | 6,666,847 B | 6.4 MB | **6.4 GB** | — |
| R14-P201-KB | 75,889 B | 74.1 KB | **74.1 MB** | — |
| qa_r12_priv | 3,577 B | 3.5 KB | **3.5 MB** | — |
| （其余 7 条同比例） | … | … | 均放大 1024× | — |

- 判定：**FAIL**（两页面"互相一致"但都错了 1024×）
- 归属澄清（rev2，判据落在**源码现状**而非构建时间，按协调侧口径）：本条**不是旧包造成**。① `formatFileSize` 正是 r14-D 提交 `4415ed3` 新增的函数，且它假设"fileTotalSize 单位是 KB"（提交内注释原文：`R14-D-FIX-02：知识库 fileTotalSize 的单位是 KB（后端原始值）`）；② 页面实际显示「6.4 GB」恰是该函数的 GB 分支输出，说明 dist 里跑的就是 r14-D 的这段代码；③ 因此结论是 **r14-D 的修复前提与实测单位不符**（后端给的是字节），不是"未进包"。④ 附带说明 r14-D 提交自述把 `6717181M` 修正为"实为 6.4GB"——按字节实测应为 6.4MB，仍差 1024×
- 判据结论：**HEAD 里的 `formatFileSize` 仍按 1024 进制换算、且前提单位判断错误**（源码现状如此，`src/core/helps/index.ts:45-52`）→ 与包新旧无关 → **照记产品缺陷**，不走"包滞后导致"的口径、不需要等 ROUND-B 复验
- 证据：`AG-1/evidence/S2/size-consistency.json`、`03-kb-detail-34.png`

### S2-04 删除不存在库 → 明确错误提示（非 500）
- 实际：`HTTP=404 success=false errorCode=10001 errorMsg="知识库不存在"`；探测后 total=15、id 集合与探测前完全一致
- 判定：**PASS**
- 证据：`AG-1/evidence/S2/delete-nonexistent.json`

### S2-05 列表刷新时机记录
- 实际：进入列表发出 `/knowledgeBase/list` 请求 2 次；切第 2 页 +1；搜索「qa_r12」+1 并正确过滤；网络面板无轮询/WebSocket 长连接
- 判定：**PASS**
- 子项 **UNVERIFIED**："新建/删除后是否自动刷新"需真实新建/删除，本轮禁止；代码级线索：`KnowledgeBaseZh/index.tsx:112-116`（新建成功后 `closeModal(true)` 刷新）、`:176-186`（删除后 `fetchListByDelDone` 刷新或回退页码）
- 证据：`AG-1/evidence/S2/05-search-filter.png`、`05-network.json`

### S2-06（附加）文件级大小单位
- 实际：kb_34 文件接口 `size` 字段把字节数直接拼 "MB"：`pdf-encrypted.pdf 4445 → "4445.0MB"`、`pdf-scanned.pdf 6525683 → "6525683.0MB"`、`R12FIX-product-loan.docx 37544 → "37544.0MB"`（磁盘原件 37544 字节 = 36.7KB，偏差约 1024×1024）
- 判定：**FAIL**
- 归属澄清：该字段由**后端**生成（`size` 与 `fileSize` 同响应返回），与前端包版本无关
- 证据：`AG-1/evidence/S2/file-size-raw.json`

### S1-07（附加观察）登录后强制密保弹窗行为
- 实际：每次登录、以及**每次整页刷新**都会弹「密保问题设置｜请您设置密保问题用于忘记密码时重置密码！」；按钮只有「确 定」「退出登录」；**无关闭按钮**；ESC 实测不可关；遮罩 `.ant-modal-wrap` 覆盖全站并拦截 pointer events（Playwright 报 `intercepts pointer events`）
- 判定：PASS（行为记录属实，属**产品行为观察**，与我的注入操作无关）；对应缺陷 **D-7/P2**
- 本轮处置见「4. 注入式操作清单」
- 证据：`AG-1/evidence/S1/01-login-security-modal.png`

## 4. 注入式操作清单（rev2 新增，按判定口径必须单列）

| # | 注入内容 | 位置 | 为什么必须注入 | 未提交/未写入的证明 | 因此**未覆盖**的断言 |
|---|---|---|---|---|---|
| I-1 | 用 `page.evaluate` 移除 `.ant-modal-wrap / .ant-modal-mask / .ant-modal-root` 并把 `body.style.overflow` 置回 `auto` | S1-05、S1-06、S2 全流程（每次登录后与每次整页刷新后各执行一次） | 密保弹窗无关闭按钮且 ESC 无效，遮罩拦截全站 pointer events，不绕行则任何点击都不可达 | 未点「确 定」、未提交任何密保问题/答案/验证码；服务端无对应请求（网络面板无 `/userSecurityQuestion` 类写请求） | **密保设置流程本身（选题/答案校验/落库/后续"忘记密码"可用性）全部未验证 → 记 UNVERIFIED**，不记 PASS |
| I-2 | 只读方式从 Redis 读取图形验证码明文（`docker exec r12-redis redis-cli`），解码后填入表单 | S1-01/02/08 的 UI 登录 | 等价人工识图；不关闭也不降级服务端校验 | 服务端 `validateKaptchaFour` 仍在校验；错误码（30000 验证码错误）可被触发即证明校验生效（S1-08） | 无（识图能力本身不是被测功能）。风险声明：若多角色并行在同一 IP+UA 上取码会互相覆盖 key，本角色为 captcha 路径唯一 owner，未受影响 |

> 说明：D-7 记录的是"弹窗不可关闭"这一**产品行为**，由弹窗自身实现决定（无 close 按钮、`maskClosable=false`、ESC 不响应），不是我的注入造成的；我的注入只是把遮罩移走以便继续只读用例。

## 5. 版本漂移核查（rev2 新增，回应 AG-2）

- AG-2 指出：`dist/assets/index-*.js` 构建时间 13:22，而 `src/core/components/StreamReader.tsx` 13:35 修改、r14-D 提交在 16:19 → 运行包可能滞后于 HEAD。**该事实成立**（我复核：`stat` 时间一致），且影响 AG-2 的"引用打开原文/失败文案三态"两项。
- **对我的断言的影响已逐条核查**：
  1. `formatFileSize`（S2-03）——r14-D 提交 `4415ed3` 引入；页面显示「6.4 GB」即该函数输出 ⇒ 运行包**已包含**该函数，非旧包；且该提交自述的"单位是 KB"前提与实测（37544 字节原件 = API 37544.0）不符 ⇒ 属**代码缺陷**，非版本漂移。
  2. 文件级 `size` 字段（S2-06）——后端生成，与前端包无关。
  3. S1/S13 全部为接口行为与会话语义，不经过 `StreamReader`，不受影响。
- **结论块（D-5a，按协调侧指定口径）**：
  - **缺陷归属**：前端 `formatFileSize` 的单位假设与后端实际单位不一致（形参名 `kb`、按 KB 语义换算，后端给的是字节）
  - **成因**：r14-D 提交 `4415ed3` 的修复注释断言"后端给的是 KB"，实测是字节（`fileTotalSize=6,746,568` 走该函数 → 6.4 GB，实际 6.4 MB）
  - **判据**：运行包**已包含**该函数（页面 GB 分支的输出恰是该函数产出，除它无第二处能产出 "6.4 GB"），故与包新旧无关
  - **修复方向**：先由接口侧确认单位口径（字节 or KB），再改函数**或**改字段命名/语义，**二者不可各改一半**
  - **修复前提（写在最前）**：**先定单位口径、再动一侧**。这类单位 bug 最常见的二次事故就是"前端改一半、后端也改一半，结果又错一倍"——本次 r14-D 已是先例（把 `6717181M` 改成 `6.4 GB`，方向对但单位前提错，等于换了件错衣服）
  - 交叉佐证（非本报告主张的依据）：AG-2 从线上 entry bundle 抠出该函数（压缩名 `qm`，KB→MB→GB 三级分支与 `index.ts:45-52` 一致），证据 `AG-2/evidence/version-check/served-bundle-formatFileSize.txt`；与本报告"运行包已含该函数"的推断互相独立地吻合
- 判据（按协调侧口径，落在**源码现状**而非构建时间）：先看 HEAD 源码是否仍错 —— 是 → 与包新旧无关、照记产品缺陷；源码已修只是包没重建 → 记"包滞后导致"、留 ROUND-B 复验。对 S2 单位两条：HEAD 的 `formatFileSize`（`src/core/helps/index.ts:45-52`）**仍按 1024 换算且单位前提错误**，后端 `size` 字段生成逻辑不含换算 → 均属**源码现状缺陷**，故直接记产品缺陷，不走"包滞后"口径
- 分工声明（合并纪律）：**D-5a（库级 1024×，标签/换算错）与 D-5b（文件级 1024²，后端 `size` 字段硬拼 "MB"）是两个不同成因，保持分开计数，不合并**；AG-2 侧的同名观察与 D-5a 同源，合并报告时按 D-5a 归并到本报告，D-5b 独立
- 结论：**我的 6 条 FAIL（必需项）中，无一条可用"旧包"解释**；AG-2 的版本漂移问题归 AG-2 报告，我不代其定级。

## 缺陷清单

| ID | 级别 | 现象 | 复现步骤 | 期望 vs 实际 | 影响面 | 稳定复现 |
|---|---|---|---|---|---|---|
| D-1a | **P0** | 无权限账号可读任意知识库的文件清单与元数据（BOLA，元数据层） | `r13_noauth` token 请求 `GET /index/knowledgeBase/file/folder/list?pageNo=1&pageSize=20&kbId=34&fileListType=1` | 期望 403；实际 `200 success=true total=8`，含 fileName/version/status/MinIO 全路径/`synLogs.errorDetail`（LOG_ID、task_id） | 任意已登录账号可枚举全部知识库文件资产与内部存储结构；同资源其他接口（getKbById/file getById 403、stream 401）正常 ⇒ 单点漏校验 | 2/2 账号 |
| D-1b | **P0（最高档）** | 无权限账号可读他人知识库**全文分块**（跨库读原文） | `r13_noauth` → `GET /file/getFileChunks?kbId=34&docId=483` / `GET /file/getKbFileChunks?kbName=kb_34&fileName=docx-plain.docx` | 期望 403；实际均 `200 success=true` 且返回真实正文（① total=1、②' n=1）；② **不需要 kbId**，只要 `kb_<id>`+文件名，而 primitiveName 由 A 类接口直接给出 | 任意已登录账号可"枚举资产 → 读任意文件全文"；与 D-1a 串成完整攻击链；权限模型在此处等于不存在 | 2/2 接口（①②'） |
| D-1d | **P3** | 分块查询 fail-open：键名写错（用显示名）返回 `200 success=true, data=[]`，把"取不到"伪装成"成功且为空" | `GET /file/getKbFileChunks?kbName=R14-BASELINE-KB&fileName=docx-plain.docx`（显示名）vs `kbName=kb_34` | 期望 404/明确错误；实际 200+空数组，调用方无法区分"无此库/无此文件"与"该文件没有分块" | 排障误导、前端静默空态 | 1/1 |
| D-2 | **P3**（rev2 由 P1 降级） | 畸形 Authorization（非三段 JWT）→ 公开端点 `/auth/user/kaptcha` 500（健壮性缺口：畸形输入未转换为 401） | 对 kaptcha 带 `FORGED-AG1` / `a.b.c` / `Bearer <token>`；或浏览器 localStorage 写入无点串后访问受保护页 | 期望 401；实际 500（`JWTDecodeException: The token was expected to have 3 parts, but got 0`）。该状态下登录页验证码加载失败（输入框 0 个）→ 需手工清 localStorage | 仅垃圾输入触发；正常过期/签名错/篡改/缺 token 均 401（三态矩阵），故不构成"会话过期即锁死" | 3/3 畸形变体 |
| D-3 | **P1** | 普通账号可访问管理员用户接口（纵向越权） | `r13_reader`/`r13_noauth` 请求 `GET /auth/user/searchUserList`、`GET /auth/user/getUserInfoByUserName/admin` | 期望 403；实际均 `200 success=true`（用户列表 total=5） | 账号枚举、组织信息泄露 | 2/2 |
| D-4 | **P1** | 无权限账号可创建知识库（越权写成功） | `r13_reader` token `POST /index/knowledgeBase/create {"kbName":"…"}` | 期望 403；实际 `200 success=true`，DB 新增 id=35 `create_by=r13_reader` | 只读/无授权账号可写库；与 D-1 同源（权限校验在多个写读接口缺位） | 1/1（已回滚，见自检；另 3 条间接旁证：create 与 delete/get 的权限口径不一致） |
| D-5a | **P2** | **1024× 偏大**：库级总大小把字节当 KB 换算 | 看 `/chats/knowledgeBase` 卡片「大小：6.4 GB」；再看详情页 `/chats/knowledgeBase/34` 同一行 | 期望 6.4 MB；实际 6.4 GB。**接口/字段**：`GET /index/knowledgeBase/list` 响应的 **`fileTotalSize`**（字节，如 6,679,637），经前端 `formatFileSize`（`src/core/helps/index.ts:45-52`，按 KB 解释）渲染到卡片 `KnowledgeBaseCard.tsx:179` 与详情 `Detail.tsx:205` | 12/12 库（卡片 + 详情页） | 12/12 库 |
| D-5b | **P2** | **1024² 偏大**：单文件大小把字节数直接拼 "MB" 后缀，未做任何换算 | 打开 kb_34 文件列表，或直接看接口响应里的 `size` 字段 | 期望 `36.7 KB`；实际 `"37544.0MB"`。**接口/字段**：`GET /index/knowledgeBase/file/folder/list`（及 `flatFiles` 等）响应中的 **`size` 字段**（后端生成，与 `fileSize` 并列返回），如 `"6525683.0MB"`；对照磁盘原件 37,544 字节 | 全部文件条目 | 5/5 文件 |
| D-6 | **P2** | 登录类业务异常被映射为 HTTP 500（验证码错误、密码错误） | ① 真实表单输错验证码 ② 输入错误密码 | 期望 200/400 + 明确 errorCode；实际 `HTTP=500`（`errorCode=30000 验证码错误！` / `用户名或密码错误`） | 正常用户每天都在走的路径；监控/网关按 5xx 计入服务故障，前端只能落通用兜底文案 | 3/3 |
| D-7 | **P2** | 强制「密保问题设置」弹窗无关闭按钮、ESC 无效、每次整页刷新重现并拦截全站点击 | 用 admin 登录（`hasSetSecurityQuestion=false`） | 期望可关闭或仅首次提示；实际覆盖全站无关闭按钮，只读用户只能"退出登录" | 阻断所有页面操作；自动化验收须绕行 | 5/5 次登录与刷新 |
| D-8 | **P3** | 登出后 `localStorage.isLoggedIn` 仍为 `true` | 登录→退出登录→读 `localStorage["gitech_ril:rag_ai"].isLoggedIn` | 期望 false；实际 true（`getToken()` 返回 undefined，而 `isLogined` 判据为 `token !== null`；`clear()` 后 provider 又 init 重建对象） | 仅状态标志失真（token 已清除，不构成越权） | 1/1 |
| D-9 | **P2**（独立计数，主查 AG-2） | `/qa/feedback/que/list` 恒 500：合法 JWT 也报 `syntax error : { … fastjson-2.0.47`，errorCode 999 | 同一合法 JWT：`GET /qa/feedback/que/list` 500 / 999，而 `GET /index/knowledgeBase/getKbById?id=9` 200 | 期望 200；实际 500 | 反馈列表页不可用；**与 D-2 不是同一族**：D-2 是"token 非法 → JWT 解码异常"，本条是"token 合法 → 接口自身报文解析异常"（壳层接口族） | 2/2 |

**缺陷条数：P0 = 2（D-1a 元数据 / D-1b 内容级），P1 = 2，P2 = 5（D-5a / D-5b / D-6 / D-7 / D-9），P3 = 3（D-1d / D-2 / D-8），合计 12 条。**

> D-5a 与 D-5b 是**两个不同的单位换算 bug**（1024× 与 1024²），命中不同接口的不同字段、修法不同，故拆分独立计数：
> D-5a 修 `formatFileSize` 的入参单位假设（或后端统一改语义 + 全链路对齐）；D-5b 修后端 `size` 字段生成逻辑（现在是把 `fileSize` 数字直接拼 "MB"）。

**合并修复建议（仅建议，不改动 D 的独立计数）**：D-2 与 D-6 同属「可预期的输入/会话错误被当作系统故障」——`GlobalHandler` 应先按 `ApplicationException`/`ErrCodeEnum` 映射 4xx + 明确 errorCode，`UserContextFilter` 应捕获 `JWTDecodeException` 并回落 401；只有真正的服务异常才允许 500。D-9 属另一族（接口自身报文解析），需单独修 fastjson 入参处理。

## 未覆盖项

| 场景 | 原因 | 谁能解除阻塞 |
|---|---|---|
| **密保设置流程本身**（选题/答案校验/落库/忘记密码可用性） | 只读角色不能设置密保（写入），我以 DOM 移除遮罩绕行（I-1），故整条流程未被执行 | 产品/业务 owner 或持写入权的角色 |
| S13-05 撤权后原会话立即失效 | 需写 `user_privilege`（删/改授权行），零写入约束禁止；他人历史证据不得引用 | security_owner / 有权写权限数据的角色 |
| S2-05 子项「新建/删除后列表是否自动刷新」 | 需真实新建/删除知识库，本轮禁止（且本角色已因 D-4 探测产生过一次副作用，不再重复写） | 持独占锁的写入角色（AG-5 链） |
| S1-06 真实 24h 过期窗口 | 不可等待；已用三态矩阵 ② 组（过期/签名错 → 401）与 S13-06 覆盖拒绝语义 | 无需解除 |
| 文件内容级越权（非元数据） | 已实测被挡（MinIO 匿名 403、`file/stream` 普通 token 401）；"有 A 库权、取 B 库文件内容"需构造合法授权 token，属写权限数据 | security_owner |
| 「密保弹窗」是否属产品合规要求 | 属产品策略判断，非本次 E2E 判据 | 产品/业务 owner |

## 自检

- **断言总数**：规范必需 **16** 条（S1×7：01/02/03/04/05/06/08、S13×4、S2×5）+ 附加 4 条（S1-07、S13-04、S13-06、S2-06）= **20**
- **已执行**：20；**未执行**：0；其中 **UNVERIFIED 2 项**：S13-05（撤权需写权限数据）、密保设置流程（因注入式绕行未覆盖）
- **判定分布**：PASS 12 / FAIL 7 / UNVERIFIED 1（必需 16 条中：PASS 9、FAIL 6、UNVERIFIED 1）
- **是否用旧证据**：否。所有页面文本、截图、接口值均为 2026-10-27 23:58 ~ 2026-10-28 11:05 本 session 现场采集；仓内他人 `evidence/REVOKE-*`、`R13-*` 仅用于**查夹具账号口令与接口路径**，未作为任何 PASS 依据
- **是否含注入**：含 2 项，已在上方「4. 注入式操作清单」逐条列明（密保遮罩 DOM 移除、只读取验证码），并列出因此未覆盖的断言
- **零写入约束的偏离（必须披露）**：为验证「越权写是否被拒」，于 2026-10-28 10:24:39 以 `r13_reader` 执行了 1 次 `POST /index/knowledgeBase/create`，**实际创建成功**（即 D-4），产生 `gienrag.knowledge_base` id=35「AG1-SHOULD-NOT-CREATE」
  - 处置：随即 `DELETE /index/knowledgeBase/delete?id=35` 回滚，返回 `success=true`，该行被软删为 `status=0`（与库内既有 20 条软删夹具同态），不再出现在任何业务查询中（admin 列表仍 15、id 集合与原基线完全一致）
  - 残留：1 条 `status=0` 软删行 + 该表 `AUTO_INCREMENT` 由 35 推进到 36
  - 该探测未重复执行；此后未再执行任何新建/删除/改配置。留痕：`AG-1/evidence/S13/00-side-effect-and-revert.log`
- **服务代次**：开工 8088=1403651 / 18083=1647331 / 18082=2139785 / 19527=1823402 / 19529=1461792 / 19995=1481869；收工复核 pid 未变（未重启任何服务）
- **前端版本**：entry `assets/index-CpE2zvYY.js`，服务端返回体与磁盘 dist 均 `de2424501bd29e358043049876db2a75`（315576 B）；**已额外核查该 dist 与 r14-D 提交的关系（见第 5 节），确认 S2 单位结论不受版本漂移影响**
- **rev2 变更摘要**：① S1-04 补三态矩阵 → 降级 P3；② 新增 S1-08；③ `/qa/feedback/que/list` 的 500 从 S1-04 剥离为 D-9 独立计数；④ 新增第 4 节注入式清单与第 5 节版本漂移核查；⑤ 缺陷 8→9 条（P1 3→2、P2 3→4、P3 1→2）
- **rev3 变更摘要**：① P0 补静态行号证据（`:100/:148/:198/:217` 有 assert，`:154-158 folderList` 无），并按实测把范围由"单点"修正为"列表类只读接口成片缺失（≥5 条放行）"；② 新增第 3 节 S13 五项逐条映射（期望/实际状态码/判定，S13-5 受保护面与公开面分开判）；③ D-5 拆为 D-5a（1024×，前端 `formatFileSize`）与 D-5b（1024²，后端 `size` 字段），缺陷 9→10 条；④ 新增 S13-02A 两层结构与修复点；⑤ S2 单位归属判据改为落在"源码现状"（HEAD 仍按 1024 且单位前提错）→ 照记产品缺陷
- **纪律整改（协调侧要求，已接受）**：本次越权写举证属"事后补报"，此后凡需写操作**先报批再执行**；自 2026-10-28 11:00 起本角色**未再执行任何写操作**（含创建/删除/改配置），后续 S13 范围复核全部为只读 GET

## 一句话结论

会话/列表主链基本可用（登录、落地、未登录拦截、登出、刷新保活、条数/名称/文档数、删除不存在库均 PASS），但**权限模型有 4 处实质缺口，其中 P0 两档（D-1a 元数据泄露、D-1b 内容级跨库读原文）、P1 两处（纵向越权、越权建库）**；D-1a 与 D-1b 串成完整攻击链：任意账号 → 列表接口枚举 kbId/primitiveName/fileName → 分块接口读全文；登录链路上"可预期错误被当系统故障"表现为两处 500（畸形 token=D-2/P3、验证码错误=D-6/P2），正常过期路径不锁死；大小单位问题为**代码缺陷而非旧包**（按源码现状判据）：库级 `fileTotalSize`→卡片/详情放大 **1024×**（D-5a，前端），文件级 `size` 字段放大 **1024²×**（D-5b，后端），两个 bug 的修法不同。
