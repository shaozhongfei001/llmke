# STEP2-I 接手核证与阻塞登记（T-D2MD-17 / 2026-11-12）

> 接手来源：`docs/v2-tasks/HANDOVER-20261112.md`、`TASKS.yaml` 的 `T-D2MD-17`(IN_PROGRESS)。
> 本轮性质：**只读核对 + 一次离线零风险验证**。未启动/停止/重启任何服务，未写入生产图根，未改任何状态结论，未执行 `git add` / `git commit`。
> 纪律：每条结论附可复跑命令或文件:行号；事实 / 推断 / 判断分开标注。

---

## 一、纠正交接单中过时或不准确的事实（实测）

| # | 交接单 / 要点表述 | 实测事实 | 可复跑来源 |
|---|---|---|---|
| 1 | 「STEP2-E/F/G/H 与 TASKS.yaml 均在本地工作树（未提交）」 | **STEP2-E/F 已在 `d2af1e6a` 提交**；未提交仅 `TASKS.yaml`(M)、`HANDOVER-20261112.md`、`STEP2-G`、`STEP2-H`(??) | `git status --short`、`git log -1 --oneline` |
| 2 | 「todo 2-8 尚未动手」 | **todo 1~3 已落地**（11:27–11:54 产物）：6 份源、6 份标准四件套、`current.json` 指针已修 | 见 §二 |
| 3 | 「18094/18096/19531/19532 + Java 均 LISTEN」 | 成立；另**多出** `18097 kb_parse_service`(pid 181090)、`12340`(pid 3292180) 仍 LISTEN，及第二个 rag-index-service(pid 3293253) | `ss -ltnp`、`ps -eo pid,ppid,lstart,cmd` |
| 4 | 「生产 `current.json.dir` 指向已删 llmke-r12（失效指针）」 | **已修复**：现指向 `llmke-runtime/app/platform/r12/data/graph-root/kb_9/snapshot-20261107212905-365431-g0`（实测存在），并留 `current.json.bak.20261112` | `diff -u current.json.bak.20261112 current.json` |
| 5 | 「`llmke-v2` / `llmke-r12` worktree」 | 两者在 `/home/szf/data/dev/` 与 `/home/szf/dev/` **均已不存在**；运行代码在 `llmke-runtime/app/` 与发布树 `llmke/` | `ls -ld ...`、`readlink /proc/<pid>/cwd` |
| 6 | 「生产 graph-root 三副本」 | 实测 **6 个** `kb_9` 副本（app / data / legacy-r12 / shadow / shadow-backup / legacy-shadow），artifact-store 3 个 | `find llmke-runtime -type d -name kb_9` |
| 7 | STEP2-H 记「xlsx 解析 FAILED」 | `parse_queue.json` 标 `PARSE_FAILED`，但 `53d265c7` 四件套实测 `status=SUCCESS` —— **队列状态陈旧，产物已可用** | 各 `parse_manifest.json` |

---

## 二、当前真实状态（接手基线）

### 运行态（现查，非 11-08 旧值）

| 端口 | 服务 | PID | env 关键项 |
|---|---|---|---|
| 18094 | `graph_engine_adapter.api:app`（双 worker） | 1464293 / 1466203 | `LLMKE_V2_SNAPSHOT=<app graph-root>/snapshot-20261111121015-000516-g0`，**无 `LLMKE_V2_ROOT`** |
| 18096 | `kb_ingest_service:app` | 46796 | `GRAPH_ROOT=shadow/graph-root`、`ARTIFACT_STORE=shadow/artifact-store`、`KB_STATE=shadow/kb-state/kb_state.json` |
| 19531 | `legacy_shim:app` | 46795 | `LLMKE_V2_ROOT=<app>/platform/r12/data/graph-root` |
| 19532 | `retrieval_shim:app` | 1464291 | upstream 18094 |
| 18082 / 18084 | Java rag-index / rag-graph | 46793 / 46794 | r12 conf |
| 18097 / 12340 | kb_parse_service / 旧解析 | 181090 / 3292180 | 交接单未列，仍 LISTEN |

`/health` 只读实测：18094 `9 节点/16 边/5 事实/1 社区`；18096 `store_root=shadow/artifact-store`、`graph_api=18094`；19531 `root=<app>/platform/r12/data/graph-root`。

### 产物与指针

