#!/usr/bin/env bash
# R12 部署制品打包：把"可复现部署所需的一切"打成离线包（不含模型权重与 venv，体积原因单列）。
# 产物：platform/r12/dist/r12-bundle-<YYYYmmddHHMM>.tar.gz + MANIFEST.sha256 + INSTALL.md
set -euo pipefail

R12_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$R12_ROOT/../.." && pwd)"
STAMP="$(date +%Y%m%d%H%M)"
OUT="$R12_ROOT/dist"
NAME="r12-bundle-$STAMP"
STAGE="$OUT/$NAME"
JAVA_PARENT="$REPO_ROOT/services/rag-java/rag-parent"

mkdir -p "$OUT" "$STAGE"

echo "== 1/6 Java 产物 =="
mkdir -p "$STAGE/jars"
for m in rag-auth-service rag-index-service rag-qa-service rag-gateway sensitive-words-service rag-graph-service; do
  jar="$JAVA_PARENT/$m/target/$m-0.0.1-SNAPSHOT.jar"
  [[ -f "$jar" ]] && cp "$jar" "$STAGE/jars/" || echo "WARN 缺少 $jar"
done

echo "== 2/6 配置文件 =="
mkdir -p "$STAGE/conf" "$STAGE/maven"
cp -r "$R12_ROOT/conf/." "$STAGE/conf/"
cp "$R12_ROOT/maven/settings-r12.xml" "$STAGE/maven/"
cp "$R12_ROOT/.env.example" "$STAGE/.env.example"
cp -r "$R12_ROOT/log4j2" "$STAGE/log4j2" 2>/dev/null || true

echo "== 3/6 编排与脚本 =="
mkdir -p "$STAGE/docker" "$STAGE/bin"
cp -r "$R12_ROOT/docker/." "$STAGE/docker/"
cp "$R12_ROOT/bin/r12ctl.sh" "$STAGE/bin/"
chmod +x "$STAGE/bin/r12ctl.sh"

echo "== 4/6 种子与验收脚本 =="
mkdir -p "$STAGE/seed" "$STAGE/qa"
cp -r "$R12_ROOT/seed/." "$STAGE/seed/"
cp "$R12_ROOT/qa/r12_client.py" "$R12_ROOT/qa/acceptance.py" "$STAGE/qa/"

echo "== 5/6 前端产物 =="
if [[ -d "$REPO_ROOT/frontend/plateform/dist" ]]; then
  mkdir -p "$STAGE/frontend"
  tar -C "$REPO_ROOT/frontend/plateform/dist" -czf "$STAGE/frontend/dist.tar.gz" .
else
  echo "WARN 前端 dist 不存在，跳过（需先 npm run build）"
fi

echo "== 6/6 说明与校验 =="
cp "$R12_ROOT/README.md" "$STAGE/INSTALL.md"
cat >> "$STAGE/INSTALL.md" <<'EOT'

---
## 离线包补充说明
- 本包**不含**模型权重（`platform/r12/models/**`，约 6GB）与 Python venv，原因：体积与架构相关。
  目标机获取方式见 §3（一次性联网拉取后即可离线运行）。
- 校验：`sha256sum -c MANIFEST.sha256`
- 还原：解包到目标机任意目录，`cp .env.example .env` 填口令，按 §4 顺序启动。
EOT

( cd "$STAGE" && find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256 )

tar -C "$OUT" -czf "$OUT/$NAME.tar.gz" "$NAME"
echo "== 完成 =="
ls -lh "$OUT/$NAME.tar.gz"
du -sh "$STAGE"
