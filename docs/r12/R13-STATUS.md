# R13 状态与能力矩阵（真实核对版）

更新时间：2026-10-26（末次回归 20261026T083716Z / SEC-20261026T084621Z）
分支：`feature/R12-real-rag`
证据目录：`platform/r12/qa/evidence/`

## 1. 本轮实测通过

| 套件 | 结果 | 证据 |
|---|---|---|
| 主链 S1–S8（登录/建库/上传/解析/问答/引用/原文/负例） | **31/31 PASS** | `20261026T083716Z` |
| 安全负例与授权（16 条） | **16/16 PASS** | `SEC-20261026T084621Z` |

主链覆盖：中文 DOCX / XLSX / PPTX / 数字 PDF / 扫描 PDF(OCR) / 纯文本 / 含表格；
加密 PDF 按预期解析失败；坏文件、伪造 token、越权删除均被拒。

## 2. 本轮关闭的缺陷（全部有实测证据）

### 2.1 安全

| 编号 | 缺陷 | 处置 | 证据 |
|---|---|---|---|
| SEC-A1 | 只有登录校验，按 id 可直读/直删他人知识库与文件 | `KbAuthzService` 对象级授权（`0/1/2/3` 复用 `user/dept/group_privilege`），覆盖 KB 详情/更新/删除/重解析/下载、文件详情/删除/解析、`/stream` 对象键、问答入口；Feign 传递主体；无主体 fail-closed | SEC-1..9,12,16 |
| SEC-A2 | 原文可匿名取走（MinIO 匿名 GetObject + `/minio` 反代） | 撤销桶匿名策略（直连与反代均 403）；`/stream` 按对象键反查知识库鉴权 | SEC-3,15 |
| SEC-A2b | 预览服务 `/preview/` 对浏览器直开放 | nginx `/preview/` → 403；改走 `/index/knowledgeBase/file/previewStream`（先鉴权再转 PDF） | SEC-11..14 |
| SEC-A3 | 口令仅 MD5 存储 | BCrypt 哈希；历史 MD5 登录成功后透明升级；移除全部 MD5 写入路径 | SEC-10 + 库内 `$2a$/$2b$` |
| SEC-A4 | 权限不足被映射成 500 | 统一 403 | SEC-1..7 |

### 2.2 运行

| 编号 | 缺陷 | 处置 |
|---|---|---|
| RUN-01 | 启动期自调用失败直接击杀进程（"进程莫名消失"的真因） | `InitInterface` 重试 + 降级，服务继续启动 |
| RUN-02 | 依赖终端存活 | systemd `--user` 单元：`r12-models` / `r12-alg` / `r12-docparse` / `r12-java@<svc>`，`enable-linger` 已开 |
| RUN-03 | 启停不完整 | `platform/r12/bin/up.sh {up|down|status|verify}` 覆盖 基础设施(含 Nebula)→模型→算法→解析→图谱→业务→预览→前端 |

### 2.3 问答链（本轮定位到的真实故障链）

| 编号 | 缺陷 | 现象 |
|---|---|---|
| QA-07 | `/index/modelInfo/getSimpByModeName` 在服务间异步线程无主体，`allPage` 抛 `Cannot parse null string` | `model_info=null` |
| QA-08 | 上述失败被写回 `config_json` 并持久化，后续会话永久缺 `model_info` | 推理服务 422 |
| QA-09 | 简化文档模式只下发 `page_content/order_num`，`attribute.split_documents` 取 `item["metadata"]` 抛 `KeyError` | SSE 流中断，前端只显示"模型暂时无法返回" |
| S6-01 | 非 pdf 文件标题被改写成 `.pdf` 去匹配 ES `title`（实际存原始名） | 引用→原文取回 0 chunk |
| FAQ-04/06/07 | chunk 标题同样被改写；`alg_llm_config_py` 缺 `milvus_config/es_config`；`llm_service` 读启动期配置缓存 | FAQ 抽取"成功但 0 产出" |
| VER-10..15 | 版本号未贯通解析链路；`ParsedTextMetadata` 无 `version` 字段导致 pydantic 抛错整批解析失败；`document_version` 只看 `revise_date` 且缺 metadata/file_id 时 KeyError、`int(None)`、排序 NPE | V0/V1 同时进上下文、回答前后矛盾；解析队列积压 |
| QA-10 | 上游 LLM 断开但无终止帧，Flux 等不到 onComplete | SSE 常驻，客户端/脚本 Read timeout（验收偶发 19/20） |
| RUN-05 | 进程重启残留 status=2/3 任务，调度器按 DB 计数限流 | 队列永久卡死，上传后一直排队 |

