# 506 条接口清单 vs 生产快照 核验报告 V1.0

- 日期：2026-10-21
- 批次：`LD-legacy-discovery`
- 对象：`docs/reuse/INTERFACE-ASSETS.yaml` 的 506 条记录
- 参照物：`docs/approvals/OWNER-RESOLUTION-2026-10-21-PRODUCTION-BASELINE.md` 认定的生产快照
  （Java `prod` @ `2b363e6a…`；Python `dev` @ `7299b288…`）
- 复跑命令：

  ```bash
  python3 loops/LD-legacy-discovery/tools/verify_interface_inventory.py \
      --src-root <RAG-SRC/_src> --repo-root . \
      --out loops/LD-legacy-discovery/evidence
  ```

- 原始结果：`evidence/interface-inventory-check.json`；表格：`evidence/interface-inventory-check.md`

## 1. 结论

| 技术栈 | 总数 | 源码中存在（OK） | 仅存在于注释 | 行号漂移 | 未找到 |
|---|---|---|---|---|---|
| Java | 440 | **438** | **1** | **1** | 0 |
| Python | 66 | **66** | 0 | 0 | 0 |
| 合计 | 506 | **504** | **1** | **1** | 0 |

- **504/506（99.6%）** 的清单记录能在生产快照里找到对应的路由声明（方法 + 完整路径 + handler 一致）。
- **1 条只存在于注释**：`API-0345  GET /ai/getRerankModelInfos  (rag-qa-service)`，
  路径仅出现在被注释的代码块中（`AiController.java` 约 L135）。这与 `P0-CLOSURE.yaml` 中
  P0-01 已登记的「`GET /ai/getRerankModelInfos` 处理函数记错且该 `@GetMapping` 连同方法已被注释」**独立吻合**。
- **1 条行号漂移**：`API-0425  GET /database/dataTable/queryTableFileData/{databaseId}/{tableId}`
  （`tools-database`），清单记 L114，实际注解在 L103，漂移 11 行；路径与 handler 均存在。
- 506 条**全部**能在源码里定位到声明文件（0 条 `FILE_MISSING`、0 条 `UNMAPPED`），
  说明清单与源码属同一谱系，可用作逐端点决议的基线。

## 2. 方法（为什么这样做）

清单每行自带 `source_file + source_line`，但 **`path` 是拼接后的完整路径**
（Java 类级 `@RequestMapping("/ai")` + 方法级 `@PostMapping("/question")`），
因此不能用「文本包含」判断，必须先为每个源文件建立路由表：

| 语言 | 识别到的注册写法 |
|---|---|
| Java | `@RequestMapping` 类级前缀 + `@Get/Post/Put/Delete/PatchMapping` 方法级；裸注解（无括号）视为无子路径；多行注解按括号配平 |
| Python | ① `@app.post(...)` 装饰器（含多行）② `@app.route(..., methods=[...])` ③ `XxxView(path="/x", ...)` 实例化（含多行）④ `app.get('/x')(handler)` 函数式注册 |

共解析 52 个源文件。判定顺序：文件存在 → 路径（方法+完整路径）命中 → 是否仅在注释 → handler 一致 → 行号（注解行或 handler 行，偏差 ≤2 视为一致）。

## 3. 本报告证明什么 / 不证明什么

**证明**：清单里的 504 条接口，在「被认定为生产版本」的源码里确有对应的路由声明，
且方法与 handler 对得上；清单整体可信度高，可作为 P0-01 逐端点决议的工作底稿。

**不证明**（P0-01 关闭仍缺）：

1. **运行时可路由**：静态声明 ≠ 应用真正起来、路由被注册、网关未被拦。
   框架「运行时路由导出」这一项仍需真实运行实例（或 owner 明示以静态抽取替代）。
2. **有人调用**：`P0-CLOSURE.yaml` 要求「约 380 条在用判断的调用日志**或调用方确认**」，
   两者本报告都不提供。
3. **`/retrieval_qa` 的保留或废弃**：属业务裁决，需 `interface-owner` 书面决议。
4. 注释中的 `getRerankModelInfos` 是否曾上线过：源码只能说明「当前快照里被注释」，不能说明历史。

## 4. 建议的下一步（P0-01 方向）

1. 以本报告为底稿，建立**逐端点决议表**（键：服务身份 + 方法 + 原始大小写路径），
   为 504 条填入目标合同（`llmke-retrieval-api` / `llmke-kb-api` / `llmke-graph-api` 或「不迁移」）。
2. 对 `API-0345` 单独出决议：`getRerankModelInfos` 是否作为历史接口保留（当前源码不可用）。
3. 向调用方索取「在用」确认，优先覆盖 Java 440 条中被网关/前端实际调用的子集。
4. 运行时导出若可得，用本脚本的输出做三方比对；若不可得，需 owner 明示「静态抽取即视为运行时口径」。
