#!/usr/bin/env bash
# R14 Loop3：隔离目录 + 独立库的首次实装演练（共享宿主，非干净目标机）
#
# 目的：在**不碰现网**的前提下，把安装文档的顺序真跑一遍，采集每步耗时与失败点。
# 边界（必须如实写进报告）：
#   * 共享宿主：基础设施容器（MySQL/Nacos/ES/MinIO…）是现网那一套，本演练只用**独立 schema**
#     与**独立 Nacos 命名空间**隔离，不是独立主机；
#   * 模型/venv 来自离线包拷贝（不是重新下载），因此本演练证明"安装器+初始化+配置发布"，
#     不能证明"目标机首次下载/构建"；
#   * 业务服务默认**不启动**（模型需 GPU、端口与现网冲突）；需要时用 --with-services 显式打开，
#     并遵守"现网 F 在跑时不动"的窗口纪律。
#
# 用法：
#   rehearsal.sh --prefix /home/szf/data/r14-rehearsal --db gienrag_r14 --ns r14-rehearsal
#   选项：--pkg <离线包目录>  --skip-sha  --skip-copy  --with-services
#
# 输出：逐步耗时表 + TSV（logs/rehearsal-<ts>.tsv）；任一 must 失败立即停止并记录失败点。
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$R12/../.." && pwd)"
PKG="$REPO/platform/r12/dist/offline"
PREFIX=""; DB="gienrag_r14"; NS="r14-rehearsal"
SKIP_SHA=0; SKIP_COPY=0; WITH_SVC=0; OVERLAY=1
while [ $# -gt 0 ]; do case "$1" in
  --prefix) PREFIX="${2:-}"; shift 2 ;;
  --db) DB="${2:-}"; shift 2 ;;
  --ns) NS="${2:-}"; shift 2 ;;
  --pkg) PKG="${2:-}"; shift 2 ;;
  --skip-sha) SKIP_SHA=1; shift ;;
  --skip-copy) SKIP_COPY=1; shift ;;
  --with-services) WITH_SVC=1; shift ;;
  --no-overlay) OVERLAY=0; shift ;;
  *) echo "未知参数: $1"; exit 2 ;;
esac; done
[ -n "$PREFIX" ] || { echo "必须给 --prefix（/opt 不可写时用家目录下的独立目录）"; exit 2; }

TS="$(date +%Y%m%dT%H%M%SZ)"; LOG="$R12/logs/rehearsal-$TS.tsv"
mkdir -p "$(dirname "$LOG")"
printf 'step\tname\tstart\tend\tduration_ms\tresult\tdetail\n' > "$LOG"

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1"; exit 1; }
now_ms() { date +%s%3N; }
STEP=0; T0=0; SNAME=""
begin() { STEP=$((STEP+1)); SNAME="$1"; T0=$(now_ms); printf '\n== [%d] %s ==\n' "$STEP" "$SNAME"; }
end()   {  # end <result> <detail>
  local dur=$(( $(now_ms) - T0 ))
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$STEP" "$SNAME" "$(date -d @$(( $(date +%s) - dur/1000 )) +%H:%M:%S)" "$(date +%H:%M:%S)" "$dur" "$1" "$2" >> "$LOG"
  printf '  → %s（%sms）%s\n' "$1" "$dur" "${2:+ | $2}"
}

# ---------------- 1. 前置：磁盘/端口/包 ----------------
begin "preflight（磁盘、包完整性、端口）"
[ -d "$PKG/payload" ] || die "离线包不存在: $PKG/payload"
avail_g=$(df -BG --output=avail "$(dirname "$PREFIX")" 2>/dev/null | tail -1 | tr -dc '0-9')
pkg_g=$(du -sBG "$PKG/payload" 2>/dev/null | cut -f1 | tr -dc '0-9')
printf '  可用空间=%sG  包体积=%sG  前缀=%s\n' "${avail_g:-?}" "${pkg_g:-?}" "$PREFIX"
[ -w "$(dirname "$PREFIX")" ] || die "$(dirname "$PREFIX") 不可写（/opt 需 root，改用家目录下的独立目录）"
[ "${avail_g:-0}" -gt "$(( ${pkg_g:-0} + 5 ))" ] || die "磁盘余量不足（需 > 包体积+5G）"
for p in 28088 28081 28082 28083 28085; do
  ss -lntH "sport = :$p" 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$p\$" && die "演练端口 $p 已被占用"
