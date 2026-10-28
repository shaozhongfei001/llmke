# S13 五项逐条映射（协调侧要求的精确化表，不重跑，仅整理既有证据）

| 编号 | 项 | 主体 | 期望 | 实际状态码 | 判定 | 证据文件 |
|---|---|---|---|---|---|---|
| S13-1 | 无权限账号读他人库文件清单 | r13_noauth / r13_reader | 403 或明确拒绝 | `200 success=true total=8`（kb_34，另一账号同）；对照 `getKbById?id=34`=403/30016、`file/getById?id=483`=403/30016、`stream`=401/30021 | **FAIL** | B-horizontal-authz.json、G-p0-scope-5-endpoints.txt |
| S13-2 | 普通账号越权创建知识库 | r13_reader | 403 或明确拒绝 | `200 success=true`（库表新增 id=35 `kb_name=AG1-SHOULD-NOT-CREATE`、`create_by=r13_reader`、`status=0`） | **FAIL** | 00-side-effect-and-revert.log（DB 前后全量 + 回滚留痕） |
| S13-3 | 普通账号读管理员用户列表 | r13_reader / r13_noauth | 403 | `200 success=true total=5`（含 admin 全部账号）；`getUserInfoByUserName/admin` 亦 200 | **FAIL** | C-vertical-authz.json |
| S13-4 | 撤权后会话失效 | 需他人先撤权 | 原会话 401 | 未执行（撤权=写 user_privilege，零写入约束禁止） | **UNVERIFIED** | E-revoke-unverified.txt |
| S13-5 | 伪造 Authorization 头 | 无 token / 空 / 畸形 / 三段错签 | 401 或 403（**500 不合格**） | 分两栏见下 | **FAIL**（受保护栏 PASS，公开栏 FAIL） | A-auth-matrix.json、../S1/04-tristate-matrix.json |

## S13-5 分栏判定（按要求不合并）

| 路径类别 | 端点 | 实际 | 子判定 |
|---|---|---|---|
| 受保护（过网关兜底） | `GET /auth/resource/getMenusByUser` | 无头/空/畸形/错签/篡改 全部 `401`（30022 或 30013） | **PASS** |
| 业务（过网关兜底） | `GET /index/knowledgeBase/list` | 同上，全部 `401`/30022·30013 | **PASS** |
| 公开（`isNoTokenFree` 白名单，绕过网关兜底） | `GET /auth/user/kaptcha` | 畸形无点串/两段/`a.b.c`/`Bearer <token>` → **500**；无 token/空 → 200（白名单设计如此，非缺陷） | **FAIL** |
| 登录接口（公开） | `POST /auth/user/login` 带畸形头 | **500**（空/无头 → 200 正常） | **FAIL** |

合计：受保护面合格、公开面不合格 → 整条 **FAIL**，对应缺陷 **D-2（P3）**；与 S1-04（浏览器侧同一根因）互为两面证据，分开计数（S1-04 也是 FAIL）。
