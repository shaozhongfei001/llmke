#!/usr/bin/env python3
"""R15 / F12 反例法验收断言集的公共设施。

设计原则（与任务书 §5.3 一致）：
  - 每条断言都必须至少带一个**反例**：不仅验"对的出现了"，还要验"错的没出现"。
    反例不成立时判 FAIL，而不是把"没看到错"当成通过。
  - 判据只取真实存储与真实接口（Nebula / ES / MySQL / 网关），不看 git 状态、不看代码注释。
  - 需要写操作的子项（触发解析、上传、删除、撤权、重启）一律 SKIP，绝不真做。

依赖边界：
  - 网关/ES 用本机 python3 + requests（已有）。
  - Nebula 的 nebula3 客户端只装在 platform/r12/venvs/graph，故用子进程调用，
    不要求跑 run_all.py 的解释器里装 nebula3。
  - MySQL 走 docker exec r12-mysql，密码从环境变量取（默认与仓库既有夹具一致），不打印。
"""
import base64
import json
import os
import re
import subprocess
import time

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

GATEWAY = os.environ.get("R15_GW", "http://127.0.0.1:8088")
GRAPH = os.environ.get("R15_GRAPH", "http://127.0.0.1:19529")
ES = os.environ.get("R15_ES", "http://127.0.0.1:19200")
KB = "kb_9"
SPACE = "g_kb_9"
CONFIG_ID = 1                      # search_config.id=1，knowledge_base_name=kb_9（实测）
UA = "Mozilla/5.0 (X11; Linux x86_64) R15-Acceptance/1.0"
AES_KEY = b"1234567890123456"

MYSQL_PWD = os.environ.get("R15_MYSQL_PWD", "R12r00t#2026local")
VENV_PY = os.path.join(ROOT, "platform/r12/venvs/graph/bin/python")
GRAPH_SVC = os.path.join(ROOT, "services/rag-alg/index_data_service/index_graph_service")

MODEL_INFO = {"model_id": "qwen2.5-7b-instruct",
              "url": "http://127.0.0.1:18092/v1/chat/completions",
              "key": "sk-r12-local"}

# ────────────────────────────────────────────────────────── 断言结果容器
PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


def chk(name, ok, detail=""):
    """一条正例/反例检查项。ok 必须由真实数据算出，不能留空。"""
    return {"check": name, "ok": bool(ok), "detail": detail}


def res(aid, title, status, reason, checks=None, writes=False):
    return {"id": aid, "title": title, "status": status, "reason": reason,
            "checks": checks or [], "writes_required": writes}


def verdict(aid, title, checks, skip_reason=None, writes=False):
    """统一收敛：有 hard 失败 → FAIL；否则若有 skip_reason（写操作受限）→ SKIP；否则 PASS。"""
    bad = [c for c in checks if c["ok"] is False]
    if bad:
        return res(aid, title, FAIL, "反例命中：" + bad[0]["check"], checks, writes)
    if skip_reason:
        return res(aid, title, SKIP, skip_reason, checks, writes)
    return res(aid, title, PASS, "全部正例与反例检查成立", checks, writes)


# ────────────────────────────────────────────────────────── 登录 / 问答
def _aes_zero_pad(plain):
    data = plain.encode("utf-8")
    data += b"\x00" * ((-len(data)) % 16)
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    enc = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_KEY)).encryptor()
    return base64.b64encode(enc.update(data) + enc.finalize()).decode()


_TOKEN = {}


def login(user="admin", password="Admin@12345"):
    if "token" in _TOKEN:
        return _TOKEN["token"]
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Content-Type": "application/json"})
    r = s.post(f"{GATEWAY}/auth/user/simpleLogin",
               json={"userName": user, "password": _aes_zero_pad(password)}, timeout=30)
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(f"登录失败 http={r.status_code} body={str(body)[:200]}")
    _TOKEN["token"] = (body.get("data") or {}).get("token")
    return _TOKEN["token"]


_ASK_CACHE = {}
RETRIEVE_ID_RE = re.compile(r'retrive-tag\s+id="(\d+)"')
L_CITE_RE = re.compile(r"\[(L\d+-[0-9a-fA-F]+)\]")


