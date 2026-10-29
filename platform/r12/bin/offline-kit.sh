#!/usr/bin/env bash
# R13 离线安装工具：盘点 / 打包 / 校验 / 无外网冒烟
# 用法: offline-kit.sh {manifest|pack|verify|smoke}
#
# 设计原则：
#   - 离线安装的"真相"是清单：镜像 + 模型 + Python venv + jar + 源码 + 前端产物 + 配置 + 运行脚本
#   - pack 产出一个可拷贝的目录（images.tar + payload + SHA256SUMS + INSTALL-OFFLINE.md）
#   - verify 在没有外网的机器上也能跑（只做本地校验，不访问任何网络）
#     verify 的每一项都必须是"缺失即失败"，不允许出现 0 个文件也报 [ok] 的假绿
#   - smoke 用 --network none 起容器，证明静态产物/预览服务不依赖外网
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$R12/../.." && pwd)"
OUT="${OUT:-$R12/dist/offline}"
# PACK_SCOPE=full（默认，运行包+源码）/ src（只出源码与离线构建材料，用于快速验证与源码交付）
PACK_SCOPE="${PACK_SCOPE:-full}"
# 源码落地根：构建机上就是仓库根；目标机上由 install-paths.sh 放到 <前缀>/src
SRC_ROOT="${R12_SRC_ROOT:-}"
if [ -z "$SRC_ROOT" ]; then
  if [ -d "$R12/src" ]; then SRC_ROOT="$R12/src"; else SRC_ROOT="$REPO"; fi
fi
PY="$R12/venvs/parse/bin/python"
[ -x "$PY" ] || PY="$(command -v python3 2>/dev/null || true)"

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1"; exit 1; }
# R14-SEC：口令只从环境变量或包内 .env 取，不在公开仓库写死默认值。
R12_ENV_FILE="${R12_ENV_FILE:-$R12/.env}"
ROOT_PW="${R12_MYSQL_ROOT_PASSWORD:-${MYSQL_ROOT_PASSWORD:-}}"
if [ -z "$ROOT_PW" ] && [ -f "$R12_ENV_FILE" ]; then
  ROOT_PW=$(grep -hE '^(R12_MYSQL_ROOT_PASSWORD|MYSQL_ROOT_PASSWORD)=' "$R12_ENV_FILE" | head -1 | sed 's/^[^=]*=//' | tr -d '\r')
fi

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
VENV_DIRS=(parse alg graph models)
SERVICES=(rag-auth-service rag-index-service rag-qa-service rag-gateway sensitive-words-service rag-graph-service)
# 算法侧源码目录（Python 服务直接从源码目录启动，不打 wheel，必须随包）
ALG_SRC_DIRS=(alg_doc_parse_service index_data_service alg_retrieval_service alg_llm_inference_service)

# 打包/校验共用的"必需文件"清单（相对安装前缀）
REQUIRED_FILES=(
  "bin/up.sh" "bin/r12ctl.sh" "bin/offline-kit.sh" "bin/init-db.sh" "bin/init-nacos.sh" "bin/install-paths.sh" "bin/check-bind.sh"
  # R14-F07：自愈与暴露面门禁脚本必须随包（否则目标机装完没有自愈）
  "bin/r12-watchdog.sh" "bin/r12-wait-ready.sh" "bin/es-single-node.sh"
  "bin/check-exposure.sh" "bin/offline-build-manifest.py" "bin/check-endpoints-sync.py"
  "bin/init-endpoints.sh" "bin/check-units.sh" "bin/gates-selftest.sh" "bin/boot-timing.sh"
  "run/algctl.sh" "run/doc-parse.env"
  "models/start-all.sh"
  "systemd/r12.target" "systemd/r12-alg.service" "systemd/r12-docparse.service" "systemd/r12-graphsvc.service"
  "systemd/r12-java@.service" "systemd/r12-models.service" "systemd/doc-parse.env"
  "systemd/r12-watchdog.service" "systemd/r12-watchdog.timer"
  "docker/docker-compose.infra.yml" "docker/rocketmq/broker.conf"
  "frontend/nginx/r12-18088.conf"
  "frontend/dist/index.html"
  "db/gienrag.sql" "nacos/configs.json"
  ".env.template"
  # R14-F06：源码与离线构建材料（运行包与源码复建是两件事，都要在包里点名）
  "src-build/services/rag-java/rag-parent/pom.xml"
  "src-build/frontend/plateform/package.json"
  "src-build/frontend/plateform/package-lock.json"
  "src-build/build/BUILD-OFFLINE.md"
  "src-build/build/OFFLINE-BUILD-MANIFEST.tsv"
  "src-build/build/settings-r12.xml"
)
REQUIRED_DIRS=(
  "conf" "graph" "preview" "jars" "log4j2" "models" "venvs"
  "src/services/rag-alg/alg_doc_parse_service"
  # R14-F06：Java 与前端**源码**（不是只有 jar/dist）
  "src-build/services/rag-java/rag-parent/rag-gateway/src"
  "src-build/services/rag-java/rag-parent/rag-index-service/src"
  "src-build/frontend/plateform/src"
)

