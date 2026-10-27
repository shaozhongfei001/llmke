# R14-F02 暴露面收口 + ES 单节点副本治理 + Nebula 探针根因（E-deliver）

日期：2026-10-27　所有权：`platform/r12/{bin,docker,conf,systemd}`；`bin/check-exposure.sh` 属 TL，本文件只给补丁不擅改。

## 1. 暴露面：7 → 3（剩余 3 个经核实不属于 r12 可自主处置范围）

### 1.1 改前（改前门禁原样输出，节选）
```
$ bash platform/r12/bin/check-exposure.sh --expect-closed
  33060  0.0.0.0:33060      数据面    对外
  3306   0.0.0.0:3306       数据面    对外
  2379   172.17.0.1:2379    数据面    对外
  18085  [::ffff:127.0.0.1]:18085 数据面 对外
  18081  [::ffff:127.0.0.1]:18081 数据面 对外
  18083  [::ffff:127.0.0.1]:18083 数据面 对外
  18082  [::ffff:127.0.0.1]:18082 数据面 对外
  数据面非回环=7 ... [FAIL] 7 个本项目数据面/管理面端口仍对外可达   (exit 1)
```

### 1.2 修掉 4 个：Java 双栈绑定
Spring 的 `server.address: 127.0.0.1` 在双栈 JVM 上会绑成 `[::ffff:127.0.0.1]`，`ss` 看起来像对外监听（实际仍是 IPv4-mapped 回环，但判定有歧义）。

`bin/r12ctl.sh`：
```bash
local netopt="-Djava.net.preferIPv4Stack=true"
[[ "$name" == "rag-gateway" ]] && netopt=""     # 8088 是批准对外入口，不砍 IPv6 客户端
```
改后：
```
18081  127.0.0.1:18081
18082  127.0.0.1:18082
18083  127.0.0.1:18083
18084  127.0.0.1:18084
18085  127.0.0.1:18085
8088   *:8088          <- 批准对外
18088  0.0.0.0:18088   <- 批准对外（r12-fe，host 网络）
```

### 1.3 剩余 3 个的归属证据

| 端口 | 真实属主 | 证据 | r12 实际用什么 |
|---|---|---|---|
| 3306 / 33060 | 宿主 `/usr/sbin/mysqld`（pid 1306，user mysql，10:00:51 启动） | `/etc/mysql/mysql.conf.d/mysqld.cnf`: `bind-address = 0.0.0.0`、`mysqlx-bind-address = 0.0.0.0`；`systemctl is-enabled mysql` = `enabled`；`ss -tnp state established '(dport=:3306)'` 无本机连接（只有 172.22.0.x 容器网段流量） | 容器 `r12-mysql` → `127.0.0.1:13306`；`conf/*/application-r12.yml` 全部 `jdbc:mysql://127.0.0.1:13306/gienrag` |
| 2379 @172.17.0.1 | 本机 k8s 控制面 etcd | `ps`: `/opt/kube/bin/etcd --name=etcd-172.17.0.1 --initial-cluster-token=etcd-cluster-0 --listen-client-urls=https://172.17.0.1:2379,http://127.0.0.1:2379`；同机 `kube-apiserver --etcd-servers=https://172.17.0.1:2379` | `r12-etcd` 容器 **无宿主端口映射**：`docker ps` 显示 `r12-etcd 2379-2380/tcp`（无 `->`） |

无法自主处置的原因：`sudo -n true` → `sudo: 需要密码`（本会话无 root）。关闭宿主 MySQL 的准确命令（需有 root 的人执行）：
```bash
sudo sed -i 's/^bind-address.*/bind-address = 127.0.0.1/; s/^mysqlx-bind-address.*/mysqlx-bind-address = 127.0.0.1/' \
     /etc/mysql/mysql.conf.d/mysqld.cnf && sudo systemctl restart mysql
```

### 1.4 门禁口径补丁（不擅改 TL 文件）
`offline/patches/check-exposure-attribution.diff`：
1. 回环识别补 `[::ffff:127.0.0.1]:*` / `[::ffff:7f00:1]:*`（IPv4-mapped 回环，不是对外）；
2. 新增 `HOST` 分类（3306/33060/2379/9092），单独计数并始终打印，**不静默忽略**。

在 /tmp 用同版本脚本打补丁实测：
```
$ bash /tmp/ce-new-run.sh --expect-closed
  33060  0.0.0.0:33060       宿主   对外
  3306   0.0.0.0:3306        宿主   对外
  2379   172.17.0.1:2379     宿主   对外
  数据面非回环=0  宿主其它软件非回环=3（需 root 处置，不计入本项目判定）  其他项目监听=82
  [ok] 本项目数据面/管理面全部仅回环
EXIT=0
```

### 1.5 收口后的 r12 监听面（按容器映射 + 宿主进程核对）

