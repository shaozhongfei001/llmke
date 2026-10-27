# R14 严格断言基线（F-qa）

- 证据目录：`platform/r12/qa/evidence/R14-BASELINE-20261027T021804Z`
- 生成时间：2026-10-27 10:18–11:10 CST（UTC+8）
- 脚本版本：本目录 `platform/r12/qa/{r13_full_check,acceptance,security_acceptance,revoke_acceptance,permission_domain_scope}.py`（R14 收紧版，工作树）
- 断言自检：`platform/r12/qa/assert_selftest.py` → **60/60 一致**；对 R13 旧断言同跑 → **26/60（34 条不符）**，证明本自检不是空转。

> 判定纪律：产品结论只取自"断言通过/失败"，且必须先排除环境。凡落在下述环境事件内或紧随其后的 FAIL，一律标 **环境待复测**，不计产品缺陷。

---

## 1. 环境前置（每套运行前记录）

| 时点 | date(本地) | `ss -lnt \| grep -c 1999` | `docker ps --filter name=r12-` 容器数 | 备注 |
|---|---|---|---|---|
| 10:18:04 | 2026-10-27T10:18:04+0800 | 2（仅 127.0.0.1:19995 / 19996） | 13 | ES=200（cluster yellow，27 replica 未分配，单节点预期）；19995/docs=200；19996/docs=200；18092/v1/models=200；网关登录 200 |
| 10:22:05 | 2026-10-27T10:22:05+0800 | 2 | 13 | |
| 10:24:33 | 2026-10-27T10:24:33+0800 | 2 | 13 | |
| 10:24:43 | 2026-10-27T10:24:43+0800 | 2 | 13 | |
| 10:35:23（第二轮） | 2026-10-27T10:35:23+0800 | 2 | 14 | 已发生 jar 热替换 + 服务重启，**该轮无效** |

时间窗声明：**02:26–10:05 的 7 小时故障窗（ES 丢 IK 插件 / r12-alg 不可用）早于本轮全部运行**，本轮所有起点均在 10:18 之后，故本轮 FAIL 不受该窗口影响。第二轮另起一段故障（见 §4）。

## 2. 第一轮（10:18–10:25，环境一致，**判定有效**）

| 套 | 主链严格通过 / 总数 | 耗时 | FAIL |
|---|---|---|---|
| `r13_full_check.py` | **4 / 7** | 207s | NORMAL（偶发，复测 PASS）、GLOBAL、GRAPH_LOCAL |
| `acceptance.py` | **30 / 31** | 142s | S7 |
| `security_acceptance.py` | **16 / 16** | 4s | — |
| `revoke_acceptance.py` | **21 / 21** | 29s | — |
| 合计 | **71 / 75** | 382s | 4 |

复测：`r13_full_check.py --only NORMAL,GRAPH_LOCAL,GLOBAL` → NORMAL **PASS**（73 字 / refs=3），GLOBAL、GRAPH_LOCAL 仍 FAIL（连续两次同败）。

## 3. FAIL 逐条归类

| # | 用例 | 实测 | 归类 | 依据 |
|---|---|---|---|---|
| 1 | NORMAL「智造贷最高额度」 | 首跑 `http=200 status=3 answer_len=16 refs=0`，答案=`模型暂无法返回，请稍后再试!!!`；复测 PASS | **偶发/待观察**（非稳定 FAIL） | 复测 1 次即通过；`model-llm.log` 无 error；按"连续两次同败才算 FAIL"不计缺陷；但首调冷启失败需 C 侧留意 |
| 2 | GLOBAL 跨文档归纳 | `refs=5`，source 全为 `http://127.0.0.1:19000/http://127.0.0.1:19000/r12-rag/kb_9/...`（host 重复拼接），答案为拒答「无法直接找到…具体关系描述」 | **产品缺陷（B-graph 主责，含 C 侧 endpoint 拼接待核）** | 证据 `CAPS-20261027T021804Z/GLOBAL.json`；两个独立缺陷：引用不可解析 + 未形成跨文档归纳 |
| 3 | GRAPH_LOCAL 图局部检索 | `docs=3 graph_docs=0`；直连 19529：`code=200, msg=查询成功，共0条文本数据, result_data=[], entity_list=['评级授信','放款','月度','60个基点',…]` | **产品/数据缺陷（B-graph + A-data）** | 实体能召回、正文回取为空；与 `platform/r12/graph/LOCAL-RETRIEVAL.md` 记录的 L1（`chunk_pk_list` 存旧代次 ES `_id`，重解析后失效）一致；19995 确实调用了 19529（`alg_retrieval_service.log` 10:25:58） |
| 4 | S7 历史对话可恢复 | `getDialogBySessionId?sessionId=r12-sess-1` → `data=None` | **夹具/断言缺陷（F-qa 自身，已修）** | S5 写入的 sessionId 是 `kb_9`（primitiveName），S7 却查从未创建的 `r12-sess-1`；且服务真实返回 `data.queryReplyPairList[{query,reply}]`，旧实现只遍历 list → 该断言在 R13/R14 早期**恒假**。修复后实测：`session=kb_9 问答对数=38 本轮queryId=q-… 命中=True` PASS |
| 5 | VERSION 多版本 | `groups=1 多版本组=1 版本=['V0','V1','V0']` → **PASS** | 原"已知预期红"消除 | C 的多版本夹具已落库 |

