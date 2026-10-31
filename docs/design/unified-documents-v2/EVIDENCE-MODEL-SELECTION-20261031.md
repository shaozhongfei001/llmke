# 模型现状与替换评估（2026-10-31）

## 1. 当前用的是什么

| 用途 | 模型 | 端点 |
|---|---|---|
| 问答/抽取/重排（chat） | `qwen2.5-7b-instruct` | `http://127.0.0.1:18092/v1`（本地） |
| 向量 | `text-embedding-bge-m3` | `http://127.0.0.1:18090/v1`（本地） |
| 多模态（版面/表格图） | `qwen2.5-vl-3b-instruct` | `http://127.0.0.1:18093/v1`（本地） |
| 图引擎 | `hipporag 2.0.0a4` | 独立 venv，LLM/embedding 复用上面两个端点 |

换模型只影响 **chat 这一段**（抽取、重排、回答组装）；embedding 与图引擎不动，
因为换 embedding 会让已有向量全部失效。

## 2. 环境变量里的凭据（只列键名与可用性）

| 变量 | 来源 | 探测结果 |
|---|---|---|
| `DASHSCOPE_API_KEY` | 阿里云百炼（`~/.bashrc`） | **可用**：qwen-plus 484ms、qwen-max 414ms |
| `DSEEK_2026_SZF_KEY` | DeepSeek 官网 | **可用**：deepseek-chat 845ms |
| `VOLCANO_ARK_APIKEY` | 火山方舟 | **不可用**：`/api/v3` 返回 401 `AuthenticationError`（模型 id 或 key 类型不匹配） |

注意：这些键在 `~/.bashrc` 里，**非交互 shell 不会自动加载**（`bash -lc` 读不到）。
复现要先 `eval "$(grep -E '^export DASHSCOPE_API_KEY=' ~/.bashrc)"`。

## 3. 用同一套三问实测（`scripts/v2_answer_e2e.py`）

同一语料（333 docx + 329 xlsx，CJK 补丁，top_k=5），失败一律是"引用核验不过"：

| 模型 | 样本 | 通过 | 通过率 | 失败形态 |
|---|---|---|---|---|
| 本地 `qwen2.5-7b` | 12 | 7 | **58%** | 4 次"材料不足"（全在第一问）+ 1 次拼接引用 |
| 百炼 `qwen-plus` | 12 | 10 | **83%** | 2 次"材料不足"（都在第二问） |
| 百炼 `qwen-max` | 3 | 2 | 67% | 1 次"材料不足" |
| `deepseek-chat` | 3 | 2 | 67% | 1 次"材料不足" |

分查询看差异才看得清：

- **第一问「多指标对账口径是什么」**：本地 7B **0/4**（答案行就在材料里，模型连不上），
  qwen-plus **4/4**。这是唯一能明确归因于模型能力的差距——需要"标题句 + 数据行"的联合理解。
- **第二问「授信额度是多少」**：本地 3/4、qwen-plus 2/4，两边都会挂。

## 4. 一处我自己的评估错误（必须先纠正）

第二问的失败**不是模型问题**，是**我的问句有歧义**：表里 4 个客户有 4 个不同额度，
"授信额度是多少"本身没有唯一答案。改成「江南装备科技有限公司的授信额度是多少」后：

| 模型 | 结果 |
|---|---|
| 本地 `qwen2.5-7b` | **2/2 通过** |
| `qwen-plus` | **2/2 通过** |

所以之前"本地模型 58%"里有一部分是我的测试集缺陷造成的。
更正后的结论：**本地 7B 的真实短板集中在"跨行/标题与数据行联合"这类语义连接上**，
不是普遍的引用纪律问题。

## 5. 结论与建议

- **建议换 `qwen-plus` 做回答组装**：在唯一能归因的差异点（第一问）上 4/4 vs 0/4，
  且延迟 ~0.5s/次，成本可控；`deepseek-chat` 与 `qwen-max` 各测 3 次样本太小，不足以定论。
