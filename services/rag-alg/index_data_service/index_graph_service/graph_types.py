"""R13 图谱类型体系 / 实体过滤 / canonical 归一。

定位：不改原抽取 Prompt 与 LLM 协议，只在"抽取结果落库之前"加一层确定性的规范化，
解决实测暴露的三类问题：
  1. 纯数字、结构性词（下表/table/天数）被当成实体入图；
  2. LLM 给的类型不在业务类型表里，或直接落到"其他"；
  3. 同一实体的长短名（华东 / 华东精密制造有限公司）被拆成两个节点。

设计约束（与用户要求对齐）：
  - 类型体系带版本号 SCHEMA_VERSION，写入响应与审计，便于后续演进与回溯；
  - 未能判定类型的实体不静默丢弃，标记为 unclassified 并在响应里返回清单（可人工复核）；
  - 归一只做**确定可解释**的规则（别名表 + 全称包含关系），不做不可复现的猜测。
"""
import json
import logging
import os
import re

SCHEMA_VERSION = "v1"

# R14-LIVE-15：三元组内部键的分隔符。
# 原来用逗号拼 "src,rel,dst"，而实体名本身可能含逗号（金额 "2,983,333.33"），
# 于是 split(",") 切出 5 段、triples_source_dict 找不到键 —— 实测 KeyError
# '日均存款,指标值,2,983,333.33' 直接把整个解析打成失败。改用不可出现在实体名里的 \x1f。
TRIPLE_SEP = "\x1f"

# 业务类型表（v1）：与知识库的 graphPrompt/entity_types 同口径，作为"合法类型"白名单
_BUILTIN_ALLOWED_TYPES = [
    "机构", "客户", "产品", "金额", "期限", "指标", "日期",
    "业务动作", "单证", "条款", "评级", "地点", "担保", "编号", "口径", "其他",
]


def _load_contract_types():
    """从 contracts/ontology 读受控类型表（R15 W01/A01）。

    为什么：类型表原本是源码字面量，改一次要改代码、无法评审、也无法审计。
    契约是 `entity-types.v1.json`，每个码带 `legacy`（现有中文名）与 `label`；
    白名单取 `legacy or label`，**保持中文**，避免改动下游已入库的 v.type 取值。

    健壮性：向上最多找 6 级目录；找不到/解析失败一律回退内置 16 类，
    不允许因为契约文件缺失导致服务起不来（部署路径与开发路径不同）。
    返回 (types, source_path, reason)。
    """
    import os as _os
    here = _os.path.dirname(_os.path.abspath(__file__))
    for _ in range(6):
        cand = _os.path.join(here, "contracts", "ontology", "entity-types.v1.json")
        if _os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as fh:
                    spec = json.load(fh)
                names = []
                for t in spec.get("types", []):
                    nm = (t.get("legacy") or t.get("label") or "").strip()
                    if nm and nm not in names:
                        names.append(nm)
                if names:
                    return names, cand, "contract"
                return list(_BUILTIN_ALLOWED_TYPES), cand, "contract_empty_types"
            except Exception as e:  # noqa: BLE001
                return list(_BUILTIN_ALLOWED_TYPES), cand, f"contract_invalid:{e}"
        here = _os.path.dirname(here)
    return list(_BUILTIN_ALLOWED_TYPES), "", "contract_not_found"


ALLOWED_TYPES, _TYPES_SOURCE, _TYPES_REASON = _load_contract_types()
# 此处是模块级导入期，业务 logger 还没就绪，用标准 logging 记录来源（可 grep 定位兜底是否生效）
logging.getLogger(__name__).info(
    f"类型白名单来源={_TYPES_REASON} 共{len(ALLOWED_TYPES)}类 path={_TYPES_SOURCE}")


# ─────────────────────────────────────────────────────────────────────────────
# R15 / T-B01：关系本体契约（symmetric + domain/range）
#
# 缺陷（外部评审 B01，graph_types.py:283 起）：pair_key 用 sorted() 把端点对一律当无序，
# `甲 -担保-> 乙` 与 `乙 -担保-> 甲` 落成同一个键，只留**先到者** ——
# 两条不同的业务事实被压成一条，且丢哪条取决于抽取顺序（不可复现、不可审计）。
#
# 修法：方向语义由本体声明，不由代码猜。
#   · symmetric=true（当前只有 相似/关联）→ 同一事实的两种写法，用无序键去重；
#   · symmetric=false 且 domain/range 可判定 → 方向由端点类型裁决，反向即伪反向边；
#   · 谓词未登记 / 类型未判定 / domain==range → 方向**不可裁决**，两个方向都保留，
#     记 direction_unresolved 审计，不静默合并（不可裁决 ≠ 重复）。
# 无向键降级为"拓扑投影专用"（undirected_pair_key：社区/相似边/连通分量），
# 不再充当业务事实身份 —— 这就是评审要求的"无向投影仅供社区，不回写业务事实"。
# ─────────────────────────────────────────────────────────────────────────────

def _load_relations_contract():
    """读 contracts/ontology/relations.v1.json：每个谓词的 symmetric/domain/range/aliases。

    返回 (relations, source_path, reason)；relations = {name: {symmetric, domain, range, aliases}}。

    健壮性：找不到/解析失败一律返回空表。空表意味着"所有谓词都按有向且方向不可裁决处理"，
    即**不合并任何方向** —— 宁可多留一条候选，也不把两条事实压成一条。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        cand = os.path.join(here, "contracts", "ontology", "relations.v1.json")
        if os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as fh:
                    spec = json.load(fh)
                rels = {}
                for r in spec.get("relations", []):
                    nm = (r.get("name") or "").strip()
                    if not nm:
                        continue
                    rels[nm] = {
                        "symmetric": bool(r.get("symmetric")),
                        "domain": (r.get("domain") or "").strip(),
                        "range": (r.get("range") or "").strip(),
                        "aliases": [a.strip() for a in (r.get("aliases") or []) if str(a).strip()],
                    }
                return rels, cand, ("contract" if rels else "contract_empty_relations")
            except Exception as e:  # noqa: BLE001
                return {}, cand, f"contract_invalid:{e}"
        here = os.path.dirname(here)
    return {}, "", "contract_not_found"


def _load_type_codes():
    """读 entity-types.v1.json，得到 {中文名/别名 -> code}，供 domain/range 比对。

    取 legacy / label / aliases 三个来源，均映射到 code；冲突时先到者优先（确定性）。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        cand = os.path.join(here, "contracts", "ontology", "entity-types.v1.json")
        if os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as fh:
                    spec = json.load(fh)
                out = {}
                for t in spec.get("types", []):
                    code = (t.get("code") or "").strip()
                    if not code:
                        continue
                    for nm in [t.get("legacy"), t.get("label")] + list(t.get("aliases") or []):
                        nm = (nm or "").strip()
                        if nm:
                            out.setdefault(nm, code)
                return out
            except Exception:  # noqa: BLE001
                return {}
        here = os.path.dirname(here)
    return {}


