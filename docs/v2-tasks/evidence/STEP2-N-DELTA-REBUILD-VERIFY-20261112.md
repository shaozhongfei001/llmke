# STEP2-N delta 重建分支「不削」实证（T-D2MD-17 / 2026-11-12）

> 补齐 `STEP2-M` §三 登记的缺口：生产窗口的 6 份 POST 都判 `freshness.stale=False` → `SKIPPED_FRESH` 零重建，因此「delta **重建分支执行后**仍不削」未验证。
> 本轮在**隔离副本 root** 上让重建分支真实执行，**不碰生产图、不重启服务、不发 HTTP、不写 ES/Milvus**。

---

## 一、方法（可复跑）

入口：`scripts/p6_delta_rebuild_probe.py`

```
cd /home/szf/data/dev/llmke
<hipporag-toolenv>/bin/python scripts/p6_delta_rebuild_probe.py            # 真实 apply_fn
<hipporag-toolenv>/bin/python scripts/p6_delta_rebuild_probe.py --light    # 不调 LLM 的降级路径
```

1. **副本**：复制生产 `kb_9/`（`current.json` + 2 个快照）到 `coordination/p6-window-20261112/replica/<case>/graph-root/kb_9/`，并把副本指针的 `dir`/`previous` 改指向**副本内部**快照 —— 确保 `rebuild_delta` 的 `base_dir` 不指向生产目录。
2. **触发 stale**：`rebuild.py:82-108` 的 `check_freshness` 比对 `docs_fingerprint(live)` 与指针 `fingerprint`。从生产快照派生同源 `live`（46 行 / 11 file_id），**只改 `290` 的一块文本** → `changed=['290']` → `stale=True`。
3. **真实重建**：进程内直接调 `graph_engine_adapter.delta_build.delta_build()`，`root=<副本 graph-root>`、`requested_mode=auto`（`_resolve_mode` 默认 → `DELTA`），**不注入 apply_fn**，使用真实 `_default_apply` → `HippoRAGEngine.apply_delta()`（实测日志有 NER / 三元组抽取 / LLM 与 embedding 调用）。
4. **变异复验**：换成 shadow 4 文件 `live`，对变异体执行**同一个**「11 个 file_id 全在」判据，必须 FAIL。

---

## 二、实测结果（真实 apply_fn，`delta-rebuild-probe.json` 留痕）

```
verdict = PASS      apply_mode = real (_default_apply, 调 LLM/embed)
status  = BUILT     effective_mode = DELTA
freshness = {stale: True, reason: SNAPSHOT_OUT_OF_DATE, changed: ['290']}
```

| 判据 | 窗口前 | 重建后 | 结论 |
|---|---|---|---|
| `documents` | 46 | **46** | 不削 |
| `fingerprint.files` | 11 个（290/329/330/331/332/333/334/343/999016/999019/999020） | **完全相同的 11 个** | **不削** ✔ |
| `sources.json` 的 file_id | 11 个 | **11 个全在** | 旧块保留 ✔ |
| `mode` | FULL | **DELTA** | 走的是增量分支 ✔ |
| 指针 `dir` | 副本内 `snapshot-20261107212905-365431-g0` | 副本内**新快照** `snapshot-20261112190738-230055-g0` | 指针真实推进 ✔ |
| `fencing` | 1 | **2** | CAS 递增 ✔ |
| 新快照文件 | — | `community.json` / `fence.json` / `kb.json` / `llm_cache` / `openie_results_ner_*.json` / embedding 目录 / `sources.json` | 收口完整 ✔ |

**引擎真实增量结果**（非替身）：
```
apply_result = {deleted: 0, added: 1, reused: 30, duplicates: 15,
                remaining: 31, expected: 31, consistent: True}
```
即：改动的 1 块被加入、30 块复用、**0 块删除**，`consistent=True`。这正是「不削」的引擎级证据。

**变异复验**：shadow 4 文件 `live` 重建后 `fingerprint.files = ['290','291','292','293']`，判据捕获
`mutant lost prod file_ids: ['329','330','331','332','333','334','343','999016','999019','999020']`（丢 10 个）。
→ 「11 个全在」断言**不是空转**：输入换成错误 state 就会 FAIL，精确复现 B-1 的风险形态。

**零生产风险核验**：
- 生产 `current.json` sha256 前后同为 `fa650c7de99237ad0690e673f83d8788054f20f6c928c810a880b82756ab97d6`。
- 8 端口全 LISTEN；18094/18096/19531/19532 `/health` 全 200；`r12-watchdog.timer` 保持 `active`。
- 副本目录 11 MB 已清理（脚本可复跑），保留 `delta-rebuild-probe.json`、`delta-probe-real.stdout`、`delta-probe-light.stdout`。

降级路径 `--light` 亦 PASS（替身 apply_fn，不调 LLM），其 `apply_result` 明确标注 `light-apply (no LLM)`，未被当作正式证据。

---

## 三、结论与边界

- **结论**：`STEP2-M` 的缺口已补上 —— delta **重建分支真实执行后**，`current.json` 的 `documents` 与 11 个 `fingerprint.files` 不削，旧块在 `sources.json` 中保留，引擎 `deleted=0`。这与 `STEP2-J` 的 `wanted_docs` 层证据、`STEP2-M` 的生产窗口证据形成完整链条：
  1. `STEP2-J`：同源 state 下 6 份 POST 的 `wanted_docs` 始终含 11 个 file_id（编排层）；
  2. `STEP2-N`：真实 `rebuild_delta` 后指针指纹仍为 11 个（引擎/指针层）；
  3. `STEP2-M`：生产切读配置生效、查询可读、幂等短路、生产数据零改动（运行态层）。
- **不扩大的边界**：本次重建发生在**隔离副本**，生产图仍保持窗口后的状态（未被重建）。不声称「生产图已完成重建」，也不声称「查询等价性已验收」（`T-D2MD-18` 的 50 条固定 query 对照未做）。
- **状态判定**：工程侧可执行验证已闭环，但 `T-D2MD-17` **仍保持 `IN_PROGRESS`，不标 `VERIFIED`、不签 `QA_PASS`** —— G-4 独立 QA 主体/公钥缺失、G-2 放行阈值未就绪、依赖链 `17←16←15←14` 未闭环，均属真实外部阻塞（禁止自签 QA）。`T-D2MD-18` 保持 `TODO`。

---

## 四、纪律留痕

- 未启动/停止/重启任何服务；未改生产图根、未写 ES/Milvus、未发 HTTP 到生产端点。
- 失败与降级路径如实保留（`delta-probe-light.stdout` 及脚本内 `--light` 标注）；变异复验曾出现措辞误导与判据方向写反，两处均已修正后重跑，未删失败记录。
- 未执行 `git add` / `git commit`；未改 `contracts/`、`generated/`；本文件、`scripts/p6_delta_rebuild_probe.py`、台账与检查点改动全部留本地工作树，待「提交一次 git」指令。
