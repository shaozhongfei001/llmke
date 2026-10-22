# P0-04 现状核查：双代/切换协议在代码里存在吗

日期：2026-10-22　性质：只读分析；不改源码、不改控制面
结论：**P0-04 要求的四类机制在代码里一个都没有**；仅存在"任务领取"的乐观锁。
因此 S1–S5 五场景**无法在当前代码上验证**，P0-04 属"未实现"，不是"部分实现"。

---

## 1. 查了什么

| 检索项 | 结果 |
|---|---|
| `@Index/@Unique` 之外的代次相关列名（`generation`/`epoch`/`fence*`/`config_version`） | **0 处** |
| Java 中 `generation` / `fencing` / `activation` 关键字 | **0 处** |
| `is_migrate` | 1 处：`ReEmbeddingFileDO`（`@TableField("is_migrate")`） |
| `version` 列 | 1 处：`knowledge_base_list.version VARCHAR(16)`，语义是**文档版本号**，不是索引代次 |
| 迁移脚本 `.sql` | 0 个 |
| 定时任务 | 1 个：`FileParseTaskScheduler` |

对照 P0-04 的 `decision_required`（不可变 generation manifest、单原子激活指针、outbox/补偿归属、每 KB 写入版本与 fencing token）：
**四项均无对应实现或字段。**

---

## 2. 唯一相关的实现：任务领取（不是"代次"）

`ReEmbeddingRetryTaskServiceImpl.getRetryTask()`（`@Transactional`）：

```java
wrapper.eq(ReEmbeddingRetryTaskDO::getIsDel, 0);
wrapper.eq(ReEmbeddingRetryTaskDO::getStatus, 2);        // 等待处理
wrapper.eq(ReEmbeddingRetryTaskDO::getType, FILE);
wrapper.lt(ReEmbeddingRetryTaskDO::getRetryTimes, maxRetryTimes);
wrapper.orderByAsc(ReEmbeddingRetryTaskDO::getGmtCreate);
wrapper.last("LIMIT 1");
...
updateWrapper.eq(ReEmbeddingRetryTaskDO::getId, one.getId());
updateWrapper.eq(ReEmbeddingRetryTaskDO::getStatus, 2);
updateWrapper.set(ReEmbeddingRetryTaskDO::getStatus, 1);  // 处理中
boolean updated = this.update(updateWrapper);
if (!updated) return null;                                // 被别的线程抢先
```

**这一点要说公道话**：它是 **id 级 CAS**（`WHERE id=? AND status=2` + 检查影响行数），
不是我最初怀疑的"批量把 status=2 全改成 1"。所以**同一任务不会被两个 worker 同时领走**。

### 但它补不上 P0-04 的缺

| 缺什么 | 后果 |
|---|---|
| **无租约/超时回收**：全仓只有 `setStatus(1)`，没有把 `status=1` 退回 `2` 的逻辑 | worker 崩溃后任务**永久卡在处理中**，只能人工修数据 |
| **无 worker 身份 / fencing token** | 无法判断"这个结果来自哪次领取"，迟到的旧 worker 仍可写结果 |
| **无代次（generation）概念** | 新旧两代索引并存时，任务无法标注"我属于哪一代" |
| **无 outbox / 补偿** | 失败后的状态回写没有可靠投递机制 |

对应的正是 P0-04 `known_facts` 里那句"幂等键仅为 `(kb_id, file_id, config_version)`，
同内容被覆盖而配置不变时无法区分"——代码里连 `config_version` 都不存在。

---

## 3. 对 S1–S5 的含义

P0-04 要求证明的五场景：部分后端失败、切换中断、内容覆盖、迟到重试、旧服务回退。

| 场景 | 能否在当前代码上验证 | 为什么 |
|---|---|---|
| S1 部分后端失败 | **不能** | 没有"各存储物理位置"的 manifest，无法判断哪几个后端成功 |
| S2 切换中断 | **不能** | 没有原子激活指针；四后端各自切换正是文档指出的问题 |
| S3 内容覆盖 | **不能** | 幂等键缺 `config_version`，无法区分"同内容不同配置" |
| S4 迟到重试 | **不能** | 无 fencing token，无法拒绝旧代的结果 |
| S5 旧服务回退 | **不能** | 无代次标记，回退后新旧数据无法区分归属 |

**结论：P0-04 不是"跑几个测试就能关"，而是"先要有设计"。** 需要 `index-owner` 先给出：

1. `generation manifest` 的字段与存放位置（内容哈希、文档版本、解析/分块/embedding 版本、各存储物理位置）；
2. 激活指针的表结构与切换语义（单行原子更新？CAS？）；
3. 每 KB 的写入版本 + fencing token 形态（单调递增？租约？）；
4. outbox/补偿的归属（谁写状态、谁重试、失败如何落库）；
5. 任务租约与超时回收策略（当前完全没有）。

拿到 1–5 之后，S1–S5 才能变成可执行的测试；在此之前写"验证脚本"只是摆样子。

---

## 4. 附带发现（不影响结论，但值得修）

`getRetryTask()` 里第二个分支重复写了两次 `wrapper.eq(type, REPARSE)`（第 113 与 118 行附近），
属复制粘贴残留。功能上无害（同条件重复），但说明这段代码是赶出来的——
与 P0-04 的整体判断一致：**这里是"能用"，不是"有协议"。**
