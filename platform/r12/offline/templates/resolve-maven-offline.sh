#!/usr/bin/env bash
# R14-F06：在"可联网或内网镜像可达"的机器上一次性拉齐 Maven 依赖，
# 产出一个可整体拷到目标机的本地仓库；目标机随后可用 `mvn -o` 离线构建。
#
# 用法（在 rag-parent 目录下执行）:
#   resolve-maven-offline.sh [本地仓库目录，默认 ./m2repo]
# 环境变量:
#   MAVEN_MIRROR  内网仓库 URL，例: https://nexus.internal/repository/maven-public/
#                 （不设则用 settings.xml 里已配置的镜像，即真正走外网中央仓）
set -uo pipefail
REPO="${1:-./m2repo}"
SETTINGS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/settings-r12.xml"

ok()   { printf '  [ok] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1"; exit 1; }

[ -f pom.xml ] || die "请在 rag-parent 目录下执行（找不到 pom.xml）"
command -v mvn >/dev/null || die "未安装 maven"

if [ -n "${MAVEN_MIRROR:-}" ]; then
  sed "s#<url>.*</url>#<url>${MAVEN_MIRROR}</url>#" "$SETTINGS" > /tmp/settings-resolve.xml
  S="$SETTINGS"; S=/tmp/settings-resolve.xml
  ok "使用内网镜像 $MAVEN_MIRROR"
else
  S="$SETTINGS"; ok "使用 settings-r12.xml（若其中仍是占位 URL，请改用 MAVEN_MIRROR 指定内网仓库）"
fi

echo "== 拉取依赖到 $REPO（parent + 插件 + 运行时依赖）=="
mvn -B -s "$S" -Dmaven.repo.local="$REPO" \
    -DincludeScope=runtime dependency:go-offline || die "dependency:go-offline 失败"

echo "== 预热编译插件（go-offline 不覆盖所有插件）=="
mvn -B -s "$S" -Dmaven.repo.local="$REPO" -DskipTests clean package >/tmp/mvn-warm.log 2>&1 \
  || { echo "  [!!] 预热构建失败，详见 /tmp/mvn-warm.log（依赖可能仍不全）"; }

ok "本地仓库就绪: $REPO（$(du -sh "$REPO" 2>/dev/null | cut -f1)）"
echo "拷到目标机后："
echo "  mvn -o -B -Dmaven.repo.local=<该目录> -DskipTests clean package"
