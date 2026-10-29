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
     **TL 裁决 b（2026-10-29）：维持救回，但必须可追溯** —— 该类关系在日志里打 `description_overflow=true`，并在返回的关系字典上追加同名键（只加侧车标记，**不改** `name`/`src_entity`/`dest_entity`/`description` 本身），`EXTRACT_STATS` 行尾追加 `description_overflow=N`。这样社区摘要与引用侧能识别"这条描述不可靠"，将来收紧也有据可查。
     说明边界：现有消费者（`graph_service.llm_generate_triple`、`_generate_filtered_response`）都按字段名取值，多一个键不受影响；**要真正落库/进 metadata 需 `graph_service` 侧消费该键**，那是他人文件，本包不越界，所以标记目前只到「关系字典 + 日志」。不改"丢弃+要求重写"，那是语义变更。
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

**TL 约束（已落实，不得静默回退）**：seed 变化必须记录在案，且**默认值保持"变 seed"（=1）**。理由：`temperature=0` + 固定 seed 会稳定复现同一处截断，默认改回同参重发等于把重试做成空转。任何把该默认值改成 `0` 的调整都必须写入本文件并说明理由。

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

---

## 5. 真实样本（3 passage × 2 次复放）

### 5.1 复放方法与边界（先讲清楚，避免把复放当整库实测）

- **真实部分**：真实 LLM（`127.0.0.1:18092/v1/chat/completions`, qwen2.5-7b-instruct）、真实 ES 原文（经 `127.0.0.1:19527` 代理按 `file_id` 取 `kb_9` / `table_chunks_kb_9` 的 chunk）、真实配置（`nacos-data/snapshot/` 的 `alg_common_py` + `index_graph_config_py` 合并，与运行服务同源）、**同一函数** `generate_graph_relations`、**同一组默认环境变量**（`SAMPLES=3`、`MAX_ROUNDS=5`、重试 2 次/1s,3s），所以每次 `llm_calls=4`（1 主轮 + 1 续写判定 + 2 补充采样）与生产一致。
- **不真实的部分**：**跳过图写入**（不调 `/generate_triple_data`、不碰 Nebula/Milvus），所以产物只存在于内存，**g_kb_9 零写入**。因此本节可支撑"抽取层耗时-产出分布"，**不能**替代 UI 级整库实测。
- **证据日志未被污染**：复放进程导入模块后先 `loguru.logger.remove()` 掐掉文件 sink，再替换 `graph_extract.logger` 为内存记录器。复核：复放前后 `graph_info_2026-10-29.log` 的 `R15-W01 EXTRACT_STATS` 行数恒为 **1**（即只有服务自己那条），服务日志里查不到任何我的复放行。
- 未起停任何服务。耗时存在背景负载（该服务同时在跑 W03 重建），故**耗时数值偏保守**，但同批次内部可比。

### 5.2 样本明细（7 个数据点）

| # | passage | 类型 | chars | llm_calls | retries | parse_failed_lines | field_anomalies | valid_entities | valid_triples | elapsed_ms |
|---|---|---|---|---|---|---|---|---|---|---|
| A0 | file_id 343 | pptx 产品要点 | 123 | 4 | 0 | 0 | 0 | 25 | 29 | 30568 |
| A1 | file_id 343 | 同上 | 123 | 4 | 0 | 0 | 2 | 15 | 25 | 24415 |
| A2 | file_id 343 | 同上 | 123 | 4 | 0 | 0 | 1 | 14 | 16 | 17730 |
| B1 | file_id 332 | docx 纯文本 | 45 | 4 | 0 | 0 | 0 | 3 | 1 | 4848 |
| B2 | file_id 332 | 同上 | 45 | 4 | 0 | 0 | 0 | 3 | 1 | 4567 |
| C1 | file_id 329 | xlsx 表格 | 221 | 4 | 0 | 0 | 0 | 26 | 24 | 73142 |
| C2 | file_id 329 | 同上 | 221 | 4 | 0 | 0 | 0 | 26 | 25 | 73480 |
| D1 | 未知（服务侧） | 长度 101 | 101 | 4 | 0 | 0 | 0 | 6 | 6 | 10576 |
| D2 | 未知（服务侧） | 长度 86 | 86 | 4 | 0 | 0 | 0 | 4 | 3 | 5007 |

A0 是 22:14:48 运行服务（PID 1278581，工作树代码）真实落盘的那条；A1/A2 是本次复放。三者构成同一 passage 的 3 个独立样本。D1/D2 是 22:27 服务侧自己产生的两条（TL 复核期间的重建抽取），非本次复放，一并计入真实样本 —— 它们再次印证"chars 不驱动耗时"：101 字 10.6s vs 123 字 30.5s。

### 5.3 结论：耗时由"输出行数"驱动，不由"输入字数"驱动