| 层 | 绑定 | 证据 |
|---|---|---|
| 容器 | 全部 `127.0.0.1` | `docker ps`：es `127.0.0.1:19200/19300`、minio `19000/19001`、mysql `127.0.0.1:13306`、redis `16379`、nacos `18848/19848`、milvus `19630/19191`、nebula `19669/19559/19779`、rocketmq `19876/10909/10911`；`r12-etcd` 无映射 |
| 宿主进程 | 仅 8088/18088 对外 | `ss -lntH`；其余 12340/18081-18085/18091-18093/19526/19527/19529/19995/19996/18095 全 `127.0.0.1` |
| 同机无关 | 未改动 | hadoop(NodePort 30042-31988)、WeKnora(80/8080)、yuxi(5050/5273)、dkws(8106)、k8s(6443/2379@172.17.0.1) |

## 2. ES 单节点 yellow：根因与处置

### 2.1 不是数据故障
```
$ curl /_cluster/health
status=yellow number_of_nodes=1 active_primary_shards=27 active_shards=27 unassigned_shards=27
$ curl '/_cat/indices?h=index,health,pri,rep'
kb_9 yellow 1 1 8      <- pri=1 rep=1，27 个索引全部如此
$ curl '/_cat/shards?h=index,shard,prirep,state,unassigned.reason' | grep UNASSIGNED
table_summary_r12_it_parse_002 0 r UNASSIGNED CLUSTER_RECOVERED   <- r = replica
```
结论：27 个 unassigned **全是副本**，单 data node 上副本永远分配不了。主分片 27/27 可用，数据完整。

### 2.2 处置（两条一起做才既修现状又防新增）
```bash
PUT /_all/_settings?expand_wildcards=open   {"index":{"number_of_replicas":0}}
PUT /_index_template/r12-single-node-default
    {"index_patterns":["kb_*","table_chunks_*","table_summary_*","faq_*","community_summary_*","r12_*"],
     "priority":201,"template":{"settings":{"index":{"number_of_replicas":0}}}}
```
- priority 取 201：本镜像自带 `.monitoring-*`（priority 0）与 `.fleet-*`（priority 200）模板，同优先级会被 ES 拒绝（实测两次 400，原因原文已记录）。
- 不使用前导通配（`*-chunks-*`）：ES 对前导通配做保守重叠判断，会与 `.fleet-*` 冲突。

### 2.3 结果
```
$ curl /_cluster/health
{"status":"green","active_primary_shards":27,"unassigned_shards":0,"active_shards_percent_as_number":100.0}
$ curl '/_cat/indices?h=index,health,pri,rep' | head -3
community_summary_kb_9 green 1 0 7
db1                    green 1 0 41
faq_kb_9               green 1 0 20
$ PUT /r12_replica_probe   -> {"index":{"number_of_shards":"1","number_of_replicas":"0"}}   # 模板生效
```
落成幂等脚本 `bin/es-single-node.sh`（含 green/unassigned=0 断言，不通过退出非零），`up.sh` 1.2 步调用，安装文档第 8 步必做。

## 3. Nebula unhealthy：是探针错，不是引擎坏

```
$ docker exec r12-nebula-metad curl -fsS -m3 http://127.0.0.1:19559/status   -> exit 7 (Connection refused)
$ docker exec r12-nebula-metad curl -fsS -m3 http://172.28.0.2:19559/status  -> exit 0
$ docker inspect -f '{{json .Config.Healthcheck.Test}}' r12-nebula-metad
["CMD-SHELL","bash -c 'exec 3<>/dev/tcp/172.28.0.2/9559' || exit 1; curl -fsS -m 3 -o /dev/null http://172.28.0.2:19559/status || exit 1"]
```
根因：Nebula 的 `--ws_ip` 是容器自身 IP（172.28.0.2/3/4），WS 管理口只监听该地址，`127.0.0.1` 上没有监听 → 旧探针恒 exit 7 → 三个容器长期 unhealthy，而引擎是好的。

现在三容器 `healthy`，并用**真实客户端**证明可读写（不是只看探针）：
```
venvs/graph/bin/python: nebula3 ConnectionPool.init -> True
SHOW SPACES -> [["g_kb_9"],["g_rag_graph"],["rag_graph"]]
USE g_kb_9; SHOW TAGS -> ['entity']
USE g_kb_9; LOOKUP ON entity YIELD id(vertex) | LIMIT 3 -> ok rows=3
```

## 4. 未能自主完成 / 需要他人动作

1. `3306/33060` 收紧需要 **root**（本会话 `sudo` 需密码）。命令见 §1.3。
2. `2379@172.17.0.1` 属 k8s 控制面，**不该**由本项目改（改了会打断集群）。
3. `check-exposure.sh --expect-closed` 要退出 0，需要 adopt §1.4 补丁（文件属 TL）。在此之前该门禁会因 3 个非 r12 端口**必然**退出 1 —— 这是口径问题，不是收口没做。
