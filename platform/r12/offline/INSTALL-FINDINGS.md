# R13 离线安装可执行性核查（INSTALL-FINDINGS）

- 角色：ops-offline（运行/交付）
- 日期：2026-10-26
- 对象：`platform/r12/dist/offline/`（23G，images.tar + payload + SHA256SUMS + INSTALL-OFFLINE.md）
- **路径约定**：本报告里凡写 `payload/...`，均指 `platform/r12/dist/offline/payload/...`（**不是** `platform/r12/offline/payload/`，后者不存在）。定位命令：
  `find platform/r12 -maxdepth 4 -name payload -type d` → `platform/r12/dist/offline/payload`；
  `find . -name configs.json -path '*nacos*'` → `./platform/r12/dist/offline/payload/nacos/configs.json`。
- 方法：在 `/tmp/r13-target/r12` 做只读解包模拟（`cp -a payload`，16G），按 `INSTALL-OFFLINE.md` 逐步照做；
  数据库用临时库 `gienrag_ofs_test` 真跑（不碰 `gienrag`），验证后 drop。
- 结论：**当前包按文档装不起来**。阻断级 10 项、中等 6 项、事实登记 3 条；另含 1 项**我自己引入并已修**的缺陷（补 F-03 打包源码会带入含 `0.0.0.0`/构建机路径的 Nacos 本地快照，见 §七末段）；
  已改 3 个脚本 + 新增 2 个脚本（`install-paths.sh`、`check-bind.sh`）+ 1 个模板，但**缺失资产只能靠重新 pack 补齐**（脚本补不了不存在的文件）。
- 另有一节跨角色复核：**§七 监听面暴露**（qa-authz 在撤权验收中发现，离线包会把该暴露面一起搬到目标机；修法待 TL 决策，本角色未擅自改）。

判据说明：本报告区分【事实】（实测/可复查）、【推断】（由事实推出但未在目标机复现）、【判断】（我的取舍建议）。

---

## 一、阻断级：照文档做会直接失败

### F-01 payload 缺 `run/`（`algctl.sh`、`doc-parse.env`）
- 【事实】payload 顶层目录为 `bin conf db docker docs frontend graph jars models nacos preview systemd venvs`，**无 `run/`**。
- 【事实】`bin/up.sh:34` 执行 `bash "$R12/run/algctl.sh" start all` → 文件不存在。
- 【事实】`up.sh:40-42` 读 `$R12/run/doc-parse.env` 后启动 doc-parse → 文件不存在。
- 修：`offline-kit.sh` 的 `pack` 现在拷 `run/algctl.sh`、`run/doc-parse.env`；`verify` 列为必需项（`REQUIRED_FILES`）。

### F-02 payload 缺 `models/start-all.sh` 与 `venvs/models`
- 【事实】`payload/models/` 只有 6 个模型目录（`bge-m3 bge-reranker-v2-m3 gguf gguf-vl llama.cpp ocr_models`），无 `start-all.sh`。
- 【事实】原 `pack` 只按 `MODEL_DIRS` 逐目录拷贝，**根下脚本没有被拷**；`VENV_DIRS=(parse alg graph)` 漏了 `models`（构建机上 `venvs/models` 1.2G 真实存在）。
- 【事实】`models/start-all.sh:12` `VENV="${R12_DIR}/venvs/models"` → 两个缺失叠加，`up.sh` 第 2 步必失败。
- 修：`VENV_DIRS` 增加 `models`；`pack` 拷 `models/start-all.sh`；`verify` 检查两处。

### F-03 payload 缺算法侧源码 `services/rag-alg/*`
- 【事实】Python 算法/解析服务**直接从源码目录运行**，不打 wheel：`run/algctl.sh` 的 `svc_cwd()` 用 `$ROOT/services/rag-alg/...`，`run/doc-parse.env` 的 `PYTHONPATH` 指向 `services/rag-alg/alg_doc_parse_service`。
- 【事实】payload 里**没有 `services/`**。目标机上 `$ROOT` 还会算成 `/`（见 F-17）。
- 修：`pack` 把 `services/rag-alg/{alg_doc_parse_service,index_data_service,alg_retrieval_service,alg_llm_inference_service}` 打到 `payload/src/services/rag-alg/`（约 100M，其中 doc_parse 84M）；`install-paths.sh` 把构建机仓库根改写为 `<prefix>/src`。
- 【判断】不打包 `services/rag-java`（jar 已在 `jars/`，源码仅用于 r12ctl 的 `target/` 路径，用软链兼容即可，见 F-08）。

### F-04 payload 缺 `log4j2/`（6 个 xml）
- 【事实】`bin/r12ctl.sh:43` 传 `-Dlogging.config=$R12_ROOT/log4j2/$name.xml`；payload 无 `log4j2/` → Spring Boot 启动即因日志配置缺失失败。
- 修：`pack` 增加 `log4j2/`；`install-paths.sh` 第 5 段做存在性检查；`verify` 列为必需目录。