- **不要换 embedding**：换 bge-m3 会让已建向量全部失效，收益也未见。
- **先把测试集修好**：像第二问这种歧义问句必须改写或加限定，否则通过率反映的是出题质量。
- 火山方舟这把 key 401，暂不纳入候选。

## 6. 还没做

- 百炼只在 3 条问句上跑过，没有覆盖多跳、跨文档、表格合计；
- 未评估外部模型的**限流与失败重试**、密钥轮换、按量成本；
- 未把 `qwen-plus` 接入产品默认路径（只作为可选项加进脚本），切换需要单独评审。

## 7. 回答段接入 DeepSeek-V4.1-Flash（2026-10-31）

要求：回答段用 `DSEEK_2026_SZF_KEY` + 模型 `Deepseek-4.1-Flash`。

### 7.1 模型 id 与用户说法不一致，按 API 为准

查 `GET https://api.deepseek.com/v1/models`（同一把 key）：

```json
{"id":"deepseek-flash","name":"DeepSeek-V4.1-Flash","context_window":1048576,
 "max_output_tokens":393216,"input_modalities":["text","image"],
 "effort":{"supported_levels":["low","high","max"],"default_level":"high"}}
```

**请求里要传的 model 是 `deepseek-flash`**，不是 `DeepSeek-4.1-Flash`（后者是展示名）。
同仓还有 `deepseek-v4-pro` 可选。

### 7.2 实现（`graph_engine_adapter/llm_config.py`）

- 代码里**不写密钥**，只写"环境变量名"；默认 `LLMKE_ANSWER_KEY_ENV=DSEEK_2026_SZF_KEY`；
- 默认端点 `https://api.deepseek.com/v1`、默认模型 `deepseek-flash`；
- `LLMKE_ANSWER_PROVIDER=local` 可整体切回本机 18092（无 key 也能跑）；
- `describe()` 只输出 provider/base/model/key_env/key_present/key_len，**不含键值**，可直接进日志；
- 缺键时报"请设置环境变量 X"，不在请求阶段抛 401 让人猜；
- 401/403 不重试（重试无意义），其余错误退避重试。

### 7.3 一个真实坑：JSON 被截断，报错却像"格式错误"

首轮 Q 验收出现 `UNPARSEABLE_LLM_OUTPUT: JSONDecodeError: Unterminated string`。
根因不是模型不会写 JSON，而是 `max_tokens=512` 把它截断了。
处理：默认提到 1024，并**按 `finish_reason=="length"` 判定后加倍预算重试一次**；
截断与"输出不合法"必须分开报，否则会去调提示词治错病。

### 7.4 结果

| 模型 | 样本 | 通过 | 备注 |
|---|---|---|---|
| **DeepSeek-V4.1-Flash（deepseek-flash）** | **18** | **18（100%）** | 6 轮 × 3 问，引用均为单行原文 |
| 本地 `qwen2.5-7b-instruct` | 12 | 7（58%） | 短板在"标题句+数据行"联合 |
| 百炼 `qwen-plus` | 12 | 10（83%） | — |

样例（`deepseek-flash`）：

```
问：多指标对账口径是什么
答：多指标对账口径为：日均存款按业务日跨账户汇总/天数；用电量按月度同比。
引：日均存款 | T-CORE-001 | 按业务日跨账户汇总/天数（file_id=333）
```

Q 验收随之变化：`biz:端到端业务问答` 从 NOT_IMPLEMENTED 变成**真实检查**
（跑 `v2_answer_e2e.py` 单问），现 **26 PASS / 0 FAIL / 1 NOT_IMPLEMENTED**（只剩社区/global 消费）。

### 7.5 产品化前还要做的

- 密钥注入：现在依赖 `~/.bashrc`，非交互 shell 读不到；服务化要走部署注入，不能进仓库；
- 限流与成本：未统计 token 用量与 QPS 上限；
- 失败降级：DeepSeek 不可用时是否回落本地 7B，需要产品决定（回落会让引用质量下降）；
- 覆盖面：18 次都在 3 条问句上，多跳/表格合计/跨文档未测。