def ask(content, endpoint="/qa/ai/question_re", timeout=300):
    """SSE 问答。返回 answer/frames/refs/http/elapsed；同一 (端点,问题) 进程内复用，避免重复打模型。"""
    key = (endpoint, content)
    if key in _ASK_CACHE:
        return _ASK_CACHE[key]
    token = login()
    payload = {"sessionId": f"r15acc-{int(time.time() * 1000)}",
               "queryId": f"r15q-{int(time.time() * 1000)}",
               "content": content, "type": "text", "sysType": "KNO_INDEX",
               "configId": CONFIG_ID}
    t0 = time.time()
    try:
        r = requests.post(GATEWAY + endpoint, json=payload, stream=True, timeout=timeout,
                          headers={"Authorization": token, "Accept": "text/event-stream",
                                   "Content-Type": "application/json", "User-Agent": UA})
    except requests.exceptions.RequestException as e:
        out = {"answer": "", "frames": [], "refs": [], "http": 0,
               "error": f"{type(e).__name__}: {str(e)[:200]}", "elapsed": 0.0}
        _ASK_CACHE[key] = out
        return out
    texts, frames, stream_err, cumulative = [], [], "", False
    # 只认 data: 行；按 bytes 逐行解码，避免跨块多字节 UTF-8 被撕裂（R12 踩过）
    try:
        for raw in r.iter_lines(decode_unicode=False):
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace")
            if not line.startswith("data:"):
                continue
            line = line[5:].strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            frames.append(obj)
            rep = obj.get("reply") or {}
            if isinstance(rep, dict) and rep.get("content"):
                piece = rep["content"]
                # 两个入口的 SSE 语义不同（实测 question_re=逐帧增量、question=逐帧累计）。
                # 判定必须拿"累计串"比而不是拿"上一片"比：中文增量的下一片常以上一片开头
                # （'额' → '额度'），拿上一片比会把它误判成累计帧并丢掉前半句。
                joined = "".join(texts)
                if joined and piece.startswith(joined) and len(piece) >= len(joined):
                    texts = [piece]
                    cumulative = True
                else:
                    texts.append(piece)
    except Exception as e:
        # 流在中途断掉（网关重启/连接被切）必须如实记录：半截答案不能当完整答案
        stream_err = f"{type(e).__name__}: {str(e)[:160]}"
    refs = []
    for fr in frames:
        v = fr.get("reference")
        if not v:
            continue
        try:
            parsed = json.loads(v) if isinstance(v, str) else v
        except Exception:
            continue
        if isinstance(parsed, dict):
            inner = parsed.get("documents")
            try:
                parsed = json.loads(inner) if isinstance(inner, str) else (inner or [])
            except Exception:
                parsed = []
        if isinstance(parsed, list) and parsed:
            refs = parsed
    out = {"answer": "".join(texts), "frames": frames, "refs": refs,
           "http": r.status_code, "elapsed": round(time.time() - t0, 1),
           "stream_error": stream_err,
           "frame_semantics": "cumulative" if cumulative else "incremental"}
    _ASK_CACHE[key] = out
    return out


def cited_ids(answer):
    """答案里可回查的引用 id（retrive-tag / L0-xxx 两种真实形态都收）。"""
    return RETRIEVE_ID_RE.findall(answer or "") + L_CITE_RE.findall(answer or "")


# ────────────────────────────────────────────────────────── Nebula（子进程）
_NEBULA_SNIPPET = r'''
import json, sys
from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool
space, ngql = sys.argv[1], sys.argv[2]
cfg = Config(); pool = ConnectionPool(); pool.init([("127.0.0.1", 19669)], cfg)
s = pool.get_session("root", "nebula")
r = s.execute("USE " + space)
if not r.is_succeeded():
    print(json.dumps({"error": "USE failed: " + str(r.error_msg())})); sys.exit(0)
out = []
for stmt in [x for x in ngql.split(";;") if x.strip()]:
    rr = s.execute(stmt)
    if not rr.is_succeeded():
        print(json.dumps({"error": str(rr.error_msg())})); sys.exit(0)
    rows = [[str(rr.row_values(i)[j]) for j in range(rr.col_size())] for i in range(rr.row_size())]
    out.append(rows)
print(json.dumps(out, ensure_ascii=False))
'''


def _clean(v):
    v = str(v)
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return v


