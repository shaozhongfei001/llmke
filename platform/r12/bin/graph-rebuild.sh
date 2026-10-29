#!/usr/bin/env bash
# W03 整库图重建（清理陈旧边 + 重建社区摘要）
#
# 为什么需要它：
#   文档被删除后，kb_list 的行只是 status 变成 0（已删），但 Nebula 里由它抽出的
#   relationship 边仍然留着 —— 于是"幽灵事实"会继续参与社区检测与 global 问答，
#   引用还指向一个已经打不开的文件。图谱侧不会因为"文件删了"自动收回这些边。
#
# 用法:
#   graph-rebuild.sh <kbId>                 # 默认 dry-run，只统计，不写任何数据
#   graph-rebuild.sh <kbId> --apply         # 真正删除"仅来自已删文件"的边 + 重建社区摘要
#   graph-rebuild.sh <kbId> --apply --force-community
#                                           # 即使 0 条陈旧边也强制重建社区（默认会跳过）
#
# 步骤（每步打印 [ok]/[!!]/[FAIL]，任一步失败非零退出）：
#   0 环境前置：.env 口令 / docker 容器 / graph venv / 并发守卫
#     内容指纹（TL 裁决的版本绑定口径）：content_fingerprint = sha256(排序后逐文件
#       sha256("路径|内容"))，范围 = 9 个 index_graph_service py + rag-index-service **jar** +
#       部署态 application-r12.yml（整文件 hash）。HEAD 只作参考，不作判据。
#     硬判据 runtime_matches_content = 进程启动时间 **>** 内容文件最大 mtime（严格大于）；
#       为 false 时结论行会写"本次结果不作为代次对比依据"。
#   1 有效文件集合：MySQL knowledge_base_list.status=3
#   2 边来源统计：全图边数 / 仅来自已删文件 / 混合来源 / 无法判定
#   3 [--apply] 删除"仅来自已删文件"的边（逐条 DELETE EDGE type "src"->"dst"@rank）
#   4 [--apply] 调 /generate_community 重建社区摘要，打印 社区数/摘要数/失败数，并按新代
#              社区 id 清理 ES 里已经消失的旧摘要（Milvus 侧写入方本身是整代替换）
#   5 一致性校验：删除前后边数守恒、ES 摘要条数 == 本次摘要条数
#     附：抽取侧可复现性提示（grep R15-W01 EXTRACT_STATS / "单块重试：最终失败"），
#         只提示不改退出码——那行日志属于 W01 的工作包，硬绑会把本脚本拖成假红
#
# 安全边界（逐条都有理由，改之前先看 docs/r15/w03-rebuild.md）：
#   · 默认 dry-run；只有显式 --apply 才写。没有 --yes、没有隐式开关。
#   · 口令只从 platform/r12/.env 的 R12_MYSQL_ROOT_PASSWORD / 环境变量读，
#     脚本不写死任何口令，也不把口令放进命令行参数（走 docker exec -e MYSQL_PWD 转发）。
#   · "已删"= status 0 或该文件行已不存在；status 1/2/4（正常/解析中/解析失败）**不删**，
#     只报 [!!] 待人工确认 —— 把"解析失败"当"已删"会误删仍然可见资料的事实。
#   · 混合来源边（既有有效文件又有已删文件）**不删**：另一来源仍然支持它。
#   · file_id 为空 / 无法解析的边**不删**：来源未知，删了无法回滚。
#   · --apply 前若检测到并发重建/验收进程，默认拒绝（GRAPH_REBUILD_FORCE=1 可越过）。
#
# 退出码：0 全部通过；1 有步骤失败；2 前置条件/用法错误（未产生任何写入）。
set -uo pipefail

R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$R12/../.." && pwd)"
PY_BIN="$R12/venvs/graph/bin/python"
ENV_FILE="${R12_ENV_FILE:-$R12/.env}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-r12-mysql}"

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1" >&2; exit "${2:-2}"; }
usage() {
  cat >&2 <<'EOF'
用法:
  graph-rebuild.sh <kbId>                              # 默认 dry-run，只统计不写
  graph-rebuild.sh <kbId> --apply                      # 删陈旧边 + 重建社区摘要
  graph-rebuild.sh <kbId> --apply --force-community    # 0 条陈旧边也强制重建社区
  graph-rebuild.sh <kbId> --apply --strict-extract     # 抽取侧"重试最终失败>0"也算失败
EOF
}

KB_ID=""
APPLY=0
FORCE_COMMUNITY=0
STRICT_EXTRACT=0
for a in "$@"; do
  case "$a" in
    --apply)           APPLY=1 ;;
    --force-community) FORCE_COMMUNITY=1 ;;
    --strict-extract)  STRICT_EXTRACT=1 ;;
    -h|--help)         usage; exit 0 ;;
    -*)                printf '未知参数: %s\n' "$a" >&2; usage; exit 2 ;;
    *)                 [ -z "$KB_ID" ] || { printf '只接受一个 kbId\n' >&2; usage; exit 2; }
                       KB_ID="$a" ;;
  esac
done
[ -n "$KB_ID" ] || { usage; exit 2; }
case "$KB_ID" in ''|*[!0-9]*) die "kbId 必须是数字，收到: $KB_ID" 2 ;; esac

MODE="DRY-RUN"
[ "$APPLY" -eq 1 ] && MODE="APPLY"

echo "== W03 graph-rebuild =="
printf '  [..] kb=%s  mode=%s  script=%s\n' "$KB_ID" "$MODE" "${BASH_SOURCE[0]}"

# ---------------------------------------------------------------- [0/5] 前置
echo "== [0/5] 环境前置 =="
[ -x "$PY_BIN" ] || die "缺少 graph venv 解释器: $PY_BIN"
ok "python: $PY_BIN"

