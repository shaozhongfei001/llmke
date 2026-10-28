#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-6 公共层：FAQ 全链路（列表 / 抽取 / 编辑 / 启停 / 直答 / 删除）。

边界（R2/R3）：
- 只写自建库 R14-E2E-AG6-<HHMM>（id 从建库响应取，不硬编码）
- 不写 kb_9 / kb_22，不重启服务，不改配置，不改数据库（只做 SELECT）
- 证据只落 AG-6/evidence/**

事实来源优先级：
- 一级：HTTP 响应体（success/data/total/records）、ES 实际条数、页面可见文本
- 二级：源码阅读（只解释"为什么"，不单独定事实）
"""
import base64
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone

import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

GATEWAY = "http://127.0.0.1:8088"
FE = "http://127.0.0.1:18088"
RETR = "http://127.0.0.1:19995/retrieval_documents"
ES = "http://127.0.0.1:19200"
UA = "Mozilla/5.0 (X11; Linux x86_64) R14-AG6-Acceptance/1.0"
AES_KEY = b"1234567890123456"

RUN = "/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357"
AG6 = os.path.join(RUN, "AG-6")
EVID = os.path.join(AG6, "evidence")
STATE = os.path.join(AG6, "state.json")

# 本地语料（与 kb_9 同源同文件，避免写 kb_9）
FIXTURES = {
    "docx_plain": "/home/szf/data/dev/llmke-r12/platform/r12/parse/fixtures/generated/docx-plain.docx",
    "docx_table": "/home/szf/data/dev/llmke-r12/platform/r12/parse/fixtures/generated/docx-table.docx",
    "pdf_digital": "/home/szf/data/dev/llmke-r12/platform/r12/parse/fixtures/generated/pdf-digital.pdf",
    "pptx": "/home/szf/data/dev/llmke-r12/platform/r12/qa/fixtures/R12FIX-product-intro.pptx",
    "docx_loan": "/home/szf/data/dev/llmke-r12/platform/r12/qa/fixtures/R12FIX-product-loan.docx",
    "xlsx": "/home/szf/data/dev/llmke-r12/platform/r12/qa/fixtures/R12FIX-credit-ledger.xlsx",
}

FAQ_STATUS = {0: "禁用", 1: "启用"}
FAQ_EXTRACT_STATUS = {1: "未抽取", 2: "抽取中", 3: "抽取成功", 4: "抽取失败"}


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


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(st):
    os.makedirs(AG6, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    return STATE


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
    t0 = time.time()
    try:
        r = s.request(method, GATEWAY + path, headers=h, **kw)
    except requests.exceptions.RequestException as e:
        return 0, {"transport_error": f"{type(e).__name__}: {str(e)[:200]}"}, 0
    el = round(time.time() - t0, 3)
    try:
        return r.status_code, r.json(), el
    except Exception:
        return r.status_code, r.text[:800], el


# ---------------------------------------------------------------- 知识库

def kb_list(s, token, size=100):
    return api(s, "GET", f"/index/knowledgeBase/list?pageNo=1&pageSize={size}", token)


def kb_find(recs, name):
    for r in recs or []:
        if isinstance(r, dict) and r.get("kbName") == name:
            return r
    return None


def kb_create(s, token, name, desc="R14 E2E AG-6 FAQ 全链路验收（用完即删）"):
    payload = {"kbName": name, "kbDes": desc, "fileType": "naive",
               "chunkSize": 512, "chunkOverlap": 50,
               "embeddingModelName": "bge-m3", "privateKb": 0, "platform": "rag-qa"}
    return api(s, "POST", "/index/knowledgeBase/create", token, json=payload)


def kb_delete(s, token, kb_id):
    return api(s, "DELETE", f"/index/knowledgeBase/delete?id={kb_id}", token)


# ---------------------------------------------------------------- 文件（串行上传）

def upload(s, token, kb_id, path, fname=None, is_parse=True, is_extract_faq=False,
           timeout=900):
    fname = fname or os.path.basename(path)
    uid = f"ag6-{int(time.time()*1000)}-{fname[:12]}"
    param = {"kbId": int(kb_id),
             "fileList": [{"fileName": fname, "type": "OVERWRITE", "uid": uid}],
             "fileListType": 1, "isParse": is_parse, "isExtract": is_extract_faq,
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


def faq_extract_status(s, token, file_id):
    return api(s, "GET",
               f"/index/knowledgeBase/file/getFAQExtractStatusById?fileId={file_id}", token)


def folder_list(s, token, kb_id):
    return api(s, "GET", f"/index/knowledgeBase/file/folder/list?kbId={kb_id}", token)


# ---------------------------------------------------------------- FAQ

def faq_list(s, token, kb_id, page_no=1, page_size=10, status=None, fuzzy=None,
             file_id=None, folder_id=None):
    q = f"kbId={kb_id}&pageNo={page_no}&pageSize={page_size}"
    if status is not None:
        q += f"&status={status}"
    if fuzzy:
        q += f"&fuzzy={requests.utils.quote(fuzzy)}"
    if file_id is not None:
        q += f"&fileId={file_id}"
    if folder_id is not None:
        q += f"&folderId={folder_id}"
    return api(s, "GET", f"/index/faq/list?{q}", token)


def faq_extract(s, token, kb_id, kb_name, file_id, file_path, file_size="0MB",
                parent_name=None, is_all=False, folder_ids=None):
    """FAQ 抽取（前端 FAQ抽取 tab 走的 extractFQA；files[] 才会被消费，file_ids 历史上有坑）"""
    payload = {"files": [{
        "folder_id": None,
        "file_path": file_path,
        "file_size": file_size,
        "file_id": int(file_id),
        "parent_file_name": parent_name or os.path.basename(file_path),
    }],
        "folder_ids": folder_ids or [],
        "knowledge_base_name": kb_name,
        "knowledge_base_id": int(kb_id),
        "override": True,
        "is_all": is_all}
    return api(s, "POST", "/index/knowledgeBase/file/extractFQA", token, json=payload)


def faq_extract_all(s, token, kb_id):
    return api(s, "POST", f"/index/knowledgeBase/file/extractAllFQA?kbId={kb_id}", token)


def faq_update(s, token, kb_id, faqs, file_id=None, folder_id=None):
    payload = {"kbId": int(kb_id), "faqs": faqs}
    if file_id is not None:
        payload["fileId"] = int(file_id)
    if folder_id is not None:
        payload["folderId"] = int(folder_id)
    return api(s, "PUT", "/index/faq/update", token, json=payload)


def faq_create(s, token, kb_id, faqs, folder_id=None, file_id=None):
    payload = {"kbId": int(kb_id), "faqs": faqs}
    if folder_id is not None:
        payload["folderId"] = int(folder_id)
    if file_id is not None:
        payload["fileId"] = int(file_id)
    return api(s, "POST", "/index/faq/create", token, json=payload)


def faq_change_status(s, token, kb_id, status, related_pks=None,
                      file_ids=None, folder_ids=None):
    payload = {"kbId": int(kb_id), "status": int(status)}
    if related_pks:
        payload["relatedpks"] = [int(x) for x in related_pks]
    if file_ids:
        payload["fileIds"] = [int(x) for x in file_ids]
    if folder_ids:
        payload["folderIds"] = [int(x) for x in folder_ids]
    return api(s, "PUT", "/index/faq/changeStatus", token, json=payload)


def faq_delete(s, token, kb_id, related_pks=None, pks=None):
    payload = {"kbId": int(kb_id)}
    if related_pks:
        payload["relatedPks"] = [int(x) for x in related_pks]
    if pks:
        payload["pks"] = [int(x) for x in pks]
    return api(s, "POST", "/index/faq/delete", token, json=payload)


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
                          json={"query": q, "size": size, "sort": [{"_doc": "asc"}]},
                          timeout=60)
        j = r.json()
        if "error" in j:
            return {"error": j["error"]}
        return j
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


def retrieval(kb_name, query, top_k=10, enabled_faq=True, policy=1, rerank=False, graph=False):
    payload = {"query": query, "knowledge_base_name": [kb_name], "top_k": top_k,
               "enabled_faq": enabled_faq, "enabled_graph": graph,
               "enabled_rerank": rerank, "search_policy": policy}
    t0 = time.time()
    try:
        r = requests.post(RETR, json=payload, timeout=180)
        j = r.json()
        return {"http": r.status_code, "body": j, "elapsed": round(time.time() - t0, 3)}
    except Exception as e:
        return {"http": 0, "error": f"{type(e).__name__}: {str(e)[:200]}",
                "elapsed": round(time.time() - t0, 3)}


def pids():
    out = {}
    for p in (8088, 18082, 18083, 19527, 19529, 19995):
        r = subprocess.run(["bash", "-lc",
                            f"ss -lntp 2>/dev/null | grep ':{p} ' | grep -oP 'pid=\\K[0-9]+' | head -1"],
                           capture_output=True, text=True)
        out[str(p)] = r.stdout.strip()
    return out


def pid_start(pid):
    if not pid:
        return None
    r = subprocess.run(["bash", "-lc", f"ps -o lstart= -p {pid} 2>/dev/null"],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def mysql_rows(sql, db="gienrag"):
    """只读 SELECT（凭据来自 platform/r12/.env，不回显）。"""
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
        ["docker", "exec", "-e", f"MYSQL_PWD={pw}", "r12-mysql", "mysql", "-uroot",
         "-N", "-B", "--default-character-set=utf8mb4", db, "-e", sql],
        capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout)[:400]}
    rows = [l.split("\t") for l in r.stdout.splitlines() if l]
    return {"rows": rows}


def milvus_stats(kb_id):
    """Milvus 集合条数：_<idx> 命名，用 pymilvus 查 row_count（不可用则返回错误，不静默）。"""
    out = {}
    try:
        from pymilvus import connections, Collection, utility
        connections.connect(alias="ag6", host="127.0.0.1", port="19630")
        for idx in (f"kb_{kb_id}", f"table_chunks_kb_{kb_id}", f"table_summary_kb_{kb_id}",
                    f"community_summary_kb_{kb_id}"):
            name = idx if idx.startswith("_") else f"_{idx}"
            if not utility.has_collection(name, using="ag6"):
                out[name] = {"exists": False}
                continue
            c = Collection(name, using="ag6")
            c.load()
            out[name] = {"exists": True, "row_count": c.num_entities}
        connections.disconnect("ag6")
    except Exception as e:
        out["_error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return out


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def size(path):
    return os.path.getsize(path)
