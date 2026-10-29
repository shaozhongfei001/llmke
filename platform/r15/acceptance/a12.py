#!/usr/bin/env python3
"""A12 全局语义与贡献（任务书 §5.2 A12）。

判据：无实体名主题问、同义改写、多跳、无答案和冲突题各有正确结果；trace 证明图/社区有贡献。
反例：
  N1 对"库里有支持"的问题答成"无相关信息/无法回答" → 覆盖不足被当成正常
  N2 答案里的金额**既不在图里、也无法由图内两条事实算出** → 凭空生成（模型先验冒充证据）
  N3 同义改写换了说法就答不出关键数值 → 只能靠实体全名匹配

N2 的判定口径见 README §8.1（2026-10-29T22:52:22+0800 冻结），三档：
  档1 逐字在图内            → 通过
  档2 可派生且答案标注了推导 → 通过
  档2' 可派生但未标注        → 观察项（不判 FAIL，单独在 detail 里点名）
  档3 真凭空                → FAIL
金额一律按**元**归一成整数比较，不做任何字符串模糊匹配（不用编辑距离/相似度）。
"""
import re

import common as C

ID = "A12"
TITLE = "全局语义：同义改写与无实体名主题问有覆盖、无凭空数值"
WRITES = False

Q_SYNONYM = "智造贷最多能借多少钱？"
Q_TOPIC = "制造业中小微企业的贷款产品在额度上有什么限制？"
NO_ANSWER = ("无相关信息", "无法回答", "抱歉", "没有找到", "未找到相关")

# 金额：万/万元/亿/亿元 四种写法都收，统一按"元"归一再比
AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(亿元|万元|亿|万)")

# 推导标记：闭集，写死（README §8.1），答问方不得扩充
DERIVE_MARKERS = ("其余", "差额", "扣除", "减去", "剩余", "扣减", "刨除", "=", "＝")

# 派生表最多列多少条进 detail（判定用全表，展示截断并注明总数）
TABLE_SHOW = 60
# 算子符号（打印派生表用）
OP_SIGN = {"和": "+", "差": "−", "积": "×", "商": "÷"}


# ────────────────────────────────────────────────────────── 金额解析（整数元）
def _to_yuan(num, unit):
    u = unit.replace(" ", "")
    scale = 10 ** 8 if u.startswith("亿") else 10 ** 4
    return int(round(float(num) * scale))


def amounts_of(text):
    """从文本里取金额 → [(原始串, 元整数值)]。"""
    return [(f"{n}{u}", _to_yuan(n, u)) for n, u in AMOUNT_RE.findall(text or "")]


def fmt_yuan(v):
    """把元整数值格式化回人可读的金额串（用于打印派生表）。"""
    if v and v % 10 ** 8 == 0:
        return f"{v // 10 ** 8}亿元"
    if v % 10 ** 4 == 0:
        return f"{v // 10 ** 4}万元"
    return f"{v}元"


# ────────────────────────────────────────────────────────── 图事实与派生表
def fact_pool():
    """图事实池：amount(元) -> [事实文本]，事实文本形如 `智造贷 -最高额度-> 8000万元`。"""
    pool = {}
    for e in C.edges():
        t = f"{e['s']} -{e['p']}-> {e['o']}"
        seen = {v for _, v in amounts_of(t)}
        for v in seen:
            pool.setdefault(v, [])
            if t not in pool[v]:
                pool[v].append(t)
    return pool


