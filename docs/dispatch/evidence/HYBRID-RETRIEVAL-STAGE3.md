# HybridRetrieval 阶段 3 验收记录（三路融合）

日期：2026-11-06。loop：HYBRID-RETRIEVAL-1。执行身份：tech-lead（TL）。

## 结论

| 验收项（HR-05/06/07 / 派工单） | 结果 |
|---|---|
| dense/lexical/graph 三路并行召回 | ✅ 三路分别有召回，且不互相阻断 |
| RRF 按 pk 去重（k=60），禁止按 page_content | ✅ 同 pk 重复数=0，es+graph、milvus+graph 同 pk 正确合并 |
| rerank 相对阈值（top×0.3） | ✅ 弱相关英文书「Tips on growing」被正确过滤 |
| 部署到运行环境 | ✅ r12 同步 + `algctl restart alg_retrieval_service` 重启 19995 |

## 部署动作

1. 备份 r12 旧版 → `/tmp/reranker_service.py.r12.bak`；
2. 复制 v2 改造版 `reranker_service.py` 到 r12（`rrf_k=60`、按 pk 去重、相对阈值）；
3. `platform/r12/run/algctl.sh restart alg_retrieval_service` → 19995 重启成功（http=200）。

## 验收实测（19995 混合检索，开图）

**query「智造贷的单户最高授信额度是多少」**（search_policy=1 混合）：
```
pk=257380967606107716  search_type=['es','es','graph']  ← es×2 + graph 同 pk 合并
pk=176702357037858174  search_type=['es','es','graph']
pk=606479882502856278  search_type=['es','es','graph']
同 pk 重复数 = 0
```

**query「授信额度是多少」**（混合 + 开图）：
```
pk=1152386378966098989  search_type=['milvus','graph']  ← milvus + graph 同 pk 合并
pk=1137902847478273881  search_type=['graph']
```

## 关键结论

1. **RRF 按 pk 去重（HR-06）已生效**：`es×2+graph` 合并为 1 条、`milvus+graph` 合并为 1 条，
   不再是旧版「按 page_content 精确字符串去重」（旧版会在 es 带标题/图无标题时拆成两条）。
2. **rrf_k=60（HR-06）已生效**：RRF score 为 `1/60`、`1/61` 级别（旧版 k=5）。
3. **相对阈值（HR-07）已生效**：milvus 对「智造贷…」误召的英文书 chunk「Tips on growing」
   （kb_9 混入 4520 条英文书 + 44 条中文金融）因 rerank 分数低被相对阈值过滤，未污染结果。

## 观察（非阻塞，如实记录）

- kb_9 语料是「4520 条英文书 *Allotment month by month* + 44 条中文金融文档」的混合。
  dense（bge-m3）对中文长问句「智造贷的单户最高授信额度是多少」的 top1 误召回英文书 chunk，
  但对短问句「授信额度是多少」能正确命中中文。这是**语料分布 + dense 检索质量**问题，
  不是阶段 3 融合缺陷；融合链路（RRF+相对阈值）已正确兜底过滤弱相关结果。
- 「search_type 同时含 es+milvus+graph」在单一 query 下不保证同时出现（rerank 会按相关性
  过滤某一路），三路已分别在合适 query 下验证接通。
