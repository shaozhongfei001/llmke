# 代次、任务与删除协议

## 四类对象

1. BuildManifest：kb、文档内容/解析文本版本、parser/chunking/embedding/type-system版本、后端位置/checksum/必需标记、派生完整叶子；无时间和可变状态。generation=g+sha256(规范内容不含generation)，documents/artifacts/derived_refs按reference函数排序后规范UTF-8 JSON。
2. BuildRun：创建时间、building/ready/failed/superseded、产物回执、资源版本与fencing；可变，不回写清单。
3. PublicationState：artifact_id/revision、draft/published/stale/retired、业务有效期与批准；引用固定内容revision，状态可变。
4. ActivationPointer：每KB单条权威记录，generation/manifest_hash/pointer_version/fencing_token/回滚窗口。active不靠每后端别名分别切换。

## 写入和激活

业务库单写入者持久化命令与任务/outbox；算法只执行并回执。每个任务带KB、逻辑文件/文档版本、resource_version、generation和服务端fencing。迟到/已删除/代次不符回执拒绝，不自动改当前状态。

校验不可变manifest摘要、完整服务端必需集和对应ready/checksum，再在业务事务内CAS切换唯一指针。客户端不能自报缩小必需集；首次expected_pointer=null/version0；已有代次需同时比对pointer_version。围栏令牌由业务侧发放，客户端不能自行提高。切换前后查询固定同一完整快照，不混代。

## 删除与回退

同事务推进资源/授权版本、墓碑与查询围栏，再持久入清理任务后返回202。后端物理删除可异步，但查询、扩召回、缓存和旧任务回执立即检查围栏。历史引用需保留指向指定解析快照的受权解析能力；未授权历史同样拒绝。

回退指针仍须CAS，按新授权/墓碑过滤；旧服务不得覆写新协议状态。完整旧服务版本/DDL和同版本恢复副本未到位时，不承诺秒级回滚。双代磁盘/内存、重建期间写入、资源GC和回滚期限在P2前验证。

内容blob可去重，逻辑file_id、document_version和权限绑定独立；同内容不同文件/KB不能共用业务身份。每次分块/parser/embedding版本变化建立新代，先离线质量/引用回放再切换。

实际业务存储表/事务DDL待P0-02/04关闭；reuse/db-migration合同规定需要的证据，不从37表CSV补造约束。