if [ ! -f "$ENV_FILE" ]; then
  die "缺少 $ENV_FILE：无法取得 R12_MYSQL_ROOT_PASSWORD（脚本不提供内置口令）"
fi
# 只挑口令键读入，其余键不导出，避免把无关秘密带进子进程
while IFS= read -r line; do
  line="${line%$'\r'}"                 # 兼容 CRLF 的 .env，否则口令尾部会多一个 \r
  case "$line" in ''|\#*) continue ;; esac
  key="${line%%=*}"; val="${line#*=}"
  case "$key" in
    R12_MYSQL_ROOT_PASSWORD|MYSQL_ROOT_PASSWORD) [ -n "${!key:-}" ] || export "$key=$val" ;;
  esac
done < "$ENV_FILE"
ROOT_PW="${R12_MYSQL_ROOT_PASSWORD:-${MYSQL_ROOT_PASSWORD:-}}"
[ -n "$ROOT_PW" ] || die "$ENV_FILE 里没有 R12_MYSQL_ROOT_PASSWORD / MYSQL_ROOT_PASSWORD"
ok "MySQL 口令已从 $ENV_FILE 读取（值不打印）"
# docker exec -e MYSQL_PWD（不带 =值）从宿主环境转发：口令不进 argv，ps 看不到
export MYSQL_PWD="$ROOT_PW"

command -v docker >/dev/null 2>&1 || die "找不到 docker 命令"
docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$MYSQL_CONTAINER" \
  || die "MySQL 容器 $MYSQL_CONTAINER 未运行"
ok "MySQL 容器 $MYSQL_CONTAINER 运行中"

if [ "$APPLY" -eq 1 ]; then
  if [ "${GRAPH_REBUILD_FORCE:-0}" != "1" ]; then
    # 用 pgrep 而不是 ps|grep：pgrep 不会匹配自己，命令替换子 shell 也不会误命中
    busy="$(pgrep -af 'rebuild_kb9|generate_triple|acceptance\.py' 2>/dev/null || true)"
    if [ -n "$busy" ]; then
      printf '%s\n' "$busy" | sed 's/^/       /'
      die "检测到可能的并发重建/验收进程；图断言与删除会互相踩。确认无并发后重试，或 GRAPH_REBUILD_FORCE=1 强行越过"
    fi
    ok "无并发重建/验收进程"
  else
    warn "GRAPH_REBUILD_FORCE=1：已跳过并发守卫（后果自负）"
  fi
else
  ok "dry-run：并发守卫不生效（本模式只读）"
fi

# ---------------------------------------------------------------- [1-5/5] 主体
# 主体用 graph venv + nebula3 直连 Nebula，不依赖 nebula-console；REST 用 requests。
KB_ID="$KB_ID" \
MODE="$MODE" \
FORCE_COMMUNITY="$FORCE_COMMUNITY" \
STRICT_EXTRACT="$STRICT_EXTRACT" \
MYSQL_CONTAINER="$MYSQL_CONTAINER" \
REPO="$REPO" \
"$PY_BIN" - <<'PY'
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time

import requests
from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool

KB_ID = os.environ["KB_ID"]
MODE = os.environ["MODE"]
FORCE_COMMUNITY = os.environ.get("FORCE_COMMUNITY", "0") == "1"
APPLY = MODE == "APPLY"
CONTAINER = os.environ.get("MYSQL_CONTAINER", "r12-mysql")
REPO = os.environ.get("REPO", "")
SVC_DIR = "services/rag-alg/index_data_service/index_graph_service"
# W03-2 版本绑定（TL 2026-10-29 裁决 = 方案 c：内容哈希）。
# 文件集合**由 TL 指定，不要自己扩**；扩了会让所有历史 fingerprint 不可比。
CONTENT_PY = ("base.py", "graph_community.py", "graph_extract.py", "graph_fun_tool.py",
              "graph_service.py", "graph_summary.py", "graph_types.py",
              "prompt_config.py", "utils.py")
# Java 取 **构建产物 jar** 的 sha256：源码改了没重编，源码 hash 代表不了运行版本
JAR_GLOB = "services/rag-java/rag-parent/rag-index-service/target/rag-index-service-*.jar"
# 配置只取部署态那份：进程读的是它（源码树里的 resources 副本只作参考，不进指纹）
CFG_FILE = "platform/r12/conf/rag-index-service/application-r12.yml"
STRICT_EXTRACT = os.environ.get("STRICT_EXTRACT", "0") == "1"

GRAPH = os.environ.get("GRAPH", "http://127.0.0.1:19529")
ES = os.environ.get("ES", "http://127.0.0.1:19200")
NEBULA = (os.environ.get("NEBULA_HOST", "127.0.0.1"), int(os.environ.get("NEBULA_PORT", "19669")))
NEBULA_USER = os.environ.get("NEBULA_USER", "root")
NEBULA_PASS = os.environ.get("NEBULA_PASS", "nebula")
DB = os.environ.get("W03_MYSQL_DB", "gienrag")
# 与 platform/r12/qa/evidence/R14-A-20261027T021902Z/probe_community_twice.py 同一个 body，
# 改这里必须同步那份证据脚本，否则两边社区数不可比。
MODEL_INFO = {
    "model_id": os.environ.get("GRAPH_LLM_MODEL", "qwen2.5-7b-instruct"),
    "url": os.environ.get("GRAPH_LLM_URL", "http://127.0.0.1:18092/v1/chat/completions"),
    "key": os.environ.get("GRAPH_LLM_KEY", "sk-r12-local"),
}
EDGE_TYPE = "relationship"   # 只有它带 file_id；relationship_similar 无来源属性，不参与
STATUS_VALID = 3             # 0删除 1正常 2解析中 3解析成功 4解析失败


class StepFail(Exception):
    pass


