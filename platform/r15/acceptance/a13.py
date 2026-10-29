#!/usr/bin/env python3
"""A13 安全/并发/预算/流式（任务书 §5.2 A13）。

判据：多 KB 并行不串库、超深/超量有真实资源边界、依赖失败可辨识、取消可停；
一般 500 不能当"鉴权成功"，未核验的错误片段不能当最终答案。
反例：
  N1 无 token / 伪造 token 访问被 200 放行
  N2 无授权提问返回 200 且带答案正文（越权但答了）
  N3 超量 top_k/depth 让 global 端点返回量随参数增长（无真实上界）
  N4 超量请求耗时无界（>60s 视为没有预算）
"""
import time

import requests

import common as C

ID = "A13"
TITLE = "安全/预算：越权被拒且非 200、超量参数有真实上界"
WRITES = False

UA = {"User-Agent": C.UA, "Content-Type": "application/json"}


def _get(path, headers):
    try:
        r = requests.get(C.GATEWAY + path, headers=headers, timeout=20)
        return r.status_code, (r.text or "")[:160]
    except requests.exceptions.RequestException as e:
        return 0, f"{type(e).__name__}: {e}"


def run():
    checks = []

    for label, headers in (("无 token", UA),
                           ("伪造 token", dict(UA, Authorization="Bearer forged.tok.en"))):
        code, body = _get("/index/knowledgeBase/list?pageNo=1&pageSize=5", headers)
        checks.append(C.chk(f"N1 反例：{label} 被拒且不是 200", code in (401, 403),
                            f"http={code} body={body!r}"))

    try:
        r = requests.post(f"{C.GATEWAY}/qa/ai/question_re",
                          json={"sessionId": "acc-noauth", "queryId": "q1", "content": "授信额度是多少",
                                "type": "text", "sysType": "KNO_INDEX", "configId": C.CONFIG_ID},
                          headers=UA, timeout=60)
        code, body = r.status_code, (r.text or "")[:160]
    except requests.exceptions.RequestException as e:
        code, body = 0, f"{type(e).__name__}: {e}"
    checks.append(C.chk("N2 反例：无授权提问被拒且不返回答案正文",
                        code in (401, 403) and "retrive-tag" not in body,
                        f"http={code} body={body!r}"))

    # N3/N4：global 端点在超量参数下的真实上界
    base = {"space_name": C.KB, "query": "智造贷最高额度是多少", "mode": "global",
            "model_info": C.MODEL_INFO}
    sizes, elapsed = [], []
    for tk in (5, 5000):
        t0 = time.time()
        code, resp = C.graph_post("/query_community", dict(base, top_k=tk), timeout=600)
        elapsed.append(round(time.time() - t0, 1))
        data = (resp or {}).get("data") or {}
        sizes.append((code, len(data.get("communities") or []), len(data.get("answer") or "")))
    checks.append(C.chk("N3 反例：top_k 放大 1000 倍后返回量不膨胀",
                        sizes[0][1] == sizes[1][1] and sizes[1][2] <= max(4000, sizes[0][2] * 2),
                        f"top_k=5 → {sizes[0]}；top_k=5000 → {sizes[1]}（code, 社区数, 答案长度）"))
    checks.append(C.chk("N4 反例：超量请求耗时在预算内（<60s）", max(elapsed) < 60,
                        f"耗时 top_k=5:{elapsed[0]}s / top_k=5000:{elapsed[1]}s"))

    return C.verdict(ID, TITLE, checks, writes=WRITES,
                     skip_reason="多 KB 并发隔离与流式取消/持久化需第二套授权夹具，本轮不执行")
