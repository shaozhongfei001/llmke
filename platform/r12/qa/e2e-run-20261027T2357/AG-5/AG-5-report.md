# AG-5 验收报告：上传 · 解析状态 · 收敛

- 角色：AG-5（写入角色，独占写锁 `evidence/.write-lock`：11:10:09 建，收工删）
- 运行目录：`/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357`
- 执行窗口：2026-10-28 11:10:09 – 11:38（本地时间）
- 自建库：`R14-E2E-AG5-1111`（**id=36**，取自建库响应 `data.id`）；
  `R14-E2E-AG5-1121-C`（**id=37**，专用于"全新库首建索引"并发窗口）
- 未触碰：`kb_9`（id=9，业务语料）、`kb_22` 及任何既有库；未重启服务、未改配置、未改数据库、未 git 提交

---

## 0. 第 0 步自证：我测的是哪一版

```
入口包  assets/index-fup9RT0c.js
curl http://127.0.0.1:18088/assets/index-fup9RT0c.js → http=200, 315489 B
md5(served) = 5161c957f19bb7f1ee825ca33d6771cc
md5(dist)   = 5161c957f19bb7f1ee825ca33d6771cc      ← 两哈希相同（收工复核仍相同）
证据：AG-5/evidence/S0/preflight-2026-10-28T111119+0800.json ; env/pids-closed.txt
```

**中途发生一次前端部署（11:11 前后），后端未重启**：

| | 旧包 | 新包（本轮全部 UI 证据使用） |
|---|---|---|
| entry | assets/index-CpE2zvYY.js | assets/index-fup9RT0c.js |
| md5 | de2424501bd29e358043049876db2a75 | 5161c957f19bb7f1ee825ca33d6771cc |
| bytes | 315576 | 315489 |

- 我 11:10 手工 curl 时仍是旧包；11:11:17 起取到新包，此后所有页面证据均为新包 `5161c957`。
- 11:11 之后我的第一条上传请求在 11:15:12，**无请求落在容器重启那 8 秒内**，无需剔除样本。
- 登记：`AG-5/evidence/env/ENV-EVENT-frontend-redeploy.md`

**另一件我自己发现、必须自己声明的环境事件**：检索服务 19995 于 **11:28:16** 重启过一次
（pid 922468 → 1079761，启动时刻取自 `ps lstart`）。核对结果：S3/S4 不走 19995（不受影响）；
S14 全部检索样本产生于 11:30:45 之后，**同一新代次**，无跨代混采。
登记：`AG-5/evidence/ENV-ALERT-20261028T1138.md`

服务代次（开工 → 收工）：

| 端口 | 开工 pid | 收工 pid | 一致 |
|---|---|---|---|
| 8088 网关 | 925533 | 925533 | 是 |
| 18082 | 923878 | 923878 | 是 |
| 18083 | 1647331 | 1647331 | 是 |
| 19527 全文 | 922312 | 922312 | 是 |
| 19529 图 | 1461792 | 1461792 | 是 |
| 19995 检索 | 922468 | **1079761** | 否（11:28:16 重启，见上） |

---

## 1. 一页总表

| 场景 | 判定 | 断言通过/总数 | 耗时 | 关键证据 |
|---|---|---|---|---|
| S3-1 docx（纯文本） | PASS | 5/5 | 上传 0.14s + 解析 6.1s | `S3/S3-case-docx-plain.json` |
| S3-2 docx（含表格） | PASS | 5/5 | 0.10s + 22.2s | `S3/S3-case-docx-table.json` |
| S3-3 xlsx（台账） | PASS | 5/5 | 0.09s + 14.1s | `S3/S3-case-xlsx-ledger.json` |
| S3-4 pptx | PASS | 5/5 | 0.16s + 8.1s | `S3/S3-case-pptx-intro.json` |
| S3-5 数字版 PDF | PASS | 5/5 | 0.10s + 14.1s | `S3/S3-case-pdf-digital.json` |
| S3-6 扫描版 PDF | PASS | 5/5 | 0.32s + 14.1s | `S3/S3-case-pdf-scanned.json` |
| S3-7 docx（业务件） | PASS | 5/5 | 0.14s + 14.1s | `S3/S3-case-docx-loan.json` |
| S3-8 负例：加密 PDF | PASS（正确失败） | 3/3 | 14.1s | `S3/S3-case-neg-encrypted-pdf.json` |
| S3-9 负例：文本改 .pdf | PASS（正确失败） | 3/3 | 44.3s | `S3/S3-case-neg-bad-pdf.json` |
| S3-10 负例：随机字节改 .docx | PASS（正确失败） | 3/3 | 44.3s | `S3/S3-case-neg-bad-docx.json` |
| S3-11 负例：截断 docx | PASS（正确失败） | 3/3 | 46.3s | `S3/S3-case-neg-truncated-docx.json` |
| S3-12 3 并发（已有索引库） | PASS 3/3 入库 | 9/9 | 0.14s + 解析 | `S3/S3b-batch-interrupt-*.json` |
| S3-13 3 并发（**全新库首建索引**） | PASS 3/3 入库 | 9/9 | 0.21s + 解析 | `S3/S3c-freshkb-concurrent-*.json` |
| S3-14 上传中断 + 重试 | PASS | 3/3 | 内联 | `S3/S3b-batch-interrupt-*.json` |
| S4-1 状态流转（API 0.3s 采样） | PASS | 2/2 | 12–15s/次 | `S4/S4-retry2-*.json` |
| S4-2 页面两态可见 | PASS | 2/2 | — | `S4/ui/01-filelist.png`、`S4/ui2/01-hover-failed.png` |
| S4-3 页面自动刷新 | **FAIL**（25s 内 0 请求） | 0/1 | 25s 观测 | `S4/ui2/s4-ui2.json`、`S4/ui/02-after-20s.png` |
| S4-4 失败原因可见 | **FAIL**（只给通用文案） | 0/1 | — | `S4/ui2/s4-ui2.json` tooltip |
| S4-5 重试产生新任务 | PASS | 2/2 | UI/API 各一次 | `S4/S4-retry2-*.json`、`S4/ui3/s4-ui3.json` |
| S4-6 超过阈值仍"解析中" | **FAIL**（任务拖在 DEAL_ING，12m31s 后才被僵尸兜底回收） | 0/1 | 12m31s | `S4/S4-stuck-task-564.json` |
| S14-1 新版本检索收敛 | PASS | 2/2 | 30s | `S14/S14b-converge-*.json` |
| S14-2 删除后三处收敛 | PASS | 3/3 | 6s 等待 | `S14/S14-delete-rejudge-*.json` |
| S14-3 重解析后引用代次 | **FAIL**（version 被清空） | 1/2 | 15s | `S14/S14c-version-null-*.json` |