def derivations(pool):
    """由图中**两个不同金额**经 和/差/积/商 算出允许的派生值。

    返回 {结果(元): [(左, 右, 算子名, 左的事实, 右的事实)]}；同值保留全部见证便于复核。
    见证优先选"左右来自**不同**边"的那条，让"两条事实"这个说法站得住；
    只有找不到不同边时才退回同一条边的两端（并在见证里看得出来）。
    """
    vals = sorted(pool)
    out = {}
    for i, a in enumerate(vals):
        for b in vals[i + 1:]:
            hi, lo = max(a, b), min(a, b)      # 差按 大−小 展示，避免出现负数序
            cands = [("和", a + b, a, b), ("差", hi - lo, hi, lo), ("积", a * b, a, b)]
            if b and a % b == 0 and a // b >= 1:
                cands.append(("商", a // b, a, b))
            for op, v, left, right in cands:
                if v == 0:
                    continue
                out.setdefault(v, []).append((left, right, op, pool[left][0], pool[right][0]))
    op_rank = {"差": 0, "和": 1, "积": 2, "商": 3}
    for v, wits in out.items():
        # 见证排序：先"左右来自不同边"，再按 差>和>积>商（差最容易读，优先展示）
        wits.sort(key=lambda w: (0 if w[3] != w[4] else 1, op_rank[w[2]]))
    return out


def tier_of(v, pool, deriv):
    """三档判定：返回 (档位, 见证文本)。"""
    if v in pool:
        return 1, f"图内事实：{pool[v][0]}"
    if v in deriv:
        left, right, op, fl, fr = deriv[v][0]
        same_edge = "（两个操作数同出一条边的两端）" if fl == fr else ""
        return 2, (f"{fmt_yuan(left)}{OP_SIGN[op]}{fmt_yuan(right)}={fmt_yuan(v)}（{op}）；"
                   f"{fl} ／ {fr}{same_edge}")
    return 3, "既不在图内金额集合，也不在两条事实的派生集合内"


def markers_in(text):
    return [m for m in DERIVE_MARKERS if m in (text or "")]


# ────────────────────────────────────────────────────────── 断言
def run():
    checks = []
    pool = fact_pool()
    deriv = derivations(pool)
    graph_amounts = sorted(pool)

    checks.append(C.chk(
        "P0 图内金额夹具可用（≥2 个金额，否则派生判定无意义）",
        len(graph_amounts) >= 2,
        f"图内金额 {len(graph_amounts)} 个：{[fmt_yuan(v) for v in graph_amounts]}"))

    # N2b：派生表必须逐条可复算 —— 防止"派生表本身空转/伪造"
    bad_calc = []
    for v, wits in deriv.items():
        for a, b, op, _, _ in wits:
            redo = {"和": a + b, "差": abs(a - b), "积": a * b,
                    "商": a // b if b else None}[op]
            if redo != v:
                bad_calc.append((fmt_yuan(v), fmt_yuan(a), op, fmt_yuan(b), redo))
    table_lines = []
    for v in sorted(deriv):
        parts = [f"{fmt_yuan(a)}{OP_SIGN[op]}{fmt_yuan(b)}({op})"
                 for a, b, op, _, _ in deriv[v][:2]]
        table_lines.append(f"{fmt_yuan(v)} ⇐ " + " ／ ".join(parts))
    checks.append(C.chk(
        "N2b 派生表可复核（逐条重算 a op b == 表内结果）",
        bool(deriv) and not bad_calc,
        f"派生值 {len(deriv)} 个、见证 {sum(len(w) for w in deriv.values())} 条，"
        f"重算不一致 {len(bad_calc)} 条{bad_calc[:3]}；全表（按值去重，前 {TABLE_SHOW} 条）："
        + "；".join(table_lines[:TABLE_SHOW])
        + (f"；……（共 {len(table_lines)} 条，全表见本 check 的 json）" if len(table_lines) > TABLE_SHOW else "")))

    for name, q in (("同义改写", Q_SYNONYM), ("无实体名主题问", Q_TOPIC)):
        r = C.ask(q)
        ans = r["answer"]
        checks.append(C.chk(f"P1 {name} 有非空答案", r["http"] == 200 and len(ans.strip()) > 10,
                            f"http={r['http']} 耗时={r['elapsed']}s 答案={ans[:120]!r}"))
        checks.append(C.chk(f"P2 {name} 流未中途断开（半截答案不算完成）",
                            not r.get("stream_error"),
                            f"stream_error={r.get('stream_error') or '无'}；收帧={len(r['frames'])}"))
        checks.append(C.chk(f"N1 反例：{name} 未被判为无答案",
                            not any(x in ans for x in NO_ANSWER),
                            f"命中无答案话术={[x for x in NO_ANSWER if x in ans]}"))

        # N2：三档判定（README §8.1）
        marks = markers_in(ans)
        rows, t3, t2prime = [], [], []
        # 同一数值在答案里重复出现只判一次档（按值去重），不重复计入
        seen = sorted({v for _, v in amounts_of(ans)})
        for v in seen:
            tier, why = tier_of(v, pool, deriv)
            if tier == 1:
                rows.append(f"{fmt_yuan(v)}[档1 逐字] ← {why}")
            elif tier == 2:
                if marks:
                    rows.append(f"{fmt_yuan(v)}[档2 可派生+已标注({'/'.join(marks)})] ← {why}")
                else:
                    rows.append(f"{fmt_yuan(v)}[档2' 可派生但未标注] ← {why}")
                    t2prime.append(fmt_yuan(v))
            else:
                rows.append(f"{fmt_yuan(v)}[档3 凭空]")
                t3.append(fmt_yuan(v))
        checks.append(C.chk(
            f"N2 反例：{name} 金额三档判定（无第三档凭空数值）",
            not t3,
            f"答案金额命中档位：{'；'.join(rows) if rows else '（答案里没有带单位金额）'}；"
            f"派生标记={marks or '无'}；档3 凭空={t3}; 档2' 待观察={t2prime}"))

    # N3：同义改写后仍有关键额度
    syn = C.ask(Q_SYNONYM)
    checks.append(C.chk("N3 反例：同义改写后仍给出关键额度",
                        C.has_amount(syn["answer"], "8000万"),
                        f"答案={syn['answer'][:120]!r}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES,
                     skip_reason="受控关闭图/社区的对照实验需改检索配置（写操作），本轮不执行")
