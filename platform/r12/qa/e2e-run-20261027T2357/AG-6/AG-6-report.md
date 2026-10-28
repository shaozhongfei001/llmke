# AG-6 验收报告：FAQ 全链路（S9）

- 角色：AG-6（写入角色，独占写锁 `AG-6/evidence/.write-lock`：11:42:25 建，11:57:10 记 stop 后删除）
- 运行目录：`/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357`
- 执行窗口：2026-10-28 11:42:27 – 11:57:10（本地时间）
- 自建库：`R14-E2E-AG6-1143`（**id=38**，取自建库响应 `data.id`，`primitiveName=kb_38`），收工已删
- 未触碰：`kb_9`（只读，仅做 FAQ 检索/问答取证，未写入）、`kb_22` 及任何既有库；未重启服务、未改配置、未改数据库、未 git 提交

---

## 0. 环境代次（本轮全程同一批；与 ROUND-A 不是同一批）

**开工 pid（11:42:27）**

```
8088=925533   18082=923878   18083=1647331   19527=922312   19529=1461792   19995=1079761
```

**收工 pid（11:57:09，清理前后各记一次，两次相同）**

```
8088=925533   18082=923878   18083=1647331   19527=922312   19529=1461792   19995=1079761
```

六端口逐一比对：**完全一致，无 ENV_EVENT**。启动时刻（`ps -o lstart` 实测）：

```
19527 fulltext    Wed Oct 28 11:05:00 2026
18082 index       Wed Oct 28 11:05:11 2026
8088  gateway     Wed Oct 28 11:05:20 2026
19995 retrieval   Wed Oct 28 11:28:16 2026   ← 这批之外，单独一次（早于本角色开工 11:42）
18083 auth        Tue Oct 27 14:22:00 2026
19529 sensitive   Tue Oct 27 13:53:18 2026
```

即 11:05 那次批量重启发生在 ROUND-A 收尾之后、本角色开工之前；19995 的 11:28:16 重启同样早于开工。**本角色全部样本（11:42–11:57）落在同一代次内。**

### 0.1 前端版本自证（QA-SPEC §1.4）

```
entry   assets/index-fup9RT0c.js
curl    http://127.0.0.1:18088/assets/index-fup9RT0c.js → 200, 315489 B
md5(served) = 5161c957f19bb7f1ee825ca33d6771cc
md5(dist)   = 5161c957f19bb7f1ee825ca33d6771cc     ← 两哈希相同（开工 11:42:27 与收工 11:57:09 两次自证均相同）
dist mtime  2026-10-28 11:11:00.802388587 +0800
旧包锚点    de2424501bd29e358043049876db2a75（dist.bak-r14e-1111，本角色未使用）
```

证据：`AG-6/evidence/S0/preflight-20261028T034227Z.json`、`S0/env-20261028T035606Z.json`、`S0/env-20261028T035709Z.json`

---

## 1. 一句话结论

**FAQ 六条主链里三条 PASS、两条 FAIL，最严重的一条是"编辑问答对必失败，并把原问答对删掉"。**

```
FAIL  S9-3 编辑：PUT /faq/update → HTTP 500「更新失败(es)」；服务端"先删后插"，插入 100% 失败
            → 编辑没生效，原问答对从索引里消失（42→41 / 列表 30→29）。复现 2/2，既有缺陷（非本轮改动引入）
FAIL  S9-5 直答：FAQ 通道确实被命中（关闭开关则 0 条，开关有效），但
            答案与"被问的那条 FAQ 原文"逐字符一致 0/4；3/4 给的是**另一条相近问答对**的答案，1/4 回退文档生成；
            页面无任何"FAQ 命中/来源"标记，用户无法区分是 FAQ 原文还是模型输出
PASS  S9-1 列表（30 条 / 3 页，页面行数与接口一致）
PASS  S9-2 从语料抽取（实际产出 18 条，不是"报成功但 0 条"）
PASS  S9-4 启停（真实切换状态真落库；注入 500 时 toast 可读、开关不回落）
PASS  S9-6 删除（页面/列表/检索/ES 四处都不再返回）
```

---

## 2. 一页总表

