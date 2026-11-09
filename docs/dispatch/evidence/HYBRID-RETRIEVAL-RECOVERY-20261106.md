# 图栈故障恢复记录（2026-11-06 ~ 11-07）

执行身份：tech-lead（TL）。触发：用户询问「系统是否正在运行」，探测发现图能力已中断。

## 故障现象

- Java 6 服务、算法 4 服务、ES/Milvus/MySQL/模型服务全部 RUNNING，但**业务不可用**：
  - `19995 /retrieval_documents_global` → `msg=无相关社区事实`、`global_answer` 为空
  - `19995 /retrieval_documents` → `search_type=['es']`（正常应为 es+milvus+graph）
  - 19995 日志：`V2 global 查询失败，转图检索回退: All connection attempts failed`
- 18094 HippoRAG、19531 建图 shim **未监听**。
- 已下线的 V1（19529 + Nebula×3）**被重新拉起**。

## 根因（两条叠加）

1. **`/tmp` 被清空**：`/tmp/tl-a2-root`（18094 图快照）、`/tmp/kb-artifact-store`（kb_state.json +
   doc2md 四件套）、`/tmp/doc2md-fullrun` 全部丢失。阶段 5 建好的 kb_9(46)/kb_1004(4520)
   图与重建数据源一起没了。
2. **`r12-watchdog.sh` 仍按 V1 拓扑守护**：TARGETS 里 `graphsvc|19529|r12-graphsvc|unit-restart`
   每 45s 把 19529 拉回；CONTAINERS 里的 `r12-nebula-*` 每 45s `docker start` 拉回。
   而 18094/19531 不在任何守护列表里，挂了无人自愈。
   `r12.target` 的 `Wants=r12-graphsvc.service` 又会在整栈启动时复活 V1。

## 恢复动作

| # | 动作 | 结果 |
|---|---|---|
| 1 | 新建持久化图根 `platform/r12/data/graph-root`，拉起 18094 | ✅ 不再依赖 /tmp |
| 2 | 新增 `scripts/v2_graph_rebuild_from_es.py`：从 ES 统一 pk 重建图 | ✅ 不需重新解析 48MB PDF |
| 3 | 重建 kb_9（44 text + 2 table = 46 doc） | ✅ `status=BUILT` 128s，communities=30 |
| 4 | 重建 kb_1004（4520 doc） | ✅ `status=BUILT` 11910s≈3h18m，communities=1540 |
| 5 | 拉起 19531 建图 shim（同一持久化 root） | ✅ health 显示 root 正确 |
| 6 | 停 19529 + Nebula×3，`mask r12-graphsvc.service`，同步 r12.target | ✅ 100s（>2 巡检周期）未复活 |
| 7 | watchdog 收敛到 V2：TARGETS 改 hipporag(18094,19531)、新增 `graph-v2` heal、移除 nebula 容器 | ✅ 自愈实测通过 |
| 8 | 修正启动脚本「端口在即健康」误判，加 openapi.json 探针 | ✅ watchdog 也加 HTTP 探针双保险 |

## 验证结果

- **重启 18094 后自动加载持久化快照**：kb_9=46、kb_1004=4520，**无需重建**（核心改进自证）。
- **三者对齐**：kb_9 ES=44(+2 table) / Milvus=44 / 18094=46；kb_1004 ES=4520 / Milvus=4520 / 18094=4520。
- **三路融合**（kb_9）：`授信额度是多少` 召回 4 条，`search_type=['es','graph','milvus']`。
- **global 双库**：kb_9 社区命中 6 条（5000万+增信方式准确）；kb_1004 命中 4 条（英文种植步骤）。
- **自愈实测**：kill 19531 → watchdog 3 次 FAIL → `graph-v2` 修复 → 13s 内自动拉起；
  启动脚本幂等（18094 跳过、19531 拉起）。
- **防复发**：等 100s（>2×45s），19529/19559/19669/19779/19532 全部仍停，Nebula 容器 Exited，
  `r12-graphsvc` = masked，watchdog `不健康组数=0`。

## 如实标注：1 个既有边界（非本次恢复引入）

kb_1004 的 `19995 /retrieval_documents` 对英文 query 仍只回 1 条 `['es']`。诊断：
19526 milvus 单独检索有 3 条（score 0.694）、18094 graph 单独检索 `GRAPH` 5 命中，
19995 也确实向两路都发了请求（日志可证），只是融合后未并入结果。
该现象在故障前（阶段 0 基线）即存在，不属于本次恢复的回归，未在本切片内改动。

## 回滚说明

- `r12-graphsvc.service` 只是 mask（源文件仍在 `platform/r12/systemd/`），`unmask` 即可恢复 V1。
- Nebula 容器是 `docker stop`，数据卷未删。
- 旧图根 `/tmp/tl-a2-root` 已随 /tmp 清理不复存在；新图根持久化，不受 /tmp 清理影响。
