# P0-01 仪器：源码路由提取 ↔ 接口清单比对（含实测结论）

日期：2026-10-22　状态：**已对真实源码跑通**
工具：`docs/baseline/validation/p0-01-route-extract.py`
源码：`RAG-SRC/_src/gien-rag/gien-rag/rag-parent`（1003 个 `.java`）
清单：`docs/upstream/源码接口契约-接口总表.csv`
性质：只读分析；不改源码、不改清单、不改控制面；r9 候选不受影响。

---

## 1. 实测结论（这是 P0-01 的第一份机器证据）

```
源码 .java 文件=1003（其中 Feign 客户端 27 个，已排除）
活代码路由=440   注释中路由=1   清单路由(Java)=440

清单有、源码无 = 1     源码有、清单无 = 1     处理函数不一致 = 0
```

| 差异 | 明细 | 含义 |
|---|---|---|
| 清单有、源码无 | `GET /ai/getRerankModelInfos`（rag-qa-service） | 该接口的注解与方法体**已被 `//` 注释**（`AiController.java:135-138`），清单仍登记为可用 |
| 同一行的处理函数 | 清单记为 `audioUploadAndIdentify`（CSV 第 148 行） | **张冠李戴**：`audioUploadAndIdentify` 是另一个方法，真实的 `getRerankModelInfos` 已注释 |
| 源码有、清单无 | `GET /version/getCurrentVersion`（rag-auth-service，`SystemVersionController.java:32`） | 源码存在的接口未登记 |
| 注释中路由 | 1 条，即上述 `getRerankModelInfos` | 与第一条互相印证 |

**两个数字正好相等（440 vs 440）是巧合**：差异方向相反、互相抵消。
这恰恰说明"用总数核对"会得出"清单准确"的错误结论——必须逐条比对。

### 与 P0-01 登记事实的对应

| P0-01 已知事实（原文） | 本次验证 |
|---|---|
| 清单记录数 506 不等于运行时可路由数 | **成立**：506 = Java 440 + Python 66；Java 侧有 1 条不可路由 |
| `GET /ai/getRerankModelInfos` 的处理函数被记为 `audioUploadAndIdentify` | **成立**，CSV 第 148 行 |
| 该 `@GetMapping` 连同方法已被 `//` 注释 | **成立**，`AiController.java:135-138` |

---

## 2. 工具怎么做到

| 机制 | 说明 |
|---|---|
| 注释剥离 | 状态机处理 `//`、`/* */`、字符串与字符字面量；注释内容单独保留用于反查 |
| 类级前缀 | 取 `class` 声明之前的最后一个 `@RequestMapping` 作为前缀 |
| 无括号注解 | 支持 `@GetMapping`（不带 `()`，路径全在类级）——**这条是实测补上的**：漏了它就会把 `/roleResource` 三条误判为"清单多记" |
| Feign 排除 | `@FeignClient` 是**出站调用**，不是服务端路由；排除 27 个文件，否则"源码有清单无"被系统性夸大（实测从 90 条降到 1 条） |
| 处理函数 | 先剥离 `@Operation(...)`/`@OperationLog(...)` 等注解，再取方法声明；否则会解析成注解名（实测曾误报 198 条） |
| 路径归一 | `{id}`/`{name}` 统一为 `{*}`，避免路径变量名差异造成假差异 |

### 三次自我纠错（都写出来，因为都能复现）

1. **处理函数误取注解名** → 198 条假 `HANDLER_DIFF`（取到了 `OperationLog`）。修正后为 0。
2. **注释中的路由数为 0** → 无 class 声明时把起始下标设成了 `len(matches)`，整段被跳过。
3. **`@GetMapping` 不带括号** → 漏 3 条，导致把 `/roleResource` 误判为清单多记。

第 3 条尤其说明：**工具本身也会有假差异**，所以每条差异都要回到源码行确认，不能直接当结论。

---

## 3. 它不判定什么

| 项 | 原因 |
|---|---|
| 运行时可路由 | 静态提取只能证明"注解存在于源码"，不证明服务启动后可访问 |
| 网关路由 | `rag-gateway` 的转发规则多为配置，不在控制器注解里 |
| Python 侧 66 条 | 源码树仅含 Java（`find *.py` = 0），Python 服务不在本树 |
| 鉴权与权限 | 属 P0-03 范围 |

因此本工具产出的是**差异候选清单**，供 `interface-owner` 逐条裁定，不是 P0-01 的关闭结论。

---

## 4. 复现命令

```bash
cd ~/data/dev/llmke-r8
export PATH=~/data/dev/llmke/.venv/bin:$PATH

python3 docs/baseline/validation/p0-01-route-extract.py \
  --src ~/data/repo/RAG-SRC/_src/gien-rag/gien-rag/rag-parent \
  --csv docs/upstream/源码接口契约-接口总表.csv \
  --out /tmp/java-routes.csv
```

输出中的 `CSV_ONLY` / `SRC_ONLY` / `HANDLER_DIFF` / `COMMENTED` 四类，即 P0-01 的 D01 回答素材。

---

## 5. 顺带发现（不在 P0-01 范围，但值得记）

`/version/getCurrentVersion` 未登记在清单里。清单中确实有一条 `/version`，但它的栈是 **Python**
（服务 `version_service`），与这个 Java 接口不是同一件事。
这意味着**清单以"服务名"区分栈时，同名路径可能跨栈重复**，逐条比对时不能只按路径匹配。
