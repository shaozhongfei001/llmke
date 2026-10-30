# 图谱抽取链路架构评估：自研 vs 官方 GraphRAG

**文档用途**：提交外部专家做**双重架构评估**
① 评估现有自研方案的技术合理性
② 评估"是否应以官方 GraphRAG 框架替代自研图谱抽取"这一决策

**被测候选**：`shaozhongfei001/llmke` main = `22dd800`
**编写时间**：2026-10-30
**事实来源**：本文所有数字均为本机真实实测（Nebula / ES / MySQL / 服务进程），
代码位置均给出文件与行号，可直接核对。凡属推断的地方均标注【推断】。

---

## 0. 结论摘要（先给判断，后给依据）

### 0.1 事实认定

```
本项目的图谱抽取与 GraphRAG 能力，是**从零自研的实现**，
未使用微软 graphrag、llama-index graphrag、LightRAG 等任何框架。

证据：services/rag-alg/requirements.txt 无 graphrag 依赖；
      Java pom.xml、前端零引用；
      全仓 grep "graphrag" 仅命中注释标题与交付文档；
      核心 5559 行 Python 全部为本仓自研代码。
```

它**套用了 GraphRAG 的方法论**（LLM 实体抽取 → 社区检测 → 社区摘要 → global/local 检索），
prompt 形态也借鉴了微软 GraphRAG（`("entity"::name::type)` / `####` 分隔 / 追问补漏），
但算法选型与工程实现是独立的一套。

### 0.2 我的判断（供专家质疑）

```
不建议整体替换为官方 GraphRAG 框架（方案 B）。
建议采用"服务壳保留自研 + 建图内核向官方对齐"的混合路线（方案 C）。

理由不是"自研更好"，而是：
  本项目真正卡住的能力——多知识库隔离、代次、权限域、在线证据回指——
  官方框架同样没有或很弱，换框架不能解决，还要额外承担集成成本。

但自研确实缺了四步，且这四步是官方已经验证过的成熟做法：
  ① 实体消歧（entity resolution）
  ② 社区算法用 Leiden 而非 Louvain
  ③ 社区报告结构化（findings/claims + 来源回指）
  ④ 抽取格式修复（format repair）而非丢弃
```

### 0.3 本文要专家裁定的 8 个问题

见 §10。其中最关键的三个：

```
Q1  是否认同"换框架不解决代次/权限/证据回指"这一判断？
Q2  实体消歧应该做成独立离线步骤，还是嵌入抽取时（entity linking）？
Q3  社区算法是否必须换 Leiden（涉及"社区内连通性"是否作为验收项）？
```

---

## 1. 系统定位与边界

### 1.1 它不是一个 GraphRAG 产品，而是一个"知识库平台里的图谱增强子系统"

```
上层：Java 微服务（rag-index-service / rag-qa-service）
      · 负责知识库/文件/权限/代次/状态机/任务编排
      · 图谱只是"文件解析"之后的又一个异步后处理
下层：Python 算法服务（index_graph_service，端口 19529）
      · 负责抽取、建图、社区、摘要、图查询
存储：Nebula（图）+ Elasticsearch（chunk 与社区摘要）+ Milvus（实体/三元组向量）
```

这个定位决定了几件事，也是后面所有架构权衡的前提：

```
· 图谱构建是**文件级触发**的（Java 侧按 fileId 发起），不是"整库批处理"
· 必须有在线状态与失败可见（用户点按钮要看到进度）
· 必须支持多知识库并存（每个 KB 一个 Nebula space）
· 必须支持代次（文档重传后新旧不能混）—— 这一点目前未实现，见 §3.4
```

### 1.2 代码规模与分层

