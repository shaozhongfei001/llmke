# STEP2-F 生产切读窗口 Runbook（受限）

> 配套证据：`docs/v2-tasks/evidence/STEP2-E-FULL-REBUILD-ISOLATION-20261112.md`
> 目标任务书条目：T-D2MD-17（P6 kb_9 影子切读 + delta 策略）

## 目标

把 `kb_9` 的 18096 摄取从 **shadow 根**切到**生产 app 图根**，并对 `kb_9` 执行
`FULL_REBUILD` / `UPSERT`，重建 46 块 / 11 文件，验证**不削数据**、查询可读、重复请求短路。

## 当前实测事实（2026-11-12，来自 `/proc` 与代码 grep）

- 18096 运行 pid `46796`，关键 env：
  - `LLMKE_V2_GRAPH_ROOT=/home/szf/data/dev/llmke-runtime/shadow/graph-root`
  - `LLMKE_ARTIFACT_STORE=/home/szf/data/dev/llmke-runtime/shadow/artifact-store`
  - `LLMKE_V2_GRAPH_API=http://127.0.0.1:18094`、`ES/Milvus=19527/19526`
- 生产 app 图根真相：`/home/szf/data/dev/llmke-runtime/app/platform/r12/data/graph-root/kb_9`
  （`documents=46, per_file=11`，与影子根 `4/3` 分离）。
- 隔离机制验证（STEP2-E）：`FULL_REBUILD` 重建**整个** kb（保留所有已注册 file_id），
  **连续 FULL / DELTA 累积均不削**；删 ES/Milvus 调用均回「不存在/无需删除」（隔离 build
  未写远端向量库）。
- **标准切读开关 `INGEST_READ_MODE` / `INGEST_READ_KBS` 在 18096 当前代码未实现**
  （`services/rag-alg/index_data_service` 下 grep 无命中，仅有 `isolated_snapshot_rebuild`
  能力声明与 `global_report` 的 snapshot 读取）。T-D2MD-17 原设计的「按 kb 粒度切 read」路径
  代码尚未就绪。
- 部署仓 `llmke-r12/platform/r12/conf/kb-ingest.env` **缺失**，systemd unit 现不可启动；
  当前 18096 进程是手动 env 注入启动（env 残留在 `/proc`）。

## 切换路径 A：图根式切读（当前唯一可行）

1. **核对生产 app 根 artifact-store 路径**（与 `graph-root` 同级的 `artifact-store`），并确认
   11 份四件套为**标准 doc2md 四件套**（含 `document_ir.json`、无非预期顶层文件）。
   隔离演练教训：`c5edbe` 缺 `document_ir.json`（旧 3 项格式）、`shadow-backup/artifact-store`
   下 4 份含多余 `artifact.json` 顶层文件，均会被 18096 拒绝（`MISSING_PART` / `UNKNOWN_TOP_LEVEL_FILE`）。
2. **停 19531 生产 build**（通道互斥，切换窗口内不得并发写同一 root）。
3. **重启 18096**，注入生产 env：
   - `LLMKE_V2_GRAPH_ROOT=/home/szf/data/dev/llmke-runtime/app/platform/r12/data/graph-root`
   - `LLMKE_ARTIFACT_STORE=<生产 app 根 artifact-store 路径>`
   - 其余（`GRAPH_API` / `ES` / `MILVUS` / `DOC2MD_CONFIG` / `DOC2MD_LOCK`）保持当前值。
   - 重启方式：kill 当前 pid → 用 `r12-kb-ingest-start.sh` 或手动 env 注入 `nohup uvicorn`，
     走 `services/rag-alg/index_data_service`，**不要**依赖缺失的 unit/env 文件。
4. 对 `kb_9` 发 `POST /kb/ingest`：遍历 11 文件四件套
   - 方式一：首文件 `FULL_REBUILD`（建基线）→ 其余 `UPSERT`（累积）
   - 方式二：直接 11 次 `UPSERT`
   - 两者实测均不削（见 STEP2-E）。若当前指针已含 11 文件且四件套未变，`diff=NO_CHANGE`
     直接 `SKIPPED_FRESH`，零重建。
5. **回归查询**：`/v2/graph/query` 命中 46 块、来源覆盖 11 文件、`route=GRAPH`；重复相同
   请求返回 `SKIPPED_FRESH`（零重建、响应稳定）。
6. **回滚**：18096 改回 `shadow/graph-root` + `shadow/artifact-store` 重启即可（图根切换是
   进程级 env，无持久化破坏；生产 app 根数据不被篡改，仅 18096 的读取/写入落点变化）。

## 切换路径 B：标准 snapshot 切读（INGEST_READ_MODE）

- 代码未实现，待 P6 收敛。实现后：`INGEST_READ_MODE=snapshot` + `INGEST_READ_KBS=[kb_9]`，
  按 kb 粒度切 read，无需改图根目录。届时以该路径替代路径 A 第 3 步。

## 真实外部阻塞（需 Owner 授权 / 裁定）

- **`@Lazy` 授权**（P5-0b，Nebula 退役后 graph-service 启动期连库失败）：T-D2MD-14。
- **12340 退役**待 **G-1 裁定**（`database_desc` 是否保留只读子集）：T-D2MD-16。
- **图 root env 变更属生产变更，需 Owner 授权**（改 18096 指向生产 app 根）。
- 任务书依赖链：`17 ← 16 ← 15 ← 14` 未闭环，故 T-D2MD-17 当前 `state=TODO` 不应直接执行。

## 前置核对清单（执行路径 A 前逐项打勾）

- [ ] 生产 app 根 `artifact-store` 路径确认
- [ ] 11 份四件套标准格式确认（含 `document_ir.json`、无多余顶层文件）
- [ ] 旧软链指针 `kb_9/current.json` 的 `dir` 指向已删 `llmke-r12/…` → 切后首写刷新
- [ ] 19531 可停（窗口内）
- [ ] Owner 授权图 root env 变更 + `@Lazy`、`G-1` 前置闭环

## 风险提示（来自 STEP2-E）

- 之前「切到生产 root 会按影子 manifest 把图削成 3 文件」是**未实测假设**，已被否定；
  真实风险更小——只要 18096 指向正确生产 root 且生产 root 上 `kb_9` 快照完整（现状 46/11），
  切换安全。
- 仍须警惕的格式门槛：四件套必须标准；非标准会被拒绝而非静默空结果。
- 切换窗口内严禁 19531 并发写同一 root（通道互斥）。