def ok(m):
    print("  [ok] %s" % m, flush=True)


def warn(m):
    print("  [!!] %s" % m, flush=True)


def stepfail(m):
    raise StepFail(m)


_CLEANUP = []


def _cleanup():
    """会话先 release 再关池，否则 nebula3 会打 'Closing a connection that is in use'。"""
    for obj in reversed(_CLEANUP):
        try:
            if hasattr(obj, "release"):
                obj.release()
            else:
                obj.close()
        except Exception:  # noqa: BLE001
            pass


def ngql_str(s):
    """把任意 vid 变成合法 nGQL 字符串字面量（vid 是中文/带引号都要能删）。"""
    out = str(s).replace("\\", "\\\\").replace('"', '\\"')
    out = out.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return '"' + out + '"'


def _run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except Exception as exc:  # noqa: BLE001
        return 1, "", "%s: %s" % (type(exc).__name__, exc)


def _sha256_file(path):
    """sha256(路径|内容) 的分项：前缀写路径，再流式喂内容（jar 225MB，不整读进内存）。"""
    h = hashlib.sha256()
    rel = os.path.relpath(path, REPO).replace(os.sep, "/")
    h.update(rel.encode("utf-8")); h.update(b"|")
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return rel, h.hexdigest()


def build_fingerprint():
    """W03-2 版本绑定：content_fingerprint（TL 2026-10-29 裁决 = 内容哈希）。

    为什么不用 commit：实测 95 秒内 `worktree == HEAD` 就翻面（文件被提交），而进程根本没重启；
    commit 只代表"仓库某一刻的样子"，不代表"进程加载的字节"。所以：
      · 判据 = content_fingerprint（9 个 py + jar + 部署态 yml）
      · 硬判据 = runtime_matches_content = 进程启动时间 **>** 内容文件最大 mtime（严格大于：
        同一秒重启可能读到半写文件）
      · HEAD / worktree 脏只作参考字段，不作判据
    算法：按路径排序，逐文件算 sha256("相对路径|内容")，把这些 hex 用 "\\n" 连接后再 sha256。
    """
    print("  -- 内容指纹（版本绑定硬判据：进程加载的字节）--", flush=True)
    fp = {"service_pid": None, "service_start": None, "content_files": 0,
          "runtime_matches_content": None, "content_max_mtime": None, "content_max_file": None}

    # 1) 收集文件集合（集合由 TL 定；缺文件要显式报，不能静默缩小指纹口径）
    paths = []
    for name in CONTENT_PY:
        p = os.path.join(REPO, SVC_DIR, name)
        if os.path.exists(p):
            paths.append(p)
        else:
            warn("内容指纹缺文件（跳过，指纹口径变小）: %s/%s" % (SVC_DIR, name))
    jars = sorted(glob.glob(os.path.join(REPO, JAR_GLOB)))
    if jars:
        jar = max(jars, key=os.path.getmtime)
        paths.append(jar)
        fp["jar"] = os.path.relpath(jar, REPO)
    else:
        warn("找不到 rag-index-service 的 jar（%s）：Java 侧运行版本无法绑定" % JAR_GLOB)
    cfg = os.path.join(REPO, CFG_FILE)
    if os.path.exists(cfg):
        paths.append(cfg)
        fp["config"] = CFG_FILE
    else:
        warn("找不到部署态配置 %s" % CFG_FILE)

    if not paths:
        warn("一个内容文件都没找到，无法计算 content_fingerprint")
        return fp

    # 2) 逐项 sha256(路径|内容) → 排序拼接 → 再 sha256
    items, per, mts = [], {}, []
    for p in sorted(paths, key=lambda x: os.path.relpath(x, REPO)):
        rel, h = _sha256_file(p)
        items.append(h)
        per[os.path.basename(rel)] = h[:12]
        mts.append((os.path.getmtime(p), os.path.basename(rel)))
    fp["content_fingerprint"] = hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()
    fp["content_files"] = len(items)
    fp["per_file"] = per
    ok("content_fingerprint=%s（%d 项：%d py + %s + %s）"
       % (fp["content_fingerprint"][:16] + "…", len(items), len(CONTENT_PY),
          "jar" if fp.get("jar") else "无 jar", "yml(整文件 hash)" if fp.get("config") else "无 yml"))
    print("      逐项: %s" % ", ".join("%s=%s" % (k, v) for k, v in sorted(per.items())), flush=True)

    # 3) 硬判据：进程启动 > 内容文件最大 mtime
    mt, mt_name = max(mts)
    fp["content_max_mtime"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(mt))
    fp["content_max_file"] = mt_name

    rc, out, _ = _run(["pgrep", "-af", "graph_api_start"])
    pids = [int(ln.split()[0]) for ln in out.splitlines() if ln.strip() and ln.split()[0].isdigit()]
    if not pids:
        warn("没有 graph_api_start 进程在跑：runtime_matches_content 无法判定（第 4 步也会失败）")
        fp["runtime_matches_content"] = False
        fp["comparable"] = False
        return fp
    pid = max(pids)   # 多个 PID 时取最新那个（父子进程同时匹配时，子进程才是真正干活的）
    _rc, et, _ = _run(["ps", "-o", "etimes=", "-p", str(pid)])
    if not et.strip().isdigit():
        warn("拿不到 graph 服务启动时间（PID %d）" % pid)
        fp["runtime_matches_content"] = False
        fp["comparable"] = False
        return fp
    start = time.time() - int(et.strip())
    fp["service_pid"] = pid
    fp["service_start"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(start))
    fp["runtime_matches_content"] = bool(start > mt)
    fp["comparable"] = fp["runtime_matches_content"]
    if fp["runtime_matches_content"]:
        ok("runtime_matches_content=true：进程(PID %d, %s) 晚于 %s 的 mtime %s -> 本次结果可用于代次对比"
           % (pid, fp["service_start"], mt_name, fp["content_max_mtime"]))
    else:
        warn("runtime_matches_content=false：进程(PID %d) 启动于 %s，不晚于 %s 的 mtime %s "
             "-> 进程加载的不是当前内容；本次结果不作为代次对比依据"
             % (pid, fp["service_start"], mt_name, fp["content_max_mtime"]))

    # 4) HEAD / 工作树只作参考（实测会翻面，不能当判据）
    rc, head, _ = _run(["git", "-C", REPO, "rev-parse", "HEAD"])
    fp["head"] = head if rc == 0 and head else None
    if fp["head"]:
        _rc, desc, _ = _run(["git", "-C", REPO, "log", "-1", "--format=%s"])

        def _dirty(pathspec):
            # 不能用 ln[3:]：git status 首行的 " M " 前缀被整体 strip 后错位一格，会截出 "latform/..."
            rc2, out2, _ = _run(["git", "-C", REPO, "status", "--porcelain", "--"] + pathspec)
            if rc2 != 0 or not out2:
                return []
            return [ln.split(None, 1)[-1].strip() for ln in out2.splitlines() if ln.strip()]

        fp["dirty"] = _dirty([SVC_DIR])
        fp["script_dirty"] = _dirty(["platform/r12/bin"])
        print("      [参考] HEAD=%s %s；服务源码脏=%d 项%s（仅供参考，不作判据）"
              % (head[:7], desc[:60], len(fp["dirty"]),
                 "" if not fp["dirty"] else "：" + ", ".join(os.path.basename(d) for d in fp["dirty"][:4])),
              flush=True)
    return fp