### F-05 payload 缺 `.env`，compose 直接报错
- 【事实】实测 `docker compose --env-file /tmp/nonexistent.env -f docker-compose.infra.yml config` →
  `couldn't find env file: /tmp/nonexistent.env`。
- 【事实】`INSTALL-OFFLINE.md` 第 6 步要求 `--env-file /opt/r12/.env`，但包内既无 `.env` 也无模板。
- 修：新增 `platform/r12/offline/templates/env.template`（4 个必填口令占位 + `R12_PREFIX/R12_SRC_ROOT`，不含任何真实口令），`pack` 复制为 `payload/.env.template` 并显式删除误入包的 `.env`；`install-paths.sh` 提示 `cp .env.template .env`；`verify` 检测 `.env` 缺失或仍含 `CHANGE_ME`。

### F-06 payload 缺 `docker/rocketmq/broker.conf`
- 【事实】`docker-compose.infra.yml:186` bind mount `./rocketmq/broker.conf`；`payload/docker/` 只有 compose 文件本身。
- 【推断】`docker compose up` 会把不存在的源建成空目录挂进去，broker 读不到配置 → 起不来或行为异常。
- 修：`pack` 改为整目录拷 `docker/`（含 `rocketmq/`）。

### F-07 payload 缺前端 nginx 配置；`r12-fe` 的真实启动姿势未文档化
- 【事实】`docker inspect r12-fe`：`NetworkMode=host`，两个 bind：`frontend/plateform/nginx/r12-18088.conf → /etc/nginx/conf.d/default.conf`、`frontend/plateform/dist → /usr/share/nginx/html/rag`。
- 【事实】payload 只有 `frontend/dist`，**没有 nginx conf**；`INSTALL` 也没有创建 `r12-fe` 的步骤，但第 8 步自检要求 18088 返回 200。
- 【事实】nginx conf 的 `root /usr/share/nginx/html/rag`（第 14 行）与容器挂载点一致，`index.html` 在 dist 根 → 布局本身匹配，缺的只是配置文件与启动步骤。
- 修：`pack` 打 `frontend/nginx/`（`r12-18088.conf` + `nginx.conf`）；`INSTALL` 增加 `docker run --network host` 步骤。

### F-08 systemd 5 个 unit + `doc-parse.env` 写死 20 处构建机绝对路径
- 【事实】`grep -c /home/szf`：`r12-alg.service 3`、`r12-docparse.service 5`、`r12-graphsvc.service 5`、`r12-java@.service 4`、`r12-models.service 3`，另有 `systemd/doc-parse.env` 与 `run/doc-parse.env`。
- 修：新增 `bin/install-paths.sh`：按前缀幂等改写（`--dry-run` 预演、`--check` 只验残留），并同步补 `logs/ run/ logs/java logs/parse graph/audit`、修 venv 解释器、生成 r12ctl 需要的 jar 兼容布局。
- 【事实】沙箱实测：改写 9 个文件 → 再跑一次输出「无需改写」；`--check` 退出码 0；改写后 `r12-docparse.service` 的 `EnvironmentFile/WorkingDirectory/ExecStart/StandardOutput` 全部落在 `/tmp/r13-target/r12/...`。

### F-09 Nacos 配置**内容**里也有绝对路径（改文件改不到）
- 【事实】`nacos/configs.json` 的 `alg_doc_config_py` 含 `log_path: /home/szf/data/dev/llmke-r12/platform/r12/logs/parse`、`layout_garbage_path: .../layout_garbage`，共 2 处。
- 【事实】这属于**配置中心里的数据**，`systemd/conf` 改写覆盖不到；不改就会让解析服务往不存在的目录写日志。
- 修：`install-paths.sh` 把 `nacos/configs.json` 纳入改写（沙箱实测改写为 `/tmp/r13-target/r12/logs/parse`）；`init-nacos.sh` 发布前做「路径是否存在」检查、发布后回读长度比对。

### F-10 venv 不可重定位
- 【事实】`venvs/parse/bin/python → /home/szf/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11`（绝对路径），`venvs/alg` 同；`venvs/graph/bin/python3 → /usr/bin/python3`（3.10）；`pyvenv.cfg` 的 `home` 也是构建机路径。
- 【判断】目标机若无同路径解释器，四个 venv 全部失效；`INSTALL` 第 4 步推荐的 `python3 -m venv --upgrade` 会改 `pyvenv.cfg` 但不解决 ABI，属误导。
- 修：`install-paths.sh` 第 3 段按 `pyvenv.cfg` 的 `version/version_info` 找同小版本解释器重指软链并改 `home`；找不到则明确告警「请装 python3.X」。
- 【事实】沙箱里三个 venv 判定为「可用（3.11.15 / 3.10.12 / 3.11.15）」，是因为本机恰好有构建机路径——**这条不能当作目标机通过的证据**，只能证明脚本逻辑不误伤。

---

## 二、中等：会误导/浪费，但不一定立刻崩

