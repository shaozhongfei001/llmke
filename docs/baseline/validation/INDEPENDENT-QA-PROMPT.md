# 给独立 E2E QA 的提示词（可直接投喂）

> 用途：让**另一个主体、持独立私钥**的 QA 完成真正的独立背书。
> 现状提示：当前 `r10` 的签名是**业主授权的自签**（见 `R10-QA-HANDOFF.md` §8），
> 不能作为独立背书。本提示词的产出，是形成一份**可审计的独立签名**。

---

## 0. 你的身份与边界（先确认，再动手）

你是**独立 QA**，不是实现方。请先自检三条，任何一条不成立就停止并说明：

| 条件 | 要求 |
|---|---|
| 主体独立 | 你持有**独立私钥**，且该私钥从未参与本项目实现 |
| 主体登记 | 你的 `principal_id` **不在**目标批次 `LOOP.yaml` 的 `implementation_principals` 中 |
| 决策独立 | 你可以拒绝通过，且拒绝不受任何"尽快合并"的压力影响 |

**禁止**：复用 `/tmp/r10-attestation.json` 或任何已有签名；禁止修改 `implementation_principals`；
禁止修改 `trust-root.json`（那是业主/受保护 CI 的动作，不是你的）。

---

## 1. 当前仓库事实（请自行复核，不要相信本文）

| 项 | 声称值 | 你要做的 |
|---|---|---|
| 工作分支 | `main` | `git log --oneline -1` 自查 |
| 技术门禁 | `framework-verify` exit 0 / **252 passed、0 skipped** | 自己跑，必须 0 skipped |
| 落地验证 | 43 表 / 538 列 / 97 模块测试 / 体检 6 项 | 自己跑 `schema-verify.sh` |
| 业务闸门 | `p0-gate` **exit 2** | 自己跑；若变 0 直接判 FAIL |
| r10 | `DONE`，但签名为**自签** | 读 `R10-QA-HANDOFF.md` §8 |

---

## 2. 第一步：独立复核（在签名之前完成）

### 2.1 环境

```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH
export LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
~/data/dev/coordination/mysql-probe.sh start     # 真库测试必须真的跑，不能被 skip
```

### 2.2 门禁与落地（必须两条都过，且 **0 skipped**）

```bash
make framework-verify           # 期望 exit 0；输出必须是 "252 passed"，不得出现 skipped
docs/baseline/validation/schema-verify.sh   # 期望 PASS：43 表 / 97 测试 / 体检 6 项
make p0-gate                    # 期望 exit 2（业务仍被 P0 阻断，这是正确状态）
```

**若出现 `skipped`：直接判 FAIL。** 依据：`DECISIONS.md` D44——曾有 29 项真库测试被跳过而门禁仍通过。

### 2.3 对抗测试（必须由你自己制造，不许只读我们的结论）

```bash
# A. 改实现代码 -> QA 证据必须失效
printf '\n# qa-probe\n' >> modules/chunk_store/chunk_store.py
PYTHONPATH=$PWD python3 scripts/loop_guard.py evidence-check --loop <候选批次>   # 期望 FAIL
git checkout -- modules/chunk_store/chunk_store.py

# B. 控制面加文件 -> 全部记录 STALE
echo "x: 1" > contracts/_qa_probe.yaml
PYTHONPATH=$PWD python3 scripts/loop_guard.py evidence-check --loop <候选批次>   # 期望 9/9 STALE
rm contracts/_qa_probe.yaml

# C. 文档改动 -> 只应影响 traceability_gate
echo probe > docs/_qa_probe.md
PYTHONPATH=$PWD python3 scripts/loop_guard.py evidence-check --loop <候选批次>   # 期望只有 traceability STALE
rm docs/_qa_probe.md

# D. 篡改证据日志 -> 必须 hash mismatch
cp loops/<候选批次>/evidence/baseline_gate.log /tmp/bk.log
echo tampered >> loops/<候选批次>/evidence/baseline_gate.log
PYTHONPATH=$PWD python3 scripts/loop_guard.py evidence-check --loop <候选批次>   # 期望 FAIL
cp /tmp/bk.log loops/<候选批次>/evidence/baseline_gate.log
```

### 2.4 抽查实现方结论（挑 3 项即可，目的是验证"不是纸面结论"）

```bash
# ① P0-01：清单里有一条注释掉的接口（应为 getRerankModelInfos）
python3 docs/baseline/validation/p0-01-route-extract.py \
  --src ~/data/repo/RAG-SRC/_src/gien-rag/gien-rag/rag-parent \
  --csv docs/upstream/源码接口契约-接口总表.csv | head -20

# ② DDL 真机可执行（含 43 表 + 契约一致 + 体检）
docs/baseline/validation/schema-verify.sh

# ③ create_by 语义（应为账号，不是用户 ID）
grep -rn "setCreateBy(userName)" ~/data/repo/RAG-SRC/_src/gien-rag/gien-rag/rag-parent --include="*.java" | head -3
```

### 2.5 判定（任何一条不满足即 **FAIL**）

- [ ] `framework-verify` = `252 passed` 且 **无 skipped**
- [ ] `schema-verify.sh` PASS（43 表 / 97 测试 / 体检 6 项）
- [ ] `p0-gate` = `exit 2`
- [ ] 四个对抗测试全部按预期反应（STALE / 9-of-9 / 仅 traceability / hash mismatch）
- [ ] 证据记录含 `digest_scheme=3` 与 `code_sha256`
- [ ] 冻结清单 `files` 数量与 `FROZEN-MANIFEST.json` 一致，`baseline_version` = `VERSION`
- [ ] 未发现"文档说通过、实际未跑"的情况