def extract_stats_advisory():
    """抽取侧可复现性提示（来自 R15-W01 的单行 stats）。**只提示，不改退出码**。

    为什么不当硬闸门：那行日志格式属于 W01 的工作包，把本脚本的成败绑在别人的日志
    文本上，一旦该行改名/下线就会红得莫名其妙。真正的判据是第 [5/5] 步的边数守恒与
    摘要对数；这里只负责把"边数变了"拆成"抽取侧不可复现"还是"替换逻辑有问题"。
    """
    print("  -- 抽取侧可复现性（R15-W01 EXTRACT_STATS，仅提示）--", flush=True)
    d = os.environ.get("GRAPH_LOG_DIR") or os.path.join(REPO, SVC_DIR, "logs", "graph_service")
    # 只读当天的 loguru 文件；**不要**扫 platform/r12/logs/index_graph_service.log（同一行会重复计）
    cand = os.path.join(d, "graph_info_%s.log" % time.strftime("%Y-%m-%d"))
    files = [cand] if os.path.exists(cand) else sorted(glob.glob(os.path.join(d, "graph_info_*.log")))[-1:]
    if not files:
        warn("找不到 graph_info_*.log（%s），跳过" % d)
        return {}
    pat = re.compile(r"R15-W01 EXTRACT_STATS(.*)$")
    kv = re.compile(r"(\w+)=(-?\d+)")
    seen, agg, fails = set(), {}, 0
    for path in files:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "单块重试：最终失败" in line:
                        fails += 1
                    m = pat.search(line)
                    if not m:
                        continue
                    d2 = dict((k, int(v)) for k, v in kv.findall(m.group(1)))
                    sig = (d2.get("passage"), d2.get("elapsed_ms"))   # 两个 sink 会写同一行，去重
                    if sig in seen:
                        continue
                    seen.add(sig)
                    for k, v in d2.items():
                        agg[k] = agg.get(k, 0) + v
        except Exception as exc:  # noqa: BLE001
            warn("读 %s 失败: %s" % (path, exc))
    if not seen:
        warn("%s 里没有 R15-W01 EXTRACT_STATS（该工作包未生效或日志已轮转），跳过" % os.path.basename(files[0]))
        return {"log": os.path.basename(files[0]), "passages": 0}
    per = (agg.get("elapsed_ms", 0) / 1000.0 / agg["llm_calls"]) if agg.get("llm_calls") else 0
    ok("passage %d 个：llm_calls=%d retries=%d parse_failed_lines=%d field_anomalies=%d "
       "valid_triples=%d，平均 %.1fs/次调用"
       % (len(seen), agg.get("llm_calls", 0), agg.get("retries", 0), agg.get("parse_failed_lines", 0),
          agg.get("field_anomalies", 0), agg.get("valid_triples", 0), per))
    if fails:
        warn("'单块重试：最终失败' %d 次 -> 该 passage 贡献 0 事实，边数不可复现，"
             "不要用它做代次对比，先重跑该 passage" % fails)
    if agg.get("parse_failed_lines") or agg.get("field_anomalies"):
        warn("parse_failed_lines=%d / field_anomalies=%d：抽取输出有结构问题，边数会漂"
             % (agg.get("parse_failed_lines", 0), agg.get("field_anomalies", 0)))
    return {"log": os.path.basename(files[0]), "passages": len(seen), "retry_final_fail": fails,
            "llm_calls": agg.get("llm_calls", 0), "retries": agg.get("retries", 0),
            "parse_failed_lines": agg.get("parse_failed_lines", 0),
            "field_anomalies": agg.get("field_anomalies", 0),
            "valid_triples": agg.get("valid_triples", 0),
            "secs_per_call": round(per, 1)}


