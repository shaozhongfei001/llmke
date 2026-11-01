# 跨实例共享配额（MySQL 计数窗口）2026-11-01

## 1. 要解决的问题

`quota.py` 的令牌桶只在**单进程内**成立：3 副本部署时每个实例各自计数，
"配额 100 QPS"实际是 3 × 100，面板上还看不出来。缺口不是"限流不够准"，
而是**上限不存在**——扩副本就等于扩额度。

本机没有可靠的 Redis 客户端，因此复用已经存在的 MySQL（隔离库 `gienrag_v2_restore`，
端口 13306）做计数器：所有实例共用同一张表，靠主键冲突走到一次原子 UPDATE。

## 2. 实现

文件：

| 文件 | 作用 |
|---|---|
| `services/rag-alg/index_data_service/graph_engine_adapter/quota_shared.py` | `SharedQuotaCounter` / `SharedQuotaError` / `DDL` / `ensure_schema` / SQL 常量 |
| `.../graph_engine_adapter/sql/003_shared_quota.sql` | 给 DBA 预建的同一份 DDL（与 `quota_shared.DDL` 逐字一致） |
| `tests/test_quota_shared.py` | 17 项单测（假连接，不连真库） |

计数原语（一个事务内完成）：

```
DELETE  只删本租户 window_start < 当前-retention 的旧窗口（每租户每窗口一次）
INSERT  INTO v2_quota_window (tenant, window_start, used) VALUES (%s,%s,%s)
        ON DUPLICATE KEY UPDATE used = used + %s          -- 原子自增，不先 SELECT
SELECT  used ... WHERE tenant=%s AND window_start=%s        -- 读自己这一行（含本次）
        used > limit  → UPDATE used = GREATEST(used - %s, 0) 然后重新 SELECT
COMMIT
```

三个关键决定：

1. **必须"先增后判"**。先 `SELECT` 再 `UPDATE` 会在两个实例间丢更新（都读到 2、都写 3），
   额度凭空多一份。用主键冲突把读-改-写合成一条语句，行锁天然串行化。
2. **被拒必须扣回**。判断用的是"含本次"的计数，所以超限时要把本次自增退掉；
   否则 limit=3 的租户在第 4 次请求后，**本窗口内永远**不再放行（表现为"没跑满却一直 429"），
   且只有等下一窗口才自愈——线上几乎无法定位。退款与判断同事务，不存在退一半。
3. **失败 fail-closed**。数据库不可用时返回 `allowed=True` 等于配额失效（比没有配额更糟：
   看起来有保护，实际全开）。这里一律抛 `SharedQuotaError`，消息带操作名/租户/驱动摘要，
   不含连接串与口令，由调用方决定拒绝或降级。

窗口是**固定窗口**（`window_start = floor(epoch / window_s)`），不是严格滑动窗口：
边界上允许最多 2 × limit 的瞬时突发，换来每次计数只有"一行 UPSERT + 一行 SELECT"。
要更严格应上预扣额度 + 下窗口预留（GCRA），不在本次范围。

## 3. 单测（17 项，假连接）

```
$ cd /home/szf/data/dev/llmke-v2 && PYTHONPATH=services/rag-alg/index_data_service \
    /home/szf/data/dev/llmke-v2-toolenv/bin/python -m pytest tests/test_quota_shared.py -q
.................                                                        [100%]
17 passed in 0.05s
```

覆盖：未超限递增 / 恰好等于 limit 放行、超 1 个拒绝 / **被拒后计数回到 limit 以内** /
窗口滚动重新放行 / 租户互不影响 / 旧窗口被清理且不动当前窗口 / 清理不碰别的租户 /
连不上 → `SharedQuotaError`（fail-closed）/ 事务中途失败不留半截自增 / `stats()` 只含计数 /
批量 `n > limit` 拒绝且不占额度 / `wait_take` 等到下窗口、超时放弃不占额度 /
DDL 与 SQL 文件不漂移 / SQL 语句语义（`used = used + %s`、`GREATEST(used - %s, 0)`、租户谓词）/
参数校验（`n=True`、`n=0`、`limit=0`、`window_s=0`、`retention_windows=0`）。

假连接不是"按预期语义执行"，而是**按 SQL 文本的谓词执行**（有 `tenant = %s` 才限定租户），
并带暂存-提交-回滚，因此改坏 SQL 或改坏事务边界都能被验出来。见下节变异记录。

## 4. 变异验证（证明断言不空转）

