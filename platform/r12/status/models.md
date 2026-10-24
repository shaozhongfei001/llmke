# R12 模型与制品服务状态（model-ops 交付）

更新时间：2026-10-25　执行角色：model-ops（模型与制品）
依据：`platform/r12/R12-ENV-CONTRACT.md`。18090/18091/18092 与契约一致；**18093（VLM）原为契约外新增，TL 已于 2026-10-25 批准纳入 R12 契约**（定位：可选增强，非硬依赖）
结论：**四个服务全部真实可用**——`models/verify.py` 27/27 PASS（18090/18091/18092）、`models/verify_vl.py` 全 PASS（18093），均退出码 0

<!-- R12-DOC-STATE {"schema": 1, "service": "models", "era": "2026-10-25T06:22", "values": {"emb_port": 18090, "emb_dim": 1024, "rr_port": 18091, "llm_port": 18092, "llm_ctx": 8192, "llm_ngl": 99, "vlm_port": 18093, "vlm_model": "qwen2.5-vl-3b-instruct", "vlm_parallel": 2, "vlm_ctx_total": 32768, "vlm_ctx_slot": 16384, "vlm_ngl": 0}} -->

---

## 1. 服务总览

| 服务 | 端点 | 模型 | 设备 | 状态 |
|---|---|---|---|---|
| embedding | `http://127.0.0.1:18090/v1/embeddings` | `BAAI/bge-m3` (1024 维) | CPU 20 线程 | UP |
| rerank | `http://127.0.0.1:18091/v1/rerank` | `BAAI/bge-reranker-v2-m3` | CPU 20 线程 | UP |
| LLM | `http://127.0.0.1:18092/v1/chat/completions` | `Qwen2.5-7B-Instruct Q4_K_M` (GGUF) | CUDA0 RTX 3060 Laptop，33/33 层全量 offload | UP |
| VLM（TL 已批准纳入契约） | `http://127.0.0.1:18093/v1/chat/completions` | `Qwen2.5-VL-3B-Instruct Q4_K_M` + mmproj-f16 | CPU 20 线程（2 槽 × 16384） | UP |

一键启停：`platform/r12/models/start-all.sh {up|down|status|restart}`
- 冷启动实测 **5.1s** 全部就绪（页面缓存热；首次含模型加载见下表）。**含 VLM 后 6-8s**
- 日志：`platform/r12/logs/model-{embedding,rerank,llm}.log`
- PID：`platform/r12/run/model-{embedding,rerank,llm}.pid`（`setsid nohup` 常驻，独立进程组）

## 2. 制品与路径（全部本地，运行时不出网）

| 制品 | 路径 | 体积 | 来源 |
|---|---|---|---|
| bge-m3 | `platform/r12/models/bge-m3` | 2.2G | `HF_ENDPOINT=https://hf-mirror.com`（已删除未使用的 `onnx/` 副本 2.2G） |
| bge-reranker-v2-m3 | `platform/r12/models/bge-reranker-v2-m3` | 2.2G | 同上（`model.safetensors` 2.27GB） |
| Qwen2.5-7B-Instruct Q4_K_M | `platform/r12/models/gguf/qwen2.5-7b-instruct-q4_k_m-0000{1,2}-of-00002.gguf` | 4.4G | 同上，2 分片（4.68GB） |
| Qwen2.5-VL-3B-Instruct Q4_K_M | `platform/r12/models/gguf-vl/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf` | 1.93G | hf-mirror，仓库 `ggml-org/Qwen2.5-VL-3B-Instruct-GGUF` |
| mmproj（视觉投影器 f16） | `platform/r12/models/gguf-vl/mmproj-Qwen2.5-VL-3B-Instruct-f16.gguf` | 1.34G | 同上 |
| llama.cpp 源码 | `platform/r12/models/llama.cpp` | 661M | 取自 `llama_cpp_python-0.3.36` sdist 内置 `vendor/llama.cpp`（github 直连仅 ~60KB/s，sdist 走阿里云更快） |
| llama-server 二进制 | `platform/r12/models/llama.cpp/build/bin/llama-server` | — | 本机 cmake 构建，`GGML_CUDA=ON` `CMAKE_CUDA_ARCHITECTURES=86`，版本 `0.5.0-dev (build 132, 87072f9)` |
| Python venv | `platform/r12/venvs/models` | 1.1G | Python **3.11.9**；`torch 2.6.0+cpu`、`transformers 4.57.6`、`fastapi 0.162.0` |

依赖来源：`https://mirrors.aliyun.com/pypi/simple/` + `torch-2.6.0+cpu` 阿里云 pytorch-wheels 直链。**未安装进系统 Python。**

## 3. 实测指标（全部为本机真实测量，无 mock 分支）

### 3.1 embedding（18090）
| 指标 | 实测值 |
|---|---|
| 维度 | **1024**（healthz 与响应一致） |
| 余弦(银行承兑汇票的贴现利率, 供应链金融授信额度) | **0.5376** |
| 余弦(银行承兑汇票的贴现利率, 今天天气很好适合去公园散步) | **0.3295**（对照，证明非随机/常量向量） |
| 相关 > 无关 | PASS（0.5376 > 0.3295） |
| 向量 L2 范数 | 1.0000（已归一化）；非零元素 1024/1024 |
| 吞吐（batch=32，句长 ~30 字） | **9.9–17.5 句/s**（同机 4 次实测区间；测试时 load average 26.7/20 核，受其他角色编译与服务抢占，属环境噪声非模型波动） |
| 吞吐（长文本 877 tokens 一批 16 句） | 2.15s → **407 tok/s** |
| 首次加载 | 2.03s（冷启含进程启动 5s 内就绪） |
| 常驻内存 RSS | 1.9G |

### 3.2 rerank（18091）
| 指标 | 实测值 |
|---|---|
| query=票据贴现利率如何确定 / doc0=银行承兑汇票贴现利率由票据市场供求决定 | **0.98153** |
| 同 query / doc1=今天天气很好 | **0.0000162**（Δ=0.9815，量级差 6 万倍） |
| 5 文档重排 | top1 index=0，分数 0.9982，耗时 0.51s |
| 吞吐（20 篇长文档，512 token 截断） | 3.90s → **5.1 doc/s** |
| 分数区间 | sigmoid → (0,1)；同时返回 `relevance_score` 与 `score`（值一致） |
| 首次加载 | 0.49s；RSS 1.9G |