def mysql_rows(sql):
    """docker exec -e MYSQL_PWD -i：口令由宿主环境转发，不出现在 argv 里。"""
    p = subprocess.run(
        ["docker", "exec", "-e", "MYSQL_PWD", "-i", CONTAINER,
         "mysql", "-uroot", "-N", "-B", "-e", sql],
        capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError("mysql 失败: %s" % (p.stderr or "").strip()[:300])
    rows = []
    for line in (p.stdout or "").splitlines():
        if line.strip() == "":
            continue
        rows.append(line.split("\t"))
    return rows


def http_json(method, url, body=None, timeout=60):
    if method == "GET":
        r = requests.get(url, timeout=timeout)
    elif method == "DELETE":
        r = requests.delete(url, timeout=timeout)
    else:
        r = requests.post(url, json=body, timeout=timeout)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"_raw": (r.text or "")[:300]}


def es_count(index):
    code, js = http_json("GET", "%s/%s/_count" % (ES, index), timeout=30)
    if code == 200:
        return js.get("count", 0)
    if code == 404:
        return 0
    raise RuntimeError("ES _count %s -> http %s %s" % (index, code, json.dumps(js, ensure_ascii=False)[:200]))


# ---------------------------------------------------------------- [1/5]
def step_files(primitive):
    print("== [1/5] 有效文件集合（MySQL knowledge_base_list.status=3）==", flush=True)
    rows = mysql_rows("select status, count(*) from `%s`.knowledge_base_list where kb_id=%s group by status"
                      % (DB, KB_ID))
    by_status = {}
    for r in rows:
        if len(r) >= 2 and r[0] not in ("NULL", ""):
            by_status[int(r[0])] = int(r[1])
    if not by_status:
        stepfail("kb %s 在 knowledge_base_list 里没有任何文件行" % KB_ID)
    total_rows = sum(by_status.values())
    ok("文件行 %d 条，按 status 分布 %s"
       % (total_rows, ", ".join("%s=%d" % (k, v) for k, v in sorted(by_status.items()))))
    valid = set(int(r[0]) for r in
                mysql_rows("select id from `%s`.knowledge_base_list where kb_id=%s and status=%d"
                           % (DB, KB_ID, STATUS_VALID)) if r and r[0] not in ("NULL", ""))
    if not valid:
        stepfail("kb %s 没有 status=3（解析成功）的文件；无法判定哪些边还有效，拒绝继续" % KB_ID)
    ok("有效文件 %d 个: %s" % (len(valid), ",".join(str(x) for x in sorted(valid))))

    # 其余状态要显式报出来：把"已删"和"解析失败/正常未解析"混成一类是最常见的误删来源
    others = {k: v for k, v in by_status.items() if k != STATUS_VALID}
    if others:
        label = {0: "0=已删", 1: "1=正常(未解析完成)", 2: "2=解析中", 4: "4=解析失败"}
        warn("非有效状态: %s —— 其中只有 0 与'行不存在'算已删，1/2/4 不会被删除"
             % ", ".join("%s %d 条" % (label.get(k, "%d=未知" % k), v) for k, v in sorted(others.items())))

    st_map = {}
    for r in mysql_rows("select id, status from `%s`.knowledge_base_list where kb_id=%s" % (DB, KB_ID)):
        if len(r) >= 2 and r[0] not in ("NULL", ""):
            st_map[int(r[0])] = int(r[1]) if r[1] not in ("NULL", "") else None
    return valid, st_map


# ---------------------------------------------------------------- [2/5]
def enumerate_edges(sess, space):
    """两种独立口径枚举 relationship 边，返回 (rows, note)。
    rows: [(src, dst, rank:int, file_id:str)]，按 (src,dst,rank) 去重。
    rows 里带不上 file_id 的边就是"来源未知"，只统计不删。
    """
    q_match = ("MATCH (a)-[e:%s]->(b) RETURN id(a) AS s, id(b) AS d, rank(e) AS rk, "
               "e.file_id AS fid" % EDGE_TYPE)
    q_go = ("LOOKUP ON entity YIELD id(vertex) AS vid | GO FROM $-.vid OVER %s "
            "YIELD src(edge) AS s, dst(edge) AS d, rank(edge) AS rk, "
            "properties(edge).file_id AS fid" % EDGE_TYPE)

    def run(q):
        r = sess.execute(q)
        if not r.is_succeeded():
            return None, r.error_msg()
        out = []
        for i in range(r.row_size()):
            v = r.row_values(i)
            src = v[0].as_string() if hasattr(v[0], "as_string") else str(v[0])
            dst = v[1].as_string() if hasattr(v[1], "as_string") else str(v[1])
            rk = v[2].as_int() if hasattr(v[2], "as_int") else int(v[2])
            try:
                fid = v[3].as_string() if hasattr(v[3], "as_string") else str(v[3])
            except Exception:
                fid = ""
            out.append((src, dst, int(rk), fid if fid != "__EMPTY__" else ""))
        return out, None

    m_rows, m_err = run(q_match)
    g_rows, g_err = run(q_go)
    if m_rows is None and g_rows is None:
        stepfail("两条枚举口径都失败: MATCH=%s / LOOKUP+GO=%s" % (m_err, g_err))
    note = []
    if m_rows is None:
        note.append("MATCH 口径失败(%s)，只用 LOOKUP+GO" % m_err)
        base = g_rows
    elif g_rows is None:
        note.append("LOOKUP+GO 口径失败(%s)，只用 MATCH" % g_err)
        base = m_rows
    else:
        # 交叉校验：两个口径行数不一致说明有边落在"无 tag 顶点"上，或查询本身不确定
        if len(m_rows) != len(g_rows):
            note.append("交叉校验不一致：MATCH=%d / LOOKUP+GO=%d（无 tag 端点或读路径不一致）"
                        % (len(m_rows), len(g_rows)))
        base = m_rows if len(m_rows) >= len(g_rows) else g_rows
    dedup = {}
    for row in base:
        dedup[(row[0], row[1], row[2])] = row
    dup = len(base) - len(dedup)
    if dup:
        note.append("枚举结果有 %d 行同 (src,dst,rank) 重复，已去重" % dup)
    return sorted(dedup.values(), key=lambda x: (x[0], x[1], x[2])), note


