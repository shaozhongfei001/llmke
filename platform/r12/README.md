# R12 部署与运行手册（真实 RAG 主链）

本目录是 R12 的**运行面**：基础设施编排、配置、启停脚本、种子数据、验收脚本、日志与运行态。
源码在仓库其它位置：`services/rag-java`（业务）、`services/rag-alg`（算法）、`frontend/plateform`（前端）。

## 1. 版本与依赖（实测）

| 组件 | 版本 | 说明 |
|---|---|---|
| OS | Ubuntu 22.04 | 本机为 x86_64，20 核 / 62GB / RTX 3060 6GB |
| JDK | OpenJDK 21.0.11 | 源码 target=17，运行 21 |
| Maven | 3.6.3 + 镜像 settings | 见 `platform/r12/maven/settings-r12.xml`（`mirrorOf=*` → 阿里云） |
| Node | v25.0.0 / npm 11.6.2 | 前端构建；安装用腾讯 npm 镜像 |
| Python | 3.11（独立 venv） | 算法 `venvs/alg`、解析 `venvs/parse`、模型 `venvs/models` |
| MySQL | 8.4（容器） | 库 `gienrag` |
| Redis | 7.4（容器） | 需口令 |
| Elasticsearch | 8.13.4（容器） + analysis-ik 8.13.4 | 中文分词插件 |
| Milvus | 2.5.6（容器，etcd+minio 后端） | database `rag_knowledge_base` |
| MinIO | RELEASE.2023-03-20（容器） | bucket `r12-rag` |
| Nacos | 2.3.2（容器） | 仅服务发现 + Python 配置 |
| RocketMQ | 4.9.7（容器，namesrv+broker） | 解析任务队列 |
| 模型服务 | bge-m3 / bge-reranker-v2-m3 / Qwen2.5-7B-Instruct / Qwen2.5-VL-3B | 独立进程，OpenAI 兼容 |

## 2. 目录约定

```
platform/r12/
  .env                 # 运行期口令（**不入库**，由密管/手工创建）
  .env.example         # 变量清单
  docker/              # docker-compose.infra.yml + rocketmq/broker.conf
  conf/<svc>/          # Java 服务外置 application-r12.yml（优先级高于 jar 内）
  nacos/               # Python 侧 Nacos data_id 权威内容 + publish.py
  maven/settings-r12.xml
  seed/                # 权限/账号、模型登记（幂等）
  models/              # 模型权重 + start-all.sh（权重不入库）
  venvs/               # 三个 venv（不入库）
  bin/r12ctl.sh        # Java 服务启停
  logs/ run/           # 运行态（不入库）
  qa/                  # r12_client.py / acceptance.py / evidence/
```

## 3. 首次安装（联网一次，之后可离线）

```bash
cd platform/r12
cp .env.example .env && vi .env         # 填口令（与既有系统不同端口/不同库）
docker compose -f docker/docker-compose.infra.yml --env-file .env up -d
# 等待健康：docker ps 看 r12-* 全部 healthy

# ES 中文分词插件（首次）
curl -fsSL -o /tmp/ik.zip https://get.infini.cloud/elasticsearch/analysis-ik/8.13.4
docker cp /tmp/ik.zip r12-es:/tmp/ik.zip
docker exec r12-es bin/elasticsearch-plugin install --batch file:///tmp/ik.zip
docker restart r12-es

# Java 构建（-s 指定镜像 settings，避免内网 Nexus 阻塞）
cd services/rag-java/rag-parent
mvn -B -s ../../platform/r12/maven/settings-r12.xml -DskipTests install

# 前端
cd frontend/plateform && npm install --legacy-peer-deps --registry=https://mirrors.tencent.com/npm/ && npm run build

# Python 三个 venv + 模型权重
platform/r12/models/start-all.sh up        # 会拉起 18090/18091/18092/18093
# 算法与解析服务：见 services/rag-alg/*/start（各角色脚本）与 platform/r12/status/*.md
```

## 4. 启动顺序（有依赖，别乱序）

1. 基础设施：`docker compose -f docker/docker-compose.infra.yml --env-file .env up -d`
2. 模型服务：`platform/r12/models/start-all.sh up`（等 18090/18091/18092 就绪）
3. 算法服务：index_fulltext(19527) → index_vector(19526) → retrieval(19995) → llm(19996)
4. 解析服务：doc-parse(12340)
5. 业务服务：`platform/r12/bin/r12ctl.sh start rag-auth-service rag-index-service rag-qa-service sensitive-words-service rag-gateway`
6. 前端：dev `cd frontend/plateform && npm run dev`（15174）或生产 nginx（18088）

## 5. 健康检查

```bash
platform/r12/bin/r12ctl.sh status                       # Java 5 服务
docker ps --format '{{.Names}}\t{{.Status}}' | grep r12 # 基础设施
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8088/auth/user/kaptcha   # 期望 200
curl -s http://127.0.0.1:19200/_cluster/health                                   # 期望 green
python3 platform/r12/qa/r12_client.py                   # 登录+菜单+知识库列表
python3 platform/r12/qa/acceptance.py                   # 端到端验收，产出 evidence/
```

## 6. 停止与恢复

```bash
platform/r12/bin/r12ctl.sh stop          # 业务服务
platform/r12/models/start-all.sh down    # 模型服务
docker compose -f docker/docker-compose.infra.yml --env-file .env stop
```

**数据持久化**：MySQL/ES/Milvus/MinIO/Nacos 均使用命名卷（`r12rag_*`），`down` 不删卷；
`down -v` 才会清空数据（慎用）。

**备份/恢复（本环境实测口径）**

```bash
# 备份
docker exec r12-mysql mysqldump -uroot -p"$R12_MYSQL_ROOT_PASSWORD" --databases gienrag > backup.sql
docker run --rm -v r12rag_r12-minio-data:/d -v "$PWD":/b alpine tar czf /b/minio.tgz -C /d .
# 恢复
docker exec -i r12-mysql mysql -uroot -p"$R12_MYSQL_ROOT_PASSWORD" < backup.sql
docker run --rm -v r12rag_r12-minio-data:/d -v "$PWD":/b alpine sh -c 'rm -rf /d/* && tar xzf /b/minio.tgz -C /d'
```

## 7. 配置要点（踩过的坑）

- **口令走环境变量**：`conf/*/application-r12.yml` 中写的是 `${R12_MYSQL_PASSWORD}` 等占位，
  `r12ctl.sh` 会从 `.env` 注入。不要把它们改回明文。
- **两个端口语义**：`es_server.port` / `milvus_server.port` 指**代理**（19527/19526）；
  本体连接在 `es_conn_config.es_connect.port` / `milvus_conn_config.milvus_connect.port`（19200/19630）。混用必 404。
- **重建 jar 后必须重启进程**：Spring Boot 嵌套 jar 在运行期被覆盖会导致惰性类加载
  `EOFException`（本环境已复现一次，验证码接口 500 的根因）。
- **端口占用**：本机另有 WeKnora(80/8080)、yuxi(5050/5273/8002/19530) 等演示环境，
  R12 全端口段与之隔离，见 `R12-ENV-CONTRACT.md`。Milvus 端口冲突过一次，最终用 19630。
- **actable 自动建表**：`mybatis.table.auto=update` 会按实体创建/更新表。
  本环境是**新建空库初始化**，不代表已兼容生产 DDL（见 `docs/r12/ADAPTATIONS.md` §6）。