### 3.3 LLM（18092）
| 指标 | 实测值 |
|---|---|
| 首字延迟 TTFT（流式） | **26 ms / 49 ms**（两次测量） |
| 流式分片数 | 24–27 片，以 `data: [DONE]` 收尾 |
| 流式生成速度 | **43.8–46.7 tok/s** |
| 非流式生成速度（307 tokens/6.95s） | **44.2 tok/s** |
| 中文质量样例（前 80 字） | 「银行承兑汇票贴现是指持票企业将未到期的承兑汇票以一定贴息折扣卖给银行。」（流式）<br>「应收账款融资、预付款融资、存货融资」（非流式） |
| 显存占用 | **4911 MiB / 6144 MiB**（ctx 提到 8192 后；模型 4.4G + KV/计算缓冲，n_slots=4、kv_unified） |
| 宿主内存 RSS | 0.6G |
| 模型加载 | 1.75s（CUDA 全量 offload，`--n-gpu-layers 99`） |
| 长 prompt 实测 | 2552 token prompt + 48 max_tokens → 1.79s，**未截断**，答「上表列出了多个客户的日均存款、授信额度及风险等级信息。」 |

> ctx 已于 2026-10-25 02:25 从 4096 提到 **8192**（parse 侧表格摘要需要）。8192 是 4 个并发槽共享总预算。
> **02:35 已实测生效**：`/v1/models` → `n_ctx=8192`；复刻 parse 侧 5000 字符表格 + `max_tokens=1000` → prompt 3670 + completion 115，`finish_reason=stop`（未截断），3.87s。
> 余量结论：5000 字符表（parse 实测 prompt≈4069）+1000 max_tokens ≈ 5069，8192 下单一请求剩约 3100；
> **两个大表并发就会超预算**，大表必须串行（parse 已把 `table_split_max_worker` 降到 1）。

### 3.4 VLM（18093，TL 已批准纳入契约）
| 指标 | 实测值 |
|---|---|
| 模型 | `Qwen2.5-VL-3B-Instruct-Q4_K_M` + `mmproj-f16`（llama.cpp mtmd） |
| 上下文 | **2 槽 × 16384（`--parallel 2 --ctx-size 32768`，每槽私有 KV，04:35 起）**；历史：4096 → 8192(02:35) → 16384 共享(03:20) |
| 图片编码（视觉塔，纯 CPU） | **约 16–26s / 张**（900×420 PNG，约 518 image tokens）；**极度负载敏感**：load≈25 时同图 111.5s；**load≈30 时实测 2801 token 图 prompt eval 212s + 64 token 生成 359s（0.18 tok/s）≈ 571s**，parse 侧同源观测 0.28 tok/s → **高负载按 30–50× 余量估算，且此时基本不适合在线使用** |
| 图片 token 公式（实测拟合） | `tokens ≈ (W/28) × (H/28)` —— 900×420→518、1600×747→1570、2048×956→2513、2048×1800→4111，全部吻合 |
| 大图实测 | 2048×1800 JPEG → prompt 4111 tokens，**239.3s**，答案仍正确（`对公客户存款与授信情况表`）——4111 token 已超过旧配置 ctx 4096（现在是 16384） |
| 格式支持 | PNG 与 JPEG 的 `data:image/{png,jpeg};base64,...` 均实测可用 |
| mime 校验 | 不校验：把 PNG 字节声明成 `image/jpeg` 仍能正确识别（按字节嗅探），parse 侧硬编码 jpeg 不是问题 |
| 负载 vs 吞吐（A4 ≈2780 image token，首次请求） | load1=**13.4** → prompt eval **29.25 tok/s**，总 **125.2s**；load1=**25–30** → prompt eval **13.21 tok/s**（212s 仅 prefill），总 348–571s。<br>**同一份 13.21 tok/s 在「4 槽共享池」与「2 槽私有」两种配置下完全一致 ⇒ 单图延迟由机器负载决定，与 `--parallel`/ctx 配置无关**（不要把低负载窗口的提速归因于配置） |
| 表格 → Markdown | **37.7s，4 行表格逐格全对**（见下方样例） |
| 定向问答（按客户名） | 「华东制造集团的日均存款和授信额度」→ **1250 / 8000**（正确），16.8s |
| 自由描述 | 27.7s，正确说出标题「对公客户存款与授信情况表」+ 3 个客户名 + 3 个日均存款数字 |
| 流式 | 可用，TTFT≈16.4s（首片要等视觉编码完），总 20.9s |
| 显存 | **0**（`--n-gpu-layers 0 --no-mmproj-offload`）；mmproj 尝试上 GPU 直接 OOM，见 §6.8 |
| 模型加载 | 2.8s（含 mmproj 1.34G） |

**能力边界：多图拼接会丢内容并虚构（重要，勿用多图单请求做逐字转录）**

样本仍是 parse 的真实 fixture（3 张 1240×1754 扫描页）。先逐图单独问「逐字抄录图中所有可见文字」，得到 ground truth，再把 3 张塞进**同一个请求**：

| 方式 | 输入 | 输出 | 判定 |
|---|---|---|---|
| 单图 image1（英文页，14 行 + 页眉） | 1 图 | 140 token，页眉 + `line 1…line 14` **逐字全对** | ✅ |
| 单图 image2 | 1 图 | `扫描页副本 1：客户 1 日均存款 137 万` | ✅ |
| 单图 image3 | 1 图 | `扫描页副本 2：客户 2 日均存款 274 万` | ✅ |
| **2 图同一请求**（image1 英文页 + image2 中文页，`max_tokens=256`） | 2 图，prompt 5581 | 131 token，只有 `line 1…` `line 2…` 英文行 | ❌ **中文页内容整段消失**（应出现 `扫描页副本 1：客户 1 日均存款 137 万`） |
| **3 图同一请求**（`max_tokens=1024`） | 3 图，prompt 8387 | 57 token，`finish_reason=stop`：<br>`扫描页副本 1：客户 1 日均存款 137 万`<br>`扫描页副本 2：客户 2 日均存款 274 万`<br>`扫描页副本 3：客户 3 日均存款 123 万` | ❌ **整张英文页内容全丢**（140 token 应有内容一个字都没有）+ **虚构了不存在的"副本 3 / 客户 3 / 123 万"** |

