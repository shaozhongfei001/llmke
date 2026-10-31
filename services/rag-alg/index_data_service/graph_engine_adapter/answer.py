"""回答组装：把检索候选变成"带可核验引用"的答案。

三条硬规则（对应设计 §6.2：最终回答由平台组装、核验、引用，不让引擎 rag_qa 绕过）：
1. **只用给定材料**：上下文由命中段落 + 断言组成，模型不得引入外部知识；
2. **引用必须可核验**：`file_id` 必须在本次上下文里，`quote` 必须是该文件材料里的**原文子串**；
   核验不过的引用单列 `invalid_citations`，且整体 `passed=False`——宁可无答案，不给假引用；
3. **强制图验收沿用到回答**：`require_graph` 时若 `executed_route != GRAPH`，直接拒绝组装。

LLM 通过 `llm_call(messages, **kw)` 注入，测试用假实现即可，不加载模型。
"""

import json
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

SCHEMA = "llmke.graph-engine.answer.v1"

SYSTEM_PROMPT = (
    "你只能依据用户给出的【材料】回答，不得使用材料之外的知识。\n"
    "若材料不足以回答，answer 写\"材料不足\"，citations 留空数组。\n"
    "必须输出 JSON：{\"answer\": string, \"citations\": [{\"file_id\": string, \"quote\": string}]}\n"
    "只输出这一个 JSON 对象本身，不要解释、不要序号、不要任何前后缀。\n"
    "quote 必须是从【材料】里**逐字复制**的原文片段，不得改写、不得拼接；"
    "不得引用任何推断、总结或表格之外的转述。\n"
    "示例：{\"answer\": \"8000万元\", \"citations\": [{\"file_id\": \"333\", "
    "\"quote\": \"最高额度 8000万元\"}]}"
)


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    return (m.group(1) if m else t).strip()


def parse_answer(raw: str) -> Dict[str, Any]:
    """容忍前后废话与代码块；解析失败返回结构化错误，不抛异常给调用方。"""
    try:
        data = json.loads(_strip_fences(raw))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}", "raw": (raw or "")[:200]}
    if not isinstance(data, dict):
        return {"error": "NOT_AN_OBJECT", "raw": (raw or "")[:200]}
    return data


def build_context(store, hits: Sequence[Dict[str, Any]], *,
                  max_passages: int = 6, include_derived: bool = False) -> List[Dict[str, Any]]:
    """上下文 = 命中段落（默认不含平台派生断言）。

    默认不给模型看派生断言：给了它就会去引用断言，而断言不是原文，引用一律核验不过
    （实测：模型稳定引用"产品甲 额度 8000万元"这类渲染文本）。图的价值体现在**召回排序**上，
    不靠把派生物喂进上下文。
    """
    ctx: List[Dict[str, Any]] = []
    seen_files = set()
    for hit in hits[:max_passages]:
        files = [s.get("file_id") for s in hit.get("sources") or [] if s.get("file_id")]
        # 只有段落是原文，可被引用；断言是平台派生物，只能辅助理解
        ctx.append({"kind": "passage", "text": hit.get("text", ""), "files": files,
                    "citable": True})
        seen_files.update(files)

    if not include_derived:
        return ctx

    for fid in sorted(seen_files):
        for fact in store.facts_by_source(fid):
            ctx.append({"kind": "assertion", "text": store.render(fact), "files": [fid],
                        "citable": False})
    return ctx


def _norm(text: str) -> str:
    """核验引用时忽略空白差异（表格换行/空格），但**不**忽略字词改动。"""
    return re.sub(r"\s+", "", text or "")


def _render_materials(context: Sequence[Dict[str, Any]]) -> str:
    lines = []
    for i, item in enumerate(context, 1):
        files = ",".join(item["files"]) or "unknown"
        lines.append(f"[{i}] (file_id={files})\n{item['text']}")
    return "\n\n".join(lines)


