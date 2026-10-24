#!/usr/bin/env python3
"""负例断言库（纯函数：只吃「观察」，不自己发请求）。

为什么要拆出来：断言必须能被"喂假观察"重新求值，否则无法证明它不是恒真（空转）。
本文件每个用例提供：
  fn(obs) -> (verdict, why)   verdict ∈ {"PASS","FAIL","BLOCKED"}
  flip(obs) -> obs'           构造一个"违约观察"，用于变异自检（见 mutate.py）

约定：任何"拒绝类"断言都必须同时具备正向对照（control），否则端点挂掉也会误判成"权限生效"。
"""
DENY = (401, 403)


# ---------------------------------------------------------------- token 类
def check_no_token(obs):
    ctl = obs.get("control_status")
    st = obs.get("status")
    if ctl != 200:
        return "BLOCKED", f"正向对照未建立（带凭证同请求 http={ctl}），拒绝无法归因于鉴权"
    if st in DENY:
        return "PASS", f"无 token http={st}，对照 http={ctl}"
    return "FAIL", f"无 token 未被拒绝 http={st}（对照 http={ctl}）"


def flip_no_token(obs):
    return dict(obs, status=200)


def check_forged_token(obs):
    ctl = obs.get("control_status")
    results = obs.get("results") or []          # [{"label","status"}]
    if ctl != 200:
        return "BLOCKED", f"正向对照未建立 http={ctl}"
    if not results:
        return "FAIL", "没有采到任何伪造 token 的观察"
    passed = [r for r in results if 200 <= r["status"] < 300]
    if passed:
        return "FAIL", "伪造 token 被放行(2xx): " + ", ".join(f"{r['label']}->{r['status']}" for r in passed)
    noisy = [r for r in results if r["status"] >= 500 or r["status"] < 0]
    if noisy:
        # 5xx 不等于放行，但也不是"规范化拒绝"：未捕获异常会泄露内部细节，必须单独记缺陷
        return "FAIL", ("未被规范化拒绝(5xx，非放行，属健壮性/信息泄露缺陷): "
                        + ", ".join(f"{r['label']}->{r['status']}" for r in noisy))
    return "PASS", f"{len(results)} 种伪造 token 全部拒绝: " + ", ".join(f"{r['label']}->{r['status']}" for r in results)


def flip_forged_token(obs):
    return dict(obs, results=[{"label": "forged", "status": 200}])


def check_tampered_token(obs):
    """篡改 payload（把 sub/用户名改成 admin）但保留原签名 → 必须拒绝。"""
    ctl = obs.get("control_status")
    st = obs.get("status")
    leaked_admin = obs.get("leaked_admin", False)
    if ctl != 200:
        return "BLOCKED", f"正向对照未建立 http={ctl}"
    if leaked_admin:
        return "FAIL", "篡改 token 后拿到了 admin 的数据（身份伪造成功）"
    if st in DENY:
        return "PASS", f"篡改 token http={st}"
    return "FAIL", f"篡改 token 未被拒绝 http={st}"


def flip_tampered_token(obs):
    return dict(obs, status=200, leaked_admin=True)


def check_revoked_token(obs):
    """会话被服务端注销（redis token 删除）后旧 token 必须失效。"""
    ctl = obs.get("control_status")
    st = obs.get("status")
    if ctl != 200:
        return "BLOCKED", f"正向对照未建立 http={ctl}"
    if st in DENY:
        return "PASS", f"注销后旧 token http={st}"
    return "FAIL", f"注销后旧 token 仍可用 http={st}"


def flip_revoked_token(obs):
    return dict(obs, status=200)


# ---------------------------------------------------------------- 越权
def check_idor(obs):
    """非属主访问他人私有知识库：必须被拒；返回数据即越权。"""
    if obs.get("kb_private") != 1:
        return "BLOCKED", "夹具不是私有库（private_kb!=1），越权前提不成立"
    st = obs.get("status")
    n = obs.get("n_records") or 0
    if st in DENY:
        return "PASS", f"非属主 {obs.get('who')} 被拒 http={st}"
    if st == 200 and n > 0:
        return "FAIL", (f"越权：非属主 {obs.get('who')} 读到他人私有库 "
                        f"kbId={obs.get('kb_id')}（owner={obs.get('kb_owner')}）共 {n} 条文件记录")
    if st == 200 and n == 0:
        return "BLOCKED", "返回 200 但 0 条（无法区分'空库'与'被过滤'，需换已有文件的库复测）"
    return "FAIL", f"非预期响应 http={st}"


def flip_idor(obs):
    return dict(obs, status=200, n_records=3, kb_private=1)


def check_unauth_whitelist(obs):
    """网关白名单端点必须只放行"无需鉴权也无副作用"的接口。"""
    results = obs.get("results") or []
    if not results:
        return "FAIL", "未采到白名单端点观察"
    bad = [r for r in results if r["status"] not in DENY]
    if bad:
        names = ", ".join(f"{r['path']}->{r['status']}({r.get('snippet','')[:40]})" for r in bad)
        return "FAIL", f"未带任何凭证即可进入业务链路: {names}"
    return "PASS", f"{len(results)} 个白名单端点均返回 {DENY}"


def flip_unauth_whitelist(obs):
    return dict(obs, results=[{"path": "/index/parseTask/callback", "status": 500, "snippet": "npe"}])


