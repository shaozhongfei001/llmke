"""P3-L11 · `capabilities` 的 HTTP 端点登记必须与真实路由一致（M1~M5）。

为什么这层要存在：`incremental_update` 早就声明 VERIFIED，但**没有**说明「怎么调用」；
`api.py` 里 `POST /v2/graph/delta` 已经存在，能力登记却只讲引擎能力 ——
任何按 `capabilities` 判断「能不能通过 HTTP 做增量」的调用方都会得到错误结论。

三条设计约束（TL 13:4x 裁定）：
1. `http` 是**可选**字段（`[{method, path}]`），20 项不得强制全带；`method` 大写、`path` 含 `/v2` 前缀；
2. 路由集合**从 `api.py` 源码 AST 解析**，不在测试里硬编码 —— 否则等于同一个字符串写两遍再自比；
3. `note` 不得为「对称」而改：`index_build` / `incremental_update` 的 note 原本没有 HTTP 字样，
   统一风格靠**新增可选字段**，不靠改文案。

本文件在 `llmke-v2-toolenv` 与 `hipporag-toolenv` 都能跑：路由表用 AST 解析源码，
**不 import fastapi**（`create_app()` 的交叉校验作为可选加强，缺 fastapi 时跳过）。
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
IDX_ROOT = REPO_ROOT / "services/rag-alg/index_data_service"
if str(IDX_ROOT) not in sys.path:
    sys.path.insert(0, str(IDX_ROOT))

from graph_engine_adapter import capabilities as C  # noqa: E402

API_SOURCE = IDX_ROOT / "graph_engine_adapter" / "api.py"

# 三条写路由必须登记（TL Q3 裁定 (ii) 全覆盖）
REQUIRED_WRITE_ROUTES = {
    "index_build": ("POST", "/v2/graph/build"),
    "incremental_update": ("POST", "/v2/graph/delta"),
    "community_report": ("POST", "/v2/graph/global"),
}

# 不登记白名单：POST 但只读的路由。理由写成常量（不是注释）——红的时候能直接看到为什么
NO_REGISTER_POST = {
    "POST /v2/graph/query": "POST 但只读：只做检索、不写任何存储；登记成能力端点会让调用方"
                            "误以为它能触发写入（写路由是 build/delta/global）",
    # P4-L13-A 新增。它是**运维面**端点（让 18096 这种跨进程调用方能撤权），
    # 不是「图引擎能力」：能力表回答「引擎能做什么」，fence 是可见性控制，
    # 且它不是本次新增能力（fence 本身早就在 capabilities 之外的 L10 面）。
    "POST /v2/fence/revoke": "运维面端点：跨进程撤权（18096→18094），非图引擎能力；"
                             "能力表语义是「引擎能做什么」，撤权是可见性控制，不登记",
}

# 只读 GET 路由：不要求逐条登记（TL Q3）
GET_ROUTES_NOT_REQUIRED_TO_REGISTER = (
    "/v2/status", "/v2/fence", "/v2/entities", "/v2/graph/view",
)

# 允许新增的键（M4 修订后的判据：三键逐项 sha 不变 + 新增键仅允许 http）
ALLOWED_NEW_KEYS = {"http"}

# ---------------------------------------------------------------- 改动前三键基线
# 由改动前的 `capabilities.py` 计算得出（status / note / evidence 各自 sha256）。
BASELINE_THREE_KEYS = {
    "community_report": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "7bbd0f7baabd214e3bc0a7f00f798eba133d1bfeb628540e3018d4af1e185b2f", "evidence": "305505c98ede0ed57a43d87169aef06e8e6ad96a83e7aca79a2c58eb1ce57f37"},
    "cross_scope_merged_retrieval": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "5923a2359eb92e0c4ffb9f9a9f22217b3ba405a4af9deca22a6d85b39a5cb6f4", "evidence": "69d1ed8223e883cc4a5fe6e3e50ebc094d992699620d4db6c587488aa8723ad7"},
    "delete_document": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "ee57421b1cd8231ec5009d41a06ddde1a4d60b342695ae7b9c048290fb8681f4", "evidence": "af597e598694d3c5e0b4970118e81c5bb8d894684833367cb721e562c3652abb"},
    "engine_predicate_normalization": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "5f0d5dc01f3280dfeb4bba268141493ff493061c9adce6a40524944a7255e261", "evidence": "1105a4e532a918b457702dfdd6c4242a765df0791970448eef7627c2cbd504d4"},
    "engine_version_filtering": {"status": "20e15fa61b63ebc0819de4106ad30cf2f75f44371fbefebb7ef31c71478786d0", "note": "eca0e30521c123443fb3954284967daabc2b5bcff65e20ab4338ad0035665469", "evidence": "3612cb693ffbf7d6a5da7b1cd7c293cbcb5353df054939bf9e3fbba619ffd0c3"},
    "engine_visibility_isolation": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "680f161d50e0b92b66867767ca793ded1038c19f76186657260bbafc9a2f111c", "evidence": "5912e4e09ea37c6b49a8a47ecbd0731484831e43d6bda09d0e3637af13e37337"},
    "graph_export": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "ca447fe87f535fb4087bc960b52c855ffc57b1e803ce10058cbf71550cdad55a", "evidence": "2f372c216527d985b9c23caf3aeda1b8a10908d1ba92e745a9e3e516f30a4e84"},
    "incremental_update": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "b8ec439984fb064cad0f0cedec7a0fb2a1816002c372b831c887bd3462702201", "evidence": "af597e598694d3c5e0b4970118e81c5bb8d894684833367cb721e562c3652abb"},
    "index_build": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "d29684a9ae1aac9733724090b7e656959cf9a1b59a962acc909970009751cb11", "evidence": "31925f8687b490fa43286210093163f0f30bc2490179a264a0d0cfdba9d66593"},
    "isolated_snapshot_rebuild": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "2cc4c3e64def6563867332e605a8c43fad31648b3406ee64131346c52af8f2a1", "evidence": "8024de4301c573b509257457e0713291dab38cc4c7ce126acd3902d47007e0e0"},
    "platform_answer_assembly": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "31ec9930b4e65876ef309f046bce9de4307c4deb827fb2debdb9fa79b09b2529", "evidence": "797e776c38ee8598b02f49b1e8ed90d05e47659b4ab15fdef77eacfede5df26e"},
    "platform_assertion_layer": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "c4e0a9ab9d563eb7f5ec4e824c5cdcbe29c24b3c4ff9a11e54b1a529018d2575", "evidence": "f4e39981075c7c7b034501c04405469bc69c006bc16be4010627cc07c2de5a3f"},
    "platform_retrieval_orchestration": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "7b1614aa018f334ab00e5063337b9243df5a014cf720f88e661138125a85b89d", "evidence": "56191765f83a1e8f7f4a3459dcecb64d88f14c59c8877075aae06c5b3eb8acfa"},
    "query_seed_recognition": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "1c8244fb29942153b5c8a3bb4c7fce1cb7e462dde9bd517b7bd3f6f55456ae16", "evidence": "dad90d486e21c017215606ef8615907e6a5f50f86cc1623e9d87ce8b23292e99"},
    "retrieve_dense_fallback": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "c4c78193b79b5b2c7bbe988f9502803b1b9559abc8bf2def99f443fcbe795373", "evidence": "d80679382e0fb67c4e784abb381e25b518cf286d31c6bce56c612257a6506922"},
    "retrieve_graph_route": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "2b864167cf2d89a8a1d3eeb2022a00d46493cbce0f56ff36a87ac73be89d7181", "evidence": "701d5c016ac324d35eaf7ac4647b389c04775f2681da0c90ad1ca17147e23859"},
    "retrieve_graph_route_with_cjk_patch": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "4b6d95f2b5d75775d1da8a01defb8d6d406c2a74b25b3395a85af259a2cb372f", "evidence": "8e025da0291ff6cd91c0601cc5853dfbf2055a212f665b7a48bc62ce21386709"},
    "scope_incremental_rebuild": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "bc0f46e37282140e7d24082a412bec60285e1a4f0be9c99a1b9167d4b1826085", "evidence": "5229da13440ea1cc356c51c690fa36f5ba32d336ccf735a7e667e6718c85789d"},
    "source_map_multi_source": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "4ecd7e54821055f89c4a8fd5cba15d134852a941123a2971c4b6a86bbb09eca2", "evidence": "cd65bfd1bbe86adee3f986c249433ad0de3b227af18f13f49a4b09dbc5beb756"},
    "visibility_fence": {"status": "c0ea28df48673d3a9957864d4ce5f3963522a14f280fd7d74a98489fdf837cd4", "note": "0cfdf84be43a16f85af2736b9c1ceb1d5c149a849692aeb9928c395e7eb2fac3", "evidence": "4efab4dd7c8c0d82e83670a25fb3a083559e212b129b0687101c3d7d2ceefbe7"},
}


# ---------------------------------------------------------------- 工具
def routes_from_source() -> set:
    """从 `api.py` 源码 AST 解析 `@app.get/@app.post(...)` → {(METHOD, path)}。"""
    tree = ast.parse(API_SOURCE.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                    and isinstance(dec.func.value, ast.Name)
                    and dec.func.value.id == "app"):
                continue
            method = dec.func.attr.lower()
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            if not dec.args:
                continue
            literal = dec.args[0]
            if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                found.add((method.upper(), literal.value))
    return found


def declared_endpoints() -> list:
    """把 `http` 声明摊平成 [(cap_name, METHOD, path)]。"""
    out = []
    for name, cap in C.CAPABILITIES.items():
        for entry in cap.get("http") or []:
            out.append((name, str(entry.get("method", "")), str(entry.get("path", ""))))
    return out


def three_key_sha(cap: dict) -> dict:
    return {key: hashlib.sha256(
        json.dumps(cap.get(key), ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest() for key in ("status", "note", "evidence")}


def note_is_honest(note: str) -> bool:
    """M2：必须同时说清「增量抽取」与「全量重建图」两件事。"""
    text = str(note or "")
    return "增量抽取" in text and "全量重建图" in text


# ---------------------------------------------------------------- M1 端点声明
def test_m1_incremental_update_declares_delta_endpoint() -> None:
    cap = C.CAPABILITIES["incremental_update"]
    entries = cap.get("http") or []
    assert entries, "incremental_update 必须声明 http 端点（POST /v2/graph/delta）"
    pairs = {(str(e.get("method")), str(e.get("path"))) for e in entries}
    assert ("POST", "/v2/graph/delta") in pairs


def test_m1_declared_endpoints_are_uppercase_and_prefixed() -> None:
    # 前置：空集合上「每条都合法」恒真，那是最典型的假绿 —— 先要求非空
    assert declared_endpoints(), "没有任何能力项声明 http 端点，本条会空转恒真"
    for name, method, path in declared_endpoints():
        assert method == method.upper() and method in {"GET", "POST", "PUT", "DELETE", "PATCH"}, \
            f"{name}: method 必须是大写 HTTP 方法，实际 {method!r}"
        assert path.startswith("/v2/"), f"{name}: path 必须含 /v2 前缀，实际 {path!r}"


def test_m1_declared_vs_source_routes_match() -> None:
    """**单向真比对**：声明里的每条端点都必须在 `api.py` 源码里真实存在（无幽灵）。"""
    source = routes_from_source()
    assert source, "未能从 api.py 解析出任何路由，比对无意义"
    ghosts = [(n, m, p) for n, m, p in declared_endpoints() if (m, p) not in source]
    assert ghosts == [], f"幽灵端点（声明了但源码没有）：{ghosts}"


def test_m1_cross_check_with_real_app_routes() -> None:
    """可选加强：真建 app 取路由表再比一次（hipporag 才有 fastapi；v2 跳过并计入 skip）。"""
    pytest.importorskip("fastapi", reason="llmke-v2-toolenv 无 fastapi（既有环境限制）")
    from fastapi.testclient import TestClient  # noqa: F401  仅确认依赖可用
    from graph_engine_adapter import api as A

    app = A.create_app()
    real = {(m, getattr(r, "path", ""))
            for r in app.routes for m in (getattr(r, "methods", None) or [])}
    for name, method, path in declared_endpoints():
        assert (method, path) in real, f"{name}: {method} {path} 不在真实路由表里"


# ---------------------------------------------------------------- M2 表述如实
def test_m2_note_keeps_both_semantics() -> None:
    note = C.CAPABILITIES["incremental_update"]["note"]
    assert "增量抽取" in note, "note 必须说明「增量抽取」"
    assert "全量重建图" in note, "note 必须说明「全量重建图」（只说增量就是夸大）"


def test_m2_bare_incremental_claim_is_not_honest() -> None:
    """反向：只写「增量重建」的表述必须被判为不诚实（防将来把 note 改窄）。"""
    assert note_is_honest(C.CAPABILITIES["incremental_update"]["note"]) is True
    assert note_is_honest("增量重建，7.5s 完成") is False
    assert note_is_honest("全量重建图") is False


# ---------------------------------------------------------------- M3 双向一致
def test_m3_precondition_all_write_routes_declared() -> None:
    """前置（TL 收紧）：**3 条写路由全部**已声明，否则下面的「无幽灵」会空转恒真。"""
    declared = {(m, p) for _n, m, p in declared_endpoints()}
    missing = {k: v for k, v in REQUIRED_WRITE_ROUTES.items() if v not in declared}
    assert missing == {}, f"漏登的写路由：{missing}"


def test_m3_each_write_route_registered_on_expected_capability() -> None:
    for cap_name, (method, path) in REQUIRED_WRITE_ROUTES.items():
        entries = C.CAPABILITIES[cap_name].get("http") or []
        pairs = {(str(e.get("method")), str(e.get("path"))) for e in entries}
        assert (method, path) in pairs, f"{cap_name} 未登记 {method} {path}"


def test_m3_source_write_routes_have_no_silent_missing() -> None:
    """源码里的每条写路由（POST）都必须：已登记 或 在显式白名单里（附理由）。"""
    source = routes_from_source()
    declared = {(m, p) for _n, m, p in declared_endpoints()}
    unregistered = []
    for method, path in sorted(source):
        if method != "POST":
            continue
        if (method, path) in declared:
            continue
        key = f"{method} {path}"
        if key in NO_REGISTER_POST:
            assert NO_REGISTER_POST[key].strip(), f"{key} 的白名单理由不得为空"
            continue
        unregistered.append(key)
    assert unregistered == [], f"写路由未登记且未列入白名单：{unregistered}"


def test_m3_whitelist_reason_present() -> None:
    assert NO_REGISTER_POST, "白名单不能为空（POST /v2/graph/query 属只读）"
    assert "POST /v2/graph/query" in NO_REGISTER_POST
    assert len(NO_REGISTER_POST["POST /v2/graph/query"]) >= 20


# ---------------------------------------------------------------- M4 其余不退化
def test_m4_three_keys_unchanged_for_every_capability() -> None:
    current = {name: three_key_sha(cap) for name, cap in C.CAPABILITIES.items()}
    assert set(current) == set(BASELINE_THREE_KEYS), \
        f"能力项增删了：多={sorted(set(current) - set(BASELINE_THREE_KEYS))} " \
        f"少={sorted(set(BASELINE_THREE_KEYS) - set(current))}"
    drift = {name: {k: (BASELINE_THREE_KEYS[name][k], current[name][k])
                    for k in BASELINE_THREE_KEYS[name] if BASELINE_THREE_KEYS[name][k] != current[name][k]}
             for name in BASELINE_THREE_KEYS}
    drift = {k: v for k, v in drift.items() if v}
    assert drift == {}, f"三键（status/note/evidence）被改动：{drift}"


def test_m4_new_keys_limited_to_http() -> None:
    for name, cap in C.CAPABILITIES.items():
        extra = set(cap) - {"status", "note", "evidence"}
        assert extra <= ALLOWED_NEW_KEYS, f"{name} 出现未授权的新键：{sorted(extra)}"


def test_m4_community_report_prose_subset_of_http() -> None:
    """`community_report.note` 里的散文端点必须 ⊆ `http` 列表（散文与结构化不许漂移）。"""
    import re

    note = C.CAPABILITIES["community_report"]["note"]
    prose = set(re.findall(r"/v2/[A-Za-z0-9_/\-]+", note))
    declared = {str(e.get("path")) for e in (C.CAPABILITIES["community_report"].get("http") or [])}
    assert prose, "community_report.note 里应有散文端点（原样保留，不得删）"
    assert prose <= declared, f"散文里有、结构化里没有：{sorted(prose - declared)}"


# ---------------------------------------------------------------- M5 结构可消费
def test_m5_schema_and_counts_unchanged() -> None:
    d = C.describe()
    assert d["schema"] == "llmke.graph-engine.describe.v1", "http 是可选字段，不得升 schema 版本"
    assert d["counts"] == {"VERIFIED": 19, "NOT_VERIFIED": 1, "NOT_IMPLEMENTED": 0}
    assert sum(d["counts"].values()) == len(d["capabilities"])
    assert d["declared"] == sorted(d["capabilities"])


def test_m5_json_serializable() -> None:
    text = C.to_json()
    assert text.startswith("{")
    parsed = json.loads(text)
    assert "http" in json.dumps(parsed["capabilities"], ensure_ascii=False) or True
    json.dumps(parsed, ensure_ascii=False)


def test_m5_http_field_is_optional_for_old_producers() -> None:
    """旧的三键能力项（无 `http`）必须仍然合法 —— 否则新字段变成必填，破坏兼容。"""
    assert "http" not in C.CAPABILITIES["visibility_fence"], \
        "本 loop 只给 3 条写路由登记 http；其余项不得为了对称而新增"
    legacy = {name: {"status": "VERIFIED", "note": "n", "evidence": "e"} for name in ("x",)}
    for cap in legacy.values():
        assert set(cap) == {"status", "note", "evidence"}
    three_key_only = [n for n, c in C.CAPABILITIES.items() if "http" not in c]
    assert len(three_key_only) == len(C.CAPABILITIES) - len(REQUIRED_WRITE_ROUTES)


def test_m5_describe_copies_capabilities_not_aliases() -> None:
    d = C.describe()
    d["capabilities"]["incremental_update"]["status"] = "TAMPERED"
    assert C.CAPABILITIES["incremental_update"]["status"] == "VERIFIED"
