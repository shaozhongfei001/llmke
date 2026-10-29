# W01 抽取稳定性（R15 / owner: extract-w01）

状态：**代码完成，待 TL 统一验证**（未重启任何服务、未改数据库、未 commit、未动 Nebula/ES）。
工作树：`/home/szf/data/dev/llmke-r12`，分支 `feature/R12-real-rag`，改动文件只有 1 个：
`services/rag-alg/index_data_service/index_graph_service/graph_extract.py`（+227/−0 语义行，未删除任何既有日志与注释，新增内容一律以 `R15-W01` 标注）。

---

## 1. 改了什么

### 1.1 单块重试（`generate_graph_relations`）

- 每次抽取请求包进一个 `attempt` 内循环：请求 → `process_relation_response` → 判定是否"拿不到可用结果"→ 不可用则 `time.sleep` 退避后**重发同一条 `extract_message`**。
- 重试上限 `EXTRACT_MAX_RETRIES`（默认 **2**，退避默认 **1s / 3s**），且预算是**按 passage 记**而不是按轮次记，所以最坏情况只多 2 次 LLM 调用 —— 这是刻意为之：原实现 `max_rounds=5 × samples=3` 已经能跑到 200s+，重试不能再线性放大。
- 失败判定（`_classify_attempt`，不重试合法空）：
  | 现象 | 判定 | 是否重试 |
  |---|---|---|
  | 返回文本为空/全空白 | `空响应` | 是（请求失败或模型无输出） |
  | 没有任何 `("entity"::` / `("relationship"::` 候选行 | `无可解析行` | 是（模型跑题） |
  | 有候选关系行但 0 条落地 | `关系行全部丢弃` | 是（**"0 边"的直接原因**） |
  | 有实体落地，或 ≥1 条关系落地 | 可用 | 否（不为正常块付额外费用） |
- prompt 语义不变：`messages` / `system_prompt` / `user_prompt` / `CONTINUE_PROMPT` / `LOOP_PROMPT` / `max_tokens` / `temperature` 全部不动。唯一变化是第 2 次起的 `seed`（42 → 43 → 44）：`temperature=0 + 固定 seed` 实测会**稳定复现同一处截断**，原样重发等于空转。需要"严格同参重试"时 `GRAPH_EXTRACT_RETRY_VARY_SEED=0`。
- 留痕日志（"第几次成功/最终失败"）：
  - `单块重试：第N次尝试不可用（原因），Xs 后重发同一请求（prompt 不变, 已重试1/2）`
  - `单块重试：第N次尝试成功（passage_chars=…, 首次失败原因=…, seed=…, 本轮落库三元组=…）`
  - `单块重试：最终失败（共尝试N次, 原因=…, passage_chars=…, 已重试2次）`
- 最终失败的轮次**直接跳出多轮循环**（不再用"还有遗漏吗"追问），把兜底交给既有的补充采样（`GRAPH_EXTRACT_SAMPLES`，temperature=0.3）。

### 1.2 输出结构校验（`process_relation_response`）

- 新增常量：`ENTITY_FIELDS=3`、`RELATION_CORE_FIELDS=3`、`RELATION_MIN_FIELDS=4`（tag + 三元组 3 段）、`RELATION_MAX_FIELDS=5`（+ 可选描述段）。
- 关系行三类异常全部打 `字段数异常` 并计数（`field_anomalies` / `parse_failed_lines`）：
  1. **不足**（< 4 段，例如实测的 `("relationship"::评级授信` 被截断的半行）→ 丢弃 + `ERROR`。日志同时保留原文片段，`关系行字段不足` 字样仍在，历史 grep 不受影响。
  2. **超出**（> 5 段，如描述里自带 `::`）→ **只计数 + `WARNING`，仍然落地**（描述按剩余段拼接）。这是刻意的：把"描述含双冒号"当脏数据丢弃会直接减少边数，等于用丢数据换好看的统计。
  3. **核心字段为空**（关系名/源/目标任一段为空）→ 丢弃 + `ERROR`（原实现是静默 `continue`，日志里看不到边为什么少）。