RELATIONS, _REL_SOURCE, _REL_REASON = _load_relations_contract()
SYMMETRIC_RELATIONS = frozenset(n for n, s in RELATIONS.items() if s.get("symmetric"))
_REL_ALIAS_TO_NAME = {}
for _rel_name, _rel_spec in RELATIONS.items():
    _REL_ALIAS_TO_NAME[_rel_name] = _rel_name
    for _alias in _rel_spec.get("aliases") or []:
        _REL_ALIAS_TO_NAME.setdefault(_alias, _rel_name)
_TYPE_CODE_BY_NAME = _load_type_codes()

logging.getLogger(__name__).info(
    f"关系本体来源={_REL_REASON} 共{len(RELATIONS)}个谓词 对称谓词={sorted(SYMMETRIC_RELATIONS)} "
    f"path={_REL_SOURCE}；类型码映射{len(_TYPE_CODE_BY_NAME)}项")


def relation_spec(rel):
    """按契约取谓词本体声明；未登记返回 None（别名先归一到契约名）。"""
    name = _REL_ALIAS_TO_NAME.get(clean_name(rel))
    return RELATIONS.get(name) if name else None


def canonical_relation(rel):
    """谓词归一到契约名（仅用于本体判定，不在此处改写落库数据）。"""
    s = clean_name(rel)
    return _REL_ALIAS_TO_NAME.get(s, s)


def is_symmetric_relation(rel):
    """契约显式声明 symmetric=true 才算对称；未登记一律按**有向**处理（保守）。"""
    spec = relation_spec(rel)
    return bool(spec and spec.get("symmetric"))


def direction_determinable(rel):
    """方向能否由本体裁决。返回 (bool, reason)。"""
    spec = relation_spec(rel)
    if spec is None:
        return False, "predicate_unregistered"
    if spec.get("symmetric"):
        return False, "symmetric"
    dom, rng = spec.get("domain") or "", spec.get("range") or ""
    if not dom or not rng or "*" in (dom, rng):
        return False, "domain_range_wildcard"
    if dom == rng:
        return False, "domain_eq_range"
    return True, "domain_range"


def type_code_of(entity_type):
    """实体类型（图中存的中文 legacy 名）→ 契约 code；未判定/兜底类返回 None。"""
    t = clean_name(entity_type)
    if not t:
        return None
    code = _TYPE_CODE_BY_NAME.get(t)
    if code in (None, "unknown", "other"):
        return None
    return code


def resolve_direction(rel, src_type, dst_type):
    """按 domain/range 判定这条边的方向是否成立。

    返回 "forward"（当前方向成立）/ "reverse"（反向才成立）/ "unknown"（不可裁决）。
    只看端点类型，不看先后顺序 —— 这是 B01 与旧实现（sorted() + 先到者）的根本差别。
    """
    ok, _why = direction_determinable(rel)
    if not ok:
        return "unknown"
    spec = relation_spec(rel)
    sc, dc = type_code_of(src_type), type_code_of(dst_type)
    if not sc or not dc:
        return "unknown"
    fwd = (sc == spec.get("domain") and dc == spec.get("range"))
    rev = (sc == spec.get("range") and dc == spec.get("domain"))
    if fwd and not rev:
        return "forward"
    if rev and not fwd:
        return "reverse"
    return "unknown"

# 规则推断：LLM 没给出合法类型时，按名称形态兜底
RULES = [
    ("金额", re.compile(r"(人民币)?\s*[\d,.]+\s*(万元|亿元|元)")),
    ("日期", re.compile(r"^\d{4}[-/年]\d{1,2}([-/月]\d{1,2})?日?$")),
    ("期限", re.compile(r"^[一二三四五六七八九十百\d]+\s*(个工作日|个工作日|个月|年|天|日)$")),
    ("评级", re.compile(r"^(AAA|AA|A|BBB|BB|B|CCC|CC|C)$")),
    ("指标", re.compile(r"(率|占比|额度|余额|存款|用电量|同比|环比|天数|金额)$")),
    ("单证", re.compile(r"^[A-Z]{1,4}-[A-Z]{2,}-\d+")),
    ("机构", re.compile(r"(公司|集团|银行|中心|工厂|厂|企业|机构|研究院|大学)$")),
    ("地点", re.compile(r"(省|市|区|县|镇|街道|北方|南方|东方|西方|华东|华南|华北|华中|东北|西南|西北|长三角|珠三角)$")),
    ("担保", re.compile(r"(抵押|质押|保证|担保|信用方式|信用贷)")),
    ("编号", re.compile(r"^[A-Z]{2,}-[A-Z0-9-]+$")),
    ("口径", re.compile(r"(口径|跨账户|汇总|折算|加点幅度|加点)")) ,
    ("条款", re.compile(r"(等额本息|等额本金|按月付息|按季付息|到期还本|分期还本|先息后本)")),
    ("评级", re.compile(r"^(正常|关注|次级|可疑|损失)$")),
    ("时间", re.compile(r"(月度|季度|年度|月度同比|环比|旬|周|本期|上期|当期)$")),
    ("产品", re.compile(r"(贷|票据|贴现|保理|理财|存款|险|手机|设备|装备|终端|系统|平台|软件)$")),
]

