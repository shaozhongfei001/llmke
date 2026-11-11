# P5-L14 PLAN（Java 派发切换）· R-0 只读核实

> 任务：`T-D2MD-14`（`TASKS.yaml` owner 名义为 `backend-engineer`；本轮由 `python-engineer` 执行 **R-0 只读核实**，实现阶段再由 Owner 决定执行者）
> 上游：`T-D2MD-13`（P4 已完成代码面）
> 依据：`docs/design/doc2md-incremental-graphrag/03-IMPLEMENTATION.md:354-383`（P5-1/P5-2/P5-3）

---

## 一、R-0 的唯一目标

**在写任何 Java 代码之前，把「改哪份文件、编译哪份、怎么验证」这三件事钉死。**

不是走流程。P4 已经用血证明了代价：`L13-B` 的 6 项产物全在源码侧，部署侧一项没有；`_is_own_root` 统一没被运行中的 18094 加载。**Java 侧副本更多，同样的坑更深。**

---

## 二、TL 已预核的事实（R-0 需确认或推翻）

```
FileAppServiceImpl.java 存在 **三份**：
  A  llmke-v2/services/rag-java/rag-parent/rag-index-service/src/main/java/.../FileAppServiceImpl.java
  B  llmke-r12/services/rag-java/rag-parent/rag-index-service/src/main/java/.../FileAppServiceImpl.java
  C  llmke-r12/platform/r12/dist/offline/payload/src-build/services/rag-java/.../FileAppServiceImpl.java

RemoteV2IngestUtils.java  只有 A 一份（B 不存在）        ← 需解释
v2-ingest 配置            llmke-v2 有（application-r12.yml:108），llmke-r12 **无该键**  ← 需解释
mvn  /usr/bin/mvn ；java 21.0.11                         ← 可用
```

---

## 三、R-0 必须回答的问题（逐条给证据，不许「大概」）

### R-0-1 Java 源码的「真值」是哪一份

1. A/B/C 三份的 md5 与行数；
2. **运行中的 rag-index-service 加载的是哪份编译产物**（jar 路径、jar 内 class 的 mtime）；
3. 构建流程是「源码仓 mvn package → 部署 jar 到 llmke-r12」还是「部署侧直接构建」——**给出证据**（jenkinsfile/Makefile/脚本/文档任一）；
4. C（`dist/offline/payload/src-build`）是什么用途，会不会被误当成真值改；
5. **结论必须是一句话**：「本 loop 应该改 A，因为 ……」。

### R-0-2 `FileAppServiceImpl` 四个方法的现状

对 `filesParse`、`filesParseSync`/`doParse`、`v2Ingest`、`generateGraph` 逐个给：

- 方法签名（行号）；
- **当前调用哪个下游**（URL 从哪个配置键来）；
- 返回值怎么处理（是否读 body `code`）；
- 失败怎么回写（状态机改了哪个字段、有没有回写 `PARSE_FAIL`）；
- `generateGraph` 的 **19531 路径**具体是什么（调用点、参数、返回判断）。

### R-0-3 `RemoteV2IngestUtils` 现状

- 是否有超时设置（连接/读）；
- 返回类型是什么（`String`? DTO?）；有无 `IngestResult`；
- **是否按 HTTP 状态码判断失败**、**是否读 body `code`**；
- 与 L13 已验证结论「HTTP 码决定是否抛、body `code` 决定 207 vs 200」的差距在哪。

> 这一条是 P5 的核心。L13 的 C 段已实测出：Python 侧 207 是 `PARTIAL`、200 是 `OK`、502 是硬失败。**Java 侧若不读 body `code`，会把 207 当成成功或失败，两者都错。**

### R-0-4 `FileParseTaskAppServiceImpl.doSuccess` 现状

- `:310-363` 具体做了什么；
- 是否**无条件触发建图**（这是 P5-1 要删的）；
- 若删除建图触发，状态机是否还完整（谁写 `graph_parse_status`）。

### R-0-5 配置键现状（两仓逐键对比）

`03-IMPLEMENTATION.md:369-373` 列的键，逐个给两仓现状（存在/值/指向）：

```
remote.file-parse.url / file-parse-sync.url / file-revise_date.url
remote.file-multi-version.url / tl-database-table-description.url
remote.generate-graph.url / generate-community.url / del-graph-space.url / del-graph-entity.url
remote.v2-ingest.url
```