| 层 | 文件 | 行数 | 职责 |
|---|---|---|---|
| 抽取 | `graph_extract.py` + `prompts/entity_extraction.py` | 573 + 82 | LLM 抽取实体与关系、多轮补漏、重试 |
| 归一/类型 | `graph_types.py` | 733 | 类型白名单、实体过滤、canonical 归一、三元组去重 |
| 建图 | `graph_service.py` | 1109 | chunk 读取、抽取编排、顶点/边写入、向量双写 |
| 图工具 | `graph_fun_tool.py` | 1129 | LLM/向量库/Nebula 访问封装、PPR 数据准备 |
| 社区 | `graph_community.py` | 210 | Louvain 社区检测、社区 id 派生 |
| 摘要/检索 | `graph_summary.py` | 996 | 社区摘要 MAP/REDUCE、global/local 查询 |
| 图算法 | `graph_p_array.py` | 200+ | Personalized PageRank 扩散 |
| 服务 | `graph_api_start.py` | ~120 | FastAPI 路由 + 巡检 + 中间件 |

合计约 5559 行 Python（不含测试与脚本）。

---

## 2. 现有技术方案（详细）

### 2.1 建图数据流

```
① Java: POST /index/knowledgeBase/file/graphParse  {file_ids:[...]}
   ↓ 异步线程
② Java → Python: POST /generate_triple_data
   {space_name, col_name:"file_id", col_values:[fileId], model_info, top_k}
   ↓
③ Python: get_document_chunk() 从 ES 取该文件的 chunk（kb_9 每文件 1~N 块）
   ↓
④ Python: fetch_known_entities() 从 Nebula 取本库已有实体（R15 新增，用于 entity linking）
   ↓ 逐块循环
⑤ Python → LLM(18092 /v1/chat/completions): 抽取
   每块最多 5 轮（首轮 + 追问补漏），失败重试 3 次
   ↓
⑥ normalize_graph_data(): 类型判定 → 实体过滤 → canonical 归一 → 三元组清洗/去重
   ↓
⑦ 三写：
   · Nebula  g_<kb>：INSERT VERTEX entity + INSERT EDGE relationship
                       边 rank 由 (src, 谓词, dst) 的 SHA1 派生（R15 修）
   · Milvus  graph_entity_<kb> / graph_triples_<kb>：向量化，供相似实体查询
   · ES      不写（chunk 已在 ES，仅读）
   ↓
⑧ 返回 BaseResponse(code, msg, data{triples_total, edges_total, edges_written, type_report})
```

### 2.2 抽取环节的关键实现细节

```
prompt 结构（prompts/entity_extraction.py）：
  system_prompt  : 目标 + 步骤 + "分级/分档对照必须逐项抽取" 反例约束 + 2 个 few-shot 示例
  user_prompt    : Entity_types / (R15 新增)Known_entities / Text
  追问           : CONTINUE_PROMPT（"上次遗漏了，请补充"）+ LOOP_PROMPT（"还有吗？Y/N"）
  输出格式       : ("entity"::name::type) / ("relationship"::rel::src::dst::desc)，#### 分隔

多轮策略：
  MAX_EXTRACT_ROUNDS 默认 5。原为 2 轮，实测 459 字的"产品要素+评级加点表"
  两轮只能覆盖约 2/3 事实，因此改为默认 5 轮、成本护栏改由上限控制。

重试策略：
  单块失败重发**完全相同的 messages**（只递增 seed），prompt 语义不变。
  失败分类见 _classify_attempt：截断 / 解析失败 / 关系行全部丢弃。
```

### 2.3 归一与过滤（这是自研痕迹最重的一段）

`normalize_graph_data()` 做了六件事，每件都是"踩坑后补的"：

```
① 类型白名单      ALLOWED_TYPES 27 码（6 大类），越界落 unclassified
② 实体过滤        is_valid_entity：停用词 / 纯数字 / 文档标题 / 测试夹具 /
                  sentence_like（整句当实体，R15 新增）/ 长度
③ canonical 归一  canonical_of（别名表 + 公司名前缀）+ numeric_canon（去"人民币/加/减"）
④ 三元组清洗      _junk（含逗号/超长丢弃）+ _clean_rel（含 "->" 取箭头前谓词，R15 新增）
⑤ 逆否去重        同一(关系,无序实体对)只保留首次方向
⑥ 谓词冲突改写    split_total_predicate："最高额度->1000万" 改写为 "分项上限->1000万"
```

### 2.4 存储模型

