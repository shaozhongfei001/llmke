# A2 MinerU/OCR 真实跑通证据（2026-10-31）

目标：把"扫描件/复杂版面"这条路线从"看起来可用"变成"本机真跑出结果"，并记下所有踩到的真实阻断。

## 结论先说

- `magic-pdf==1.3.12` **能在本机装成并在 CPU 上跑通扫描件**，中文正文与金额数字都正确提取；
- 但上游 `[full]` extra **不完整**，且**三处默认行为会去连 huggingface.co**（本机不可达），
  必须逐项改成"本地权重 + 关闭模型"才跑得起来；
- GPU 路径当前**不可用**：torch（cu126 构建）要求驱动 ≥ 12.6，本机是 12.5。

## 实测命令与结果

```
magic-pdf -p fixtures/generated/cn-scan.pdf -o /tmp/mineru-out5 -m ocr
Layout Predict 1.81s → OCR-det 5.33it/s → OCR-rec 19/19 → 输出 md / content_list / middle json
```

提取结果（`cn-scan.md`）：

```
附件三： 授信审批意见通知书
客户名称： 上海浦东发展集团有限公司
授信金额： 人民币 5000 万元
审批结论： 同意， 期限 12 个月
签发日期： 2026年10月20日
编号： SPDB-2026-PJ-00871
```

## 权重来源与体积（ModelScope，HF 不可达）

`scripts/fetch_mineru_weights.py --preset scanned-cn`，仓库 `opendatalab/PDF-Extract-Kit-1.0`：

| 子集 | 体积 |
|---|---|
| `models/Layout/YOLO`（版面，doclayout_yolo） | 129 MB（3 个 pt） |
| `models/MFD/YOLO`（公式检测） | 334 MB |
| `models/MFR/unimernet_hf_small_2503`（公式识别） | 810 MB |
| `models/ReadingOrder/layout_reader`（阅读顺序） | 680 MB |
| `models/OCR/paddleocr_torch`（中文 det/rec） | 71 MB |
| 合计 | **1.94 GB / 17 文件** |

清单入库：`docs/design/unified-documents-v2/offline/mineru-weights.manifest.json`（逐文件 sha256）。

## 五个真实阻断（都已处理，全部写进脚本/文档，不做隐式绕过）

1. **`[full]` 缺 `pycocotools`**：layoutlmv3 的 visualizer 需要它，装 `magic-pdf[full]` 后仍报
   `ModuleNotFoundError: pycocotools`。
2. **`layoutlmv3` 需要 `detectron2`**（PyPI 无预编译包）。改走 `layout-config.model=doclayout_yolo`
   （YOLO 版版面模型）绕开，代价是多下一份 129 MB 权重。
3. **`mfr_model` 默认值是 HF 格式**（`unimernet_hf_small_2503`），`from_pretrained` 会去连 HF；
   本机 HF 返回 000。处理：先尝试关闭公式识别（`formula-config.enable=false`）。
   代价是**公式不识别**，正文不受影响。
4. **阅读顺序模型默认从 HF 拉 `hantian/layoutreader`**，报
   `LocalEntryNotFoundError ... OfflineModeIsEnabled`。处理：加 `layoutreader-model-dir`
   指向本地 `models/ReadingOrder/layout_reader`。
5. **OCR 检测模型文件名对不上**：`models_config.yml` 的 `ch_lite` 要 `ch_PP-OCRv3_det_infer.pth`，
   而公开 kit 仓只剩 v4/v5/v6 命名。处理：把 `Multilingual_PP-OCRv3_det_infer.pth` 复制成
   `ch_PP-OCRv3_det_infer.pth`。**这是替代不是原版对齐**，需要用真实中文扫描件回归比对；
   已在此标注，不允许当成"官方权重已就位"。

## GPU 现状（不是配置问题）

```
RuntimeError: The NVIDIA driver on your system is too old (found version 12050).
```

torch 是 cu126 构建，驱动 12.5 不够。要么把 torch 换 cu121 构建，要么维持 CPU。
CPU 单页扫描件 ~10 s（Layout 1.8s + OCR 1.3s），一页量级可接受；批量要看页数。

## 配置文件（可复制）

```json
{
  "models-dir": "/home/szf/data/dev/models/mineru/models",
  "device-mode": "cpu",
  "layout-config": {"model": "doclayout_yolo"},
  "formula-config": {"mfd_model": "yolo_v8_mfd", "mfr_model": "unimernet_small", "enable": false},
  "table-config": {"model": "rapid_table", "sub_model": "slanet_plus", "enable": false, "max_time": 400},
  "layoutreader-model-dir": "/home/szf/data/dev/models/mineru/models/ReadingOrder/layout_reader"
}
```

## 尚未做

- **接入平台解析服务**：`alg_doc_parse_service` 里还没有 mineru 适配器分支，上面是独立 CLI 跑通；
- **公式识别**：需要 MFR 的本地加载方式（HF 远程代码不可用），或换非 HF 的 `unimernet`（.pth）分支；
- **表格结构**（`struct_eqtable` 1.8 GB）未下、未验；
- 中文 OCR 的 det 权重替代件未做质量回归（只看了一页样例）。


## 可复现的冒烟入口（已入库）

```bash
MINERU_TOOLS_CONFIG_JSON=/path/magic-pdf.json HF_HUB_OFFLINE=1 \
  /path/mineru-venv/bin/python scripts/v2_mineru_smoke.py \
  --pdf platform/r12/parse/fixtures/generated/cn-scan.pdf \
  --expect "授信审批意见通知书" "5000 万元"
# -> {"status":"OK","chars":121,"missing":[]}
```

`tests/test_mineru_smoke.py`：
- 无 CLI → `NO_MINERU_CLI`；无配置 → `NO_CONFIG_ENV`（这两项在任何环境都跑，防止"没装却报通过"）；
- 真实 OCR 项在缺环境时 **skip**，本机实跑通过（3 passed）。

**为什么不直接 import 平台 `MinerUParser`**：它连带 `deepdoc.parser.__init__` 的一串云厂商 SDK
（ali/textin/…），在没有完整 parse venv 的环境里 import 不进去（实测卡在
`alibabacloud_docmind_api20220711`）。适配器接缝留给"部署进 parse venv 后再验"，
不当成已验证。