# 明确不是实体的结构性词 / 表头词 / 通用词
STOPWORDS = {
    "下表", "上表", "表格", "表头", "table", "document", "docx", "xlsx", "pptx", "pdf",
    "文本", "内容", "数据", "天数", "业务日", "序号", "备注", "合计", "小计", "单位",
    "无", "其他", "如下", "上述", "以上", "以下", "说明",
    # R15/A01：原先把"正常"当停用词，但 RULES 又把它判为评级(grade) ——
    # 结果"正常"这个合法风险分类永远进不了图。停用词只收结构性词，业务取值交给类型体系。
    # R14-LIVE-15：业务实体词不能当停用词。
    # 原实现把 客户/用户/供应商/公司/企业/项目/产品/申请人/借款人 一并过滤，
    # 而贷款知识库的主实体恰恰是"客户/产品/借款人"；过滤掉它们，
    # 以它们为端点的三元组会被 normalize 整条丢弃（src/dst 不在 name_map 就 drop）。
    # 只保留真正的结构性词（下表/合计/单位/序号…），业务名词交给类型体系判定。
    # R14-M1-R1（TL 2026-10-27 批准）：单位词与泛指标词不该成为实体。
    # 实测 g_kb_9 里 `万元`、`额度`、`已用额度` 都成了节点，`万元` 更是纯单位。
    "万元", "亿元", "元", "个基点", "基点", "BP", "额度", "额度上限", "已用额度",
}

RULE_DATE = re.compile(r"^\d{4}[-/年]\d{1,2}([-/月]\d{1,2})?日?$")
RULE_AMOUNT = re.compile(r"(人民币)?\s*[\d,.]+\s*(万元|亿元|元)")
DOC_TITLE = re.compile(r"^(docx|xlsx|pptx|pdf|word|excel)[\s_\-.]*", re.I)
CJK_OR_ALNUM = re.compile(r"[\u4e00-\u9fa5A-Za-z0-9]")
PURE_NUMBER = re.compile(r"^[\d,.\-%]+$")
# R14-LIVE-15：金额型纯数字（千分位或两位小数）不丢。
# 实测：模型抽出 ("relationship"::金额::日均存款::2,983,333.33::...) 时把"元"省掉了，
# PURE_NUMBER 判成纯数字 -> 该实体被过滤 -> 以它为端点的三元组整条丢弃 -> 全库 0 条图数据。
# 判断依据是"长得像金额"（有千分位或固定两位小数），不是"包含数字"，避免把年份/序号也放进来。
AMOUNT_LIKE = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$|^\d+\.\d{2}$")
COMPANY_SUFFIX = re.compile(r"(股份有限公司|有限责任公司|有限公司|集团有限公司|集团|公司|银行|中心)$")

_ALIAS_CACHE = None


def _alias_file():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "alias_map.json")


def load_alias_map():
    """别名表（可选）：{"别名": "标准名"}，缺失时返回空表，不影响主链。"""
    global _ALIAS_CACHE
    if _ALIAS_CACHE is not None:
        return _ALIAS_CACHE
    path = _alias_file()
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                _ALIAS_CACHE = {str(k).strip(): str(v).strip() for k, v in json.load(f).items()}
        except Exception:
            _ALIAS_CACHE = {}
    else:
        _ALIAS_CACHE = {}
    return _ALIAS_CACHE


def clean_name(name):
    if name is None:
        return ""
    s = str(name).strip()
    s = s.strip("\"'“”‘’《》<>()（）[]【】")
    s = re.sub(r"\s+", "", s)
    return s


def sentence_like(s):
    """R15-W09：整句被当成实体。

    实测脏样例（kb_9 现网）：
        "放款是智造贷办理流程的一部分"
        "制造业中小微企业是智造贷的适用对象"
        "审批是办理流程的一部分"
        "信用部分的最高额度为1000万元"
        "8000万元中的信用部分不超过1000万元"
    这些是三元组/整句被反序列化成了实体，进图后既不能参与推理，
    又把社区摘要污染成"一句话一个节点"。它不是"实体名长"的问题，
    而是**含判断/关系谓语**，所以不能只靠长度阈值。

    判定：短名放行（<=8 字基本是专名）；否则要求同时出现
      · 关系/判断词（是/为/属于/包括/包含/不超过/需要）
      · 限定语尾（的/之一/一部分/对象/额度/上限/条件/环节/周期）
    或长于 14 字且带限定语（覆盖"信用部分最高额度为1000万元，不超过8000万元"）。
    """
    if len(s) <= 8:
        return False
    has_pred = re.search(r"(是|为|属于|包括|包含|不超过|需要|应当|提出|申请)", s)
    # 限定语尾：重解析 343 后仍漏出"办理流程包含评级授信步骤""提前十五个工作日提出书面申请"，
    # 说明原尾词表太窄（缺 步骤/书面/时限/工作日 这类），按实测补全。
    has_mod = re.search(r"(的|之一|一部分|对象|额度|上限|条件|环节|周期|范围|步骤|时限|书面|申请|规定|要求)", s)
    if has_pred and has_mod:
        return True
    # 长句兜底：>=12 字且含限定语（原为 >14，漏掉 14 字整句）
    return len(s) >= 12 and bool(re.search(r"(的|不超过|最高|步骤|申请|时限)", s))


def is_valid_entity(name):
    """过滤纯数字、纯符号、结构词、过短/过长。返回 (bool, reason)。"""
    s = clean_name(name)
    if not s:
        return False, "empty"
    if s.lower() in STOPWORDS:
        return False, "stopword"
    # R15-W09：句子判定必须在金额/日期放行**之前**。
    # "8000万元中的信用部分不超过1000万元" 开头就是合法金额，会被 RULE_AMOUNT.match
    # 提前放行，从而绕过句子过滤（实测就漏了这一类）。
    if sentence_like(s):
        return False, "sentence_entity"
    # 日期要保留（是业务实体），不能因为形如数字带连字符被当成纯数字过滤
    if RULE_DATE.match(s) or RULE_AMOUNT.match(s):
        return True, ""
    if AMOUNT_LIKE.match(s):
        return True, ""
    if PURE_NUMBER.match(s):
        return False, "pure_number"
    # 文档标题/文件名不该成为实体（如 "DOCX with table"、"xxx.xlsx"）
    if DOC_TITLE.match(s):
        return False, "doc_title"
    # 测试夹具 / 样本名不应成为业务实体（避免验收数据污染图谱）
    if re.search(r"(测试夹具|夹具|测试样本|fixture|样例|sample)", s, re.I):
        return False, "test_fixture"
    if not CJK_OR_ALNUM.search(s):
        return False, "no_alnum"
    if len(s) < 2:
        return False, "too_short"
    if len(s) > 30:
        return False, "too_long"
    return True, ""


