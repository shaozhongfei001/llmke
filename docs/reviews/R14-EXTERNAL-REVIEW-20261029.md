# R14 交付现状 / 待评审 / 待修复 —— 外部评审简报

| 项 | 内容 |
|---|---|
| 文档版本 | 2026-10-29，R14-LIVE 批次 |
| 用途 | 提交外部专家智能体评审：判定"能否验收""哪些必须先修""哪些设计已偏离目标" |
| 事实口径 | 只写本机实测过的；每条结论附证据路径或命令；未验证的一律标注 |
| 阅读建议 | 先读 §3（契约缺口）与 §6（待评审问题），再看 §1/§2 的细节 |
| 证据根 | `platform/r12/qa/evidence/`、`platform/r12/logs/`、`docs/reviews/` |

---

## 0. 一句话现状

**主链路已打通（上传 → 解析 → 图谱解析 → 可视化出图 → 问答引用），但"打通"与"符合契约"是两件事**：目前有 3 处实现明确违反 `contracts/` 里的 required 条款，且最关键的**本体（entity/relation 类型）合同目录是空的**，导致类型体系只能靠实现硬编码。

---

## 1. 交付完成情况（详细）

### 1.1 交付物

| 类别 | 内容 | 状态 |
|---|---|---|
| 源码 | 前端（React/Vite）、Java 四层（gateway/auth/index/qa/graph）、Python 算法服务、tools-database | 已提交 |
| 制品 | 前端 `dist/`（入口 `assets/index-*.js`，每次部署做 md5 自证） | 已部署 |
| 制品 | 各服务 jar（`services/rag-java/rag-parent/*/target/*.jar`） | 已构建、已重启 |
| 交付包 | `platform/r12/dist/offline`（25G，含 images/jars/frontend/src/bin/models） | 已重打 + `[ok] 离线校验通过` |
| 门禁脚本 | `platform/r12/bin/check-endpoints-sync.py`（接口注册表对账） | 已入包、已挂进装机流程 |
| 证据 | `r13_full`、`acceptance`、`security`、`revoke`、`F05` 五套运行证据 | 已提交 |

**提交序列（本批次）**

```
1e6705a  预览 / 图谱列表 / 图接口鉴权 / 图空间名 + 自研图谱渲染
7f46b13  输入类错误 400 / 大小单位 / 壳层接口 500 / 旧图谱路由预览
234044b  回归证据
05b8d7c  删库作废未完成任务 + 队列判据拆分
c3697c9  接口注册表对账门禁
f45d46b  门禁脚本入包（两份清单都要加）
d33225f  26 条 STALE 归零（25 条扫描器漏扫 + 1 条真缺失）
a5e315c  图谱解析全链路打通（4 处设计缺陷）
bbdd3a8  列表关系数恒 0 + 已删知识库查列表 500
```

### 1.2 已修复并实测验证的问题

> 格式：**现象 → 真因 → 修法 → 验证**。每条都可复现。

#### ① 文件列表无法预览 Office（用户直接报障）

```
现象  点 docx →「PDF请求失败: 500」
真因  两层：
      (a) /file/stream 白名单只有 md/pdf（checkFileExtIsSupported），docx 必 500/5004
      (b) 分流判据用了 getFileType()，而它对 Office 一律返回 "pdf"
          （R13 起按服务端转出的 PDF 渲染）→ 永远判不出该走 previewStream
修法  按**对象键真实后缀**判定（core/helps/fileAccess.ts）
验证  presign 200 → previewStream 200 → PDF 渲染 1/1，canvas=1
```

#### ② 图谱增强列表永远「暂无数据」

```
真因  SQL 按 parse_type=3 过滤，但图谱解析不新建 parse_type=3 的行，
      而是在原文件行上置 graph_parse_status
修法  Repository 改传 graphParsedOnly 参数；Mapper 增加
      AND graph_parse_status IS NOT NULL AND graph_parse_status <> 0
验证  kb=9 返回 10–11 行（此前 0 行）
```

#### ③ 图数据接口全部 401/30021