三点结论：
1. **不是 max_tokens 不够**：输出只有 57 token、`finish_reason=stop`，远未触顶；两张中文页逐字只需 ~20 token/张，预算充足。
2. **不是随机改写漂移**：是**整图内容丢失 + 按模式补全虚构**——比"表述变差"严重一个量级，直接污染证据链。
3. **硬规则：逐字转录必须一图一请求**；多图拼接只能用于「整体摘要/分类」，绝不能作为正文或证据来源。
   **调用侧现状（已核对代码，非违规）**：parse 的 `server/controller.py:160-201` 是「每个 worker 只放 1 条 text + 1 条 image」，N 张图 = N 次独立 chat 调用（并发线程池提交），**现状就是一图一请求**，本条红线是防止后续改动退化成拼接。
4. **危害等级**：虚构条目**编号连续、格式规整**（`副本 3：客户 3 日均存款 123 万`），人工抽检几乎无法发现，机器校验也难过（字段齐全、类型正确）。
   因此判定不是"准确率下降"，而是"**多图批量输出不得作为证据链输入**"——一旦进入 chunk/索引，错误会被后续检索与问答无限放大。

**分辨率：不存在「一刀切缩放」的安全值（本条经两方实测修正，勿按长边阈值配置）**

早前本文写过「长边 ≤1024 可提速」，**该结论已撤回**。同一批实验显示可读性取决于「有效字形像素高度 + 扫描噪声」，不能用统一长边阈值概括：

| 来源 | 图片 | 送入尺寸 | img_tokens | 结果 |
|---|---|---|---|---|
| parse-ops（真实 docx 扫描页） | A4 小字扫描 | 1240×1754 原始 | 2774 | ✅ 完整读出，215.4s |
| parse-ops（同上） | 同上 | 723×1024 | 944 | ❌ **NO_TEXT（连跑 3 次都是）** |
| parse-ops（同上） | 同上 | 542×768 | 531 | ⚠ 只读正文，**丢页眉** |
| 我（合成小字页，13px 无噪声） | 1240×1754 | 原始 | 2802 | ✅ 正文全读，**页眉同样漏**，456.8s |
| 我（同上） | 同上 | 723×1024 | 992 | ✅ 正文仍可读（与 parse 相反，因为合成字清晰无噪声），**页眉仍漏**，91.1s |

结论：①**是否可缩放必须在真实扫描件集上标定**，合成图不能替代；②**页眉页脚不是 VLM 盲区**（见下条更正）；③R12 现状取「原图直送（能读但慢）」，压缩只在「大字号照片/示意图」类安全。

> **更正（2026-10-25 03:40）：早前"页眉被漏读"的结论不成立，系合成图伪影。**
> 在 parse 的真实 fixture `docx-image.docx`（1240×1754 扫描页）上定向提问「页面最上方、正文之前那一行英文是什么」→ VLM 输出 **`SCANNED PAGE - no text layer`（逐字正确）**，286.8s，prompt 2810。
> 另一组批量请求也一次读出了页眉 + 前 5 行：`'SCANNED PAGE - no text layer\n\nline 1 of a scanned document image'`。
> 我先前观察到的"页眉漏读"只出现在自造合成页上，且当时输出被 `max_tokens=220` 截断（末尾为半句 `Th`）——**是先抄正文、预算耗尽后没抄页眉，不是看不清**。
> 对照：parse 侧 OCR 也抓到了该页眉，但带噪声（`SCANNED PAGE-notex layene 1 of eline 2ofascanned`），VLM 版本逐字干净。
> 因此职责划分应是 **OCR 负责覆盖度/定位，VLM 负责精确转录，二者互补**；不要据此立"VLM 页眉盲区"缺陷。

**并发与 KV 预算**

> **04:35 配置变更（消除跨请求 KV 争抢）**：`--parallel 2 --ctx-size 32768` ⇒ 服务端分配 **2 个槽、每槽私有 16384**（日志 `n_slots = 2, n_ctx_slot = 16384, kv_unified = 'false'`）。
> 早前是 `n_slots=4 + kv_unified=true`，16384 由 4 个槽**共享**——这正是"2 图 71% 占用即 `failed to process mtmd chunk`"的成因。
> 改后实测：**4 个并发独立请求（各 2801 token）全部 200，零 mtmd/KV 错误**（c0 716.9s / c1 405.7s / c2 259.7s / c3 574.4s，墙钟 716.9s，load≈29.6），
> 超出 2 个的请求**排队而非报错**。⇒ 调用侧并发过高不再导致整篇 500，代价是延迟线性拉长。
> 注意 per-slot 16384 意味着**单个请求自身也必须 ≤16384**（3 图 8355 ✅，超过则仍会失败）。

下表保留两轮历史实测（8192 共享池 / 16384 共享池）作为成因证据，样本是 parse 侧真实 fixture（`platform/r12/parse/fixtures/generated/docx-{2,3}images.docx` 内嵌的 1240×1754 PNG，2728 token/张）：

| ctx | 场景 | prompt tokens | 占 ctx | 结果 |
|---|---|---|---|---|
| 8192 | 串行 4 张（515 token/张） | — | — | 总 94.9s，单张 19.8–32.5s ✅ |
| 8192 | 并发 4 张（另 4 张全新图） | 2060 | 25% | 总 87.7s，但每请求等 87.7s → 加速比 **1.08×** |
| 8192 | 2 并发独立请求 × 2513（2048×956） | 5026 | 61% | 全部 200 ✅ |
| 8192 | 2 并发独立请求 × 2803（真实 A4 扫描件） | 5606 | 68% | 全部 200 ✅，但日志出现 `failed to find free space in the KV cache, retrying with smaller batch size`（已在悬崖边缘） |
| 8192 | **单请求 2 图**（真实 A4） | 5581 | 68% | 200 ✅（同样触发 KV 警告） |
| 8192 | 单请求 2 图（**parse 真实链路**，max_tokens 256） | ~5804 | 71% | ❌ **HTTP 500 `failed to process mtmd chunk, res = -1`** |
| 8192 | 单请求 3 图（parse 真实链路） | ~8322 | 102% | ❌ HTTP 500（超出 ctx） |
| 8192 | 2 并发 × 4489 纯文本 | 8978 | 110% | ❌ 两请求同时 500 `Context size has been exceeded` |
| **16384** | 单请求 2 图（真实 A4） | 5581 | 34% | ✅ 200，212.3s，**无 KV 警告** |
| **16384** | 单请求 **3 图**（真实 A4） | 8355 | 51% | ✅ 200，175.3s，**无 KV 警告**（out 256 打满 max_tokens） |

