#!/usr/bin/env bash
# 离线初始化 Nacos 配置：把 nacos/configs.json 里的配置逐条发布回去
# 用法: init-nacos.sh [configs.json] [nacos地址] [--dry-run]
#
# 前置：本机 Nacos 已就绪（compose 起 r12-nacos）。脚本会先等端口可用再发布。
# 注意：配置内容里可能含绝对路径（如 log_path），必须先用 install-paths.sh 改写成目标前缀，
#       否则服务启动后会把日志写到不存在的目录。本脚本发布前会做一次残留检查并告警。
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JSON=""
BASE=""
DRY=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    -*) echo "未知参数: $a"; exit 2 ;;
    *) if [ -z "$JSON" ]; then JSON="$a"; elif [ -z "$BASE" ]; then BASE="$a"; fi ;;
  esac
done
JSON="${JSON:-$R12/nacos/configs.json}"
BASE="${BASE:-${R12_NACOS_ADDR:-http://127.0.0.1:18848}}"

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1"; exit 1; }

[ -f "$JSON" ] || die "找不到 $JSON"
command -v python3 >/dev/null || die "需要 python3（只用标准库）"

echo "== init-nacos =="
printf '  [..] configs=%s  nacos=%s\n' "$JSON" "$BASE"

# 1) 等待 Nacos 就绪（离线机上 compose 刚起时容器内还在初始化）
printf '  [..] 等待 Nacos 就绪'
for i in $(seq 1 60); do
  if curl -sS -m 2 -o /dev/null "${BASE}/nacos/v1/console/health/readiness" 2>/dev/null \
     || curl -sS -m 2 -o /dev/null "${BASE}/nacos/" 2>/dev/null; then
    echo " ok"; ready=1; break
  fi
  printf '.'; sleep 2
done
[ "${ready:-0}" = "1" ] || die "Nacos 60s 内未就绪（先执行 docker compose up -d nacos）"

# 2) 发布前残留检查：配置内容里指向不存在的绝对路径，服务会启动即报错
"${PYTHON3:-python3}" - "$JSON" <<'PY' || true
import json, os, re, sys
items = json.load(open(sys.argv[1], encoding="utf-8"))
bad = []
for it in items:
    for p in re.findall(r"/(?:home|Users)/[A-Za-z0-9._/-]+", it.get("content") or ""):
        if not os.path.exists(p):
            bad.append((it["dataId"], p))
for d, p in bad:
    print(f"  [!!] {d} 引用了目标机不存在的路径: {p}（先跑 install-paths.sh）")
print(f"  [..] 路径检查: {'全部存在' if not bad else str(len(bad)) + ' 处不存在'}")
PY

if [ "$DRY" = 1 ]; then
  "${PYTHON3:-python3}" - "$JSON" <<'PY'
import json, sys
items = json.load(open(sys.argv[1], encoding="utf-8"))
print(f"  [..] dry-run：将发布 {len(items)} 条")
for it in items:
    print(f"       {it['dataId']}  group={it.get('group') or 'DEFAULT_GROUP'}  type={it.get('type') or 'yaml'}  {len(it.get('content') or '')}B")
PY
  exit 0
fi

# 3) 逐条发布 + 回读校验
"${PYTHON3:-python3}" - "$JSON" "$BASE" <<'PY' || die "Nacos 配置发布未全部成功"
import json, sys, urllib.parse, urllib.request
path, base = sys.argv[1], sys.argv[2]
items = json.load(open(path, encoding="utf-8"))
okc = 0
for it in items:
    data = urllib.parse.urlencode({
        "dataId": it["dataId"], "group": it.get("group") or "DEFAULT_GROUP",
        "content": it.get("content") or "", "type": it.get("type") or "yaml",
    }).encode()
    try:
        r = urllib.request.urlopen(base + "/nacos/v1/cs/configs", data=data, timeout=20).read().decode().strip()
        if r != "true":
            print(f"  [!!] {it['dataId']} -> {r[:60]}"); continue
    except Exception as e:
        print(f"  [!!] {it['dataId']} 发布失败: {e}"); continue
    # 回读校验：内容长度一致才算真发布（防止存在但内容为空）
    try:
        q = urllib.parse.urlencode({"dataId": it["dataId"], "group": it.get("group") or "DEFAULT_GROUP"})
        got = urllib.request.urlopen(f"{base}/nacos/v1/cs/configs?{q}", timeout=20).read().decode()
        if len(got) != len(it.get("content") or ""):
            print(f"  [!!] {it['dataId']} 回读长度不一致: {len(got)} != {len(it.get('content') or '')}"); continue
    except Exception as e:
        print(f"  [!!] {it['dataId']} 回读失败: {e}"); continue
    okc += 1
print(f"  [ok] Nacos 配置发布并回读校验 {okc}/{len(items)}")
sys.exit(0 if okc == len(items) else 1)
PY
