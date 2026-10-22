# 提交包 · qa-owner（签署与语义裁决）

**要什么**：三件授权动作 + 一项语义确认。**实现者不得代做任何一项。**

## ① 更新信任根锚点（治理动作）

| 项 | 值 |
|---|---|
| 文件 | `~/data/qa-keys/trust-root.json`（工作区外） |
| 字段 | `approved_baseline_sha256` |
| 现值 | `c8a73c3736dba301c8771cf7f09a575adcaf8be64763e55da04e746376cece04`（窗口前旧基线） |
| 应改为 | `213c6ebc203ef846c3edf5397a9640310a683391878ddb5af4c12b8da25cbc52`（r5 当前冻结清单） |

> 这一步等价于「批准 r5 这条基线」。**由实现者修改即构成自签。**
> 请把变更前后值抄录到签署记录（信任根目前无审计字段，见提案 P-10）。

## ② 签署 r5

```bash
cd ~/data/dev/llmke
python3 scripts/qa_payload.py --loop L0-contract-baseline-r5 \
  --gate independent_qa_gate --principal-id qa-owner-01 \
  --out docs/baseline/validation/qa-payload-r5.json

LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json \
python3 scripts/qa_sign.py --key-file $HOME/data/qa-keys/llmke-qa.key \
  --key-id qa-ed25519-2026-10 \
  --payload docs/baseline/validation/qa-payload-r5.json \
  --out docs/baseline/validation/qa-envelope-r5.json

python3 scripts/loop_guard.py accept-qa --loop L0-contract-baseline-r5 \
  --gate independent_qa_gate --attestation docs/baseline/validation/qa-envelope-r5.json
python3 scripts/loop_guard.py finish --loop L0-contract-baseline-r5
```

**载荷 1 小时有效**；过期只需重跑第 1 条（被签署的 `subject_sha256` 不含时间字段，内容不变）。

## ③ P-02 语义三选一

见 `DECISION-PACK-V1.1.1.md` D-01：
A 接受时校验有效期、复核只看签名与撤销（建议）／ B 维持现状／ C 延长有效期。

## ④ P-10 是否同意审计语义

信任根增加 `baseline_approvals` 追加列表（含批准人、时间、撤销），见 `ROUND4-PROPOSALS.md` P-10。

## 独立性要求

签署者 `principal_id` 不得出现在 `LOOP.yaml.implementation_principals`（r5 为 `integration-agent`）。
注意：框架只能拦「声明的实现者」，**拦不住「实现者拿别人钥匙签」**——独立性靠钥匙与执行者分离。

## 对应与影响

①② → **合并的唯一拦路条件**；③ → 历史 QA 复核能力；④ → 信任根可审计。
