# R14-F07 安装流程 + F06 源码与离线构建材料（E-deliver）

日期：2026-10-27　改动文件：`bin/{up.sh,offline-kit.sh,r12ctl.sh}`、`offline/templates/*`

## 1. F07-①：安装文档顺序倒置（已修）

R13 文档顺序是「先 init-db / init-nacos，再起容器」，而 `init-db.sh` 第 31 行明确：
```
docker ps --format '{{.Names}}' | grep -qx "$CT" || die "容器 $CT 未运行（先 docker compose up -d mysql）"
```
即**文档第一步就会失败**。

`offline-kit.sh` 生成的 `INSTALL-OFFLINE.md` 已改为（实测生成的目录顺序）：
```
0) 放置安装包
1) 导入镜像
2) 校验完整性（sha256sum -c，禁止 --ignore-missing）
3) 环境变量
4) 路径适配
5) 起基础设施并**等就绪**（Nacos readiness 200 / mysqladmin ping / ES 可应答）
6) 初始化数据库（必须在第 5 步之后）
7) 发布 Nacos 配置并**回读比对内容**
8) ES 单节点副本治理（幂等，必做）
9) 起模型/算法/业务
10) 前端（生产 nginx 容器；**不要** npm dev）
11) 自检（must 失败即非零）
12) systemd --user 托管（含自愈看门狗）
13) 源码复建（与运行包分开验证）
```

`up.sh` 同步加就绪判据（第 1.1 步）：`r12-wait-ready.sh nacos 300`、`mysqladmin ping`、ES `_cluster/health` 可应答，任一失败即整体退出非零。

## 2. F07-②：`up.sh verify` 曾"只打印不判失败"（已修）

R13 的 verify 只 `printf`，永远 exit 0，安装流程无法据此中断。

现在分 must / warn 两级，**must 任一失败 exit 1**：

| 级别 | 判据 |
|---|---|
| must | 18088 `/`=200；8088 `/auth/user/kaptcha`=200；18095 `/healthz`=200 |
| must | ES `kb_9/_count`=200 且集群 **green**；MinIO 匿名 GET=**403** |
| must | 内部端口在监听：12340 18081-18085 19526 19527 19529 19995 19996 |
| must | 模型真实可用：18090 `/healthz`、18091 `/healthz`、18092 `/health` = 200 |
| warn | 18093 `/health`（VLM 可选）、15174 前端 dev |

实测：
```
$ up.sh verify            -> 20 项 [ok]，warn 1（dev 未起）
$ echo $?                 -> 0
# 负例：先 systemctl --user stop r12-docparse
$ up.sh verify ; echo $?  -> [FAIL] 验收失败：must 项 1 个未通过  $?=1
# 恢复后再跑             -> $?=0
```

## 3. F07-③：生产默认 npm dev（已移除）

`up.sh` 第 8 步改为只起生产 nginx 容器（18088），dev server 必须显式 `--with-dev-fe`：
```
$ up.sh up                -> [ok] 未启动 npm dev（生产默认走 18088 nginx；需要时加 --with-dev-fe）
```
`up.sh` 起前端后追加 `docker update --restart unless-stopped r12-fe`（此前 r12-fe 是 14 个 r12-* 容器里唯一 `RestartPolicy=no`，停掉后无人拉起，D 已踩）。

## 4. F07-④：Nebula unhealthy（探针错，已证实）
见 `R14-E-EXPOSURE-ES.md §3`：容器内 `127.0.0.1:19559` exit 7、`172.28.0.2:19559` exit 0；现三容器 healthy，并用 nebula3 客户端 `SHOW SPACES` / `LOOKUP ON entity` 证明引擎可读写。

## 5. F06：源码与离线构建材料（已纳入打包与清单）

### 5.1 包里原来有什么、缺什么
原 payload：算法源码 `src/services/rag-alg/*` + 前端 `frontend/dist` + jar + venv + 模型。
**缺**：Java 源码、前端源码与构建配置、以及"离线构建怎么做"的任何说明。

### 5.2 新增 `payload/src-build/`
```
src-build/
  services/rag-java/                16M（tar --exclude=target --exclude=*.class，原始 998M）
  frontend/plateform/               92M（src 41M + public 48M + package.json + package-lock.json
                                     + pnpm-lock.yaml + yarn.lock + vite/tsconfig/postcss/tailwind 等，不含 node_modules 1.4G）
  build/
    BUILD-OFFLINE.md                构建说明（Java/npm/Python 三段 + 验收判据）
    OFFLINE-BUILD-MANIFEST.tsv      409 行清单
    settings-r12.xml                Maven 内网镜像模板
    resolve-maven-offline.sh        dependency:go-offline 拉齐本地仓库
    resolve-npm-offline.sh          npm ci → 离线 cache
    resolve-python-offline.sh       pip download → wheel 目录
  README-NOT-INCLUDED.md            明确写"哪些没进包、怎么复现"
```