结论（据此修正早前"N=2 就安全"的说法）：
1. **失败根因是 KV 余量，不是 mtmd 并发编码本身**：unified KV 需要给整段图像 chunk 找到**连续**空间；占用到 68% 就开始出现 `failed to find free space in the KV cache`，到 71% 直接 `failed to process mtmd chunk`（parse 实测），超过 100% 则 `Context size has been exceeded`。
2. **安全水位取可用 ctx 的 ≤60%**，且必须另留 `max_tokens`。按 60% 反推：每图 T 个 token 时 `N = floor(0.6*ctx - max_tokens) / T`。
   共享池时代 16384 下 T≈2728（整页扫描件）→ N≤3；**现在每槽私有 16384，单个请求上限即 16384**。
   **新配置下已实测**：单请求 3 图（3×1240×1754 全新图）→ prompt **8374** token、**HTTP 200**、零 mtmd/KV 错误、613.3s（load1 18→27）✅；
   4 图约 11000（占 67%），理论上可容纳但不推荐。
6. **单页逐字转录的 `max_tokens` 余量实测（中文）**：
   - 稀疏页（fixture，14 行短句）→ 输出 140–200 token，512 有 2.5× 余量；
   - **密排页（36 行中文条款、输出 704 字）→ 实际用掉 427 token、`finish=stop`**，512 只剩 **1.2×** 余量。
   - 中文经验比 ≈ **1.65 字/token** ⇒ `max_tokens=512` 约合 **840 汉字**输出；超过会 `finish=length`。
   - ⇒ 条款/合同类整页密排扫描件建议 **768–1024**；若坚持 512，必须依赖 `finish_reason=='length'` 判定 `truncated`（调用侧已实现），否则会静默只抄半页。
7. **多图逐字转录时 `max_tokens` 必须按图数放大**：同一 3 图请求用 `max_tokens=600` 实测 `finish_reason=length` —— 只抄完【图1】的 14 行就截断，图2/图3 完全没输出，
   且【图1】**页眉再次被略过**（模型先抄正文，预算耗尽后跳过头行）。单张 A4（14 行小字）逐字约需 150–200 token，3 图应给 **≥1500**。
   这与"页眉不是识别盲区、而是输出预算问题"的结论一致（见 §3.4 更正块）。
3. **并发几乎不换吞吐**（1.08×），只放大延迟 → **推荐并发 1**。
4. **失败形态**：单请求自身超 per-slot ctx → 硬 500；**跨请求超配在 04:35 后不再产生 500**，而是排队（实测 4 并发全 200）。
5. 内存：共享池配置（4 槽/16384）多图任务后 RSS 峰值 **7.7G**；**现配置（2 槽 × 16384 私有）起步 4.5G**，反而更省。
   仍**不建议再加 ctx**：本机 available 一度只有 7G，且加 ctx 对吞吐无帮助。
6. 注意 `verify_vl.py` 打印的耗时是**缓存热值**（实测 25.5s / 1.14s / 6.2s，因为是脚本内复用的同一张图），**不可当作性能指标**；
   冷启动/首次请求的真实值见 §3.4（20–457s，随图大小与负载变化）。

**延迟评估方法（缓存陷阱，必读）**
llama-server 会缓存「相同图片 + 相同 prompt 前缀」的计算结果：同一张图同一问题，**首次 38.1s / 111.5s，第二次仅 0.7s / 2.0s**（我在 4 并发实验里也复现了这个假象，一度误判并发有 2.35× 收益）。
因此：①**报延迟只认首次请求**；②**每次测量必须换新图片**；③不要用重复请求评估吞吐。

> **取数机制（04:50 定稿，比 `uptime` 可靠）**：非流式响应体自带 `timings`，字段有 `prompt_n / cache_n / prompt_per_second / predicted_per_second`。
> - **权威延迟指标 = `prompt_per_second` / `predicted_per_second`**（服务端自测），**不要用 `load1` 倒推**——load1 采样时点滞后，
>   parse 侧实测过「请求期间低负载、请求结束后 load1 才升到 25.96」的错配。
> - **`cache_n` = 从 KV 缓存复用的 prompt token 数**（实测：首次约 14–29，仅模板前缀；**完全相同的图片+问题第二次复用 506/507**，`prompt_n` 掉到 1）。
>   ⇒ 校验规则：**`cache_n / (prompt_n + cache_n) ≤ 5%`** 才算一次干净的首次测量。
>   口径订正（parse 侧 06:20）：llama.cpp 的 `prompt_n` = **本次实际评估**的 token，`cache_n` = **复用**的 token，两者之和才是总 prompt
>   （实测 `usage.prompt_tokens == prompt_n + cache_n`：493+14=507、1+506=507）。分母必须用 `prompt_n + cache_n`；
>   写成 `cache_n / prompt_n` 会把"完全命中"算成 296200%，反而看不出问题。
> - `bench_vl.py` 已按此实现：每次运行随机换图 + `cache_n` 校验 + 打印服务端 tok/s。

> **"慢"的真实成因：不是机器慢，是槽间争抢（05:40 定位）**
> parse 侧一次 2 图测量在 load≈30 下 532s 未完成，服务端日志显示同一条请求：
> **prefill 正常（157.9s / 3331 token = 21.1 tok/s）、生成被饿死（374.6s / 276 token = 0.73 tok/s）**。
> 同一时刻另一个槽正在处理 3871 token 的长请求（邻居任务）⇒ **2 个槽里一个做长 prefill，另一个的 generation 会被抢到 0.7 tok/s**。
> 推论：①"load1 高"只是表象，**真正的判据是"两个槽都空闲"**；②VLM 自身 `--threads 20` 一个请求就吃 ~8–12 核，
> **用 load1 当测量闸门是循环论证**（一开始测，load 就涨）。
> 为此新增 `models/measure_window.py`：同时判 **load1/load5、MemAvailable、VLM 进程 CPU（<0.25 核 = 空闲）、embedding/rerank 占用**，输出 GO/NO-GO。
> 两种模式（parse 侧反例促成）：`--mode capacity` 要求负载**与**槽都干净（容量数据要可引用）；`--mode functional` 只要求槽空闲 + 内存够，负载仅提示不阻塞（功能/回归用例的正确性与负载无关）。
> 实测反例：`load1=19.67/load5=26.49` 但 `VLM cpu=0.00 核` ⇒ capacity 判 NO-GO、functional 判 GO —— **"机器忙"和"模型槽被占"是两件事**。
> 另测到**邻居的 rerank 大 batch 会瞬时吃掉 17.7 核**（embedding 也曾 1.5 核），同样会抢 VLM 的 CPU，属跨角色资源冲突，需排期而非调参。

