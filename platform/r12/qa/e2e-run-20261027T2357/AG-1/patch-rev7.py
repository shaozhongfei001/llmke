#!/usr/bin/env python3
# rev7：新增内容级越权实证（P0 最高档），缺陷 10→11 条
import io
P = "AG-1-report.md"
s = io.open(P, encoding="utf-8").read()

ANCHOR = "  - **两个静态高危项（尚未做运行态验证，列为待验证）**："
NEW = """  - **[rev7] 静态高危项已运行态证实 → P0 最高档（内容级越权）**：见下方"内容级越权实证"小节，D-1b
  - **两个静态高危项（原标"待验证"，其中第 1 条已于 rev7 证实）**："""

assert ANCHOR in s
s = s.replace(ANCHOR, NEW, 1)

# 在 P0 明细块之后插入内容级越权实证小节（锚点：S13-02 标题前）
SEC = """### S13-01B（rev7 新增）内容级越权实证：无授权账号读他人知识库全文

- 主体：`r13_noauth`（无任何授权）；目标库 kb_34；**3 次只读 GET（上限内），零写入**
- 无权对照（既有证据）：同账号 `getKbById?id=34` = **403 / 30016**

| # | 请求 | HTTP | chunk 数 | 是否真实正文 |
|---|---|---|---|---|
| ① | `GET /file/getFileChunks?kbId=34&docId=483&pageNo=1&pageSize=3` | **200** success=true | total=1, records=1 | **是**：`"「智"造贷」企业流动资金贷款产品说明书 文件编号：PRD-CORP-LOAN-20██-██（R12 验收测试夹具…）一、适用对象 面向制造业中小微企业…"` |
| ② | `GET /file/getKbFileChunks?kbName=R14-BASELINE-KB&fileName=docx-plain.docx` | 200 success=true | **0** | 否 —— 但**错键名也返回 200 成功**（fail-open，见 D-1d） |
| ②' | `GET /file/getKbFileChunks?kbName=kb_34&fileName=docx-plain.docx` | **200** success=true | **1** | **是**：`"Plain DOCX 第一段：客户访前准备。第二段：日均存款 █,███,███.██ 元。"` |

- 判定：**FAIL（P0 最高档：从"元数据泄露"升级为"跨库读原文"）**
- 关键点：**② 的入参不含 kbId**，只要 `kbName + fileName`；而 `kbName` 就是 **primitiveName = `kb_<id>`**，A 类列表接口的响应里 `primitiveName` 字段**直接给出**，无需猜
- **完整可达链路（任意已登录账号，全程无授权）**：
  `GET /file/folder/list?kbId=<N>`（A 类，无 assert）→ 拿到 `id / primitiveName / fileName / convertedFilePath`
  → `GET /file/getFileChunks?kbId=<N>&docId=<id>` 或 `GET /file/getKbFileChunks?kbName=kb_<N>&fileName=<fileName>`
  → **读到任意库任意文件的全文分块**
- 证据：`AG-1/evidence/S13/K-content-level-leak-proof.md`（含三张表与打码后的正文片段）
- 3 次额度用法说明：原定第 3 次用于"换库确认非特例"，我改用在 ② 的键名复核（否则会把可能的内容漏洞记成弱泄露）；"非特例"已有替代保障——同账号对 kb_34 的 `getKbById` 403 已证无权。若需换库泛化样本，需再批 1 次只读 GET

### S13-02 伪造 Authorization 头 → 401/403，**不得 500**"""

s = s.replace("### S13-02 伪造 Authorization 头 → 401/403，**不得 500**", SEC, 1)

# 缺陷清单：新增 D-1b / D-1d，修改 D-1 描述为 D-1a
D1_OLD = "| D-1 | **P0** | 无权限账号可读任意知识库的文件清单与元数据（BOLA） |"
D1_NEW = "| D-1a | **P0** | 无权限账号可读任意知识库的文件清单与元数据（BOLA，元数据层） |"
assert D1_OLD in s
s = s.replace(D1_OLD, D1_NEW, 1)

# 在 D-1a 行后插入 D-1b
row_end = "| 2/2 账号 |"
idx = s.find(row_end, s.find(D1_NEW))
assert idx > 0
insert_at = idx + len(row_end)
D1B = """
| D-1b | **P0（最高档）** | 无权限账号可读他人知识库**全文分块**（跨库读原文） | `r13_noauth` → `GET /file/getFileChunks?kbId=34&docId=483` / `GET /file/getKbFileChunks?kbName=kb_34&fileName=docx-plain.docx` | 期望 403；实际均 `200 success=true` 且返回真实正文（① total=1、②' n=1）；② **不需要 kbId**，只要 `kb_<id>`+文件名，而 primitiveName 由 A 类接口直接给出 | 任意已登录账号可"枚举资产 → 读任意文件全文"；与 D-1a 串成完整攻击链；权限模型在此处等于不存在 | 2/2 接口（①②'） |
| D-1d | **P3** | 分块查询 fail-open：键名写错（用显示名）返回 `200 success=true, data=[]`，把"取不到"伪装成"成功且为空" | `GET /file/getKbFileChunks?kbName=R14-BASELINE-KB&fileName=docx-plain.docx`（显示名）vs `kbName=kb_34` | 期望 404/明确错误；实际 200+空数组，调用方无法区分"无此库/无此文件"与"该文件没有分块" | 排障误导、前端静默空态 | 1/1 |"""
s = s[:insert_at] + D1B + s[insert_at:]

CNT_OLD = "**缺陷条数：P0 = 1，P1 = 2，P2 = 5（D-5a / D-5b / D-6 / D-7 / D-9），P3 = 2（D-2 / D-8），合计 10 条。**"
CNT_NEW = "**缺陷条数：P0 = 2（D-1a 元数据 / D-1b 内容级），P1 = 2，P2 = 5（D-5a / D-5b / D-6 / D-7 / D-9），P3 = 3（D-1d / D-2 / D-8），合计 12 条。**"
assert CNT_OLD in s
s = s.replace(CNT_OLD, CNT_NEW, 1)

# 头部 rev 记录
s = s.replace("；**rev6 2026-10-28 12:05**", "；rev6 12:05", 1)
s = s.replace(
"（按批准做纯静态授权追踪：controller→service 方法全名+行号+判定，结论为 7 个映射有 assert、读接口 13 个无 assert、写接口 7 个无 assert；新发现 `getFileChunks`/`getKbFileChunks` 返回分块正文且无授权，列待验证）",
"（按批准做纯静态授权追踪：controller→service 方法全名+行号+判定；新发现 `getFileChunks`/`getKbFileChunks` 返回分块正文且无授权）；**rev7 2026-10-28 12:15**（3 次只读 GET 运行态证实内容级越权：两接口均 200 且返回真实正文，② 不需要 kbId → P0 从元数据升级为跨库读原文，新增 D-1b/D-1d，缺陷 10→12 条）", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("rev7 applied")
