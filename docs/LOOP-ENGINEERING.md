# Loop Engineering V2

## 进入条件

schema_version=2；kind 为 contract/diagnostic/implementation；LOOP与PROJECT-PLAN依赖一致。每个gate引用受控catalog中的完整argv、类型和required_checks，禁止自由shell。implementation必须有p0_strict_gate且其余gate传递依赖它；业务前置也在执行前统一重查。

## 状态和接力

STATE.json是唯一权威，包含 revision/status/blocked/baton_holder/attempts。允许 DRAFT→IN_DEV、BLOCKED→IN_DEV 仅通过 TL arm（需要条件真实满足）；IN_DEV→QA_PENDING→DONE；失败保留记录；DONE不再执行。独立签署缺失时不得DONE。

```bash
python3 scripts/loop_guard.py arm --loop L1 --to backend-engineer --executor tech-lead --expected-revision 1
python3 scripts/loop_guard.py baton-transfer --loop L1 --to python-engineer --executor backend-engineer --expected-revision 2
python3 scripts/loop_guard.py run-gate --loop L1 --gate p0_strict_gate --executor python-engineer
```

示例revision必须读取当前STATE，不能照抄；当前原四P0 OPEN，第一条arm应失败。transfer不隐式解锁BLOCKED。锁内读状态、CAS并原子替换单文件，渲染视图不是分布式事务。

## 执行

统一入口先验证kind、前置、holder、catalog、预算及旧证据是否仍对应当前快照。持久预扣一次attempt，再执行shell=False argv；进程中断也消耗次数。失败先追加FAILURES/events，记录退出码，不保留旧PASS冒充本次成功。

同gate最多3次（模板值，允许受控1–5）；耗尽STOP。修复原因和影响登记后由TL创建新批次/新修订；不能删日志或手动清零计数。通过条件必须由命令和真实测试实现，文本不产生断言。

## QA与完成

普通run-gate不能把qa_gate标为PASS。外部QA runner在干净、固定版本工作区执行qa-run，得到QA_PENDING候选日志；由未参与实现的真实QA身份签署 payload（含源码/控制基线/gate/日志摘要与检查集），accept-qa验签后才转PASS；finish重新检查全部门禁才写DONE。

外部信任配置、公钥、批准基线摘要和私钥权限由受保护环境管理员配置，见QA-TRUST.md。本地可以验证算法与合成签名夹具，不能由此声称已完成独立业务QA。
