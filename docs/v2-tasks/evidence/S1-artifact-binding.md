# S1 · doc2md 产物绑定（D1）证据

角色：s1-artifact-binding（V2 收口团队 S1）
日期：2026-11-02
工作目录：/home/szf/data/dev/llmke-v2

## 1. 做了什么

新增 doc2md 产物绑定层：把一次解析产物(ParseArtifact)投影成带公共身份(`artifact_id` +
`content_hash`)的 `docs` 列表，使 RAG 索引与图谱建图可以证明"引用的是同一版本产物"。

只新增 3 个文件，**未改任何既有文件**：

| 文件 | 行数 | md5（现拼） |
|---|---|---|
| `services/rag-alg/index_data_service/graph_engine_adapter/artifact_binding.py` | 199 | `e81e51510ff9ea858c587b7f547ba1cc` |
| `tests/test_artifact_binding.py` | 204 | `2d6f3c537b22967855f2d3f7dac96409` |
| `docs/v2-tasks/evidence/S1-artifact-binding.md` | — | 本文件 |

## 2. 先读真实结构（字段口径，不臆造）

1. `services/rag-alg/index_data_service/graph_engine_adapter/assertions.py:33-41`
   `SourceRef` 实际字段 = `file_id / artifact_id / channel="text" / locator=""`。
   即：**来源三要素（文件、产物、定位）在平台侧已有位置**，但建图入口没填 `artifact_id`。
2. `contracts/schema/llmke-document-pipeline-v2.json`
   - `ParseArtifact`（L131-232）必填含 `artifact_id`（1-256 字符串）、`content_uid`（`^[0-9a-f]{64}$`）。
   - `ArtifactBinding`（L233-270）字段 `file_id / document_version / content_uid / parse_artifact_id / …`。
   - `SourceRefV2`（L671-...）同样带 `parse_artifact_id` + `parsed_text_hash`。
   - `locator` 在合同里是**对象**；闭集 `TextLocator(text_span)` / `CellLocator(table_cell)` /
     `FigureLocator(figure_asset)`（L580-670、L705-717）。
3. `scripts/v2_graph_bridge.py:36-44,74-86`：投影侧从 `metadata.parse_artifact_id` 取产物身份，
   缺省填空串；`to_refs()` 再把它塞进 `SourceRef.artifact_id`。
   → 说明"桥已有位置"，但缺一道**校验**：任何人传 `artifact_id=""` 或换一份正文都能过。
4. `graph_engine_adapter/api.py:38-46`（当前缺口）：`BuildDoc = {file_id, text, locator?}`，
   `BuildRequest = {docs, root}` —— `/v2/graph/build` 全链路**没有 artifact 字段**，
   所以今天无法证明"RAG 与图谱同一 Artifact"。本模块就是补这个校验点。

## 3. 规则实现（每条带"为什么")

`bind_artifact(artifact) -> dict`，输入 `{artifact_id, document_id, chunks[{text,locator,file_id}]}`：

1. `artifact_id` 必须 64 位小写十六进制，否则抛 `ArtifactBindingError`。
   为什么：`mapping.input_unit_id()` 直接把 `parse_artifact_id` 拼进 `sha256(f"{artifact}:{channel}:{seq}")`，
   非定长/含分隔符的值会让不同组合撞 id；大写、变长同理。fail-closed 才能保证
   `assert_same_artifact` 的字符串比较有意义。
2. 每个 chunk 必须有非空 `text` 与 `locator`，缺 `locator` 直接拒绝（D7 要求可定位）。
   `locator` 同时接受字符串（`"p1"`、`"table:r2"`）与合同对象；对象必须是闭集 `kind`
   之一，否则无法判断"哪种可定位"，等于没有 locator。`text` 原样保留、不 strip：
   引用正文必须与产物逐字节一致，否则 quote_hash 对不上原文。
3. 计算 `text` 的 sha256；chunk 自带 hash（`text_sha256` / `content_hash` / `hash` / `sha256`）
   且不匹配 → 拒绝。带了但本身不是 64 hex 也拒绝：**无法校验的"校验字段"等于没有校验**。
4. 输出 `{artifact_id, document_id, content_hash, docs:[{file_id,text,locator,artifact_id}]}`，
   `docs` 顺序与输入一致（换序即换产物），`file_id` 缺省回落 `document_id`。
5. 空 `chunks` → 拒绝。为什么：空产物会让 `content_hash` 退化成"空串哈希"，任意两个空产物
   都"绑定成功"——这是最常见的假绿来源。

