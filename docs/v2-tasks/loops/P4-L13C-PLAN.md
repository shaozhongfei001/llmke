# P4-L13-C · Loop 规划（运行态，Owner 已授权 2026-11-08 16:2x）

- 切片 `VL-DOC2MD-INC` / 任务 `T-D2MD-13` C 段
- **Owner 授权范围**：① 创建 `v2cand_*` 影子索引（L8 模式 B）；② 启动 18096
- 授权**不包含**：重启 18094、改 `index_prefix`、写线上索引、改运行态开关

---

## 零、当前基线（2026-11-08 16:27 实测）

```
18094  在线  pid 3189651 / 3202203（2026-11-07 01:20/01:21 启动）
18096  未监听
19527 / 19526  在线
kb_9 = 44      线上索引，**全程不得写入**
v2cand* = 0    影子索引，本段创建
```

---

## 一、影子隔离方案（本段最重要的部分）

| 面 | 影子目标 | 隔离依据 |
|---|---|---|
| ES | `v2cand_kb_9`、`v2cand_table_chunks_kb_9` | `index_writer` 硬约束前缀 `v2cand_`，与 `kb_9` 物理隔离 |
| Milvus | `v2cand_kb_9`、`v2cand_table_chunks_kb_9` | 同上 |
| **图** | **必须显式传 `graph_root`** 指向影子目录 | `IngestRequest.graph_root` 默认 `None` → 会落到 18094 的默认 root = **线上图** |

**⚠️ 图是本段最大的风险点**：`_build_service(graph_root=None)` → `os.environ.get("LLMKE_V2_GRAPH_ROOT")` → 若也为空，则 18094 用自身默认 root。**C 段所有 ingest 请求必须显式带 `graph_root`**，指向影子目录（建议 `services/rag-alg/index_data_service/.shadow-graph/kb_9`）。

**R-0 必须先回答**：`POST /v2/graph/delta` 的 `root` 参数是否被 18094 接受并用于选择快照根；若 18094 忽略该参数（只用自己的 root），则**图无法隔离**，C3 必须停止并回 TL —— 不能为了跑通而去改线上图。

---

## 二、线上保护（每一步都要做）

| 措施 | 执行方式 |
|---|---|
| 不重启 18094 | 全程不 `systemctl`/`kill` 18094；结束时 pid 必须仍是 `3189651 / 3202203` |
| 不改 `index_prefix` | 任何代码/配置不得把前缀改成非 `v2cand_` |
| 线上索引零写入 | 每步前后记录 `kb_9` 的 `_count` 与 `_cat/indices` 的 store size，必须完全不变 |
| 线上图零变更 | ingest 前后对**真实线上图目录**做基线快照，确认未被写入 |

**⚠️ 线上图目录（TL 16:3x 更正，原稿路径错误）**：

```
LLMKE_V2_ROOT=/home/szf/data/dev/llmke-r12/platform/r12/data/graph-root     ← 另一个仓（llmke-r12 运行仓）
  └─ kb_9/current.json  mtime 2026-11-07 21:31
     dir=.../snapshot-20261107212905-365431-g0  fencing=1  documents=46  generation=0
```

原稿写的 `platform/r12/data/graph-root` **在本仓不存在**（说的是 llmke-r12 运行仓）。`.artifacts/api-root` 下**没有 `kb_9/current.json`**（只有个旧 snapshot），**拿它做断言会永远通过 —— 是失败的通过**。基线必须取 `/proc/<18094 pid>/environ` 里的 `LLMKE_V2_ROOT`，不能靠读代码猜默认值。
| 影子可回滚 | 删 `v2cand_*` 索引/collection + 删影子图目录 + 停 18096，三条命令回到现状 |

---

## 三、分步执行（**每步验证通过才进下一步，禁止一把梭**）

### C1 · 建影子索引（可回滚）

```
POST 19527/create_es_index   {"index_name": "v2cand_kb_9"}          + table_chunks
POST 19526/create_milvus_collection ...                             + table_chunks
```

**R-0 须确认**：建 ES 索引是否需要传 mapping body（`es_kb_config.py` 的 `properties` 含 `file_id` 的 `keyword` 子字段）；建 Milvus collection 的维度参数从哪来（embedding dim）。

**验收**：4 个目标（2 ES index + 2 Milvus collection）创建成功；`kb_9` 仍 44 条；`_cat/indices` 的线上条目数不变。

