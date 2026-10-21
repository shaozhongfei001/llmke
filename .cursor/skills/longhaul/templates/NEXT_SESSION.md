# Next Session Baton

| 字段 | 值 |
|------|-----|
| **Updated** | {{ISO_TIME}} |
| **holder** | `{{HOLDER}}` |
| **packet** | `{{PACKET}}` |
| **wave** | `{{WAVE}}` |
| **ops_gate** | （可执行 gate 摘要） |
| **do_not_start** | BUSINESS_SIGNED；抢 baton 旁路 |

## 短提示词

```text
你是 {{HOLDER}}。读 longhaul dispatch + memory/PROTOCOL + waves/{{WAVE}}-PLAN.md。
Loop engineering：attempt≤{{MAX}}；每次跑 gate 并 append ITER.md；未绿不得交棒。收工写 handoff；NEXT_SESSION→下一包。STOP。
```