### F-11 `SHA256SUMS` 校验命令是假校验
- 【事实】清单里路径带 `payload/` 前缀；按 `INSTALL` 第 2 步在 `payload/` 内执行
  `sha256sum -c ../SHA256SUMS --ignore-missing` → 输出 `sha256sum: ../SHA256SUMS: 未验证任何文件`，退出码 1。
- 修：`INSTALL` 改为在 offline 目录执行（生成器已改）；`verify` 第 1 段在 `$OUT` 下校验，实测构建机上「SHA256 全部匹配」。

### F-12 `pack` 非幂等 → payload 自带重复目录
- 【事实】payload 存在 `frontend/dist/dist`（1585 文件、约 130M）、`preview/preview`、`graph/graph`；`SHA256SUMS` 57071 行里含 `payload/frontend/dist/dist/...` 条目。
- 【事实】`frontend/dist/index.html` 与 `frontend/dist/dist/index.html` 是不同 inode 的两份拷贝。
- 修：`pack` 统一走 `put()`（先 `rm -rf` 再 `cp -a`）；`verify` 第 4 段检测嵌套 `dist/`。

### F-13 旧 `verify` 是假绿
- 【事实】在缺 10 项资产的沙箱里跑旧 `verify`：`[ok] 离线校验通过`，退出码 0。
- 【事实】旧 `verify` 的 YAML 检查写死 `/home/szf/...`，且用 `len(files)-len(bad)` 计算——**0 个文件时也打印 6/6 通过**。
- 修：重写 `verify` 为 8 段（清单/镜像/必需文件与目录/jar 与 dist/venv 与模型/.env 与运行目录/配置解析/可移植性），0 文件即失败，并区分「构建机模式（路径残留只提示）」与「目标机模式（残留即失败）」。
- 【事实】新 `verify` 在沙箱（目标机视角）：缺 10 项、`[FAIL] 离线校验失败项: 5`；同一脚本在构建机：30 项齐备、`[ok] 离线校验通过`。两边不互相假绿。

### F-14 `collect_payload`/必需清单漏项
- 【事实】原清单没有 `db`、`nacos`、`bin/init-db.sh`、`bin/init-nacos.sh`、`run/`、`log4j2/`、`src/`；`manifest` 因此看不出缺什么。
- 修：改为 `REQUIRED_FILES`(22) + `REQUIRED_DIRS`(8) 共 30 项，`manifest`/`verify` 共用同一套判定（`have()`，含构建机↔目标机路径别名），`manifest` 实测输出「必需文件齐备（22 项文件 / 8 项目录）」。

### F-15 `init-db.sh` 口令来源与 compose 不一致
- 【事实】compose 用 `${R12_MYSQL_ROOT_PASSWORD}`，原脚本只认 `MYSQL_ROOT_PASSWORD`（且默认写死），也不读 `.env`；口令用 `-p"$PW"` 行内传参（`ps` 可见）。
- 修：读 `.env`（`R12_ENV_FILE` 可覆盖）→ `R12_MYSQL_ROOT_PASSWORD > MYSQL_ROOT_PASSWORD > 内置默认`；改用 `MYSQL_PWD`；支持第 3 参数指定库名（现场改写 dump 标识符，用于沙箱预演）；导入后打印 5 张关键表行数。

### F-16 `init-nacos.sh` 无等待/无回读/无干跑
- 【事实】原脚本 `command -v python3` 硬依赖系统 python3（目标机 venv 里已有 python，没必要）；不等 Nacos 就绪（compose 刚起时容器内还在初始化）；发布成功只信 HTTP `true`，不校验内容是否真落地。
- 修：等待就绪（120s 上限）→ 发布前路径存在性检查 → 发布 → **回读长度比对** → `--dry-run` 只打印不发布。

---

## 三、事实登记（不作为缺陷）

- **F-17 路径推导**：`up.sh`/`r12ctl.sh`/`algctl.sh` 都用 `$R12/../..` 推仓库根。装到 `/opt/r12` 后得到 `/`。
  【判断】本角色不改这三个脚本（不在文件所有权内，且被其他角色共用）；改由 `install-paths.sh` 把构建机仓库根映射为 `<prefix>/src`，并生成 `rag-parent/<svc>/target/*.jar` 软链让 `r12ctl.sh` 不必改代码。**`up.sh` 第 8 步会 `npm run dev`（离线机无 node/源码），属应另行裁剪的逻辑，需 owner 决策。**
- **F-18 logs/run/pid**：`up.sh` 不自建目录；`r12ctl.sh:12`、`algctl.sh:16`、`models/start-all.sh:18` 各自 `mkdir -p`。沙箱实测首次 `up.sh status` 后 `logs/`、`run/` 已被 r12ctl 创建。`install-paths.sh` 现在统一预建（含 `logs/java`、`logs/parse`、`graph/audit`）。
- **F-19 前端产物完整性**：`frontend/dist` 外层 = `index.html` + `config.json` + `assets/996` + `cmaps/font/worker`；nginx `root /usr/share/nginx/html/rag` 与之匹配。冗余在 `dist/dist`（F-12）。

