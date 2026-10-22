# ROUND8 关闭记录

- 关闭时间：2026-10-23
- 关闭人：project-owner（裁定"按 ② 收尾，无独立背书，就此为止"）
- 关闭方式：**业主主动关闭**，不是"全部达成后自然结束"

## 一句话结论

**技术完成、无独立背书。** 代码/数据/证据无待修项；业务不可开工。

## 判定口径（避免后人误读）

"结束"有两种，本文件按第二种：

| 口径 | 本轮 |
|---|---|
| 全部目标达成后自然结束 | **否**（2 项未达成） |
| 业主确认不再投入、明确记录未达成项后关闭 | **是** |

因此：**不得把本轮关闭表述为"第八轮全部完成"**，尤其不得表述为"已通过独立 QA"。

## 达成项（25 / 27）

| 项 | 实测 |
|---|---|
| 框架门禁 | `make framework-verify` rc=0 / **252 passed、0 skipped** |
| schema 落地 | `schema-verify.sh` rc=0 / 43 表 538 列 / 97 模块测试 / C1–C6 全 PASS |
| 候选证据 | r11 `evidence-check` **PASS**（8 pass + `independent_qa_gate=QA_PENDING`，scheme=3） |
| 冻结 | `revision 12` / 215 文件 / `1.1.1`，与 `VERSION` 一致 |
| 证据绑定 | 改实现代码 → 仅 QA 门禁 STALE；控制面加文件 → 9 条全 STALE；改文档 → 仅 traceability；篡改日志 → hash mismatch |

## 未达成项（不结转成"已完成"）

| 任务 | 状态 | 事实 |
|---|---|---|
| `R8-T04` 独立 QA 签署 | `CLOSED_WITHOUT_ENDORSEMENT` | 技术复核 PASS 但**未出具签名**：`qa-ed25519-indep` 私钥已 shred、无副本、无交付证据 → 公钥悬空，永久无法签名 |
| `R8-T05` 真实 DDL / 路由 / E1 / S1–S5 | `BLOCKED_EXTERNAL` | 对应 owner 未提供；**随轮次结转下一轮**，不得视为已解决 |

## 业务闸门（未因本轮关闭而改变）

- `make p0-gate` → **rc=2**
- P0-01 / P0-02 / P0-03 / P0-04 **全部 OPEN**
- L1–L4 **BLOCKED**，业务**不可开工**

## 结转与后续

1. `R8-T05` → 下一轮首要输入，依赖四位 owner 的材料。
2. 若将来要独立背书：**不要复用 r11**。原因有二：`attempts` 中 `independent_qa_gate` 已用 2/3（再失败即耗尽），签名窗口固定 1 小时。正确顺序见 `NEXT-SESSION.md`。
3. `trust-root` 中 `qa-ed25519-indep` 为**悬空登记**（公钥在册、私钥不存在）。是否清除由业主决定，清除属 trust-root 改动、不影响基线。

## 复验命令（规则 R1：不接管道）

```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
~/data/dev/coordination/mysql-probe.sh start
make framework-verify > /tmp/fv.log 2>&1; echo "rc=$?"; tail -3 /tmp/fv.log
~/data/dev/coordination/evidence-check.sh L0-contract-baseline-r11
make p0-gate > /tmp/p0.log 2>&1; echo "rc=$?（期望 2）"
```
