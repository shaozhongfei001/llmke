#!/usr/bin/env bash
# R13 监听面自检：把"配置说绑什么"和"实际绑什么"摆在一起，专门抓“改了配置却没生效”。
#
# 为什么需要它（而不是看配置就算过）：
#   内部数据面端口的绑定地址有三处来源，且运行时会互相覆盖 ——
#     ① Nacos 配置内容（6 处 server.host）
#     ② 各服务目录下的 Nacos 本地快照 nacos-data/snapshot/<dataId>+<group>+
#        （python-nacos SNAPSHOT_BASE 默认是相对路径，配置中心不可达时回读；
#          只有 alg_doc_parse_service 显式传了 no_snapshot=True）
#     ③ 源码/启动参数（preview/app.py、systemd r12-graphsvc 的 --host）
#   典型踩坑：把 ① 改成 127.0.0.1 就宣布修好，但 ② 仍是 0.0.0.0，
#   于是"配置看起来是回环、实际仍对外"，验收假绿。
#
# 用法: check-bind.sh [--prefix <安装前缀>] [--expect-loopback] [--json]
#   --prefix          默认取脚本所在 bin/ 的上一级
#   --expect-loopback 收紧后使用：任一内部端口仍绑 0.0.0.0 即退出 1
#   --samples N       采样次数（默认 1，间隔 1s，取并集=worst case）。服务在 systemd
#                     重启抖动/Restart=always 时，单次采样可能刚好落在"未监听"而漏判，
#                     对这类端口建议 --samples 5。
#   本脚本只读，不改任何配置、不重启任何服务。
set -uo pipefail
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX=""
EXPECT=0
JSONOUT=0
SAMPLE=1        # 采样次数：服务在重启抖动时，单次采样可能刚好落在"未监听"而漏掉外露
while [ $# -gt 0 ]; do
  case "$1" in
    --prefix) PREFIX="${2:-}"; shift 2 ;;
    --expect-loopback) EXPECT=1; shift ;;
    --samples) SAMPLE="${2:-1}"; shift 2 ;;
    --json) JSONOUT=1; shift ;;
    -h|--help) sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "未知参数: $1"; exit 2 ;;
  esac
done
[ -n "$PREFIX" ] || PREFIX="$(cd "$SELF_DIR/.." && pwd)"

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
info() { printf '  [..] %s\n' "$1"; }

CFG="$PREFIX/nacos/configs.json"
SRC="$PREFIX/src"
[ -d "$SRC" ] || SRC="$PREFIX"          # 兼容 src/ 未落地的情况

echo "== check-bind（前缀 $PREFIX）=="

# 1) 配置侧声明值：端口 -> 声明来源集合
declared="$(python3 - "$PREFIX" "$CFG" "$SRC" <<'PY' 2>/dev/null
import glob, json, os, re, sys
prefix, cfg, src = sys.argv[1], sys.argv[2], sys.argv[3]
# (dataId, 行号) -> (端口, 服务, 面)
MAP = {
    ("alg_doc_config_py", 3):      (12340, "doc-parse", "写入面"),
    ("index_data_config_py", 7):   (19526, "index_vector", "写入面"),
    ("index_data_config_py", 37):  (19527, "index_fulltext", "写入面"),
    ("alg_retrieval_config_py", 7): (19995, "alg_retrieval", "读"),
    ("alg_llm_config_py", 6):      (19996, "llm_open_chat", "推理"),
    ("index_graph_config_py", 4):  (19529, "index_graph", "读"),
}
rows = {}   # port -> {"svc","face","declared":set(),"srcs":[(value, where)]}
def add(port, svc, face, value, where):
    r = rows.setdefault(port, {"svc": svc, "face": face, "declared": set(), "srcs": []})
    r["declared"].add(value)
    # 记录“值@来源”，才能看出是哪一处来源与别处不一致（例如 payload 仍 0.0.0.0、
    # systemd 已改 127.0.0.1 —— 只看值集合会丢掉这个信息）
    r["srcs"].append((value, where))