**特别确认**：`v2-ingest` 在部署仓**是否真的没有**——若没有，Java 侧读不到这个键会不会启动即失败，或走默认值？

### R-0-6 mvn 基线与测试环境

- `mvn -o -pl rag-index-service test` 能否跑通（**允许跑一次只读基线**，但不许改代码）；
- 当前 `Tests run` 数字、`failures`/`errors`（TL 记的判据是「Tests run 7 且 failures errors 为 0」——**核实这个数字是否仍准确**）；
- 若离线依赖不全（`-o` 失败），说明需要联网还是本地仓库已有。

### R-0-7 12340 的调用面（P5-3 的前置情报）

- 当前有哪些 Java 代码调 `12340`（`RemoteFileUtils` 的哪些方法）；
- 「多版本解析 / revise_date / 按 documentId 取 chunk」三类辅助接口，**各自被谁调用**（给调用点）。

> 不是本 loop 要改，但 R-0 不查清，P5-3 会返工。

---

## 四、红线（R-0 阶段）

**允许**：
- 读任意源码/配置/日志；
- 跑一次 `mvn -o ... test` 只读基线（不改代码）；
- 在 `/tmp` 下写临时分析脚本。

**禁止**：
- 改任何 `.java` / `.yml` / 脚本；
- `mvn package` / `install` / 部署 jar；
- 重启任何 Java 服务（`rag-index-service` 正在跑）；
- 改 `TASKS.yaml`（由 TL 改）；
- **开始实现**（R-0 只交报告与裁定请求）。

---

## 五、交付物

`docs/v2-tasks/evidence/P5-L14-<ts>.log`，结构：

```
§0 结论摘要（不超过 10 行，先给判断）
§1 ~ §7 对应 R-0-1 ~ R-0-7，每条：命令 + 原始输出 + 结论
§8 需要 TL 裁定的问题（编号 Q1..Qn，每条给建议方案与理由）
§9 红线自查（改了哪些文件：应为 0；跑了哪些命令）
```

**报告纪律**：
- 「我没查」比「大概是」有价值 —— 查不到就写「查不到，可能原因 X/Y，建议 TL 定」；
- 任何结论必须能指到「哪一行/哪条命令输出」；
- 若发现 PLAN 的前提有错（很可能，P4 每轮都有），**直接说**，不要迁就 PLAN。

---

## 五·二、R-0/R-0b 结论（已裁定，替代 §三 的待查项）

### 关键事实

```
jar 内 RemoteV2IngestUtils.class = 0；FileAppServiceImpl 无 v2Ingest
⇒ 线上**根本没有 v2-ingest 功能** —— P5 是「从零启用」不是「切换」

部署仓源码落后：rag-index(10-29) / rag-common / rag-qa / rag-graph(2026-01-21) / rag-gateway(10-26)
jar 时间离散（11-07 02:57 / 11-07 20:57 / 10-28 23:51）⇒ 按需手工 package，从未全量重建

源码 classify 已正确：classify(httpStatus, code) → 200+200=OK / 200+207=RETRY / 4xx=PARSE_FAIL / 5xx=RETRY
remote.file-revise_date.url 是本模块内死配置（零调用点，已排除反射/继承）
```

### 执行顺序（TL 裁定，P5-0 需 Owner 批）

```
P5-0  部署仓源码同步（5 模块 A→B）+ 全量重建        ← 新增前置，运行态变更
P5-1  Java 派发切换（改 A、加二选一开关、v2Ingest 写 graph_parse_status）
P5-2  两仓配置同步（v2-ingest.url 保持 ""）
P5-3  启用 v2-ingest + 12340 退役
```

**P5-0 的理由**：原计划假设「改 A 再构建就上线」，前提不成立 —— 部署仓源码是旧的，构建出来仍是旧代码。

---

## 五·三、Java 侧「改动是否生效」验收判据（**强制**，对应 Python 的 pyc 扫描）

三个条件**同时成立**才算生效。缺任一条，都可能出现「源码改了 / 单测绿了 / jar 构建了，线上仍是旧行为」。

### (1) 类是否在 jar 内

```bash
JAR=services/rag-java/rag-parent/<module>/target/<module>-0.0.1-SNAPSHOT.jar
unzip -l "$JAR" | grep -c "<ClassName>.class"      # 期望 ≥1；0 = 本次改动不在运行代码里
```