```
Nebula（每 KB 一个 space，命名 g_<kb>）
  Tag   entity      : name, type, file_id, show_flag, ...
  Edge  relationship: name（谓词）, file_id, show_flag, page_num, generation, chunk_ref
  唯一键 (src, dst, rank, type)；rank 由断言身份派生，同端点不同谓词可共存

Elasticsearch
  <kb>                      : chunk 原文（270 条，当前库）
  community_summary_<kb>    : 社区摘要（10 条）

Milvus
  graph_entity_<kb>   : 实体向量（用于"相似实体"查询）
  graph_triples_<kb>  : 三元组向量
```

**三写的一致性问题**：Nebula 写成功、Milvus 写失败时，图里有事实但没有向量，
表现为"图能查到、相似实体推荐不到"。目前三步是顺序写、无事务、无补偿。

### 2.5 社区与摘要

```
检测（graph_community.py:64）
  networkx.community.louvain_communities(g, weight="weight", resolution=1.0, seed=42)
  手写分层：max_level 默认 2，level0 社区数 >= 2 才做 level1 聚合
  community_id = hash(namespace, level, sorted(members))  ← 逻辑身份，同划分同 id

摘要（graph_summary.py）
  MAP   : 每个社区 → 3-6 句自由文本摘要（prompt 明确禁止编造）
  REDUCE: global 查询时，对命中的社区摘要做一次 LLM 汇总
  存储  : ES 主存 + Milvus 同写（索引/collection 同名 community_summary_<kb>）
```

这里有两个自研特色，官方没有：

```
· community_id 逻辑身份（同一图同一划分 → 同一 id），原用 uuid4 导致重建即失效
· 摘要额外落 file_names（不只是 file_ids），因为文档重传后旧 file_id 指向已删文件，
  global 引用会出现"摘要能显示、source 点不开"
```

### 2.6 检索

```
local  : 实体识别 → 图子图查询（无向 MATCH）→ **PPR 扩散**（graph_p_array.py）
         cal_ppr_score_hippo 用 igraph 的 personalized_pagerank，
         alpha=0.1，取 ppr>0.05 的实体，再回捞 chunk（get_chunk_by_ppr_score）
global : query_community → 命中社区摘要 → MAP 事实 + REDUCE 生成答案
         R15 修：question_re 现在会真正消费 global_answer（此前直接丢弃又重新生成）

PPR 这一层是自研的，官方 GraphRAG 的 local search 是"实体邻域文本拼装"，
不做图扩散。这是本项目相对官方的一个能力增量。
```

### 2.7 调用方与入口

```
前端（frontend/plateform/src/components/KnowledgeBaseZh）
  GraphBox.tsx:462-464   showGraphHandler → type:"allGraph"
  GraphBox.tsx:753-762   文件行 → type:"subGraph" + fileId
  GraphBox.tsx:851-861   页面顶部"可视化图谱"按钮
  GraphCanvas.tsx:62-74  按 type 调 wholeGraphSearch / subGraph

后端接口
  POST /graph/search/wholeGraphSearch {spaceName}        → {nodeList, edgeList}
  GET  /graph/search/subGraph?spaceName=&fileId=
  实测：wholeGraphSearch 返回 111 节点/92 边（整库）；subGraph(343) 返回 27 节点/50 边
```

**这说明"库级图"在接口层是成立的**，用户感知不到的原因不是入口缺失，
而是整库图本身在拓扑上是多个互不相连的簇（见 §3.2）。

### 2.8 实测规模与资源

```
当前库 kb_9：
  图      137 实体 / 114 边
  chunk   270 条
  社区摘要 10 条
  图服务   RSS 135 MB，单进程
  单文件抽取耗时  464 字文档约 157 s（含 5 轮追问 + 3 次重试）
```

---

## 3. 现状质量评估（用实测说话）

### 3.1 抽取能出东西，但受"表述随机性"支配

```
同一段 129 字文本、同一模型：
  不注入 ：10 条关系 → 归一后 7 条三元组，过滤 0 丢弃 0
  注入80个无关实体：模型格式漂移，整句当实体，日志"关系行全部丢弃，重试3次仍失败"
```

### 3.2 整库图是多个孤岛

```
kb_9 边按文件：343=66, 329=21, 333=4, 332=1
跨文件实体：2 个（日均存款、智造贷）
连通分量：4 个（44 / 4 / 4 / 3）
```

