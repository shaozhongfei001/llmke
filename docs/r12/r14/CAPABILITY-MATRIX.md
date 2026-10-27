# R14 能力矩阵（C01–C20）

> 更新：2026-10-27（R14 Loop 0 起点）
> 口径：状态只认**运行态证据**；`✅` 必须有可复跑命令 + 证据目录；`⚠️` 表示有实现但证据不达标（R13 的假绿项都落这里）；`❌` 无实现；`?` 未核实。
> 所有者：A=数据代次 B=图谱 C=业务解析检索 D=前端 E=交付运行 F=QA安全

| ID | 能力 | 状态 | 真实入口 / 实现位置 | R14 待办（阻断项加粗） | 证据 | 所有者 |
|---|---|---|---|---|---|---|
| C01 | 用户/角色/部门组/资源/API Key/撤权 | ✅ | `/index/user/*`、`KbAuthzService` | 撤权后旧 session/缓存已验；**API Key 能力未核** | REVOKE-20261026T163545Z | F |
| C02 | KB/目录/文件/标签/模型与检索配置 | ✅ | `/index/knowledgeBase/*`、`/index/searchConfig/*` | 重启后持久化已验；标签/目录能力未逐项点验 | 主链 31/31 | C/D |
| C03 | PDF/DOCX/XLSX/PPTX/文本/图片OCR/VLM | ⚠️ | `alg_doc_parse_service` | 主链覆盖 7 类；**OCR 与 VLM 仅单样本**；.doc 未验 | 20261026T163339Z | C |
| C04 | 标题/表格/图片/原文定位与预览 | ⚠️ | `preview`、`getFileChunks` | 预览通；**原文定位只有 chunk 级，无 Unicode 区间/页码坐标** | S6 | A/C |
| C05 | profiler 与 5 种分块策略 | ? | 解析服务 | **未核实是否存在 profiler 与策略切换** | — | C |
| C06 | 异步解析/抽取/索引 + 四类存储适配 | ⚠️ | worker + ES/Milvus/Nebula/MySQL | 异步通；**四类存储"删/改"一致性未验**；事件幂等未验 | — | A |
| C07 | 真实 Embedding、多路召回 | ✅ | `alg_retrieval_service` | 向量+全文+图+FAQ 多路已通 | CAPS | C |
| C08 | 融合/RRF/Rerank/邻块补全/降级 | ⚠️ | 检索服务 | rerank 单路已通；**融合策略与单路失败降级未验** | — | C |
| C09 | LLM/SSE/多轮/取消/历史/反馈 | ⚠️ | `rag-qa-service` | SSE 通；**取消、重登录恢复、反馈未验**；S7 曾空历史假通过 | 主链 S5/S7 | C |
| C10 | FAQ 抽取/管理/编辑/启停/导入/直答 | ⚠️ | `llm_faq_generate` + 前端 FAQ 页 | 抽取/直答已验；**编辑/启停/导入/去重从页面点验未做** | CAPS-FAQ | C/D |
| C11 | 表格数值/结构化/受控 Text2SQL | ⚠️ | `tools-database` | 单题表格问答通；**多行聚合/单位/无答案/只读账号/行数限制未验** | CAPS-TABLE | C |
| C12 | 生效版本/历史列表/历史检索/差异问答 | ❌ | — | **当前 kb_9 无真实 V0/V1（两条都 V0），收紧断言后 FAIL** | CAPS-20261026T182423Z | C |
| C13 | 实体/关系抽取 + M1 归一化 | ⚠️ | `index_graph_service` | 抽取通；**误合并（授信额度→5000万元）、无审计/回滚** | LOCAL-RETRIEVAL.md | B |
| C14 | 图谱展示/查询/实体链接/邻域/PPR | ⚠️ | `query_graph_data` | 内部口通；**经用户入口 + 真实多跳未验** | CAPS-GRAPH_LOCAL | B |
| C15 | 权限域内社区/分级报告/摘要/global | ⚠️ | `graph_summary` + `/retrieval_documents_global` | 通路通；**权限域未验证、只有拒答题、source 重复 host、摘要重复计数** | CAPS-GLOBAL | B/A |
| C16 | 内容安全/无依据拒答/资料内指令隔离 | ⚠️ | sensitive-words + prompt | 敏感词有；**提示注入隔离（文档内指令）未验** | — | F |
| C17 | 完整管理与问答前端 | ⚠️ | `frontend/plateform/dist` | 页面存在；**未从浏览器逐项点验 12 条旅程** | — | D |
| C18 | 更新/删除/重解析/重建/切换/回滚 | ❌ | — | **无代次切换指针；重解析需人工 graph-refresh；删除联动未验** | — | A |
| C19 | 效果评测/监控/审计/诊断 | ❌ | partial | **无 100 题效果集；无监控面板/审计** | — | F |
| C20 | 完整源码/离线安装/恢复升级/发布 | ⚠️ | `offline-kit.sh` | 包可安装但**未在干净环境实装**；无 Java/前端源码构建材料；无备份恢复演练 | offline-verify | E |

## R14 已确认的阻断项（来自评审 F01–F09）

