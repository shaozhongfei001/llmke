# C1：HippoRAG 版本固定 + 真实最小运行（2026-10-31）

> 结论：**HippoRAG 2.0.0a4 已在独立环境装成，并用本机真实 LLM/embedding 端点跑通
> `index()` + `retrieve()`**；引擎 chunk 键规则已实测确认，同文异源的来源保留由平台映射表保证。
> 仍**未**完成：跨文档大规模图、社区/global 消费、断网 wheelhouse、Nebula 落地。

## 1. 版本与制品

| 项 | 值 |
|---|---|
| 包 | `hipporag==2.0.0a4`（PyPI 镜像可取，GitHub 直连不可达：`git ls-remote` 无输出/超时） |
| wheel | `hipporag-2.0.0a4-py3-none-any.whl` |
| wheel sha256 | `eee80804299cd37b485c7d09caa0b03a1e00609aaf884759e4ba3cdbd4a99a7a` |
| 解释器 | `/home/szf/data/dev/hipporag-toolenv`（CPython 3.11.15） |
| 依赖锁 | `docs/design/unified-documents-v2/locks/hipporag-2.0.0a4-requirements.txt`（184 行，`pip freeze`） |
| GPU | `torch.cuda.is_available() == True`（torch 2.5.1+cu124） |

## 2. 安装期真实坑（会阻断"装完就能用"的假设）

1. **硬导入 vllm**：`hipporag/llm/vllm_offline.py` 在模块级 `from vllm import SamplingParams, LLM`，
   而 `hipporag.llm.__init__` 会加载它 → **不装 vllm 连 `import hipporag` 都失败**，
   哪怕实际用 OpenAI 兼容后端。已装 `vllm==0.6.6.post1`。
2. **vllm 把 transformers 拉到 5.22.1**，与声明的 `transformers==4.45.2` 冲突；需回装锁定版本。
3. **pyarrow 26 要求 numpy≥2**，而 vllm 装完后 numpy 被降到 1.26.4 → `to_parquet` 直接 ImportError。
   最终可用组合：`numpy 2.1.3 / pandas 2.2.3 / pyarrow 26.0.0 / transformers 4.45.2 / torch 2.5.1+cu124`。
4. 引擎 embedding 类按名字路由：名字含 `text-embedding` 才走 `OpenAIEmbeddingModel`。
   本机端点是 bge-m3，实测**服务端忽略 model 字段**，因此用 `text-embedding-bge-m3` 即可；
   若换成严格校验 model 名的端点，需要适配层改名或加代理。

这些都要进离线交付清单，否则目标机"网络通但装不上/装完 import 失败"。

## 3. 真实运行结果（脚本 `scripts/v2_hipporag_smoke.py`）

数据：4 个输入单元，其中"产品甲最高额度…"一句**同时来自文件 333 与 334**。

```json
{"status":"OK",
 "engine":{"version":"hipporag==2.0.0a4",
           "llm_base_url":"http://127.0.0.1:18092/v1",
           "embedding_base_url":"http://127.0.0.1:18090/v1",
           "chunk_ids":["chunk-89d6b39e9bc4ba93f7a35cceb50dd674",
                        "chunk-967af49b40ddc5f2e8a0c8d13fa05cae",
                        "chunk-f9919d83c6ff99a3253b2ce449696261"],
           "chunk_id_rule":"chunk-<md5(text)>"},
 "mapping":{"units":4,"engine_chunks":3,"shared_chunks":1,"max_sources_per_chunk":2},
 "hits":[{"native_key":"chunk-89d6b39e9bc4ba93f7a35cceb50dd674",
          "sources":[{"file_id":"333","source":"r12-rag/kb_9/甲-产品定价.docx"},
                     {"file_id":"334","source":"r12-rag/kb_9/乙-客户申请.docx"}]},
         {"native_key":"chunk-967af49b40ddc5f2e8a0c8d13fa05cae",
          "sources":[{"file_id":"333","source":"r12-rag/kb_9/甲-产品定价.docx"}]}]}
```