---

## 四、数据库沙箱导入（真跑）

- 【事实】命令：`sed 's/`gienrag`/`gienrag_ofs_test`/g' db/gienrag.sql` → 导入 `r12-mysql` → 统计 → `drop database`。生产库 `gienrag` 全程只读。
- 【事实】dump 自带 `CREATE DATABASE /*!32312 IF NOT EXISTS*/` + `USE`（第 22/24 行），改库名后可直接导入；41 张表全部建成。
- 【事实】行数与生产库逐项一致：

| 表 | 沙箱导入 | 生产库 |
|---|---|---|
| 表数量 | 41 | 41 |
| user_info | 5 | 5 |
| role_info | 3 | 3 |
| search_config | 9 | 9 |
| interface_info | 442 | 442 |
| knowledge_base | 11 | 11 |

- 【事实】改动后的 `init-db.sh` 用同一路径复跑：首次导入 41 表并打印 5 张表行数；二次执行输出「已存在业务表，跳过导入」；验证后 `drop database gienrag_ofs_test`，`information_schema` 复查残留 0。

---

## 五、Nacos 配置覆盖核对

- 【事实】`configs.json` 9 条，与运行中 Nacos（`127.0.0.1:18848`，`totalCount=9`、`pagesAvailable=1`）**dataId 完全一致**，均 `DEFAULT_GROUP`、public 命名空间：
  `alg_doc_config_py(yaml) alg_doc_parse_java_common(text) alg_doc_parse_java_gateway(text) alg_doc_parse_index(text) alg_common_py(yaml) index_data_config_py(yaml) alg_retrieval_config_py(yaml) alg_llm_config_py(yaml) index_graph_config_py(yaml)`
- 【事实】6 个 Java 服务的 `application-r12.yml` 里 `spring.cloud.nacos.config.enabled: false`，**Java 侧不读 dataId**，只用 `discovery`；9 条 dataId 全部由 Python 侧（`nacos_utils.py` / `retrieval_config.py` / `utils.py`）消费 → 缺配置只影响 Python 侧，Java 侧不会因此起不来。
- 【事实】缺失补生成逻辑：原 `pack` 已按分页导出，但 9 条内容里的绝对路径未处理（F-09）；`init-nacos.sh` 现在等就绪 + 路径检查 + 回读校验，`--dry-run` 已实测「将发布 9 条」。
- 注意：**未向运行中的 Nacos 发布任何内容**（沙箱改写过路径，发布会污染现网配置）。

---

## 六、本次改动清单

| 文件 | 动作 | 关键内容 |
|---|---|---|
| `platform/r12/bin/install-paths.sh` | 新增（可执行） | 路径改写（幂等/`--dry-run`/`--check`，集合含 `src/**/nacos-data/snapshot/*`）、运行目录预建、venv 重定位、jar 兼容布局、log4j2/.env 体检 |
| `platform/r12/bin/check-bind.sh` | 新增（可执行） | 只读自检监听面：配置声明（Nacos 内容 + 本地快照 + 源码/启动参数）逐端口对比实际 `ss` 绑定，能识别「静默抵消」「配置自相矛盾」；`--expect-loopback` 供收紧后做验收门 |
| `platform/r12/bin/offline-kit.sh` | 重写 | 必需清单 30 项；`pack` 幂等 `put()` + 补 10 类资产 + `.env.template`（并删误入包的 `.env`）；`verify` 9 段真实校验（含快照路径残留、监听面盘点）；`manifest` 逐项报缺；`smoke` 兼容新布局 |
| `platform/r12/bin/init-db.sh` | 重写 | 读 `.env`、`R12_MYSQL_ROOT_PASSWORD` 优先、`MYSQL_PWD`、库名参数、行数证据、表数下限断言 |
| `platform/r12/bin/init-nacos.sh` | 重写 | 等待就绪、路径存在性检查、发布后回读长度校验、`--dry-run`、`R12_NACOS_ADDR` |
| `platform/r12/offline/templates/env.template` | 新增 | 4 项口令占位 + 2 项前缀，无真实口令 |
| `platform/r12/offline/INSTALL-FINDINGS.md` | 新增 | 本文件 |

未改：`services/**`、`frontend/**`、`docs/**`、`platform/r12/conf/**`、`dist/offline/**`（包只读）；未动任何容器，未跑 `qa/acceptance.py`。

【事实】语法检查：4 个脚本 `bash -n` 全通过（环境无 shellcheck）。

---

## 七、监听面暴露（qa-authz 在撤权验收中发现，本节为离线安装侧复核）

