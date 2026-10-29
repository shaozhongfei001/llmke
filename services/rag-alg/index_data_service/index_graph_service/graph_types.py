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


def is_valid_entity(name):
    """过滤纯数字、纯符号、结构词、过短/过长。返回 (bool, reason)。"""
    s = clean_name(name)
    if not s:
        return False, "empty"
    if s.lower() in STOPWORDS:
        return False, "stopword"
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
# ─────────────────────────────────────────────────────────────────────────────

def pair_key(rel, src, dst):
    """(关系名, 无序端点对) 的稳定键 —— 方向无关，是"同一条业务事实"的身份。

    刻意不含方向：反向边 `A -rel-> B` 与 `B -rel-> A` 是同一事实的两种写法，
    而 `A -rel1-> B` 与 `A -rel2-> B` 是不同事实（D7 同端点两谓词必须都保留）。
    """
    return (clean_name(rel), tuple(sorted((clean_name(src), clean_name(dst)))))


def as_pair_index(existing_pairs):
    """把多种形态的"已有三元组"统一成 pair 索引（set of pair_key）。

    接受：
      - None / 空           -> 空索引（等于只做批内去重，行为与旧版一致）
      - 三元组序列           -> [(src, rel, dst), ...] 或 [[src, rel, dst], ...]
      - 字典行               -> {"src|source": .., "rel|relationship": .., "dst|dest": ..}
      - 已构建的 pair 索引   -> {(rel, (a, b)), ...}（幂等，可反复传入）

    刻意 **fail-closed**：遇到无法识别的元素直接抛 ValueError，而不是跳过。
    理由：静默跳过会让索引变空 -> 去重全程空转却仍报"去重已启用"，
    正是本项目反复出现的"假绿"形态（断言恒真、门禁全绿而结论为空）。
    """
    if not existing_pairs:
        return set()
    index = set()
    for item in existing_pairs:
        if isinstance(item, dict):
            src = item.get("src", item.get("source"))
            rel = item.get("rel", item.get("relationship"))
            dst = item.get("dst", item.get("dest", item.get("target")))
        elif isinstance(item, (tuple, list)):
            if len(item) == 3:
                src, rel, dst = item[0], item[1], item[2]
            elif len(item) == 2 and isinstance(item[1], (tuple, list, set, frozenset)):
                # 已是 pair_key 形态：(rel, (a, b))
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
        index.add(pair_key(rel, src, dst))
    return index


def is_reverse_duplicate(src, rel, dst, existing_pairs):
    """该三元组是否与 existing_pairs 中已有事实"同关系名 + 同无序端点对"。

    existing_pairs 可以是 as_pair_index() 的结果，也可以直接传原始三元组序列。
    方向是否相反由证据/原文决定，本函数不做业务猜测 —— 它只回答
    "同一个 (关系, 无序对) 是否已经被写过"，避免同一事实在存储里出现两个方向。
    """
    if not existing_pairs:
        return False
    if isinstance(existing_pairs, (set, frozenset)):
        # set 里可能是已构建的 pair_key（2 元组），也可能是原始三元组（3 元组）
        first = next(iter(existing_pairs), None)
        index = existing_pairs if (first is not None and len(first) == 2) else as_pair_index(existing_pairs)
    else:
        index = as_pair_index(existing_pairs)
    return pair_key(rel, src, dst) in index


def build_pair_index(triples):
    """从三元组序列构建 pair 索引（写入前给 is_reverse_duplicate / filter 用）。"""
    return as_pair_index(triples)


def filter_reverse_duplicates(triples, existing_pairs=None):
    """按"同关系名 + 同无序端点对"过滤三元组，返回 (kept, skipped)。

    - existing_pairs：存储里已存在的三元组（跨批次）；不传则等价于"只去批内重复"。
    - skipped 原样返回被跳过的三元组，供调用方记录/审计，**不静默丢弃**。
    """
    seen = as_pair_index(existing_pairs)
    kept, skipped = [], []
    for triple in triples or []:
        try:
            src, rel, dst = triple[0], triple[1], triple[2]
        except Exception:
            kept.append(triple)   # 形态不合法的交给下游既有校验，不在这里吞掉
            continue
        key = pair_key(rel, src, dst)
        if key in seen:
            skipped.append(triple)
            continue
        seen.add(key)
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
    形态见 as_pair_index()。传入后，与已有事实"同关系名 + 同无序端点对"的新三元组
    会被跳过并记入 report['dropped_reverse_existing'] / report['reverse_dup_skipped']。
    不传时行为与旧版一致（只做批内去重），调用方无需改动即可保持兼容。
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
        bucket["e_type"] = [typ]
        if typ == "unclassified":
            unclassified.append(canon)

    # 重写三元组
    new_triples = []
    dropped_triples = 0
    dropped_junk = 0

    def _junk(rel, a, b):
        """R15 W01：明显不是三元组形态的抽取产物。

        实测脏样例：'1000万元 -[最高额度-信用部分不超过->8000万元]-> 信用部分最高额度为1000万元…'
        特征：关系名里塞了值/箭头/逗号，或实体名是整句话。
        这些进图后会污染社区摘要与推导，宁可在落库前丢弃。
        """
        if "->" in rel or "，" in rel or "," in rel or len(rel) > 20:
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

    # R15 W02：逆否去重。抽取模型会把同一事实正反各输出一次
    #（实测 '智造贷 -最高额度-> 8000万元' 与 '8000万元 -最高额度-> 智造贷' 并存），
    # 进图后社区摘要会重复计数、reduce 也会把方向说反。
    # 同一 (关系, 无序实体对) 只保留首次出现的方向；方向是否正确由抽取与证据回指保证，
    # 这里不做业务猜测。
    #
    # R15-W02/A02：seen_pairs 预置 existing_pairs（存储里已存在的三元组），
    # 于是"本批已写过的"与"历史批次已写过的"用同一套判定 —— 内存窗口之外的反向事实
    # 也能在这里被拦住（前提是调用方把存储回读传进来）。
    existing_index = as_pair_index(existing_pairs)
    deduped, seen_pairs = [], set(existing_index)
    dropped_reverse = 0            # 批内重复
    dropped_reverse_existing = 0   # 与存储已有事实重复（跨批次）
    reverse_dup_skipped = []
    for src, rel, dst in new_triples:
        pair = pair_key(rel, src, dst)
        if pair in seen_pairs:
            if pair in existing_index:
                dropped_reverse_existing += 1
            else:
                dropped_reverse += 1
            if len(reverse_dup_skipped) < 50:   # 审计用，不无限增长
                reverse_dup_skipped.append({"src": src, "rel": rel, "dst": dst,
                                            "scope": "existing" if pair in existing_index else "batch"})
            continue
        seen_pairs.add(pair)
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
    }
    return new_triples, kept, new_triples_source, report
