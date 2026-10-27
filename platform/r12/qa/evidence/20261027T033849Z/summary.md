# R12 验收 20261027T033849Z

计划场景：['S7']（未知：[]）
总计 7/8 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| PREP | 删除上一轮验收库（保证基线独立可重复） | PASS | kbId=17 kbName=R14-BASELINE-KB http=200 |
| PREP | 创建独立验收库 | PASS | http=200 kbId=18 kbName=R14-BASELINE-KB primitive=kb_18 旧库清理=1 |
| PREP | 独立库助手配置就绪 | PASS | kbName=kb_18 configId=12（R14-BASELINE-CFG） |
| PREP | 真实模型回答（29字问题） | PASS | http=200 帧数=73 答案长度=125 |
| PREP | 回答带引用 | FAIL | 引用条数=0 |
| S7 | 历史对话可恢复 | PASS | http=200 session=kb_18 问答对数=1 问与答均有正文=True 本轮queryId=q-1793072330054 命中=True |
| S7 | 会话列表可查 | PASS | http=200 |
| COVERAGE | 选中的场景均已真实执行 | PASS | 选中=['S7'] 实际执行=['S7'] 未执行=[] 未知场景=[] |
