"""检索命中的**后置过滤**：生效期（as-of）与可见域（scope）两道闸。

为什么放在这一层、而不是去改引擎：
`capabilities.py` 里 `engine_version_filtering` / `engine_visibility_isolation` 一直是
NOT_IMPLEMENTED，理由是"断言层成立、引擎检索未接"。但**没有理由要求引擎先学会这两件事**：
引擎只负责召回，平台负责认定——`pipeline.retrieve` 已经在结果回来后用 `fence.filter_hits`
拦撤权内容，同样的位置可以再拦"过期"与"越权"。改引擎意味着把平台语义塞进第三方库
（HippoRAG）的检索路径里，既不可测也不可回退；后置过滤是纯函数，构造数据就能反证。

因此本模块只做一件事：给 `[{text, sources}]` 列表加两道过滤，返回
`{"hits", "dropped", "stats"}`，**不改引擎、不改既有调用方**（是否默认开启由 TL 决定）。

两条闸的方向**刻意相反**（不是笔误，是本模块最重要的设计点）：

- 生效期（版本）：查不到日期 → **保留**，计 `stats["unknown_window"]`。
  理由：绝大多数正常文档没有写生效期。若把"没写日期"当作"过期"，一次开启就会把语料
  大片误杀，运维只能把开关关掉——安全机制一旦以误杀为代价就活不下来。
  代价是"漏杀"，可接受，因为我们只在**能证明过期**（有日期且全部落在窗口外）时丢弃。

- 可见域（权限）：查不到可见集合 → **丢弃**，计 `stats["unknown_scope_dropped"]`。
  理由：越权是单向不可逆的事故（内容已经到了用户眼前），而版本过期最多是答案旧一点。
  两者风险量级不同，所以方向不同：一个 fail-open（只在有证据时杀），一个 fail-closed
  （没有证据就当无权限）。这与 `assertions.decide_route`、`fence.assert_index_fresh`
  里"没声明代次就拒绝读"的口径一致。

边界（写清楚，避免被当成已支持）：
- 只过滤**命中级可见性**，不是构建期索引隔离——不可见文件的内容仍可能被引擎召回并送回，
  只是在这里被丢掉（`engine_visibility_isolation` 的构建期部分依然没有做）；
- 保留的命中会**裁掉失效来源**（见下），但正文本身不重写：同一块文本若只有部分来源过期，
  正文仍是整块，引用请按 `sources` 走；
- 未接进 `pipeline.retrieve`，默认行为零变化。
"""

from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

__all__ = ["filter_hits", "REASON_OUT_OF_WINDOW", "REASON_SCOPE_DENIED",
           "REASON_UNKNOWN_SCOPE"]

REASON_OUT_OF_WINDOW = "OUT_OF_WINDOW"
REASON_SCOPE_DENIED = "SCOPE_DENIED"
REASON_UNKNOWN_SCOPE = "UNKNOWN_SCOPE"

# 每个来源文件在某一维上的判定结果
_ALIVE = "ALIVE"
_DEAD = "DEAD"
_UNKNOWN = "UNKNOWN"

TEXT_PREFIX_LIMIT = 40


# ---------------------------------------------------------------- 基础取值
def _fid_of(src: Any) -> str:
    """取单个来源的 file_id。

    兼容两种来源写法：`{"file_id": ...}` 字典（`pipeline._norm_sources` 归一后的形态）
    与 `SourceRef` 对象（断言层原生形态）。只认 `file_id`——它是引用收口的唯一外键，
    缺了就无法回查事实与可见域。
    """
    fid = (src.get("file_id", "") if isinstance(src, dict)
           else getattr(src, "file_id", ""))
    return str(fid or "")


def _file_ids(hit: Dict[str, Any]) -> List[str]:
    """取命中的来源文件 id，保持顺序并去重（用于 dropped 记录与统计）。"""
    out: List[str] = []
    for src in (hit.get("sources") or []):
        fid = _fid_of(src)
        if fid and fid not in out:
            out.append(fid)
    return out


def _text_prefix(hit: Dict[str, Any]) -> str:
    """日志只留 40 字：dropped 会进报告/指标，正文太长会把日志和指标撑爆。"""
    return str(hit.get("text") or "")[:TEXT_PREFIX_LIMIT]


