# R14 C（业务/解析/检索）证据索引

采集窗口：2026-10-27 10:19 – 11:37（Asia/Shanghai）
仓库：`/home/szf/data/dev/llmke-r12`（未 commit）
所有权：`services/rag-java/**`、`services/rag-alg/alg_doc_parse_service/**`；本目录只写证据，不改 `platform/r12/qa/**` 脚本

## 1. 结论速览

| 项 | 结果 | 证据文件 |
|---|---|---|
| C12 多版本（a~e 五项断言） | **6/6 PASS** | `60_verify_ae.json` |
| 归组不串文档（F04 / id=300） | **10/10 PASS** | `50_group_regression.json`、`52_group_300_before_after.json` |
| 归组守卫反例（内容相同不同名） | 未被并组；**守卫拒绝分支未被触发** | `55_guard_proof.json` |
| S5→S6→S7（acceptance 原函数） | **8/9 PASS**（唯一 FAIL 是不存在的会话 `r12-sess-1`，脚本口径） | `results_s6s7.json`、`s5_answer.json`、`s6_chunks.json`、`s7_history.json` |
| C11 表格四类题 | 单值/筛选/换算/无答案 PASS；**聚合两次算错（真缺陷）** | `80_table_cases.json`、`81_table_cases2.json` |
| 「默认现行版本」作用域 | **MAJOR：只在召回候选集内生效**，V0 单独命中时会答旧值 | `62_version_scope_finding.json` |
| 双桶名写库缺陷 | 新行已单桶名（实测） | `80_upload_R12FIX-credit-ledger_OVERWRITE.json` |
| 对象键归一化（`/minio` 等六种写法） | 离线自检 **6/6 正确**（运行态待重启验证） | `72_object_key_normalize_offline.json` |
| presign 端点 | 直连索引 200 + 可用预签名 URL；经网关需注册 interface_info | `71_presign_direct_vs_gateway.json` |
| 不传 configId | admin 也 500（真缺陷，待 TL 裁语义后改） | `90_probe_configid.json` |

## 2. 复跑命令

```bash
cd /home/szf/data/dev/llmke-r12
# C12 五项断言（V0=290 V1=328 组=614524213）
python3 -u /tmp/r14_c/verify_ae.py platform/r12/qa/evidence/R14-VERSION-T0-20261027T021959Z 614524213 290 328
# 归组回归（会新建一个 R14C-归组回归<tag> 库）
RUN_TAG=<tag> python3 -u /tmp/r14_c/group_regression.py platform/r12/qa/evidence/R14-VERSION-T0-20261027T021959Z
# S5→S6→S7（复用 acceptance.py 的原函数，不复制断言）
python3 -u /tmp/r14_c/run_s6s7.py platform/r12/qa/evidence/R14-VERSION-T0-20261027T021959Z kb_9
# 表格四类题
python3 -u /tmp/r14_c/table_cases.py platform/r12/qa/evidence/R14-VERSION-T0-20261027T021959Z
# presign（直连 / 网关）
python3 -u /tmp/r14_c/presign_test.py <证据目录> http://127.0.0.1:18082/index
python3 -u /tmp/r14_c/presign_test.py <证据目录> http://127.0.0.1:8088/index
```
> 脚本都在 `/tmp/r14_c/`（不落在仓内，避免与 qa 脚本所有权冲突）。若要长期留存，请 TL 决定是否移入 `platform/r12/qa/` 由 F 接管。

## 3. kb_9 当前语料（2026-10-27 11:27 实测，可见行 11 条 / ES 8 chunk）

