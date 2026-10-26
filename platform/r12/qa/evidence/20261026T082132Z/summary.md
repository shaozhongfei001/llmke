# R12 验收 20261026T082132Z

总计 19/20 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S1 | 登录并取菜单 | PASS | http=200 menus=7 |
| S1 | 取当前用户信息 | PASS | http=200 user=admin |
| S2 | 知识库已存在（复用） | PASS | kbId=9 primitive=kb_9 |
| S3 | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=218 name=R12FIX-product-loan.docx |
| S3 | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=219 name=R12FIX-credit-ledger.xlsx |
| S3 | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=220 name=R12FIX-product-intro.pptx |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=221 name=pdf-digital.pdf |
| S3 | 上传 DOCX 纯文本 | PASS | http=200 fileId=222 name=docx-plain.docx |
| S3 | 上传 DOCX 含表格 | PASS | http=200 fileId=223 name=docx-table.docx |
| S3 | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=224 name=pdf-scanned.pdf |
| S3 | 加密 PDF 已入库待解析 | PASS | http=200 fileId=225 |
| S4 | 解析完成 中文 DOCX 业务夹具 | PASS | fileId=218 最终状态=3 耗时=27s |
| S4 | 解析完成 中文 XLSX 业务夹具 | PASS | fileId=219 最终状态=3 耗时=0s |
| S4 | 解析完成 中文 PPTX 业务夹具 | PASS | fileId=220 最终状态=3 耗时=0s |
| S4 | 解析完成 PDF 数字版 | PASS | fileId=221 最终状态=3 耗时=0s |
| S4 | 解析完成 DOCX 纯文本 | PASS | fileId=222 最终状态=3 耗时=18s |
| S4 | 解析完成 DOCX 含表格 | PASS | fileId=223 最终状态=3 耗时=21s |
| S4 | 解析完成 PDF 扫描件(OCR) | PASS | fileId=224 最终状态=3 耗时=0s |
| S4 | 负例按预期失败 加密 PDF(应解析失败) | PASS | fileId=225 最终状态=4(4=失败) 耗时=21s |
| ERR | 执行异常 | FAIL | HTTPConnectionPool(host='127.0.0.1', port=8088): Read timed out.
Traceback (most recent call last):
  File "/usr/lib/python3/dist-packages/urllib3/response.py", line 438, in _error_catcher
    yield
  File "/usr/lib/python3/dist-packages/urllib3/response.py", line 764, in read_chunked
    self._update_chunk_length()
  File "/usr/lib/python3/dist-packages/urllib3/response.py", line 694, in _update_chunk_length
    line = self._fp.fp.readline()
  File "/usr/lib/python3.10/socket.py", line 705, in readinto
    return self._sock.recv_into(b)
TimeoutError: timed out

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/lib/python3/dist-packages/requests/models.py", line 753, in generate
    for chunk in self.raw.stream(chunk_size, decode_content=True):
  File "/usr/lib/python3/dist-packages/urll |
