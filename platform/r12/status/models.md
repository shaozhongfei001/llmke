# R12 模型与制品服务状态（model-ops 交付）

更新时间：2026-10-25　执行角色：model-ops（模型与制品）
依据：`platform/r12/R12-ENV-CONTRACT.md` v12.1。18090/18091/18092 与契约完全一致；**18093（VLM）为契约外新增**（原因与实测见 §6.8，待 TL 裁定是否纳入契约）
结论：**四个服务全部真实可用**——`models/verify.py` 27/27 PASS（18090/18091/18092）、`models/verify_vl.py` 全 PASS（18093），均退出码 0

---

## 1. 服务总览

| 服务 | 端点 | 模型 | 设备 | 状态 |
|---|---|---|---|---|
| embedding | `http://127.0.0.1:18090/v1/embeddings` | `BAAI/bge-m3` (1024 维) | CPU 20 线程 | UP |
| rerank | `http://127.0.0.1:18091/v1/rerank` | `BAAI/bge-reranker-v2-m3` | CPU 20 线程 | UP |
| LLM | `http://127.0.0.1:18092/v1/chat/completions` | `Qwen2.5-7B-Instruct Q4_K_M` (GGUF) | CUDA0 RTX 3060 Laptop，33/33 层全量 offload | UP |
| VLM（契约外新增） | `http://127.0.0.1:18093/v1/chat/completions` | `Qwen2.5-VL-3B-Instruct Q4_K_M` + mmproj-f16 | CPU 20 线程 | UP |

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

### 3.4 VLM（18093，契约外新增）
| 指标 | 实测值 |
|---|---|
| 模型 | `Qwen2.5-VL-3B-Instruct-Q4_K_M` + `mmproj-f16`（llama.cpp mtmd） |
| 上下文 | **16384**（02:35 → 8192；03:20 → 16384，为多图整页扫描件留 KV 余量） |
| 图片编码（视觉塔，纯 CPU） | **约 16–26s / 张**（900×420 PNG，约 518 image tokens）；**负载敏感**：load≈25 时同图单次实测 111.5s（≈7×），parse 侧另测到 0.28 tok/s 的极端值 → **高负载按 ≥10× 余量估算** |
| 图片 token 公式（实测拟合） | `tokens ≈ (W/28) × (H/28)` —— 900×420→518、1600×747→1570、2048×956→2513、2048×1800→4111，全部吻合 |
| 大图实测 | 2048×1800 JPEG → prompt 4111 tokens，**239.3s**，答案仍正确（`对公客户存款与授信情况表`）——4111 token 已超过旧配置 ctx 4096（现在是 16384） |
| 格式支持 | PNG 与 JPEG 的 `data:image/{png,jpeg};base64,...` 均实测可用 |
| mime 校验 | 不校验：把 PNG 字节声明成 `image/jpeg` 仍能正确识别（按字节嗅探），parse 侧硬编码 jpeg 不是问题 |
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

**并发与共享 KV 预算（`kv_unified=true` ⇒ ctx 是 4 个槽的共享池，不是每人一份）**

ctx 于 **03:20 从 8192 提到 16384**（原因见本段下方「能力边界」与预算实测）。下表把 8192 与 16384 两轮实测并列，样本是 parse 侧真实 fixture（`platform/r12/parse/fixtures/generated/docx-{2,3}images.docx` 内嵌的 1240×1754 PNG，2728 token/张）：

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
2. **安全水位取 ctx 的 ≤60%**，且必须另留 `max_tokens`。按 60% 反推：每图 T 个 token 时 `N = floor(0.6*ctx - max_tokens) / T`。
   16384 下 T≈2728（整页扫描件）→ **N≤3**（实测 3 图 8355 通过）；T≈500 → N≤8（受 n_slots=4 限制，即 4）。
