# 第三波收口：C4 灰度判定 / 镜像 load / Q 自举与续跑（2026-11-01）

四个角色并行（canary / deploy / quality / filter），TL 负责接线与验收。下面只写**真跑过**的数字。

## 1. C4 灰度判定（`scripts/v2_canary_verdict.py`）

把 C2（结构/抽取）+ C3（检索）+ 基线噪声合成**一个**结论，而不是让人肉对着三份 JSON 心算。

判据：`UNSAFE`（块集合不同 / 检索 top1 不一致 / 路线变化 / 基线本身不稳）、
`REVIEW`（事实有差异但检索一致）、`SAFE`（全一致）。退出码 SAFE=0 / REVIEW=1 / UNSAFE=2。

真跑：

```
--a /tmp/dual-full --a2 /tmp/dual-full2 --b /tmp/delta-drill/snapshot-...-g0
→ verdict = REVIEW (exit 1)
→ chunks identical=true, facts only_b=1, retrieval top1/ordered/jaccard 全 1.0
→ reasons: 抽取事实存在差异：only_a=0 only_b=1（检索未见差异，需人工核对差异清单）
```

**REVIEW ≠ 可以切**：它表示"现有证据既不能否决也不能放行"。这正是 C2 发现的那 1 条差异
（`董事会|审议通过|单笔授信`），C3 证明它没传导到检索层，C4 把它固定成"待人工裁决"。

单测 14 项，覆盖"事实有差异但检索一致必须是 REVIEW 而不是 SAFE"这类误判。

## 2. 镜像 load 覆盖检测（`scripts/v2_image_load_drill.py`）

之前只校验 tar 的摘要/标签/层，**刻意没 load**——怕覆盖在用 tag。真到离线机现场才发现问题代价最大。

真跑（redis tar，39MB）：

```
load_seconds=0.1, already_present=true, overwrote_existing=false,
container: started=true, health_ok=true, cleaned_up=true, probe_seconds=2.4
```

安全约束写死在代码里：只**记录**是否覆盖（含 `previous_image_id`），**绝不自动 rmi**；
起容器用随机端口并在 `finally` 里 `docker rm -f`。单测 7 项用注入执行器测判定，
含"ID 不同必须报覆盖""探活失败仍要清理"。

注意：`docker ps -a --filter ancestor=redis:7.4.10-alpine` 会列出 `r12-redis`、`yuxi-redis-1`
等**既有的**基础设施容器，不能拿它当"我的演练容器没清理"的证据；清理依据是 `cleaned_up=true`。

## 3. Q 自举（`ensure_payloads`）

6 项图检查依赖 `/tmp/ingest-333.json`、`/tmp/ingest-329.json`。换机器或 /tmp 被清，
这些检查整片 SKIP——报告仍是 PASS，但少测了半边。

真跑（先 `mv` 走两个载荷再调用）：

```
paths ['/tmp/ingest-333.json', '/tmp/ingest-329.json']
ingest-333.json 4582 bytes, chunks 3
ingest-329.json 4016 bytes, chunks 2
```

生成失败**抛 `PayloadBootstrapError`**，不退化成 SKIP——"造不出验收数据"是环境问题，不是能力缺失。

踩到的坑：生成器产出的是**简化投影**（缺 `status/mode/artifact_id/channels/field_fill`），
比我手工准备的那份少了元数据。跑完 Q 后把原文件从 `.bak` 还原：
**自举是兜底，不该覆盖真实样本**。这条要写进使用说明。

## 4. Q 断点续跑（`--checkpoint/--resume`）

整轮 Q 要 40+ 分钟，任一检查卡住就丢掉**整份**结果。现在每条 `record()` 即时落盘，
`--resume` 按**函数**粒度续跑：上一轮该函数产出的记录**全是 PASS** 才跳过，有一条 SKIP/FAIL 就重跑
（SKIP 往往意味着环境变了，不能当"上次过了"）。

实测：`--resume` 跳过 35 个检查函数 → 54 PASS / 0 FAIL / 0 SKIP / 1 NOT_IMPLEMENTED（缺 Office Writer）。

## 5. 端到端问答的采样抖动（顺带修）

上一轮全量 Q 出现一次 `biz:端到端业务问答` FAIL：`reason=INVALID_CITATION`、`citations=0`，
单独复跑立即 PASS。根因不是检索坏了，是**回答模型采样**偶发给出不是原文子串的 quote。

一次抖动记 FAIL 会把真回归淹掉，所以改成失败重试一次，并把 `attempts` 写进报告；
两次都失败才判 FAIL（那多半是检索/引用链路真坏了）。

## 6. 检索后置过滤（`retrieval_filter.py`，角色产出，TL 验收）

`filter_hits` 按断言 `effective_from/to` 与可见域过滤命中：
- 版本过滤**部分来源过期不误杀整块**，无日期事实计入 `unknown_window`（不能因为没写日期就当过期）；
- 可见性过滤**查不到可见域就丢**（fail-closed）——与版本过滤方向相反是有意的。

11 项测试通过。**没有接进 pipeline 默认路径**，所以 `capabilities` 里只升到 `NOT_VERIFIED`，
不写成"引擎检索已按生效期约束"。

## 能力声明变更

| 能力 | 之前 | 现在 |
|---|---|---|
| `incremental_update` | NOT_IMPLEMENTED | VERIFIED（C2 证据） |
| `delete_document` | NOT_IMPLEMENTED | VERIFIED（文本差集删除） |
| `graph_export` | NOT_IMPLEMENTED | VERIFIED（本轮） |
| `engine_version_filtering` | NOT_IMPLEMENTED | NOT_VERIFIED（有实现、未接线） |
| `engine_visibility_isolation` | NOT_IMPLEMENTED | NOT_VERIFIED（有实现、未接线） |

## 还没做

- 真实告警通道（Webhook 有了，但没有企业微信/钉钉网关可用，签名与鉴权未做）；
- doc2md 的 5 项 CLI-help 失败在**另一个仓库**（`fix/017-ir-emission-wiring`），本轮未动；
- 谓词归一仍未实现；
- 大库/高相似语料上的灰度判定（当前 3 块语料区分度太高，结论不可外推）。