```
真因  seed 里 interface_info 有 17 条 /graph/*，但 resource_interface 一条都没挂
      → 网关 authenticate() 恒 false → 任何角色（含 admin）都拒绝
修法  挂到 resource_id=8；注意该表约定 is_del=1 才是"有效"（写 0 会被过滤）
      并固化进 init-endpoints.sh（否则重装后必然回归）
验证  nodes / edges / statistics 全 200
```

#### ④ 图空间名传了中文展示名

```
真因  前端传 kbName="R12验收主链" → 后端拼 g_R12验收主链（不存在）
      → NebulaGraph pool init failed（表现为 500，不是"空数据"）
修法  前端改用 kbInfo.primitiveName
验证  spaceName=kb_9 → 200，space=g_kb_9，87 节点 / 61 关系
```

#### ⑤ 图谱渲染空白（vendored 组件静默失败）

```
真因  vendored <AiGraph/>（@mxmweb/somelib）停在 app_init → app_wait：
      画布 1524×676 正常、三个数据接口 200、一个节点都不画、且不抛错
      控制台仅 "当前版本: undefined"、"Cannot read properties of undefined (reading 'config')"
修法  自研 GraphCanvas（SVG + 确定性力导，零新增依赖），
      数据取 /graph/search/wholeGraphSearch 与 /graph/search/subGraph
验证  circles=87  lines=61；节点数 87/87、关系数 61/61；点节点出属性面板
```

#### ⑥ 可预期的输入错误被当成服务故障（500）

```
真因  GlobalHandler 只识别 403/404/400 三类错误码，其余一律 500
      → 验证码错(30000)、参数非法(5004) 都返回 500
修法  增加 clientInput 分支 → 400
验证  验证码错 → 400 + {"errorMsg":"验证码错误！","errorCode":"30000"}
```

#### ⑦ 文件大小量级错 1024 倍

```
真因  fileSize 是**字节**，DTO.getSize() 直接 fileSize+"MB"；
      前端 formatFileSize 又按"入参是 KB"换算 → 双重错位凑出 6.4 GB
修法  后端 formatSize()（1024 进制 B/KB/MB/GB）+ 前端改按字节
验证  28.7 KB / 6.2 MB / 库总量 6.4 MB
```

#### ⑧ 每页一次 500 的壳层接口

```
真因  question.conf 未配置时是 '{}'（空对象），却用 JSON.parseArray 解析
修法  空/空对象返回空列表；真解析失败只 warn
验证  /qa/feedback/que/list → 200 {"data":[]}
```

#### ⑨ 队列"孤儿任务"与判据假红

```
真因  删除知识库不取消其任务 → 2 条 PENDING 永久滞留（最老 1321 分钟）
修法  新增 cancelOpenTasksByKb(kbId,msg)，删库时先作废；
      判据拆成 PARSE_QUEUE_STALL（只统计文件仍存在的任务）+ PARSE_ORPHAN_TASK
验证  r13_full 20/20；孤儿任务查询为空
```

#### ⑩ 已删知识库查列表 500

```
真因  buildKbFileListResult 里 knowledgeBase 为空时直接 getPrimitiveName() → NPE
修法  空值 warn + 只回基础字段（不补计数）
验证  kb=34（status=0）fileListType=3 → 200
```

#### ⑪ 列表「关系数」恒 0

```
真因  写边时 file_id 来自 triples_attribute 的键查找，键分隔符已改 \x1f，
      该处仍用 ",".join(ed) → 查不到 → file_id 写成空串 → 按文件查边数恒 0
修法  统一 TRIPLE_SEP
验证  新解析 docx-table.docx → node=6 / edge=4
遗留  修复前已解析的行边属性仍为空，需重建空间才显示正确值
```

#### ⑫ 图谱解析（LLM 抽取）全链路失败 —— 本批次最大的一个

**现象**：全库 `graph_parse_status=3`（成功）为 0，有效文件全是 1（未做）或 4（失败）；UI 上"图谱解析"永远失败。

**四个断点，逐个实证：**

