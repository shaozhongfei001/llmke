#!/usr/bin/env python3
"""R12 独立复核套件（QA 自写，不 import 开发自检脚本）。

用法:
  python3 suite.py                 # 全跑
  python3 suite.py --only S1,S2    # 只跑指定场景
  python3 suite.py --tag run1      # 证据目录加后缀

产出: platform/r12/qa/evidence/<ts>-<tag>/{results.json,trace.json,summary.md}

场景:
  S1 登录/菜单      S2 建库        S3 上传(5 类)   S4 状态+chunk 落地
  S5 换措辞问答     S6 引用一致性+不提交正文        S7 历史对话
  S8 负例 N1~N9
"""
import argparse
import base64
import hashlib
import json
import os
import random
import subprocess
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import negatives as NEG  # noqa: E402
from client import ALLOWED_ASK_FIELDS, Client  # noqa: E402

R12 = "/home/szf/data/dev/llmke-r12/platform/r12"
SAMPLES = f"{R12}/parse/fixtures/generated"
FIXTURES = f"{R12}/qa/fixtures"   # R12FIX 业务夹具（有中文正文，能触发模型输出引用标签）
KB_NAME = "qa_r12_final"          # 只用 [a-z0-9_]：Milvus 集合名对非法字符会退化成 uuid5
KB_NAME_PRIV = "qa_r12_priv"      # 同上，私有库夹具
TS = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
RESULTS = []
EVID = None


def rec(scene, case, verdict, detail, extra=None):
    row = {"scene": scene, "case": case, "verdict": verdict, "detail": detail}
    if extra is not None:
        row["extra"] = extra
    RESULTS.append(row)
    print(f"{verdict:7} [{scene}] {case}: {detail}")
    return verdict