合计：**80 通过 / 84 已执行**（另有 7 项判据 N/A，见 §5）。缺陷 **8 条**：P0 0 / P1 0 / **P2 6** / **P3 2**。

> **读这张表前必须知道的三条判据（TL 要求写在结论旁）**
>
> 1. **文件级 3 = 解析成功，任务级 3 = RETRY_ING —— 同名不同义。**
>    不改这一条，上表 7 个正例会被整片判成"重试中/超时"的**假红**。
>    这与"改一个请求字段以为在测同一件事"是同一类错误：**字段/枚举同名不等于同义**。
> 2. **表格块不在主索引。** xlsx / 含表格 docx 的块只落在 `table_chunks_*` / `table_summary_*`；
>    只查 `kb_<id>` 会把成功判成"成功但 0 条"（假红）。
> 3. **检索在 `enabled_rerank=false` 时无阈值过滤，且响应里没有 `metadata.pk`（恒 None）。**
>    按"返回条数"判残留会假红，按 pk 判代际会恒真（假绿）；代次锚点只能用 ES 侧 `pk + create_time` 与内容。

---

## 2. 每条明细

### 2.1 S3-1~S3-7 逐格式上传（判据 v2）

```
前置：admin 登录（simpleLogin，服务端签发 token）；自建库 id=36（响应取）；三索引初始均 404
步骤：每个文件单独 uploadFileList（串行，绝不并发）→ 轮询文件状态至终态
      → 查 ES 三索引（kb_36 / table_chunks_kb_36 / table_summary_kb_36）该 file_id 的块数与 create_time
      → 查 file_parse_task 任务级状态
期望：① 接口 success=true 且有 file_id
      ② 任务级终态 = 4(SUCCESS)（响应体不含 task_statuses，口径见下）
      ③ 文件级终态 = 3(解析成功)
      ④ 跨三索引至少 1 条该 file_id 的块，且 create_time ≥ 请求时刻
      ⑤ /file/getFileChunks 能取到正文
实际（逐个，全部满足）：
  docx-plain  fid=493 文件=3(解析成功) 任务 537=SUCCESS 块 1  ct 11:15:15 > 请求 11:15:12
  docx-table  fid=494 文件=3(解析成功) 任务 538=SUCCESS 块 3（主 1 + table_chunks 1 + table_summary 1）
  xlsx-ledger fid=495 文件=3(解析成功) 任务 539=SUCCESS 块 2（都在 table_chunks / table_summary，主索引 0）
  pptx-intro  fid=496 文件=3(解析成功) 任务 540=SUCCESS 块 1
  pdf-digital fid=497 文件=3(解析成功) 任务 541=SUCCESS 块 2
  pdf-scanned fid=498 文件=3(解析成功) 任务 542=SUCCESS 块 1
  docx-loan   fid=499 文件=3(解析成功) 任务 543=SUCCESS 块 1
判定：PASS 7/7
证据：AG-5/evidence/S3/S3-final-summary-2026-10-28T111928+0800.json（判据 v2 复核）
      AG-5/evidence/S3/S3-case-*.json（单例原始响应、状态采样、ES 明细）
复跑：PYTHONPATH=scripts <venv>/bin/python scripts/s3_upload.py && PYTHONPATH=scripts <venv>/bin/python scripts/s3_rejudge.py
```

**口径（必须写清，否则会被误读成"漏验"）**：`uploadFileList` 响应体**不含 `task_statuses` 键**
（11 例逐条记录 `has_task_statuses_key=false`）。`task_statuses` 只出现在失败时
`file_parse_task.error_msg` 的内嵌 JSON 里（见 2.2）。因此 §1.3① 的等价校验取
「任务级 status=4(SUCCESS) + 文件级 status=3(解析成功) + 跨索引有块且 create_time 晚于请求」三条同时成立。

