#!/usr/bin/env bash
# 离线初始化 Nacos 配置：把 nacos/configs.json 里的配置逐条发布回去
# 用法: init-nacos.sh [configs.json] [nacos地址] [--namespace <租户/命名空间id>] [--dry-run]
#
# R14：新增 --namespace（Nacos 的 tenant 参数）。实装演练必须发布到**独立命名空间**，
#      否则会覆盖现网 public 命名空间的配置（共享宿主上的致命冲突）。
# R14：回读校验从"只比长度"升级为"比 sha256 摘要 + 长度"，长度相同但内容不同必须判失败。
#
# 前置：本机 Nacos 已就绪（compose 起 r12-nacos）。脚本会先等端口可用再发布。
# 注意：配置内容里可能含绝对路径（如 log_path），必须先用 install-paths.sh 改写成目标前缀，
#       否则服务启动后会把日志写到不存在的目录。本脚本发布前会做一次残留检查并告警。
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JSON=""
BASE=""
DRY=0
NS="${R12_NACOS_NAMESPACE:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --namespace) NS="${2:-}"; shift 2 ;;
    -*) echo "未知参数: $1"; exit 2 ;;
    *) if [ -z "$JSON" ]; then JSON="$1"; elif [ -z "$BASE" ]; then BASE="$1"; else echo "多余参数: $1"; exit 2; fi; shift ;;
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
printf '  [..] configs=%s  nacos=%s  namespace=%s\n' "$JSON" "$BASE" "${NS:-<public>}"

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
        # /logs/ 下的路径是运行期才会创建的产物（日志、garbage 目录），不存在属正常
        if "/logs/" in p or p.endswith("/logs"):
            continue
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
"${PYTHON3:-python3}" - "$JSON" "$BASE" "$NS" <<'PY' || die "Nacos 配置发布未全部成功"
import hashlib, json, sys, time, urllib.parse, urllib.request
path, base, ns = sys.argv[1], sys.argv[2], sys.argv[3]
items = json.load(open(path, encoding="utf-8"))
okc = 0
def h(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
for it in items:
    did = it["dataId"]; grp = it.get("group") or "DEFAULT_GROUP"; content = it.get("content") or ""
    payload = {"dataId": did, "group": grp, "content": content, "type": it.get("type") or "yaml"}
    if ns: payload["tenant"] = ns
    data = urllib.parse.urlencode(payload).encode()
    try:
        r = urllib.request.urlopen(base + "/nacos/v1/cs/configs", data=data, timeout=20).read().decode().strip()
        if r != "true":
            print(f"  [!!] {did} -> {r[:60]}"); continue
    except Exception as e:
        print(f"  [!!] {did} 发布失败: {e}"); continue
    # 回读校验：长度 + sha256 摘要都要一致（只比长度会放过内容被改写的情形）
    # R14 实测：Nacos 发布后**立即**回读可能瞬时 404（9 条全部 404，1s 后全部 200），故加重试。
    got = None; last_err = None
    for attempt in range(1, 5):
        try:
            q = {"dataId": did, "group": grp}
            if ns: q["tenant"] = ns
            got = urllib.request.urlopen(f"{base}/nacos/v1/cs/configs?{urllib.parse.urlencode(q)}", timeout=20).read().decode()
            break
        except Exception as e:
            last_err = e; time.sleep(attempt)
    if got is None:
        print(f"  [!!] {did} 回读失败（重试 4 次）: {last_err}"); continue
    if len(got) != len(content) or h(got) != h(content):
        print(f"  [!!] {did} 回读内容不一致: len {len(got)} vs {len(content)}, sha {h(got)} vs {h(content)}"); continue
    okc += 1
print(f"  [ok] Nacos 配置发布并回读校验（长度+sha256）{okc}/{len(items)}  namespace={ns or '<public>'}")
sys.exit(0 if okc == len(items) else 1)
PY