def nebula(ngql, space=SPACE):
    """执行 NGQL（多语句用 ;; 分隔），返回 [[row...], ...]；失败抛 RuntimeError，不静默返回空。"""
    p = subprocess.run([VENV_PY, "-c", _NEBULA_SNIPPET, space, ngql],
                       capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"nebula 子进程失败: {(p.stderr or '')[-300:]}")
    try:
        data = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        raise RuntimeError(f"nebula 输出不可解析: {p.stdout[:200]}")
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"nebula 查询失败: {data['error']}")
    return [[[_clean(c) for c in row] for row in stmt] for stmt in data]


_EDGES = {}


def edges():
    """g_kb_9 全部 relationship 边（含 show_flag=0 的隐藏边，便于反例检查）。"""
    if "v" in _EDGES:
        return _EDGES["v"]
    rows = nebula("MATCH (a:entity)-[e:relationship]->(b:entity) RETURN a.entity.name, "
                  "e.name, b.entity.name, e.file_id, e.generation, e.show_flag")[0]
    out = [{"s": r[0], "p": r[1], "o": r[2], "fid": r[3], "gen": r[4], "sf": r[5]} for r in rows]
    _EDGES["v"] = out
    return out


# ────────────────────────────────────────────────────────── MySQL（只读台账）
def mysql(sql):
    env = dict(os.environ)
    env["MYSQL_PWD"] = MYSQL_PWD
    p = subprocess.run(["docker", "exec", "-e", "MYSQL_PWD", "r12-mysql", "mysql",
                        "-uroot", "-N", "-B", "--default-character-set=utf8mb4", "-e", sql],
                       capture_output=True, text=True, env=env, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f"mysql 查询失败: {(p.stderr or '').strip()[:200]}")
    rows = []
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


_LEDGER = {}


def ledger():
    """kb_9 文件台账：status 0=失效/被取代、3=生效、4=解析失败；graph_parse_status 3=图解析成功。"""
    if "v" in _LEDGER:
        return _LEDGER["v"]
    rows = mysql("select id,file_name,version,status,graph_parse_status,parent_file_name "
                 "from gienrag.knowledge_base_list where kb_id=9")
    out = {}
    for r in rows:
        if len(r) < 6:
            continue
        out[str(r[0])] = {"id": r[0], "name": r[1], "version": r[2], "status": r[3],
                          "gps": r[4], "parent": r[5]}
    _LEDGER["v"] = out
    return out


def active_fids():
    """当前生效文件（status=3）的 id 集合。反例：图里出现不在该集合内的 file_id = 幽灵/旧代事实。"""
    return {fid for fid, m in ledger().items() if m["status"] == "3"}


# ────────────────────────────────────────────────────────── ES
def es_search(index, body, size=50, timeout=60):
    b = dict(body or {"query": {"match_all": {}}})
    b["size"] = size
    r = requests.post(f"{ES}/{index}/_search", json=b, timeout=timeout)
    r.raise_for_status()
    return r.json()


def es_get(index, doc_id, timeout=30):
    r = requests.get(f"{ES}/{index}/_doc/{doc_id}", timeout=timeout)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    j = r.json()
    return j if j.get("found") else None


def communities():
    """community_summary_<kb> 全部摘要文档。"""
    d = es_search(f"community_summary_{KB}", {"query": {"match_all": {}}}, size=200)
    out = []
    for h in d["hits"]["hits"]:
        md = (h.get("_source") or {}).get("metadata") or {}
        out.append({"es_id": h["_id"], "meta": md,
                    "body": (h.get("_source") or {}).get("page_content") or ""})
    return out


# ────────────────────────────────────────────────────────── 图服务
def graph_post(path, body, timeout=180):
    try:
        r = requests.post(GRAPH + path, json=body, timeout=timeout)
    except requests.exceptions.RequestException as e:
        return 0, {"transport_error": f"{type(e).__name__}: {str(e)[:200]}"}
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text[:300]}


# ────────────────────────────────────────────────────────── 文本工具
def norm_num(text):
    """把 8000万元 / 8,000万 / 8000 万 归一成 8000万，用于"同一数值"比较。"""
    if text is None:
        return ""
    return re.sub(r"\s+", "", str(text)).replace(",", "")


def has_amount(text, amount):
    t = norm_num(text)
    return amount in t


def sentences(text):
    return [s.strip() for s in re.split(r"[。；;\n]", text or "") if s.strip()]


def read_src(rel):
    p = os.path.join(ROOT, rel)
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
