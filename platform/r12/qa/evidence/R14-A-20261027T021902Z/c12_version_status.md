# C12 版本替换：三步判据实测（含对 C 结论的两处更正）

采集：2026-10-27T12:06:05+08:00；19995 pid 721403（12:02:08），rag-index-service pid 474113（11:17:01）

## 步1：`metadata.version` 是否落库 —— **BLOCKED（仍为 null）**
```
ES kb_9 9 条文档 metadata.version 全部为 None（逐条核对）
  R12FIX-product-loan.docx      fid=290 ver=None ci=0 ct=02:29:00
  R12FIX-product-loan(1).docx   fid=328 ver=None ci=0 ct=10:45:15
  R12FIX-product-intro.pptx     fid=330 ver=None ci=0 ct=10:46:45
  R12FIX-product-intro(1).pptx  fid=343 ver=None ci=0 ct=11:20:15
  …… 其余 fid=331/332/333/334 同为 None
```
**更正 C 的判断**："`/qa` refs 里能看到 ver=V1"**不等于** ES 有 version：
- `alg_retrieval_service/app/retrieval_fun_tool.py:143` 有 `df["version"] = df["source"].map(_ver_from_source)`，
  即版本号是**从 source 路径 `/V\\d+/` 正则反推**的兜底值（R13-VER-11），与 Java 透传无关；
- 因此"透传是否生效"**只能看 ES `metadata.version`**，现在仍是 null。

## 根因：index 服务没有重启（新 jar 未加载）
```
rag-index-service  pid=474113  端口 18082  启动 11:17:01
target jar mtime  12:04:51  md5 6fd91ccc639a7a46decbda20aa7e4597
C staged jar      /tmp/r14_c/new-index2.jar 11:52:15  md5 47de4b6b7499a1255017a2553f0155d5
→ 两者 md5 不同，且进程启动早于两个 jar，运行中加载的是旧 class。
```

## 补充（12:1x 复核）：target jar 整体 md5 不可作判据，要按 class 级比
```
new-index3.jar (C 构建)  md5 6fd91ccc…  11:52:15
target jar               md5 ae20b1a7…  12:08:21   ← 之后又被别人重建过一次
BOOT-INF/classes 202 个 class：两者逐字节一致，差异 0
  KnowledgeBaseListAppServiceImpl.class 双方均 05d0e6941422fa7f0542df34195ea3ff
```
结论：`file.setVersion(fileInfo.getVersion())`（version 透传）确实在 target 里，"只差重启"成立。
整体 md5 会被任何模块的重新构建改变，判等必须落到承载改动的 class。

## 步1-b（12:36 实测）：version 能落 ES，但**检索侧仍然全部靠 source 兜底**
直连解析（`POST 12340/parse_sync`，`version:"V1"`，文件 fid=328 真实重解析，5.0s 返回 200）：
```
ES kb_9  fid=328  _id=409721235889955614  ver=V1  ci=0  parent=R12FIX-product-loan.docx   （1 条，kb_9 总数仍 9）
Milvus _kb_9 fid=328  pk=409721235889955614  ci=0                                        （1 行，total 仍 9）
```
→ **`server/loader.py:430 metadata.version = getattr(_file,"version",None)` 生效，version 可落 ES；ES `_id` 与 Milvus `pk` 仍一致。**

但检索侧打点（C 的 FIX-17，已含新增的 `无版本行`）：
```
12:40:02  document_version: blocks=5 其中靠 source 路径兜底=5 无版本行=0
12:40:22  document_version: blocks=6 其中靠 source 路径兜底=6 无版本行=0
```
而同一时刻 `POST 19527/search_by_custom_param` 返回的 `_source.metadata` 明确带 `version=V1`（fid=328），
说明 **`document_version()` 收到的 blocks 里根本没有 version**——version 在"多路召回 → rerank → 合并"环节被丢了，
不是 ES 没落库。**结论：C 提的"兜底=0"判据，只靠重解析永远不会达成**，还要修主路径的 metadata 透传（`retrieval_service.py:534` 之前）。

旁证（解释为什么这个缺陷长期被掩盖）：Milvus `_kb_9` 的 schema **没有 version 列**
（fields 实测：pk/text/vector/source/chunk_doc_id/document_id/.../main_id，无 version），
任何只经 Milvus 命中的块天生无 version，只能靠 source 正则。

另一个副作用（重要）：本次重解析把 fid=328 的 `_id` 从 `1689901252393637717` 换成 `409721235889955614`，
原因是 `document_id` 由**调用方传入的路径形态**决定（这次是 `r12-rag/kb_9/.../V1/xxx.docx`，上次是文件名 `xxx.docx`），
而 `derive_doc_id` 的种子含 `document_id` → 同一文件同内容也会换 id。**这是图侧 `chunk_pk_list` 悬空的机制性根源**：
pk 依赖一个易变的 document_id，而不是稳定的 file_id。

## 步2：V0/V1 两代在 ES 共存且 pk 互不覆盖 —— **PASS**
```
product-loan:  fid=290 ver=None 正文含 5000万  _id=498386897502206386
               fid=328 ver=None 正文含 8000万  _id=1689901252393637717
product-intro: fid=330 ver=None 正文含 5000万  _id=2107837105731089944
               fid=343 ver=None 正文含 8000万  _id=2779346151338697596
（两代各自独立行、pk 不同，可分别检索到）
```

## 步3：提问"最高额度"是否各命中自己版本 —— **PASS（V0 未污染）**
```
query=智造贷单户最高授信额度是多少  enabled_graph=false/true  enabled_rerank=true/false
  top_k=5  th=0.001 : docs=2  → fid=328(V1,8000万) / fid=343(V1,8000万)
  top_k=10 th=0.001 : docs=3  → 上述两条 + fid=329(V0 台账，另一文档)
  top_k=20 th=0.0001+graph : docs=6 → 仍无 fid=290/330（V0 版产品文档）
→ V0 版从未进入候选，答案取到 8000万（V1）。
```
机制：`retrieval_fun_tool.document_version()`（R13-VER-11）按版本号只保留"当前有效版本"，
所以 B 担心的"V0/V1 同进候选、答案在 5000万/8000万 间摇摆"在本环境**未复现**。
注意：这套过滤依赖 `_ver_from_source`（source 正则），**不是**依赖 ES metadata.version；
一旦某天 source 里没有 `/V\\d+/` 段，过滤会失效——这是 C12 的真实残余风险。
