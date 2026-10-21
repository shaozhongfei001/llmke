# 独立 QA 交办说明 V1.0

- 日期：2026-10-21
- 对象批次：`L0-contract-baseline-r2`、`LD-legacy-discovery-r2`（均 `QA_PENDING`）
- 当前角色：**开发侧已自检，未签署任何 QA 结论**。本文件只说明"外部 QA 怎么签"，不构成签署。
- 本文件位于 `docs/baseline/validation/`（不参与源码快照），写入它不会使门禁证据失效。

## 1. 已就绪的东西

| 项 | 值 |
|---|---|
| L0-r2 QA 候选运行 | `independent_qa_gate`：`make framework-verify` 退出码 0，记录状态 `QA_PENDING` |
| LD-r2 QA 候选运行 | `independent_qa_gate`：`make discovery-verify` 退出码 0，记录状态 `QA_PENDING` |
| 未签名载荷 | `qa-payload-L0-r2.json`、`qa-payload-LD-r2.json`（本目录） |
| 源码快照 | `source_sha256 = d0530bee289b8bfdf369762bb07a1e0cf8f9ba457c3b10ccf68b0e4b7353689c` |
| 冻结基线 | `baseline_sha256 = c8a73c3736dba301c8771cf7f09a575adcaf8be64763e55da04e746376cece04` |

载荷里已固定：`loop_id / gate_id / gate_spec_sha256 / source_sha256 / baseline_sha256 / log_sha256 / result=PASS / executed_checks`。
**签署就是对这些值背书**——任何一项变化，载荷立即失效（这是设计意图）。

## 2. 外部 QA 的五个步骤

```bash
# ① 取当前载荷（注意：载荷 1 小时过期，签署前必须重新生成一次）
cd <llmke>
MAKEFLAGS=--no-print-directory python3 scripts/loop_guard.py qa-run \
  --loop L0-contract-baseline-r2 --gate independent_qa_gate --executor integration-agent
python3 scripts/qa_payload.py --loop L0-contract-baseline-r2 --gate independent_qa_gate \
  --principal-id <你的 principal_id> --out /tmp/qa-payload-l0.json

# ② 在受保护环境用私钥签名（私钥必须在工作区之外，工具会强制检查）
python3 scripts/qa_sign.py --key-file <工作区外的私钥> --key-id <key_id> \
  --payload /tmp/qa-payload-l0.json --out /tmp/qa-envelope-l0.json

# ③ 配置信任根（只在受保护 runner 上，路径必须在工作区之外）
export LLMKE_TRUST_ROOT=/etc/llmke/trust-root.json

# ④ 接受签名
python3 scripts/loop_guard.py accept-qa --loop L0-contract-baseline-r2 \
  --gate independent_qa_gate --attestation /tmp/qa-envelope-l0.json

# ⑤ 收尾
python3 scripts/loop_guard.py finish --loop L0-contract-baseline-r2
```

LD-r2 把 `--loop` 换成 `LD-legacy-discovery-r2`、`--executor` 换成 `legacy-owner`，其余相同。

## 3. 信任根文件的最低要求

```json
{
  "environment": "PROTECTED_RUNNER",
  "approved_baseline_sha256": "c8a73c3736dba301c8771cf7f09a575adcaf8be64763e55da04e746376cece04",
  "principals": {
    "<key_id>": {
      "principal_id": "<与载荷中的 principal_id 完全一致>",
      "roles": ["qa-owner"],
      "public_key_pem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
      "enabled": true
    }
  }
}
```

四条硬约束（实现里逐条校验）：

1. `environment` 必须是 `PROTECTED_RUNNER`；
2. `approved_baseline_sha256` 必须等于**当前** `FROZEN-MANIFEST.json` 的哈希（改了基线就要同步改这里）；
3. `principal_id` **不得**出现在批次的 `implementation_principals` 里（实现方不得自签）；
4. 载荷有效期 ≤ 7 天且签发时间不得超前 5 分钟（默认 1 小时，过期需重新生成）。

## 4. 注意：签署 ≠ P0 关闭

- 四项业务 P0 仍全部 `OPEN`，`make p0-gate` 仍以退出码 2 拒绝；
- 即使两批次 `finish`，L1–L4 仍 `BLOCKED`；
- 本说明不改变任何 P0 状态，也不代表业务可交付。

## 5. 当前缺口（外部 QA 会遇到的）

| 缺口 | 影响 |
|---|---|
| 尚无 `LLMKE_TRUST_ROOT` 与公私钥对 | `accept-qa` 会报 `external trust root not configured`，QA 保持 PENDING |
| 载荷 `principal_id` 现为占位 `qa-external-pending` | 实际 QA 主身份确定后必须用其真实 `principal_id` 重新生成载荷 |
| 尚未确定固定快照的复跑环境 | 外部 QA 必须在与上述 `source_sha256` 完全一致的树上复跑，否则证据 STALE |
