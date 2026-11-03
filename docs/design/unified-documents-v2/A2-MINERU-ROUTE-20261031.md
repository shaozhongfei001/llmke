# A2：MinerU/OCR 路线可行性核实（2026-10-31）

本机实测，不臆断：

| 项 | 实测 | 结论 |
|---|---|---|
| `magic-pdf` 包 | 镜像可取得，最高 `1.3.12`（另有 1.x 全系） | **可装**，不是"包都没有" |
| 已装情况 | `platform/r12/venvs/alg`、系统 python3 均无 `magic_pdf`（解析服务启动日志亦确认） | 当前栈未启用 MinerU 路径 |
| GPU | `NVIDIA GeForce RTX 3060 Laptop GPU, 6144 MiB` | 够跑 OCR/VLM 小模型，大模型需限流 |
| HuggingFace | `https://huggingface.co` → `000`（不可达） | **官方默认权重下载路径不可用** |
| ModelScope | `https://modelscope.cn` → `302`（可达） | 权重可改从 ModelScope 取（MinerU/opendatalab 有镜像仓库） |

路线结论：

1. 扫描 PDF/图片的 OCR 路线**不以 magic_pdf 为唯一出口**，但 MinerU 仍是结构还原的首选；
   包可装、GPU 够、权重须走 ModelScope（HF 不可达）。
2. 该路线**只影响扫描件与复杂版面**，不阻塞原生 Office（docx/xlsx 的表格结构已由
   doc2md 原生读取器产出，见 `EVIDENCE-VL1-REAL-UPSTREAM-20261030.md`）。
3. 下一步（未做）：在独立 venv 装 `magic-pdf==1.3.12`，从 ModelScope 拉权重，
   对 `platform/r12/parse/fixtures/generated` 里的扫描件跑一次真实解析，登记耗时与显存峰值；
   装不上或权重不可得时，按"具体资源/兼容问题"分类，不笼统转交。
