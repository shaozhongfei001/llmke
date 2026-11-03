"""查询侧种子匹配：把"问句里提到的实体"认出来，交给图检索当起点。

现状与问题（实测）：`find_seeds` 只做"实体名是 query 子串"的**精确**匹配。
真实提问很少写全称——用户说"华东精密的额度"，库里的实体叫"华东精密制造有限公司"，
于是 seeds 为空、引擎回退稠密、`require_graph` 直接判失败。这不是检索坏了，是认不出种子。

这里只做一件事：**在保持精确匹配优先的前提下，增加"去掉机构后缀后再比"这一档**。
刻意不做的事（都会引入不可解释的误配）：
- 不做编辑距离模糊匹配（"江南" 会匹配到一堆名字相近的公司）；
- 不做同义词/向量相似（那是另一个模型的事，判断依据不可复核）；
- 不把数字短语当实体（"3000" 到处出现，认成种子会把图检索带偏）。

宁可少认（回退稠密，结果仍可用），也不要错认（把查询引到错误的实体子图）。
"""

from typing import Any, Dict, Iterable, List, Tuple

SCHEMA = "llmke.graph-engine.seed-match.v1"

# 只剥离**机构类型后缀**，不剥离业务词（"银行/支行"这类可能是实体名的一部分）
ORG_SUFFIXES = ("股份有限公司", "有限责任公司", "有限公司", "集团有限公司", "集团", "公司")
MIN_NORMALIZED_LEN = 4          # 去后缀后太短（如"华东"）容易误配，直接放弃


def normalize_name(name: str) -> str:
    """去空白/标点，再去机构后缀。只用于**比较**，不用于写回库。"""
    text = "".join(ch for ch in str(name or "") if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
    for suffix in ORG_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            return text[: -len(suffix)]
    return text


def _short_form(name: str, query: str) -> str:
    """问句里可能出现的"机构简称"：实体核心名的**最长前缀**且至少 MIN_NORMALIZED_LEN 字。

    `华东精密的额度` 与 `华东精密制造有限公司` 的关系就是前缀关系——
    去后缀只能处理"写全称不写后缀"，处理不了"只写前四个字"，所以才需要这一档。
    """
    key = normalize_name(name)
    if len(key) < MIN_NORMALIZED_LEN:
        return ""
    best = ""
    # 简称不一定从第一个字开始（"华东精密电子" 常被叫成 "华东电子"），
    # 所以取**最长且出现在问句里的连续片段**，而不是只看前缀。
    for start in range(len(key) - MIN_NORMALIZED_LEN + 1):
        for end in range(len(key), start + MIN_NORMALIZED_LEN - 1, -1):
            piece = key[start:end]
            if len(piece) > len(best) and piece in query:
                best = piece
                break
    return best


def _groups(query: str, names: List[str]) -> Tuple[List[List[str]], str]:
    """把候选按"匹配到的片段"分组：同一组的名字共享同一个简称。"""
    exact = [n for n in names if n in query]
    if exact:
        return [exact], "exact"

    normalized_query = normalize_name(query)
    if not normalized_query:
        return [], "none"

    full = [n for n in names if len(normalize_name(n)) >= MIN_NORMALIZED_LEN
            and normalize_name(n) in normalized_query]
    if full:
        return [full], "normalized"

    by_form: Dict[str, List[str]] = {}
    for name in names:
        form = _short_form(name, normalized_query)
        if form:
            by_form.setdefault(form, []).append(name)
    return list(by_form.values()), ("normalized" if by_form else "none")


def match_seeds(query: str, names: Iterable[str], resolve) -> Dict[str, Any]:
    """按"能不能解析成**唯一实体**"判歧义，而不是按名字个数。

    引擎里同一个实体常有两个登记名（`ent:华东精密制造有限公司` 与不带 `ent:` 的原名），
    按名字数判会把它们误当成两个实体 → 明明只有一个实体却放弃种子。
    真正的歧义是"解析出两个不同 id"。
    """
    names = [n for n in names if n]
    groups, method = _groups(str(query or ""), names)

    seeds: List[str] = []
    accepted: List[str] = []
    ambiguous: List[Dict[str, Any]] = []
    for group in groups:
        ids = []
        for name in group:
            cid = resolve(name)
            if cid and cid not in ids:
                ids.append(cid)
        if len(ids) == 1:
            if ids[0] not in seeds:
                seeds.append(ids[0])
            accepted.extend(group)
        elif len(ids) > 1:
            ambiguous.append({"names": group, "ids": ids})
        # ids 为空（同名异体解析不出）时静默跳过，交由调用方按"没种子"处理
    if ambiguous and not seeds:
        method = "none"
    return {"seeds": seeds, "method": method, "matched_names": accepted,
            "ambiguous": ambiguous}


def match_names(query: str, names: Iterable[str]) -> Tuple[List[str], str]:
    """只要名字、不要 id 的轻量版（测试与诊断用；歧义判断需要 resolve，请用 match_seeds）。"""
    groups, method = _groups(str(query or ""), [n for n in names if n])
    return [n for group in groups for n in group], method


def diagnose(query: str, store: Any) -> Dict[str, Any]:
    """给调用方/验收看的诊断：认出了什么、用的是哪一档、没认出时为什么。

    没有这个，`seeds=[]` 只能靠猜——到底是"问句里真没实体"还是"匹配规则太死"，
    两者的修法完全不同。
    """
    names = list(store.entity_names()) if store is not None else []
    result = match_seeds(query, names, store.resolve)
    seeds, method, matched = result["seeds"], result["method"], result["matched_names"]
    unresolved = [n for grp in result["ambiguous"] for n in grp["names"]]
    reason = {"exact": "实体名直接出现在问句里",
              "normalized": "去掉机构后缀后匹配（问句用了简称）",
              "none": "问句里没有可识别的实体名：缺少种子，会回退稠密"}[method]
    return {"schema": SCHEMA, "query": query, "method": method,
            "matched_names": matched, "seeds": seeds,
            "unresolved_ambiguous": unresolved,
            "entities_considered": len(names), "reason": reason}
