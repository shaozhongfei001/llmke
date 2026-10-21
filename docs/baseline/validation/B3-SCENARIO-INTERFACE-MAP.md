# B3：P0-03 场景 ↔ 506 接口关联索引

> 关联只表示「可能受该场景约束」，**不表示存在漏洞，也不表示已验证**。
> 置信级别 `KEYWORD_MATCH_LOW`；策略状态 `UNCONFIRMED_ASSUMPTION`。

## 场景覆盖

| 场景 | 草案对应 | 命中接口数 |
|---|---|---|
| N1_cross_domain_and_deny_override | E2 + E3 | 204 |
| N2_graph_unauthorized_interference | E6 | 29 |
| N3_side_channel_indistinguishability | 扩展（侧信道） | 76 |
| N4_cache_isolation_after_policy_change | 扩展（缓存隔离） | 172 |
| N5_revocation_residue | E4 | 140 |
| N6_faq_inherit_source_permission | E5 | 106 |
| N7_error_metadata_leak | 扩展（错误元数据） | 506 |

## 草案六类覆盖检查

| 草案类 | 对应场景 | 状态 |
|---|---|---|
| E2 越权读（跨 KB/文件） | N1 | 有场景 |
| E3 目录聚合 + deny 优先 | N1 | 有场景 |
| E4 撤权即时性 | N5 | 有场景 |
| E5 FAQ 继承来源复核 | N6 | 有场景 |
| E6 图路降级 | N2 | 有场景 |
| **E7 邻近块/图片回查二次取数** | — | **缺场景（GAP）** |

> N3/N4/N7 属**扩展场景**（侧信道/缓存/错误元数据），不强行计入六类。

## 口径

- `route_evidence=CODE_ONLY`：仅表示清单记有该路由且源码核验过，**未验证运行时可达**；
- 未做任何漏洞推理；命中数只反映关键词覆盖面。