- 证据来源：**终版 `platform/r12/qa/evidence/REVOKE-20261026T160008Z/{summary.md,detail.json}`（21/21 PASS，exit=0，本轮定版）**；过程轮次 `151323Z → 151614Z → 152955Z → 155033Z → 155653Z` 结论一致（`152955Z` 起 17/21，`155033Z` 起转 21/21）。终版 summary 已内置「## 修复归属清单」与本节的修法口径逐条一致。Java 侧收口本身有效（R8-R14 全部 403/30016），问题只在**直连内部服务绕过网关**（R15/R16/R18 已在终版转 PASS）。
- 【限定】`12340/19526/19527` 属写入面（解析任务提交、向量/全文索引写入），qa-authz 只做了**端口绑定盘点、未发任何写入请求**（避免向真实库写入副作用）；本节引用时保留该限定，不得据此推断这些写口已实测可写。
- 【事实】`ss -ltnp` 实测本机绑定情况（2026-10-26），与 qa-authz R17 的 7 个端口枚举一致：
  - `0.0.0.0`：`12340`(doc-parse，写入面)、`19526`(vector，写入面)、`19527`(全文，写入面)、`19529`(graph，读)、`19995`(retrieval，读)、`19996`(llm，推理)、`18095`(preview，读)；另有 `18088`(nginx)、`8088`(gateway) 属用户入口，绑 `0.0.0.0` 为预期。
  - `127.0.0.1`：`18090/18091/18092/18093`(模型)、`18084`(Java graph-svc) —— 说明"只绑回环"在本环境是可行的，有先例。
- 【事实】根因分三类，**修法完全不同**：
  1. **Nacos 配置内容**（6 个端口，6 处键位）：所有 Python 服务都 `uvicorn.run(host=server_config["server"]["host"])`（`retrieval_api_start.py:45`、`llm_api_start.py:44`、`vector_milvus_api_start.py:64`、`fulltext_es_api_start.py:50`、`graph_api_start.py:99`），host 来自配置中心：

     | dataId | 行 | 服务 | 端口 |
     |---|---|---|---|
     | `alg_doc_config_py` | L3 | doc-parse | 12340 |
     | `index_data_config_py` | L7 | index_vector | 19526 |
     | `index_data_config_py` | L37 | index_fulltext | 19527 |
     | `alg_retrieval_config_py` | L7 | alg_retrieval | 19995 |
     | `alg_llm_config_py` | L6 | llm_open_chat | 19996 |
     | `index_graph_config_py` | L4 | index_graph | 19529 |

     → **改配置文件没用，要改 Nacos 里的配置内容**（这也意味着"改代码"同样无效）。
  2. **代码硬编码 + 容器 host 网络**（18095）：核查时 `platform/r12/preview/app.py:399` 写死 `host="0.0.0.0"`，`preview/run.sh:31` 用 `--network host`（实测 `grep -n 'network host' platform/r12/preview/run.sh` → `31:`；本节早期写作 `:32` 系笔误，已更正）。
     **现场已变化（2026-10-26 23:25 后，他人实施）**：`app.py:401` 改为 `host=os.getenv("PREVIEW_HOST","127.0.0.1")`，`run.sh:32` 增加 `-e PREVIEW_HOST="${PREVIEW_HOST:-127.0.0.1}"`，`systemd/r12-graphsvc.service:14` 改为 `--host 127.0.0.1`。但 **两处"源码已改、运行态未生效"**：
     - `18095`：容器仍跑旧代码（`ss` 实测 `0.0.0.0`；进程命令行 `python -m uvicorn app:app --host 0.0.0.0 --port 18095`）→ 需重建/重启容器。
     - `19529`：`systemctl --user show r12-graphsvc -p ExecStart` 仍显示 `--host 0.0.0.0`（**改的是 unit 文件，没做 `daemon-reload`**），且该 unit `Restart=always`，所以进程被 TERM 后又以旧参数起回来——`is-active` 采样到 `deactivating`、`ss` 采样到 `0.0.0.0`，表现为**抖动**。单次采样会误判为"未运行"，故 `check-bind.sh` 增加 `--samples N`（默认 1，取并集），`--samples 5` 可稳定抓到它。
     - `payload/nacos/configs.json` 6 处仍是 `0.0.0.0`（配置类未动）。
     `check-bind.sh` 对本状态给出 `静默抵消：配置已收紧但实际外露`（18095）与 `配置自相矛盾（来源间取值不一致）`（19529：`0.0.0.0@payload` vs `127.0.0.1@systemd`）。
     **运行态继续演进（23:40+ 采样，`--samples 3`）**：`12340/19526/19527/19995/19996` 已实际改为只绑 `127.0.0.1`（判定 `已收紧但配置未同步`——即运行态比包内配置更严）；`18095` 容器在 `restarting`；`19529` 仍 `0.0.0.0`（unit 未 reload）。此刻真实外露面只剩 1 个端口（19529）。
     由此得到一条对交付的直接结论：**运行态已收紧、但 `payload/nacos/configs.json` 仍是 6 处 `0.0.0.0`** —— 若按现状重打离线包，目标机会把这些端口重新放开。重打前必须把包内配置同步为运行态生效值，否则"本机修好了、装机又退回去"。
