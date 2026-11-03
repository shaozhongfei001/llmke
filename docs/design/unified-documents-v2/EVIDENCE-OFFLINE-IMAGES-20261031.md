# 离线交付：镜像包校验（2026-10-31）

入口 `scripts/v2_verify_image_bundles.py`，报告 `offline/image-bundle-verify.json`。

## 结果

```
{"PASS": 6, "FAIL": 0}  verdict=PASS
```

| 镜像 | 层数 | RepoTags |
|---|---|---|
| milvusdb/milvus:v2.5.6 | 7 | 一致 |
| r12/elasticsearch-ik:8.13.4 | 12 | 一致 |
| mysql:8.4 | 10 | 一致 |
| redis:7.4.10-alpine | 7 | 一致 |
| minio/minio:RELEASE.2023-03-20T20-16-18Z | 6 | 一致 |
| quay.io/coreos/etcd:v3.5.5 | 7 | 一致 |

每项校验：文件大小、sha256、tar 内 `manifest.json` 的 RepoTags 是否含声明镜像、
所有 `Layers` 是否都在包内（缺层即判失败）。

## 一个刻意的取舍：不 `docker load`

本机 docker 里跑着 r12 中间件容器，**同名 tag 一旦被新 tar 覆盖，下次重启就会换镜像**。
为了"验一下包"去改动运行环境的 tag 不值得，所以这里只读包内 manifest，不 load。
真正的 `docker load` 应放到干净目标机上做——那时没有在用容器，也不存在覆盖问题。

这条边界必须写明，否则"镜像校验 PASS"会被误读成"已在干净机验证过启动"。