def _in_window(assertion: Any, as_of: str) -> bool:
    """生效期判定，语义**必须**与 `AssertionStore._in_window` 一致（半开区间）。

    刻意在这里复写而不是调 `store._in_window`：那是私有方法，跨模块调用会把
    两个模块的演进绑死；但两边口径必须一样，否则"断言层查得到、检索侧却丢掉"
    这种自相矛盾会出现。`tests/test_retrieval_filter.py` 里用同一批构造事实
    同时走 `store.facts(as_of=...)` 与 `filter_hits(as_of=...)` 做交叉校验。
    """
    start = getattr(assertion, "effective_from", None)
    end = getattr(assertion, "effective_to", None)
    if start and as_of < start:
        return False
    if end and as_of >= end:      # 右开：到期当天即失效（与断言层一致）
        return False
    return True


# ---------------------------------------------------------------- 两维判定
def _window_state(file_id: str, store: Any, as_of: str) -> str:
    """某个来源文件在 `as_of` 这一天是否还有效。

    - 无任何**带生效期**的事实 → UNKNOWN（保留，计 unknown_window）；
    - 有带生效期的事实，任一落在窗口内 → ALIVE；
    - 有带生效期的事实但**全部**落在窗口外 → DEAD。

    注意：文件里若同时有"带日期但已过期"和"没写日期"的事实，仍判 DEAD。
    没写日期的事实不构成新鲜度证明——它既不能说明内容新，也不能说明内容旧，
    拿它来自证"还有效"等于给过期文档开后门。
    """
    facts = store.facts_by_source(file_id)
    dated = [f for f in facts
             if getattr(f, "effective_from", None) or getattr(f, "effective_to", None)]
    if not dated:
        return _UNKNOWN
    return _ALIVE if any(_in_window(f, as_of) for f in dated) else _DEAD


def _scope_state(file_id: str, scopes: Set[str], doc_scopes: Any) -> str:
    """某个来源文件在当前可见域集合下是否可见（fail-closed）。

    - `doc_scopes` 没给、或里面查不到该文件 → UNKNOWN（**按不可见处理**）；
    - 可见域集合与 `scopes` 有交集 → ALIVE；交集为空 → DEAD。

    为什么 `doc_scopes=None` 也按 UNKNOWN 处理而不是"不过滤"：调用方既然给了
    `scopes`，就表示这次查询要求做可见性隔离；拿不到文件的可见域就等于拿不到授权，
    只能拒绝。若这里选择放行，"忘记传 doc_scopes"会静默变成"全部可见"，
    而调用方看不出任何异常——这类静默降级正是权限事故的典型形态。
    """
    if doc_scopes is None:
        return _UNKNOWN
    owned = doc_scopes.get(file_id) if hasattr(doc_scopes, "get") else None
    if owned is None:
        return _UNKNOWN
    if isinstance(owned, str):        # 容忍单个字符串写法，别因为类型差异误判
        owned = {owned}
    return _ALIVE if (set(owned) & scopes) else _DEAD


def _is_alive(window: str, scope: str) -> bool:
    """两维按**各自方向**解读后合成：`window != DEAD` 且 `scope == ALIVE`。

    这里必须是两个方向的判定，不能先折成"最弱一档"再判断——初版就是折成
    `DEAD > UNKNOWN > ALIVE` 再比 `== ALIVE`，结果版本维的 UNKNOWN（没写日期）
    被当成了拒绝，恰好把本模块要保护的正常语料误杀（`unknown_window` 那个用例
    第一次跑就红了）。UNKNOWN 的含义完全取决于维度：
    - 版本维 UNKNOWN = "无法证明过期" → 放行（fail-open）；
    - 可见性维 UNKNOWN = "无法证明有权看" → 拒绝（fail-closed）。
    """
    return window != _DEAD and scope == _ALIVE