### 3.3 三类真实缺陷（均已修复，作为质量基线）

```
① 边唯一键缺失  Nebula 边唯一键含 rank，原实现 rank 恒 0、谓词只作属性
                → 同端点不同谓词互相覆盖；写边处还人为补一条反向边造伪事实
② 关系名含 "->" 被整条丢弃  "加点幅度->加30个基点" 因含 "->" 判为脏数据丢弃
                → 3 档加点全灭；同一模型换种说法就能保留
③ 写入失败裸奔  Milvus 返回非 JSON → JSONDecodeError 冒泡 → HTTP 500 + 空 body
                → 调用方只看到 "Internal Server Error"，44 条图数据全部丢失
```

### 3.4 未实现的能力（架构级缺口）

```
· 代次（generation）  MySQL 无 build/manifest 表，ES/Nebula 无代次维度
                      → 文档重传后新旧边混在一张图（合同要求 8 字段的 BuildRun）
· 证据回指           社区摘要是自由文本，摘要中的句子无法定位到 chunk
· 自动建图           上传时传 isGraphParse=true，实测 graph_parse_status 一直停在 1
· txt 上传           txt 也被送进 LibreOffice 转 PDF → 必然失败
```

---

## 4. 官方 GraphRAG 的能力模型

微软 graphrag（Python 库/CLI）的标准流水线：

```
① 文本切分（固定/语义）
② 实体与关系抽取（LLM，prompt 内置，格式 `("entity"<|>...)`）
③ **Entity Resolution**（实体消歧合并，embedding + LLM 判定）
④ 社区检测（**Leiden**，天然层级，递归下钻）
⑤ 社区报告（结构化：title / summary / findings / claims，每条 claim 有来源）
⑥ 索引输出（Parquet + LanceDB/向量库）
⑦ 查询：
   Global Search = 对社区报告做 map-reduce
   Local Search  = 实体邻域文本 + 关系描述拼装
   DRIFT Search  = 混合
```

官方强项与弱项（这是判断"能不能换"的关键）：

| 维度 | 官方 GraphRAG | 说明 |
|---|---|---|
| 离线全量建图 | 强 | 批处理设计，天然适合"一次性建完" |
| 实体消歧 | 强 | 独立步骤，效果经过调优 |
| 社区质量 | 强 | Leiden 保证社区内部连通 |
| 报告可回指 | 强 | findings/claims 结构化 |
| prompt 成熟度 | 强 | 针对多语料迭代过 |
| **增量/代次** | **弱** | 以全量重建为主，增量支持有限 |
| **多租户隔离** | **弱** | 设计上单语料库 |
| **在线状态/失败可见** | **弱** | CLI/批处理，不面向"用户点按钮等结果" |
| **图扩散检索（PPR）** | 无 | local search 不做图扩散 |
| **中文业务语料优化** | 一般 | 需重调 prompt |

---

## 5. 逐项对照矩阵

| 能力 | 官方 GraphRAG | 本项目自研 | 差距性质 |
|---|---|---|---|
| LLM 实体抽取 | ✅ 成熟 prompt | ✅ 自维护 prompt（82 行，2 个示例） | **质量差距**：few-shot 少、无 format repair |
| 实体消歧 | ✅ 独立步骤 | ⚠ 仅字符串级 canonical + 别名表 | **能力缺失** |
| 社区检测 | ✅ Leiden 分层 | ⚠ Louvain + 手写 2 层 | **算法差距**（Louvain 会切出不连通社区） |
| 社区报告 | ✅ 结构化 claims | ⚠ 自由文本 3-6 句 | **能力缺失**（影响证据回指） |
| 增量/代次 | ⚠ 弱 | ❌ 无 | 双方都缺，需自建 |
| 多 KB 隔离 | ⚠ 弱 | ✅ 每 KB 一 space + 权限域 | **自研优于官方** |
| 在线状态机 | ⚠ 弱 | ✅ 状态码 + 失败原因 + 重试 | **自研优于官方** |
| 图扩散检索 | ❌ 无 | ✅ PPR（igraph personalized_pagerank） | **自研优于官方** |
| 多格式解析 | ⚠ 文本为主 | ✅ PDF/DOCX/XLSX/PPTX/OCR/VLM（Java 侧） | **自研优于官方** |
| 权限过滤 | ❌ 无 | ✅ 与 KB 权限域绑定 | **自研优于官方** |
| 三写一致性 | 单一索引 | ⚠ Nebula/Milvus/ES 顺序写无补偿 | **自研缺陷** |