3. **并发几乎不换吞吐**（1.08×），只放大延迟 → **推荐并发 1**；「单请求内含 2–3 图」比「2–3 个并发请求」安全（前者 KV 连续、后者碎片化）。
4. **失败形态是硬 500 而非降级**，parse 侧 LLM 失败会异常冒泡成整篇 500，所以宁可按低水位配置。
5. ctx 提到 16384 的代价是内存：VLM RSS 起步 **3.9G**，跑过一轮多图任务后峰值到 **7.7G**（KV + 计算/批缓冲，纯 RAM，不占显存）。
   **这已经到上限**：本机 available 一度只有 7G，因此**不要再往上加 ctx**（16384 已能覆盖 3 图 8355 token，占 51%）；若要跑更多图请改为多请求串行。
6. 注意 `verify_vl.py` 打印的耗时是**缓存热值**（实测 25.5s / 1.14s / 6.2s，因为是脚本内复用的同一张图），**不可当作性能指标**；
   冷启动/首次请求的真实值见 §3.4（20–457s，随图大小与负载变化）。

**延迟评估方法（缓存陷阱，必读）**
llama-server 会缓存「相同图片 + 相同 prompt 前缀」的计算结果：同一张图同一问题，**首次 38.1s / 111.5s，第二次仅 0.7s / 2.0s**（我在 4 并发实验里也复现了这个假象，一度误判并发有 2.35× 收益）。
因此：①**报延迟只认首次请求**；②**每次测量必须换新图片**；③不要用重复请求评估吞吐。

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
# vlm（契约外新增，纯 CPU）
platform/r12/models/llama.cpp/build/bin/llama-server \
  --model platform/r12/models/gguf-vl/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf \
  --mmproj platform/r12/models/gguf-vl/mmproj-Qwen2.5-VL-3B-Instruct-f16.gguf \
  --alias qwen2.5-vl-3b-instruct --host 127.0.0.1 --port 18093 \
  --ctx-size 16384 --n-gpu-layers 0 --threads 20 --no-mmproj-offload --jinja --no-webui