| 场景 | 判定 | 断言通过/总数 | 耗时 | 关键证据 |
|---|---|---|---|---|
| S9-1 列表加载（条数、分页） | PASS | 6/6 | 约 40s | `S9/ui-list/s9-ui-list.json`、`02-page1.png`、`03-lastpage.png` |
| S9-2 从语料抽取 FAQ（产出>0） | PASS | 5/5 | 抽取 39.2s + 轮询至终态 | `S9/S9-2-faq-extract.json` |
| S9-3 编辑保存后生效 | **FAIL** | 1/5 | 3.2s（失败） | `S9/ui-edit/s9-ui-edit.json`、`S9/S9-3-edit-extracted-repro.json`、`S9/edit-bug-fulltext-log.txt` |
| S9-4 启停切换（含注入 500） | PASS | 6/6 | 2×约 25s | `S9/ui-toggle/s9-ui-toggle.json`、`S9/S9-4-toggle-state-after.json` |
| S9-5 直接提问命中 FAQ 直答 | **FAIL** | 4/8 | 4 问约 30s + UI 1 问 8s | `S9/S9-5-direct.json`、`S9/S9-5-answer-level.json`、`S9/ui-chat/s9-ui-chat.json` |
| S9-6 删除后列表与检索不再返回 | PASS | 6/6 | 约 30s | `S9/ui-delete/s9-ui-delete.json`、`S9/S9-6-delete-verify.json` |
| **合计** | — | **28/36** | 11:42–11:57 | 缺陷 4 条（P1×1 / P2×3）+ 观察 2 条 |

---

## 3. 每条明细

### 3.1 S9-1 列表加载（条数、分页）——PASS 6/6

```
前置：admin 登录（simpleLogin，服务端签发 token）；自建库 id=38；FAQ 文件行 folder_id=525
夹具：① 抽取产生 18 条  ② 按前端真实 payload（fileId+folderId）新建 12 条 → 共 30 条
步骤：/chats/knowledgeBase/38 → FAQ tab → FAQ管理 → 点文件名「R12FIX-product-loan.docx」
      → 读第 1 页行数与分页页码 → 点最后一页再读行数；同时比对接口 /faq/list 的 total/pages/size
期望：A1 文件入口可见；A2 第 1 页行数 = min(size,total)；A3 页码个数 = pages；
      A4 最后一页行数 = total-(pages-1)*size；A5 页面结构入口齐全；A6 页面行数与接口一致
实际：A1 可见「全部文件R12FIX-product-loan.docx」
      A2 第 1 页 10 行，接口 total=30 / pages=3 / size=10
      A3 页码 = ["1","2","3"]（3 个）
      A4 最后一页（第 3 页）10 行
      A5 重复问题检测 / 新建问答 / 导入 / 新建文件夹 均可见
      A6 10×3=30 = total，一致
判定：PASS 6/6
证据：AG-6/evidence/S9/ui-list/s9-ui-list.json、01-faq-manage-root.png、02-page1.png、03-lastpage.png
复跑：NODE_PATH=/home/szf/env/my-playwright/node_modules AG6_KB_ID=<id> node AG-6/scripts/s9_ui_list.js
```

**判读须知（防止被误读成"列表只有 1 条"）**：FAQ 管理页是**文件维度**的两级结构。
`GET /faq/list?kbId=38`（不带 fileId/folderId）返回 **dataType=2 的文件行 1 条**；
问答对（dataType=3）必须带 `folderId` 才能列出。抽取会在 `knowledge_base_list` 里**新增一行 parse_type=5 的"FAQ 文件"（id=525）**，与源文件（523）同名 —— 这也是库头部「文件数：2」的由来。

### 3.2 S9-2 从语料抽取 FAQ（产出>0）——PASS 5/5

```
前置：kb_38 内 R12FIX-product-loan.docx（fid=523）解析成功（文件级 3=解析成功）
步骤：① 串行上传源语料（1 次 1 个文件，绝不并发）→ 等文件级终态
      ② POST /index/knowledgeBase/file/extractFQA（前端 FAQ抽取 的同一端点，files[] 带 file_id/file_path）
      ③ 轮询 GET /file/getFAQExtractStatusById → 终态
      ④ 数**实际产出**：ES faq_kb_38 条数 + /faq/list(folderId=525) 的 total（不只看 success）
期望：① 接口 success=true；② 抽取状态终态=3(抽取成功)；③ ES 条数 > 0；④ 列表 total > 0；
      ⑤ 文件行 faqExtractStatus=3
实际：① 200 {"success":true,"data":true}（39.2s）
      ② 抽取状态 1(未抽取) → 3(抽取成功)，轮询 39.2s 到终态
      ③ ES faq_kb_38：抽取前 404 index_not_found → 抽取后 **18 条**
      ④ /faq/list folderId=525：0 → **18 条**（问题样例「流动资金贷款的最长还款期限是多少？」「授信额度的有效期如何？」…）
      ⑤ 文件 525 faq_extract_status=3
判定：PASS 5/5（**产出条数以存储与列表双证，不看接口 200**）
证据：AG-6/evidence/S9/S9-2-faq-extract.json、S9-2-filelist-flat.json
复跑：PYTHONPATH=AG-6/scripts <venv>/bin/python AG-6/scripts/s9_extract.py
```

