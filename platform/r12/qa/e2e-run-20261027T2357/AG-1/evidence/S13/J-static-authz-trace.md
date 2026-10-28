# 静态授权追踪：controller 映射 → service 方法 → 是否有 assert（纯静态，未发任何请求）

采集：2026-10-28 12:0x，只读源码（grep/read），**未执行任何 HTTP 请求**。
范围：`rag-index-service`
- controller：`com/gientech/ragindexservice/interfaces/KnowledgeBaseFileController.java`
- service 实现：`com/gientech/ragindexservice/application/service/impl/KnowledgeBaseListAppServiceImpl.java`（3007 行）

## 0. 前置结论：该模块不存在 AOP/注解式授权

| 检查项 | 结果 |
|---|---|
| `@PreAuthorize` / `@Secured` | 全模块 **0 处** |
| `HandlerInterceptor` / `WebMvcConfigurer` | 全模块 **0 处** |
| 对象级授权设施 | 只有 `application/authz/KbAuthzService.java`（`assertRead/assertWrite/assertManage/assertSuperAdmin`） |
| `kbAuthzService` 的全部调用点 | `KnowledgeBaseFileController` :100/:148/:198/:207/:217/:228/:240/:249；`KnowledgeBaseController` :60/:93/:100/:109/:118/:125/:132/:139/:147/:154/:161/:167 |
| 推论 | 该模块的授权**全部是 controller 内显式调用**；controller 没有 `kbAuthzService` 调用的映射，在本模块内**不存在**其它授权入口（网关只做"接口级"放行，不做知识库对象级判定——由运行态旁证：同一账号 kb 列表 200、getKbById 403） |

## 1. 逐映射对照表

判定口径：**有 assert** = 控制器或 service 方法体内存在 `kbAuthzService.assertXxx`；**无 assert** = 两处均无授权调用（但方法体内可能有 `getHighestPermission` 这类"只读权限值用于展示"的调用，不计为授权）；**无法判定** = 依赖运行期条件/动态代理等。

| # | controller 映射 | 行号 | 委派方法（全名 + 行号） | service 体内授权 | 判定 |
|---|---|---|---|---|---|
| 1 | `GET /folder/list` | :154 | `KnowledgeBaseListAppServiceImpl.folderList` **L1935** | 无（L1936 起仅 `getHighestPermission` 用于给 DTO 填 `permission` 展示字段，`buildKbFileListResult` L2051 同） | **无 assert** |
| 2 | `GET /list` | :161 | `…listNew` **L1625** | 无（同上，只填 permission 展示值） | **无 assert** |
| 3 | `GET multiple/version` | :167 | `…multipleVersion` **L1659** | 无（同上） | **无 assert** |
| 4 | `GET /flatList` | :173 | `…flatList` **L1969** → `searchUserFileList` **L2041** | 无授权；`searchUserFileList` 只把 `req.getUserName()` 传给查询做**数据范围过滤**，userName 为空即不过滤；真正的 `privilegeClient.isPermissionApi(...)`（L2016/L2027）在 `searchFileList`（**L1997**）里，而 `flatList` 走的是 `searchUserFileList`，**不经过它** | **无 assert** |
| 5 | `GET /flatFiles` | :181 | `…flatFiles` **L1979** → `searchUserOnlyFileList` **L2046** | 无 | **无 assert** |
| 6 | `GET /queryList` | :189 | `…queryList` **L2563** | 无 | **无 assert** |
| 7 | `GET /getFileStatusById` | :290 | `…getFileStatusById` **L808-816** | 无：直接 `knowledgeBaseListDomainService.findById(fileId)` 取 `status` 返回 | **无 assert** |
| 8 | `GET /getFAQExtractStatusById` | :301 | `…getFAQExtractStatusById` **L927-935** | 无：同上，取 `faqExtractStatus` | **无 assert** |
| 9 | `GET /getGraphParseStatus` | :307 | `…getGraphParseStatus` **L2496-2504** | 无：同上，取 `graphParseStatus` | **无 assert** |
| 10 | `GET /getFileStatusByUids` | :295 | `…getFileStatusByUids` **L2692-2699** | 无 | **无 assert** |
| 11 | `PUT /updateEnable`（**写**） | :284 | `…updateEnable` **L801-807** | 无：直接 `knowledgeBaseListDomainService.updateEnable(fileIds, enableStatus)` | **无 assert（写接口）** |
| 12 | `PUT /filesReviseDate`（**写**） | :255 | `…filesReviseDate` **L1701-1729** | 无 | **无 assert（写接口）** |
| 13 | `POST /extractFQA` / `POST /reExtractFQA`（**写**） | :327 / :341 | `…reExtractFQA` **L2257-2296** | 无 | **无 assert（写接口）** |
| 14 | `POST /extractAllFQA`（**写**） | :335 | `…extractAllFQA` **L2389-2392**（4 行，直接委派） | 无 | **无 assert（写接口）** |
| 15 | `POST /filesAllParse`（**写**） | :247 | `…filesAllParse` | — | **有 assert**（controller `:249 assertWrite(kbId)`） |
| 16 | `POST /filesParse`、`/graphParse`（**写**） | :223 / :235 | `…filesParseNew` / `…graphParse` | — | **有 assert**（controller `:228`/`:240` 逐 fileId `assertWrite`） |
| 17 | `POST /uploadParsedFile`（**写**） | :313 | `…uploadFile` **L273-395** | 方法体内**无授权关键字**；controller 亦无 | **无 assert（写接口）** |
| 18 | `POST /upload`（分片上传，**写**） | :269 | `…chunkUpload` **L747-759** | 无（入参只有 fileMd5，方法内无 kb 归属信息） | **无 assert（写接口）** |
| 19 | `POST /merge`（分片合并，**写**） | :277 | `…chunkMerge` **L760-800** | 无 | **无 assert（写接口）** |
| 20 | `GET /exist` | :127 | `…exist` **L2711-2718** | 无 | **无 assert** |
| 21 | `GET /precheck` | :137 | `…precheck` **L1610-1624** | 无 | **无 assert** |
| 22 | `GET /check` | :260 | `…checkCunkFile` **L717-746** | 无 | **无 assert** |
| 23 | `GET /getFileChunks`（**返回分块正文**） | :348 | `…getFileChunksByPage` **L896-926** | 无授权：仅校验 `kbId` 存在（`findByKbId`）、`docId` 存在、`status==PARSE_SUCCESS`，随后 `getFileChunks(docId,…)` 返回正文 | **无 assert（内容级）** |
| 24 | `GET /getKbFileChunks`（**返回分块正文**） | :355 | `…getKbFileChunks` **L2914-2918**（5 行） | 无：`chunkDomainService.getChunks(kbName, fileName, …)` 直接取 | **无 assert（内容级）** |
| 25 | `GET /getById` | :143 | `…getById` | — | **有 assert**（controller `:148 assertRead`） |
| 26 | `GET /getByIds` | :213 | `…getByIds` | — | **有 assert**（controller `:217` 逐 fileId） |
| 27 | `DELETE /delete` | :195 | `…deleteById` | — | **有 assert**（controller `:198 assertWrite`） |
| 28 | `DELETE /deleteByIds` | :203 | `…deleteByIds` | — | **有 assert**（controller `:207` 逐 fileId） |
| 29 | `/stream`（取流） | — | `assertStreamAllowed` | — | **有 assert**（`:100`，对象键→kb_ 段→反查→assertRead，认不出即拒） |