- 实体行同样要求**恰好 3 段**，异常时打 `数据处理失败,字段数异常(实体行期望3段,实际N段),<行>`（保留原 `数据处理失败` 前缀）。
- 修正 `line[1:-1]` 的硬切问题：新增 `_strip_wrapper()`，只在确实以 `)` 结尾时才去掉尾字符。原来遇到截断行会把最后一个真实字符也切掉，导致字段值莫名少一位（例如实体类型变成 `:`）。
- 兼容性：`stats` 是**可选出参**（默认 `None`），函数仍返回原来的三元组 `(entity_dict, relation_dict, filtered_response)`，既有调用方式与返回值形状不变。

### 1.3 可诊断统计

`generate_graph_relations` 返回前输出**一行**固定格式（单行、`k=v`、grep 键 `R15-W01 EXTRACT_STATS`）：

```
R15-W01 EXTRACT_STATS passage=1 passage_chars=… llm_calls=… rounds=… retries=… \
candidate_lines=… parse_failed_lines=… field_anomalies=… valid_entities=… valid_triples=… elapsed_ms=…
```

- `passage` 固定 1（本函数按 passage 调用，字段保留以和批量侧口径一致）。
- `llm_calls` 覆盖**全部**调用：抽取轮、续写判定、重试、补充采样 —— 否则"总耗时"无法解释。
- `parse_failed_lines` = 字段数异常丢弃行 + 其他解析异常行；`field_anomalies` 单独给出（含 "超出但已救回" 的行）。
- 该行在 `samples` 循环之后输出，异常路径（`except: traceback.print_exc()`）也会走到，不会漏打。

### 1.4 新增可配置项

| 环境变量 | 默认 | 含义 |
|---|---|---|
| `GRAPH_EXTRACT_RETRY_TIMES` | `2` | 每个 passage 最大重试次数 |
| `GRAPH_EXTRACT_RETRY_BACKOFF` | `1,3` | 各次重试前的等待秒数 |
| `GRAPH_EXTRACT_RETRY_VARY_SEED` | `1` | 重试时是否递增 seed（`0`=严格同参重发） |

## 2. 为什么这么改

实测事实：同一文件连续解析四次得到 155 条 / 0 边 / 59 条 / 200s+ 未结束；错误日志反复出现
`关系行字段不足: ("relationship"::评级授信`。查看 `logs/graph_service/graph_info_2026-10-29.log` 可见同期模型输出里同一块**能正常吐出 15 条实体 + 11 条关系**（`("relationship"::办理流程-包含->::办理流程::受理::…`），说明不是"模型不会抽"，而是**单次输出被截断/退化**后，解析侧：

1. 该行解析失败 → `logger.error` → `pass`，**整条丢弃**；
2. 一个 passage 的失败只在日志里留一条 error，**没有重试**、**没有计数**、**没有汇总**；
3. 因此"0 边"与"155 条"在日志上完全无法区分，也无法判断是模型问题还是解析问题。

R15 要求"完成要有判据"：所以补的不是"再多采样一次"，而是三件可被外部验证的东西 —— 重试（可救回的失败要救回）、结构校验（不可救回的失败要计数且不静默）、单行汇总（能 grep、能算分布）。

## 3. 判据如何验证

已在本机执行（venv：`platform/r12/venvs/graph/bin/python`，工作目录 `index_graph_service`）：

1. **语法**：
   `python -c "import ast; ast.parse(open('graph_extract.py',encoding='utf-8').read())"` → `AST_OK`；`prompt_config.py` → `AST_OK_PROMPT`。
2. **可导入**：`NACOS_SERVER_ADDRESS=127.0.0.1:18848 python -c "import graph_extract"` → `IMPORT_OK`；
   `generate_graph_relations` 签名 `(passage, model_info, server_config, entity_types=None)` 未变，
   `process_relation_response` 签名 `(response_text, entity_dict=None, relation_dict=None, debug=False, stats=None)`（仅追加可选出参）。