### 3.3 S9-3 编辑问答对保存后生效——**FAIL 1/5**

```
前置：FAQ 列表内任意问答对（抽取生成 / 手工新建都试过）
步骤：FAQ管理 → 进文件 → 「搜索内容」输入标记并按 Enter 过滤 → 点行内编辑（title="编辑"）
      → 抽屉「编辑问答」内改 Q/A → 点「确定」→ 抓 /faq/update 响应 → 再读页面（不刷新）
      → 刷新后再读一次 → 对比 ES 条数与列表条数
期望：E1 接口 success=true；E2 页面该行文本变为新值；E3 刷新后仍为新值；
      E4 原问答对不丢失；E5 失败时给出可读原因且不静默
实际：E1 **HTTP 500** `{"success":false,"errorMsg":"更新失败(es)","errorCode":"10029","data":null}`
      E2 页面未更新；抽屉保持打开（未关闭）
      E3 刷新后仍是旧值（该问答对已从列表消失，见 E4）
      E4 **原问答对消失**：ES 42→41、/faq/list total 30→29（另一次复现 41→40 / 29→28）
      E5 可读但信息不全：toast 两条「更新失败(es)」「编辑问答对失败！」
判定：FAIL 1/5（仅 E5 成立）
证据：AG-6/evidence/S9/ui-edit/s9-ui-edit.json（含前端真实请求体）、03-after-save.png、04-after-reload.png
      AG-6/evidence/S9/S9-3-edit-extracted-repro.json（对"抽取生成"的问答对再复现一次）
      AG-6/evidence/S9/edit-bug-fulltext-log.txt（服务端原文日志）
复跑：NODE_PATH=... AG6_KB_ID=<id> AG6_MARK=<问题标记> AG6_NEW_Q=... AG6_NEW_A=... node AG-6/scripts/s9_ui_edit.js
      PYTHONPATH=AG-6/scripts <venv>/bin/python AG-6/scripts/s9_edit_repro.py
```

前端真实请求体（抓包原文）：

```json
{"kbId":"38","faqs":[{"status":0,"question":"AG6Q-114802-001-EDIT 智造贷的最高授信额度是多少（编辑后）？",
 "answer":"AG6A-114802-001-EDIT 编辑后答案：最高授信额度为 8000 万元（人民币捌仟万元整）。",
 "pk":"2115289472208343042","relatedPk":"2115289472208343043"}]}
```

### 3.4 S9-4 启停切换——PASS 6/6（其中 3 条为**注入 500** 验分支）

```
A 段（真实链路）
步骤：FAQ管理 → 进文件 → 过滤到 status=0 的问答对 → 读开关 aria-checked → 点开关 → 抓 /faq/changeStatus
实际：请求 {"kbId":"38","status":1,"relatedpks":["..."]} → 200 {"success":true}
      开关 aria-checked false→true；toast「问答对启用成功！」
      复核（接口再读）：该问答对 status=0→1 真落库
判定：PASS（A1 接口 success / A2 开关翻转 / A3 toast 成功 / A4 状态真落库）

B 段（**注入 500**，客户端拦截，与真实故障分开记）
注入方式：Playwright page.route("**/faq/changeStatus") → fulfill 500 + 平台通用错误信封
         {"success":false,"errorMsg":"注入500：模拟服务端异常","errorCode":"999"}
实际：注入命中 1 次；开关 aria-checked **false→false（不回落、也不显示已切换）**；
      toast 可读：「注入500：模拟服务端异常」（axios 拦截器转发服务端 errorMsg）
                「问答对启用失败：服务不可用」
      复核：该问答对 status 仍为 0（无副作用）
判定：B1 开关不回落 PASS；B2 toast 可读 PASS
⚠ 口径：B 段只证明"失败分支表现正确"，**不能**据此写"真实 500 下也如此"；真实 500 未在本轮出现。
证据：AG-6/evidence/S9/ui-toggle/s9-ui-toggle.json、A-real-toggle.png、B-injected-500.png
      AG-6/evidence/S9/S9-4-toggle-state-after.json
复跑：NODE_PATH=... AG6_KB_ID=<id> AG6_MARK_A=<启用用> AG6_MARK_B=<注入用> node AG-6/scripts/s9_ui_toggle.js
```