# 固定端口全集：表格必须每个端口都有一行，否则手工核对时会误以为"少的那行不用管"
ALL = {12340: ("doc-parse", "写入面"), 19526: ("index_vector", "写入面"),
       19527: ("index_fulltext", "写入面"), 19529: ("index_graph", "读"),
       19995: ("alg_retrieval", "读"), 19996: ("llm_open_chat", "推理"),
       18095: ("preview", "读")}
for _p, (_s, _f) in ALL.items():
    rows[_p] = {"svc": _s, "face": _f, "declared": set(), "srcs": []}

# ① Nacos 配置内容：安装前缀、离线包 payload、现网导出，逐个收集（不 break，
#    以便发现“包内与现网不一致”这种更难查的情况）
paths = [
    cfg,
    os.path.join(prefix, "nacos", "configs.json"),
    os.path.join(prefix, "dist", "offline", "payload", "nacos", "configs.json"),
]
for p in paths:
    if not p or not os.path.isfile(p):
        continue
    try:
        items = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    tag = "nacos" if p == cfg else ("payload" if "dist/offline" in p else "nacos")
    for it in items:
        for i, line in enumerate((it.get("content") or "").splitlines(), 1):
            s = line.strip()
            if not s.startswith("host:"):
                continue
            v = s.split(":", 1)[1].strip()
            if "0.0.0.0" not in v and "127.0.0.1" not in v:
                continue
            hit = MAP.get((it["dataId"], i))
            if hit:
                add(hit[0], hit[1], hit[2], v, f"{tag}:{it['dataId']}")

# ② 本地快照（配置中心不可达时的回退值）
for f in glob.glob(os.path.join(src, "**/nacos-data/snapshot/*"), recursive=True):
    if not os.path.isfile(f):
        continue
    base = os.path.basename(f).split("+")[0]
    for i, line in enumerate(open(f, encoding="utf-8", errors="ignore").read().splitlines(), 1):
        s = line.strip()
        if not s.startswith("host:"):
            continue
        v = s.split(":", 1)[1].strip()
        if "0.0.0.0" not in v and "127.0.0.1" not in v:
            continue
        for (did, ln), hit in MAP.items():
            if did == base:
                add(hit[0], hit[1], hit[2], v, "snapshot:" + base)

# ③ 源码/启动参数（不参与快照回退，但必须进表格）
#    注意：不能用 __file__ —— 本段从 stdin 执行，__file__ 不可靠（曾导致 18095 缺行）
_HOST_ANY = re.compile(r"""host\s*=\s*(?:os\.getenv\(\s*["']([A-Z_]+)["']\s*,\s*["']([^"']+)["']\s*\)|["']([^"']+)["'])""")
_ENV_DEF = re.compile(r"""-e\s+([A-Z_]+)=["']?\$\{\1:-([^}"]+)\}""")

def norm(v):
    return v if v in ("0.0.0.0", "127.0.0.1") else "其它:" + v

for app in (os.path.join(prefix, "preview", "app.py"),
            os.path.join(src, "preview", "app.py"),
            os.path.join(prefix, "src", "preview", "app.py")):
    if not os.path.isfile(app):
        continue
    for i, line in enumerate(open(app, encoding="utf-8", errors="ignore"), 1):
        if "uvicorn.run(" not in line:
            continue
        m = _HOST_ANY.search(line)
        if not m:
            continue
        if m.group(2):          # os.getenv("PREVIEW_HOST", "默认值")
            add(18095, "preview", "读", norm(m.group(2)), f"源码:app.py({m.group(1)}默认)")
            add(18095, "preview", "读", norm(m.group(2)), f"源码:app.py:{i}")
        elif m.group(3):
            add(18095, "preview", "读", norm(m.group(3)), f"源码:app.py:{i}")
        break

