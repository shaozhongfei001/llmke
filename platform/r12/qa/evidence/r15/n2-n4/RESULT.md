# R15 N1–N4 执行记录（含两处判断纠正）

> **证据等级 RECORD_ONLY**：这是排障过程记录，**不可独立复跑**（依赖当时的临时夹具/中间态）。不得用作文档所述能力的通过证据；对应的稳定判据见 `platform/r15/acceptance/` 中的断言。


- 时间：2026-10-29 20:40–20:55
- 环境：网关 8088 → qa 18083 → index 18082 → 图服务 19529 → Nebula/ES

## 一、纠正两条此前记录的错误（必须先说）

### 纠正 1：graphParse 的 10001「知识库不存在」是我方参数名错误，不是产品缺陷

```
接口契约（FilesParseReq）：file_ids / knowledge_base_id / knowledge_base_name（snake_case）
我之前传：knowledgeBaseId（camelCase）→ 字段未绑定 → kbId=null → 10001
用正确字段：POST {"file_ids":["343"],"knowledge_base_id":9} → 200 success=true
```

⇒ 从 blocker 列表移除。但仍有一条真实缺陷随之暴露（见纠正 2 与 N3）。

### 纠正 2：任务 status=4 是「处理成功」，不是失败

```
ParseTaskStatusEnums: PENDING(1) DEAL_ING(2) RETRY_ING(3) SUCESS(4) DEAL_FAIL(5)
```

我之前把 4 读成失败，据此判断"成功被记成失败"，属于误判。
实际 604/605 都是**成功**。

## 二、N1/N3 过程中修掉的两个真实缺陷

### 缺陷 A：归一化后 source 键不一致 → KeyError → 解析任务半成功

```
graph_types.normalize_graph_data:
  三元组用 clean_name(rel) 清洗关系名
  source 键却用原样 parts[1]
  → graph_service 写 Milvus 时 triples_source_dict[name] KeyError
    （实测 'KeyError: 放款\x1f放款期限-\x1f3个工作日'）

修法：
  ① graph_types: source 键也用 clean_name(rel)
  ② graph_service: 溯源缺失降级为"无溯源"+告警，不再 500
  ③ graph_fun_tool: Milvus 更新路径 setdefault，避免同类 KeyError
```

### 缺陷 B：零产出可以记成功（A06）

```
file 343 曾在 gps=3（解析成功）状态下，图中 0 条边 —— 写边全失败却没校验
修法：
  Python 回传 triples_total / edges_total / edges_failed / edges_written
  Java generateGraph 校验 edges_written>0，否则判失败并打日志
```

## 三、N2 归一化层反例（COMPONENT，PASS）

输入 4 条三元组：正常 2 条 + 逆否 1 条 + 垃圾 1 条

```
保留：('智造贷','最高额度','8000万元') / ('智造贷','信用方式上限','1000万元')
report: dropped_junk=1  dropped_reverse=1  dropped_triples=0
source 键缺失数 = 0
判定 PASS
```

垃圾样例（被丢弃）：
```
1000万元 -[最高额度-信用部分不超过->8000万元]-> 信用部分最高额度为1000万元，不超过8000万元
```
逆否样例（被去重）：
```
智造贷 -最高额度-> 8000万元   与   8000万元 -最高额度-> 智造贷（模型自己输出了两次）
```

## 四、N4 端到端四问（INTEGRATION）

| 问法 | global | local |
|---|---|---|
| 智造贷最高额度是多少？ | 8000万元（1.5s）**未带分项** | 8000万元 + **其中信用方式不超过1000万元**（40.7s） |
| 智造贷信用方式最高多少？ | 1000万元（2.0s） | 1000万元（17.9s） |

判读：

```
✅ 语义反转已消除：四个答案的数值与指向都正确，不再出现"最高额度=1000万"
✅ 分项问题 global 也能正确回答 1000 万
❌ "最高额度"这一问，global 只给总额度、不主动带出分项约束；local 完整
```

## 五、仍未解决（下一轮）

```
1. 343 任务成功后 gps 停在 1（正常/未做），未收敛到 3（解析成功）
   → doSuccess → generateGraph 是 @Async，状态写入与任务状态不同源
2. 603 被看门狗以 "recover: 超过10min" 处理过；队列僵尸兜底仍在参与
3. global 的完整性（分项约束）受 reduce prompt 与事实选择影响，需单独修
```