- 【采样纪律】qa-authz 的 7 端口结论带时刻（`REVOKE-20261026T152955Z`，UTC），引用时必须带时刻、不可当作当前态；本节所有运行态数字同样只是采样时刻快照，服务在重启抖动时请用 `--samples N` 取并集。
- 【事故复盘·18095 曾 crash-loop，且"改对了也无效"】三段时间线（均为现场实测，非推断）：
  1. **坏在缩进**：有人把 `uvicorn.run(...)` 顶到第 0 列（脱离 `if __name__ == "__main__":`），而 `import uvicorn` 是该块内的局部导入 → 容器 `NameError: name 'uvicorn' is not defined`，`Status=restarting / ExitCode=1 / RestartCount=11`。**`py_compile` / `compileall` 对这份文件是通过的**（列 0 语法合法），任何"语法检查"类门禁都抓不到，只有真起进程才暴露。
  2. **修了也不生效**：源码已改回块内、`host=os.getenv("PREVIEW_HOST","127.0.0.1")`，`run.sh` 也传了 `-e PREVIEW_HOST=127.0.0.1`（`docker inspect` 里能看到该 env），**但 18095 仍绑 `0.0.0.0`**。根因：容器 PID1 是 `python -m uvicorn app:app --host 0.0.0.0 --port 18095 --no-access-log`，来自 **`preview/Dockerfile:52` 的 CMD 硬编码 `--host 0.0.0.0`**；以模块方式启动时 `app.py` 的 `__main__` 整块**根本不执行**，`PREVIEW_HOST` 与 app.py 的默认值都被 CMD 覆盖。→ 必须改 Dockerfile CMD（或 override entrypoint/command）并重建镜像，改 app.py/传环境变量都无用。
  3. **包内第三方状态**：`payload/preview/app.py` 缩进正常但仍写死 `host="0.0.0.0"`；`payload/preview/Dockerfile:52` 同样是 `--host 0.0.0.0`。即"源码已修 / 镜像CMD 未修 / 包内副本未修"三者并存，**重打前必须同时修这三处**。
  对应加固：`offline-kit verify` 新增 **4.1 preview 启动结构**检查（检测 `uvicorn.run` 落在第 0 列但 `import uvicorn` 在块内 → 报 NameError 风险；变异测试：合成坏样本命中、当前源码不命中）；`check-bind.sh` 新增 **镜像CMD** 来源解析（现可显示 `0.0.0.0@镜像CMD` 与 `127.0.0.1@源码/启动参数` 并存 → 判 `配置自相矛盾`）。
- 【仍待决策·包内待同步项，**分档**说明】离线包未跟随运行态更新，按现状重打会把外露面带回去。**必须区分"现有磁盘包"与"重打后"**，否则按现包核对会找不到快照文件：
  - **现状（未重打的磁盘包）：2 处**
    1. **配置侧**：`payload/nacos/configs.json` 6 处 `server.host: 0.0.0.0`（`alg_doc_config_py` L3→12340、`index_data_config_py` L7→19526 与 L37→19527、`alg_retrieval_config_py` L7→19995、`alg_llm_config_py` L6→19996、`index_graph_config_py` L4→19529）。实测 `grep -o '0[.]0[.]0[.]0' | wc -l` = 6。
    2. **镜像 CMD 侧（唯一真正生效点）**：`payload/preview/Dockerfile:52` 的 `CMD ["python","-m","uvicorn","app:app","--host","0.0.0.0", ...]`；连带 `payload/preview/app.py:399` 的 `host="0.0.0.0"` 与 `run.sh` 的 `--network host`（三者要一致，但**生效的是 CMD**）。
  - **重打后：3 处（新增第 3 处）**
    3. **快照回退侧**：`payload/src/services/rag-alg/**/nacos-data/snapshot/*` 约 7 份带 `host: 0.0.0.0` —— 配置中心不可达时会被回读，只改 ① 等于没改（仅 doc-parse 关了 `no_snapshot`）。**当前包里没有 `payload/src/`**（实测 `ls payload/` 无 `src`，`find ... -path '*nacos-data/snapshot*' | wc -l` = 0），这 7 份是 **F-03 修复（把 `services/rag-alg` 纳入包）后才会随包出现**的引入项，不是现存残留。故重打前后都要跑 `verify` 第 9 段核对（它会按现包实况报 2 处、重打后报 3 处）。
  → TL 的 A/B 决策点：**A**=重打时按运行态生效值同步（当前均为 `127.0.0.1`，由 `init-nacos.sh` 显式开关控制，默认关闭）；**B**=保持包内现值、装机后人工收紧并跑 `check-bind --expect-loopback` 验收。**运行态已给出事实依据，A 更安全**。
