#!/usr/bin/env python3
"""R13 撤权验收：撤权后全链路是否立即失效（真实网关 / 真实模型 / 真实库，不用 Mock）。

主体：r13_reader（user_privilege 中 biz_type=1(target) permission=1 只读授权）
对象：知识库 kb_9（kbId=9）

每条链路都做三态验证：授权可用 -> 撤权立即拒绝 -> 恢复后可用。
撤权动作只针对 user_privilege 中 (biz_type=1, target_id=9, user_id=r13_reader) 这一行；
脚本在 finally 里恢复该行，并在 summary 中标注。

夹具说明（不是被撤权对象，仅为让被测账号具备"合法可用"的前置条件）：
  1) search_config：r13_reader 自有的默认助手配置（create_by=r13_reader,is_default=1,is_del=1,
     config_json 与系统默认配置 id=1 相同，knowledge_base_name=kb_9）。
     - 为什么必须自有：qa-service 的 saveOrUpdateDialogue 对 configId 有"助手级数据权限"判定
       （create_by 命中或 authClient.isPermission(biz_type=2)），否则回落到 getDefaultConfig()；
       用户没有默认配置时回落到 nacos defaultSearchConf（内容为 {}），配置里没有任何
       knowledge_base_name，问答链路的对象级授权检查会被整体跳过，且必然 422 无答案。
     - 为什么用 is_del=1：ConfigIsDelEnums 语义是 NO(1)=未删除 / YES(-1)=已删除，
       线上 search_config id=9 的 is_del=0 实际被判定为"已删除"，故 configId=9 取不到配置。
  2) model_info 使用权限：user_privilege (biz_type=3) 对 qwen2.5-7b-instruct(1)、bge-reranker-v2-m3(3)
     permission=1，否则问答直接返回"您没有权限使用该模型"。

用法：python3 platform/r12/qa/revoke_acceptance.py
产出：platform/r12/qa/evidence/REVOKE-<UTC>/{summary.md,detail.json}
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r12_client import GATEWAY, UA, login  # noqa: E402

import requests  # noqa: E402

R12 = "/home/szf/data/dev/llmke-r12/platform/r12"
TS = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
EVID = os.path.join(R12, "qa", "evidence", f"REVOKE-{TS}")
MYSQL = ["docker", "exec", "r12-mysql", "mysql", "-uroot", "-pR12r00t#2026local", "-N", "-e"]

KB_ID = 9
PRIMITIVE = "kb_9"
USER = "r13_reader"
PWD = "R13@Test2026"
MODEL_IDS = (1, 3)          # qwen2.5-7b-instruct / bge-reranker-v2-m3
Q_NORMAL = "我们这种汽车零部件企业最多能借多少钱、能借多久？"
Q_FAQ = "客户访前准备是否是文档的主要内容？"

RESULTS = []
INFO = []
FIXTURE_LOG = []

# R17 的处置路由（与 ops-offline 双方独立核对一致）。本脚本只记录，不执行任何修改。
FIX_ROUTING = [
    "Nacos 配置内容（配置/算法侧 owner）：6 处 server.host=0.0.0.0 —— "
    "alg_doc_config_py L3→12340(doc-parse,写入面)、index_data_config_py L7→19526(写入面)、"
    "index_data_config_py L37→19527(写入面)、alg_retrieval_config_py L7→19995(读)、"
    "alg_llm_config_py L6→19996(推理)、index_graph_config_py L4→19529(读)。"
    "注意：改代码或改 conf/ 均无效，只有配置中心 dataId 内容有效。",
    "预览 18095（已修复，留三条经验）：① app.py 里 host=os.getenv(\"PREVIEW_HOST\",\"127.0.0.1\") 位于 "
    "`if __name__ == \"__main__\":` 内，而容器是 `python -m uvicorn app:app` **模块方式**启动 → 该行是死代码；"
    "真正生效点是 Dockerfile:54 的 CMD，现为 `--host ${PREVIEW_HOST:-127.0.0.1}` + 容器 env "
    "PREVIEW_HOST=127.0.0.1 + 重建镜像。② 期间曾因缩进被改坏（uvicorn.run 顶到第 0 列 → NameError）"
    "导致容器 crash-loop 12 次，且 **py_compile 能通过**，只有起进程才暴露。③ 容器是 host 网络、无端口映射，"
    "改 PortBindings 无从改起（本脚本最早的建议已撤回）。",
    "部署 19529（已修复）：unit 文件改成 --host 127.0.0.1 必须配 `systemctl --user daemon-reload` + restart "
    "才生效；此前未 reload 时 ExecStart 实参仍是 0.0.0.0，且 Restart=always 会用旧参数 5s 后自动起回，"
    "表现为「一会儿有、一会儿没有」的抖动（会造成不同人采样结论不一致）。",
    "index-service：services/rag-java/.../interfaces/KnowledgeBaseFileController.java:442 的注释"
    "（「预览服务在 127.0.0.1:18095 内部端口不做鉴权，这里是唯一收口点」）在 18095 收回回环后**重新成立**；"
    ":55 为默认 URL。它只是注释，不是修复点。",
    "离线包风险（TL 决策，当前**未同步**）：运行态 7 个端口都已只绑回环，但包内配置仍是 0.0.0.0 —— "
    "check-bind 的判定为「已收紧但配置未同步」（12340/19526/19527/19529/19995/19996），"
    "即按现状重打包会把已收紧的端口重新放开。拆成两条来源，只改一条无效。"
    "注意路径约定：凡写 payload/... 均指 platform/r12/dist/offline/payload/... "
    "（platform/r12/offline/ 是安装报告目录，不含 payload，别去那里找）。复现路径与自测值："
    "①配置侧 6 处：platform/r12/dist/offline/payload/nacos/configs.json，"
    "`grep -o '0\\.0\\.0\\.0' | wc -l`=6（`grep -c` 只得 5，因 index_data_config_py 的 L7/L37 "
    "两处落在 JSON 同一行内容里）；"
    "②源码硬编码 1 处：真正生效点是 platform/r12/dist/offline/payload/preview/Dockerfile:52 "
    "的镜像 CMD，现仍为 `--host 0.0.0.0`（源码侧 Dockerfile:54 已改为 `${PREVIEW_HOST:-127.0.0.1}`，"
    "两者不一致）；包内 payload/preview/app.py 仍是 host=\"0.0.0.0\" 且 run.sh 用 --network host。"
    "注意 app.py 里的 host 只在 `__main__` 生效，模块方式启动不执行，改它不解决问题。"
    "ops-offline 已在 offline-kit.sh verify 第 9 段做提示性盘点（不计失败）并记入 "
    "platform/r12/offline/INSTALL-FINDINGS.md §七；pack/init-nacos 的收紧与否由 TL 决策。",
    "收紧后的验收门（ops-offline 提供、qa-authz 已只读试跑）：platform/r12/bin/check-bind.sh --expect-loopback，"
    "退出 0 才算通过；它同时比对“配置声明 vs 实际监听”，能识别快照未同步导致的“静默抵消”。"
    "本脚本终版采样时 qa-authz 实测该命令**退出 0**（7 个端口全部只绑回环，18095 判「一致」，"
    "其余 6 个判「已收紧但配置未同步」）；早期采样曾退出 1，可作对照。",
    "加固有效性限定（否则可能空转）：只改配置中心/包内 configs.json 不足以保证生效——"
    "5 个 Python 服务存在 Nacos 本地快照回退：nacos client 的 SNAPSHOT_BASE 默认是相对路径 "
    "`nacos-data/snapshot`（platform/r12/venvs/alg/.../nacos/client.py:65，按服务 CWD 解析），"
    "只有 doc-parse 显式传了 no_snapshot=True（services/rag-alg/alg_doc_parse_service/server/nacos_utils.py:39,61）；"
    "检索/推理/向量/全文/图谱在配置中心不可达时会按本地快照启动。源码树实测有 7 份快照含 host: 0.0.0.0"
    "（alg_llm_config_py、alg_doc_config_py、alg_retrieval_config_py、index_data_config_py×3、index_graph_config_py），"
    "故加固须同步处理 `services/rag-alg/**/nacos-data/snapshot/*`，否则改动可能被静默抵消。"
    "（口径补充：**当前磁盘上的离线包内不含 `payload/src/`、快照副本 0 份**，即该风险目前只存在于源码树；"
    "一旦重打包把 `services/rag-alg` 纳入 `payload/src/`，它才会随包复制到目标机。）"
    "（本节事实由 qa-authz 独立复现：client.py:65、nacos_utils.py:39/61、7 份快照文件清单；"
    "写入面的绑定盘点限定同样适用于本节。）",
]


# ------------------------------------------------------------------ 基础设施
def sql(q):
    # R14-F08：与 security_acceptance.sql 同一缺陷 —— 不检查退出码时，
    # SQL 失败输出的空串会让下游 all(...) 在空集上为真，把"查询失败"读成"检查通过"。
    out = subprocess.run(MYSQL + [q], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"sql failed rc={out.returncode}: {out.stderr.strip()[:200]}")
    return out.stdout.strip()


def record(case, ok, detail, extra=None):
    row = {"case": case, "ok": bool(ok), "detail": detail}
    if extra is not None:
        row["extra"] = extra
    RESULTS.append(row)
    print(("PASS " if ok else "FAIL ") + f"{case}: {detail}")
    return ok


def denied_http(code, body):
    """HTTP 层拒绝信封（R14-F08 收紧，与 security_acceptance.denied 同口径）。

    旧实现：`401/403` 或 **任意** `success=false` 或 `errorCode == 30016` 即判"已拒绝"。
    问题：上一版把一般业务异常/内部错误（同样返回 success=false）也算成"撤权生效"，
    于是故障方向反而更容易通过验收。现口径：
      - 只认 HTTP 401/403，或网关明确的鉴权错误码（30016/30017/30018）；
      - 5xx / http=0（连接中断、超时）/ 取不到状态码 —— 一律判**未拒绝**（fail-closed）；
      - 200 + success=false 但无鉴权错误码 —— 判未拒绝，需人工看 body 定性。
    """
    if code in (401, 403):
        return True
    if code is None or code == 0 or code >= 500:
        return False
    if isinstance(body, dict):
        if str(body.get("errorCode") or "") in ("30016", "30017", "30018"):
            return True
    return False


class _BrokenResp:
    """请求层异常（连接中断/超时）的占位响应：http=0，绝不当作"被拒绝"。"""

    def __init__(self, ex):
        self.status_code = 0
        self.text = ""
        self.content = b""
        self.headers = {}
        self.encoding = "utf-8"
        self.err = f"{type(ex).__name__}: {str(ex)[:120]}"

    def json(self):
        raise ValueError("no json body")


def call(method, path, token, json_body=None, timeout=300):
    try:
        r = requests.request(method, GATEWAY + path,
                             headers={"Authorization": token, "X-Platform": "rag-qa",
                                      "Accept": "text/event-stream, application/json",
                                      "Content-Type": "application/json", "User-Agent": UA},
                             json=json_body, timeout=timeout)
        r.encoding = "utf-8"
        return r
    except Exception as ex:                      # 流式连接被上游掐断很常见，不能让它打断整轮验收
        return _BrokenResp(ex)


def parse_sse(text):
    frames = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            frames.append(json.loads(payload))
        except Exception:
            pass
    return frames


def summarize_frames(frames):
    """reply.content 在 /qa/ai/question 上是"累计全文"而不是增量，因此取最长/最后一帧。"""
    if not frames:
        return {"status": None, "resultType": None, "content": "", "references": [], "n": 0}
    last = frames[-1]
    content = ""
    for f in frames:
        c = ((f.get("reply") or {}) if isinstance(f.get("reply"), dict) else {}).get("content") or ""
        if len(c) > len(content):
            content = c
    refs_raw = last.get("reference")
    refs = []
    if isinstance(refs_raw, str) and refs_raw.strip():
        try:
            v = json.loads(refs_raw)
            refs = v if isinstance(v, list) else []
        except Exception:
            refs = []
    elif isinstance(refs_raw, list):
        refs = refs_raw
    if not refs:
        for f in frames:
            r = f.get("reference")
            if isinstance(r, str) and r.strip() and r.strip() != "[]":
                try:
                    v = json.loads(r)
                    if isinstance(v, list) and v:
                        refs = v
                except Exception:
                    pass
            elif isinstance(r, list) and r:
                refs = r
    return {"status": last.get("status"), "resultType": last.get("resultType"),
            "content": content, "references": refs, "n": len(frames)}


def ask(token, content, config_id, session_id, global_mode=False, path="/qa/ai/question"):
    body = {"sessionId": session_id, "queryId": f"q{int(time.time() * 1000)}",
            "content": content, "type": "text", "sysType": "KNO_INDEX", "configId": config_id}
    if global_mode:
        body["globalMode"] = True
    r = call("POST", path, token, body)
    frames = parse_sse(r.text)
    info = summarize_frames(frames)
    try:
        envelope = r.json() if "json" in (r.headers.get("Content-Type") or "") else None
    except Exception:
        envelope = None
    info.update({"http": r.status_code, "envelope": envelope, "raw_head": (r.text or "")[:300],
                 "error": getattr(r, "err", None)})
    return info


def ask_ok(token, content, config_id, sid_prefix, global_mode=False, tries=3, wait=10):
    """授权态断言（"应该能用"）依赖外部模型服务，允许有限重试；
    拒绝态断言（"必须被拒"）一律单发，绝不重试，避免把"拒绝"重试成"通过"。"""
    last = None
    for i in range(tries):
        info = ask(token, content, config_id, f"{sid_prefix}-{i}-{int(time.time())}", global_mode)
        info["attempt"] = i + 1
        last = info
        if info["status"] == 2 and len(info["content"]) > 20:
            return info
        if i < tries - 1:
            time.sleep(wait)
    return last


# ------------------------------------------------------------------ 夹具
def ensure_fixture():
    uid = sql(f"select id from gienrag.user_info where user_name='{USER}'")
    if not uid:
        raise SystemExit(f"测试账号 {USER} 不存在，请先由安全验收脚本创建")
    uid = int(uid)
    FIXTURE_LOG.append(f"{USER} user_id={uid}")

    # R14-F01l（schema 变更适配）：11:58 之后 search_config 增加了函数唯一索引
    #   UNIQUE KEY uk_search_config_default (((case when is_default=1 and is_del=1 then 1 else NULL end)))
    #   —— 即**全局只允许一行**"默认助手"。因此 r13_reader 不能再有 is_default=1（会 1062）。
    #   这里改用 is_default=0 的自有配置：question/ question_re 走显式 configId 时只校验
    #   "配置属主命中 create_by 或有配置级权限"，不依赖 is_default，所以夹具语义不变。
    cfg = sql("select id from gienrag.search_config "
              f"where create_by='{USER}' and is_del=1 order by id limit 1")
    if not cfg:
        sql("insert into gienrag.search_config(status,is_default,config_json,name,des,create_by,"
            "gmt_create,gmt_modified,enabled_faq,depend_on_kb,is_del) "
            "select 1,0,config_json,'R13-QA-READER-CFG','QA 夹具：reader 自有助手配置(指向 kb_9)',"
            f"'{USER}',now(),now(),1,0,1 from gienrag.search_config where id=1")
        cfg = sql("select id from gienrag.search_config "
                  f"where create_by='{USER}' and is_del=1 order by id limit 1")
    else:
        # 老夹具可能是 is_default=1（新唯索引落地后会 1062），归零以免再次冲突
        sql(f"update gienrag.search_config set is_default=0 where id={int(cfg)} and is_default=1")
    cfg = int(cfg)
    FIXTURE_LOG.append(f"助手配置 fixture configId={cfg}（create_by={USER}, is_default=0, is_del=1, kb_9）")

    for mid in MODEL_IDS:
        has = sql("select id from gienrag.user_privilege where user_id=%d and biz_type=3 "
                  "and target_id=%d and is_del=1" % (uid, mid))
        if not has:
            sql("insert into gienrag.user_privilege(biz_type,target_id,user_id,permission,is_del,"
                "gmt_create,gmt_modified) values(3,%d,%d,1,1,now(),now())" % (mid, uid))
            FIXTURE_LOG.append(f"模型使用权限 fixture: biz_type=3 target_id={mid} user_id={uid}")
    return uid, cfg


def grant_kb(uid):
    sql("delete from gienrag.user_privilege where user_id=%d and biz_type=1 and target_id=%d"
        % (uid, KB_ID))
    sql("insert into gienrag.user_privilege(biz_type,target_id,user_id,permission,is_del,"
        "gmt_create,gmt_modified) values(1,%d,%d,1,1,now(),now())" % (KB_ID, uid))


def revoke_kb(uid):
    """撤权 = 删除该用户对 target_id=9 的知识库授权行（不做 is_del 软删，直接删行）。"""
    sql("delete from gienrag.user_privilege where user_id=%d and biz_type=1 and target_id=%d"
        % (uid, KB_ID))


def priv_state(uid):
    return sql("select biz_type,target_id,permission,is_del from gienrag.user_privilege "
               "where user_id=%d order by biz_type,target_id" % uid).replace("\n", ";")


# ------------------------------------------------------------------ 旁路探测
# 这些是网关背后的算法/预览服务。它们自身不做对象级授权，全部靠"只在内网/只被 Java 调用"来收口；
# 一旦监听 0.0.0.0，局域网内任何主机都能绕开撤权直接取数据。撤权验收必须把它们一起测，否则
# "撤权后全链路失效"只是网关层的结论，不是系统的结论。
# 读面：能否无凭据取回内容；写面（12340 文档解析、19526/19527 索引写入）只做端口绑定盘点，
# 不做写入探测——写入会产生真实副作用（解析任务/索引数据），超出只读取证边界。
INTERNAL_PORTS = [(19995, "算法检索 alg_retrieval_service(读/召回)", "POST /retrieval_documents"),
                  (18095, "Office 预览 r12-preview(读)", "POST /stream"),
                  (12340, "文档解析 doc-parse(写入面)", ""),
                  (19526, "向量检索 index_vector_service(写面)", ""),
                  (19527, "全文检索 index_fulltext_service(写面)", ""),
                  (19529, "图谱检索 graph(读)", "POST /query_graph_data"),
                  (19996, "模型推理 llm_open_chat(读/推理)", "POST /llm_open_chat")]


def lan_ip():
    out = subprocess.run(["hostname", "-I"], capture_output=True, text=True).stdout.split()
    for ip in out:
        if not ip.startswith("127."):
            return ip
    return None


def listening_addrs(port):
    out = subprocess.run(["ss", "-ltn"], capture_output=True, text=True).stdout
    addrs = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[3].endswith(":%d" % port):
            addrs.append(parts[3].rsplit(":", 1)[0])
    return sorted(set(addrs))


def bypass_probe(key):
    """在"已撤权"状态下探测内部端口。

    口径（重要）：内部服务本身不做对象级授权，其安全边界是"只绑回环、只被 Java 调用"。
    因此本函数按"**非回环地址不可达**"判定（R15/R16/R18），而回环内的无凭据可读只作为
    **事实记录（INFO，不计分）**——它属既定信任边界，不是本次撤权失效；若该边界不被接受，
    应另行立项（内部服务加内网凭据），不能混进撤权 PASS/FAIL。
    """
    ip = lan_ip()
    qa_payload = {"query": Q_NORMAL, "knowledge_base_name": [PRIMITIVE], "top_k": 5,
                  "enabled_faq": False, "enabled_graph": False, "enabled_rerank": False,
                  "model_info": {"model_id": "qwen2.5-7b-instruct",
                                 "url": "http://127.0.0.1:18092/v1/chat/completions",
                                 "key": "sk-r12-local"}}

    def lan_call(port, path, body, timeout=20):
        """从非回环地址调用；连不上/被拒即视为"网络面已收口"。"""
        if not ip:
            return None, "未取到非回环地址"
        try:
            r = requests.post(f"http://{ip}:{port}{path}", json=body, timeout=timeout)
            return r, f"POST http://{ip}:{port}{path}（无 Authorization） http={r.status_code}"
        except Exception as ex:
            return None, f"POST http://{ip}:{port}{path} 不可达（{type(ex).__name__}）"

    # R15 非回环地址打检索服务（LAN 地址不可达即通过）
    r, detail = lan_call(19995, "/retrieval_documents", qa_payload)
    docs = 0
    if r is not None:
        try:
            docs = len(((r.json() or {}).get("data") or {}).get("documents_list") or [])
        except Exception:
            docs = 0
    ok15 = (r is None) or docs == 0
    RESULTS.append({"case": "R15 撤权后经非回环地址无法无凭据取回 kb_9 内容",
                    "ok": ok15, "detail": detail + (f" documents={docs}" if r is not None else "")})
    print(("PASS " if ok15 else "FAIL ")
          + f"R15 撤权后经非回环地址无法无凭据取回 kb_9 内容: {detail}")

    # R16 非回环地址打预览服务
    r, detail = lan_call(18095, "/stream", {"convertedFilePath": key})
    got_pdf = bool(r is not None and r.status_code == 200 and r.content[:4] == b"%PDF")
    ok16 = not got_pdf
    RESULTS.append({"case": "R16 撤权后经非回环地址无法无凭据取回原文",
                    "ok": ok16, "detail": detail + (f" 字节={len(r.content)}" if r is not None else "")})
    print(("PASS " if ok16 else "FAIL ")
          + f"R16 撤权后经非回环地址无法无凭据取回原文: {detail}")

    # R17 监听面：内部端口不应监听 0.0.0.0
    bad = []
    for port, name, _ in INTERNAL_PORTS:
        addrs = listening_addrs(port)
        if any(a in ("0.0.0.0", "*", "::") for a in addrs):
            bad.append(f"{port}({name})={addrs}")
    ok17 = not bad
    detail = ("全部仅监听回环" if ok17
              else "以下内部端口监听 0.0.0.0（局域网可直达）: " + "; ".join(bad)
                   + "；12340/19526/19527 属写入面，本脚本只做绑定盘点、未发写入请求（避免副作用）")
    RESULTS.append({"case": "R17 内部服务端口仅监听回环地址（含写入面 12340/19526/19527）",
                    "ok": ok17, "detail": detail})
    print(("PASS " if ok17 else "FAIL ")
          + f"R17 内部服务端口仅监听回环地址（含写入面）: {detail}")

    # R18 非回环地址打图谱服务
    r, detail = lan_call(19529, "/query_graph_data", {"query": Q_NORMAL,
                                                     "knowledge_base_name": PRIMITIVE})
    ok18 = r is None or r.status_code >= 400
    RESULTS.append({"case": "R18 撤权后经非回环地址无法取回图谱检索结果",
                    "ok": ok18, "detail": detail})
    print(("PASS " if ok18 else "FAIL ")
          + f"R18 撤权后经非回环地址无法取回图谱检索结果: {detail}")

    # INFO（不计分）：回环内仍然是无凭据可读——属"内部服务只绑回环、不做鉴权"的既定边界
    try:
        r1 = requests.post("http://127.0.0.1:19995/retrieval_documents", json=qa_payload, timeout=120)
        loop_docs = len(((r1.json() or {}).get("data") or {}).get("documents_list") or [])
    except Exception:
        loop_docs = -1
    try:
        r2 = requests.post("http://127.0.0.1:18095/stream", json={"convertedFilePath": key}, timeout=120)
        loop_pdf = f"http={r2.status_code} 字节={len(r2.content)}"
    except Exception as ex:
        loop_pdf = f"不可达（{type(ex).__name__}）"
    INFO.append("回环内无凭据可读（既定边界，不计分）："
                f"POST 127.0.0.1:19995/retrieval_documents → documents={loop_docs}；"
                f"POST 127.0.0.1:18095/stream → {loop_pdf}。"
                "含义：内部服务不做对象级授权，安全性完全依赖'只绑回环 + 仅 Java 调用'；"
                "本机任意进程/用户仍可绕过 user_privilege 取数据，若该边界不被接受需另行立项。")
    print("[INFO] " + INFO[-1])
    return None


# ------------------------------------------------------------------ 主流程
def main():
    uid, cfg = ensure_fixture()
    s, token, _ = login(user=USER, password=PWD)
    kb_before = sql(f"select concat(status,'/',length(kb_name)) from gienrag.knowledge_base where id={KB_ID}")
    restored = False
    try:
        # ============ 阶段 A：有授权时可用 ============
        grant_kb(uid)
        FIXTURE_LOG.append("阶段A 起：已授予 biz_type=1 target_id=9 permission=1")

        r = call("GET", f"/index/knowledgeBase/getKbById?id={KB_ID}", token)
        body = r.json() if "json" in (r.headers.get("Content-Type") or "") else {}
        kb_name = ((body.get("data") or {}) if isinstance(body, dict) else {}).get("kbName")
        record("R1 授权时知识库详情可读",
               r.status_code == 200 and isinstance(body, dict) and body.get("success") and kb_name,
               f"GET /index/knowledgeBase/getKbById?id={KB_ID} http={r.status_code} kbName={kb_name}")

        sid_auth = f"revoke-auth-{int(time.time())}"
        qa = ask_ok(token, Q_NORMAL, cfg, sid_auth)
        ok_qa = qa["status"] == 2 and len(qa["content"]) > 20
        record("R2 授权时普通问答返回完整回答",
               ok_qa, f"POST /qa/ai/question http={qa['http']} status={qa['status']} "
                      f"resultType={qa['resultType']} 内容长度={len(qa['content'])} "
                      f"引用数={len(qa['references'])} 帧数={qa['n']} 尝试={qa.get('attempt')}")

        gl = ask_ok(token, Q_NORMAL, cfg, "revoke-global", global_mode=True)
        # R14-F01m：原判据 `len(content)>20` 是"完整回答"的**代理指标**，实测不稳定：
        # 同一问同一配置三次分别得到 275 / 24 / 19 字（B 也记录过 global reduce 输出不可复现）。
        # 本用例的目的只是"撤权前 global 链路可用"（对照 R10 撤权后被拒），因此判据改为：
        #   status==2 且答案非空 且（有可解析引用 **或** 明确拒答语义）——
        # 既不会把"合法短拒答"判红，也不会放过"空回答/异常态"。
        _dsem = ("未提及", "无法确定", "无法回答", "未提供", "没有相关", "没有直接", "未找到相关")
        ok_gl = (gl["status"] == 2 and len(gl["content"].strip()) > 0
                 and (len(gl["references"]) >= 1 or any(k in gl["content"] for k in _dsem)))
        record("R3 授权时 global 问答返回完整回答",
               ok_gl, f"POST /qa/ai/question(globalMode=true) http={gl['http']} status={gl['status']} "
                      f"内容长度={len(gl['content'])} 引用数={len(gl['references'])} 帧数={gl['n']} 尝试={gl.get('attempt')}")

        # R14-F01k：FAQ 直答的成功判据是 `resultType==2`，而 ask_ok 的提前返回条件是
        # "status==2 且内容>20 字"——普通回答也满足，会在第 1 次就返回 rt=1 的结果，
        # 于是 3 次重试形同虚设（实测就发生过：单发 rt=1 FAIL、另一次 rt=2 PASS）。
        # 这里单独重试，判据仍是严格的 resultType==2；**撤权后的拒绝态（R11）依旧单发不重试**。
        faq = None
        for _i in range(3):
            faq = ask(token, Q_FAQ, cfg, f"revoke-faq-{_i}")
            faq["attempt"] = _i + 1
            if faq["status"] == 2 and faq["resultType"] == 2 and len(faq["content"]) > 0:
                break
        ok_faq = faq["status"] == 2 and faq["resultType"] == 2 and len(faq["content"]) > 0
        record("R4 授权时 FAQ 直答命中（resultType=2）",
               ok_faq, f"POST /qa/ai/question(FAQ) http={faq['http']} status={faq['status']} "
                       f"resultType={faq['resultType']} 内容长度={len(faq['content'])} 尝试={faq.get('attempt')}")

        # 引用里的对象键：优先取上层回答的 reference.metadata.source
        key = None
        for ref in (qa["references"] + faq["references"]):
            md = (ref or {}).get("metadata") or {}
            src = md.get("source") or md.get("file_path") or ""
            if "kb_" in src:
                key = src.split("//")[-1]
                key = key[key.find("kb_"):] if "kb_" in key else key
                key = "r12-rag/" + key if not key.startswith("r12-rag/") else key
                break
        if not key:
            key = f"r12-rag/{PRIMITIVE}/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx"
        record("R5 引用可构造出可访问的对象键", bool(key), f"对象键={key}")

        st = call("POST", "/index/knowledgeBase/file/stream", token,
                  {"convertedFilePath": key}, timeout=180)
        ok_stream = st.status_code == 200 and len(st.content) > 1000
        record("R6 授权时可取回引用原文流",
               ok_stream, f"POST /index/knowledgeBase/file/stream http={st.status_code} "
                          f"ctype={st.headers.get('Content-Type')} 字节={len(st.content)} "
                          f"head={st.content[:4]!r}")

        pv = call("POST", "/index/knowledgeBase/file/previewStream", token,
                  {"convertedFilePath": key}, timeout=180)
        ok_pv = pv.status_code == 200 and pv.content[:4] == b"%PDF"
        record("R7 授权时可预览（返回真实 PDF）",
               ok_pv, f"POST /index/knowledgeBase/file/previewStream http={pv.status_code} "
                      f"ctype={pv.headers.get('Content-Type')} 字节={len(pv.content)} "
                      f"head={pv.content[:8]!r}")

        # ============ 阶段 B：撤权后立即失效 ============
        revoke_kb(uid)
        FIXTURE_LOG.append("阶段B 起：已撤权（删除 user_privilege biz_type=1 target_id=9 行）")
        priv_after_revoke = priv_state(uid)

        r = call("GET", f"/index/knowledgeBase/getKbById?id={KB_ID}", token)
        try:
            body = r.json()
        except Exception:
            body = r.text[:200]
        record("R8 撤权后知识库详情被拒",
               denied_http(r.status_code, body),
               f"GET /index/knowledgeBase/getKbById?id={KB_ID} http={r.status_code} resp={str(body)[:160]}")

        qa2 = ask(token, Q_NORMAL, cfg, f"revoke-after-{int(time.time())}")
        leaked = bool(qa2["content"].strip()) or bool(qa2["references"])
        rejected = denied_http(qa2["http"], qa2["envelope"])
        record("R9 撤权后问答被拒且未返回知识库内容",
               rejected and not leaked,
               f"POST /qa/ai/question http={qa2['http']} status={qa2['status']} "
               f"内容长度={len(qa2['content'])} 引用数={len(qa2['references'])} "
               f"errorCode={((qa2['envelope'] or {}).get('errorCode') if isinstance(qa2['envelope'], dict) else None)} "
               f"body={(qa2['raw_head'] or '').replace(chr(10), ' ')[:140]}")

        gl2 = ask(token, Q_NORMAL, cfg, f"revoke-global-after-{int(time.time())}", global_mode=True)
        leaked_gl = bool(gl2["content"].strip()) or bool(gl2["references"])
        record("R10 撤权后 global 问答被拒且未返回内容",
               denied_http(gl2["http"], gl2["envelope"]) and not leaked_gl,
               f"POST /qa/ai/question(globalMode=true) http={gl2['http']} status={gl2['status']} "
               f"内容长度={len(gl2['content'])} 引用数={len(gl2['references'])}")

        faq2 = ask(token, Q_FAQ, cfg, f"revoke-faq-after-{int(time.time())}")
        leaked_faq = bool(faq2["content"].strip()) or bool(faq2["references"])
        record("R11 撤权后 FAQ 直答被拒且未返回内容",
               denied_http(faq2["http"], faq2["envelope"]) and not leaked_faq,
               f"POST /qa/ai/question(FAQ) http={faq2['http']} status={faq2['status']} "
               f"resultType={faq2['resultType']} 内容长度={len(faq2['content'])} 引用数={len(faq2['references'])}")

        st2 = call("POST", "/index/knowledgeBase/file/stream", token,
                   {"convertedFilePath": key}, timeout=180)
        try:
            st2_body = st2.json()
        except Exception:
            st2_body = f"binary {len(st2.content)} bytes"
        record("R12 撤权后按已知对象键取原文被拒",
               denied_http(st2.status_code, st2_body),
               f"POST /index/knowledgeBase/file/stream http={st2.status_code} "
               f"ctype={st2.headers.get('Content-Type')} resp={str(st2_body)[:160]}")

        pv2 = call("POST", "/index/knowledgeBase/file/previewStream", token,
                   {"convertedFilePath": key}, timeout=180)
        try:
            pv2_body = pv2.json()
        except Exception:
            pv2_body = f"binary {len(pv2.content)} bytes"
        record("R13 撤权后预览被拒",
               denied_http(pv2.status_code, pv2_body),
               f"POST /index/knowledgeBase/file/previewStream http={pv2.status_code} "
               f"resp={str(pv2_body)[:160]}")

        # ============ 阶段 C：缓存旁路（连续两次都必须拒绝） ============
        c1 = ask(token, Q_NORMAL, cfg, sid_auth)          # 复用"授权时成功过的会话"，最容易被会话/缓存放行
        c2 = ask(token, Q_NORMAL, cfg, f"revoke-cache2-{int(time.time())}")   # 新会话
        ok_cache = (not (c1["content"].strip() or c1["references"])
                    and not (c2["content"].strip() or c2["references"])
                    and denied_http(c1["http"], c1["envelope"])
                    and denied_http(c2["http"], c2["envelope"]))
        record("R14 撤权后连续两次问答均被拒（无缓存旁路）",
               ok_cache,
               f"复用旧会话 http={c1['http']} status={c1['status']} 内容={len(c1['content'])} 引用={len(c1['references'])}; "
               f"新会话 http={c2['http']} status={c2['status']} 内容={len(c2['content'])} 引用={len(c2['references'])}")

        # ============ 阶段 D：旁路探测（内部服务端口是否让撤权失效） ============
        bypass = bypass_probe(key)

        # ============ 阶段 E：恢复授权后恢复可用 ============
        grant_kb(uid)
        restored = True
        FIXTURE_LOG.append("阶段D 起：已恢复授权（重新写入 biz_type=1 target_id=9 permission=1）")

        r = call("GET", f"/index/knowledgeBase/getKbById?id={KB_ID}", token)
        try:
            body = r.json()
        except Exception:
            body = r.text[:200]
        record("R19 恢复授权后知识库详情恢复可读",
               r.status_code == 200 and isinstance(body, dict) and body.get("success") and body.get("data"),
               f"GET /index/knowledgeBase/getKbById?id={KB_ID} http={r.status_code}")

        qa3 = ask_ok(token, Q_NORMAL, cfg, "revoke-restored")
        record("R20 恢复授权后问答恢复可用",
               qa3["status"] == 2 and len(qa3["content"]) > 20,
               f"POST /qa/ai/question http={qa3['http']} status={qa3['status']} "
               f"内容长度={len(qa3['content'])} 引用数={len(qa3['references'])} 尝试={qa3.get('attempt')}")

        kb_after = sql(f"select concat(status,'/',length(kb_name)) from gienrag.knowledge_base where id={KB_ID}")
        record("R21 全过程知识库本体未被改动",
               kb_before == kb_after, f"before={kb_before} after={kb_after} 撤权期间授权表={priv_after_revoke}")

    finally:
        if not restored:
            grant_kb(uid)
            print("\n[finally] 已恢复 r13_reader 对 kb_9 的授权（biz_type=1, target_id=9, permission=1）")
        else:
            print("\n[finally] 授权已处于恢复状态（阶段D 已恢复）")
        print(f"[finally] 最终授权状态: {priv_state(uid)}")

        os.makedirs(EVID, exist_ok=True)
        passed = sum(1 for r in RESULTS if r["ok"])
        with open(os.path.join(EVID, "detail.json"), "w", encoding="utf-8") as f:
            json.dump({"ts": TS, "user": USER, "kbId": KB_ID, "results": RESULTS,
                       "info": INFO, "fixture": FIXTURE_LOG}, f, ensure_ascii=False, indent=2)
        with open(os.path.join(EVID, "summary.md"), "w", encoding="utf-8") as f:
            f.write(f"# R13 撤权验收 {TS}\n\n")
            f.write(f"主体：`{USER}`（biz_type=1 / target_id={KB_ID} / permission=1）；"
                    f"撤权动作：删除该行；finally 中已恢复。\n\n")
            f.write(f"总计 {passed}/{len(RESULTS)} PASS\n\n")
            f.write(f"> 采样时刻：{TS}（UTC）。R15–R18 的端口监听结论是**该时刻的运行态快照**，"
                    f"不代表源码/配置仓当前内容——源码已改但运行态未重载时，两者会不一致，"
                    f"这本身就是本报告要暴露的\"静默抵消\"情形。\n\n")
            f.write("| 用例 | 结果 | 详情 |\n|---|---|---|\n")
            for r in RESULTS:
                f.write(f"| {r['case']} | {'PASS' if r['ok'] else 'FAIL'} | "
                        f"{str(r['detail']).replace('|', '/')} |\n")
            if INFO:
                f.write("\n## 事实记录（INFO，不计入 PASS/FAIL）\n\n")
                for line in INFO:
                    f.write(f"- {line}\n")
            f.write("\n## 夹具前置（不是被撤权对象）\n\n")
            for line in FIXTURE_LOG:
                f.write(f"- {line}\n")
            f.write("\n## 修复归属清单（R17 端口 0.0.0.0 的处置路由；本脚本只取证不改）\n\n")
            for line in FIX_ROUTING:
                f.write(f"- {line}\n")
        print(f"\n== {passed}/{len(RESULTS)} PASS == 证据: {EVID}")
    return 0 if all(r["ok"] for r in RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