# Dockerfile 的 CMD/ENTRYPOINT：这是最容易漏的绑定来源。
# 若镜像是 `python -m uvicorn app:app --host X`，则 app.py 里的 `if __name__=="__main__"`
# 整块（含 PREVIEW_HOST 默认值）**根本不会执行** —— 改源码/传环境变量都不生效。
for df in (os.path.join(prefix, "preview", "Dockerfile"), os.path.join(src, "preview", "Dockerfile")):
    if not os.path.isfile(df):
        continue
    for line in open(df, encoding="utf-8", errors="ignore"):
        if not re.match(r"\s*(CMD|ENTRYPOINT)\b", line):
            continue
        m = re.search(r'"--host",\s*"([^"]+)"', line) or re.search(r"--host\s+([0-9.]+)", line)
        if m:
            add(18095, "preview", "读", norm(m.group(1)), "镜像CMD:Dockerfile")


# run.sh 里的 -e PREVIEW_HOST="${PREVIEW_HOST:-127.0.0.1}"（启动参数默认值）
for rs in (os.path.join(prefix, "preview", "run.sh"), os.path.join(src, "preview", "run.sh")):
    if not os.path.isfile(rs):
        continue
    for line in open(rs, encoding="utf-8", errors="ignore"):
        m = _ENV_DEF.search(line)
        if m and m.group(1) == "PREVIEW_HOST":
            add(18095, "preview", "读", norm(m.group(2)), "启动参数:run.sh(-e PREVIEW_HOST)")
            break

# systemd 启动参数（19529 的第二条绑定路径）
for unit in (os.path.join(prefix, "systemd", "r12-graphsvc.service"),):
    if os.path.isfile(unit):
        for line in open(unit, encoding="utf-8", errors="ignore"):
            m = re.search(r"--host\s+(\S+)", line)
            if m:
                add(19529, "index_graph", "读", norm(m.group(1)), "systemd:r12-graphsvc")
                break

for port in sorted(rows):
    r = rows[port]
    # 来源短标签 + 值@来源 明细，便于一眼看出"哪个来源与别的来源不一致"
    pairs = []
    for val, where in r["srcs"]:
        tag = where.split(":", 1)[0]
        pairs.append(f"{val}@{tag}")
    print("\t".join([str(port), r["svc"], r["face"],
                     ",".join(sorted(r["declared"])) or "-",
                     ",".join(sorted(set(pairs))) or "-"]))
PY
)"

if [ -z "${declared:-}" ]; then
  warn "无法从 $CFG 解析声明值（文件缺失？）；下面只报实际监听"
fi

# 2) 实际监听地址
actual_once() {  # actual_once <port> -> 逗号分隔的监听地址集合
  ss -ltn 2>/dev/null | awk -v p=":$1" '
    $4 ~ (p "$") {
      a = $4; sub(/:[0-9]+$/, "", a);
      if (a == "0.0.0.0" || a == "*" || a == "[::]" ) print "0.0.0.0";
      else if (a == "127.0.0.1" || a == "[::ffff:127.0.0.1]" || a ~ /127\.0\.0\.1/) print "127.0.0.1";
      else print a;
    }' | sort -u | paste -sd, -
}