def infer_type(name, llm_type):
    """优先采用 LLM 给出的合法类型；否则按规则推断；都不中则 unclassified。"""
    t = clean_name(llm_type)
    if t in ALLOWED_TYPES and t not in ("其他",):
        return t, "llm"
    for type_name, pattern in RULES:
        if pattern.search(clean_name(name)):
            return type_name, "rule"
    return "unclassified", "none"


NUMERIC_PREFIX = re.compile(r"^(人民币|加|减)\s*")


def numeric_canon(name):
    """R2（收窄版，TL 2026-10-27 批准）：只去 `人民币/加/减` 前缀，**不吃掉语义限定**。

    例：`人民币5000万元 -> 5000万元`、`加30个基点 -> 30个基点`。
    刻意**不**处理 `信用部分不超过1000万元` 这类带语义限定的写法（R3 的事）。
    返回 (canonical, 是否发生归一)。
    """
    s0 = clean_name(name)
    if not RULE_AMOUNT.search(s0) and not re.search(r"(个基点|基点|BP|bp)$", s0):
        return s0, False
    s1 = NUMERIC_PREFIX.sub("", s0)
    return (s1, True) if s1 and s1 != s0 else (s0, False)


def canonical_of(name, all_names, alias_map=None):
    """
    canonical 归一（确定性规则）：
      1) 命中别名表 -> 用标准名；
      2) 名称是另一实体名的严格前缀，且后者带公司/机构后缀 -> 归到后者（长名优先）。
    其余保持自身。
    """
    s = clean_name(name)
    alias_map = alias_map if alias_map is not None else load_alias_map()
    if s in alias_map:
        return alias_map[s]
    candidates = []
    for other in all_names:
        o = clean_name(other)
        if o == s or not COMPANY_SUFFIX.search(o):
            continue
        if o.startswith(s) and len(o) > len(s):
            candidates.append(o)
    if candidates:
        # 取最短的合法全称，避免一路并到过长的复合名
        return sorted(candidates, key=len)[0]
    return s


# ─────────────────────────────────────────────────────────────────────────────
# R15-W02 / A02：反向重复判定（跨写入批次可见）
#
# 问题：`normalize_graph_data` 里的 `dropped_reverse` 只在**本次调用的内存**里生效
# （seen_pairs 是局部 set）。落库侧 `graph_service.batch_insert_vertex` 不做任何
# 已有数据回读，`_edge_rank(src,rel,dst)` 又把方向算进 rank —— 于是
# `1年期LPR -利率基准-> 智造贷` 与 `智造贷 -利率基准-> 1年期LPR` 是两个 rank，
# 两条都能 INSERT 成功、show_flag 都是 1（实测 g_kb_9，两条 file_id 都是 343）。
# 只要"写这批"与"写那批"不是同一次 normalize 调用，内存去重就永远看不见对方。
#
# 因此把判定抽成可复用纯函数：调用方（graph_service）在**写入前**把存储里已存在的
# 三元组索引传进来，由本模块判定"这条是不重复/是重复"，本模块不认识 Nebula/Milvus。
#
# R15/T-B01：键的粒度从"一律无序"改为"按本体分流"（见文件上方 B01 说明）。
# ─────────────────────────────────────────────────────────────────────────────

PAIR_KEY_SCHEME = "b01-ontology-directed-v1"


def undirected_pair_key(rel, src, dst):
    """(谓词, 无序端点对) —— **只用于拓扑投影**：社区 / 相似边 / 连通分量。

    不要拿它当业务事实身份：`甲 -担保-> 乙` 与 `乙 -担保-> 甲` 在拓扑上相邻，
    业务上却是两条事实。写事实账本必须用 pair_key。
    """
    return (canonical_relation(rel), tuple(sorted((clean_name(src), clean_name(dst)))))


def pair_key(rel, src, dst):
    """业务事实身份（R15/T-B01）。

    - 对称谓词（契约 symmetric=true，当前只有 相似/关联）：无序端点对，
      `A 相似 B` 与 `B 相似 A` 是同一事实的两种写法；
    - 其余谓词：**有向**。方向对不对由 resolve_direction 按 domain/range 裁决，
      不由 sorted() 把方向抹掉 —— 抹掉就会把"甲担保乙"与"乙担保甲"压成一条（B01）。
    - 未登记谓词一律按有向处理：宁可多留一条候选，也不静默丢一条事实。
    """
    r = canonical_relation(rel)
    a, b = clean_name(src), clean_name(dst)
    if is_symmetric_relation(rel):
        return (r, tuple(sorted((a, b))))
    return (r, (a, b))


def _iter_triples(existing_pairs):
    """把多种形态的"已有三元组"摊平成 (src, rel, dst)。

    接受：
      - 三元组序列  [(src, rel, dst), ...] / [[src, rel, dst], ...]
      - 字典行      {"src|source": .., "rel|relationship": .., "dst|dest": ..}
      - 已构建键    {(rel, (a, b)), ...}（幂等，可反复传入）
    形态无法识别时抛 ValueError（fail-closed，见 as_pair_index 说明）。
    """
    for item in existing_pairs or []:
        if isinstance(item, dict):
            src = item.get("src", item.get("source"))
            rel = item.get("rel", item.get("relationship"))
            dst = item.get("dst", item.get("dest", item.get("target")))
        elif isinstance(item, (tuple, list)):
            if len(item) == 3:
                src, rel, dst = item[0], item[1], item[2]
            elif len(item) == 2 and isinstance(item[1], (tuple, list, set, frozenset)):
                # 已是键形态：(rel, (a, b))
                rel, ends = item[0], tuple(item[1])
                if len(ends) != 2:
                    raise ValueError(f"pair 索引端点不是 2 个: {item!r}")
                src, dst = ends[0], ends[1]
            else:
                raise ValueError(f"无法识别的已有三元组形态: {item!r}")
        else:
            raise ValueError(f"无法识别的已有三元组形态: {item!r}")
        if rel is None or src is None or dst is None:
            raise ValueError(f"已有三元组缺字段(src/rel/dst): {item!r}")
        yield src, rel, dst


def as_pair_index(existing_pairs):
    """把已有三元组统一成**有向**事实键索引（set of pair_key）。

    刻意 **fail-closed**：遇到无法识别的元素直接抛 ValueError，而不是跳过。
    理由：静默跳过会让索引变空 -> 去重全程空转却仍报"去重已启用"，
    正是本项目反复出现的"假绿"形态（断言恒真、门禁全绿而结论为空）。
    """
    return {pair_key(rel, src, dst) for src, rel, dst in _iter_triples(existing_pairs)}