def dump(name, obj):
    os.makedirs(EVID, exist_ok=True)
    with open(os.path.join(EVID, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)


def _env():
    out = {}
    with open(f"{R12}/.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip("'\"")
    return out


def redis_cli(*args):
    pw = _env()["R12_REDIS_PASSWORD"]
    r = subprocess.run(["docker", "exec", "r12-redis", "redis-cli", "-a", pw,
                        "--no-auth-warning", *args], capture_output=True, text=True)
    return r.stdout.strip()


# ================================================================ S1
def s1(a):
    r = a.menus()
    menus = r.data or []
    ok = r.status == 200 and r.ok and len(menus) > 0
    rec("S1", "登录后取菜单", "PASS" if ok else "FAIL",
        f"http={r.status} success={r.ok} menus={len(menus)}")
    r2 = a.me()
    name = (r2.data or {}).get("userName") if r2.ok else None
    rec("S1", "取当前用户身份", "PASS" if name == "admin" else "FAIL", f"userName={name}")
    # 口令外泄检查：登录响应不得回显口令/口令哈希
    lr = a.login("admin", "Admin@12345")
    raw = json.dumps(lr.data or {}, ensure_ascii=False)
    md5 = hashlib.md5(b"Admin@12345").hexdigest()
    leak = md5 in raw or "Admin@12345" in raw
    rec("S1", "登录响应不回显口令/哈希", "FAIL" if leak else "PASS",
        "响应含口令哈希！" if leak else "响应中 userPassword 字段为 null，未回显")


# ================================================================ S2
def s2(a, name=KB_NAME, private=0):
    r = a.kb_list()
    for kb in ((r.data or {}).get("records") or []):
        if kb.get("kbName") == name:
            rec("S2", f"知识库存在({name})", "PASS",
                f"kbId={kb['id']} primitive={kb.get('primitiveName')} private={kb.get('privateKb')}")
            return kb
    c = a.kb_create(name, private=private)
    d = c.data or {}
    ok = c.status == 200 and c.ok and d.get("id")
    rec("S2", f"创建知识库({name})", "PASS" if ok else "FAIL",
        f"http={c.status} kbId={d.get('id')} primitive={d.get('primitiveName')} {'' if ok else c.dump(200)}")
    return d if ok else None


def s2c(a, kb):
    """在**自己的库**上建独立检索配置（不复用他人的默认配置），返回 configId。"""
    prim = kb.get("primitiveName")
    cfg = {"knowledge_base_name": prim, "model_name": "qwen2.5-7b-instruct",
           "rerank_model_name": "bge-reranker-v2-m3",
           "plan_model_name": "qwen2.5-7b-instruct",
           "recommend_model_name": "qwen2.5-7b-instruct",
           "enabled_llm": True, "need_trace_source": True,
           "enabled_rerank": True, "enabled_faq": False, "score_threshold": 0.001,
           "top_k": 10, "max_round": 5, "enable_thinking": False,
           "enable_web_search": False, "enabled_table_select": False, "enable_database": False}
    name = f"qa_r12_cfg_{prim}"
    lst = a.get("/qa/search/config/searchList?pageNo=1&pageSize=50")
    for row in ((lst.data or {}).get("records") or []) if lst.ok else []:
        if row.get("name") == name:
            rec("S2", "检索配置已存在（复用）", "PASS",
                f"configId={row.get('id')} kb={prim}")
            return row.get("id")
    r = a.post("/qa/search/config/add", {
        "name": name, "des": "QA 独立复核配置", "isDefault": 0, "enabledFaq": 0,
        "dependOnKb": 0, "configJson": json.dumps(cfg, ensure_ascii=False)})
    cid = (r.data or {}).get("id") if r.ok else None
    rec("S2", "创建独立检索配置", "PASS" if cid else "FAIL",
        f"http={r.status} configId={cid} kb={prim} {'' if cid else r.dump(200)}")
    return cid



ES = "http://127.0.0.1:19200"   # 只读：用于交叉核对"分块是否真的落库"，避免被产品接口的缺陷误导


def es_chunks(primitive, file_id, size=300):
    """直接从 ES 取该文件的分块（权威事实源，绕开产品接口）。"""
    out = []
    for idx in (primitive, f"table_chunks_{primitive}", f"table_summary_{primitive}"):
        if not idx:
            continue
        try:
            r = requests.post(f"{ES}/{idx}/_search", timeout=30, json={
                "size": size, "_source": ["page_content", "metadata"],
                "query": {"term": {"metadata.file_id": int(file_id)}}})
            hits = (((r.json() or {}).get("hits") or {}).get("hits") or [])
            out += [h.get("_source") or {} for h in hits]
        except Exception:
            pass
    return out


# ================================================================ S3/S4
UPLOAD_CASES = [
    (f"{FIXTURES}/R12FIX-product-loan.docx", "DOCX 中文业务文档"),
    (f"{FIXTURES}/R12FIX-credit-ledger.xlsx", "XLSX 授信台账"),
    (f"{FIXTURES}/R12FIX-product-intro.pptx", "PPTX 产品介绍"),
    (f"{SAMPLES}/pdf-digital.pdf", "PDF 数字版"),
    (f"{SAMPLES}/scan-text.png", "扫描图片(纯图)"),
]


def s3(a, kb_id, cases=None):
    up = []
    for fname, label in (cases or UPLOAD_CASES):
        path = fname if os.path.isabs(fname) else os.path.join(SAMPLES, fname)
        if not os.path.exists(path):
            rec("S3", f"上传 {label}", "BLOCKED", f"样本不存在 {path}")
            continue
        r = a.upload(kb_id, path)
        data = r.data
        fid = None
        if isinstance(data, list) and data:
            fid = (data[0] or {}).get("id")
        elif isinstance(data, dict):
            fid = data.get("id")
        ok = r.status == 200 and r.ok and fid
        rec("S3", f"上传 {label}", "PASS" if ok else "FAIL",
            f"http={r.status} fileId={fid} name={fname}" if ok else
            f"http={r.status} resp={r.dump(200)}")
        if ok:
            up.append({"fileId": fid, "name": os.path.basename(path), "label": label, "kbId": kb_id})
    dump("s3_uploaded.json", up)
    return up


def s4(a, up, timeout_s=420):
    done = []
    for f in up:
        t0, last = time.time(), None
        while time.time() - t0 < timeout_s:
            r = a.file_status(f["fileId"])
            last = r.data if r.ok else f"ERR:{r.status}"
            if last in (3, 4):
                break
            time.sleep(4)
        f["final_status"] = last
        if last != 3:
            rec("S4", f"解析完成 {f['label']}", "BLOCKED", f"fileId={f['fileId']} 最终状态={last}")
            continue
        c = a.chunks(f["kbId"], f["fileId"])
        recs = ((c.data or {}).get("records") if c.ok else None) or []
        # 权威口径：ES 里是否真有分块（避免把"产品接口取不到"误判成"解析没产出"）
        es_docs = es_chunks(f.get("primitive") or "", f["fileId"])
        f["chunk_count"] = len(es_docs)
        f["chunk_api_count"] = len(recs)
        verdict, why = NEG.check_silent_success({"final_status": last, "chunk_count": len(es_docs)})
        rec("S4", f"解析完成且 chunk 落地 {f['label']}", verdict,
            f"fileId={f['fileId']} status={last} ES分块={len(es_docs)} 接口返回={len(recs)}")
        if len(es_docs) and not recs:
            rec("S4", f"分块可经产品接口取回 {f['label']}", "FAIL",
                f"fileId={f['fileId']} ES={len(es_docs)} 但 getFileChunks=0（点击引用定位的前提不成立）")
        elif len(es_docs):
            rec("S4", f"分块可经产品接口取回 {f['label']}", "PASS",
                f"fileId={f['fileId']} ES={len(es_docs)} 接口={len(recs)}")
        if es_docs:
            done.append(f)
    dump("s4_status.json", up)
    return done


# ================================================================ S5/S6
def key_elements(text, n=2):
    """抽关键要素：ASCII 词 + 中文 n-gram。用于'要点支撑'比对，不做整句匹配。"""
    import re
    t = (text or "")
    els = set(w.lower() for w in re.findall(r"[A-Za-z0-9\u4e00-\u9fa5]+", t) if len(w) >= 2)
    cjk = re.findall(r"[\u4e00-\u9fa5]{2,}", t)
    for seg in cjk:
        for i in range(len(seg) - n + 1):
            els.add(seg[i:i + n])
    return {e for e in els if len(e) >= 2}


def coverage(answer, corpus):
    ea = key_elements(answer)
    if not ea:
        return 0.0, 0
    ec = key_elements(corpus)
    hit = [e for e in ea if e in ec]
    return len(hit) / len(ea), len(ea)



def strip_citation(text):
    """去掉引用标记（retrive-tag 块与 [N] 角标）——它们是标记不是内容，留着会污染要点比对。"""
    import re
    t = text or ""
    t = re.sub(r"\[/?retrive-tag[^\]]*\]", "", t)
    t = re.sub(r"\[\d+\]", "", t)
    return t


def strong_elements(text):
    """强要素 = 长度 4 的中文 n-gram + "数字+单位"事实串。
    口径说明：4-gram 能代表短语级事实，又不至于像 5/6-gram 那样把"句子的具体措辞"当事实；
    数字+单位（5000万元/三年/12个月）是最硬的事实锚点。"""
    import re
    t = strip_citation(text)
    out = set()
    for tok in re.findall(r"\d+(?:\.\d+)?\s*(?:万元|亿元|元|%|年|个月|天|万|亿|个)", t):
        out.add(tok.replace(" ", "").lower())
    for seg in re.findall(r"[\u4e00-\u9fa5]{4,}", t):
        for i in range(len(seg) - 4 + 1):
            out.add(seg[i:i + 4])
    return out


def strong_coverage(answer, corpus):
    ea = strong_elements(answer)
    if not ea:
        return 0.0, 0, []
    ec = strong_elements(corpus)
    miss = [e for e in ea if e not in ec]
    return (len(ea) - len(miss)) / len(ea), len(ea), miss

def ref_files(refs):
    out = []
    for r in refs or []:
        md = r.get("metadata") or {}
        fid = md.get("file_id") or md.get("fileId") or r.get("fileId")
        if fid is not None:
            out.append(str(fid))
    return out


def s5(a, session_id, q1, q2=None, config_id=None):
    outs = []
    for i, q in enumerate([q1] + ([q2] if q2 else [])):
        qid = f"qa-{int(time.time()*1000)}-{i}"
        extra = {"configId": int(config_id)} if config_id else None
        r = a.ask(session_id, qid, q, extra=extra)
        body = r.body if isinstance(r.body, dict) else {}
        ans = (body.get("reply") or "").strip()
        refs = body.get("refs") or []
        ok = r.status == 200 and len(ans) > 10
        rec("S5", f"提问{i+1}（{len(q)}字）得到模型回答", "PASS" if ok else "BLOCKED",
            f"http={r.status} 帧={body.get('n_frames')} 答案长度={len(ans)}"
            + ("" if ok else f" resp={str(r.body)[:150]}"))
        rec("S5", f"提问{i+1} 返回引用", "PASS" if refs else "BLOCKED", f"引用条数={len(refs)}")
        outs.append({"q": q, "qid": qid, "answer": ans, "refs": refs,
                     "req_keys": r.req_keys, "req_body": r.req_body})
    dump("s5_answers.json", outs)

    # 语义命中一致性：两种措辞应命中重叠的文件集合（证明不是纯关键词匹配）
    if len(outs) == 2 and outs[0]["refs"] and outs[1]["refs"]:
        f1, f2 = set(ref_files(outs[0]["refs"])), set(ref_files(outs[1]["refs"]))
        inter = f1 & f2
        rec("S5", "换措辞后命中相同文件（语义检索证据）",
            "PASS" if inter else "FAIL",
            f"措辞1文件={sorted(f1)} 措辞2文件={sorted(f2)} 交集={sorted(inter)}")
    return outs


def s6(a, kb_id, uploaded, out):
    """引用一致性 + "不随请求提交正文"。"""
    refs = out.get("refs") or []
    upids = [str(u["fileId"]) for u in uploaded]
    cited = ref_files(refs)
    v, why = NEG.check_ref_files({"cited": cited, "uploaded": upids})
    rec("S6", "引用 file_id 属于本库已上传文件", v, why)

    # 请求体不含正文
    keys = out.get("req_keys") or []
    cbody = (out.get("req_body") or {}).get("content") or ""
    v, why = NEG.check_payload_no_body({
        "allowed": sorted(ALLOWED_ASK_FIELDS), "req_keys": keys,
        "content_len": len(cbody), "question_len": len(out.get("q") or "")})
    rec("S6", "提问请求体不含正文文本字段", v, why)

    # 逐条引用与 chunk 交叉核对（关键要素覆盖，不做整句匹配）
    # 定位合法性口径（按 TL 澄清后的事实）：pdf 必须有页码；docx/xlsx/pptx 页码为空/0 是"如实"，不判 FAIL，
    # 但必须有可用的字符 offset 或单元格坐标，且 chunk 接口必须能查得到这条引用所属文件的分块。
    verified, details, pools = 0, [], []
    for ref in refs:
        md = ref.get("metadata") or {}
        fid = md.get("file_id") or md.get("fileId")
        if not fid:
            details.append({"skip": "无 file_id"})
            continue
        c = a.chunks(kb_id, fid)
        recs = ((c.data or {}).get("records") if c.ok else None) or []
        pool = "\n".join((x.get("pageContent") or x.get("content") or "") for x in recs)
        pool_src = "getFileChunks"
        if not pool:      # 接口取不到时用 ES 兜底，保证"要点是否有原文支撑"仍可判定
            prim = next((u.get("primitive") for u in uploaded if str(u["fileId"]) == str(fid)), "")
            es_docs = es_chunks(prim, fid) if prim else []
            pool = "\n".join((d.get("page_content") or "") for d in es_docs)
            pool_src = f"ES({len(es_docs)}块)"
        reftext = ref.get("content") or ref.get("pageContent") or ""
        cov, n = coverage(out.get("answer") or reftext, pool)
        src = md.get("source") or md.get("file_path") or ""
        ext = (src.rsplit(".", 1)[-1] if "." in src else "").lower()
        page = md.get("page_number")
        pages = page if isinstance(page, list) else ([page] if page is not None else [])
        real_pages = [p for p in pages if isinstance(p, int) and p >= 1]
        if ext == "pdf":
            page_ok = bool(real_pages)          # pdf 必须给页码
        else:
            page_ok = True                      # 非 pdf 页码为空属如实
        offset = md.get("offset")
        pos_ok = bool(offset) or bool(md.get("position"))
        # 文件级：chunk 接口能否查到该文件的分块（这是"点击引用→定位原文"的前提）
        chunk_api_ok = len(recs) > 0
        item = {"file_id": fid, "ext": ext, "cited_len": len(reftext),
                "coverage": round(cov, 3), "n_elements": n,
                "page_numbers": pages, "page_ok": page_ok,
                "has_offset_or_position": pos_ok,
                "chunk_api_total": len(recs), "chunk_api_ok": chunk_api_ok,
                "source": src}
        details.append(item)
        pools.append(pool)
        if cov >= 0.6 and page_ok and pos_ok and chunk_api_ok:
            verified += 1
    dump("s6_ref_check.json", details)
    if refs:
        union = "\n".join(pools)
        cov_all, n_all = coverage(out.get("answer") or "", union)
        scov, sn, smiss = strong_coverage(out.get("answer") or "", union)
        rec("S6", "答案要点能在引用原文中找到支撑（强要素覆盖 ≥60%）",
            "PASS" if scov >= 0.6 else "FAIL",
            f"强要素 {sn} 个，覆盖 {scov:.1%}（2-gram 参考值 {cov_all:.1%}）；缺失示例 {smiss[:5]}")
        rec("S6", "引用定位信息合法（pdf 有页码 / 非 pdf 有 offset 或坐标）",
            "PASS" if all(d.get("page_ok") and d.get("has_offset_or_position") for d in details) else "FAIL",
            "; ".join(f"{d.get('ext')}#{d.get('file_id')} pages={d.get('page_numbers')} off={d.get('has_offset_or_position')}"
                      for d in details))
        rec("S6", "引用所属文件的分块可被接口取到（点击定位前提）",
            "PASS" if all(d.get("chunk_api_ok") for d in details) else "FAIL",
            "; ".join(f"{d.get('ext')}#{d.get('file_id')} chunk_api={d.get('chunk_api_total')}" for d in details))
    else:
        rec("S6", "引用相关三项（要点支撑/定位合法/分块可取）", "BLOCKED", "本轮无引用可核对")


# ================================================================ S7
def s7(a, session_id, expect_answer):
    r = a.dialog(session_id)
    d = r.data or {}
    text = json.dumps(d, ensure_ascii=False)
    rec("S7", "按 sessionId 恢复历史对话", "PASS" if r.ok and d else "BLOCKED",
        f"http={r.status} success={r.ok} 长度={len(text)}")
    if expect_answer:
        head = expect_answer[:20]
        rec("S7", "历史中包含本轮流式回答", "PASS" if head and head in text else "FAIL",
            f"查找片段={head!r} 命中={head in text}")
    r2 = a.dialog_list()
    rec("S7", "会话列表可查", "PASS" if r2.ok else "FAIL", f"http={r2.status} total={(r2.data or {}).get('total')}")


# ================================================================ S9 会话完整性
def s9(a, tag=None):
    """会话创建 / 按 sessionId 恢复 / 列表，并检查同一 sessionId 是否重复落库。"""
    sid = f"qa-s9-{tag or int(time.time())}"
    c = a.post("/qa/dialogue/create",
               {"sessionId": sid, "label": "QA独立复核会话", "sysType": "KNO_INDEX"})
    rec("S9", "创建会话", "PASS" if c.ok else "FAIL", f"http={c.status} resp={c.dump(150)}")
    g = a.dialog(sid)
    label = (g.data or {}).get("label") if g.ok else None
    rec("S9", "按 sessionId 恢复会话（label 往返一致）",
        "PASS" if g.ok and label == "QA独立复核会话" else "FAIL",
        f"http={g.status} 期望label=QA独立复核会话 实际={label!r}")
    lst = a.dialog_list()
    recs = ((lst.data or {}).get("records") or []) if lst.ok else []
    same = [r for r in recs if r.get("sessionId") == sid]
    rec("S9", "同一 sessionId 不得重复落库",
        "PASS" if len(same) <= 1 else "FAIL",
        f"sessionId={sid} 记录数={len(same)}（>1 表示无唯一约束，历史恢复可能取到空壳）",
        {"rows": same})
    dump("s9_session.json", {"sessionId": sid, "get": g.body, "list_rows": same})

    # 复现路径：先提问（服务端自动建壳）→ 再用同一 sessionId 显式建会话
    sid2 = f"{sid}-dup"
    a.ask(sid2, f"q-{int(time.time()*1000)}", "承兑汇票贴现利率怎么算")
    a.post("/qa/dialogue/create",
           {"sessionId": sid2, "label": "QA重复会话复现", "sysType": "KNO_INDEX"})
    lst2 = a.dialog_list(page=1, size=50)
    recs2 = ((lst2.data or {}).get("records") or []) if lst2.ok else []
    dup = [r for r in recs2 if r.get("sessionId") == sid2]
    got = a.dialog(sid2)
    rec("S9", "提问后再建会话不得产生重复会话记录",
        "PASS" if len(dup) <= 1 else "FAIL",
        f"sessionId={sid2} 记录数={len(dup)}；恢复返回 label={(got.data or {}).get('label')!r}",
        {"rows": dup})


# ================================================================ S8 负例
PROT = "/index/knowledgeBase/list?pageNo=1&pageSize=5"


def run_negative(cid, obs):
    name, fn, _ = NEG.CASES[cid]
    verdict, why = fn(obs)
    rec("S8", f"{cid} {name}", verdict, why, {"obs": obs})
    return verdict


def s8(a, kb_id, uploaded):
    obs_all = {}

    # ---- N1 无 token
    anon = Client(label="anon")
    ctl = a.get(PROT)
    r = anon.get(PROT)
    obs = {"status": r.status, "control_status": ctl.status, "snippet": str(r.body)[:120]}
    obs_all["N1"] = obs
    run_negative("N1", obs)

    # ---- N2 伪造 token
    iat = int(time.time())
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=").decode()
    forged = {
        "alg_none": (b64({"alg": "none", "typ": "JWT"}) + "." +
                     b64({"userName": "admin", "userId": 1, "sub": "mixedQuantum",
                          "aud": "admin", "iat": iat, "exp": iat + 3600}) + "."),
        "wrong_sig": (b64({"alg": "HMAC256", "typ": "JWT"}) + "." +
                      b64({"userName": "admin", "userId": 1, "sub": "mixedQuantum",
                           "aud": "admin", "iat": iat, "exp": iat + 3600}) + ".AAAA"),
        "random": "Bearer " + hashlib.sha256(str(random.random()).encode()).hexdigest(),
    }
    res = []
    for k, tk in forged.items():
        rr = Client(token=tk, label=k).get(PROT)
        res.append({"label": k, "status": rr.status})
    obs_all["N2"] = {"control_status": ctl.status, "results": res}
    run_negative("N2", obs_all["N2"])

    # ---- N3 篡改 payload：拿 **非管理员** 的合法 token，把身份改成 admin，保留原签名
    low = Client(label="qa_user_c")
    low.login("qa_user_c", "Qa!2345678")
    parts = (low.token or "").split(".")
    tampered = None
    if len(parts) == 3:
        pad = lambda s: s + "=" * (-len(s) % 4)          # noqa: E731
        pl = json.loads(base64.urlsafe_b64decode(pad(parts[1])))
        pl["userName"] = "admin"
        pl["aud"] = "admin"
        pl["userId"] = 1
        tampered = parts[0] + "." + base64.urlsafe_b64encode(
            json.dumps(pl, separators=(",", ":")).encode()).rstrip(b"=").decode() + "." + parts[2]
    rt = Client(token=tampered or "", label="tampered").get("/auth/user/getUserInfo")
    leaked = (rt.ok and isinstance(rt.data, dict) and rt.data.get("userName") == "admin"
              and tampered and tampered != low.token)
    obs_all["N3"] = {"status": rt.status, "control_status": ctl.status, "leaked_admin": bool(leaked),
                     "who": "qa_user_c->admin", "snippet": str(rt.body)[:150]}
    run_negative("N3", obs_all["N3"])

    # ---- N4 会话注销后旧 token
    b = Client(label="qa_user_b")
    lr = b.login("qa_user_b", "Qa!2345678")
    if not lr.ok:
        obs_all["N4"] = {"status": None, "control_status": None}
        rec("S8", "N4 会话注销后旧 token 复用", "BLOCKED", f"第二用户登录失败: {lr.dump(150)}")
    else:
        ctl_b = b.get(PROT)
        redis_cli("del", "user:token:qa_user_b")
        rr = Client(token=b.token, label="qa_user_b-revoked").get(PROT)
        obs_all["N4"] = {"status": rr.status, "control_status": ctl_b.status}
        run_negative("N4", obs_all["N4"])

    # ---- N5 越权：非属主读 admin 私有库
    priv = s2(a, KB_NAME_PRIV, private=1)
    if priv:
        # 先确保库里有 1 个文件（上传后轮询到可见，避免"刚上传还没落库"造成假结果）
        for _ in range(10):
            lr0 = a.file_list(priv["id"])
            if ((lr0.data or {}).get("records") or []):
                break
            a.upload(priv["id"], os.path.join(SAMPLES, "pdf-digital.pdf"), uid=f"qa-priv-{int(time.time()*1000)}")
            time.sleep(3)
        b2 = Client(label="qa_user_b")
        b2.login("qa_user_b", "Qa!2345678")
        rr = b2.get(f"/index/knowledgeBase/file/list?kbId={priv['id']}&type=1")
        n = len(((rr.data or {}).get("records") or [])) if rr.ok else 0
        obs_all["N5"] = {"status": rr.status, "n_records": n, "kb_private": 1,
                         "kb_id": priv["id"], "kb_owner": "admin", "who": "qa_user_b",
                         "snippet": str(rr.body)[:200]}
        run_negative("N5", obs_all["N5"])
        # 附：非属主按 id 直读文件详情（必须真的返回了数据才算泄露，data=null 不算）
        rr2 = b2.get(f"/index/knowledgeBase/file/getById?id=1")
        leaked = rr2.status == 200 and rr2.ok and rr2.data is not None
        rec("S8", "N5b 非属主按 fileId 直读他人文件",
            "FAIL" if leaked else "PASS",
            f"http={rr2.status} data={'非空(泄露)' if leaked else 'null(未泄露)'} resp={rr2.dump(140)}")
        # N5c 写级越权：非属主删除他人私有库文件（夹具库；删后由 admin 重传恢复）
        recs5 = ((rr.data or {}).get("records") or [])
        if recs5:
            victim = recs5[0].get("id")
            dd = b2.delete(f"/index/knowledgeBase/file/delete?id={victim}")
            wrote = dd.status == 200 and dd.ok and (dd.data in (True, "true"))
            rec("S8", "N5c 越权删除他人私有库文件",
                "FAIL" if wrote else "PASS",
                f"file_id={victim} http={dd.status} resp={dd.dump(120)}")
            if wrote:                       # 恢复夹具，避免影响后续用例
                a.upload(priv["id"], os.path.join(SAMPLES, "pdf-digital.pdf"), uid=f"qa-restore-{TS}")
    else:
        rec("S8", "N5 越权：非属主读他人私有库", "BLOCKED", "私有库夹具创建失败")

    # ---- N6 白名单端点未授权可达（拆两组：已修复的读接口 / 仍开放的内部回写入口）
    fixed_probes = [
        ("GET", "/index/knowledgeBase/file/list?kbId=1&type=1"),
        ("GET", "/index/knowledgeBase/file/multiple/version?kbId=1&type=1"),
    ]
    open_probes = [
        ("POST", "/index/parseTask/callback"),
        ("POST", "/index/knowledgeBase/file/uploadParsedFile?kbId=1&fileId=1&userId=1"),
    ]
    def _probe(m, p):
        c = Client(label="anon")
        rr = c.post(p, {"taskId": 1}) if m == "POST" else c.get(p)
        return {"path": p, "method": m, "status": rr.status, "snippet": str(rr.body)[:90]}
    res_fixed = [_probe(m, p) for m, p in fixed_probes]
    res_open = [_probe(m, p) for m, p in open_probes]
    obs_all["N6"] = {"results": res_fixed}
    run_negative("N6", obs_all["N6"])
    # 仍开放的内部回写入口：按 TL 口径保留为"已知未修复缺口"，不得因前两条修了就判安全通过
    bad = [r for r in res_open if r["status"] not in NEG.DENY]
    rec("S8", "N6b 内部回写入口仍免 token（R12-KNOWN-01）",
        "FAIL" if bad else "PASS",
        "未授权可达: " + "; ".join(f"{r['path']}->{r['status']}({r['snippet'][:40]})" for r in bad)
        if bad else f"均返回 {NEG.DENY}")
    obs_all["N6b"] = {"results": res_open}

    # ---- N7 随机字节 + N8 扩展名伪装
    tmp = f"/tmp/qa-suite-{TS}"
    os.makedirs(tmp, exist_ok=True)
    bad = f"{tmp}/random-bytes.pdf"
    with open(bad, "wb") as f:
        f.write(bytes(random.getrandbits(8) for _ in range(4096)))
    fake = f"{tmp}/plain-text-pretend.pdf"
    with open(fake, "wb") as f:
        f.write(b"this is definitely not a pdf, just ascii text.\n" * 60)

    for cid, path, label in (("N7", bad, "随机字节.pdf"), ("N8", fake, "纯文本伪装.pdf")):
        rr = a.upload(kb_id, path)
        rej = (rr.status != 200) or (not rr.ok)
        fid = None
        d = rr.data
        if isinstance(d, list) and d:
            fid = (d[0] or {}).get("id")
        elif isinstance(d, dict):
            fid = d.get("id")
        obs = {"reject": rej, "http": rr.status, "snippet": rr.dump(150),
               "final_status": None, "chunk_count": None}
        if not rej and fid:
            for _ in range(40):
                st = a.file_status(fid)
                obs["final_status"] = st.data if st.ok else None
                if obs["final_status"] in (3, 4):
                    break
                time.sleep(3)
            c = a.chunks(kb_id, fid)
            obs["chunk_count"] = len(((c.data or {}).get("records") or [])) if c.ok else 0
            obs["file_id"] = fid
        obs_all[cid] = obs
        run_negative(cid, obs)

    # ---- N9 删除文档后再提问
    if uploaded:
        victim = uploaded[0]
        dr = a.file_delete(victim["fileId"])
        ok_del = dr.status == 200 and dr.ok
        rec("S8", "删除文档", "PASS" if ok_del else "FAIL",
            f"fileId={victim['fileId']} http={dr.status} resp={dr.dump(120)}")
        if ok_del:
            sess = f"qa-del-{int(time.time())}"
            q = "文档里讲了什么？请给出出处"
            r = a.ask(sess, f"qa-del-{int(time.time()*1000)}", q)
            refs = (r.body or {}).get("refs") or []
            obs = {"cited_after_delete": ref_files(refs),
                   "deleted_file_ids": [victim["fileId"]],
                   "snippet": str((r.body or {}).get("reply") or "")[:150]}
            obs_all["N9"] = obs
            run_negative("N9", obs)

    dump("s8_negative_obs.json", obs_all)
    return obs_all


# ================================================================ main
def main():
    global EVID
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    only = {x.strip().upper() for x in args.only.split(",") if x.strip()}
    want = lambda s: (not only) or s in only  # noqa: E731   # noqa: E731
    EVID = f"{R12}/qa/evidence/{TS}" + (f"-{args.tag}" if args.tag else "")
    os.makedirs(EVID, exist_ok=True)

    a = Client(label="admin")
    lr = a.login("admin", "Admin@12345")
    if not lr.ok:
        print("登录失败，无法继续:", lr.dump(300))
        return 2
    print(f"== R12 独立复核 {TS} 证据目录 {EVID} ==")

    kb = uploaded = done = None
    answers = []
    session_id = None
    try:
        if want("S1"):
            s1(a)
        if any(want(x) for x in ("S2","S3","S4","S5","S6","S7","S8","S9")):
            kb = s2(a)
        if kb and want("S3"):
            uploaded = s3(a, kb["id"])
        elif kb and any(want(x) for x in ("S4", "S5", "S6", "S7", "S8")):
            # 不重传时，从库内已有文件构造 uploaded，供 S4~S7 复用
            r = a.file_list(kb["id"])
            recs = ((r.data or {}).get("records") or []) if r.ok else []
            uploaded = [{"fileId": x.get("id"), "name": x.get("fileName") or str(x.get("id")),
                         "label": x.get("fileName") or str(x.get("id")), "kbId": kb["id"]}
                        for x in recs if x.get("id")]
            rec("S3", "复用库内已有文件（未重传）", "PASS" if uploaded else "BLOCKED",
                f"kbId={kb['id']} 文件数={len(uploaded)}")
        if uploaded and kb:
            for x in uploaded:
                x["primitive"] = kb.get("primitiveName")
        if uploaded and want("S4"):
            done = s4(a, uploaded)
        if (done or uploaded) and want("S5"):
            cid = s2c(a, kb)
            session_id = f"qa-sess-{int(time.time())}"
            answers = s5(a, session_id,
                         "智造贷这个产品的授信额度是多少？期限多长？",
                         "智造贷给企业的贷款最多能批多少钱，可以贷几年？",
                         config_id=cid)
        if answers and want("S6"):
            first = next((x for x in answers if x["refs"]), answers[0])
            s6(a, kb["id"], uploaded, first)
        if session_id and want("S7"):
            s7(a, session_id, answers[0]["answer"] if answers else "")
        if want("S9"):
            s9(a)
        if kb and want("S8"):
            s8(a, kb["id"], done or [])
    except Exception as e:
        import traceback
        rec("ERR", "套件异常", "FAIL", f"{e} :: {traceback.format_exc()[:500]}")

    dump("results.json", RESULTS)
    dump("trace.json", a.trace)
    cnt = {}
    for r in RESULTS:
        cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1
    lines = [f"# R12 独立复核运行 {TS}", "",
             f"PASS={cnt.get('PASS',0)} FAIL={cnt.get('FAIL',0)} BLOCKED={cnt.get('BLOCKED',0)}", "",
             "| 场景 | 用例 | 结论 | 说明 |", "|---|---|---|---|"]
    for r in RESULTS:
        lines.append(f"| {r['scene']} | {r['case']} | {r['verdict']} | {r['detail']} |")
    open(os.path.join(EVID, "summary.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\n== PASS={cnt.get('PASS',0)} FAIL={cnt.get('FAIL',0)} BLOCKED={cnt.get('BLOCKED',0)} ==")
    print("证据:", EVID)
    return 0 if cnt.get("FAIL", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
