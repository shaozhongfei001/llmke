# 部署收口：镜像条件 load + 冒烟、差分升级（2026-10-31）

两件一直卡着的事：镜像"只验包不 load"、升级"只会全量重装"。这轮都做了，但都加了
**前置条件**而不是无脑执行。

## 1. 镜像：条件 load + 冒烟启动

原来拒绝 load 的理由是"同名 tag 被覆盖会影响下次重启"。这次先做了**ID 比对**：

```
tar 内 manifest.json 的 Config 摘要  vs  本地 docker image inspect <tag> 的 .Id
```

6 个镜像**全部一致**，所以 load 是 no-op（不改变任何 tag），可以安全执行。
脚本现在只在两者完全相同时 load，不一致一律 `REFUSED` 并报 DIFF——把"要不要覆盖"交回给人。

load 之后 `docker run --rm --network none` 跑最轻启动命令：

| 镜像 | 冒烟命令 | 结果 |
|---|---|---|
| mysql:8.4 | `mysql --version` | `Ver 8.4.11` |
| redis:7.4.10-alpine | `redis-server --version` | `v=7.4.10` |
| quay.io/coreos/etcd:v3.5.5 | `etcd --version` | `etcd Version: 3.5.5` |
| minio/minio:RELEASE… | `minio --version` | `RELEASE.2023-03-20…` |
| r12/elasticsearch-ik:8.13.4 | `elasticsearch --version` | `Version: 8.13.4` |
| milvusdb/milvus:v2.5.6 | `milvus --help` | rc=0 |

ES 在 `--network none` 下会先打一条 hostname 解析 ERROR（隔离环境产物），但随后仍输出
`Version: 8.13.4` 且 rc=0。所以冒烟判据不只看 rc，还要求**期望片段**出现——否则
"输出对但有一行噪声"和"根本没起来"会被混为一谈。

## 2. 差分升级：只装新增/替换，且替换必须授权

`scripts/v2_delta_upgrade.py`：按 manifest 的**包名**做差集（不是文件名），
`--no-index --find-links` 装绝对路径，`--repin` 收尾回锁。

真跑（parse 基线 → 并入 models + mineru）：

```
新增 56、替换 25、删除 0 → 安装 81 个 wheel（不是全量 250+）
装完 repin numpy==1.26.4 成功
探针：MinerU 解析出 111 字符中文正文 + bbox
最终：numpy 1.26.4 / pandas 2.3.2 / torch 2.6.0+cpu
```

三条硬规则（都是踩出来的，已写进工具）：

1. **替换必须显式 `--allow-replace`**。把 models 并进 parse 会**顶掉 25 个核心包**：
   `fastapi / pydantic / starlette / uvicorn / pandas / httpx / scipy / onnxruntime …`。
   不授权时工具直接 `REFUSED_REPLACEMENTS`（退出码 2），而不是"升级成功、运行期崩"。
2. **同一个包的多个版本不能同时进安装列表**。第一次跑就撞上 `hf-xet 1.7.0` 与 `1.8.0`
   并存 → `ResolutionImpossible`；现在按包合并、后给的覆盖先给的，并记进 `superseded`。
3. **差集必须按包名不按文件名**。`numpy-1.26.4` 与 `numpy-2.4.6` 是两个不同文件名，
   按文件名比会把它算成"新增"，于是悄悄装上 numpy 2.x，pandas 运行期 ABI 崩。
   现在合并后会明确 `superseded: numpy 2.4.6 → 1.26.4`。

## 3. 一个必须说清的结论

"把 MinerU 并进 parse 环境"这件事，**不是装一个包，而是替换 25 个核心依赖**。
当前实测能跑（探针通过、imports 全绿），但 `pdfminer.six` 的 pin 冲突仍然存在
（pdfplumber 要 `==20231228`，实际 20250506），只是没在用到的那条路径上炸。

所以交付建议保持：**MinerU 用独立 venv / 独立服务**，或出一份人工审过的联合约束文件，
而不是运行时并包。

## 还没做 / 边界

- **没有干净目标机**：load 是在"ID 相同"前提下做的 no-op，不是首次安装；
  镜像能否在空白机器上起来仍未验证；
- 差分升级只验了 venv 层（导入 + 探针），**没验服务进程真的用新依赖跑起来**；
- `pdfminer.six` 冲突未解（需要把 pdfplumber 或 pdfminer 锁到同一版本）；
- 差分**没有回滚脚本**：升级失败可以重建 venv，但不能一键退回上一版；
- 权重（1.94GB）仍不在 wheelhouse 里，靠 ModelScope 子集清单单独交付。
