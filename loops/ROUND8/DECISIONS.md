# ROUND8 决策记录

## D1 采用独立 worktree 而非原分支
- 原因：r5 候选证据绑定原工作树的文件内容；在原树写代码会让 r5 立即 STALE，而 r5 正等 QA 签署。
- 做法：`git worktree add ../llmke-r8 -b round8/delivery HEAD`，所有实现落在独立树。
- 结果：原树 `evidence-check --loop r5` 仍 PASS；main 未动。

## D2 选择「引用证据组装器」作为最小纵向切片
- 判据：① 输入输出由冻结契约强约束（`Evidence/DocumentEvidence/SourceRef/Offset`）；
  ② 不依赖未决 DDL、权限策略或容量阈值；③ 可在本地端到端跑；④ 对 L1 有真实复用价值。
- 拒绝的候选：PDF 解析（两臂不可运行）、接口迁移（需运行时证据）、索引代次（需四套存储）。

## D3 不做 555 行的批量 AI 建议（本轮）
- 原因：无明确建议口径时批量贴标签，会把"推断"包装成"建议"，与项目纪律冲突。
- 处理：登记为 BLOCKED_EXTERNAL，需先定口径（见 WORK-LEDGER R8-T03）。

## D4 未改任何门禁与 P0 状态

## D5 自纠：NEXT-SESSION.md 触犯「宿主绝对路径」规则
- 现象：`security-check` 报 5 处 `PERSONAL_ABSOLUTE_PATH`，全部在本轮新写的续跑文件里。
- 处理：改为 `~/` 写法；重跑门禁确认通过。
- 教训：门禁对"文档"同样生效，续跑文件也必须遵守产物规范。

## D6 入口脚本必须识别工作树（否则会"跑错地方还显示绿"）
- 现象：在 `llmke-r8` 里直接 `make framework-verify` 失败（`openapi_spec_validator` 缺失，
  R-02 的 conda 解释器问题）；而 `coordination/mk.sh` 旧版固定 `cd` 到 `llmke` 主库，
  在 r8 调用会静默跑成主库的门禁。
- 处置：`mk.sh` 与 `verify-all.sh` 改为「优先用当前目录（须含 Makefile + scripts/loop_guard.py + VERSION），
  否则回退主库」，并把 `root=` 打到 stderr，避免跑错地方。
- 复验：在 r8 执行 `mk.sh framework-verify` → exit 0 / 145 passed（`[mk] root=.../llmke-r8`）。

## D7 r8 的代码新增不会让 r5 证据失效（P-03 的实际效果）
- 事实：在 r8 工作树执行 `verify-all.sh`，`evidence-check --loop L0-contract-baseline-r5` 仍 PASS。
- 原因：`digest_scheme=2` 只绑 `control_digest`（契约/策略/门禁），`modules/` 属业务代码不在控制面；
  `doc_digest` 仅对 `traceability_gate` 生效。
- 含义：开发期新增业务代码不会反复作废候选证据；但**合并仍需「拟合并树 == QA 审查树」**，
  所以这不能用来绕过 QA。