| file_id | 文件 | 版本 | 状态 | group | 说明 |
|---|---|---|---|---|---|
| 290 | R12FIX-product-loan.docx | V0 | 3 | 614524213 | 正文 5000万元（历史） |
| 328 | R12FIX-product-loan(1).docx | V1 | 3 | 614524213 | 正文 8000万元（现行） |
| 329 | R12FIX-credit-ledger.xlsx | V0 | 3 | 1577230197 | 台账，`table_file_paths` 单桶名 |
| 330 | R12FIX-product-intro.pptx | V0 | 3 | 1939665135 | 正文 5000万元（历史） |
| 343 | R12FIX-product-intro(1).pptx | V1 | 3 | 1939665135 | 正文 8000万元（现行） |
| 331/332/333/334 | pdf-digital / docx-plain / docx-table / pdf-scanned | V0 | 3 | 各自 | 补充语料 |
| 320 | pdf-encrypted.pdf | V0 | **4** | 1593893933 | 加密 PDF，预期解析失败（负例） |

状态口径（`KbFileStatusEnums`）：`1 正常 / 2 解析中 / 3 解析成功 / 4 解析失败 / 5 重新向量化 / 98 重试中 / 99 排队中 / 0 已删除`。
**判定规则：`getFileStatusById` 与 MySQL `knowledge_base_list.status` 双读一致才算定论**；空列表/空正文/5xx/超时一律不算通过。

## 4. 本轮代码改动（均在 C 所有权内，未 commit）

| 编号 | 位置 | 内容 | 激活状态 |
|---|---|---|---|
| R14-C-FIX-01 | `FileAppServiceImpl.doFileMultiversion` + `versionKeyOf` | 跨文档归组写入前拦截 | 已激活（index 10:39 jar） |
| R14-C-FIX-02 | `AiServiceImpl.toAbsoluteSource/toObjectKey/trimTrailingSlash` | source 双 host 归一化 | 已激活（qa 10:29 jar） |
| R14-C-FIX-03 | `KnowledgeBaseFileController.presign` + `normalizeObjectKey` | 预签名取原文（300s） | 代码已激活；网关注册由 TL 手工补 |
| R14-C-FIX-03b | 同上 `contentTypeOfKey` | 预签名带 `response-content-type` | **待重启 index**（`/tmp/r14_c/new-index.jar` md5 `43fa56a1…`） |
| R14-C-FIX-04 | `KnowledgeBaseListAppServiceImpl.uploadParsedFile` + `stripBucketPrefix` | 修桶名拼两次 | 已激活（index 10:39 jar） |
| R14-C-FIX-05 | `RetrievedData.getGlobalAnswer` + `combineRetrieveDataList` + 主链短路 | global 的 reduce 答案直接采用 | **待激活**（`/tmp/r14_c/new-qa.jar` md5 `f509615c…`） |
| R14-C-FIX-06 | `GlobalHandler.applicationExceptionHandle` | SSE 端点拒绝态写 JSON（403+30016） | 同上 |
| R14-C-FIX-07 | `FileStorageUtils.getObjectNameFromUrl` | `/minio` 前缀 + 双桶名归一化（一处覆盖 stream/previewStream/markdown/pdf） | **待重启 index**（同上 new-index.jar） |

## 5. 待决事项（不属我可单方决定）

1. **TL**：不传 configId 的语义（回落系统默认助手 / 必须显式选助手）；另 `search_config` 有**两行** `is_default=1`（id=1、id=10），无论哪种方案都要清。
2. **TL**：`alg_retrieval_service/app/multiple_retrieval.py`（`except→return` 丢结果）与 `retrieval_fun_tool.py`（metadata 白名单丢审计字段）**不在 CHECKPOINT 给我的所有权内**，请划归属（A 提的改法已转述）。
3. **TL**：`alg_doc_parse_service` 的 7 处随机 pk 改确定性派生（A 报，我选方案 A=`chunk_index`）需要 docparse 重启窗口。
4. **E**：新端点必须在 `interface_info` + `resource_interface` 注册（presign 已由 TL 手工补；后续新端点请纳入 init-db）。
5. **产品级**：C11 多行聚合不可依赖 LLM 心算（两次算错），需 Text2SQL/计算工具；`gienrag.tools_table` 仍 0 行。
6. **产品级**：版本"默认现行"应做成索引级/查询级约束，而不是召回后去重（`62_version_scope_finding.json`）。
