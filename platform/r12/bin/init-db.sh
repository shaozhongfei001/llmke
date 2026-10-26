#!/usr/bin/env bash
# 离线初始化业务库：把 db/gienrag.sql 导入 MySQL 容器
# 用法: init-db.sh [sql路径] [容器名] [库名]
#   库名默认 gienrag；给别的库名时会现场改写 dump 里的 `gienrag` 标识符，
#   用于目标机预演/沙箱验证（不碰生产库）。
#
# 口令来源（按优先级）：环境变量 R12_MYSQL_ROOT_PASSWORD > MYSQL_ROOT_PASSWORD > 包内 .env > 内置默认
# 注意：容器口令由 docker-compose 的 ${R12_MYSQL_ROOT_PASSWORD} 决定，两边必须一致，否则认证失败。
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL="${1:-$R12/db/gienrag.sql}"
CT="${2:-r12-mysql}"
DB="${3:-gienrag}"

# 读包内 .env（不覆盖已导出的环境变量）
R12_ENV_FILE="${R12_ENV_FILE:-$R12/.env}"
if [ -f "$R12_ENV_FILE" ]; then
  while IFS= read -r line; do
    case "$line" in ''|\#*) continue ;; esac
    key="${line%%=*}"; val="${line#*=}"
    case "$key" in
      R12_MYSQL_ROOT_PASSWORD|MYSQL_ROOT_PASSWORD)
        [ -n "${!key:-}" ] || export "$key=$val" ;;
    esac
  done < "$R12_ENV_FILE"
fi
ROOT_PW="${R12_MYSQL_ROOT_PASSWORD:-${MYSQL_ROOT_PASSWORD:-R12r00t#2026local}}"

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1"; exit 1; }

# 统一用 MYSQL_PWD 传口令：避免 `-p` 的行内口令在 ps 里可见、也避免告警噪声
my() { docker exec -e MYSQL_PWD="$ROOT_PW" "$@"; }

[ -f "$SQL" ] || die "找不到 SQL 文件: $SQL"
docker ps --format '{{.Names}}' | grep -qx "$CT" || die "容器 $CT 未运行（先 docker compose up -d mysql）"
[ -f "$R12_ENV_FILE" ] || warn "未找到 $R12_ENV_FILE，使用默认口令（与 compose 不一致时导入会认证失败）"

echo "== init-db =="
printf '  [..] sql=%s  container=%s  database=%s\n' "$SQL" "$CT" "$DB"

# 幂等：库里已有业务表就跳过（避免覆盖现场数据）
have=$(my "$CT" mysql -uroot -N -e \
  "select count(*) from information_schema.tables where table_schema='$DB' and table_name='knowledge_base'" 2>/dev/null | tr -d '\r')
if [ "${have:-0}" != "0" ]; then
  ok "$DB 已存在业务表，跳过导入（如需重建请先手动 drop database $DB）"
  exit 0
fi

# 库名非默认时现场改写，不动包内原文件
SRC="$SQL"
if [ "$DB" != "gienrag" ]; then
  SRC="$(mktemp /tmp/r12-initdb-XXXXXX.sql)" || die "无法创建临时文件"
  sed "s/\`gienrag\`/\`$DB\`/g" "$SQL" > "$SRC" || die "改写库名失败"
  trap 'rm -f "$SRC"' EXIT
  printf '  [..] 已改写库名为 %s（临时文件 %s）\n' "$DB" "$SRC"
fi

my -i "$CT" mysql -uroot --default-character-set=utf8mb4 \
  -e "create database if not exists \`$DB\` default charset utf8mb4" 2>/dev/null \
  || die "创建库 $DB 失败（口令是否与 compose 一致？）"
my -i "$CT" mysql -uroot --default-character-set=utf8mb4 < "$SRC" || die "导入失败"

cnt=$(my "$CT" mysql -uroot -N -e \
  "select count(*) from information_schema.tables where table_schema='$DB'" 2>/dev/null | tr -d '\r')
[ "${cnt:-0}" -ge 30 ] || die "导入后表数量异常: ${cnt:-0}（期望 ≥30）"
ok "$DB 导入完成，表数量: $cnt"

# 关键表行数（作为“导的不是空壳”的证据）
for t in user_info role_info search_config interface_info knowledge_base; do
  n=$(my "$CT" mysql -uroot -N -e "select count(*) from \`$DB\`.$t" 2>/dev/null | tr -d '\r')
  printf '  [ok] %-16s rows=%s\n' "$t" "${n:-n/a}"
done
