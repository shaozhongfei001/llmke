#!/usr/bin/env python3
"""R12 独立复核客户端（QA 自写，不 import 开发自检脚本 r12_client.py / acceptance.py）。

设计要点（可审计性）：
- 每个请求都把「实际发出的 method/path/header 键/payload 形状」记录下来，供断言检查
  「提问不随请求提交正文」这类"看不见的承诺"。
- 不吞异常：网络错误也记成一次观察，交给断言判定 FAIL/BLOCKED。
"""
import base64
import json
import os
import time

import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

GATEWAY = os.environ.get("R12_GW", "http://127.0.0.1:8088")
UA = "Mozilla/5.0 (X11; Linux x86_64) R12-QA-independent/1.0"
AES_KEY = b"1234567890123456"   # 与前端 platform 约定一致（conf aes.key/iv）

# 请求体字段白名单：提问请求体只允许出现这些字段（用于证明"不提交正文"）
ALLOWED_ASK_FIELDS = {
    "sessionId", "queryId", "content", "type", "sysType", "configId",
    "config", "fileUids", "enableThinking", "enableWebsearch",
    "dialogueId", "lastDate", "audioUrl",
}


def aes_zero_pad(plain: str) -> str:
    data = plain.encode("utf-8")
    data += b"\x00" * ((-len(data)) % 16)
    enc = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_KEY)).encryptor()
    return base64.b64encode(enc.update(data) + enc.finalize()).decode()


class Resp:
    """一次观察（observation）。断言只读这个对象。"""

    def __init__(self, method, path, status, body, req_keys=None,
                 req_body=None, raw=None, elapsed=0.0):
        self.method = method
        self.path = path
        self.status = status
        self.body = body
        self.req_keys = sorted(req_keys or [])
        self.req_body = req_body
        self.raw = raw
        self.elapsed = elapsed

    @property
    def ok(self):
        return isinstance(self.body, dict) and bool(self.body.get("success"))

    @property
    def data(self):
        return self.body.get("data") if isinstance(self.body, dict) else None

    def dump(self, limit=600):
        b = self.body
        s = json.dumps(b, ensure_ascii=False) if not isinstance(b, str) else b
        return s[:limit]


