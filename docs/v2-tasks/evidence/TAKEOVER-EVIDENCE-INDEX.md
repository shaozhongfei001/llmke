# 接管期真机证据索引（供 M4 盲审包引用）

> 汇总本会话接管（round 4 起）到当前的全部可复核证据；每条=命令+输出+路径。

## 代码级（离线可复现）

- 图引擎全套回归：`123+ passed`（10 文件，含 B01 28 项；历轮 pytest 输出见各轮计划文档）
- B01 落地：`docs/v2-tasks/evidence/B1-landed.md`
- D8 CAS/fence：`tests/test_d8_fence_cas.py`
- D10 结构层：`tests/test_d10_eval.py` + `tests/fixtures/d10_spec.json`
- D9 重验：`scripts/v2_cjk_revalidate.py`（实测 PASS：上游清中文→补丁保留中文）

## 真机（自起 18094/19532，验证后均停止并释放端口）

- `docs/v2-tasks/evidence/LIVE-VERIFY-20261103.md`：D6-B/D0/D9/shim 分层 4 PASS；
  D6-A 首测 FAIL 根因=存量快照（补丁前），**新鲜构建已复验成立**（见下）。
- D10 首次真实上传文档语料（kb_9 id=333 产品解析块）：
  `docs/v2-tasks/evidence/d10-run-T02-real-corpus.json`：
  - D6-A：GRAPH/graph_calls=1/seed_hits=["日均存款"](seeds_source=auto)/rerank_fallback=false/facts_after_rerank=1；
  - global：READY，两条正确事实带（来源：333），另有 2 条抽取噪声（如实记录）；
  - d10_eval：T-02 检索链路与 global 结构判定 PASS。
- 补充真机（r20 快照）：D3 稳定性 STABLE（top1=1.0）；D0 view 11 节点/23 边+file_index；
  D4 entities 9 实体（修复回退 bug 后复验）；D8 fence 端点形状正常。

## 前端

- dist 重建成功：`✓ built in 3m 21s`，0 error（含 GraphCanvas subGraph/mockAdapter httpAdapter/
  DrawerPreview 高亮等接管期改动）。
- 页面级联调仍待 8088/18083 恢复（runbook 第 3 步）。

## 独立评审（M4 盲审）

- `docs/v2-tasks/evidence/M4-blind-review-20261103.json`：qwen-max 两轮——首轮 11 条
  7 supported/4 overstated（措辞问题），改写复核 4/4 not overstated；
  最终口径：D0/D9 成立，其余“代码级落地、验收未达”。

## 交付准备

- `docs/v2-tasks/P4-PUSH-CHECKLIST.md`：推送/合并确认清单（未经用户同意不 push/merge）。
- `scripts/v2_make_review_pkg.sh`：评审包打包脚本（dry-run 01=9911 文件/02=446 文件）。

## 尚未成立（如实）

- 页面级点引用高亮渲染（T-A5/D7b）真机未验；D10 其余 8 问句未跑；语义质量未评（M4/用户）；
  存量 Nebula 清库（T-B2）未做；推送/合并待用户确认。
