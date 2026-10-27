# R12 验收 20261027T053921Z

计划场景：['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8']（未知：[]）
总计 8/11 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S1 | 登录并取菜单 | PASS | http=200 menus=7 |
| S1 | 取当前用户信息 | PASS | http=200 user=admin |
| S2 | 删除上一轮验收库（保证基线独立可重复） | PASS | kbId=21 kbName=R14-BASELINE-KB http=200 |
| S2 | 创建独立验收库 | PASS | http=200 kbId=23 kbName=R14-BASELINE-KB primitive=kb_23 旧库清理=1 |
| PREP | 独立库助手配置就绪 | PASS | kbName=kb_23 configId=12（R14-BASELINE-CFG） |
| S3 | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=398 name=R12FIX-product-loan.docx |
| S3 | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=399 name=R12FIX-credit-ledger.xlsx |
| S3 | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=400 name=R12FIX-product-intro.pptx |
| S3 | 上传 PDF 数字版 | FAIL | http=500 fileId=None name=pdf-digital.pdf |
| ERR | 执行异常 | FAIL | HTTPConnectionPool(host='127.0.0.1', port=8088): Max retries exceeded with url: /index/knowledgeBase/file/uploadFileList (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7c86a05d3c10>: Failed to establish a new connection: [Errno 111] Connection refused'))
Traceback (most recent call last):
  File "/usr/lib/python3/dist-packages/urllib3/connection.py", line 169, in _new_conn
    conn = connection.create_connection(
  File "/usr/lib/python3/dist-packages/urllib3/util/connection.py", line 96, in create_connection
    raise err
  File "/usr/lib/python3/dist-packages/urllib3/util/connection.py", line 86, in create_connection
    sock.connect(sa)
ConnectionRefusedError: [Errno 111] Connection refused

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/lib/python3/dist-packages/urllib3/connectionpool.py", line 700, in urlopen
    httplib_response = self._make_request(
  File "/usr/lib/python3/dist-packages/urllib3/connectionpool.py", line 395, in _make_request
    conn.request(metho |
| COVERAGE | 选中的场景均已真实执行 | FAIL | 选中=['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'] 实际执行=['S1', 'S2'] 未执行=['S3', 'S4', 'S5', 'S6', 'S7', 'S8'] 未知场景=[] |
