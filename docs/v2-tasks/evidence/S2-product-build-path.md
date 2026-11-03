# S2 产品建图链路：Java → 19531 → 18094（真实跑通）

日期：2026-11-02 22:35
目标：证明产品（Java 索引服务）真实上传/解析后，建图请求走 HippoRAG，而不是 legacy 19529。

## 配置切换

`/home/szf/data/dev/llmke-r12/platform/r12/conf/rag-index-service/application-r12.yml`
（运行态外部配置，已备份 `.bak-20261102`）：

```yaml
generate-graph:
  url: http://127.0.0.1:19531/generate_triple_data
```

索引服务已重启（新进程加载该配置）。

## 真实链路

1. 上传 1 个 docx 到 kb_9（`R12FIX-product-loan.docx`）：
   `POST /index/knowledgeBase/file/uploadFileList` → 200，记录 id=999016。
2. 等待解析：`getFileStatusById` → status=3（成功）。
3. 触发图解析：
   `POST /index/knowledgeBase/file/graphParse {"knowledge_base_id":9,"file_ids":["999016"]}`
   → 200 `data=true`。
4. Java 日志（`platform/r12/logs/rag-index-service.out`）：

```
22:35:31 RemoteGraphUtils - 远程url:http://127.0.0.1:19531/generate_triple_data,请求方式:POST
22:35:45 RemoteGraphUtils - 响应结果:"{\"code\":200,\"msg\":\"V2 建图完成 ...
```

5. 结果落库：`knowledge_base_list.id=999016` → `graph_parse_status=3`（成功）。
6. 新快照与来源映射：

```
/tmp/v2-shim-root/snapshot-20261102223531-579610-g0
sources.json:
 {"chunk-ca1d8268933dd200d88189cca497d46c":
   [{"file_id":"999016","locator":"page=-;offset=[[0, 459]];chunk=0"}]}
```

## 判定

- D0 的建图段成立：产品请求经兼容层进入 HippoRAG，legacy 图服务未参与本次建图；
- Java 的零产出闸门通过（edges_total=3 / edges_written=12，均为真实计数）；
- 引用可回指到 chunk（file_id + offset/chunk 定位，不是伪造页码）。

## 未完成

- 查询/答案仍走 legacy（qa-service + Nebula），页面尚未消费新快照；
- community 端点为 501（Java 只告警，不影响图状态）；
- 删除端点仍 501。
