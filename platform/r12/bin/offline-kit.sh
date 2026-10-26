#!/usr/bin/env bash
# R13 离线安装工具：盘点 / 打包 / 校验 / 无外网冒烟
# 用法: offline-kit.sh {manifest|pack|verify|smoke}
#
# 设计原则：
#   - 离线安装的"真相"是清单：镜像 + 模型 + Python venv + jar + 前端产物 + 配置
#   - pack 产出一个可拷贝的目录（images.tar + payload + SHA256SUMS + INSTALL-OFFLINE.md）
#   - verify 在没有外网的机器上也能跑（只做本地校验，不访问任何网络）
#   - smoke 用 --network none 起容器，证明静态产物/预览服务不依赖外网
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$R12/../.." && pwd)"
OUT="${OUT:-$R12/dist/offline}"
PY="${R12}/venvs/parse/bin/python"

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1"; exit 1; }

# 与 docker-compose.infra.yml 保持一致；更新编排时必须同步这里
IMAGES=(
  "mysql:8.4"
  "redis:7.4.10-alpine"
  "minio/minio:RELEASE.2023-03-20T20-16-18Z"
  "elasticsearch:8.13.4"
  "milvusdb/milvus:v2.5.6"
  "quay.io/coreos/etcd:v3.5.5"
  "nacos/nacos-server:v2.3.2"
  "apache/rocketmq:4.9.7"
  "docker.1ms.run/vesoft/nebula-metad:v3.8.0"
  "docker.1ms.run/vesoft/nebula-storaged:v3.8.0"
  "docker.1ms.run/vesoft/nebula-graphd:v3.8.0"
  "nginx:alpine"
  "r12/preview-office:r13"
)
MODEL_DIRS=(bge-m3 bge-reranker-v2-m3 gguf gguf-vl llama.cpp ocr_models)
VENV_DIRS=(parse alg graph)

collect_payload() {
  # 打印 payload 相对路径清单（每行一个），供 manifest/verify/pack 共用
  echo "jars"
  echo "conf"
  echo "bin/up.sh"; echo "bin/r12ctl.sh"; echo "bin/offline-kit.sh"
  echo "systemd"
  echo "preview"
  echo "graph"
  echo "docker/docker-compose.infra.yml"
  echo "frontend/dist"
  echo "docs/R13-STATUS.md"
  echo "venvs"
  echo "models"
}

