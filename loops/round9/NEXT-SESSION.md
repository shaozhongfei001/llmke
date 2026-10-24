# ROUND9 续跑说明（2026-10-24）

## 一句话

代码与证据交付已完成（18 任务：10 VERIFIED / 3 VERIFIED_DRYRUN / 4 BLOCKED_EXTERNAL / 1 BLOCKED_WINDOW）；
**四项 P0 仍全 OPEN**，业务不可开工；轮次是否关闭由业主裁定。

## 下一条命令

```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH
~/data/dev/coordination/mysql-probe.sh start
make framework-verify > /tmp/fv.log 2>&1; echo "rc=$?"; grep -E "passed|security" /tmp/fv.log | tail -2
python -m pytest modules -q > /tmp/m.log 2>&1; echo "rc=$?"; tail -2 /tmp/m.log
~/data/dev/coordination/round9-index.py | head -20
```

## 已完成（勿重做）

- 纵向切片：`modules/answer_api/`（query→授权取块→证据→答案→HTTP 状态码），40+ 条测试含 5 条真库
- 代次守卫（只取 ACTIVE 代次，真库 4 条）；outbox 投递语义（真库 3 条）
- 两个 dry-run 工具：P0-01 清单审计、P0-02 三产物对账
- 摘要缺口实测 + `command_digest` 可行性验证（均 DRY_RUN，未落地）

## 未完成（全部依赖外部）

见 `P0-INPUTS.md`（四项 P0 输入表）与 `ROUND10-INPUTS.md`（DAG + owner 清单）。

## 关键约束

1. 新批次会作废 r11（`loops/*/LOOP.yaml` 属控制面）；
2. 控制面改动必须"先全部落盘 → 一次冻结 → 再跑门禁"；
3. `command_digest` 落地前，"验证脚本被改"仍不被摘要覆盖（R9-T13 实测）；
4. 不得把 `route export` 当作 `IN_USE` 证据；不得声称"块级代次已绑定"（目前只按版本对齐）。