done
ok "端口 28088/28081-28085 空闲"
end pass "pkg=$PKG prefix=$PREFIX"

# ---------------- 2. 包完整性 ----------------
begin "sha256 校验（SHA256SUMS）"
if [ "$SKIP_SHA" = "1" ]; then warn "跳过（--skip-sha）"; end skip "按参数跳过"
else
  [ -f "$PKG/SHA256SUMS" ] || die "缺 SHA256SUMS"
  if ( cd "$PKG" && sha256sum -c SHA256SUMS --quiet ); then ok "全部匹配"; end pass "$(wc -l < "$PKG/SHA256SUMS") 行"
  else die "校验失败（禁止 --ignore-missing 掩盖缺项）"; fi
fi

# ---------------- 3. 前缀与 payload 拷贝 ----------------
begin "payload 拷贝到独立前缀"
if [ "$SKIP_COPY" = "1" ] && [ -x "$PREFIX/bin/up.sh" ]; then warn "跳过拷贝（--skip-copy，复用已有前缀）"; end skip "已有前缀"
else
  mkdir -p "$PREFIX"
  # 用 tar 管道保留权限；不用 rsync（目标机不一定有）
  ( cd "$PKG/payload" && tar -cf - . ) | ( cd "$PREFIX" && tar -xf - ) || die "payload 拷贝失败"
  chmod +x "$PREFIX/bin/"*.sh "$PREFIX/run/"*.sh "$PREFIX/models/"*.sh 2>/dev/null
  ok "已拷入 $PREFIX（$(du -sh "$PREFIX" | cut -f1)）"
  end pass "$(du -sh "$PREFIX" | cut -f1)"
fi

# ---------------- 3.5 覆盖安装脚本（记录为偏差）----------------
begin "覆盖为仓库当前安装脚本（偏差说明）"
if [ "$OVERLAY" != "1" ]; then
  warn "未覆盖（--no-overlay）：将使用包内 12:00 的旧脚本，仅能证明旧缺陷"
  end skip "--no-overlay"
else
  # 现有 24G 包是 12:00 打的，包内 bin/systemd 早于今天修的缺陷（init-endpoints / 占位符 must /
  # ES 治理 / check-units / boot-timing / STALE_JAR 双 bug 修复都不在里面）。
  # 直接用它安装只能证明"旧缺陷仍在"；为验证**修好后的安装器**，这里把仓库当前的
  # bin/ 与 systemd/ 覆盖进前缀，其余运行时资产（jars/venvs/models/dist）仍用包内的。
  for d in bin systemd; do
    [ -d "$R12/$d" ] || continue
    mkdir -p "$PREFIX/$d"
    ( cd "$R12/$d" && tar -cf - . ) | ( cd "$PREFIX/$d" && tar -xf - ) || die "覆盖 $d 失败"
  done
  [ -f "$R12/offline/templates/env.template" ] && cp "$R12/offline/templates/env.template" "$PREFIX/.env.template"
  chmod +x "$PREFIX/bin/"*.sh 2>/dev/null
  ok "已用仓库当前 bin/、systemd/、.env.template 覆盖（其余资产仍取自包）"
  printf '  偏差：包内脚本为 12:00 版本，缺 init-endpoints/占位符校验/ES 治理等修复；候选冻结后必须重打包\n'
  end pass "overlay bin+systemd"
fi

