# R12 验收 20261025T044325Z

总计 11/13 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S1 | 登录并取菜单 | PASS | http=200 menus=7 |
| S1 | 取当前用户信息 | PASS | http=200 user=admin |
| S2 | 知识库已存在（复用） | PASS | kbId=9 primitive=kb_9 |
| S3 | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=79 name=R12FIX-product-loan.docx |
| S3 | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=80 name=R12FIX-credit-ledger.xlsx |
| S3 | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=81 name=R12FIX-product-intro.pptx |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=82 name=pdf-digital.pdf |
| S3 | 上传 DOCX 纯文本 | PASS | http=200 fileId=83 name=docx-plain.docx |
| S3 | 上传 DOCX 含表格 | PASS | http=200 fileId=84 name=docx-table.docx |
| S3 | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=85 name=pdf-scanned.pdf |
| S3 | 加密 PDF 已入库待解析 | PASS | http=200 fileId=86 |
| S4 | 解析完成 中文 DOCX 业务夹具 | FAIL | fileId=79 最终状态=98 耗时=601s |
| ERR | 执行异常 | FAIL | HTTPConnectionPool(host='127.0.0.1', port=8088): Max retries exceeded with url: /index/knowledgeBase/file/getFileStatusById?fileId=80 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x73f5b61212a0>: Failed to establish a new connection: [Errno 111] Connection refused'))
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
