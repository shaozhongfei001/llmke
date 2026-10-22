#!/usr/bin/env bash
# 一键落地验证：在【本机 MySQL 独立实例】上从零建库、建表、跑模块集成测试。
#
# 为什么不用 docker：业主要求用本机 MySQL 起独立实例；实例由 coordination/mysql-probe.sh 管理。
#
# 用法:
#   docs/baseline/validation/schema-verify.sh            # 全流程
#   docs/baseline/validation/schema-verify.sh --keep     # 保留数据库便于排查
#
# 退出码：0 全部通过；非 0 说明"设计不可落地"或环境缺失，不做降级通过。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PROBE="${MYSQL_PROBE:-$HOME/data/dev/coordination/mysql-probe.sh}"
SCHEMA="$ROOT/docs/baseline/validation/artifacts/schema-v1.3.sql"
DB="${LLMKE_SCHEMA_DB:-llmke_verify}"
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

say() { printf '[schema-verify] %s\n' "$*"; }
fail() { printf '[schema-verify] FAIL: %s\n' "$*" >&2; exit 1; }

[ -x "$PROBE" ] || fail "缺少实例管理脚本：$PROBE"
[ -f "$SCHEMA" ] || fail "缺少 schema 文件：$SCHEMA"

say "启动/复用本机 MySQL 独立实例"
"$PROBE" start >/dev/null 2>&1 || fail "实例启动失败（见 /tmp/mysql-probe/run.log）"

say "重建数据库 $DB"
"$PROBE" sql -e "DROP DATABASE IF EXISTS \`$DB\`" >/dev/null
"$PROBE" sql -e "CREATE DATABASE \`$DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci" >/dev/null

say "应用 schema（$(grep -c '^CREATE TABLE' "$SCHEMA") 张表）"
MYSQL_PROBE_DB="$DB" "$PROBE" apply "$SCHEMA" >/dev/null 2>&1 || fail "schema 执行失败（这是硬阻断，不得忽略）"

TABLES="$("$PROBE" sql -N -B -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB'" | tr -d '[:space:]')"
COLS="$("$PROBE" sql -N -B -e "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='$DB'" | tr -d '[:space:]')"
EXPECTED_TABLES="$(grep -c '^CREATE TABLE' "$SCHEMA")"
say "表=$TABLES（预期 $EXPECTED_TABLES）  列=$COLS"
[ "$TABLES" = "$EXPECTED_TABLES" ] || fail "表数量不符：实际 $TABLES，预期 $EXPECTED_TABLES"

say "契约 ↔ 表列一致性"
( cd "$ROOT" && PATH="$HOME/data/dev/llmke/.venv/bin:$PATH" \
  python3 docs/baseline/validation/contract-schema-check.py ) || fail "契约与表列不一致（先修契约或表）"

say "模块集成测试（真库读写）"
( cd "$ROOT" && PATH="$HOME/data/dev/llmke/.venv/bin:$PATH" PYTHONPATH="$ROOT" \
  LLMKE_MYSQL_SOCKET="${MYSQL_PROBE_DIR:-/tmp/mysql-probe}/mysql.sock" \
  LLMKE_CI_DB="${DB}_ci" python3 -m pytest modules -q ) || fail "集成测试未通过"

say "跨表一致性体检（孤儿数据/半成品代次/租约过期/积压事件）"
( cd "$ROOT" && PATH="$HOME/data/dev/llmke/.venv/bin:$PATH" \
  python3 docs/baseline/validation/consistency-doctor.py \
  --socket "${MYSQL_PROBE_DIR:-/tmp/mysql-probe}/mysql.sock" --db "$DB" ) || fail "一致性体检发现问题"

if [ "$KEEP" = 0 ]; then
  "$PROBE" sql -e "DROP DATABASE IF EXISTS \`$DB\`" >/dev/null
  say "已清理数据库 $DB"
fi

say "PASS：schema 可落地、模块可与真库协同"
