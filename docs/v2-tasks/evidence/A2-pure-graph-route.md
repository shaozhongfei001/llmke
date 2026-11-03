# T-A2 自证：D6 纯图 route 真实生效（seed 接通 + 无 rerank 兜底的 GRAPH trace + 禁用图对照）

- 任务：`docs/v2-tasks/TASKS.yaml` → `T-A2`（acceptance D6）
- 执行人：TL（tl-audit）
- 日期：2026-11-03
- 工作树：`/home/szf/data/dev/llmke-v2`，分支 `design/v2-input-engine-adoption-20261030-2101`，开工 HEAD `6dd3b4f`
- 引擎解释器：`/home/szf/data/dev/hipporag-toolenv/bin/python`（hipporag 2.0.0a4）

## 0. 结论先行（事实 / 判断分开写）

**事实**：在独立实例 `127.0.0.1:18095` 上，同一语料跑两组对照：

| 组 | `executed_route` | `reason` | `graph_calls` | `rerank_fallback` | `facts_after_rerank` | `seed_hits` |
|---|---|---|---|---|---|---|
| A（`enable_graph=true`） | `GRAPH` | `GRAPH_CALLED` | 1 | **false** | 1 | `["ent:智造贷"]` |
| B（`enable_graph=false`） | `DENSE_FALLBACK` | `GRAPH_DISABLED` | 0 | false | 0 | `["ent:智造贷"]` |

**判断**：A 组的 `rerank_fallback=false` 且 `facts_after_rerank=1`，说明图分支不是靠兜底进去的——上游
`HippoRAG.retrieve` 只在 `len(top_k_facts)>0` 时才调 `graph_search_with_fact_entities`
（`/home/szf/data/dev/hipporag-toolenv/lib/python3.11/site-packages/hipporag/HippoRAG.py:411-423`），
所以 `graph_calls=1` + `facts_after_rerank=1` + `rerank_fallback=false` 三条同时成立，才允许说"图真的执行了"。
A/B 两组的命中集合不同（rank2 分别是 `F005 客户准入条件` / `F006 授信审批权限管理办法`），也说明 A 组不是稠密结果。

## 1. 改了什么（先给 diff 位置）

| 文件 | 位置 | 改动 |
|---|---|---|
| `services/rag-alg/index_data_service/graph_engine_adapter/api.py` | `:40` | `QueryRequest.seeds: List[str]`（此前 HTTP 层**没有**种子字段，种子永远到不了引擎） |
| 同上 | `:43` | `QueryRequest.enable_graph: bool = True`（禁用图对照开关） |
| 同上 | `:114` 附近 `query()` | `eng.retrieve(req.query, seeds=req.seeds, top_k=req.top_k, use_graph=req.enable_graph)` |
| 同上 | `:158` `_install_cjk_compat` / `:179` `_ensure_cjk_compat` | 中文补丁**默认安装**（`LLMKE_V2_CJK_COMPAT=0` 可关），安装点在 `_load_engine`(`:80`) 与 `_default_build`(`:114`) |
| 同上 | `health()` | 新增 `cjk_compat` 字段，装了/没装/为什么没装都可见 |
| `.../engine_hipporag.py` | `:115` | `retrieve(..., use_graph: bool = True)` |
| 同上 | `:120-146` | 禁用图分支：清空 rerank 事实让上游走稠密，标 `DENSE_FALLBACK` / `GRAPH_DISABLED`，并在 trace 写 `facts_after_rerank=0`、`graph_disabled` |
| 同上 | `:240` | trace 增 `facts_after_rerank`（重排器自己选出几条事实） |
| 同上 | `:252-270` | `_fill_seed_hits`：中文被上游清洗成空串时，命中空实体键（`entity-d41d8cd9…`=md5("")）**不计入** `seed_hits`，改记 `seed_hits_degenerate` |
| `tests/test_graph_api.py` | 新增 `test_query_forwards_seeds_and_graph_switch` | 断言 seeds/enable_graph 原样到引擎并回显 |

改动前的工作树状态（开工时 `git status --short` 为空，HEAD `6dd3b4f`）。

## 2. 根因：为什么"以前 graph route 永远是假的"

两个独立缺陷叠加，缺任何一个都出不来 §0 那张表：

1. **HTTP 层没有种子字段**：`api.py` 原 `QueryRequest` 只有 `query/top_k`（原 `:35-37`），
   线上 trace 里 `seed_hits` 恒为 `[]`（`docs/v2-tasks/CHECKPOINT.md:27` 已记此缺口）。
2. **服务端没装中文补丁**：上游 `text_processing` 是
   `re.sub('[^A-Za-z0-9 ]', ' ', text.lower()).strip()`
   （`/home/szf/data/dev/hipporag-toolenv/lib/python3.11/site-packages/hipporag/utils/misc_utils.py:54-59`），
   中文全被清掉。补丁 `graph_engine_adapter/hipporag_compat.py` 早就存在，但**只有 `scripts/v2_*` 显式调用**，
   `api.py` 从不安装 → 18094 上事实是 `("","","5000")`、中文种子换算撞空实体。