```

可调环境变量：`EMB_DEVICE/EMB_THREADS/EMB_MAX_BATCH/EMB_MAX_LEN`、`RR_BATCH/RR_MAX_LEN/RR_THREADS`、`LLM_NGL/LLM_CTX/LLM_THREADS/GGUF_PATH`、`VL_NGL/VL_CTX/VL_THREADS/VL_MMPROJ_OFFLOAD/VL_IMAGE_MAX_TOKENS/VL_MODEL_PATH/VL_MMPROJ_PATH`。

## 5. 验证方式（可复跑）

```bash
cd platform/r12/models && ../venvs/models/bin/python verify.py      # 18090/18091/18092 期望 RESULT: ALL PASS
cd platform/r12/models && ../venvs/models/bin/python verify_vl.py   # 18093（先跑 make_test_image.py 生成图）
```
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
3. **llama-server 未设 API key**（日志有 `no API key is set and CORS allows all origins` 告警）。
   服务只监听 `127.0.0.1`，仅本机可访问；网关侧（18088/8088）如要暴露必须自行加鉴权，**不能直接把 18092 对外**。
4. **不出网**：transformers `local_files_only=True`，llama-server 纯本地 GGUF。运行期采样 `ss -tanp`：
   三个服务的连接**全部为 127.0.0.1 回环**，非回环连接数 0（排除的其他监听端口 8106/12340 属既有进程，非本批次服务）。
5. **下载来源**：pypi/github 直连不可用或极慢（github ~60KB/s）；已按 TL 指定走阿里云镜像与 `hf-mirror.com`。
   llama.cpp 源码改从 `llama_cpp_python-0.3.36` sdist（76MB，内置 `vendor/llama.cpp`）取得，版本等价于上游 0.5.0-dev。
6. **rerank 长文档吞吐偏低**（5.1 doc/s，CPU fp32、512 token）。若整链路压测不够，优先调 `RR_BATCH=32` 或缩短 `RR_MAX_LEN=256`；
   不建议上 GPU（见限制 1）。
7. `models/bge-m3/onnx/` 已删除（2.2G 重复制品，服务走 PyTorch 路径）；如需 onnxruntime 方案需重新下载。
8. **VLM 只能跑 CPU，且是契约外新增端口 18093**。为解 parse 侧「文档内图片理解」的阻塞（18092 是纯文本 7B，无视觉），
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
     16384 下整页扫描件（≈2728 token/张）**N≤3**（实测 3 图 8355 token 通过）；但吞吐上并发无收益，**运行时仍按 N=1**。
     parse 的 `run_in_thread_pool`（controller.py:194）默认 32 并发线程池仍是风险点，需其调用侧自限。
   - **并发不带来吞吐**（实测 1.08×），推荐值为 1 —— 并发只会放大延迟。
   - **不建议一刀切缩放图片**：parse 的真实 A4 小字扫描页压到长边 1024 后模型判定「无文字」（连跑 3 次），768 丢页眉；
     而我用合成小字页在 1024 下仍可读。差异来自「有效字形像素高度 + 扫描噪声」，只能拿真实扫描件集标定，不能写成通用阈值。
   - **页眉页脚不是盲区**（03:40 更正）：真实 fixture 上 VLM 逐字读出 `SCANNED PAGE - no text layer`；
     先前的"漏读"是我的合成图 + `max_tokens` 截断造成的假象，不据此立缺陷。
   - 18093 未写入 `R12-ENV-CONTRACT.md`，已同步 TL；若 TL 不采纳，删掉该服务即可，不影响 18090/18091/18092。

## 7. 给其他角色的接口约定

- embedding 请求体：`{"model":"bge-m3","input": "单句" | ["句1","句2"], }`，`EMB_MAX_BATCH=64` 上限；
  响应 `{"object":"list","data":[{"object":"embedding","index":i,"embedding":[1024 floats]}],"model":"bge-m3","usage":{prompt_tokens,total_tokens}}`。
- rerank 请求体：`{"query":str,"documents":[str]|["{text}"]}` 或 `{"query":str,"texts":[str]}`，可选 `top_n`、`return_documents`；
  响应 `{"model":...,"results":[{"index":i,"relevance_score":f,"score":f}],"usage":{...}}`，**已按分数降序**；`index` 指向原始文档下标。
- LLM：标准 OpenAI `POST /v1/chat/completions`，`stream:true` 返回标准 SSE；`/v1/models` 返回 `qwen2.5-7b-instruct`；
  健康检查用 `/health`（llama.cpp 原生，返回 `{"status":"ok"}`）。
- VLM：`http://127.0.0.1:18093/v1/chat/completions`，model=`qwen2.5-vl-3b-instruct`，ctx=16384，
  `content` 数组里放 `{"type":"text","text":...}` 与 `{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}`（png/jpeg 均可）。
  **客户端超时必须 ≥600s**（纯 CPU 且负载敏感：515 token 图约 20–30s，2700 token 扫描页 215–457s）。
  提问建议指向具体客户名/字段名，纯「第 N 行」容易串行。
  **页眉页脚 VLM 能逐字读对**（`docx-image.docx` 实测读出 `SCANNED PAGE - no text layer`），但批量抄写时若 `max_tokens` 不够，会先抄正文、把页眉挤掉 —— 属输出预算问题，不是识别盲区；需要页眉时请定向提问或加大 max_tokens。
  **并发建议 1**（实测并发 4 的吞吐只提升 1.08%，却把单请求延迟放大 4 倍）；并发上限按 §3.4 的 token 预算算。
  **调用侧必须保持一图一请求（parse 现状 `controller.py:160-201` 已如此，非违规）**；任何把多图拼进一个请求的批处理都不得用于逐字转录或证据提取
  （3 图单请求实测丢整图并虚构条目，详见 §3.4「能力边界」），只能用于整体摘要/分类。
  **分辨率没有通用安全阈值**，是否缩放须在真实扫描件上标定，见 §3.4「分辨率」小节。
- **重启约定**：18092/18093 的 down/up 演练会打断调用方（parse 侧 LLM 失败是异常冒泡→整篇 500）。重启前先通知 parse-ops。