- 6 份源：`coordination/kb9-rebuild-corpus/`（sha256 见下），与 STEP2-H 所列 6 份非 PDF fixtures 一致。
- 6 份标准四件套：`doc2md/parsed/by_hash/<sha 前 2>/<次 2>/<sha>/`，全部含 `document_ir.json` / `parsed_metadata.json` / `parsed_text.md` / `parse_manifest.json`，无多余顶层文件，`parse_manifest.status=SUCCESS`、`parser_name=markitdown`。
- 另有 `275eccb8…`（`parse_queue.json` 自身被当文档解析）与 `c5edbeaf…`（旧 3 件、缺 `document_ir.json`）—— **均不得计入 6 份语料**。
- 生产 `kb_9/current.json`：`documents=46`，`fingerprint.files` = `290/329/330/331/332/333/334/343/999016/999019/999020`（11 份），`dir` 已指向现存 snapshot。

### 本轮完成的离线验证（零生产风险）

对 6 份 `doc2md_dir` 逐一调用 `kb_pipeline.commit_snapshot()`（即 18096 `_commit_snapshot` 的同一入口），写入隔离 store `coordination/.p6-probe-store`，**6/6 成功**，各得独立 `artifact_id`，验证 STEP2-E 指出的「标准四件套格式门槛」不再阻塞；临时 store 已删除。

```
aa8f26b9 -> 519efc69…  50f2740f -> a9295c80…  efd100b7 -> 6713cc90…
f4982001 -> b958704b…  a846ab14 -> bad52b5e…  53d265c7 -> fd537daf…
```

---

## 三、新发现的两个真实阻塞（本轮核心，**交接单与 STEP2-E/F/H 均未识别**）

### B-1（阻断 todo 4/5）：`LLMKE_KB_STATE` 与生产图根不同源 ⇒ 会用影子 state 覆盖生产图

- **事实**：18096 的 `LLMKE_KB_STATE=/home/szf/data/dev/llmke-runtime/shadow/kb-state/kb_state.json`，其 `kb.kb_9` 活跃 file_id = `290/291/292/293`（4 个，P4-L13-C5 演练遗留）；生产 `kb_9/current.json` 为 11 个 file_id，**仅 `290` 重叠**。
- **事实**：`kb_delta.py:546-548` 用 prospective state 调 `build_wanted_docs()`；`kb_pipeline.py:453-479` 明确「从 `kb_state.chunks` 组装该库**全量** wanted docs」；该 `wanted` 经 `kb_delta.py:576` → `graph_client.post_graph_delta()` → 18094 `delta_build.py:273-274` 成为 `live`；`:306` `rebuild_delta(root, fence, live, ...)` **按 live 重建整个 kb**，`root = <graph_root>/<kb>`（`:51-58`）。
- **判断**：若只改 `LLMKE_V2_GRAPH_ROOT` / `LLMKE_ARTIFACT_STORE`（STEP2-F 路径 A 第 3 步）而不同步切换 `LLMKE_KB_STATE`，POST 6 份会把生产 `kb_9` 图谱按「shadow 4 文件 + 6 个新 id」重建 —— **不是「不削」，而是替换掉生产 46/11**，直接违反红线「不动 `platform/r12/data` 生产图数据」。
- **判断**：STEP2-H「`removed` 恒空 ⇒ 切读不削」只覆盖 `diff.removed`（`kb_delta.py:325-396`），未覆盖 `wanted_docs` 的全量装配；STEP2-E 隔离演练使用**同一实例累积的 kb_state**（2 文件），从未构造「state 与 root 不同源」这一生产形态，故其「不削」结论**不可外推到路径 A**。
- **恢复条件**（三选一，需 Owner 裁定）：① 提供与生产 11 file_id / 46 块同源的 `kb_state`（本机无，STEP2-G 已证四件套不可得）；② 改为纯只读切换验证（不 POST）；③ 在**隔离副本 root** 上先做同源 state 演练，实证 `documents` 与 11 文件集合不变后再谈生产。

### B-2（阻断 todo 6）：runbook 的「查询可读」判据在当前 18094 配置下不可达

- **事实**：只读实测 `POST /v2/graph/query {"kb":"kb_9","query":"日均存款","top_k":3,"enable_graph":true}` → `{"status":"NOT_BUILT","hit_count":0,"docs":[]}`。
- **事实**：18094 env 无 `LLMKE_V2_ROOT` → `_root_dir()`（`api.py:188-189`）回退 `.artifacts/api-root`（实测为空）；`_resolve_snapshot()`（`:208-231`）按库解析失败，且 env 单快照目录**无 `kb.json`**，`_snapshot_owner()` 不认领；`QueryRequest`（`:56-65`）**无 `root` 字段**；`graph_delta`（`:563`）仅在 `_is_own_root(...)` 为真时更新内存槽，生产 root ≠ 本进程 root ⇒ 不更新。
- **判断**：STEP2-F「回归查询命中 46 块、来源覆盖 11 文件」在**未重启 18094 并设 `LLMKE_V2_ROOT`、或未给 `QueryRequest` 增加 `root`（属新边界，需 CR）**之前不可达；即使完成切读写入生产 root，查询仍为 `NOT_BUILT`。
- **恢复条件**（三选一，需 Owner 裁定）：(a) 授权重启 18094 并设 `LLMKE_V2_ROOT=<生产 graph-root>`；(b) `QueryRequest` 增 `root` → 合同源 + CR + 重启；(c) 把 todo 6 验收改为「比对 `kb_9/current.json` 的 `documents` / `fingerprint.files` 指纹 + 快照目录可读性」，不依赖 `/v2/graph/query`。

