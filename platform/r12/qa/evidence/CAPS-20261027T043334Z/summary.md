# R13 能力矩阵自检

总计 6/9 PASS（另有 INFO 4 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | FAIL | 异常: ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=8088): Read timed out. |
| FAQ | PASS | http=200 status=2 resultType=2 尝试=1/3 answer='是的，文档的结构包含客户访前准备在第一段，日均存款在第二段。' refs=2 |
| GLOBAL_POS | FAIL |  http=200 status=2 cost=3.7s configId=1 refs=1 可解析=1（绝对URL=0 相对键=1）社区id=True src示例=product-loan.docx/V0/R12FIX-product-loan.docx |
| GLOBAL_REFUSE/R1 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-18625408]' |
| GLOBAL_REFUSE/R2 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-3c882b30]' |
| GLOBAL_FAITH | PASS | 多数票=2/2 首次 http=200 首次实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] 各次=[{'江南装备': '30', '华东精密': '60', '北方重工': '60'}, {'江南装备': '30', '华东精密': '60', '北方重工': '60'}] |
| VERSION | PASS | http=200 groups=2 多版本组=2 版本=['V1', 'V0', 'V1', 'V0'] |
| TABLE | FAIL | http=500 status=500 数值=False 单位=False 主体=False 口径='授信/额度'=False refs=0 answer='' |
| GRAPH_LOCAL | INFO | 环境不可用：19529 未监听（图服务重启窗口，不是产品 FAIL） |
| GRAPH_IDENTITY | INFO | 环境不可用：19529 未监听（图服务重启窗口，不是产品 FAIL） |
| GRAPH_PROVENANCE | INFO | 环境不可用：19529 未监听（图服务重启窗口，不是产品 FAIL） |
| GRAPH_UPPERCASE | INFO | 环境不可用：19529 未监听（图服务重启窗口，不是产品 FAIL） |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