# ---------------------------------------------------------------- 坏文件
def check_bad_file(obs):
    """坏文件必须"明确失败"。最危险的不是报错，而是"成功态 + 空内容"。

    关键防呆：如果拒绝原因是"环境未就绪"（如 7009 模型未登记），那是被别的原因挡住，
    不能算"坏文件被正确识别"，必须记 BLOCKED，否则就是空转的 PASS。
    """
    snippet = str(obs.get("snippet") or "")
    env_blocked = ("7009" in snippet or "模型类型不能为空" in snippet
                   or "MODEL_TYPE" in snippet)
    if obs.get("reject"):
        if env_blocked:
            return "BLOCKED", ("被环境错误挡住而非被内容识别（7009 模型未登记）："
                               "该 PASS 会空转，须在上传链可用后重测")
        return "PASS", f"接口层明确拒绝 http={obs.get('http')} resp={snippet[:80]}"
    st = obs.get("final_status")
    ch = obs.get("chunk_count")
    if st == 4:
        return "PASS", f"进入解析失败态 status=4，chunk={ch}"
    if st == 3 and (ch or 0) == 0:
        return "FAIL", "静默成功：解析状态=3(成功) 但 chunk=0，等于用空文档污染知识库"
    if st == 3 and (ch or 0) > 0:
        return "FAIL", f"伪装文件被当成正常文档入库，chunk={ch}"
    return "BLOCKED", f"最终状态未收敛 status={st}（解析链路未就绪）"


def flip_bad_file(obs):
    return dict(obs, reject=False, final_status=3, chunk_count=0)


# ---------------------------------------------------------------- 删除一致性
def check_deleted_not_cited(obs):
    """文档删除后再提问，引用里不得再出现被删文档。"""
    cited = obs.get("cited_after_delete") or []
    deleted = set(obs.get("deleted_file_ids") or [])
    hit = [c for c in cited if str(c) in {str(d) for d in deleted}]
    if hit:
        return "FAIL", f"被删文档仍在引用中出现 file_id={hit}"
    if not cited:
        return "BLOCKED", "删除后提问没有任何引用，无法证明'不再召回'（需有可用因果链）"
    return "PASS", f"删除后 {len(cited)} 条引用均不含被删文档 {sorted(deleted)}"


def flip_deleted_not_cited(obs):
    deleted = obs.get("deleted_file_ids") or [1]
    return dict(obs, deleted_file_ids=deleted, cited_after_delete=list(deleted))


# ---------------------------------------------------------------- 正向侧关键断言（也要做变异）
def check_ref_files(obs):
    """引用里的 file_id 必须都属于本库已上传文件（否则引用指向了别的文件/版本）。"""
    cited = {str(x) for x in (obs.get("cited") or [])}
    uploaded = {str(x) for x in (obs.get("uploaded") or [])}
    if not cited:
        return "BLOCKED", "本轮无引用"
    stray = cited - uploaded
    if stray:
        return "FAIL", f"引用指向本库未上传的文件: {sorted(stray)}"
    return "PASS", f"{len(cited)} 个引用 file_id 全部属于本库({len(uploaded)} 个文件)"


def flip_ref_files(obs):
    return dict(obs, cited=["999999"], uploaded=obs.get("uploaded") or ["1"])


def check_payload_no_body(obs):
    """提问请求体不得出现正文类字段，content 长度必须≈问题长度。"""
    allowed = set(obs.get("allowed") or [])
    keys = set(obs.get("req_keys") or [])
    extra = keys - allowed
    if extra:
        return "FAIL", f"请求体出现非白名单字段: {sorted(extra)}"
    ql = obs.get("question_len") or 0
    cl = obs.get("content_len") or 0
    if ql and cl > ql + 5:
        return "FAIL", f"content 长度 {cl} 远超问题长度 {ql}，疑似随请求提交了正文"
    return "PASS", f"payload 字段={sorted(keys)} content={cl}≈问题={ql}"


def flip_payload_no_body(obs):
    return dict(obs, req_keys=sorted(set(obs.get("req_keys") or []) | {"fileContent"}))


def check_silent_success(obs):
    """解析完成必须有内容：status=成功 且 chunk=0 属于静默成功。"""
    st, ch = obs.get("final_status"), obs.get("chunk_count")
    if st != 3:
        return "BLOCKED", f"未到成功态 status={st}"
    if (ch or 0) == 0:
        return "FAIL", "静默成功：status=3(解析成功) 但 chunk=0"
    return "PASS", f"status=3 chunk={ch}"


def flip_silent_success(obs):
    return dict(obs, final_status=3, chunk_count=0)


CASES = {
    "N1": ("无 token 访问受保护接口", check_no_token, flip_no_token),
    "N2": ("伪造 JWT（alg=none / 伪签名）", check_forged_token, flip_forged_token),
    "N3": ("篡改 token payload 保留原签名", check_tampered_token, flip_tampered_token),
    "N4": ("会话注销后旧 token 复用", check_revoked_token, flip_revoked_token),
    "N5": ("越权：非属主读他人私有知识库", check_idor, flip_idor),
    "N6": ("网关白名单端点未授权可达", check_unauth_whitelist, flip_unauth_whitelist),
    "N7": ("坏文件必须明确失败（随机字节）", check_bad_file, flip_bad_file),
    "N8": ("扩展名伪装文件必须明确失败", check_bad_file, flip_bad_file),
    "N9": ("删除文档后不得再被引用", check_deleted_not_cited, flip_deleted_not_cited),
    "P1": ("引用 file_id 必须属于本库", check_ref_files, flip_ref_files),
    "P2": ("提问请求体不含正文", check_payload_no_body, flip_payload_no_body),
    "P3": ("解析成功必须真的有内容", check_silent_success, flip_silent_success),
}