### 5.3 清单口径（不编造）
`OFFLINE-BUILD-MANIFEST.tsv` 列：`kind / coords / name / version / scope / sha256 / local_path / how_to_obtain`
```
$ awk -F'\t' 'NR>1{print $1}' .../OFFLINE-BUILD-MANIFEST.tsv | sort | uniq -c
      4 build-config
    398 java-runtime
      1 npm-lock
      1 npm-package
      1 pnpm-lock
      2 python-requirements
      1 yarn-lock
```
- `java-runtime` 398 行来自**实际 fat jar 的 `BOOT-INF/lib`**，坐标 `groupId:artifactId:version` 从本机 `~/.m2` 反查并给 `sha256`（例：`com.zaxxer.HikariCP:HikariCP:5.0.1 26d49239…`）。
- 其中 **1 个**工件本机 `~/.m2` 无同版本缓存 → 输出 `coords=UNKNOWN:… / sha256=-`，并在生成时打印 `[!!] 1 个 … 未找到，已标注为需按坐标获取（未编造哈希）`。**不伪造校验和**。
- Maven **构建期**（parent pom、装饰插件）不在 fat jar 里，无法离线枚举 → 不编造，改由 `resolve-maven-offline.sh`（`dependency:go-offline` + 预热构建）在联网/内网镜像环境一次性拉齐。
- 前端以 `package-lock.json` 为精确清单（lock 自带 integrity）；Python 以 `requirements.txt` 为准。
- 显式**不装** `node_modules`（1.4G）与 `~/.m2`：改成"清单 + 校验和 + 获取脚本"，并在 `README-NOT-INCLUDED.md` 点明。

### 5.4 实跑验证（源码范围打包，跳过 20G 镜像/venv/模型）
```
$ PACK_SCOPE=src OUT=/tmp/pack-src offline-kit.sh pack
  [ok] src-build/services/rag-java 16M（已排除 target/ 与 *.class）
  [ok] src-build/frontend/plateform 92M（15 项，不含 node_modules）
  [ok] OFFLINE-BUILD-MANIFEST.tsv: build-config=4, java-runtime=398, npm-lock=1, npm-package=1, pnpm-lock=1, python-requirements=2, yarn-lock=1
  [ok] build/OFFLINE-BUILD-MANIFEST.tsv 409 行
  [ok] src-build/README-NOT-INCLUDED.md
  [ok] SHA256SUMS 5404 行
  [ok] INSTALL-OFFLINE.md

$ OUT=/tmp/pack-src offline-kit.sh manifest | sed -n '/源码与离线构建材料/,/代码/p'
  [ok]   src-build/services/rag-java/rag-parent/pom.xml
  [ok]   src-build/frontend/plateform/package.json
  [ok]   src-build/frontend/plateform/package-lock.json
  [ok]   src-build/frontend/plateform/src
  [ok]   src-build/build/BUILD-OFFLINE.md
  [ok]   src-build/build/OFFLINE-BUILD-MANIFEST.tsv
  [ok]   src-build/build/settings-r12.xml
  [..]   前端 src 顶层 12 项；Java 源文件 1044 个；node_modules 与 ~/.m2 按要求不入包
  [ok] 源码/构建材料齐备（7 项）
```
`PACK_SCOPE=src` 是我新增的打包范围开关（默认 `full`），用于"只出源码材料"的快速交付与验证，不影响完整包。

## 6. 打包侧顺带修的真实缺陷
| 缺陷 | 现象 | 修法 |
|---|---|---|
| `$P/models` 目录未创建 | `cp: 无法创建普通文件 'payload/models/': 不是目录`，随后误报"models/start-all.sh 不存在" | mkdir 列表补 `"$P/models"`；消息改成"不存在"与"目录缺失"分离 |
| 自愈脚本未随包 | 目标机装完只有 unit、没有看门狗与就绪闸门 | `bin/` 拷贝与 `REQUIRED_FILES` 增加 `r12-watchdog.sh`、`r12-wait-ready.sh`、`es-single-node.sh`、`check-exposure.sh`、`offline-build-manifest.py` |
| 校验和把 images.tar 当必需 | `PACK_SCOPE=src` 下 `sha256sum images.tar` 报错 | 改为存在才追加 |

## 7. 未做/待外部
1. **完整包（含 20G 镜像与 24G 运行时）本次未重打**：本轮只做了源码范围实跑与清单验证；完整重打需要 ~20-40 分钟磁盘拷贝，等候选冻结后再打一次，并用 `offline-kit.sh verify` 复核。
2. **干净目标机实装**仍未做（需要独立主机/VM），当前只能做到"独立目录 + 独立库"。
3. `check-exposure.sh --expect-closed` 归零依赖 TL 决定补丁口径（见 `R14-E-EXPOSURE-ES.md §1.4`）。