`content_hash` 口径（写死在模块常量 `CONTENT_SPEC = "llmke.artifact-binding.chunks/1"`）：

```
sha256(json({schema: CONTENT_SPEC,
             chunks: [{locator: <locator 稳定键>, text_sha256: sha256(text)}, ...] 按输入顺序},
            ensure_ascii=False, sort_keys=True, separators=(",",":")))
```

- 不把 `artifact_id` 混进 `content_hash`：`artifact_id` 是**编号**、`content_hash` 是**内容**，
  两者独立才能交叉校验（编号同而内容变 = 被原地改写；内容同而编号变 = 重新解析过，不算同一产物）。
- locator 若是对象，按 `sort_keys` 序列化参与哈希：键序不承载语义，按插入序会造成"同一产物算出不同 hash"的误报。
- spec 标记进哈希：换聚合口径（例如改成去重块）时 hash 必须变，否则两种口径会算出同值、绑定失效。

`assert_same_artifact(a, b)`：`artifact_id` 或 `content_hash` 任一不同即抛错；参数不像
`bind_artifact` 输出（缺字段）也抛错，**不返回 True/False**，避免调用方忽略返回值。

模块不读文件、不联网、不 import 引擎（无 torch/vllm 依赖，可在无 GPU 环境跑）。

## 4. 测试真跑（真实输出）

命令：

```
cd /home/szf/data/dev/llmke-v2
PYTHONPATH=services/rag-alg/index_data_service \
  /home/szf/data/dev/llmke-v2-toolenv/bin/python -m pytest tests/test_artifact_binding.py -q
```

真实输出：

```
..............................                                           [100%]
30 passed in 0.05s
```

30 个用例（含 parametrize）覆盖任务要求的 6 类：

| # | 要求 | 用例 |
|---|---|---|
| 1 | 合法 2 块（段落+表格）→ docs 与 hash 正确 | `test_bind_two_chunks_keeps_order_and_hash`、`test_file_id_falls_back_to_document_id`、`test_chunk_declared_hash_matching_is_accepted` |
| 2 | artifact_id 非 64 hex → 拒绝 | `test_bad_artifact_id_rejected`（7 组：空/63/65/大写/非 hex/人类可读/None/整数） |
| 3 | chunk 缺 locator → 拒绝 | `test_missing_locator_rejected`（6 组：缺失/空串/空白/空对象/自造 kind/非字符串）；另有 `test_structured_locator_from_contract_is_accepted`、`test_locator_key_order_does_not_change_content_hash` |
| 4 | 自带 hash 不匹配 → 拒绝 | `test_declared_hash_mismatch_rejected`、`test_declared_hash_not_hex_rejected` |
| 5 | 空 chunks → 拒绝 | `test_empty_chunks_rejected`（3 组）、`test_empty_text_rejected` |
| 6 | assert_same_artifact 不同抛错/相同通过 | `test_assert_same_artifact_passes_for_same_product`、`..._rejects_different_artifact_id`、`..._rejects_same_id_different_content`、`..._rejects_reordered_chunks`、`..._rejects_unbound_input` |

期望哈希不是调被测模块算的：`expected_content_hash()` 里 spec 字符串与序列化参数是**手写常量**，
模块改口径它就会失败（防"期望值跟着实现一起漂移"）。

### 4.1 解释器口径与 skip 说明（不把 skip 记成 pass）

本文件用例在**两个**环境都实跑过，结论一致（**30 passed，0 skipped**，无 skip）：

| 环境 | 解释器 | 本文件结果 |
|---|---|---|
| v2 环境 | `/home/szf/data/dev/llmke-v2-toolenv/bin/python`（3.10.12，**无 fastapi**） | `30 passed in 0.05s` |
| 图/兼容层环境 | `/home/szf/data/dev/hipporag-toolenv/bin/python`（3.11.15，fastapi 0.162.0） | `30 passed in 0.04s` |

对照：同一批文件在 v2 环境跑三个文件是 `37 passed, 1 skipped`，skip 的是
`tests/test_legacy_shim.py` **整个文件**（`could not import 'fastapi': No module named 'fastapi'`）；
在 hipporag 环境同一命令是 `59 passed`（=30+7+22）。**skip 不等于 pass**，故：
图/兼容层（含 `test_legacy_shim.py`、`test_graph_api.py`）必须用 hipporag 环境跑，
纯 normalize 与本文档模块在 v2 环境即可。本模块不依赖 fastapi，因此不受此环境影响。

