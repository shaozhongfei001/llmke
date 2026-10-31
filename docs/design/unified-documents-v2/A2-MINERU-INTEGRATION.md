# A2 MinerU 接进平台解析服务：已验证的依赖面与配置面

日期：2026-10-31。范围：只做"平台适配器 `deepdoc.parser.MinerUParser` 真跑通"，
不涉及线上 `use-mineru` 开关切换。

## 1. 结论

平台适配器本身**没问题**：用真实扫描件跑出 1 个 `ParsedText`，`page_content` 含完整中文正文，
`metadata` 带 `type=text / title / page_number=[1] / page_size=[[480,201.6]] / position`（真实 bbox）。

真正的工作量全在**依赖面**：`pip install "magic-pdf[core]"` 不足以让适配器跑起来，
还差 7 个模块级导入依赖，且装它们会反复把 numpy 顶到 2.x。

## 2. 缺的 7 项（按踩坑顺序）

| # | 报错 | 处理 |
|---|---|---|
| 1 | `No module named 'pycocotools'` | `pip install pycocotools` |
| 2 | `No module named 'ultralytics'` | `pip install ultralytics` |
| 3 | `No module named 'doclayout_yolo'` | `pip install doclayout-yolo` |
| 4 | `No module named 'rapid_table'` | `pip install rapid-table` |
| 5 | `UnpicklingError: Weights only load failed`（torch≥2.6 默认 `weights_only=True`） | 环境变量 `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1`（不改上游代码） |
| 6 | `No module named 'dill'`（ckpt 里用 dill 序列化） | `pip install dill` |
| 7 | `No module named 'openai'`（`post_proc/llm_aided.py` 模块级导入） | `pip install openai` |

**反复出现的 ABI 冲突**：装 ultralytics / doclayout-yolo 会拉 numpy 2.x，导致
`pandas._libs` 报 `numpy.dtype size changed`。每次装完必须
`pip install "numpy==1.26.4"` 回锁。这是"加 MinerU 就崩检索侧"的真实原因，
不能靠一次 `pip install` 解决，必须写进部署脚本的顺序里。

## 3. 配置面

1. `mineru` 段必须出现在解析服务的 nacos 配置里，否则
   `lazy_parse` 直接 `KeyError: 'mineru'`。用到的键：`build-in`、`backend`、`version`、`endpoint`。
   仓内模板已补（`platform/r12/nacos/alg_doc_config_py.yaml`），**`use-mineru` 仍为 false**。
2. `MINERU_TOOLS_CONFIG_JSON` 指向 `magic-pdf.json`（模型目录 + layout/公式/表格开关 + layoutreader 目录）。
3. `HF_HUB_OFFLINE=1`：本机 huggingface.co 不可达，必须离线。
4. `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1`（见上表 #5）。

## 4. 复现命令

```bash
# 平台适配器（验证字段映射）
python scripts/v2_mineru_adapter_probe.py \
  --pdf platform/r12/parse/fixtures/generated/cn-scan.pdf \
  --expect "授信审批意见通知书" "SPDB-2026-PJ-00871"
# -> {"status":"OK","docs":1,"rows":[{"chars":111,"type":"text","page_number":[1],"has_position":true,...}]}
```

探针用测试 data-id `alg_doc_config_py_v2test`（在本地 nacos 上带 `mineru` 段的一份拷贝），
**不动线上 `alg_doc_config_py`**。

两个脚本的分工：
- `v2_mineru_smoke.py`：走上游 CLI，只验模型链路；
- `v2_mineru_adapter_probe.py`：走平台适配器，验 `ParsedText` 字段。

## 5. 还没做（不许当成已具备）

- **未写进 parse venv 的部署脚本**：现在是一次性手工装（`/home/szf/data/dev/parse-v2-venv`）。
  要进交付必须把这 7 步固化成幂等安装脚本 + wheelhouse（含 numpy 回锁顺序）。
- **`use-mineru` 未开**：切换需要重启解析服务，会打断当前在跑的环境；且要确认 OCR 质量与耗时。
- **doc/docx 走 MinerU 会调 `convert_file_to_pdf`**，同样依赖 LibreOffice；本机缺 writer（D-01），
  这条路径对 Office 文件仍不可用——MinerU 目前只对 PDF/图片成立。
- 公式识别关闭（MFR 需 HF 远程代码）；表格结构模型未装。
