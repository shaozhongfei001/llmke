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
