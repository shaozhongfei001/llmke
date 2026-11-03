"""D2 第一版：跨文档实体链接（别名归并 + 同名异体隔离，确定性规则，可审计）。

范围（如实）：
- 只做规则层归并/隔离，不做向量召回、不做 LLM 裁决（那两层留待业务语料验证后加）；
- 归并判据 = alias_key（去括号/去企业后缀后的名字）；同键多实体默认归并，
  同名异体名单（homonyms.v1.json 的 separate 组）里的名字永不互相归并；
- 归并后事实按 content_key 自动合账，来源取并集（AssertionStore.add 既有行为）；
- 输出 report 记每一组"归并了谁 / 隔离了谁"，可审计、可回滚（重跑即回原状）。
"""

import json
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .assertions import Assertion, AssertionStore, SourceRef

SCHEMA = "llmke.entity-link.rules.v1"

_SUFFIXES = ("股份有限公司", "有限责任公司", "有限公司", "集团", "分公司", "公司")


def _clean(name: str) -> str:
    s = str(name or "")
    # 去全角/半角括号内容（如 "星航贷（产品A）" → "星航贷"）
    while "（" in s and "）" in s:
        s = s[: s.index("（")] + s[s.index("）") + 1 :]
    while "(" in s and ")" in s:
        s = s[: s.index("(")] + s[s.index(")") + 1 :]
    return "".join(s.split())


def alias_key(name: str) -> str:
    """候选键：去空白/括号后迭代去企业后缀。空名返回空串（不参与归并）。"""
    s = _clean(name)
    changed = True
    while changed and s:
        changed = False
        for suf in _SUFFIXES:
            if s.endswith(suf) and len(s) > len(suf):
                s = s[: -len(suf)]
                changed = True
                break
    return s


def load_homonyms(path: Optional[str] = None) -> List[List[str]]:
    """同名异体隔离名单：每组里的名字**永不互相归并**。

    默认读仓库 `contracts/ontology/homonyms.v1.json`（逐级向上找，找不到/解析失败 → 空名单，
    宁可多归并也不静默猜）。schema: {"schema":..., "separate": [["甲","乙"], ...]}
    """
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        for _ in range(6):
            cand = os.path.join(here, "contracts", "ontology", "homonyms.v1.json")
            if os.path.isfile(cand):
                path = cand
                break
            here = os.path.dirname(here)
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
        out: List[List[str]] = []
        for group in spec.get("separate") or []:
            names = [str(n).strip() for n in group if str(n).strip()]
            if len(names) >= 2:
                out.append(names)
        return out
    except Exception:  # noqa: BLE001 - 名单坏了按"无隔离"处理并留空，不炸主链
        return []


def _group_ids(store: AssertionStore) -> Dict[str, List[str]]:
    """按 alias_key(可读名) 分组 canonical id。"""
    groups: Dict[str, List[str]] = {}
    for cid in sorted(store._entities):  # 确定性遍历
        readable = store.name_of(cid)
        key = alias_key(readable)
        if not key:
            continue
        groups.setdefault(key, []).append(cid)
    return groups


def plan_merges(
    store: AssertionStore, separate: Sequence[Sequence[str]] = ()
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """决定哪些 canonical id 归并到哪个。返回 (remap, report)。

    remap：旧 id → 新 canonical id（不变的键不出现在 remap）。
    report：merged_groups（key → {kept, merged, names}）、kept_separate（被名单隔离的组）。
    """
    separate_sets = [set(g) for g in separate]
    remap: Dict[str, str] = {}
    merged_groups: List[Dict[str, Any]] = []
    kept_separate: List[Dict[str, Any]] = []
    for key, ids in sorted(_group_ids(store).items()):
        if len(ids) < 2:
            continue
        names = [store.name_of(i) for i in ids]
        # 名单隔离：同一 separate 组里出现 ≥2 个本组名字 → 全组不归并
        if any(len(set(names) & ss) >= 2 for ss in separate_sets):
            kept_separate.append({"alias_key": key, "ids": ids, "names": names})
            continue
        kept = ids[0]  # sorted 后最小 id，确定性
        for cid in ids[1:]:
            remap[cid] = kept
        merged_groups.append({"alias_key": key, "kept": kept, "merged": ids[1:], "names": names})
    return remap, {
        "schema": SCHEMA,
        "merged_groups": merged_groups,
        "merged_count": len(merged_groups),
        "kept_separate": kept_separate,
        "separate_count": len(kept_separate),
    }


def apply_linking(
    store: AssertionStore, separate: Sequence[Sequence[str]] = ()
) -> Tuple[AssertionStore, Dict[str, Any]]:
    """执行归并：返回新 store（实体、别名、断言全部重映射）与 report。

    事实按 content_key 在 store.add 里自动合账 → 跨文档多来源取并集（D2 要求）。
    """
    remap, report = plan_merges(store, separate)
    new = AssertionStore()

    def map_id(cid: Optional[str]) -> Optional[str]:
        if not cid:
            return cid
        return remap.get(cid, cid)

    # 实体与别名：新 id 下重登记（原名 + id 名，保持 name_of 行为一致）
    registered: Set[str] = set()
    for cid in sorted(store._entities):
        target = map_id(cid)
        names = set(store._entities[cid]) | {target}
        if target not in registered:
            new.register_entity(target, *sorted(names))
            registered.add(target)
        else:
            new.register_entity(target, *sorted(names))

    for orphan in sorted(store._orphans or []):
        new._orphans.add(map_id(orphan))

    for a in store._assertions.values():
        new.add(Assertion(
            subject=map_id(a.subject), predicate=a.predicate,
            object_entity=map_id(a.object_entity), object_value=a.object_value,
            unit=a.unit, direction=a.direction, op=a.op, key=a.key,
            effective_from=a.effective_from, effective_to=a.effective_to,
            qualifiers=dict(a.qualifiers), visibility=set(a.visibility),
            sources=list(a.sources)))

    report["entities_before"] = len(store._entities)
    report["entities_after"] = len(new._entities)
    report["assertions_before"] = len(store._assertions)
    report["assertions_after"] = len(new._assertions)
    return new, report
