#!/usr/bin/env bash
# 离线初始化 Nacos 配置：把 nacos/configs.json 里的配置逐条发布回去
# 用法: init-nacos.sh [configs.json] [nacos地址]
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JSON="${1:-$R12/nacos/configs.json}"
BASE="${2:-http://127.0.0.1:18848}"
ok() { printf '  [ok] %s\n' "$1"; }
die() { printf '  [FAIL] %s\n' "$1"; exit 1; }

[ -f "$JSON" ] || die "找不到 $JSON"
command -v python3 >/dev/null || die "需要 python3"

python3 - "$JSON" "$BASE" <<'PY'
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
        if r == "true":
            okc += 1
        else:
            print(f"  [!!] {it['dataId']} -> {r[:60]}")
    except Exception as e:
        print(f"  [!!] {it['dataId']} 发布失败: {e}")
print(f"  [ok] Nacos 配置发布 {okc}/{len(items)}")
sys.exit(0 if okc == len(items) else 1)
PY