## 3. 能力矩阵（真实状态）

| 能力 | 状态 | 说明 |
|---|---|---|
| 普通 RAG（召回+rerank+引用+原文核对） | ✅ 实测 | 31/31；答案要点可在被引用原文逐字找到 |
| 对象级授权（读/写/删/管理+撤权） | ✅ 实测 | 16/16 负例；撤权后立即失效 |
| 原文访问收口（下载/预览/存储直连） | ✅ 实测 | 匿名、越权、无法归属的对象键全部拒绝 |
| 口令 BCrypt + 迁移 | ✅ 实测 | 库内已无 MD5 |
| Office 预览 DOCX/PPTX/XLSX | ✅ 实测 | 容器 `r12-preview:18095`，LibreOffice 25.2.3.2，中文与表格正确 |
| FAQ 抽取/入库/召回 | ✅ 实测 | 20 条 `status=1`；`faq_result_list` 命中 0.9997；问答链需助手配置 `enabled_faq=true` 才启用 |
| FAQ 直接以答案作答（resultType=2） | ⚠️ 未确认 | 开启后回答与 FAQ 语义一致，但响应 `resultType` 仍为 1（走文档）|
| VLM 多模态解析 | ✅ 实测 | `use_multi_modal=true`，双图 DOCX 产出图像描述 chunk |
| 多版本：当前有效版本 | ✅ 实测 | kb_9 同时存在 V0(5000万)/V1(8000万)，检索只返回 V1；问答答"8000万元"，不再自相矛盾 |
| 多版本：历史列表 | ✅ 实测 | `GET /index/knowledgeBase/file/multiple/version?kbNames=kb_9` 返回父子版本组（V0/V1） |
| 版本标识（引用） | ✅ 实测 | 引用 metadata 带 `parent_file_name/version` |
| GraphRAG local（实体链接+邻域/PPR+原文回填） | ⚠️ 部分 | 图服务 19529 + Nebula 3.8 已起，schema/写入链路可用；召回质量受抽取覆盖度限制 |
| GraphRAG global（社区摘要 + map-reduce） | ✅ 已接入（引用待补） | 助手配置 `query_mode=global` 时，`/qa/ai/question` 改走 `19995/retrieval_documents_global`，实测 5.9s 返回基于社区摘要的回答；社区摘要已带 `file_id` 可回溯来源文件；**逐句引用仍为空**（社区摘要无分句 offset 语义） |

| FAQ 前端管理界面 | ❌ 未做 | 仅后端与召回 |
| 表格问答（数值+引用） | ✅ 实测 | 台账数字问答："华东精密制造授信额度"→3000万元；"五级分类为正常的客户"→枚举 3 家，与原文一致 |

## 4. 交付入口

| 项 | 值 |
|---|---|
| 前端（生产） | http://127.0.0.1:18088/ |
| 网关 | http://127.0.0.1:8088 |
| Office 预览 | 内部 http://127.0.0.1:18095（仅经鉴权端点访问） |
| 图服务 | http://127.0.0.1:18084（Java）/ 19529（Python 图索引） |
| Nebula | graphd 19669 |
| 账号 | `admin`（口令单独交付）；测试夹具 `r13_reader` / `r13_noauth` |

## 5. 明确未完成（不静默缩范围）

1. GraphRAG global 已接入 `/qa`（配置驱动），但前端尚无"全局/局部"切换控件；global 的逐句引用为空（只有回答与社区摘要）。
2. 多版本历史查询、FAQ 前端管理、表格数值问答未端到端。
3. 离线制品仍为 `r12-bundle-202610250617.tar.gz`（914M），**未包含**本轮 jar/dist/preview/systemd/Nebula 变更；干净环境离线安装未验证。
4. 图抽取覆盖度低（社区数少），跨文档 global 问题的答案质量不足以作为效果验收。
5. 生产验证（容量/安全复核/备份恢复/升级回滚/发布）属 R14，未关闭。