**判据 v1 的两个自曝缺陷（改判据，不改结论）**：

1. **枚举读反**：文件级 `KbFileStatusEnums` 是 `3=解析成功 / 4=解析失败`；任务级
   `ParseTaskStatusEnums` 是 `3=RETRY_ING / 4=SUCCESS`。第一版把文件级 3 当"重试中"，会把全部正例判成假红。
2. **只查主索引**：xlsx / 含表格 docx 的块落在 `table_chunks_*` / `table_summary_*`，
   第一版据此把 xlsx 判成"成功但 0 条"（假红）—— 正是 QA-SPEC §1.6 警告的坑。
   v2 改为跨三索引判（xlsx 实测 2 条、docx-table 3 条）。

### 2.2 S3-8~S3-11 负例：坏文件必须失败且可见

```
步骤：加密 PDF（pypdf RC4-128，user_pw=123456；自证：无密码取页抛 FileNotDecryptedError，带密码可读）
      / 纯文本改 .pdf / 随机字节改 .docx / 合法 docx 截断 60% → 各自单独上传
期望：不得"接口 200 静默成功"，不得"成功但 0 条"；必须有可见失败信号
实际：
  encrypted.pdf    fid=500 文件=4(解析失败) 任务 544=DEAL_FAIL 重试 1/3 块 0
      fail_reason="解析失败："                        ← 原因文本为空（缺陷 AG5-D2）
  bad-renamed.pdf  fid=501 文件=4 任务 545=DEAL_FAIL 3/3 块 0
      fail_reason="解析失败：No /Root object! - Is this really a PDF?"   可读
  bad-renamed.docx fid=502 文件=4 任务 546=DEAL_FAIL 3/3 块 0
      fail_reason="解析失败：File is not a zip file"                     可读
  truncated.docx   fid=503 文件=4 任务 547=DEAL_FAIL 3/3 块 0
      fail_reason="解析失败：File is not a zip file"                     可读
判定：PASS 4/4（"失败可见"成立；但 4 例的用户侧文案都是通用句，见 AG5-D1）
证据：S3/S3-fail-reason-utf8mb4.json（utf8mb4 复采原文）、S3/S3-case-neg-*.json
复跑：scripts/s3_upload.py（负例段）
```

> 取证自查：首轮用默认字符集 mysql 客户端取 `error_msg`，中文显示成 `?????`，我一度准备按
> "失败原因乱码"上报。改用 `--default-character-set=utf8mb4` 复采后确认**是我方客户端编码问题，
> 不是产品乱码**，已按事实改判（`S3-fail-reason-utf8mb4.json` 内记录这次自我纠正）。

### 2.3 S3-12/13 并发上传（两类窗口都测）

```
S3-12 已有索引的库（kb_36）：3 个文件同时 POST → 0.14s 内全部返回
  逐文件确认 3/3 都有 DB 行 + ES 块 + 终态 3 → 无静默丢失
S3-13 全新库（kb_37，三索引均 404）首次 3 并发：0.21s
  AG5-CONC1-pdf  fid=514 主索引 2 块
  AG5-CONC3-xlsx fid=515 table_chunks 1 + table_summary 1
  AG5-CONC2-docx fid=516 主 1 + table_chunks 1 + table_summary 1
  索引由上传自动创建（kb_37=3 / table_chunks=2 / table_summary=2）
判定：PASS 6/6（两轮），均未复现"建索引 400 被吞 → 文件静默丢失"
边界：仅 2 轮 N=6 个文件，不是穷尽；不能据此写"并发缺陷已不存在"
证据：S3/S3b-batch-interrupt-2026-10-28T112102+0800.json、S3/S3c-freshkb-concurrent-2026-10-28T112210+0800.json
```

### 2.4 S3-14 上传中断（注入，已标注）

```
注入方式：客户端 timeout=0.1s 主动中断 POST（非服务端故障，与真实故障分开记）
实际：客户端得到可读错误 ReadTimeout: Read timed out. (read timeout=0.1)
      随后正常超时重传同名文件 → fid=513 入库成功（主索引 1 块，终态 3）
判定：PASS 3/3
副作用（真实缺陷，非注入造成）：被中断的那次上传留下 2 条**永不派发的 PENDING 任务**
      （task 551 / 556，文件 507/512 已被后续覆盖上传置为"已删除"，17 分钟后仍 status=1）→ 缺陷 AG5-D7
证据：S3/S3b-batch-interrupt-*.json（DB 复采见 §3 AG5-D7）
```

### 2.5 S4-1 状态流转可见（接口层，0.3s 密集采样）

```
步骤：对文件调 filesParse（前端真实 payload，见 2.7），0.3s 一次轮询 getFileStatusById
实际：
  成功文件 fid=493 → 99(解析排队中) → 2(解析中) → 3(解析成功)，新任务 563
  失败文件 fid=503 → 99(解析排队中) → 4(解析失败)，新任务 564
  两次都抓到中间态（intermediate_seen=true）
判定：PASS 2/2（接口层流转完整可观测）
证据：S4/S4-retry2-2026-10-28T112730+0800.json
```

### 2.6 S4-2/S4-3 页面：两态可见，但不自动刷新

