# 源码复建说明（离线 / 内网镜像）

本目录是**源码与离线构建材料**，与运行包（jar / dist / venv / 模型）是两件事：
运行包用于"照单装机"，本目录用于"从源码重新构建出同一候选"。二者要分别验证。

```
src-build/
  services/rag-java/             Java 业务源码（已剔除 target/ 与 *.class）
  frontend/plateform/            前端源码与构建配置（src/ public/ package.json + 三种 lock）
  build/
    BUILD-OFFLINE.md             本文件
    OFFLINE-BUILD-MANIFEST.tsv   离线构建清单（见下）
    settings-r12.xml             Maven 内网镜像 settings 模板
    resolve-maven-offline.sh     在"可联网或内网镜像"机器上一次性拉齐依赖
    resolve-npm-offline.sh       同上，npm
    resolve-python-offline.sh    同上，pip
```

## 0. 三个 lock/manifest 的口径（不要混用）

| 类别 | 精确清单 | 说明 |
|---|---|---|
| Java 运行时 | `OFFLINE-BUILD-MANIFEST.tsv` 中 `kind=java-runtime` | 来自**实际 fat jar 的 `BOOT-INF/lib`**，坐标 `groupId:artifactId:version` + `sha256`。这就是跑起来必需的那批工件 |
| Java 构建期 | 不在清单里，按需拉齐 | parent pom 与 maven 插件不在 fat jar 内，无法只靠离线枚举。用 `resolve-maven-offline.sh` 在可联网/内网镜像环境执行 `dependency:go-offline` |
| 前端 | `package-lock.json`（npm）为主 | lock 本身就是精确清单（含 integrity 哈希）；`pnpm-lock.yaml` / `yarn.lock` 仅作历史对照，三选一，与 `package.json` 保持一致 |
| Python | `requirements.txt` / `requirements.lock` | 用 `resolve-python-offline.sh` 拉成 wheel 目录 |

**清单里 `coords` 为 `UNKNOWN:` 前缀的行**表示该工件在本机 `~/.m2` 没有同版本缓存，因此**没有哈希**——
不要当作已验证，按坐标从内网镜像取回后自行补算 `sha256sum`。

## 1. 目标环境前提

- JDK 21（`java -version` 与运行包一致）；Maven 3.6+
- Node.js 20 LTS + npm 10（与 `package.json` 的 `engines` 一致）
- Python 3.11（`venvs/` 的 `pyvenv.cfg` 版本必须与目标机解释器一致）
- 内网镜像可达：Maven（Nexus/Artifactory）、npm registry、PyPI

## 1.5 跨模块构建陷阱（本轮最大时间黑洞，必读）

本项目是多模块 Maven 工程，`rag-common`、`gien-starter-*`（file-storage / easyexcel / redisson / swagger）、
`tools-*` 等**共享模块**被业务模块以依赖形式引用。

**只 `mvn -pl <业务模块> package` 会用 `~/.m2` 里的旧依赖**——源码改了、业务模块却链接到旧的共享模块字节码，
表现为"源码已改、运行态不生效，而离线自检通过"。正确顺序：

```bash
# 1) 先安装被改动的共享模块到本地仓库
mvn -o -B -Dmaven.repo.local="$PWD/m2repo" -DskipTests install -pl gien-starter-file-storage -am
#    （改了哪个装哪个：rag-common / gien-starter-* / tools-* 同理）
# 2) 再打业务模块
mvn -o -B -Dmaven.repo.local="$PWD/m2repo" -DskipTests package -pl rag-index-service
```

**验证 fat jar 里到底是哪个版本**（不要只看构建成功）：

```bash
# 列出 fat jar 内置依赖
unzip -l rag-index-service/target/rag-index-service-0.0.1-SNAPSHOT.jar | grep 'BOOT-INF/lib/' | awk '{print $4}'
# 特征串核对：确认被打进去的是"你刚改的"那份（举例：本次改动含某个新增类名/常量）
unzip -p rag-index-service/target/*.jar 'BOOT-INF/lib/gien-starter-file-storage-*.jar' > /tmp/gsfs.jar \
  && unzip -p /tmp/gsfs.jar '**/你的新增类.class' | strings | grep -m1 '你的特征串'
```

判据：`BOOT-INF/lib/` 里共享模块的版本号必须与 `mvn install` 时装进去的一致；特征串必须能找到。

## 2. Java 构建

```bash
cd src-build/services/rag-java/rag-parent
# 2.1 先用内网镜像拉齐依赖（一次即可，之后可 -o 离线构建）
bash ../../../build/resolve-maven-offline.sh ./m2repo        # 产出本地仓库 m2repo/
# 2.2 离线构建
mvn -o -B -Dmaven.repo.local="$PWD/m2repo" -DskipTests clean package
# 2.3 产物对齐运行包
ls */target/*.jar | wc -l        # 期望 ≥12（6 个服务各自的可执行 jar + 依赖模块）
```

构建产物与运行包 `jars/` 的对应关系：`jars/<service>-0.0.1-SNAPSHOT.jar`。
**必须比对 sha256**，不一致就说明源码/依赖与运行包不是同一候选：

```bash
sha256sum */target/*.jar          # 与安装前缀 jars/ 下同名文件比对
```

## 3. 前端构建

```bash
cd src-build/frontend/plateform
bash ../../build/resolve-npm-offline.sh ./npm-cache    # 产出离线 npm 缓存
npm ci --offline --cache ./npm-cache                   # 严格按 lock 安装
npm run build                                          # 产出 dist/
```

产物 `dist/` 与运行包 `frontend/dist` 比对：`index.html` + `assets/` 项数、关键 chunk 的 sha256。

## 4. Python 侧

```bash
cd <repo根>
bash src-build/build/resolve-python-offline.sh ./wheels     # 按 requirements.txt 下载 wheel
python3.11 -m venv venv && venv/bin/pip install --no-index --find-links ./wheels -r requirements.txt
```

venv **不能**直接拷贝到异构目标机（https://docs.python.org/3.11/library/venv.html ）：
运行包里的 `venvs/` 只适用于同 ABI/同 libc 目标机，否则按本节重建。

## 5. 验收判据（构建侧）

1. `mvn -o` 构建成功且 jar 数量 ≥12；
2. `npm ci --offline` 成功且 `npm run build` 产出 `dist/index.html`；
3. 复建产物与运行包同名文件 `sha256` 一致（不一致即候选漂移，需说明原因）；
4. 复建产物能在干净环境启动并通过 `bin/up.sh verify`。

## 6. 不在包内的东西（体积原因，按需自取）

- `node_modules/`（1.4G）：用 `resolve-npm-offline.sh` + lock 复现；
- `~/.m2/repository/`：用 `resolve-maven-offline.sh` + `OFFLINE-BUILD-MANIFEST.tsv` 坐标复现；
- Python wheel 全量缓存：用 `resolve-python-offline.sh` 复现。

这三项都**不**随包分发，但每一项都有"清单 + 校验和 + 获取脚本"，不是"缺了就装不了"。
