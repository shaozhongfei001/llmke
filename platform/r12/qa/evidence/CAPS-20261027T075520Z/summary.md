# R13 能力矩阵自检

总计 4/4 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| GLOBAL_POS | PASS |  http=200 status=2 cost=3.6s configId=1 refs=3 可解析=3 覆盖度(去重前缀)=2（绝对URL=0 相对键=3）社区id=True src示例=duct-loan.docx/V1/R12FIX-product-loan(1).docx infra(graph_pid=1461792,es_ok=True,8.9ms) |
| GLOBAL_REFUSE/R1 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-18625408]' infra(graph_pid=1461792,es_ok=True) |
| GLOBAL_REFUSE/R2 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-3c882b30]' infra(graph_pid=1461792,es_ok=True) |
| GLOBAL_FAITH | PASS | 多数票=2/2 首次 http=200 首次实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] 各次=[{'江南装备': '30', '华东精密': '60', '北方重工': '60'}, {'江南装备': '30', '华东精密': '60', '北方重工': '60'}] infra(graph_pid=1461792,es_ok=True) |
