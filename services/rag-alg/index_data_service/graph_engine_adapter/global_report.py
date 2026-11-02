"""建图后产社区报告：抽取结果 → 标准断言 → 社区 → 可核验的 global 报告（落盘 community.json）。

分工（对应设计 §6.4）：社区/global 只能消费**经原文与可见性校验的标准事实**，不能用普通
RAG 结果顶替。所以本模块不读引擎的图结构，只吃两样东西：
1. `engine.openie_docs()` —— 抽取出来的三元组候选（不是业务事实）；
2. 快照里的 `sources.json` —— idx → [{file_id, locator, title}]，把每条事实绑回真实来源。

## 为什么"引用校验"要自己判，不能只信 community.build_report

`community.build_report` 里的 `validate_report_citations` 校验的是**已经被导出过滤后**的
事实，而导出时不可见来源的整条事实已被剔除——于是 `invalid` 天然为空。
只看它就会得到"引用失效=0"的假绿灯（项目里反复出现的空转形态）。本模块额外做三件：

- `known_files` 用**本次 build 实际写入的 file_id 列表**（而不是被检查的 sources.json 自己），
  这样把 sources.json 改成幽灵 id 时，来源会立即判为不可见；
- 来源文件缺失 / 抽到的事实全都挂不上来源时，判 `SOURCES_MISSING`，**不因为"没东西可查"就通过**；
- `checked == 0`（没有任何引用被真正校验）一律 `ok=False / NO_FACTS`，不允许空集当通过。

## 确定性

同一份输入两次建图，`community.json` 必须逐字节相同（验收要求 sha256 相同）：
所以文件里**不写时间戳、不写快照路径**，所有集合取 `sorted`，`json.dump(sort_keys=True)`。

## 文件形状（community.json）

    {schema, status, sources_available, inputs{file_ids,documents,facts},
     communities[{id,size,isolated,entities,facts[{text,sources}],fact_count,sources}],
     community_count, answer, citations[{community,text,sources}],
     citation_check{ok,checked,valid,invalid,sources_available,reason},
     excluded[], policy}
"""

import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .assertions import SourceRef
from .community import build_report
from .normalize import build_store

SCHEMA = "llmke.graph-engine.global-report.v1"
FILE_NAME = "community.json"
CHANNEL = "graph"

POLICY = ("global 报告只消费经原文与可见性校验的标准事实；"
          "无社区或无引用时如实标不可用，不用普通检索结果顶替")