**读法**：4 项自研优于官方、4 项官方优于自研、1 项双方都缺。
这决定了"整体替换"的净收益是负的——**会丢掉 4 项已有优势，只换回 4 项可局部补齐的能力**。

---

## 6. 差距根因（为什么自研会长成这样）

```
R1  缺少"实体消歧"独立步骤
    → 只能靠字符串相等合并（VID = 实体名），所以 "智造贷"/"该产品" 永远两个节点
    → 跨文档只能靠"恰好同名"，异构文档之间天然不连通

R2  社区算法选择了 Louvain（networkx 自带、零依赖）
    → 社区可能不连通，摘要会把无关事实拼在一起
    → 手写 2 层聚合，层级质量依赖调参

R3  社区报告是"自由文本"而非"结构化 claim"
    → 摘要里的话无法回指 chunk
    → A11（原文证据）在 global 路径上先天做不实

R4  抽取失败处理是"丢弃"而非"修复"
    → 模型表述漂移（关系名塞值、整句当实体）直接导致事实消失
    → 已修 _clean_rel，但同类问题还会以别的形态出现（缺 format repair 层）
```

四条根因的共同点：**每一处都是"当时选最省事的做法"，单独看都合理，串起来就成为质量天花板。**

---

## 7. 三个候选方案

### 方案 A：保持自研，补齐内核

```
做法：不引入官方库，按官方方法论补四步
  ① entity resolution 独立步骤（embedding 聚类 + LLM 判定）
  ② Louvain → Leiden（引入 leidenalg，或 networkx 的 louvain + 连通性校验）
  ③ community report 结构化（findings/claims + chunk_ref）
  ④ 抽取侧 format repair 层（关系名规范化 + 句子实体拆解）

工作量（估算）：3~4 人周
风险：中（改动集中在 Python 服务内部，不影响 Java/前端接口）
收益：直接命中 4 项差距，保留 4 项已有优势
```

### 方案 B：整体替换为官方 GraphRAG

```
做法：以官方 graphrag 库重建建图内核，Python 服务退化为"适配层"

工作量（估算）：8~12 人周，且需要：
  · 重写 chunk 读取（官方从文本文件读，我们从 ES 读）
  · 重写存储（官方输出 Parquet+向量库，我们需落 Nebula + 三写语义）
  · 重建权限/代次边界（官方无此概念，要在外层包）
  · 重写检索对接（官方有 CLI 查询，需包装成 HTTP 服务给 Java 调）
  · 重调中文业务语料 prompt（官方示例是英文语料）

风险：高
  · 官方库版本迭代快，锁定风险
  · 离线包体积（25G 已很紧），新增依赖需评估
  · 已有 PPR 检索、多 KB 隔离、权限过滤需要重新实现

收益：拿到 4 项官方优势（消歧/Leiden/结构化报告/prompt 成熟度）
      但其中 3 项在方案 A 里可以单独补，成本远低于整体替换
```

### 方案 C：混合——服务壳自研 + 建图内核对齐官方

```
做法：保留现有 Python 服务、存储模型、接口、检索（PPR）；
      只把"离线建图内核"按官方方法论重写为独立模块，可独立测试与替换

  具体：
  · 抽取：保留现有链路，增加 format repair 层；prompt 参考官方重写（few-shot 扩充到 6+）
  · 消歧：新增 resolve_entities(chunks) 独立步骤，在抽取后、建图前执行
  · 社区：引入 leidenalg（或保留 Louvain + 连通性拆分），社区 id 逻辑身份不变
  · 报告：community report 改为结构化（title/summary/findings[].claim + source_ref[]）
  · 检索：local 保留 PPR；global 改为消费结构化 report，支持 claim → chunk 回指

工作量（估算）：4~6 人周（比 A 多出"结构化 report + 检索改造"）
风险：中低（新增模块可与旧链路并行，按开关切换，可回退）
收益：拿到全部 4 项官方优势 + 保留 4 项自研优势 + 为 A11（证据回指）打好地基
```