def classify(edges, valid, st_map):
    """把每条边分到 5 个桶。判定规则写在 docs/r15/w03-rebuild.md §3，改这里必须同步文档。"""
    buckets = {"valid": [], "stale": [], "mixed": [], "pending": [], "unknown": []}
    for e in edges:
        fids = [x.strip() for x in str(e[3] or "").split(",") if x.strip()]
        if not fids:
            buckets["unknown"].append(e)
            continue
        kinds = {}
        for f in fids:
            try:
                i = int(f)
            except (TypeError, ValueError):
                kinds.setdefault("unparsable", []).append(f)
                continue
            st = st_map.get(i, "missing")
            if st == STATUS_VALID:
                kinds.setdefault("valid", []).append(f)
            elif st == 0 or st == "missing":
                kinds.setdefault("stale", []).append(f)
            else:
                kinds.setdefault("pending", []).append(f)   # 1/2/4：文件行还在
        if kinds.get("unparsable") or kinds.get("pending"):
            buckets["pending"].append(e)
        elif kinds.get("valid") and kinds.get("stale"):
            buckets["mixed"].append(e)
        elif kinds.get("stale"):
            buckets["stale"].append(e)
        elif kinds.get("valid"):
            buckets["valid"].append(e)
        else:
            buckets["unknown"].append(e)
    return buckets


def report_buckets(edges, buckets):
    total = len(edges)
    print("  全图 %s 边合计 %d 条" % (EDGE_TYPE, total), flush=True)

    def line(name, items, note, action):
        msg = "%-30s: %d  %s" % (name, len(items), note)
        if action:
            warn(msg)
        else:
            ok(msg)

    line("仅来自有效文件(status=3)", buckets["valid"], "保留", False)
    line("仅来自已删文件(0/行不存在)", buckets["stale"],
         "--apply 时逐条 DELETE EDGE" if buckets["stale"] else "无陈旧边", bool(buckets["stale"]))
    line("混合来源(有效+已删)", buckets["mixed"], "不删：另一来源仍支持该事实", bool(buckets["mixed"]))
    line("待确认(status 1/2/4 或 file_id 非法)", buckets["pending"], "不删：文件行还在，需人工判定",
         bool(buckets["pending"]))
    line("来源未知(file_id 为空)", buckets["unknown"], "不删：删了无据可依", bool(buckets["unknown"]))
    if buckets["mixed"]:
        warn("混合来源边示例（前 3 条）: %s"
             % json.dumps([{"src": e[0], "dst": e[1], "rank": e[2], "file_id": e[3]}
                           for e in buckets["mixed"][:3]], ensure_ascii=False))
    if buckets["pending"]:
        warn("待确认边示例（前 3 条）: %s"
             % json.dumps([{"src": e[0], "dst": e[1], "rank": e[2], "file_id": e[3]}
                           for e in buckets["pending"][:3]], ensure_ascii=False))
    if buckets["unknown"]:
        warn("来源未知边示例（前 3 条）: %s"
             % json.dumps([{"src": e[0], "dst": e[1], "rank": e[2]} for e in buckets["unknown"][:3]],
                          ensure_ascii=False))


# ---------------------------------------------------------------- [3/5]
def delete_stale(sess, stale):
    print("== [3/5] 删除陈旧边（逐条 DELETE EDGE，无批量、无 DROP SPACE）==", flush=True)
    print("  计划语句示例:", flush=True)
    for e in stale[:5]:
        print("    DELETE EDGE %s %s->%s@%d" % (EDGE_TYPE, ngql_str(e[0]), ngql_str(e[1]), e[2]), flush=True)
    if len(stale) > 5:
        print("    ... 共 %d 条" % len(stale), flush=True)

    done, failed = 0, []
    for e in stale:
        stmt = "DELETE EDGE %s %s->%s@%d" % (EDGE_TYPE, ngql_str(e[0]), ngql_str(e[1]), e[2])
        r = sess.execute(stmt)
        if r.is_succeeded():
            done += 1
        else:
            failed.append({"edge": [e[0], e[1], e[2], e[3]], "err": r.error_msg()[:200]})
        if done and done % 50 == 0:
            print("    .. 已删除 %d/%d" % (done, len(stale)), flush=True)
    if failed:
        for f in failed[:5]:
            warn("删除失败: %s -> %s" % (json.dumps(f["edge"], ensure_ascii=False), f["err"]))
        stepfail("%d/%d 条边删除失败（部分写入，需人工复核；脚本未回滚）" % (len(failed), len(stale)))
    ok("已删除 %d 条陈旧边" % done)
    return done