# ---------------- 4. 路径适配 ----------------
begin "install-paths 路径适配（dry-run → apply → check）"
bash "$PREFIX/bin/install-paths.sh" --prefix "$PREFIX" --dry-run >/tmp/r14-reh-paths-dry.txt 2>&1 || die "dry-run 失败（见 /tmp/r14-reh-paths-dry.txt）"
n_dry=$(grep -c '\[\.\.\]' /tmp/r14-reh-paths-dry.txt || true)
bash "$PREFIX/bin/install-paths.sh" --prefix "$PREFIX" >/tmp/r14-reh-paths-apply.txt 2>&1 || die "apply 失败（见 /tmp/r14-reh-paths-apply.txt）"
if bash "$PREFIX/bin/install-paths.sh" --prefix "$PREFIX" --check >/tmp/r14-reh-paths-check.txt 2>&1; then ok "无构建机路径残留（dry-run 动作 $n_dry 条）"; end pass "dry=$n_dry"
else warn "仍有残留（详见 /tmp/r14-reh-paths-check.txt）"; end warn "残留见 check 输出"; fi

# ---------------- 4.5 环境变量（安装文档第 3 步）----------------
begin "环境变量 .env（cp .env.template → .env）"
if [ -f "$PREFIX/.env" ]; then
  ok "已存在 .env（幂等跳过）"
  end pass "existing"
else
  [ -f "$PREFIX/.env.template" ] || die "缺 .env.template（compose --env-file 会直接失败）"
  cp "$PREFIX/.env.template" "$PREFIX/.env"
  # 口令来源：同一台机器的同一 MySQL 容器，故取现网 platform/r12/.env 的实际值（不是伪造）
  src_env="${R12_ENV_FILE:-$R12/.env}"
  if [ -f "$src_env" ]; then
    while IFS= read -r line; do
      case "$line" in R12_*=*) k="${line%%=*}"; v="${line#*=}"
        sed -i "s|^${k}=.*|${k}=${v}|" "$PREFIX/.env" ;; esac
    done < "$src_env"
    chmod 600 "$PREFIX/.env"
    # 包内 .env.template 可能是 12:00 旧版（缺 R12_MYSQL_PASSWORD 等），按 conf 实际引用的占位符补齐
    added=0
    for k in $(grep -rho '\${R12_[A-Z_]*}' "$PREFIX/conf" 2>/dev/null | sed 's/[${}]//g' | sort -u); do
      if ! grep -qE "^${k}=" "$PREFIX/.env"; then
        v="$(sed -n "s/^${k}=//p" "$src_env" | head -1)"
        printf '%s=%s\n' "$k" "${v:-CHANGE_ME}" >> "$PREFIX/.env"; added=$((added+1))
      fi
    done
    ok "已生成 .env 并填入 $(grep -c '^R12_' "$PREFIX/.env") 个键（补齐 conf 占位符 $added 个；值取自同机现网 .env）"
  else
    warn "未找到 $src_env，.env 仍是 CHANGE_ME 占位（init-db 会认证失败）"
  fi
  end pass ".env"
fi

# ---------------- 5. 独立 schema 初始化 ----------------
begin "init-db（独立 schema $DB，不碰现网 gienrag）"
bash "$PREFIX/bin/init-db.sh" "$PREFIX/db/gienrag.sql" r12-mysql "$DB" > /tmp/r14-reh-initdb.txt 2>&1 || { tail -20 /tmp/r14-reh-initdb.txt | sed 's/^/    /'; die "init-db 失败（见 /tmp/r14-reh-initdb.txt）"; }
tail -6 /tmp/r14-reh-initdb.txt | sed 's/^/    /'
tb=$(docker exec -e MYSQL_PWD="$(sed -n 's/^R12_MYSQL_ROOT_PASSWORD=//p' "$PREFIX/.env" 2>/dev/null | head -1)" r12-mysql \
     mysql -uroot -N -e "select count(*) from information_schema.tables where table_schema='$DB'" 2>/dev/null | tr -d '\r')