def filter_hits(hits: Sequence[Dict[str, Any]], *, as_of: Optional[str] = None,
                scopes: Optional[Iterable[str]] = None, store: Any = None,
                doc_scopes: Optional[Dict[str, Set[str]]] = None) -> Dict[str, Any]:
    """按生效期与可见域过滤检索命中，返回 `{"hits", "dropped", "stats"}`。

    参数：
    - `as_of`：业务日期 `YYYY-MM-DD`；需要同时给 `store`（断言层）才有意义，
      只给 `as_of` 而没有 `store` 时**完全不过滤**——没有事实可查，猜日期等于编造；
    - `scopes`：本次查询允许的可见域集合；给了就必须同时给 `doc_scopes`，
      否则全部来源按 UNKNOWN_SCOPE 丢弃（见 `_scope_state`）；
    - `doc_scopes`：`file_id -> {scope, ...}`，文件可见域表；
    - `store`：`AssertionStore`，用 `facts_by_source` 反查文件的生效期事实。

    规则：
    1. 一个命中只要还有**至少一个来源**在两维上都活着就保留，并把失效/不可见的来源
       从返回副本里裁掉（与 `fence.filter_hits` 同构：多来源内容不该被单个坏来源拖死，
       但也不能让坏来源留在 citations 里被下游引用）；
    2. 全部来源都死 → 丢弃，`reason` 优先级 `SCOPE_DENIED` > `UNKNOWN_SCOPE` >
       `OUT_OF_WINDOW`：多重原因同时成立时报可见性那条，因为可见性是被拒的最短且
       不会因版本恢复而改变的结论；
    3. 保持输入顺序；不修改入参（裁来源时生成新 dict / 新 list）；
    4. 三个过滤参数全空 → 原样返回，`stats` 全零，保证"开了模块不等于改了行为"。

    `stats` 口径：
    - `input` / `kept` / `dropped`：命中数；
    - `unknown_window`：生效期不可判定的 **(命中, 来源) 对**数（按对计数，不按命中），
      用来观察"语料里有多少内容没有写生效期"，这就是版本过滤的真实覆盖率上限；
    - `unknown_scope_dropped`：因可见域不可确定而**整条命中**被丢弃的个数；
    - `trimmed_sources`：保留的命中里被裁掉的来源数（含过期、越权、无法判定三类）。
    """
    items = list(hits or [])
    stats = {"input": len(items), "kept": 0, "dropped": 0,
             "unknown_window": 0, "unknown_scope_dropped": 0, "trimmed_sources": 0}

    window_on = bool(as_of) and store is not None
    scope_on = scopes is not None
    if not window_on and not scope_on:
        # 不改变行为：没开闸就原样返回，连 dict 都不重建（省一次深拷贝，也避免误改）
        stats["kept"] = len(items)
        return {"hits": items, "dropped": [], "stats": stats}

    wanted: Set[str] = set(scopes) if scope_on else set()

    kept: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []

    for hit in items:
        fids = _file_ids(hit)
        if not fids:
            # 没有来源的命中：版本维无法判定 → 按"未知生效期"放行；
            # 可见性维无法判定 → 拒绝（没有来源就没有授权依据）。
            if scope_on:
                dropped.append({"text_prefix": _text_prefix(hit), "file_ids": [],
                                "reason": REASON_UNKNOWN_SCOPE})
                stats["dropped"] += 1
                stats["unknown_scope_dropped"] += 1
                continue
            stats["unknown_window"] += 1
            kept.append(hit)
            continue

        alive: Set[str] = set()
        reasons: List[str] = []
        # 逐个来源判定。生效期与可见域都是**文件级**属性，所以同一 file_id 的多个片段
        # （不同 locator/channel）只判一次，否则 unknown_window 会被同一文件重复计数。
        for fid in fids:
            window = _ALIVE
            if window_on:
                window = _window_state(fid, store, as_of)
                if window == _UNKNOWN:
                    stats["unknown_window"] += 1

            scope = _ALIVE
            if scope_on:
                scope = _scope_state(fid, wanted, doc_scopes)

            if _is_alive(window, scope):
                alive.add(fid)
                continue

            # 记失败原因，供整条命中被丢弃时按优先级挑 reason
            if scope == _DEAD:
                reasons.append(REASON_SCOPE_DENIED)
            elif scope == _UNKNOWN:
                reasons.append(REASON_UNKNOWN_SCOPE)
            else:
                reasons.append(REASON_OUT_OF_WINDOW)

        if alive:
            all_src = list(hit.get("sources") or [])
            # 没有 file_id 的来源无法回查授权，一旦需要裁剪就一并裁掉；
            # 不需要裁剪时保留原样，避免无谓地改变调用方拿到的数据形态。
            live_src = [s for s in all_src if _fid_of(s) in alive]
            trimmed = len(all_src) - len(live_src)
            if trimmed:
                stats["trimmed_sources"] += trimmed
                # 生成新副本：入参 hits 与 hit["sources"] 一个都不动
                kept.append({**hit, "sources": live_src})
            else:
                kept.append(hit)
            continue

        reason = REASON_OUT_OF_WINDOW
        for candidate in (REASON_SCOPE_DENIED, REASON_UNKNOWN_SCOPE):
            if candidate in reasons:
                reason = candidate
                break
        dropped.append({"text_prefix": _text_prefix(hit), "file_ids": fids,
                        "reason": reason})
        stats["dropped"] += 1
        if reason == REASON_UNKNOWN_SCOPE:
            stats["unknown_scope_dropped"] += 1

    stats["kept"] = len(kept)
    return {"hits": kept, "dropped": dropped, "stats": stats}