cmd_manifest() {
  echo "== 镜像（$((${#IMAGES[@]})) 个）=="
  local missing=0
  for i in "${IMAGES[@]}"; do
    if docker images --format '{{.Repository}}:{{.Tag}}' | grep -qx "$i"; then
      printf '  [ok]   %-58s %s\n' "$i" "$(docker images --format '{{.Size}}' "$i" | head -1)"
    else
      printf '  [MISS] %-58s\n' "$i"; missing=$((missing+1))
    fi
  done
  echo "== 运行时资产 =="
  for d in models venvs; do
    [ -d "$R12/$d" ] && printf '  [ok]   %-58s %s\n' "$d" "$(du -sh "$R12/$d" | cut -f1)" || { printf '  [MISS] %s\n' "$d"; missing=$((missing+1)); }
  done
  for d in "${MODEL_DIRS[@]}"; do
    [ -d "$R12/models/$d" ] && printf '  [ok]   models/%-51s %s\n' "$d" "$(du -sh "$R12/models/$d" | cut -f1)" || printf '  [warn] models/%s 不存在\n' "$d"
  done
  echo "== 代码/配置 =="
  local jars=0
  for f in "$REPO"/services/rag-java/rag-parent/*/target/*.jar; do [ -f "$f" ] && jars=$((jars+1)); done
  [ "$jars" -ge 6 ] && ok "业务 jar: $jars 个" || warn "业务 jar 只有 $jars 个（应 ≥6）"
  [ -f "$OUT/payload/db/gienrag.sql" ] && ok "业务库导出: $(du -sh "$OUT/payload/db/gienrag.sql" | cut -f1)" || warn "业务库导出缺失（pack 后才有）"
  [ -f "$OUT/payload/nacos/configs.json" ] && ok "Nacos 配置导出: $(grep -c dataId "$OUT/payload/nacos/configs.json" 2>/dev/null) 条" || warn "Nacos 配置未导出（pack 后才有）"
  [ -f "$REPO/frontend/plateform/dist/index.html" ] && ok "前端 dist: $(du -sh "$REPO/frontend/plateform/dist" | cut -f1)" || warn "前端 dist 缺失"
  [ -f "$R12/preview/app.py" ] && ok "Office 预览服务（源码 + 镜像定义）" || warn "Office 预览目录缺失"
  echo
  [ "$missing" -eq 0 ] && ok "清单完整（镜像与运行时资产齐备）" || die "缺少 $missing 项，无法离线安装"
}

cmd_pack() {
  mkdir -p "$OUT" || die "无法创建 $OUT"
  echo "== 1. 导出镜像（体积较大，耐心等）=="
  if [ ! -f "$OUT/images.tar" ]; then
    docker save -o "$OUT/images.tar" "${IMAGES[@]}" || die "docker save 失败"
    ok "images.tar $(du -sh "$OUT/images.tar" | cut -f1)"
  else ok "images.tar 已存在，跳过"; fi

  echo "== 2. 拷贝运行时资产与代码 =="
  local P="$OUT/payload"
  mkdir -p "$P/jars" "$P/conf" "$P/bin" "$P/systemd" "$P/frontend" "$P/docker" "$P/docs"
  cp "$REPO"/services/rag-java/rag-parent/*/target/*.jar "$P/jars/" 2>/dev/null
  cp -r "$R12/conf/." "$P/conf/" 2>/dev/null
  cp "$R12/bin/up.sh" "$R12/bin/r12ctl.sh" "$R12/bin/offline-kit.sh" "$P/bin/" 2>/dev/null
  cp "$R12/systemd/"*.service "$P/systemd/" 2>/dev/null
  cp -r "$R12/preview" "$P/preview" 2>/dev/null
  cp -r "$R12/graph" "$P/graph" 2>/dev/null
  cp "$R12/docker/docker-compose.infra.yml" "$P/docker/" 2>/dev/null
  cp -r "$REPO/frontend/plateform/dist" "$P/frontend/dist" 2>/dev/null
  cp "$REPO/docs/r12/R13-STATUS.md" "$P/docs/" 2>/dev/null
  ok "payload 代码/配置已就绪"

  echo "== 2.1 导出数据库与 Nacos 配置（离线重建的关键）=="
  mkdir -p "$P/db" "$P/nacos"
  if docker ps --format '{{.Names}}' | grep -qx 'r12-mysql'; then
    docker exec r12-mysql mysqldump -uroot -p"${MYSQL_ROOT_PASSWORD:-R12r00t#2026local}" \
      --single-transaction --routines --triggers --databases gienrag 2>/dev/null > "$P/db/gienrag.sql" \
      && ok "db/gienrag.sql $(du -sh "$P/db/gienrag.sql" | cut -f1)"
  else warn "r12-mysql 未运行，跳过业务库导出"; fi
  "$PY" - "$P/nacos/configs.json" <<'PYEOF' && ok "nacos/configs.json 已导出"
import json, sys, urllib.request, urllib.parse
base="http://127.0.0.1:18848"; out=[]
for page in range(1,6):
    q=urllib.parse.urlencode({"search":"accurate","pageNo":page,"pageSize":100,"tenant":"","group":"","dataId":""})
    r=json.load(urllib.request.urlopen(f"{base}/nacos/v1/cs/configs?{q}", timeout=20))
    items=r.get("pageItems") or []
    for it in items:
        out.append({"dataId":it["dataId"],"group":it.get("group") or "DEFAULT_GROUP",
                    "type":it.get("type") or "yaml","content":it.get("content")})
    if len(items)<100: break
json.dump(out, open(sys.argv[1],"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"  [ok] Nacos 配置 {len(out)} 条")
PYEOF
  cp "$R12/bin/init-db.sh" "$R12/bin/init-nacos.sh" "$P/bin/" 2>/dev/null

  echo "== 3. 拷贝 venv 与模型 =="
  for d in "${VENV_DIRS[@]}"; do
    if [ -d "$R12/venvs/$d" ] && [ ! -d "$P/venvs/$d" ]; then
      mkdir -p "$P/venvs"; cp -a "$R12/venvs/$d" "$P/venvs/" && ok "venv $d $(du -sh "$P/venvs/$d" | cut -f1)"
    else warn "venv $d 跳过"; fi
  done
  for d in "${MODEL_DIRS[@]}"; do
    if [ -d "$R12/models/$d" ] && [ ! -d "$P/models/$d" ]; then
      mkdir -p "$P/models"; cp -a "$R12/models/$d" "$P/models/" && ok "model $d $(du -sh "$P/models/$d" | cut -f1)"
    else warn "model $d 跳过"; fi
  done

  echo "== 4. 生成校验和 =="
  ( cd "$OUT" && find payload -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS 2>/dev/null; sha256sum images.tar >> SHA256SUMS )
  ok "SHA256SUMS $(wc -l < "$OUT/SHA256SUMS") 行"

  echo "== 5. 写安装说明 =="
  cat > "$OUT/INSTALL-OFFLINE.md" <<'EOF'
# R13 离线安装（禁外网）

前提：目标机已有 Docker（含 compose 插件）、bash、systemd --user。

1) 导入镜像
   docker load -i images.tar

2) 校验完整性（不联网）
   cd payload && sha256sum -c ../SHA256SUMS --ignore-missing

3) 落盘（示例路径，按目标机调整）
   /opt/r12/{jars,conf,bin,systemd,preview,graph,docker,frontend,venvs,models}

4) 恢复 Python 虚拟环境
   venv 内的 bin/python 是符号链接，若目标机 python 路径不同：
     python3 -m venv --upgrade <venv>
   或直接用同版本解释器重装 requirements（venv 内 site-packages 已随包拷贝）

5) 初始化数据库与配置（离线重建的关键）
   /opt/r12/bin/init-db.sh /opt/r12/db/gienrag.sql
   /opt/r12/bin/init-nacos.sh /opt/r12/nacos/configs.json

6) 起容器（基础设施）
   cd /opt/r12/docker && docker compose -f docker-compose.infra.yml --env-file /opt/r12/.env up -d

7) 起业务与算法（按依赖顺序）
   /opt/r12/bin/up.sh up

8) 自检
   /opt/r12/bin/up.sh verify
   预期：18088/8088/18095/19200 全 200，MinIO 匿名 GET 403

9) 无外网冒烟（可选）
   /opt/r12/bin/offline-kit.sh smoke
EOF
  ok "INSTALL-OFFLINE.md"
  echo
  ok "离线包就绪：$OUT（$(du -sh "$OUT" | cut -f1)）"
}

cmd_verify() {
  local bad=0
  if [ -f "$OUT/SHA256SUMS" ]; then
    ( cd "$OUT" && sha256sum -c SHA256SUMS --quiet 2>/dev/null ) && ok "SHA256 全部匹配" || { warn "SHA256 有不匹配项"; bad=$((bad+1)); }
  else warn "未找到 SHA256SUMS（先执行 pack）"; fi

  for i in "${IMAGES[@]}"; do
    docker images --format '{{.Repository}}:{{.Tag}}' | grep -qx "$i" || { warn "镜像缺失: $i"; bad=$((bad+1)); }
  done
  [ "$bad" -eq 0 ] && ok "镜像齐备（${#IMAGES[@]} 个）"

  for d in "${VENV_DIRS[@]}"; do [ -x "$R12/venvs/$d/bin/python" ] && ok "venv $d 可执行" || { warn "venv $d 不可执行"; bad=$((bad+1)); }; done
  for d in "${MODEL_DIRS[@]}"; do [ -d "$R12/models/$d" ] && ok "model $d 存在" || { warn "model $d 缺失"; bad=$((bad+1)); }; done

  "$PY" - <<'PYEOF' || bad=$((bad+1))
import glob, sys, yaml
files = glob.glob("/home/szf/data/dev/llmke-r12/platform/r12/conf/*/application-r12.yml")
bad = [f for f in files if not (lambda: (yaml.safe_load(open(f, encoding="utf-8")), True)[1])()]
print(f"  [ok] 配置 YAML 可解析: {len(files)-len(bad)}/{len(files)}")
sys.exit(1 if bad else 0)
PYEOF

  [ "$bad" -eq 0 ] && ok "离线校验通过" || die "离线校验失败项: $bad"
}

