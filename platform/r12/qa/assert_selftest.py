#!/usr/bin/env python3
"""R14 断言自检（F01/F03/F08）：证明收紧后的断言"能被假数据判 FAIL"，而不是又一次假绿。

为什么需要这个脚本（事实来源）：
  R13 四套验收登记 31/31、16/16、21/21、7/7 全绿，但评审用**函数级隔离调用**证明下面这些假数据
  都能进入各自脚本的通过分支：
    - VERSION：`groups=[]`（空版本列表）通过，因为断言是 `isinstance(groups, list)`，空列表恒真；
    - S7：`data: None`（空历史）通过，因为只校验 `success=true`；
    - S6：首块长度=0 通过，因为取错字段（服务返回 `content`，脚本取 `pageContent`）且不校验非空；
    - GLOBAL：「没有直接…的信息」这类拒答，只要带任意 source 就通过；
    - TABLE：答案里出现 "3000" 就通过，主体/单位/口径全不校验；
    - F08：`denied(500, {"success": false})` 返回 True —— 一般 5xx 被当成"已拒绝"。
  即：**"通过计数"本身不是业务能力的证据**，必须先证明断言有失败能力。

本脚本做什么：
  对每个被修断言做**双向**验证 ——
    - 反证（expected=False）：喂会骗过旧断言的假数据，新断言必须判 FAIL；
    - 正例（expected=True） ：喂合规数据，新断言必须判 PASS（只判 FAIL 的断言是恒假，同样是坏断言）。

边界（必须如实说明）：
  - 不联网、不登录、不读数据库、不启停服务；只 monkeypatch 被测脚本的
    `api() / ask() / requests.post() / subprocess.run()`，属函数级隔离验证。
  - 本脚本证明的是"断言具备失败能力"，**不是"产品通过"**。产品结论只能来自真实跑基线
    （见 evidence/R14-BASELINE-<ts>/summary.md）。

用法：
  python3 platform/r12/qa/assert_selftest.py
退出码：0=全部用例与期望一致；1=存在断言仍假绿/恒假；2=自检自身异常。
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
from datetime import datetime, timezone

QA_DIR = os.path.dirname(os.path.abspath(__file__))
# 默认测本目录脚本；--scripts-dir 可指向旧版本副本，用于**验证本自检自己不是空转**：
# 指回 R13 旧断言时必须报大量"不符"，指回 R14 收紧版时必须全一致。两次都跑过才算自检有效。
SCRIPT_DIR = QA_DIR
OUT = os.path.join(QA_DIR, "evidence",
                   "R14-SELFTEST-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
SCRATCH = os.path.join(OUT, "_scratch")          # 被测脚本 record()/dump() 的落盘目录（隔离用）
CASES = []


# --------------------------------------------------------------------- 加载被测脚本
def _load(fname, alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(SCRIPT_DIR, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod          # dataclass/pickle 等需要模块已注册
    spec.loader.exec_module(mod)
    return mod


class _Sess:
    """被测函数只用到 .token，不需要真会话。"""
    token = "selftest-not-a-real-token"


def _probe(mod, fn, patches):
    """注入夹具 -> 执行一个被测探针函数 -> 收集它 record() 出来的行。返回 (rows, stdout)。"""
    saved = {}
    for k, v in patches.items():
        saved[k] = getattr(mod, k)
        setattr(mod, k, v)
    saved["RESULTS"] = getattr(mod, "RESULTS", None)
    mod.RESULTS = []
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn(_Sess())
        rows = list(mod.RESULTS)
    finally:
        for k, v in saved.items():
            setattr(mod, k, v)
    return rows, buf.getvalue()


def add(cid, target, desc, expected, fn):
    CASES.append({"id": cid, "target": target, "desc": desc, "expected": expected, "fn": fn})


# ===================================================================== 夹具：r13_full_check
def _ver(body, code=200):
    """VERSION 探针：api() 返回固定 (code, body)。"""
    def fn(s):
        FC.cap_version(s)
    rows, _ = _probe(FC, fn, {"api": lambda *a, **k: (code, body), "EVID": SCRATCH})
    r = rows[0]
    return r["ok"], r["detail"]


def _table(ans, ref=None, code=200, status=2):
    """TABLE 探针：ask() 返回固定 (code, status, answer, refs, resultType)。"""
    def fn(s):
        FC.cap_table(s)
    rows, _ = _probe(FC, fn, {"ask": lambda *a, **k: (code, status, ans, ref or [], 1),
                              "EVID": SCRATCH})
    r = rows[0]
    return r["ok"], r["detail"]


def _global(ans, sources, code=200, status=2):
    """GLOBAL 探针：ask() 返回带 metadata.source 的引用列表。"""
    ref = [{"metadata": {"source": s}, "page_content": "正文"} for s in sources]
    def fn(s):
        FC.cap_global(s)
    rows, _ = _probe(FC, fn, {"ask": lambda *a, **k: (code, status, ans, ref, 3),
                              "EVID": SCRATCH})
    r = rows[0]
    return r["ok"], r["detail"]


class _Resp:
    def __init__(self, code, payload):
        self.status_code = code
        self._p = payload

    def json(self):
        return self._p


def _graph_local(docs, code=200):
    """GRAPH_LOCAL 探针：替换 requests 模块（探针只用到 .post）。"""
    class _Req:
        @staticmethod
        def post(*a, **k):
            return _Resp(code, {"data": {"documents_list": docs}})
    def fn(s):
        FC.cap_graph_local(s)
    rows, _ = _probe(FC, fn, {"requests": _Req, "EVID": SCRATCH})
    r = rows[0]
    return r["ok"], r["detail"]


def _internal_guard(cb, up):
    """INTERNAL_GUARD 探针：两次 requests.post 分别返回 cb / up 状态码。"""
    codes = [cb, up]
    class _Req:
        @staticmethod
        def post(*a, **k):
            c = codes.pop(0) if codes else 500
            return _Resp(c, {})
    def fn(s):
        FC.cap_internal_guard(s)
    rows, _ = _probe(FC, fn, {"requests": _Req, "EVID": SCRATCH})
    r = rows[0]
    return r["ok"], r["detail"]


def _global_refuse(text, ref=None):
    """GLOBAL_REFUSE 探针：R1/R2 两问都返回同一 text；取 R1 那一行判定。"""
    def fn(s):
        FC.cap_global_refuse(s)
    rows, _ = _probe(FC, fn, {"ask": lambda *a, **k: (200, 2, text, ref or [], 3),
                              "EVID": SCRATCH})
    return rows[0]["ok"], rows[0]["detail"]


def _global_faith(text, ref=None):
    def fn(s):
        FC.cap_global_faith(s)
    rows, _ = _probe(FC, fn, {"ask": lambda *a, **k: (200, 2, text, ref or [], 3),
                              "EVID": SCRATCH})
    return rows[0]["ok"], rows[0]["detail"]


def _faq(seq):
    """FAQ 探针：按顺序返回 (http,status,ans,ref,resultType)；用于验证"3 次重试"不制造假绿。"""
    items = list(seq)
    def _ask(*a, **k):
        return items.pop(0) if items else (200, 2, "", [], 1)
    def fn(s):
        FC.cap_faq(s)
    rows, _ = _probe(FC, fn, {"ask": _ask, "EVID": SCRATCH})
    return rows[0]["ok"], rows[0]["detail"]


def _graph_identity_neutral_200():
    """TL 批准的新契约：200 + code=200 + result_data=[] + reason → INFO（允许空，不计正例）。"""
    class _Req:
        @staticmethod
        def post(*a, **k):
            return _Resp(200, {"code": 200, "msg": "查询成功，共0条文本数据",
                               "data": {"result_data": [], "identity_violations": [],
                                        "identity_violations_count": 0,
                                        "reason": "no_vertex_matched"}})

    def fn(s):
        FC.cap_graph_identity(s)
    rows, _ = _probe(FC, fn, {"requests": _Req, "EVID": SCRATCH})
    r = rows[0]
    return r["neutral"] is True, f"neutral={r['neutral']} ok={r['ok']}"


def _graph_prov(blocks, es=1, es_ids=None):
    """GRAPH_PROVENANCE 探针：post 分两路（19529 拿图块 / 19200 按 _id 反查），get=ES _count。

    R14-F01z：重建后 19529 不再返回 provenance_quality，此时判据回落到"pk ∩ ES._id"，
    所以夹具必须能模拟 ES `_search` 返回命中的 _id 集合。
    """
    ids = set(map(str, es_ids if es_ids is not None else
                  [b.get("pk") for b in blocks if b.get("pk")]))

    class _Req:
        @staticmethod
        def post(url=None, *a, **k):
            if "19529" in str(url):
                return _Resp(200, {"code": 200, "data": {"result_data": [
                    {"metadata": dict(b)} for b in blocks]}})
            return _Resp(200, {"hits": {"total": {"value": len(ids)},
                                        "hits": [{"_id": i} for i in ids]}})

        @staticmethod
        def get(*a, **k):
            return _Resp(200, {"count": es})

    def fn(s):
        FC.cap_graph_provenance(s)
    rows, _ = _probe(FC, fn, {"requests": _Req, "EVID": SCRATCH})
    return rows[0]["ok"], rows[0]["detail"]


# ===================================================================== 夹具：acceptance
def _s7(body, code=200, qid=None):
    """S7 探针：getDialogBySessionId 返回固定 body；会话列表恒 200。
    qid 用于验证"必须命中本轮提问"（否则旧历史也能蒙过）。"""
    def h(*a, **k):
        path = a[2]
        if "getDialogBySessionId" in path:
            return code, body
        return 200, {"success": True, "data": []}
    def fn(s):
        AC.s7(s, "kb_9", qid)
    rows, _ = _probe(AC, fn, {"api": h, "EVID": SCRATCH})
    r = rows[0]
    return r["ok"], r["detail"]


def _s6(first_body, code=200, ref=None, corpus="授信额度5000万元，期限三年。", row=0):
    """S6 探针：首次 getFileChunks(pageSize=5) 用 first_body；其余按 corpus 回。"""
    def h(*a, **k):
        path = a[2]
        if "pageSize=50" in path:              # 引用回填用的取块
            return 200, {"data": {"records": [{"content": corpus}]}}
        return code, first_body
    def fn(s):
        AC.s6(s, 9, 282, ref or [], "授信额度5000万元，期限三年。")
    rows, _ = _probe(AC, fn, {"api": h, "EVID": SCRATCH})
    r = rows[row]
    return r["ok"], r["detail"]


# ===================================================================== 夹具：security_acceptance
def _sql_of(mod, returncode, stdout="", stderr=""):
    """sql() 探针：mysql 返回非零退出码时必须抛错（返回 observed=False 表示"该检查判失败"）。"""
    class _R:
        pass

    def fake_run(*a, **k):
        r = _R()
        r.returncode = returncode
        r.stdout = stdout
        r.stderr = stderr
        return r

    saved = mod.subprocess.run
    mod.subprocess.run = fake_run
    try:
        try:
            got = mod.sql("select 1")
            return True, f"未抛异常，返回 {got!r}（期望 RuntimeError）"
        except RuntimeError as e:
            return False, f"抛出 RuntimeError: {str(e)[:90]}（期望如此）"
    finally:
        mod.subprocess.run = saved


def _sql(returncode, stdout="", stderr=""):
    return _sql_of(SC, returncode, stdout, stderr)


# ===================================================================== 夹具：图侧新增两断言
def _graph_identity(body, code=200):
    """GRAPH_IDENTITY 探针：直连 19529 的响应体固定为 body。"""
    class _Req:
        @staticmethod
        def post(*a, **k):
            return _Resp(code, body)
    def fn(s):
        FC.cap_graph_identity(s)
    rows, _ = _probe(FC, fn, {"requests": _Req, "EVID": SCRATCH})
    return rows[0]["ok"], rows[0]["detail"]


def _graph_identity_neutral_200():
    """TL 批准的新契约：200 + code=200 + result_data=[] + reason → INFO（允许空，不计正例）。"""
    class _Req:
        @staticmethod
        def post(*a, **k):
            return _Resp(200, {"code": 200, "msg": "查询成功，共0条文本数据",
                               "data": {"result_data": [], "identity_violations": [],
                                        "identity_violations_count": 0,
                                        "reason": "no_vertex_matched"}})

    def fn(s):
        FC.cap_graph_identity(s)
    rows, _ = _probe(FC, fn, {"requests": _Req, "EVID": SCRATCH})
    r = rows[0]
    return r["neutral"] is True, f"neutral={r['neutral']} ok={r['ok']}"


def _graph_prov(blocks, es=1, es_ids=None):
    """GRAPH_PROVENANCE 探针：post 分两路（19529 拿图块 / 19200 按 _id 反查），get=ES _count。

    R14-F01z：重建后 19529 不再返回 provenance_quality，此时判据回落到"pk ∩ ES._id"，
    所以夹具必须能模拟 ES `_search` 返回命中的 _id 集合。
    """
    ids = set(map(str, es_ids if es_ids is not None else
                  [b.get("pk") for b in blocks if b.get("pk")]))

    class _Req:
        @staticmethod
        def post(url=None, *a, **k):
            if "19529" in str(url):
                return _Resp(200, {"code": 200, "data": {"result_data": [
                    {"metadata": dict(b)} for b in blocks]}})
            return _Resp(200, {"hits": {"total": {"value": len(ids)},
                                        "hits": [{"_id": i} for i in ids]}})

        @staticmethod
        def get(*a, **k):
            return _Resp(200, {"count": es})

    def fn(s):
        FC.cap_graph_provenance(s)
    rows, _ = _probe(FC, fn, {"requests": _Req, "EVID": SCRATCH})
    return rows[0]["ok"], rows[0]["detail"]


# ===================================================================== 夹具：acceptance
def _s7(body, code=200, qid=None):
    """S7 探针：getDialogBySessionId 返回固定 body；会话列表恒 200。
    qid 用于验证"必须命中本轮提问"（否则旧历史也能蒙过）。"""
    def h(*a, **k):
        path = a[2]
        if "getDialogBySessionId" in path:
            return code, body
        return 200, {"success": True, "data": []}
    def fn(s):
        AC.s7(s, "kb_9", qid)
    rows, _ = _probe(AC, fn, {"api": h, "EVID": SCRATCH})
    r = rows[0]
    return r["ok"], r["detail"]


def _s6(first_body, code=200, ref=None, corpus="授信额度5000万元，期限三年。", row=0):
    """S6 探针：首次 getFileChunks(pageSize=5) 用 first_body；其余按 corpus 回。"""
    def h(*a, **k):
        path = a[2]
        if "pageSize=50" in path:              # 引用回填用的取块
            return 200, {"data": {"records": [{"content": corpus}]}}
        return code, first_body
    def fn(s):
        AC.s6(s, 9, 282, ref or [], "授信额度5000万元，期限三年。")
    rows, _ = _probe(AC, fn, {"api": h, "EVID": SCRATCH})
    r = rows[row]
    return r["ok"], r["detail"]


# ===================================================================== 夹具：security_acceptance
def _sql_of(mod, returncode, stdout="", stderr=""):
    """sql() 探针：mysql 返回非零退出码时必须抛错（返回 observed=False 表示"该检查判失败"）。"""
    class _R:
        pass

    def fake_run(*a, **k):
        r = _R()
        r.returncode = returncode
        r.stdout = stdout
        r.stderr = stderr
        return r

    saved = mod.subprocess.run
    mod.subprocess.run = fake_run
    try:
        try:
            got = mod.sql("select 1")
            return True, f"未抛异常，返回 {got!r}（期望 RuntimeError）"
        except RuntimeError as e:
            return False, f"抛出 RuntimeError: {str(e)[:90]}（期望如此）"
    finally:
        mod.subprocess.run = saved


def _sql(returncode, stdout="", stderr=""):
    return _sql_of(SC, returncode, stdout, stderr)


# ===================================================================== 夹具：图侧新增两断言
def _graph_identity(body, code=200):
    """GRAPH_IDENTITY 探针：直连 19529 的响应体固定为 body。"""
    class _Req:
        @staticmethod
        def post(*a, **k):
            return _Resp(code, body)
    def fn(s):
        FC.cap_graph_identity(s)
    rows, _ = _probe(FC, fn, {"requests": _Req, "EVID": SCRATCH})
    return rows[0]["ok"], rows[0]["detail"]


def _graph_identity_neutral():
    """业务空结果（http=200 + body code=500 + reason）必须被判成 INFO，而不是 FAIL。"""
    class _Req:
        @staticmethod
        def post(*a, **k):
            return _Resp(200, {"code": 500, "msg": "查询失败，图服务并无问题中相关的顶点数据",
                               "data": {"result_data": [], "reason": "no_vertex_matched"}})

    def fn(s):
        FC.cap_graph_identity(s)
    rows, _ = _probe(FC, fn, {"requests": _Req, "EVID": SCRATCH})
    r = rows[0]
    return r["neutral"] is True, f"neutral={r['neutral']} ok={r['ok']} detail={r['detail'][:90]}"


def _graph_upper(codes, graph_blocks=True):
    """GRAPH_UPPERCASE 探针：按顺序返回大写/小写的 HTTP 码，并带上 documents_list。

    R14-F01h：断言已从"只看 HTTP 码"升级为"必须证明图真的参与"（search_type 含 graph），
    所以夹具必须能表达两种形态：含 graph 块 / 不含 graph 块。
    """
    seq = list(codes)

    def _doc(with_graph):
        st = ["milvus", "graph"] if with_graph else ["milvus", "es"]
        return {"page_content": "授信额度5000万元", "metadata": {"search_type": st}}

    class _Req:
        @staticmethod
        def post(*a, **k):
            return _Resp(seq.pop(0) if seq else 500,
                         {"code": 200, "data": {"documents_list": [_doc(graph_blocks)]}})

    def fn(s):
        FC.cap_graph_uppercase(s)
    rows, _ = _probe(FC, fn, {"requests": _Req, "EVID": SCRATCH})
    return rows[0]["ok"], rows[0]["detail"]


# ===================================================================== 用例登记
# ---- F01: VERSION（r13_full_check） ----  R13 假绿点：groups=[] 判 PASS
add("VERSION-1", "r13_full_check.cap_version",
    'groups=[]（R13 实测假绿点：空版本列表）', False,
    lambda: _ver({"success": True, "data": {"records": []}}))
add("VERSION-2", "r13_full_check.cap_version",
    'data=None（接口无数据）', False,
    lambda: _ver({"success": True, "data": None}))
add("VERSION-3", "r13_full_check.cap_version",
    '一组两条但版本号相同 [V0,V0]（同名重复入库，不是两版冲突）', False,
    lambda: _ver({"success": True, "data": {"records": [
        {"id": 1, "kbFiles": [{"version": "V0"}, {"version": "V0"}]}]}}))
add("VERSION-4", "r13_full_check.cap_version",
    '一组只有一条 [V0]（单版本，无冲突可区分）', False,
    lambda: _ver({"success": True, "data": {"records": [
        {"id": 1, "kbFiles": [{"version": "V0"}]}]}}))
add("VERSION-5", "r13_full_check.cap_version",
    'http=500 但 body 合规（故障不得当通过）', False,
    lambda: _ver({"success": True, "data": {"records": [
        {"id": 1, "kbFiles": [{"version": "V0"}, {"version": "V1"}]}]}}, code=500))
add("VERSION-6", "r13_full_check.cap_version",
    '正例对照：一组含 V0/V1 两版', True,
    lambda: _ver({"success": True, "data": {"records": [
        {"id": 1, "kbFiles": [{"version": "V0"}, {"version": "V1"}]}]}}))

# ---- F01: S7 历史（acceptance） ----  R13 假绿点：data=None 判 PASS
add("S7-1", "acceptance.s7",
    'data=None（R13 摘要实测：success=true 但无历史）', False,
    lambda: _s7({"success": True, "data": None}))
add("S7-2", "acceptance.s7",
    'data=[]（空历史）', False,
    lambda: _s7({"success": True, "data": []}))
add("S7-3", "acceptance.s7",
    'data=[{id:1}]（有记录但无正文）', False,
    lambda: _s7({"success": True, "data": [{"id": 1, "sessionId": "s"}]}))
add("S7-4", "acceptance.s7",
    'http=500 但 data 含正文（故障不得当通过）', False,
    lambda: _s7({"success": True, "data": [{"id": 1, "content": "答：3000万元"}]}, code=500))
add("S7-5", "acceptance.s7",
    '正例对照：服务真实结构 data={queryReplyPairList:[{query,reply}]} 且问答均有正文',
    True,
    lambda: _s7({"success": True, "data": {"sessionId": "kb_9", "queryReplyPairList": [
        {"query": {"content": "我们最多能借多少钱、能借多久？"},
         "reply": {"content": "授信额度为5000万元，其中信用方式不超过1000万元，期限三年。"}}]}}))
add("S7-6", "acceptance.s7",
    'data={queryReplyPairList: []}（会话存在但没有任何问答对）', False,
    lambda: _s7({"success": True, "data": {"sessionId": "kb_9", "queryReplyPairList": []}}))
add("S7-7", "acceptance.s7",
    '问答对里 reply 正文为空（只存了问题没存答案，R14-F01b 收紧点）', False,
    lambda: _s7({"success": True, "data": {"queryReplyPairList": [
        {"query": {"content": "我们最多能借多少钱？"}, "reply": {"content": "  "}}]}}))
add("S7-8", "acceptance.s7",
    '问答对里 query 正文为空（只有答案没有提问，无法证明是同一轮问答）', False,
    lambda: _s7({"success": True, "data": {"queryReplyPairList": [
        {"query": {"content": ""}, "reply": {"content": "授信额度为5000万元。"}}]}}))
add("S7-9", "acceptance.s7",
    '正例对照：历史里存在本轮 queryId 的问答对且回答非空', True,
    lambda: _s7({"success": True, "data": {"queryReplyPairList": [
        {"query": {"queryId": "q-THIS-ROUND", "content": "我们最多能借多少钱？"},
         "reply": {"content": "授信额度为5000万元，期限三年。"}}]}}, qid="q-THIS-ROUND"))
add("S7-10", "acceptance.s7",
    '只有旧 queryId 的历史（本轮提问未落库，历史再多也不算通过）', False,
    lambda: _s7({"success": True, "data": {"queryReplyPairList": [
        {"query": {"queryId": "q-OLD-1", "content": "旧问题一"}, "reply": {"content": "旧答案一"}},
        {"query": {"queryId": "q-OLD-2", "content": "旧问题二"}, "reply": {"content": "旧答案二"}}]}},
                qid="q-THIS-ROUND"))

# ---- F01: S6 原文（acceptance） ----  R13 假绿点：首块长度=0 判 PASS
add("S6-1", "acceptance.s6",
    'records=[{content:""}]（空原文，R13 摘要"首块长度=0"仍 PASS）', False,
    lambda: _s6({"data": {"records": [{"content": ""}]}}))
add("S6-2", "acceptance.s6",
    'records=[]（取不到任何块）', False,
    lambda: _s6({"data": {"records": []}}))
add("S6-3", "acceptance.s6",
    'content/pageContent/page_content 全空', False,
    lambda: _s6({"data": {"records": [{"content": None, "pageContent": None,
                                       "page_content": ""}]}}))
add("S6-4", "acceptance.s6",
    'http=500 但含正文', False,
    lambda: _s6({"data": {"records": [{"content": "授信额度5000万元"}]}}, code=500))
add("S6-5", "acceptance.s6",
    '正例对照：正文在服务真实字段 content', True,
    lambda: _s6({"data": {"records": [{"content": "授信额度5000万元，期限三年",
                                       "pageContent": ""}]}}))
add("S6-6", "acceptance.s6",
    '引用无 metadata.source（"引用携带文件与定位信息"）', False,
    lambda: _s6({"data": {"records": [{"content": "授信额度5000万元"}]}},
                ref=[{"metadata": {}}], row=1))
add("S6-7", "acceptance.s6",
    '正例对照：引用带 source', True,
    lambda: _s6({"data": {"records": [{"content": "授信额度5000万元"}]}},
                ref=[{"metadata": {"source": "kb_9/R12FIX-product-loan.docx"}}], row=1))

# ---- F01: TABLE（r13_full_check） ----  R13 假绿点：只匹配 "3000"
_TBL_REF = [{"metadata": {"source": "kb_9/R12FIX-credit-ledger.xlsx/0"}}]
add("TABLE-1", "r13_full_check.cap_table",
    '答案含 3000 但主体错（"本季度市场预算是3000元"）', False,
    lambda: _table("本季度市场预算是3000元，与授信无关。", _TBL_REF))
add("TABLE-2", "r13_full_check.cap_table",
    '答案含 3000/万元/主体，但口径错（营收而非授信额度）', False,
    lambda: _table("华东精密制造有限公司2025年营业收入为3000万元。", _TBL_REF))
add("TABLE-3", "r13_full_check.cap_table",
    '答案对但无引用（不可回填的结论不算证据）', False,
    lambda: _table("华东精密制造有限公司的授信额度为3000万元。", []))
add("TABLE-4", "r13_full_check.cap_table",
    '答案无主体（"授信额度3000万元" 不知是谁的）', False,
    lambda: _table("授信额度3000万元。", _TBL_REF))
add("TABLE-5", "r13_full_check.cap_table",
    'http=500 但答案文本对', False,
    lambda: _table("华东精密制造有限公司的授信额度为3000万元。", _TBL_REF, code=500))
add("TABLE-6", "r13_full_check.cap_table",
    '正例对照：数值+单位+主体+口径+引用齐备（= 02:24 真实答案）', True,
    lambda: _table("华东精密制造有限公司的授信额度为3000万元。", _TBL_REF))

# ---- F01k: FAQ 正例允许 3 次尝试，但不得把"始终未命中"放过 ----
add("FAQ-1", "r13_full_check.cap_faq",
    '正例对照：首次即 resultType=2（FAQ 直答）', True,
    lambda: _faq([(200, 2, "是的，客户访前准备在第一段。", [{"metadata": {"source": "kb_9/a"}}], 2)]))
add("FAQ-2", "r13_full_check.cap_faq",
    '前两次 resultType=1、第三次=2（LLM 选择器抖动）→ 有重试就应 PASS', True,
    lambda: _faq([(200, 2, "普通回答", [], 1), (200, 2, "普通回答", [], 1),
                  (200, 2, "是的，客户访前准备在第一段。", [], 2)]))
add("FAQ-3", "r13_full_check.cap_faq",
    '3 次都 resultType=1（从未走 FAQ 直答）→ 必须 FAIL，重试不得变假绿', False,
    lambda: _faq([(200, 2, "普通回答", [], 1)] * 3))
add("FAQ-4", "r13_full_check.cap_faq",
    '3 次都 http=500 → 必须 FAIL（故障不得当通过）', False,
    lambda: _faq([(500, None, "", [], None)] * 3))


# ---- F01z: provenance 字段缺失时按"pk ∩ ES._id"兜底（TL 的 F04 判据）----
add("GPROV-4", "r13_full_check.cap_graph_provenance",
    '重建后 pq 字段缺失，但 pk 命中当前 ES _id → 必须 PASS（不能因字段缺失判 FAIL）', True,
    lambda: _graph_prov([{"pk": "139363536840301567", "source": "r12-rag/kb_9/a.docx/V1/a.docx"},
                         {"pk": "626225001556669433", "source": "r12-rag/kb_9/b.pptx/V1/b.pptx"}],
                        es=1))
add("GPROV-5", "r13_full_check.cap_graph_provenance",
    'pq 缺失且 pk 在当前 ES 里一个都不存在（真悬空）→ FAIL', False,
    lambda: _graph_prov([{"pk": "999", "source": "r12-rag/kb_9/a.docx/V1/a.docx"}], es=1, es_ids=[]))


# ---- F01y: provenance 判定的 strict 开关（重建前不硬判 stale，重建后硬判）----
add("PROV-1", "r13_full_check._prov_verdict",
    'strict=0：exact>0 且无悬空即通过（stale 只记 INFO，重建前口径）', True,
    lambda: (FC._prov_verdict(1, [], 2, strict=False), "strict=off"))
add("PROV-2", "r13_full_check._prov_verdict",
    'strict=1：exact>0 但 stale=2（V0 混入）→ 必须 FAIL（重建后口径）', False,
    lambda: (FC._prov_verdict(1, [], 2, strict=True), "strict=on"))
add("PROV-3", "r13_full_check._prov_verdict",
    'strict=1 且 stale=0 且无悬空 → 通过（重建后的目标态）', True,
    lambda: (FC._prov_verdict(3, [], 0, strict=True), "clean"))
add("PROV-4", "r13_full_check._prov_verdict",
    'strict=1：exact=0 → 无论 stale 如何都不得通过（"数字好看"不能替代出处）', False,
    lambda: (FC._prov_verdict(0, [], 0, strict=True), "no-exact"))
add("PROV-5", "r13_full_check._prov_verdict",
    '有悬空引用 → 任何口径都不得通过', False,
    lambda: (FC._prov_verdict(5, ["gone.docx"], 0, strict=False), "dangling"))


# ---- F01x: 摘要三态契约（B 的三态；区分"读不到"与"确实没有"）----
add("SUMST-1", "r13_full_check._summary_store_state",
    'code=500 + data.error=summary_store_unavailable → store_down（可监控/可重试）', True,
    lambda: (FC._summary_store_state({"code": 500, "data": {"error": "summary_store_unavailable"}},
                                     "现有社区摘要不足以回答") == "store_down", "store_down"))
add("SUMST-2", "r13_full_check._summary_store_state",
    '还没建社区（200 + 提示先 /generate_community）→ no_community，不得混成"无事实"', True,
    lambda: (FC._summary_store_state({"code": 200,
                                      "msg": "该知识库还没有社区摘要，请先 /generate_community"},
                                     "现有社区摘要不足以回答") == "no_community", "no_community"))
add("SUMST-3", "r13_full_check._summary_store_state",
    '有社区但无该事实（事实中未提及）→ no_fact（正常拒答）', True,
    lambda: (FC._summary_store_state({"code": 200}, "事实中未提及 [L0-18625408]") == "no_fact",
             "no_fact"))
add("SUMST-4", "r13_full_check._summary_store_state",
    '正常作答 → answered', True,
    lambda: (FC._summary_store_state({"code": 200}, "江南装备 AAA 加 30 个基点") == "answered",
             "answered"))
add("SUMST-5", "r13_full_check._summary_store_state",
    '空响应 + 空答案 → unknown（不得当 answered）', True,
    lambda: (FC._summary_store_state({}, "") == "unknown", "unknown"))


# ---- F01u: "同批全类别无来源拒答" = ENV_EVENT（B 的根因：_load_summaries 读 ES 异常被吞）----
add("ENVREF-1", "r13_full_check._is_env_refusal",
    '同批 POS 也无来源 + 环境拒答文案 + 本条无来源 → 判 ENV_EVENT（不判 FAIL）', True,
    lambda: (FC._is_env_refusal("现有社区摘要不足以回答该问题，未生成推测性答案。", [], True),
             "ENV_EVENT"))
add("ENVREF-2", "r13_full_check._is_env_refusal",
    '只有个别题无来源拒答（同批 POS 正常）→ 不是环境，必须判产品 FAIL', False,
    lambda: (FC._is_env_refusal("现有社区摘要不足以回答该问题，未生成推测性答案。", [], False),
             "product"))
add("ENVREF-3", "r13_full_check._is_env_refusal",
    '环境拒答文案但**带引用**（refs=1）→ 不算环境事件（有来源就不是"读不到")', False,
    lambda: (FC._is_env_refusal("事实中未提及 [L0-18625408]", ["r12-rag/kb_9/a"], True), "has-src"))
add("ENVREF-4", "r13_full_check._is_env_refusal",
    '正常拒答文案 + 无来源 + 同批环境态 → 文案不属环境类，仍按产品判', False,
    lambda: (FC._is_env_refusal("事实中未提及 [L0-18625408]", [], True), "not-env-text"))


# ---- F01s: 解析响应必须逐任务校验 task_statuses（TL 指定；A 发现的 .md 假成功）----
add("PSTAT-1", "r13_full_check._parse_resp_ok",
    '顶层 success=true 但 task_statuses[0].success=false（.md 重解析假成功原型）→ 不得判过', False,
    lambda: (FC._parse_resp_ok({"success": True,
                                "task_statuses": [{"success": False, "message": "unsupported .md"}]})[0],
             str(FC._parse_resp_ok({"success": True,
                                    "task_statuses": [{"success": False, "message": "unsupported .md"}]})[:2])))
add("PSTAT-2", "r13_full_check._parse_resp_ok",
    '正例对照：顶层 true 且 task_statuses 全部 success=true', True,
    lambda: (FC._parse_resp_ok({"success": True,
                                "task_statuses": [{"success": True}, {"success": True}]})[0],
             str(FC._parse_resp_ok({"success": True,
                                    "task_statuses": [{"success": True}, {"success": True}]})[:2])))
add("PSTAT-3", "r13_full_check._parse_resp_ok",
    '顶层 success=false（明确失败）→ 判不过', False,
    lambda: (FC._parse_resp_ok({"success": False, "task_statuses": [{"success": False}]})[0],
             str(FC._parse_resp_ok({"success": False, "task_statuses": [{"success": False}]})[:2])))
add("PSTAT-4", "r13_full_check._parse_resp_ok",
    '没有 task_statuses 字段 → 必须返回"无法判定"（None），不得当 PASS', True,
    lambda: (FC._parse_resp_ok({"success": True})[0] is None,
             f"kind={FC._parse_resp_ok({'success': True})[1]}"))


# ---- F01i: GLOBAL 拆三层（正例 / 拒答 / 忠实度） ----
# R13 假绿点：拒答带任意 source 即 PASS。R14 又发现我方第二个错：拿"无答案题 R1"当正例。
_LONG = ("授信额度与票据贴现属于同一授信体系下的两类工具，票据贴现占用授信额度，"
         "贴现余额会扣减可用授信，两者在额度管理与风险占用上直接联动。")
_LONG_CID = _LONG + " [L0-18625408]"
_REF2 = ["r12-rag/kb_9/a.docx/V0/a.docx", "r12-rag/kb_9/b.docx/V0/b.docx"]

add("GLOBAL-1", "r13_full_check.cap_global",
    '正例题却答成拒答（没有 [L0- 社区 id）→ 不得当通过', False,
    lambda: _global("没有直接关于授信额度与票据贴现关系的信息。", _REF2))
add("GLOBAL-2", "r13_full_check.cap_global",
    'source 重复拼接 host（http://h/http://h/…）→ 不可解析', False,
    lambda: _global(_LONG_CID, ["http://127.0.0.1:19000/http://127.0.0.1:19000/r12-rag/a.docx/0",
                                "r12-rag/kb_9/b.docx/V0/b.docx"]))
add("GLOBAL-3", "r13_full_check.cap_global",
    '只有 1 条可解析 source + 社区 id（B 判定：当前语料 ≥2 不可稳定达标，改为 ≥1 判 PASS）', True,
    lambda: _global(_LONG_CID, ["r12-rag/kb_9/a.docx/V0/a.docx"]))
add("GLOBAL-4", "r13_full_check.cap_global",
    '两条 source 都是重复拼接 host → 全部不可解析', False,
    lambda: _global(_LONG_CID, ["http://127.0.0.1:19000/http://127.0.0.1:19000/a.docx",
                                "http://127.0.0.1:19000/http://127.0.0.1:19000/b.docx"]))
add("GLOBAL-6", "r13_full_check.cap_global",
    '正例对照：单 host 绝对 URL（合法形态，R14-F01j 实测修正，不得判不可解析）', True,
    lambda: _global(_LONG_CID, ["http://127.0.0.1:19000/r12-rag/kb_9/a.docx/V0/a.docx",
                                "http://127.0.0.1:19000/r12-rag/kb_9/b.docx/V0/b.docx"]))
add("GLOBAL-5", "r13_full_check.cap_global",
    '正例对照：≥2 条可解析 source + 出现社区 id（不判措辞/行数）', True,
    lambda: _global(_LONG_CID, _REF2))
add("GLOBAL-7", "r13_full_check.cap_global",
    '0 条可解析 source（即便有社区 id）→ 必须 FAIL', False,
    lambda: _global(_LONG_CID, []))
add("GREFUSE-1", "r13_full_check.cap_global_refuse",
    '正例对照：拒答且未出现任何具体数值（引用数不设下限）', True,
    lambda: _global_refuse("提供的资料中未提及票据贴现与授信额度的关系，无法确定。"))
add("GREFUSE-2", "r13_full_check.cap_global_refuse",
    '拒答话术里夹带编造数值（"AAA 加 15 个基点"）→ 必须 FAIL（B 实测过的回归）', False,
    lambda: _global_refuse("资料未提及，但按行业惯例 AAA 加 15 个基点。"))
add("GREFUSE-3", "r13_full_check.cap_global_refuse",
    '不拒答且直接给数值（R2 计提比例被编造）→ 必须 FAIL', False,
    lambda: _global_refuse("关注类需要计提 2% 的贷款损失准备。"))
add("GFAITH-1", "r13_full_check.cap_global_faith",
    '正例对照：答案与原文一致（AAA→30 个基点、AA→60 个基点）', True,
    lambda: _global_faith("江南装备 AAA 加 30 个基点；华东精密与北方重工为 AA，加 60 个基点。"))
add("GFAITH-2", "r13_full_check.cap_global_faith",
    '答案与上下文矛盾（AAA→100 个基点）→ 忠实度 FAIL（A 实测过 100/60 形态）', False,
    lambda: _global_faith("江南装备 AAA 加 100 个基点；华东精密 AA 加 60 个基点。"))
add("GFAITH-3", "r13_full_check.cap_global_faith",
    '正例对照：评级句与加点句分开表述（实测真实形态），映射 30/60/60 正确即 PASS', True,
    lambda: _global_faith(
        "江南装备科技有限公司的信用评级是AAA，依据为[L0-3af0d4bc]。"
        "华东精密制造有限公司的信用评级是AA，依据为[L0-60d6fa91]。"
        "北方重工配件厂的信用评级是AA，依据为[L0-60d6fa91]。"
        "江南装备科技有限公司的执行利率相对一年期LPR的加点是30个基点，依据为[L0-18625408]。"
        "华东精密制造有限公司的执行利率相对一年期LPR的加点是60个基点，依据为[L0-18625408]。"
        "北方重工配件厂的执行利率相对一年期LPR的加点是60个基点，依据为[L0-18625408]。"))

# ---- F03: GRAPH_LOCAL（r13_full_check） ----  R13 假绿点：只看 metadata 有 graph
add("GRAPH_LOCAL-1", "r13_full_check.cap_graph_local",
    'search_type 含 graph 但正文为空（无法回填原文）', False,
    lambda: _graph_local([{"page_content": "",
                           "metadata": {"source": "graph", "file_id": 1,
                                        "search_type": ["milvus", "graph"]}}]))
add("GRAPH_LOCAL-2", "r13_full_check.cap_graph_local",
    'http=500 但文档列表非空', False,
    lambda: _graph_local([{"page_content": "有正文",
                           "metadata": {"source": "graph", "search_type": ["milvus", "graph"]}}],
                         code=500))
add("GRAPH_LOCAL-3", "r13_full_check.cap_graph_local",
    '正例对照：search_type 含 graph 且正文非空', True,
    lambda: _graph_local([{"page_content": "智造贷授信额度5000万元",
                           "metadata": {"source": "graph", "file_id": 282,
                                        "search_type": ["milvus", "es", "graph"]}}]))
add("GRAPH_LOCAL-4", "r13_full_check.cap_graph_local",
    '正文非空但 search_type 不含 graph（只是普通向量/全文命中，不得当"图参与"）', False,
    lambda: _graph_local([{"page_content": "智造贷授信额度5000万元",
                           "metadata": {"source": "kb_9/a.docx", "search_type": ["milvus", "es"]}}]))

# ---- F08: INTERNAL_GUARD 仍须拒绝无令牌 ----  （保持不回归）
add("INTERNAL_GUARD-1", "r13_full_check.cap_internal_guard",
    '内部回写入口返回 200（未鉴权放行）', False,
    lambda: _internal_guard(200, 403))
add("INTERNAL_GUARD-2", "r13_full_check.cap_internal_guard",
    '内部回写入口返回 500（故障不得当"已拒绝"）', False,
    lambda: _internal_guard(500, 403))
add("INTERNAL_GUARD-3", "r13_full_check.cap_internal_guard",
    '正例对照：两个入口均 403', True,
    lambda: _internal_guard(403, 403))

# ---- F08: denied()（security_acceptance） ----  R13 假绿点：任意 success=false 判"已拒绝"
add("DENIED-1", "security_acceptance.denied",
    'denied(500, {"success": false})（R13 实测返回 True，一般故障被当拒绝）', False,
    lambda: (SC.denied(500, {"success": False}), "denied(...) = " + str(SC.denied(500, {"success": False}))))
add("DENIED-2", "security_acceptance.denied",
    'denied(0, {"success": false})（连接中断/超时）', False,
    lambda: (SC.denied(0, {"success": False}), "denied(...) = " + str(SC.denied(0, {"success": False}))))
add("DENIED-3", "security_acceptance.denied",
    'denied(None, {"success": false})（取不到状态码）', False,
    lambda: (SC.denied(None, {"success": False}), "denied(...) = " + str(SC.denied(None, {"success": False}))))
add("DENIED-4", "security_acceptance.denied",
    'denied(200, {"success": false, "errorCode": "99999"})（业务报错≠鉴权拒绝）', False,
    lambda: (SC.denied(200, {"success": False, "errorCode": "99999"}),
             "denied(...) = " + str(SC.denied(200, {"success": False, "errorCode": "99999"}))))
add("DENIED-5", "security_acceptance.denied",
    'denied(200, {"success": false})（无明确鉴权错误码）', False,
    lambda: (SC.denied(200, {"success": False}), "denied(...) = " + str(SC.denied(200, {"success": False}))))
add("DENIED-6", "security_acceptance.denied",
    '正例对照：denied(403, …)', True,
    lambda: (SC.denied(403, {"success": False}), "denied(...) = " + str(SC.denied(403, {"success": False}))))
add("DENIED-7", "security_acceptance.denied",
    '正例对照：denied(200, {"errorCode": "30016"})（网关明确鉴权错误码）', True,
    lambda: (SC.denied(200, {"errorCode": "30016"}), "denied(...) = " + str(SC.denied(200, {"errorCode": "30016"}))))
add("DENIED-8", "security_acceptance.denied",
    '正例对照：denied(200, {"errorCode": 30017})（整型错误码）', True,
    lambda: (SC.denied(200, {"errorCode": 30017}), "denied(...) = " + str(SC.denied(200, {"errorCode": 30017}))))

# ---- F08: sql()（security_acceptance） ----  R13 假绿点：sql 失败输出空串 -> all() 空集为真
add("SQL-1", "security_acceptance.sql",
    'mysql 退出码 1（口令检查容器/查询失败）-> 必须抛错而不是返回空串', False,
    lambda: _sql(1, stdout="", stderr="ERROR 2003 (HY000): Can't connect"))
add("SQL-2", "security_acceptance.sql",
    '正例对照：退出码 0 -> 原样返回', True,
    lambda: _sql_pos())


def _sql_pos():
    """正例：rc=0 时应返回 stdout 而不是抛错。返回 (ok, detail)。"""
    class _R:
        returncode = 0
        stdout = "admin\t$2a$\n"
        stderr = ""
    saved = SC.subprocess.run
    SC.subprocess.run = lambda *a, **k: _R()
    try:
        try:
            out = SC.sql("select 1")
        except Exception as e:                      # noqa: BLE001
            return False, f"意外抛出 {type(e).__name__}: {e}"
        return (out == "admin\t$2a$"), f"返回 {out!r}"
    finally:
        SC.subprocess.run = saved


# ---- F01p: "本轮解析过"的判口（since 只约束本轮解析的文件，且必须真生效）----
def _ps(end_time, since="2026-10-27T14:15:00"):
    orig = FC._mysql
    FC._mysql = lambda q: end_time
    try:
        return FC._parsed_since(1, since)
    finally:
        FC._mysql = orig


add("PSINCE-1", "r13_full_check._parsed_since",
    '解析任务在本轮 since 之后结束 → 必须受 since 约束（判据真的会生效）', True,
    lambda: (_ps("2026-10-27 14:16:00") is True, f"end_time=14:16 since=14:15 -> {_ps('2026-10-27 14:16:00')}"))
add("PSINCE-2", "r13_full_check._parsed_since",
    '解析任务结束于 13:25（存量）→ 不受 since 约束（避免每轮对存量假红）', True,
    lambda: (_ps("2026-10-27 13:25:00") is False, f"end_time=13:25 since=14:15 -> {_ps('2026-10-27 13:25:00')}"))
add("PSINCE-3", "r13_full_check._parsed_since",
    '查不到解析任务（NULL）→ 不受 since 约束（不伪造"本轮解析过"）', True,
    lambda: (_ps("NULL") is False, f"end_time=NULL -> {_ps('NULL')}"))


# ---- P1-01: 零召回仍给确定性答案（无依据作答）----
add("NORECALL-1", "r13_full_check.no_recall_verdict",
    '零引用 + "抱歉未能找到您要的答案" → PASS（明确拒答）', True,
    lambda: FC.no_recall_verdict(0, "抱歉未能找到您要的答案"))
add("NORECALL-2", "r13_full_check.no_recall_verdict",
    '零引用 + "恒星项目的归口部门是阿里云智能" → FAIL（B 实测的编造形态）', False,
    lambda: FC.no_recall_verdict(0, "恒星项目的归口部门是阿里云智能。"))
add("NORECALL-3", "r13_full_check.no_recall_verdict",
    '零引用 + 只有数值（"归口比例 60%"）→ FAIL', False,
    lambda: FC.no_recall_verdict(0, "归口比例 60%"))
add("NORECALL-4", "r13_full_check.no_recall_verdict",
    '有引用时不进入本判据（不能把有依据的答案判成编造）', True,
    lambda: FC.no_recall_verdict(3, "授信额度为8000万元。"))
add("NORECALL-5", "r13_full_check.no_recall_verdict",
    '零引用 + 极短非拒答（"是的。"）→ 不可判读，不判通过', False,
    lambda: FC.no_recall_verdict(0, "是的。"))


# ---- P2-01: 无限重试（同一 file_id 反复新建 task）----
add("RETRY-1", "r13_full_check.retry_storm_verdict",
    '同一 file_id 30 分钟内 5 条 task → 判无限重试（R14-P2-01 现场形态）', False,
    lambda: FC.retry_storm_verdict([["435", "5"]], 3))
add("RETRY-2", "r13_full_check.retry_storm_verdict",
    '正常重试（1 条文件 2 次）→ 不判红（不能把正常重试当风暴）', True,
    lambda: FC.retry_storm_verdict([["435", "2"], ["436", "1"]], 3))

# ---- S4 三态与 SLOW（TL 口径 C）----
add("S4V-1", "acceptance.s4_verdict",
    'status=3 且耗时 30s → PASS', True,
    lambda: (AC.s4_verdict(3, 30)[0] is True and AC.s4_verdict(3, 30)[1] == "PASS",
             f"tag={AC.s4_verdict(3, 30)[1]}"))
add("S4V-2", "acceptance.s4_verdict",
    'status=3 但耗时 700s → PASS 且标记 SLOW（环境慢不判产品坏）', True,
    lambda: (AC.s4_verdict(3, 700)[0] is True and AC.s4_verdict(3, 700)[1] == "PASS_SLOW",
             f"tag={AC.s4_verdict(3, 700)[1]}"))
add("S4V-3", "acceptance.s4_verdict",
    'status=4（正例却解析失败）→ 判 FAIL（本条断言验证 tag 必须为 FAIL）', True,
    lambda: (AC.s4_verdict(4, 20)[0] is False and AC.s4_verdict(4, 20)[1] == "FAIL",
             f"tag={AC.s4_verdict(4, 20)[1]}"))
add("S4V-4", "acceptance.s4_verdict",
    '1200s 仍未终态（卡在 98 无限重试）→ 必须记 TIMEOUT 而不是 FAIL', True,
    lambda: (AC.s4_verdict(98, 1200)[0] is False and AC.s4_verdict(98, 1200)[1] == "TIMEOUT",
             f"tag={AC.s4_verdict(98, 1200)[1]}"))
add("S4V-5", "acceptance.s4_verdict",
    '负例（加密 PDF 期望失败）最终 status=4 → PASS', True,
    lambda: (AC.s4_verdict(4, 70, "fail")[0] is True, f"ok={AC.s4_verdict(4, 70, 'fail')[0]}"))

add("S4V-6", "acceptance.s4_verdict",
    '负例卡在 98 到 1200s（无限重试）→ 必须记 TIMEOUT，不能记 FAIL（排查方向相反）', True,
    lambda: (AC.s4_verdict(98, 1201, "fail")[0] is False
             and AC.s4_verdict(98, 1201, "fail")[1] == "TIMEOUT",
             f"tag={AC.s4_verdict(98, 1201, 'fail')[1]}"))


# ---- P3-01: 转换产物缺失（回落到 .pdf 导致 NoSuchKey）----
add("CONV-1", "r13_full_check.convert_path_verdict",
    '窗口内 6 条 NoSuchKey(*.pdf) 失败 → 判 FAIL（15:32–15:40 现场）', False,
    lambda: FC.convert_path_verdict([["497", "469", "NoSuchKey"],
                                     ["495", "467", "NoSuchKey"],
                                     ["494", "466", "NoSuchKey"]]))
add("CONV-2", "r13_full_check.convert_path_verdict",
    '无此类失败 → PASS（不能把普通解析失败也算上）', True,
    lambda: FC.convert_path_verdict([]))


# ---- OBS1: 解析队列停摆（TL 指定：僵尸占槽 / 孤儿 99 / 调度没取走）----
add("STALL-1", "r13_full_check.stall_verdict",
    '队列健康（无 99 孤儿、无 PENDING 积压、无 RETRY_ING）→ PASS', True,
    lambda: FC.stall_verdict(0, None, 0, 5))
add("STALL-2", "r13_full_check.stall_verdict",
    '有 5 条 RETRY_ING(status=3) 僵尸占槽（14:05 那次事故形态）→ FAIL', False,
    lambda: FC.stall_verdict(0, None, 5, 5))
add("STALL-3", "r13_full_check.stall_verdict",
    'status=99 超阈值未推进（解析孤儿）→ FAIL', False,
    lambda: FC.stall_verdict(2, None, 0, 5))
add("STALL-4", "r13_full_check.stall_verdict",
    '最老 PENDING 已等 12 分钟（调度没取走）→ FAIL', False,
    lambda: FC.stall_verdict(0, 12, 0, 5))
add("STALL-5", "r13_full_check.stall_verdict",
    'PENDING 只等了 2 分钟（正常排队）→ PASS（不能把正常排队判停摆）', True,
    lambda: FC.stall_verdict(0, 2, 0, 5))


# ---- F01d: --only 门控（选中但未执行必须 FAIL，不得 0 用例 exit 0） ----
add("ONLY-1", "acceptance.plan",
    '--only S6,S7 必须解析为"要执行 S6/S7"（旧实现两者都会落空 → 0 用例）', True,
    lambda: (AC.plan("S6,S7") == (["S6", "S7"], []), f"plan('S6,S7')={AC.plan('S6,S7')}"))
add("ONLY-2", "acceptance.plan",
    '--only S99 必须被识别为未知场景（不得静默当成全量/空跑）', True,
    lambda: (AC.plan("S99") == ([], ["S99"]), f"plan('S99')={AC.plan('S99')}"))
add("ONLY-3", "acceptance.plan",
    '空 --only = 全量场景（顺序固定）', True,
    lambda: (AC.plan("") == (AC.SCENES, []), f"plan('')={AC.plan('')}"))
add("COVERAGE-1", "acceptance.check_coverage",
    '选中 S6/S7 但只执行了 S6 → 必须判"未覆盖"（选中未执行=失败）', False,
    lambda: AC.check_coverage(["S6", "S7"], {"S6"}))
add("COVERAGE-2", "acceptance.check_coverage",
    '正例对照：选中的场景全部执行（多余的前置 PREP 不影响判定）', True,
    lambda: AC.check_coverage(["S6", "S7"], {"S6", "S7", "PREP"}))
add("COVERAGE-3", "acceptance.check_coverage",
    '--only 里有不存在的场景（S99）时覆盖判定也必须 FAIL（不能"选中=[] 就已覆盖"）', False,
    lambda: AC.check_coverage([], set(), ["S99"]))

# ---- F01e/F01f: 图侧两条新断言 ----
add("GID-1", "r13_full_check.cap_graph_identity",
    '正例对照：200 且含 identity_violations*/count=0', True,
    lambda: _graph_identity({"code": 200, "data": {"result_data": [1], "entity_list": ["x"],
                                                   "identity_violations": [],
                                                   "identity_violations_count": 0}}))
add("GID-2", "r13_full_check.cap_graph_identity",
    '200 但缺 identity 键（不得用默认 0 当通过）', False,
    lambda: _graph_identity({"code": 200, "data": {"result_data": [1], "entity_list": ["x"]}}))
add("GID-3", "r13_full_check.cap_graph_identity",
    '200 但 identity_violations_count=2（chunk_pk_list 与社区摘要混用）', False,
    lambda: _graph_identity({"code": 200, "data": {"result_data": [1],
                                                   "identity_violations": [{"pk": "4"}],
                                                   "identity_violations_count": 2}}))
add("GID-4", "r13_full_check.cap_graph_identity",
    'http=500（非 200 不得当通过，identity 无法验证）', False,
    lambda: _graph_identity({"code": 500, "data": None}, code=500))
add("GUP-1", "r13_full_check.cap_graph_uppercase",
    '大写查询 500 / 小写 200（开图对大写 ASCII 抛异常）', False,
    lambda: _graph_upper([500, 200]))
add("GID-6", "r13_full_check.cap_graph_identity",
    'http=200 + body code=500 + reason（把故障伪装成业务空）→ 必须 FAIL', False,
    lambda: _graph_identity({"code": 500, "msg": "查询失败，图服务并无问题中相关的顶点数据",
                             "data": {"result_data": [], "reason": "no_vertex_matched"}}))
add("GID-7", "r13_full_check.cap_graph_identity",
    'http=200 + code=200 + result_data=[] + reason（TL 批准的合法空）→ 记 INFO，不计 PASS/FAIL', True,
    lambda: _graph_identity_neutral_200())
add("GPROV-1", "r13_full_check.cap_graph_provenance",
    '正例对照：有 exact_chunk 且 source 在 ES 命中 → PASS', True,
    lambda: _graph_prov([{"provenance_quality": "exact_chunk", "source": "r12-rag/kb_9/a.docx"}], es=1))
add("GPROV-2", "r13_full_check.cap_graph_provenance",
    '全部 entity_content_recovered（exact_chunk=0，本机现状）→ FAIL 归"数据代次悬空"', False,
    lambda: _graph_prov([{"provenance_quality": "entity_content_recovered",
                          "source": "r12-rag/kb_9/a.docx"}], es=1))
add("GPROV-3", "r13_full_check.cap_graph_provenance",
    '有 exact_chunk 但 source 在 ES 命中 0（引用悬空）→ FAIL', False,
    lambda: _graph_prov([{"provenance_quality": "exact_chunk",
                          "source": "r12-rag/kb_9/gone.docx"}], es=0))

add("GUP-2", "r13_full_check.cap_graph_uppercase",
    '正例对照：大写与小写都 200，且两边都含 graph 块', True,
    lambda: _graph_upper([200, 200]))
add("GUP-3", "r13_full_check.cap_graph_uppercase",
    '两边都 200 但检索结果里没有 graph 块（只证明"不 500"，没证明图参与 → 仍判 FAIL）', False,
    lambda: _graph_upper([200, 200], graph_blocks=False))

# ---- F05: permission_domain_scope 的判据函数（跨域引用 / 5xx 不得当拒绝） ----
add("F05-OOD-1", "permission_domain_scope.out_of_domain",
    'kb_10 的引用被判为域外（跨域引用=泄露）', True,
    lambda: (bool(PD.out_of_domain(["http://x/r12-rag/kb_10/a.docx"])),
             f"out_of_domain(kb_10)={PD.out_of_domain(['http://x/r12-rag/kb_10/a.docx'])}"))
add("F05-OOD-2", "permission_domain_scope.out_of_domain",
    'kb_9 引用 + 空 source（FAQ 直答命中）均不算域外', True,
    lambda: (PD.out_of_domain(["r12-rag/kb_9/a.docx", ""]) == [],
             f"out_of_domain(kb_9,空)={PD.out_of_domain(['r12-rag/kb_9/a.docx', ''])}"))
add("F05-5XX-1", "permission_domain_scope.classify_5xx",
    '500 必须被判为 5xx（错误页炸掉不能算"已拒绝"）', True,
    lambda: (PD.classify_5xx(500) is True, f"classify_5xx(500)={PD.classify_5xx(500)}"))
add("F05-5XX-2", "permission_domain_scope.classify_5xx",
    '403 不得被判为 5xx（真拒绝不能被当成故障）', True,
    lambda: (PD.classify_5xx(403) is False, f"classify_5xx(403)={PD.classify_5xx(403)}"))

# ---- F05t: 拒绝体判定（400+4014 新契约 / 不得 5xx / 不得复用 30016）----
add("F05-DENY-1", "permission_domain_scope.deny_verdict",
    '400 + errorCode=4014（C 定的新契约）→ 必须判通过', True,
    lambda: PD.deny_verdict(400, "4014", "缺少默认助手配置"))
add("F05-DENY-2", "permission_domain_scope.deny_verdict",
    '500 空体（当前缺陷形态）→ 必须判不通过（5xx 不是拒绝）', False,
    lambda: PD.deny_verdict(500, None, ""))
add("F05-DENY-3", "permission_domain_scope.deny_verdict",
    '400 但复用越权码 30016 → 必须判不通过（缺参与越权不可混）', False,
    lambda: PD.deny_verdict(400, "30016", "没有足够权限"))
add("F05-DENY-4", "permission_domain_scope.deny_verdict",
    '403 + 非 30016（历史拒绝语义）→ 通过', True,
    lambda: PD.deny_verdict(403, "4014", "缺少默认助手配置"))
add("F05-DENY-5", "permission_domain_scope.deny_verdict",
    '200 被误当成拒绝（不可判读）→ 不通过', False,
    lambda: PD.deny_verdict(200, None, "ok"))


# ---- F08: revoke_acceptance.denied_http（同缺陷第二处） ----  旧实现同样接受任意 success=false
add("REVOKE-DENIED-1", "revoke_acceptance.denied_http",
    'denied_http(500, {"success": false})（撤权验收把一般故障当"撤权生效"）', False,
    lambda: (RV.denied_http(500, {"success": False}),
             "denied_http(...) = " + str(RV.denied_http(500, {"success": False}))))
add("REVOKE-DENIED-2", "revoke_acceptance.denied_http",
    'denied_http(200, {"success": false})（无鉴权错误码）', False,
    lambda: (RV.denied_http(200, {"success": False}),
             "denied_http(...) = " + str(RV.denied_http(200, {"success": False}))))
add("REVOKE-DENIED-3", "revoke_acceptance.denied_http",
    'denied_http(0, …)（连接中断，不得当撤权生效）', False,
    lambda: (RV.denied_http(0, {"success": False}),
             "denied_http(...) = " + str(RV.denied_http(0, {"success": False}))))
add("REVOKE-DENIED-4", "revoke_acceptance.denied_http",
    '正例对照：denied_http(403, …)', True,
    lambda: (RV.denied_http(403, {"success": False}),
             "denied_http(...) = " + str(RV.denied_http(403, {"success": False}))))
add("REVOKE-DENIED-5", "revoke_acceptance.denied_http",
    '正例对照：denied_http(200, {"errorCode": "30016"})', True,
    lambda: (RV.denied_http(200, {"errorCode": "30016"}),
             "denied_http(...) = " + str(RV.denied_http(200, {"errorCode": "30016"}))))
add("REVOKE-SQL-1", "revoke_acceptance.sql",
    'mysql 退出码 1（撤权 SQL 失败）-> 必须抛错而不是空串', False,
    lambda: _sql_of(RV, 1))


# ---- F01b: s7 不再允许"不传会话"（旧默认 r12-sess-1 不存在） ----
def _s7_nosession():
    def fn(s):
        AC.s7(s, None, None)
    rows, _ = _probe(AC, fn, {"api": lambda *a, **k: (200, {"success": True, "data": {}}),
                              "EVID": SCRATCH})
    return rows[0]["ok"], rows[0]["detail"]


add("S7-11", "acceptance.s7",
    '不传 session（旧默认 r12-sess-1 不存在）必须判 FAIL，不得静默查一个不存在的会话', False,
    _s7_nosession)

# ===================================================================== 执行
def main():
    os.makedirs(SCRATCH, exist_ok=True)
    rows = []
    for c in CASES:
        try:
            observed, detail = c["fn"]()
        except Exception as e:                      # noqa: BLE001
            observed, detail = None, f"自检执行异常: {type(e).__name__}: {e}"
        verdict = (observed is c["expected"])
        rows.append({**{k: c[k] for k in ("id", "target", "desc", "expected")},
                     "observed": observed, "match": verdict, "detail": str(detail)[:400]})

    print(f"R14 断言自检  {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print("被测脚本: platform/r12/qa/{r13_full_check,acceptance,security_acceptance,revoke_acceptance}.py")
    print(f"用例数: {len(rows)}  （反证 {sum(1 for r in rows if r['expected'] is False)} / "
          f"正例 {sum(1 for r in rows if r['expected'] is True)}）\n")
    print(f"{'#':<16} {'期望':<5} {'实测':<5} {'判定':<5} 喂入数据 / 说明")
    print("-" * 110)
    for r in rows:
        exp = "FAIL" if r["expected"] is False else "PASS"
        obs = {True: "PASS", False: "FAIL", None: "ERR"}[r["observed"]]
        print(f"{r['id']:<16} {exp:<5} {obs:<5} {'OK' if r['match'] else '不符':<5} {r['desc']}")
    bad = [r for r in rows if not r["match"]]
    print("-" * 110)
    print(f"结论: {len(rows) - len(bad)}/{len(rows)} 用例与期望一致"
          + ("" if not bad else f"；不符 {len(bad)} 条 -> 断言仍有假绿或恒假，见 evidence"))
    print(f"证据: {OUT}")

    with open(os.path.join(OUT, "selftest.json"), "w", encoding="utf-8") as f:
        json.dump({"ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "scripts_dir": SCRIPT_DIR,
                   "scripts": ["r13_full_check.py", "acceptance.py",
                               "security_acceptance.py", "revoke_acceptance.py",
                               "permission_domain_scope.py"],
                   "rows": rows, "mismatch": [r["id"] for r in bad]}, f,
                  ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8") as f:
        f.write(f"# R14 断言自检 {datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}\n\n")
        f.write(f"- 结果：{len(rows) - len(bad)}/{len(rows)} 用例与期望一致\n")
        f.write("- 性质：函数级隔离验证（monkeypatch，不联网）。它只证明**断言有失败能力**，"
                "不证明产品通过；产品结论见 R14-BASELINE 证据。\n\n")
        f.write("| # | 目标 | 喂入数据 / 说明 | 期望 | 实测 | 判定 | 详情 |\n|---|---|---|---|---|---|---|\n")
        for r in rows:
            exp = "FAIL" if r["expected"] is False else "PASS"
            obs = {True: "PASS", False: "FAIL", None: "ERR"}[r["observed"]]
            f.write(f"| {r['id']} | {r['target']} | {r['desc']} | {exp} | {obs} | "
                    f"{'一致' if r['match'] else '**不符**'} | {r['detail'][:160]} |\n")
    return 0 if not bad else 1


# 被测模块由 main() 在解析参数后加载（用例 lambda 在调用时才解析 AC/FC/SC/RV 全局名）
AC = FC = SC = RV = PD = None


def _bootstrap():
    global AC, FC, SC, RV, PD
    AC = _load("acceptance.py", "r14_selftest_acceptance")
    FC = _load("r13_full_check.py", "r14_selftest_full_check")
    SC = _load("security_acceptance.py", "r14_selftest_security")
    RV = _load("revoke_acceptance.py", "r14_selftest_revoke")
    PD = _load("permission_domain_scope.py", "r14_selftest_f05")


if __name__ == "__main__":
    try:
        import argparse
        _ap = argparse.ArgumentParser(description="R14 断言自检")
        _ap.add_argument("--scripts-dir", default=QA_DIR,
                         help="被测脚本目录（默认本目录；指回旧版可用于验证自检非空转）")
        _args = _ap.parse_args()
        SCRIPT_DIR = os.path.abspath(_args.scripts_dir)
        if SCRIPT_DIR != QA_DIR:
            OUT = OUT + "-" + os.path.basename(SCRIPT_DIR.rstrip("/"))
            SCRATCH = os.path.join(OUT, "_scratch")
        _bootstrap()
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:                        # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"自检自身异常: {exc}")
        sys.exit(2)
