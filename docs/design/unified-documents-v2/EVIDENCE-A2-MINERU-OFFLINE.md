# A2 离线交付：MinerU wheelhouse 与干净 venv 实测（2026-10-31）

上一轮 A2 的"安装"还依赖公网镜像。本轮把它做成**真正离线可装**并实测到解析出中文正文。
过程中踩了 4 个坑，全部是"装的时候不报、跑起来才炸"的类型。

## 交付物

| 项 | 值 |
|---|---|
| wheelhouse | `delivery/wheels-mineru-py311`：97 个 wheel / 376.5 MB |
| 清单 | `offline/r12-mineru-venv-py311.manifest.json`（逐文件 sha256） |
| 基础包 | 复用 `wheels-r12-parse`（554MB）+ `wheels-r12-models` 的 `torch-2.6.0+cpu` |
| 安装 | `scripts/install_mineru_parse.py --offline --wheel-dir ...`（新增离线参数） |

为什么 py311 而不是原来的 py310：**服务实际跑在 parse venv（3.11）**，
单独再维护一个 3.10 环境只是为了先前手工验证；交付要跟服务对齐。

## 实测（干净 venv，全程 `--no-index`）

```
python3.11 -m venv /tmp/offline-mineru
# 1) parse 基础包（153 包）
install_offline_bundle.py --manifest r12-parse-venv-py311.manifest.json
# 2) CPU torch（来自 models 包）
pip install --no-index --find-links wheels-r12-models torch==2.6.0+cpu
# 3) MinerU 依赖
install_mineru_parse.py --python /tmp/offline-mineru/bin/python --offline \
  --wheel-dir wheels-r12-parse --wheel-dir wheels-r12-models --wheel-dir wheels-mineru-py311
→ 9 步全 rc=0，imports.bad=[]，numpy 1.26.4 / pandas 2.0.3
```

适配器探针（同一 venv，`HF_HUB_OFFLINE=1`，权重走本地）：

```
{"status": "OK", "sdk": true, "docs": 1, "missing": [],
 "rows": [{"chars": 111, "type": "text", "title": "cn-scan.pdf",
           "page_number": [1], "has_position": true, "page_size": [[480.0, 201.6]]}]}
```

即：**离线装出来的环境，真的解析出了中文正文与 bbox**，不是 only-import-ok。

## 四个坑（都是运行时才炸）

**1. torchvision 必须与 torch 同为 `+cpu` 构建。**
wheelhouse 里的 `torchvision-0.21.0`（PyPI，cu124）配 `torch-2.6.0+cpu` 会报
`RuntimeError: operator torchvision::nms does not exist`——装得上、import 也过，
一旦 ultralytics 注册算子就炸。换成 `torchvision==0.21.0+cpu` 才对齐。

**2. 我用 `rm -f nvidia_*.whl` 把 `nvidia-ml-py` 一起删了。**
ultralytics 依赖它（纯 Python 小包），离线安装直接 `Could not find a version`。
教训：清理"大包"时不要用宽通配，要按 `nvidia_*cu12*` 这种精确模式。

**3. `omegaconf` 是运行时依赖，装包阶段不报。**
`magic-pdf` 的 OCR 子模块 `pytorchocr_utility.get_arch_config` 里才 `from omegaconf import OmegaConf`。
已加进 `STEPS`；这正是"import 自检要覆盖真实调用路径"的原因——只 import `magic_pdf` 发现不了。

**4. 离线装会动 parse 侧的既有依赖。**
实测被改动的：`httpx 0.23.0 → 0.28.1`、`pdfminer.six 20231228 → 20250506`、
`openai → 3.42.0`（pip 报 pdfplumber 的 pin 冲突）。当前 import 与探针都正常，
但 `openai 3.x` 与 magic-pdf 期望的 API 未必兼容——**这条只做了"能跑"，没做"长期兼容"验证**，
记在这里而不是当它不存在。

## 还没做

- **没验 openai 3.x 下 magic-pdf 的在线模式**（我们当前用 pipeline + 本地权重，不走 openai）；
- **没锁 parse 侧被顶掉的版本**（httpx/pdfminer/openai），要彻底干净应出一份联合约束文件；
- wheelhouse 与 parse 包有重叠文件（pip 会以 `--find-links` 顺序解析），未做去重；
- 未在**无外网机器**上验（本机装的时候虽然有网，但命令全程 `--no-index`，没有回退公网）；
- 权重（1.94GB）仍走 ModelScope 子集清单，未打进 wheelhouse（体积与更新频率都不合适）。
