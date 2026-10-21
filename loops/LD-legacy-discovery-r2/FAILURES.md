# DRAFT

先完成切片目标、依赖、角色和门禁，再由 TL 武装。

## FAIL-2026-10-21-07 已接受的 QA 证据在 1 小时后无法复核（框架缺陷）

### 现象
本批次已 `DONE`，`independent_qa_gate` 记录为 `pass/VERIFIED_QA`，签名在 `accept-qa` 当时校验通过。
但在 2026-10-21T10:31Z 再次执行 `make evidence-check LOOP=LD-legacy-discovery-r2`（已设置
`LLMKE_TRUST_ROOT`）时报：

```
FAIL: independent_qa_gate: invalid approval validity window
```

### 根因
1. `scripts/qa_payload.py` 把载荷有效期固定为 **1 小时**
   （实测：`issued_at=08:13:13Z`，`expires_at=09:13:13Z`）。
2. `scripts/baseline_support.py: verify_envelope()` 在**每次校验**时都检查
   `issued-5min <= now < expires`，而 `evidence_errors()` 对 `pass` 记录会**重新验签**。
3. 于是：签名在有效期内被接受 → 1 小时后任何复核都会判"有效期窗口无效"。

### 影响（不要夸大）
- **批次状态与结论不受影响**：`DONE` 是在签名有效期内达成的，`finish` 已完成。
- 受影响的是**事后可复核性**：超过窗口后，任何人跑 `evidence-check` 都会看到这条红。
- 这不是"证据造假"，也不是"签名无效"，而是**有效期语义与复核机制冲突**。

### 可选处置（需业主/框架维护方决定）
| 选项 | 做法 | 代价 |
|---|---|---|
| A | 修 `qa_payload.py` 的窗口（如 7 天，框架硬上限）或让 `verify_envelope` 对**已接受**记录只校验签名不校验窗口 | 属冻结脚本变更，需重冻结 |
| B | 重新签一次，载荷窗口手工延长到 ≤7 天（框架允许的上限） | 需私钥再签一次；仍会过期，只是更久 |
| C | 接受现状：批次 DONE 有效，事后复核需在签署后 1 小时内进行 | 无改动；审计时会遇到这条红 |

**当前采纳 C**（未改动任何冻结文件），并在本文件留痕，供后续框架修复时引用。