cmd_smoke() {
  echo "== 无外网冒烟（--network none）=="
  docker rm -f r12-smoke-fe >/dev/null 2>&1
  docker run -d --name r12-smoke-fe --network none \
    -v "$REPO/frontend/plateform/dist:/usr/share/nginx/html/rag:ro" \
    -v "$REPO/frontend/plateform/nginx/r12-18088.conf:/etc/nginx/conf.d/default.conf:ro" \
    nginx:alpine >/dev/null 2>&1 || die "前端容器启动失败"
  sleep 4
  local code
  code=$(docker exec r12-smoke-fe sh -c 'wget -q -O /dev/null -S http://127.0.0.1:18088/ 2>&1' | grep -oE 'HTTP/[0-9.]+ [0-9]{3}' | awk '{print $2}' | head -1)
  if [ "$code" = "200" ]; then ok "前端静态产物在无外网容器内可服务（18088 → 200）"; else warn "前端冒烟返回 ${code:-无响应}"; fi
  docker rm -f r12-smoke-fe >/dev/null 2>&1

  docker rm -f r12-smoke-pv >/dev/null 2>&1
  docker run -d --name r12-smoke-pv --network none r12/preview-office:r13 >/dev/null 2>&1 || die "预览容器启动失败"
  sleep 6
  local h
  h=$(docker exec r12-smoke-pv sh -c 'python -c "import urllib.request;print(urllib.request.urlopen(\"http://127.0.0.1:18095/healthz\",timeout=5).status)"' 2>/dev/null | tr -d '\r')
  [ "$h" = "200" ] && ok "Office 预览服务在无外网容器内健康（200）" || warn "预览冒烟返回 ${h:-无响应}"
  docker rm -f r12-smoke-pv >/dev/null 2>&1
}

case "${1:-manifest}" in
  manifest) cmd_manifest ;;
  pack)     cmd_pack ;;
  verify)   cmd_verify ;;
  smoke)    cmd_smoke ;;
  *) echo "用法: $0 {manifest|pack|verify|smoke}"; exit 2 ;;
esac