# Answer 里每条事实后面必须带来源，缺来源的事实根本不进报告，所以这里只做格式统一。
SOURCE_HINT = "（来源：{files}）"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_sources(snapshot: Optional[str]) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """读快照的 sources.json；**文件不存在返回 None**（与"存在但为空"区分开）。"""
    if not snapshot:
        return None
    path = os.path.join(snapshot, "sources.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _resolver(sources: Optional[Dict[str, List[Dict[str, Any]]]]):
    """idx → SourceRef 列表；拿不到 file_id 的条目不生成引用（不挂空来源）。"""
    table = sources or {}

    def resolve(idx: str) -> List[SourceRef]:
        refs = []
        for item in table.get(idx) or []:
            file_id = item.get("file_id") if isinstance(item, dict) else None
            if file_id in (None, ""):
                continue
            refs.append(SourceRef(file_id=str(file_id), artifact_id=str(idx or ""),
                                  channel=CHANNEL, locator=str(item.get("locator") or "")))
        return refs

    return resolve


def _citation_check(report: Dict[str, Any], *, sources_available: bool,
                    fact_total: int) -> Dict[str, Any]:
    """对报告的引用做**非空转**校验：没有可校验项也不算通过。"""
    base = report.get("citations") or {"valid": [], "invalid": []}
    valid = list(base.get("valid") or [])
    invalid = list(base.get("invalid") or [])

    # 导出阶段被剔除的"来源不可见"事实同样算引用失效——它们本来会被引用，只是被挡下了。
    invisible: List[str] = []
    for item in report.get("excluded") or []:
        if item.get("reason") != "SOURCE_NOT_VISIBLE":
            continue
        files = item.get("files") or ["<unknown>"]
        invisible.append(f"{files[0]}:{(item.get('fact') or '')[:20]}")

    checked = len(valid) + len(invalid) + len(invisible)
    if not sources_available:
        return {"ok": False, "checked": 0, "valid": [], "invalid": [],
                "sources_available": False, "reason": "SOURCES_MISSING",
                "detail": "快照里没有可读的 sources.json，引用无法回到真实文件，不能判通过"}
    if fact_total <= 0:
        return {"ok": False, "checked": checked, "valid": valid, "invalid": invalid,
                "sources_available": True, "reason": "NO_FACTS",
                "detail": "没有任何标准事实进入报告，引用无从校验，不能判通过"}
    if invalid or invisible:
        return {"ok": False, "checked": checked, "valid": valid,
                "invalid": sorted(set(invalid + invisible)), "sources_available": True,
                "reason": "CITATION_INVALID",
                "detail": "存在无法回到真实来源的引用，global 结论不可对外使用"}
    return {"ok": True, "checked": checked, "valid": valid, "invalid": [],
            "sources_available": True, "reason": None, "detail": None}


def section_id(section: Dict[str, Any]) -> Optional[str]:
    """社区 id 的**唯一取法**：`community.build_report` 写的是 `community` 键，
    自己构造的 section 可能写 `id`。两处都认，避免下游拿到 None 当社区号。"""
    return section.get("community") or section.get("id")


def _bigrams(text: str) -> set:
    cleaned = "".join(ch for ch in str(text or "") if not ch.isspace())
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def _relevance(query: str, section: Dict[str, Any]) -> int:
    """社区与问句的字面重合度（字符二元组计数）。

    只做**排序**用的粗相关度：不生成事实、不改写事实，也不能把不相关的事实"算成"相关。
    用二元组而不是整串包含，是因为抽取出的实体名往往被切碎（"总行授信审查委员会"），
    整串匹配几乎不会命中。
    """
    grams = _bigrams(query)
    if not grams:
        return 0
    text = " ".join([str(f.get("text") or "") for f in section.get("facts") or []]
                    + [str(e) for e in section.get("entities") or []])
    return len(grams & _bigrams(text))


def assemble_answer(sections: Sequence[Dict[str, Any]], *,
                    max_communities: int = 3, query: str = "") -> Tuple[str, List[Dict[str, Any]]]:
    """把报告里的社区事实拼成答案：每行一条事实、逐条带来源，不写无来源的结论。

    `query` 只用来**重排**社区（相关度高的排前面，同分保持报告原序），不新增、不改写事实。
    """
    ordered = list(sections)
    if query and query.strip():
        order = sorted(enumerate(ordered),
                       key=lambda pair: (-_relevance(query, pair[1]), pair[0]))
        ordered = [section for _, section in order]

    lines: List[str] = []
    citations: List[Dict[str, Any]] = []
    for section in ordered[:max_communities]:
        for fact in section.get("facts") or []:
            sources = sorted({str(s) for s in (fact.get("sources") or [])})
            if not sources:
                # 防御：报告生成时就不会有这种事实，真出现也不许进答案。
                continue
            lines.append("- " + fact["text"] + SOURCE_HINT.format(files=",".join(sources)))
            citations.append({"community": section_id(section), "text": fact["text"],
                              "sources": sources})
    return "\n".join(lines), citations


def build_report_for_snapshot(snapshot: Optional[str], built_file_ids: Sequence[str]) -> Dict[str, Any]:
    """从快照里的 openie 结果 + sources.json 生成报告（**不写盘**，纯函数）。

    可见文件集合（`known_files`）的取法很关键：
    - 调用方给了本次 build 的 file_id 列表 → **只用它**。这样把 sources.json 改成幽灵 id 时，
      引用会立刻判为不可见；否则"用被检查的文件自己当答案"就是空转。
    - 没给（例如事后单独补报告）→ 退回用 sources.json 的 id，并在 `inputs.visibility_source`
      里写明这是弱一层的核对，不冒充等价。
    """
    sources = read_sources(snapshot)
    built = sorted({str(f) for f in built_file_ids if f not in (None, "")})
    if built:
        known_all, visibility_source = built, "build_inputs"
    else:
        known_all = sorted({str(item.get("file_id")) for items in (sources or {}).values()
                            for item in items if isinstance(item, dict) and item.get("file_id")})
        visibility_source = "sources_json"

    docs = _openie_docs(snapshot)
    store_result = build_store(docs, _resolver(sources))
    store = store_result["store"]
    fact_total = len(store._assertions)

    base = build_report(store, known_all)
    check = _citation_check(base, sources_available=sources is not None, fact_total=fact_total)
    # 引用不过或没有社区时答案留空：报告本身也不许存一份"看起来能答"的文本。
    answer, citations = (assemble_answer(base["communities"])
                         if check["ok"] and base["communities"] else ("", []))

    report = {
        "schema": SCHEMA,
        "status": base["status"] if check["ok"] else "BLOCKED",
        "sources_available": sources is not None,
        "inputs": {"file_ids": known_all, "visibility_source": visibility_source,
                   "documents": len(docs),
                   "triples": sum(len(d.get("extracted_triples") or []) for d in docs),
                   "facts": fact_total,
                   "normalize": store_result["stats"]},
        "communities": base["communities"],
        "community_count": len(base["communities"]),
        "answer": answer,
        "citations": citations,
        "citation_check": check,
        "excluded": base["excluded"],
        "policy": POLICY,
    }
    return report


def _openie_docs(snapshot: Optional[str]) -> List[Dict[str, Any]]:
    """读快照里最新的 openie 结果文件（与 engine.openie_docs 同一读法，避免为报告再加载引擎）。"""
    if not snapshot:
        return []
    import glob

    files = sorted(glob.glob(os.path.join(snapshot, "openie_results_ner_*.json")))
    if not files:
        return []
    try:
        with open(files[-1], encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    return list(data.get("docs") or [])


def render(report: Dict[str, Any]) -> str:
    """规范序列化：顺序稳定、无时间戳/无快照路径 → 同输入同字节。"""
    return json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True)


def write(snapshot: Optional[str], built_file_ids: Sequence[str]) -> Dict[str, Any]:
    """生成并写 `community.json`；返回 {path, sha256, community_count, citation_check, status}。"""
    report = build_report_for_snapshot(snapshot, built_file_ids)
    text = render(report)
    path = os.path.join(snapshot or "", FILE_NAME)
    if snapshot:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return {"path": path, "sha256": _sha256(text), "status": report["status"],
            "community_count": report["community_count"],
            "citation_check": report["citation_check"]}


def load(snapshot: Optional[str]) -> Optional[Dict[str, Any]]:
    """读快照里已有的 community.json；没有/坏了返回 None（由调用方如实说不可用）。"""
    if not snapshot:
        return None
    path = os.path.join(snapshot, FILE_NAME)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def stats(snapshot: Optional[str]) -> Dict[str, Any]:
    """health 用：只报 community.json 里**真实存在**的数字。"""
    report = load(snapshot)
    if report is None:
        return {"wired": False, "communities": 0, "citation_failures": None,
                "reason": "no community.json in snapshot"}
    check = report.get("citation_check") or {}
    return {"wired": True,
            "communities": int(report.get("community_count") or 0),
            "citation_failures": len(check.get("invalid") or []),
            "citation_check_ok": bool(check.get("ok")),
            "status": report.get("status")}