| 变异 | 结果 |
|---|---|
| `if over:` → `if False:`（跳过退款） | **6 项失败**（含 `test_denial_does_not_consume_quota`、`test_batch_n_larger_than_limit_...`）；恢复后 17 passed |
| `SQL_PRUNE` 去掉 `tenant = %s`（全表删） | 首次**未被捕获**，补强后 **2 项失败**（`test_prune_never_touches_other_tenants`、`test_sql_statements_keep_their_semantics`） |
| `raise self._fail(...)` → `return True, 0`（fail-open） | **1 项失败**（`test_mid_transaction_failure_leaves_no_partial_increment`，`DID NOT RAISE`）；连接失败路径由 `test_connection_failure_is_fail_closed` 单独钉住 |

第二行是本次最有价值的一条：初版假驱动**替 SQL 补上了租户谓词**，
于是"全表 DELETE"改坏后测试照样全绿——断言测的是假驱动的意图，不是真实 SQL。
处置：假驱动改为按 SQL 文本判断作用域（无谓词即跨租户删），并新增
`test_sql_statements_keep_their_semantics` 直接断言语句常量里的算术与谓词。
变异前后均恢复文件并核对 md5（`quota_shared.py` = `61e3de2d4de93fd449451915777e5a85`）。

## 5. 真库验证（隔离库 `gienrag_v2_restore`，13306）

单实例，`limit=3, window_s=2.0`，连续 5 次 `take`：

```
tenant       t-quota-1001394
allowed      [True, True, True, False, False]
used         [1, 2, 3, 3, 3]
window_start [896771953, 896771953, 896771953, 896771953, 896771953]
retry_after  [None, None, None, 1.696, 1.676]

stats        {'used': 3, 'limit': 3}
rows         (('t-quota-1001394', 896771953, 3),)
```

`rows` 里是 **3 而不是 5**：两次拒绝各退回自己那 1，计数没有被永久占用。
`used` 序列停在 3、`retry_after_s` 递减（下个窗口越来越近）也与固定窗口语义一致。

跨实例（两个 `SharedQuotaCounter`、各自独立连接，模拟 2 副本），交替 6 次：

```
两个实例交替 6 次 allowed -> [True, True, True, False, False, False]  放行总数 = 3
窗口滚动后          -> {'allowed': True, 'used': 1, 'window_start': 896771957}
rows                -> (('t-quota2-1002003', 896771956, 3), ('t-quota2-1002003', 896771957, 1))
```

放行总数 = 3（单实例配额会是 6），`window_start` 递增后新窗口从 0 起算，
上一窗口的行保留（供对账与滞后清理）。两次运行都以自己的 `t-quota-*` / `t-quota2-*` 前缀
删净，未触碰其它租户的行。

## 6. 没做 / 边界

- **没接活**：`quota.py`、`lease_mysql.py`、metrics 导出层、HTTP 入口一行未改。
  `SharedQuotaCounter` 目前没有调用方，接入（实例化 + `take` 放在请求入口、
  `stats()` 接指标）属于接线工作，本次未做；因此"3 副本总量不再 ×3"尚未在真实部署上验证。
- **固定窗口的 2×limit 边界突发**是已知取舍，未做滑动窗口/GCRA。
- **行锁串行**：同一租户同一窗口的所有计数在 MySQL 行锁上排队，
  极热租户的吞吐上限取决于单行 UPDATE 的 RT；未做本地批量合并（会把精度换回来）。
- **未做并发压测**：跨实例验证是两实例交替调用，不是多线程/多进程高并发；
  "不丢更新"由 SQL 语义（主键 + `used = used + %s`）保证，未用压测数值证明。
- **未验证 MySQL 宕机后的自愈**：fail-closed 只保证"算不出来就报错"，没有自动降级到进程内桶，
  也没做"恢复后自动接回"的演练。
- `stats()` 每个窗口一次 `WHERE window_start = %s` 扫描（当前窗口行数 = 活跃租户数），
  租户极多时应改为增量指标导出，未做。
- `retention_windows` 默认 60：清理只在"该租户本实例首次进入新窗口"时触发，
  长期无请求的租户旧行会留到它下次被调用才清；未加独立清理任务（避免引入全表 DELETE 风险）。
- 顺带观察（与本改动无关）：`tests/test_security_scan.py::test_framework_repo_itself_is_clean`
  在本次改动前即为失败（`security-check: FAIL (1739 finding(s))`），
  命中列表中不含本次新增的两个文件。