实测（见 §4）不装补丁时，两个中文种子的换算键都是空实体键，被记为 `seed_hits_degenerate`。

## 3. 环境与操作留痕（不碰运行中服务的做法）

- **没有**改动/重启 18094（S3 在用的实例）。另外起独立实例：

```
$ cd /home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service
$ LLMKE_V2_ROOT=/tmp/tl-a2-root LLMKE_V2_SNAPSHOT=/tmp/tl-a2-root/snapshot-20261103133335-412712-g0 \
  PYTHONPATH=. setsid nohup /home/szf/data/dev/hipporag-toolenv/bin/python \
  -m uvicorn graph_engine_adapter.api:app --host 127.0.0.1 --port 18095 > /tmp/tl-a2-api.log 2>&1 &
```

- 语料：从 18094 当前快照 `/tmp/s4-root-c/snapshot-20261103000343-927116-g0` 的
  `openie_results_ner_*.json` 取 12 个块原文、配 `sources.json` 的 file_id/locator/title，
  在新实例上**重建**（这样才有中文实体键）：

```
$ curl -s -X POST http://127.0.0.1:18095/v2/graph/build -H 'Content-Type: application/json' \
    --data-binary @/tmp/a2-build.json
{"schema":"llmke.graph-api.v1","status":"BUILT",
 "snapshot":"/tmp/tl-a2-root/snapshot-20261103133335-412712-g0",
 "generation":0,"documents":12,"chunks":12,"sources":12,"facts":68,"edges":251,
 "community":{"path":".../community.json",
   "sha256":"c7c09b82894d61d0c976251df034b4508f3ed2e325c800231831f98f266e8661",
   "status":"READY","community_count":35,
   "citation_check":{"ok":true,"checked":64,...}}}
```

- health 确认补丁真的装上（不是"以为装上了"）：

```
$ curl -s http://127.0.0.1:18095/health
{"schema":"llmke.graph-api.v1","status":"ok","snapshot":"/tmp/tl-a2-root/snapshot-20261103133335-412712-g0",
 "nodes":112,"edges":251,"facts":68,
 "community":{"wired":true,"communities":35,"citation_failures":0,"citation_check_ok":true,"status":"READY"},
 "cjk_compat":{"installed":true,
   "patched":["hipporag.utils.misc_utils.text_processing","hipporag.HippoRAG.text_processing"],
   "pattern":"[^0-9A-Za-z\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff ]",
   "upstream_pattern":"[^A-Za-z0-9 ]",
   "note":"显式偏离上游：上游会清空全部中文事实"}}
```

## 4. A 组：seed 命中 + 无 rerank 兜底的 GRAPH trace

```
$ curl -s -X POST http://127.0.0.1:18095/v2/graph/query -H 'Content-Type: application/json' \
  -d '{"query":"智造贷的单户最高授信额度是多少","top_k":3,
       "seeds":["ent:智造贷","ent:授信额度"],"enable_graph":true}'
```

原样输出（`/tmp/a2-A.json`）：

```json
{
 "query": "智造贷的单户最高授信额度是多少",
 "seeds": ["ent:智造贷", "ent:授信额度"],
 "graph_enabled": true,
 "executed_route": "GRAPH",
 "reason": "GRAPH_CALLED",
 "trace": {
  "graph_calls": 1,
  "seed_hits": ["ent:智造贷"],
  "fact_candidates": 5,
  "rerank_fallback": false,
  "graph_enabled": true,
  "facts_after_rerank": 1,
  "weights_assert_skipped": false
 },
 "hit_count": 3
}
```

命中与引用：

```
 1 chunk-ddb6ef23f083b55cae3e2f2696a22da4 | “智造贷”产品说明书。…单户最高授信额度为5000万元…
 2 chunk-3b8ea08f047125a2f817ef603465321f | 星航贷额度分项说明。…单户最高授信额度为8000万元…
 3 chunk-6adc9d5f3b3fcae2b83d79adfc777c42 | 客户准入条件。制造业中小微企业须持续经营满三年…
CIT: [{"file_id":"F001","locator":"page=1;chunk=0","title":"丙-智造贷产品说明书.docx"},
      {"file_id":"F002","locator":"page=1;chunk=0","title":"丙-额度分项.docx"},
      {"file_id":"F005","locator":"page=1;chunk=0","title":"客户准入条件.docx"}]
```

三个判据逐条对应：

| 判据 | 证据 |
|---|---|
| seed 命中 | `trace.seed_hits=["ent:智造贷"]`（`ent:授信额度` 不在图里 → 未命中，如实为空项） |
| `graph_calls>0` | `graph_calls=1` |
| `rerank_fallback=false` | `false`，且 `facts_after_rerank=1` ≠ 0 → 是重排器自己选出的事实，不是兜底 |
| 命中来自图检索 | A/B 同问同参数，rank2 命中不同（A=`F005`，B=`F006`），路由与 trace 也不同 |

