# D10 验收：固定语料与分档（2026-11-03）

## 结构层（本机可核，已落地）

- `graph_engine_adapter/d10_eval.py`：T-01…T-09 结构判据（答案非空、引用非空、每条引用有 locator、
  路线 ∈ {GRAPH, COMMUNITY_REPORT, DENSE_FALLBACK}、回退必带原因、禁用对照 B 组显式 DENSE_FALLBACK）；
- 用例规格 `tests/fixtures/d10_spec.json`（9 条，含各自注记）；
- 语义层（答案对不对）不在本模块：由 M4 盲审 + 用户抽查按同一份 spec 判，不冒充。

## 分档（Q 验收口径）

| 档 | 内容 | 可否离线 |
|---|---|---|
| 离线可复现 | 单测/评估器/合同/静态证据（本机 pytest） | 是 |
| 需服务 | 真机 A/B、视图、global 分层（scripts/v2_live_verify.sh） | 否 |
| 需模型 | 业务问答语义、global 答案质量（需 DSEEK key） | 否 |

## 缺口（如实）

- 语料未固化：spec 已声明“须以真实上传文档（数字 file_id）重建快照后固化”，F 夹具不满足；
- 9 条用例尚未在真实环境跑过（服务/模型未恢复）。
