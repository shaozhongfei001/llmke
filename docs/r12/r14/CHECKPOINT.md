# R14 持久检查点

> 新会话读完本节即可接手，不需要沿革叙述。
> 任务书：`/home/szf/data/dev/llmke/docs/LLMKE_R14_完整知识库最终交付长程任务_20261027.md`
> 仓库：`/home/szf/data/dev/llmke-r12`　基线：`feature/R12-real-rag @ 6f73985`（R14 改动未提交前以工作树为准）

## 1. 当前状态（2026-10-27 Loop 0/1 交界）

| 项 | 值 |
|---|---|
| 宿主 | CodeBuddy IDE（**无 CLI、无 `/goal`、无 hook 注册入口** — 已实测，见 §4） |
| 团队 | `r14-delivery`：A-data / B-graph / C-business / E-deliver / F-qa 已启动；D 前端待复用槽位 |
| 本轮已完成 | 收紧 4 处假绿断言（VERSION/GLOBAL/TABLE/S6/S7/denied）；建立能力矩阵；确认 F02 真实监听面 |
| 正在跑 | A：代次契约+社区去重；B：global 引用 host 重复+效果题；C：多版本夹具；E：基础设施收口+安装顺序；F：断言自检+基线+权限域 |
| 当前 FAIL（真实） | `r13_full_check.py --only VERSION`：kb_9 无 V0/V1 共存（两条都是 V0） |

## 1A. 文件所有权（R14 硬约束，避免并发改同一文件）

| 路径 | 唯一写入者 | 说明 |
|---|---|---|
| `platform/r12/qa/**`（四套脚本+证据） | **F-qa** | TL 不再改断言；如需变更走消息 |
| `platform/r12/{docker,conf,nacos,offline,systemd,preview}/**`、`bin/{up,r12ctl,offline-kit,install-paths,init-*}.sh` | **E-deliver** | |
| `services/rag-alg/index_data_service/**`（不含 index_graph_service） | **A-data** | |
| `services/rag-alg/index_data_service/index_graph_service/**`、`alg_retrieval_service/app/view/api/retrieval_global_view.py`、`platform/r12/graph/**` | **B-graph** | |
| `services/rag-java/**`、`services/rag-alg/alg_doc_parse_service/**` | **C-business** | |
| `frontend/plateform/src/**` | **D-frontend** | |
| `docs/r12/r14/**`、`bin/{check-exposure,r14-exit-check}.sh` | **TL** | |

已发生一次并发冲突：02:24 TL 与 F 同时改 `r13_full_check.cap_version`（结论一致，无回滚）。此后 qa 目录只归 F。

## 1B. 事故记录：02:26–10:05 全栈停摆（已恢复）

| 项 | 内容 |
|---|---|
| 触发 | E 收口基础设施时 recreate 容器，ES 容器重建 |
| 直接原因 | IK 插件是 R13 运行时 `elasticsearch-plugin install` 进可写层的，卷只挂 data → 重建即丢；mapping 硬编码 `ik_max_word` → 全部分片 ALLOCATION_FAILED，cluster **red**（54 unassigned） |
| 放大原因 | `r12-alg.service` 为 `RemainAfterExit=yes` + `Restart=no`，Nacos 抖动时 19995/19996/19526/19527 全部退出且**无人拉起**，单元进入 failed，停摆 7 小时 |
| 恢复 | 派生镜像 `r12/elasticsearch-ik:8.13.4`（Dockerfile 内 sha256 校验 + 插件目录非空断言）+ compose 指向该镜像；alg 手工 `systemctl --user restart` |
| 当前 | ES `yellow`（27 primary active、27 副本无处分配，单节点正常态）；kb_9=8 / faq=20 / community=7；问答 200 |
| 待办 | E：服务自愈 watchdog / Type=simple、副本数 0、启动等 Nacos readiness |

**教训（写进 R14 报告）**：基础设施"能重建"不等于"重建后能起来"。R13 把插件装进容器可写层，是典型的**不可复现部署**；systemd `Restart=no` 则是把"依赖抖动"放大成"长时间不可用"。

## 2. 下一条精确动作

