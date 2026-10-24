#!/usr/bin/env python
"""报告与运行态一致性对账（parse-ops 侧，对应 model-ops 的 check_doc_consistency.py）。

为什么需要：配置变了、代码改了、用例加了，而文档没跟着走 —— 不报错、不失败，
只会让后人按旧数字做决策（本报告今天就腐化过 3 处：12→13 例、§3 的 16384、脚本清单）。

对账对象：
  1. 报告里的 `<!-- R12-PARSE-DOC-STATE {...} -->` 状态块  vs  **Nacos live 配置**；
  2. 状态块 `cases` vs `parse_cases.py` 里 `CASES` 注册表长度（不是脚本文本，是真注册表）；
  3. 状态块 `port` vs **pidfile ↔ listening pid 一致**（证明"这个 PID 确实在监听这个端口"，
     而不是"这个 PID 还活着"——用 /proc/net/tcp 的 inode 反查）；
  4. OCR 模型资产（`OCR_PATH` 下的关键文件）是否仍在；
  5. 索引写入模板（`es-insert` / `milvus-insert`）是否已配置（缺则 /parse 会 KeyError）。

退出码：0 = 全部 PASS（文档可引用）；1 = 有 FAIL（文档不可引用）；2 = 环境不可达。
用法：
  ../venvs/parse/bin/python check_report_consistency.py
  ../venvs/parse/bin/python check_report_consistency.py --mutate      # 变异自测：证明它会红
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

R12 = "/home/szf/data/dev/llmke-r12/platform/r12"
REPORT = os.path.join(R12, "status", "parse.md")
NACOS = "http://127.0.0.1:18848/nacos"
DATA_ID, GROUP, TENANT = "alg_doc_config_py", "DEFAULT_GROUP", ""
FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_PATH = os.environ.get("OCR_PATH", os.path.join(R12, "models", "ocr_models"))

# 兼容两种标记：旧 `R12-PARSE-DOC-STATE` 与新共享 schema `R12-DOC-STATE`
STATE_RE = re.compile(r"<!--\s*R12-(?:PARSE-)?DOC-STATE\s*(\{.*?\})\s*-->", re.S)
# 正文锚点行：`port=12340 chunk_size=512 ...`，用于覆盖"正文改了但状态块没改"这一类腐化
ANCHOR_RE = re.compile(r"^\*\*运行态摘要.*?\*\*[：:]\s*\n?`([^`]+)`", re.M)
KV_RE = re.compile(r"(\w+)=([\w.\-]+)")


def check(results, name, ok, note="", kind="FAIL"):
    """kind: FAIL = 值不匹配（该改配置/文档）；ERROR = 根本没取到值（该改检查器/路径）。

    [分类纪律] 两类失败必须分开：
      - 提取失败 ⇒ ERROR：连"比什么"都没比上，**不能伪装成"配置错了"**（带点的模型名、
        Nacos 改 key、嵌套层级变动都会走这里）；
      - 取到值但不等 ⇒ FAIL：这才是真的不一致。
    混在一起时人会去改**没问题的配置**——本脚本首版就差点让我那么做。
    """
    results.append({"check": name, "ok": bool(ok), "note": note, "kind": kind})
    tag = "PASS" if ok else kind
    print(f"  [{tag}] {name}" + (f" — {note}" if note else ""))


def read_state(report_path):
    text = open(report_path, encoding="utf-8").read()
    m = STATE_RE.search(text)
    if not m:
        return None, "报告里找不到 R12-PARSE-DOC-STATE 状态块"
    try:
        doc = json.loads(m.group(1))
    except Exception as e:  # noqa: BLE001
        return None, f"状态块不是合法 JSON：{e}"
    if "values" not in doc:
        return None, "状态块缺 values（应使用 {schema,service,era,values{...}}）"
    return doc, ""


def nacos_config():
    import urllib.request
    url = f"{NACOS}/v1/cs/configs?dataId={DATA_ID}&group={GROUP}&tenant={TENANT}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode()


def nested(cfg_text, keys, default=None):
    """极简 YAML 取值：支持缩进嵌套 + 行尾注释。

    ⚠ keys 必须是**列表**：早期版本按 '.' 切分，而 `qwen2.5-vl-3b-instruct` 里的 `2.5`
    本身就带点，会被切成 `qwen2 / 5-vl-3b-instruct` → 永远取不到值（真实的踩坑）。
    """
    keys = list(keys)
    stack = []
    for raw in cfg_text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        body = line.strip()
        if body.startswith("- "):
            continue
        if ":" not in body:
            continue
        k, v = body.split(":", 1)
        k = k.strip()
        v = v.split("#")[0].strip() if not v.strip().startswith("#") else ""
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not v:  # 开始一个嵌套块
            stack.append((indent, k))
            continue
        path = [x[1] for x in stack] + [k]
        if path == keys:
            return v.strip('"').strip("'")
    return default


def listening_pid(port):
    """通过 /proc/net/tcp* 的 inode 反查监听该端口的 PID（不依赖 ss 的解析格式）。"""
    inodes = set()
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            for line in open(f).read().splitlines()[1:]:
                parts = line.split()
                local, st, inode = parts[1], parts[3], parts[9]
                if st != "0A":  # LISTEN
                    continue
                if int(local.split(":")[1], 16) != port:
                    continue
                inodes.add(inode)
        except FileNotFoundError:
            continue
    if not inodes:
        return None
    for pid_dir in glob.glob("/proc/[0-9]*"):
        try:
            for fd in os.listdir(os.path.join(pid_dir, "fd")):
                link = os.readlink(os.path.join(pid_dir, "fd", fd))
                m = re.match(r"socket:\[(\d+)\]", link)
                if m and m.group(1) in inodes:
                    return int(os.path.basename(pid_dir))
        except (PermissionError, FileNotFoundError, OSError):
            continue
    return None


def cases_count():
    """导入 parse_cases 拿真实注册表长度（不靠 grep 文本猜）。"""
    path = os.path.join(FIXTURES_DIR, "parse_cases.py")
    spec = importlib.util.spec_from_file_location("_r12_parse_cases", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # 只读；该模块 import 期不连服务
    ids = [c["id"] for c in mod.CASES]
    default = [c["id"] for c in mod.CASES
               if not c.get("stress") and not c.get("vlm_heavy")]
    return len(mod.CASES), ids, len(default)


def run_checks(report_path, results, inject_fail=None):
    print(f"— 报告 vs 运行态对账（{report_path}）—")
    doc, err = read_state(report_path)
    if doc is None:
        check(results, "state_block_present", False, err)
        return
    check(results, "state_block_present", True, json.dumps(doc, ensure_ascii=False))
    check(results, "state_schema", doc.get("schema") == 1 and doc.get("service") == "parse"
          and bool(doc.get("era")), f"schema={doc.get('schema')} service={doc.get('service')} era={doc.get('era')}")
    state = doc["values"]

    # 正文锚点 vs 状态块（覆盖"正文腐化"这一类：只改正文、不改块）
    text = open(report_path, encoding="utf-8").read()
    am = ANCHOR_RE.search(text)
    if not am:
        check(results, "prose_anchor_present", False, "找不到正文锚点行（**运行态摘要...**：`k=v ...`）")
    else:
        prose = dict(KV_RE.findall(am.group(1)))
        diff = {k: (v, state.get(k)) for k, v in prose.items() if str(state.get(k)) != str(v)}
        check(results, "prose_matches_block", not diff, f"不一致项(正文,状态块)={diff}")

    cfg = nacos_config()

    # 1. 配置类字段 —— **先全量体检，再开始比**
    # 理由（model-ops）：只要有一个 key 取不到，后面所有 PASS 都是"残缺前提下的假绿"。
    keys = [
        ("port", ["server", "port"]),
        ("chunk_size", ["chunk_size"]),
        ("overlap_size", ["overlap_size"]),
        ("multi_modal_max_workers", ["multi_modal_max_workers"]),
        ("output_max_tokens", ["online_multi_modal_model", "qwen2.5-vl-3b-instruct", "output_max_tokens"]),
    ]
    extracted, missing = {}, []
    for doc_key, yaml_key in keys:
        live = nested(cfg, yaml_key, default=None)
        if inject_fail and doc_key in [x.strip() for x in inject_fail.split(",")]:
            live = None  # 自测注入：模拟"路径解析错/键改名"
        if live is None:
            missing.append((doc_key, ".".join(yaml_key)))
        else:
            extracted[doc_key] = live
    if missing:
        for doc_key, path in missing:
            check(results, f"cfg_{doc_key}", False,
                  f"提取失败：key 不存在或路径解析错（{path}）——这是检查器问题，不是配置问题",
                  kind="ERROR")
        # 立刻中止：后面任何 PASS 都只是"在残缺前提下"的假绿
        return
    for doc_key, _ in keys:
        check(results, f"cfg_{doc_key}", str(extracted[doc_key]) == str(state.get(doc_key)),
              f"doc={state.get(doc_key)} live={extracted[doc_key]}")

    # 2. 用例数 vs 真实注册表
    n, ids, n_default = cases_count()
    check(results, "cases_total", n == state.get("cases_total"),
          f"doc={state.get('cases_total')} registry={n} ids={ids}")
    check(results, "cases_default", n_default == state.get("cases_default"),
          f"doc={state.get('cases_default')} default_run={n_default} "
          f"（排除 stress/vlm_heavy 的附加用例）")

    # 3. 端口 ↔ pidfile ↔ listening pid
    port = int(state.get("port") or 0)
    pidfile = os.path.join(R12, "run", "doc-parse.pid")
    pid_doc = None
    if os.path.exists(pidfile):
        try:
            pid_doc = int(open(pidfile).read().strip())
        except Exception:  # noqa: BLE001
            pid_doc = None
    pid_live = listening_pid(port)
    check(results, "port_listening", pid_live is not None, f":{port} listening_pid={pid_live}")
    check(results, "pidfile_matches_listener", pid_doc == pid_live,
          f"pidfile={pid_doc} listening={pid_live}")

    # 4. 索引模板
    for key in ("es-insert", "milvus-insert"):
        check(results, f"cfg_{key.replace('-', '_')}", bool(nested(cfg, [key])),
              f"live={nested(cfg, [key])}")

    # 4.5 跨服务共享边界键（与 model-ops 的 models.md 状态块互相对账）
    peer_path = os.path.join(R12, "status", "models.md")
    shared = ["vlm_port", "vlm_model", "vlm_parallel", "vlm_ctx_slot"]
    if not os.path.exists(peer_path):
        check(results, "peer_state_block", True, f"SKIP 未找到 {peer_path}")
    else:
        peer, perr = read_state(peer_path)
        if peer is None:
            check(results, "peer_state_block", False, perr)
        else:
            pv = peer["values"]
            diff = {k: (state.get(k), pv.get(k)) for k in shared
                    if str(state.get(k)) != str(pv.get(k))}
            check(results, "peer_shared_keys", not diff,
                  f"parse vs models 不一致(parse,models)={diff}")

    # 5. OCR 资产
    must = ["det.onnx", "rec.onnx", "layout.onnx", "tsr.onnx", "ocr.res", "updown_concat_xgb.model"]
    missing = [f for f in must if not os.path.exists(os.path.join(OCR_PATH, f))]
    check(results, "ocr_assets", not missing, f"missing={missing} path={OCR_PATH}")


def mutate_selftest():
    """变异测试：把状态块里的 output_max_tokens 改错，断言脚本真的会红。

    不这么做的话，这个检查就只是"只会亮绿灯的装饰"（model-ops 语）。
    """
    src = open(REPORT, encoding="utf-8").read()
    mut = STATE_RE.sub(lambda m: "<!-- R12-DOC-STATE "
                       + json.dumps({**json.loads(m.group(1)), "values": {**json.loads(m.group(1))["values"],
                                                                          "output_max_tokens": 512}})
                       + " -->", src, count=1)
    assert mut != src, "变异未生效（状态块没匹配到）"
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(mut)
        tmp = f.name
    try:
        proc = subprocess.run([sys.executable, __file__, "--report", tmp],
                              capture_output=True, text=True)
        red = proc.returncode == 1
        print("\n— 变异自测 —")
        print(f"  文档改 output_max_tokens=512 → rc={proc.returncode} "
              f"({'RED ✅ 证明会失败' if red else 'GREEN ❌ 这个检查是装饰'})")
        for line in proc.stdout.splitlines():
            if "cfg_output_max_tokens" in line:
                print("  " + line.strip())
        rc1 = 0 if red else 1
    finally:
        os.unlink(tmp)

    # 第二类变异：只改正文锚点（覆盖"正文腐化"）
    mut2 = ANCHOR_RE.sub(lambda m: m.group(0).replace("output_max_tokens=768",
                                                      "output_max_tokens=512"), src, count=1)
    assert mut2 != src, "正文锚点变异未生效（找不到 output_max_tokens=768）"
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f2:
        f2.write(mut2)
        tmp2 = f2.name
    try:
        proc2 = subprocess.run([sys.executable, __file__, "--report", tmp2],
                               capture_output=True, text=True)
        red2 = proc2.returncode == 1
        print(f"  正文锚点改 output_max_tokens=512 → rc={proc2.returncode} "
              f"({'RED ✅ 证明会失败' if red2 else 'GREEN ❌ 正文腐化抓不到'})")
        for line in proc2.stdout.splitlines():
            if "prose_matches_block" in line:
                print("  " + line.strip())
        return 0 if (red and red2) else 1
    finally:
        os.unlink(tmp2)


def error_class_selftest():
    """证明"提取失败"会走 ERROR(rc=3) 而不是 FAIL(rc=1)——防止把检查器的错报成配置的错。"""
    proc = subprocess.run([sys.executable, __file__, "--inject-extract-fail", "output_max_tokens,chunk_size"],
                          capture_output=True, text=True)
    ok = (proc.returncode == 3 and "[ERROR]" in proc.stdout
          and proc.stdout.count("[ERROR]") >= 2)
    print("\n— ERROR 分类自测 —")
    print(f"  注入 2 个 key 提取失败 → rc={proc.returncode} "
          f"({'✅ ERROR 且未伪装成 FAIL' if ok else '❌ 混淆了提取失败与值不匹配'})")
    for line in proc.stdout.splitlines():
        if "ERROR" in line or "结论" in line:
            print("  " + line.strip())
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--mutate", action="store_true", help="变异自测：证明脚本会红（两类腐化）")
    ap.add_argument("--selftest-error-class", action="store_true",
                    help="自测 ERROR 分类：注入'提取失败'，断言 rc=3 且标 ERROR 而非 FAIL")
    ap.add_argument("--inject-extract-fail", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()

    results = []
    try:
        run_checks(args.report, results, inject_fail=args.inject_extract_fail)
    except Exception as e:  # noqa: BLE001  环境不可达
        print(f"  [FAIL] env_unreachable — {e}")
        return 2

    errors = [r["check"] for r in results if not r["ok"] and r.get("kind") == "ERROR"]
    failed = [r["check"] for r in results if not r["ok"] and r.get("kind") != "ERROR"]
    verdict = "PASS" if not (errors or failed) else ("ERROR" if errors else "FAIL")
    print(f"\n结论：{verdict}  checks={len(results)} errors={errors} failed={failed}")
    if errors:
        return 3          # 检查器自身取不到值 —— 与"配置不一致"必须区分
    if failed:
        return 1
    if args.selftest_error_class:
        return error_class_selftest()
    if args.mutate:
        return mutate_selftest()
    return 0


if __name__ == "__main__":
    sys.exit(main())
