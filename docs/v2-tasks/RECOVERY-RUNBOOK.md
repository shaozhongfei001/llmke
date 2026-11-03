# 服务恢复后一次性执行清单（冻结基线 135e93d，2026-11-03）

> 前提：18094/8088/18083/19532/19531/19669(Nebula) 全部恢复（当前仅 18088 在听，已实测）。
> 本清单 = 服务恢复后的全部真机验证，按顺序执行，每步留证据到 `docs/v2-tasks/evidence/`。

## 0. 基线

- HEAD：`135e93d`（工作树干净）；图引擎全套回归 **123 passed**（10 文件，含 B01 28 项）。

## 1. 起服务（按 ENV.md）

1. 18094 图服务（hipporag venv，默认装中文补丁，health 看 `cjk_compat.installed=true`）；
2. 19531 legacy_shim（构建兼容层）、19532 retrieval_shim（问答/global）；
3. 8088 网关、18083 rag-qa-service（v2 jar）、18095 预览服务（preview/run.sh up）；
4. 前端：18088 nginx 挂 `llmke-v2/frontend/plateform/dist`（最新构建）。

## 2. 自动验证：`scripts/v2_live_verify.sh`

覆盖：D6 A/B（seeds+无兜底 / 禁用对照）、D0 `/v2/graph/view`、D9 health.cjk_compat、
shim global 未命中分层（200+reason）。**全部 PASS 才继续**；FAIL 逐条定位修复并重跑。

## 3. 页面级联调（agent-browser，真实点击）

1. 图谱增强页：GraphBox 顶栏 LifecycleBar（httpAdapter 取 `/v2/status`）、库级图（GraphCanvas →
   `/proxy/graph/search/v2WholeGraph`）、Tab4 global（社区报告徽标）；Tab2/Tab5 接 `/v2/entities`/`/v2/status`
   （需网关映射或 dev 直连 18094 + CORS）。
2. 引用链路：提问 → 知识溯源 → 抽屉 → 预览打开 → **locator 高亮**（T-A5 真机验证；若矩形未落在
   正确文字上，校准 `citationHighlight.ts` 的坐标口径）。
3. 撤权：`GET /v2/fence` 可见；撤权后查询不含该文件内容（D8）。

## 4. D10 语料固化（真实上传文档）

- 语料：kb_9 id=333 `docx-table.docx`（已解析）、kb_1002 `999017 docx-plain.docx`（已上传/建图）+
  补齐至少 2 份新上传（覆盖表格/数值/方向类）；
- 用 `tests/fixtures/d10_spec.json` 的 9 条问句逐条跑 A/B（`enable_graph=true/false`），
  输出按 `d10_eval.evaluate_all` 入参格式落盘 `docs/v2-tasks/evidence/d10-run.json`；
- 语义层交 M4 盲审 + 用户抽查（本会话不自评）。

## 5. T-B2（需授权）

- Nebula 19669 在跑但缺 nebula3 客户端：装客户端后按 A4 §5.4 先只读取证存量 `g_kb_9` 边数与反向对，
  再评估清库重建（写入冻结 → 快照 → DROP SPACE → 重建 → 校验），**未经用户批准不执行清库**。

## 6. 出下一评审包

- `git status` 干净后按上一轮口径打离线包（01 全量树 + 02 diff + 证据 + Q JSON），交评审会话复核。
