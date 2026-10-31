# 平台侧离线依赖现状（2026-10-31 实测）

目标不是"记录一堆数字"，而是回答：**断网机器能不能从源码重建这套服务**。分三块量。

## 1. Java（rag-parent，Maven）

| 项 | 实测 |
|---|---|
| 本地仓库 `~/.m2` | **4.3 GB** |
| 离线构建 | `mvn -o -pl rag-index-service -am clean package -DskipTests -Dmaven.compiler.source=17 -Dmaven.compiler.target=17` 通过 |
| 产物 | `rag-index-service-0.0.1-SNAPSHOT.jar` 约 216 MB（fat jar，含 354 个依赖） |

两个必须写进部署脚本的事实：
1. 必须 **`-am`**（连带构建依赖模块）；只 `-pl` 会缺依赖，实测启动即
   `NoClassDefFoundError: cn/hutool/core/date/DateUtil`；
2. 必须显式 `-Dmaven.compiler.source/target=17`：仓库里有个 starter 模块默认 source 更低，
   会在 reactor 构建时失败（与本轮改动无关，是既有问题）。

## 2. Python 服务（platform/r12/venvs）

| venv | 体积 | 依赖数（锁文件） |
|---|---|---|
| `alg`（解析/索引/检索） | 537 MB | 103 |
| `graph`（图表服务） | 428 MB | 106 |
| `models`（多模态/模型适配） | 1.2 GB | 44 |
| `parse`（文档解析） | 1.5 GB | 151 |

锁文件：`offline/locks/r12-<venv>-venv.txt`（`alg`/`parse` 没有 pip，用 `importlib.metadata` 导出）。

## 3. 已有制品流程（可复用）

HippoRAG 已经跑通"清单 + 校验安装 + 干净机复验"（见同目录 `README.md` 与
`hipporag-2.0.0a4-py311-linux-x86_64.manifest.json`，184 wheel / 3.5 GB）。平台 venv 沿用同一套：

```bash
# 组装（联网机）
pip download --no-deps -r offline/locks/r12-graph-venv.txt -d /path/to/wh-graph
python scripts/build_offline_bundle.py --wheel-dir /path/to/wh-graph \
  --requirements offline/locks/r12-graph-venv.txt --name r12-graph-venv-py311 \
  --out offline/r12-graph-venv-py311.manifest.json

# 安装（断网机）
python scripts/install_offline_bundle.py --manifest offline/r12-graph-venv-py311.manifest.json \
  --wheel-dir /path/to/wh-graph --pip /opt/r12-graph/bin/pip
```

## 4. 仍未覆盖（不许当成已具备离线交付）

1. **模型权重**：`models` venv 1.2 GB 里是否含权重未逐一核对；MinerU/OCR 权重在 ModelScope，
   HuggingFace（`huggingface.co`）本机不可达（实测 000），权重来源必须单独登记；
2. **容器镜像**：Milvus / ES / MinIO / etcd / Redis / MySQL 的镜像 tar 未导出；
3. **前端静态资源**：未见构建产物清单；
4. **venv wheelhouse 只下了 graph 一个**（后台作业，`/tmp/wh-graph`），其余三个未拉。

## 5. 制品存放位置（持久目录，非 /tmp）

本轮把 7.5 GB 制品从 `/tmp`（重启即失）迁到持久目录，并逐个复核哈希：

| 目录 | 内容 | 体积 | 复核 |
|---|---|---|---|
| `/home/szf/data/dev/delivery/wheels-hipporag` | 184 wheels | 3.5 GB | 184/184 哈希匹配，0 不符 |
| `/home/szf/data/dev/delivery/images-r12` | 6 个镜像 tar | 3.98 GB | 6/6 哈希匹配，0 不符 |

复核方式（不安装、只比对）：
```bash
python scripts/install_offline_bundle.py --manifest <manifest> \
  --wheel-dir /home/szf/data/dev/delivery/wheels-hipporag --pip <venv>/bin/pip --skip-verify
# 以及逐文件 sha256 比对（见本节脚本片段/CI 目标）
```
迁移后再次用新路径安装通过（`status: OK`），说明清单不依赖原路径。

## 6. 中间件镜像包（本轮补）

按**运行中容器的实际镜像**导出（不是按猜测的镜像名），`docker save` 后生成清单：

| 镜像 | tar 体积 |
|---|---|
| `milvusdb/milvus:v2.5.6` | 1.6 GB |
| `r12/elasticsearch-ik:8.13.4` | 1.2 GB |
| `mysql:8.4` | 794 MB |
| `minio/minio:RELEASE.2023-03-20T20-16-18Z` | 244 MB |
| `quay.io/coreos/etcd:v3.5.5` | 179 MB |
| `redis:7.4.10-alpine` | 39 MB |
| **合计** | **3.98 GB**（6 个） |

清单：`offline/r12-middleware-images.manifest.json`（逐 tar 的 sha256 + 字节数 + 镜像名），
生成用 `scripts/build_image_bundle.py`（镜像名与文件名显式映射，不做猜测）。
`docker load` 回环已用最小的 redis 镜像验证：`Loaded image: redis:7.4.10-alpine`。

一个实际踩过的坑：最初导出了 `openspg-minio` 和 `mysql:8.0`，而运行栈用的是
`minio/minio:RELEASE.2023-03-20` 与 `mysql:8.4`——**镜像名必须从 `docker inspect <container>` 取**，
不能按仓库里出现过的名字猜，否则离线包会"装得上但版本不对"。
