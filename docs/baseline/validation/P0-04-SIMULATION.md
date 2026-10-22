# P0-04 五场景协议模拟结果（SIMULATED）

> **这不是 P0-04 关闭证据。** 它验证的是「协议设计是否自洽、能否挡住已知混代路径」，
> 不验证真实存储行为。P0-04 仍 `OPEN`。
>
> 工具：`loops/LD-legacy-discovery/tools/p0_04_scenarios.py`
> 数据：`loops/LD-legacy-discovery/evidence/p0-04-scenarios.json`
> 复跑：`python3 loops/LD-legacy-discovery/tools/p0_04_scenarios.py --out loops/LD-legacy-discovery/evidence/p0-04-scenarios.json`

---

## 1. 建模的三条协议约束

| 约束 | 模型中的实现 |
|---|---|
| generation manifest 不可变 | 同一 `generation_id` 二次 `open` 直接抛错，修正只能新开代次 |
| 每 KB 单原子激活指针 | `activate()` 先检查**四后端**可用，任一不可用则整体不切；读指针与写目标**同时**切换 |
| 写入必须带 `(kb_id, generation_id, fencing_token)` | 代次不等于写目标 → 抛 `stale generation`；token 小于已见最大值 → 抛 `fenced out` |
| 幂等键必须含内容哈希 | `(kb, file, config, sha256(payload))`；变异体退回 `(kb, file, config)` |

## 2. 五场景结果（对应 P0-04 `evidence_expectation`）

| 场景 | 断言 | 结果 |
|---|---|---|
| **S1 部分后端失败** | `milvus` 不可用时激活必须中止；可读代次集合大小必须为 1 | **PASS**（未切换，可读 `{1}`） |
| **S2 切换中断** | 中断后指针停在旧代；可读集合必须仍是 `{1}` | **PASS** |
| **S3 内容覆盖** | 同 `(kb,file,config)` 但内容不同，两次写入的幂等键必须不同 | **PASS**（含内容哈希后可区分） |
| **S4 迟到重试** | 旧代任务在新代激活后到达，代次已匹配但 token 过期 → 必须被 fencing 拒绝，且新代数据不得被污染 | **PASS** |
| **S5 旧服务回退** | 切到 gen2 后旧服务仍按 gen1 写入 → 必须被拒 | **PASS** |

## 3. 变异对照（证明断言非空转）

把每场景的关键约束改坏，断言必须由 PASS 变 FAIL：

| 场景 | 变异内容 | 期望 | 实测 |
|---|---|---|---|
| S1 | 绕过原子性直接改读指针 | 混代被检出 | **变异体 FAIL**（被检出） |
| S2 | 中断后强行置指针 | 同上 | **变异体 FAIL** |
| S3 | 幂等键退回不含内容哈希 | 覆盖不可区分 | **变异体 FAIL** |
| S4 | 绕过 fencing 直接写入新代 | 新代被污染 | **变异体 FAIL** |
| S5 | 允许旧代继续写入 | 未拒绝 | **变异体 FAIL** |

**5/5 变异体被拒** → 五条断言都在真实起作用，不是 `assert True` 式空转。

## 4. 这个模拟**不能**证明什么

| 不能证明 | 为什么 | 需要什么 |
|---|---|---|
| 真实四后端的一致性 | 模型里的「后端」只是一个 list | MySQL/ES/Milvus/Neo4j 实机 |
| 双代存储与内存余量 | 没有真实数据量与资源曲线 | `index-owner` 的实测数字（P2 前必须给出，不得推到 P3） |
| 历史引用不断链 | 未涉及旧答案如何指向被替换的快照 | 快照保留策略 + 真实回放 |
| 迟到任务的真实来源 | 未模拟 MQ/重试队列语义 | 任务队列与 outbox 实测 |
| 切换的秒级/分钟级耗时 | 纯内存模型 | 压测 |

## 5. 结论与下一步

- **协议层面：五条已知混代路径都能被挡住**，且断言经过变异验证；
- **工程层面：P0-04 仍 OPEN**，`blocks` 未清空，L1–L4 仍 BLOCKED；
- 升级为真实证据需要：可运行检索链 + 四套存储 + 双代余量实测 + 快照保留验证，
  由 `index-owner` 在受保护环境执行，`baseline-owner` 复核后方可改 `P0-CLOSURE.yaml`。
