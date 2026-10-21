# Longhaul Shared Memory Protocol

## 开场
1. `git status -sb` · `git rev-parse --short HEAD`
2. 读 ROLE_BOARD.yaml · NEXT_SESSION.md · ORCHESTRATOR.md
3. 读当前 `waves/<WAVE>-PLAN.md`（若存在）
4. holder 不匹配 → **STOP**

## Worker 内层（loop engineering）
1. 确认/刷新 PLAN（goal + **可执行** gate 命令列表）
2. For attempt in 1..max_attempts:
   - Build
   - Measure（跑全部 gate 命令）
   - Append `waves/<WAVE>-ITER.md`：attempt / cmds / pass|fail / 根因 / 下一步
   - 全绿 → break；触红线 → BLOCKED.md + STOP
3. 次数用尽仍红 → BLOCKED.md（含最后 ITER）+ STOP（不假装 PASS）

## 收工
handoffs/<packet>.md · ../EVIDENCE.md · ../STATE.json · ROLE_BOARD · NEXT_SESSION  
未落盘 = 其它 Agent 视为未发生

## TL tick
验收须核对 ITER；无 ITER 且中途曾红 → REJECT  
ACCEPT 才允许改 baton 到下一波