```
步骤：注入式会话打开 /chats/knowledgeBase/36（新包 5161c957），读表格每行文本；
      静默 20s 观察请求；另起进程上传新文件后再静默 25s
实际（页面文本原文节选）：
  "AG5-BATCH2-docx-112039.docx  1  自定义切片  解析完成  26-10-28 11:20  重新解析  删除 ..."
  "truncated.docx  0  自定义切片  解析失败  26-10-28 11:18  解析  删除 ..."
  → 两种状态都在页面上真实可见；失败行操作按钮是"解析"，成功行是"重新解析"
  → 点击失败文件名：toast「文件解析状态为【解析失败】，无法进行单文档问答！」
自动刷新实测：
  静默 20s：requests_in_window = 0
  上传 AG5-LIVE-112518.docx（fid=517）后静默 25s：requests_in_window = 0，
      visibleAfterWait = false；手动 reload 后 visibleAfterReload = true
判定：S4-2 PASS 2/2；S4-3 FAIL（页面永不自动更新）
影响：排队→解析中两个中间态在页面上基本看不到（缺陷 AG5-D3）
证据：S4/ui/01-filelist.png、S4/ui/02-after-20s.png、S4/ui2/s4-ui2.json、
      S4/ui2/04-after-upload-25s.png、S4/ui2/05-after-reload.png
备注：本场景为注入式会话（simpleLogin token 写入前端 AppStorage），未走图形验证码；
      按 FINAL-REPORT §六口径，登录流程结论归 AG-1，本处只判页面内容。
```

### 2.7 S4-4 失败原因可见性（FAIL）+ S4-5 重试入口（PASS）

```
步骤：hover 失败行的"解析失败"文字 → 抓 tooltip 原文；再点该行"解析"按钮并抓请求体
实际 tooltip 原文：["解析失败", "系统服务异常，请联系管理员。", …]
  同一失败文件在接口层的数据（/file/folder/list）：
    synLogs[0].errorMessage = "系统服务异常，请联系管理员。"        ← 页面显示的就是它
    synLogs[0].errorDetail  = {"...","task_statuses":[{"fail_reason":"解析失败：File is not a zip file"}]}
  → 真实原因被埋在 errorDetail JSON 字符串里（缺陷 AG5-D1）
重试入口：失败行"解析"可点
  POST /proxy/index/knowledgeBase/file/filesParse → 200 {"success":true}
  页面该行立即变为"排队等待"（02-after-parse-click.png）
  DB：新任务 562（旧 547），文件 status 99(解析排队中)
  前端真实请求体（抓包原文）：
  {"files":[{"folder_id":null,"file_path":"r12-rag/kb_36/truncated.docx/V0/truncated.docx",
             "file_size":"22029MB","file_id":"503","parent_file_name":"truncated.docx"}],
   "folder_ids":[],"knowledge_base_name":"R14-E2E-AG5-1111","knowledge_base_id":"36",
   "override":true,"is_all":false}
判定：S4-4 FAIL；S4-5 PASS（两个 task id：547 → 562；另有 API 侧 537→563、→564）
证据：S4/ui2/s4-ui2.json、S4/ui2/01-hover-failed.png、S4/ui3/s4-ui3.json、S4/ui3/02-after-parse-click.png
```

### 2.8 S4-6 超过阈值仍"解析中"（FAIL，附等待时长与最终收敛方式）

```
现象：任务 564（重解析 truncated.docx）11:27:30 进入 DEAL_ING，
      至 11:37:17（收工前最后采样）仍 DEAL_ING，end_time=NULL，retry_times=0 → 9 分 47 秒；
      同文件文件级状态早已 4(解析失败)（gmt_modified 11:27:31）
      → 任务级与文件级长期不一致，且 DEAL_ING 计入"在飞"限流（源码 FIX-30 注释：在飞只算 DEAL_ING）
最终收敛（删库后复核时发现，如实补记）：该任务于 **11:40:01** 被判"僵尸"并回收，
  error_msg = "recover: 处理中超时(>10min)判为僵尸，于 2026-10-28 11:40:01 重置为待处理"，
  终态 5(DEAL_FAIL)；即从 11:27:30 到被回收共 **12 分 31 秒**。
  → 结论修正：不是"永久卡死"，而是"卡到 10 分钟兜底阈值才被回收"；**兜底存在，但阈值 10 分钟**
    （用户侧最长可看到"解析中"10 分钟以上，期间占 in-flight 槽位）
全表状态分布（收工复核时）：SUCCESS 30 / FAIL 6 / PENDING 2（=551/556，仍卡）/ DEAL_ING 0
判定：FAIL（超过阈值仍"解析中"；附等待 12m31s 与收敛方式）
运维提醒：DEAL_ING 计入在飞限流，若同时有多条任务被这样拖住，会挤占调度槽导致新提交排队（源码 FIX-30 已把 RETRY_ING 从在飞里剔除，但 DEAL_ING 仍是"在飞"）
证据：S4/S4-stuck-task-564.json（11:37:17 现场）、本报告 §5 残留复核（11:40:32 回收后状态）
```

### 2.9 S14-1 同名新版本：检索指向新版本（PASS）