- **elapsed 与 `candidate_lines` 强相关**：9 行→4.6s；48 行→24.4s；138 行→73.1s。而 chars 45/123/221 与耗时**不成比例**（123 字反而比 221 字快）。
  → 单次 LLM 调用耗时 1.1s ~ 18.3s，差异来自**生成 token 数**，不是输入长度。这就是"200s+ 未结束"的真正机理：长输出块 × 多轮续写 × samples=3，而不是"文本太长"。
- **每条三元组的时间成本**：约 **1.5 ~ 3.0 s/三元组**（B: 4.6s/1 条；A1: 24.4s/25 条；C1: 73.1s/24 条）。C 组单条最贵，因为表格块要生成大量实体行，实体行不产生三元组但仍耗 token。
- **波动区间**：
  - 表格块（329）**稳定**：三元组 24/25（±4%），耗时 73.1/73.5s（±0.5%）。
  - 纯文本块（332）**稳定**：1/1，4.6/4.8s。
  - 产品要点块（343）**不稳定**：三元组 16 / 25 / 29（最低到最高的 **+81%**），耗时 17.7 / 24.4 / 30.5s，实体数 14 / 15 / 25。
    → 与"同一文件四次 155/0/59"同源现象，只是本轮没跌到 0。**不稳定源是要点式短文本块的自由发挥，不是表格块。**
- 一个可操作推论：把"耗时预算"按 chars 估会系统性错判；应按 `candidate_lines` 或历史 `valid_triples` 估。

### 5.4 重试路径的实际覆盖率（必须如实说）

- 7 个数据点 `retries` 全为 **0**，`单块重试` 关键字在全部 10 个日志文件中计数为 **0**。
- **`grep -c "单块重试：最终失败"` 当前 = 0**（全部日志；本次 6 次复放同样是 0）。
- 结论：**重试分支本轮没有被真实数据触发**，它的正确性目前只有 stub 级证据（§3.4 的 case1 首次截断→第 2 次成功、case2 三次全截断→最终失败），**不是**真实链路证据。样本量 7 个数据点，**不足以给分布（无法给置信区间/分位）**，只能给区间。
- 同时它是"零成本"的正面证据：6 次真实复放全部 `retries=0`，说明新增重试在正常块上不产生任何额外调用或耗时。

### 5.5 一个被真实数据修正的认识（重要）

本轮 3 个 `field_anomalies` **全部是"超出"型**（如 `("relationship"::办理流程->::受理::资料审核::评级授信::审批::放款::智造贷::…` 9 段：模型把整串流程塞进一行），"不足"型（`("relationship"::评级授信` 半行）本轮**一次都没出现**。

- 说明：历史日志里的"关系行字段不足"是**偶发**（截断/退化），不是稳定复现；而"模型把多实体串成一行"是**常见**形态。
- 因此"请求恰好 3 段、否则丢弃"如果按字面实现，会在 343 块上每次丢掉 1–2 条关系 —— 这正是我把"超出"设计成**计数 + 告警 + 仍落地**的原因（与旧代码 `join(_parts[4:])` 行为一致，不是回归）；只有"不足"和"核心字段为空"才丢弃。
- 代价要承认：救回的那条关系，其 description 会带上一串本应是端点的名词（如"受理、资料审核、评级授信…"），描述质量下降。若 TL 认为"描述错误的边不如不要"，需要把"超出"改成丢弃并要求模型重写 —— 那属于语义变更，需单独裁定，本次未做。

### 5.6 附：当天服务侧真实写入记录（含 200s+ 的最坏样本，供估工时）

只读扫 `logs/graph_service/graph_info_2026-10-29.log` 的 `共生成N条图数据` / `生成数据所需时间`：

| 时间 | 处理文本数 | 图数据 | 耗时(s) | 备注 |
|---|---|---|---|---|
| 21:38:39 | 1 | 20 | 27.42 | 旧代码 |
| **21:52:13** | **1** | **22** | **234.59** | **旧代码，对应"200s+ 未结束"** |
| 22:14:48 | 1 | 14 | 30.57 | 工作树 W01 代码（A0 样本） |

- **单 passage 的最坏上界应按 235s 算，不是 30s**；同一天三个样本 27.4s / 234.6s / 30.6s，说明"同一 passage 的耗时波动本身接近一个数量级"，估整库重建工时不能按均值乘块数。
- 22:14:48 之后到 22:26 该服务**没有任何写入行**，全天 `删除` 关键字计数 **0**。这是"边数在 22:15 之后变化"不来自本服务写入的直接证据（当时窗口内只有检索侧只读告警：`chunk 候选…图数据与文本块不同步，可重建图修复`）。

---

## 6. 重试分支的真实覆盖（TL 授权 a：`GRAPH_EXTRACT_MAX_TOKENS` 压低复现）

> **本节所有失败都是人为构造的，不是生产环境发生过的事实。** 约束：无写回（跳过图写入、g_kb_9 零写）、只经环境变量覆盖、不改文件默认值。

### 6.1 先按 TL 给的 `MAX_TOKENS=200` 跑：**没触发重试**