> **单图冷测的耗时构成（06:10 干净窗口，parse 侧 C14 图2）**：prompt 2879（`prompt_n 2863 + cache_n 16`，命中率 0.56% ✅）、
> **prefill 96.25s @ 29.74 tok/s** + **generation 170 tok / 46.21s @ 3.66 tok/s** = **142.47s**。
> 该 prefill 速率与我 05:15 在 load1≈13.4 测的 29.25 tok/s 互相印证（同负载档一致）。
> ⇒ 容量要点：**prefill（图像 token）占约 2/3 时间，generation 每 token 才是真慢**；按此推算 2 张冷图约 285s（估算，需实测）。

> **一阶成本模型（低负载档，load1 ≤5、20 线程；系数经 10 个历史任务独立复核）**
> `单图耗时 T(s) ≈ 0.0334 × image_tokens + 0.287 × output_tokens`（generation 系数取 272–302 中值）
> - prefill 系数：**33.4 / 33.62 / 34.14 ms/img-token**（我 1 条 + parse 侧 2 条独立数据，差 1.5% 内）✅
> - generation：**272–302 ms/out-token（3.3–3.7 tok/s）**，272 是**下界不是中位**；
>   **长输出更贵**：输出 427 token 时升到 **361 ms/token** ⇒ 线性模型对长输出会低估，>300 token 输出需实测。
> - 自校验：A4（2863 img tok）+170 输出 → 公式 141.8s vs **实测 142.47s（差 0.5%）**；900×420+64 → 34.4s vs 实测 37.5s（负载更高）。
> - **推算必须写死假设**：`2 张 A4 冷图 ≈ 301s`、`3 张 ≈ 440s`，前提是**每图 200 字输出（≈400 tok 合计）**；
>   若误把 200 字理解成"两图共 200 字"，会得到 246s（差 55s）。**推算值一律标注"推算、非实测"**；偏差 >20% 视为"发现"，要查并发/KV/内存带宽，**不得回头改模型去拟合**。
> - **负载敏感度（parse 侧 10 任务复算，比我原表更保守）**：prefill 33.6→47.4 ms/token（load 3.5→30，**1.41×**）；generation 272→1357 ms/token（**5.0×**）。
>   ⇒ 高负载下瓶颈是 **generation（5×）而非图像大小（1.4×）**，加核/配额 > 缩图（且缩图在真实小字件上会 NO_TEXT）。
> - **取数纪律**：容量数据必须同时带 `prompt_n / cache_n / out_tok` 三件套，否则**不可校验**（FIX-PARSE-05 之前的数据没采 `timings`，无法反推 token，不能拿来推翻或支持模型）。
> - **era 依赖（与 parse 侧 §16.18.1 同规则）**：本模型系数属于 `era=2026-10-25T06:22`（线程 20/20/20/20、18093 `parallel 2 + ctx 32768`）。
>   **一旦执行 B（线程配额变更）或再改 ctx/parallel，era 立即失效：系数必须重标定，旧系数不得复用于新 era 的推算**；
>   同理，引用任何耗时/容量数据前先确认它的 era 与当前配置一致，否则标「不可校验」。


> **已排除的严重怀疑：同尺寸不同图片不会被旧 KV 污染（负结果，重要）**
> 担心点：A4 扫描页尺寸全相同、图像在 prompt 里占位 token 也相同，若按 token 前缀匹配就可能复用**上一张图的 KV**。
> 实测 3 张同尺寸（1240×1754）不同内容的图，同一问题连续请求：
> `CASE-AAA111` → `AAA111` ✅（prompt_n 2793 / cache_n 14）、`CASE-BBB222` → `BBB222` ✅（2793 / 14）、
> `CASE-CCC333` → **`CASE-CC333` ❌**（2778 / 29）。
> 前两张证明**不同图片不会复用旧 KV**（否则会答出前一张的编号）；第三张**prompt_n 为全量、非缓存**，是**字符级识别错误**（三个连续 C 丢了一个）。
> ⇒ ①跨图缓存污染不存在，parse 一图一请求的链路安全；②但 **VLM 逐字并非字符零错**，连号/重复字符易丢，**编号、金额、日期这类字符敏感字段不能只靠 VLM**，需 OCR 或结构化校验兜底。

表格 → Markdown 实测输出（未做任何后处理）：
```
| 客户名称 | 日均存款(万元) | 授信额度(万元) | 风险等级 |
| --- | --- | --- | --- |
| 华东制造集团 | 1250 | 8000 | 正常 |
| 城南物流有限公司 | 860 | 5000 | 关注 |
| 北方能源科技 | 2310 | 15000 | 正常 |
```
验证入口：`../venvs/models/bin/python verify_vl.py`（读取 `make_test_image.py` 生成的中文表格图，断言命中图中真实客户名/数字）。

## 4. 启动命令（等价于 start-all.sh）

```bash
PY=platform/r12/venvs/models/bin/python
# embedding
EMB_MODEL_DIR=platform/r12/models/bge-m3 EMB_PORT=18090 $PY platform/r12/models/serve_embedding.py
# rerank
RR_MODEL_DIR=platform/r12/models/bge-reranker-v2-m3 RR_PORT=18091 $PY platform/r12/models/serve_rerank.py
# llm
platform/r12/models/llama.cpp/build/bin/llama-server \
  --model platform/r12/models/gguf/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf \
  --alias qwen2.5-7b-instruct --host 127.0.0.1 --port 18092 \
  --ctx-size 8192 --n-gpu-layers 99 --threads 8 --jinja --no-webui --metrics
# vlm（TL 已批准纳入契约，纯 CPU）
platform/r12/models/llama.cpp/build/bin/llama-server \
  --model platform/r12/models/gguf-vl/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf \
  --mmproj platform/r12/models/gguf-vl/mmproj-Qwen2.5-VL-3B-Instruct-f16.gguf \
  --alias qwen2.5-vl-3b-instruct --host 127.0.0.1 --port 18093 \
  --ctx-size 32768 --parallel 2 --n-gpu-layers 0 --threads 20 --no-mmproj-offload --jinja --no-webui
```

