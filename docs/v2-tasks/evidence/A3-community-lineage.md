# T-A3 自证：D4 社区同源（openie → 断言 → export_facts → build_communities → community.json）

- 任务：`docs/v2-tasks/TASKS.yaml` → `T-A3`（acceptance D4）
- 执行人：TL（tl-audit）
- 日期：2026-11-03
- 快照：`/tmp/tl-a2-root/snapshot-20261103133335-412712-g0`（12 块 / 68 抽取三元组 / 引擎图 112 节点 251 边）
- 脚本（已落仓）：`scripts/v2_a3_lineage_probe.py`
- 解释器：`/home/szf/data/dev/hipporag-toolenv/bin/python`

## 0. 结论

一条真实中文事实 **`智造贷 适用于 制造业中小微企业`** 的五跳全部闭合：

| 跳 | 载体 | 实测 |
|---|---|---|
| 1 openie | `openie_results_ner_qwen2.5-7b-instruct.json` | 三元组在 `chunk-ddb6ef23f083b55cae3e2f2696a22da4` 的 `extracted_triples` 里；同块原文含"适用对象为制造业中小微企业" |
| 2 normalize → 断言 | `AssertionStore._assertions` | `subject=智造贷 predicate=适用于 object_entity=制造业中小微企业 direction=forward`，`sources=[{file_id:F001, locator:page=1;chunk=0}]`，`render=智造贷 适用于 制造业中小微企业` |
| 3 export_facts | 标准事实导出 | `facts=67 excluded=0`，该事实 `content_key` 在导出集合内 = True |
| 4 build_communities | 确定性标签传播 | 35 个社区；该事实主体落在 `c-3`（size=5, isolated=False） |
| 5 community.json | 落盘报告 | 35 社区，该事实文本出现在 `c-3` 的 `facts[].text`；`inputs.facts=67 / inputs.triples=68`；两次生成 **sha256 相同** |

引用校验：`citation_check = {ok: true, checked: 64, invalid: []}` → **0 条失效**。
孤点：`isolated` 社区 1 个，且仍在 `communities` 里（未被丢弃）。

## 1. 命令与完整输出（原样）

```
$ cd /home/szf/data/dev/llmke-v2
$ /home/szf/data/dev/hipporag-toolenv/bin/python scripts/v2_a3_lineage_probe.py \
    /tmp/tl-a2-root/snapshot-20261103133335-412712-g0
SNAPSHOT: /tmp/tl-a2-root/snapshot-20261103133335-412712-g0

[跳 1] openie 文件: openie_results_ner_qwen2.5-7b-instruct.json
        docs(块)=12  triples=68
        选中三元组: ["智造贷", "适用于", "制造业中小微企业"]
        所在块 idx=chunk-ddb6ef23f083b55cae3e2f2696a22da4
        原文片段: “智造贷”产品说明书。适用对象为制造业中小微企业。单户最高授信额度为5000万元。…

[跳 2] normalize stats: {"facts_in": 68, "facts_out": 67, "dropped_no_source": 0, "dropped_empty": 1,
        "numeric": 5, "relational": 62, "unmapped_predicates": ["determines", "executes", "不得", …],
        "store": {"entities": 92, "aliases": 184, "assertions": 67, "orphans": 0, "sources": 12}}
        assertions=67  orphans=0
        assertion: subject=智造贷 predicate=适用于 object_entity=制造业中小微企业 object_value=None
                   unit=None direction=forward
        sources=[{"file_id": "F001", "locator": "page=1;chunk=0"}]
        render: 智造贷 适用于 制造业中小微企业

[跳 3] export_facts: facts=67 excluded=0
        known_files=['F001','F002','F003','F004','F005','F006','F007','F008','F009','F010','F011','F012']
        excluded 原因分布: {}
        该事实是否在导出集合内: True

[跳 4] communities=35  该事实主体所属社区=[('c-3', 5, False)]
        isolated(孤点)社区数=1  孤点是否保留=True

[跳 5] community.json: communities=35 citation_check={"checked": 64, "detail": null, "invalid": [],
        "ok": true, "reason": null, "sources_available": true, "valid": [...]}
        inputs.facts=67 inputs.triples=68
        该事实出现在社区: [('c-3', 5)]
        两次生成 sha256: c7c09b82894d61d0c976251df034b4508f3ed2e325c800231831f98f266e8661 /
                        c7c09b82894d61d0c976251df034b4508f3ed2e325c800231831f98f266e8661  相同=True
        引用失效数=None (checked=64)

[结论] openie → 断言 → export_facts → build_communities → community.json 五跳闭合=True
```

## 2. 为什么这不是"平台自研抽取"也不是"HippoRAG 内部相似图"

**不是平台自研抽取**：跳 1 的输入是快照里 `openie_results_ner_*.json`（HippoRAG `index()` 的产物），
本脚本与 `global_report._openie_docs` 读的是同一个文件（`global_report.py:269-283`）。

**不是 HippoRAG 内部相似图**（三条独立依据，任一成立即可排除，三条都成立）：

1. **代码路径**：`community.build_report` 的输入是 `export_facts(store, known)` 返回的**断言对象**
   （`community.py:104-110`），再 `build_communities(facts)`；整条链没有引用 `hp.graph`/`synonymy` 边。
2. **数量对照**：引擎图规模 `nodes=112 edges=251`（`GET /health`），而报告 `inputs.triples=68`、
   `inputs.facts=67` —— 若用内部相似图，社区规模应跟随 251 条边，不会正好等于抽取三元组数。
3. **可复现性**：两次 `global_report.write()` 得到同一 sha256
   `c7c09b82…f266e8661`；相似图标签传播受边权重影响，报告侧没有参与这条数值。

```
$ curl -s http://127.0.0.1:18095/health | python3 -c "…"
nodes=112 edges=251 facts=68
```

## 3. 孤点与引用校验（D4 的两个硬要求）

| 要求 | 实测 |
|---|---|
| 孤点保留 | `isolated` 社区 1 个，仍在 `communities` 数组中（脚本打印 `孤点是否保留=True`） |
| 引用 0 失效 | `citation_check.ok=true`、`checked=64`、`invalid=[]` |

`citation_check.invalid` 为空是**逐条校验**的结果（64 条引用逐条对回来源），不是"没检查所以没报错"。

## 4. 与 T-A2 的关系（同一份快照，避免各说各话）

本报告与 `docs/v2-tasks/evidence/A2-pure-graph-route.md` 使用同一快照
`/tmp/tl-a2-root/snapshot-20261103133335-412712-g0`（建图响应 sha256 同为 `c7c09b82…`），
所以"查询走图"与"社区同源"指向的是同一份数据，不存在报告说 A、检索给 B。

## 5. 未做项

| 项 | 状态 |
|---|---|
| 真实业务语料（非 F001–F012）的社区溯源 | 未做。本快照语料来自 18094 现有块原文（F001–F012）。T-A3 派发未禁止演示语料，但"业务语料"验收需另建快照。 |
| 库级多文件路径可视（D4 前半"库级图看多文件来源与路径"） | 未自证（属前端/图查看链路） |
| 报告自然语言综合 | 未做（`capabilities.community_report` 已如实记为"只逐条拼装，不做综合"） |