### 3.5 S9-5 直接提问命中 FAQ 直答——**FAIL 4/8**

```
L1 检索层（我的库 kb_38，enabled_faq=true）
实际：200，「查询成功」，faq_result_list 2 条：
      {"faq_question":"ag6q-114802-002 智造贷的最高授信额度是多少？","faq_answer":"单户最高授信额度为人民币5000万元。","score":0.3667}
      {"faq_question":"ag6q-114802-002 智造贷的最高授信额度是多少？","faq_answer":"信用方式最高授信额度为人民币1000万元。","score":0.3095}
      A1 通道确实命中（2 条）                                        PASS
      A3 faq_question ≠ FAQ 原问题（返回的是检索 query，且被小写化）  **FAIL**
L2 对照（同一问题，enabled_faq=false）
实际：faq_result_list 0 条（docs 2 条）→ 说明 A1 的 2 条确实来自 FAQ 通道
      A2 关闭通道即 0 条                                              PASS
L3 答案层（kb_9 只读，POST /qa/ai/question_re，即 UI 实际端点）
4 条 kb_9 既有 FAQ 的原问题逐条提问，逐字符比对返回答案：
  ①「客户访前准备属于哪一部分？」  期望「客户访前准备属于第一段。」
     实得「文档的第一段主要讨论了客户访前准备。」   → 来自**另一条**问答对（FROM_OTHER_FAQ）  resultType=2
  ②「客户的日均存款是多少？」      期望「客户的日均存款是2,983,333.33元。」
     实得「日均存款的具体数值是2,983,333.33元。」   → FROM_OTHER_FAQ  resultType=2
  ③「文档的第一段主要讨论了什么？」 期望「文档的第一段主要讨论了客户访前准备。」
     实得 retrive-tag 文档引用片段（走文档生成）     → 未命中 FAQ       resultType=1
  ④「文档中提到了日均存款的具体数值吗？」 期望「是的，文档中提到了日均存款的具体数值。」
     实得「是的，日均存款的数值2,983,333.33元包含整数部分和小数点后的数值。」→ FROM_OTHER_FAQ  resultType=2
      A4 resultType=2 出现 3/4                                       PASS
      A5 答案 == 被问问答对原文 0/4                                   **FAIL**
      A6 答案来自"某条"FAQ 原文（非模型自由生成）3/4                  PASS
L4 页面层（问答页真实提问「客户的日均存款是多少？」，助手=R12默认问答配置）
实际：页面正文「客户端…日均存款的具体数值是2,983,333.33元。」+「本次回答总计消耗 0 tokens」，
      无「知识溯源」按钮、无任何 FAQ 标记；答案仍是**另一条**问答对的原文
      A7 页面可辨"这是 FAQ 答案/来源"                                 **FAIL**
      A8 页面答案 == 被问 FAQ 原文                                    **FAIL**
判定：FAIL 4/8
附加观察（写清归属，不当缺陷）：kb_9 的 faq_kb_9 里存在大量**近似重复**问答对
（"客户的日均存款是多少？" / "日均存款的具体数值是多少？" / "文档中提到了客户日均存款的多少元？"…共 20 条），
近似问句互相竞争是"串答"的温床；但"取哪一条的答案"由 /llm_faq_select 的大模型判定，不是精确问句匹配。
证据：AG-6/evidence/S9/S9-5-direct.json、S9-5-answer-level.json、ui-chat/s9-ui-chat.json、ui-chat/02-answer.png
复跑：PYTHONPATH=AG-6/scripts <venv>/bin/python AG-6/scripts/s9_direct.py && .../s9_direct_answer.py
      NODE_PATH=... node AG-6/scripts/s9_ui_chat_faq.js
```

### 3.6 S9-6 删除后列表与检索都不再返回——PASS 6/6