可调环境变量：`EMB_DEVICE/EMB_THREADS/EMB_MAX_BATCH/EMB_MAX_LEN`、`RR_BATCH/RR_MAX_LEN/RR_THREADS`、`LLM_NGL/LLM_CTX/LLM_THREADS/GGUF_PATH`、`VL_NGL/VL_CTX/VL_THREADS/VL_MMPROJ_OFFLOAD/VL_IMAGE_MAX_TOKENS/VL_MODEL_PATH/VL_MMPROJ_PATH`。

## 5. 验证方式（可复跑）

```bash
cd platform/r12/models && ../venvs/models/bin/python verify.py      # 18090/18091/18092 期望 RESULT: ALL PASS
cd platform/r12/models && ../venvs/models/bin/python verify_vl.py   # 18093（先跑 make_test_image.py 生成图）
cd platform/r12/models && ../venvs/models/bin/python bench_vl.py    # 18093 首次请求延迟基准（诚实口径）
cd platform/r12/models && ../venvs/models/bin/python measure_window.py       # 测量窗口闸门（capacity）
cd platform/r12/models && ../venvs/models/bin/python check_doc_consistency.py # 文档腐化检查（文档 vs 运行态）
```

`check_doc_consistency.py` 把本文档里的关键参数（18092 ctx、18093 parallel/ctx、embedding 维度、pidfile↔listening pid、工具文件是否存在）
与**活着的进程**逐条对账。起因：今天两个角色各自踩过"配置改了文档没跟"（本文 §6.8 的 N≤3、parse 侧 §3 的 16384），
这类错误不报错、不失败，只会让后人按旧数字决策。**已做变异测试证明它真会失败**：把文档 `--ctx-size 8192` 改成 4096 → `FAIL 文档 4096 vs 实测 8192`；恢复 → PASS。
**每次改配置后必须跑一次**；它绿 = 文档可引用，它红 = 文档不可引用。

**退出码分三类，目的是告诉你该改哪里**（与 parse 侧 §16.18.2 同口径；三类都已做变异自测）：

| rc | 类别 | 含义 | 该改什么 |
|---|---|---|---|
| 0 | 一致 | 文档与运行态相同 | — |
| 1 | `FAIL` | 取到值但**不相等**（`vlm_ctx_slot 8192 vs 实测 16384`） | 配置或文档 |
| 3 | `ERROR` | **根本没取到值**（key 改名 / 路径解析错 / 层级变动） | **检查器**，不是配置 |
| 2 | `UNREACHABLE` | 端口/进程连不上 | 环境（服务没起） |

`ERROR` 会**立即中止比对并优先返回**——因为一行都没比上，继续比只会误导。三类自测：
```bash
sed 's/"vlm_ctx_slot": 16384,//' status/models.md > /tmp/m1.md && python models/check_doc_consistency.py --doc /tmp/m1.md   # rc=3 ERROR
sed 's/"vlm_ctx_slot": 16384/"vlm_ctx_slot": 8192/' status/models.md > /tmp/m2.md && python models/check_doc_consistency.py --doc /tmp/m2.md  # rc=1 FAIL
sed 's/"emb_port": 18090/"emb_port": 18999/' status/models.md > /tmp/m3.md && python models/check_doc_consistency.py --doc /tmp/m3.md        # rc=2 UNREACH
```
`--doc` 参数就是为自测加的；没有它，自测只能靠"手动改真文档再恢复"，那是风险不是测试。

`bench_vl.py` 强制三条口径，供对外引用的性能数字必须来自它：①`load1 > 15` 直接 SKIP（高负载下 0.18 tok/s，测出的耗时是噪声）；
②每次测量**生成全新图片**（不命中缓存）；③**每张图独立请求**（符合 R-1 红线）。实测样例（load1=21.46，900×420，510 image token）：
首次 **37.5s**，marker 命中 1/1；同机 `--force` 可用于高负载对照。
`verify.py` 覆盖：维度=1024、batch index 顺序、真实 token usage、相关/无关余弦对比、str 与 list[str] 两种入参、
rerank 两种请求体（`documents` / `texts`）+ `top_n`、`score` 字段一致性、SSE 分片数>1 + `[DONE]` + 中文汉字计数、
非流式对照 + 真实 `completion_tokens`、TTFT 上限。任一项不满足退出码非 0。
`verify_vl.py` 覆盖：模型 id、图片描述命中图中真实客户名/数字、定向核对 1250/8000、流式可用。

## 6. 关键决策与已知限制（如实记录）

1. **GPU 只给了 LLM（7B）**。6GB 显存装不下「7B Q4(4.68G) + bge-m3(2.2G) + reranker(2.2G)」，实测 LLM 单独占用 4911MiB（ctx 8192）、余量约 1.2GB 不足以再放 bge-m3，也不足以放 VLM 的 mmproj（需 1276MiB，实测 OOM）。
   因此 embedding/rerank/VLM 全部走 CPU 20 线程（吞吐如上，对 RAG 检索链路够用：单条 query 编码 <100ms）。
   **CPU 是三方共享资源**：embedding / rerank / VLM 各自 `torch.set_num_threads(20)` 或 `--threads 20`，同时跑会互相抢核；
   批处理图片期间建议错开索引/检索高峰。
2. **venv 内 torch 是 CPU 版（`2.6.0+cpu`，`torch.cuda.is_available()==False`）**。若要给 embedding 上 GPU，
   需另装 CUDA 版 torch（额外约 3GB 依赖）并解决与 LLM 争用显存；本轮**未做**，不声称支持。
   `EMB_DEVICE=cuda` 开关存在但当前依赖下会失败 —— 这是真实限制，不是配置遗漏。
3. **四个服务均未设 API key**（llama-server 日志有 `no API key is set and CORS allows all origins` 告警），只监听 `127.0.0.1`。
   **不得直接对外暴露或做端口映射**；前端/外部调用必须经 Java 网关（8088）或前端反代（18088）转发并在网关侧鉴权限流 —— 详见 §8 R-2。
4. **不出网**：transformers `local_files_only=True`，llama-server 纯本地 GGUF。运行期采样 `ss -tanp`：
   三个服务的连接**全部为 127.0.0.1 回环**，非回环连接数 0（排除的其他监听端口 8106/12340 属既有进程，非本批次服务）。
5. **下载来源**：pypi/github 直连不可用或极慢（github ~60KB/s）；已按 TL 指定走阿里云镜像与 `hf-mirror.com`。
   llama.cpp 源码改从 `llama_cpp_python-0.3.36` sdist（76MB，内置 `vendor/llama.cpp`）取得，版本等价于上游 0.5.0-dev。
