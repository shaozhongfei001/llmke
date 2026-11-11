
# P2-L8 · Loop 规划（开发前定验证标准）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-08`（`docs/v2-tasks/TASKS.yaml`）
- 阶段 P2 平台同源链路收尾，Loop 8 `影子命名空间`
- holder：`python-engineer` → `DEV_SELF_CHECK_PASS` → baton
- 依赖：`T-D2MD-07`（L7，同源闸门 + kb_state v2）
- 状态：**标准已锁定，待 L7 内部收口后派工**

> 依据：`03-IMPLEMENTATION.md` §P2-4（`:196-219`）、`IMPLEMENTATION-QUEUE-V2.md:100-106`、`04-ACCEPTANCE.md` B-1/B-2。

---

## 一、Scope

| 允许 | 路径 | 约束 |
|---|---|---|
| 改 | `services/rag-alg/alg_retrieval_service/app/projection_read.py` | 对齐读前缀（`INGEST_READ_PREFIX`），默认仍读旧命名空间；不改检索算法 |
| 改 | `ingest_pipeline/index_writer.py` | 仅 `index_prefix` 相关（默认 `v2cand_` 已具备）；不得改 L6/L7 已验收的 body 形状、`file_id` fail-closed、`delete_scope` |
| 新增 | 平台侧测试与 fixtures | 反例先 FAIL 再 PASS |

| 禁止 | 理由 |
|---|---|
| 写旧命名空间 `<kb>` / `table_chunks_<kb>` / Milvus `_<kb>` | 影子必须独立，旧索引只读 |
| 默认切读（`INGEST_READ_MODE=legacy` 保持不变） | P6 才放量；本 loop 只准备能力 |
| 启停服务、改运行态配置 | 在线检索服务运行中 |
| 改 L1~L7 语义、`_table_pk` / `table_summary_id`、设计包 / `MANIFEST.sha256` / `TASKS.yaml` / doc2md 仓 | 越界 |

### 影子写入的授权边界（本 loop 关键）

设计包验收命令含 `curl v2cand_kb_9/_count`（真实影子索引）。本 loop **默认只做离线/mock 验证**：

- **模式 A（默认）**：`projection_read` 前缀对齐 + `index_writer` 计划目标名断言 + `INGEST_READ_*` 开关行为，全部 mock/离线，**不真实创建索引**。
- **模式 B（需 Owner 明确授权）**：真实创建 `v2cand_kb_9` / `v2cand_table_chunks_kb_9`（ES）与 `v2cand_kb_9`（Milvus collection），仅写 `v2cand_` 前缀；写前记录索引清单、写后 `_count` 核对；旧索引必须 0 变化。

未获授权时不得进入模式 B，也不得用「只写影子不算写线上」自行放行。

---

## 二、R-0 结论与 TL 裁定（12:1x，已裁定，可进入实现）

成员 R-0（`P2-L8-20261108T120209.log`）发现 PLAN 三处前提不成立，TL 独立复核**全部成立**，并纠正一处数字：

**键集差异实测**：影子（`index_writer.build`）**36 键** / 线上 **38 键**；影子多 `artifact_id`、`content_hash`；影子缺 `n_cols`、`n_rows`、`parsed_text_ref`、`source`（成员只报了 2 个，漏 `n_rows`/`n_cols`）。

**三处前提失效**：
1. **命名不一致**：读侧 `"table_chunks_" + "v2cand_kb_9"` = `table_chunks_v2cand_kb_9`，写侧 `v2cand_table_chunks_kb_9` → snapshot 下表格通道静默空；错名还被 `test_projection_read.py:20-26` 固化成契约。
2. **图召回断**：`multiple_retrieval.py:463-470` 把非 `faq_/table_chunks_/table_summary_` 前缀者当 kb 名 → `{"kb": "v2cand_kb_9"}`，18094 按 `kb_9` 目录组织 → 查不到。
3. **`shadow` 与 `test_runtime_switches.py:22` 冲突**，且 `resolve()` 内结构上做不到「双读不改结果」。

**五项裁定**：

| # | 裁定 |
|---|---|
| Q1 | **读侧改为「整个索引名前缀」，用显式 `channel_names` 映射**（`{"text": "v2cand_kb_9", "table_chunks": "v2cand_table_chunks_kb_9", "table_summary": "v2cand_table_summary_kb_9", "faq": "v2cand_faq_kb_9"}`），**禁止再用字符串拼接**；`index_writer._target_name` 不动；必须修正 `test_projection_read.py` 的错名断言，并加「读侧通道名 == 写侧 `_target_name` 输出」逐字对拍 |
| Q2 | `resolve()` 的 info 增 **`graph_kb`**（`v2cand_kb_9 → kb_9`）；`multiple_retrieval.py` 取 kb 处优先用它（一行）；断言 snapshot 下 graph 请求 `kb=kb_9` |
| Q3 | `table_summary` 影子通道**本 loop 不新增**，info 增 `missing_channels=["table_summary"]`；已写入 `T-D2MD-17.blocker`（切读前必须补齐，否则表格总结静默空） |
| Q4 | **授权**改 `RUNTIME-SWITCHES.yaml` + `test_runtime_switches.py`；**`shadow` 降级**为「只解析名字 + 返回 `shadow_names` 供比对，不发第二次查询」，真双读留 P6 |
| Q5 | **授权** `index_writer.build` additive 补 **4 个键**：`source`（取 `file_path`）/ `parsed_text_ref`（表格 `"table"`）/ `n_rows` / `n_cols`（取 IR，缺失 `None` 不编造）；同步更新 L6 的 F1 断言；evidence 必须写「影子 = 线上 38 键 + 2 个 V2 溯源键」，**不得声称完全一致** |