state_hint() {  # state_hint <服务名> <端口> —— 未监听时区分“主动停机/崩溃/轮询中”
  local svc="$1" port="$2" unit="" log="" pid="" tail_txt=""
  case "$svc" in
    index_graph)   unit="r12-graphsvc"; log="$PREFIX/logs/index_graph_service.log" ;;
    doc-parse)     unit="r12-docparse";  log="$PREFIX/logs/doc-parse.log" ;;
    index_vector)  log="$PREFIX/logs/index_vector_service.log" ;;
    index_fulltext) log="$PREFIX/logs/index_fulltext_service.log" ;;
    alg_retrieval) log="$PREFIX/logs/alg_retrieval_service.log" ;;
    llm_open_chat) log="$PREFIX/logs/alg_llm_inference_service.log" ;;
    preview)       : ;;
  esac
  if [ "$svc" = "preview" ]; then
    if command -v docker >/dev/null 2>&1; then
      local st; st="$(docker inspect r12-preview --format '{{.State.Status}}' 2>/dev/null)"
      [ -n "$st" ] && { printf '容器 %s' "$st"; return; }
    fi
    printf '无容器信息'; return
  fi
  # systemd 托管的一眼看出状态；未托管的看日志尾迹
  if [ -n "$unit" ] && command -v systemctl >/dev/null 2>&1; then
    local us; us="$(systemctl --user is-active "$unit" 2>/dev/null)"
    case "$us" in
      active|activating|deactivating|failed) printf 'unit %s' "$us"; return ;;
    esac
  fi
  pid="$PREFIX/run/${svc//-/_}.pid"
  [ -f "$pid" ] || pid="$PREFIX/run/$svc.pid"
  if [ -f "$log" ]; then
    tail_txt="$(tail -n 40 "$log" 2>/dev/null)"
    case "$tail_txt" in
      *Traceback*|*"Address already in use"*|*"Out of memory"*|*Killed*) printf '日志见异常（疑似崩溃）'; return ;;
      *"shutdown complete"*|*"Finished server process"*|*"Shutting down"*) printf '日志见优雅停机'; return ;;
    esac
  fi
  if [ -f "$pid" ]; then
    local p; p="$(cat "$pid" 2>/dev/null)"
    kill -0 "${p:-0}" 2>/dev/null || { printf 'pid 文件残留(进程已退出)'; return; }
    printf '进程在但未监听'; return
  fi
  printf '无日志无 pid'
}

actual_of() {  # 多次采样取并集（worst case）：抖动中的服务不会因"刚好停着"被判成未运行
  local p="$1" i=1 acc="" one
  while [ "$i" -le "${SAMPLE:-1}" ]; do
    one="$(actual_once "$p")"
    [ -n "$one" ] && acc="${acc:+$acc,}$one"
    i=$((i+1))
    [ "$i" -le "${SAMPLE:-1}" ] && sleep 1
  done
  [ -n "$acc" ] && printf '%s' "$acc" | tr ',' '\n' | sort -u | paste -sd, -
}

external=0
mismatch=0
printf '  %-6s %-14s %-6s %-18s %-38s %-14s %s\n' PORT 服务 面 配置声明 声明来源（值@来源） 实际监听 判定
PRINTED=" "
while IFS=$'\t' read -r port svc face decl pairs; do
  [ -n "${port:-}" ] || continue
  PRINTED="$PRINTED$port "
  [ -n "$decl" ] || decl="(未找到声明)"
  [ -n "$pairs" ] || pairs="-"
  act="$(actual_of "$port")"
  [ -n "$act" ] || act="(未监听)"
  if [ "$act" = "0.0.0.0" ] || [ "$act" = "(未监听),0.0.0.0" ]; then external=$((external+1)); fi
  verdict="一致"
  any_ext=0
  case "$decl" in *0.0.0.0*) any_ext=1 ;; esac
  case "$act" in
    "(未监听)")
      hint="$(state_hint "$svc" "$port")"
      case "$decl" in
        *127.0.0.1*) [ "$any_ext" = 1 ] && verdict="未运行（声明矛盾；${hint:-状态未知}）" || verdict="未运行（${hint:-状态未知}）" ;;
        *) verdict="未运行（${hint:-状态未知}）" ;;
      esac ;;
    *0.0.0.0*)
      if [ "$any_ext" = 1 ]; then
        case "$decl" in
          *127.0.0.1*) verdict="配置自相矛盾（来源间取值不一致，见来源列）"; mismatch=$((mismatch+1)) ;;
          *)           verdict="一致（仍外露）" ;;
        esac
      else
        verdict="静默抵消：配置已收紧但实际外露"; mismatch=$((mismatch+1))
      fi ;;
    *127.0.0.1*)
      [ "$any_ext" = 1 ] && verdict="已收紧但配置未同步" ;;
  esac
  printf "  %-6s %-14s %-6s %-18s %-38s %-14s %s\n" "$port" "$svc" "$face" "$decl" "$pairs" "$act" "$verdict"
