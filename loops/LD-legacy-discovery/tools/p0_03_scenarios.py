#!/usr/bin/env python3
"""P0-03 六类负例协议模拟（**SIMULATED**，不得关闭 P0-03）。

边界：
- 合成数据，纯内存模型；不连接任何真实检索链；
- 策略来源是第四轮 `ROUND4-PARALLEL-WORK.md` §3 的**草案**，
  **未经 security-owner 批准**，因此每条场景都记为「待确认的假设」，不是已批准政策；
- 不关闭 P0-03，不替代 E1 正式规范与 E2–E7 实际结果。

每个场景配一个变异体：把关键约束改坏，断言必须由 DENY 变 ALLOW（或反之）。
变异体全部被检出，才说明断言非空转。
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

POLICY_SOURCE = "ROUND4-PARALLEL-WORK.md §3（草案，待 security-owner 确认）"


class Denied(Exception):
    pass


class NotFound(Exception):
    pass


# ---------------- 最小授权模型 ----------------
class Doc:
    def __init__(self, doc_id, kb, allow, deny=()):
        self.doc_id, self.kb = doc_id, kb
        self.allow, self.deny = set(allow), set(deny)


class Store:
    """四类对象：文档、FAQ、图节点、缓存。"""

    def __init__(self):
        self.docs = {}
        self.faq = {}          # faq_id -> source_doc_id
        self.graph = []        # (node_id, doc_id, edges[])
        self.policy_version = 1
        self.cache = {}

    def add_doc(self, d: Doc):
        self.docs[d.doc_id] = d

    def add_graph_nodes(self, nodes):
        self.graph.extend(nodes)

    def bump_policy(self):
        self.policy_version += 1


class Engine:
    def __init__(self, store, strict_deny=True, filter_graph=True,
                 cache_with_version=True, leak_metadata=False,
                 error_allowlist=True):
        self.s = store
        self.strict_deny = strict_deny
        self.filter_graph = filter_graph
        self.cache_with_version = cache_with_version
        self.leak = leak_metadata
        self.error_allowlist = error_allowlist

    # --- 授权判定：叶子落文件、deny 优先、撤销即时 ---
    def allowed(self, principal, doc_id):
        d = self.s.docs.get(doc_id)
        if d is None:
            raise NotFound("not found")
        if principal in d.deny:
            raise Denied("denied")               # deny 优先
        if not self.strict_deny and principal not in d.allow:
            return True                          # 变异：忽略 allow 列表
        if principal not in d.allow:
            raise Denied("denied")
        return True

    # --- 读：拒绝与不存在必须不可区分（防侧信道） ---
    def read(self, principal, doc_id):
        try:
            self.allowed(principal, doc_id)
        except (Denied, NotFound):
            if self.leak:
                n = len(self.s.docs)
                return {"error": "denied_or_missing", "doc_id": doc_id,
                        "total_docs": n, "policy_version": self.s.policy_version}
            return {"error": "not_found"}
        return {"doc_id": doc_id, "content": f"content-of-{doc_id}"}

    # --- FAQ：命中后按来源文档复核 ---
    def read_faq(self, principal, faq_id, inherit=True):
        src = self.s.faq.get(faq_id)
        if src is None:
            return {"error": "not_found"}
        if inherit:
            try:
                self.allowed(principal, src)
            except (Denied, NotFound):
                return {"error": "not_found"}
        else:
            return {"error": None, "answer": f"faq-answer-{faq_id}"}   # 变异：不继承
        return {"error": None, "answer": f"faq-answer-{faq_id}"}

    # --- 图社区：只对授权子集建图（结构性隔离） ---
    def communities(self, principal):
        allowed_nodes = []
        for node_id, doc_id, edges in self.s.graph:
            if self.filter_graph:
                try:
                    self.allowed(principal, doc_id)
                except (Denied, NotFound):
                    continue
            allowed_nodes.append((node_id, doc_id, edges))
        ids = {n[0] for n in allowed_nodes}
        # 极简社区：按连边做连通分量；边只在授权子集内生效
        parent = {i: i for i in ids}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for node_id, _doc, edges in allowed_nodes:
            for e in edges:
                if e in ids:
                    parent[find(node_id)] = find(e)
        groups = {}
        for i in ids:
            groups.setdefault(find(i), set()).add(i)
        return {"communities": sorted(sorted(g) for g in groups.values()),
                "count": len(groups)}

    # --- 缓存：键含策略版本 ---
    def cached_read(self, principal, doc_id):
        key = (principal, doc_id, self.s.policy_version) if self.cache_with_version \
            else (principal, doc_id)
        if key in self.s.cache:
            return self.s.cache[key]
        result = self.read(principal, doc_id)
        self.s.cache[key] = result
        return result

    # --- 错误对象：字段白名单 ---
    def error_object(self, doc_id):
        if self.error_allowlist:
            return {"code": "E_NOT_FOUND", "message": "resource unavailable"}
        return {"code": "E_NOT_FOUND", "message": "resource unavailable",
                "doc_id": doc_id, "kb": self.s.docs[doc_id].kb,
                "policy_version": self.s.policy_version}


def base_store():
    s = Store()
    s.add_doc(Doc("d1", "kb1", allow={"u1"}))
    s.add_doc(Doc("d2", "kb1", allow={"u1", "u2"}))
    s.add_doc(Doc("d3", "kb2", allow={"u2"}))
    s.add_doc(Doc("d4", "kb2", allow={"u2"}))            # u1 无权
    s.add_doc(Doc("d5", "kb1", allow={"u1"}, deny={"u1"}))   # deny 覆盖 allow
    s.add_doc(Doc("d6", "kb2", allow={"u9"}))
    s.faq["f1"] = "d3"                                   # FAQ 指向 u1 无权的文档
    s.add_graph_nodes([
        ("n1", "d1", ["n2"]), ("n2", "d2", ["n1"]),
        ("n3", "d4", ["n1", "n4"]), ("n4", "d4", ["n3"]),
    ])
    return s


def scn1_cross_domain(strict=True):
    e = Engine(base_store(), strict_deny=strict)
    r_other = e.read("u1", "d4")          # 跨 KB 未授权
    r_deny = e.read("u1", "d5")           # deny 覆盖 allow
    ok = r_other.get("error") == "not_found" and r_deny.get("error") == "not_found"
    return {"expected": "DENY(不可区分)", "actual": {"other_kb": r_other, "deny_override": r_deny},
            "pass": ok}


def scn2_graph_interference(filter_graph=True):
    s = base_store()
    e = Engine(s, filter_graph=filter_graph)
    before = e.communities("u1")
    # 只增加未授权域数据，授权域可见结果必须不变
    s.add_doc(Doc("d7", "kb2", allow={"u9"}))
    s.add_graph_nodes([("n5", "d7", ["n1"]), ("n6", "d7", ["n5"])])
    after = e.communities("u1")
    ok = before == after
    return {"expected": "授权域社区不变", "actual": {"before": before, "after": after},
            "pass": ok}


def scn3_side_channel(leak=False):
    e = Engine(base_store(), leak_metadata=leak)
    denied = e.read("u1", "d4")
    missing = e.read("u1", "no-such-doc")
    numeric = {k: v for k, v in denied.items()
               if isinstance(v, (int, float)) and not isinstance(v, bool)}
    ok = denied == missing and not numeric
    return {"expected": "拒绝与不存在响应完全一致，且无计数", "actual": {"denied": denied, "missing": missing},
            "pass": ok}


def scn4_cache_isolation(cache_with_version=True):
    s = base_store()
    e = Engine(s, cache_with_version=cache_with_version)
    first = e.cached_read("u2", "d1")     # u2 无权 d1
    s.docs["d1"].allow.add("u2")          # 授权变更
    s.bump_policy()                       # 版本递增
    second = e.cached_read("u2", "d1")
    ok = second.get("error") is None
    return {"expected": "策略版本变化后缓存不得命中旧结论",
            "actual": {"first": first, "second": second, "policy_version": s.policy_version},
            "pass": ok}


def scn5_revocation_residue(revoke=True):
    s = base_store()
    e = Engine(s)
    before = e.read("u1", "d1")
    if revoke:
        s.docs["d1"].deny.add("u1"); s.bump_policy()
    after = e.read("u1", "d1")
    return {"expected": "撤权后立即 DENY", "actual": {"before": before, "after": after},
            "pass": before.get("error") is None and after.get("error") == "not_found"}


def scn6_faq_inherit(inherit=True):
    e = Engine(base_store())
    r = e.read_faq("u1", "f1", inherit=inherit)
    return {"expected": "FAQ 命中后按来源文档复核 → DENY",
            "actual": r, "pass": r.get("error") == "not_found"}


def scn7_error_leak(allowlist=True):
    e = Engine(base_store(), error_allowlist=allowlist)
    obj = e.error_object("d1")
    allowed = {"code", "message"}
    leaked = set(obj) - allowed
    return {"expected": "错误对象字段 ⊆ {code,message}", "actual": obj,
            "pass": not leaked}


def scn8_neighbor_expansion(filter_expansion=True):
    """E7：邻近块/图片回查的二次取数，必须重新校验权限。

    风险路径：首轮检索只返回授权块 → 为了上下文去取相邻块/图片 → 若不再校验，
    等于用「邻接关系」绕过了授权（这是旧系统已知缺陷之一）。
    """
    s = Store()
    s.add_doc(Doc("d1", "kb1", allow={"u1"}))
    s.add_doc(Doc("d2", "kb1", allow={"u2"}))       # d1 的相邻块，u1 无权
    e = Engine(s)
    # 首轮：只命中授权块
    first = e.read("u1", "d1")
    # 二次取数：扩到相邻块
    if filter_expansion:
        try:
            e.allowed("u1", "d2")
            second = e.read("u1", "d2")
            blocked = False
        except (Denied, NotFound):
            second = {"error": "not_found"}
            blocked = True
    else:
        second = {"doc_id": "d2", "content": "content-of-d2"}   # 变异：不校验
        blocked = False
    leaked = bool(second.get("content"))
    return {"expected": "首轮命中授权块；相邻块必须被拒且不泄露内容",
            "actual": {"first": first, "second": second},
            "pass": first.get("error") is None and blocked and not leaked}


SCENARIOS = [
    ("N1_cross_domain_and_deny_override", scn1_cross_domain, {"strict": False}),
    ("N2_graph_unauthorized_interference", scn2_graph_interference, {"filter_graph": False}),
    ("N3_side_channel_indistinguishability", scn3_side_channel, {"leak": True}),
    ("N4_cache_isolation_after_policy_change", scn4_cache_isolation, {"cache_with_version": False}),
    ("N5_revocation_residue", scn5_revocation_residue, {"revoke": False}),
    ("N6_faq_inherit_source_permission", scn6_faq_inherit, {"inherit": False}),
    ("N7_error_metadata_leak", scn7_error_leak, {"allowlist": False}),
    ("N8_neighbor_block_and_image_expansion", scn8_neighbor_expansion, {"filter_expansion": False}),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    records, mutants, failures = [], [], []
    for name, fn, mutant_kwargs in SCENARIOS:
        base = fn()
        rec = {"scenario": name, "policy_source": POLICY_SOURCE,
               "policy_status": "UNCONFIRMED_ASSUMPTION", "classification": "SIMULATED",
               **base}
        records.append(rec)
        if not base["pass"]:
            failures.append(f"{name}: 基准未通过")

        if mutant_kwargs is None:
            # 该场景无参数化变异：用一个必然破防的替代实现做对照
            mutants.append({"scenario": name, "mutant": "N/A(无参数化变异)",
                            "mutant_pass": None})
            continue
        m = fn(**mutant_kwargs)
        mutants.append({"scenario": name, "mutant": str(mutant_kwargs),
                        "mutant_pass": m["pass"], "mutant_actual": m["actual"]})
        if m["pass"]:
            failures.append(f"{name}: 变异体竟然仍通过 → 断言空转")

    checked = [m for m in mutants if m["mutant_pass"] is not None]
    payload = {
        "scope": "P0-03 六类负例协议模拟（SIMULATED）",
        "warning": "策略来自草案，未经 security-owner 批准；不得关闭 P0-03，不替代 E1 规范与 E2-E7 实测",
        "policy_source": POLICY_SOURCE,
        "policy_status": "UNCONFIRMED_ASSUMPTION",
        "scenarios": records,
        "mutation_check": mutants,
        "mutants_total": len(checked),
        "mutants_rejected": sum(1 for m in checked if not m["mutant_pass"]),
        "failures": failures,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, indent=1)
    import re
    if re.search(r"(?<![\w.])(?:/home|/Users)/[A-Za-z0-9._-]+/", body):
        print("FAIL: artifact would contain a personal absolute path")
        return 3
    a.out.write_text(body + "\n", encoding="utf-8")

    print(f"scenarios={len(records)} passed={sum(1 for r in records if r['pass'])}")
    print(f"mutants_rejected={payload['mutants_rejected']}/{payload['mutants_total']}")
    for f in failures:
        print("FAIL:", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
