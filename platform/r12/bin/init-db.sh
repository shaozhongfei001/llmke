#!/usr/bin/env bash
# 离线初始化业务库：把 db/gienrag.sql 导入 MySQL 容器
# 用法: init-db.sh [sql路径] [容器名]
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL="${1:-$R12/db/gienrag.sql}"
CT="${2:-r12-mysql}"
ROOT_PW="${MYSQL_ROOT_PASSWORD:-R12r00t#2026local}"
ok() { printf '  [ok] %s\n' "$1"; }
die() { printf '  [FAIL] %s\n' "$1"; exit 1; }

[ -f "$SQL" ] || die "找不到 SQL 文件: $SQL"
docker ps --format '{{.Names}}' | grep -qx "$CT" || die "容器 $CT 未运行（先 docker compose up -d mysql）"

# 幂等：库里已有业务表就跳过（避免覆盖现场数据）
have=$(docker exec "$CT" mysql -uroot -p"$ROOT_PW" -N -e \
  "select count(*) from information_schema.tables where table_schema='gienrag' and table_name='knowledge_base'" 2>/dev/null | tr -d '\r')
if [ "${have:-0}" != "0" ]; then
  ok "gienrag 已存在业务表，跳过导入（如需重建请先手动 drop）"
  exit 0
fi

docker exec -i "$CT" mysql -uroot -p"$ROOT_PW" -e "create database if not exists gienrag default charset utf8mb4" 2>/dev/null
docker exec -i "$CT" mysql -uroot -p"$ROOT_PW" < "$SQL" || die "导入失败"
cnt=$(docker exec "$CT" mysql -uroot -p"$ROOT_PW" -N -e \
  "select count(*) from information_schema.tables where table_schema='gienrag'" 2>/dev/null | tr -d '\r')
ok "gienrag 导入完成，表数量: ${cnt:-0}"