## 5. 真实中文 2 块的一次性验证（真实输出）

```
cd /home/szf/data/dev/llmke-v2 && PYTHONPATH=services/rag-alg/index_data_service \
/home/szf/data/dev/llmke-v2-toolenv/bin/python -c "
import json
from graph_engine_adapter.artifact_binding import bind_artifact, assert_same_artifact
art = {
  'artifact_id': '3f' * 32,
  'document_id': 'DOC-2026-0417',
  'chunks': [
    {'text': '产品甲的单笔最高额度为8000万元，期限不超过三年。', 'locator': 'p1', 'file_id': 'F-333'},
    {'text': '产品乙 | 年化利率 | 4.35%', 'locator': 'table:r2', 'file_id': 'F-333'},
  ],
}
out = bind_artifact(art)
print(json.dumps(out, ensure_ascii=False, indent=1))
print('docs_len=%d artifact_id_uniq=%s' % (len(out['docs']), {d['artifact_id'] for d in out['docs']}))
assert_same_artifact(out, bind_artifact(dict(art)))
print('assert_same_artifact(同产物) -> PASS(未抛错)')
"
```

输出（原样）：

```
{
 "artifact_id": "3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f",
 "document_id": "DOC-2026-0417",
 "content_hash": "447f82d1b5dd0a1b0958289068cf9c4da61d8561521afe5486b4fe55d9321722",
 "docs": [
  {
   "file_id": "F-333",
   "text": "产品甲的单笔最高额度为8000万元，期限不超过三年。",
   "locator": "p1",
   "artifact_id": "3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f"
  },
  {
   "file_id": "F-333",
   "text": "产品乙 | 年化利率 | 4.35%",
   "locator": "table:r2",
   "artifact_id": "3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f"
  }
 ]
}
docs_len=2 artifact_id_uniq={'3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f'}
assert_same_artifact(同产物) -> PASS(未抛错)
```

中文未转义（`ensure_ascii=False`）、2 块顺序与输入一致、`content_hash` 为 64 hex。

## 6. 变异复验（证明断言不是空转）

对模块做 3 次单点变异，每次跑全量用例后立即还原：

| 变异 | 结果 |
|---|---|
| M1 把"缺 locator 抛错"改成 `return None` | `1 failed, 29 passed`（`test_missing_locator_rejected[None]`） |
| M2 把"自带 hash 不一致抛错"改成 `if False:` | `1 failed, 29 passed`（`test_declared_hash_mismatch_rejected`） |
| M3 把 `CONTENT_SPEC` 的 `/1` 改成 `/2` | `1 failed, 29 passed`（`test_bind_two_chunks_keeps_order_and_hash`） |

还原后：模块 md5 = `e81e51510ff9ea858c587b7f547ba1cc`（与变异前备份一致，`cmp` 无差异），
用例 `30 passed`。

**过程中踩到的真坑（记录，供他人复用）**：M3 只用 `sed` 把 `1` 改 `2`，字符数不变；`cp` 还原后
源文件大小与 mtime 秒级与变异时相同，CPython 认为
`__pycache__/artifact_binding.cpython-310.pyc` 仍有效，**继续加载变异版字节码**，
导致"已还原但测试仍红"。处置：删掉该 pyc（该文件不在版本库中，`git ls-files` 为空）后复跑即绿。
→ 做变异测试时，还原后务必确认加载的是新字节码（删 pyc 或 `python -B`），否则误判。

## 7. 我没做的部分（边界）

- **没接进 `api.py`**：`BuildDoc` / `BuildRequest`（`api.py:38-46`）未改，`/v2/graph/build`
  仍只收 `{file_id,text,locator}`；本模块是纯函数层，接线由其他角色决定。
- **没改既有文件**：`assertions.py`、`mapping.py`、`normalize.py`、`v2_graph_bridge.py`、
  `contracts/**` 一律未动（`git status` 中 `normalize.py` / `TASKS.yaml` 的 `M` 不是我改的）。
- **没落库、没改合同**：`content_hash` 只是模块内聚合口径，未登记为合同字段，也未写入任何
  `content_uid` / `parsed_text_hash` 字段（合同里那几个哈希的生成者仍是 doc2md / 流水线）。
- 未执行 `git add` / `git commit`；未启动或停止任何服务；未联网。
