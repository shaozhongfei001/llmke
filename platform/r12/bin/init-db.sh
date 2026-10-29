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
ROOT_PW="${R12_MYSQL_ROOT_PASSWORD:-${MYSQL_ROOT_PASSWORD:-}}"
# R14-SEC：公开仓库不得写死数据库口令；读不到就明确失败，不静默回退到内置默认。
[ -n "$ROOT_PW" ] || { printf '  [FAIL] 缺少 MySQL root 口令：请在 %s 提供 R12_MYSQL_ROOT_PASSWORD，或导出同名环境变量\n' "$R12_ENV_FILE" >&2; exit 2; }

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1"; exit 1; }

# R14（C 报的成对修复）：search_config 只能有 1 行"生效中的默认助手"。
# 只加唯一索引不归零数据 -> 导入直接 1062 把 init 打断；只归零不加索引 -> 以后还能插出两行默认。
# 所以索引与数据两条都要校验，缺一条就非零退出（不允许"装完了但默认助手语义已经坏了"）。
check_default_helper_invariant() {
  local n idx
  n=$(my "$CT" mysql -uroot -N -e \
      "select count(*) from \`$DB\`.search_config where is_default=1 and is_del=1" 2>/dev/null | tr -d '\r')
  if [ -z "$n" ]; then warn "search_config 不变量无法读取（表不存在？）"; return 1; fi
  # 结构校验不能只看索引名：普通唯一索引建在 (is_default) 列上只允许"1 个 0 + 1 个 1"，语义是错的
  # （多用户永远标不了默认）。必须校验它是**唯一**索引，且是**函数索引**、表达式里含 is_default，等价于
  # case when (is_default=1 and is_del=1) then 1 else null end。C 提的边界，已采纳。
  idx=$(my "$CT" mysql -uroot -N -e \
      "select count(*) from information_schema.statistics where table_schema='$DB' and table_name='search_config' \
        and index_name='uk_search_config_default' and non_unique=0 \
        and expression is not null and expression like '%is_default%'" 2>/dev/null | tr -d '\r')
  if [ "${n:-0}" -gt 1 ]; then
    die "search_config 有 $n 行生效默认助手（应 ≤1）；修复: update search_config set is_default=0 where id<>1 and is_default=1;"
  fi
  if [ "${idx:-0}" -eq 0 ]; then
    warn "search_config 的 uk_search_config_default 不是"唯一且基于 is_default 表达式的函数索引"（数据当前只有 $n 行默认，但约束语义不对/缺失）"
    return 1
  fi
  ok "默认助手不变量成立：生效默认=$n 行；唯一函数索引存在（唯一且表达式含 is_default）"
  return 0
}

# 统一用 MYSQL_PWD 传口令：避免 `-p` 的行内口令在 ps 里可见、也避免告警噪声
my() { docker exec -e MYSQL_PWD="$ROOT_PW" "$@"; }

[ -f "$SQL" ] || die "找不到 SQL 文件: $SQL"
docker ps --format '{{.Names}}' | grep -qx "$CT" || die "容器 $CT 未运行（先 docker compose up -d mysql）"
[ -f "$R12_ENV_FILE" ] || warn "未找到 $R12_ENV_FILE，使用默认口令（与 compose 不一致时导入会认证失败）"

echo "== init-db =="
printf '  [..] sql=%s  container=%s  database=%s\n' "$SQL" "$CT" "$DB"

# R14 实测教训：端点注册不能放在建库/导入之前（全新库会 "Unknown database 'gienrag_r14'"，
# 也会因为 interface_info 表还没建而失败）。正确位置：**两条路径都在表就绪之后**。
# 幂等：库里已有业务表就跳过（避免覆盖现场数据）
have=$(my "$CT" mysql -uroot -N -e \
  "select count(*) from information_schema.tables where table_schema='$DB' and table_name='knowledge_base'" 2>/dev/null | tr -d '\r')
if [ "${have:-0}" != "0" ]; then
  ok "$DB 已存在业务表，跳过导入（如需重建请先手动 drop database $DB）"
  check_default_helper_invariant || die "已有库的默认助手不变量不成立（见上）"
  echo "== 接口注册表补齐（升级已有库时同样要补）=="
  bash "$R12/bin/init-endpoints.sh" "$CT" "$DB" || die "接口注册表补齐失败（新端点会经网关 401/30021）"
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
check_default_helper_invariant || die "默认助手不变量校验未通过（见上）"

echo "== 接口注册表补齐 =="
bash "$R12/bin/init-endpoints.sh" "$CT" "$DB" || die "接口注册表补齐失败（新端点会经网关 401/30021）"

# 关键表行数（作为“导的不是空壳”的证据）
for t in user_info role_info search_config interface_info knowledge_base; do
  n=$(my "$CT" mysql -uroot -N -e "select count(*) from \`$DB\`.$t" 2>/dev/null | tr -d '\r')
  printf '  [ok] %-16s rows=%s\n' "$t" "${n:-n/a}"
done