- 【安全前提·必须写进安装验收】"只绑回环"是**信任边界**，不是"不可读"：qa-authz 实测回环内仍可无凭据读取（`127.0.0.1:19995/retrieval_documents` 返回 documents=1、`127.0.0.1:18095/stream` 返回 100329 字节 PDF）。这些内部服务**本身不做鉴权**，唯一收口在 Java 网关/控制器。因此安装验收必须声明两个前提：
  1. **单租户主机**：同机若有其他用户/租户进程，回环边界等于不设防（同机任意进程可读原文）；
  2. **仅本机调用**：这些端口只允许本机 Java 服务/nginx 访问；跨机需求必须加凭据或网络隔离。
  若目标机不满足，需在装机前追加内网凭据或按租户隔离（超出本包能力，须另行立项）。
- 【运行态收口基线·回归用】终版证据 `REVOKE-20261026T160008Z`（21/21 PASS，exit=0）；本侧复核 `check-bind.sh --samples 3 --expect-loopback` **退出码 0**，7 个内部端口全部只绑 `127.0.0.1`，18095 判定由 `配置自相矛盾` 转为 `一致`；源码 `preview/Dockerfile:54` 已为 `--host ${PREVIEW_HOST:-127.0.0.1}` 且镜像已重建。**这条基线只代表运行态，不代表包内**（见上一条“分档”说明：现包 2 处、重打后 3 处）。
 - 【易踩的第二个错觉】「改端口映射 `127.0.0.1:18095:18095`」在本拓扑下**不成立**：`docker inspect r12-preview` 为 `PortBindings={}`、`NetworkMode=host`，没有映射可改；改桥接会让容器内 `MINIO_ENDPOINT=127.0.0.1:19000` 失效（这大概正是当初选 host 网络的原因）。（该建议 qa-authz 已自行撤回，双方复核结论一致。）
- 【事实】Java 侧"唯一收口"注释的前提已失效：`rag-index-service/.../interfaces/KnowledgeBaseFileController.java:442` 写「预览服务在 127.0.0.1:18095 内部端口不做鉴权，这里是唯一收口点」，`:55` 的默认 URL 也是 `127.0.0.1:18095`，但实际监听是 `0.0.0.0` —— 只要绕过网关直连就能拿到原文（R16/R18 已实证 100329 字节 PDF）。
- 【事实·对离线包的影响】**离线包会把 7 个端口的暴露面一起搬到目标机**，拆开是两条来源，都要改才有效：
  1. 配置侧 6 处：`payload/nacos/configs.json`（= `platform/r12/dist/offline/payload/nacos/configs.json`）由现网 Nacos 导出，`grep -o '0.0.0.0' | wc -l` = **6**（`grep -c` 只数到 5 行，因为 `index_data_config_py` 的 L7/L37 在 JSON 的同一行内容里，别被行数误导）。
  2. 源码硬编码 1 处：`payload/preview/app.py:399`（`host="0.0.0.0"` 写死）+ `payload/preview/run.sh:31`（`--network host`，无端口映射可限）。
  → 已实现在 `offline-kit.sh verify` 第 9 段做**提示性盘点**（不计失败，避免构建机上正常绑 0.0.0.0 被误判为红），当前输出 6 行 dataId→端口映射 + 一行 app.py/systemd 提示。
- 【事实·加固空转点，重要】**只改配置中心会被本地快照静默抵消**。python-nacos 的 `SNAPSHOT_BASE` 默认是**相对路径** `nacos-data/snapshot`（`site-packages/nacos/client.py:65`），按服务 CWD 解析，正好命中源码树里这些文件：
  `get_config()` 在拉取失败时回读快照（`client.py:511-517`）；`no_snapshot` 默认 `False`（`client.py:342`），**只有 `alg_doc_parse_service/server/nacos_utils.py:39,61` 传了 `no_snapshot=True`**。
  → 即 `alg_retrieval(19995)`、`alg_llm(19996)`、`index_vector(19526)`、`index_fulltext(19527)`、`index_graph(19529)` 在配置中心不可达时会按快照启动。实测源码树 7 份快照含 `host: 0.0.0.0`，其中 `alg_doc_parse_service/nacos-data/snapshot/alg_doc_config_py+DEFAULT_GROUP+` 还含 2 处构建机路径。