6. **rerank 长文档吞吐偏低**（5.1 doc/s，CPU fp32、512 token）。若整链路压测不够，优先调 `RR_BATCH=32` 或缩短 `RR_MAX_LEN=256`；
   不建议上 GPU（见限制 1）。
7. `models/bge-m3/onnx/` 已删除（2.2G 重复制品，服务走 PyTorch 路径）；如需 onnxruntime 方案需重新下载。
8. **VLM 只能跑 CPU**（18093 已由 TL 批准纳入契约，但受显存限制只能 CPU）。为解 parse 侧「文档内图片理解」的阻塞（18092 是纯文本 7B，无视觉），
   新增 `Qwen2.5-VL-3B-Instruct`（GGUF Q4_K_M + mmproj-f16，llama.cpp mtmd）。实测结论：
   - 把 mmproj 放 GPU 会直接失败：`cudaMalloc failed: out of memory`（需 1276.40 MiB，当时仅余约 1.2GB）→ `GGML_ASSERT(buffer)` abort。
     因此固定 `--n-gpu-layers 0 --no-mmproj-offload`，显存占用 0，不与 7B 争抢。
   - 代价是**慢**：视觉编码约 16s/张，表格→Markdown 37.7s/张。适合异步/批处理，不适合实时问答。
   - 若后续要提速，唯一可行方向是减少 GPU 上 7B 的 offload 层数腾显存（7B 会掉到 10 tok/s 量级）——
     这是业务取舍，需 TL 决策，我不擅自改 7B 配置。
   - `--image-max-tokens 512` 实测能省 ~1s 但会**降低表格准确率**（把第 2 行答成第 3 行的 860/5000），故默认不设该参数。
   - ctx 两次上调：4096 → **8192**（单张大图视觉 token 就 4111，4096 放不下）→ **16384**（多图/大图要留 KV 余量，
     8192 下 68% 就出 `failed to find free space in the KV cache`、71% 直接 `failed to process mtmd chunk`）。均为纯内存开销，不占显存（RSS 起步 3.9G，多图任务后峰值 7.7G）。
   - **并发必须按水位限**（§3.4 表）：安全水位取 `Σ(prompt+max_tokens) ≤ 0.6×ctx`；超预算不是静默截断，而是硬 500（`Context size has been exceeded` 或 `mtmd chunk`），且会连累同批其他请求。
     **现行配置（04:35 起）**：2 槽 × **私有** 16384 ⇒ 单请求上限 16384（3 图 8355 ✅、4 图 ~11000 不推荐）；
     跨请求争抢已消除（4 并发全 200、超出 2 个改排队，见 §3.4）。吞吐上并发仍无收益（1.08×），**运行时按 N=1**。
     parse 的 `run_in_thread_pool`（controller.py:194）默认 32 并发线程池仍是风险点（会造成排队长尾与线程阻塞），需其调用侧自限。
   - **单请求超过 16384 仍会硬 500**；且 2 槽里一个做长 prefill 时另一槽生成会被饿到 0.73 tok/s（§3.4「槽间争抢」）。
   - **并发不带来吞吐**（实测 1.08×），推荐值为 1 —— 并发只会放大延迟。
   - **不建议一刀切缩放图片**：parse 的真实 A4 小字扫描页压到长边 1024 后模型判定「无文字」（连跑 3 次），768 丢页眉；
     而我用合成小字页在 1024 下仍可读。差异来自「有效字形像素高度 + 扫描噪声」，只能拿真实扫描件集标定，不能写成通用阈值。
   - **页眉页脚不是盲区**（03:40 更正）：真实 fixture 上 VLM 逐字读出 `SCANNED PAGE - no text layer`；
     先前的"漏读"是我的合成图 + `max_tokens` 截断造成的假象，不据此立缺陷。
   - 18093 已由 TL 批准纳入 `R12-ENV-CONTRACT.md`（可选增强、非硬依赖）；调用侧仍应按「VLM 不可用可降级为纯 OCR」设计，避免把可选能力变成硬依赖。

## 7. 给其他角色的接口约定

- embedding 请求体：`{"model":"bge-m3","input": "单句" | ["句1","句2"], }`，`EMB_MAX_BATCH=64` 上限；
  响应 `{"object":"list","data":[{"object":"embedding","index":i,"embedding":[1024 floats]}],"model":"bge-m3","usage":{prompt_tokens,total_tokens}}`。
- rerank 请求体：`{"query":str,"documents":[str]|["{text}"]}` 或 `{"query":str,"texts":[str]}`，可选 `top_n`、`return_documents`；
  响应 `{"model":...,"results":[{"index":i,"relevance_score":f,"score":f}],"usage":{...}}`，**已按分数降序**；`index` 指向原始文档下标。
- LLM：标准 OpenAI `POST /v1/chat/completions`，`stream:true` 返回标准 SSE；`/v1/models` 返回 `qwen2.5-7b-instruct`；
  健康检查用 `/health`（llama.cpp 原生，返回 `{"status":"ok"}`）。
- VLM：`http://127.0.0.1:18093/v1/chat/completions`，model=`qwen2.5-vl-3b-instruct`，2 槽 × 16384（每槽私有），
  `content` 数组里放 `{"type":"text","text":...}` 与 `{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}`（png/jpeg 均可）。
  **客户端超时必须 ≥600s**（纯 CPU 且负载敏感：515 token 图约 20–30s，2700 token 扫描页 215–457s）。
  提问建议指向具体客户名/字段名，纯「第 N 行」容易串行。
  **页眉页脚 VLM 能逐字读对**（`docx-image.docx` 实测读出 `SCANNED PAGE - no text layer`），但批量抄写时若 `max_tokens` 不够，会先抄正文、把页眉挤掉 —— 属输出预算问题，不是识别盲区；需要页眉时请定向提问或加大 max_tokens。
  **并发建议 1**（实测并发 4 的吞吐只提升 1.08%，却把单请求延迟放大 4 倍）；并发上限按 §3.4 的 token 预算算。
  **调用侧必须保持一图一请求（parse 现状 `controller.py:160-201` 已如此，非违规）**；任何把多图拼进一个请求的批处理都不得用于逐字转录或证据提取
  （3 图单请求实测丢整图并虚构条目，详见 §3.4「能力边界」），只能用于整体摘要/分类。
  **分辨率没有通用安全阈值**，是否缩放须在真实扫描件上标定，见 §3.4「分辨率」小节。