```
前置：先造一条"检索可唯一定位"的目标问答对「是否有违约金？/ 提前还款不收取违约金。」
      （删除前实测：检索该问题能召回这条的答案，故本用例**非空转**）
步骤：FAQ管理 → 过滤该问题 → 点行内删除（title="删除"）→ Popconfirm「确认删除问答对吗？」→ 点「确认」
      → 抓 /faq/delete → 页面重新过滤一次 → 复核列表 / 检索 / ES 三处
期望：D1 行从页面消失；D2 接口 success；D3 toast 可读；D4 列表不再返回；D5 检索不再返回该答案；D6 ES 文档消失
实际：D1 过滤结果 1 行 → 0 行              D2 200 {"success":true,"data":true}
      D3 toast「删除成功!」                  D4 /faq/list total 30→28 且无该 pk
      请求体 {"kbId":"38","relatedPks":["275195405320273198"]}
      D5 检索同一问题，faq_result_list 中**不再出现**「提前还款不收取违约金。」（仍有 1 条其它问答对）
      D6 ES faq_kb_38 中该 pk 不存在
判定：PASS 6/6
证据：AG-6/evidence/S9/ui-delete/s9-ui-delete.json、01-before-delete.png、02-popconfirm.png、04-after-delete-refilter.png
      AG-6/evidence/S9/S9-6-delete-verify.json
复跑：NODE_PATH=... AG6_KB_ID=<id> AG6_DEL_MARK='是否有违约金？' node AG-6/scripts/s9_ui_delete.js
      PYTHONPATH=AG-6/scripts <venv>/bin/python AG-6/scripts/s9_delete_verify.py
```

---

## 4. 缺陷清单（4 条 + 2 观察）

### AG6-D1｜P1｜编辑问答对必失败，且原问答对同时被删除（数据丢失）

- **现象**：`PUT /index/faq/update` → HTTP 500 `{"success":false,"errorMsg":"更新失败(es)","errorCode":"10029"}`；
  编辑未生效，且该问答对**从 ES 索引与列表中消失**（ES 42→41、列表 30→29；二次复现 41→40、29→28）
- **复现步骤**：
  1. FAQ管理 → 进 FAQ 文件 → 任选一条问答对 → 点编辑 → 改答案 → 点「确定」
  2. 抓 `/faq/update` 响应（500/10029）；对比操作前后 ES 条数与列表 total
  3. 对"抽取生成的"问答对重复一次（排除"只有 API 新建的才出错"）
- **期望 vs 实际**：期望保存成功且其他问答对数量不变；实际保存失败 + 丢掉一条问答对
- **根因（代码 + 服务端日志，双一级证据）**：
  ```
  FAQAppServiceImpl.updateFaqBatch()
    → remoteFileUtils.faqUpdateEs()                 （同步；返回 code≠200 就抛 UPDATE_ES_ERROR 10029）
    → ES 服务 es_kb_service.update_doc()：
         pk_list = [ud["pk"] ...]
         del_by_id(...)        ← ① 先把原文档删掉
         asyncio.run(add_documents_async(insert_model))  ← ② 再插入
  ```
  服务端日志（`platform/r12/logs/index_fulltext_service.log`，两次独立复现均同型）：
  ```
  11:49:26.964 POST /update_doc  index_name=faq_kb_38 pk=2115289472208343042
  11:49:26.966 del_by_id {'terms': {'_id': ['2115289472208343042']}}
  11:49:26.970 ERROR controller.es:_add_documents_async_impl:468 - 创建索引失败,Timeout context manager should be used inside a task
  11:49:27.008 ERROR 同上（重试 1）  11:49:29.980（重试 2）  11:49:36.001（重试 3）
  11:51:07.775 / 11:51:07.815 / 11:51:10.784   ← 第二次复现，同样 4 次全失败
  ```
  即 `update_doc()` 里的 `asyncio.run(...)` 在该运行环境必然抛
  `Timeout context manager should be used inside a task`，而**删除步骤已经执行**，于是"删了没插回去"。
  重试 4 次只会重复"再删一次（0 条）+ 再失败"，不具恢复能力。
- **引入时点（避免误判为 R14 回归）**：`git log -S "asyncio.run(add_documents_async"` →
  该写法在 `527e1ba feat(r12): 恢复原工程三套源码并打通 Java 业务主链` 即存在，**属既有缺陷**；
  R14 的修复批次没有改这一处（`es_kb_service.py` 最近一次提交 `db413ff 2026-10-25`）。