关键事实：

- **chunk 键 = `chunk-<md5(正文)>`**：用 `hp.chunk_embedding_store.get_all_id_to_rows()` 与
  `md5(text)` 逐条对齐确认（不是 sha256，也不是自增 id）；
- 同文异源 → 引擎只有 1 个 chunk（4→3），但检索命中能回指**两个文件**；
- 检索 query"客户A申请产品甲的额度是多少"命中该句与其同文档句，顺序正确。

## 4. 平台侧契约（`graph_engine_adapter/mapping.py`）

- `input_unit_id = sha256(parse_artifact_id + ':' + seq)`：换引擎不变、换快照必须变；
- `native_key = "chunk-" + md5(text)`：只作缓存/对齐键，**允许 1:N**；
- `SourceMap` 负责 `native_key -> [InputUnit]`，`sources_for()` 去重但保留多来源；
- `from_json()` 校验 `input_unit_id` 自洽 + `native_key` 形态，拒绝被篡改的映射表；
- 表里没有"边/相似度"，避免把引擎的算法结构当成业务断言。

单测 `tests/test_graph_engine_mapping.py` 6 项：同文两源、id 稳定性、重复登记幂等、
正文变更拒绝、JSON 往返、投影 chunk→单元（表格带 `table_id`，不冒充正文来源）。

## 5. 仍未完成（不许标"图已接入"）

1. **只有 3 条短句的最小样本**，未做 333/329 全量或跨文档路径；`retrieve` 的
   `RuntimeWarning: invalid value encountered in divide`（`phrase_weights /= number_of_occurs`）
   出现在 3 文档规模，需在大样本上确认是否会退化成 NaN 权重；
2. 引擎图是 igraph/内存 + `save_dir` 持久化，**未接入 Nebula**，也未验证与平台
   `graph_base` 现有三元组的关系（不得双写两套事实）；
3. 社区/global 仍未消费任何真实产物；
4. 断网安装：目前是联网 pip 装成，尚无 wheelhouse；184 个包 + torch/vllm 体积需单独打包验证。

## 6. 扩量到真实投影块（同一轮补）

`scripts/v2_hipporag_crossdoc.py`：输入改用 `ingest_pipeline` 的真实 payload（999011 的 63 块 + 333 的 3 块 = 66 块），
跨文件查询并回指来源。

```
{"status":"OK","save_dir":"/tmp/hippo-cross-015610",
 "entities":197,"facts":253,
 "input":{"chunks":66,"unique_texts":66,"engine_chunks":66,"merged":0},
 "mapping":{"units":66,"engine_chunks":66,"shared_chunks":0,"max_sources_per_chunk":1},
 "queries":[{"query":"实体类型体系里对别名的处理规则是什么","hits":3,"resolved":3,"unmapped":[],"files":["999011"]},
            {"query":"产品的最高额度和利率基准","hits":3,"resolved":3,"unmapped":[],"files":["999011"]},
            {"query":"额度分项与总额度的关系","hits":3,"resolved":3,"unmapped":[],"files":["333","999011"]}]}
```

**发现并修掉一个真陷阱**：引擎是持久化存储，沿用旧 `save_dir` 会把历史 chunk 一起检索出来。
第一次跑 66 块却得到 68 个 chunk、且 2 条命中无法回指——不是引擎错，是数据混了。
现在默认每次新建目录，并把命中里"不在当前映射表"的键显式记进 `unmapped`，不静默丢弃。

**仍未解决**：`phrase_weights /= number_of_occurs` 的除零警告在 3 块时出现、66 块两轮未见，
但未在更大规模复现/排除；跨文档查询在 66 块规模下"相关性排序"仍偏弱（query2 只回到单文件），
属检索质量问题，不作通过结论。

## 7. 小样本上的诚实结论

5 块时三个查询都返回两个文件的命中——**这是图太小、候选几乎全覆盖**，不能当作"跨文档检索准确"。
真正的判别力要在 333/329/999011 全量 + 多主题语料上测，目前只到"链路通、来源可回指"。

