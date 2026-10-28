#!/usr/bin/env python3
# rev3 定向补丁：S13 五项映射表 / P0 代码级证据+范围修正 / 拆分 D-5a·D-5b
import io

P = "AG-1-report.md"
s = io.open(P, encoding="utf-8").read()

S13_TABLE = """## 3. S13 五项逐条映射（期望 / 实际状态码 / 判定，不合并）

| 编号 | 项 | 主体 | 期望 | 实际状态码 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| S13-1 | 无权限账号读他人库文件清单 | r13_noauth / r13_reader | 403 或明确拒绝 | `200 success=true total=8`（kb_34）；对照 `getKbById?id=34`=403/30016、`file/getById?id=483`=403/30016、`stream`=401/30021 | **FAIL** | `S13/B-horizontal-authz.json`、`S13/G-p0-scope-5-endpoints.txt` |
| S13-2 | 普通账号越权创建知识库 | r13_reader | 403 或明确拒绝 | `200 success=true`；库表新增 id=35 `AG1-SHOULD-NOT-CREATE`、`create_by=r13_reader`、`status=0` | **FAIL** | `S13/00-side-effect-and-revert.log`、`S13/H-s13-item-mapping.md` |
| S13-3 | 普通账号读管理员用户列表 | r13_reader / r13_noauth | 403 | `200 success=true total=5`（含 admin 全部账号）；`getUserInfoByUserName/admin` 亦 200 | **FAIL** | `S13/C-vertical-authz.json` |
| S13-4 | 撤权后会话失效 | 需他人先撤权 | 原会话 401 | 未执行（撤权=写 `user_privilege`，零写入约束禁止） | **UNVERIFIED** | `S13/E-revoke-unverified.txt` |
| S13-5 | 伪造 Authorization 头 | 无/空/畸形/错签 | 401 或 403（**500 不合格**），受保护面与公开面**分开判** | 受保护面（getMenusByUser、kb list）全部 401 → **PASS**；公开面（kaptcha、login）畸形串 → **500** → **FAIL**；无 token/空 → kaptcha 200（白名单设计，非缺陷） | **FAIL**（分栏见 `S13/H-s13-item-mapping.md`） | `S13/A-auth-matrix.json`、`S1/04-tristate-matrix.json` |

### S13-01 直接构造 URL 访问无权资源 → 403 或明确拒绝，**不得 200**"""

s = s.replace("### S13-01 直接构造 URL 访问无权资源 → 403 或明确拒绝，**不得 200**", S13_TABLE, 1)

P0_OLD = """- 判定：**FAIL**
- 证据：`AG-1/evidence/S13/B-horizontal-authz.json`、`s13-raw.jsonl`
- 复跑：`node s13-perm.js`
- 内容面补充（未被突破）：MinIO 直取匿名 403；`file/stream` 带普通 token 401。即**元数据泄露、内容未泄露**"""

P0_NEW = """- 判定：**FAIL**
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
- 证据：`AG-1/evidence/S13/B-horizontal-authz.json`、`s13-raw.jsonl`、`S13/G-p0-scope-5-endpoints.txt`
- 复跑：`node s13-perm.js`
- 内容面补充（未被突破）：MinIO 直取匿名 403；`file/stream` 带普通 token 401。即**元数据泄露、内容未泄露**"""

assert P0_OLD in s, "P0 段未命中"
s = s.replace(P0_OLD, P0_NEW, 1)

D5_OLD = "| D-5 | **P2** | 大小单位错：字节被当 KB/MB，放大 1024×（卡片/详情）/ 1024²×（文件 size 字段） | 看卡片「大小：6.4 GB」；对照接口 `fileTotalSize=6679637` 与磁盘 6.4MB 原件 | 期望 6.4 MB；实际 6.4 GB。r14-D 的修复前提（\"单位是 KB\"）与实测单位（字节）不符 | 全站 12/12 库卡片 + 详情页 + 文件列表 | 12/12 库、5/5 文件 |"

D5_NEW = """| D-5a | **P2** | **1024× 偏大**：库级总大小把字节当 KB 换算 | 看 `/chats/knowledgeBase` 卡片「大小：6.4 GB」；再看详情页 `/chats/knowledgeBase/34` 同一行 | 期望 6.4 MB；实际 6.4 GB。**接口/字段**：`GET /index/knowledgeBase/list` 响应的 **`fileTotalSize`**（字节，如 6,679,637），经前端 `formatFileSize`（`src/core/helps/index.ts:45-52`，按 KB 解释）渲染到卡片 `KnowledgeBaseCard.tsx:179` 与详情 `Detail.tsx:205` | 12/12 库（卡片 + 详情页） | 12/12 库 |
| D-5b | **P2** | **1024² 偏大**：单文件大小把字节数直接拼 "MB" 后缀，未做任何换算 | 打开 kb_34 文件列表，或直接看接口响应里的 `size` 字段 | 期望 `36.7 KB`；实际 `"37544.0MB"`。**接口/字段**：`GET /index/knowledgeBase/file/folder/list`（及 `flatFiles` 等）响应中的 **`size` 字段**（后端生成，与 `fileSize` 并列返回），如 `"6525683.0MB"`；对照磁盘原件 37,544 字节 | 全部文件条目 | 5/5 文件 |"""

assert D5_OLD in s, "D-5 行未命中"
s = s.replace(D5_OLD, D5_NEW, 1)

CNT_OLD = "**缺陷条数：P0 = 1，P1 = 2，P2 = 4（D-5/D-6/D-7/D-9），P3 = 2（D-2/D-8），合计 9 条。**"
CNT_NEW = """**缺陷条数：P0 = 1，P1 = 2，P2 = 5（D-5a / D-5b / D-6 / D-7 / D-9），P3 = 2（D-2 / D-8），合计 10 条。**

> D-5a 与 D-5b 是**两个不同的单位换算 bug**（1024× 与 1024²），命中不同接口的不同字段、修法不同，故拆分独立计数：
> D-5a 修 `formatFileSize` 的入参单位假设（或后端统一改语义 + 全链路对齐）；D-5b 修后端 `size` 字段生成逻辑（现在是把 `fileSize` 数字直接拼 "MB"）。"""

assert CNT_OLD in s, "计数行未命中"
s = s.replace(CNT_OLD, CNT_NEW, 1)

S13_SUM_OLD = "| S13 权限负例 | **FAIL**（3 条不过，1 条 UNVERIFIED） | 0/3 通过 + 1 UNVERIFIED | 1m40s | `AG-1/evidence/S13/`（11 文件） |"
S13_SUM_NEW = "| S13 权限负例 | **FAIL**（S13-1/2/3/5 不过，S13-4 UNVERIFIED） | 0/4 通过 + 1 UNVERIFIED（逐条映射见 §3） | 1m40s | `AG-1/evidence/S13/`（13 文件） |"
if S13_SUM_OLD in s:
    s = s.replace(S13_SUM_OLD, S13_SUM_NEW, 1)

io.open(P, "w", encoding="utf-8").write(s)
print("rev3 patch applied")