| # | 断点 | 证据 |
|---|---|---|
| 1 | `space_name` 传中文名 → ES 索引不存在 | 日志 `es查询失败:'NoneType' object is not subscriptable`、`该知识库R12验收主链未查询到相关文本` |
| 2 | 类型表默认值是通用 NER 8 类 | 日志 `抽取类型表（source=request）：['人','机构','位置','时间','角色','疾病','药品','项目']` |
| 3 | 停用词表含"客户/公司/企业/产品/借款人" | 归一化后 `过滤N个`，三元组整条丢弃 |
| 4 | 三元组内部键用逗号，被金额 `2,983,333.33` 切断 | `KeyError: '日均存款,指标值,2,983,333.33'` |

**修法**：
```
① Java 侧 space_name 改用 primitiveName（ES 索引名就是 kb_9）
② base.py 默认改 None；显式传通用 8 类也视为"未指定"→ 统一升级业务类型表
③ 停用词只保留结构性词（下表/合计/单位/序号）
④ 新增 AMOUNT_LIKE（千分位/两位小数）→ 金额型纯数字不丢
⑤ 内部键统一 \x1f（4 处：拼接/归一/解析/写库），page_content 仍逗号展示
⑥ 零结果时返回归一化明细（保留/过滤/未分类/丢弃 + 被过滤示例 + 类型表来源）
```

**验证（改后实测）**：
```
docx-plain.docx      graphParse → 30s → gps=3（成功）  子图 51 节点 / 50 关系
product-intro.pptx   graphParse → 75s → gps=3（成功）  节点数 41
g_kb_9 总量          87/61 → 89/62（增量来自 App 自己的解析）
UI 图谱增强          「解析完成」+「可视化图谱」入口
点开渲染             51 圆 / 50 线，标签为真实实体（智造贷 / 1000万元 / 100个基点）
```

#### ⑬ 接口注册表与代码不同步（门禁化）

```
背景  网关接口级鉴权：interface_info（登记）→ resource_interface（挂资源）→ 角色。
      任何一环缺失都返回同一个 401/30021，"没登记"和"没权限"在外观上完全同形。
门禁  check-endpoints-sync.py：扫 13 个模块 444 条接口，与注册表对账，输出四类：
      MISS（代码有、注册表无）、BUCKET（分桶键错位）、OPEN（/api 面）、STALE（残留）
实测  代码 444 / 注册表 444 / MISS 0 / BUCKET 0 / OPEN 0 / STALE 0
```

清理过程中发现两件高价值事实：

```
· 26 条 STALE 里 25 条是**扫描器漏扫**（嵌套模块 tools-database、裸注解 @GetMapping、
  @GetMapping ("/x") 带空格、嵌套源码根拼错），只有 1 条是真缺失
  → 教训：清理动作必须排在"确认扫描覆盖率"之后，顺序颠倒就是事故
· 新增 BUCKET 检查的来源：某接口登记成 app_name_abbreviate=database，
  而网关用 URL 首段（index）查权限缓存 → 缓存里有这条也 401
```

### 1.3 回归结果（当前运行版本）

```
r13_full      20/20
acceptance    34/34
security      16/16
revoke        21/21
F05            9/9
合计         100/100
```

证据目录：`platform/r12/qa/evidence/CAPS-*`、`SEC-*`、`REVOKE-*`、`R14-F05-*`、`20261029T*`。

### 1.4 交付状态自证方式

```
前端    宿主 md5 == 线上 md5（每次部署执行）
jar     与进程启动时间比对（r12ctl status 的 STALE_JAR 告警）
包      离线校验 sha256 + 包内 entry chunk / jar 时间逐项核对
```

---

## 2. 项目设计面临的问题（实施侧判断）

> 这一节是"我看到的结构性问题"，不是单点 bug。请专家重点判断是否成立。

### 2.1 标识符由调用方透传，而不是服务端映射

契约 `GraphQueryRequest.description` 明确写：**"物理空间名由服务端映射"**。

但实现里"空间名"是一条贯穿三层的自由参数：

```
前端 kbName（中文） → Java knowledgeBaseName → Python space_name（同时用作 ES 索引名）
```

