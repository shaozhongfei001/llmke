# R14 F06/F07：把 analysis-ik 从"运行时手工 docker cp 安装"固化成镜像层。
#
# 为什么必须这样（真实事故）：
#   R13 交付时 IK 是用 `docker cp ik.zip r12-es:/tmp/` + `elasticsearch-plugin install file:///tmp/ik.zip`
#   装进 **容器可写层** 的（见 platform/r12/status/alg.md:145-172）。可写层不随镜像走、不随离线包走。
#   R14 为收口监听面重建 r12-es（`docker compose up -d` 会 recreate 变更过的服务）后，可写层被丢弃，
#   插件消失 → 19 个已存在的索引 mapping 里仍是 ik_max_word → ES 加载分片失败
#   → `_cluster/health` 变 red（active_primary_shards=0）。而旧 healthcheck 只 curl /_cluster/health
#   看 HTTP 200，red 也返回 200，所以 30 小时里一直是"healthy"假绿。
#
# 构建（构建机，需能取到 IK zip；目标机不需要联网，用 images.tar 里的成品镜像）：
#   cd platform/r12/docker
#   docker build -f elasticsearch-ik.Dockerfile -t r12/elasticsearch-ik:8.13.4 .
#   docker save r12/elasticsearch-ik:8.13.4 >> <offline>/images.tar
#
# 校验：镜像内 /usr/share/elasticsearch/plugins/analysis-ik 必须存在且非空。
FROM elasticsearch:8.13.4

# 期望的 IK 包 sha256（与 plugins/elasticsearch-analysis-ik-8.13.4.zip 一致）
ARG IK_SHA256=9fa37bad9da16a7d5b256bb5d3542eec5300b041c539c461fa9c24c4c41abd09

COPY plugins/elasticsearch-analysis-ik-8.13.4.zip /tmp/ik.zip

# 不在 Dockerfile 里 curl 下载：离线可复建的前提是"包内自带"。
# 校验 sha256，避免把错版本/被替换的包打进镜像。
# 注意：官方 ES 镜像的 /tmp 在本环境删除会报 "Operation not permitted"，
# 因此清理失败不视为构建失败（残留 4.6MB，不影响运行）；插件目录必须非空才算成功。
RUN set -eux; \
    echo "${IK_SHA256}  /tmp/ik.zip" | sha256sum -c -; \
    /usr/share/elasticsearch/bin/elasticsearch-plugin install --batch file:///tmp/ik.zip; \
    rm -f /tmp/ik.zip || true; \
    test -n "$(ls -A /usr/share/elasticsearch/plugins/analysis-ik)" || \
      (echo "FAIL: analysis-ik 插件目录为空" >&2; exit 1)