## 5. B 组：禁用图 → `DENSE_FALLBACK` + 原因

```
$ curl -s -X POST http://127.0.0.1:18095/v2/graph/query -H 'Content-Type: application/json' \
  -d '{"query":"智造贷的单户最高授信额度是多少","top_k":3,
       "seeds":["ent:智造贷","ent:授信额度"],"enable_graph":false}'
```

原样输出（`/tmp/a2-B.json`）：

```json
{
 "query": "智造贷的单户最高授信额度是多少",
 "seeds": ["ent:智造贷", "ent:授信额度"],
 "graph_enabled": false,
 "executed_route": "DENSE_FALLBACK",
 "reason": "GRAPH_DISABLED",
 "trace": {
  "graph_calls": 0,
  "seed_hits": ["ent:智造贷"],
  "fact_candidates": 5,
  "rerank_fallback": false,
  "graph_enabled": false,
  "facts_after_rerank": 0,
  "graph_disabled": "GRAPH_DISABLED"
 },
 "hit_count": 3
}
```

两点如实说明，避免误读：

1. `seed_hits` 在禁用组里仍非空——它描述的是"这个种子能不能换算到图里的实体键"，**不代表图被执行**；
   执行与否只由 `graph_calls` + `executed_route` 决定。
2. `facts_after_rerank=0` 是**人为清空**（`engine_hipporag.py:120-146`），不是"重排器没选出事实"；
   trace 里用 `graph_disabled` 单独标出。

## 6. 反例对照：不装中文补丁时 seed 命中是假的

同一快照、同一查询，进程内不安装补丁直接调 `HippoRAGEngine.retrieve`：

```
$ cd /home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service
$ /home/szf/data/dev/hipporag-toolenv/bin/python /tmp/probe_degenerate.py
NO-PATCH route: GRAPH GRAPH_CALLED
NO-PATCH trace: {"graph_calls": 1, "seed_hits": [], "fact_candidates": 5,
 "rerank_fallback": false, "graph_enabled": true, "facts_after_rerank": 1,
 "weights_assert_skipped": false,
 "seed_hits_degenerate": ["ent:智造贷", "ent:授信额度"]}
hit_count: 3
```

→ 不装补丁时，两个中文种子的换算键都落到 `entity-d41d8cd98f00b204e9800998ecf8427e`（md5("")），
被记进 `seed_hits_degenerate` 而**不**计入 `seed_hits`。这既证明补丁是必要的，也证明
"空实体命中"不会被当成种子证据。

## 7. 回归

```
$ cd /home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service && PYTHONPATH=. \
  /home/szf/data/dev/hipporag-toolenv/bin/python -m pytest -p no:cacheprovider \
  ../../../tests/test_graph_api.py ../../../tests/test_graph_engine_hipporag.py \
  ../../../tests/test_graph_engine_capabilities.py ../../../tests/test_graph_hipporag_compat.py \
  ../../../tests/test_graph_pipeline.py ../../../tests/test_graph_community.py \
  ../../../tests/test_graph_global.py ../../../tests/test_graph_export.py \
  ../../../tests/test_graph_normalize.py -q
73 passed in 0.52s
```

说明：`tests/test_graph_api.py` 的 `FakeEngine.retrieve` 签名同步为
`(query, seeds=None, top_k=3, use_graph=True)`——接口真的变了，假引擎必须跟上；
另新增 `test_query_forwards_seeds_and_graph_switch` 覆盖接线（不是把旧断言改松）。

## 8. 能力定级

`capabilities.CAPABILITIES["retrieve_graph_route"]` 由 `NOT_VERIFIED` 升为 `VERIFIED`，
证据指针 = 本文件 + 其 sha256（登记在 `capabilities.py` 内，**不在本文件内自引**，避免指纹自引用）。

`retrieve_graph_route_with_cjk_patch` 保持 `VERIFIED`，但它的前置条件已改变：
补丁现在由服务端**默认安装**并在 `/health.cjk_compat` 可见，不再依赖脚本显式调用。

## 9. 未做项（不补充理由，只列事实）

| 项 | 状态 |
|---|---|
| 产品链路（Java → 19532 shim → 18094）透传 seeds | **未做**。`retrieval_shim.py:416-417` 只发 `{"query","top_k"}`；该文件属 S3 分工，本任务未改。因此"产品页面查询带种子"仍不成立。 |
| Java 侧种子识别 | 未验证（本次只在 18094 边界验证） |
| 页面级 E2E | 未做（属 T-A1/D7 范围） |
| 18094 运行实例 | 未重启，仍跑旧代码（无 seeds 字段）。要用新能力需重启它——**未擅自重启**。 |
