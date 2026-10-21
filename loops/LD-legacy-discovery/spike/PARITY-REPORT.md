# 回放对比：切断服务层耦合前 vs 后

- 原始模块：`…/alg_doc_parse_service`（完整路径由运行参数给出，不入库）
- 改写文件数：**14**（`server.*` → `_shims.*`）
- 生成桩：lazy parser/__init__ replaced; shims: config.py, errors.py, model.py, progress.py, runtime.py
- 样本数：5；**逐字段一致：5**；不一致：0；不完整：0

| 样本 | 大小 | 臂A 块数 | 臂B 块数 | 结论 | 备注 |
|---|---|---|---|---|---|
| `sample-docx-textonly.docx` | 37081 | 6 | 6 | **IDENTICAL** |  |
| `sample-m0.docx` | 41794 | 95 | 95 | **IDENTICAL** |  |
| `sample-m1.docx` | 31365 | 71 | 71 | **IDENTICAL** |  |
| `sample.html` | 110 | 1 | 1 | **IDENTICAL** |  |
| `sample.txt` | 143 | 4 | 4 | **IDENTICAL** |  |

## 两臂实际解析到的源码路径（防止臂 A 被臂 B 顶替）

| 样本 | 臂A 解析器文件 | 臂B 解析器文件 |
|---|---|---|
| `sample-docx-textonly.docx` | `…/deepdoc/parser/docx_parser.py` | `…/deepdoc/parser/docx_parser.py` |
| `sample-m0.docx` | `…/deepdoc/parser/docx_parser.py` | `…/deepdoc/parser/docx_parser.py` |
| `sample-m1.docx` | `…/deepdoc/parser/docx_parser.py` | `…/deepdoc/parser/docx_parser.py` |
| `sample.html` | `…/deepdoc/parser/html_parser.py` | `…/deepdoc/parser/html_parser.py` |
| `sample.txt` | `…/deepdoc/parser/txt_parser.py` | `…/deepdoc/parser/txt_parser.py` |

## 运行期桩统计（量化导入期耦合）

| 样本 | 臂A 需要桩的模块数 | 臂B 需要桩的模块数 |
|---|---|---|
| `sample-docx-textonly.docx` | 21 | 21 |
| `sample-m0.docx` | 21 | 21 |
| `sample-m1.docx` | 21 | 21 |
| `sample.html` | 0 | 0 |
| `sample.txt` | 0 | 0 |