done <<< "$declared"

# 3) 兜底：表格里没覆盖到的端口单独报（正常情况下已全覆盖，这里只防配置解析失败）
LEFTOVER=""
for p in 12340 18095 19526 19527 19529 19995 19996; do
  case "$PRINTED" in *" $p "*) continue ;; esac
  LEFTOVER="$LEFTOVER $p"
done
if [ -n "$LEFTOVER" ]; then
  echo "== 未纳入表格的端口（声明来源未识别，仅报实际监听）=="
  for p in $LEFTOVER; do
    a="$(actual_of "$p")"
    [ -n "$a" ] || { info "$p 未监听"; continue; }
    case "$a" in *0.0.0.0*) warn "$p 监听 $a（外露）"; external=$((external+1)) ;; *) ok "$p 监听 $a" ;; esac
  done
fi

echo
# ===== 2c) 基础设施面与容器监听面（R14 F02）=====
# 为什么必须有这一节：R13 的 check-bind 只覆盖 7 个应用端口（12340/18095/1952x/1999x），
# 于是"七个端口已回环"被当成"整栈只有两个对外入口"，而 ss 快照里
# 19200 ES / 18848 Nacos / 19000 MinIO / 16379 Redis / 13306 MySQL / 19669 Nebula /
# 19876 RocketMQ 全是 0.0.0.0（IPv4 与 IPv6 双通配）。数据面/管理面同样是被绕过的入口。
#
# 判定依据取"实际"的两层证据：
#   ① docker 侧：容器 PortBindings 的 HostIp（配置意图）
#   ② 宿主 ss：该端口真实监听地址（含 [::] 与 *:）
# 两者只要有一处不是 127.0.0.1，且该端口不在批准对外清单里，就算外露。
#
# 批准对外清单（唯一客户端入口）：18088 前端 nginx、8088 Java 网关。
# 这两个必须对外，其余一律回环。
ALLOW_EXTERNAL="18088 8088"