用真实 LLM + 真实 343 passage（123 字），结果 `retries=0`。逐次解析快照：

| MAX_TOKENS | 首个 block 的解析快照 | 结局 | 是否重试 |
|---|---|---|---|
| **200** | candidate=12, entity=7, **relation=5, parsed=4** | 部分成功 → 判"可用" | **否** |
| 120 | candidate=9, entity=7, relation=2, parsed=1 | 部分成功 → 可用 | 否 |
| 100 | candidate=8, entity=7, relation=1, parsed=1 | 部分成功 → 可用 | 否 |
| 80 | candidate=7, entity=7, **relation=0** | 关系块被整段砍掉 → 无关系行失败 → 判可用 | **否** |

**这组负结果比正结果更重要**：`max_tokens` 截断在结构上**无法**触发本重试。三种截断位置对应三种"仍算可用"的结局：
1. 关系行部分完整、部分坏 → 有 ≥1 条落地 → 可用（历史那条 `("relationship"::评级授信` 半行正是这种形态，但它旁边的关系行是好的）；
2. 切点正好落在唯一一条关系行内部 → 这一次才会 `relations_parsed=0` → 重试（窗口极窄，实测 80/100 之间都跨过去了）；
3. 关系块整段被砍掉（cap=80）→ 输出里连关系行都没有 → `candidate_lines>0` 但 `relation_lines=0` → 判可用。

### 6.2 因此改用"真实 LLM 内容 + 构造半行"完成判据（仍然标注为构造）

做法：先让真实模型按真实 prompt 产出一次完整输出（真实模型、真实温度 0/seed 42、默认 max_tokens），**只把这次真实输出在首个关系行内部切一刀**（`("relationship"::包含::智造贷:`），再把这半行喂给同一解析路径。第 1 次给半行、其后给完整输出 = 救回场景；每次都给半行 = 连续退化场景。

**场景 D（救回）日志原文**：
```
WARN 单块重试：第1次尝试不可用（关系行全部丢弃），1.0s 后重发同一请求（prompt 不变, 已重试1/2）
WARN 单块重试：第2次尝试成功（passage_chars=123, 首次失败原因=关系行全部丢弃, seed=43, 本轮落库三元组=3）
INFO R15-W01 EXTRACT_STATS … llm_calls=5 rounds=1 retries=1 candidate_lines=18 parse_failed_lines=1
     field_anomalies=1 valid_entities=4 valid_triples=3 elapsed_ms=1002 description_overflow=0
```

**场景 E（最终失败）日志原文**：
```
WARN 单块重试：第1次尝试不可用（关系行全部丢弃），1.0s 后重发同一请求（prompt 不变, 已重试1/2）
WARN 单块重试：第2次尝试不可用（关系行全部丢弃），3.0s 后重发同一请求（prompt 不变, 已重试2/2）
ERROR 单块重试：最终失败（共尝试3次, 原因=关系行全部丢弃, passage_chars=123, 已重试2次）
INFO R15-W01 EXTRACT_STATS … llm_calls=5 rounds=1 retries=2 candidate_lines=15 parse_failed_lines=5
     field_anomalies=5 valid_entities=2 valid_triples=0 elapsed_ms=4005 description_overflow=0
```

判据核对：**D 满足**「`第2次尝试成功` + `retries>=1`」；**E 满足**「`最终失败（共尝试N次…已重试2次）` + `rels=0`」；退避实际为 **1.0s / 3.0s**，与配置一致；重试预算 2 次封顶，没有额外第 4 次。

### 6.3 必须一起报的盲区（这是新发现，需 TL 裁定）

重试**只覆盖"关系行存在但全坏"**，对"关系块整段被截断而缺失"（§6.1 第 3 类）**是盲的**：那种情况输出里一条关系行都没有，分类器看到的是"有实体、无关系行"，与"合法无关系资料（D8）"无法区分，因此判可用、不重试。

- 若历史上的"0 边"属于这一类，**重试救不回来** —— 这也是为什么 §5.4 的结论只能写"未被生产触发"，不能写"已解决"。
- 三个候选修法（我**没有**擅自实现，都改变重试频率/成本或跨文件）：
  1. **末行完整性**（推荐，零依赖、不跨文件）：完整输出末行必以 `)` 或 `########` 结尾；实测 80/100/120/200 四组截断输出末行都不以 `)` 结尾。加一条"末行不以 `)` 结尾 → 判截断 → 重试"即可精确覆盖第 3 类，且不会误伤合法空（合法空通常直接返回空文本）。
  2. **暴露 `finish_reason`**：OpenAI 协议里能区分 `stop` / `length`，但 `graph_fun_tool.requests_llm` 把它丢了，要用必须改他人文件。
  3. 用 `candidate_lines`/实体数低于历史中位数触发，需先有基线，成本最高。
- 我的建议是选 1，但要 TL 明确"重试频率会上升、最坏成本仍 +2 次/passage"后再动手。