def as_undirected_index(existing_pairs):
    """拓扑投影用的无序索引。只服务"同谓词反向是否已存在"这一判断，不写回事实账本。"""
    return {undirected_pair_key(rel, src, dst) for src, rel, dst in _iter_triples(existing_pairs)}


def is_reverse_duplicate(src, rel, dst, existing_pairs):
    """这条三元组是否**已是既有事实**（不是"同无序对"就算）。

    判定分三种（R15/T-B01）：
      1) 有向键命中 -> 同一事实同一方向，重复；
      2) 对称谓词 -> 有向键本身就是无序键，已由 1) 覆盖；
      3) 非对称且方向可由 domain/range 裁决、无序对已存在 -> 反向是**伪反向边**，算重复；
      4) 非对称但方向不可裁决（未登记谓词/domain==range/通配）-> 反向是**另一条事实**，
         不算重复（"甲担保乙"与"乙担保甲"必须都在）。
    """
    if not existing_pairs:
        return False
    if isinstance(existing_pairs, (set, frozenset)):
        # set 里可能是已构建的键（2 元组），也可能是原始三元组（3 元组）
        first = next(iter(existing_pairs), None)
        if first is not None and len(first) == 2:
            if pair_key(rel, src, dst) in existing_pairs:
                return True
            if not direction_determinable(rel)[0]:
                return False
            return undirected_pair_key(rel, src, dst) in existing_pairs
    if pair_key(rel, src, dst) in as_pair_index(existing_pairs):
        return True
    if not direction_determinable(rel)[0]:
        return False
    return undirected_pair_key(rel, src, dst) in as_undirected_index(existing_pairs)


def build_pair_index(triples):
    """从三元组序列构建**有向**事实索引（写入前给 filter_reverse_duplicates 用）。"""
    return as_pair_index(triples)


def filter_reverse_duplicates(triples, existing_pairs=None):
    """写入前过滤"同一事实"，返回 (kept, skipped)。

    - existing_pairs：存储里已存在的三元组 / 键（跨批次）；不传等价于"只去批内重复"。
    - skipped 原样返回被跳过的三元组，供调用方记录/审计，**不静默丢弃**。

    R15/T-B01：不再"同无序对一刀切"。只有**方向可由本体裁决**的谓词，
    才把反向视作同一事实；未登记谓词（如"担保"）或 domain==range 的谓词，
    正反两个方向是两条事实，都保留 —— 否则互相担保这类事实会被丢掉一条。
    """
    seen_directed = as_pair_index(existing_pairs)
    seen_undirected = as_undirected_index(existing_pairs)
    kept, skipped = [], []
    for triple in triples or []:
        try:
            src, rel, dst = triple[0], triple[1], triple[2]
        except Exception:
            kept.append(triple)   # 形态不合法的交给下游既有校验，不在这里吞掉
            continue
        key = pair_key(rel, src, dst)
        if key in seen_directed:
            skipped.append(triple)
            continue
        if direction_determinable(rel)[0] and undirected_pair_key(rel, src, dst) in seen_undirected:
            skipped.append(triple)
            continue
        seen_directed.add(key)
        seen_undirected.add(undirected_pair_key(rel, src, dst))
        kept.append(triple)
    return kept, skipped


# ─────────────────────────────────────────────────────────────────────────────
# R15-W02 / A03+A09：总额/最高 类谓词不得被"分项值"冒充
#
# 实测（g_kb_9，file_id=343，同一 chunk）：
#   智造贷 -最高额度-> 8000万元
#   智造贷 -最高额度-> 1000万元        ← 原文是"8000万元（信用部分不超过1000万元）"
# 两条 show_flag 都是 1，于是任何按 (主体, 谓词) 取值的地方都会撞上互斥双值；
# 答案层即使把两者配对输出，存储层仍然是"两个最高额度"。
#
# 处理顺序（确定性、可解释、不丢事实优先）：
#   规则 A（端点自证）：端点含"信用/分项/其中/部分/单项/专项"等强分项标记
#                       -> 关系名改写为分项谓词（信用方式上限 / 分项上限）。
#   规则 B（数值裁决）：同一 (主体, 总额类谓词) 出现 ≥2 个不同金额值
#                       -> 最大值保留为总额，其余（必然是分项）改写为分项谓词。
# 两条规则都**只改关系名，不改端点、不改方向、不丢三元组**，全部写进 report。
# ─────────────────────────────────────────────────────────────────────────────

# "总额/最高"类谓词的语义域：额度、授信、金额、规模、敞口
TOTAL_PREDICATE_DOMAIN = re.compile(r"(额度|授信|金额|规模|敞口)")
# 同一语义域里表示"总额/上限"的词
TOTAL_PREDICATE_HEAD = re.compile(r"(最高|总额|最大|上限|不超过)")
# 强分项标记：出现即足以判定"这是分项，不是总额"。
# 刻意**不**把裸"不超过"放进来 —— "不超过8000万元"本身可以是总额（上限语义），
# 单靠它判定会把总额误改成"分项上限"，属于用规则制造错误事实。
ITEM_STRONG_MARKERS = re.compile(r"(信用|分项|其中|部分|单项|专项)")
AMOUNT_PARSE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(亿元|万元|元)")
_AMOUNT_UNIT = {"亿元": 100000000.0, "万元": 10000.0, "元": 1.0}

ITEM_PREDICATE_CREDIT = "信用方式上限"
ITEM_PREDICATE_GENERIC = "分项上限"


def is_total_predicate(rel):
    """关系名是否"总额/最高"类谓词（语义上单值，不允许第二个值并存）。"""
    s = clean_name(rel)
    if not s:
        return False
    return bool(TOTAL_PREDICATE_DOMAIN.search(s)) and bool(TOTAL_PREDICATE_HEAD.search(s))


def parse_amount(text):
    """把"8000万元 / 1,000万元 / 3亿元"解析成以"元"为单位的浮点；解析不到返回 None。"""
    s = clean_name(text)
    m = AMOUNT_PARSE.search(s)
    if not m:
        return None
    try:
        value = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    return value * _AMOUNT_UNIT[m.group(2)]


def item_predicate_of(text):
    """端点文本若自证是"分项"，返回对应分项谓词名；否则返回空串。"""
    s = clean_name(text)
    if not s or not ITEM_STRONG_MARKERS.search(s):
        return ""
    return ITEM_PREDICATE_CREDIT if "信用" in s else ITEM_PREDICATE_GENERIC