3. **调用方兼容**：`graph_service.py:450` 仍为 `relations, entity_dict = generate_graph_relations(content, model_info, server_config, entity_types=entity_types)`，
   返回仍是 `(list[relation], entity_dict)` 二元组，调用处无需改动。
4. **行为验证**（stub 掉 `requests_llm`，`GRAPH_EXTRACT_SAMPLES=1 / MAX_ROUNDS=1 / RETRY_BACKOFF=0,0`，只读内存，不碰网络与存储）：
   - case1 首次截断 → 第 2 次成功：`rels=1 ents=3 calls=3`，日志出现
     `单块重试：第2次尝试成功（… 首次失败原因=关系行全部丢弃, seed=43, 本轮落库三元组=1）`，
     `EXTRACT_STATS … retries=1 … parse_failed_lines=1 field_anomalies=1 valid_triples=1`。
   - case2 三次全截断：`rels=0 calls=3`，日志出现 `单块重试：最终失败（共尝试3次, 原因=关系行全部丢弃…已重试2次）`，
     `EXTRACT_STATS … retries=2 … parse_failed_lines=3 field_anomalies=3 valid_triples=0`（**验证了"最多 2 次"上限，没有无限重试**）。
   - case3 混合脏行（不足 / 超出 / 空端点 / 正常）：`rels=2`，三类 `字段数异常` 各打一条，
     `field_anomalies=3 parse_failed_lines=2`，其中"描述含 `::`"那条**被救回**而不是丢弃。
5. **未做（留给 TL）**：真实 LLM 复放（需重启 graph 服务，按分工不允许我重启）、Nebula/Milvus 回读、整库重建后的边数分布对比。
   建议 TL 验证时用 `grep -c "R15-W01 EXTRACT_STATS"` 与
   `grep -o "retries=[0-9]*\|valid_triples=[0-9]*\|field_anomalies=[0-9]*"` 直接看分布。

## 4. 遗留 / 边界

1. **`prompt_config.py` 未改**（在允许范围内，但确认不需要改）：该文件的 `KG_TRIPLET_EXTRACT_TMPL` 是另一套"（主语,谓语,宾语）逗号格式"模板，在 rag-alg 内**零引用**（`alg_llm_inference_service` 用的是它自己目录下的同名 `prompt_config.py`，含 `PROMPT_TEMPLATES`），图谱抽取链路用的是 `prompts/entity_extraction.py`。改它既不会影响抽取稳定性，也会踩"不得改变 prompt 语义"的约束。所以本次只留下 1 个被改文件。
2. **重试不解决根因**：`("relationship"::评级授信` 这类半行来自模型输出被截断（`max_tokens` 或服务端中途结束）。重试是把"可救回的失败"救回，真正的稳定性还依赖输出预算（`GRAPH_EXTRACT_MAX_TOKENS`）与模型服务端；如果 TL 侧观察到 `retries` 长期接近 1、`parse_failed_lines` 仍高，应往"提高输出预算/换模型"方向查，而不是继续加重试次数。
3. **耗时**：最坏情况每个 passage 多 2 次 LLM 调用（约 +10~20s）。本次没有压低既有 `GRAPH_EXTRACT_MAX_ROUNDS=5` / `GRAPH_EXTRACT_SAMPLES=3`，200s+ 的量级不变；如需压耗时应调这两个变量，不在 W01 范围内擅改。
4. **统计只到 passage 粒度**：没有做模块级全局累加器（gunicorn 多 worker 下全局计数会失真且需加锁），批量口径建议在上层（`llm_generate_triple`，属他人文件）汇总或对日志做聚合。
5. **未覆盖的脏行形态**：模型输出成 `"- (…)"` 带项目符号、或被 markdown 包裹放在代码块里的行，目前仍按"无可解析行"整体重试/丢弃，没有做行内清洗。若 TL 复放时看到这类形态占多数，可作为后续增量（会改变解析语义，需单独裁定）。