def verify_citations(citations: Iterable[Dict[str, str]],
                     context: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    """逐条核验：file_id 在上下文里 + quote 是该文件**原文段落**的子串。

    断言是平台派生物（我们自己的渲染），拿它当"原文"引用属于自证循环，
    所以只在 `citable=True` 的材料里找；只在派生文本里找到的单独报 QUOTE_IN_DERIVED_ONLY。
    """
    by_file: Dict[str, List[str]] = {}
    derived: Dict[str, List[str]] = {}
    for item in context:
        for fid in item["files"]:
            bucket = by_file if item.get("citable", True) else derived
            bucket.setdefault(str(fid), []).append(item["text"])

    valid, invalid = [], []
    for c in citations or []:
        fid = str((c or {}).get("file_id", ""))
        quote = str((c or {}).get("quote", "") or "").strip()
        if not fid or not quote:
            invalid.append({**c, "reason": "MISSING_FIELD"})
        elif fid not in by_file:
            invalid.append({**c, "reason": "FILE_NOT_IN_CONTEXT"})
        elif not any(_norm(quote) in _norm(text) for text in by_file.get(fid, [])):
            only_derived = any(_norm(quote) in _norm(text) for text in derived.get(fid, []))
            invalid.append({**c, "reason": "QUOTE_IN_DERIVED_ONLY" if only_derived
                            else "QUOTE_NOT_FOUND"})
        else:
            valid.append({**c, "reason": "OK"})
    return {"valid": valid, "invalid": invalid}


def assemble(query: str, *, store, retrieval: Dict[str, Any],
             llm_call: Callable[..., Any], require_graph: bool = False,
             require_citation: bool = True, **llm_kwargs) -> Dict[str, Any]:
    """返回 {answer, citations, invalid_citations, passed, reason, context_size}。"""
    if require_graph and retrieval.get("executed_route") != "GRAPH":
        return {"schema": SCHEMA, "query": query, "answer": None, "citations": [],
                "invalid_citations": [], "passed": False,
                "reason": f"GRAPH_ROUTE_REQUIRED_BUT_{retrieval.get('executed_route')}",
                "context_size": 0}

    context = build_context(store, retrieval.get("hits") or [])
    if not context:
        return {"schema": SCHEMA, "query": query, "answer": None, "citations": [],
                "invalid_citations": [], "passed": False, "reason": "EMPTY_CONTEXT",
                "context_size": 0}

    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"【材料】\n{_render_materials(context)}\n\n"
                                            f"【问题】\n{query}"}]
    raw = llm_call(messages=messages, **llm_kwargs)
    if isinstance(raw, tuple):     # 有的实现返回 (text, usage, ...)
        raw = raw[0]
    parsed = parse_answer(raw if isinstance(raw, str) else str(raw))

    if parsed.get("error"):
        return {"schema": SCHEMA, "query": query, "answer": None, "citations": [],
                "invalid_citations": [], "passed": False,
                "reason": f"UNPARSEABLE_LLM_OUTPUT: {parsed['error']}",
                "context_size": len(context), "raw": parsed.get("raw")}

    check = verify_citations(parsed.get("citations") or [], context)
    answer = (parsed.get("answer") or "").strip()
    passed = bool(answer) and (not require_citation or bool(check["valid"])) \
        and not check["invalid"]
    reason = "OK"
    if not answer:
        reason = "EMPTY_ANSWER"
    elif check["invalid"]:
        # 有"看起来像引用但核验不过"的条目时优先报它：这比"没有引用"更能说明问题
        reason = "INVALID_CITATION"
    elif require_citation and not check["valid"]:
        reason = "NO_VALID_CITATION"

    return {"schema": SCHEMA, "query": query, "answer": answer,
            "citations": check["valid"], "invalid_citations": check["invalid"],
            "passed": passed, "reason": reason, "context_size": len(context)}