- **重启约定**：18092/18093 的 down/up 演练会打断调用方（parse 侧 LLM 失败是异常冒泡→整篇 500）。重启前先通知 parse-ops。

## 8. 红线与安全边界（对外必须遵守，本节为可检索口径）

**R-1【逐字转录 / 证据提取必须一图一请求】**
同一请求内塞多张图会给模型制造"整图丢失 + 按模式补全虚构"的确定性错误（实测：3 图单请求丢整张英文页 140 token 内容，并虚构出不存在的「副本 3 / 客户 3 / 123 万」；`finish_reason=stop`、输出仅 57 token，已排除 max_tokens 截断）。
→ **多图拼接只能做整体摘要/分类；其结果不得作为证据链文本源**，不得写入 chunk、索引、检索语料或对外报告的证据字段。
→ 该错误"编号连续、格式规整"，人工抽检与常规字段校验均无法发现，且**重试/投票无效**（确定性行为）。

**R-1b【`finish_reason=='length'` 的输出不得并入正文】**
被截断的 VLM 输出是半句/残缺文本，混入 `page_content` 会污染正文（实测：`max_tokens=1` 时合并结果 347 字 OCR + **3 字残句** = 352 字）。
→ 截断即弃用该段 VLM 文本，或至少加显式分隔标记并在 chunk 元数据里带 `vlm_status='truncated'`；
→ **状态字段必须随 chunk 一起落库**（ES/Milvus payload），否则解析输出之后下游无从判断这段文字来源是否完整。
→ 落库实测（parse 侧 2026-10-25）：**ES 通道保留** `vlm_status / vlm_finish_reason / vlm_needs_crosscheck / vlm_prompt_n`（剔除 `boxes`/`base64` 后 count=2 成功）；
**Milvus 通道会按建表 schema 过滤掉未声明的 `vlm_*` 键** ⇒ **证据链校验以 ES 通道为准**，Milvus 只用于向量召回；若要两边一致，建议把 `vlm_*` 打包进 schema 里已存在的单个 VARCHAR（如 `meta_json`），避免每次加标记都改表。

**R-2【服务不得直接对外暴露】**
18092（LLM）、18093（VLM）、18090（embedding）、18091（rerank）**均未设 API key**，只监听 `127.0.0.1`。
llama-server 启动日志明确告警 `no API key is set and CORS allows all origins`。
→ **一律不得直接对外暴露或做端口映射**；前端与外部调用必须经 Java 网关（8088）/ 前端反代（18088）转发并在网关侧做鉴权与限流。
→ 不要用 `[::1]` 访问（只绑 IPv4 回环，会 connection refused）；显式写 `127.0.0.1`。

**R-3【私有资料不出网】**
transformers 以 `local_files_only=True` 加载，LLM/VLM 使用本地 GGUF；运行期采样 `ss -tanp` 三服务连接全部为回环，非回环连接 0。禁止把它们接到任何外部 API（含云端 LLM/embedding）。

**R-4【禁止假服务】**
不允许以"随机向量 / 固定文本 / mock 分支"替代真实推理；模型不可用时必须显式报错或在调用侧标记降级状态（如 `vlm_status='failed'`），并回落 OCR 等真实能力，**不得返回伪造结果**。

**R-5【不依赖中间件】**
本组四个服务不依赖 MySQL / Redis / Elasticsearch / MinIO / Milvus / Nacos，只依赖本地模型文件与 CPU/GPU。
→ ES 重启、Milvus 重建、Nacos 配置发布期间，模型服务无需停机，也不会因此失败。

## 9. 交付快照（2026-10-25 06:22）

| 服务 | 端口 | PID | 连续运行 | RSS | 状态 |
|---|---|---|---|---|---|
| embedding (bge-m3) | 18090 | 3356869 | 4h22m | 2.0G | UP |
| rerank (bge-reranker-v2-m3) | 18091 | 3356870 | 4h22m | 2.2G | UP |
| LLM (Qwen2.5-7B Q4_K_M) | 18092 | 3366947 | 4h20m | 2.3G | UP |
| VLM (Qwen2.5-VL-3B + mmproj) | 18093 | 4001031 | 2h06m | 7.2G | UP |

- GPU：5204 MiB / 6144 MiB（仅 7B 使用，`--n-gpu-layers 99`）；MemAvailable 6.4G（**无 swap**）
- 关键参数：18092 `--ctx-size 8192`；18093 `--parallel 2 --ctx-size 32768`（每槽私有 16384）、`--n-gpu-layers 0`
- 验证：`verify.py` ALL PASS（27 断言）、`verify_vl.py` ALL PASS、`bench_vl.py`（负载哨兵 + `cache_n` 校验）、`measure_window.py`（GO/NO-GO 闸门）
- 复跑一键：`platform/r12/models/start-all.sh {up|down|status|restart}`
- 注：PID 与 RSS 是**快照时点**，重启后会变；判定服务是否健康请用 `start-all.sh status` 或 `measure_window.py`，不要引用本节 PID。

## 10. 线程预算（结构性瓶颈，待 TL 裁定 A/B）

20 核机器上四个模型服务的**线程配额合计 68**，本身就过配；java index-service / gateway / parse 还要抢同一批核。

| 服务 | 当前配额 | 实测占用 | B 方案建议值 |
|---|---|---|---|
| VLM 18093 | `--threads 20` | **8.5–11.6 核**（有请求时） | 14 |
| embedding 18090 | `EMB_THREADS=20` | 0.5–1.5 核 | **6** |
| rerank 18091 | `RR_THREADS=20` | 0.4 核（**峰值 17.7 核**） | **6** |
| LLM 18092 | `--threads 8` | ≈0（GPU 全量 offload） | 8 |
| 合计 | **68** | — | **34** |

**后果（已实测）**：VLM 2 槽中一个做长 prefill 时，另一槽生成被饿到 **0.73 tok/s**（同请求 prefill 21.1 tok/s 正常）⇒ 容量测量必须等独占窗口，或先调配额。

**一键应用 B（已在 `start-all.sh` 中参数化，无需改代码）**：
```bash
cd platform/r12/models
EMB_THREADS=6 RR_THREADS=6 VL_THREADS=14 ./start-all.sh restart
```
**代价（估算，非实测）**：单条 embedding 查询 ~100ms → 250–300ms；VLM prompt eval 慢 ~1.2–1.4×。
**注意**：重启各服务 5–15s 不可用；**含 embedding 的链路（图片关联、落库向量化）耗时不可跨此变更横向比较**；功能正确性不受影响。