- **影响面**：所有 FAQ 编辑入口（问答对编辑、相似问编辑走同一 `PUT /faq/update`）。
  用户侧表现是"改不了 + 越编辑越少条"，且**失败提示与数据丢失同时发生，用户不会知道数据已丢**。
  在金融知识库里这属于"维护动作反向破坏数据"，建议按 **P1** 处理（若认为"编辑必失败=主流程不可用"则升 P0）。
- **稳定复现**：**2/2**（抽取生成项 1 次、手工新建项 1 次；日志各 4 次重试全失败）
- **证据**：`S9/ui-edit/s9-ui-edit.json`、`S9/S9-3-edit-extracted-repro.json`、`S9/edit-bug-fulltext-log.txt`

### AG6-D2｜P2｜"FAQ 直答"给的不是被问问答对的原文，且页面无来源标记

- **现象**：4 条 FAQ 原问题逐条提问，返回答案与"被问问答对"的 `answer` **逐字符一致 0/4**；
  其中 3 条与**另一条**问答对的 `answer` 完全相等（串到邻近问答对），1 条完全没命中 FAQ 而回退文档生成；
  页面只显示答案 + 耗时，**无「知识溯源」按钮、无任何 FAQ 标记**
- **复现步骤**：`POST /qa/ai/question_re`（UI 同一端点，configId=1 → kb_9，只读）分别提问上述 4 条原问题，逐字符比对
- **期望 vs 实际**：期望命中 FAQ 时返回该问答对原文（或至少页面标明"来自 FAQ 并给出是哪一条"）；
  实际返回相似问答对的答案，用户无法核对其来源
- **影响面**：数值型 FAQ（日均存款 2,983,333.33 / 额度 5000 万 vs 1000 万）一旦串到相邻问答对，
  事实层面就可能出错；本轮 4 条里事实恰好相同，属"幸运"而非机制保证
- **稳定复现**：**4/4 答案不一致（3/4 串邻近问答对、1/4 回退文档生成）**
- **证据**：`S9/S9-5-answer-level.json`、`S9/ui-chat/s9-ui-chat.json`、`S9/ui-chat/02-answer.png`

### AG6-D3｜P2｜`faq_result_list.faq_question` 返回的是检索 query，不是 FAQ 原问题

- **现象**：`faq_result_list[*].faq_question` = `"ag6q-114802-002 智造贷的最高授信额度是多少？"`
  （即我提问的 query，且被**小写化**），而库里该问答对的问题是
  `"AG6Q-114802-002 智造贷的最高授信额度是多少？"`
- **复现步骤**：`POST /retrieval_documents`（enabled_faq=true，knowledge_base_name=[kb_38]）→ 读 `data.faq_result_list`
- **代码位置**：`alg_retrieval_service/app/retrieval_service.py:526` 取的是 `metadata["query"]`；
  而 `metadata["query"]` 在 `reranker_service.py:55` 被赋成 `search_params["query"]`（检索用 query，已 lower）。
  应取 `metadata["question"]`。**（"读的是哪个键"= 代码一级证据；"谁写的"= 已定位到 reranker 赋值行）**
- **期望 vs 实际**：期望 `faq_question` = FAQ 原问题（可用于引用/审计/前端展示"命中标准问"）；实际给的是用户 query
- **影响面**：任何依赖 `faq_question` 做展示、日志归因、命中率统计的消费方都会被污染；
  `faq_answer` 与 `faq_question` 因此**不成对**（答案来自 A 条、问题显示成用户问句）
- **稳定复现**：**3/3**（L1 命中 2 条 + 启用后唯一问句命中 1 条，均为小写 query）
- **证据**：`S9/S9-5-direct.json`（`L1.faq_result_list`）、`S9/S9-6-enable-and-hit.json`

### AG6-D4｜P2｜新建问答对默认"禁用"，创建即不参与召回；抽取生成的却是"启用"

- **现象**：`POST /faq/create`（前端「新建问答」同路径）创建 12+1 条，返回 200 + pk，
  但列表与 ES 里 `status=0（禁用）`；抽取流程生成的 18 条是 `status=1（启用）`。
  检索侧对 FAQ 的过滤条件是 `metadata["status"] == 1`（`retrieval_service.py:523`），
  故**新建的问答对默认不会被召回**（实测：新建后检索该问句 0 命中；手工启用后才有命中）
