# P0 关闭闸门红队审计

日期：2026-10-22　对象：`scripts/p0_closure_check.py::check`
结论：**14 个用例全部被拦住**，未发现可绕过的伪造关闭路径。
脚本：`docs/baseline/validation/p0-gate-redteam-audit.py`（224 行，可复现）
性质：只读审计，在 `/tmp` 造夹具，**未改动仓库任何控制面文件**；r9 候选不受影响（已复核 PASS）。

---

## 1. 为什么要做这件事

四项 P0 是业务开工的唯一硬阻塞。它们的关闭依赖 `P0-CLOSURE.yaml` 里把 `status` 改成 `CLOSED`。
如果这个闸门能被"填个空文件"骗过，那么整套"p0-gate exit 2"的阻断就是装饰品。

所以问题不是"P0 什么时候关"，而是"**关的时候能不能骗过去**"。

---

## 2. 审计方法

1. 在 `/tmp/p0audit/run` 造一个最小 root（策略文件 + 证据 + dossier），不碰真仓库；
2. 先构造一个"除签名外全绿"的基线：4 项都 `CLOSED`、dossier 结构完整、
   `D01..Dnn` 全答、证据带正确 sha256、`verified_tests` 全 PASS；
3. 然后**每次只破坏一个点**，断言 `check()` 必须报错，且错误指向被破坏的那个点
   （避免"因为别的原因报错"而误判为拦住）。

---

## 3. 结果

| # | 伪造方式 | 结果 | 闸门的报错 |
|---|---|---|---|
| 基线 | 结构全绿、仅缺签名 | **拦住** | 4 项均报 approval/trust root（签名不可绕过） |
| A1 | `CLOSED` 但 `evidence: []` | 拦住 | `CLOSED requires closure dossier` |
| A2 | dossier 的 `blocker_id` 换成别的 | 拦住 | snapshot/blocker 不符 |
| A3 | `source_snapshot_sha256` 用假值 | 拦住 | `closure baseline/source snapshot mismatch` |
| A4 | 少答一项 decision | 拦住 | `not all decision items answered` |
| A5 | 某个 answer 的 `evidence` 为空 | 拦住 | `decision answer lacks conclusion/evidence` |
| A6 | 引用证据的 `sha256` 改掉 | 拦住 | `hash mismatch` |
| A7 | 引用一个空文件 | 拦住 | `missing/EMPTY closure evidence` |
| A8 | `verified_tests` 用 `SKIPPED` | 拦住 | `closure has no verified successful tests` |
| A9 | 不带任何 `approvals` | 拦住 | approval/trust root |
| A10 | `ACCEPTED_RISK` 不带 `waiver_ref` | 拦住 | `accepted risk requires separate waiver` |
| A11 | `ACCEPTED_RISK` 带 waiver，试图过 strict | 拦住 | `strict requires CLOSED` |
| A12 | 直接删掉 `P0-04` | 拦住 | `required IDs cannot be deleted or duplicated` |
| A13 | 篡改 `owner` / `blocks` | 拦住 | `owner/impact differs from approved baseline` |

---

## 4. 过程中的一次自我纠错

第一次跑 A10 显示 `MISSED`，我一度以为找到了闸门漏洞。实际是**我的断言字符串写错了**：
代码报的是 `accepted risk requires separate waiver; it never closes the blocker`，
而我的断言在找 `waiver_ref` 这个词。打印实际错误信息后确认闸门正常，改正断言后 14/14 通过。

这条记下来，是因为它和之前几次"假绿/假红"是同一类错误：
**断言的措辞与实现的措辞不一致时，很容易把工具的正确行为误报成缺陷**（反之亦然）。

---

## 5. 审计覆盖不到的地方（不夸大结论）

| 项 | 为什么覆盖不到 |
|---|---|
| 伪造签名 | 需要 qa-owner/baseline-owner 私钥；本审计只能验证"没有签名就过不去" |
| 伪造证据内容 | 闸门只校验"文件存在且哈希匹配声明"，不判断内容是否真的是 DDL/调用日志；那属于人工复核 |
| 时间有效性 | `verify_envelope` 有 5 分钟时钟偏移与 7 天上限，但本审计未构造过期签名 |
| `P0-CLOSURE.yaml` 自身版本 | 文件内 `baseline_version: 1.1.0` 与 `VERSION=1.1.1` 不一致；该文件不在 `control_digest` 内但在 `doc_digest` 内，改动会让 `traceability_gate` STALE，故本轮**只登记不改** |

---

## 6. 对当前状态的结论

- `p0-gate` 报 `exit 2` 不是"没人去改登记"，而是**四项确实没有可追溯的关闭材料**；
- 闸门结构是可靠的：要关闭任何一项，必须同时具备
  ① 当前快照下的 dossier、② 逐项回答且每项带哈希证据、③ 通过的验证测试、④ owner + baseline-owner 的**真实签名**；
- 因此"先做业务、P0 后补"这条路在机制上被堵住，而不是仅靠纪律。