**这条链上一个多月出现了三次同类故障**（中文名、primitiveName、前端 state 丢失），每次都在调用方打补丁。这是"缺少映射层"的必然结果，不是三次独立的粗心。

同一模式在别处也存在：`app_name / app_name_abbreviate / URL 首段` 三套标识需要人肉保持一致，错位即 401。

### 2.2 缺 generation（代次）维度，与目标直接冲突

契约中 `generation` 在 Request / Response / Evidence / Health **全部 required**；
`docs/SDD-ENGINEERING.md` 也把"文件→代次激活/删除"列为三个测量切片之一。

而实现的物理空间是 `g_kb_9`（知识库级），**没有代次分区**：

```
后果  V0 与 V1 的实体/关系混在同一张图；
      按代次回滚、按代次审计、按代次清理都做不了；
      溯源只能靠节点属性 file_id，而 file_id 是"逗号拼接的列表"，不是稳定引用
```

### 2.3 结果不可回指（GraphEvidence 未落地）

契约要求 `GraphEvidence` 带 `evidence_id / node_ids / edge_ids / source_refs`（均 required、minItems=1）。
当前子图接口只回节点/边，没有 evidence 概念，也无法对一条关系回答"它来自哪个文件的哪一段"。

### 2.4 「图谱增强」语义混用：任务列表 vs 图谱视图

同一页面承担两种语义：

```
既是"图谱解析任务列表"（未解析→解析中→成功/失败，行内按钮随状态变化）
又被当作"看图谱的入口"（只有成功的行才出现"可视化图谱"）
```

用户点进来看到"暂无数据"时，无法区分"没解析过""解析失败""解析成功但图是空的"。这一页的文案与状态机需要重定义（是否要 4 态：未做/进行中/失败/成功但有 0 结果）。

### 2.5 图数据与应用状态脱节（旁路数据污染）

```
Nebula 的 g_kb_9 里有 87 节点/61 关系，但应用侧 parse_type=3 记录为 0
→ 图是旁路脚本建的，从没走过应用内解析链路
→ 用户看到"有图"，但应用认为"没解析过"；反过来修好解析后又叠加在旧图上
```

**没有任何 provenance 字段区分"脚本建的"与"App 建的"**，这在验收与迁移时是硬伤。

### 2.6 静默失败是本项目的主导故障模式

| 现象 | 失败时的外部表现 |
|---|---|
| vendored 图组件 | 不画、不报错，只停在 `app_wait` |
| 接口未登记 / 未挂资源 / 分桶错位 | 三种不同原因，同一个 `401 没有足够的权限` |
| 图谱解析 | 只回一句"数据未生成三元组数据"（现已补明细） |
| 解析任务 | 4(失败) 与"任务结束"在 DB 里同值语义不同，曾被误读 |

**共同点：失败不指向原因。** 这类系统无法靠"多点几次"定位，必须靠门禁与可诊断返回。

### 2.7 第三方 vendored 组件不可控

`@mxmweb/somelib`（AiGraph）已 minify，静默失败后无法定位；它读的 `initData` / `config` 契约没有任何文档。
本次以自研 SVG 渲染替代（87 节点规模下性能足够）。**风险仍在别处**：`GientechStreamReader`（预览）、`@mxmweb/fv`（PDF）同样是 vendored。

### 2.8 交付物落后于代码（三次）

```
现象  dist 落后 HEAD 一次、jar 落后源码一次、离线包落后代码两次
后果  "代码修好了"与"交付物修好了"之间存在时间窗，任何一次重装都会回退
已做  每次部署做 md5 自证；打包含"复制清单 + 必需文件清单"双清单核对
```

补充事故：**在服务运行时覆盖 jar** 会让进程进入懒加载损坏态（`ClassNotFoundException: com.mysql.cj.protocol.ExportControlled`），表现为整段接口超时。规则已定：先停服务再覆盖 jar。

---

## 3. 契约缺口（按 `contracts/` 现状逐条列）

### 3.1 【最严重】本体合同缺失

