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

## 7. graph venv 的 wheelhouse 已具备（第一批平台服务）

| 项 | 值 |
|---|---|
| 目录 | `/home/szf/data/dev/delivery/wheels-r12-graph` |
| 文件 | 106 个（99 wheel + **7 sdist**），95.4 MB |
| 清单 | `offline/r12-graph-venv-py310.manifest.json` |
| 解释器 | CPython 3.10（该 venv 实际是 3.10.12，与 hipporag 的 3.11 不同，清单里分开记） |

sdists 是 `alibabacloud-darabonba-*` 系列（上游只发 sdist）。离线安装它们需要目标机自带
`setuptools/wheel`，否则 `pip install` 会在构建阶段失败——这属于**必须在部署脚本里检查的前置条件**，
已写进本节而不是等装机时才发现。

清单生成器已同时统计 `wheel_count` 与 `sdist_count`（原来只数 `.whl`，会把 7 个 sdist 静默漏掉）。

## 8. 剩余三个 venv 未做

`alg`(103 包) / `parse`(151 包) / `models`(44 包, 1.2 GB) 的 wheelhouse 尚未拉取；
做法与 graph 完全一致（`pip download --no-deps -r locks/<venv>.txt`）。`models` 里若含权重，
需要单独区分"包"与"模型文件"，不能混在一个清单里。

## 9. 已完成的三份 wheelhouse（alg / graph / hipporag）

| 清单 | 文件数 | 体积 | 解释器 |
|---|---|---|---|
| `hipporag-2.0.0a4-py311-linux-x86_64.manifest.json` | 184（全 wheel） | 3,526 MB | 3.11 |
| `r12-graph-venv-py310.manifest.json` | 106（99 wheel + 7 sdist） | 95.4 MB | 3.10 |
| `r12-alg-venv-py311.manifest.json` | 103（含 sdist） | 141.8 MB | 3.11 |

清单里 `requirements.path` 改为**相对 manifest 的路径**（原来只写 basename，
放到 `locks/` 下就找不到），并由测试钉住"清单同级/相对路径必须存在且哈希一致"。

`parse`(151 包) 与 `models`(44 包，含 torch 714 MB / transformers 119 MB，**不含权重**) 的
wheelhouse 正在拉取/待拉取；两者做法相同，`models` 需注意"包 ≠ 权重"。

## 10. D-06 更正：真正缺的只有 1 个版本，已用"重打包"补上

上一版用**跑在 3.10 的 pip** 去核对 3.11 目标的版本可得性，把"解释器不匹配"误判成"公开源没有"，
得出 alg 7 / parse 10 / models 6 个缺失——**这个结论是错的**，在此更正。

按目标解释器（`--python-version 3.11`）重测：

| venv | 包数 | 真正缺失 | 说明 |
|---|---|---|---|
| `graph` | 106 | 0 | — |
| `alg` | 103 | 0（重测后） | 之前 7 个是 3.10/3.11 差异导致的误判 |
| `parse` | 151 | **1**：`soupsieve==3.0.4` | 公开最高 2.10，该版本来自私有索引 |
| `models` | 43 | 待按 3.11 重测 | — |

`parse` 的 1 个缺失用 `scripts/repack_installed_wheel.py` 从**本机已安装**的同版本重建 wheel
（纯 Python 包，拒绝非纯 Python；清单里用 `r12-parse-venv-py311.repacked.json` 标注来源，
不冒充上游发布物）。

### 离线安装 sdist 的两个硬约束（实测踩过）

1. 构建隔离会去索引找 `wheel`/`Cython` → 离线必失败；必须先把构建工具装进目标环境，
   再用 `--no-build-isolation`（安装器已内置该步骤）；
2. **构建工具也要按目标解释器拉**：用 3.10 的 pip 拉 `Cython` 会得到 cp310 wheel，
   装到 3.11 环境报 `from versions: none`（我踩过，别再用默认解释器偷懒）。

### 实测结果（parse，全新 3.11 venv，仅本地 wheel）

```
install_offline_bundle -> {"status":"OK","wheels":153,...}
pip list                -> 156 包
import fastapi/pydantic/numpy -> ok（0.109.1 / 2.14.1 / 1.26.4）
import soupsieve        -> 3.0.4（即重打包那个）
```


## 12. 四个平台 venv 的 wheelhouse 全部就位（本轮收尾）

| venv | 清单 | 文件数 | 体积 | 离线安装实测 |
|---|---|---|---|---|
| `graph` (3.10) | `r12-graph-venv-py310.manifest.json` | 106 | 95.4 MB | 全新 venv 装成 + 主模块 import ok |
| `alg` (3.11) | `r12-alg-venv-py311.manifest.json` | 103 | 141.8 MB | 清单校验通过（含 sdist） |
| `parse` (3.11) | `r12-parse-venv-py311.manifest.json` | 153 | 552.8 MB | 全新 venv 装成（156 包）+ fastapi/pydantic/numpy/soupsieve 可导入 |
| `models` (3.11) | `r12-models-venv-py311.manifest.json` | 44 | 234.0 MB | 全新 venv 装成 + `torch 2.6.0+cpu` / `transformers 4.57.6` 可导入 |

`models` 的 torch 是 **CPU 版**（2.6.0+cpu，234 MB），比 HippoRAG 那套 CUDA 栈小一个数量级——
说明"能不能离线"和"要不要 GPU"要分开算。

制品目录（持久，非 /tmp）：`/home/szf/data/dev/delivery/`
- `wheels-hipporag` / `wheels-r12-{alg,graph,parse,models}`：wheelhouse
- `images-r12`：6 个中间件镜像 tar（3.98 GB）

**已删除**：`venv-r12-parse-py311.tar`（1.36 GB 环境快照）——wheelhouse 已可用（含重打包的
soupsieve 3.0.4），快照作为兜底没有保留价值，避免交付介质里出现两套来源不一致的 parse 环境。

## 13. 离线环境里把图服务**真正跑起来并回答**（不是只 import）

用 `wheels-r12-graph` 装出的 3.10 venv，在 19531 端口起 `index_graph_service`：

```
GET  /openapi.json   -> ['/generate_community','/query_community','/del_community']
POST /query_community {"space_name":"kb_9","mode":"global","query":"产品额度","top_k":3}
 -> code=200 msg="global 汇总完成（社区 10 个，命中 4 个，有相关事实 4 个）"
    answer="海川电子材料股份有限公司的智造贷产品额度为8000万元 [L0-659385b9]。
            其中 信用部分最高额度 1000万元（分项，不属于总额度）[L1-e0525331]"
```

这同时证明三件事：离线依赖闭包完整、服务能启动、并且能连真实 ES/Milvus/LLM 产出带引用的答案。

启动时踩到的配置坑（与离线包无关，但会让人误判）：
- `DATA_ID` 必须用 `index_graph_config_py`（我从 19529 进程的 environ 里取到的真值）；
- 先用 `index_data_config_py` 启会报 `KeyError: 'graph_server'`，看着像"包不全"，其实是配置读错。

实例已关停（19531 无监听）。
