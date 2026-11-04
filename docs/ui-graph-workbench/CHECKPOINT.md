# 知识图谱工作台 —— 检查点

- 更新时间：2026-11-04
- 工作树：/home/szf/data/dev/llmke-v2（分支 fix/login-kaptcha-null-guard，未提交改动 6 个前端文件）
- 后端：网关 8088（运行中）、图服务 18094（运行中）、preview 18095（运行中）
- 前端 dev server：http://127.0.0.1:15174（setsid 后台运行，日志 /tmp/llmke-vite.log）
- 登录：admin / Admin@12345（simpleLogin，AES-128-CBC key=iv=1234567890123456）
- 演示库：kb_9（R12验收主链，primitiveName=kb_9，18 文件）

## 数据接口结论（阶段0）
| 能力 | 接口 | 返回 |
|---|---|---|
| 业务图谱 | POST /graph/search/wholeGraphSearch {spaceName} | 137 节点(name=业务名/nodeType=类型/properties.file_id+title) + 114 有向边(edgeType=谓词/src/dst) |
| 文件子图 | GET /graph/search/subGraph?spaceName=&fileId= | nodeList/edgeList |
| 社区 | POST 18094 /v2/graph/global {query,max_communities} | communities=35, sections[community/entities/facts[{text,sources}]/size], source_meta{F001..→title} |
| 问答 | POST /qa/ai/question_re (SSE) | reply.content 流式 + reference |
| 原文 | GET /index/knowledgeBase/file/getById?id= | fileName/filePath(MinIO)/pdfPage/tableFilePaths |

## 当前进度
- T0 完成（数据能力探测）。T1 进行中。

## 下一动作
重写 GraphWorkbench 组件：工具栏（探索/社区/问答+搜索+筛选+跨文档+全屏+构建菜单）、画布填满、默认收起详情/筛选。

## 接续命令
```
cd /home/szf/data/dev/llmke-v2/frontend/plateform
# 若 dev server 已停：setsid bash -c 'npm run dev > /tmp/llmke-vite.log 2>&1 < /dev/null' &
```
