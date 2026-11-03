# D9：HippoRAG 升级重验流程（交付/升级固定步骤）

- 补丁默认安装：`graph_engine_adapter/api.py` 的 `_ensure_cjk_compat()`（`LLMKE_V2_CJK_COMPAT=0` 可关，仅对照用）；
  安装状态在 `GET /health` 的 `cjk_compat` 字段可见。
- **升级 HippoRAG 后必须执行**（不通过不得继续上线）：

```bash
cd /home/szf/data/dev/llmke-v2
/home/szf/data/dev/hipporag-toolenv/bin/python scripts/v2_cjk_revalidate.py
```

- 判据：上游 text_processing 行为记录在案；补丁可安装；补丁后中文保留、ASCII 路径不变；exit 0 才算 PASS。
- 实测（2026-11-03）：上游 `text_processing('智造贷 AAA档 5000万元') -> 'aaa  5000'`（中文被清空）；
  补丁后 `-> '智造贷 aaa档 5000万元'`，PASS。