## 2. 结论

- **有 assert 的只有 6 个映射**（getById、getByIds、delete、deleteByIds、filesParse、graphParse、filesAllParse、stream —— 其中 filesAllParse 在 :249，共 8 个位置，7 个映射）。
- **无 assert 的读接口**：列表类 6 个（#1-#6，其中 #3 multiple/version 运行时被自身 500 掩盖）、状态类 4 个（#7-#10）、元信息 3 个（#20-#22）、**内容级 2 个（#23/#24，返回分块正文）**。
- **无 assert 的写接口**：`updateEnable`(#11)、`filesReviseDate`(#12)、`extractFQA/reExtractFQA`(#13)、`extractAllFQA`(#14)、`uploadParsedFile`(#17)、`upload`(#18)、`merge`(#19)。
- 没有"无法判定"项：本模块无 AOP/注解式授权、无父类模板方法包装（controller 直接 extends 无父类），判定条件足够。
- **两个需要立刻复看的高危项（静态结论，未做运行态验证）**：
  1. `GET /getFileChunks`（:348）与 `GET /getKbFileChunks`（:355）—— **返回分块正文**且无授权。若 kbId/docId/kbName+fileName 可枚举（A 类列表接口已能给出 kbId + fileName），等价于**跨库读取原文**。这比 A 类的"元数据泄露"更严重，建议优先验证。
  2. 7 个写接口无授权（updateEnable / filesReviseDate / extractFQA / extractAllFQA / uploadParsedFile / upload / merge）——其中 updateEnable 只需 fileIds 即可改启停状态。
- 统一修法不变：在 controller 层按 `req.kbId` / `kbIdOfFile(fileId)` / `(kbName→kbId)` 统一 `assertRead`/`assertWrite`，或把校验下沉到 `KnowledgeBaseListAppServiceImpl` 的每个 public 方法入口；逐个补会漏（漏的规律是"后来新增的接口没人想到加"）。

## 3. 边界声明

- 本表**全部为静态阅读结论**，未执行任何请求（按协调侧四条限定）。
- 表中"无 assert"仅表示"本模块 controller + service 方法体内无授权调用"，不排除上游网关接口级放行策略的影响；但运行态旁证（同账号 kb 列表 200 / getKbById 403）表明网关不做知识库对象级判定。
- 未展开的更深层（repository/mapper 内是否按用户过滤）已抽检 2 处：`searchUserFileList` 走 `req.getUserName()` 数据范围过滤（非授权），`searchShareFileList` 走 `privilegeClient.isPermissionApi`（**是授权过滤，但只在 scope=SHARE/ALL 分支**，`flatList`/`flatFiles` 不经过它）。其余 mapper 未逐条展开，属"未展开"而非"无"。