---

## 四、依赖链与系统阻塞（复核，仍成立）

- 依赖链 `17 ← 16 ← 15 ← 14`：14 `DOING`、15/16 `TODO`；**G-1**（`database_desc` 是否保留 12340 只读子集）未裁定，实测 12340 仍 LISTEN。STEP2-F §62 明确「依赖链未闭环，17 不应直接执行」。
- **G-4**：独立 QA principal / 公钥缺失 → `T-D2MD-01~12` 保持 `WAIT_QA_ATTESTATION`，不补签、不声称 `QA_PASS`。
- ①②③ 类阻塞现状：① 标准 snapshot 切读开关仍未实现（走路径 A 图根式，需重启 18096）；② 部署仓 `kb-ingest.env` 仍缺失（18096 为手动 env 注入裸进程，可按 runbook 手动重启，非硬阻塞）；③ 四件套不可得已由「6 份重建」决策覆盖且本轮验收通过；④ 指针已修。

---

## 五、todo 状态修订（本轮结论）

| todo | 状态 | 依据 |
|---|---|---|
| 1 探索 doc2md 生成入口 | 已完成 | `scripts/v2_ingest_doc2md.py` + `doc2md/parsed/by_hash` |
| 2 重生成 6 份四件套 | 已完成并本轮验收 | 6/6 `commit_snapshot` PASS、manifest `SUCCESS` |
| 3 修 `current.json` 指针 | 已完成 | 11:54 修改 + `.bak.20261112` + 目标 snapshot 存在 |
| 4 停 19531 + 改 env + 重启 18096 | **BLOCKED** | B-1；且需 Owner 确认授权窗口仍开放 |
| 5 POST 6 份 | **BLOCKED** | B-1（会用影子 state 覆盖生产图） |
| 6 验证不削 / 查询可读 / 短路 | **BLOCKED** | B-2（查询判据不可达） |
| 7 证据提交 git | **待「提交一次 git」指令** | 本文件、`STEP2-G/H`、`HANDOVER`、`TASKS.yaml` 均留本地工作树 |
| 8 台账流转解锁 `T-D2MD-18` | **不得执行** | 17 未验收；18 保持 `TODO`，`G-2` 阈值未放行 |

---

## 六、恢复条件（最小可执行）

1. Owner 就 **B-1**（同源 `kb_state` 方案 / 是否改为只读切换 / 隔离副本演练）与 **B-2**（是否授权重启 18094 设 `LLMKE_V2_ROOT`，或改验收口径）作出裁定。
2. 若选「纯只读切换」：可仅改 18096 env 指向生产 root 做 `/health` 与指针核对，不 POST、不写图，零数据风险。
3. 若选「隔离副本演练」：复制生产 `kb_9` 46/11 快照到隔离 root，用独立 18096 实例 + **同源 kb_state** 跑 6 份，实证 `documents` 与 11 文件集合不变后再申请生产窗口。
4. G-1 闭环、G-4 补齐独立 QA 主体 / 密钥后，方可讨论 17 的验收与 18 的解锁；本轮不代签、不自证。

---

## 七、纪律留痕

- 本轮命令均为只读（`ps` / `ss` / `curl /health`、`/v2/graph/query` / `ls` / `cat` / `grep` / `diff` / `find` / `python` 读文件），外加**一次离线** `commit_snapshot`（写入并清理 `coordination/.p6-probe-store`，已确认删除）。
- 未停 / 重启任何服务；8 个生产端口保持 LISTEN；本轮**未写入** `platform/r12/data`（`current.json` 的 11:54 修改发生在本轮接手之前，非本轮动作）。
- 未执行 `git add` / `git commit`；未改 `generated/`；未改合同；未自签 QA、未声称 `QA_PASS`。
- 事实与结论分离：§一/§二/§三 的「事实」条目均可复跑；「判断」条目是依据代码路径作出的推断，需按 §六 的实测方案证伪或确认。