```
步骤：kb_36 上传 AG5-CONV2-doc.docx（V0，5000万）→ 同名再传 v1（NEWVERSION，9000万 + 唯一标记 AG5-CONV-MARK-9001）
实际：
  V0 fid=521 终态 3、主索引 1 块；V1 fid=522 终态 3、主索引 1 块
  文件列表该组：{"kbFiles":[{"id":520,"version":"V1"},{"id":519,"version":"V0"}]}（V1 有效）
  检索两版共有内容（智造贷 适用对象 制造业中小微企业）→ 返回版本集合 = ['V1']   ← 只给新版本
  检索 V1 独有标记 → n_marker=1，来源 r12-rag/kb_36/AG5-CONV2-doc.docx/V1/AG5-CONV2-doc(1).docx
判定：PASS 2/2（检索侧自动指向新版本）
观察（非缺陷，需产品确认）：旧版本 V0 的 chunk 仍留在主索引（1 条，未物理淘汰），本次未被召回；
      若将来排序变化可能重复召回新旧两份 → AG5-O1
证据：S14/S14b-converge-2026-10-28T113240+0800.json
口径：答案级引用 /qa/ai/question 绑定助手配置 configId=1（指向 kb_9），本角色禁止改配置，
      故"引用层"对自建库不作断言（UNVERIFIED，见 §4）；引用内容由检索结果驱动，收敛结论在检索层取证。
陷阱规避：版本比对按 source 里 /Vn/ 之前的前缀归一（QA-SPEC §5-1），不用 title 比对。
```

### 2.10 S14-2 删除后三处收敛（PASS，判据 v2）

```
步骤：删除 V0(521)+V1(522) → 等 6s → 三处复核
实际：删除接口 2/2 success=true
  文件列表 still_in_file_list=false
  ES 两文件在 kb_36 / table_chunks / table_summary 均 0 条
  检索结果里 file_path 指向被删文件的条数 = 0（marker 与共有内容两条查询都查了）
判定：PASS 3/3
判据 v1 缺陷（自曝）：第一版按 documents **条数**判"删除后不再出现"，但 enabled_rerank=false 时
  检索无阈值过滤、必然返回若干无关块 → 条数 2，误判 FAIL（假红）。v2 改为按"来源前缀 + 内容标记"判。
  另：检索响应里**没有 metadata.pk 字段**（恒 None），用 pk 判代际会恒真（假绿，FINAL-REPORT §4.1② 那类）。
证据：S14/S14-delete-rejudge-2026-10-28T113409+0800.json、S14/S14b-converge-*.json
```

### 2.11 S14-3 重解析后引用代次（FAIL）

```
步骤：对未被重解析过的 docx-loan(fid=499) 取 ES 现状 → filesParse 重解析 → 等终态 → 再取
实际（before → after）：
  metadata.version : "V0"  →  null            ← 版本信息被清空（可复现 2/2：fid=522 的 "V1"→null）
  pk               : 373175319049028896 → 373175319049028896（未变）
  create_time      : 11:16:45 → 11:33:45（前进，块确实被原地重写）
  终态             : 解析成功
判定：FAIL（create_time 前进 成立 / version 保留 不成立）
影响：重解析后该块无法再标注版本 → §1.5③"引用版本=当前有效版本"对重解析过的文件失效；多版本库新旧稿无法区分
根因（**推断**，未验证）：前端与我的请求体 files[] 都不含 version 字段，解析服务回写 metadata 时按缺失处理；
      初始上传能带版本，说明两条路径装配不同 → 建议按 payload 对比定位
证据：S14/S14c-version-null-2026-10-28T113347+0800.json、S14/S14b-converge-*.json（含 522 的 V1→null）
```

---

## 3. 缺陷清单

### AG5-D1｜P2｜解析失败原因对用户不可见（只给固定通用句）

- 现象：页面 hover「解析失败」的 tooltip 恒为「系统服务异常，请联系管理员。」；真实原因
  （"File is not a zip file" / "No /Root object!…"）只在 `/file/folder/list` 的 `synLogs[].errorDetail` JSON 里
- 复现：上传任意坏文件 → 在 `?kbId=<自建库>` 列表 hover 状态文字 → 读 tooltip
- 期望 vs 实际：期望显示具体原因；实际是与原因无关的系统异常文案
- 影响面：所有解析失败场景的用户侧可诊断性；用户被引导"联系管理员"而非"文件已加密/格式不支持"
- 稳定复现：3/3 文件同一通用文案
- 证据：`S4/ui2/s4-ui2.json`（tooltipAfterHoverStatus）+ 接口 `synLogs.errorMessage` vs `errorDetail`

### AG5-D2｜P2｜加密 PDF 的失败原因是空字符串

- 现象：`task_statuses[0].fail_reason = "解析失败："`（冒号后为空），`errorDetail` 亦无原因文本
- 复现：上传 `evidence/fixtures/encrypted.pdf`（pypdf RC4-128，user_pw=123456）→ 查 `file_parse_task.error_msg`
- 期望 vs 实际：期望"PDF 已加密，无法解析"之类可读原因；实际只有前缀
- 影响面：加密 PDF 在金融场景高频，无法指导用户"另存为无密码 PDF"
- 稳定复现：2/2（首采 + utf8mb4 复采）
- 证据：`S3/S3-fail-reason-utf8mb4.json`（fid=500）

