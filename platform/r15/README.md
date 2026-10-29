# R15 验收与举证包

这份目录的目的只有一个：**让第三方能自己复现结论，而不是读一份别人的结论**。

## 三条命令

```bash
# 1) 跑全部断言（前置检查不通过会直接 ABORT，不给假 PASS/FAIL）
platform/r15/verify.sh

# 2) 只跑某几条
platform/r15/verify.sh --only A01,A03,A09

# 3) 指向另一套环境
platform/r15/verify.sh \
  --gw http://10.0.0.5:8088 --es http://10.0.0.5:19200 \
  --nebula-host 10.0.0.5 --nebula-port 9669 \
  --graph http://10.0.0.5:19529 --kb kb_9 --space g_kb_9
```

退出码就是结论：

```
0  没有 FAIL（SKIP 不算通过）
1  存在 FAIL
2  环境/依赖不满足，断言集根本没跑起来 —— 这种结果不得用于举证
```

## 每次运行产出什么

```
acceptance/results/<run_id>/
  env.json            本次环境指纹：网关/ES/Nebula/库/空间/模型/解释器/口令长度
  report.json         全部断言判定
  summary.txt         人读摘要
  raw/A01.json ...    每条断言的完整返回（含每项 check 的 detail）
  baseline-diff.json  与基线的差异（regressed / recovered / still_fail / new / missing）
```

**`env.json` 是这份证据能不能被采信的前提**：同一份断言在不同环境上跑出不同结果，
没有环境指纹就无法判断差异来自代码还是环境。

## 基线的作用

```
platform/r15/baseline/expect.json   某次评审确认的状态
```

单次运行只能说“此刻怎样”。有基线才能回答第三方最关心的问题：

```
他跑出来和我一样吗？   → 比对 baseline-diff.json
哪条变差了？           → regressed 列表
哪条从坏变好？         → recovered 列表
```

冻结新基线（会覆盖）：

```bash
platform/r15/verify.sh --freeze-baseline
```

## 证据等级：这个包里的东西强度不同，必须分清

`platform/r12/qa/evidence/r15/<case>/RESULT.md` 头部都标了等级：

| 等级 | 含义 | 能不能用于举证 |
|---|---|---|
| `REPRODUCIBLE` | 目录内 `run.sh` 可独立重跑，原始输出落 `raw/` | 能 |
| `ASSERTION` | 由 `verify.sh --only Axx` 复跑，判定在 `results/*/raw/` | 能 |
| `RECORD_ONLY` | 排障过程记录，依赖当时的临时夹具与中间态 | **不能**，只作背景 |

当前 8 份证据的分布：

```
REPRODUCIBLE  a02（断言 rank）· a03（评级推导前提与符号）
ASSERTION     a08（global 答案）· a09（代次混存与零产出）
RECORD_ONLY   n2-n4 · n5 · n6-n7-n9 · n8
```

`RECORD_ONLY` 的 `run.sh` 会直接以退出码 3 说明"不可复跑"，而不是伪造一个能跑的样子。

## 这个包不能证明什么

必须写在最前面，避免被当成"全部通过"：

```
1  契约意义上的"符合预期" —— contracts/ontology/ 仍是空的，
   "类型是否偏离目标"没有书面基准，任何 PASS 只证明"与断言一致"，不证明"与业务预期一致"
2  写操作类能力 —— A05/A10/A12/A13/A14 本轮 SKIP（上传/删除/撤权/重启/并发），
   没有任何真实执行证据
3  容量与持续运行 —— A15 未执行，没有 24h 观察数据
4  干净环境可复建 —— A16-ENG 未执行；离线包无 manifest，无法把"你跑的包"和"我验的 commit"对上
```

这三条不是自我贬低，是**举证边界**。外部复核时，超出边界的结论一律应被问回去。