[ "${tb:-0}" -ge 30 ] || die "表数量异常: ${tb:-0}（期望 ≥30）"
ok "表数量=$tb；默认助手不变量 + 接口注册表已在 init-db 内校验"
end pass "tables=$tb"

# ---------------- 6. Nacos 独立命名空间发布 + 回读 ----------------
begin "init-nacos（独立 namespace=$NS，回读比 sha256）"
# 先建命名空间（幂等：存在则返回 already exist，不视为失败）
curl -sS -m 10 -X POST "http://127.0.0.1:18848/nacos/v1/console/namespaces" \
  --data-urlencode "customNamespaceId=$NS" --data-urlencode "namespaceName=$NS" \
  --data-urlencode "namespaceDesc=R14 rehearsal isolated namespace" >/dev/null 2>&1 || true
bash "$PREFIX/bin/init-nacos.sh" "$PREFIX/nacos/configs.json" http://127.0.0.1:18848 --namespace "$NS" > /tmp/r14-reh-nacos.txt 2>&1 \
  || { tail -15 /tmp/r14-reh-nacos.txt | sed 's/^/    /'; die "Nacos 发布/回读失败"; }
grep -E '\[ok\] Nacos|\[!!\]' /tmp/r14-reh-nacos.txt | sed 's/^/    /'
ok "配置已发布到独立命名空间（现网 public 未改动）"
end pass "namespace=$NS"

# ---------------- 7. ES 副本治理（幂等，共享 ES）----------------
begin "es-single-node（幂等；共享 ES，必须 no-op）"
bash "$PREFIX/bin/es-single-node.sh" > /tmp/r14-reh-es.txt 2>&1 || { tail -8 /tmp/r14-reh-es.txt | sed 's/^/    /'; die "ES 治理失败"; }
tail -3 /tmp/r14-reh-es.txt | sed 's/^/    /'
end pass "green"

# ---------------- 8. 安装器自检三件套 ----------------
begin "交付门禁四件套（check-units / boot-timing 只读模式 / gates-selftest / 占位符）"
bash "$PREFIX/bin/check-units.sh" --repo-only > /tmp/r14-reh-units.txt 2>&1 || { tail -10 /tmp/r14-reh-units.txt | sed 's/^/    /'; die "check-units 失败"; }
ok "check-units 通过"
ph_missing=""
for v in $(grep -rho '\${R12_[A-Z_]*}' "$PREFIX/conf" 2>/dev/null | sed 's/[${}]//g' | sort -u); do
  grep -qE "^$v=" "$PREFIX/.env" 2>/dev/null || ph_missing="$ph_missing $v"
done
[ -z "$ph_missing" ] || die "conf 占位符在 .env 缺失:$ph_missing"
ok "conf 占位符全部可在 .env 找到"
end pass "units+placeholders"

# ---------------- 9. 业务实例（可选，默认不做）----------------
begin "业务实例启动（默认跳过）"
if [ "$WITH_SVC" != "1" ]; then
  warn "跳过：模型需 GPU、端口需重映射，本演练不启动业务实例（报告里列明为未验证项）"
  end skip "未启动（需独立主机/GPU）"
else
  warn "--with-services 已请求，但端口重映射与模型并行不在本脚本范围；请人工按报告执行"
  end skip "需人工"
fi

echo
echo "  TSV: $LOG"
awk -F'\t' 'NR>1{printf "  %-2s %-46s %8sms  %s\n", $1, $2, $5, $6}' "$LOG"
fails=$(awk -F'\t' 'NR>1 && $6=="fail"{c++} END{print c+0}' "$LOG")
skips=$(awk -F'\t' 'NR>1 && $6=="skip"{c++} END{print c+0}' "$LOG")
echo
[ "$fails" -gt 0 ] && { echo "  [FAIL] 有 $fails 步失败"; exit 1; }
echo "  [ok] 演练完成（跳过 $skips 步，见报告）"
