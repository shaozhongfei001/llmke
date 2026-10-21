# QA 主体与密钥交接单 V1.0

- 日期：2026-10-21
- 用途：把"真实 QA 主体 + 密钥"接入 LLMKE 的 QA_ATTESTATION 流程
- 本文件位于 `docs/baseline/validation/`（不参与源码快照）

## 1. 我需要的三样输入（由 QA 一方提供）

| # | 输入 | 说明 | 示例 |
|---|---|---|---|
| 1 | `principal_id` | QA 主体标识，**不得**等于批次的实现方（`integration-agent` / `legacy-owner`） | `qa-owner-zhang` |
| 2 | `key_id` | 密钥标识，写入 trust root 与信封 | `qa-key-2026-10` |
| 3 | `public_key_pem` | **公钥** PEM 文本（私钥绝不外传） | `-----BEGIN PUBLIC KEY-----\nMCow…\n-----END PUBLIC KEY-----` |

**私钥由 QA 一方在受保护环境生成并保管**，不需要、也不应该给我。

## 2. 密钥生成（在 QA 侧的受保护机器上执行）

```bash
# Ed25519（verify_envelope 用 openssl pkeyutl -verify -rawin 校验）
mkdir -p ~/data/qa-keys && chmod 700 ~/data/qa-keys
openssl genpkey -algorithm ED25519 -out ~/data/qa-keys/llmke-qa.key
chmod 600 ~/data/qa-keys/llmke-qa.key
openssl pkey -in ~/data/qa-keys/llmke-qa.key -pubout -out ~/data/qa-keys/llmke-qa.pub

# 把公钥内容发给我（三行 PEM，含首尾行）
cat ~/data/qa-keys/llmke-qa.pub
```

要点：
- 私钥路径**必须在 llmke 工作区之外**，`qa_sign.py` 会强制检查
  （`private key must remain outside implementation workspace`）；
- 建议私钥只存在于受保护 runner，不落开发者机器。

## 3. 信任根文件（由持有方在受保护 runner 上放置）

```json
{
  "environment": "PROTECTED_RUNNER",
  "approved_baseline_sha256": "c8a73c3736dba301c8771cf7f09a575adcaf8be64763e55da04e746376cece04",
  "principals": {
    "<key_id>": {
      "principal_id": "<principal_id>",
      "roles": ["qa-owner"],
      "public_key_pem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
      "enabled": true
    }
  }
}
```

四个字段的硬约束（`verify_envelope` 逐条校验）：

| 字段 | 要求 |
|---|---|
| `environment` | 必须是 `PROTECTED_RUNNER` |
| `approved_baseline_sha256` | 必须等于**当前** `docs/baseline/FROZEN-MANIFEST.json` 的哈希（现为 `c8a73c37…`；基线一变就要同步改） |
| `roles` | 必须含 `qa-owner` |
| `principal_id` | 必须与载荷里的完全一致，且**不在** `implementation_principals` 内 |

放置位置：`export LLMKE_TRUST_ROOT=<工作区外的绝对路径>`，且该路径不得位于 llmke 目录内
（`verify_envelope` 会报 `trust root must be outside implementation workspace`）。

## 4. 接到输入后我做什么（两条命令）

```bash
# ① 用真实 principal_id 重新生成载荷（载荷 1 小时过期，须在签署前生成）
python3 scripts/qa_payload.py --loop L0-contract-baseline-r2 --gate independent_qa_gate \
  --principal-id <principal_id> --out /tmp/qa-payload-l0.json
python3 scripts/qa_payload.py --loop LD-legacy-discovery-r2 --gate independent_qa_gate \
  --principal-id <principal_id> --out /tmp/qa-payload-ld.json

# ② 交 QA 侧签名并接受（QA 侧执行）
python3 scripts/qa_sign.py --key-file ~/data/qa-keys/llmke-qa.key --key-id <key_id> \
  --payload /tmp/qa-payload-l0.json --out /tmp/qa-envelope-l0.json
python3 scripts/loop_guard.py accept-qa --loop L0-contract-baseline-r2 \
  --gate independent_qa_gate --attestation /tmp/qa-envelope-l0.json
```

## 5. 当前两个批次的固定值（签名会绑定这些）

| 项 | L0-r2 | LD-r2 |
|---|---|---|
| `source_sha256` | `d0530bee…53689c` | 同左（同一快照） |
| `baseline_sha256` | `c8a73c37…cece04` | 同左 |
| `executed_checks` | `all_framework_tests, semantic_check, rule_mirror, trace, p0_integrity, baseline_hashes` | `candidate_register_integrity, source_and_DDL_missing_stay_pending` |
| `result` | PASS | PASS |

## 6. 为什么不由我生成密钥

如果私钥经过我手，我就能对任意载荷签名，"独立 QA"在机制上就不成立了。
`verify_envelope` 只校验"签名有效 + 主体不是实现方"，它**无法检测**"私钥是否被实现方掌握"——
这条只能靠流程保证：**私钥从不进入实现方环境**。