```
contracts/ontology/      → 只有 .gitkeep，空
contracts/registry.yaml  → 无任何 ontology 条目
```

**后果**：实体类型 / 关系类型 / 归一规则没有合同依据，只能在实现里硬编码。已出现两代"凭人设定的类型表"：

```
第一代（原始代码）：['人','机构','位置','时间','角色','疾病','药品','项目']   ← 通用 NER
第二代（本次修改）：['机构','客户','产品','金额','期限','指标','日期','业务动作',
                    '单证','条款','评级','地点','担保','编号','口径','其他']  ← 实施方选定
```

两代都没有契约背书。**这意味着"类型体系是否偏离目标"目前无法用契约回答**，只能靠评审判断。

### 3.2 graph API 契约覆盖不到"解析/抽取"

```
contracts/api/llmke-graph.openapi.yaml 只有两个端点：
  POST /v1/graph/query
  GET  /v1/graph/kb/{kb_id}/health
```

没有"解析触发 / 解析状态 / 抽取结果"的契约。当前实现暴露的 `/graph/search/*`、`/graph/info/*`、
`/graph/graphStatistics/*`（17 条）全部不在契约内，只能靠 `interface_info` 兜底鉴权。

**请评审：抽取是"内部能力，不需要对外契约"，还是"必须有契约约束其输入输出（含类型体系、失败语义）"？**

### 3.3 generation 契约与实现不一致

```
契约  Request/Response/Evidence/Health 全 required generation
实现  g_kb_9 无代次分区；file_id 是逗号拼接串
判定  契约与实现不一致，且属于"目标级"不一致（SDD 把它列为测量切片之一）
```

### 3.4 GraphEvidence 字段未落地

`evidence_id / node_ids / edge_ids / source_refs` 全部 required，实现无对应能力（见 §2.3）。

### 3.5 health 语义与 UI 冲突

```
契约  GraphHealth："仅授权运维角色可调用；**不公开跨域节点数或空间列表**"
实现  普通页面直接展示"节点数 87 / 关系数 61"
判定  契约禁止的能力被做成了常规 UI 元素
```

### 3.6 权限面（interface_info / resource_interface）不在契约体系内

这是**部署期**才生效的鉴权数据，没有任何 schema/契约约束，也不能被 `make contract-all` 校验。
本次已用 `check-endpoints-sync.py` 做门禁（MISS/BUCKET/OPEN/STALE），但**脚本不是契约**：
它依赖源码正则 + 数据库现状，无法覆盖"注解在父类""运行时动态注册"等形态。

### 3.7 错误码语义与契约不一致

```
契约  ErrorEnvelope（含 errorCode 语义）
实现  30021 / 30016 / 5004 / 999 混用，且曾把输入类错误(30000/5004)返成 500
状态  已修输入类为 400；但"同一失败多种错误码"的问题仍在（未登记/未授权/未挂资源都是 30021）
```

### 3.8 展示口径无契约

单位换算（B/KB/MB/GB）、"节点数/关系数"的统计口径（实例数 vs 去重实体数）、
"已解析"的判定（graph_parse_status=3 vs 有图数据）都没有契约定义，
于是出现"6.4 GB（实际 6.4 MB）"这种**数字看起来合理、量级错 1024 倍**的问题长期存在。

---

## 4. 下一步开发建议（优先级 / 工作量 / 风险）