def split_total_predicate(triples):
    """把"总额谓词吞并分项"的三元组改写成分项谓词。

    返回 (new_triples, conflicts, rel_map)：
      - new_triples：与输入等长（只改关系名，顺序/端点/方向不变）
      - conflicts：每处改写的审计记录（含触发规则、数值证据）
      - rel_map：{(src, 旧rel, dst): 新rel}，供 triples_source 的键同步改写
    """
    triples = list(triples or [])
    new_rel_of = {}
    conflicts = []

    # 规则 A：端点自证分项
    for idx, (src, rel, dst) in enumerate(triples):
        if not is_total_predicate(rel):
            continue
        item_rel = item_predicate_of(dst) or item_predicate_of(src)
        if not item_rel or item_rel == rel:
            continue
        _hit = ITEM_STRONG_MARKERS.search(clean_name(dst)) or ITEM_STRONG_MARKERS.search(clean_name(src))
        new_rel_of[idx] = item_rel
        conflicts.append({
            "src": src, "rel": rel, "dst": dst, "new_rel": item_rel,
            "rule": "item_marker", "action": "rewrite",
            "reason": f"端点自证分项（标记={_hit.group(1) if _hit else ''}）",
        })

    # 规则 B：同一 (主体, 总额谓词) 多值 -> 最大值是总额，其余是分项
    groups = {}
    for idx, (src, rel, dst) in enumerate(triples):
        if idx in new_rel_of or not is_total_predicate(rel):
            continue
        src_val, dst_val = parse_amount(src), parse_amount(dst)
        if dst_val is not None and src_val is None:
            subject, value = src, dst_val
        elif src_val is not None and dst_val is None:
            subject, value = dst, src_val
        else:
            # 两端都是金额（值的值）或都不是金额 -> 不做数值裁决，避免瞎猜
            continue
        groups.setdefault((subject, rel), []).append((idx, value))

    for (subject, rel), members in groups.items():
        values = {round(v, 2) for _i, v in members}
        if len(values) < 2:
            continue
        total = max(values)
        for idx, value in members:
            if round(value, 2) == total:
                continue
            src, _r, dst = triples[idx]
            item_rel = item_predicate_of(dst) or item_predicate_of(src) or ITEM_PREDICATE_GENERIC
            if item_rel == rel:
                continue
            new_rel_of[idx] = item_rel
            conflicts.append({
                "src": src, "rel": rel, "dst": dst, "new_rel": item_rel,
                "rule": "value_conflict", "action": "rewrite",
                "reason": f"同主体同总额谓词出现 {len(values)} 个金额值，最大值 {total:,.0f} 元保留为总额",
            })

    if not new_rel_of:
        return triples, conflicts, {}

    rel_map = {}
    out = []
    for idx, (src, rel, dst) in enumerate(triples):
        new_rel = new_rel_of.get(idx, rel)
        if new_rel != rel:
            rel_map[(clean_name(src), clean_name(rel), clean_name(dst))] = new_rel
        out.append((src, new_rel, dst))
    return out, conflicts, rel_map