- 【事实·我自己引入的缺陷，已修】按 F-03 把 `services/rag-alg` 打进包，会把这 7 份快照一并带进 `payload/src/` —— 等于让离线包多出 7 份 `0.0.0.0` 与 2 处构建机路径，**而且看起来像"已经修过配置中心"**。已修：`install-paths.sh` 的改写集合纳入 `src/**/nacos-data/snapshot/*`（沙箱实测把快照里 2 处 `/home/szf` 改成目标前缀、`--check` 残留 0，且**不擅自改 `host:`**）；`verify` 第 8 段增加快照路径残留检查、第 9 段增加快照 `0.0.0.0` 提示条数。
- 【判断】本角色**不擅自改绑定**：`getenv` 默认值、Nacos 配置内容、`preview/app.py`、`systemd/*.service`、`docker-compose` 均不在我的文件所有权内，且 qa-authz 已明确这需要 TL 决策。若 TL 决定收紧，改动点就是上面三类，我可以按决策补进 pack/install 流程（例如 pack 时把内部数据面 dataId 的 `server.host` 落成 `127.0.0.1`，并在 `init-nacos.sh` 增加显式开关，默认关闭）。
- 【交付·加固验收判据】新增只读工具 `bin/check-bind.sh`，专门回答"收紧之后到底生效没有"：
  `check-bind.sh [--prefix <前缀>] [--expect-loopback]` —— 把每个端口的**声明值**（Nacos 内容 / 本地快照 / 源码与启动参数）与**实际 `ss` 绑定**并排列出，判定为 `一致`/`一致（仍外露）`/`静默抵消`/`配置自相矛盾`/`未运行`。
  当前本机实测 7 行全为「一致（仍外露）」；`--expect-loopback` 退出码 1（未收紧）。变异复验：把沙箱 `configs.json` 的 `host` 改成 `127.0.0.1` 但保留快照 `0.0.0.0` → 工具报 `配置自相矛盾（部分来源仍 0.0.0.0，如快照未同步）`，正是"看起来修好了"的那种假绿。**收紧决策落地后，用它做验收门，不要只看配置文件。**
- 附带提示：目标机若按本报告的清单执行，第 5 步发布会把 6 处 `0.0.0.0` 一起写进配置中心；**在 TL 决策前，目标机应同时具备网络层隔离**（安全组/防火墙只放 8088/18088）。

---

## 八、目标机执行清单（命令级）

```bash
# 0) 落盘（示例前缀 /opt/r12）
mkdir -p /opt/r12 && cp -a payload/. /opt/r12/
chmod +x /opt/r12/bin/*.sh /opt/r12/run/*.sh /opt/r12/models/*.sh

# 1) 导入镜像
docker load -i images.tar

# 2) 完整性（必须在 offline 目录，不能在 payload 内）
cd <offline 目录> && sha256sum -c SHA256SUMS --ignore-missing

# 3) 口令（不填则第 6 步 compose 直接失败）
cp /opt/r12/.env.template /opt/r12/.env
vi /opt/r12/.env && chmod 600 /opt/r12/.env     # 改 4 项 CHANGE_ME

# 4) 路径适配（先预演，再落地，最后验残留）
/opt/r12/bin/install-paths.sh --prefix /opt/r12 --dry-run
/opt/r12/bin/install-paths.sh --prefix /opt/r12
/opt/r12/bin/install-paths.sh --prefix /opt/r12 --check      # 期望退出码 0

# 5) 数据库与配置中心
/opt/r12/bin/init-db.sh /opt/r12/db/gienrag.sql
/opt/r12/bin/init-nacos.sh /opt/r12/nacos/configs.json --dry-run
/opt/r12/bin/init-nacos.sh /opt/r12/nacos/configs.json

# 6) 基础设施
cd /opt/r12/docker && docker compose -f docker-compose.infra.yml --env-file /opt/r12/.env up -d

# 7) 业务与算法（Python 源码须已随包到 /opt/r12/src/services/rag-alg）
/opt/r12/bin/up.sh up

# 8) 前端（host 网络，nginx 直接听 18088）
docker run -d --name r12-fe --network host --restart unless-stopped \
  -v /opt/r12/frontend/dist:/usr/share/nginx/html/rag:ro \
  -v /opt/r12/frontend/nginx/r12-18088.conf:/etc/nginx/conf.d/default.conf:ro \
  nginx:alpine

# 9) 自检
/opt/r12/bin/up.sh verify
/opt/r12/bin/offline-kit.sh verify

# 10) 监听面自检（只读；收紧决策落地后加 --expect-loopback 当验收门）
/opt/r12/bin/check-bind.sh --prefix /opt/r12
/opt/r12/bin/check-bind.sh --prefix /opt/r12 --expect-loopback   # 收紧后要求退出码 0
```

**仍必须人工处理（脚本无法替代）**
1. **重新 pack**：当前包缺 F-01/02/03/04/06/07 的 10 类资产与 `.env.template`。`install-paths.sh` 只能补目录/软链，补不了不存在的文件。改好的 `pack` 已就绪，重跑一遍即可（须核对新的 `SHA256SUMS`）。
2. 填写 `.env` 4 项口令，并与 compose 的 `${R12_*}` 保持一致。
3. 目标机 Python：需 `3.11.x`（parse/alg/models）与 `3.10.x`（graph）两套，与包内 `pyvenv.cfg` 同小版本；否则 site-packages ABI 不兼容。
4. 端口占用：18088/8088/18095/19200/19630/19669/18848/15174 及 12340/19526/19527/19529/19995/19996；`r12-fe` 是 host 网络，冲突会直接占失败。
5. Docker ≥ 20.10 且带 compose v2 插件；磁盘 ≥ 30G（包 23G + 解包后容器卷）。
6. `systemd --user` 是否启用（不启用则只能手工 `up.sh up`，进程不随系统重启恢复）。
7. `up.sh` 第 8 步的 `npm run dev` 在离线机必然失败（静默），建议由 owner 决策裁剪该分支。
