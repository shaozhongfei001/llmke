# {{TITLE}}｜长程无人值守编排

| 字段 | 值 |
|------|-----|
| **状态** | DRAFT / ARMED / HOLD / CLOSED |
| **loop_id** | `{{LOOP_ID}}` |
| **horizon** | `{{HORIZON}}` |
| **tick_interval** | `{{TICK}}` |
| **end_gate** | `{{END_GATE}}` |
| **设计 SSOT** | `{{DESIGN_SSOT}}` |
| **共享记忆** | `loops/{{LOOP_ID}}/memory/` |
| **max_attempts / wave** | `{{MAX_ATTEMPTS}}`（默认 5） |
| **红线** | （项目填写：不代签、不删基线…） |

## 三层循环

1. **外层** horizon + TL tick  
2. **中层** Wave baton（NEXT_SESSION）  
3. **内层** 每波 **loop engineering**：Plan→Build→Measure→Learn 直到 GATE_PASS / BLOCKED / 次数用尽  

详见 skill `ontos-longhaul` · 波次 ITER 日志：`memory/waves/<W>-ITER.md`

## §0 波次板

| Wave | Packet | Role | Gate（可执行） | max_attempts | 状态 |
|------|--------|------|----------------|--------------|------|
| W1 | … | … | `pytest …` · 文件存在… | 5 | |

## §1 短提示词

### @TL Supervisor tick
（粘贴 skill Step 4）

### @Worker（每波；须含 loop engineering）
```text
你是 {{PACKET}}。读本派工 + memory/PROTOCOL + waves/{{W}}-PLAN.md。
按 loop engineering：attempt≤{{MAX}}；每次跑 gate 命令并 append ITER.md；未绿不得交棒。
收工写 handoff；NEXT_SESSION→下一包。STOP。
```

## §6 签字门槛

| 门 | 条件 |
|----|------|
| Wave PASS | gates 全绿 + ITER 完整 + TL ACCEPT |
| End | end_gate only |

## §8 变更记录

| 日期 | 作者 | 说明 |
|------|------|------|