### AG5-D3｜P2｜解析状态/文件列表不自动刷新，中间态不可见

- 现象：详情页静默 20s **零请求**；另起进程上传新文件后 25s 内仍零请求、页面不含该文件；手动 reload 才出现
- 复现：打开 `/chats/knowledgeBase/36` → 保持不动 → 期间上传文件 → 观察 network 与页面文本
- 期望 vs 实际：期望轮询/SSE 自动更新；实际需手动刷新
- 影响面：大文件解析期间用户只能反复手动刷新；"解析中"与"卡死"无法区分（与 D1 叠加更糟）
- 稳定复现：2/2 窗口（20s + 25s，均 0 请求）
- 证据：`S4/ui2/s4-ui2.json`（autoRefresh / visibleAfterWait / visibleAfterReload）、`S4/ui/02-after-20s.png`

### AG5-D4｜P2｜`filesParse` 的 `file_ids` 是"假开关"：返回 success 但零动作

- 现象：`POST /index/knowledgeBase/file/filesParse` 只传
  `{"file_ids":["503"],"knowledge_base_name":"kb_36","knowledge_base_id":36}` →
  HTTP 200 `{"success":true,"data":true}`，但**无新任务、文件状态未变、行 gmt_modified 未变**
- 根因（源码事实）：`KnowledgeBaseListAppServiceImpl.getFilePathByFolder()`（689–709 行）只从
  `folder_ids` 装配 `files`，从不读 `fileIds`；后续 `filesParseReq.getFiles()` 为空 → 空循环 → 返回 true
- 复现：对任意文件（成功/失败各一次）按上述 payload 调用，比对 `file_parse_task` 前后
- 期望 vs 实际：期望 400/参数错误或该字段被移除；实际"成功且什么都没做"（§1.3 类假成功）
- 影响面：任何按接口 schema 集成 `file_ids` 的调用方都会静默失效，日志还显示成功
- **调用方视角（TL 要求补写）**：任何按接口 schema 集成该字段的人都会静默失效，**且没有任何错误提示** ——
  请求成功、响应 `success=true`、日志无异常，只有"任务没出现"这一个间接现象可循。
- **同族归并（TL 裁定）**：本条与「FAQ 抽取 0 条 / filesParse 零任务 / .md 解析 success=false /
  并发建索引 400」是同一族"200 掩盖失败"，合并报告时并列成"**假成功五例**"，本报告只出本族中的这一例。
- 稳定复现：2/2
- 证据：`S4/S4-retry-2026-10-28T112623+0800.json`（before/after tasks 与 row 完全一致）

### AG5-D5｜P2｜重解析后 chunk 的 `metadata.version` 被清空

- 现象：重解析后 `metadata.version` 由 `V0`/`V1` 变为 `null`；`create_time` 前进、`pk` 不变
- 复现：`filesParse`（前端同款 files[] payload）→ 对比重解析前后 ES 元数据
- 期望 vs 实际：期望版本元数据保留；实际丢失
- 影响面（TL 修订口径，按此写入）：
  ```
  受影响：所有经过重解析的文件（不止多版本库）
  后果：引用三段里第③段无法判定，"引旧稿"这种问题会重新变成不可检测
  与 P0-4（global 给旧值）的关系：那条是"摘要旧代次"，这条是"引用版本字段丢失"，
  两条都会让用户拿到旧内容，但修复位置不同，不要合并
  ```
- 稳定复现：2/2（fid=499 V0→null；fid=522 V1→null）
- 证据：`S14/S14c-version-null-*.json`、`S14/S14b-converge-*.json`

### AG5-D6｜P2｜解析任务在 DEAL_ING 被拖住 12 分 31 秒，靠 10 分钟僵尸兜底才收敛

- 现象：任务 564 `start_time=11:27:30`、`end_time=NULL`、`retry_times=0`，至 11:37:17（收工采样）仍
  `status=2(DEAL_ING)`（9m47s）；同文件文件级状态早已 `4(解析失败)`
- 最终收敛（删库后复核补记）：**11:40:01** 被判定僵尸并回收，
  `error_msg="recover: 处理中超时(>10min)判为僵尸，于 2026-10-28 11:40:01 重置为待处理"`，终态 `5(DEAL_FAIL)`
  → 总卡滞 **12 分 31 秒**，收敛依赖兜底而非正常回调
- 复现：对已失败文件重试（前端同款 payload）→ 观察 `file_parse_task`
- 期望 vs 实际：期望任务随回调（数秒级）收敛；实际长时间停在 DEAL_ING，最终由超时兜底收尾
- 影响面（**需提醒运维**）：DEAL_ING 计入"在飞"限流（源码 FIX-30 只把 RETRY_ING 从在飞中剔除，DEAL_ING 仍在），
  多条任务被这样拖住时会挤占调度槽 → 新提交表现为"长时间不派发"；同时"任务在飞、文件已终态"让运维无法判断真实进度
- 稳定复现：1/1（阈值内 12m31s 收敛；未做多次重复以确认触发概率）
- 证据：`S4/S4-stuck-task-564.json`（现场）+ §5 残留复核（回收后状态、error_msg 原文）

### AG5-D7｜P3｜中断上传残留 PENDING 任务永不清理

