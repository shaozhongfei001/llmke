# E2E 环境基线（阶段 0，协调者产）

采集时刻：2026-10-27 23:57（本机时间）
采集人：协调者（TL）

## 前端代次（证明测的是哪一版）
```
dist 路径   /home/szf/data/dev/llmke-r12/frontend/plateform/dist
nginx 挂载  /home/szf/data/dev/llmke-r12/frontend/plateform/dist -> /usr/share/nginx/html/rag
entry       assets/index-CpE2zvYY.js
大小        315576 字节
md5         de2424501bd29e358043049876db2a75
比对        宿主文件 md5 == 线上取回 md5（一致，非 SPA fallback）
特征串      无权访问该原文 ×1；FAQ 列表加载失败 ×0
```

## 服务代次（开工基线）
```
8088=1403651   18082=2139785   18083=1647331   19527=1823402   19529=1461792   19995=1481869
```

## 环境坐标
```
前端   http://127.0.0.1:18088
网关   http://127.0.0.1:8088
登录   admin / Admin@12345
```

## 知识库清单（接口快照，共 15 个）
```
kb_9  = 业务语料（只读）
kb_22 = 他人夹具（禁止动）
其余：7/8/10/12/13/14/25/26/32/34 等
```

## 测试语料基准（kb_9）
```
R12FIX-product-loan.docx   V0+V1（有效 V1）
R12FIX-product-intro.pptx  V0+V1（有效 V1）
pdf-digital.pdf / pdf-scanned.pdf / docx-plain.docx / docx-table.docx
R12FIX-credit-ledger.xlsx  台账（块在 table_chunks_kb_9 / table_summary_kb_9）
授信额度基准：V1=8000万 / V0=5000万
global 三地加点：江南 30 / 华东 60 / 北方 60 个基点
```

## 工具
```
Playwright 1.60.0（chromium 已装）
Python venv  platform/r12/venvs/alg/bin/python（含 requests/pymilvus/pyyaml）
QA 客户端    platform/r12/qa/r12_client.py（login/api；Authorization 用裸 token + X-Platform 头）
```

## 注意
本目录内所有路径均相对于 /home/szf/data/dev/llmke-r12。