## 4. 第二轮（10:35 起）——**判定环境无效，不作产品结论**

| 时刻 | 事件（实测） |
|---|---|
| 10:29:24 / 10:29:27 | `rag-index-service` / `rag-qa-service` 的 target jar 被重新构建，但两 JVM 是 **10:02:34** 启动的（仍在跑被替换的 jar）→ 懒加载失败 `ClassNotFoundException: org.springframework.boot.web.error.ErrorAttributeOptions$Include`；拒绝态变 500 空体。示例：`r13_noauth` + `configId=1` 提问 = 500（10:24 时同用例为 403 PASS） |
| 10:31:29 | rag-qa-service 重启（新 jar）。 |
| 10:33 | rag-index-service 未注册到 Nacos → qa 日志 `[503] Load balancer does not contain an instance for the service rag-index-service` → 权限校验抛"没有足够权限" → 500 |
| 10:34:20 / 10:34:49 | rag-index-service 启动 / 18082 开始监听；admin 提问恢复 200 |
| 10:35:54–11:05 | `acceptance.py` S4：fileId=313/314/315 三个解析任务各卡 600s 至 `status=None`（doc-parse 链路未就绪）→ 该轮 S4 FAIL 全属环境 |
| 11:06 起 | 8088 / 18082 / 18083 全部停止监听（整栈拆除重装中），QA 停止一切请求 |

该轮临时读数（**不采信**）：`r13_full_check` 4/7（FAQ `resultType` 由 2 变 1、GLOBAL `refs` 由 5 变 0）、`acceptance` 因解析卡死出现 3 条 S4 FAIL。

## 5. 本轮新增的真实产品缺陷（与上述环境事件无关，可复现）

**SSE 内容协商把 403 变成 500**（归 C-business，`GlobalHandler` / `AiController` produces）

```
user=r13_noauth Accept='text/event-stream'                    -> http=500 ctype=None body=''
user=r13_noauth Accept='text/event-stream, application/json'  -> http=403 ctype=application/json
                                                                 body={"success":false,"errorMsg":"没有足够权限","errorCode":"30016","data":null}
user=admin      Accept='text/event-stream'                    -> http=200 ctype=text/event-stream
```

- 证据：本目录 `sse_deny_probe.txt`（2026-10-27T10:35:19+0800）。
- 前端实际只发 `Accept: "text/event-stream"`（`frontend/plateform/src/**/servers.ts:231/290/292`），因此真实用户在无权限时拿到的是 **500 空体**，无法区分"无权限"与"服务故障"。
- 与 jar 热替换无关：该现象在服务重启、jar 与进程一致之后仍复现。

## 6. 覆盖与未覆盖

- 已覆盖：主链 8 场景、能力矩阵 7 项、对象授权 16 项、撤权全链 21 项、权限域对照（A 同问对照 / B 跨域提问）。
- 未覆盖 / 待办：多版本（V0/V1）维度的权限域对照（依赖 C 的多版本夹具）；前端 12 条浏览器旅程（D）；干净主机安装（E，当前只能做到"独立目录+独立库"）。

## 7. 断言自检（每次改断言后必跑）

| 被测脚本集 | 结果 | 证据 |
|---|---|---|
| R14 收紧版（5 个脚本） | **60 / 60 与期望一致** | `evidence/R14-SELFTEST-20261027T023154Z` |
| R13 旧断言（`git show HEAD:` 导出版） | **26 / 60**，34 条不符 | `evidence/R14-SELFTEST-20261027T023154Z-r13qa` |

本轮新增/收紧的自检用例：S7-5~S7-10（真实 `queryReplyPairList` 结构、缺答案、缺提问、必须命中本轮 queryId）、F05-OOD-1/2（跨域引用判定）、F05-5XX-1/2（5xx 不得当拒绝）。

## 8. 待办（明确依赖外部）

1. E 重装完成 → 复跑四套 + F05，出洁净基线（预计 9 分钟）。
2. C 修 SSE 拒态 500 → 复跑 security/revoke 中的拒绝态用例。
3. B 修 GLOBAL 引用 host 重复 + 跨文档召回；修/重建图代次（GRAPH_LOCAL）。
4. C 提供多版本夹具后补"多版本 × 权限域"对照。

> 后续：本轮（首轮）结论已被洁净轮取代，见 ../R14-BASELINE-CLEAN-20261027T032432Z/summary.md（83/86，3 FAIL→2 个产品缺陷，无环境 FAIL）。