def normalize_graph_data(triples_data_list, entity_source_dict, triples_source_dict,
                         existing_pairs=None):
    """
    返回 (triples, entities, triples_source, report)。
    report 里带 schema_version、被过滤实体及原因、合并映射、未分类实体。

    existing_pairs（R15-W02，可选）：存储里**已存在**的三元组（跨写入批次），
    形态见 as_pair_index()。传入后，与本批共用同一套"本体分流"判定
    （R15/T-B01：对称谓词按无序对判重；非对称谓词按 domain/range 裁决方向；
    方向不可裁决时两个方向都保留），跳过项记入 report['dropped_reverse_existing'] /
    report['reverse_dup_skipped']，方向判定明细记入 spurious_direction /
    direction_conflict / direction_unresolved。
    不传时等价于"只做批内去重"，调用方无需改动即可保持兼容。
    """
    alias_map = load_alias_map()
    raw_names = [n for n, v in entity_source_dict.items() if v.get("entity_type") == "1"]

    kept, filtered, merged, unclassified = {}, [], {}, []
    name_map = {}
    norm_rule_of = {}

    for name in raw_names:
        ok, reason = is_valid_entity(name)
        if not ok:
            filtered.append({"name": clean_name(name), "reason": reason})
            continue
        raw_clean = clean_name(name)
        canon = canonical_of(name, raw_names, alias_map)
        rule = "alias_or_company_prefix" if canon != raw_clean else ""
        # R2（收窄版）：只去 人民币/加/减 前缀
        num_canon, changed = numeric_canon(canon)
        if changed:
            canon, rule = num_canon, "numeric_prefix"
        name_map[name] = canon
        norm_rule_of[name] = rule
        if raw_clean != canon:
            merged[raw_clean] = canon

    # 合并实体属性（title / file_id / e_type 取并集），类型冲突时保留首个已判定类型
    for name, canon in name_map.items():
        raw_clean = clean_name(name)   # 每轮重算，不能用上一个循环的残留值
        src = entity_source_dict[name]
        if canon not in kept:
            # 保留原字典的**全部**字段（chunk_pk_list / e_type / title / file_id ...），
            # 只对列表型字段做并集，避免下游因缺字段 KeyError。
            bucket = {k: (list(v) if isinstance(v, list) else v) for k, v in src.items()}
            bucket["entity_type"] = "1"
            kept[canon] = bucket
            # R14-M1-R4（TL 批准）：保留原始 mention 与归一痕迹，可审计、可回滚。
            bucket["norm_rule"] = norm_rule_of.get(name, "")
            bucket["norm_from"] = raw_clean if raw_clean != canon else ""
            bucket["mentions"] = [{"text": raw_clean,
                                   "chunk_pk": list(src.get("chunk_pk_list") or []),
                                   "file_id": src.get("file_id", ""),
                                   "title": src.get("title", "")}]
        else:
            bucket = kept[canon]
            for key, val in src.items():
                if key == "entity_type":
                    continue
                if isinstance(val, list):
                    bucket.setdefault(key, [])
                    for v in val:
                        if v not in bucket[key]:
                            bucket[key].append(v)
                else:
                    bucket.setdefault(key, val)
            # 归一痕迹要落在 canonical 顶点上（R4 可审计）：取本批未记录的规则/原名
            _rule = norm_rule_of.get(name, "")
            if _rule and not bucket.get("norm_rule"):
                bucket["norm_rule"] = _rule
            if raw_clean != canon and not bucket.get("norm_from"):
                bucket["norm_from"] = raw_clean
            # 同一 canonical 的其它原始写法也要留 mention（R4）
            mentions = bucket.setdefault("mentions", [])
            if raw_clean != canon and all(m.get("text") != raw_clean for m in mentions):
                mentions.append({"text": raw_clean,
                                 "chunk_pk": list(src.get("chunk_pk_list") or []),
                                 "file_id": src.get("file_id", ""),
                                 "title": src.get("title", "")})
        # 类型推断
        llm_type = next((t for t in bucket["e_type"] if t), "")
        typ, source = infer_type(canon, llm_type)
        # R15/A04：金额必须有单位。实测 xlsx 表格里的 "2,983,333.33"（单位在表头"元"）
        # 被标成"金额"直接进图 → A04 的"裸数字金额"反例。
        # 无单位数值本身是有效指标值，不丢弃，但不允许冒充金额（否则 A03 的
        # "总额度/分项"比对会把它当成一个额度取值）。
        if typ == "金额" and not RULE_AMOUNT.search(canon):
            typ, source = "unclassified", "amount_without_unit"
        bucket["e_type"] = [typ]
        if typ == "unclassified":
            unclassified.append(canon)

    # 重写三元组
    new_triples = []
    dropped_triples = 0
    dropped_junk = 0

    def _clean_rel(rel):
        """R15-A17：关系名里塞了箭头时，取箭头前的谓词主体，而不是丢掉整条事实。

        实测（A17 夹具，同一段 129 字文本、同一模型）：
          不注入时模型输出 '星航贷AAA档 -[加点幅度对应]-> 30个基点'  → 保留，3 档齐全
          注入时  模型输出 '星航贷AAA档 -[加点幅度->加30个基点]-> 30个基点' → 含 "->"，
                  被原 _junk 整条丢弃 → 3 档加点全部消失，该文件最终只剩 1 条边
        差别只在模型表述的随机性，不该由它决定一条业务事实的存亡。
        所以：先清洗成 '加点幅度'，清洗后仍然脏（含逗号/过长）才丢弃。
        """
        if "->" in rel:
            head = rel.split("->", 1)[0].strip()
            if head:
                return head
        return rel

    def _junk(rel, a, b):
        """R15 W01：明显不是三元组形态的抽取产物。

        实测脏样例：'1000万元 -[最高额度-信用部分不超过->8000万元]-> 信用部分最高额度为1000万元…'
        特征：关系名里塞了值/箭头/逗号，或实体名是整句话。
        箭头已在 _clean_rel 里处理；这里只拦清洗后仍然不可用的。
        """
        if "，" in rel or "," in rel or len(rel) > 20:
            return True
        if len(a) > 30 or len(b) > 30:
            return True
        return False

    for td in triples_data_list:
        try:
            src, rel, dst = clean_name(td[0]), clean_name(td[1]), clean_name(td[2])
        except Exception:
            dropped_triples += 1
            continue
        # 先判形态再判实体：垃圾条目通常连实体都不合法，
        # 若先判实体，审计里会被记成"实体未登记"，掩盖真正原因（关系名塞值/实体是整句）。
        rel = _clean_rel(rel)
        if _junk(rel, src, dst):
            dropped_junk += 1
            continue
        if src not in name_map or dst not in name_map:
            dropped_triples += 1
            continue
        src, dst = name_map[src], name_map[dst]
        if src == dst:
            dropped_triples += 1
            continue
        new_triples.append((src, rel, dst))

    # R15 W02 / A03+A09：总额/最高 类谓词不得被"分项值"冒充（改写关系名，不丢事实）。
    # 必须在逆否去重**之前**做：改写后 `最高额度->1000万元` 变 `分项上限->1000万元`，
    # 它和 `最高额度->8000万元` 不再同键，不会在下一步被误当重复丢掉。
    new_triples, predicate_conflicts, rel_map = split_total_predicate(new_triples)

    # R15 W02 + R15/T-B01：反向去重改为"本体分流"，不再"同无序对一刀切"。
    #
    # 旧实现：同 (谓词, 无序端点对) 只留先到者 —— 抽取模型把同一事实正反各输出一次时
    # 确实能挡住，但代价是 `甲 -担保-> 乙` 与 `乙 -担保-> 甲` 也被判成同一条，
    # 丢哪条取决于抽取顺序（B01）。现在按契约分流：
    #   1) 完全相同的有向三元组 -> 重复（批内 / 存量），丢；
    #   2) 对称谓词（相似/关联）-> 无序键，两种写法是同一事实，丢后者；
    #   3) 非对称 + domain/range 可裁决 -> 用端点类型判方向：
    #        · 本方向不成立            -> 伪反向边，丢（记 spurious_direction）
    #        · 本方向成立、反向在批内  -> 用本方向**替换**反向那条（保留正确方向，不增边）
    #        · 本方向成立、反向在存量  -> 不动存量（清存量另行处理），本方向丢弃并记
    #          direction_conflict，避免同一事实在库里出现两个可见方向（A02/N1）
    #   4) 非对称但方向不可裁决（谓词未登记 / 类型未判定 / domain==range / 通配）
    #        -> **两个方向都保留**，记 direction_unresolved。不可裁决 ≠ 重复。
    #
    # existing_pairs 仍只作为"已见"的预置集合（跨批次），判定口径与本批完全一致。
    _type_of = {}
    for _n, _v in kept.items():
        _et = (_v.get("e_type") or [""])
        _type_of[_n] = _et[0] if _et else ""

    def _dir_of(src, rel, dst):
        return resolve_direction(rel, _type_of.get(src, ""), _type_of.get(dst, ""))

    existing_index = as_pair_index(existing_pairs)
    existing_undirected = as_undirected_index(existing_pairs)
    seen_pairs = set(existing_index)
    seen_undirected = set(existing_undirected)
    deduped = []
    pos_of_undirected = {}          # 无序键 -> 批内已接受条目下标（供"替换伪反向"）
    dropped_reverse = 0             # 批内重复（含对称谓词两种写法）
    dropped_reverse_existing = 0    # 与存储已有事实重复（跨批次）
    symmetric_dedup = 0
    spurious_direction = []         # 伪反向边（本体判定本方向不成立）
    direction_conflict = []         # 本方向成立但存量已有反向
    direction_unresolved = []       # 方向不可裁决，两个方向都保留
    reverse_dup_skipped = []
    for src, rel, dst in new_triples:
        pair = pair_key(rel, src, dst)
        uk = undirected_pair_key(rel, src, dst)
        if pair in seen_pairs:
            _sym = is_symmetric_relation(rel)
            if pair in existing_index:
                dropped_reverse_existing += 1
            else:
                dropped_reverse += 1
            if _sym:
                # 对称谓词的有向键本身就是无序键，落到这里就是"同一事实的另一种写法"
                symmetric_dedup += 1
            if len(reverse_dup_skipped) < 50:   # 审计用，不无限增长
                reverse_dup_skipped.append({"src": src, "rel": rel, "dst": dst,
                                            "scope": ("symmetric:" if _sym else "")
                                                     + ("existing" if pair in existing_index else "batch")})
            continue

        symmetric = is_symmetric_relation(rel)
        if not symmetric and uk in seen_undirected:
            verdict = _dir_of(src, rel, dst)
            if verdict == "reverse":
                spurious_direction.append({
                    "src": src, "rel": rel, "dst": dst, "rule": "ontology_domain_range",
                    "reason": f"端点类型 {_type_of.get(src, '?')}/{_type_of.get(dst, '?')} "
                              f"不满足 {canonical_relation(rel)} 的 domain/range，本方向是伪反向边",
                })
                continue
            if verdict == "forward":
                pos = pos_of_undirected.get(uk)
                old = deduped[pos] if (pos is not None and pos < len(deduped)) else None
                if old is not None and pair_key(old[1], old[0], old[2]) == pair_key(rel, dst, src):
                    # 批内反向那条才是伪反向：换成当前（本体判定成立）的方向
                    deduped[pos] = (src, rel, dst)
                    seen_pairs.discard(pair_key(old[1], old[0], old[2]))
                    seen_pairs.add(pair)
                    spurious_direction.append({
                        "src": old[0], "rel": old[1], "dst": old[2], "rule": "ontology_domain_range",
                        "replaced_by": f"{src} -{rel}-> {dst}",
                        "reason": "批内同谓词反向；本体判定当前方向成立，反向那条是伪反向边",
                    })
                    continue
                if uk in existing_undirected:
                    direction_conflict.append({
                        "src": src, "rel": rel, "dst": dst, "scope": "existing",
                        "reason": "存量已有同谓词反方向；本方向本体判定成立，需清存量后重写",
                    })
                    continue
            if verdict == "unknown":
                direction_unresolved.append({
                    "src": src, "rel": rel, "dst": dst,
                    "why": direction_determinable(rel)[1],
                    "types": [clean_name(_type_of.get(src, "")), clean_name(_type_of.get(dst, ""))],
                })
        elif symmetric and uk in seen_undirected:
            # 理论不可达（对称谓词的 pair_key 已是无序键，会被上面的重复分支接住）。
            # 保留为显式断言式兜底：真走到这里说明 pair_key 的对称分支被改坏了。
            symmetric_dedup += 1
            dropped_reverse += 1
            if len(reverse_dup_skipped) < 50:
                reverse_dup_skipped.append({"src": src, "rel": rel, "dst": dst,
                                            "scope": "symmetric:fallback"})
            continue

        seen_pairs.add(pair)
        seen_undirected.add(uk)
        pos_of_undirected.setdefault(uk, len(deduped))
        deduped.append((src, rel, dst))
    new_triples = deduped

    # triples_source 的 key 是 "src\x1frel\x1fdst"
    new_triples_source = {}
    rel_renamed = 0
    for key, val in (triples_source_dict or {}).items():
        parts = str(key).split(TRIPLE_SEP)
        if len(parts) != 3:
            continue
        # R15 W01：这里的关系名必须和上面三元组用同一个 clean_name，
        # 否则 new_triples 用清洗后的 rel、source 却用原样 r0，键对不上 →
        # graph_service 写 Milvus 时 KeyError（实测 '放款\x1f放款期限-\x1f3个工作日'），
        # 整个解析任务 500、文件被标失败，而图数据其实已经写了一半。
        s0, r0, d0 = clean_name(parts[0]), clean_name(parts[1]), clean_name(parts[2])
        if s0 not in name_map or d0 not in name_map:
            continue
        _s, _d = name_map[s0], name_map[d0]
        # R15-W02/A03：关系名被 split_total_predicate 改写时，source 键必须同步改写，
        # 否则 graph_service 按 (src, 新rel, dst) 查 triples_attribute 查不到 ->
        # 边的 file_id/chunk_ref 变空（正是 R14-LIVE-16 踩过的"边写进去但没有来源"）。
        _r = rel_map.get((_s, r0, _d), r0)
        if _r != r0:
            rel_renamed += 1
        new_key = f"{_s}{TRIPLE_SEP}{_r}{TRIPLE_SEP}{_d}"
        new_triples_source[new_key] = val

    report = {
        "schema_version": SCHEMA_VERSION,
        "kept_entities": len(kept),
        "filtered": filtered,
        "merged": merged,
        "unclassified": unclassified,
        "dropped_triples": dropped_triples,
        "dropped_junk": dropped_junk,
        "dropped_reverse": dropped_reverse,
        # R15-W02 新增（只在行尾追加 key，既有消费方按 key 取值不受影响）
        "dropped_reverse_existing": dropped_reverse_existing,
        "reverse_dup_skipped": reverse_dup_skipped,
        "predicate_conflict": predicate_conflicts,
        "predicate_rewritten": len(predicate_conflicts),
        "triples_source_rel_renamed": rel_renamed,
        "existing_pairs_loaded": len(existing_index),
        # R15/T-B01 新增：方向判定不再靠"先到者"，这些字段是它的可审计证据。
        "pair_key_scheme": PAIR_KEY_SCHEME,
        "relation_contract_source": _REL_REASON,
        "symmetric_dedup": symmetric_dedup,
        "spurious_direction": spurious_direction[:50],
        "spurious_direction_count": len(spurious_direction),
        "direction_conflict": direction_conflict[:50],
        "direction_conflict_count": len(direction_conflict),
        "direction_unresolved": direction_unresolved[:50],
        "direction_unresolved_count": len(direction_unresolved),
    }
    return new_triples, kept, new_triples_source, report