1. 收 E 的监听面收口结果 → 复核 `ss -lntup` 中 r12-* 基础设施是否只剩 127.0.0.1，网关 8088/前端 18088 保留。
2. 收 C 的多版本夹具 → 复跑 `r13_full_check.py --only VERSION` 期望 PASS 且版本号集合含 V0 与 V1。
3. 收 F 的基线分类表 → 把"产品缺陷"逐条派给 A/B/C/D，把"夹具缺失"派给 C。
4. 派 D（前端）做 12 条浏览器旅程，前置是 E 收口完成（避免端口变更打断）。
5. 最终候选确定后，E 做一次完整干净安装（当前只能做到"独立目录+独立库"，不是独立主机，须如实标注）。

## 3. 不可再走的错误路线（已证伪）

- 只看 `git diff` 判定"已修复"（R13 撞过 4 次：配置缓存 / 未 daemon-reload / 镜像 CMD 硬编码 / 快照回退）。
- 只看脚本打印 `PASS` 结项（R13 的 VERSION 空列表、S7 空历史都是假绿）。
- 用 `pkill -f python` 或整栈重启（会打断其他人的在跑任务）。
- 直接用 `del_space` 删图数据（先在副本验证，或走新代构建+切换）。

## 4. 续跑机制的真实能力与限制（重要，不得夸大）

- 实测：`which codebuddy` 无输出；`~/.codebuddy/` 只有 plugins/skills/settings，无 hooks 注册；宿主是 IDE。
- 因此**不能用** `/goal` 或 Stop hook 做到"会话结束自动续跑"。
- 已提供的最小替代：`platform/r12/bin/r14-exit-check.sh`（读证据目录 + 台账，输出 CONTINUE/COMPLETE/WAITING_EXTERNAL），以及本检查点。
- 限制必须如实转述：**本会话结束不会自动重启执行**；需要人工重新发起并让执行者先读本文件。
- 若宿主后续提供 `/goal`，应把任务书 §0A-G 的条件原文灌入，而不是改写简化。

## 5. 关键路径与端口

- 前端 18088 / 网关 8088（唯一对外）
- 业务 18081-18085；算法 12340/19995/19996/19526/19527/19529/18095（已回环）
- 基础设施 MySQL 3306、ES 19200、MinIO 19000、Redis 16379、Nacos 18848、Nebula 19669、RocketMQ 19876 —— **R14 正在收口（E）**

## 6. 证据索引

| 主题 | 目录 |
|---|---|
| R13 四套终版 | `platform/r12/qa/evidence/{20261026T163339Z,SEC-*,REVOKE-*,CAPS-*}` |
| R14 收紧后基线 | `platform/r12/qa/evidence/CAPS-20261026T182423Z`（VERSION 真 FAIL） |
| R14 各角色 | `platform/r12/qa/evidence/R14-*` |

## 7. 构建纪律（R14 实测教训，F20）

**跨模块改动必须 install 依赖模块，否则 fat jar 里是旧字节码。**

- 现象：C 改了 `gien-starter-file-storage` 的 `getObjectNameFromUrl`（/minio 归一化），用 `mvn -pl rag-index-service package` 打包后运行态仍 500，而离线自检 6/6 通过 → **自检跑源码、运行跑旧类**。
- 验证方法：`unzip -p fat.jar BOOT-INF/lib/<dep>.jar > /tmp/d.jar && unzip -p /tmp/d.jar <Class>.class | strings | grep <特征串>`
- 正确命令：
```
mvn install -pl gien-starter-file-storage,rag-common -DskipTests
mvn package -pl rag-index-service,rag-qa-service -DskipTests
```
- 适用范围：`gien-starter-*`、`rag-common`、`tools-*` 等被业务模块依赖的所有模块。

## 8. 当前总账（2026-10-27 12:15）

| 套件 | 结果 |
|---|---|
| r13_full_check | 8/9（剩 GLOBAL：待归类——A 判"无依据题当正例"的夹具问题，B 判"refs=1 未达 ≥2"） |
| acceptance（独立库 kb_17） | 34/34 |
| security | 16/16 |
| revoke | 20/21（R3 global 同源） |
| permission_domain_scope | 8/8 |
| 合计 | **86/88**，2 条同一根因 |

已闭环：FAQ 直答（offset `break`）、大写开图 500（KeyError）、多 KB 静默丢结果、SSE 拒绝体 500 空、双 host、解析 pk 确定性、社区去重、索引幂等、`/minio` 归一化、presign MIME。