## 8. 社区与 global 的真实消费（平台侧，非 HippoRAG）

平台已有的社区能力在真实图上可用，本轮验证的是**消费者**而不是重造：

```
# 经检索服务（19995）走 global
POST /retrieval_documents_global {"knowledge_base_name":["kb_9"],"query":"产品额度与利率的关系","query_mode":"global"}
-> code=200 msg="社区摘要 1 条"
   top=「这个社区围绕"智造贷"这一主题聚集…」 source=…/V1/R12FIX-product-intro(1).pptx  chunk_refs=3

# local 模式
-> code=200 msg="社区摘要 2 条" docs=2

# 无社区的知识库（kb_10）负例
-> code=200 msg="社区摘要 0 条" global_answer="" documents_list=[]   # 不编造
```

社区文档字段齐全：`community_id / level / generations=['V1'] / file_ids / chunk_refs /
sources_resolved_by=file_id`，即引用可回指、代次可回答。

**一次自我纠错**：我先用 ES 的 `term`/`prefix` 查 `metadata.source` 得到 0 条，差点判成"引用指向不存在的源"；
实际是 `metadata.source` 在 ES 里是分词语义字段，term/prefix 不适用。改查 Milvus（`source like ...`）得到 **2 行**，
与 ES 总量 270=270 一致。**以 Milvus 查询为准，未发现索引不一致**；这条也说明"引用失效"的判据不能只看一次 ES 查询。

**仍未验证**：真正的"引用失效"反例（删掉被引文件后 global 是否标记失效）——需要动 kb_9 的既有数据，
本轮不做破坏性实验，留作独立反例任务。

## 9. 离线 wheelhouse 体积基线（U-03 断网交付的前置数字）

实测已装环境与关键包体积（`du -sh`）：

| 项 | 体积 |
|---|---|
| `hipporag-toolenv` 总体 | **7.4 GB** |
| `nvidia/*`（CUDA 运行时） | 2.7 GB |
| `torch` | 1.7 GB |
| `vllm` | 531 MB |
| `transformers` | 98 MB |
| `hipporag` wheel 本体 | 85 KB（sha256 `eee80804…`） |

即"断网可装"至少要准备 4–5 GB 级别的 wheelhouse；纯 Python 依赖（hipporag/networkx/tiktoken）
只有 ~2.8 MB，体积全在 torch/vllm/nvidia。

已启动的后台作业（本轮发起，跨回合续跑）：
```
pip download -d /tmp/wh-full -r locks/hipporag-2.0.0a4-requirements.txt
log: /tmp/wh-full.log   pid 见启动记录
```
进展核对方式：`du -sh /tmp/wh-full`、`tail /tmp/wh-full.log`；完成后应得到可断网安装的 wheelhouse。

**已知取舍**（下一步要决策，不是能靠下载解决的）：`hipporag 2.0.0a4` 在模块级 `import vllm`，
即使只用 OpenAI 兼容后端也绕不开 → 离线包必须带 vllm+torch+nvidia（≈4.5 GB）。
若目标机只需 OpenAI 后端，可评估"CPU 版 torch + 受控 vllm 占位"把体积压到 ~1 GB，
但这属于对上游行为的偏离，需要单独评审，不能默默替换。

## 10. 断网安装与离线运行实证（U-03 关键项）

`pip download --no-deps -r locks/hipporag-2.0.0a4-requirements.txt` 产出 wheelhouse：
**184 个 wheel、3.5 GB**（`/tmp/wh-full`）。

随后在**全新 venv** 中用 `--no-index --find-links /tmp/wh-full --no-deps` 安装（禁用网络）：

```
Successfully installed ... hipporag-2.0.0a4 torch-2.5.1 transformers-4.45.2 vllm-0.6.6.post1 ...
offline import ok  /hipporag/__init__.py  torch 2.5.1+cu124
```

