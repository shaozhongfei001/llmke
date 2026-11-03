# D4 前端 Tab2/3/5 真接口方案（2026-11-03）

前端骨架（v2/ 组件）已在 78f70e0 落地并回落 mock；本文件定“真接口”契约，后端按此补齐。

## Tab2 实体（库级实体列表 + 跨文档来源）

- 数据源：`GET /v2/graph/view` 的 nodes + 断言层来源映射。缺“实体→事实→来源文件”的聚合视图。
- 拟新增：`GET /v2/entities`：
  `{entities:[{id,name,aliases,facts:[{predicate,object,unit,direction,sources:[{file_id,locator,title}]}]}]}`
  实现 = community.json 的 entities/facts + sources.json 反查（global_report 已具备全部原料，只差聚合端点）。

## Tab3 社区（层级/成员/代表性事实/支持组）

- 数据源：`GET /v2/graph/global` 的 `sections`（communities 含 entities/facts/sources）已可用；
  前端只需在 query 为空时仍取 sections 做列表展示（当前 mock 回落是因为没有契约接线，不是缺数据）。
- 拟补充字段：`isolated`、`size` 已存在于 community.json；global 响应 `sections` 透出即可。

## Tab5 构建与更新

- 数据源：`GET /health`（counts/community/cjk_compat）+ `GET /v2/fence`（generation/revoked）+
  发布指针（rebuild pointer.json 的 generation/fencing/built_at——需新增只读端点 `GET /v2/status` 透出）。
- 拟新增：`GET /v2/status`：{snapshot, generation, fencing, built_at, documents, dropped_revoked}。

## 分工

- 后端（本会话）：补 `/v2/entities` 与 `/v2/status`（只读聚合）；
- 前端：Tab2/3/5 把 mock 回落换成 httpAdapter 真接口（契约见本文件），mock 仅作无后端演示。