| 优先级 | 事项 | 为什么 | 预估 | 风险 |
|---|---|---|---|---|
| P0 | **CR-3：ontology 合同**（`contracts/ontology/*.schema.json` + 别名/归一表） | 类型体系无合同，直接决定"是否偏离目标"，也是 CR-1/CR-2 的前置 | 2–3 人日 | 需业务确认类型清单，否则只是把"实施方拍脑袋"变成"合同拍脑袋" |
| P0 | **CR-1：generation 隔离** | 契约 required + SDD 测量切片 | 3–5 人日 | 选型：空间分区（干净，需重建）vs 属性过滤（快，查询成本高） |
| P1 | **CR-2：GraphEvidence 回指** | 契约 required；且决定"引用可不可信" | 2–3 人日 | 依赖图谱写入时保存 chunk 引用（当前只存 file_id 列表） |
| P1 | 图谱增强页语义拆分（任务视图 / 图谱视图分离） | 用户无法区分"没解析"与"解析了但空" | 1 人日 | 需产品确认 4 态文案 |
| P2 | 图服务 Nebula 会话池自愈（broken pipe 后自动重连） | 实测：500 → 重启服务 → 200，属可用性缺陷 | 1 人日 | 需确认现象是连接池老化还是 Nebula 主动断连 |
| P2 | 历史图数据治理（重建空间 / 补 provenance） | 旁路脚本数据与应用数据混存，无法区分 | 1–2 人日 | 重建会短暂影响演示数据 |
| P2 | 门禁扩展：schema 校验 + 契约生成物一致性 | `check-endpoints-sync.py` 只是兜底 | 2 人日 | 需要先有 §3 的契约 |
| P3 | 下线或明确 `/api/**` 对外面 | 现两套都已登记、都能用，维护成本翻倍 | 0.5 人日 | 需确认是否有外部集成方 |

**建议顺序：CR-3 → CR-1 → CR-2**。
理由：CR-1/CR-2 都要引用"节点是什么类型、边是什么语义、证据怎么表达"，本体没有合同，另外两条只能在临时约定上继续叠加。

---

## 5. 其他影响"完美达标"的点（容易被忽略）

### 5.1 环境噪声与产品缺陷长期混杂

```
· 本次出现 4 次强制终止（构建被 kill、日志中断）
· jar 覆盖运行中进程导致类加载损坏
· 服务进程陈旧：19529 图解析服务自 10-27 13:53 起运行，
  期间源码改过 3 次（max_tokens/seed/多采样），一直跑的是旧代码
```

**"跑的是哪份代码"这件事本身需要门禁**（现在只有 r12ctl 的 STALE_JAR 提示，且只覆盖 jar，不覆盖 Python 源码）。

### 5.2 数据层存在重复与逻辑删除并存

```
kb_9 同时存在：id 35–46（status=0）与 id 332–343（status=3）；
                id 119–124（status=0, graph_parse_status=3 旧成功记录）
后果：任何"按 kb 统计"的查询都会受污染；图实例统计与 UI 计数可能对不上
```

### 5.3 问答侧存在"语义反转"级别的问题（本次新证据）

```
问：智造贷最高额度是多少？
答（失败态）："信用方式下最高授信额度为人民币1000万元"
原文：8000 万总额中，信用方式这一部分不超过 1000 万
判定：数字对、语义反转 —— 把"分项限额"说成"最高额度"
```

且同一请求 3 秒失败（status=3），说明**失败前已提交半句内容**，用户先读到错答案、错误提示后到。

关联：`/qa/ai/question_re` 未实现 global map-reduce（该开关是假开关），
`/qa/ai/question` 才有实现 → **同一问题两条路径给两个错数**。

### 5.4 无性能/容量基线

全链路没有 SLO（解析时延、抽取 token 成本、图谱查询 P95）。
本次观测到：单文件图谱解析 30–75 秒（随文本量线性增长），但没有基线判断"这是正常还是退化"。

### 5.5 离线包无差分机制

25G 全量包，重打约 5 分钟（镜像复用）；但**没有增量/差分**，也没有"包内容与 git commit 的映射清单"，
导致"包是否包含某次修复"只能靠人工抽样（本次已发生两次包内 frontend 未更新的情况）。

### 5.6 QA 判据自身存在假阴性/假阳性风险

```
· 队列判据曾把"孤儿任务"当成"队列卡住"（假红）
· 图谱列表判据曾按 parse_type=3 判定，与实现口径不一致
· 契约生成物（generated/）与源码的一致性没有自动校验
```

### 5.7 中文名/原始名双标识是系统性风险

`kbName`（中文，展示）/ `primitiveName`（kb_9，物理）/ `app_name_abbreviate`（分桶键）
三者需要人肉保持一致，本次已因此产生 4 次故障（空间名、ES 索引名、权限分桶、前端 state）。