---

## 3. 第二步：用你的私钥签名（仅当 §2 全过）

### 3.1 一次性准备（由业主/受保护 CI 完成，不是你）

```bash
# 生成独立密钥（私钥必须留在仓库之外）
openssl genpkey -algorithm ED25519 -out /secure/qa-independent.key
openssl pkey -in /secure/qa-independent.key -pubout -out /secure/qa-independent.pub
```

在 `trust-root.json` 的 `principals` 中新增一项（**由业主执行**）：

```json
"qa-ed25519-indep": {
  "principal_id": "qa-external-02",
  "roles": ["qa-owner"],
  "enabled": true,
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\n…\n-----END PUBLIC KEY-----\n"
}
```

并确认：

- `approved_baseline_sha256` **等于**候选当前 `baseline_hash`（用 `scripts/freeze_baseline.py` 的输出核对）；
- `qa-external-02` **不在**该批次 `LOOP.yaml` 的 `implementation_principals` 中。

### 3.2 为什么必须对新批次签名

`accept-qa` 的前置条件是记录状态为 `QA_PENDING`（`loop_guard.py:228`）。
r10 的 QA 记录已是 `pass`，**无法被第二次签名接受**；而把已接受记录改回 `QA_PENDING`
属于改写历史证据，**明确禁止**。

因此独立签名必须落在**新批次**上（例如 `r11`，树与 r10 相同或更新）：

- 若候选批次已提供：按其 `LOOP.yaml` 的 `loop_id` 执行下文；
- 若未提供：**要求实现方建批**，不要自己建批（建批会让你变成作者）。

### 3.3 签名与接受

```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH
export LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
LOOP=<候选批次>          # 例：L0-contract-baseline-r11

# 1) 重新生成载荷（有效期 1 小时，必须现场生成）
PYTHONPATH=$PWD python3 scripts/qa_payload.py --loop $LOOP \
  --gate independent_qa_gate --principal-id qa-external-02 \
  --out /tmp/qa-payload.json

# 2) 检查载荷确实绑定了这次审查的对象
python3 - <<'PY'
import json;d=json.load(open('/tmp/qa-payload.json'))
for k in ('loop_id','gate_id','result','baseline_sha256','source_sha256','subject_sha256','expires_at'):
    print(k,'=',d[k])
PY

# 3) 用你的私钥签名（私钥不得放进仓库；qa_sign.py 会强制检查）
PYTHONPATH=$PWD python3 scripts/qa_sign.py \
  --key-file /secure/qa-independent.key --key-id qa-ed25519-indep \
  --payload /tmp/qa-payload.json --out /tmp/qa-attestation.json

# 4) 接受
PYTHONPATH=$PWD python3 scripts/loop_guard.py accept-qa --loop $LOOP \
  --gate independent_qa_gate --attestation /tmp/qa-attestation.json

# 5) 校验并收口
PYTHONPATH=$PWD python3 scripts/loop_guard.py evidence-check --loop $LOOP
PYTHONPATH=$PWD python3 scripts/loop_guard.py finish --loop $LOOP
```

### 3.4 签名后的自证（必须做）

```bash
PYTHONPATH=$PWD python3 - <<'PY'
import json
m=json.load(open('loops/<候选批次>/evidence/manifest.json'))
q=m['gates']['independent_qa_gate']
print('status=',q['status'],'| key_id=',q['attestation']['key_id'],'| role=',q['role'])
assert q['attestation']['key_id']=='qa-ed25519-indep', '签名不是你的 key'
PY
```

---

## 4. 你的输出报告（按此格式提交）

```
【独立 QA 报告】
候选批次: <loop_id>
候选指纹: baseline_sha256=<…> subject_sha256=<…>
代码版本: main@<commit>  树哈希=<…>
复核环境: MySQL <版本> / Python <版本>

逐项结论:
1. framework-verify        PASS/FAIL  <关键输出行>
2. schema-verify           PASS/FAIL  <表数/列数/测试数/体检项数>
3. p0-gate                 exit=<n>    PASS/FAIL
4. 对抗 A 改代码            <预期STALE> 实际<…>
5. 对抗 B 控制面            <9/9>      实际<…>
6. 对抗 C 文档              <仅traceability> 实际<…>
7. 对抗 D 篡改日志          <hash mismatch> 实际<…>
8. 抽查 P0-01 / DDL / create_by  <结论>

签名: key_id=qa-ed25519-indep  principal=qa-external-02
结论: 允许合并 / 拒绝（理由）
未通过项与复现命令: <…>
```

## 5. 拒绝条件（出现即 FAIL，不给"有条件通过"）

- 任一对抗测试没有按预期失效；
- 出现 `skipped` 而仍声称通过；
- `p0-gate` 变成 0；
- 证据记录与 `FROZEN-MANIFEST` 不一致（文件数/版本/`baseline_sha256`）；
- 发现签名密钥与实现方共用，或 `principal_id` 出现在 `implementation_principals`；
- 发现任何"用旧批次签名冒充当前候选"的行为。

## 6. 一句提醒

这份复核的价值不在"确认它通过"，而在**你能证明它不通过时会被拦住**。
若你所有检查都通过而没有真正制造过失败，请回去把 §2.3 至少重做一遍。