| 编号 | 结论 | 现状 | 归属 |
|---|---|---|---|
| F01 | 断言假绿（VERSION 空列表/历史空/表格只匹配数字/GLOBAL 拒答） | 已收紧 4 处；VERSION 现真实 FAIL（缺夹具） | F/C |
| F02 | "仅两个对外端口"不成立 | 实测 40+ 监听，含 MySQL/ES/MinIO/Nacos/Redis/Nebula | E |
| F03 | GraphRAG 仅通路探测 | source 重复 host；global 只有拒答题 | B |
| F04 | 文件名回落不等于稳定引用 | 无代次契约，靠名字兜底 | A |
| F05 | 社区权限域未验证 | 仅验"整库撤权" | F |
| F06 | 包不含完整源码与离线构建材料 | 只含算法源码 + 前端 dist | E |
| F07 | 安装顺序/健康脚本掩盖失败 | init-db 顺序倒置；verify 不退出非零 | E |
| F08 | 安全断言可被 5xx 骗过 | 已收紧 denied()，自检通过 | F |
| F09 | 完整产品范围未证 | C05/C12/C18/C19 基本空白 | 全员 |
| F10 | **多版本误合并（新发现，实测）** | `id=300 R12FIX-credit-ledger.xlsx` 的 `parent_file_name` 串成 `R12FIX-product-loan.docx`、`group_id=614524213` 与 loan 同组 → 不同文件被并进同一版本组，检索去重会挤掉台账 | C（Java 归组） |
| F11 | **`--only` 假绿（新发现）** | `acceptance.py --only S6,S7` 实际 0 用例、exit 0；选中但未执行被当成通过 | F |
| F12 | **验收污染生产语料（新发现）** | acceptance 按库名复用 kb_9，S3 整批 OVERWRITE：一次运行把 V1(8000万) 打回 V0(5000万)，且 ES 按 source 先删后插 → 版本内容被静默替换 | F |
| F13 | **部署不可复现（事故实证）** | IK 插件装在容器可写层，recreate 即丢 → cluster red；`r12-alg` `Restart=no` → 停摆 7 小时无人拉起 | E |

## 度量口径（R14 沿用并加严）

1. 空列表、`data:None`、拒答、只匹配一个数字 → 一律 FAIL。
2. 拒绝态只认 401/403 或 30016/30017/30018；5xx 与超时判**验收失败**。
3. 每项能力必须有"用户入口"（网关/页面）证据，内部端口直连只能算通路探测。
4. 证据带采样时刻；同一结论重复跑两次一致才算稳定。

## R14 进展更新（2026-10-27 11:30）

### 状态变化
| ID | 之前 | 现在 | 依据 |
|---|---|---|---|
| C12 多版本 | ❌ | **✅** | 夹具 V0=5000万/V1=8000万，a~e 6/6 PASS；默认只答 8000万、历史引用各自定位原文（`R14-VERSION-T0-...`） |
| C15 global | ⚠️ 通路 | **⚠️ 链路已通、效果待验** | C 的 `global_answer` 消费生效，`/qa` 2.4s 返回带 `[L0-xxx]` 的社区答案；但数值与 B 的 ground truth 不符（30/20/20 vs 30/60/60），且每结论未回链到 chunk |
| C04 原文定位 | ⚠️ | ⚠️ | presign 已通（200/403），但定位仍 chunk 级，无 Unicode 区间/页码坐标 |
| C06/C18 幂等 | ⚠️ | **⚠️ 半通过** | 索引层幂等 PASS（不翻倍、ES `_id`=Milvus `pk`）；端到端"代次稳定"FAIL——解析侧 7 处 `create_uuid()`（C） |
| C11 表格 | ⚠️ | ❌ 退化 | `tools_table` 0 行、xlsx 无 chunk（10:22 并发重传打掉），Text2SQL 无资产 |
| C17 前端 | ⚠️ | ⚠️ | 旅程 3/4/11 页面通过；旅程 5(FAQ 启停假成功)/9(global 开关)/3(引用打开) 已定位并修，待构建验证；旅程 4 取消不具备（库不支持） |

### 新增缺陷（R14 实测）
| 编号 | 缺陷 | 影响 | 归属 |
|---|---|---|---|
| F14 | 运行中 jar 被原地覆盖 → `NoClassDefFoundError`（随机） | 服务随机 500，肉眼像"产品缺陷" | 纪律（已入检查点） |
| F15 | watchdog 自伤两例：`exit 1` 致 timer 被停摆 11 分钟；自愈拉起的进程落在 watchdog cgroup 被连带 SIGKILL | 停摆 + 杀死刚救活的服务 | E（已修，实测 8s 恢复） |
| F16 | conf 用 `${R12_*}` 占位符但 unit 无 `EnvironmentFile`、且 `.env` 变量名不一致 | **5 个 Java 服务全挂** | E（已临时修，需固化） |
| F17 | 多 KB 图检索：一个库 `space_not_found` → `except: return` 丢掉后续所有库 | 图像结果静默丢失，验收会误判"图无效" | B(已修 788)/C(continue) |
| F18 | 检索层 metadata 白名单重建，丢弃审计字段（`provenance_quality/identity_stability/id_origin/recovered_*`）+ title | B/A 做的可审计性到不了 Java/前端 | C |
| F19 | 检索不可用时静默降级：直接把空上下文丢给 LLM 生成 | 用户得到"看起来正常"的无依据答案（比报错更危险） | C |

### 度量口径更新（R14 v2）
1. **5xx / 超时 / 断流 = 验收失败**；图的"业务空"必须是 `200 + data.reason`，不得用 500 表达。
2. 合法空结果可 PASS 该次调用，但**该题不计入正例统计**。
3. global 正例判据：`data.global_answer` 与 `reply.content` 逐字一致，且每条关键结论可回链到 chunk。
4. 拒绝态只认 401/403/30016（SSE 端点也必须给可读 JSON）。
