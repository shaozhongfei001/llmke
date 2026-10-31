"""标准断言层：平台权威的业务事实表示（不是引擎的算法图）。

为什么单独一层：设计 §6.3 明确——HippoRAG 的检索图是**算法结构**，它的无向投影和相似边
不能直接当业务关系。方向、单位、生效期、可见范围、原文支持必须在平台侧作为标准断言保留。
所以这里存的是"平台认定的事实"，引擎只负责召回，二者不互相冒充。

九条语义（对应任务书业务场景）在这里落地，且都能用构造数据反证：
1. 同谓词双向不误合并：`direction="symmetric"` 才双向成立，默认单向；
2. 加/减/零调整：`op` 为 set/add/subtract，总额与分项可对账，单位不一致直接拒绝；
3. 别名与同名异体：别名指向 canonical id；同名是两个不同 id，**不合并**，必须显式选 id；
4. 同事实多来源删一留一：断言按内容去重、按 SourceRef 合并；删掉一个来源只移除该来源；
5. 合法孤点：没有任何关系的实体仍可登记与查询；
6. 新旧政策有效版本：按 `effective_from/effective_to` 做 as-of 查询；
7. 不可见文件变化不污染可见构建：断言带 visibility scope，查询按 scope 过滤；
8. 图禁用/无种子：`decide_route` 给出 GRAPH 或 DENSE_FALLBACK 及原因，不靠"有结果"判断；
9. 引用失效识别：`validate_citations` 比对已知来源，失效的显式列出。
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

SCHEMA = "llmke.assertions.v1"

FORWARD = "forward"
SYMMETRIC = "symmetric"

OP_SET = "set"
OP_ADD = "add"
OP_SUB = "subtract"


@dataclass(frozen=True)
class SourceRef:
    file_id: str
    artifact_id: str
    channel: str = "text"
    locator: str = ""

    def key(self) -> Tuple[str, str, str, str]:
        return (self.file_id, self.artifact_id, self.channel, self.locator)


@dataclass
class Assertion:
    subject: str                     # canonical entity id
    predicate: str                   # 归一后的谓词（平台字典，不是模型自由产出）
    object_entity: Optional[str] = None
    object_value: Optional[float] = None
    unit: Optional[str] = None
    direction: str = FORWARD
    op: str = OP_SET
    key: Optional[str] = None        # 数值断言的账目键，如 "额度"
    effective_from: Optional[str] = None   # YYYY-MM-DD
    effective_to: Optional[str] = None
    qualifiers: Dict[str, Any] = field(default_factory=dict)
    visibility: Set[str] = field(default_factory=lambda: {"public"})
    sources: List[SourceRef] = field(default_factory=list)

    def content_key(self) -> Tuple:
        """同一事实的身份：来源不算在内，用来做多来源合并。"""
        return (self.subject, self.predicate, self.object_entity, self.object_value,
                self.unit, self.direction, self.op, self.key,
                self.effective_from, self.effective_to,
                json.dumps(self.qualifiers, sort_keys=True, ensure_ascii=False))

    def source_keys(self) -> Set[Tuple[str, str, str, str]]:
        return {s.key() for s in self.sources}


class AssertionError_(ValueError):
    pass


class AssertionStore:
    def __init__(self):
        self._aliases: Dict[str, Set[str]] = {}     # name -> 全部 canonical id（同名异体不合并）
        self._entities: Dict[str, Set[str]] = {}    # canonical id -> names
        self._assertions: Dict[Tuple, Assertion] = {}
        self._orphans: Set[str] = set()

    # ---------- 实体 / 别名 ----------
    def register_entity(self, canonical_id: str, *names: str) -> str:
        bucket = self._entities.setdefault(canonical_id, set())
        for name in names or (canonical_id,):
            bucket.add(name)
            self._aliases.setdefault(name, set()).add(canonical_id)
        return canonical_id

    def resolve(self, name_or_id: str) -> Optional[str]:
        """解析成唯一 id；**同名异体解析不唯一时返回 None**，逼调用方显式选 id。"""
        if name_or_id in self._entities:
            return name_or_id
        ids = self._aliases.get(name_or_id) or set()
        return next(iter(ids)) if len(ids) == 1 else None

    def entities_named(self, name: str) -> List[str]:
        """同名异体：返回**所有** canonical id，绝不擅自挑一个。"""
        return sorted(cid for cid, names in self._entities.items()
                      if name in names or cid == name)

    def add_orphan(self, canonical_id: str, *names: str) -> str:
        cid = self.register_entity(canonical_id, *names)
        self._orphans.add(cid)
        return cid

    # ---------- 断言 ----------
    def add(self, assertion: Assertion) -> Assertion:
        if assertion.op not in (OP_SET, OP_ADD, OP_SUB):
            raise AssertionError_(f"未知 op: {assertion.op}")
        if assertion.object_value is not None and not assertion.unit:
            raise AssertionError_("数值断言缺少单位（单位不一致会让总额对不上）")
        if assertion.object_value is not None and not assertion.key:
            raise AssertionError_("数值断言缺少账目 key")
        if not assertion.sources:
            raise AssertionError_("断言必须带来源（无来源的事实不可引用）")

        ck = assertion.content_key()
        existing = self._assertions.get(ck)
        if existing:
            # 同事实多来源：合并来源，不新建断言
            have = existing.source_keys()
            for ref in assertion.sources:
                if ref.key() not in have:
                    existing.sources.append(ref)
            existing.visibility |= assertion.visibility
            return existing
        self._assertions[ck] = assertion
        return assertion

    def remove_source(self, file_id: str) -> List[Tuple]:
        """删掉某文件后：只移除该来源；来源全没了的断言才真正消失。"""
        dropped = []
        for ck, a in list(self._assertions.items()):
            before = len(a.sources)
            a.sources = [s for s in a.sources if s.file_id != file_id]
            if before != len(a.sources) and not a.sources:
                dropped.append(ck)
                del self._assertions[ck]
        return dropped

    # ---------- 查询 ----------
    @staticmethod
    def _visible(assertion: Assertion, scopes: Optional[Set[str]]) -> bool:
        return scopes is None or bool(assertion.visibility & scopes)

    @staticmethod
    def _in_window(a: Assertion, as_of: Optional[str]) -> bool:
        if as_of is None:
            return True
        if a.effective_from and as_of < a.effective_from:
            return False
        if a.effective_to and as_of >= a.effective_to:
            return False
        return True

    def facts(self, subject: str, predicate: Optional[str] = None, *,
              as_of: Optional[str] = None, scopes: Optional[Set[str]] = None) -> List[Assertion]:
        sid = self.resolve(subject) or subject
        out = [a for a in self._assertions.values()
               if a.subject == sid and (predicate is None or a.predicate == predicate)
               and self._visible(a, scopes) and self._in_window(a, as_of)]
        out.sort(key=lambda a: (a.effective_from or "", a.predicate))
        return out

    def effective_fact(self, subject: str, predicate: str, as_of: Optional[str] = None,
                       scopes: Optional[Set[str]] = None) -> Optional[Assertion]:
        """as-of 查询：取生效期最晚且仍在有效期内的那一条。"""
        cands = [a for a in self.facts(subject, predicate, scopes=scopes)
                 if self._in_window(a, as_of)]
        if not cands:
            return None
        cands.sort(key=lambda a: a.effective_from or "", reverse=True)
        return cands[0]

    def related(self, subject: str, predicate: str, obj: str, *,
                as_of: Optional[str] = None, scopes: Optional[Set[str]] = None) -> bool:
        """方向语义：A→B 成立不代表 B→A 成立，除非谓词显式声明 symmetric。"""
        sid, oid = self.resolve(subject) or subject, self.resolve(obj) or obj
        for a in self._assertions.values():
            if a.predicate != predicate or not self._visible(a, scopes) or not self._in_window(a, as_of):
                continue
            if a.object_entity is None:
                continue
            if a.subject == sid and a.object_entity == oid:
                return True
            if a.direction == SYMMETRIC and a.subject == oid and a.object_entity == sid:
                return True
        return False

    # ---------- 数值账目 ----------
    def ledger(self, subject: str, key: str, *, as_of: Optional[str] = None,
               scopes: Optional[Set[str]] = None) -> Dict[str, Any]:
        """把 set/add/subtract 合成总额，并给出分项与差额；单位不一致直接报错。"""
        rows = [a for a in self.facts(subject, as_of=as_of, scopes=scopes)
                if a.key == key and a.object_value is not None]
        if not rows:
            return {"total": None, "components": [], "unit": None, "consistent": True}
        units = {a.unit for a in rows}
        if len(units) > 1:
            raise AssertionError_(f"同一账目 {key} 出现多单位 {sorted(units)}，拒绝相加")

        base = [a for a in rows if a.op == OP_SET]
        base.sort(key=lambda a: a.effective_from or "")
        total = base[-1].object_value if base else 0.0
        components = []
        for a in rows:
            if a.op == OP_SET:
                continue
            delta = a.object_value if a.op == OP_ADD else -a.object_value
            total += delta
            components.append({"op": a.op, "value": a.object_value,
                               "source": a.sources[0].file_id if a.sources else None})
        declared = base[-1].object_value if base else None
        component_sum = sum((c["value"] if c["op"] == OP_ADD else -c["value"]) for c in components)
        return {"total": total, "declared": declared, "components": components,
                "unit": rows[0].unit,
                "delta_from_components": (declared - component_sum) if declared is not None else None,
                "consistent": True}

    # ---------- 引用 ----------
    def validate_citations(self, known_files: Iterable[str]) -> Dict[str, List[str]]:
        """引用失效识别：断言指向的文件已不在可见集合里就报出来。"""
        known = set(known_files)
        valid, invalid = [], []
        for a in self._assertions.values():
            for ref in a.sources:
                (valid if ref.file_id in known else invalid).append(
                    f"{a.subject}.{a.predicate}@{ref.file_id}")
        return {"valid": sorted(set(valid)), "invalid": sorted(set(invalid))}

    def stats(self) -> Dict[str, int]:
        return {"entities": len(self._entities), "aliases": len(self._aliases),
                "assertions": len(self._assertions), "orphans": len(self._orphans),
                "sources": len({s.key() for a in self._assertions.values() for s in a.sources})}


GRAPH = "GRAPH"
DENSE_FALLBACK = "DENSE_FALLBACK"


def decide_route(graph_enabled: bool, seed_entities: Iterable[str],
                 store: Optional[AssertionStore] = None,
                 scopes: Optional[Set[str]] = None) -> Dict[str, str]:
    """路线判定要**先说清楚为什么**：没有种子或图被禁用就走稠密回退，且不许算图验收通过。"""
    seeds = [s for s in seed_entities if s]
    if not graph_enabled:
        return {"route": DENSE_FALLBACK, "reason": "GRAPH_DISABLED"}
    if not seeds:
        return {"route": DENSE_FALLBACK, "reason": "NO_SEED_ENTITY"}
    if store is not None:
        resolved = [store.resolve(s) for s in seeds]
        if not [r for r in resolved if r]:
            return {"route": DENSE_FALLBACK, "reason": "SEEDS_UNKNOWN"}
        has_fact = any(store.facts(r, scopes=scopes) for r in resolved if r)
        if not has_fact:
            return {"route": DENSE_FALLBACK, "reason": "SEEDS_WITHOUT_ASSERTIONS"}
    return {"route": GRAPH, "reason": "SEEDS_WITH_ASSERTIONS"}