---

### 5.8 【安全】公开仓库历史中含明文数据库口令

```
发现  3 个运维脚本把 MySQL root 口令写成了环境变量的默认值
      （init-db.sh / graph-refresh.sh / offline-kit.sh）
影响  仓库为 public，口令随历史 commit 长期可见
处理  已改为"只从 .env 或环境变量读取，缺失即失败退出"，不再有内置默认值
遗留  历史 commit 里仍可检出；未做历史重写
建议  ① 轮换该口令（本机演示环境影响有限，但仓库是公开的）
      ② 装机流程改为首次安装随机生成 + .env.template 只留占位
      ③ 若需彻底清除，只能重写历史并 force push（需评估协作影响）
```

## 6. 待评审问题（请专家逐条给结论）

| # | 问题 | 需要哪种结论 |
|---|---|---|
| Q1 | 本体（entity/relation 类型）合同是否应作为 P0，先于 generation 隔离？ | 优先级判定 |
| Q2 | "物理空间名由服务端映射"应落在哪一层：gateway / graph-service / index-service？ | 架构位置 |
| Q3 | generation 隔离选型：**物理空间分区** vs **节点/边属性过滤 + 强制 WHERE**？ | 方案选型（含迁移代价） |
| Q4 | 抽取（parse/extract）是内部能力还是必须有 API 契约？若必须，契约边界在哪？ | 契约范围 |
| Q5 | 图谱解析"成功但 0 三元组"应判定为：成功（部分）/ 失败 / 需人工复核？ | 状态机语义 |
| Q6 | 列表里的"节点数/关系数"应展示：图实例计数 / 去重实体数 / 不展示？ | 展示口径 |
| Q7 | `/api/**` 对外面是否下线？若不对外，是否有保留价值？ | 产品边界 |
| Q8 | 图数据 provenance（脚本 vs App）是否需要进入合同（如 `generation` 之外的 `source`）？ | 是否立契约 |
| Q9 | 问答"半句已提交 + 后置错误"的处理策略：缓冲到最后再吐 / 显式标记部分结果？ | 交互语义 |
| Q10 | 是否接受"门禁脚本"作为契约缺口的长期兜底，还是必须转成契约生成物？ | 治理口径 |

---

## 7. 附录

### 7.1 复现命令（关键几条）

```bash
# 图谱解析一次
POST /index/knowledgeBase/file/graphParse  {"fileIds":["332"],"knowledgeBaseId":9,"knowledgeBaseName":"R12验收主链"}

# 状态核对
select id,graph_parse_status from knowledge_base_list where id=332;   -- 3=成功 4=失败

# 接口注册表对账
platform/r12/bin/check-endpoints-sync.py            # 退出码 1 = 有缺失
platform/r12/bin/check-endpoints-sync.py --fix --resource-id 8

# 契约
contracts/api/llmke-graph.openapi.yaml              # 只有 query / health
contracts/schema/llmke-core.json                    # GraphQueryRequest/Response/Evidence/Health
contracts/ontology/                                 # 空
```

### 7.2 术语

| 术语 | 含义 |
|---|---|
| primitiveName | 知识库物理标识（如 `kb_9`），用于 ES 索引 `kb_9`、Nebula 空间 `g_kb_9` |
| generation | 代次（V0/V1…），契约要求所有图请求/证据携带 |
| graph_parse_status | 文件级图谱解析状态：1=正常(未做) 2=解析中 3=成功 4=失败 |
| BUCKET | 权限缓存分桶键（=URL 首段）与 `app_name_abbreviate` 不一致导致的 401 |
| 孤儿任务 | 所属文件已删除、仍停留在 PENDING/DEAL_ING/RETRY_ING 的解析任务 |

### 7.3 本文档未包含（避免误导评审）

```
· 未做全量安全渗透；security 16/16 为既定用例集
· 未做压力/容量测试；性能数据仅为观测值，非基线
· 多租户/多平台隔离未验证
· 灾难恢复（Nebula/ES/Milvus 单点）未验证
```