class Client:
    def __init__(self, token=None, label="anon"):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA})
        self.token = token
        self.label = label
        self.trace = []          # 全量请求留痕，作为证据

    # ---------------------------------------------------------------- 基础
    def _headers(self, extra=None):
        h = {"X-Platform": "rag-qa", "User-Agent": UA}
        if self.token:
            h["Authorization"] = self.token
        if extra:
            h.update(extra)
        return h

    def call(self, method, path, **kw):
        headers = self._headers(kw.pop("headers", None))
        t0 = time.time()
        trace = {"label": self.label, "method": method, "path": path,
                 "header_keys": sorted(headers.keys()),
                 "token_present": "Authorization" in headers}
        try:
            r = self.s.request(method, GATEWAY + path, headers=headers, timeout=kw.pop("timeout", 120), **kw)
            elapsed = time.time() - t0
            try:
                body = r.json()
            except Exception:
                body = r.text[:2000]
            trace.update({"status": r.status_code, "elapsed": round(elapsed, 3)})
            self.trace.append(trace)
            return Resp(method, path, r.status_code, body, elapsed=elapsed)
        except Exception as e:  # 网络层失败也作为观察
            self.trace.append(dict(trace, error=repr(e)))
            return Resp(method, path, -1, {"transport_error": repr(e)},
                        elapsed=time.time() - t0)

    def get(self, path, **kw):
        return self.call("GET", path, **kw)

    def post(self, path, payload=None, **kw):
        kw.setdefault("json", payload)
        r = self.call("POST", path, **kw)
        if payload is not None:
            r.req_keys = list(payload.keys()) if isinstance(payload, dict) else []
            r.req_body = payload
        return r

    def delete(self, path, **kw):
        return self.call("DELETE", path, **kw)

    # ---------------------------------------------------------------- 登录
    def login(self, user, password):
        r = self.post("/auth/user/simpleLogin",
                      {"userName": user, "password": aes_zero_pad(password)})
        if r.ok and isinstance(r.data, dict):
            self.token = r.data.get("token")
        return r

    # ---------------------------------------------------------------- 业务
    def menus(self):
        return self.get("/auth/resource/getMenusByUser")

    def me(self):
        return self.get("/auth/user/getUserInfo")

    def kb_list(self, page=1, size=50, extra=""):
        return self.get(f"/index/knowledgeBase/list?pageNo={page}&pageSize={size}{extra}")

    def kb_create(self, name, private=0, desc="QA 独立复核"):
        return self.post("/index/knowledgeBase/create", {
            "kbName": name, "kbDes": desc, "fileType": "naive",
            "chunkSize": 512, "chunkOverlap": 50,
            "embeddingModelName": "bge-m3", "privateKb": private,
            "platform": "rag-qa"})

    def upload(self, kb_id, path, uid=None, is_parse=True):
        fname = os.path.basename(path)
        param = {
            "kbId": int(kb_id),
            "fileList": [{"fileName": fname, "type": "OVERWRITE",
                          "uid": uid or f"qa-{int(time.time()*1000)}"}],
            "fileListType": 1, "isParse": is_parse, "isExtract": False,
            "isGraphParse": False, "chunking": True, "needChunk": True,
            "saveTxt": True, "platform": "rag-qa",
        }
        data = {"uploadFileParam": json.dumps(param, ensure_ascii=False)}
        with open(path, "rb") as f:
            files = [("files", (fname, f, "application/octet-stream"))]
            t0 = time.time()
            try:
                r = self.s.post(f"{GATEWAY}/index/knowledgeBase/file/uploadFileList",
                                data=data, files=files, headers=self._headers(), timeout=600)
                body = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:2000]
                self.trace.append({"label": self.label, "method": "POST",
                                   "path": "/index/knowledgeBase/file/uploadFileList",
                                   "part_keys": sorted(data.keys()),
                                   "file_part": "files", "status": r.status_code,
                                   "elapsed": round(time.time() - t0, 3)})
                return Resp("POST", "/index/knowledgeBase/file/uploadFileList",
                            r.status_code, body, elapsed=time.time() - t0)
            except Exception as e:
                self.trace.append({"label": self.label, "path": "upload", "error": repr(e)})
                return Resp("POST", "upload", -1, {"transport_error": repr(e)})

    def file_status(self, file_id):
        return self.get(f"/index/knowledgeBase/file/getFileStatusById?fileId={file_id}")

    def file_list(self, kb_id, page=1, size=100):
        return self.get(f"/index/knowledgeBase/file/list?kbId={kb_id}&pageNo={page}&pageSize={size}")

    def chunks(self, kb_id, doc_id, page=1, size=200):
        return self.get(f"/index/knowledgeBase/file/getFileChunks?kbId={kb_id}"
                        f"&docId={doc_id}&pageNo={page}&pageSize={size}")

    def file_delete(self, file_id):
        return self.delete(f"/index/knowledgeBase/file/delete?id={file_id}")

    def ask(self, session_id, query_id, content, extra=None):
        """SSE 提问；返回 Resp，body 里塞 {'reply': 全文, 'frames': [...], 'refs': [...]}"""
        payload = {"sessionId": session_id, "queryId": query_id,
                   "content": content, "type": "text", "sysType": "KNO_INDEX"}
        if extra:
            payload.update(extra)
        t0 = time.time()
        h = self._headers({"Accept": "text/event-stream", "Content-Type": "application/json"})
        try:
            r = self.s.post(f"{GATEWAY}/qa/ai/question_re", json=payload, headers=h,
                            stream=True, timeout=900)
        except Exception as e:
            self.trace.append({"label": self.label, "path": "/qa/ai/question_re",
                               "req_keys": sorted(payload), "error": repr(e)})
            return Resp("POST", "/qa/ai/question_re", -1, {"transport_error": repr(e)})

        text, frames = [], []
        # 注意：不能 decode_unicode=True —— requests 按 chunk 解码会把跨块的多字节 UTF-8 撕开，
        # 中文会变成 mojibake，后面的"要点支撑"比对就全错。改为按行取 bytes 再逐行 utf-8 解码。
        for raw in r.iter_lines(decode_unicode=False):
            if not raw:
                continue
            raw = raw.decode("utf-8", errors="replace")
            line = raw[5:].strip() if raw.startswith("data:") else raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                text.append(line)
                continue
            frames.append(obj)
            rep = obj.get("reply") or {}
            if isinstance(rep, dict) and rep.get("content"):
                text.append(rep["content"])

        refs = []
        for fr in frames:
            if fr.get("reference"):
                try:
                    v = fr["reference"]
                    refs = json.loads(v) if isinstance(v, str) else v
                except Exception:
                    pass
        body = {"reply": "".join(text), "frames": frames, "refs": refs,
                "http": r.status_code, "n_frames": len(frames)}
        self.trace.append({"label": self.label, "method": "POST",
                           "path": "/qa/ai/question_re", "status": r.status_code,
                           "req_keys": sorted(payload.keys()),
                           "query_len": len(content),
                           "elapsed": round(time.time() - t0, 3)})
        resp = Resp("POST", "/qa/ai/question_re", r.status_code, body,
                    elapsed=time.time() - t0)
        resp.req_keys = sorted(payload.keys())
        resp.req_body = payload
        return resp

    def dialog(self, session_id):
        return self.get(f"/qa/dialogue/getDialogBySessionId?sessionId={session_id}")

    def dialog_list(self, page=1, size=10):
        return self.get(f"/qa/dialogue/list?pageNo={page}&pageSize={size}")

    def dialog_create(self, title="QA独立复核会话"):
        return self.post("/qa/dialogue/create", {"title": title, "sysType": "KNO_INDEX"})
