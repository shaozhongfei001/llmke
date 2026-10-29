# W09 抽取侧 entity linking（COMPONENT + 一次真实重解析）

> **证据等级 COMPONENT**：prompt 注入已在组件级验证（prompt 原文可见），
> 真实重解析跑通一次，但**未能证明跨文件关联提升**（见"实测"）。

## 改了什么

```
graph_extract.py  _known_entities_section() + generate_graph_relations(known_entities=)
graph_service.py  fetch_known_entities(space) + llm_generate_triple 透传
```

注入位置在 `Entity_types` 之后、`Text` 之前；`known_entities` 为空时不插入任何内容，
prompt 与改造前逐字一致（可做前后对照）。

## 实测

```
① prompt 注入生效（组件级，日志原文）
   Entity_types: 产品,客户,金额,期限,业务动作,指标,评级
   Known_entities（本知识库中**已存在**的实体名）：
   智造贷、制造业中小微企业、8000万元、1000万元、办理流程、审批、放款、受理、资料审核、10个工作日
   规则：若文本中出现的确实是上述某一个事物，请**原样复用该名称**…
   Text: 智造贷面向制造业中小微企业…

② 取已有实体函数可用
   graph_service:fetch_known_entities:505 - 抽取注入已有实体 80 个（space=g_kb_9）
   返回样本: ['AAA级','T-CORE-001','北方','华东精密制造有限公司','江南装备科技有限公司',…]

③ 真实重解析 file 343（产品说明书，464 字）
   http=200 cost=157s  返回："新增和更新84条图数据,新增9条实体"
   重解析后：总边 89→92，跨文件实体仍 2（智造贷、日均存款），连通分量仍 4
```

## 结论：机制成立，但效果受物理限制

```
跨文件连接没有因为注入而增加。原因不是实现失败，而是：
  file 343（产品规则）与 file 329（客户额度表）在语义上没有共享实体。
  注入只能让"同一事物在不同文件里的写法统一"，不能让两份无关文档长出关系。
所以"关联"必须靠：
  · 业务关系（BRIDGE-1，已做，+3 条边，连通分量 7→4）
  · 或同类文档之间的共享实体（多份产品说明书、多份客户表时注会明显起作用）
```

## 副作用与已修的漏例

```
重解析后新增实体里出现新的句子型实体，说明首版 sentence_like 尾词表太窄：
  "提前十五个工作日提出书面申请"（14 字，未超 14 阈值）
  "办理流程包含评级授信步骤"（尾词"步骤"不在表内）
  "办理流程包含资料审核步骤"
已补：has_pred 加 提出/申请；has_mod 加 步骤/时限/书面/申请/规定/要求；长句兜底 >=12 字
回归：正常实体（客户名/产品名/编号/日期）均不受影响

另发现疑似新问题（未深挖）：实体 "北方" 应为 "北方重工配件厂" 被截断，
需单独确认是 mention 归一错误还是模型输出问题。
```

## 复跑

```bash
# 组件级（prompt 是否注入）
NACOS_SERVER_ADDRESS=127.0.0.1:18848 DATA_ID=index_graph_config_py \
  platform/r12/venvs/graph/bin/python -c "import graph_service as G; print(len(G.fetch_known_entities('kb_9')))"

# 真实重解析
curl -sS -X POST http://127.0.0.1:19529/generate_triple_data \
  -H 'Content-Type: application/json' \
  -d '{"space_name":"kb_9","col_name":"file_id","col_values":["343"],"model_info":{},"top_k":30}'
```