- **复现步骤**：新建问答对 → 查 `/faq/list` 的 `status` → 检索该问句；对比抽取生成的问答对
- **期望 vs 实际**：期望"新建即可用"或"新建后明确提示未启用"；实际静默为禁用，且与抽取口径相反
- **影响面**：手工维护的问答对（最贴近业务话术的那批）默认不进直答；与 AG6-D1（无法编辑）叠加后，
  用户几乎无法把一条手工问答对变成可用状态
- **口径保留**：**"默认禁用"是否是有意的审核设计，需产品确认**；在确认前按"静默无效"记录
- **稳定复现**：**25/25**（本轮 25 条新建问答对（12+12+1 探针）创建后全部 `status=0`；18 条抽取生成全部 `status=1`）
- **证据**：`S9/S9-1-fixture-v2.json`、`S9/S9-6-delete-prep.json`、`S9/S9-6-enable-and-hit.json`

### AG6-O1｜P3（观察，供合并）｜`/faq/create` 只给 folderId（或都不给）时：200 + 返回 pk，但任何列表都看不到

- 现象：只传 `folderId=525`（不传 fileId）创建 12 条 → 200 + pk；ES `faq_kb_38` 确实 +12 条，
  但 FAQ 文件视角列表（UI 与 `fileId+folderId` 查询）**一条都看不到**；完全不带 folder/file 的 12 条更是任何视图都不可见
- 原因（推断）：列表在按文件过滤时用 `metadata.file_id`，而"只给 folderId"创建的文档 `file_id=None`
- 影响面：接口/集成方按 schema 创建后"成功但不可见"；UI 路径因强制选文件夹/文件而不复现，故定 **P3**
- 清理动作：这 25 条已用 `/faq/delete`（按 relatedPks）删除，ES 43→31→30 与预期一致（顺带证明删除链路无残留）
- 证据：`S9/S9-1-fixture-and-list.json`、`S9/S9-1-fixture-v2.json`（含 delete_orphans 段）

### AG6-O2｜P3（与 AG-2 P1-6 同型，建议并档）｜启停失败的第二条 toast 把原因替换成固定文案

- 现象：注入 500 时同时出现两条 toast：`注入500：模拟服务端异常`（axios 拦截器转发 errorMsg）
  与 `问答对启用失败：服务不可用`（业务 catch 兜底）；后者丢失了服务端原因
- 代码：`useFaqController.ts` 的 catch 读 `err?.response?.data?.errorMsg || err?.message || "服务不可用"`，
  而 `src/apis/index.ts` 的错误拦截器**没有 return Promise.reject(error)**，下游拿不到 `response`
- 影响面：失败原因只剩第一层 toast，且两条并存易被用户误读
- 证据：`S9/ui-toggle/s9-ui-toggle.json`（B 段 toasts 原文）

> **不另立缺陷**：库头部「文件数：2 大小：72.5 MB」（真实 74 KB）与 AG-5 D8 / AG-1 D-5 同源，只作实例补充。

---

## 5. 未覆盖项

| 场景 | 状态 | 原因 | 谁能解除阻塞 |
|---|---|---|---|
| 编辑"相似问"（`/faq/update` 同理） | 未单独跑 | 与 AG6-D1 同一端点同一代码路径；按"依赖缺陷"不重复取证 | 修 D1 后补一条即可 |
| FAQ 导入（模板下载 / `uploadFiles` 批量导入） | NOT RUN | S9 六条判据未包含；且属批量写入，需单独授权与独立库 | TL 排期 |
| FAQ 重复问题检测（`repeatCheck`）页面闭环 | UNVERIFIED | 只确认入口可见（S9-1 A5），未造重复数据验证弹层 | 需在自建库造重复对 |
| 我的自建库上的"答案层"（question_re） | BLOCKED | 该端点知识库取自**助手配置**（`knowledge_base_name` / `selectedKnowledgeBase`），
指向 kb_9；把答案层切到自建库必须改助手配置 → 违反 §1.12 | TL 授权一次性临时助手配置，或有配置权限的角色代跑 |
| 编辑失败后的自动恢复/补偿任务 | NOT RUN | 未观察到任何补偿任务（`file_parse_task` 与 FAQ 无关），本轮不做猜测 | 需研发确认设计意图 |

---

## 6. 自检

