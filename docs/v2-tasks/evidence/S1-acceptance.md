# S1 验收（TL）

日期：2026-11-02
范围：19529 兼容层（A）、ParseArtifact 绑定（B）、方向语义（C）

## A. 兼容层：legacy 形状请求真实跑通

启动：19531（`graph_engine_adapter.legacy_shim:app`），上游 18094，ES 代理 19527。

请求（与 Java `FileAppServiceImpl` 同形，**不带 docs**）：

```json
{"space_name":"kb_9","col_name":"title","col_values":["丙-额度分项.docx"],"generation":"V0"}
```

真实响应：

```json
{"code":200,
 "msg":"V2 建图完成 docs=1 chunks=1 facts=3 edges=12",
 "data":{"docs":1,"chunks":1,"triples_total":3,"edges_total":3,
         "edges_written":12,
         "snapshot":"/tmp/v2-shim-root/snapshot-20261102215805-143662-g0"},
 "es_hits":1,"fallbacks":0}
```

判定：
- 无 docs 时按 legacy 读法从 ES 取到 1 块（不是 400 拒绝）；
- `edges_total>0` 且 `edges_written>0`，满足 Java 的零产出闸门；
- 计数来自 18094 的真实 `facts/edges`，不是用 chunks 冒充。

测试：`tests/test_legacy_shim.py` 22 passed。

## B. ParseArtifact 绑定

独立验证（2 块：段落 + 表格单元格）：

```
docs 2, content_hash 3fe7864eba48
file_id=doc-1, locator=p1
assert_same_artifact 同产物 → 通过；换 artifact_id → ArtifactBindingError
```

已接入 `/v2/graph/build`：传 `artifact` 时先校验，非法直接 400；
响应带 `artifact_id` 与 `content_hash`。
测试：`tests/test_artifact_binding.py` + `tests/test_graph_api.py` 共 16 passed（含新增 3 项）。

## C. 方向语义

真实 `normalize.build_store`（4 条输入）：

```
assertions 3
甲 担保 乙 forward
乙 担保 甲 forward
乙 相似 甲 symmetric
data_stats facts_out=4 / assertions=3
```

判定：有向谓词双向保留；对称谓词合并为一条；未知谓词默认非对称。
测试：`tests/test_semantics_direction.py` 全部通过。

## 结论

| 任务 | 状态 | 证据 |
|---|---|---|
| T-S1A 兼容层 | PASS | 本文 §A + `S1-legacy-shim.md` |
| T-S1B 产物绑定 | PASS | 本文 §B + `S1-artifact-binding.md` |
| T-S1C 方向语义 | PASS | 本文 §C + `S1-direction.md` |

未做（进入 S2）：
- Java 配置仍指向 19529 legacy，未切到 19531；
- `generate_community` / 删除端点仍是 501；
- 页面端到端尚未跑。