**授权改动面（超出需回 TL）**：`projection_read.py` / `retrieval_service.py` / `multiple_retrieval.py`（仅 kb 取值一行）/ `index_writer.py`（additive 4 键）/ `RUNTIME-SWITCHES.yaml` / `test_projection_read.py` / `test_runtime_switches.py` / `test_index_writer.py` / 新增 L8 测试与 fixtures。

**新增三条断言**：① 读写通道名逐字对拍；② snapshot 下 graph 请求 `kb=kb_9`；③ 影子 metadata = 线上 38 + `artifact_id`/`content_hash`，且 4 个读侧依赖键齐全。

---

## 二·原 R-0 核实清单（已执行完毕，保留留痕）

1. `projection_read.py` 现状：是否已有 `INGEST_READ_MODE/PREFIX`、默认值、读哪些索引名、是否有 `canary.load` 接口；
2. `index_writer` 的 `index_prefix` 是否已全链路可传（`consume_for_kb` → `build`）；
3. 现有 `v2cand_*` 索引/集合是否存在（`_cat/indices/v2cand*`、Milvus list）；
4. 读路径切影子后，引用回查（`parse_artifact_id` / `pk`）是否仍有效；
5. 建议：模式 A 的断言清单 + 模式 B 的准备清单。

---

## 三、可证伪断言（退出标准，模式 A）

### I1 · 前缀对齐且默认不碰线上

```
index_writer.build 默认 index_prefix="v2cand_"；目标名 v2cand_<kb> / v2cand_table_chunks_<kb>；
projection_read 默认 INGEST_READ_MODE=legacy → 读旧命名空间；
反例：把 index_prefix 设为 "" 或 <kb> → 必须拒绝（防误写线上）
```

### I2 · 读模式开关行为

```
INGEST_READ_MODE ∈ {legacy, shadow, snapshot}；
legacy → 旧索引；shadow → 双读并比对（不改变返回结果）；snapshot → 只读 v2cand_*；
未知值必须拒绝，不静默默认。
```

### I3 · 旧命名空间零影响

```
模式 A 下：旧 <kb> / table_chunks_<kb> / _<kb> 的写入计划不存在；
索引清单与 _count 前后一致。
```

### I4 · 回滚可逆

```
删 v2cand_* 即回到 legacy；INGEST_READ_MODE 改回 legacy 后行为与改动前一致（回归测试比对）。
```

### I5 · 回归

```
L1~L7 既有测试全 PASS（31 + 24 = 55 条平台侧）；doc2md 仓 14 项封存态不变。
```

### 组件级反例清单

| # | 反例 | 期望 |
|---|---|---|
| R-1 | `index_prefix` 为空/等于 kb | 拒绝（I1） |
| R-2 | `INGEST_READ_MODE=bogus` | 拒绝，不静默默认（I2） |
| R-3 | 影子读时混入旧索引名 | I2 FAIL |
| R-4 | 旧索引 `_count` 变化 | I3 FAIL |
| R-5 | 回滚后行为与改动前不一致 | I4 FAIL |
| R-6 | 既有 55 条回归退化 | I5 FAIL |

---

## 四、验收命令（模式 A）

```bash
cd /home/szf/data/dev/llmke-v2
V2=/home/szf/data/dev/llmke-v2-toolenv/bin/python
HIP=/home/szf/data/dev/hipporag-toolenv/bin/python
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest <新测试> -q
PYTHONPATH=services/rag-alg/index_data_service $V2 -m pytest tests/test_rag_projection.py \
  services/rag-alg/index_data_service/tests/ -q          # I5 回归
$HIP -m pytest <新测试 + 回归> -q                          # 交叉
grep -rn 'INGEST_READ_MODE\|INGEST_READ_PREFIX' services/rag-alg/ | head
curl -s http://127.0.0.1:19200/_cat/indices/v2cand*?h=index,docs.count   # 应为空（模式 A 不创建）
ss -tlnp | grep -E ':(19200|19526|19527|19995|18094|19531|18082|18083)\b'
git -C /home/szf/data/dev/llmke-v2 status --short ; git -C /home/szf/data/dev/doc2md status --short
```

evidence 写 `docs/v2-tasks/evidence/P2-L8-<ts>.log`：R-0 结果、diff 全文、反例 FAIL→PASS、索引清单与 `_count` 前后对比、解释器标注。

---

## 五、Baton / 回滚 / 依赖

- **Baton**：`DEV_SELF_CHECK_PASS` → TL 复核 → 可派工 P3-L9。`QA_PASS` 仍挂起待 G-4。
- **回滚**：恢复 `projection_read.py` / `index_writer.py`，删除新增测试；若已进入模式 B，删除 `v2cand_*` 索引，旧索引不动。
- **依赖**：`T-D2MD-09`（P3 18094 delta 端点）可与本 loop 并行；P6 切读依赖本 loop 的开关与影子索引。
