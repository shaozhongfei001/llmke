#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-5 公共层：上传 / 解析状态 / 收敛 的接口与存储事实采集。

边界（R2/R3）：
- 只写自建库 R14-E2E-AG5-<HHMM>（id 从建库响应取，不硬编码）
- 不写 kb_9 / kb_22，不重启服务，不改配置
- 证据只落 AG-5/evidence/**

事实来源优先级：
- 一级：HTTP 响应体（含 task_statuses / success / data）、ES 实际条数、Milvus row_count
- 二级：源码阅读（只用来解释"为什么"，不单独定事实）
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

GATEWAY = "http://127.0.0.1:8088"
RETR = "http://127.0.0.1:19995/retrieval_documents"
ES = "http://127.0.0.1:19200"
UA = "Mozilla/5.0 (X11; Linux x86_64) R14-AG5-Acceptance/1.0"
AES_KEY = b"1234567890123456"

RUN = "/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357"
AG5 = os.path.join(RUN, "AG-5")
EVID = os.path.join(AG5, "evidence")

# 本地语料（来源：仓库 fixtures，与 kb_9 语料同名同源文件）
FIXTURES = {
    "docx_plain": "/home/szf/data/dev/llmke-r12/platform/r12/parse/fixtures/generated/docx-plain.docx",
    "docx_table": "/home/szf/data/dev/llmke-r12/platform/r12/parse/fixtures/generated/docx-table.docx",
    "pdf_digital": "/home/szf/data/dev/llmke-r12/platform/r12/parse/fixtures/generated/pdf-digital.pdf",
    "pdf_scanned": "/home/szf/data/dev/llmke-r12/platform/r12/parse/fixtures/generated/pdf-scanned.pdf",
    "pptx": "/home/szf/data/dev/llmke-r12/platform/r12/qa/fixtures/R12FIX-product-intro.pptx",
    "docx_loan": "/home/szf/data/dev/llmke-r12/platform/r12/qa/fixtures/R12FIX-product-loan.docx",
    "xlsx": "/home/szf/data/dev/llmke-r12/platform/r12/qa/fixtures/R12FIX-credit-ledger.xlsx",
}


def now():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S%z")


def ts():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def dump(name, obj, sub=""):
    d = os.path.join(EVID, sub) if sub else EVID
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return p


def aes_zero_pad(plain: str) -> str:
    data = plain.encode("utf-8")
    data += b"\x00" * ((-len(data)) % 16)
    enc = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_KEY)).encryptor()
    return base64.b64encode(enc.update(data) + enc.finalize()).decode()


def login(user="admin", password="Admin@12345"):
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Content-Type": "application/json"})
    r = s.post(f"{GATEWAY}/auth/user/simpleLogin",
               json={"userName": user, "password": aes_zero_pad(password)}, timeout=30)
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(f"登录失败: {body}")
    token = (body.get("data") or {}).get("token")
    return s, token


def api(s, method, path, token, **kw):
    h = {"Authorization": token, "X-Platform": "rag-qa", "User-Agent": UA}
    kw.setdefault("timeout", 180)
    try:
        r = s.request(method, GATEWAY + path, headers=h, **kw)
    except requests.exceptions.RequestException as e:
        return 0, {"transport_error": f"{type(e).__name__}: {str(e)[:200]}"}
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text[:800]


# ---------------------------------------------------------------- 知识库

def kb_list(s, token, size=100):
    return api(s, "GET", f"/index/knowledgeBase/list?pageNo=1&pageSize={size}", token)


def kb_find(self_recs, name):
    for r in self_recs:
        if isinstance(r, dict) and r.get("kbName") == name:
            return r
    return None


def kb_create(s, token, name, desc="R14 E2E AG-5 上传/解析/收敛验收（用完即删）"):
    payload = {"kbName": name, "kbDes": desc, "fileType": "naive",
               "chunkSize": 512, "chunkOverlap": 50,
               "embeddingModelName": "bge-m3", "privateKb": 0, "platform": "rag-qa"}
    return api(s, "POST", "/index/knowledgeBase/create", token, json=payload)


def kb_delete(s, token, kb_id):
    return api(s, "DELETE", f"/index/knowledgeBase/delete?id={kb_id}", token)


# ---------------------------------------------------------------- 文件

def upload(s, token, kb_id, path, fname=None, uid=None, is_parse=True,
           file_list_type=1, timeout=900, ftype="OVERWRITE"):
    """上传单个文件（串行调用，禁止并发）。返回 (http, body, meta)。"""
    fname = fname or os.path.basename(path)
    uid = uid or f"ag5-{int(time.time()*1000)}-{fname[:12]}"
    param = {"kbId": int(kb_id),
             "fileList": [{"fileName": fname, "type": ftype, "uid": uid}],
             "fileListType": file_list_type, "isParse": is_parse, "isExtract": False,
             "isGraphParse": False, "chunking": True, "needChunk": True,
             "saveTxt": True, "platform": "rag-qa"}
    t0 = time.time()
    with open(path, "rb") as f:
        files = [("files", (fname, f, "application/octet-stream"))]
        try:
            r = requests.post(f"{GATEWAY}/index/knowledgeBase/file/uploadFileList",
                              data={"uploadFileParam": json.dumps(param, ensure_ascii=False)},
                              files=files,
                              headers={"Authorization": token, "X-Platform": "rag-qa",
                                       "User-Agent": UA},
                              timeout=timeout)
        except requests.exceptions.RequestException as e:
            return 0, {"transport_error": f"{type(e).__name__}: {str(e)[:200]}"}, {
                "fname": fname, "uid": uid, "elapsed": round(time.time() - t0, 3),
                "req_time": now()}
    elapsed = round(time.time() - t0, 3)
    try:
        body = r.json()
    except Exception:
        body = r.text[:2000]
    meta = {"fname": fname, "uid": uid, "elapsed": elapsed, "req_time": now(),
            "req_epoch": t0, "http": r.status_code, "kb_id": kb_id,
            "bytes": os.path.getsize(path)}
    return r.status_code, body, meta


def file_list(s, token, kb_id, size=200):
    return api(s, "GET", f"/index/knowledgeBase/file/list?kbId={kb_id}&pageNo=1&pageSize={size}",
               token)


def file_status(s, token, file_id):
    return api(s, "GET", f"/index/knowledgeBase/file/getFileStatusById?fileId={file_id}", token)


def file_status_by_uids(s, token, uids):
    q = "&".join(f"uids={u}" for u in uids)
    return api(s, "GET", f"/index/knowledgeBase/file/getFileStatusByUids?{q}", token)


def chunks(s, token, kb_id, doc_id, size=200):
    return api(s, "GET", f"/index/knowledgeBase/file/getFileChunks?kbId={kb_id}"
                        f"&docId={doc_id}&pageNo=1&pageSize={size}", token)


def file_delete(s, token, file_id):
    return api(s, "DELETE", f"/index/knowledgeBase/file/delete?id={file_id}", token)


def folder_list(s, token, kb_id):
    return api(s, "GET", f"/index/knowledgeBase/file/folder/list?kbId={kb_id}", token)


# ---------------------------------------------------------------- 存储事实

def es_count(idx):
    try:
        r = requests.post(f"{ES}/{idx}/_search",
                          json={"query": {"match_all": {}}, "size": 0}, timeout=60)
        j = r.json()
        if "error" in j:
            return {"idx": idx, "http": r.status_code, "error": j["error"].get("type"),
                    "reason": str(j["error"].get("reason"))[:160]}
        return {"idx": idx, "http": r.status_code, "count": j["hits"]["total"]["value"]}
    except Exception as e:
        return {"idx": idx, "error": f"{type(e).__name__}: {str(e)[:120]}"}


def es_docs(idx, size=200, query=None):
    q = query or {"match_all": {}}
    try:
        r = requests.post(f"{ES}/{idx}/_search",
                          json={"query": q, "size": size,
                                "sort": [{"_doc": "asc"}]}, timeout=60)
        j = r.json()
        if "error" in j:
            return {"error": j["error"]}
        return j
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


def es_ids(idx, size=2000):
    j = es_docs(idx, size=size)
    if "error" in j:
        return None
    return [h["_id"] for h in j.get("hits", {}).get("hits", [])]


def milvus_stats(kb_id):
    """Milvus 集合条数：_<idx> 命名，用 pymilvus 查 row_count（不可用则返回错误，不静默）。"""
    out = {}
    try:
        from pymilvus import connections, Collection, utility
        connections.connect(alias="ag5", host="127.0.0.1", port="19630")
        for idx in (f"kb_{kb_id}", f"table_chunks_kb_{kb_id}", f"table_summary_kb_{kb_id}",
                    f"_community_summary_kb_{kb_id}"):
            name = idx if idx.startswith("_") else f"_{idx}"
            if not utility.has_collection(name, using="ag5"):
                out[name] = {"exists": False}
                continue
            c = Collection(name, using="ag5")
            c.load()
            out[name] = {"exists": True, "row_count": c.num_entities}
        connections.disconnect("ag5")
    except Exception as e:
        out["_error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return out


def retrieval(kb_name, query, top_k=10, policy=1, rerank=False, graph=False):
    payload = {"query": query, "knowledge_base_name": [kb_name], "top_k": top_k,
               "enabled_faq": False, "enabled_graph": graph, "enabled_rerank": rerank,
               "search_policy": policy}
    t0 = time.time()
    try:
        r = requests.post(RETR, json=payload, timeout=180)
        j = r.json()
        return {"http": r.status_code, "body": j, "elapsed": round(time.time() - t0, 3)}
    except Exception as e:
        return {"http": 0, "error": f"{type(e).__name__}: {str(e)[:200]}",
                "elapsed": round(time.time() - t0, 3)}


def ask(s, token, content, session_id=None, query_id=None, timeout=600):
    """SSE 问答（API 路径 /qa/ai/question，含 global 分支）。"""
    payload = {"sessionId": session_id or f"ag5-{int(time.time()*1000)}",
               "queryId": query_id or f"ag5q-{int(time.time()*1000)}",
               "content": content, "type": "text", "sysType": "KNO_INDEX",
               "configId": 1}
    t0 = time.time()
    r = requests.post(GATEWAY + "/qa/ai/question", json=payload,
                      headers={"Authorization": token, "Accept": "text/event-stream",
                               "Content-Type": "application/json", "User-Agent": UA},
                      stream=True, timeout=timeout)
    raw = b""
    for line in r.iter_lines():
        if line:
            raw += line + b"\n"
    txt = raw.decode("utf-8", "replace")
    return {"http": r.status_code, "raw_len": len(raw), "text": txt[:20000],
            "elapsed": round(time.time() - t0, 3)}


def pids():
    out = {}
    for p in (8088, 18082, 18083, 19527, 19529, 19995):
        r = subprocess.run(["bash", "-lc",
                            f"ss -lntp 2>/dev/null | grep ':{p} ' | grep -oP 'pid=\\K[0-9]+' | head -1"],
                           capture_output=True, text=True)
        out[str(p)] = r.stdout.strip()
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ================= 两套状态枚举（数值同名不同义，读反就会把"成功"判成"重试中"）=================
# 文件级 KbFileStatusEnums（rag-common/index/enmus/KbFileStatusEnums.java）
FILE_STATUS = {0: "已删除", 1: "正常", 2: "解析中", 3: "解析成功", 4: "解析失败",
               5: "重新向量化", 98: "重试中", 99: "解析排队中"}
# 任务级 ParseTaskStatusEnums（rag-common/index/enmus/ParseTaskStatusEnums.java）
TASK_STATUS = {1: "PENDING", 2: "DEAL_ING", 3: "RETRY_ING", 4: "SUCCESS", 5: "DEAL_FAIL"}
FILE_TERMINAL = (3, 4)
FILE_OK, FILE_FAIL = 3, 4


def fstatus_name(v):
    return f"{v}({FILE_STATUS.get(v, '?')})"


def tstatus_name(v):
    return f"{v}({TASK_STATUS.get(v, '?')})"


def mysql_rows(sql, db="gienrag"):
    """只读查询（SELECT）。凭据从 platform/r12/.env 读取，不回显。"""
    env_path = "/home/szf/data/dev/llmke-r12/platform/r12/.env"
    pw = None
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("R12_MYSQL_PASSWORD="):
                    pw = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except Exception as e:
        return {"error": f"env read: {e}"}
    if not pw:
        return {"error": "no R12_MYSQL_PASSWORD"}
    r = subprocess.run(
        ["docker", "exec", "-e", f"MYSQL_PWD={pw}", "r12-mysql", "mysql", "-uroot", "-N", "-B",
         "--default-character-set=utf8mb4", "-e", sql],
        capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout)[:400]}
    rows = [l.split("\t") for l in r.stdout.splitlines() if l]
    return {"rows": rows}


def parse_tasks(file_ids):
    """按 file_id 取解析任务（含 task id / 任务级状态 / 重试次数）——只读。"""
    ids = ",".join(str(i) for i in file_ids)
    q = (f"select id,file_id,status,retry_times,retry_limit,start_time,end_time,"
         f"ifnull(error_msg,'') from gienrag.file_parse_task where file_id in ({ids}) order by id")
    r = mysql_rows(q)
    if "error" in r:
        return r
    out = []
    for row in r["rows"]:
        st = int(row[2]) if row[2].isdigit() else row[2]
        out.append({"task_id": row[0], "file_id": row[1], "status": st,
                    "status_name": TASK_STATUS.get(st, "?") if isinstance(st, int) else "?",
                    "retry_times": row[3], "retry_limit": row[4],
                    "start_time": row[5], "end_time": row[6], "error_msg": row[7]})
    return {"tasks": out}


def file_rows(file_ids):
    """knowledge_base_list 行（文件级 status 真相）——只读。"""
    ids = ",".join(str(i) for i in file_ids)
    r = mysql_rows(f"select id,kb_id,file_name,status,temp_status,version,gmt_modified "
                   f"from gienrag.knowledge_base_list where id in ({ids}) order by id")
    if "error" in r:
        return r
    return {"rows": [{"id": x[0], "kb_id": x[1], "file_name": x[2], "status": x[3],
                      "status_name": FILE_STATUS.get(int(x[3]), "?") if x[3].lstrip("-").isdigit() else "?",
                      "temp_status": x[4], "version": x[5], "gmt_modified": x[6]} for x in r["rows"]]}