---

## 8. 方案对比

| 维度 | A 补齐内核 | B 官方替换 | C 混合 |
|---|---|---|---|
| 工作量 | 3~4 人周 | 8~12 人周 | 4~6 人周 |
| 风险 | 中 | 高 | 中低 |
| 保留自研优势（PPR/多KB/权限/状态机） | ✅ | ❌ 需重做 | ✅ |
| 获得官方优势（消歧/Leiden/结构化报告） | ✅ | ✅ | ✅ |
| 支持 A11 证据回指 | ⚠ 部分（报告需结构化） | ✅ | ✅ |
| 可回退 | ✅ | ❌ 推倒重来 | ✅ 开关切换 |
| 离线包影响 | 小（+leidenalg） | 大 | 小 |
| 对 Java/前端接口影响 | 无 | 大 | 无 |

---

## 9. 推荐方案与分阶段路线（方案 C）

```
阶段 0（1~2 天）  固化基线
  · 冻结当前候选的验收结果与证据（已完成：verify.sh + baseline/expect.json）
  · 明确"换内核"的对照指标：跨文件实体数、连通分量数、claim 可回指率、抽取三元组数

阶段 1（3~5 天）  抽取侧 format repair（ROI 最高）
  · 关系名规范化（已做 _clean_rel，扩展到 target 侧：句子实体拆解）
  · prompt 扩 few-shot（把"分档对照""额度分项"做成示例）
  · 验收：同一夹具连续 5 次抽取，三元组数方差收敛

阶段 2（1 周）    实体消歧独立步骤
  · resolve_entities：Milvus 现有实体向量 + 相似度聚类 + LLM 判定同名异体/异名同体
  · 输出 alias 表，写回 canonical 顶点（保留 mentions 审计，现有结构已支持）
  · 验收：A17 三份夹具跨文件实体数从 1 提升；且"同名不同主体"不误合并（D7 反例）

阶段 3（1 周）    社区算法与报告结构化
  · Louvain → Leiden（或 Louvain + 连通分量拆分）
  · community report 结构化：{title, summary, findings:[{claim, source_ref:[chunk_pk]}]}
  · 验收：社区内连通；每条 claim 能回指 chunk（A11）

阶段 4（1 周）    检索侧消费结构化报告
  · global 改为 claim 级 map-reduce，回答里每条结论带 claim id
  · local 保留 PPR，但把 PPR 命中的实体与 claim 交叉，提升可解释性
  · 验收：A08（两入口一致）+ A11（引用可回查）

阶段 5（3~5 天）  回归与证据
  · A01–A17 全量复跑；对比 baseline
  · 输出"换内核前后"的对照报告
```

---

## 10. 需要外部专家裁定的问题

```
Q1  是否认同"换官方框架不解决代次/权限/证据回指，净收益为负"这一判断？
    如果不认同，请指出我低估了官方的哪一项能力。

Q2  实体消歧应做成"抽取后独立步骤"，还是"抽取时注入（entity linking）"？
    实测：抽取时注入无关实体会导致模型格式漂移（80 个实体注入 → 关系行全部丢弃）；
    改为"只注入本文出现过的实体"后恢复。这说明 online 注入对上下文极敏感。
    是否应彻底放弃 online 注入，改为纯离线批量消歧？

Q3  社区算法是否必须换 Leiden？
    现用 Louvain（networkx 自带，零新依赖）。Leiden 需引入 leidenalg。
    若不换，用"Louvain + 连通分量后拆分"能否满足 A17 第 5 条的"真实算法社区"？

Q4  community report 的结构化程度应该到哪一级？
    {title, summary, findings[]} 够不够？claims 是否要带置信度与冲突标记？

Q5  三写（Nebula/Milvus/ES）无补偿，是否应先做"写失败可重放"（幂等）再谈算法升级？
    现在一次 Milvus 非 JSON 响应就会让 44 条图数据全丢。

Q6  A11（原文证据）要求"每个关键结论有真实支持"，在 global 路径上
    是否只有结构化 claim 才能满足？自由文本摘要是否可以直接判不合格？

Q7  是否认同"不要求所有文档强行连通"（任务书 §1.4-7）与
    "跨文档实体数应提升"（A17 第 2 条）之间存在张力？
    边界应如何划定：什么情况必须连通、什么情况允许独立分量？

Q8  中文业务语料下，官方 prompt 直接迁移的可用性如何？
    是否需要中文 few-shot 重建（成本约 2~3 天），还是官方 prompt 已足够？
```