# ---------------------------------------------------------------- [4/5]
def rebuild_community(primitive):
    print("== [4/5] 重建社区摘要（POST /generate_community）==", flush=True)
    es_index = "community_summary_" + primitive.lower()   # ES 名必须 lower（is_index_lower）
    before_docs = es_count(es_index)
    print("  重建前 ES %s 摘要 %d 条" % (es_index, before_docs), flush=True)

    body = {"space_name": primitive, "max_level": 2, "min_community_size": 3,
            "resolution": 1.0, "with_summary": True, "model_info": MODEL_INFO}
    t0 = time.time()
    try:
        code, js = http_json("POST", GRAPH + "/generate_community", body, timeout=1800)
    except Exception as exc:
        stepfail("调用 /generate_community 失败: %s: %s" % (type(exc).__name__, str(exc)[:200]))
    secs = time.time() - t0
    print("  http=%s 用时 %.1fs  msg=%s" % (code, secs, str(js.get("msg"))[:160]), flush=True)
    payload = js.get("data") or {}
    if code != 200:
        stepfail("HTTP %s（/generate_community 不可用）" % code)
    if js.get("code") != 200:
        stepfail("业务码 %s：%s（ES/Milvus 写入异常时服务返回 500，不能当成功）"
                 % (js.get("code"), str(js.get("msg"))[:200]))

    communities = int(payload.get("communities") or 0)
    summaries = int(payload.get("summaries") or 0)
    failures = payload.get("failures") or []
    ok("社区数 %d / 摘要数 %d / 失败数 %d（es_ok=%s milvus_ok=%s）"
       % (communities, summaries, len(failures), payload.get("es_ok"), payload.get("milvus_ok")))

    if communities == 0:
        # 合法空：图太小/边太少，服务直接回 code=200 + "未检测到满足条件的社区（图可能过小）"。
        # 这不是故障（A06「合法空资料不冒充故障」），保留旧摘要、不判失败，只把事实记进 RESULT。
        warn("本次未检测到满足条件的社区（图可能过小）：属合法空，保留旧摘要不动，不判失败")
        after_docs = es_count(es_index)
        print("  重建后 ES %s 摘要 %d 条（重建前 %d，未改动）" % (es_index, after_docs, before_docs), flush=True)
        return {"communities": 0, "summaries": 0, "failures": 0, "empty_graph": True,
                "es_index": es_index, "es_before": before_docs, "es_after": after_docs,
                "es_removed": 0, "secs": round(secs, 1)}
    if failures:
        warn("摘要失败明细（前 3 条）: %s"
             % json.dumps([{"community_id": f.get("community_id"), "reason": f.get("reason")}
                           for f in failures[:3]], ensure_ascii=False))
    if payload.get("es_ok") is False or payload.get("milvus_ok") is False:
        stepfail("摘要索引写入失败（es_ok=%s milvus_ok=%s）：%s"
                 % (payload.get("es_ok"), payload.get("milvus_ok"), str(js.get("msg"))[:200]))
    if summaries == 0:
        # 检测到社区却一条摘要都没写出来 = 这一步真失败了（LLM 全挂/写入全失败），不能当"图太小"
        stepfail("检测到 %d 个社区但摘要 0 条（LLM 或索引写入失败）：保留旧摘要不动，本次重建不算成功"
                 % communities)

    # ES 侧残留清理：Milvus 写入方对社区集合是"整代替换"，ES 侧只按派生 _id 覆盖，
    # 社区变少时旧摘要会留下（global 仍会读到上一代的社区）。这里按本次新代的
    # community_id 反向清理，避免"新旧摘要混在一代里"。
    new_ids = set()
    for d in (payload.get("community_detail") or []):
        cid = d.get("community_id")
        if cid:
            new_ids.add(str(cid))
    removed, kept, unlabeled = 0, 0, 0
    if new_ids:
        code, js2 = http_json("POST", "%s/%s/_search" % (ES, es_index),
                              {"size": 1000, "_source": ["metadata.community_id"]}, timeout=60)
        if code == 404:
            warn("ES 索引 %s 不存在（本次未写入？）" % es_index)
        elif code != 200:
            stepfail("读取 %s 文档失败: http %s" % (es_index, code))
        else:
            hits = ((js2.get("hits") or {}).get("hits")) or []
            for h in hits:
                md = (h.get("_source") or {}).get("metadata") or {}
                cid = md.get("community_id")
                if cid and str(cid) in new_ids:
                    kept += 1
                    continue
                if not cid:
                    unlabeled += 1
                dc, _dj = http_json("DELETE", "%s/%s/_doc/%s" % (ES, es_index, h.get("_id")), timeout=30)
                if dc in (200, 201, 202):
                    removed += 1
                else:
                    warn("删除旧摘要 %s 失败: http %s" % (h.get("_id"), dc))
            ok("ES 按新代 community_id 清理：命中新代 %d 条，删除旧代 %d 条%s"
               % (kept, removed, ("，无 community_id 字段 %d 条" % unlabeled) if unlabeled else ""))
    else:
        warn("响应里没有 community_detail，跳过 ES 旧摘要清理（无法判定哪些是新代）")

    after_docs = es_count(es_index)
    print("  重建后 ES %s 摘要 %d 条（重建前 %d）" % (es_index, after_docs, before_docs), flush=True)
    return {"communities": communities, "summaries": summaries, "failures": len(failures),
            "es_index": es_index, "es_before": before_docs, "es_after": after_docs,
            "es_removed": removed, "secs": round(secs, 1)}