并在该离线环境里真跑索引+检索（LLM/embedding 用本机端点，不访问公网）：

```json
{"status":"OK","engine":{"version":"hipporag==2.0.0a4","chunk_id_rule":"chunk-<md5(text)>"},
 "mapping":{"units":4,"engine_chunks":3,"shared_chunks":1,"max_sources_per_chunk":2},
 "hits":[{"native_key":"chunk-89d6b39e…","sources":[{"file_id":"333"},{"file_id":"334"}]}]}
```

即：**断网可装、可导入、可跑通最小链路**，同文异源仍保留两个来源。

两个必须记住的限制：
1. `pip install -r`（带依赖解析）在冻结清单上会 `ResolutionImpossible`——清单里有历史钉版冲突；
   离线安装必须 `--no-deps` 按冻结清单顺序装（本环境即如此建成），且需要在部署脚本里固化这一点；
2. 安装后部分包版本与上游声明不一致（如 openai 3.x、pydantic 2.14），因为清单来自实际环境快照；
   若后续要接更严格的依赖校验，需要单独做一次干净重建并重新冻结。

## 11. 离线包制品化（清单 + 校验安装 + 干净机复验）

仓库只提交**清单**（wheels 3.5 GB 不进 git），清单里逐文件记录 sha256/字节数，以及冻结清单的 sha256：

```
scripts/build_offline_bundle.py   → offline/hipporag-2.0.0a4-py311-linux-x86_64.manifest.json
                                   184 wheels / 3,526.1 MB / schema=llmke.offline-bundle.v1
scripts/install_offline_bundle.py → 先逐文件校验 sha256 与大小，再 --no-index --no-deps 安装
tests/test_offline_bundle_manifest.py → 清单自洽（数量/大小合计/同名重复/哈希格式）
                                        + 冻结清单哈希与实际文件一致（防止"清单换了 wheel 没换"）
```

干净机验证（全新 venv，仅本地 wheel）：

```
install_offline_bundle -> {"status":"OK","wheels":184,...}
hipporag 索引+检索       -> {"status":"OK", 4 units -> 3 engine_chunks, 命中回指 333 与 334}
```

失败过一次并已修正：清单里 `requirements.path` 只写了 basename，而冻结清单原本在 `locks/`，
安装器在同级找不到 → 改为"冻结清单与 manifest 同级存放"，并在测试里钉住这个约束。

安装期两个必须写进部署脚本的事实：
1. 必须 `--no-deps`（带解析会 ResolutionImpossible）；
2. 必须先校验 sha256 再装（离线环境里"同名不同内容的旧 wheel"是最隐蔽的故障源）。

## 12. 离线 + 规模：83 块跨文档跑通（并修掉一个 id 撞车缺陷）

在"按清单装好的清洁环境"里跑 83 块（999011 的 46 正文 + 17 表格 + 17 摘要 + 333 的 3 块）：

```json
{"status":"OK","entities":204,"facts":280,
 "input":{"chunks":83,"engine_chunks":83,"merged":0},
 "queries":[{"query":"实体类型体系里对别名的处理规则是什么","hits":3,"resolved":3,"files":["999011"]},
            {"query":"产品的最高额度和利率基准","hits":3,"resolved":3,"files":["333","999011"]},
            {"query":"额度分项与总额度的关系","hits":3,"resolved":3,"files":["333","999011"]}]}
```

**跑出来的真实缺陷（已修）**：`input_unit_id` 原来只由 `(parse_artifact_id, seq)` 生成，
而正文块与表格块**各自从 0 编号**，于是同一快照的"正文 seq=0"和"表格 seq=0"撞成同一个单元，
映射层直接抛 `同一 input_unit_id 出现不同正文`。加入 `channel` 维度
（`sha256(artifact:channel:seq)`）后正常，并在单测里补了这条断言：
`input_unit_id(a,3) != input_unit_id(a,3,"table")`。

这也说明：**只有把真实的多通道数据喂进去才会暴露**，3 块的手写样本永远发现不了这个。
