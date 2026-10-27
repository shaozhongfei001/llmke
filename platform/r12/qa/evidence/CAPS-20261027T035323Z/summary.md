# R13 能力矩阵自检

总计 2/4 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| GLOBAL_POS | FAIL |  http=200 status=2 cost=6.3s refs=3 可解析=0 社区id=True src示例=None |
| GLOBAL_REFUSE/R1 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='授信额度与票据贴现的关系在提供的事实中未提及，因此无法得出结论。[L0-18625408]' |
| GLOBAL_REFUSE/R2 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-3c882b30]' |
| GLOBAL_FAITH | FAIL | http=200 AAA→30bp=False AA→60bp=False AAA处其它数值=[] answer='江南装备科技有限公司的信用评级是AAA，依据为[L0-3af0d4bc]。\n\n华东精密制造有限公司的信用评级是AA，依据为[L0-60d6fa91]。\n\n北方重' |