**失败回滚**：`DELETE /del_index` + `drop collection`。

### C2 · 起 18096（可回滚）

```
bash platform/r12/bin/r12-kb-ingest-start.sh        # 内部含六步自检 + 幂等 + 探针
```

**前置**：Java 编译 + `mvn -pl rag-index-service test -Dtest=RemoteV2IngestClassifyTest`，**判据 `Tests run: 7`、failures/errors=0**（不是 `BUILD SUCCESS`）。

**env 必须显式配**：`LLMKE_ES_BASE_URL` / `LLMKE_MILVUS_BASE_URL` / `LLMKE_V2_GRAPH_ROOT`（影子）/ `LLMKE_ARTIFACT_STORE` / `LLMKE_KB_STATE` / `LLMKE_DOC2MD_CONFIG` / `LLMKE_DOC2MD_LOCK`。**禁止设 `LLMKE_ALLOW_DEFAULT_WRITE_TARGET=1`**。

**验收**：`/openapi.json` 可访问且含 `/kb/ingest`；`/health` 返回 200 且 `write_targets.configured=true`、`status="ok"`（若 `degraded` → 停，回去配 env）。

**失败回滚**：杀 18096 进程（用 pid 文件，不碰 18094）。

### C3 · 真实 ingest（写影子，隔离）

```
POST 127.0.0.1:18096/kb/ingest
{"kb":"kb_9","operation":"UPSERT","file_id":"...","doc2md_dir":"...",
 "manifest_path":"...", "graph_root":"<影子图目录>"}
```

**验收（正向）**：
- HTTP 200、`status="OK"`、`state_committed=true`；
- `index_write.applied=true` + `deletes` 含 4 个 target；
- ES/Milvus 的 `v2cand_*` 真有数据（`_count > 0`）；
- **`kb_9` 仍 44 条**、线上图目录未变。

**验收（隔离）**：影子图目录存在且 `current.json` 指向新快照；**18094 默认图目录 mtime 未变**。

### C4 · 幂等 / 撤权 / 删除

- 重复同一请求 → `SKIPPED_FRESH`、`index_write` 零调用、影子数据不重复；
- `operation=DELETE` → `removed` 生效、影子索引该 fid 的块被删、`state_committed=true`；
- 缩水文件重摄取 → 旧块**不再残留**（A2 的 delete 真正生效，端到端验证）。

### C5 · 故障演练（**不停 18094**）

设计包原文要求「停掉 18094 → `GRAPH_UNREACHABLE` + Java 回写 `RETRY`」。**18094 是在线服务，不得停。**

**替代**：把 18096 的 `LLMKE_V2_GRAPH_API` 指向一个**不存在的端口**（如 `127.0.0.1:19999`），重起 18096 → ingest 必须在 delta 阶段失败 → `PARTIAL`、`state_committed=false`、cursor 不推进、错误映射 `GRAPH_UNREACHABLE`(502)。

**验收**：不产生「文件显示解析成功但图没建」；影子索引是否已写需如实记录（这是 L12 顺序语义的真实检验）。

**注意**：此步会写影子索引（因为 apply 在 delta 之前），所以必须在 C3/C4 之后做，且做完把 `LLMKE_V2_GRAPH_API` 改回 18094 重起一次。

---

## 四、每步 evidence 要求

- 每步的**命令原文 + 真实输出**（禁止概括）；
- 每步的**线上基线对比**（`kb_9` count / 线上图 mtime）；
- 18094 pid 前后一致；
- 任一验收不过 → **立即停在该步**，不做下一步，回 TL。

---

## 五、收尾（C 段完成后由 TL 决定）

- **保留**影子索引与影子图（P5 切读要用），还是**清理**？—— 由 TL 按 P5 计划决定，**成员不得自行删除**；
- 18096 保持运行还是停？—— 由 TL 决定。

---

## 六、红线

| 禁止 | 理由 |
|---|---|
| 停/重启 18094 | 在线承载查询 |
| 改 `index_prefix` 指向线上 | 污染线上索引 |
| 向 `kb_9` 写入 | 线上数据 |
| 设 `LLMKE_ALLOW_DEFAULT_WRITE_TARGET=1` | 等于接受配置缺失就写默认 |
| 不带 `graph_root` 就 ingest | 会改线上图 |
| 改设计包 / `MANIFEST.sha256` / `TASKS.yaml` / doc2md | 越界 |
| 一把梭跑完 C1~C5 | 每步必须验证后再进 |
