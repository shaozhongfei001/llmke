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