- 现象：中断（注入 0.1s 超时）那次上传留下 task 551/556，对应文件已被覆盖上传置为"已删除"(status 0)，
  任务 17 分钟后仍 `status=1(PENDING)`、`start_time=NULL`，无人派发也无人清理
- 期望 vs 实际：期望文件被删除/替换时其挂起任务同步终结；实际永久残留
- 影响面：任务表污染；若派发逻辑放宽，会对已删除文件做无效解析
- 稳定复现：2/2（551、556）
- 证据：`S4/S4-stuck-task-564.json`（inflight 列表）+ DB 复采（§2.4）

### AG5-D8｜P3｜体积单位错误（同源既有缺陷的补充实例，不另立新缺陷）

- 现象：上传响应 `fileSize=36716, size="36716.0MB"`（真实 36 KB）；库总览「文件数：19 大小：6.5 GB」（真实约 500 KB）；
  重试请求体里也带 `file_size:"22029MB"`
- 影响面：用户/运营看到的大小失真 10⁶ 量级；按大小计费或配额场景直接错
- 说明：ROUND-A 已报同类缺陷，本条只补充"上传响应与重试请求体同样错"的实例
- 证据：`S3/S3-case-docx-plain.json`（upload.body）、`S4/ui/s4-ui.json`（bodyText「6.5 GB」）、`S4/ui3/s4-ui3.json`（postData）

### 观察项（不计缺陷）

- **AG5-O1**：同名新版本上传后，旧版本 chunk 仍留在主索引（未物理淘汰），本次未被召回。若后续排序/召回策略变化，可能同时引用新旧两版 → 建议产品明确"旧版本是否淘汰"。
- **AG5-O2**：枚举同名不同义（文件级 3=解析成功；任务级 3=RETRY_ING；文件级 4=解析失败；任务级 4=SUCCESS），前端/运维读反会把成功当重试、把失败当成功 —— 本轮我方判据就先踩了一次。

---

## 4. 未覆盖项

| 场景 | 原因 | 谁能解除阻塞 |
|---|---|---|
| 答案级引用（/qa/ai/question）对自建库的收敛 | 该端点绑定助手配置 configId=1（指向 kb_9）；把引用指向自建库必须**改助手配置**，违反"不改配置"边界 | TL 授权一次临时助手配置，或有配置权限的角色代跑 |
| 解析失败原因在"详情页/解析日志"的展示 | 只验了列表页 tooltip 与接口字段；列表页仅有 `...` 更多操作，未找到独立日志页入口 | 需产品确认入口位置 |
| 大文件（>100MB）/ 断点续传 `/file/check` | 语料最大 37 KB，无大文件样本 | 提供大文件样本 |
| 扫描 PDF 的 OCR 文本质量 | 属 AG-2 解析质量范围；本角色只判"有块 + 状态成功" | AG-2 覆盖 |
| 更深并发（>3）的建索引竞争 | 已完成 2 轮共 6 文件未复现；更深并发违反"串联上传"纪律，需授权在专用库做破坏性压测 | TL 批准 |

---

## 5. 自检

```
断言总数 84（S3 68 + S4 9 + S14 7）
已执行   84
未执行   0
N/A 7    task_statuses 全 true（7 个正例）：该端点响应不含此键 → 用任务级 status=4 等价校验替代；
         失败用例里已实证该结构存在（error_msg 内嵌 {"success":false,"task_statuses":[{"success":false,"fail_reason":...}]}）
未执行逐条原因：无
是否用旧证据：否。全部为本轮 11:15–11:37 采集；前端哈希 11:11 与 11:38 两次自证同为 5161c957
是否含注入：是 1 处 —— 上传中断用客户端 timeout=0.1s 主动注入，已在 §2.4 与 D7 标注"注入"
服务代次：6 个关键端口中 5 个 pid 全程未变；19995 于 11:28:16 重启（ENV-ALERT），
         S3/S4 不经该服务，S14 检索样本全在重启后
前端版本：assets/index-fup9RT0c.js / md5 5161c957f19bb7f1ee825ca33d6771cc（served == dist）

判据自我修正 5 次（都是先怀疑判据，再怀疑产品；TL 要求写进结论旁，已同时置顶于 §1 总表下方）：
 ① 文件级 3=解析成功，不是任务级 3=RETRY_ING → 否则 7 个正例全假红
    【同类】：同名不同义的字段/枚举；"看起来是同一个 3，其实两套语义"
 ② 表格块在 table_chunks_*/table_summary_* → 否则 xlsx 假红
 ③ 检索条数在 rerank=false 时无阈值 → 否则"删除后仍有 2 条"假红（改为按来源/内容判）
 ④ 检索响应无 metadata.pk（恒 None）→ 用 pk 判代际会恒真（假绿），改用 ES 侧 pk + create_time
 ⑤（取证侧）mysql 客户端字符集导致 error_msg 显示 ????，复采确认是我方编码问题，撤回报表
    【教训】取证载体本身也会造假象：先排除"我方工具/编码/口径"，再认定产品缺陷
```

### 清理与残留（收工必做）

**已清理（可复核）**