```
断言总数   36（S9-1 6 / S9-2 5 / S9-3 5 / S9-4 6 / S9-5 8 / S9-6 6）
已执行     36
通过       28        失败 8（S9-3 4 条、S9-5 4 条）
未执行     0        N/A 0
是否用旧证据  否。全部样本产生于 11:42–11:57；前端哈希 11:42:27 与 11:57:09 两次自证同为 5161c957
是否含注入   是 1 处 —— S9-4 B 段用 Playwright route 把 /faq/changeStatus 打成 500，
             响应体为构造件，已在 §3.4 与 AG6-O2 明确标注"注入"，**未与任何真实故障混记**
服务代次   6 端口开工/收工 pid 完全一致；18083/19529 是 10-27 的老代次；
          18082/8088/19527 为 10-28 11:05 批量重启；19995 为 11:28:16 单独重启（均早于开工）
前端版本   assets/index-fup9RT0c.js · 315489 B · md5 5161c957f19bb7f1ee825ca33d6771cc（served == dist）
判据自我修正 4 次（都是先怀疑判据，再怀疑产品）：
  ① 首轮编辑用例「搜索过滤」没按 Enter → 过滤没生效、编辑到了错行：**是我方脚本缺陷，已修**（§3.3 复跑命令含 Enter）
  ② 首轮选"抽取生成的"问答对做编辑复现，才排除"只有 API 新建的才失败" → D1 定性从"局部"升为"全路径"
  ③ faq_result_list 的 faq_question 小写 → 先怀疑自己传了大小写，回查代码确认是取 metadata["query"]（D3）
  ④ 首轮新建夹具没带 fileId → 12 条"看不见"，先怀疑产品，核对 ES 元数据后确认是我方 payload 与 UI 不一致，
     改按前端真实 payload 重建（24→30 条口径因此澄清），同时把这一现象降级为观察项 AG6-O1
```

### 清理与残留（收工必做）

| 项 | 清理前 | 清理后 |
|---|---|---|
| 知识库列表条数 | 16（含自建 1） | **15**（= 开工前 15，逐一名称比对一致） |
| ES `kb_38` / `faq_kb_38` / `table_chunks_kb_38` / `table_summary_kb_38` | 存在（faq_kb_38 峰值 43 条） | **全部 404 `index_not_found`** |
| Milvus `_kb_38` / `_table_chunks_kb_38` / `_table_summary_kb_38` / `_community_summary_kb_38` | 不存在（未生成） | 不存在 |
| 我的对话（5 条 `ag6*` + 1 条 UI 提问） | status=1 | **status=0（逻辑删除），列表接口不再返回**；行仍在库 |
| MySQL `knowledge_base`（id=38） | 1 行 | **1 行仍在，status=0（逻辑删除）** |
| MySQL `knowledge_base_list`（kb_38） | 3 行（523/524/525） | 同上（未物理删除） |
| MySQL `file_parse_task`（kb_38） | 3 行 | 同上 |
| MySQL `syn_log`（kb_38） | 0 行 | 0 行 |

**残留说明（如实记录，未手动改库）**：删库在 **ES 层是物理清理**（四索引 404）、**Milvus 无集合**、
**列表接口不可见**；MySQL 元数据行仍在（`knowledge_base.status=0` + 3 文件行 + 3 任务行）。
对话删除同样是**逻辑删除**（`dialogue.status 1→0`，`gmt_modified` 未更新），问题/答案行按 11:40 后时间窗计 6+6 行；
如需物理清理请由有 DB 权限者执行。

证据：`AG-6/evidence/cleanup-20261028T035629Z.json`、`AG-6/evidence/cleanup-dialogues.json`
写锁：`AG-6/evidence/.write-lock`（start=11:42:25 / stop=11:57:10），已记录后删除。

---

## 7. 给下一步的三条建议（按修复代价排序）

```
① D1 先修，且**不要**只改报错文案：把 update_doc 的"先删后插"改成"先写入/或先 update_by_id 原地改，
   成功后再清理旧文档"，并对 asyncio.run 在请求上下文中的用法做一次改正（现写法 100% 失败）
   修完必须回归：编辑后答案变了、条数不变（本轮判据可直接复用：ES 条数 + 列表 total 前后相等）
② D3 一行改：retrieval_service.py:526 的 metadata["query"] → metadata["question"]
   修完用本轮脚本即可验证（faq_question 应与库内 question 逐字符相等）
③ D2 属机制问题：FAQ 直答要能回答"凭什么是这一条"。建议
   精确问句相等 → 直接返回该问答对（短路）；否则把候选集与选中项写进响应/页面（让用户看得到）
   仅靠 /llm_faq_select 选答案，在近似重复问答对较多的库里必然出现本轮这种串答
```