# ---------------------------------------------------------------- main
def main():
    result = {"kb": KB_ID, "mode": MODE, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    try:
        rows = mysql_rows("select primitive_name from `%s`.knowledge_base where id=%s" % (DB, KB_ID))
        primitive = (rows[0][0] if rows and rows[0] else "").strip()
        if not primitive or primitive == "NULL":
            stepfail("knowledge_base 里找不到 kb %s 或 primitive_name 为空" % KB_ID)
        space = primitive if primitive.startswith("g_") else "g_" + primitive
        result.update({"primitive": primitive, "space": space})
        ok("primitive_name=%s  Nebula space=%s" % (primitive, space))
        result["fingerprint"] = build_fingerprint()

        valid, st_map = step_files(primitive)

        # Nebula
        cfg = Config()
        cfg.max_connection_pool_size = 3
        pool = ConnectionPool()
        if not pool.init([NEBULA], cfg):
            stepfail("连接 Nebula %s:%s 失败" % NEBULA)
        _CLEANUP.append(pool)
        sess = pool.get_session(NEBULA_USER, NEBULA_PASS)
        _CLEANUP.append(sess)
        r = sess.execute("USE `%s`" % space)
        if not r.is_succeeded():
            stepfail("Nebula 空间 %s 不存在或不可用: %s" % (space, r.error_msg()[:200]))
        ok("Nebula %s:%s 空间 %s 已选中" % (NEBULA[0], NEBULA[1], space))

        print("== [2/5] 边来源统计 ==", flush=True)
        edges, notes = enumerate_edges(sess, space)
        for n in notes:
            warn(n)
        buckets = classify(edges, valid, st_map)
        report_buckets(edges, buckets)
        result.update({"edges_total": len(edges), "edge_valid": len(buckets["valid"]),
                       "edge_stale": len(buckets["stale"]), "edge_mixed": len(buckets["mixed"]),
                       "edge_pending": len(buckets["pending"]), "edge_unknown": len(buckets["unknown"])})

        if APPLY:
            if buckets["stale"]:
                deleted = delete_stale(sess, buckets["stale"])
            else:
                deleted = 0
                ok("0 条陈旧边，无需删除")
            result["deleted"] = deleted
        else:
            print("== [3/5] 删除陈旧边：dry-run 跳过（加 --apply 才执行）==", flush=True)
            if buckets["stale"]:
                print("  将删除 %d 条；示例语句：" % len(buckets["stale"]), flush=True)
                for e in buckets["stale"][:5]:
                    print("    DELETE EDGE %s %s->%s@%d"
                          % (EDGE_TYPE, ngql_str(e[0]), ngql_str(e[1]), e[2]), flush=True)

        # [4] 社区重建
        need_community = APPLY and (buckets["stale"] or FORCE_COMMUNITY)
        if need_community:
            try:
                result["community"] = rebuild_community(primitive)
            except StepFail:
                if buckets["stale"]:
                    warn("边已删除但社区重建失败：图与社区摘要现在不同代，需要重跑本脚本（加的 --apply 会幂等）")
                raise
        elif APPLY:
            warn("0 条陈旧边且未加 --force-community：图没变，跳过 /generate_community（省 LLM 且不动索引）")
        else:
            try:
                code, js = http_json("GET", GRAPH + "/openapi.json", timeout=8)
                ok("图服务可达（http %s）：--apply 时会调 /generate_community 重建社区摘要" % code)
            except Exception as exc:
                warn("图服务 %s 不可达（%s）：--apply 会在第 4 步失败" % (GRAPH, type(exc).__name__))
            print("== [4/5] 重建社区摘要：dry-run 跳过 ==", flush=True)

        # [5] 一致性校验
        print("== [5/5] 一致性校验 ==", flush=True)
        after, _notes2 = enumerate_edges(sess, space)
        b2 = classify(after, valid, st_map)
        print("  %s %s 边合计 %d 条（进场时 %d）"
              % ("删后" if APPLY else "当前", EDGE_TYPE, len(after), len(edges)), flush=True)
        result.update({"edges_after": len(after), "edge_stale_after": len(b2["stale"])})
        if APPLY:
            expect = len(edges) - result.get("deleted", 0)
            if len(after) != expect:
                stepfail("边数不守恒：期望 %d（删前 %d - 删除 %d），实际 %d"
                         % (expect, len(edges), result.get("deleted", 0), len(after)))
            ok("边数守恒：%d - %d = %d" % (len(edges), result.get("deleted", 0), len(after)))
            if b2["stale"]:
                stepfail("删除后仍有 %d 条陈旧边（DELETE 未真正生效）" % len(b2["stale"]))
            ok("陈旧边已归零")
            if len(b2["valid"]) != len(buckets["valid"]):
                stepfail("有效来源边数从 %d 变成 %d（不该动到它们）"
                         % (len(buckets["valid"]), len(b2["valid"])))
            ok("有效来源边数不变：%d" % len(b2["valid"]))
            cm = result.get("community")
            if cm and cm.get("empty_graph"):
                warn("社区摘要未重建（合法空）：ES 仍为上一代 %d 条，本次不做条数对账" % cm["es_after"])
            elif cm:
                if cm["es_after"] != cm["summaries"]:
                    stepfail("ES 摘要条数 %d != 本次摘要数 %d（新旧代混杂或写入丢失）"
                             % (cm["es_after"], cm["summaries"]))
                ok("ES 摘要条数 == 本次摘要数 == %d；社区数 %d；失败 %d"
                   % (cm["summaries"], cm["communities"], cm["failures"]))
        else:
            warn("dry-run：跳过'边数守恒/陈旧边归零/摘要条数'三项校验（需 --apply 才有写入）")
            print("  将校验: 边数守恒(%d 条) / 陈旧边归零 / ES 摘要条数 == 本次摘要数"
                  % len(edges), flush=True)
        result["extract_stats"] = extract_stats_advisory()
        result["verdict"] = "PASS"
        print("RESULT " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        return 0
    except StepFail as exc:
        result["verdict"] = "FAIL"
        result["reason"] = str(exc)
        print("  [FAIL] %s" % exc, flush=True)
        print("RESULT " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        return 1
    except Exception as exc:  # noqa: BLE001
        result["verdict"] = "FAIL"
        result["reason"] = "%s: %s" % (type(exc).__name__, str(exc)[:300])
        print("  [FAIL] 未预期异常 %s: %s" % (type(exc).__name__, str(exc)[:300]), flush=True)
        print("RESULT " + json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        return 1
    finally:
        _cleanup()


if __name__ == "__main__":
    sys.exit(main())
PY
rc=$?

echo "== 结论 =="
if [ "$rc" -eq 0 ]; then
  ok "graph-rebuild 通过（mode=$MODE kb=$KB_ID）"
  [ "$APPLY" -eq 0 ] && warn "本次是 dry-run，未写任何数据；确认上面的数字后再加 --apply"
else
  printf '  [FAIL] graph-rebuild 未通过（mode=%s kb=%s rc=%s）\n' "$MODE" "$KB_ID" "$rc" >&2
fi
exit "$rc"