collect_payload() {
  # 打印 payload 相对路径清单（每行一个），供 manifest/verify/pack 共用
  echo "jars"
  echo "conf"
  echo "bin/up.sh"; echo "bin/r12ctl.sh"; echo "bin/offline-kit.sh"
  echo "bin/init-db.sh"; echo "bin/init-nacos.sh"; echo "bin/install-paths.sh"; echo "bin/check-bind.sh"
  echo "run/algctl.sh"; echo "run/doc-parse.env"
  echo "models/start-all.sh"
  echo "log4j2"
  echo "systemd"
  echo "preview"
  echo "graph"
  echo "docker"
  echo "frontend/dist"; echo "frontend/nginx"
  echo "src/services/rag-alg"
  echo "db"
  echo "nacos"
  echo ".env.template"
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
  for d in "${VENV_DIRS[@]}"; do
    [ -x "$R12/venvs/$d/bin/python" ] && printf '  [ok]   venvs/%-52s %s\n' "$d" "$(du -sh "$R12/venvs/$d" 2>/dev/null | cut -f1)" || printf '  [warn] venvs/%s 缺失（该侧服务无法启动）\n' "$d"
  done
  echo "== 源码与离线构建材料（F06）=="
  local sb_ok=0 sb_miss=0
  for p in "src-build/services/rag-java/rag-parent/pom.xml" "src-build/frontend/plateform/package.json" \
           "src-build/frontend/plateform/package-lock.json" "src-build/frontend/plateform/src" \
           "src-build/build/BUILD-OFFLINE.md" "src-build/build/OFFLINE-BUILD-MANIFEST.tsv" \
           "src-build/build/settings-r12.xml"; do
    if have "$p"; then printf '  [ok]   %s\n' "$p"; sb_ok=$((sb_ok+1))
    else printf '  [MISS] %s\n' "$p"; sb_miss=$((sb_miss+1)); fi
  done
  local fe_n; fe_n=$(ls "$SRC_ROOT/frontend/plateform/src" 2>/dev/null | wc -l)
  local jv_n; jv_n=$(find "$SRC_ROOT/services/rag-java" -name '*.java' 2>/dev/null | wc -l)
  printf '  [..]   前端 src 顶层 %s 项；Java 源文件 %s 个；node_modules 与 ~/.m2 按要求不入包\n' "$fe_n" "$jv_n"
  [ "$sb_miss" -eq 0 ] && ok "源码/构建材料齐备（$sb_ok 项）" || warn "源码/构建材料缺 $sb_miss 项（pack 时补齐）"

  echo "== 代码/配置 =="
  local jars=0
  for f in "$REPO"/services/rag-java/rag-parent/*/target/*.jar; do [ -f "$f" ] && jars=$((jars+1)); done
  [ "$jars" -ge 6 ] && ok "业务 jar: $jars 个" || warn "业务 jar 只有 $jars 个（应 ≥6）"
  local miss=0
  for f in "${REQUIRED_FILES[@]}"; do have "$f" || { warn "缺少 $f"; miss=$((miss+1)); }; done
  for d in "${REQUIRED_DIRS[@]}"; do have "$d" || { warn "缺少目录 $d"; miss=$((miss+1)); }; done
  [ "$miss" -eq 0 ] && ok "必需文件齐备（${#REQUIRED_FILES[@]} 项文件 / ${#REQUIRED_DIRS[@]} 项目录）" || warn "缺 $miss 项必需资产"
  echo
  [ "$missing" -eq 0 ] && ok "镜像与运行时资产齐备" || die "缺少 $missing 项运行时资产，无法离线安装"
  [ "$miss" -eq 0 ] || warn "注意：仍有必需文件缺失，pack 前请补齐（否则目标机必然装不起来）"
}

cmd_pack() {
  mkdir -p "$OUT" || die "无法创建 $OUT"
  if [ "$PACK_SCOPE" = "src" ]; then
    echo "== PACK_SCOPE=src：只出源码与离线构建材料（跳过镜像/venv/模型/DB 导出）=="
  fi
  echo "== 1. 导出镜像（体积较大，耐心等）=="
  if [ "$PACK_SCOPE" = "src" ]; then
    warn "PACK_SCOPE=src：跳过 docker save"
  elif [ ! -f "$OUT/images.tar" ]; then
    docker save -o "$OUT/images.tar" "${IMAGES[@]}" || die "docker save 失败"
    ok "images.tar $(du -sh "$OUT/images.tar" | cut -f1)"
  else ok "images.tar 已存在，跳过"; fi

  echo "== 2. 拷贝运行时资产与代码 =="
  local P="$OUT/payload"
  # 幂等拷贝：先删目标再拷，避免 cp -r 在已存在目录下产生 dist/dist、preview/preview 这类嵌套重复
  put() {  # put <源> <payload 相对路径>
    local s="$1" d="$P/$2"
    if [ ! -e "$s" ]; then warn "源不存在，跳过: $s"; return 0; fi
    mkdir -p "$(dirname "$d")"
    rm -rf "$d"
    cp -a "$s" "$d" || warn "拷贝失败: $s -> $d"
  }
  mkdir -p "$P/jars" "$P/bin" "$P/systemd" "$P/frontend" "$P/docker" "$P/docs" "$P/run" "$P/log4j2" "$P/models"
  if [ "$PACK_SCOPE" = "src" ]; then
    warn "PACK_SCOPE=src：跳过 jar 拷贝（jar 属运行包）"
  else
    cp "$REPO"/services/rag-java/rag-parent/*/target/*.jar "$P/jars/" 2>/dev/null
  fi
  put "$R12/conf" "conf"
  for f in up.sh r12ctl.sh offline-kit.sh init-db.sh init-nacos.sh install-paths.sh check-bind.sh \
           r12-watchdog.sh r12-wait-ready.sh es-single-node.sh check-exposure.sh offline-build-manifest.py \
           init-endpoints.sh check-units.sh gates-selftest.sh boot-timing.sh check-endpoints-sync.py \
           recover-stuck-tasks.sh r12-change.sh r12-kill-port.sh pack-verify.sh; do
    [ -f "$R12/bin/$f" ] && cp "$R12/bin/$f" "$P/bin/" || warn "bin/$f 不存在"
  done
  chmod +x "$P/bin/"*.sh "$P/bin/"*.py 2>/dev/null
  for f in algctl.sh doc-parse.env; do
    [ -f "$R12/run/$f" ] && cp "$R12/run/$f" "$P/run/" || warn "run/$f 不存在（up.sh 第 3/4 步会失败）"
  done
  if [ -f "$R12/models/start-all.sh" ]; then cp "$R12/models/start-all.sh" "$P/models/"
  else warn "models/start-all.sh 不存在（up.sh 第 2 步会失败）"; fi
  put "$R12/log4j2" "log4j2"
  put "$R12/systemd" "systemd"
  put "$R12/preview" "preview"
  put "$R12/graph" "graph"
  put "$R12/docker" "docker"     # 含 rocketmq/broker.conf，compose 有 bind mount 依赖
  put "$SRC_ROOT/frontend/plateform/dist" "frontend/dist"
  put "$SRC_ROOT/frontend/plateform/nginx" "frontend/nginx"
  # 算法侧源码：Python 服务直接从源码目录 run，必须随包
  for d in "${ALG_SRC_DIRS[@]}"; do
    if [ -d "$SRC_ROOT/services/rag-alg/$d" ]; then
      mkdir -p "$P/src/services/rag-alg"
      rm -rf "$P/src/services/rag-alg/$d"
      cp -a "$SRC_ROOT/services/rag-alg/$d" "$P/src/services/rag-alg/$d"
    else warn "缺源码 services/rag-alg/$d"; fi
  done
  cp "$SRC_ROOT/docs/r12/R13-STATUS.md" "$P/docs/" 2>/dev/null || true
  # 附加 SQL（如 r14_group_audit.sql）：随包但不自动执行——本轮 group 审计只留日志、不建表
  if [ -d "$R12/sql" ] && ls "$R12/sql"/*.sql >/dev/null 2>&1; then
    mkdir -p "$P/sql"; cp "$R12/sql"/*.sql "$P/sql/" && ok "附加 SQL: $(ls "$R12/sql"/*.sql | xargs -n1 basename | paste -sd, -)（不自动执行）"
  fi
  ok "payload 代码/配置已就绪"

  if [ "$PACK_SCOPE" != "src" ]; then
  echo "== 2.1 导出数据库与 Nacos 配置（离线重建的关键）=="
  mkdir -p "$P/db" "$P/nacos"
  # R14：db/gienrag.sql 已被 C 打过补丁（search_config 默认助手唯一函数索引 uk_search_config_default
  # + id=10 is_default 归一），**默认沿用已有文件，不重新导出覆盖**；需要重导时必须显式 FORCE_DB_DUMP=1。
  if [ -s "$P/db/gienrag.sql" ] && [ "${FORCE_DB_DUMP:-0}" != "1" ]; then
    if grep -q 'uk_search_config_default' "$P/db/gienrag.sql"; then
      ok "沿用已有 db/gienrag.sql（含 uk_search_config_default 补丁，$(du -sh "$P/db/gienrag.sql" | cut -f1)）"
    else
      warn "沿用已有 db/gienrag.sql，但**缺少** uk_search_config_default 补丁（C 的默认助手唯一性修复会丢）"
    fi
  elif docker ps --format '{{.Names}}' | grep -qx 'r12-mysql'; then
    [ -n "${ROOT_PW:-}" ] || die "缺少 MySQL root 口令：请设置 R12_MYSQL_ROOT_PASSWORD 或在 $R12_ENV_FILE 提供"
    docker exec r12-mysql mysqldump -uroot -p"$ROOT_PW" \
      --single-transaction --routines --triggers --databases gienrag 2>/dev/null > "$P/db/gienrag.sql" \
      && ok "db/gienrag.sql $(du -sh "$P/db/gienrag.sql" | cut -f1)"
    if grep -q 'uk_search_config_default' "$P/db/gienrag.sql"; then
      ok "重导出结果含 uk_search_config_default"
    else
      warn "重导出的 dump 缺少 uk_search_config_default：线上库可能没打 C 的补丁，离线包会退化成无唯一约束"
    fi
  else warn "r12-mysql 未运行，跳过业务库导出"; fi
  if [ -n "$PY" ] && [ -x "$PY" ]; then
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
  else warn "无可用 python，跳过 Nacos 配置导出"; fi
  else warn "PACK_SCOPE=src：跳过 DB / Nacos 数据导出"; fi

  echo "== 2.2 环境变量模板（不入包真实口令）=="
  local tpl="$R12/offline/templates/env.template"
  [ -f "$tpl" ] || tpl="$R12/.env.example"
  if [ -f "$tpl" ]; then cp "$tpl" "$P/.env.template" && ok ".env.template（口令为占位符）"
  else warn "缺 .env.template 与 .env.example —— 目标机 compose --env-file 会直接失败"; fi
  [ -f "$P/.env" ] && { warn "payload 里存在 .env，已删除（口令不得入包）"; rm -f "$P/.env"; }

  echo "== 2.3 源码与离线构建材料（F06）=="
  local SB="$P/src-build"
  mkdir -p "$SB/build"
  # Java 源码：剔除 target/ 与 *.class（体积从 ~1G 降到 ~16M）
  if [ -d "$SRC_ROOT/services/rag-java" ]; then
    mkdir -p "$SB/services"; rm -rf "$SB/services/rag-java"
    ( cd "$SRC_ROOT/services" && tar -cf - --exclude='target' --exclude='*.class' rag-java )       | ( cd "$SB/services" && tar -xf - ) \
      && ok "src-build/services/rag-java $(du -sh "$SB/services/rag-java" | cut -f1)（已排除 target/ 与 *.class）" \
      || warn "Java 源码拷贝失败"
  else warn "缺 $SRC_ROOT/services/rag-java（Java 源码不入包）"; fi
  # 前端源码与构建配置（不含 node_modules，1.4G）
  local FE="$SRC_ROOT/frontend/plateform" fe_ok=0
  mkdir -p "$SB/frontend/plateform"
  for item in src public package.json package-lock.json pnpm-lock.yaml yarn.lock index.html \
              custom.d.ts postcss.config.js tailwind.config.cjs vite.config.ts vite.config.js \
              tsconfig.json tsconfig.node.json .env.production .env.development; do
    [ -e "$FE/$item" ] && { cp -a "$FE/$item" "$SB/frontend/plateform/"; fe_ok=$((fe_ok+1)); }
  done
  [ "$fe_ok" -gt 0 ] && ok "src-build/frontend/plateform $(du -sh "$SB/frontend/plateform" | cut -f1)（$fe_ok 项，不含 node_modules）" \
    || warn "前端源码未纳入（检查 $FE）"
  # 构建说明 + 依赖获取脚本 + 镜像 settings
  for f in BUILD-OFFLINE.md resolve-maven-offline.sh resolve-npm-offline.sh resolve-python-offline.sh settings-r12.xml; do
    if [ -f "$R12/offline/templates/$f" ]; then cp "$R12/offline/templates/$f" "$SB/build/"; else warn "缺 offline/templates/$f"; fi
  done
  chmod +x "$SB/build/"*.sh 2>/dev/null
  # 离线构建清单（Java 运行时坐标+sha256 / lock / requirements）
  if [ -n "$PY" ] && [ -x "$PY" ] && [ -f "$R12/bin/offline-build-manifest.py" ]; then
    "$PY" "$R12/bin/offline-build-manifest.py" "$SRC_ROOT" "$SB/build/OFFLINE-BUILD-MANIFEST.tsv" \
      && ok "build/OFFLINE-BUILD-MANIFEST.tsv $(wc -l < "$SB/build/OFFLINE-BUILD-MANIFEST.tsv") 行" \
      || warn "离线构建清单生成失败"
  else warn "无可用 python，跳过 OFFLINE-BUILD-MANIFEST.tsv"; fi
  # 明确声明什么都没塞进去（避免"以为包里带了 node_modules / .m2"）
  cat > "$SB/README-NOT-INCLUDED.md" <<'NOTINC'
# 本目录**不含**以下内容（体积原因）

| 未包含 | 体积 | 复现方式 |
|---|---|---|
| `frontend/plateform/node_modules/` | ~1.4G | `build/resolve-npm-offline.sh` + `package-lock.json` |
| `~/.m2/repository/` | 视环境 | `build/resolve-maven-offline.sh` + `OFFLINE-BUILD-MANIFEST.tsv` 坐标 |
| Python wheel 缓存 | 视环境 | `build/resolve-python-offline.sh` + `requirements.txt` |

每一项都给了**清单 / 校验和 / 获取脚本**，不是"缺了就装不了"。
详见 `build/BUILD-OFFLINE.md`。
NOTINC
  ok "src-build/README-NOT-INCLUDED.md"

  echo "== 3. 拷贝 venv 与模型 =="
  if [ "$PACK_SCOPE" = "src" ]; then
    warn "PACK_SCOPE=src：跳过 venv 与模型"
  else
  for d in "${VENV_DIRS[@]}"; do
    if [ -d "$R12/venvs/$d" ]; then
      mkdir -p "$P/venvs"; rm -rf "$P/venvs/$d"
      cp -a "$R12/venvs/$d" "$P/venvs/" && ok "venv $d $(du -sh "$P/venvs/$d" | cut -f1)"
    else warn "venv $d 不存在（对应服务无法启动）"; fi
  done
  for d in "${MODEL_DIRS[@]}"; do
    if [ -d "$R12/models/$d" ] && [ ! -d "$P/models/$d" ]; then
      mkdir -p "$P/models"; cp -a "$R12/models/$d" "$P/models/" && ok "model $d $(du -sh "$P/models/$d" | cut -f1)"
    else warn "model $d 跳过"; fi
  done
  fi

  echo "== 4. 生成校验和 =="
  ( cd "$OUT" && find payload -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS 2>/dev/null
    [ -f images.tar ] && sha256sum images.tar >> SHA256SUMS )
  ok "SHA256SUMS $(wc -l < "$OUT/SHA256SUMS") 行"

  echo "== 5. 写安装说明 =="
  cat > "$OUT/INSTALL-OFFLINE.md" <<'EOF'
# R14 离线安装（禁外网）

前提：目标机已有 Docker（含 compose 插件）、bash、curl、python3(3.10/3.11)、可选 systemd --user。
说明：本文件由 `bin/offline-kit.sh pack` 生成；示例前缀 /opt/r12，按目标机调整。

**顺序口径（R14 修正）**：校验 → 镜像 → 环境变量 → 路径适配 → **先起基础设施并等就绪** →
再初始化 DB / 发布 Nacos 配置 → ES 副本治理 → 模型 → 算法 → 业务 → 前端 → 验收。
R13 文档把"初始化 DB/Nacos"写在"起容器"之前，而 `init-db.sh` 明确要求 `r12-mysql` 容器已在运行，
顺序倒置会让装机在第一步就失败 —— 本版已改正。

0) 放置安装包
   mkdir -p /opt/r12 && cp -a payload/. /opt/r12/
   chmod +x /opt/r12/bin/*.sh /opt/r12/run/*.sh /opt/r12/models/*.sh /opt/r12/src-build/build/*.sh

1) 导入镜像
   docker load -i images.tar

2) 校验完整性（在"解压出来的 offline 目录"里执行，不是 payload/ 内部）
   cd <offline 目录> && sha256sum -c SHA256SUMS
   注意：禁止 `--ignore-missing`。SHA256SUMS 的路径带 payload/ 前缀，在 payload/ 内部执行会"未验证任何文件"。

3) 环境变量（缺 .env 时 compose --env-file 直接失败）
   cp /opt/r12/.env.template /opt/r12/.env && 编辑 4 项口令
   chmod 600 /opt/r12/.env

4) 路径适配（把构建机绝对路径改成本机前缀，幂等）
   /opt/r12/bin/install-paths.sh --prefix /opt/r12 --dry-run   # 先看要改什么
   /opt/r12/bin/install-paths.sh --prefix /opt/r12             # 正式改
   /opt/r12/bin/install-paths.sh --prefix /opt/r12 --check     # 期望：无残留

5) 起基础设施并**等就绪**（不是"起完就算"）
   cd /opt/r12/docker && docker compose -f docker-compose.infra.yml --env-file /opt/r12/.env up -d
   # 就绪判据（三条都要 200/成功，任一失败就停在这里排查，别继续往下装）
   curl -fsS http://127.0.0.1:18848/nacos/v1/console/health/readiness      # 期望 200
   docker exec r12-mysql mysqladmin ping -uroot -p"$R12_MYSQL_ROOT_PASSWORD"  # 期望 mysqld is alive
   curl -fsS http://127.0.0.1:19200/_cluster/health                        # 期望有 status 字段
   /opt/r12/bin/r12-wait-ready.sh nacos 300                                # 可选：脚本化等待

6) 初始化数据库（必须在第 5 步之后：init-db.sh 要求 r12-mysql 已在运行）
   /opt/r12/bin/init-db.sh /opt/r12/db/gienrag.sql
   幂等：库内已有业务表会跳过；如需重建先手工 drop database gienrag
   校验（失败即非零退出）：
     - 默认助手不变量：`select count(*) from search_config where is_default=1 and is_del=1` 必须 ≤1
     - 唯一索引 `uk_search_config_default` 必须存在（否则以后还能插出第二个默认助手）
     - 接口注册表补齐（init-endpoints.sh）在导入前后都会执行

7) 发布 Nacos 配置并**回读比对内容**（不能只比长度）
   /opt/r12/bin/init-nacos.sh /opt/r12/nacos/configs.json

7.1) 接口注册表补齐（网关按 interface_info 做接口级鉴权；缺行即 401/30021）
   /opt/r12/bin/init-endpoints.sh
   幂等；第 6 步 init-db.sh 末尾也会自动执行一次。新增 Java 端点时在脚本 ENDPOINTS 里加一行即可。

8) ES 单节点副本治理（幂等，必做）
   /opt/r12/bin/es-single-node.sh
   背景：单 data node 上 number_of_replicas=1 的副本永远无法分配 → 集群长期 yellow。
   该脚本把既有索引副本置 0 并注册新索引默认 0 副本模板，最后断言 green 且 unassigned=0。

9) 起模型 / 算法 / 业务（按依赖顺序，脚本内已串好）
   /opt/r12/bin/up.sh up
   # 依赖闸门已内置：算法等 Nacos readiness、图服务等 Nacos+Nebula、业务等 Nacos+MySQL+Redis

10) 前端（生产入口：nginx 容器 + 已构建 dist；**不要**在生产用 npm dev）
   docker run -d --name r12-fe --network host --restart unless-stopped \
     -v /opt/r12/frontend/dist:/usr/share/nginx/html/rag:ro \
     -v /opt/r12/frontend/nginx/r12-18088.conf:/etc/nginx/conf.d/default.conf:ro \
     nginx:alpine
   # 重要（R14 实测陷阱）：bind mount 钉的是**目录 inode**。若用"建新目录再 mv/rsync --delete"替换 dist，
   # 容器仍持有旧 inode，nginx 继续服务旧文件（表现为"构建了但页面没变"）。替换 dist 后必须：
   #   docker restart r12-fe
   # `up.sh verify` 有 must 断言比对"宿主 index.html 的入口 chunk 名 vs 18088 返回的"，
   # 不一致会直接失败并提示 restart。

11) 自检（**必需项失败即非零退出**；不允许"打印了一堆状态但退出 0"）
   /opt/r12/bin/up.sh verify ; echo "rc=$?"     # rc 必须为 0
   /opt/r12/bin/check-bind.sh --prefix /opt/r12 --expect-loopback ; echo "rc=$?"
   /opt/r12/bin/check-exposure.sh --expect-closed ; echo "rc=$?"
   说明：verify 分 must / warn 两级，must 项（前端 200、网关 200、ES 可读、MinIO 匿名 403、
   各算法端口在监听、模型端口在监听）任一失败即退出 1。

12) systemd --user 托管（含自愈看门狗）
   mkdir -p ~/.config/systemd/user && cp /opt/r12/systemd/*.service /opt/r12/systemd/*.timer /opt/r12/systemd/r12.target ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable r12.target          # 整栈唯一入口 -> default.target.wants/r12.target
   systemctl --user enable --now r12-watchdog.timer
   systemctl --user start r12.target           # 拉起 9 个服务单元
   # 校验：default.target.wants 下应只有 r12.target 一条 r12 条目（原为 11 条）
   systemctl --user list-dependencies default.target --no-pager | grep -c 'r12\.[a-z@.-]*service' || true
   # 看门狗 45s 巡检、连续 2 次判失才动作；维护停机时 touch /opt/r12/run/.maintenance
   # 看门狗故意不并入 r12.target：它是安全网，必须在整栈被停时仍能巡检与自愈。
   #
   # 为什么收敛到 target：R14 两次全栈中断（13:22 / 13:39）都是本机另一个自动化
   # 按字母序 stop/restart systemd user unit，dkws-skill 与 r12-* 出现在同一秒。
   # 收敛后外部按 unit 名逐个扫时不再逐个命中；但这只是"收敛入口"，不是"隔离边界"，
   # 按 r12-* 通配或遍历全部已加载 unit 仍会命中 —— 硬隔离需独立 system user 或独立主机。

13) 源码复建（与运行包分开验证，见 /opt/r12/src-build/build/BUILD-OFFLINE.md）
   包内不含 node_modules / ~/.m2 / wheel 缓存，但含：Java 与前端源码、三种 lock、
   Maven 内网 settings 模板、三个依赖获取脚本、OFFLINE-BUILD-MANIFEST.tsv（含 sha256）。

交付前置（需目标机运维配合，不阻塞门禁）：
  - 宿主若自带 MySQL（`/etc/mysql/mysql.conf.d/mysqld.cnf` 的 `bind-address=0.0.0.0`），
    请让运维把它绑回 `127.0.0.1` 并重启 mysql。本项目自己的 MySQL 是容器 r12-mysql -> 127.0.0.1:13306，
    不依赖宿主 3306；`check-exposure.sh` 会把宿主这类端口单列成"宿主其它软件（需 root 处置）"。

已知前置（不满足则第 9 步会失败）：
  - /opt/r12/src/services/rag-alg/* 必须存在（Python 服务直接跑源码）
  - /opt/r12/venvs/{parse,alg,graph,models} 的解释器需与包内 pyvenv.cfg 版本一致（3.11 / 3.10）
    venv 通常不可搬移（https://docs.python.org/3.11/library/venv.html ）：异构目标机请按
    src-build/build/BUILD-OFFLINE.md 用 wheel 重建，不要只改软链
  - docker/docker-compose.infra.yml 依赖 ./rocketmq/broker.conf 的 bind mount

安全前提（务必确认，否则等于不设防）：
  - 算法/解析/预览/图检索等内部服务（12340/18095/19526/19527/19529/19995/19996）**自身不做鉴权**，
    唯一收口在 Java 网关/控制器。它们应只绑 127.0.0.1：
    `/opt/r12/bin/check-bind.sh --prefix /opt/r12 --expect-loopback` 必须退出 0。
  - 对外只允许 8088（网关）/ 18088（前端）；数据面/管理面（MySQL 13306、ES 19200、MinIO 19000/19001、
    Nacos 18848、Redis 16379、Nebula 19669/19559/19779、RocketMQ 19876/10909/10911）必须仅回环，
    `check-exposure.sh --expect-closed` 必须退出 0。
  - 前提一：**单租户主机**。同机其他用户/租户进程可直接读到原文（回环不等于不可读）。
  - 前提二：**仅本机调用**。跨机访问必须加内网凭据或网络隔离，本包不提供该能力。

EOF
  ok "INSTALL-OFFLINE.md"
  echo
  ok "离线包就绪：$OUT（$(du -sh "$OUT" | cut -d' ' -f1)）"
}

# 判定某必需项在“安装前缀视角”下是否存在。
# 构建机（源仓）与目标机（prefix 布局）同一项的相对路径不同，这里做别名映射，
# 保证同一份清单在两边都能判真：目标机走 $R12/... 分支，构建机走别名分支。
have() {  # have <相对路径>
  local p="$1"
  [ -e "$R12/$p" ] && return 0
  [ -e "$SRC_ROOT/$p" ] && return 0
  [ -e "$REPO/$p" ] && return 0
  # pack 产物（db/nacos/jars 只在打包后存在于 payload 里）
  [ -e "$OUT/payload/$p" ] && return 0
  case "$p" in
    .env.template)
      [ -f "$R12/offline/templates/env.template" ] && return 0
      [ -f "$R12/.env.example" ] && return 0 ;;
    frontend/nginx/*)
      [ -f "$SRC_ROOT/frontend/plateform/${p#frontend/}" ] && return 0 ;;
    frontend/dist|frontend/dist/*)
      [ -e "$SRC_ROOT/frontend/plateform/${p#frontend/}" ] && return 0 ;;
    src/services/*)
      [ -e "$SRC_ROOT/${p#src/}" ] && return 0 ;;
    src-build/services/*)
      [ -e "$SRC_ROOT/${p#src-build/}" ] && return 0 ;;
    src-build/frontend/plateform/*)
      [ -e "$SRC_ROOT/frontend/plateform/${p#src-build/frontend/plateform/}" ] && return 0 ;;
    src-build/build/*)
      [ -f "$R12/offline/templates/$(basename "$p")" ] && return 0 ;;
  esac
  return 1
}

cmd_verify() {
  local bad=0
  echo "== 1. 完整性清单 =="
  if [ -f "$OUT/SHA256SUMS" ]; then
    ( cd "$OUT" && sha256sum -c SHA256SUMS --quiet 2>/dev/null ) && ok "SHA256 全部匹配" || { warn "SHA256 有不匹配项"; bad=$((bad+1)); }
  else warn "未找到 $OUT/SHA256SUMS（先执行 pack；目标机上应在 offline 目录里再校验一次）"; bad=$((bad+1)); fi

  echo "== 2. 镜像 =="
  local missimg=0
  for i in "${IMAGES[@]}"; do
    docker images --format '{{.Repository}}:{{.Tag}}' | grep -qx "$i" || { missimg=$((missimg+1)); }
  done
  [ "$missimg" -eq 0 ] && ok "镜像齐备（${#IMAGES[@]} 个）" || { warn "镜像缺失 $missimg/${#IMAGES[@]} 个（未 docker load？）"; bad=$((bad+1)); }

  echo "== 3. 必需文件与目录（缺一个就是装不起来）=="
  local miss=0 m
  for f in "${REQUIRED_FILES[@]}"; do
    have "$f" || { warn "缺文件: $f"; miss=$((miss+1)); }
  done
  for d in "${REQUIRED_DIRS[@]}"; do
    have "$d" || { warn "缺目录: $d"; miss=$((miss+1)); }
  done
  [ "$miss" -eq 0 ] && ok "必需项齐备（$((${#REQUIRED_FILES[@]}+${#REQUIRED_DIRS[@]})) 项）" || { bad=$((bad+1)); }

  echo "== 4. jar 与前端产物 =="
  # jar 可能在安装前缀 jars/、payload/jars/ 或构建机的 target/ 下，取最大者
  local jars=0 n
  for root in "$R12/jars" "$OUT/payload/jars"; do
    n=0; for f in "$root"/*.jar; do [ -f "$f" ] && n=$((n+1)); done
    [ "$n" -gt "$jars" ] && jars=$n
  done
  n=0; for f in "$REPO"/services/rag-java/rag-parent/*/target/*.jar; do [ -f "$f" ] && n=$((n+1)); done
  [ "$n" -gt "$jars" ] && jars=$n
  [ "$jars" -ge 12 ] && ok "jar $jars 个" || { warn "jar 只有 $jars 个（应 ≥12）"; bad=$((bad+1)); }
  local dist=""
  for c in "$R12/frontend/dist" "$SRC_ROOT/frontend/plateform/dist" "$REPO/frontend/plateform/dist"; do
    [ -f "$c/index.html" ] && { dist="$c"; break; }
  done
  if [ -n "$dist" ]; then
    local nidx; nidx=$(ls "$dist/assets" 2>/dev/null | wc -l)
    if [ "$nidx" -ge 10 ]; then ok "前端 dist 完整：index.html + assets/$nidx 项（$dist）"
    else warn "前端 dist 可疑：assets 仅 $nidx 项（$dist）"; bad=$((bad+1)); fi
    if [ -d "$dist/dist" ]; then warn "前端 dist 存在嵌套子目录 dist/（打包非幂等残留，会白占体积）"; bad=$((bad+1)); fi
  else warn "前端 dist 缺失（index.html 找不到）"; bad=$((bad+1)); fi

  echo "== 4.1 preview 启动结构（py_compile 抓不到的坑）=="
  # 真实事故：把 uvicorn.run(...) 顶到第 0 列（脱离 if __name__ 块），而 import uvicorn
  # 是块内局部导入 → 模块级执行时 NameError，容器无限重启；py_compile/compileall 全部通过。
  local pv="" pvbad=0
  for c in "$R12/preview/app.py" "$OUT/payload/preview/app.py"; do
    [ -f "$c" ] || continue
    pv="$c"
    if grep -qE '^uvicorn\.run\(' "$c" && grep -qE '^[[:space:]]+import uvicorn' "$c"; then
      warn "${c#$R12/}: uvicorn.run 在模块级但 import uvicorn 在块内 → 启动即 NameError（容器会 crash-loop）"; pvbad=1
    elif [ -n "$(awk '/^uvicorn\.run\(/{print; exit}' "$c")" ]; then
      warn "${c#$R12/}: uvicorn.run 出现在第 0 列（疑似缩进丢失）"; pvbad=1
    fi
  done
  [ -z "$pv" ] && info "未找到 preview/app.py（跳过）"
  [ "$pvbad" -eq 0 ] && [ -n "$pv" ] && ok "preview/app.py 启动结构正常（uvicorn.run 在 __main__ 块内）"
  [ "$pvbad" -gt 0 ] && bad=$((bad+1))

  echo "== 5. venv 与模型 =="
  for d in "${VENV_DIRS[@]}"; do
    if [ -x "$R12/venvs/$d/bin/python" ]; then
      if "$R12/venvs/$d/bin/python" -V >/dev/null 2>&1; then ok "venv $d 可执行（$("$R12/venvs/$d/bin/python" -V 2>&1)）"
      else warn "venv $d 解释器不可用（软链指向构建机绝对路径？目标机需跑 install-paths.sh）"; bad=$((bad+1)); fi
    else warn "venv $d 缺失"; bad=$((bad+1)); fi
  done
  for d in "${MODEL_DIRS[@]}"; do [ -d "$R12/models/$d" ] && ok "model $d 存在" || { warn "model $d 缺失"; bad=$((bad+1)); }; done

  echo "== 6. .env 与运行目录 =="
  if [ -f "$R12/.env" ]; then
    grep -q 'CHANGE_ME' "$R12/.env" 2>/dev/null && { warn ".env 仍含 CHANGE_ME 占位符"; bad=$((bad+1)); } || ok ".env 已配置"
  elif [ -f "$R12/.env.template" ]; then
    warn ".env 缺失（需 cp .env.template .env 并填口令，否则 compose 起不来）"; bad=$((bad+1))
  else warn ".env 与 .env.template 都缺失"; bad=$((bad+1)); fi
  local dirc=0
  for d in logs run logs/java logs/parse; do
    if [ -d "$R12/$d" ] || mkdir -p "$R12/$d" 2>/dev/null; then dirc=$((dirc+1)); fi
  done
  [ "$dirc" -eq 4 ] && ok "logs/run/pid 目录可创建" || { warn "运行目录不可创建（$dirc/4）——检查前缀写权限"; bad=$((bad+1)); }

  echo "== 7. 配置可解析 =="
  local ymls=0 ybad=0
  for f in "$R12"/conf/*/application-r12.yml; do [ -f "$f" ] && ymls=$((ymls+1)); done
  if [ "$ymls" -eq 0 ]; then warn "没找到 conf/*/application-r12.yml（路径不对或包不全）"; bad=$((bad+1))
  elif [ -n "$PY" ] && [ -x "$PY" ]; then
    "$PY" - "$R12/conf" <<'PYEOF' || ybad=1
import glob, sys, yaml
root = sys.argv[1]
files = glob.glob(f"{root}/*/application-r12.yml")
bad = []
for f in files:
    try: yaml.safe_load(open(f, encoding="utf-8"))
    except Exception as e: bad.append((f, e))
print(f"  [ok] 配置 YAML 可解析: {len(files)-len(bad)}/{len(files)}")
for f, e in bad: print(f"  [!!] {f}: {e}")
sys.exit(1 if bad or not files else 0)
PYEOF
    [ "$ybad" -eq 0 ] && ok "配置解析通过（$ymls 个）" || { warn "配置解析失败"; bad=$((bad+1)); }
  else warn "无可用 python，跳过 YAML 解析（$ymls 个文件未验证）"; fi

  echo "== 8. 可移植性（构建机绝对路径残留）=="
  # 构建机上这些文件本来就写着构建机路径（pack 后由 install-paths.sh 改写），
  # 所以只在“目标机模式”下把残留算失败，构建机上只做提示。
  local resid=0 f2 on_build=0
  [ "$R12" = "$REPO/platform/r12" ] && on_build=1
  for f2 in "$R12"/systemd/*.service "$R12"/systemd/*.env "$R12"/run/*.env "$R12"/nacos/configs.json; do
    [ -f "$f2" ] || continue
    if grep -qE '/(home|Users)/[A-Za-z0-9._-]+/' "$f2" 2>/dev/null; then
      resid=$((resid+1))
      if [ "$on_build" = 1 ]; then printf '  [..] 构建机路径（预期）: %s\n' "${f2#$R12/}"
      else warn "残留本机路径: ${f2#$R12/}（执行 install-paths.sh 修）"; fi
    fi
  done
  # 算法服务的 Nacos 本地快照也会被服务在“配置中心不可达”时回读，同样不能带构建机路径
  if [ -d "$R12/src" ]; then
    while IFS= read -r f3; do
      [ -f "$f3" ] || continue
      if grep -qE '/(home|Users)/[A-Za-z0-9._-]+/' "$f3" 2>/dev/null; then
        resid=$((resid+1))
        if [ "$on_build" = 1 ]; then printf '  [..] 构建机路径（预期·快照）: %s\n' "${f3#$R12/}"
        else warn "残留本机路径（Nacos 快照）: ${f3#$R12/}（执行 install-paths.sh 修）"; fi
      fi
    done < <(find "$R12/src" -path '*/nacos-data/snapshot/*' -type f 2>/dev/null)
  fi
  if [ "$resid" -eq 0 ]; then ok "无构建机绝对路径残留"
  elif [ "$on_build" = 1 ]; then warn "构建机模式：$resid 个文件含构建机路径（打包后由 install-paths.sh 改写，目标机不算通过）"
  else warn "共 $resid 个文件残留"; bad=$((bad+1)); fi

  echo "== 9. 监听面基线（提示项，不计失败；由安全侧定夺）=="
  # 这 5 个内部数据面端口的绑定地址由 Nacos 配置内容决定（不是代码、不是 compose），
  # 而离线包会把这些配置原样发布到目标机 —— 打包时把暴露面一起带过去。
  local cfgjson=""
  for c in "$R12/nacos/configs.json" "$OUT/payload/nacos/configs.json"; do [ -f "$c" ] && { cfgjson="$c"; break; }; done
  if [ -n "$cfgjson" ] && [ -n "$PY" ] && [ -x "$PY" ]; then
    "$PY" - "$cfgjson" <<'PYEOF'
import json, sys
# dataId -> (行号, 服务, 端口, 面)：端口枚举与 qa-authz R17 一致
KNOWN = {
    ("alg_doc_config_py", 3):      ("doc-parse", 12340, "写入面"),
    ("index_data_config_py", 7):   ("index_vector", 19526, "写入面"),
    ("index_data_config_py", 37):  ("index_fulltext", 19527, "写入面"),
    ("alg_retrieval_config_py", 7): ("alg_retrieval", 19995, "读"),
    ("alg_llm_config_py", 6):      ("llm_open_chat", 19996, "推理"),
    ("index_graph_config_py", 4):  ("index_graph", 19529, "读"),
}
try:
    items = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    # 配置导出损坏不该让 verify 抛 traceback（既难读，也会截断后面的检查）
    print(f"  [!!] {sys.argv[1]} 不是合法 JSON（{type(e).__name__}），跳过监听面盘点")
    sys.exit(0)
hits = []
for it in items:
    for i, line in enumerate((it.get("content") or "").splitlines(), 1):
        s = line.strip()
        if s.startswith("host:") and "0.0.0.0" in s:
            svc, port, face = KNOWN.get((it["dataId"], i), ("?", "?", "?"))
            hits.append((it["dataId"], i, svc, port, face))
if hits:
    for d, i, svc, port, face in hits:
        print(f"  [..] {d} L{i} -> {port}({svc}, {face}) host: 0.0.0.0（对外可达；如需仅本机改 127.0.0.1）")
    print(f"  [..] 共 {len(hits)} 处 server.host=0.0.0.0，将随本包发布到目标机")
else:
    print("  [ok] 配置内无 server.host=0.0.0.0")
PYEOF
    # preview 的绑定不在 app.py 的 __main__ 块里（模块方式启动时那块不执行），真正生效点是镜像 CMD
    # 逐个检查（源码与包内副本都要看：源码修好了、包内副本可能还是旧的）
    local c
    for c in "$R12/preview/Dockerfile" "$OUT/payload/preview/Dockerfile"; do
      [ -f "$c" ] || continue
      if grep -qE '"--host",[[:space:]]*"0\.0\.0\.0"|--host[[:space:]]+0\.0\.0\.0' "$c" 2>/dev/null; then
        warn "${c} 的镜像 CMD 硬编码 --host 0.0.0.0 —— 这是 18095 真正生效的绑定点（app.py 的 __main__ 块在模块启动下不执行，改它无效）"
      fi
    done
    for c in "$R12/preview/app.py" "$OUT/payload/preview/app.py"; do
      [ -f "$c" ] || continue
      if grep -q 'host="0.0.0.0"' "$c" 2>/dev/null; then
        warn "${c} 仍写死 host=\"0.0.0.0\"（结构可能正常，但值未收紧）"
      fi
    done
    # 汇总口径必须分档：快照只在“重打把 services/rag-alg 纳入 payload/src”后才出现在包里，
    # 当前磁盘包（未重打）是没有 src/ 的；混在一起会让人按现包核对时找不到文件而怀疑清单。
    local cfg_n=0 snap_n=0
    [ -f "$OUT/payload/nacos/configs.json" ] && cfg_n=$(grep -o '0[.]0[.]0[.]0' "$OUT/payload/nacos/configs.json" 2>/dev/null | wc -l)
    [ -d "$OUT/payload/src" ] && snap_n=$(find "$OUT/payload" -path '*/nacos-data/snapshot/*' -type f -exec grep -l '0\.0\.0\.0' {} + 2>/dev/null | wc -l)
    if [ -f "$OUT/payload/preview/Dockerfile" ] && grep -qE '"--host",[[:space:]]*"0[.]0[.]0[.]0"|--host[[:space:]]+0[.]0[.]0[.]0' "$OUT/payload/preview/Dockerfile" 2>/dev/null; then
      if [ "${snap_n:-0}" -gt 0 ]; then
        warn "包内需同步 3 处：①配置 ${cfg_n} 处 server.host ②快照 ${snap_n} 份 ③preview 镜像 CMD（唯一生效点，连带 app.py/run.sh）—— 详见 offline/INSTALL-FINDINGS.md §七"
      else
        warn "包内需同步 2 处（当前包实况）：①配置 ${cfg_n} 处 server.host ②preview 镜像 CMD（唯一生效点，连带 app.py/run.sh）；③快照项待重打纳入 payload/src 后才出现（届时约 7 份，见 INSTALL-FINDINGS §七 分档）"
      fi
    fi
    warn "落地后用 check-bind.sh 核实际绑定（--expect-loopback 要求退出 0）；preview 为 host 网络，无端口映射可限"
    local snapn=0
    [ -d "$R12/src" ] && snapn=$(find "$R12/src" -path '*/nacos-data/snapshot/*' -type f -exec grep -l '0\.0\.0\.0' {} + 2>/dev/null | wc -l)
    [ "${snapn:-0}" -gt 0 ] && warn "另有 $snapn 份 Nacos 本地快照含 0.0.0.0：配置中心不可达时会被回读，只改配置中心会被静默抵消（python-nacos SNAPSHOT_BASE 默认 nacos-data/snapshot；仅 doc-parse 传了 no_snapshot=True）"
  else warn "未找到 nacos/configs.json，跳过监听面盘点"; fi

  echo
  [ "$bad" -eq 0 ] && ok "离线校验通过" || die "离线校验失败项: $bad"
}

cmd_smoke() {
  echo "== 无外网冒烟（--network none）=="
  local dist="" nginx=""
  for c in "$R12/frontend/dist" "$SRC_ROOT/frontend/plateform/dist"; do [ -f "$c/index.html" ] && { dist="$c"; break; }; done
  for c in "$R12/frontend/nginx/r12-18088.conf" "$SRC_ROOT/frontend/plateform/nginx/r12-18088.conf"; do [ -f "$c" ] && { nginx="$c"; break; }; done
  [ -n "$dist" ] || die "前端 dist 缺失，无法冒烟"
  [ -n "$nginx" ] || die "前端 nginx 配置缺失（frontend/nginx/r12-18088.conf），无法冒烟"

  docker rm -f r12-smoke-fe >/dev/null 2>&1
  docker run -d --name r12-smoke-fe --network none \
    -v "$dist:/usr/share/nginx/html/rag:ro" \
    -v "$nginx:/etc/nginx/conf.d/default.conf:ro" \
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

cmd_doc() {  # cmd_doc [输出路径]：只生成安装文档，不打包（演练与评审用）
  local out="${1:-$OUT/INSTALL-OFFLINE.md}"
  mkdir -p "$(dirname "$out")"
  awk '/^[[:space:]]*cat > "\$OUT\/INSTALL-OFFLINE\.md" <<.EOF.[[:space:]]*$/{f=1;next} f&&/^EOF$/{exit} f' "${BASH_SOURCE[0]}" > "$out"
  [ -s "$out" ] && { ok "INSTALL-OFFLINE.md -> $out（$(wc -l < "$out") 行）"; } || die "生成失败（heredoc 标记没找到）"
}

case "${1:-manifest}" in
  doc)      shift; cmd_doc "${1:-}" ;;
  manifest) cmd_manifest ;;
  pack)     cmd_pack ;;
  verify)   cmd_verify ;;
  smoke)    cmd_smoke ;;
  *) echo "用法: $0 {manifest|pack|verify|smoke|doc [输出路径]}"; exit 2 ;;
esac