> **坑**：Spring Boot fat jar 里是 `BOOT-INF/classes/...`，用 `<ClassName>.class` 匹配而非全路径，避免路径前缀写错导致**假 0**。

### (2) 方法签名是否在 class 里

```bash
javap -p -classpath "$JAR" com.gientech.<pkg>.<Class> | grep -n "v2Ingest\|graphParseStatus"
```

> 比「类存在」更强：防「类在但方法是旧的」。
> `javap` 读 fat jar 失败时退化：
> ```bash
> unzip -p "$JAR" BOOT-INF/classes/<pkg>/<Class>.class > /tmp/X.class && javap -p /tmp/X.class
> ```

### (3) 运行进程确实用这个 jar

```bash
PID=$(ss -tlnpH | grep ':<port>\b' | grep -o 'pid=[0-9]*' | cut -d= -f2 | head -1)
tr '\0' '\n' < /proc/$PID/cmdline | grep '\.jar'
ps -o lstart= -p $PID      # 进程启动时间必须**晚于** jar 的 mtime
```

> 防「jar 新、进程还挂在旧 class 上」。**等价于 Python 侧的「代码改了但没重启」**。

### 合并判据（写进每份 Java 报告首段）

> **jar 内 class 存在 + 方法签名存在 + 进程启动晚于 jar mtime** —— 三者同时成立才算「Java 改动生效」。

---

## 五·四、P5-1 的两个**必踩坑**（前置条件，不写进 PLAN 一定会重演）

### 坑 1：A 先改，`diff A B` 为空，再构建

```
A = llmke-v2/services/rag-java/rag-parent/...   ← 唯一可信源
B = llmke-r12/services/rag-java/rag-parent/...  ← 构建源（mvn 在这跑）

规则：改 A → `diff A B` 该文件为空 → 在 B 构建 → 部署 → 重启
禁止：直接改 B（会在下次 A→B 同步时被静默覆盖）
```

**实证**：P5-0b 的 `@Lazy` 起初只落在 B，A 没有；若不修正，下次同步会让 18084 重新起不来，而且「同步」看起来是无害操作。

**P5-1 涉及两个文件，两个都要遵守**：
- `FileAppServiceImpl.java`（`filesParse` / `filesParseSync` / `v2Ingest` / `generateGraph`）
- `rag-common/.../FeignErrorDecode.java`（与原计划的 `FileParseTaskInfo` 同批）

### 坑 2：`v2Ingest` 上线必须**同时写 `graph_parse_status`**

Q8 裁定方案（由「知道结果的一方」写）：

| 事件 | 值 |
|---|---|
| 触发建图 | 2 PARSE_ING（现有触发点不变） |
| `outcome=OK` | **3 PARSE_SUCCESS** |
| **`outcome=RETRY`（207/5xx/连不上）** | **保持 2**（不落 4，否则前端显示失败并停自动重试） |
| `outcome=PARSE_FAIL`(4xx) | 4 PARSE_FAIL |

**现状**：`v2Ingest` **不写任何值**，`generateGraph` 写 3/4、`doFail` 写 4、触发点写 2。

**若只切调用不补写** → 切过去后该字段**永远停在「未做(1)」**，前端显示卡死，且没人会立刻想到是这里。

**冲突必须同批解决**：legacy `generateGraph` 与 `v2Ingest` 同时跑会「先 3 后 4」或反之，终值取决于完成顺序。**删 legacy 必须与「二选一开关」同批**，禁止两条路径同时写同一字段。

**`RETRY` 保持 2 必须有独立用例** —— 它是「前端不误判」的唯一保障，不能只靠代码读起来对。

---

## 六、预期裁定点（TL 预判，供 R-0 参考）

1. **改哪一份 Java 源码**（A/B/C 三选一，或「改 A + 同步到 B」）；
2. **`RemoteV2IngestUtils` 是否新建 `IngestResult` DTO**，还是在现有返回上扩展；
3. **207 的语义在 Java 侧怎么落**：`PARTIAL` 是否等同失败、是否触发 `RETRY`；
4. **`v2-ingest` 部署仓缺键**如何处理（补键 vs 代码默认值）；
5. **回退窗口**：P5-3 下线 12340 后不可回退，P4/P5 之间是否保留旧链路开关。
