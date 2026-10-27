# R13 能力矩阵自检

总计 6/6 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| VERSION | PASS | http=200 groups=2 多版本组=2 版本=['V1', 'V0', 'V1', 'V0'] |
| TABLE | PASS | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=3 answer='华东精密制造有限公司的授信额度为3000万元。' |
| GLOBAL_POS | PASS |  http=200 status=2 cost=4.3s refs=3 可解析=3（其中绝对URL=3 相对键=0）社区id=True src示例=product-loan.docx/V0/R12FIX-product-loan.docx |
| GLOBAL_REFUSE/R1 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='授信额度与票据贴现的关系在提供的事实中未提及，因此无法得出结论。[L0-18625408]' |
| GLOBAL_REFUSE/R2 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-3c882b30]' |
| GLOBAL_FAITH | PASS | http=200 客户→加点实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] |