echo "== 基础设施 / 容器监听面（数据面与管理面）=="
printf '  %-6s %-22s %-24s %-14s %s\n' PORT 容器 容器HostIp 实际监听 判定
INFRA_EXT=0
if command -v docker >/dev/null 2>&1; then
  # name|networkmode|container_port=hostip:hostport;...
  infra_rows="$(docker inspect --format '{{.Name}}|{{.HostConfig.NetworkMode}}|{{range $p, $b := .HostConfig.PortBindings}}{{$p}}={{range $b}}{{.HostIp}}:{{.HostPort}}{{end}};{{end}}' \
      $(docker ps --format '{{.Names}}' | grep -E '^r12-' | tr '\n' ' ') 2>/dev/null)"
  while IFS='|' read -r name netmode binds; do
    [ -n "${name:-}" ] || continue
    name="${name#/}"
    if [ "$netmode" = "host" ]; then
      # host 网络容器无法用 HostIp 约束：端口直接由容器内进程绑定。
      # 只能按其真实监听地址判定（r12-fe 的 nginx `listen 18088` 是批准的对外入口；
      # r12-preview 由 PREVIEW_HOST 默认 127.0.0.1 约束）。
      printf '  %-6s %-22s %-24s %-14s %s\n' "(host)" "$name" "(host网络-无HostIp)" "见下" "按进程绑定判定"
      continue
    fi
    [ -n "${binds:-}" ] || continue
    echo "  $binds" | tr ';' '\n' | while IFS='=' read -r cport hp; do
      [ -n "${cport:-}" ] || continue
      hostip="${hp%%:*}"; hostport="${hp##*:}"
      [ -n "$hostip" ] || hostip="(空=0.0.0.0)"
      act="$(actual_of "$hostport")"
      [ -n "$act" ] || act="(未监听)"
      allowed=0
      for a in $ALLOW_EXTERNAL; do [ "$a" = "$hostport" ] && allowed=1; done
      if [ "$allowed" = 1 ]; then
        # 批准入口：确认它确实对外（否则客户端不可用），不算违规
        case "$act" in
          *0.0.0.0*|*\**) printf '  %-6s %-22s %-24s %-14s %s\n' "$hostport" "$name" "$hostip" "$act" "批准对外入口（预期）" ;;
          *)              printf '  %-6s %-22s %-24s %-14s %s\n' "$hostport" "$name" "$hostip" "$act" "警告：批准入口未对外" ;;
        esac
        continue
      fi
      case "$hostip$act" in
        *0.0.0.0*|*\**)
          printf '  %-6s %-22s %-24s %-14s %s\n' "$hostport" "$name" "$hostip" "$act" "外露（数据面/管理面不该对外）"
          echo "$hostport" >> "${TMPDIR:-/tmp}/r12-bind-external.$$" ;;
        *127.0.0.1*未监听*)
          printf '  %-6s %-22s %-24s %-14s %s\n' "$hostport" "$name" "$hostip" "$act" "未监听（容器在但端口没起）" ;;
        *127.0.0.1*127.0.0.1*)
          printf '  %-6s %-22s %-24s %-14s %s\n' "$hostport" "$name" "$hostip" "$act" "仅回环" ;;
        *)
          printf '  %-6s %-22s %-24s %-14s %s\n' "$hostport" "$name" "$hostip" "$act" "未知，需人工判定" ;;
      esac
    done
  done <<< "$infra_rows"

  # host 网络容器的真实绑定地址（它们的端口不出现在 PortBindings 里）
  for hp in "18088:r12-fe(nginx)" "18095:r12-preview"; do
    port="${hp%%:*}"; who="${hp#*:}"
    act="$(actual_of "$port")"
    [ -n "$act" ] || act="(未监听)"
    allowed=0
    for a in $ALLOW_EXTERNAL; do [ "$a" = "$port" ] && allowed=1; done
    if [ "$allowed" = 1 ]; then
      case "$act" in *0.0.0.0*|*\**) verdict="批准对外入口（预期）" ;;
        *) verdict="批准入口未对外（客户端不可达）" ;; esac
    else
      case "$act" in
        *0.0.0.0*|*\**) verdict="外露（host 网络：需改容器内进程绑定地址）"
                        echo "$port" >> "${TMPDIR:-/tmp}/r12-bind-external.$$" ;;
        *127.0.0.1*) verdict="仅回环" ;;
        *) verdict="未知，需人工判定" ;;
      esac
    fi
    printf '  %-6s %-22s %-24s %-14s %s\n' "$port" "$who" "(host网络)" "$act" "$verdict"
  done
else
  warn "无 docker 命令，跳过容器监听面盘点"
fi

if [ -f "${TMPDIR:-/tmp}/r12-bind-external.$$" ]; then
  INFRA_EXT=$(sort -u "${TMPDIR:-/tmp}/r12-bind-external.$$" | wc -l | tr -d ' ')
  EXTLIST=$(sort -u "${TMPDIR:-/tmp}/r12-bind-external.$$" | paste -sd, -)
  rm -f "${TMPDIR:-/tmp}/r12-bind-external.$$"
  warn "基础设施/容器面有 $INFRA_EXT 个端口对外可达: $EXTLIST"
  external=$((external + INFRA_EXT))
else
  ok "基础设施/容器面未发现外露端口（批准对外: $ALLOW_EXTERNAL）"
fi

echo
if [ "$mismatch" -gt 0 ]; then warn "有 $mismatch 处“配置说回环、实际仍外露”——先确认服务是否重启/快照是否同步"; fi
if [ "$EXPECT" = 1 ]; then
  if [ "$external" -eq 0 ]; then ok "全部内部端口（应用面+基础设施面）仅监听回环"; exit 0
  else warn "仍有 $external 个端口对外可达（--expect-loopback 未满足）"; exit 1; fi
fi
[ "$external" -gt 0 ] && info "当前有 $external 个端口对外可达（未要求收紧，仅提示）"
exit 0
