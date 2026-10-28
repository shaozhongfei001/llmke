#!/usr/bin/env python3
# rev6：把静态授权追踪（controller→service→has assert）并入报告 P0 段
import io
P = "AG-1-report.md"
s = io.open(P, encoding="utf-8").read()

ANCHOR = "  未探测（明确不越界）：`upload :269`"
BLOCK = """- **静态授权追踪（rev6，纯静态、未发任何请求；完整表见 `AG-1/evidence/S13/J-static-authz-trace.md`）**：
  - 前置事实：`rag-index-service` 内 `@PreAuthorize`/`@Secured`/`HandlerInterceptor` **均为 0 处**，对象级授权只有 `KbAuthzService`，其全部调用点都在两个 controller 里（`KnowledgeBaseFileController` :100/:148/:198/:207/:217/:228/:240/:249；`KnowledgeBaseController` 12 处）→ **该模块不存在 AOP 类授权**，controller 没写 assert 的映射在本模块内没有第二道闸
  - 有 assert（7 个映射）：`getById :148`、`getByIds :217`、`delete :198`、`deleteByIds :207`、`filesParse :228`、`graphParse :240`、`filesAllParse :249`、`stream :100`
  - 无 assert 的**读**接口：列表类 6（`folderList L1935`、`listNew L1625`、`multipleVersion L1659`、`flatList L1969`、`flatFiles L1979`、`queryList L2563`）、状态类 4（`getFileStatusById L808-816`、`getFAQExtractStatusById L927-935`、`getGraphParseStatus L2496-2504`、`getFileStatusByUids L2692-2699`，三者方法体都是"直接 findById 取状态字段返回"）、元信息 3（`exist L2711`、`precheck L1610`、`checkCunkFile L717`）
  - 无 assert 的**写**接口 7 个：`updateEnable L801-807`、`filesReviseDate L1701`、`reExtractFQA L2257`（extractFQA :327 与 reExtractFQA :341 共用）、`extractAllFQA L2389-2392`、`uploadParsedFile→uploadFile L273-395`、`chunkUpload L747`、`chunkMerge L760`
  - **两个静态高危项（尚未做运行态验证，列为待验证）**：① `GET /getFileChunks :348 → getFileChunksByPage L896-926` 与 `GET /getKbFileChunks :355 → getKbFileChunks L2914-2918` **返回分块正文且无授权**（前者仅校验 kbId/docId 存在与 status==PARSE_SUCCESS），配合 A 类已可枚举 kbId+fileName，等价于**跨库读原文**，比元数据泄露更严重；② `PUT /updateEnable :284` 只需 fileIds 即可改启停状态
  - 另有一处"看似有授权其实只在特定分支生效"：`privlegeClient.isPermissionApi(...)`（L2016/L2027）位于 `searchFileList L1997`，只服务 `fileList(req)` 的 scope=SHARE/ALL 分支；`flatList`/`flatFiles` 走的是 `searchUserFileList L2041`（把 `req.getUserName()` 传给查询做**数据范围过滤**，非授权），userName 为空即不过滤 —— 这解释了为什么 `r13_noauth` 实测能拿到数据
  - 判定：**无"无法判定"项**（本模块无 AOP、无父类模板方法包装）；mapper 层未逐条展开，属"未展开"而非"无"

  未探测（明确不越界）：`upload :269`"""

assert ANCHOR in s
s = s.replace(ANCHOR, BLOCK, 1)

s = s.replace("；**rev5 2026-10-28 11:55**", "；rev5 11:55", 1)
s = s.replace(
"（按协调侧要求只读探测 3 个状态查询接口，把 P0 边界钉为 A 类实质泄露 / B 类弱泄露；未探测项记\"待确认范围\"）",
"（按协调侧要求只读探测 3 个状态查询接口，把 P0 边界钉为 A 类实质泄露 / B 类弱泄露；未探测项记\"待确认范围\"）；**rev6 2026-10-28 12:05**（按批准做纯静态授权追踪：controller→service 方法全名+行号+判定，结论为 7 个映射有 assert、读接口 13 个无 assert、写接口 7 个无 assert；新发现 `getFileChunks`/`getKbFileChunks` 返回分块正文且无授权，列待验证）", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("rev6 applied")