---

## 11. 风险与回退

| 风险 | 影响 | 缓解 |
|---|---|---|
| 引入 leidenalg / 消歧 LLM 调用导致抽取耗时上涨 | 单文件 157s 可能翻倍 | 消歧离线批量、按库触发；抽取链路不变 |
| 结构化 report 改造破坏现有 global 查询 | 问答不可用 | 新旧双写，开关切换，A08 守住两入口一致 |
| 实体消歧误合并（同名不同主体） | 比不合并更糟 | 保留 mentions 审计 + D7 反例必过 + 可人工回滚 |
| prompt 改动导致抽取结果波动 | 已通过的 A03 可能回退 | 固定种子 + 连续 5 次方差检查 |
| 离线包新增依赖 | 25G 包更大、复建风险 | 优先选纯 Python 实现（leidenalg 有 igraph 底座，已在依赖内） |

**回退预案**：方案 C 的所有改动都在 Python 服务内部，且新增模块（消歧、结构化报告）
以"开关 + 新旧双写"方式接入；任一步失败可直接关闭开关回到当前行为，不影响 Java/前端。

---

## 12. 附录

### 12.1 关键代码位置（可直接核对）

```
抽取        services/rag-alg/index_data_service/index_graph_service/graph_extract.py:122
            prompts/entity_extraction.py:6 (system_prompt) / :60 (user_prompt)
归一过滤    graph_types.py:153 (is_valid_entity) / :196 (numeric_canon) / :210 (canonical_of)
            graph_types.py:606 (_junk) / :607 附近 (_clean_rel)
            graph_types.py:557 (类型推断 + 金额单位校验)
建图        graph_service.py:528 (generate_triple_data) / :475 (llm_generate_triple)
            graph_service.py:372 (_edge_rank 边 rank 派生) / :751 (Milvus 写入，曾 500)
社区        graph_community.py:53 (detect_communities) / :21 (community_id_for)
摘要检索    graph_summary.py:600+ (_join_grade_rules 推导) / query_community
PPR         graph_p_array.py:78 (cal_ppr_score_hippo) / :114 (cal_ppr_fun)
服务入口    graph_api_start.py:79 (/generate_triple_data) / _safe_entry 兜底
前端入口    frontend/plateform/src/components/KnowledgeBaseZh/GraphBox.tsx:462,753,851
            GraphCanvas.tsx:62-74
```

### 12.2 实测数据快照（2026-10-30）

```
Nebula g_kb_9      137 实体 / 114 边 / 连通分量 4 / 跨文件实体 2
ES kb_9            270 chunk
ES community_*     10 条摘要
图服务进程          RSS 135 MB
单文件抽取          464 字 → 157 s / 44 条三元组 / 70 条边（修复后）
验收基线            A01–A16：PASS 8 / FAIL 1 / SKIP 7（platform/r15/baseline/expect.json）
```

### 12.3 本文未覆盖

```
· 官方 GraphRAG 的实际跑分（未在同等语料上做过对照实验）
· 大规模（10 万+ 实体）下的性能与社区算法收敛性
· 多语言语料下的 prompt 表现
· 成本模型（LLM token 消耗 vs 抽取值）
以上需在阶段 0 补齐或由专家补充评估。
```

### 12.4 术语对照

| 术语 | 本文含义 |
|---|---|
| 图谱增强 | 前端"图谱增强"功能，对应后端 graphParse → generate_triple_data |
| 社区 | GraphRAG 的 community（实体关系簇），**不是**知识库本身 |
| 代次 | generation，文档版本对应的图数据版本 |
| 三写 | Nebula + Milvus + ES 的同步写入 |
| claim | 社区报告中的一条可回指的事实陈述（官方 GraphRAG 结构） |