| 项 | 清理前 | 清理后 |
|---|---|---|
| 知识库列表条数 | 17（含自建 2） | **15**（= 开工前 15；两个自建库已删） |
| ES `kb_36` / `table_chunks_kb_36` / `table_summary_kb_36` | 存在（3 / 2 / 2 条） | **全部 404 `index_not_found`** |
| ES `kb_37` / `table_chunks_kb_37` / `table_summary_kb_37` | 存在（3 / 2 / 2 条） | **全部 404 `index_not_found`** |
| Milvus `_kb_36` / `_table_chunks_kb_36` / `_table_summary_kb_36` / `_community_summary_kb_36` | 不存在（未生成） | 不存在 |
| Milvus（kb_37 同上 4 个集合） | 不存在 | 不存在 |
| MinIO 对象 | 仅在自建库前缀 `r12-rag/kb_36`、`kb_37` 下 | 未单独清理（随库删除策略处理；本角色未逐个删除对象） |

**未清理的残留（不是"已清理"，需 DB 权限者处置）**

| 表 | kb | 行数 | id 区间 | 状态分布 | 说明 |
|---|---|---|---|---|---|
| `knowledge_base` | 36 | 1 | 36–36 | status=0（逻辑删除） | 列表接口已不可见 |
| `knowledge_base` | 37 | 1 | 37–37 | status=0（逻辑删除） | 同上 |
| `knowledge_base_list` | 36 | 29 | **491–522** | status0 已删 9 / status3 成功 16 / status4 失败 4 | 文件行未物理删除 |
| `knowledge_base_list` | 37 | 3 | **514–516** | status3 成功 3 | 同上 |
| `file_parse_task` | 36 | 35 | **535–572** | PENDING 2 / SUCCESS 27 / FAIL 6 | 含 D6 僵尸回收行 564、D7 残留 551/556 |
| `file_parse_task` | 37 | 3 | **558–560** | SUCCESS 3 | 同上 |
| `syn_log` | 36 | 14 | **666–679** | — | 含失败原因日志与僵尸回收日志 |
| `syn_log` | 37 | 0 | — | — | 无 |

**处置说明（按 TL 口径，不写成"已清理"）**：删库在 **ES 层是物理清理**（索引 404）、**Milvus 无集合**、
**列表接口不再可见**；但上述 **MySQL 元数据行仍在**（`knowledge_base.status=0` 逻辑删除，
合计 **32 个文件行 / 38 个任务行 / 14 条日志行**）。本角色边界为"不改数据库"，故未执行任何 DELETE；
**这些行需 DB 权限者处置**（是否物理清理、是否保留作为 D6/D7 物证，由 TL/运维决定）。
其中 `file_parse_task` 的 564（D6 僵尸回收，error_msg 已记回收时刻 11:40:01）与 551/556（D7，仍 PENDING）
是两条缺陷的直接物证，建议处置前先留档。

证据：`AG-5/evidence/cleanup-2026-10-28T113740+0800.json`、`AG-5/evidence/cleanup-residual-check.json`
写锁：`AG-5/evidence/.write-lock` 已记录 stop=11:38:11，收工后删除。

---

## 6. 修订记录

### V1.1（2026-10-28 11:42，依据 TL 复核意见 + 一次自查补正）

| # | 修订项 | 内容 |
|---|---|---|
| 1 | **D5 影响面改写**（TL 口径） | 从"多版本库新旧稿无法区分"改为：受影响=所有经过重解析的文件；后果=引用三段第③段无法判定，"引旧稿"重新变成不可检测；并注明与 P0-4 是两条不同缺陷（摘要旧代次 vs 引用版本字段丢失），**不合并** |
| 2 | **D4 补调用方视角**（TL 要求） | 明确"按 schema 集成该字段 → 静默失效且无任何错误提示"；并按 TL 裁定归入同族"**假成功五例**"（FAQ 抽取 0 条 / filesParse 零任务 / .md 解析 success=false / 并发建索引 400） |
| 3 | **D6 结论修正（自查补正，重要）** | 收尾后复核发现任务 564 并非"永久卡死"：**11:40:01 被僵尸回收**（`recover: 处理中超时(>10min)判为僵尸`），终态 DEAL_FAIL，总卡滞 **12m31s**。结论从"永久不收敛"改为"**卡到 10 分钟兜底阈值才收敛**"。缺陷仍成立（阈值内 10 分钟以上占 in-flight 槽），但性质与影响面表述已改，并加"需提醒运维" |
| 4 | **残留章节改写**（TL 口径） | 从"已清理/残留说明"混合表述，改为两个分表：**已清理（可复核）** 与 **未清理残留（不是"已清理"，需 DB 权限者处置）**；残留列出 `knowledge_base / knowledge_base_list / file_parse_task / syn_log` 的**行数与 id 区间**（491–522 / 514–516 / 535–572 / 558–560 / 666–679），并标注处置建议 |
| 5 | **判据自修正置顶**（TL 要求） | 三条关键判据（同名不同义枚举、表格块跨索引、检索无阈值+无 pk）同时写入 §1 总表下方"结论旁"与 §5 自检，并标注"不改会把 7 个正例全判假红" |

> 修订原则：**改表述不改事实**。D6 的现场证据（11:37:17 仍 DEAL_ING）保留未删，新增回收后的状态作为同一任务的后半段；
> 两次观测都在同一条 `file_parse_task.id=564` 上，不存在换样本。
